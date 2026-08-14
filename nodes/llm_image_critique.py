"""Wizdroid Tools — Image Critique & Revision Node.

Feed a generated IMAGE + the prompt that made it; a VL model critiques it
and writes a revised, improved prompt. Focus dropdown (general, anatomy,
composition, lighting, style fidelity) from ``data/critique/modes.json``.

Category: 🧙 Wizdroid/VL
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Tuple

from lib.constants import DEFAULT_OLLAMA_URL
from lib.critique_prompts import (
    build_critique_system_prompt,
    build_critique_user_prompt,
    get_critique_mode_choices,
    get_critique_mode_labels,
    mode_meta,
    parse_critique_response,
)
from lib.ollama_client import collect_models, generate_with_image

logger = logging.getLogger(__name__)


class WizdroidImageCritique:
    """Critique a generated image and produce a revised prompt."""

    CATEGORY = "🧙 Wizdroid/VL"
    RETURN_TYPES = ("STRING", "STRING", "STRING")
    RETURN_NAMES = ("critique", "revised_prompt", "raw")
    FUNCTION = "critique"
    OUTPUT_NODE = False
    DESCRIPTION = (
        "Vision-language critique: analyze a generated image + its prompt and "
        "return a critique plus a revised, improved image prompt."
    )

    @classmethod
    def INPUT_TYPES(cls) -> Dict[str, Any]:
        models = collect_models(DEFAULT_OLLAMA_URL)
        mode_ids = get_critique_mode_choices()
        labels = get_critique_mode_labels()
        mode_labels = [labels.get(m, m) for m in mode_ids]

        return {
            "required": {
                "image": (
                    "IMAGE",
                    {
                        "tooltip": "The generated image to critique (ComfyUI IMAGE).",
                    },
                ),
                "prompt": (
                    "STRING",
                    {
                        "default": "",
                        "multiline": True,
                        "tooltip": "The image prompt that produced the image.",
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
                "focus": (
                    mode_labels,
                    {
                        "default": mode_labels[0] if mode_labels else "General critique",
                        "tooltip": (
                            "What the critique should focus on. Modes live in "
                            "data/critique/modes.json."
                        ),
                    },
                ),
                "temperature": (
                    "FLOAT",
                    {
                        "default": 0.4,
                        "min": 0.0,
                        "max": 2.0,
                        "step": 0.05,
                        "tooltip": "LLM temperature.",
                    },
                ),
                "max_tokens": (
                    "INT",
                    {
                        "default": 512,
                        "min": 64,
                        "max": 2048,
                        "step": 32,
                        "tooltip": "Output budget (critique + revised prompt).",
                    },
                ),
            },
            "optional": {
                "extra_instructions": (
                    "STRING",
                    {
                        "default": "",
                        "multiline": True,
                        "tooltip": "Extra focus, e.g. 'fix the hands' or 'make it more cinematic'.",
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
                        "tooltip": "Downscale longest image side before sending to Ollama.",
                    },
                ),
            },
        }

    def critique(
        self,
        image: Any = None,
        prompt: str = "",
        ollama_url: str = DEFAULT_OLLAMA_URL,
        ollama_model: str = "",
        focus: str = "",
        temperature: float = 0.4,
        max_tokens: int = 512,
        extra_instructions: str = "",
        seed: int = 0,
        max_image_side: int = 1280,
    ) -> Tuple[str, str, str]:
        if image is None:
            err = "Error: image input is required for critique."
            return (err, "", err)

        prompt = (prompt or "").strip()
        mode_id, mode_label = mode_meta(focus)

        system_prompt = build_critique_system_prompt(
            mode=mode_id,
            extra_instructions=extra_instructions,
        )
        user_prompt = build_critique_user_prompt(prompt)

        ok, response = generate_with_image(
            ollama_url=ollama_url,
            model=ollama_model,
            system=system_prompt,
            prompt=user_prompt,
            image=image,
            temperature=temperature,
            max_tokens=max_tokens,
            seed=seed,
            timeout=180,
            max_side=max_image_side,
        )

        if not ok:
            logger.error("Critique failed: %s", response)
            return (f"Error: {response}", "", response)

        critique_text, revised, raw = parse_critique_response(response)
        return (critique_text, revised, raw)


# ---------------------------------------------------------------------------
# Node registration mappings
# ---------------------------------------------------------------------------
NODE_CLASS_MAPPINGS = {
    "WizdroidImageCritique": WizdroidImageCritique,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "WizdroidImageCritique": "🧙 Image Critique",
}
