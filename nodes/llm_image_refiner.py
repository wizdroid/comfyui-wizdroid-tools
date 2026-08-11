"""Wizdroid Tools — Image Prompt Refiner (iterative).

Refine an image prompt with a change request. Optionally attach a reference
IMAGE so the model can see what it is iterating on (VL model). When session
memory is enabled, the last refined prompt is remembered per session_id, so
you can refine again and again by just changing the instruction.

Category: 🧙 Wizdroid/LLM
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Tuple

from lib.constants import DEFAULT_OLLAMA_URL
from lib.ollama_client import collect_models, generate_text, generate_with_image
from lib.refine_prompts import (
    build_refine_system_prompt,
    build_refine_user_prompt,
    clear_session_prompt,
    get_session_prompt,
    parse_refine_response,
    set_session_prompt,
)

logger = logging.getLogger(__name__)


class WizdroidImageRefiner:
    """Refine an image prompt iteratively via Ollama (optionally VL)."""

    CATEGORY = "🧙 Wizdroid/LLM"
    RETURN_TYPES = ("STRING", "STRING", "STRING")
    RETURN_NAMES = ("refined_prompt", "revision_note", "raw")
    FUNCTION = "refine"
    OUTPUT_NODE = False
    DESCRIPTION = (
        "Refine an image prompt with a change request. Optional reference "
        "image (VL) and in-session memory for iterative refinement."
    )

    @classmethod
    def INPUT_TYPES(cls) -> Dict[str, Any]:
        models = collect_models(DEFAULT_OLLAMA_URL)

        return {
            "required": {
                "current_prompt": (
                    "STRING",
                    {
                        "default": "",
                        "multiline": True,
                        "tooltip": (
                            "The prompt to refine. When session memory is ON and "
                            "a stored prompt exists, the stored prompt is used "
                            "as the base instead."
                        ),
                    },
                ),
                "instruction": (
                    "STRING",
                    {
                        "default": "",
                        "multiline": True,
                        "tooltip": (
                            "What to change, e.g. 'make the lighting more dramatic' "
                            "or 'add a cyberpunk city background'."
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
                            "Use a vision-language model (llava, qwen2.5-vl, …) "
                            "when a reference image is connected."
                        ),
                    },
                ),
                "temperature": (
                    "FLOAT",
                    {
                        "default": 0.7,
                        "min": 0.0,
                        "max": 2.0,
                        "step": 0.05,
                        "tooltip": "LLM temperature.",
                    },
                ),
                "max_tokens": (
                    "INT",
                    {
                        "default": 384,
                        "min": 32,
                        "max": 2048,
                        "step": 32,
                        "tooltip": "Refined prompt length budget.",
                    },
                ),
                "use_session_memory": (
                    "BOOLEAN",
                    {
                        "default": False,
                        "tooltip": (
                            "ON = remember the last refined prompt for this "
                            "session_id and use it as the base on the next run."
                        ),
                    },
                ),
                "session_id": (
                    "STRING",
                    {
                        "default": "default",
                        "multiline": False,
                        "tooltip": "Key for the in-session memory buffer.",
                    },
                ),
            },
            "optional": {
                "image": (
                    "IMAGE",
                    {
                        "tooltip": "Optional reference image (requires a VL model).",
                    },
                ),
                "extra_instructions": (
                    "STRING",
                    {
                        "default": "",
                        "multiline": True,
                        "tooltip": "Extra refinement rules, e.g. 'keep it under 40 words'.",
                    },
                ),
                "clear_memory": (
                    "BOOLEAN",
                    {
                        "default": False,
                        "tooltip": "ON = clear this session's memory before refining.",
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
                        "tooltip": "Downscale reference image before sending to Ollama.",
                    },
                ),
            },
        }

    def refine(
        self,
        current_prompt: str = "",
        instruction: str = "",
        ollama_url: str = DEFAULT_OLLAMA_URL,
        ollama_model: str = "",
        temperature: float = 0.7,
        max_tokens: int = 384,
        use_session_memory: bool = False,
        session_id: str = "default",
        image: Any = None,
        extra_instructions: str = "",
        clear_memory: bool = False,
        seed: int = 0,
        max_image_side: int = 1280,
    ) -> Tuple[str, str, str]:
        if clear_memory:
            clear_session_prompt(session_id)

        instruction = (instruction or "").strip()
        if not instruction:
            return (
                "Error: instruction is empty. Tell the refiner what to change.",
                "",
                "",
            )

        # Base prompt: stored memory (if enabled) takes priority.
        if use_session_memory:
            stored = get_session_prompt(session_id)
            if stored:
                current_prompt = stored
        current_prompt = (current_prompt or "").strip()
        if not current_prompt:
            return (
                "Error: current_prompt is empty and no stored prompt exists.",
                "",
                "",
            )

        system_prompt = build_refine_system_prompt(
            max_tokens=max_tokens,
            extra_instructions=extra_instructions,
        )
        user_prompt = build_refine_user_prompt(
            current_prompt=current_prompt,
            instruction=instruction,
            with_image=image is not None,
        )

        if image is not None:
            ok, response = generate_with_image(
                ollama_url=ollama_url,
                model=ollama_model,
                system=system_prompt,
                prompt=user_prompt,
                image=image,
                temperature=temperature,
                max_tokens=max_tokens,
                seed=seed,
                timeout=300,
                max_side=max_image_side,
            )
        else:
            ok, response = generate_text(
                ollama_url=ollama_url,
                model=ollama_model,
                system=system_prompt,
                prompt=user_prompt,
                temperature=temperature,
                max_tokens=max_tokens,
                seed=seed,
                timeout=300,
            )

        if not ok:
            logger.error("Refine failed: %s", response)
            return (f"Error: {response}", "", response)

        note, refined, raw = parse_refine_response(response)
        if not refined:
            refined = current_prompt  # keep last known good prompt

        if use_session_memory and refined and not refined.startswith("Error"):
            set_session_prompt(session_id, refined)

        return (refined, note, raw)


# ---------------------------------------------------------------------------
# Node registration mappings
# ---------------------------------------------------------------------------
NODE_CLASS_MAPPINGS = {
    "WizdroidImageRefiner": WizdroidImageRefiner,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "WizdroidImageRefiner": "🧙 Image Prompt Refiner",
}
