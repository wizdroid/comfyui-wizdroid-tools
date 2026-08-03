"""Character prompt assembly — choices and templates from data/character/.

Files:
  data/character/choices.json  — dropdown concrete values per field
  data/character/system.json   — system_prompt_template, user_prompt_template

Spice / fantasy / detail guidance is reused from data/prompts/*.json via
lib.prompts (same levels as the LLM Prompt Generator).
"""

from __future__ import annotations

import json
import logging
import random
from typing import Any, Dict, List, Optional, Sequence

from lib.json_data import load_data_json
from lib.prompts import get_detail_prompts, get_fantasy_prompts, get_spice_prompts

logger = logging.getLogger(__name__)

# Special dropdown tokens (prepended at INPUT_TYPES time; not stored in JSON)
SPECIAL_OPTIONS: tuple[str, ...] = ("none", "random", "increment")
_SPECIAL_SET = frozenset(SPECIAL_OPTIONS)

# Stable field index order for seed offsets (dropdowns only)
DROPDOWN_FIELDS: tuple[str, ...] = (
    "gender",
    "age_group",
    "body_type",
    "body_shape",
    "height",
    "skin_tone",
    "hair_color",
    "hair_style",
    "eye_color",
    "face_shape",
    "facial_hair",
    "expression",
    "camera_azimuth",
    "camera_elevation",
    "camera_distance",
    "pose_position",
    "pose_orientation",
    "pose_style",
    "outfit_style",
    "background_setting",
    "media_type",
    "media_style",
)

FIELD_INDEX: Dict[str, int] = {name: i for i, name in enumerate(DROPDOWN_FIELDS)}

# Free-text fields included in AI character JSON when non-empty
EXTRA_TEXT_FIELDS: tuple[str, ...] = (
    "extra_face",
    "extra_hair",
    "extra_jewellery",
    "lora_trigger",
    "extra_outfit",
    "extra_background",
    "extra_media",
    "custom_input",
)

_FALLBACK_CHOICES: Dict[str, List[str]] = {
    "gender": ["male", "female"],
    "age_group": ["young adult", "adult", "middle-aged", "senior"],
    "body_type": ["slim", "average", "athletic", "muscular", "overweight"],
    "body_shape": ["pear", "apple", "hourglass", "rectangle", "inverted triangle"],
    "height": ["short", "average", "tall"],
    "skin_tone": ["fair", "light", "medium", "tan", "dark"],
    "hair_color": ["black", "brown", "blonde", "red", "auburn"],
    "hair_style": ["short", "medium", "long", "curly", "straight", "wavy"],
    "eye_color": ["brown", "blue", "green", "hazel", "gray", "amber"],
    "face_shape": ["round", "oval", "square", "heart-shaped", "diamond-shaped"],
    "facial_hair": ["clean-shaven", "mustache", "beard", "goatee", "stubble"],
    "expression": ["happy", "sad", "angry", "surprised", "neutral", "thoughtful"],
    "camera_azimuth": ["front view", "right side view", "back view", "left side view"],
    "camera_elevation": ["low-angle shot", "eye-level shot", "elevated shot", "high-angle shot"],
    "camera_distance": ["close-up", "medium shot", "wide shot"],
    "pose_position": ["standing", "sitting", "walking", "running"],
    "pose_orientation": ["front", "back", "side", "three-quarter"],
    "pose_style": ["casual", "formal", "athletic", "relaxed", "dynamic"],
    "outfit_style": [
        "casual",
        "formal",
        "athletic",
        "streetwear",
        "elegant",
        "lingerie",
        "bikini",
        "nude",
        "fantasy",
        "sci-fi",
    ],
    "background_setting": ["indoor", "outdoor", "urban", "studio"],
    "media_type": ["photography", "illustration", "digital art", "painting"],
    "media_style": ["realistic", "hyperrealistic", "anime", "photorealistic"],
}

