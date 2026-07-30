"""Wizdroid Tools - LLM Text Rewriter Node.

Mode-based text converter (Perchance-style): clean up messy prose, or rewrite
into formal / casual / shorter / pirate / custom styles via Ollama.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Tuple

from lib.constants import DEFAULT_OLLAMA_URL
from lib.ollama_client import collect_models, generate_text
from lib.rewrite_prompts import (
    build_rewrite_system_prompt,
    build_rewrite_user_prompt,
    get_rewrite_mode_choices,
    get_rewrite_mode_labels,
    sanitize_rewritten_text,
)

logger = logging.getLogger(__name__)


class WizdroidLLMTextRewriter:
    """Rewrite or restyle text via Ollama with preset modes + custom instruction.

    Default mode **clean_up** only fixes grammar/spelling/structure (no new content).
    Other modes mirror common converters (formalize, humanize, shorter, pirate, …).
    """

    CATEGORY = "🧙 Wizdroid/LLM"
    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("text",)
    FUNCTION = "rewrite"
    OUTPUT_NODE = False

    @classmethod
    def INPUT_TYPES(cls) -> Dict[str, Any]:
        models = collect_models(DEFAULT_OLLAMA_URL)
        # Reload modes from data/rewrite/modes.json every time the UI asks
        mode_choices = get_rewrite_mode_choices()
        mode_tooltip = (
            "Rewrite style from data/rewrite/modes.json. "
            "clean_up = grammar/clarity only. custom = custom_instruction. "
            "Edit the JSON to add/change modes, then refresh the page."
        )

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
                "text": (
                    "STRING",
                    {
                        "multiline": True,
                        "default": "",
                        "tooltip": "Source text to rewrite or restyle.",
                    },
                ),
                "mode": (
                    mode_choices,
                    {
                        "default": mode_choices[0] if mode_choices else "clean_up",
                        "tooltip": mode_tooltip,
                    },
                ),
                "temperature": (
                    "FLOAT",
                    {
                        "default": 0.2,
                        "min": 0.0,
                        "max": 2.0,
                        "step": 0.05,
                        "tooltip": (
                            "LLM temperature. Low (0.1–0.3) for clean_up/formal; "
                            "raise for fun modes (pirate, drunk, uwu)."
                        ),
                    },
                ),
                "max_tokens": (
                    "INT",
                    {
                        "default": 1024,
                        "min": 64,
                        "max": 8192,
                        "step": 64,
                        "tooltip": "Maximum tokens for output. Raise for longer / way_longer modes.",
                    },
                ),
            },
            "optional": {
                "custom_instruction": (
                    "STRING",
                    {
                        "multiline": True,
                        "default": "",
                        "tooltip": (
                            "Required for mode=custom; optional extra constraint on any mode "
                            "(e.g. 'keep bullet points', 'British English')."
                        ),
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

    def rewrite(
        self,
        ollama_url: str = DEFAULT_OLLAMA_URL,
        ollama_model: str = "",
        text: str = "",
        mode: str = "clean_up",
        temperature: float = 0.2,
        max_tokens: int = 1024,
        custom_instruction: str = "",
        seed: int = 0,
    ) -> Tuple[str]:
        """Rewrite or restyle text according to mode.

        Returns:
            A single-element tuple with the rewritten text string.
        """
        text = (text or "").strip()
        if not text:
            return ("Error: text is empty. Paste the text you want rewritten.",)

        mode = (mode or "clean_up").strip()
        labels = get_rewrite_mode_labels()
        if mode not in labels:
            mode = "clean_up" if "clean_up" in labels else next(iter(labels), "clean_up")

        custom_instruction = (custom_instruction or "").strip()
        if mode == "custom" and not custom_instruction:
            logger.info("mode=custom with empty instruction; falling back to clean_up rules")

        system_prompt = build_rewrite_system_prompt(
            mode=mode,
            custom_instruction=custom_instruction,
        )
        user_prompt = build_rewrite_user_prompt(
            text=text,
            mode=mode,
            custom_instruction=custom_instruction,
        )

        logger.debug(
            "Rewriting text: model=%s mode=%s chars=%d temp=%.2f tokens=%d seed=%d",
            ollama_model,
            mode,
            len(text),
            temperature,
            max_tokens,
            seed,
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
            logger.error("Ollama text rewrite failed: %s", response)
            return (f"Error: {response}",)

        result = sanitize_rewritten_text(response)
        if not result:
            logger.warning("Empty rewrite after sanitize; returning raw response")
            result = (response or "").strip()

        return (result,)


# ---------------------------------------------------------------------------
# Node registration mappings
# ---------------------------------------------------------------------------
NODE_CLASS_MAPPINGS = {
    "WizdroidLLMTextRewriter": WizdroidLLMTextRewriter,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "WizdroidLLMTextRewriter": "🧙 LLM Text Rewriter",
}
