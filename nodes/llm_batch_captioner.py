"""Wizdroid Tools — Batch Image Captioner (LoRA dataset prep).

Point at a folder of images; a vision-language Ollama model writes a caption
``<name>.txt`` next to every image. Mode dropdown selects captioning style
(booru tags, natural sentence, detailed, short) from
``data/batch_caption/modes.json``.

Category: 🧙 Wizdroid/VL
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Tuple

import numpy as np
from PIL import Image, ImageOps

from lib.batch_caption_prompts import (
    build_caption_system_prompt,
    build_caption_user_prompt,
    get_caption_mode_choices,
    get_caption_mode_labels,
    mode_meta,
    sanitize_caption,
)
from lib.constants import DEFAULT_OLLAMA_URL
from lib.ollama_client import collect_vision_models, generate_with_image

logger = logging.getLogger(__name__)

_IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif"}


class WizdroidBatchCaptioner:
    """Caption every image in a folder and write <name>.txt files."""

    CATEGORY = "🧙 Wizdroid/VL"
    RETURN_TYPES = ("STRING", "STRING", "INT", "INT")
    RETURN_NAMES = ("report", "last_caption", "processed", "failed")
    FUNCTION = "caption_folder"
    OUTPUT_NODE = False
    DESCRIPTION = (
        "Caption every image in a folder via a VL model and write "
        "<name>.txt caption files for LoRA dataset training."
    )

    @classmethod
    def INPUT_TYPES(cls) -> Dict[str, Any]:
        models = collect_vision_models(DEFAULT_OLLAMA_URL)
        mode_ids = get_caption_mode_choices()
        labels = get_caption_mode_labels()
        mode_labels = [labels.get(m, m) for m in mode_ids]

        return {
            "required": {
                "folder_path": (
                    "STRING",
                    {
                        "default": "",
                        "multiline": False,
                        "tooltip": (
                            "Absolute path to the folder of training images. "
                            "A <name>.txt caption is written next to each image."
                        ),
                    },
                ),
                "ollama_url": (
                    "STRING",
                    {
                        "default": DEFAULT_OLLAMA_URL,
                        "tooltip": "Ollama server URL.",
                    },
                ),
                "ollama_model": (
                    models,
                    {
                        "default": models[0] if models else "no_models_found",
                        "tooltip": (
                            "Vision-language model required (llava, qwen2.5-vl, "
                            "gemma3, minicpm-v, …)."
                        ),
                    },
                ),
                "caption_mode": (
                    mode_labels,
                    {
                        "default": mode_labels[0] if mode_labels else "Booru tags (comma-separated)",
                        "tooltip": (
                            "Captioning style. Modes live in "
                            "data/batch_caption/modes.json — edit and refresh to "
                            "add/change options."
                        ),
                    },
                ),
                "temperature": (
                    "FLOAT",
                    {
                        "default": 0.35,
                        "min": 0.0,
                        "max": 2.0,
                        "step": 0.05,
                        "tooltip": "Lower (0.2–0.4) for faithful captions.",
                    },
                ),
                "max_tokens": (
                    "INT",
                    {
                        "default": 256,
                        "min": 32,
                        "max": 2048,
                        "step": 32,
                        "tooltip": "Max caption length in tokens.",
                    },
                ),
                "max_images": (
                    "INT",
                    {
                        "default": 100,
                        "min": 1,
                        "max": 100000,
                        "step": 1,
                        "tooltip": "Cap on how many images to process this run.",
                    },
                ),
                "max_image_side": (
                    "INT",
                    {
                        "default": 1280,
                        "min": 256,
                        "max": 2048,
                        "step": 64,
                        "tooltip": "Downscale longest image side before sending to Ollama.",
                    },
                ),
                "overwrite": (
                    "BOOLEAN",
                    {
                        "default": False,
                        "tooltip": (
                            "ON = re-caption and overwrite existing .txt files. "
                            "OFF = skip images that already have a caption."
                        ),
                    },
                ),
                "recursive": (
                    "BOOLEAN",
                    {
                        "default": False,
                        "tooltip": "ON = also caption images in subfolders.",
                    },
                ),
            },
            "optional": {
                "extra_instructions": (
                    "STRING",
                    {
                        "default": "",
                        "multiline": True,
                        "tooltip": "Extra captioning guidance, e.g. 'always include the character name'.",
                    },
                ),
            },
        }

    def caption_folder(
        self,
        folder_path: str = "",
        ollama_url: str = DEFAULT_OLLAMA_URL,
        ollama_model: str = "",
        caption_mode: str = "",
        temperature: float = 0.35,
        max_tokens: int = 256,
        max_images: int = 100,
        max_image_side: int = 1280,
        overwrite: bool = False,
        recursive: bool = False,
        extra_instructions: str = "",
    ) -> Tuple[str, str, int, int]:
        folder = Path(folder_path or "").expanduser().resolve()
        if not folder.is_dir():
            return (
                f"Error: folder not found: {folder}",
                "",
                0,
                0,
            )

        mode_id, mode_label = mode_meta(caption_mode)
        system_prompt = build_caption_system_prompt(mode_id, extra_instructions)
        user_prompt = build_caption_user_prompt(mode_id, extra_instructions)

        pattern = "**/*" if recursive else "*"
        image_files: List[Path] = []
        for p in folder.glob(pattern):
            if p.is_file() and p.suffix.lower() in _IMAGE_EXTS:
                image_files.append(p)
        image_files.sort()
        image_files = image_files[: max(1, int(max_images))]

        if not image_files:
            return (
                f"No images found in {folder} (recursive={recursive}).",
                "",
                0,
                0,
            )

        processed = 0
        failed = 0
        skipped = 0
        last_caption = ""
        errors: List[str] = []

        for img_path in image_files:
            txt_path = img_path.with_suffix(".txt")
            if txt_path.exists() and not overwrite:
                skipped += 1
                continue

            try:
                with Image.open(img_path) as pil:
                    pil = ImageOps.exif_transpose(pil).convert("RGB")
                    arr = np.array(pil)
            except Exception as exc:  # noqa: BLE001
                failed += 1
                errors.append(f"{img_path.name}: open error {exc}")
                continue

            ok, response = generate_with_image(
                ollama_url=ollama_url,
                model=ollama_model,
                system=system_prompt,
                prompt=user_prompt,
                image=arr,
                temperature=temperature,
                max_tokens=max_tokens,
                timeout=180,
                max_side=max_image_side,
            )
            if not ok:
                failed += 1
                errors.append(f"{img_path.name}: {response}")
                continue

            caption = sanitize_caption(response)
            if not caption:
                failed += 1
                errors.append(f"{img_path.name}: empty caption")
                continue

            try:
                txt_path.write_text(caption + "\n", encoding="utf-8")
            except Exception as exc:  # noqa: BLE001
                failed += 1
                errors.append(f"{img_path.name}: write error {exc}")
                continue

            processed += 1
            last_caption = caption
            logger.info("Captioned %s", img_path.name)

        lines = [
            f"Batch caption done: {processed} captioned, {skipped} skipped, {failed} failed "
            f"({len(image_files)} total, mode={mode_label}).",
            f"Folder: {folder}",
        ]
        if errors:
            lines.append("Errors:")
            lines.extend(f"  - {e}" for e in errors[:20])
            if len(errors) > 20:
                lines.append(f"  … and {len(errors) - 20} more.")
        report = "\n".join(lines)

        return (report, last_caption, processed, failed)


# ---------------------------------------------------------------------------
# Node registration mappings
# ---------------------------------------------------------------------------
NODE_CLASS_MAPPINGS = {
    "WizdroidBatchCaptioner": WizdroidBatchCaptioner,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "WizdroidBatchCaptioner": "🧙 Batch Image Captioner",
}
