# Preset catalogs

Each `*.json` file in this folder becomes one ComfyUI node under
**🧙 Wizdroid / Presets**.

Edit freely. Save, then **refresh the ComfyUI browser page** so dropdowns reload.
Generation always uses the latest file contents (mtime-cached).

Files starting with `_` are ignored (handy for drafts).

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

## Add a new preset node

1. Create `data/presets/my_thing.json` with the schema above.
2. Restart ComfyUI **once** so the new file is registered as a node class
   (dropdown *values* hot-reload on page refresh; **new files** need a restart).
3. Find **🧙 My Thing** under **🧙 Wizdroid / Presets**.

## Example: custom footwear entry

Open `footwear.json` and append to `items`:

```json
"platform mary janes"
```

Refresh the browser page; the new option appears in the Footwear node dropdown.

## Built-in catalogs

| File | Node |
|------|------|
| `footwear.json` | Footwear |
| `headgear.json` | Headgear |
| `hairstyle_extras.json` | Hairstyle Extras |
| `expressions.json` | Expressions |
| `makeup.json` | Makeup |
| `eyewear.json` | Eyewear |
| `jewelry.json` | Jewelry |
| `piercings.json` | Piercings |
| `tattoos.json` | Tattoos |
| `body_markings.json` | Body Markings |
| `gloves.json` | Gloves |
| `nails.json` | Nails |
| `neckwear.json` | Neckwear |
| `tops.json` | Tops |
| `bottoms.json` | Bottoms |
| `outerwear.json` | Outerwear |
| `hosiery.json` | Hosiery |
| `bags.json` | Bags |
| `accessories.json` | Accessories |
| `props.json` | Props |
| `weapons.json` | Weapons |
| `goth_sets.json` | Complete Goth Set |
| `characters.json` | Character Set |
| `anime_cosplay.json` | Anime Cosplay Set |
| `candid_mini_dresses.json` | Candid Mini Dress Set |
| `glamorous_bodycon_dresses.json` | Glamorous Bodycon Dress Set |
| `indian_casual_everyday.json` | Indian Casual Everyday Set |
| `indian_chudidar_sets.json` | Indian Chudidar Set |
| `indian_lehenga_sets.json` | Indian Lehenga Set |
| `indian_sari_drapes.json` | Indian Sari Drape Set |
