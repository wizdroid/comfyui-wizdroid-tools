# Meta-prompt data (edit freely)

All LLM node instructions live here as JSON. Python only **loads** these files
at runtime (mtime-cached). Edit a file, save, then **refresh the ComfyUI page**
so dropdowns re-read choices. Generation always uses the latest file contents.

## Layout

```
data/
├── prompts/                 # LLM Prompt Generator (image) + Character AI guidance
│   ├── spice.json           # levels 0–10
│   ├── fantasy.json
│   ├── detail.json
│   └── system.json          # system_prompt_template, user_prompt_wrapper
├── character/               # Character Prompt Generator
│   ├── choices.json         # dropdown concrete values per attribute
│   └── system.json          # system/user templates ({character_json}, guidance)
├── portrait/                # High-Energy Portrait Template
│   ├── choices.json         # slot dropdowns (style, energy, pose, lighting, …)
│   └── system.json          # full/compact templates + system/user prompts
├── scene/                   # Video scene generators (text + VL)
│   ├── choices.json         # mood, style dropdowns
│   ├── system.json          # generic text/vl system + user templates
│   └── video_models.json    # per-model meta prompts + dropdown order
├── vl_extract/              # VL Image Extract (modes + templates)
│   ├── modes.json           # mode_id → label, instruction, suggested_*
│   └── system.json          # base system, mode_order, user template
├── rewrite/                 # LLM Text Rewriter
│   ├── modes.json           # mode_id → label, instruction, suggested_temperature
│   └── system.json          # base system, output rules, mode_order, templates
├── lyrics/                  # LLM Lyrics Generator (ACE-Step)
│   ├── structures.json      # structure_name → [section markers]
│   ├── choices.json         # languages, vocals, rhymes, BPM, guidance strings
│   └── system.json          # system_prompt_template, user_prompt_template
└── presets/                 # Plugin-style Preset nodes (one JSON → one node)
    ├── README.md            # schema + how to add catalogs
    ├── footwear.json
    ├── headgear.json
    ├── makeup.json
    └── …
```

## Add a rewrite mode

1. Open `rewrite/modes.json`.
2. Add a new key (dropdown value):

```json
"noir": {
  "label": "Noir detective",
  "instruction": "Mode: Noir.\nRewrite in hard-boiled detective voice. Keep the same meaning.",
  "suggested_temperature": 0.7
}
```

3. Optionally append `"noir"` to `mode_order` in `rewrite/system.json`
   (if omitted, new modes still appear after the ordered list).
4. Refresh the ComfyUI browser page and re-add or reselect the node if needed.

## Add / tweak a video model meta-prompt

The scene generators (text + VL) have a `video_model` dropdown. Options come
from `scene/video_models.json`:

```json
{
  "model_order": ["generic", "minimax", "h3"],
  "models": {
    "minimax": {
      "label": "MiniMax (Hailuo)",
      "text_system_prompt": "…",   // {duration_seconds} {mood} {style} {extra_guidance}
      "text_user_prompt": "…",     // {duration_seconds} {mood} {style} {user_prompt} {extra_block}
      "vl_system_prompt": "…",
      "vl_user_prompt": "…"
    }
  }
}
```

1. Add a new key (stable id) under `models` with a `label` and the prompt
   fields you want to override.
2. Append the id to `model_order` to control dropdown position.
3. The `generic` option always exists and maps to `scene/system.json` — no need
   to add it here.
4. Refresh the ComfyUI browser page so the dropdown reloads.

## Add a VL extract mode

1. Open `vl_extract/modes.json`.
2. Add a new key (stable id):

```json
"nails": {
  "label": "Nail description",
  "instruction": "Mode: Nails.\nDescribe nail shape, length, color, art, and finish only.",
  "suggested_temperature": 0.3,
  "suggested_max_tokens": 256
}
```

3. Optionally append `"nails"` to `mode_order` in `vl_extract/system.json`
   (if omitted, new modes still appear after the ordered list).
4. Refresh the ComfyUI browser page.

Spice/detail for NSFW density still come from `prompts/spice.json` and
`prompts/detail.json` (shared with the image prompt generator).

## Add a song structure

1. Open `lyrics/structures.json`.
2. Add:

```json
"punk": ["[intro]", "[verse]", "[chorus]", "[verse]", "[chorus]", "[outro]"]
```

3. Optionally set a default BPM in `lyrics/choices.json` → `default_bpm_by_structure`.
4. Refresh ComfyUI.

## Add a Preset catalog

Each catalog JSON becomes its own **plugin-style** node. Drop a file into a
category folder (`parts/`, `sets/female/`, `sets/male/`, `sets/unisex/`, or
the root = `unfiled`); the folder decides the node's submenu under
`🧙 Wizdroid/Presets` (e.g. `parts/foo.json` → `…/Presets/Parts → 🧙 Foo`):

```json
{
  "label": "My Category",
  "sort_order": 200,
  "description": "Select an item and optional details.",
  "details_tooltip": "Color, material, style…",
  "items": ["option a", "option b"]
}
```

**Restart ComfyUI** to register a new catalog as a node; editing an existing
catalog's `items` only needs a browser page refresh.
See `presets/README.md` for the full schema, `output_style`, and layout.

## Notes

- Keys under rewrite `modes.json` are the ComfyUI dropdown values (stable ids).
- Use `\n` in JSON strings for multi-line instructions.
- Invalid JSON falls back to built-in minimal defaults and is logged.
- New preset catalog files need a ComfyUI **restart** (node classes are built at import); editing an existing catalog's `items` hot-reloads on page refresh.
