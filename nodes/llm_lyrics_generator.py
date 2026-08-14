"""Wizdroid Tools - LLM Lyrics Generator Node (ACE-Step 1.5).

Generates structured lyrics and comma-separated audio tags via Ollama,
formatted for ACE-Step / ComfyUI TextEncodeAceStepAudio1.5.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Tuple

from lib.constants import DEFAULT_OLLAMA_URL
from lib.lyrics_prompts import (
    build_lyrics_system_prompt,
    build_lyrics_user_prompt,
    get_language_choices,
    get_rhyme_choices,
    get_structure_choices,
    get_vocal_choices,
    parse_lyrics_and_tags,
    resolve_bpm,
    sanitize_lyrics,
    sanitize_tags,
)
from lib.ollama_client import collect_models, generate_text

logger = logging.getLogger(__name__)


class WizdroidLLMLyricsGenerator:
    """Generate ACE-Step lyrics + tags from a song theme via Ollama.

    Outputs plug directly into ComfyUI's ACE-Step 1.5 text encoder:
    - **lyrics**: section markers + short singable lines
    - **tags**: genre/mood/instruments/vocals/production/BPM keywords
    """

    CATEGORY = "🧙 Wizdroid/LLM"
    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("lyrics", "tags")
    FUNCTION = "generate"
    OUTPUT_NODE = False

    @classmethod
    def INPUT_TYPES(cls) -> Dict[str, Any]:
        models = collect_models(DEFAULT_OLLAMA_URL)
        # Dropdowns reloaded from data/lyrics/*.json on each UI query
        structure_choices = get_structure_choices()
        language_choices = get_language_choices()
        vocal_choices = get_vocal_choices()
        rhyme_choices = get_rhyme_choices()
        default_structure = (
            "ballad_folk"
            if "ballad_folk" in structure_choices
            else structure_choices[0]
        )
        default_vocal = (
            "soft female vocals"
            if "soft female vocals" in vocal_choices
            else vocal_choices[0]
        )
        default_rhyme = "AABB" if "AABB" in rhyme_choices else rhyme_choices[0]
        default_lang = "en" if "en" in language_choices else language_choices[0]

        return {
            "required": {
                "ollama_url": (
                    "STRING",
                    {
                        "default": DEFAULT_OLLAMA_URL,
                        "tooltip": "Ollama server URL. Default: http://localhost:11434",
                    },
                ),
                "ollama_model": (
                    models,
                    {
                        "default": models[0] if models else "no_models_found",
                        "tooltip": "Select an Ollama model. Refresh the page if you added new models.",
                    },
                ),
                "theme": (
                    "STRING",
                    {
                        "multiline": True,
                        "default": "late-night city rain, missing someone on the last train home",
                        "tooltip": "What the song is about — story, mood, images, or a short brief.",
                    },
                ),
                "genre": (
                    "STRING",
                    {
                        "default": "chamber folk",
                        "tooltip": "Primary genre for tags (e.g. lo-fi hip-hop, progressive techno, synth-pop).",
                    },
                ),
                "mood": (
                    "STRING",
                    {
                        "default": "melancholic, intimate, hopeful",
                        "tooltip": "Mood keywords for tags and lyric tone.",
                    },
                ),
                "structure": (
                    structure_choices,
                    {
                        "default": default_structure,
                        "tooltip": (
                            "Song section layout from data/lyrics/structures.json. "
                            "Edit that file to add templates, then refresh the page."
                        ),
                    },
                ),
                "language": (
                    language_choices,
                    {
                        "default": default_lang,
                        "tooltip": (
                            "Language marker from data/lyrics/choices.json. "
                            "'none' skips markers."
                        ),
                    },
                ),
                "vocal_type": (
                    vocal_choices,
                    {
                        "default": default_vocal,
                        "tooltip": (
                            "Vocal style from data/lyrics/choices.json. "
                            "Use 'no vocals' for instrumental."
                        ),
                    },
                ),
                "instrumental": (
                    "BOOLEAN",
                    {
                        "default": False,
                        "tooltip": "If true, lyrics are section markers only (no sung words) and tags include no vocals.",
                    },
                ),
                "bpm": (
                    "INT",
                    {
                        "default": 0,
                        "min": 0,
                        "max": 220,
                        "step": 1,
                        "tooltip": "Target BPM written into tags. 0 = pick a sensible default for the structure.",
                    },
                ),
                "rhyme": (
                    rhyme_choices,
                    {
                        "default": default_rhyme,
                        "tooltip": "Preferred rhyme scheme (data/lyrics/choices.json).",
                    },
                ),
                "temperature": (
                    "FLOAT",
                    {
                        "default": 0.7,
                        "min": 0.0,
                        "max": 2.0,
                        "step": 0.05,
                        "tooltip": "LLM temperature. Lower = more predictable structure; higher = more creative lyrics.",
                    },
                ),
                "max_tokens": (
                    "INT",
                    {
                        "default": 1024,
                        "min": 128,
                        "max": 4096,
                        "step": 64,
                        "tooltip": "Maximum tokens the LLM can generate for lyrics + tags.",
                    },
                ),
            },
            "optional": {
                "custom_sections": (
                    "STRING",
                    {
                        "multiline": True,
                        "default": "",
                        "tooltip": "Used when structure=custom. One marker per line, e.g. [intro]\\n[verse]\\n[chorus].",
                    },
                ),
                "extra_instructions": (
                    "STRING",
                    {
                        "multiline": True,
                        "default": "",
                        "tooltip": "Optional constraints (hook line, forbidden words, names to include, etc.).",
                    },
                ),
                "seed": (
                    "INT",
                    {
                        "default": 0,
                        "min": 0,
                        "max": 0xFFFFFFFFFFFFFFFF,
                        "tooltip": "Seed for reproducible results. 0 = random.",
                    },
                ),
            },
        }

    def generate(
        self,
        ollama_url: str = DEFAULT_OLLAMA_URL,
        ollama_model: str = "",
        theme: str = "",
        genre: str = "",
        mood: str = "",
        structure: str = "ballad_folk",
        language: str = "en",
        vocal_type: str = "soft female vocals",
        instrumental: bool = False,
        bpm: int = 0,
        rhyme: str = "AABB",
        temperature: float = 0.7,
        max_tokens: int = 1024,
        custom_sections: str = "",
        extra_instructions: str = "",
        seed: int = 0,
    ) -> Tuple[str, str]:
        """Generate ACE-Step lyrics and tags.

        Returns:
            (lyrics, tags) string pair for TextEncodeAceStepAudio1.5.
        """
        theme = (theme or "").strip()
        if not theme:
            err = "Error: theme is empty. Describe what the song should be about."
            return (err, "")

        # Instrumental override when vocal_type is no vocals
        if (vocal_type or "").strip().lower() in ("no vocals", "instrumental"):
            instrumental = True

        resolved_bpm = resolve_bpm(bpm, structure)

        system_prompt = build_lyrics_system_prompt(
            structure_name=structure,
            custom_sections=custom_sections or "",
            language=language,
            genre=genre or "",
            mood=mood or "",
            vocal_type=vocal_type,
            instrumental=instrumental,
            bpm=resolved_bpm,
            rhyme=rhyme,
        )
        user_prompt = build_lyrics_user_prompt(
            theme=theme,
            structure_name=structure,
            language=language,
            genre=genre or "",
            mood=mood or "",
            vocal_type=vocal_type,
            instrumental=instrumental,
            bpm=resolved_bpm,
            extra_instructions=extra_instructions or "",
        )

        logger.debug(
            "Generating lyrics: model=%s structure=%s lang=%s bpm=%d instrumental=%s temp=%.2f",
            ollama_model, structure, language, resolved_bpm, instrumental, temperature,
        )

        ok, response = generate_text(
            ollama_url=ollama_url,
            model=ollama_model,
            system=system_prompt,
            prompt=user_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
            seed=seed,
            timeout=180,
        )

        if not ok:
            logger.error("Ollama lyrics generation failed: %s", response)
            return (f"Error: {response}", "")

        lyrics_raw, tags_raw = parse_lyrics_and_tags(response)
        lyrics = sanitize_lyrics(lyrics_raw)
        tags = sanitize_tags(tags_raw, bpm=resolved_bpm)

        # If tags missing but generation succeeded, build a minimal fallback from inputs
        if not tags:
            tag_bits = [
                genre.strip() if genre else None,
                mood.strip() if mood else None,
                None if instrumental else vocal_type,
                "no vocals" if instrumental else None,
                "instrumental" if instrumental else None,
                f"{resolved_bpm} bpm",
            ]
            tags = sanitize_tags(
                ", ".join(t for t in tag_bits if t),
                bpm=resolved_bpm,
            )

        if not lyrics:
            logger.warning("Empty lyrics after parse; returning raw response as lyrics")
            lyrics = sanitize_lyrics(response)

        return (lyrics, tags)


# ---------------------------------------------------------------------------
# Node registration mappings
# ---------------------------------------------------------------------------
NODE_CLASS_MAPPINGS = {
    "WizdroidLLMLyricsGenerator": WizdroidLLMLyricsGenerator,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "WizdroidLLMLyricsGenerator": "🧙 Lyrics Generator (ACE-Step)",
}
