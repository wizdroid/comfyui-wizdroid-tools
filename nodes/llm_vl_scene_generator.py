"""Wizdroid Tools — VL Video Scene Generator (image + text → scene + dialogue).

Vision-language scene package grounded in a ComfyUI source IMAGE.
Category: 🧙 Wizdroid/LLM
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Tuple

from lib.constants import DEFAULT_OLLAMA_URL
from lib.ollama_client import collect_models, generate_with_image
from lib.scene_prompts import (
    build_vl_system_prompt,
    build_vl_user_prompt,
    clamp_duration,
    get_mood_choices,
    get_style_choices,
    get_video_model_choices,
    parse_scene_response,
)

logger = logging.getLogger(__name__)


class WizdroidVLSceneGenerator:
    """Generate a video scene package from a source image + user direction.

    Requires a vision-capable Ollama model (e.g. llava, qwen2.5-vl, gemma3,
    minicpm-v). Outputs motion/scene prompt, dialogue, and a refined still
    image prompt faithful to the source frame.
    """

    CATEGORY = "🧙 Wizdroid/LLM"
    RETURN_TYPES = ("STRING", "STRING", "STRING", "STRING")
    RETURN_NAMES = ("scene_prompt", "dialogue", "image_prompt", "raw")
    FUNCTION = "generate"
    OUTPUT_NODE = False
    DESCRIPTION = (
        "Vision-language video scene: analyze a source image + user direction "
        "into a timed scene prompt, dialogue, and keyframe image prompt "
        "(duration, mood, style)."
    )

    @classmethod
    def INPUT_TYPES(cls) -> Dict[str, Any]:
        models = collect_models(DEFAULT_OLLAMA_URL)
        moods = get_mood_choices()
        styles = get_style_choices()
        video_models = get_video_model_choices()
        return {
            "required": {
                "video_model": (
                    video_models,
                    {
                        "default": video_models[0] if video_models else "Generic (any video model)",
                        "tooltip": (
                            "Target video model. Selects model-specific meta prompts "
                            "(MiniMax, MiniMax H3, Hunyuan 3, Wan 2.2, Grok Imagine 1.5, LTX 2.3) "
                            "or the generic prompt set. Edit data/scene/video_models.json."
                        ),
                    },
                ),
                "image": (
                    "IMAGE",
                    {
                        "tooltip": "Source frame for I2V. VL model will read this image.",
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
                "user_prompt": (
                    "STRING",
                    {
                        "default": "",
                        "multiline": True,
                        "tooltip": (
                            "Direction for the clip (action, speech, camera). "
                            "Empty = subtle natural motion from the image."
                        ),
                    },
                ),
                "duration_seconds": (
                    "FLOAT",
                    {
                        "default": 5.0,
                        "min": 0.5,
                        "max": 120.0,
                        "step": 0.5,
                        "tooltip": "Target clip length in seconds (paces action & dialogue).",
                    },
                ),
                "mood": (
                    moods,
                    {
                        "default": moods[0] if moods else "neutral",
                        "tooltip": "Emotional tone of the scene.",
                    },
                ),
                "style": (
                    styles,
                    {
                        "default": "cinematic" if "cinematic" in styles else (styles[0] if styles else "cinematic"),
                        "tooltip": "Directorial / visual style (cinematic, candid, anime, …).",
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
                        "default": 1024,
                        "min": 128,
                        "max": 4096,
                        "step": 32,
                        "tooltip": "Output token budget for the full scene package.",
                    },
                ),
            },
            "optional": {
                "extra_instructions": (
                    "STRING",
                    {
                        "default": "",
                        "multiline": True,
                        "tooltip": "Optional constraints (keep wardrobe, add line of dialogue, camera only, …).",
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
                        "tooltip": "Downscale longest image side before sending to Ollama (saves VRAM/time).",
                    },
                ),
            },
        }

    def generate(
        self,
        video_model: str = "generic",
        image: Any = None,
        ollama_url: str = DEFAULT_OLLAMA_URL,
        ollama_model: str = "",
        user_prompt: str = "",
        duration_seconds: float = 5.0,
        mood: str = "neutral",
        style: str = "cinematic",
        temperature: float = 0.7,
        max_tokens: int = 1024,
        extra_instructions: str = "",
        seed: int = 0,
        max_image_side: int = 1280,
    ) -> Tuple[str, str, str, str]:
        if image is None:
            err = "Error: image input is required for VL scene generation."
            return (err, "", "", err)

        duration_seconds = clamp_duration(duration_seconds)
        max_tokens = max(128, min(4096, int(max_tokens)))
        seed = int(seed) & 0xFFFFFFFF
        max_image_side = max(256, min(2048, int(max_image_side)))

        system_prompt = build_vl_system_prompt(
            duration_seconds=duration_seconds,
            mood=mood,
            style=style,
            video_model=video_model,
        )
        generation_prompt = build_vl_user_prompt(
            user_prompt=user_prompt,
            duration_seconds=duration_seconds,
            mood=mood,
            style=style,
            extra_instructions=extra_instructions,
            video_model=video_model,
        )

        logger.debug(
            "VL scene: video_model=%s model=%s duration=%.1fs mood=%s style=%s tokens=%d",
            video_model,
            ollama_model,
            duration_seconds,
            mood,
            style,
            max_tokens,
        )

        ok, response = generate_with_image(
            ollama_url=ollama_url,
            model=ollama_model,
            system=system_prompt,
            prompt=generation_prompt,
            image=image,
            temperature=temperature,
            max_tokens=max_tokens,
            seed=seed if seed != 0 else 0,
            timeout=240,
            max_side=max_image_side,
        )

        if not ok:
            logger.error("VL scene generation failed: %s", response)
            err = f"Error: {response}"
            return (err, "", "", err)

        parsed = parse_scene_response(response)
        scene = parsed.get("scene") or ""
        dialogue = parsed.get("dialogue") or ""
        image_prompt = parsed.get("image_prompt") or ""
        raw = parsed.get("raw") or response

        if not scene and raw:
            scene = raw.strip()

        return (scene, dialogue, image_prompt, raw)


NODE_CLASS_MAPPINGS = {
    "WizdroidVLSceneGenerator": WizdroidVLSceneGenerator,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "WizdroidVLSceneGenerator": "🧙 VL Video Scene Generator",
}
