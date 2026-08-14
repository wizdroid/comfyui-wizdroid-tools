"""Wizdroid Tools — LLM Video Scene Generator (text → scene + dialogue).

Text-only scene package for AI video / keyframe image pipelines.
Category: 🧙 Wizdroid/LLM
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Tuple

from lib.constants import DEFAULT_OLLAMA_URL
from lib.ollama_client import collect_models, generate_text
from lib.scene_prompts import (
    build_text_system_prompt,
    build_text_user_prompt,
    clamp_duration,
    get_mood_choices,
    get_style_choices,
    get_video_model_choices,
    parse_scene_response,
)

logger = logging.getLogger(__name__)


class WizdroidLLMSceneGenerator:
    """Generate a video scene package from text (no source image).

    Outputs a motion/scene prompt, optional dialogue, and a still
    ``image_prompt`` suitable as a keyframe for T2I → I2V workflows.
    """

    CATEGORY = "🧙 Wizdroid/LLM"
    RETURN_TYPES = ("STRING", "STRING", "STRING", "STRING")
    RETURN_NAMES = ("scene_prompt", "dialogue", "image_prompt", "raw")
    FUNCTION = "generate"
    OUTPUT_NODE = False
    DESCRIPTION = (
        "Text-to-scene for video: expand a concept into a timed scene prompt, "
        "dialogue, and a keyframe image prompt (mood + style + duration)."
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
                        "tooltip": "Text LLM (vision not required). Refresh page for new models.",
                    },
                ),
                "user_prompt": (
                    "STRING",
                    {
                        "default": "",
                        "multiline": True,
                        "tooltip": "Scene idea / story beat for the video clip.",
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
                        "default": 0.75,
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
                        "tooltip": "Optional constraints (cast, location, no dialogue, camera rules, …).",
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
            },
        }

    def generate(
        self,
        video_model: str = "generic",
        ollama_url: str = DEFAULT_OLLAMA_URL,
        ollama_model: str = "",
        user_prompt: str = "",
        duration_seconds: float = 5.0,
        mood: str = "neutral",
        style: str = "cinematic",
        temperature: float = 0.75,
        max_tokens: int = 1024,
        extra_instructions: str = "",
        seed: int = 0,
    ) -> Tuple[str, str, str, str]:
        user_prompt = (user_prompt or "").strip()
        if not user_prompt:
            err = "Error: user_prompt is empty. Describe the scene you want."
            return (err, "", "", err)

        duration_seconds = clamp_duration(duration_seconds)
        max_tokens = max(128, min(4096, int(max_tokens)))
        seed = int(seed) & 0xFFFFFFFF

        system_prompt = build_text_system_prompt(
            duration_seconds=duration_seconds,
            mood=mood,
            style=style,
            video_model=video_model,
        )
        generation_prompt = build_text_user_prompt(
            user_prompt=user_prompt,
            duration_seconds=duration_seconds,
            mood=mood,
            style=style,
            extra_instructions=extra_instructions,
            video_model=video_model,
        )

        logger.debug(
            "LLM scene: video_model=%s model=%s duration=%.1fs mood=%s style=%s tokens=%d",
            video_model,
            ollama_model,
            duration_seconds,
            mood,
            style,
            max_tokens,
        )

        ok, response = generate_text(
            ollama_url=ollama_url,
            model=ollama_model,
            system=system_prompt,
            prompt=generation_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
            seed=seed if seed != 0 else 0,
            timeout=180,
        )

        if not ok:
            logger.error("LLM scene generation failed: %s", response)
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
    "WizdroidLLMSceneGenerator": WizdroidLLMSceneGenerator,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "WizdroidLLMSceneGenerator": "🧙 Video Scene Generator (Text)",
}
