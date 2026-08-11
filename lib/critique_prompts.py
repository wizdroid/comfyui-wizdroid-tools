"""Image critique meta-prompts + response parsing.

Modes (critique focus areas) live in ``data/critique/modes.json``; the
system/user templates live in ``data/critique/system.json``.
"""

from __future__ import annotations

import re
from typing import Dict, List, Tuple

from lib.json_data import load_data_json

_FALLBACK_MODES: Dict[str, Dict[str, str]] = {
    "general": {
        "label": "General critique",
        "instruction": "Assess overall quality and prompt adherence.",
    },
}

_FALLBACK_SYSTEM: Dict[str, str] = {
    "system_prompt_template": (
        "Critique the image and rewrite an improved prompt.\n"
        "Output CRITIQUE: then REVISED PROMPT: sections.\n"
        "{mode_instruction}\n{extra_instructions}"
    ),
    "user_prompt_wrapper": "Image prompt that was used:\n{prompt}\n\nCritique this image.",
}


def _load_modes() -> Dict[str, Dict[str, str]]:
    raw = load_data_json("critique", "modes.json", default=None)
    if not isinstance(raw, dict):
        return dict(_FALLBACK_MODES)
    out: Dict[str, Dict[str, str]] = {}
    for mid, meta in raw.items():
        if isinstance(meta, dict):
            out[str(mid)] = {
                "label": str(meta.get("label") or mid),
                "instruction": str(meta.get("instruction") or ""),
            }
    return out or dict(_FALLBACK_MODES)


def _load_system() -> Dict[str, str]:
    raw = load_data_json("critique", "system.json", default=None)
    if not isinstance(raw, dict):
        return dict(_FALLBACK_SYSTEM)
    merged = dict(_FALLBACK_SYSTEM)
    merged.update({k: str(v) for k, v in raw.items()})
    return merged


def get_critique_mode_choices() -> List[str]:
    return list(_load_modes().keys())


def get_critique_mode_labels() -> Dict[str, str]:
    return {mid: meta["label"] for mid, meta in _load_modes().items()}


def mode_meta(mode_label: str) -> Tuple[str, str]:
    modes = _load_modes()
    for mid, meta in modes.items():
        if meta["label"] == mode_label:
            return mid, meta["label"]
    return mode_label, mode_label


def build_critique_system_prompt(
    mode: str,
    extra_instructions: str = "",
) -> str:
    modes = _load_modes()
    meta = modes.get(mode, _FALLBACK_MODES.get(mode, _FALLBACK_MODES["general"]))
    system = _load_system()
    template = (
        system.get("system_prompt_template")
        or _FALLBACK_SYSTEM["system_prompt_template"]
    )
    return template.format(
        mode_instruction=(meta.get("instruction") or "").strip(),
        extra_instructions=(extra_instructions or "").strip(),
    )


def build_critique_user_prompt(prompt: str) -> str:
    system = _load_system()
    template = (
        system.get("user_prompt_wrapper")
        or _FALLBACK_SYSTEM["user_prompt_wrapper"]
    )
    return template.format(prompt=(prompt or "").strip())


_CRITIQUE_MARKER = re.compile(r"(?im)^\s*CRITIQUE\s*:")
_REVISED_MARKER = re.compile(r"(?im)^\s*REVISED\s+PROMPT\s*:")


def parse_critique_response(text: str) -> Tuple[str, str, str]:
    """Split a model response into (critique, revised_prompt, raw).

    Falls back to (raw, raw, raw) if the sections can't be parsed.
    """
    raw = (text or "").strip()
    if not raw:
        return "", "", raw

    revised = re.search(_REVISED_MARKER, raw)
    if not revised:
        return raw, raw, raw

    revised_text = raw[revised.end() :].strip()
    critique_text = raw[: revised.start()].strip()

    critique_match = re.search(_CRITIQUE_MARKER, critique_text)
    if critique_match:
        critique_text = critique_text[critique_match.end() :].strip()

    return critique_text, _clean_prompt(revised_text), raw


def _clean_prompt(text: str) -> str:
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
