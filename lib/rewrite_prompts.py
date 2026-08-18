"""Text rewrite meta-prompts — loaded at runtime from data/rewrite/*.json.

Edit JSON to customize or add modes; changes apply on the next call once the
file mtime changes (refresh the ComfyUI page so INPUT_TYPES re-runs).

Files:
  data/rewrite/modes.json   — mode_id -> {label, instruction, suggested_temperature?}
  data/rewrite/system.json  — base system text, mode_order, user template, strip prefixes
"""

from __future__ import annotations

import re
from typing import Any, Dict, List

from lib.json_data import load_data_json
from lib.flux_klein_prompts import build_flux_klein_messages
from lib.qwen_image_prompts import (
    append_magic,
    build_rewrite_messages,
    resolve_language,
)

_DEFAULT_SYSTEM: Dict[str, Any] = {
    "base_system": (
        "You are an expert text rewriter and style converter.\n"
        "Transform the user's input text according to the active mode."
    ),
    "output_rules": (
        "Output rules (always):\n"
        "- Output ONLY the rewritten text — no quotes, markdown fences, or labels.\n"
        "- Keep the core meaning of the source text."
    ),
    "default_mode": "clean_up",
    "mode_order": ["clean_up", "custom"],
    "clean_up_header_extra": (
        "Fix grammar and spelling, restructure for clarity, "
        "and do not add any new content."
    ),
    "photography_base": (
        "You are a photography prompt writer for AI image and video generators.\n"
        "Output ONLY the rewritten prompt."
    ),
    "photography_rules": (
        "Honor SFW and NSFW equally. Do not invent sexual content. "
        "Do not refuse or euphemize explicit sources. Never invent minors."
    ),
    "photography_user_header": (
        "Rewrite the following into a photography image prompt using mode: {label}."
    ),
    "user_prompt_template": "{header}\n\n---\n{text}\n---\n\nRewritten text:",
    "strip_prefixes": [
        "cleaned text:",
        "corrected text:",
        "rewritten text:",
        "revised text:",
        "converted text:",
    ],
}

_DEFAULT_MODES: Dict[str, Any] = {
    "clean_up": {
        "label": "Clean up (fix only)",
        "instruction": (
            "Mode: Clean up only.\n"
            "Fix spelling, grammar, and structure. Do not add new content."
        ),
        "suggested_temperature": 0.2,
    },
    "custom": {
        "label": "Custom instruction",
        "instruction": (
            "Mode: Custom.\nFollow the user's custom instruction carefully."
        ),
        "suggested_temperature": 0.55,
    },
}


def _load_system() -> Dict[str, Any]:
    data = load_data_json("rewrite", "system.json", default=None)
    if not isinstance(data, dict):
        return dict(_DEFAULT_SYSTEM)
    # Merge so missing keys still work if user trims the file
    merged = dict(_DEFAULT_SYSTEM)
    merged.update(data)
    return merged


def _load_modes() -> Dict[str, Dict[str, Any]]:
    data = load_data_json("rewrite", "modes.json", default=None)
    if not isinstance(data, dict) or not data:
        return {k: dict(v) for k, v in _DEFAULT_MODES.items()}
    out: Dict[str, Dict[str, Any]] = {}
    for key, val in data.items():
        if not isinstance(val, dict):
            continue
        instruction = (val.get("instruction") or "").strip()
        if not instruction:
            continue
        entry: Dict[str, Any] = {
            "label": str(val.get("label") or key),
            "instruction": instruction,
            "suggested_temperature": float(val.get("suggested_temperature", 0.4)),
        }
        if val.get("kind"):
            entry["kind"] = str(val["kind"])
        if val.get("language"):
            entry["language"] = str(val["language"])
        if "append_magic" in val:
            entry["append_magic"] = bool(val["append_magic"])
        if "edit" in val:
            entry["edit"] = bool(val["edit"])
        out[str(key)] = entry
    return out or {k: dict(v) for k, v in _DEFAULT_MODES.items()}


def get_rewrite_modes() -> Dict[str, Dict[str, Any]]:
    """Return current mode map (reloads when modes.json changes)."""
    return _load_modes()


def get_rewrite_mode_choices() -> List[str]:
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
    # Any modes not listed in mode_order still appear (so new JSON keys show up)
    for key in modes:
        if key not in seen:
            choices.append(key)
            seen.add(key)
    return choices or ["clean_up"]


def get_rewrite_mode_labels() -> Dict[str, str]:
    """Map mode id -> human label."""
    return {k: v["label"] for k, v in _load_modes().items()}


def _resolve_mode_key(mode: str) -> str:
    modes = _load_modes()
    system = _load_system()
    default_mode = system.get("default_mode") or "clean_up"
    mode_key = (mode or default_mode).strip()
    if mode_key not in modes:
        mode_key = default_mode if default_mode in modes else next(iter(modes))
    return mode_key


def is_qwen_image_mode(mode: str) -> bool:
    """True for official Qwen-Image rewrite() modes."""
    modes = _load_modes()
    data = modes.get((mode or "").strip()) or {}
    return data.get("kind") == "qwen_image"


