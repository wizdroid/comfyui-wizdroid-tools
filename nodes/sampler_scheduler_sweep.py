"""Sequential KSampler × scheduler sweep with GPU cooldown and labeled outputs.

Runs each sampler/scheduler pair one at a time (not a list-map), sleeps between
combos so the GPU can cool down, burns the pair name onto the image, and saves
each file as ``{prefix}/{sampler}__{scheduler}_*.png``.
"""

from __future__ import annotations

import json
import logging
import re
import time
from itertools import product
from pathlib import Path
from typing import Any, Dict, List, Tuple

import numpy as np
import torch
from PIL import Image, ImageDraw, ImageFont
from PIL.PngImagePlugin import PngInfo

import comfy.model_management
import comfy.sample
import comfy.samplers
import comfy.utils
import folder_paths
import latent_preview
from comfy.cli_args import args

logger = logging.getLogger(__name__)

CATEGORY = "🧙 Wizdroid/Utils"

_SAFE_NAME = re.compile(r"[^A-Za-z0-9._-]+")

DEFAULT_SAMPLERS = """euler
exp_heun_2_x0
exp_heun_2_x0_sde
dpmpp_2m
res_multistep
er_sde
sa_solver
uni_pc
lcm"""

DEFAULT_SCHEDULERS = """simple
beta
beta57
bong_tangent
sgm_uniform
normal
linear_quadratic"""

DEFAULT_SKIP = """dpm_adaptive
dpm_fast
ddpm"""


def _parse_names(text: str) -> List[str]:
    names: List[str] = []
    seen = set()
    for raw in text.replace(",", "\n").splitlines():
        name = raw.strip()
        if not name or name.startswith("#"):
            continue
        if name not in seen:
            names.append(name)
            seen.add(name)
    return names


def _safe_filename(name: str) -> str:
    cleaned = _SAFE_NAME.sub("_", name).strip("._")
    return cleaned or "unnamed"


def _load_font(size: int) -> ImageFont.ImageFont:
    candidates = [
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
        Path("/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"),
        Path(__file__).resolve().parents[2]
        / "comfyui_essentials"
        / "fonts"
        / "ShareTechMono-Regular.ttf",
    ]
    for path in candidates:
        if path.is_file():
            return ImageFont.truetype(str(path), size)
    return ImageFont.load_default()