_FALLBACK_SYSTEM: Dict[str, str] = {
    "system_prompt_template": (
        "You are a prompt writer for AI image generators. Given a JSON description "
        "of a character, write a single-paragraph image prompt. Include all specified "
        "attributes. Do NOT add attributes not in the JSON. Output only the prompt "
        "text — no markdown, no explanations. Max {max_tokens} words.\n\n"
        "## CONTENT RULES\n"
        "{spice_guidance}\n\n{fantasy_guidance}\n\n{detail_guidance}\n\n"
        "Character JSON:\n{character_json}"
    ),
    "user_prompt_template": (
        "Generate a detailed image prompt for this character description in JSON. "
        "Output just the prompt text:\n{character_json}"
    ),
}

_FALLBACK_LEVEL = "Use a neutral, moderate style."
_CUSTOM_INPUT_MAX_TEMPLATE = 500


def _load_choices() -> Dict[str, List[str]]:
    data = load_data_json("character", "choices.json", default=None)
    if not isinstance(data, dict) or not data:
        return {k: list(v) for k, v in _FALLBACK_CHOICES.items()}
    out: Dict[str, List[str]] = {}
    for key, val in data.items():
        if isinstance(val, list) and val:
            out[str(key)] = [str(x) for x in val]
    return out or {k: list(v) for k, v in _FALLBACK_CHOICES.items()}


def _load_system() -> Dict[str, str]:
    data = load_data_json("character", "system.json", default=None)
    if not isinstance(data, dict):
        return dict(_FALLBACK_SYSTEM)
    merged = dict(_FALLBACK_SYSTEM)
    for k, v in data.items():
        if v is not None:
            merged[str(k)] = str(v)
    return merged


def get_concrete_choices(field: str) -> List[str]:
    """Concrete values for a field (excludes random/none/increment)."""
    choices = _load_choices()
    raw = choices.get(field) or _FALLBACK_CHOICES.get(field) or []
    return [c for c in raw if c not in _SPECIAL_SET]


def get_dropdown_choices(field: str) -> List[str]:
    """Dropdown list: none, random, increment + concrete values."""
    concrete = get_concrete_choices(field)
    return list(SPECIAL_OPTIONS) + concrete


def get_all_dropdown_choices() -> Dict[str, List[str]]:
    """Map every known dropdown field to its full choice list."""
    return {field: get_dropdown_choices(field) for field in DROPDOWN_FIELDS}


def resolve_selection(
    value: str,
    choices: Sequence[str],
    seed: int,
    field_index: int,
) -> Optional[str]:
    """Resolve a dropdown value to a concrete string, or None to omit.

    - concrete value → returned as-is
    - "none" → None (omit attribute)
    - "random" → uniform pick from concrete choices via Random(seed + field_index)
    - "increment" → (seed + field_index) % len(concrete)
    """
    raw = (value or "").strip()
    if not raw or raw == "none":
        return None

    concrete = [c for c in choices if c not in _SPECIAL_SET]
    if not concrete:
        concrete = [c for c in (value,) if c not in _SPECIAL_SET]
    if not concrete:
        return None

    seed = int(seed) & 0xFFFFFFFF
    field_seed = seed + int(field_index)

    if raw == "random":
        rng = random.Random(field_seed)
        return rng.choice(concrete)

    if raw == "increment":
        return concrete[field_seed % len(concrete)]

    # Concrete selection (or custom string from edited JSON / wiring)
    return raw


def resolve_all_selections(
    selections: Dict[str, str],
    seed: int,
    extras: Optional[Dict[str, str]] = None,
) -> Dict[str, str]:
    """Resolve all dropdowns + non-empty extras into a flat character dict.

    Keys with "none"/empty are excluded. Seed is masked to 32-bit.
    """
    seed = int(seed) & 0xFFFFFFFF
    choices_map = _load_choices()
    resolved: Dict[str, str] = {}

    for field in DROPDOWN_FIELDS:
        concrete = choices_map.get(field) or _FALLBACK_CHOICES.get(field) or []
        value = selections.get(field, "none")
        result = resolve_selection(
            value=value,
            choices=concrete,
            seed=seed,
            field_index=FIELD_INDEX.get(field, 0),
        )
        if result is not None:
            resolved[field] = result

    if extras:
        for key, val in extras.items():
            text = (val or "").strip()
            if text:
                resolved[key] = text

    return resolved


