# Preset catalogs

Each catalog JSON in this folder becomes its **own ComfyUI node**
(plugin-style). The folder it lives in decides which submenu it appears
under (root files go straight under `🧙 Wizdroid/Presets`):

| Folder | Node category |
|--------|---------------|
| `parts/` | `🧙 Wizdroid/Presets/Parts` |
| `sets/female/` | `🧙 Wizdroid/Presets/Sets/Female` |
| `sets/male/` | `🧙 Wizdroid/Presets/Sets/Male` |
| `sets/unisex/` | `🧙 Wizdroid/Presets/Sets/Unisex` |
| root (`*.json`) | `🧙 Wizdroid/Presets` |

Each node has an `item` dropdown (+ `none` / `random` / `increment`), a
free-text `details` field, and a `seed`.

Catalogs are JSON files, grouped into **categories** by folder:

```
data/presets/
├── parts/          # shared unisex part catalogs (tops, footwear, makeup, …)
├── sets/
│   ├── female/     # female complete-look sets
│   ├── male/       # male complete-look sets
│   └── unisex/     # gender-neutral sets
└── *.json          # legacy root files → category "unfiled" (migrate later)
```

A catalog's category is its folder path relative to `data/presets/`. Files at
the root load as category `unfiled` until you move them into a category
folder — nothing breaks either way.

Edit freely. Save, then **refresh the ComfyUI browser page** so dropdowns
reload. Generation always uses the latest file contents (mtime-cached).
**New catalogs** (new nodes) need a ComfyUI **restart** — node classes are
built once at import time.

Files and folders starting with `_` are ignored (handy for drafts).

## Schema

```json
{
  "label": "Footwear",
  "sort_order": 10,
  "description": "Shown as the node description.",
  "details_tooltip": "Tooltip for the free-text details box.",
  "details_label": "details",
  "include_none": true,
  "output_style": "item_then_details",
  "items": [
    "sneakers",
    "combat boots",
    "heels"
  ]
}
```

| Field | Required | Meaning |
|-------|----------|---------|
| `label` | no | Display name (default: title-cased filename) |
| `sort_order` | no | Lower sorts earlier in discovery (default 1000) |
| `description` | no | Node DESCRIPTION text |
| `details_tooltip` | no | Tooltip on the free-text field |
| `details_label` | no | Reserved / docs only (UI always uses `details`) |
| `include_none` | no | Prepend `none` to the dropdown (default true). `random` and `increment` are always added. |
| `output_style` | no | How item + details are joined (see below) |
| `items` | yes | List of strings (or `{"label": "…"}` objects) |

### `output_style`

| Value | Example result |
|-------|----------------|
| `item_then_details` (default) | `combat boots, matte black leather` |
| `details_then_item` | `matte black leather combat boots` |
| `item_only` | `combat boots` |
| `details_only` | `matte black leather` (falls back to item if empty) |

Every dropdown also includes two special values (not stored in JSON `items`):

| Value | Meaning |
|-------|---------|
| `none` | Skip the catalog type (details alone still emit) |
| `random` | Uniform pick from `items`; driven by `seed` |
| `increment` | `items[seed % len(items)]` — walks the catalog as seed changes |

Same seed + same catalog always resolve the same way. Default selection is
`none` so unused accessory nodes stay silent.

If `item` is `none` and details are empty → empty string.  
If `item` is `none` but details are set → details only.

## Add a new catalog

1. Create `data/presets/<category>/my_thing.json` (or the root for
   `unfiled`) with the schema above.
2. **Restart ComfyUI** — the new catalog becomes its own node under the
   submenu matching its folder (`data/presets/parts/foo.json` →
   `🧙 Wizdroid/Presets/Parts → 🧙 Foo`).
3. Editing an *existing* catalog's `items` only needs a browser page refresh.

## Example: custom footwear entry

Open `parts/footwear.json` and append to `items`:

```json
"platform mary janes"
```

Refresh the browser page; the new option appears in the **🧙 Footwear**
node's `item` dropdown.

## Built-in catalogs

All catalogs have been migrated into their category folders:

| Category | File | Catalog |
|----------|------|---------|
| `parts` | `accessories.json` | Accessories |
| `parts` | `bags.json` | Bags |
| `parts` | `body_markings.json` | Body Markings |
| `parts` | `bottoms.json` | Bottoms |
| `parts` | `expressions.json` | Expressions |
| `parts` | `eyewear.json` | Eyewear |
| `parts` | `footwear.json` | Footwear |
| `parts` | `gloves.json` | Gloves |
| `parts` | `hairstyle_extras.json` | Hairstyle Extras |
| `parts` | `headgear.json` | Headgear |
| `parts` | `hosiery.json` | Hosiery |
| `parts` | `jewelry.json` | Jewelry |
| `parts` | `makeup.json` | Makeup |
| `parts` | `nails.json` | Nails |
| `parts` | `neckwear.json` | Neckwear |
| `parts` | `outerwear.json` | Outerwear |
| `parts` | `piercings.json` | Piercings |
| `parts` | `props.json` | Props |
| `parts` | `tattoos.json` | Tattoos |
| `parts` | `tops.json` | Tops |
| `parts` | `weapons.json` | Weapons |
| `sets/unisex` | `anime_cosplay.json` | Anime Cosplay Set (male + female) |
| `sets/unisex` | `characters.json` | Character Set (male + female) |
| `sets/female` | `bollywood-80s.json` | 1980s Bollywood Disco Set |
| `sets/female` | `candid_mini_dresses.json` | Candid Mini Dress Set |
| `sets/female` | `glamorous_bodycon_dresses.json` | Glamorous Bodycon Dress Set |
| `sets/female` | `goth_sets.json` | Complete Goth Set |
| `sets/female` | `indian_casual_everyday.json` | Indian Casual Everyday Set |
| `sets/female` | `indian_chudidar_sets.json` | Indian Chudidar Set |
| `sets/female` | `indian_lehenga_sets.json` | Indian Lehenga Set |
| `sets/female` | `indian_sari_drapes.json` | Indian Sari Drape Set |

`sets/male/` is reserved for future male-oriented complete looks (empty for now).