def __getattr__(name: str):
    """Lazy dynamic attributes for dropdown lists (re-read JSON on access)."""
    if name == "REWRITE_MODE_CHOICES":
        return get_rewrite_mode_choices()
    if name == "REWRITE_MODE_LABELS":
        return get_rewrite_mode_labels()
    if name == "REWRITE_MODES":
        # legacy shape: id -> (label, instruction)
        return {
            k: (v["label"], v["instruction"]) for k, v in _load_modes().items()
        }
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def build_rewrite_system_prompt(
    mode: str = "clean_up",
    custom_instruction: str = "",
    text: str = "",
) -> str:
    """Build the system prompt for the selected rewrite mode."""
    system = _load_system()
    modes = _load_modes()
    mode_key = _resolve_mode_key(mode)
    mode_data = modes[mode_key]

    # Official image-model optimizers use their own system prompt, not the
    # generic rewriter rules (those would fight "infer and add details").
    if mode_data.get("kind") == "qwen_image":
        sys_txt, _, _ = build_rewrite_messages(
            text,
            str(mode_data.get("language") or "auto"),
        )
        custom = (custom_instruction or "").strip()
        if custom:
            sys_txt = f"{sys_txt}\n\nAdditional user instruction:\n{custom}"
        return sys_txt

    if mode_data.get("kind") == "flux_klein":
        sys_txt, _ = build_flux_klein_messages(
            text,
            edit=bool(mode_data.get("edit")),
        )
        custom = (custom_instruction or "").strip()
        if custom:
            sys_txt = f"{sys_txt}\n\nAdditional user instruction:\n{custom}"
        return sys_txt

    if mode_data.get("kind") == "photography":
        parts = [
            (system.get("photography_base") or "").strip(),
            (system.get("photography_rules") or "").strip(),
            mode_data["instruction"].strip(),
        ]
        custom = (custom_instruction or "").strip()
        if custom:
            parts.append(f"Additional user instruction:\n{custom}")
        return "\n\n".join(p for p in parts if p)

    base = (system.get("base_system") or "").strip()
    rules = (system.get("output_rules") or "").strip()
    parts = [p for p in (base, rules, mode_data["instruction"].strip()) if p]

    custom = (custom_instruction or "").strip()
    if mode_key == "custom":
        if custom:
            parts.append(f"Custom instruction:\n{custom}")
        else:
            # Fall back to clean_up instruction when custom text is empty
            fallback = modes.get("clean_up") or next(iter(modes.values()))
            parts.append(fallback["instruction"].strip())
    elif custom:
        parts.append(
            "Additional user instruction (apply on top of the mode above):\n"
            f"{custom}"
        )

    return "\n\n".join(parts)


def build_rewrite_user_prompt(
    text: str,
    mode: str = "clean_up",
    custom_instruction: str = "",
) -> str:
    """Wrap raw user text in a mode-aware rewrite instruction."""
    system = _load_system()
    modes = _load_modes()
    mode_key = _resolve_mode_key(mode)
    mode_data = modes[mode_key]

    if mode_data.get("kind") == "qwen_image":
        _, user, _ = build_rewrite_messages(
            text,
            str(mode_data.get("language") or "auto"),
        )
        return user

    if mode_data.get("kind") == "flux_klein":
        _, user = build_flux_klein_messages(
            text,
            edit=bool(mode_data.get("edit")),
        )
        return user

    label = mode_data["label"]
    if mode_data.get("kind") == "photography":
        header_tmpl = (
            system.get("photography_user_header")
            or _DEFAULT_SYSTEM["photography_user_header"]
        )
        header = str(header_tmpl).format(label=label)
        custom = (custom_instruction or "").strip()
        if custom:
            header = f"{header}\nAdditional instruction: {custom}"
        template = (
            system.get("user_prompt_template")
            or _DEFAULT_SYSTEM["user_prompt_template"]
        )
        return template.format(header=header, text=text.strip())

    custom = (custom_instruction or "").strip()

    header_lines = [f"Rewrite the following text using mode: {label}."]
    if mode_key == "custom" and custom:
        header_lines.append(f"Custom instruction: {custom}")
    elif mode_key == "clean_up":
        extra = (system.get("clean_up_header_extra") or "").strip()
        if extra:
            header_lines.append(extra)
    elif custom:
        header_lines.append(f"Additional instruction: {custom}")

    header = "\n".join(header_lines)
    template = system.get("user_prompt_template") or _DEFAULT_SYSTEM["user_prompt_template"]
    return template.format(header=header, text=text.strip())


def sanitize_rewritten_text(response: str) -> str:
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
            break

    if len(result) >= 2 and result[0] == result[-1] and result[0] in ('"', "'"):
        result = result[1:-1].strip()

    return result


def finish_rewritten_text(
    response: str,
    mode: str = "clean_up",
    source_text: str = "",
) -> str:
    """Sanitize LLM output and apply mode-specific finishing.

    Qwen-Image modes collapse newlines (official rewrite()) and append the
    Ultra HD / 超清 magic suffix.
    """
    result = sanitize_rewritten_text(response)
    if not result:
        return ""

    modes = _load_modes()
    mode_key = _resolve_mode_key(mode)
    mode_data = modes.get(mode_key) or {}
    if mode_data.get("kind") != "qwen_image":
        return result

    result = re.sub(r"\s+", " ", result).strip()
    lang = resolve_language(source_text, str(mode_data.get("language") or "auto"))
    if mode_data.get("append_magic", True):
        result = append_magic(result, lang, enabled=True)
    return result


def suggested_temperature(mode: str) -> float:
    """Suggested temperature from modes.json (or a safe default)."""
    modes = _load_modes()
    system = _load_system()
    default_mode = system.get("default_mode") or "clean_up"
    m = (mode or default_mode).strip()
    data = modes.get(m) or modes.get(default_mode)
    if not data:
        return 0.4
    try:
        return float(data.get("suggested_temperature", 0.4))
    except (TypeError, ValueError):
        return 0.4
