"""Website → character image prompt meta-prompts.

Loads ``data/website/system.json`` (reloaded when it changes on disk) and
reuses the spice / fantasy / detail level guidance from ``data/prompts/*.json``
via ``lib.prompts`` — same levels as the LLM Prompt Generator.
"""

from __future__ import annotations

from typing import Dict

from lib.json_data import load_data_json
from lib.prompts import get_detail_prompts, get_fantasy_prompts, get_spice_prompts

_FALLBACK_SYSTEM: Dict[str, str] = {
    "system_prompt_template": (
        "You are a prompt writer for AI image generators. Write a single "
        "paragraph image prompt describing the character from the website "
        "information. Max about {max_tokens} words.\n"
        "{spice_guidance}\n{fantasy_guidance}\n{detail_guidance}"
    ),
    "user_prompt_wrapper": (
        "Write an image prompt for this character from the website info:\n\n"
        "{website_text}"
    ),
}


def _load_system() -> Dict[str, str]:
    raw = load_data_json("website", "system.json", default=None)
    if not isinstance(raw, dict):
        return dict(_FALLBACK_SYSTEM)
    merged = dict(_FALLBACK_SYSTEM)
    merged.update({k: str(v) for k, v in raw.items()})
    return merged


def build_website_system_prompt(
    spice: int = 0,
    fantasy: int = 0,
    detail: int = 5,
    max_tokens: int = 384,
) -> str:
    """Build the Ollama system prompt for website → character image prompt."""
    spice = max(0, min(10, int(spice)))
    fantasy = max(0, min(10, int(fantasy)))
    detail = max(0, min(10, int(detail)))

    spice_map = get_spice_prompts()
    fantasy_map = get_fantasy_prompts()
    detail_map = get_detail_prompts()

    system = _load_system()
    template = (
        system.get("system_prompt_template")
        or _FALLBACK_SYSTEM["system_prompt_template"]
    )
    return template.format(
        max_tokens=max_tokens,
        spice_guidance=spice_map.get(spice, spice_map.get(5, "")),
        fantasy_guidance=fantasy_map.get(fantasy, fantasy_map.get(5, "")),
        detail_guidance=detail_map.get(detail, detail_map.get(5, "")),
    )


def build_website_user_prompt(website_text: str) -> str:
    """Build the Ollama user prompt wrapping the extracted website text."""
    system = _load_system()
    template = (
        system.get("user_prompt_wrapper")
        or _FALLBACK_SYSTEM["user_prompt_wrapper"]
    )
    return template.format(website_text=(website_text or "").strip())


def sanitize_prompt(text: str) -> str:
    """Strip whitespace, markdown fences and surrounding quotes."""
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

    return result
