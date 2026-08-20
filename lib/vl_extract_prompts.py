"""VL image extract meta-prompts — loaded from data/vl_extract/*.json.

Edit JSON to add or change extraction modes (image prompt, outfit flatlay,
makeup, …). Spice/detail guidance reuses data/prompts/{spice,detail}.json
so NSFW extraction follows the same 0–10 scale as other Wizdroid LLM nodes.

Files:
  data/vl_extract/modes.json   — mode_id -> {label, instruction, …}
  data/vl_extract/system.json  — base system, mode_order, user template
"""

from __future__ import annotations

from typing import Any, Dict, List, Tuple

from lib.json_data import load_data_json
from lib.prompts import get_detail_prompts, get_spice_prompts

_DEFAULT_SYSTEM: Dict[str, Any] = {
    "base_system": (
        "You analyze a source image and extract text for AI image pipelines.\n"
        "Spice:\n{spice_guidance}\nDetail:\n{detail_guidance}"
    ),
    "output_rules": (
        "Output ONLY the extracted text. No markdown fences or commentary.\n"
        "Ground claims in the image. Adult NSFW is allowed when spice is high "
        "and content is present. Never invent sexual content involving minors."
    ),
    "default_mode": "image_prompt",
    "mode_order": [
        "image_prompt",
        "outfit_flatlay",
        "makeup",
        "full_character",
        "custom",
    ],
    "user_prompt_template": (
        "Analyze the attached source image.\n"
        "Mode: {mode_label}\nSpice: {spice}/10 Detail: {detail}/10\n"
        "{mode_header}\n{extra_block}Produce only the extracted text."
    ),
    "extra_block_template": "Additional user direction:\n{extra_instructions}\n\n",
    "strip_prefixes": [
        "extracted text:",
        "image prompt:",
        "prompt:",
        "description:",
        "analysis:",
        "output:",
    ],
}

_DEFAULT_MODES: Dict[str, Dict[str, Any]] = {
    "image_prompt": {
        "label": "Image prompt (full reverse)",
        "instruction": (
            "Mode: Image prompt.\nWrite one Krea 2 natural-language paragraph that would recreate this image."
        ),
        "suggested_temperature": 0.35,
        "suggested_max_tokens": 512,
    },
    "outfit_flatlay": {
        "label": "Outfit / accessories flatlay",
        "instruction": (
            "Mode: Outfit flatlay.\nDescribe clothing and accessories as a product flatlay list."
        ),
        "suggested_temperature": 0.3,
        "suggested_max_tokens": 512,
    },
    "makeup": {
        "label": "Makeup description",
        "instruction": "Mode: Makeup.\nDescribe the visible makeup look in prompt fragments.",
        "suggested_temperature": 0.3,
        "suggested_max_tokens": 384,
    },
    "full_character": {
        "label": "Full character appearance",
        "instruction": "Mode: Full character.\nDescribe the full character appearance from the image.",
        "suggested_temperature": 0.35,
        "suggested_max_tokens": 640,
    },
    "custom": {
        "label": "Custom extraction",
        "instruction": (
            "Mode: Custom.\nFollow the user's custom instruction for extraction."
        ),
        "suggested_temperature": 0.4,
        "suggested_max_tokens": 512,
    },
}

_FALLBACK_LEVEL = {
    0: "Keep content completely safe for work.",
    5: "Allow romantic / alluring description when present.",
    10: "Describe explicit adult content accurately when present in the image.",
}


def _load_system() -> Dict[str, Any]:
    data = load_data_json("vl_extract", "system.json", default=None)
    if not isinstance(data, dict):
        return dict(_DEFAULT_SYSTEM)
    merged = dict(_DEFAULT_SYSTEM)
    merged.update(data)
    return merged


def _normalize_mode_entry(key: str, val: Dict[str, Any]) -> Dict[str, Any] | None:
    instruction = (val.get("instruction") or "").strip()
    if not instruction:
        return None
    try:
        temp = float(val.get("suggested_temperature", 0.35))
    except (TypeError, ValueError):
        temp = 0.35
    try:
        max_tok = int(val.get("suggested_max_tokens", 512))
    except (TypeError, ValueError):
        max_tok = 512
    return {
        "label": str(val.get("label") or key),
        "instruction": instruction,
        "suggested_temperature": temp,
        "suggested_max_tokens": max(64, min(4096, max_tok)),
    }


