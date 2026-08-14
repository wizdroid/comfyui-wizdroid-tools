"""ComfyUI Wizdroid Tools - Clean, powerful utility nodes for ComfyUI.

Includes:
- LLM Prompt Generator: Generate image prompts via Ollama with fine-grained
  control over spice, fantasy, and detail levels.
- LLM Prompt from Website: fetch a web page, extract its text, and generate a
  character image prompt via Ollama from that source material.
- Batch Image Captioner: caption every image in a folder (VL model) and write
  <name>.txt caption files for LoRA dataset training.
- Image Critique: VL critique of a generated image → critique + revised prompt.
- Image Prompt Refiner: iterative prompt refinement (optional VL reference
  image + in-session memory).
- Character Prompt Generator: Build a character via dropdowns, then generate
  an image prompt via Ollama or a plain template.
- LLM Lyrics Generator: ACE-Step 1.5 structured lyrics + tags via Ollama.
- LLM Text Rewriter: Mode-based rewrite (clean-up, formalize, humanize, pirate,
  custom instruction, …) via Ollama.
- Qwen Multi-Angles LoRA Prompt: Non-AI utility that builds the proper
  ``<sks>`` prompt string for the fal/Qwen-Image-Edit-2511-Multiple-Angles-LoRA
  (96 camera poses).
- LLM / VL Video Scene Generators: timed scene + dialogue + keyframe prompt
  for video pipelines (text-only or vision-language from a source image).
- VL Image Extract: vision-language reverse of a source image into a prompt,
  outfit flatlay, makeup description, or other selectable extract mode
  (spice-aware NSFW).
- Presets: a single ``🧙 Preset`` node browses data-driven catalogs
  (footwear, headgear, makeup, …) organized into category folders under
  ``data/presets/`` (parts/, sets/female, sets/male, sets/unisex). Drop a
  new JSON into a category folder and refresh ComfyUI — no Python edits.
"""

__version__ = "2026.08.11"

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

_qwen_multi_angles = _import_node_module("llm_qwen_multi_angles")
QWEN_MULTI_ANGLES_CLASS_MAPPINGS = _qwen_multi_angles.NODE_CLASS_MAPPINGS
QWEN_MULTI_ANGLES_DISPLAY_NAME_MAPPINGS = _qwen_multi_angles.NODE_DISPLAY_NAME_MAPPINGS

_scene_nodes = _import_node_module("llm_scene_generator")
SCENE_NODE_CLASS_MAPPINGS = _scene_nodes.NODE_CLASS_MAPPINGS
SCENE_DISPLAY_NAME_MAPPINGS = _scene_nodes.NODE_DISPLAY_NAME_MAPPINGS

_vl_scene_nodes = _import_node_module("llm_vl_scene_generator")
VL_SCENE_NODE_CLASS_MAPPINGS = _vl_scene_nodes.NODE_CLASS_MAPPINGS
VL_SCENE_DISPLAY_NAME_MAPPINGS = _vl_scene_nodes.NODE_DISPLAY_NAME_MAPPINGS

_vl_extract_nodes = _import_node_module("llm_vl_extract")
VL_EXTRACT_NODE_CLASS_MAPPINGS = _vl_extract_nodes.NODE_CLASS_MAPPINGS
VL_EXTRACT_DISPLAY_NAME_MAPPINGS = _vl_extract_nodes.NODE_DISPLAY_NAME_MAPPINGS

# Preset nodes are data-driven: one node class per data/presets/*.json file.
_preset_nodes = _import_node_module("preset_nodes")
PRESET_NODE_CLASS_MAPPINGS = _preset_nodes.NODE_CLASS_MAPPINGS
PRESET_NODE_DISPLAY_NAME_MAPPINGS = _preset_nodes.NODE_DISPLAY_NAME_MAPPINGS

# Load image from a web URL (direct link or page like Pinterest).
_web_image_node = _import_node_module("wizdroid_image_from_url")
WEB_IMAGE_NODE_CLASS_MAPPINGS = _web_image_node.NODE_CLASS_MAPPINGS
WEB_IMAGE_NODE_DISPLAY_NAME_MAPPINGS = _web_image_node.NODE_DISPLAY_NAME_MAPPINGS

