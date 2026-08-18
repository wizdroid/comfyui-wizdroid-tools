"""Official Qwen-Image prompt rewrite helpers.

Ports ``rewrite()`` / ``polish_prompt_en`` / ``polish_prompt_zh`` /
``polish_edit_prompt`` from QwenLM/Qwen-Image ``prompt_utils.py`` (line 183)
so a local Ollama model can do the same polish the official DashScope path
does.

Templates live in ``data/qwen_image/system.json`` and reload on mtime.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, List, Optional, Tuple

from lib.json_data import load_data_json

logger = logging.getLogger(__name__)

# Official get_caption_language(): first CJK Unified Ideograph → zh.
_CJK_RANGES = (("\u4e00", "\u9fff"),)

LANGUAGE_CHOICES: tuple[str, ...] = ("auto", "en", "zh")
MODE_CHOICES: tuple[str, ...] = ("rewrite", "edit")

_FALLBACK: Dict[str, Any] = {
    "helper_system": "You are a helpful assistant.",
    "system_prompt_en": (
        "You are a Prompt optimizer. Rewrite the user input into a complete "
        "image prompt under 200 words. Preserve the original meaning. "
        "Output only the rewritten prompt."
    ),
    "system_prompt_zh": (
        "你是一位Prompt优化师。将用户输入改写为完整的图像提示词，不超过200字。"
        "不改变原意。只输出改写后的提示词。"
    ),
    "user_wrapper_en": "User Input: {prompt}\n\n Rewritten Prompt:",
    "user_wrapper_zh": "用户输入：{prompt}\n改写输出：",
    "magic_en": "Ultra HD, 4K, cinematic composition",
    "magic_zh": "超清，4K，电影级构图",
    "edit_system_prompt": (
        "You are a professional edit prompt enhancer. Return JSON "
        '{"Rewritten": "..."} with a direct, specific edit instruction.'
    ),
    "edit_user_wrapper": "User Input: {prompt}\n\nRewritten Prompt:",
    "strip_prefixes": [
        "rewritten prompt:",
        "rewritten:",
        "改写输出：",
        "改写输出:",
        "prompt:",
    ],
}


def _load_system() -> Dict[str, Any]:
    data = load_data_json("qwen_image", "system.json", default=None)
    if not isinstance(data, dict):
        return dict(_FALLBACK)
    merged = dict(_FALLBACK)
    for key, val in data.items():
        if val is None:
            continue
        if key == "strip_prefixes" and isinstance(val, list):
            merged[key] = [str(x) for x in val]
            continue
        merged[str(key)] = val
    return merged


def get_language_choices() -> List[str]:
    return list(LANGUAGE_CHOICES)


def get_mode_choices() -> List[str]:
    return list(MODE_CHOICES)


def normalize_language(value: str) -> str:
    raw = (value or "auto").strip().lower()
    if raw in ("zh", "chinese", "中文", "cn"):
        return "zh"
    if raw in ("en", "english"):
        return "en"
    return "auto"


def normalize_mode(value: str) -> str:
    raw = (value or "rewrite").strip().lower()
    if raw in ("edit", "polish_edit", "image_edit"):
        return "edit"
    return "rewrite"


def get_caption_language(prompt: str) -> str:
    """Official language sniff: any CJK Unified Ideograph → zh, else en."""
    for char in prompt or "":
        for start, end in _CJK_RANGES:
            if start <= char <= end:
                return "zh"
    return "en"


def resolve_language(prompt: str, language: str = "auto") -> str:
    lang = normalize_language(language)
    if lang == "auto":
        return get_caption_language(prompt)
    return lang


def build_rewrite_messages(prompt: str, language: str = "auto") -> Tuple[str, str, str]:
    """Return ``(system, user, lang)`` for official ``rewrite()``."""
    system = _load_system()
    lang = resolve_language(prompt, language)
    if lang == "zh":
        sys_txt = str(system.get("system_prompt_zh") or _FALLBACK["system_prompt_zh"])
        wrapper = str(system.get("user_wrapper_zh") or _FALLBACK["user_wrapper_zh"])
    else:
        sys_txt = str(system.get("system_prompt_en") or _FALLBACK["system_prompt_en"])
        wrapper = str(system.get("user_wrapper_en") or _FALLBACK["user_wrapper_en"])
    user = wrapper.format(prompt=(prompt or "").strip())
    return sys_txt, user, lang


def build_edit_messages(prompt: str) -> Tuple[str, str]:
    """Return ``(system, user)`` for official ``polish_edit_prompt()``."""
    system = _load_system()
    sys_txt = str(system.get("edit_system_prompt") or _FALLBACK["edit_system_prompt"])
    wrapper = str(system.get("edit_user_wrapper") or _FALLBACK["edit_user_wrapper"])
    return sys_txt, wrapper.format(prompt=(prompt or "").strip())


def _strip_wrappers(text: str) -> str:
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
    prefixes = system.get("strip_prefixes") or _FALLBACK["strip_prefixes"]
    lower = result.lower()
    for prefix in prefixes:
        p = str(prefix).lower()
        if lower.startswith(p):
            result = result[len(prefix) :].strip()
            break

    if len(result) >= 2 and result[0] == result[-1] and result[0] in ('"', "'"):
        result = result[1:-1].strip()

    # Official path collapses newlines to spaces.
    result = re.sub(r"\s+", " ", result).strip()
    return result


def parse_edit_rewritten(response: str) -> str:
    """Pull the ``Rewritten`` field from the official JSON envelope."""
    raw = (response or "").strip()
    if not raw:
        return ""

    cleaned = raw.replace("```json", "").replace("```", "").strip()
    try:
        data = json.loads(cleaned)
        if isinstance(data, dict):
            value = data.get("Rewritten") or data.get("rewritten") or ""
            if value:
                return _strip_wrappers(str(value))
    except Exception:  # noqa: BLE001
        pass

    match = re.search(r'"Rewritten"\s*:\s*"(.*?)"\s*[,}]', cleaned, flags=re.DOTALL)
    if match:
        try:
            return _strip_wrappers(json.loads(f'"{match.group(1)}"'))
        except Exception:  # noqa: BLE001
            return _strip_wrappers(match.group(1))

    return _strip_wrappers(cleaned)


def sanitize_rewritten(response: str) -> str:
    """Clean a text-rewrite response (official ``rewrite()``)."""
    return _strip_wrappers(response)


def append_magic(prompt: str, language: str, *, enabled: bool = True) -> str:
    """Append the official Qwen-Image magic suffix.

    Official code concatenates with no separator (``polished + magic``).
    That glues the last word onto ``Ultra``. We insert a space, which is
    what every downstream Qwen-Image sampler expects.
    """
    text = (prompt or "").strip()
    if not enabled or not text:
        return text
    system = _load_system()
    lang = "zh" if normalize_language(language) == "zh" else "en"
    if lang == "zh":
        magic = str(system.get("magic_zh") or _FALLBACK["magic_zh"]).strip()
    else:
        magic = str(system.get("magic_en") or _FALLBACK["magic_en"]).strip()
    if not magic:
        return text
    if text.endswith(magic) or magic.lower() in text.lower():
        return text
    return f"{text} {magic}"


def polish_rewrite_response(
    response: str,
    language: str,
    *,
    append_magic_suffix: bool = True,
) -> str:
    return append_magic(
        sanitize_rewritten(response),
        language,
        enabled=append_magic_suffix,
    )


def polish_edit_response(response: str) -> str:
    return parse_edit_rewritten(response)