def _load_modes() -> Dict[str, Dict[str, Any]]:
    data = load_data_json("vl_extract", "modes.json", default=None)
    if not isinstance(data, dict) or not data:
        return {k: dict(v) for k, v in _DEFAULT_MODES.items()}
    out: Dict[str, Dict[str, Any]] = {}
    for key, val in data.items():
        if not isinstance(val, dict):
            continue
        entry = _normalize_mode_entry(str(key), val)
        if entry:
            out[str(key)] = entry
    return out or {k: dict(v) for k, v in _DEFAULT_MODES.items()}


def get_extract_modes() -> Dict[str, Dict[str, Any]]:
    """Return current mode map (reloads when modes.json changes)."""
    return _load_modes()


def get_extract_mode_choices() -> List[str]:
    """Ordered mode ids for the ComfyUI dropdown."""
    modes = _load_modes()
    system = _load_system()
    order = system.get("mode_order") or []
    choices: List[str] = []
    seen = set()
    for key in order:
        if key in modes and key not in seen:
            choices.append(key)
            seen.add(key)
    for key in modes:
        if key not in seen:
            choices.append(key)
            seen.add(key)
    return choices or ["image_prompt"]


def get_extract_mode_labels() -> Dict[str, str]:
    """Map mode id -> human label."""
    return {k: v["label"] for k, v in _load_modes().items()}


def get_extract_mode_label_choices() -> List[str]:
    """Ordered human labels for the dropdown (friendlier UI)."""
    modes = _load_modes()
    return [modes[k]["label"] for k in get_extract_mode_choices() if k in modes]


def resolve_extract_mode(mode: str) -> str:
    """Resolve a dropdown value (id or label) to a stable mode id."""
    modes = _load_modes()
    system = _load_system()
    default_mode = system.get("default_mode") or "image_prompt"
    raw = (mode or default_mode).strip()
    if raw in modes:
        return raw
    # Match by label (case-insensitive)
    lower = raw.lower()
    for mid, data in modes.items():
        if str(data.get("label") or "").strip().lower() == lower:
            return mid
    if default_mode in modes:
        return default_mode
    return next(iter(modes))


def _level_guidance(level_map: Dict[int, str], level: int) -> str:
    level = max(0, min(10, int(level)))
    if level in level_map:
        return level_map[level]
    # Nearest key
    if level_map:
        nearest = min(level_map.keys(), key=lambda k: abs(k - level))
        return level_map[nearest]
    return _FALLBACK_LEVEL.get(level, _FALLBACK_LEVEL[5])


def build_extract_system_prompt(
    mode: str = "image_prompt",
    spice: int = 5,
    detail: int = 5,
    extra_instructions: str = "",
) -> str:
    """Build the VL system prompt for the selected extraction mode."""
    system = _load_system()
    modes = _load_modes()
    mode_key = resolve_extract_mode(mode)
    mode_data = modes[mode_key]

    spice = max(0, min(10, int(spice)))
    detail = max(0, min(10, int(detail)))
    spice_guidance = _level_guidance(get_spice_prompts(), spice)
    detail_guidance = _level_guidance(get_detail_prompts(), detail)

    base_tmpl = (system.get("base_system") or _DEFAULT_SYSTEM["base_system"]).strip()
    try:
        base = base_tmpl.format(
            spice_guidance=spice_guidance,
            detail_guidance=detail_guidance,
        )
    except (KeyError, ValueError):
        base = (
            f"{base_tmpl}\n\nSpice guidance:\n{spice_guidance}\n\n"
            f"Detail guidance:\n{detail_guidance}"
        )

    rules = (system.get("output_rules") or "").strip()
    parts = [p for p in (base, rules, mode_data["instruction"].strip()) if p]

    extra = (extra_instructions or "").strip()
    if mode_key == "custom":
        if extra:
            parts.append(f"Custom instruction:\n{extra}")
        else:
            fallback = modes.get("image_prompt") or next(iter(modes.values()))
            parts.append(
                "No custom instruction provided — use full image-prompt reverse.\n"
                + fallback["instruction"].strip()
            )
    elif extra:
        parts.append(
            "Additional user direction (apply on top of the mode above):\n"
            f"{extra}"
        )

    return "\n\n".join(parts)


