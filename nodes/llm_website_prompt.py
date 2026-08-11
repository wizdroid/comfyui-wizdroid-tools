"""Wizdroid Tools - LLM Prompt from Website Node.

Fetch a web page (e.g. a character's bio / lore page), extract its readable
text, and ask a local Ollama LLM to turn that into a detailed image prompt
for the character — using the same spice / fantasy / detail meta-prompts as
the LLM Prompt Generator.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Tuple

from lib.constants import DEFAULT_OLLAMA_URL
from lib.ollama_client import collect_models, generate_text
from lib.web_text import fetch_page_text
from lib.website_prompts import (
    build_website_system_prompt,
    build_website_user_prompt,
    sanitize_prompt,
)

logger = logging.getLogger(__name__)


class WizdroidLLMWebsitePrompt:
    """Extract info from a website and generate a character image prompt.

    Pipeline: URL → readable page text (og:title / og:description + body)
    → Ollama meta-prompt → a single-paragraph image prompt for the character.
    """

    CATEGORY = "🧙 Wizdroid/LLM"
    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("prompt", "website_text")
    FUNCTION = "generate"
    OUTPUT_NODE = False
    DESCRIPTION = (
        "Fetch a website, extract its readable text, and generate a character "
        "image prompt via Ollama. Returns the prompt plus the extracted text."
    )

    @classmethod
    def INPUT_TYPES(cls) -> Dict[str, Any]:
        models = collect_models(DEFAULT_OLLAMA_URL)

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
                "url": (
                    "STRING",
                    {
                        "default": "",
                        "multiline": False,
                        "tooltip": (
                            "Website URL describing a character (bio, lore, wiki, "
                            "character page…). Its readable text is extracted and "
                            "passed to Ollama."
                        ),
                    },
                ),
                "max_chars": (
                    "INT",
                    {
                        "default": 4000,
                        "min": 500,
                        "max": 20000,
                        "step": 500,
                        "tooltip": (
                            "Cap on the number of characters of extracted page "
                            "text sent to the LLM."
                        ),
                    },
                ),
                "spice": (
                    "INT",
                    {
                        "default": 0,
                        "min": 0,
                        "max": 10,
                        "step": 1,
                        "tooltip": "0 = completely SFW, 10 = explicit NSFW",
                    },
                ),
                "fantasy": (
                    "INT",
                    {
                        "default": 0,
                        "min": 0,
                        "max": 10,
                        "step": 1,
                        "tooltip": "0 = photorealistic, 10 = pure surreal fantasy",
                    },
                ),
                "detail": (
                    "INT",
                    {
                        "default": 5,
                        "min": 0,
                        "max": 10,
                        "step": 1,
                        "tooltip": "0 = minimalistic, 10 = hyper-detailed 8K quality",
                    },
                ),
                "temperature": (
                    "FLOAT",
                    {
                        "default": 0.7,
                        "min": 0.0,
                        "max": 2.0,
                        "step": 0.05,
                        "tooltip": "LLM temperature. Lower = more predictable, higher = more creative.",
                    },
                ),
                "max_tokens": (
                    "INT",
                    {
                        "default": 512,
                        "min": 64,
                        "max": 2048,
                        "step": 32,
                        "tooltip": "Maximum tokens the LLM can generate.",
                    },
                ),
            },
            "optional": {
                "seed": (
                    "INT",
                    {
                        "default": 0,
                        "min": 0,
                        "max": 0xFFFFFFFF,
                        "tooltip": "Seed for reproducible results. 0 = random.",
                    },
                ),
                "referer": (
                    "STRING",
                    {
                        "default": "",
                        "multiline": False,
                        "tooltip": (
                            "Optional HTTP Referer header for sites with basic "
                            "hotlink/bot protection."
                        ),
                    },
                ),
            },
        }

    def generate(
        self,
        ollama_url: str = DEFAULT_OLLAMA_URL,
        ollama_model: str = "",
        url: str = "",
        max_chars: int = 4000,
        spice: int = 0,
        fantasy: int = 0,
        detail: int = 5,
        temperature: float = 0.7,
        max_tokens: int = 512,
        seed: int = 0,
        referer: str = "",
    ) -> Tuple[str, str]:
        """Fetch the page, extract text, and generate a character prompt.

        Returns:
            (prompt, website_text)
        """
        url = (url or "").strip()
        if not url:
            return (
                "Error: url is empty. Provide a website URL describing a character.",
                "",
            )

        # --- 1. Fetch + extract readable text ---
        try:
            text, final_url, title, description = fetch_page_text(
                url,
                max_chars=max_chars,
                referer=referer,
            )
        except Exception as exc:  # noqa: BLE001 - surface fetch errors to the user
            logger.error("Failed to fetch %s: %s", url, exc)
            return (f"Error fetching page: {exc}", "")

        if not text:
            return (
                (
                    "Error: no readable text found on the page. "
                    "It may be a JS-rendered page — try a URL with an "
                    "og:description, or use a static page."
                ),
                "",
            )

        logger.debug("Extracted %d chars from %s", len(text), final_url)

        # --- 2. Build meta-prompts ---
        target_words = max(20, int(max_tokens * 0.75))
        system_prompt = build_website_system_prompt(
            spice=spice,
            fantasy=fantasy,
            detail=detail,
            max_tokens=target_words,
        )
        user_prompt = build_website_user_prompt(text)

        # --- 3. Call Ollama ---
        ok, response = generate_text(
            ollama_url=ollama_url,
            model=ollama_model,
            system=system_prompt,
            prompt=user_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
            seed=seed,
            timeout=120,
        )

        if not ok:
            logger.error("Ollama generation failed: %s", response)
            return (f"Error: {response}", text)

        result = sanitize_prompt(response)
        if not result:
            return ("Error: Ollama returned an empty prompt.", text)

        return (result, text)


# ---------------------------------------------------------------------------
# Node registration mappings
# ---------------------------------------------------------------------------
NODE_CLASS_MAPPINGS = {
    "WizdroidLLMWebsitePrompt": WizdroidLLMWebsitePrompt,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "WizdroidLLMWebsitePrompt": "🧙 LLM Prompt from Website",
}