def build_template_prompt(resolved: Dict[str, Any]) -> str:
    """Build a plain-English prompt from resolved attributes (template mode)."""
    r = resolved or {}
    parts: List[str] = []

    def _get(key: str) -> str:
        v = r.get(key)
        return str(v).strip() if v is not None and str(v).strip() else ""

    gender = _get("gender")
    if gender:
        parts.append(gender)

    age_group = _get("age_group")
    if age_group:
        parts.append(age_group)

    body_type = _get("body_type")
    if body_type:
        parts.append(f"{body_type} body type")

    body_shape = _get("body_shape")
    if body_shape:
        parts.append(f"{body_shape} body shape")

    height = _get("height")
    if height:
        parts.append(f"{height} height")

    skin_tone = _get("skin_tone")
    if skin_tone:
        parts.append(f"{skin_tone} skin")

    # hair: [color] [style] hair [extra_hair]
    hair_color = _get("hair_color")
    hair_style = _get("hair_style")
    extra_hair = _get("extra_hair")
    hair_bits = [b for b in (hair_color, hair_style) if b]
    if hair_bits:
        hair_str = f"{' '.join(hair_bits)} hair"
        if extra_hair:
            hair_str = f"{hair_str} {extra_hair}"
        parts.append(hair_str)
    elif extra_hair:
        parts.append(extra_hair)

    eye_color = _get("eye_color")
    if eye_color:
        parts.append(f"{eye_color} eyes")

    face_shape = _get("face_shape")
    extra_face = _get("extra_face")
    if face_shape:
        face_str = f"{face_shape} face"
        if extra_face:
            face_str = f"{face_str} {extra_face}"
        parts.append(face_str)
    elif extra_face:
        parts.append(extra_face)

    facial_hair = _get("facial_hair")
    if facial_hair:
        parts.append(facial_hair)

    expression = _get("expression")
    if expression:
        parts.append(f"{expression} expression")

    # camera: distance azimuth elevation (see template example in requirements)
    cam_bits = [
        b
        for b in (
            _get("camera_distance"),
            _get("camera_azimuth"),
            _get("camera_elevation"),
        )
        if b
    ]
    if cam_bits:
        parts.append(" ".join(cam_bits))

    # pose: [style] [position] pose, [orientation] view
    pose_style = _get("pose_style")
    pose_position = _get("pose_position")
    pose_bits = [b for b in (pose_style, pose_position) if b]
    if pose_bits:
        parts.append(f"{' '.join(pose_bits)} pose")

    pose_orientation = _get("pose_orientation")
    if pose_orientation:
        parts.append(f"{pose_orientation} view")

    outfit_style = _get("outfit_style")
    extra_outfit = _get("extra_outfit")
    if outfit_style:
        outfit_str = f"wearing {outfit_style} outfit"
        if extra_outfit:
            outfit_str = f"{outfit_str} {extra_outfit}"
        parts.append(outfit_str)
    elif extra_outfit:
        parts.append(f"wearing {extra_outfit}")

    background_setting = _get("background_setting")
    extra_background = _get("extra_background")
    if background_setting:
        bg_str = f"{background_setting} background"
        if extra_background:
            bg_str = f"{bg_str} {extra_background}"
        parts.append(bg_str)
    elif extra_background:
        parts.append(extra_background)

    media_type = _get("media_type")
    if media_type:
        parts.append(media_type)

    media_style = _get("media_style")
    extra_media = _get("extra_media")
    if media_style:
        media_str = f"{media_style} style"
        if extra_media:
            media_str = f"{media_str} {extra_media}"
        parts.append(media_str)
    elif extra_media:
        parts.append(extra_media)

    custom_input = _get("custom_input")
    if custom_input and len(custom_input) > _CUSTOM_INPUT_MAX_TEMPLATE:
        custom_input = custom_input[:_CUSTOM_INPUT_MAX_TEMPLATE] + "…"

    lora_trigger = _get("lora_trigger")
    # jewellery is only in AI JSON / free text; append if present in template mode
    extra_jewellery = _get("extra_jewellery")
    if extra_jewellery:
        parts.append(extra_jewellery)

    if not parts and not custom_input:
        text = "A character."
    else:
        text = ", ".join(parts)
        if custom_input:
            text = f"{text}, {custom_input}" if text else custom_input
        if text and not text.endswith("."):
            text = f"{text}."

    if lora_trigger:
        text = f"{lora_trigger}, {text}" if text else lora_trigger

    # Normalize accidental double commas / spaces
    while ",," in text:
        text = text.replace(",,", ",")
    text = text.replace(" ,", ",").strip()
    return text


