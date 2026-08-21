"""Wizdroid Tools — VL Image Extract (image → prompt / flatlay / makeup / …).

Vision-language extraction from a ComfyUI source IMAGE. Mode dropdown selects
what to pull out (full reverse prompt, outfit flatlay, makeup, etc.).
Spice 0–10 controls SFW → explicit NSFW description of content present in
the image.

Category: 🧙 Wizdroid/VL
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Tuple

from lib.constants import DEFAULT_OLLAMA_URL
from lib.ollama_client import collect_vision_models, generate_with_image
from lib.vl_extract_prompts import (
    build_extract_system_prompt,
    build_extract_user_prompt,
    get_extract_mode_choices,
    get_extract_mode_labels,
    mode_meta,
    sanitize_extract_text,
)

logger = logging.getLogger(__name__)


class WizdroidVLExtract:
    """Extract structured prompt text from a source image via a VL Ollama model.

    Modes (from ``data/vl_extract/modes.json``): image prompt reverse, outfit
    flatlay, wardrobe breakdown, makeup, hairstyle, accessories, jewelry,
    tattoos, pose/body, full character, scene, style tags, custom.

    Requires a vision-capable model (llava, qwen2.5-vl, gemma3, minicpm-v, …).
    """

    CATEGORY = "🧙 Wizdroid/VL"
    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("text", "raw")
    FUNCTION = "extract"
    OUTPUT_NODE = False
    DESCRIPTION = (
        "Vision-language extract: reverse an image into a prompt, outfit "
        "flatlay, makeup description, or other mode. Spice 0–10 for SFW→NSFW."
    )

    @classmethod
    def INPUT_TYPES(cls) -> Dict[str, Any]:
        models = collect_vision_models(DEFAULT_OLLAMA_URL)
        mode_ids = get_extract_mode_choices()
        labels = get_extract_mode_labels()
        # Show human labels in the dropdown; resolve back to id at runtime.
        mode_labels = [labels.get(m, m) for m in mode_ids]
        default_mode = mode_labels[0] if mode_labels else "Image prompt (full reverse)"

        mode_tooltip = (
            "What to extract from the image. Modes live in "
            "data/vl_extract/modes.json — edit JSON and refresh the page to "
            "add/change options. outfit flatlay = product-style garment list; "
            "image prompt = full reverse caption for T2I."
        )

        return {
            "required": {
                "image": (
                    "IMAGE",
                    {
                        "tooltip": "Source image for VL analysis (ComfyUI IMAGE).",
                    },
                ),
                "mode": (
                    mode_labels,
                    {
                        "default": default_mode,
                        "tooltip": mode_tooltip,
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
                            "gemma3, minicpm-v, …). Refresh page for new models."
                        ),
                    },
                ),
                "spice": (
                    "INT",
                    {
                        "default": 5,
                        "min": 0,
                        "max": 10,
                        "step": 1,
                        "tooltip": (
                            "0 = fully SFW phrasing; 10 = maximally explicit NSFW "
                            "description of content that is actually in the image. "
                            "Guidance from data/prompts/spice.json."
                        ),
                    },
                ),
                "detail": (
                    "INT",
                    {
                        "default": 7,
                        "min": 0,
                        "max": 10,
                        "step": 1,
                        "tooltip": (
                            "How dense the extract should be. From "
                            "data/prompts/detail.json."
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
                        "tooltip": (
                            "LLM temperature. Lower (0.2–0.4) for faithful "
                            "extraction; higher for freer wording."
                        ),
                    },
                ),
                "max_tokens": (
                    "INT",
                    {
                        "default": 512,
                        "min": 64,
                        "max": 4096,
                        "step": 32,
                        "tooltip": "Output token budget for the extract.",
                    },
                ),
            },
            "optional": {
                "extra_instructions": (
                    "STRING",
                    {
                        "default": "",
                        "multiline": True,
                        "tooltip": (
                            "Optional focus (e.g. 'focus on shoes only', "
                            "'tags only, no prose'). Required intent for mode "
                            "Custom extraction; empty custom falls back to full "
                            "image prompt."
                        ),
                    },
                ),
                "seed": (
                    "INT",
                    {
                        "default": 0,
                        "min": 0,
                        "max": 0xFFFFFFFF,
                        "tooltip": "0 = random.",
                    },
                ),
                "max_image_side": (
                    "INT",
                    {
                        "default": 1280,
                        "min": 256,
                        "max": 2048,
                        "step": 64,
                        "tooltip": (
                            "Downscale longest image side before sending to "
                            "Ollama (saves VRAM/time)."
                        ),
                    },
                ),
            },
        }

    def extract(
        self,
        image: Any = None,
        mode: str = "image_prompt",
        ollama_url: str = DEFAULT_OLLAMA_URL,
        ollama_model: str = "",
        spice: int = 5,
        detail: int = 7,
        temperature: float = 0.35,
        max_tokens: int = 512,
        extra_instructions: str = "",
        seed: int = 0,
        max_image_side: int = 1280,
    ) -> Tuple[str, str]:
        if image is None:
            err = "Error: image input is required for VL extract."
            return (err, err)

        spice = max(0, min(10, int(spice)))
        detail = max(0, min(10, int(detail)))
        max_tokens = max(64, min(4096, int(max_tokens)))
        seed = int(seed) & 0xFFFFFFFF
        max_image_side = max(256, min(2048, int(max_image_side)))

        mode_id, mode_label = mode_meta(mode)
        system_prompt = build_extract_system_prompt(
            mode=mode_id,
            spice=spice,
            detail=detail,
            extra_instructions=extra_instructions,
        )
        user_prompt = build_extract_user_prompt(
            mode=mode_id,
            spice=spice,
            detail=detail,
            extra_instructions=extra_instructions,
        )

        logger.debug(
            "VL extract: mode=%s (%s) model=%s spice=%d detail=%d tokens=%d",
            mode_id,
            mode_label,
            ollama_model,
            spice,
            detail,
            max_tokens,
        )

        ok, response = generate_with_image(
            ollama_url=ollama_url,
            model=ollama_model,
            system=system_prompt,
            prompt=user_prompt,
            image=image,
            temperature=temperature,
            max_tokens=max_tokens,
            seed=seed if seed != 0 else 0,
            timeout=240,
            max_side=max_image_side,
        )

        if not ok:
            logger.error("VL extract failed: %s", response)
            err = f"Error: {response}"
            return (err, err)

        cleaned = sanitize_extract_text(response)
        raw = (response or "").strip()
        if not cleaned and raw:
            cleaned = raw
        return (cleaned, raw)


NODE_CLASS_MAPPINGS = {
    "WizdroidVLExtract": WizdroidVLExtract,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "WizdroidVLExtract": "🧙 Image Extract",
}
