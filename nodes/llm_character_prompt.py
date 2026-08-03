"""Wizdroid Tools - Character Prompt Generator Node.

Build a character via dropdowns & text fields, then generate an image prompt
via Ollama (AI mode) or a plain English template (template mode).
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Tuple

from lib.character_prompts import (
    DROPDOWN_FIELDS,
    build_system_prompt,
    build_template_prompt,
    build_user_prompt,
    get_dropdown_choices,
    resolve_all_selections,
    sanitize_prompt,
)
from lib.constants import DEFAULT_OLLAMA_URL
from lib.ollama_client import collect_models, generate_text

logger = logging.getLogger(__name__)

_AI_FALLBACK_SUFFIX = " # [AI unavailable — template fallback]"


def _dropdown(field: str, tooltip: str = "") -> tuple:
    """Build a ComfyUI dropdown widget for a character field."""
    choices = get_dropdown_choices(field)
    default = "none"
    opts: Dict[str, Any] = {"default": default}
    if tooltip:
        opts["tooltip"] = tooltip
    return (choices, opts)


class WizdroidCharacterPrompt:
    """Compose a character and emit a single image-generation prompt string.

    - **AI mode** (`use_ai=True`): Ollama expands a structured character JSON.
    - **Template mode** (`use_ai=False`): concatenates selections into prose.
    """

    CATEGORY = "🧙 Wizdroid/LLM"
    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("prompt",)
    FUNCTION = "generate"
    OUTPUT_NODE = False
    DESCRIPTION = (
        "Build a character via dropdowns & text fields, then generate an image "
        "prompt via Ollama or a plain template."
    )

    @classmethod
    def INPUT_TYPES(cls) -> Dict[str, Any]:
        models = collect_models(DEFAULT_OLLAMA_URL)
        # Reload choices from data/character/choices.json on each UI query
        return {
            "required": {
                # --- Global controls ---
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
                        "tooltip": "Select an Ollama model. Refresh page to pick up new models.",
                    },
                ),
                "use_ai": (
                    "BOOLEAN",
                    {
                        "default": True,
                        "tooltip": "ON = Ollama-generated prompt. OFF = plain template prompt.",
                    },
                ),
                "seed": (
                    "INT",
                    {
                        "default": 0,
                        "min": 0,
                        "max": 0xFFFFFFFF,
                        "tooltip": (
                            "Controls 'increment' selections. Same seed + same "
                            "choices → same output (deterministic)."
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
                        "tooltip": "LLM temperature (ignored when use_ai=False).",
                    },
                ),
                "max_tokens": (
                    "INT",
                    {
                        "default": 256,
                        "min": 64,
                        "max": 1024,
                        "step": 32,
                        "tooltip": "Maximum output tokens for AI-generated prompt.",
                    },
                ),
                "spice": (
                    "INT",
                    {
                        "default": 0,
                        "min": 0,
                        "max": 10,
                        "step": 1,
                        "tooltip": (
                            "0 = completely SFW, 10 = explicit NSFW. "
                            "Ignored when use_ai=False."
                        ),
                    },
                ),
                "fantasy": (
                    "INT",
                    {
                        "default": 0,
                        "min": 0,
                        "max": 10,
                        "step": 1,
                        "tooltip": (
                            "0 = photorealistic, 10 = pure surreal fantasy. "
                            "Ignored when use_ai=False."
                        ),
                    },
                ),
                "detail": (
                    "INT",
                    {
                        "default": 5,
                        "min": 0,
                        "max": 10,
                        "step": 1,
                        "tooltip": (
                            "0 = minimalistic, 10 = hyper-detailed 8K quality. "
                            "Ignored when use_ai=False."
                        ),
                    },
                ),
                # --- LoRA trigger ---
                "lora_trigger": (
                    "STRING",
                    {
                        "default": "",
                        "multiline": False,
                        "tooltip": (
                            "LoRA trigger word(s) to prepend to the prompt. For the Qwen "
                            "Multiple-Angles LoRA, use '<sks>' (the camera dropdowns will "
                            "then produce the expected '[azimuth] [elevation] [distance]' "
                            "format in the prompt)."
                        ),
                    },
                ),
                # --- Demographics ---
                "gender": _dropdown("gender"),
                "age_group": _dropdown("age_group"),
                "body_type": _dropdown("body_type"),
                "body_shape": _dropdown("body_shape"),
                "height": _dropdown("height"),
                "skin_tone": _dropdown("skin_tone"),
                # --- Head & face ---
                "hair_color": _dropdown("hair_color"),
                "hair_style": _dropdown("hair_style"),
                "eye_color": _dropdown("eye_color"),
                "face_shape": _dropdown("face_shape"),
                "facial_hair": _dropdown("facial_hair"),
                "expression": _dropdown("expression"),
                # --- Free-text additions ---
                "extra_face": (
                    "STRING",
                    {
                        "default": "",
                        "multiline": False,
                        "tooltip": "Additional facial details (scars, freckles, makeup, etc.)",
                    },
                ),
                "extra_hair": (
                    "STRING",
                    {
                        "default": "",
                        "multiline": False,
                        "tooltip": "Additional hair details (bangs, highlights, accessories, etc.)",
                    },
                ),
                "extra_jewellery": (
                    "STRING",
                    {
                        "default": "",
                        "multiline": False,
                        "tooltip": "Additional upper-body jewellery/accessories.",
                    },
                ),
                # --- Camera ---
                "camera_azimuth": _dropdown(
                    "camera_azimuth",
                    "Horizontal camera rotation around the subject. Maps to 0°–315° "
                    "in 45° increments.",
                ),
                "camera_elevation": _dropdown(
                    "camera_elevation",
                    "Vertical camera angle. -30° (looking up) to 60° (looking down).",
                ),
                "camera_distance": _dropdown(
                    "camera_distance",
                    "Camera distance from subject. close-up = details, medium = balanced, "
                    "wide = full context.",
                ),
                # --- Pose ---
                "pose_position": _dropdown("pose_position"),
                "pose_orientation": _dropdown("pose_orientation"),
                "pose_style": _dropdown("pose_style"),
                # --- Outfit ---
                "outfit_style": _dropdown("outfit_style"),
                "extra_outfit": (
                    "STRING",
                    {
                        "default": "",
                        "multiline": False,
                        "tooltip": "Additional outfit details (colors, fabrics, accessories, etc.)",
                    },
                ),
                # --- Background ---
                "background_setting": _dropdown("background_setting"),
                "extra_background": (
                    "STRING",
                    {
                        "default": "",
                        "multiline": False,
                        "tooltip": "Additional background details (time of day, weather, props, etc.)",
                    },
                ),
                # --- Media / art style ---
                "media_type": _dropdown("media_type"),
                "media_style": _dropdown("media_style"),
                "extra_media": (
                    "STRING",
                    {
                        "default": "",
                        "multiline": False,
                        "tooltip": "Additional media/style keywords (artist names, techniques, etc.)",
                    },
                ),
                # --- Freeform override ---
                "custom_input": (
                    "STRING",
                    {
                        "default": "",
                        "multiline": True,
                        "tooltip": (
                            "Custom instruction appended to the prompt. Overrides/refines "
                            "all other selections when non-empty in template mode."
                        ),
                    },
                ),
            },
        }

    def generate(
        self,
        ollama_url: str = DEFAULT_OLLAMA_URL,
        ollama_model: str = "",
        use_ai: bool = True,
        seed: int = 0,
        temperature: float = 0.7,
        max_tokens: int = 256,
        spice: int = 0,
        fantasy: int = 0,
        detail: int = 5,
        gender: str = "random",
        age_group: str = "random",
        body_type: str = "random",
        body_shape: str = "random",
        height: str = "random",
        skin_tone: str = "random",
        hair_color: str = "random",
        hair_style: str = "random",
        eye_color: str = "random",
        face_shape: str = "random",
        facial_hair: str = "random",
        expression: str = "random",
        extra_face: str = "",
        extra_hair: str = "",
        extra_jewellery: str = "",
        lora_trigger: str = "",
        camera_azimuth: str = "random",
        camera_elevation: str = "random",
        camera_distance: str = "random",
        pose_position: str = "random",
        pose_orientation: str = "random",
        pose_style: str = "random",
        outfit_style: str = "random",
        extra_outfit: str = "",
        background_setting: str = "random",
        extra_background: str = "",
        media_type: str = "random",
        media_style: str = "random",
        extra_media: str = "",
        custom_input: str = "",
    ) -> Tuple[str]:
        """Resolve selections and produce a character image prompt."""
        seed = int(seed) & 0xFFFFFFFF
        spice = max(0, min(10, int(spice)))
        fantasy = max(0, min(10, int(fantasy)))
        detail = max(0, min(10, int(detail)))
        max_tokens = max(64, min(1024, int(max_tokens)))

        selections = {
            "gender": gender,
            "age_group": age_group,
            "body_type": body_type,
            "body_shape": body_shape,
            "height": height,
            "skin_tone": skin_tone,
            "hair_color": hair_color,
            "hair_style": hair_style,
            "eye_color": eye_color,
            "face_shape": face_shape,
            "facial_hair": facial_hair,
            "expression": expression,
            "camera_azimuth": camera_azimuth,
            "camera_elevation": camera_elevation,
            "camera_distance": camera_distance,
            "pose_position": pose_position,
            "pose_orientation": pose_orientation,
            "pose_style": pose_style,
            "outfit_style": outfit_style,
            "background_setting": background_setting,
            "media_type": media_type,
            "media_style": media_style,
        }
        # Ensure we only pass known dropdown keys
        selections = {k: selections[k] for k in DROPDOWN_FIELDS if k in selections}

        extras = {
            "extra_face": extra_face,
            "extra_hair": extra_hair,
            "extra_jewellery": extra_jewellery,
            "lora_trigger": lora_trigger,
            "extra_outfit": extra_outfit,
            "extra_background": extra_background,
            "extra_media": extra_media,
            "custom_input": custom_input,
        }

        resolved = resolve_all_selections(selections, seed=seed, extras=extras)
        template_prompt = build_template_prompt(resolved)
        trigger = (lora_trigger or "").strip()

        if not use_ai:
            logger.debug(
                "Character template mode: seed=%d fields=%d",
                seed,
                len(resolved),
            )
            return (template_prompt,)

        # --- AI mode ---
        system_prompt = build_system_prompt(
            resolved=resolved,
            max_tokens=max_tokens,
            spice=spice,
            fantasy=fantasy,
            detail=detail,
        )
        user_prompt = build_user_prompt(resolved)

        logger.debug(
            "Character AI mode: model=%s seed=%d spice=%d fantasy=%d detail=%d temp=%.2f tokens=%d",
            ollama_model,
            seed,
            spice,
            fantasy,
            detail,
            temperature,
            max_tokens,
        )

        ok, response = generate_text(
            ollama_url=ollama_url,
            model=ollama_model,
            system=system_prompt,
            prompt=user_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
            seed=seed if seed != 0 else 0,
            timeout=120,
        )

        if not ok:
            logger.warning(
                "Ollama character prompt failed (%s); using template fallback",
                response,
            )
            fallback = template_prompt.rstrip()
            if not fallback.endswith(_AI_FALLBACK_SUFFIX.strip()):
                # Append warning as a trailing comment fragment (plain text)
                fallback = f"{fallback}{_AI_FALLBACK_SUFFIX}"
            return (fallback,)

        result = sanitize_prompt(response, lora_trigger=trigger)
        if not result:
            logger.warning("Empty AI character prompt; using template fallback")
            return (f"{template_prompt}{_AI_FALLBACK_SUFFIX}",)

        return (result,)


# ---------------------------------------------------------------------------
# Node registration mappings
# ---------------------------------------------------------------------------
NODE_CLASS_MAPPINGS = {
    "WizdroidCharacterPrompt": WizdroidCharacterPrompt,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "WizdroidCharacterPrompt": "🧙 LLM Character Prompt Generator",
}
