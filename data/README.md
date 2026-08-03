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

## Add a song structure

1. Open `lyrics/structures.json`.
2. Add:

```json
"punk": ["[intro]", "[verse]", "[chorus]", "[verse]", "[chorus]", "[outro]"]
```

3. Optionally set a default BPM in `lyrics/choices.json` → `default_bpm_by_structure`.
4. Refresh ComfyUI.

## Add a Preset node (plugin-style)

1. Create `presets/my_category.json`:

```json
{
  "label": "My Category",
  "sort_order": 200,
  "description": "Select an item and optional details.",
  "details_tooltip": "Color, material, style…",
  "items": ["option a", "option b"]
}
```

2. **Restart ComfyUI** once so the new node class is registered.
3. Find it under `🧙 Wizdroid/Presets`.

Editing items inside an existing file only needs a **browser refresh**.
See `presets/README.md` for full schema and `output_style` options.

## Notes

- Keys under rewrite `modes.json` are the ComfyUI dropdown values (stable ids).
- Use `\n` in JSON strings for multi-line instructions.
- Invalid JSON falls back to built-in minimal defaults and is logged.
- Preset **item lists** hot-reload on page refresh; **new preset files** need a ComfyUI restart.
