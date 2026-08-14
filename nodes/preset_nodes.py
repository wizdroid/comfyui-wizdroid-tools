"""Wizdroid Tools — Universal Preset node (category → catalog → item).

One node browses every catalog under ``data/presets/`` via cascading
dropdowns: Category (folder) → Catalog (JSON file) → Item (+ details + seed).
Category: ``🧙 Wizdroid/Presets``.

Drop a new catalog JSON into a category folder (or the root, ``unfiled``)
and refresh the ComfyUI page — the universal node picks it up. See
``data/presets/README.md`` for the layout.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Tuple

from lib.presets import (
    NONE_OPTION,
    default_dropdown_choice,
    find_preset_by_catalog_label,
    format_preset_fragment,
    get_catalog_choices,
    get_categories,
    get_dropdown_choices,
    resolve_preset_item,
)

logger = logging.getLogger(__name__)

CATEGORY = "🧙 Wizdroid/Presets"


_FALLBACK_DESCRIPTION = (
    "Browse preset catalogs by category and pick an item to emit a prompt fragment."
)
_FALLBACK_TOOLTIP = "Free-text details (color, material, style, …)."


class WizdroidPresetPicker:
    """Compose a prompt fragment from a categorized preset catalog."""

    CATEGORY = CATEGORY
    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("text",)
    FUNCTION = "build"
    OUTPUT_NODE = False

    # Last chosen category/catalog, cached so INPUT_TYPES can rebuild the
    # dependent dropdowns for that selection. ComfyUI re-invokes INPUT_TYPES on
    # widget change in recent versions; if your UI doesn't auto-refresh, a page
    # refresh syncs the catalog/item dropdowns to the chosen category.
    _last_category: str = NONE_OPTION
    _last_catalog: str = NONE_OPTION

    @classmethod
    def INPUT_TYPES(cls) -> Dict[str, Any]:
        categories = get_categories() or [NONE_OPTION]
        current_category = (
            cls._last_category if cls._last_category in categories else categories[0]
        )

        catalog_choices = get_catalog_choices(current_category) or [NONE_OPTION]
        current_catalog = (
            cls._last_catalog
            if cls._last_catalog in catalog_choices
            else catalog_choices[0]
        )

        preset = find_preset_by_catalog_label(current_category, current_catalog)
        item_choices = get_dropdown_choices(preset) if preset else [NONE_OPTION]
        cls.DESCRIPTION = preset.get("description") if preset else _FALLBACK_DESCRIPTION
        details_tooltip = (
            preset.get("details_tooltip") if preset else _FALLBACK_TOOLTIP
        )

        return {
            "required": {
                "category": (
                    categories,
                    {
                        "default": current_category,
                        "tooltip": (
                            "Preset category = folder under data/presets/. "
                            "Root files are the 'unfiled' category until moved."
                        ),
                    },
                ),
                "catalog": (
                    catalog_choices,
                    {
                        "default": current_catalog,
                        "tooltip": "Catalog JSON within the selected category.",
                    },
                ),
                "item": (
                    item_choices,
                    {
                        "default": default_dropdown_choice(item_choices),
                        "tooltip": (
                            f"Item from the selected catalog. '{NONE_OPTION}' skips the "
                            "item (details alone still emit). 'random' picks uniformly; "
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
        category: str = NONE_OPTION,
        catalog: str = NONE_OPTION,
        item: str = NONE_OPTION,
        details: str = "",
        seed: int = 0,
    ) -> Tuple[str]:
        # Remember the selection for the next INPUT_TYPES call.
        type(self)._last_category = category
        type(self)._last_catalog = catalog

        preset = find_preset_by_catalog_label(category, catalog)
        if preset is None:
            return ("",)

        style = preset.get("output_style") or "item_then_details"
        catalog_items = list(preset.get("items") or [])
        resolved = resolve_preset_item(item, catalog_items, seed)
        fragment = format_preset_fragment(
            resolved or NONE_OPTION, details, output_style=style
        )
        return (fragment,)


NODE_CLASS_MAPPINGS = {
    "WizdroidPresetPicker": WizdroidPresetPicker,
}
NODE_DISPLAY_NAME_MAPPINGS = {
    "WizdroidPresetPicker": "🧙 Preset",
}
