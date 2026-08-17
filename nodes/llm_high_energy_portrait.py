"""Wizdroid Tools - High-Energy Portrait node.

Takes slot inputs and formats the Universal High-Energy Portrait Template
via Ollama (AI mode) or a mechanical fill (template mode).
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Tuple

from lib.constants import DEFAULT_OLLAMA_URL
from lib.ollama_client import collect_models, generate_text
from lib.portrait_prompts import (
    DROPDOWN_FIELDS,
    TEXT_FIELDS,
    ai_fallback_prompt,
    build_system_prompt,
    build_template_prompt,
    build_user_prompt,
    get_dropdown_choices,
    get_variant_choices,
    normalize_variant,
    resolve_all_slots,
    sanitize_prompt,
)

logger = logging.getLogger(__name__)


def _dropdown(field: str, tooltip: str = "") -> tuple:
    """Build a ComfyUI dropdown widget for a portrait slot."""
    choices = get_dropdown_choices(field)
    opts: Dict[str, Any] = {"default": "none"}
    if tooltip:
        opts["tooltip"] = tooltip
    return (choices, opts)


class WizdroidHighEnergyPortrait:
    """Fill the Universal High-Energy Portrait Template from slot inputs.

    - **AI mode** (`use_ai=True`): Ollama formats the template, honoring
      provided slots and inventing only the empty ones.
    - **Template mode** (`use_ai=False`): mechanical fill with JSON defaults
      for missing slots (no network).
    """

    CATEGORY = "🧙 Wizdroid/LLM"
    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("prompt",)
    FUNCTION = "generate"
    OUTPUT_NODE = False
    DESCRIPTION = (
        "Fill the Universal High-Energy Portrait Template from slot inputs. "
        "Ollama formats the prompt (or use template mode for a straight fill)."
    )

    @classmethod
    def INPUT_TYPES(cls) -> Dict[str, Any]:
        models = collect_models(DEFAULT_OLLAMA_URL)
        variants = get_variant_choices()
        return {
            "required": {
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
                        "tooltip": "Select an Ollama model. Refresh the page if you added new models.",
                    },
                ),
                "use_ai": (
                    "BOOLEAN",
                    {
                        "default": True,
                        "tooltip": "ON = Ollama formats the template. OFF = mechanical fill.",
                    },
                ),
                "variant": (
                    variants,
                    {
                        "default": variants[0] if variants else "full",
                        "tooltip": (
                            "full = section headers from the Universal High-Energy "
                            "Portrait Template. compact = one dense paragraph."
                        ),
                    },
                ),
                "seed": (
                    "INT",
                    {
                        "default": 0,
                        "min": 0,
                        "max": 0xFFFFFFFF,
                        "tooltip": (
                            "Controls random/increment dropdowns and Ollama seed. "
                            "Same seed + same choices → same resolve."
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
                        "default": 1024,
                        "min": 64,
                        "max": 4096,
                        "step": 32,
                        "tooltip": (
                            "Output budget for AI mode. Full variant wants ~1024; "
                            "compact can go lower."
                        ),
                    },
                ),
                "spice": (
                    "INT",
                    {
                        "default": 0,
                        "min": 0,
                        "max": 10,
                        "step": 1,
                        "tooltip": "0 = SFW, 10 = explicit NSFW. Ignored when use_ai=False.",
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
                            "0 = photorealistic, 10 = surreal. Ignored when use_ai=False."
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
                            "0 = sparse, 10 = hyper-detailed. Ignored when use_ai=False."
                        ),
                    },
                ),
                "lora_trigger": (
                    "STRING",
                    {
                        "default": "",
                        "multiline": False,
                        "tooltip": "Optional LoRA trigger prepended to the prompt (e.g. <sks>).",
                    },
                ),
                # --- Style / Genre Anchor ---
                "style_genre": _dropdown(
                    "style_genre",
                    "Style / era / genre anchor. Override with style_custom when you want a free-typed phrase.",
                ),
                "style_custom": (
                    "STRING",
                    {
                        "default": "",
                        "multiline": False,
                        "tooltip": (
                            "Free-typed style/era/genre. When non-empty this overrides "
                            "the style_genre dropdown (e.g. cyberpunk neon noir)."
                        ),
                    },
                ),
                "adjective": _dropdown(
                    "adjective",
                    "Opening adjective: a [adjective] [character type]…",
                ),
                "character_type": _dropdown(
                    "character_type",
                    "Subject noun: woman, man, idol, dancer, …",
                ),
                "shot_type": _dropdown(
                    "shot_type",
                    "Shot type for the opening line (medium close-up studio, beauty close-up, …).",
                ),
                # --- Subject & Energy ---
                "gender": _dropdown(
                    "gender",
                    "Drives She/He/They in the template.",
                ),
                "presence": _dropdown(
                    "presence",
                    "strong / intense / magnetic / playful / dangerous.",
                ),
                "energy": _dropdown(
                    "energy",
                    "Overall energy: high-energy, theatrical, confrontational, seductive, powerful.",
                ),
                "facial_features": (
                    "STRING",
                    {
                        "default": "",
                        "multiline": False,
                        "tooltip": "Key facial features or expression (e.g. locked eye contact, sharp cheekbones).",
                    },
                ),
                # --- Outfit & Materials ---
                "clothing": (
                    "STRING",
                    {
                        "default": "",
                        "multiline": False,
                        "tooltip": "Clothing description. Wire a preset fragment here if you want.",
                    },
                ),
                "materials": (
                    "STRING",
                    {
                        "default": "",
                        "multiline": False,
                        "tooltip": "Specific materials — sequins, metallic fabric, leather, satin, vinyl, embroidery.",
                    },
                ),
                "fabric_light": _dropdown(
                    "fabric_light",
                    "How light hits the fabric: heavy specular highlights, soft sheen, sharp reflections.",
                ),
                "silhouette": _dropdown(
                    "silhouette",
                    "structured / dramatic / sharp / flowing.",
                ),
                "cut_details": (
                    "STRING",
                    {
                        "default": "",
                        "multiline": False,
                        "tooltip": "Neckline, shoulder details, cut.",
                    },
                ),
                # --- Accessories / hair / makeup ---
                "accessories": (
                    "STRING",
                    {
                        "default": "",
                        "multiline": False,
                        "tooltip": "Jewelry or key accessories that match the genre. Wire preset jewelry/accessories here.",
                    },
                ),
                "hair": (
                    "STRING",
                    {
                        "default": "",
                        "multiline": False,
                        "tooltip": "Volume, texture, styling — voluminous, slicked, wild, sculpted.",
                    },
                ),
                "makeup": (
                    "STRING",
                    {
                        "default": "",
                        "multiline": False,
                        "tooltip": "Makeup or grooming that fits the genre. Wire a makeup preset here.",
                    },
                ),
                # --- Pose & Framing ---
                "pose_energy": _dropdown(
                    "pose_energy",
                    "confident / theatrical / intense / dynamic.",
                ),
                "pose_angle": _dropdown(
                    "pose_angle",
                    "front-facing / three-quarter / slight angle.",
                ),
                "body_language": (
                    "STRING",
                    {
                        "default": "",
                        "multiline": False,
                        "tooltip": "Hand placement or body language.",
                    },
                ),
                # --- Lighting & Atmosphere ---
                "lighting_type": _dropdown(
                    "lighting_type",
                    "studio / cinematic.",
                ),
                "fill": _dropdown(
                    "fill",
                    "soft / minimal fill.",
                ),
                "colors": (
                    "STRING",
                    {
                        "default": "",
                        "multiline": False,
                        "tooltip": "Color grade — e.g. electric blues and magenta, rich and saturated.",
                    },
                ),
                "background": (
                    "STRING",
                    {
                        "default": "",
                        "multiline": False,
                        "tooltip": "Background treatment — dark / toned / atmospheric color.",
                    },
                ),
                # --- Technical ---
                "film_stock": _dropdown(
                    "film_stock",
                    "Film stock or photographic style reference.",
                ),
                "extra_instructions": (
                    "STRING",
                    {
                        "default": "",
                        "multiline": True,
                        "tooltip": (
                            "Optional extra direction. In AI mode this refines atmosphere "
                            "without erasing explicit slots."
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
        variant: str = "full",
        seed: int = 0,
        temperature: float = 0.7,
        max_tokens: int = 1024,
        spice: int = 0,
        fantasy: int = 0,
        detail: int = 5,
        lora_trigger: str = "",
        style_genre: str = "none",
        style_custom: str = "",
        adjective: str = "none",
        character_type: str = "none",
        shot_type: str = "none",
        gender: str = "none",
        presence: str = "none",
        energy: str = "none",
        facial_features: str = "",
        clothing: str = "",
        materials: str = "",
        fabric_light: str = "none",
        silhouette: str = "none",
        cut_details: str = "",
        accessories: str = "",
        hair: str = "",
        makeup: str = "",
        pose_energy: str = "none",
        pose_angle: str = "none",
        body_language: str = "",
        lighting_type: str = "none",
        fill: str = "none",
        colors: str = "",
        background: str = "",
        film_stock: str = "none",
        extra_instructions: str = "",
    ) -> Tuple[str]:
        """Resolve slots and emit a high-energy portrait prompt."""
        seed = int(seed) & 0xFFFFFFFF
        spice = max(0, min(10, int(spice)))
        fantasy = max(0, min(10, int(fantasy)))
        detail = max(0, min(10, int(detail)))
        max_tokens = max(64, min(4096, int(max_tokens)))
        variant = normalize_variant(variant)

        selections = {
            "gender": gender,
            "adjective": adjective,
            "character_type": character_type,
            "style_genre": style_genre,
            "shot_type": shot_type,
            "presence": presence,
            "energy": energy,
            "fabric_light": fabric_light,
            "silhouette": silhouette,
            "pose_energy": pose_energy,
            "pose_angle": pose_angle,
            "lighting_type": lighting_type,
            "fill": fill,
            "film_stock": film_stock,
        }
        selections = {k: selections[k] for k in DROPDOWN_FIELDS if k in selections}

        extras = {
            "style_custom": style_custom,
            "facial_features": facial_features,
            "clothing": clothing,
            "materials": materials,
            "cut_details": cut_details,
            "accessories": accessories,
            "hair": hair,
            "makeup": makeup,
            "body_language": body_language,
            "colors": colors,
            "background": background,
            "extra_instructions": extra_instructions,
            "lora_trigger": lora_trigger,
        }
        extras = {k: extras[k] for k in TEXT_FIELDS if k in extras}

        resolved = resolve_all_slots(selections, seed=seed, extras=extras)
        trigger = (lora_trigger or "").strip()

        if not use_ai:
            logger.debug(
                "Portrait template mode: variant=%s seed=%d fields=%d",
                variant,
                seed,
                len(resolved),
            )
            return (build_template_prompt(resolved, variant=variant),)

        system_prompt = build_system_prompt(
            resolved=resolved,
            variant=variant,
            max_tokens=max_tokens,
            spice=spice,
            fantasy=fantasy,
            detail=detail,
        )
        user_prompt = build_user_prompt(resolved, variant=variant)

        logger.debug(
            "Portrait AI mode: model=%s variant=%s seed=%d spice=%d fantasy=%d "
            "detail=%d temp=%.2f tokens=%d fields=%d",
            ollama_model,
            variant,
            seed,
            spice,
            fantasy,
            detail,
            temperature,
            max_tokens,
            len(resolved),
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
                "Ollama high-energy portrait failed (%s); using template fallback",
                response,
            )
            return (ai_fallback_prompt(resolved, variant=variant),)

        result = sanitize_prompt(response, lora_trigger=trigger)
        if not result:
            logger.warning("Empty AI portrait prompt; using template fallback")
            return (ai_fallback_prompt(resolved, variant=variant),)

        return (result,)


NODE_CLASS_MAPPINGS = {
    "WizdroidHighEnergyPortrait": WizdroidHighEnergyPortrait,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "WizdroidHighEnergyPortrait": "🧙 High-Energy Portrait",
}
