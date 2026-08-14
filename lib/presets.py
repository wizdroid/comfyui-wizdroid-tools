"""Preset catalogs for plugin-style preset nodes under data/presets/.

``nodes/preset_nodes.py`` generates one ComfyUI node per catalog JSON; each
node's category is derived from its folder path. This module discovers,
loads, and formats those catalogs (schema + helpers live here).

A catalog is a ``*.json`` file. Its *category* is the folder path relative to
``data/presets/``; files at the root are the ``unfiled`` category until they
are moved into a category folder. Suggested layout::

    data/presets/
    ├── parts/          # shared unisex part catalogs (tops, footwear, …)
    │   ├── tops.json
    │   └── footwear.json
    ├── sets/
    │   ├── female/     # female complete-look sets
    │   ├── male/       # male complete-look sets
    │   └── unisex/     # gender-neutral sets
    └── legacy.json     # root files load as category "unfiled"

Schema (per file)::

    {
      "label": "Footwear",                 # catalog display name
      "description": "…",                  # node DESCRIPTION for this catalog
      "details_tooltip": "…",              # free-text field tooltip
      "details_label": "details",          # optional; default "details"
      "sort_order": 10,                    # optional; lower first
      "include_none": true,                # optional; default true
      "output_style": "item_then_details", # optional; see format_preset_fragment
      "items": ["sneakers", "boots", …]
    }

A catalog id is ``<category>:<filename-stem>`` (unique). Dropdowns always
include ``random`` and ``increment`` (resolved at execute time from the
node's ``seed``). ``none`` is prepended when ``include_none``. Catalog files
and new category folders are discovered on page refresh / restart.
"""

from __future__ import annotations

import logging
import random
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

from lib.json_data import DATA_DIR, load_json

logger = logging.getLogger(__name__)

PRESETS_DIR = DATA_DIR / "presets"

# Special dropdown tokens (not stored in JSON items)
NONE_OPTION = "none"
RANDOM_OPTION = "random"
INCREMENT_OPTION = "increment"
SPECIAL_OPTIONS: tuple[str, ...] = (NONE_OPTION, RANDOM_OPTION, INCREMENT_OPTION)
_SPECIAL_SET = frozenset(SPECIAL_OPTIONS)

# Category label for legacy files sitting directly in data/presets/.
LEGACY_CATEGORY = "unfiled"

# Preferred category order for discovery/registration; unknown categories sort last.
_CATEGORY_ORDER: tuple[str, ...] = (
    "parts",
    "sets/female",
    "sets/male",
    "sets/unisex",
    LEGACY_CATEGORY,
)


def _is_special(text: str) -> bool:
    return (text or "").strip().lower() in _SPECIAL_SET

_OUTPUT_STYLES = frozenset(
    {
        "item_then_details",  # "combat boots, matte black leather"
        "details_then_item",  # "matte black leather combat boots"
        "item_only",  # ignore details in fragment (details still available? no - skip)
        "details_only",  # only free text if present, else item
    }
)

_FALLBACK_ITEMS: Dict[str, List[str]] = {
    "footwear": ["sneakers", "boots", "heels", "sandals", "barefoot"],
    "headgear": ["baseball cap", "beanie", "fedora", "hood", "none worn"],
    "makeup": ["natural makeup", "smoky eye", "bold lipstick", "no makeup"],
}


def _slug_from_path(path: Path) -> str:
    return path.stem.strip().lower().replace(" ", "_")


def _title_from_slug(slug: str) -> str:
    return slug.replace("_", " ").replace("-", " ").title()


def list_preset_files() -> List[Path]:
    """Return sorted preset JSON paths, walking category subfolders.

    Files and folders whose name starts with ``_`` are ignored (drafts).
    """
    if not PRESETS_DIR.is_dir():
        return []
    files = []
    for p in PRESETS_DIR.glob("**/*.json"):
        if not p.is_file() or p.name.startswith("_"):
            continue
        rel = p.relative_to(PRESETS_DIR)
        if any(part.startswith("_") for part in rel.parts[:-1]):
            continue
        files.append(p)
    return sorted(files)


def _category_for_path(path: Path) -> str:
    """Category = folder path relative to data/presets/; root → 'unfiled'."""
    parent = path.parent.relative_to(PRESETS_DIR)
    if parent == Path("."):
        return LEGACY_CATEGORY
    return parent.as_posix()


