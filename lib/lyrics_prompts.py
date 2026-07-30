"""ACE-Step lyrics + tags meta-prompts — loaded from data/lyrics/*.json.

Edit JSON under data/lyrics/ to customize structures, dropdown choices, and
system/user prompt templates without touching Python.

Files:
  data/lyrics/structures.json  — structure_name -> [section markers]
  data/lyrics/choices.json     — languages, vocals, rhymes, BPM defaults, guidance
  data/lyrics/system.json      — system_prompt_template, user_prompt_template
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence

from lib.json_data import load_data_json

# ---------------------------------------------------------------------------
# Minimal fallbacks if JSON is missing/corrupt
# ---------------------------------------------------------------------------
_FALLBACK_STRUCTURES: Dict[str, List[str]] = {
    "pop": [
        "[intro]", "[verse]", "[pre-chorus]", "[chorus]",
        "[verse]", "[pre-chorus]", "[chorus]", "[bridge]", "[chorus]", "[outro]",
    ],
    "minimal": ["[verse]", "[chorus]", "[verse]", "[chorus]", "[outro]"],
}

_FALLBACK_CHOICES: Dict[str, Any] = {
    "languages": ["en", "none"],
    "vocals": ["soft female vocals", "soft male vocals", "no vocals"],
    "rhymes": ["AABB", "ABAB", "loose", "free_verse"],
    "default_bpm_by_structure": {"pop": 110, "minimal": 100, "custom": 100},
    "rhyme_guidance": {
        "AABB": "prefer AABB end-rhyme within sections",
        "ABAB": "prefer ABAB end-rhyme within sections",
        "loose": "loose/occasional rhyme is fine",
        "free_verse": "free verse is OK; prioritize rhythm and singability over rhyme",
        "_default": "prefer AABB end-rhyme within sections",
    },
    "language_guidance": {
        "none": (
            "Do not add language markers. Write lyrics in the language of the theme "
            "(default English if unclear)."
        ),
        "with_marker": (
            "Place the language marker [{lang}] on its own line at the START of each "
            "sung section (verse/chorus/bridge/pre-chorus), never mid-line. "
            "Write the lyric text in that language."
        ),
    },
    "mode_guidance": {
        "instrumental": (
            "INSTRUMENTAL MODE: lyrics body must contain ONLY section markers "
            "(and blank lines). No sung words at all. Tags must include 'no vocals'."
        ),
        "vocal": (
            "VOCAL MODE: write short sung lines under [verse], [pre-chorus], [chorus], "
            "[bridge]. Leave instrumental markers empty unless a short outro line helps."
        ),
    },
}

_FALLBACK_SYSTEM: Dict[str, str] = {
    "system_prompt_template": (
        "You write ACE-Step lyrics and tags.\n"
        "Output ONLY:\n===LYRICS===\n...\n===TAGS===\n...\n"
        "Structure:\n{structure_block}\n"
        "Rhyme: {rhyme_guidance}\nLanguage: {language_guidance}\n"
        "Mode: {mode_guidance}\nBPM: {bpm}\nGenre: {genre}\nMood: {mood}\n"
        "Vocals: {vocal_type}\n"
    ),
    "user_prompt_template": (
        "Theme:\n{theme}\n\n{extra_block}"
        "Genre: {genre}\nMood: {mood}\nBPM: {bpm}\n"
        "Structure: {structure_name}\nLanguage: {language}\n"
        "Vocals: {vocal_type}\nInstrumental: {instrumental}\n"
    ),
}


def _load_structures() -> Dict[str, List[str]]:
    data = load_data_json("lyrics", "structures.json", default=None)
    if not isinstance(data, dict) or not data:
        return {k: list(v) for k, v in _FALLBACK_STRUCTURES.items()}
    out: Dict[str, List[str]] = {}
    for name, sections in data.items():
        if isinstance(sections, list) and sections:
            out[str(name)] = [str(s) for s in sections]
    return out or {k: list(v) for k, v in _FALLBACK_STRUCTURES.items()}


def _load_choices() -> Dict[str, Any]:
    data = load_data_json("lyrics", "choices.json", default=None)
    if not isinstance(data, dict):
        return dict(_FALLBACK_CHOICES)
    merged = dict(_FALLBACK_CHOICES)
    merged.update(data)
    return merged


def _load_system() -> Dict[str, str]:
    data = load_data_json("lyrics", "system.json", default=None)
    if not isinstance(data, dict):
        return dict(_FALLBACK_SYSTEM)
    merged = dict(_FALLBACK_SYSTEM)
    merged.update({k: str(v) for k, v in data.items()})
    return merged


def get_structure_templates() -> Dict[str, List[str]]:
    return _load_structures()


def get_structure_choices() -> List[str]:
    return list(_load_structures().keys()) + ["custom"]


def get_language_choices() -> List[str]:
    langs = _load_choices().get("languages") or _FALLBACK_CHOICES["languages"]
    return [str(x) for x in langs]


def get_vocal_choices() -> List[str]:
    vocals = _load_choices().get("vocals") or _FALLBACK_CHOICES["vocals"]
    return [str(x) for x in vocals]


def get_rhyme_choices() -> List[str]:
    rhymes = _load_choices().get("rhymes") or _FALLBACK_CHOICES["rhymes"]
    return [str(x) for x in rhymes]


def __getattr__(name: str):
    """Dynamic module attrs so existing imports keep working."""
    if name == "STRUCTURE_TEMPLATES":
        return get_structure_templates()
    if name == "STRUCTURE_CHOICES":
        return get_structure_choices()
    if name == "LANGUAGE_CHOICES":
        return get_language_choices()
    if name == "VOCAL_CHOICES":
        return get_vocal_choices()
    if name == "RHYME_CHOICES":
        return get_rhyme_choices()
    if name == "DEFAULT_BPM_BY_STRUCTURE":
        choices = _load_choices()
        bpm = choices.get("default_bpm_by_structure") or {}
        return {str(k): int(v) for k, v in bpm.items()}
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def _structure_block(structure_name: str, custom_sections: str = "") -> str:
    templates = _load_structures()
    if structure_name == "custom" and custom_sections.strip():
        lines = [ln.strip() for ln in custom_sections.splitlines() if ln.strip()]
        if not lines:
            lines = templates.get("pop") or next(iter(templates.values()))
    else:
        lines = templates.get(structure_name) or templates.get("pop") or next(
            iter(templates.values())
        )
    return "\n".join(lines)


def _language_guidance(language: str) -> str:
    choices = _load_choices()
    guidance = choices.get("language_guidance") or _FALLBACK_CHOICES["language_guidance"]
    lang = (language or "en").strip().lower()
    if lang in ("", "none", "unknown"):
        return str(guidance.get("none") or _FALLBACK_CHOICES["language_guidance"]["none"])
    template = str(
        guidance.get("with_marker")
        or _FALLBACK_CHOICES["language_guidance"]["with_marker"]
    )
    return template.format(lang=lang)


def _mode_guidance(instrumental: bool, vocal_type: str) -> str:
    choices = _load_choices()
    guidance = choices.get("mode_guidance") or _FALLBACK_CHOICES["mode_guidance"]
    if instrumental or vocal_type.strip().lower() in ("no vocals", "instrumental"):
        return str(guidance.get("instrumental") or _FALLBACK_CHOICES["mode_guidance"]["instrumental"])
    return str(guidance.get("vocal") or _FALLBACK_CHOICES["mode_guidance"]["vocal"])


def _rhyme_guidance(rhyme: str) -> str:
    choices = _load_choices()
    guidance = choices.get("rhyme_guidance") or _FALLBACK_CHOICES["rhyme_guidance"]
    r = (rhyme or "AABB").strip()
    if r in guidance:
        return str(guidance[r])
    return str(guidance.get("_default") or _FALLBACK_CHOICES["rhyme_guidance"]["_default"])


def resolve_bpm(bpm: int, structure_name: str) -> int:
    """Return a usable BPM; 0 means pick a structure default."""
    if bpm and bpm > 0:
        return max(40, min(220, int(bpm)))
    choices = _load_choices()
    defaults = choices.get("default_bpm_by_structure") or {}
    try:
        return int(defaults.get(structure_name, defaults.get("custom", 100)))
    except (TypeError, ValueError):
        return 100


def build_lyrics_system_prompt(
    *,
    structure_name: str = "pop",
    custom_sections: str = "",
    language: str = "en",
    genre: str = "",
    mood: str = "",
    vocal_type: str = "soft female vocals",
    instrumental: bool = False,
    bpm: int = 0,
    rhyme: str = "AABB",
) -> str:
    """Build the ACE-Step lyrics+tags system prompt."""
    templates = _load_structures()
    system = _load_system()
    if structure_name != "custom" and structure_name not in templates:
        structure_name = "pop" if "pop" in templates else next(iter(templates))
    resolved_bpm = resolve_bpm(bpm, structure_name)
    template = system.get("system_prompt_template") or _FALLBACK_SYSTEM["system_prompt_template"]
    return template.format(
        rhyme_guidance=_rhyme_guidance(rhyme),
        language_guidance=_language_guidance(language),
        mode_guidance=_mode_guidance(instrumental, vocal_type),
        structure_block=_structure_block(structure_name, custom_sections),
        bpm=resolved_bpm,
        genre=genre.strip() or "unspecified (infer from theme)",
        mood=mood.strip() or "unspecified (infer from theme)",
        vocal_type="no vocals" if instrumental else vocal_type,
    )


def build_lyrics_user_prompt(
    *,
    theme: str,
    structure_name: str = "pop",
    language: str = "en",
    genre: str = "",
    mood: str = "",
    vocal_type: str = "soft female vocals",
    instrumental: bool = False,
    bpm: int = 0,
    extra_instructions: str = "",
) -> str:
    """Build the user message for ACE-Step lyrics+tags generation."""
    system = _load_system()
    resolved_bpm = resolve_bpm(bpm, structure_name)
    extra = (extra_instructions or "").strip()
    extra_block = f"Extra instructions:\n{extra}\n" if extra else ""
    template = system.get("user_prompt_template") or _FALLBACK_SYSTEM["user_prompt_template"]
    return template.format(
        theme=theme.strip(),
        extra_block=extra_block,
        genre=genre.strip() or "(infer)",
        mood=mood.strip() or "(infer)",
        bpm=resolved_bpm,
        structure_name=structure_name,
        language=language,
        vocal_type="no vocals" if instrumental else vocal_type,
        instrumental="yes" if instrumental else "no",
    )


def _normalize_tag_block(block: str) -> str:
    """Collapse a multi-line tags block into a clean comma-separated list."""
    if not block:
        return ""
    chunks: List[str] = []
    for line in block.splitlines():
        line = line.strip()
        if not line:
            continue
        chunks.append(line)
    joined = ", ".join(chunks)
    return ", ".join(part.strip() for part in joined.split(",") if part.strip())


def parse_lyrics_and_tags(raw: str) -> tuple[str, str]:
    """Extract lyrics and tags from model output."""
    text = (raw or "").strip()
    if not text:
        return "", ""

    if text.startswith("```"):
        first_nl = text.find("\n")
        if first_nl != -1:
            text = text[first_nl + 1 :]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()

    upper = text.upper()
    lyrics_mark = "===LYRICS==="
    tags_mark = "===TAGS==="

    li = upper.find(lyrics_mark)
    ti = upper.find(tags_mark)

    if li != -1 and ti != -1 and ti > li:
        lyrics = text[li + len(lyrics_mark) : ti].strip()
        tags = _normalize_tag_block(text[ti + len(tags_mark) :])
        return lyrics.strip(), tags

    if ti != -1 and li == -1:
        lyrics = text[:ti].strip()
        tags = _normalize_tag_block(text[ti + len(tags_mark) :])
        return lyrics, tags

    if li != -1 and ti == -1:
        return text[li + len(lyrics_mark) :].strip(), ""

    lines = text.splitlines()
    has_markers = any(
        ln.strip().lower()
        in {
            "[intro]",
            "[verse]",
            "[pre-chorus]",
            "[chorus]",
            "[bridge]",
            "[inst]",
            "[build-up]",
            "[drop]",
            "[breakdown]",
            "[outro]",
        }
        or ln.strip().lower().startswith("[verse")
        or ln.strip().lower().startswith("[chorus")
        for ln in lines
    )
    if has_markers and lines:
        for idx in range(len(lines) - 1, -1, -1):
            candidate = lines[idx].strip()
            if (
                candidate
                and "[" not in candidate
                and candidate.count(",") >= 3
                and "bpm" in candidate.lower()
            ):
                lyrics = "\n".join(lines[:idx]).strip()
                tags = ", ".join(p.strip() for p in candidate.split(",") if p.strip())
                return lyrics, tags
        return text.strip(), ""

    if text.count(",") >= 3 and "\n" not in text.strip():
        return "", ", ".join(p.strip() for p in text.split(",") if p.strip())

    return text.strip(), ""


def sanitize_lyrics(lyrics: str) -> str:
    """Normalize lyrics: strip chat fluff, keep markers lowercase."""
    if not lyrics:
        return ""

    text = lyrics.strip()
    for prefix in (
        "here are the lyrics:",
        "here is the lyrics:",
        "lyrics:",
        "sure,",
        "sure!",
    ):
        low = text.lower()
        if low.startswith(prefix):
            text = text[len(prefix) :].strip()

    known = (
        "intro",
        "verse",
        "pre-chorus",
        "prechorus",
        "chorus",
        "bridge",
        "inst",
        "instrumental",
        "build-up",
        "buildup",
        "drop",
        "breakdown",
        "outro",
    )
    out_lines: List[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            if out_lines and out_lines[-1] != "":
                out_lines.append("")
            continue
        if stripped.startswith("[") and stripped.endswith("]") and len(stripped) <= 24:
            inner = stripped[1:-1].strip().lower().replace(" ", "-")
            if inner == "prechorus":
                inner = "pre-chorus"
            if inner == "buildup":
                inner = "build-up"
            if inner == "instrumental":
                inner = "inst"
            if inner in known or inner.startswith("verse") or inner.startswith("chorus"):
                out_lines.append(f"[{inner}]")
                continue
        out_lines.append(stripped)

    while out_lines and out_lines[0] == "":
        out_lines.pop(0)
    while out_lines and out_lines[-1] == "":
        out_lines.pop()
    return "\n".join(out_lines)


def sanitize_tags(tags: str, bpm: Optional[int] = None) -> str:
    """Normalize tags list; ensure bpm keyword present when provided."""
    if not tags:
        tags = ""
    parts = [p.strip() for p in tags.replace("\n", ",").split(",") if p.strip()]
    seen = set()
    unique: List[str] = []
    for p in parts:
        key = p.lower()
        if key in seen:
            continue
        seen.add(key)
        unique.append(p)

    if bpm and bpm > 0:
        has_bpm = any("bpm" in p.lower() for p in unique)
        if not has_bpm:
            unique.append(f"{bpm} bpm")
        else:
            fixed: List[str] = []
            for p in unique:
                if "bpm" in p.lower():
                    fixed.append(f"{bpm} bpm")
                else:
                    fixed.append(p)
            unique = fixed

    if len(unique) > 15:
        bpm_parts = [p for p in unique if "bpm" in p.lower()]
        core = [p for p in unique if "bpm" not in p.lower()][:14]
        unique = core + bpm_parts[:1]

    return ", ".join(unique)



