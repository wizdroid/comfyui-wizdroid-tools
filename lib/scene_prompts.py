"""Video scene prompt assembly — templates and choices from data/scene/.

Files:
  data/scene/choices.json  — mood, style dropdowns
  data/scene/system.json   — text + VL system/user templates
"""

from __future__ import annotations

import re
from typing import Dict, List

from lib.json_data import load_data_json

_FALLBACK_CHOICES: Dict[str, List[str]] = {
    "mood": [
        "neutral",
        "calm",
        "romantic",
        "tense",
        "dramatic",
        "joyful",
        "melancholy",
        "mysterious",
        "epic",
        "playful",
    ],
    "style": [
        "cinematic",
        "candid",
        "documentary",
        "anime",
        "handheld",
        "music video",
        "noir",
        "hyperrealistic",
        "arthouse",
        "commercial",
    ],
}

_FALLBACK_SYSTEM: Dict[str, str] = {
    "text_system_template": (
        "You write video scene packages for AI video models.\n"
        "Duration ~{duration_seconds}s. Mood: {mood}. Style: {style}.\n"
        "Output exactly:\n===SCENE===\n...\n===DIALOGUE===\n...\n"
        "===IMAGE_PROMPT===\n...\n{extra_guidance}"
    ),
    "text_user_template": (
        "Duration: {duration_seconds}s\nMood: {mood}\nStyle: {style}\n"
        "Idea:\n{user_prompt}\n{extra_block}"
    ),
    "vl_system_template": (
        "You analyze a source image and write a video scene package for I2V models.\n"
        "Duration ~{duration_seconds}s. Mood: {mood}. Style: {style}.\n"
        "Stay consistent with the image. Output exactly:\n"
        "===SCENE===\n...\n===DIALOGUE===\n...\n===IMAGE_PROMPT===\n...\n"
        "{extra_guidance}"
    ),
    "vl_user_template": (
        "Duration: {duration_seconds}s\nMood: {mood}\nStyle: {style}\n"
        "User direction:\n{user_prompt}\n{extra_block}"
    ),
    "extra_guidance_default": "Keep content legal and consensual.",
}

_SECTION_MARKERS = ("SCENE", "DIALOGUE", "IMAGE_PROMPT")
_SECTION_RE = re.compile(
    r"===\s*(SCENE|DIALOGUE|IMAGE_PROMPT)\s*===\s*",
    re.IGNORECASE,
)


def _load_choices() -> Dict[str, List[str]]:
    data = load_data_json("scene", "choices.json", default=None)
    if not isinstance(data, dict) or not data:
        return {k: list(v) for k, v in _FALLBACK_CHOICES.items()}
    out: Dict[str, List[str]] = {}
    for key, val in data.items():
        if isinstance(val, list) and val:
            out[str(key)] = [str(x) for x in val if str(x).strip()]
    for k, v in _FALLBACK_CHOICES.items():
        out.setdefault(k, list(v))
    return out


def _load_system() -> Dict[str, str]:
    data = load_data_json("scene", "system.json", default=None)
    merged = dict(_FALLBACK_SYSTEM)
    if isinstance(data, dict):
        for k, v in data.items():
            if v is not None:
                merged[str(k)] = str(v)
    return merged


def get_mood_choices() -> List[str]:
    return list(_load_choices().get("mood") or _FALLBACK_CHOICES["mood"])


def get_style_choices() -> List[str]:
    return list(_load_choices().get("style") or _FALLBACK_CHOICES["style"])


def _format_extra_block(extra_instructions: str) -> str:
    text = (extra_instructions or "").strip()
    if not text:
        return ""
    return f"Extra instructions:\n{text}\n\n"


def build_text_system_prompt(
    *,
    duration_seconds: float,
    mood: str,
    style: str,
    extra_guidance: str = "",
) -> str:
    system = _load_system()
    template = system.get("text_system_template") or _FALLBACK_SYSTEM["text_system_template"]
    guidance = (extra_guidance or "").strip() or system.get(
        "extra_guidance_default", _FALLBACK_SYSTEM["extra_guidance_default"]
    )
    return template.format(
        duration_seconds=_fmt_duration(duration_seconds),
        mood=(mood or "neutral").strip(),
        style=(style or "cinematic").strip(),
        extra_guidance=guidance,
    )