# Extract text from a website and generate a character image prompt via Ollama.
_website_prompt_nodes = _import_node_module("llm_website_prompt")
WEBSITE_PROMPT_NODE_CLASS_MAPPINGS = _website_prompt_nodes.NODE_CLASS_MAPPINGS
WEBSITE_PROMPT_NODE_DISPLAY_NAME_MAPPINGS = _website_prompt_nodes.NODE_DISPLAY_NAME_MAPPINGS

# Batch image captioning for LoRA dataset prep (VL, folder → .txt files).
_batch_caption_nodes = _import_node_module("llm_batch_captioner")
BATCH_CAPTION_NODE_CLASS_MAPPINGS = _batch_caption_nodes.NODE_CLASS_MAPPINGS
BATCH_CAPTION_NODE_DISPLAY_NAME_MAPPINGS = _batch_caption_nodes.NODE_DISPLAY_NAME_MAPPINGS

# Vision critique of a generated image → revised prompt.
_critique_nodes = _import_node_module("llm_image_critique")
CRITIQUE_NODE_CLASS_MAPPINGS = _critique_nodes.NODE_CLASS_MAPPINGS
CRITIQUE_NODE_DISPLAY_NAME_MAPPINGS = _critique_nodes.NODE_DISPLAY_NAME_MAPPINGS

# Iterative image prompt refiner (optional VL + in-session memory).
_refiner_nodes = _import_node_module("llm_image_refiner")
REFINER_NODE_CLASS_MAPPINGS = _refiner_nodes.NODE_CLASS_MAPPINGS
REFINER_NODE_DISPLAY_NAME_MAPPINGS = _refiner_nodes.NODE_DISPLAY_NAME_MAPPINGS

# ---------------------------------------------------------------------------
# Combined mappings for ComfyUI
# ---------------------------------------------------------------------------

NODE_CLASS_MAPPINGS = {
    **LLM_NODE_CLASS_MAPPINGS,
    **LYRICS_NODE_CLASS_MAPPINGS,
    **REWRITE_NODE_CLASS_MAPPINGS,
    **CHARACTER_NODE_CLASS_MAPPINGS,
    **QWEN_MULTI_ANGLES_CLASS_MAPPINGS,
    **SCENE_NODE_CLASS_MAPPINGS,
    **VL_SCENE_NODE_CLASS_MAPPINGS,
    **VL_EXTRACT_NODE_CLASS_MAPPINGS,
    **PRESET_NODE_CLASS_MAPPINGS,
    **WEB_IMAGE_NODE_CLASS_MAPPINGS,
    **WEBSITE_PROMPT_NODE_CLASS_MAPPINGS,
    **BATCH_CAPTION_NODE_CLASS_MAPPINGS,
    **CRITIQUE_NODE_CLASS_MAPPINGS,
    **REFINER_NODE_CLASS_MAPPINGS,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    **LLM_DISPLAY_NAME_MAPPINGS,
    **LYRICS_DISPLAY_NAME_MAPPINGS,
    **REWRITE_DISPLAY_NAME_MAPPINGS,
    **CHARACTER_DISPLAY_NAME_MAPPINGS,
    **QWEN_MULTI_ANGLES_DISPLAY_NAME_MAPPINGS,
    **SCENE_DISPLAY_NAME_MAPPINGS,
    **VL_SCENE_DISPLAY_NAME_MAPPINGS,
    **VL_EXTRACT_DISPLAY_NAME_MAPPINGS,
    **PRESET_NODE_DISPLAY_NAME_MAPPINGS,
    **WEB_IMAGE_NODE_DISPLAY_NAME_MAPPINGS,
    **WEBSITE_PROMPT_NODE_DISPLAY_NAME_MAPPINGS,
    **BATCH_CAPTION_NODE_DISPLAY_NAME_MAPPINGS,
    **CRITIQUE_NODE_DISPLAY_NAME_MAPPINGS,
    **REFINER_NODE_DISPLAY_NAME_MAPPINGS,
}
