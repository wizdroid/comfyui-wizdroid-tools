"""Official Krea 2 prompt expander (docs/expansion.txt).

https://github.com/krea-ai/krea-2/blob/main/docs/prompting.md
https://github.com/krea-ai/krea-2/blob/main/docs/expansion.txt
"""

from __future__ import annotations

from typing import Any, Dict, Tuple

from lib.json_data import load_data_json

_FALLBACK: Dict[str, str] = {
    "system_prompt": (
        "You are an expert prompt engineer for text-to-image models. "
        "Expand the user prompt into one cohesive natural-language paragraph. "
        "Preserve subjects and intent. Quote any on-image text. "
        "Output only the final prompt paragraph."
    ),
    "user_wrapper": "{prompt}",
}


def _load_system() -> Dict[str, Any]:
    data = load_data_json("krea", "system.json", default=None)
    if not isinstance(data, dict):
        return dict(_FALLBACK)
    merged = dict(_FALLBACK)
    for key, val in data.items():
        if val is not None:
            merged[str(key)] = val
    return merged


def build_krea_messages(prompt: str) -> Tuple[str, str]:
    """Return ``(system, user)`` for official Krea 2 expansion."""
    system = _load_system()
    sys_txt = str(system.get("system_prompt") or _FALLBACK["system_prompt"])
    wrapper = str(system.get("user_wrapper") or _FALLBACK["user_wrapper"])
    return sys_txt, wrapper.format(prompt=(prompt or "").strip())
