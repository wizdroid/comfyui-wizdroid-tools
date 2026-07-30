"""ComfyUI Wizdroid Tools - Clean, powerful utility nodes for ComfyUI.

Includes:
- LLM Prompt Generator: Generate image prompts via Ollama with fine-grained
  control over spice, fantasy, and detail levels.
- Character Prompt Generator: Build a character via dropdowns, then generate
  an image prompt via Ollama or a plain template.
- LLM Lyrics Generator: ACE-Step 1.5 structured lyrics + tags via Ollama.
- LLM Text Rewriter: Mode-based rewrite (clean-up, formalize, humanize, pirate,
  custom instruction, …) via Ollama.
"""

__version__ = "2026.07.30"

import sys
from pathlib import Path

# Ensure the package root is on sys.path for 'from lib.xxx' imports
_BASE_DIR = Path(__file__).resolve().parent
_BASE_DIR_STR = str(_BASE_DIR)
if _BASE_DIR_STR not in sys.path:
    sys.path.insert(0, _BASE_DIR_STR)

import importlib
import importlib.util

# Web directory for custom node UI resources
WEB_DIRECTORY = "./web"


def _import_node_module(module_basename: str):
    """Import a node module from the nodes/ directory.

    Handles both normal package imports (ComfyUI) and standalone imports
    (testing / development).
    """
    if __package__:
        try:
            return importlib.import_module(
                f".nodes.{module_basename}", package=__package__
            )
        except Exception:
            pass

    file_path = (_BASE_DIR / "nodes" / f"{module_basename}.py").resolve()
    module_name = f"comfyui_wizdroid_tools.nodes.{module_basename}"
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not import {module_basename} from {file_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


# ---------------------------------------------------------------------------
# Import node modules
# ---------------------------------------------------------------------------

_llm_nodes = _import_node_module("llm_prompt_generator")
LLM_NODE_CLASS_MAPPINGS = _llm_nodes.NODE_CLASS_MAPPINGS
LLM_DISPLAY_NAME_MAPPINGS = _llm_nodes.NODE_DISPLAY_NAME_MAPPINGS

_lyrics_nodes = _import_node_module("llm_lyrics_generator")
LYRICS_NODE_CLASS_MAPPINGS = _lyrics_nodes.NODE_CLASS_MAPPINGS
LYRICS_DISPLAY_NAME_MAPPINGS = _lyrics_nodes.NODE_DISPLAY_NAME_MAPPINGS

_rewrite_nodes = _import_node_module("llm_text_rewriter")
REWRITE_NODE_CLASS_MAPPINGS = _rewrite_nodes.NODE_CLASS_MAPPINGS
REWRITE_DISPLAY_NAME_MAPPINGS = _rewrite_nodes.NODE_DISPLAY_NAME_MAPPINGS

_character_nodes = _import_node_module("llm_character_prompt")
CHARACTER_NODE_CLASS_MAPPINGS = _character_nodes.NODE_CLASS_MAPPINGS
CHARACTER_DISPLAY_NAME_MAPPINGS = _character_nodes.NODE_DISPLAY_NAME_MAPPINGS

# ---------------------------------------------------------------------------
# Combined mappings for ComfyUI
# ---------------------------------------------------------------------------

NODE_CLASS_MAPPINGS = {
    **LLM_NODE_CLASS_MAPPINGS,
    **LYRICS_NODE_CLASS_MAPPINGS,
    **REWRITE_NODE_CLASS_MAPPINGS,
    **CHARACTER_NODE_CLASS_MAPPINGS,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    **LLM_DISPLAY_NAME_MAPPINGS,
    **LYRICS_DISPLAY_NAME_MAPPINGS,
    **REWRITE_DISPLAY_NAME_MAPPINGS,
    **CHARACTER_DISPLAY_NAME_MAPPINGS,
}
