"""Shared constants for comfyui-wizdroid-tools."""

from __future__ import annotations

# Default Ollama URL
DEFAULT_OLLAMA_URL = "http://localhost:11434"

# Thinking model name prefixes (models that support /api/generate "think" option)
THINKING_MODEL_PREFIXES = (
    "gemma",
    "qwen",
    "deepseek-r1",
    "qwq",
    "openthinking",
    "deepseek",
    "phi4",
    "glm",
    "kimi",
    "nemotron",
    "marco-o1",
    "granite4",
    "exaone-deep",
    "internlm3",
)

# Vision-language (multimodal) model name markers, used as a fallback when the
# Ollama server does not report ``details.capabilities`` in /api/tags.
VISION_MODEL_PREFIXES = (
    "llava",
    "bakllava",
    "moondream",
    "qwen-vl",
    "qwen2-vl",
    "qwen2.5-vl",
    "qwen3-vl",
    "minicpm-v",
    "gemma3",
    "llama3.2-vision",
    "phi3-vision",
    "phi3.5-vision",
    "phi4-multimodal",
    "granite3.2-vision",
    "granite4-vision",
    "internvl",
    "cogvlm",
    "deepseek-vl",
    "paligemma",
    "smolvlm",
    "nanollava",
    "mobile-vlm",
)