def character_json_string(resolved: Dict[str, Any]) -> str:
    """Serialize resolved character dict as pretty JSON for the LLM."""
    # Stable key order: dropdowns first, then extras that are present
    ordered: Dict[str, Any] = {}
    for field in DROPDOWN_FIELDS:
        if field in resolved:
            ordered[field] = resolved[field]
    for field in EXTRA_TEXT_FIELDS:
        if field in resolved:
            ordered[field] = resolved[field]
    # Any unexpected keys last
    for key, val in resolved.items():
        if key not in ordered:
            ordered[key] = val
    return json.dumps(ordered, ensure_ascii=False, indent=2)


def build_system_prompt(
    resolved: Dict[str, Any],
    max_tokens: int,
    spice: int = 0,
    fantasy: int = 0,
    detail: int = 5,
) -> str:
    """Build the Ollama system prompt with guidance + character JSON."""
    spice = max(0, min(10, int(spice)))
    fantasy = max(0, min(10, int(fantasy)))
    detail = max(0, min(10, int(detail)))
    # Target words roughly derived from token budget (same idea as prompt generator)
    target_words = max(20, int(max_tokens * 0.75))

    spice_map = get_spice_prompts()
    fantasy_map = get_fantasy_prompts()
    detail_map = get_detail_prompts()
    system = _load_system()
    template = system.get("system_prompt_template") or _FALLBACK_SYSTEM["system_prompt_template"]

    char_json = character_json_string(resolved)
    return template.format(
        max_tokens=target_words,
        spice_guidance=spice_map.get(spice, spice_map.get(5, _FALLBACK_LEVEL)),
        fantasy_guidance=fantasy_map.get(fantasy, fantasy_map.get(5, _FALLBACK_LEVEL)),
        detail_guidance=detail_map.get(detail, detail_map.get(5, _FALLBACK_LEVEL)),
        character_json=char_json,
    )


def build_user_prompt(resolved: Dict[str, Any]) -> str:
    """Build the Ollama user prompt wrapping the character JSON."""
    system = _load_system()
    template = system.get("user_prompt_template") or _FALLBACK_SYSTEM["user_prompt_template"]
    return template.format(character_json=character_json_string(resolved))


def sanitize_prompt(text: str, lora_trigger: str = "") -> str:
    """Strip whitespace/fences and optionally prepend LoRA trigger."""
    result = (text or "").strip()
    if not result:
        return ""

    if result.startswith("```"):
        first_newline = result.find("\n")
        if first_newline != -1:
            result = result[first_newline + 1 :]
        if result.endswith("```"):
            result = result[:-3]
        result = result.strip()

    if len(result) >= 2 and result[0] == result[-1] and result[0] in ('"', "'"):
        result = result[1:-1].strip()

    trigger = (lora_trigger or "").strip()
    if trigger:
        # Avoid double-prepending if the model already started with the trigger
        if not result.lower().startswith(trigger.lower()):
            result = f"{trigger}, {result}"

    return result