def build_text_user_prompt(
    *,
    user_prompt: str,
    duration_seconds: float,
    mood: str,
    style: str,
    extra_instructions: str = "",
) -> str:
    system = _load_system()
    template = system.get("text_user_template") or _FALLBACK_SYSTEM["text_user_template"]
    return template.format(
        user_prompt=(user_prompt or "").strip(),
        duration_seconds=_fmt_duration(duration_seconds),
        mood=(mood or "neutral").strip(),
        style=(style or "cinematic").strip(),
        extra_block=_format_extra_block(extra_instructions),
    )


def build_vl_system_prompt(
    *,
    duration_seconds: float,
    mood: str,
    style: str,
    extra_guidance: str = "",
) -> str:
    system = _load_system()
    template = system.get("vl_system_template") or _FALLBACK_SYSTEM["vl_system_template"]
    guidance = (extra_guidance or "").strip() or system.get(
        "extra_guidance_default", _FALLBACK_SYSTEM["extra_guidance_default"]
    )
    return template.format(
        duration_seconds=_fmt_duration(duration_seconds),
        mood=(mood or "neutral").strip(),
        style=(style or "cinematic").strip(),
        extra_guidance=guidance,
    )


def build_vl_user_prompt(
    *,
    user_prompt: str,
    duration_seconds: float,
    mood: str,
    style: str,
    extra_instructions: str = "",
) -> str:
    system = _load_system()
    template = system.get("vl_user_template") or _FALLBACK_SYSTEM["vl_user_template"]
    direction = (user_prompt or "").strip() or (
        "Animate this image naturally with subtle motion matching the mood and style."
    )
    return template.format(
        user_prompt=direction,
        duration_seconds=_fmt_duration(duration_seconds),
        mood=(mood or "neutral").strip(),
        style=(style or "cinematic").strip(),
        extra_block=_format_extra_block(extra_instructions),
    )


def _fmt_duration(seconds: float) -> str:
    try:
        val = float(seconds)
    except (TypeError, ValueError):
        val = 5.0
    val = max(0.5, min(120.0, val))
    if abs(val - round(val)) < 1e-6:
        return str(int(round(val)))
    return f"{val:.1f}"


def sanitize_section(text: str) -> str:
    """Strip fences/quotes from a section body."""
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


def parse_scene_response(text: str) -> Dict[str, str]:
    """Parse ===SCENE=== / ===DIALOGUE=== / ===IMAGE_PROMPT=== blocks.

    Missing sections fall back to empty string (dialogue may be ``none``).
    If no markers are found, the whole text is treated as the scene.
    """
    raw = (text or "").strip()
    empty = {"scene": "", "dialogue": "", "image_prompt": "", "raw": raw}
    if not raw:
        return empty

    parts = _SECTION_RE.split(raw)
    # parts: [preamble, MARKER, body, MARKER, body, ...]
    if len(parts) < 3:
        cleaned = sanitize_section(raw)
        return {
            "scene": cleaned,
            "dialogue": "",
            "image_prompt": "",
            "raw": raw,
        }

    sections: Dict[str, str] = {"scene": "", "dialogue": "", "image_prompt": ""}
    # First element is preamble; then pairs of (marker, body)
    i = 1
    while i + 1 < len(parts):
        marker = parts[i].strip().upper()
        body = sanitize_section(parts[i + 1])
        if marker == "SCENE":
            sections["scene"] = body
        elif marker == "DIALOGUE":
            sections["dialogue"] = body
        elif marker == "IMAGE_PROMPT":
            sections["image_prompt"] = body
        i += 2

    # Normalize silent dialogue
    dlg = sections["dialogue"].strip()
    if dlg.lower() in {"none", "n/a", "na", "silent", "no dialogue", "-"}:
        sections["dialogue"] = ""

    sections["raw"] = raw
    return sections


def clamp_duration(seconds: float) -> float:
    try:
        val = float(seconds)
    except (TypeError, ValueError):
        val = 5.0
    return max(0.5, min(120.0, val))
