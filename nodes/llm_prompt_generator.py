"""Wizdroid Tools - LLM Prompt Generator Node.

Generates image generation prompts via Ollama, with fine-grained control over
spice (SFW↔NSFW), fantasy (realistic↔surreal), and detail levels.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Tuple

from lib.constants import DEFAULT_OLLAMA_URL
from lib.ollama_client import collect_models, generate_text
from lib.prompts import build_system_prompt

logger = logging.getLogger(__name__)


class WizdroidLLMPromptGenerator:
    """Generate image prompts via Ollama with spice/fantasy/detail control.

    This node takes a user's concept description and uses a local Ollama LLM
    to expand it into a rich, well-structured image generation prompt. Three
    sliders fine-tune the content:

    - **Spice** (0–10): From completely SFW to explicit NSFW.
    - **Fantasy** (0–10): From photorealistic to pure surreal fantasy.
    - **Detail** (0–10): From minimalistic to hyper-detailed 8K quality.
    """

    CATEGORY = "🧙 Wizdroid Tools/LLM"
    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("prompt",)
    FUNCTION = "generate"

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
                "user_prompt": (
                    "STRING",
                    {
                        "multiline": True,
                        "default": "",
                        "tooltip": "Describe the image concept you want. The LLM will expand this into a full prompt.",
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
                        "min": 32,
                        "max": 4096,
                        "step": 32,
                        "tooltip": "Maximum tokens the LLM can generate. Higher values allow longer prompts.",
                    },
                ),
            },
            "optional": {
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
        user_prompt: str = "",
        spice: int = 0,
        fantasy: int = 0,
        detail: int = 5,
        temperature: float = 0.7,
        max_tokens: int = 512,
        seed: int = 0,
    ) -> Tuple[str]:
        """Generate an image prompt from the user's input.

        Returns:
            A single-element tuple containing the generated prompt string.
        """
        # --- Validate inputs ---
        user_prompt = (user_prompt or "").strip()
        if not user_prompt:
            return ("Error: user_prompt is empty. Please describe the image you want to generate.",)

        # Clamp slider values
        spice = max(0, min(10, spice))
        fantasy = max(0, min(10, fantasy))
        detail = max(0, min(10, detail))

        # Build the system prompt with slider-driven meta-prompts
        # Target word count derived from max_tokens (roughly 0.75 words per token)
        target_words = max(20, int(max_tokens * 0.75))
        system_prompt = build_system_prompt(
            spice=spice,
            fantasy=fantasy,
            detail=detail,
            max_tokens=target_words,
        )

        logger.debug(
            "Generating prompt: model=%s, spice=%d, fantasy=%d, detail=%d, temp=%.2f, tokens=%d, seed=%d",
            ollama_model, spice, fantasy, detail, temperature, max_tokens, seed,
        )

        # --- Call Ollama ---
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
            return (f"Error: {response}",)

        # Clean up the response — strip any markdown code fences or quotes
        result = response.strip()

        # Remove common markdown code fences some models add despite instructions
        if result.startswith("```"):
            # Find the end of the opening fence
            first_newline = result.find("\n")
            if first_newline != -1:
                result = result[first_newline + 1:]
            if result.endswith("```"):
                result = result[:-3]
            result = result.strip()

        # Remove surrounding quotes if the model wrapped the prompt
        if len(result) >= 2 and result[0] == result[-1] and result[0] in ('"', "'"):
            result = result[1:-1].strip()

        return (result,)


# ---------------------------------------------------------------------------
# Node registration mappings
# ---------------------------------------------------------------------------
NODE_CLASS_MAPPINGS = {
    "WizdroidLLMPromptGenerator": WizdroidLLMPromptGenerator,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "WizdroidLLMPromptGenerator": "🧙 LLM Prompt Generator",
}
