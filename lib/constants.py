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
)
