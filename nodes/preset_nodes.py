"""Wizdroid Tools — Preset nodes (dropdown + details → prompt fragment).

One ComfyUI node is registered per JSON file under ``data/presets/``.
Category: ``🧙 Wizdroid/Presets``.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Tuple, Type

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
)

logger = logging.getLogger(__name__)

CATEGORY = "🧙 Wizdroid/Presets"


def _make_preset_node_class(preset_id: str, label: str, description: str) -> Type:
    """Build a node class bound to a single preset catalog id."""

    class_name = class_name_for_preset(preset_id)

    class PresetNode:
        """Select a preset item and optional free-text details."""

        CATEGORY = CATEGORY
        RETURN_TYPES = ("STRING",)
        RETURN_NAMES = ("text",)
        FUNCTION = "build"
        OUTPUT_NODE = False

        @classmethod
        def INPUT_TYPES(cls) -> Dict[str, Any]:
            # Reload JSON on every UI query so edits appear after browser refresh
            preset = get_preset(preset_id)
            if preset is None:
                choices = [NONE_OPTION]
                details_tooltip = "Free-text details (color, material, etc.)"
                desc = description
            else:
                choices = get_dropdown_choices(preset)
                details_tooltip = preset.get(
                    "details_tooltip",
                    "Free-text details (color, material, etc.)",
                )
                desc = preset.get("description") or description

            # DESCRIPTION is class-level; update when possible
            cls.DESCRIPTION = desc

            return {
                "required": {
                    "item": (
                        choices,
                        {
                            "default": default_dropdown_choice(choices),
                            "tooltip": (
                                f"{label} type from data/presets/{preset_id}.json. "
                                f"'{NONE_OPTION}' skips the type (details alone still emit). "
                                "'random' picks uniformly from the catalog. "
                                "'increment' walks the catalog as seed changes."
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
                            "tooltip": (
                                "Drives 'random' and 'increment'. Same seed + same "
                                "catalog → same item (deterministic)."
                            ),
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
            style = "item_then_details"
            catalog: List[str] = []
            if preset is not None:
                style = preset.get("output_style") or style
                catalog = list(preset.get("items") or [])
            resolved = resolve_preset_item(item, catalog, seed)
            fragment = format_preset_fragment(
                resolved or NONE_OPTION, details, output_style=style
            )
            return (fragment,)

    PresetNode.__name__ = class_name
    PresetNode.__qualname__ = class_name
    PresetNode.DESCRIPTION = description
    return PresetNode


def _build_mappings() -> Tuple[Dict[str, Type], Dict[str, str]]:
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
        label = preset["label"]
        desc = preset.get("description") or f"Preset: {label}"
        cls = _make_preset_node_class(pid, label, desc)
        class_name = class_name_for_preset(pid)
        if class_name in class_map:
            logger.warning(
                "Duplicate preset class name %s for id %s — skipping",
                class_name,
                pid,
            )
            continue
        class_map[class_name] = cls
        display_map[class_name] = display_name_for_preset(label)
        logger.debug("Registered preset node %s (%s)", class_name, pid)

    return class_map, display_map


NODE_CLASS_MAPPINGS, NODE_DISPLAY_NAME_MAPPINGS = _build_mappings()
