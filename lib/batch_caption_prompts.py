"""Batch captioner meta-prompts — modes from data/batch_caption/modes.json.

Modes (captioning styles for LoRA dataset prep) live in
``data/batch_caption/modes.json``; the system/user templates live in
``data/batch_caption/system.json``. Both reload on disk change.
"""

from __future__ import annotations

from typing import Dict, List, Tuple

from lib.json_data import load_data_json

_FALLBACK_MODES: Dict[str, Dict[str, str]] = {
    "booru_tags": {
        "label": "Booru tags (comma-separated)",
        "instruction": "Write comma-separated booru-style tags for the image.",
    },
    "natural_caption": {
        "label": "Natural sentence",
        "instruction": "Write one natural sentence describing the image.",
    },
}

_FALLBACK_SYSTEM: Dict[str, str] = {
    "system_prompt_template": (
        "Caption the image. Output ONLY the caption text.\n"
        "{mode_instruction}"
    ),
    "user_prompt_wrapper": "Caption this image.\n\n{mode_instruction}\n\n{extra_instructions}",
}


def _load_modes() -> Dict[str, Dict[str, str]]:
    raw = load_data_json("batch_caption", "modes.json", default=None)
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
    raw = load_data_json("batch_caption", "system.json", default=None)
    if not isinstance(raw, dict):
        return dict(_FALLBACK_SYSTEM)
    merged = dict(_FALLBACK_SYSTEM)
    merged.update({k: str(v) for k, v in raw.items()})
    return merged


def get_caption_mode_choices() -> List[str]:
    """Ordered mode ids for the dropdown (JSON key order)."""
    return list(_load_modes().keys())


def get_caption_mode_labels() -> Dict[str, str]:
    return {mid: meta["label"] for mid, meta in _load_modes().items()}


def mode_meta(mode_label: str) -> Tuple[str, str]:
    """Resolve a dropdown label back to (mode_id, label)."""
    modes = _load_modes()
    for mid, meta in modes.items():
        if meta["label"] == mode_label:
            return mid, meta["label"]
    return mode_label, mode_label


def build_caption_system_prompt(mode: str, extra_instructions: str = "") -> str:
    modes = _load_modes()
    meta = modes.get(mode, _FALLBACK_MODES.get(mode, _FALLBACK_MODES["natural_caption"]))
    system = _load_system()
    template = (
        system.get("system_prompt_template")
        or _FALLBACK_SYSTEM["system_prompt_template"]
    )
    return template.format(
        mode_instruction=(meta.get("instruction") or "").strip(),
        extra_instructions=(extra_instructions or "").strip(),
    )


def build_caption_user_prompt(mode: str, extra_instructions: str = "") -> str:
    modes = _load_modes()
    meta = modes.get(mode, _FALLBACK_MODES.get(mode, _FALLBACK_MODES["natural_caption"]))
    system = _load_system()
    template = (
        system.get("user_prompt_wrapper")
        or _FALLBACK_SYSTEM["user_prompt_wrapper"]
    )
    return template.format(
        mode_instruction=(meta.get("instruction") or "").strip(),
        extra_instructions=(extra_instructions or "").strip(),
    )


def sanitize_caption(text: str) -> str:
    """Strip whitespace, fences, and surrounding quotes from a caption."""
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