def load_preset_file(path: Path) -> Dict[str, Any]:
    """Load one preset JSON; always returns a normalized dict with defaults.

    Adds ``category`` (folder path) and a unique ``id`` (``category:slug``).
    """
    raw = load_json(path, default=None)
    slug = _slug_from_path(path)
    category = _category_for_path(path)

    if not isinstance(raw, dict):
        logger.warning("Preset %s is not a JSON object — using fallback items", path)
        items = list(_FALLBACK_ITEMS.get(slug, ["example item"]))
        return {
            "id": f"{category}:{slug}",
            "category": category,
            "slug": slug,
            "label": _title_from_slug(slug),
            "description": f"Select {slug.replace('_', ' ')} and optional details.",
            "details_tooltip": "Color, material, style, condition, etc.",
            "details_label": "details",
            "sort_order": 1000,
            "include_none": True,
            "output_style": "item_then_details",
            "items": items,
            "path": str(path),
        }

    items_raw = raw.get("items", [])
    items: List[str] = []
    if isinstance(items_raw, list):
        for entry in items_raw:
            if isinstance(entry, str):
                text = entry.strip()
                if text and not _is_special(text):
                    items.append(text)
            elif isinstance(entry, dict):
                # Allow {"label": "…"} or {"id": "…", "label": "…"}
                label = entry.get("label") or entry.get("id") or entry.get("name")
                if isinstance(label, str) and label.strip():
                    text = label.strip()
                    if not _is_special(text):
                        items.append(text)
    if not items:
        items = list(_FALLBACK_ITEMS.get(slug, ["example item"]))
        logger.warning("Preset %s has no usable items — using fallback", path)

    label = raw.get("label") or _title_from_slug(slug)
    if not isinstance(label, str) or not label.strip():
        label = _title_from_slug(slug)

    description = raw.get("description") or (
        f"Select {label.lower()} and describe color, material, or other details."
    )
    details_tooltip = raw.get("details_tooltip") or (
        "Free-text details: color, material, wear, brand vibe, pattern, etc."
    )
    details_label = raw.get("details_label") or "details"
    if not isinstance(details_label, str) or not details_label.strip():
        details_label = "details"

    try:
        sort_order = int(raw.get("sort_order", 1000))
    except (TypeError, ValueError):
        sort_order = 1000

    include_none = raw.get("include_none", True)
    if not isinstance(include_none, bool):
        include_none = bool(include_none)

    output_style = raw.get("output_style", "item_then_details")
    if output_style not in _OUTPUT_STYLES:
        output_style = "item_then_details"

    return {
        "id": f"{category}:{slug}",
        "category": category,
        "slug": slug,
        "label": label.strip(),
        "description": str(description).strip(),
        "details_tooltip": str(details_tooltip).strip(),
        "details_label": details_label.strip(),
        "sort_order": sort_order,
        "include_none": include_none,
        "output_style": output_style,
        "items": items,
        "path": str(path),
    }


def _category_sort_key(category: Optional[str]) -> tuple:
    """Sort categories by _CATEGORY_ORDER; unknown categories sort last."""
    cat = category or LEGACY_CATEGORY
    try:
        return (_CATEGORY_ORDER.index(cat),)
    except ValueError:
        return (len(_CATEGORY_ORDER),)


def discover_presets() -> List[Dict[str, Any]]:
    """Load all preset catalogs, sorted by category, sort_order, then label."""
    presets: List[Dict[str, Any]] = []
    for path in list_preset_files():
        try:
            presets.append(load_preset_file(path))
        except Exception as e:  # noqa: BLE001
            logger.error("Failed to load preset %s: %s", path, e)
    presets.sort(
        key=lambda p: (
            _category_sort_key(p.get("category")),
            p.get("sort_order", 1000),
            p.get("label", "").lower(),
        )
    )
    return presets


def get_preset(preset_id: str) -> Optional[Dict[str, Any]]:
    """Return one preset by id (``category:slug``) or bare slug, or None."""
    for preset in discover_presets():
        if preset["id"] == preset_id or preset.get("slug") == preset_id:
            return preset
    # Legacy direct-file fallback for a bare root slug.
    path = PRESETS_DIR / f"{preset_id}.json"
    if path.is_file():
        return load_preset_file(path)
    return None


def get_categories(presets: Optional[Sequence[Dict[str, Any]]] = None) -> List[str]:
    """Sorted unique categories (folder paths) across all catalogs."""
    items = list(presets) if presets is not None else discover_presets()
    cats = sorted(
        {p.get("category", LEGACY_CATEGORY) for p in items},
        key=_category_sort_key,
    )
    return cats


def get_presets_by_category(
    category: str,
    presets: Optional[Sequence[Dict[str, Any]]] = None,
) -> List[Dict[str, Any]]:
    """Catalogs in one category, sorted by sort_order then label."""
    items = list(presets) if presets is not None else discover_presets()
    return [p for p in items if p.get("category", LEGACY_CATEGORY) == category]


def get_catalog_choices(
    category: str,
    presets: Optional[Sequence[Dict[str, Any]]] = None,
) -> List[str]:
    """Dropdown labels for the catalogs in a category.

    Duplicate labels are disambiguated by appending the slug.
    """
    catalogs = get_presets_by_category(category, presets)
    counts: Dict[str, int] = {}
    for p in catalogs:
        counts[p["label"]] = counts.get(p["label"], 0) + 1
    choices = []
    for p in catalogs:
        label = p["label"]
        if counts[label] > 1:
            choices.append(f"{label} ({p['slug']})")
        else:
            choices.append(label)
    return choices