def build_extract_user_prompt(
    mode: str = "image_prompt",
    spice: int = 5,
    detail: int = 5,
    extra_instructions: str = "",
) -> str:
    """Build the user message for VL extract (image is attached separately)."""
    system = _load_system()
    modes = _load_modes()
    mode_key = resolve_extract_mode(mode)
    mode_data = modes[mode_key]
    spice = max(0, min(10, int(spice)))
    detail = max(0, min(10, int(detail)))
    extra = (extra_instructions or "").strip()

    header_lines = [f"Extract using mode: {mode_data['label']}."]
    if mode_key == "custom" and extra:
        header_lines.append(f"Custom instruction: {extra}")
    elif extra:
        header_lines.append(f"Additional direction: {extra}")
    mode_header = "\n".join(header_lines)

    if extra and mode_key != "custom":
        # extra already in header; keep block for models that weight template fields
        extra_tmpl = (
            system.get("extra_block_template")
            or _DEFAULT_SYSTEM["extra_block_template"]
        )
        try:
            extra_block = extra_tmpl.format(extra_instructions=extra)
        except (KeyError, ValueError):
            extra_block = f"Additional user direction:\n{extra}\n\n"
    elif mode_key == "custom" and extra:
        extra_tmpl = (
            system.get("extra_block_template")
            or _DEFAULT_SYSTEM["extra_block_template"]
        )
        try:
            extra_block = extra_tmpl.format(extra_instructions=extra)
        except (KeyError, ValueError):
            extra_block = f"Custom instruction:\n{extra}\n\n"
    else:
        extra_block = ""

    template = (
        system.get("user_prompt_template")
        or _DEFAULT_SYSTEM["user_prompt_template"]
    )
    try:
        return template.format(
            mode_label=mode_data["label"],
            spice=spice,
            detail=detail,
            mode_header=mode_header,
            extra_block=extra_block,
        )
    except (KeyError, ValueError):
        return (
            f"Analyze the attached source image.\nMode: {mode_data['label']}\n"
            f"Spice: {spice}/10 Detail: {detail}/10\n{mode_header}\n"
            f"{extra_block}Produce only the extracted text."
        )


def sanitize_extract_text(response: str) -> str:
    """Strip common LLM wrappers (fences, labels, surrounding quotes)."""
    result = (response or "").strip()
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
    prefixes = system.get("strip_prefixes") or _DEFAULT_SYSTEM["strip_prefixes"]
    lower = result.lower()
    for prefix in prefixes:
        p = str(prefix).lower()
        if lower.startswith(p):
            result = result[len(prefix) :].strip()
            # drop one following newline if present
            break

    if len(result) >= 2 and result[0] == result[-1] and result[0] in ('"', "'"):
        result = result[1:-1].strip()

    return result


def suggested_temperature(mode: str) -> float:
    modes = _load_modes()
    mode_key = resolve_extract_mode(mode)
    data = modes.get(mode_key)
    if not data:
        return 0.35
    try:
        return float(data.get("suggested_temperature", 0.35))
    except (TypeError, ValueError):
        return 0.35


def suggested_max_tokens(mode: str) -> int:
    modes = _load_modes()
    mode_key = resolve_extract_mode(mode)
    data = modes.get(mode_key)
    if not data:
        return 512
    try:
        return int(data.get("suggested_max_tokens", 512))
    except (TypeError, ValueError):
        return 512


def mode_meta(mode: str) -> Tuple[str, str]:
    """Return ``(mode_id, label)`` for logging / UI."""
    modes = _load_modes()
    mode_key = resolve_extract_mode(mode)
    label = modes.get(mode_key, {}).get("label") or mode_key
    return mode_key, str(label)
