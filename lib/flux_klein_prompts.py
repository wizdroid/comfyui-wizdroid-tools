"""Official FLUX.2 [klein] 9B prompt-upsampling helpers.

Ports ``SYSTEM_PROMPT_TEXT_ONLY`` / ``SYSTEM_PROMPT_WITH_IMAGES`` from the
Black Forest Labs Hugging Face space:

https://huggingface.co/spaces/black-forest-labs/FLUX.2-klein-9B/blob/main/app.py

Templates live in ``data/flux_klein/system.json`` and reload on mtime.
"""

from __future__ import annotations

from typing import Any, Dict, Tuple

from lib.json_data import load_data_json

_FALLBACK: Dict[str, str] = {
    "system_prompt": (
        "You are an expert prompt engineer for FLUX.2 by Black Forest Labs. "
        "Rewrite user prompts to be more descriptive while strictly preserving "
        "their core subject and intent. Output only the revised prompt."
    ),
    "edit_system_prompt": (
        "You are FLUX.2 by Black Forest Labs, an image-editing expert. "
        "Convert the request into one concise instruction. "
        "Output only the final instruction."
    ),
    "user_wrapper": "{prompt}",
}


def _load_system() -> Dict[str, Any]:
    data = load_data_json("flux_klein", "system.json", default=None)
    if not isinstance(data, dict):
        return dict(_FALLBACK)
    merged = dict(_FALLBACK)
    for key, val in data.items():
        if val is not None:
            merged[str(key)] = val
    return merged


def build_flux_klein_messages(
    prompt: str,
    *,
    edit: bool = False,
) -> Tuple[str, str]:
    """Return ``(system, user)`` for official Klein prompt upsampling."""
    system = _load_system()
    if edit:
        sys_txt = str(system.get("edit_system_prompt") or _FALLBACK["edit_system_prompt"])
    else:
        sys_txt = str(system.get("system_prompt") or _FALLBACK["system_prompt"])
    wrapper = str(system.get("user_wrapper") or _FALLBACK["user_wrapper"])
    return sys_txt, wrapper.format(prompt=(prompt or "").strip())