def find_preset_by_catalog_label(
    category: str,
    catalog_label: str,
    presets: Optional[Sequence[Dict[str, Any]]] = None,
) -> Optional[Dict[str, Any]]:
    """Resolve a catalog dropdown label back to its preset dict, or None."""
    catalogs = get_presets_by_category(category, presets)
    low = (catalog_label or "").strip().lower()
    for p in catalogs:
        label = p["label"]
        if label == catalog_label or low == f"{label.lower()} ({p['slug']})":
            return p
    for p in catalogs:
        if p["label"].lower() == low:
            return p
    return None


def get_dropdown_choices(preset: Dict[str, Any]) -> List[str]:
    """Build the ComfyUI dropdown list for a preset.

    Always prepends ``random`` and ``increment``. Prepends ``none`` when
    ``include_none`` is true (the default).
    """
    items: Sequence[str] = preset.get("items") or []
    # Deduplicate while preserving order; drop special tokens if they leaked in
    seen: set[str] = set()
    ordered: List[str] = []
    for item in items:
        key = item.lower()
        if key in seen or key in _SPECIAL_SET:
            continue
        seen.add(key)
        ordered.append(item)
    specials: List[str] = []
    if preset.get("include_none", True):
        specials.append(NONE_OPTION)
    specials.extend([RANDOM_OPTION, INCREMENT_OPTION])
    if not ordered:
        return specials or [NONE_OPTION]
    return [*specials, *ordered]


def default_dropdown_choice(choices: Sequence[str]) -> str:
    """Prefer ``none`` so unused accessory nodes stay silent."""
    for choice in choices:
        if choice.strip().lower() == NONE_OPTION:
            return choice
    concrete = [c for c in choices if not _is_special(c)]
    if concrete:
        return concrete[0]
    return choices[0] if choices else NONE_OPTION


def resolve_preset_item(
    item: str,
    items: Sequence[str],
    seed: int = 0,
) -> Optional[str]:
    """Resolve a dropdown value to a concrete catalog item, or None to omit.

    - concrete value → returned as-is
    - ``none`` / empty → None
    - ``random`` → uniform pick via ``Random(seed)``
    - ``increment`` → ``items[seed % len(items)]``
    """
    raw = (item or "").strip()
    if not raw or raw.lower() == NONE_OPTION:
        return None

    concrete = [c for c in items if not _is_special(c)]
    if not concrete:
        return None

    seed = int(seed) & 0xFFFFFFFF

    if raw.lower() == RANDOM_OPTION:
        return random.Random(seed).choice(concrete)
    if raw.lower() == INCREMENT_OPTION:
        return concrete[seed % len(concrete)]

    return raw


def format_preset_fragment(
    item: str,
    details: str = "",
    *,
    output_style: str = "item_then_details",
) -> str:
    """Combine dropdown selection + free-text details into a prompt fragment.

    Returns empty string when nothing useful is selected.
    """
    item_clean = (item or "").strip()
    details_clean = (details or "").strip()
    # Collapse internal whitespace in details
    details_clean = re.sub(r"\s+", " ", details_clean)

    # Unresolved special tokens (none / random / increment) skip the item
    is_none = not item_clean or _is_special(item_clean)

    if is_none and not details_clean:
        return ""
    if is_none and details_clean:
        return details_clean

    style = output_style if output_style in _OUTPUT_STYLES else "item_then_details"

    if style == "item_only" or not details_clean:
        return item_clean
    if style == "details_only":
        return details_clean or item_clean
    if style == "details_then_item":
        return f"{details_clean} {item_clean}"
    # default: item_then_details
    return f"{item_clean}, {details_clean}"


def class_name_for_preset(preset_id: str) -> str:
    """Stable ComfyUI class name for a preset id (``category:slug``).

    e.g. ``sets/unisex:anime_cosplay`` → ``WizdroidPresetSetsUnisexAnimeCosplay``.
    """
    parts = re.split(r"[_\-\s/:]+", preset_id.strip())
    camel = "".join(p[:1].upper() + p[1:] for p in parts if p)
    if not camel:
        camel = "Generic"
    # Ensure valid Python identifier
    if camel[0].isdigit():
        camel = f"P{camel}"
    return f"WizdroidPreset{camel}"


def display_name_for_preset(label: str) -> str:
    return f"🧙 {label}"


# ComfyUI menu root for preset nodes; submenus mirror the folder layout.
PRESET_CATEGORY_ROOT = "🧙 Wizdroid/Presets"


def ui_category_for(preset: Dict[str, Any]) -> str:
    """Map a preset's folder category to a ComfyUI menu category.

    Root / ``unfiled`` files land directly under the preset root; deeper
    folders become submenus (``sets/female`` → ``…/Presets/Sets/Female``).
    """
    category = (preset.get("category") or LEGACY_CATEGORY).strip("/")
    if not category or category == LEGACY_CATEGORY:
        return PRESET_CATEGORY_ROOT
    parts = [p for p in category.split("/") if p]
    return f"{PRESET_CATEGORY_ROOT}/{'/'.join(p.title() for p in parts)}"
