"""High-energy portrait template assembly — data/portrait/.

Files:
  data/portrait/choices.json  — dropdown concrete values per field
  data/portrait/system.json   — full/compact templates, system/user prompts, defaults

Spice / fantasy / detail guidance is reused from data/prompts/*.json via
lib.prompts (same levels as the LLM Prompt Generator).
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, List, Optional

from lib.character_prompts import SPECIAL_OPTIONS, resolve_selection
from lib.json_data import load_data_json
from lib.prompts import get_detail_prompts, get_fantasy_prompts, get_spice_prompts

logger = logging.getLogger(__name__)

_SPECIAL_SET = frozenset(SPECIAL_OPTIONS)

DROPDOWN_FIELDS: tuple[str, ...] = (
    "gender",
    "adjective",
    "character_type",
    "style_genre",
    "shot_type",
    "presence",
    "energy",
    "fabric_light",
    "silhouette",
    "pose_energy",
    "pose_angle",
    "lighting_type",
    "fill",
    "film_stock",
)

FIELD_INDEX: Dict[str, int] = {name: i for i, name in enumerate(DROPDOWN_FIELDS)}

TEXT_FIELDS: tuple[str, ...] = (
    "style_custom",
    "facial_features",
    "clothing",
    "materials",
    "cut_details",
    "accessories",
    "hair",
    "makeup",
    "body_language",
    "colors",
    "background",
    "extra_instructions",
    "lora_trigger",
)

VARIANT_CHOICES: tuple[str, ...] = ("full", "compact")

_PRONOUNS: Dict[str, tuple[str, str, str]] = {
    "female": ("She", "she", "her"),
    "woman": ("She", "she", "her"),
    "girl": ("She", "she", "her"),
    "heroine": ("She", "she", "her"),
    "male": ("He", "he", "his"),
    "man": ("He", "he", "his"),
    "boy": ("He", "he", "his"),
    "antihero": ("He", "he", "his"),
    "nonbinary": ("They", "they", "their"),
    "they": ("They", "they", "their"),
    "person": ("They", "they", "their"),
}

_FALLBACK_CHOICES: Dict[str, List[str]] = {
    "gender": ["female", "male", "nonbinary"],
    "adjective": ["striking", "electric", "magnetic", "fierce"],
    "character_type": ["woman", "man", "person"],
    "style_genre": ["cyberpunk neon noir", "studio fashion editorial"],
    "shot_type": ["medium close-up studio", "cinematic portrait"],
    "presence": ["strong", "intense", "magnetic", "playful", "dangerous"],
    "energy": ["high-energy", "theatrical", "confrontational", "seductive", "powerful"],
    "fabric_light": ["heavy specular highlights", "soft sheen", "sharp reflections"],
    "silhouette": ["structured", "dramatic", "sharp", "flowing"],
    "pose_energy": ["confident", "theatrical", "intense", "dynamic"],
    "pose_angle": ["front-facing", "three-quarter", "slight angle"],
    "lighting_type": ["studio", "cinematic"],
    "fill": ["soft", "minimal"],
    "film_stock": ["cinematic 35mm color negative", "Kodak Portra 400"],
}

_FALLBACK_DEFAULTS: Dict[str, str] = {
    "adjective": "striking",
    "character_type": "woman",
    "style_genre": "high-energy cinematic glamour",
    "shot_type": "medium close-up studio",
    "presence": "magnetic",
    "facial_features": "sharp features and locked eye contact",
    "energy": "high-energy",
    "clothing": "a tailored statement outfit",
    "materials": "satin and metallic fabric",
    "fabric_light": "heavy specular highlights",
    "silhouette": "structured",
    "cut_details": "a sharp neckline and defined shoulders",
    "accessories": "Statement jewelry",
    "hair": "voluminous and sculpted",
    "makeup": "Bold eyes, glossy lips, and sharp brows",
    "pose_energy": "confident",
    "pose_angle": "three-quarter",
    "body_language": "hands placed with intent",
    "lighting_type": "cinematic",
    "fill": "soft",
    "colors": "rich and saturated",
    "background": "dark and atmospheric",
    "film_stock": "cinematic 35mm color negative",
}

_FALLBACK_FULL = (
    "[Style / Genre Anchor]\n"
    "A {adjective} {character_type} in the {style_genre} aesthetic, "
    "captured in a {shot_type} portrait.\n\n"
    "Subject & Energy\n"
    "{pronoun_cap} has a {presence} presence, with {facial_features}. "
    "The overall energy is {energy}.\n\n"
    "Outfit & Materials\n"
    "{pronoun_cap} wears {clothing} made of {materials}. "
    "The fabric has {fabric_light}. The silhouette is {silhouette}, with {cut_details}.\n\n"
    "Accessories\n"
    "{accessories}, catching light and adding visual weight.\n\n"
    "Hair\n"
    "Hair is {hair}, framed to keep the face dominant.\n\n"
    "Makeup / Styling\n"
    "{makeup}.\n\n"
    "Pose & Framing\n"
    "Pose is {pose_energy}. {pose_angle_cap}, upper body, with {body_language}. "
    "The subject fills the frame with strong presence.\n\n"
    "Lighting & Atmosphere\n"
    "Dramatic {lighting_type} lighting: strong key light creating bright specular "
    "highlights on skin and materials, {fill} fill, and a glowing rim light that "
    "separates the subject from the background. Colors are {colors}. "
    "Background is {background}.\n\n"
    "Technical Look\n"
    "Shot with {film_stock}, visible fine film grain, gentle glow around highlights, "
    "shallow depth of field. High visual energy, rich color, cinematic contrast.\n\n"
    "Quality Line\n"
    "Photorealistic, highly detailed textures and light reflections, "
    "{style_genre} glamour/energy, no modern digital sharpness, no flat lighting."
)

_FALLBACK_COMPACT = (
    "A {adjective} {character_type} in the {style_genre} aesthetic, "
    "captured in a {shot_type} portrait. {pronoun_cap} has a {presence} presence, "
    "with {facial_features}. The overall energy is {energy}. {pronoun_cap} wears "
    "{clothing} made of {materials}; the fabric has {fabric_light}. The silhouette "
    "is {silhouette}, with {cut_details}. {accessories}, catching light. Hair is "
    "{hair}. {makeup}. Pose is {pose_energy}; {pose_angle}, upper body, with "
    "{body_language}. Dramatic {lighting_type} lighting, {fill} fill, glowing rim "
    "light. Colors are {colors}. Background is {background}. Shot with {film_stock}, "
    "fine film grain, gentle highlight glow, shallow depth of field. Photorealistic, "
    "{style_genre} glamour/energy, no modern digital sharpness, no flat lighting."
)

_FALLBACK_SYSTEM: Dict[str, str] = {
    "system_prompt_template": (
        "You fill a high-energy portrait template.\n"
        "Variant: {variant_instruction}\n"
        "Max about {max_tokens} words.\n"
        "Honor provided slots; invent only missing ones.\n"
        "Skeleton:\n{skeleton}\n\nSlots:\n{slots_json}\n\n"
        "{spice_guidance}\n{fantasy_guidance}\n{detail_guidance}\n"
        "Output only the prompt."
    ),
    "user_prompt_template": (
        "Fill this portrait template. Honor provided slots. "
        "Output only the prompt.\n\nSkeleton:\n{skeleton}\n\nSlots:\n{slots_json}"
    ),
    "variant_full": (
        "Write the FULL template and keep the section headers."
    ),
    "variant_compact": (
        "Write the COMPACT template as one dense paragraph with no headers."
    ),
}

_FALLBACK_LEVEL = "Use a neutral, moderate style."
_AI_FALLBACK_SUFFIX = " # [AI unavailable — template fallback]"


def _load_choices() -> Dict[str, List[str]]:
    data = load_data_json("portrait", "choices.json", default=None)
    if not isinstance(data, dict) or not data:
        return {k: list(v) for k, v in _FALLBACK_CHOICES.items()}
    out: Dict[str, List[str]] = {}
    for key, val in data.items():
        if isinstance(val, list) and val:
            out[str(key)] = [str(x) for x in val]
    return out or {k: list(v) for k, v in _FALLBACK_CHOICES.items()}


def _load_system() -> Dict[str, Any]:
    data = load_data_json("portrait", "system.json", default=None)
    if not isinstance(data, dict):
        return {
            **_FALLBACK_SYSTEM,
            "full_template": _FALLBACK_FULL,
            "compact_template": _FALLBACK_COMPACT,
            "defaults": dict(_FALLBACK_DEFAULTS),
            "strip_prefixes": [],
        }
    merged: Dict[str, Any] = {
        **_FALLBACK_SYSTEM,
        "full_template": _FALLBACK_FULL,
        "compact_template": _FALLBACK_COMPACT,
        "defaults": dict(_FALLBACK_DEFAULTS),
        "strip_prefixes": [],
    }
    for k, v in data.items():
        if v is None:
            continue
        if k == "defaults" and isinstance(v, dict):
            defaults = dict(_FALLBACK_DEFAULTS)
            defaults.update({str(dk): str(dv) for dk, dv in v.items() if dv is not None})
            merged["defaults"] = defaults
            continue
        if k == "strip_prefixes" and isinstance(v, list):
            merged["strip_prefixes"] = [str(x) for x in v]
            continue
        merged[str(k)] = v
    return merged


def get_concrete_choices(field: str) -> List[str]:
    """Concrete values for a field (excludes random/none/increment)."""
    choices = _load_choices()
    raw = choices.get(field) or _FALLBACK_CHOICES.get(field) or []
    return [c for c in raw if c not in _SPECIAL_SET]


def get_dropdown_choices(field: str) -> List[str]:
    """Dropdown list: none, random, increment + concrete values."""
    return list(SPECIAL_OPTIONS) + get_concrete_choices(field)


def get_variant_choices() -> List[str]:
    return list(VARIANT_CHOICES)


def normalize_variant(value: str) -> str:
    raw = (value or "").strip().lower()
    if raw in VARIANT_CHOICES:
        return raw
    if raw.startswith("compact") or raw.startswith("short"):
        return "compact"
    return "full"


def resolve_all_slots(
    selections: Dict[str, str],
    seed: int,
    extras: Optional[Dict[str, str]] = None,
) -> Dict[str, str]:
    """Resolve dropdowns + non-empty text fields. Empty / none are omitted."""
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

    custom_style = (resolved.pop("style_custom", "") or "").strip()
    if custom_style:
        resolved["style_genre"] = custom_style

    return resolved


def _pronouns_for(resolved: Dict[str, str]) -> tuple[str, str, str]:
    gender = (resolved.get("gender") or "").strip().lower()
    if gender in _PRONOUNS:
        return _PRONOUNS[gender]
    character_type = (resolved.get("character_type") or "").strip().lower()
    if character_type in _PRONOUNS:
        return _PRONOUNS[character_type]
    return ("She", "she", "her")


def _sentence_case(text: str) -> str:
    raw = (text or "").strip()
    if not raw:
        return raw
    return raw[0].upper() + raw[1:]


def _polish_makeup(text: str) -> str:
    """Ensure the makeup line reads as a sentence in template mode."""
    raw = (text or "").strip()
    if not raw:
        return raw
    raw = raw.rstrip(".")
    if raw[0].islower() and not raw.startswith(("bold", "sharp", "clean", "soft", "glossy")):
        raw = _sentence_case(raw)
    # Bare fragments like "bold eyes, glossy lips" stay as-is (template supplies period)
    return raw


def _fill_values(resolved: Dict[str, str], *, use_defaults: bool) -> Dict[str, str]:
    """Build the named mapping used by the template strings."""
    system = _load_system()
    defaults = system.get("defaults") if isinstance(system.get("defaults"), dict) else {}
    defaults = {str(k): str(v) for k, v in defaults.items()}

    values: Dict[str, str] = {}
    if use_defaults:
        values.update(defaults)

    for key, val in resolved.items():
        text = (val or "").strip()
        if text:
            values[key] = text

    if use_defaults:
        for key, fallback in _FALLBACK_DEFAULTS.items():
            values.setdefault(key, fallback)

    # Prefer pronouns from the *resolved* identity, not invented defaults,
    # so a user-set gender wins even when character_type default is "woman".
    identity = resolved if (resolved.get("gender") or resolved.get("character_type")) else values
    pronoun_cap, pronoun, possessive = _pronouns_for(identity)
    values["pronoun_cap"] = pronoun_cap
    values["pronoun"] = pronoun
    values["possessive"] = possessive

    pose_angle = (values.get("pose_angle") or "").strip()
    values["pose_angle"] = pose_angle
    values["pose_angle_cap"] = _sentence_case(pose_angle) if pose_angle else pose_angle

    makeup = (values.get("makeup") or "").strip()
    if makeup:
        values["makeup"] = _polish_makeup(makeup)

    return values


def get_skeleton(variant: str) -> str:
    """Return the Python-format skeleton for a variant."""
    system = _load_system()
    variant = normalize_variant(variant)
    if variant == "compact":
        return str(system.get("compact_template") or _FALLBACK_COMPACT)
    return str(system.get("full_template") or _FALLBACK_FULL)


def skeleton_for_llm(variant: str) -> str:
    """Skeleton with [bracket] slots so the LLM sees the original template shape."""
    raw = get_skeleton(variant)
    return re.sub(r"\{([a-z_]+)\}", r"[\1]", raw)


def build_template_prompt(resolved: Dict[str, str], variant: str = "full") -> str:
    """Fill the portrait template mechanically (no LLM). Missing slots use defaults."""
    variant = normalize_variant(variant)
    values = _fill_values(resolved, use_defaults=True)
    skeleton = get_skeleton(variant)

    class _Safe(dict):
        def __missing__(self, key: str) -> str:
            return ""

    text = skeleton.format_map(_Safe(values))
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    text = re.sub(r" {2,}", " ", text)
    text = re.sub(r" \.", ".", text)
    # Collapse "word.." from makeup already ending with a period + template period
    text = re.sub(r"\.\.", ".", text)

    extra = (resolved.get("extra_instructions") or "").strip()
    if extra:
        text = f"{text.rstrip()}\n\n{extra}" if variant == "full" else f"{text.rstrip()} {extra}"

    trigger = (resolved.get("lora_trigger") or "").strip()
    if trigger:
        text = f"{trigger}, {text}" if text else trigger

    return text


def slots_json_string(resolved: Dict[str, str]) -> str:
    """Serialize provided (non-default) slots for the LLM."""
    ordered: Dict[str, Any] = {}
    for field in DROPDOWN_FIELDS:
        if field in resolved:
            ordered[field] = resolved[field]
    for field in TEXT_FIELDS:
        if field == "style_custom":
            continue
        if field in resolved:
            ordered[field] = resolved[field]
    for key, val in resolved.items():
        if key not in ordered:
            ordered[key] = val

    # Explicitly list unfilled template slots so the model knows what to invent
    provided = set(ordered)
    unfilled = [
        slot
        for slot in (
            "adjective",
            "character_type",
            "style_genre",
            "shot_type",
            "gender",
            "presence",
            "facial_features",
            "energy",
            "clothing",
            "materials",
            "fabric_light",
            "silhouette",
            "cut_details",
            "accessories",
            "hair",
            "makeup",
            "pose_energy",
            "pose_angle",
            "body_language",
            "lighting_type",
            "fill",
            "colors",
            "background",
            "film_stock",
        )
        if slot not in provided
    ]
    payload = {
        "provided": ordered,
        "unfilled": unfilled,
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


def _format_known(template: str, **kwargs: Any) -> str:
    """str.format that leaves unknown {placeholders} untouched."""

    class _Safe(dict):
        def __missing__(self, key: str) -> str:
            return "{" + key + "}"

    return str(template).format_map(_Safe(kwargs))


def build_system_prompt(
    resolved: Dict[str, str],
    variant: str = "full",
    max_tokens: int = 1024,
    spice: int = 0,
    fantasy: int = 0,
    detail: int = 5,
) -> str:
    """Build the Ollama system prompt with guidance + slots + skeleton."""
    spice = max(0, min(10, int(spice)))
    fantasy = max(0, min(10, int(fantasy)))
    detail = max(0, min(10, int(detail)))
    target_words = max(20, int(max_tokens * 0.75))
    variant = normalize_variant(variant)

    spice_map = get_spice_prompts()
    fantasy_map = get_fantasy_prompts()
    detail_map = get_detail_prompts()
    system = _load_system()
    template = (
        system.get("system_prompt_template")
        or _FALLBACK_SYSTEM["system_prompt_template"]
    )
    if variant == "compact":
        variant_instruction = str(
            system.get("variant_compact") or _FALLBACK_SYSTEM["variant_compact"]
        )
    else:
        variant_instruction = str(
            system.get("variant_full") or _FALLBACK_SYSTEM["variant_full"]
        )

    return _format_known(
        str(template),
        max_tokens=target_words,
        variant_instruction=variant_instruction,
        skeleton=skeleton_for_llm(variant),
        slots_json=slots_json_string(resolved),
        spice_guidance=spice_map.get(spice, spice_map.get(5, _FALLBACK_LEVEL)),
        fantasy_guidance=fantasy_map.get(fantasy, fantasy_map.get(5, _FALLBACK_LEVEL)),
        detail_guidance=detail_map.get(detail, detail_map.get(5, _FALLBACK_LEVEL)),
    )


def build_user_prompt(resolved: Dict[str, str], variant: str = "full") -> str:
    """Build the Ollama user prompt wrapping slots + skeleton."""
    variant = normalize_variant(variant)
    system = _load_system()
    template = (
        system.get("user_prompt_template")
        or _FALLBACK_SYSTEM["user_prompt_template"]
    )
    return _format_known(
        str(template),
        skeleton=skeleton_for_llm(variant),
        slots_json=slots_json_string(resolved),
    )


def sanitize_prompt(text: str, lora_trigger: str = "") -> str:
    """Strip fences/labels and optionally prepend LoRA trigger."""
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

    system = _load_system()
    prefixes = system.get("strip_prefixes") or []
    lower = result.lower()
    for prefix in prefixes:
        p = str(prefix).lower()
        if lower.startswith(p):
            result = result[len(prefix) :].strip()
            break

    if len(result) >= 2 and result[0] == result[-1] and result[0] in ('"', "'"):
        result = result[1:-1].strip()

    trigger = (lora_trigger or "").strip()
    if trigger and not result.lower().startswith(trigger.lower()):
        result = f"{trigger}, {result}"

    return result


def ai_fallback_prompt(resolved: Dict[str, str], variant: str = "full") -> str:
    """Template fill plus the shared AI-unavailable suffix."""
    filled = build_template_prompt(resolved, variant=variant).rstrip()
    if not filled.endswith(_AI_FALLBACK_SUFFIX.strip()):
        return f"{filled}{_AI_FALLBACK_SUFFIX}"
    return filled
