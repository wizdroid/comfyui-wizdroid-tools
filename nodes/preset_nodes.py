"""Wizdroid Tools — Preset nodes (plugin-style: one node per catalog).

A single Python module generates one ComfyUI node per JSON file under
``data/presets/`` — drop a new catalog in, restart ComfyUI, and it shows up
as its own node. No Python edits needed (that's the plugin behaviour).

Each node is placed in a category derived from its folder path:

    parts/…       → 🧙 Wizdroid/Presets/Parts
    sets/female/… → 🧙 Wizdroid/Presets/Sets/Female
    sets/male/…   → 🧙 Wizdroid/Presets/Sets/Male
    sets/unisex/… → 🧙 Wizdroid/Presets/Sets/Unisex
    root/…        → 🧙 Wizdroid/Presets

Every node has an ``item`` dropdown (+ ``none``/``random``/``increment``), a
free-text ``details`` field, and a ``seed`` that drives the random/increment
modes. See ``data/presets/README.md`` for the catalog schema.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Tuple, Type

from lib.presets import (
    NONE_OPTION,
    class_name_for_preset,
    default_dropdown_choice,
    discover_presets,
    display_name_for_preset,
    format_preset_fragment,
    get_dropdown_choices,
    get_preset,
    resolve_preset_item,
    ui_category_for,
)

logger = logging.getLogger(__name__)

_FALLBACK_TOOLTIP = "Free-text details (color, material, style, …)."
_SEED_TOOLTIP = (
    "Drives 'random' and 'increment'. Same seed + same catalog → same item "
    "(deterministic)."
)


def _make_preset_node_class(
    preset_id: str,
    label: str,
    description: str,
    category: str,
) -> Type:
    """Build a node class bound to a single preset catalog id."""

    class_name = class_name_for_preset(preset_id)

    class PresetNode:
        """Select a preset item and optional free-text details."""

        CATEGORY = category
        RETURN_TYPES = ("STRING",)
        RETURN_NAMES = ("text",)
        FUNCTION = "build"
        OUTPUT_NODE = False

        @classmethod
        def INPUT_TYPES(cls) -> Dict[str, Any]:
            # Reload JSON on every UI query so edits show up after a browser
            # refresh (load_json caches by mtime).
            preset = get_preset(preset_id)
            if preset is None:
                choices = [NONE_OPTION]
                details_tooltip = _FALLBACK_TOOLTIP
                desc = description
                path_hint = preset_id
            else:
                choices = get_dropdown_choices(preset)
                details_tooltip = preset.get("details_tooltip") or _FALLBACK_TOOLTIP
                desc = preset.get("description") or description
                path_hint = preset.get("path", preset_id)

            cls.DESCRIPTION = desc

            return {
                "required": {
                    "item": (
                        choices,
                        {
                            "default": default_dropdown_choice(choices),
                            "tooltip": (
                                f"{label} entry from {path_hint}. "
                                f"'{NONE_OPTION}' skips the item (details alone "
                                "still emit); 'random' picks uniformly and "
                                "'increment' walks the catalog as the seed changes."
                            ),
                        },
                    ),
                    "details": (
                        "STRING",
                        {
                            "default": "",
                            "multiline": False,
                            "tooltip": details_tooltip,
                        },
                    ),
                    "seed": (
                        "INT",
                        {
                            "default": 0,
                            "min": 0,
                            "max": 0xFFFFFFFF,
                            "tooltip": _SEED_TOOLTIP,
                        },
                    ),
                },
            }

        def build(
            self,
            item: str = NONE_OPTION,
            details: str = "",
            seed: int = 0,
        ) -> Tuple[str]:
            preset = get_preset(preset_id)
            if preset is None:
                return ("",)
            items = list(preset.get("items") or [])
            style = preset.get("output_style") or "item_then_details"
            resolved = resolve_preset_item(item, items, seed)
            fragment = format_preset_fragment(
                resolved or NONE_OPTION, details, output_style=style
            )
            return (fragment,)

    PresetNode.__name__ = class_name
    PresetNode.__qualname__ = class_name
    PresetNode.DESCRIPTION = description
    return PresetNode


def _build_mappings() -> Tuple[Dict[str, Type], Dict[str, str]]:
    """One node class + display name per catalog JSON under data/presets/."""
    class_map: Dict[str, Type] = {}
    display_map: Dict[str, str] = {}

    presets = discover_presets()
    if not presets:
        logger.warning(
            "No preset JSON found under data/presets/ — Preset nodes not registered"
        )
        return class_map, display_map

    for preset in presets:
        pid = preset["id"]
        class_name = class_name_for_preset(pid)
        if class_name in class_map:
            logger.warning(
                "Duplicate preset class name %s for id %s — skipping",
                class_name,
                pid,
            )
            continue
        label = preset["label"]
        desc = preset.get("description") or f"Preset: {label}"
        category = ui_category_for(preset)
        cls = _make_preset_node_class(pid, label, desc, category)
        class_map[class_name] = cls
        display_map[class_name] = display_name_for_preset(label)
        logger.debug("Registered preset node %s (%s) → %s", class_name, pid, category)

    return class_map, display_map


NODE_CLASS_MAPPINGS, NODE_DISPLAY_NAME_MAPPINGS = _build_mappings()
