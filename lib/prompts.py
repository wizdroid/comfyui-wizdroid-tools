"""Meta-prompt system for LLM image prompt nodes.

Fragments for spice, fantasy, and detail levels, plus the system prompt
template and user prompt wrapper, live under data/prompts/ and are reloaded
when those JSON files change on disk.

Files:
  data/prompts/spice.json
  data/prompts/fantasy.json
  data/prompts/detail.json
  data/prompts/system.json   — system_prompt_template, user_prompt_wrapper
"""

from __future__ import annotations

from typing import Dict

from lib.json_data import load_data_json

_FALLBACK_LEVEL: Dict[int, str] = {
    0: "Use a neutral, moderate style.",
    5: "Use a balanced, typical style.",
    10: "Use an intense, maximal style.",
}

_FALLBACK_SYSTEM = {
    "system_prompt_template": (
        "You write Krea 2 image prompts as one natural-language paragraph.\n"
        "Max about {max_tokens} words.\n"
        "{spice_guidance}\n{fantasy_guidance}\n{detail_guidance}"
    ),
    "user_prompt_wrapper": "Expand this idea into a Krea 2 image prompt:\n\n{concept}",
}


def _load_level_map(filename: str) -> Dict[int, str]:
    """Load a 0–10 (string-keyed) level map from data/prompts/."""
    raw = load_data_json("prompts", filename, default=None)
    if not isinstance(raw, dict) or not raw:
        return dict(_FALLBACK_LEVEL)
    out: Dict[int, str] = {}
    for k, v in raw.items():
        try:
            out[int(k)] = str(v)
        except (TypeError, ValueError):
            continue
    return out or dict(_FALLBACK_LEVEL)


def _load_system() -> Dict[str, str]:
    raw = load_data_json("prompts", "system.json", default=None)
    if not isinstance(raw, dict):
        return dict(_FALLBACK_SYSTEM)
    merged = dict(_FALLBACK_SYSTEM)
    merged.update({k: str(v) for k, v in raw.items()})
    return merged


def get_spice_prompts() -> Dict[int, str]:
    return _load_level_map("spice.json")


def get_fantasy_prompts() -> Dict[int, str]:
    return _load_level_map("fantasy.json")


def get_detail_prompts() -> Dict[int, str]:
    return _load_level_map("detail.json")


def __getattr__(name: str):
    """Lazy dynamic attributes so imports stay in sync with JSON on disk."""
    if name == "SPICE_PROMPTS":
        return get_spice_prompts()
    if name == "FANTASY_PROMPTS":
        return get_fantasy_prompts()
    if name == "DETAIL_PROMPTS":
        return get_detail_prompts()
    if name == "SYSTEM_PROMPT_TEMPLATE":
        return _load_system()["system_prompt_template"]
    if name == "USER_PROMPT_WRAPPER":
        return _load_system()["user_prompt_wrapper"]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def get_user_prompt_wrapper() -> str:
    """Return the user prompt wrapper template (reloads with system.json)."""
    return _load_system().get("user_prompt_wrapper") or _FALLBACK_SYSTEM["user_prompt_wrapper"]


def build_system_prompt(
    spice: int,
    fantasy: int,
    detail: int,
    max_tokens: int = 77,
) -> str:
    """Build the complete system prompt with slider-specific meta-prompts."""
    spice = max(0, min(10, spice))
    fantasy = max(0, min(10, fantasy))
    detail = max(0, min(10, detail))

    spice_map = get_spice_prompts()
    fantasy_map = get_fantasy_prompts()
    detail_map = get_detail_prompts()
    system = _load_system()

    template = system.get("system_prompt_template") or _FALLBACK_SYSTEM["system_prompt_template"]
    return template.format(
        max_tokens=max_tokens,
        spice_guidance=spice_map.get(spice, spice_map.get(5, _FALLBACK_LEVEL[5])),
        fantasy_guidance=fantasy_map.get(fantasy, fantasy_map.get(5, _FALLBACK_LEVEL[5])),
        detail_guidance=detail_map.get(detail, detail_map.get(5, _FALLBACK_LEVEL[5])),
    )