def _overlay_label(image: torch.Tensor, sampler: str, scheduler: str) -> torch.Tensor:
    arr = (image[0].detach().cpu().numpy() * 255.0).clip(0, 255).astype(np.uint8)
    if arr.shape[-1] == 1:
        arr = np.repeat(arr, 3, axis=-1)
    elif arr.shape[-1] > 3:
        arr = arr[..., :3]
    base = Image.fromarray(arr, mode="RGB").convert("RGBA")
    overlay = Image.new("RGBA", base.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    width, height = base.size
    bar_h = max(44, height // 16)
    draw.rectangle((0, height - bar_h, width, height), fill=(0, 0, 0, 188))
    label = f"{sampler}  |  {scheduler}"
    font = _load_font(max(18, bar_h - 18))
    bbox = draw.textbbox((0, 0), label, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    x = max(12, (width - text_w) // 2)
    y = height - bar_h + max(4, (bar_h - text_h) // 2) - bbox[1]
    draw.text((x + 2, y + 2), label, font=font, fill=(0, 0, 0, 220))
    draw.text((x, y), label, font=font, fill=(255, 255, 255, 255))
    out = Image.alpha_composite(base, overlay).convert("RGB")
    tensor = torch.from_numpy(np.array(out).astype(np.float32) / 255.0)
    return tensor.unsqueeze(0)


def _ksampler(model, seed, steps, cfg, sampler_name, scheduler, positive, negative, latent, denoise=1.0):
    latent_image = latent["samples"]
    latent_image = comfy.sample.fix_empty_latent_channels(
        model,
        latent_image,
        latent.get("downscale_ratio_spacial", None),
        latent.get("downscale_ratio_temporal", None),
    )
    batch_inds = latent["batch_index"] if "batch_index" in latent else None
    noise = comfy.sample.prepare_noise(latent_image, seed, batch_inds)
    noise_mask = latent.get("noise_mask")
    callback = latent_preview.prepare_callback(model, steps)
    disable_pbar = not comfy.utils.PROGRESS_BAR_ENABLED
    samples = comfy.sample.sample(
        model,
        noise,
        steps,
        cfg,
        sampler_name,
        scheduler,
        positive,
        negative,
        latent_image,
        denoise=denoise,
        noise_mask=noise_mask,
        callback=callback,
        disable_pbar=disable_pbar,
        seed=seed,
    )
    out = latent.copy()
    out.pop("downscale_ratio_spacial", None)
    out.pop("downscale_ratio_temporal", None)
    out["samples"] = samples
    return out


def _decode(vae, latent: Dict[str, Any]) -> torch.Tensor:
    samples = latent["samples"]
    if getattr(samples, "is_nested", False):
        samples = samples.unbind()[0]
    images = vae.decode(samples)
    if len(images.shape) == 5:
        images = images.reshape(-1, images.shape[-3], images.shape[-2], images.shape[-1])
    return images.detach().cpu()


class WizdroidSamplerSchedulerSweep:
    """Cartesian KSampler/scheduler sweep, sequential, with cooldown + labels."""

    CATEGORY = CATEGORY
    RETURN_TYPES = ("IMAGE", "STRING")
    RETURN_NAMES = ("images", "report")
    FUNCTION = "sweep"
    OUTPUT_NODE = True
    DESCRIPTION = (
        "Run every sampler × scheduler pair one at a time, sleep between combos "
        "for GPU cooldown, overlay the pair name on each image, and save files "
        "named {prefix}/{sampler}__{scheduler}."
    )

    @classmethod
    def INPUT_TYPES(cls) -> Dict[str, Any]:
        return {
            "required": {
                "model": ("MODEL",),
                "positive": ("CONDITIONING",),
                "negative": ("CONDITIONING",),
                "latent_image": ("LATENT",),
                "vae": ("VAE",),
                "seed": (
                    "INT",
                    {
                        "default": 42,
                        "min": 0,
                        "max": 0xFFFFFFFFFFFFFFFF,
                        "control_after_generate": True,
                        "tooltip": "Keep this fixed so every combo uses the same noise.",
                    },
                ),
                "steps": ("INT", {"default": 8, "min": 1, "max": 10000}),
                "cfg": (
                    "FLOAT",
                    {"default": 1.0, "min": 0.0, "max": 100.0, "step": 0.1},
                ),
                "denoise": (
                    "FLOAT",
                    {"default": 1.0, "min": 0.0, "max": 1.0, "step": 0.01},
                ),
                "samplers": (
                    "STRING",
                    {
                        "default": DEFAULT_SAMPLERS,
                        "multiline": True,
                        "tooltip": "One sampler per line (or comma-separated). Ignored when use_all_installed is on.",
                    },
                ),
                "schedulers": (
                    "STRING",
                    {
                        "default": DEFAULT_SCHEDULERS,
                        "multiline": True,
                        "tooltip": "One scheduler per line (or comma-separated). Ignored when use_all_installed is on.",
                    },
                ),
                "cooldown_seconds": (
                    "FLOAT",
                    {
                        "default": 1.0,
                        "min": 0.0,
                        "max": 60.0,
                        "step": 0.1,
                        "tooltip": "Pause after each combo so the GPU can cool down.",
                    },
                ),
                "overlay": (
                    "BOOLEAN",
                    {
                        "default": True,
                        "tooltip": "Burn 'sampler | scheduler' onto the bottom of each image.",
                    },
                ),
                "filename_prefix": (
                    "STRING",
                    {"default": "krea2-sweep"},
                ),
            },
            "optional": {
                "use_all_installed": (
                    "BOOLEAN",
                    {
                        "default": False,
                        "tooltip": "Ignore the text lists and sweep every sampler/scheduler ComfyUI currently exposes (still honors skip_names; drops *_gpu duplicates).",
                    },
                ),
                "skip_names": (
                    "STRING",
                    {
                        "default": DEFAULT_SKIP,
                        "multiline": True,
                        "tooltip": "Sampler or scheduler names to skip. dpm_adaptive is skipped by default because it can hang.",
                    },
                ),
                "continue_on_error": (
                    "BOOLEAN",
                    {
                        "default": True,
                        "tooltip": "Skip a failing combo and keep going. Turn off to abort the sweep on the first error.",
                    },
                ),
            },
            "hidden": {
                "prompt": "PROMPT",
                "extra_pnginfo": "EXTRA_PNGINFO",
            },
        }

    @classmethod
    def IS_CHANGED(cls, **_kwargs) -> float:
        return float("nan")

    def sweep(
        self,
        model,
        positive,
        negative,
        latent_image,
        vae,
        seed: int,
        steps: int,
        cfg: float,
        denoise: float,
        samplers: str,
        schedulers: str,
        cooldown_seconds: float,
        overlay: bool,
        filename_prefix: str,
        use_all_installed: bool = False,
        skip_names: str = DEFAULT_SKIP,
        continue_on_error: bool = True,
        prompt=None,
        extra_pnginfo=None,
    ) -> Dict[str, Any]:
        sampler_names, scheduler_names, skipped_unknown = self._resolve_lists(
            samplers, schedulers, use_all_installed, skip_names
        )
        combos = list(product(sampler_names, scheduler_names))
        if not combos:
            raise ValueError("No sampler/scheduler pairs left after filtering.")

        logger.info(
            "Sampler sweep: %s samplers × %s schedulers = %s combos (seed=%s steps=%s cfg=%s cooldown=%ss)",
            len(sampler_names),
            len(scheduler_names),
            len(combos),
            seed,
            steps,
            cfg,
            cooldown_seconds,
        )

        output_dir = folder_paths.get_output_directory()
        labeled: List[torch.Tensor] = []
        ui_images: List[Dict[str, str]] = []
        report_lines: List[str] = []
        for name in skipped_unknown:
            report_lines.append(f"SKIP unknown  {name}")

        pbar = comfy.utils.ProgressBar(len(combos))
        for index, (sampler_name, scheduler_name) in enumerate(combos):
            comfy.model_management.throw_exception_if_processing_interrupted()
            pair = f"{sampler_name} | {scheduler_name}"
            logger.info("Sweep %s/%s  %s", index + 1, len(combos), pair)
            try:
                latent_in = dict(latent_image)
                samples_in = latent_in.get("samples")
                if torch.is_tensor(samples_in):
                    latent_in["samples"] = samples_in.clone()
                latent_out = _ksampler(
                    model,
                    seed,
                    steps,
                    cfg,
                    sampler_name,
                    scheduler_name,
                    positive,
                    negative,
                    latent_in,
                    denoise=denoise,
                )
                decoded = _decode(vae, latent_out)
                del latent_out
                frames = []
                for frame in decoded:
                    frame = frame.unsqueeze(0)
                    if overlay:
                        frame = _overlay_label(frame, sampler_name, scheduler_name)
                    frames.append(frame)
                image = torch.cat(frames, dim=0)
                saved = self._save_images(
                    image,
                    filename_prefix,
                    sampler_name,
                    scheduler_name,
                    output_dir,
                    prompt,
                    extra_pnginfo,
                )
                ui_images.extend(saved)
                labeled.append(image)
                report_lines.append(f"OK    {pair}")
            except comfy.model_management.InterruptProcessingException:
                raise
            except torch.cuda.OutOfMemoryError as exc:
                report_lines.append(f"OOM   {pair}  {exc}")
                logger.warning("Sweep OOM on %s: %s", pair, exc)
                torch.cuda.empty_cache()
                if not continue_on_error:
                    raise
            except Exception as exc:
                report_lines.append(f"FAIL  {pair}  {type(exc).__name__}: {exc}")
                logger.warning("Sweep failed on %s: %s", pair, exc)
                if not continue_on_error:
                    raise
            pbar.update(1)
            if index + 1 < len(combos) and cooldown_seconds > 0:
                time.sleep(float(cooldown_seconds))

        if not labeled:
            raise RuntimeError(
                "Every sampler/scheduler combo failed:\n" + "\n".join(report_lines)
            )

        batched = torch.cat(labeled, dim=0)
        report = "\n".join(report_lines)
        return {
            "ui": {"images": ui_images},
            "result": (batched, report),
        }

    def _resolve_lists(
        self,
        samplers_text: str,
        schedulers_text: str,
        use_all_installed: bool,
        skip_text: str,
    ) -> Tuple[List[str], List[str], List[str]]:
        installed_samplers = list(comfy.samplers.KSampler.SAMPLERS)
        installed_schedulers = list(comfy.samplers.KSampler.SCHEDULERS)
        skip = set(_parse_names(skip_text))
        unknown: List[str] = []

        if use_all_installed:
            sampler_names = [
                name
                for name in installed_samplers
                if name not in skip and not name.endswith("_gpu")
            ]
            scheduler_names = [
                name for name in installed_schedulers if name not in skip
            ]
            return sampler_names, scheduler_names, unknown

        sampler_names = []
        for name in _parse_names(samplers_text):
            if name in skip:
                continue
            if name not in installed_samplers:
                unknown.append(f"sampler:{name}")
                continue
            sampler_names.append(name)

        scheduler_names = []
        for name in _parse_names(schedulers_text):
            if name in skip:
                continue
            if name not in installed_schedulers:
                unknown.append(f"scheduler:{name}")
                continue
            scheduler_names.append(name)

        return sampler_names, scheduler_names, unknown

    def _save_images(
        self,
        images: torch.Tensor,
        filename_prefix: str,
        sampler_name: str,
        scheduler_name: str,
        output_dir: str,
        prompt,
        extra_pnginfo,
    ) -> List[Dict[str, str]]:
        prefix = f"{filename_prefix.strip().rstrip('/')}/{_safe_filename(sampler_name)}__{_safe_filename(scheduler_name)}"
        full_output_folder, filename, counter, subfolder, _prefix = (
            folder_paths.get_save_image_path(
                prefix,
                output_dir,
                images[0].shape[1],
                images[0].shape[0],
            )
        )
        results: List[Dict[str, str]] = []
        for batch_number, image in enumerate(images):
            pixels = 255.0 * image.cpu().numpy()
            img = Image.fromarray(np.clip(pixels, 0, 255).astype(np.uint8))
            metadata = None
            if not args.disable_metadata:
                metadata = PngInfo()
                metadata.add_text("sampler", sampler_name)
                metadata.add_text("scheduler", scheduler_name)
                if prompt is not None:
                    metadata.add_text("prompt", json.dumps(prompt))
                if extra_pnginfo is not None:
                    for key, value in extra_pnginfo.items():
                        metadata.add_text(key, json.dumps(value))
            file_name = f"{filename.replace('%batch_num%', str(batch_number))}_{counter:05}_.png"
            img.save(
                str(Path(full_output_folder) / file_name),
                pnginfo=metadata,
                compress_level=4,
            )
            results.append(
                {"filename": file_name, "subfolder": subfolder, "type": "output"}
            )
            counter += 1
        return results


NODE_CLASS_MAPPINGS = {
    "WizdroidSamplerSchedulerSweep": WizdroidSamplerSchedulerSweep,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "WizdroidSamplerSchedulerSweep": "🧙 Sampler × Scheduler Sweep",
}
