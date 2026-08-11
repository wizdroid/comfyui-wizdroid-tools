"""Iterative prompt refiner meta-prompts + in-session memory buffer.

Templates live in ``data/refine/system.json``. A small module-level buffer
stores the last refined prompt per ``session_id`` so the node can refine
iteratively across executions (memory lives for the ComfyUI process).
"""

from __future__ import annotations

import re
from typing import Dict, Tuple

from lib.json_data import load_data_json

_FALLBACK_SYSTEM: Dict[str, str] = {
    "system_prompt_template": (
        "You are a prompt refiner for AI image generators.\n"
        "Output REVISION NOTE: then REFINED PROMPT: lines only.\n"
        "Keep the refined prompt under {max_tokens} words.\n{extra_instructions}"
    ),
    "user_prompt_wrapper": "Current prompt:\n{current_prompt}\n\nChange request: {instruction}",
    "user_prompt_wrapper_with_image": (
        "Look at the reference image first, then refine the prompt below.\n"
        "Current prompt:\n{current_prompt}\n\nChange request: {instruction}"
    ),
}

# --- in-process session memory (survives across node executions) ----------
_SESSION_BUFFER: Dict[str, str] = {}


def get_session_prompt(session_id: str) -> str:
    return _SESSION_BUFFER.get(session_id, "")


def set_session_prompt(session_id: str, prompt: str) -> None:
    _SESSION_BUFFER[session_id] = (prompt or "").strip()


def clear_session_prompt(session_id: str) -> None:
    _SESSION_BUFFER.pop(session_id, None)


def _load_system() -> Dict[str, str]:
    raw = load_data_json("refine", "system.json", default=None)
    if not isinstance(raw, dict):
        return dict(_FALLBACK_SYSTEM)
    merged = dict(_FALLBACK_SYSTEM)
    merged.update({k: str(v) for k, v in raw.items()})
    return merged


def build_refine_system_prompt(
    max_tokens: int = 384,
    extra_instructions: str = "",
) -> str:
    system = _load_system()
    template = (
        system.get("system_prompt_template")
        or _FALLBACK_SYSTEM["system_prompt_template"]
    )
    return template.format(
        max_tokens=max(20, int(max_tokens)),
        extra_instructions=(extra_instructions or "").strip(),
    )


def build_refine_user_prompt(
    current_prompt: str,
    instruction: str,
    with_image: bool = False,
) -> str:
    system = _load_system()
    key = "user_prompt_wrapper_with_image" if with_image else "user_prompt_wrapper"
    template = system.get(key) or _FALLBACK_SYSTEM[key]
    return template.format(
        current_prompt=(current_prompt or "").strip(),
        instruction=(instruction or "").strip(),
    )


_NOTE_MARKER = re.compile(r"(?im)^\s*REVISION\s+NOTE\s*:")
_PROMPT_MARKER = re.compile(r"(?im)^\s*REFINED\s+PROMPT\s*:")


def parse_refine_response(text: str) -> Tuple[str, str, str]:
    """Split a response into (note, refined_prompt, raw)."""
    raw = (text or "").strip()
    if not raw:
        return "", "", raw

    note_match = re.search(_NOTE_MARKER, raw)
    prompt_match = re.search(_PROMPT_MARKER, raw)
    if not prompt_match:
        # Lenient: treat the whole response as the refined prompt
        return "", _clean_prompt(raw), raw

    refined = raw[prompt_match.end() :].strip()
    before = raw[: prompt_match.start()].strip()
    note = ""
    if note_match and note_match.start() < prompt_match.start():
        note = before[note_match.end() :].strip()

    return note, _clean_prompt(refined), raw


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
