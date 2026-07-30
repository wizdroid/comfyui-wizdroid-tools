# Meta-prompt data (edit freely)

All LLM node instructions live here as JSON. Python only **loads** these files
at runtime (mtime-cached). Edit a file, save, then **refresh the ComfyUI page**
so dropdowns re-read choices. Generation always uses the latest file contents.

## Layout

```
data/
├── prompts/                 # LLM Prompt Generator (image)
│   ├── spice.json           # levels 0–10
│   ├── fantasy.json
│   ├── detail.json
│   └── system.json          # system_prompt_template, user_prompt_wrapper
├── rewrite/                 # LLM Text Rewriter
│   ├── modes.json           # mode_id → label, instruction, suggested_temperature
│   └── system.json          # base system, output rules, mode_order, templates
└── lyrics/                  # LLM Lyrics Generator (ACE-Step)
    ├── structures.json      # structure_name → [section markers]
    ├── choices.json         # languages, vocals, rhymes, BPM, guidance strings
    └── system.json          # system_prompt_template, user_prompt_template
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

## Notes

- Keys under rewrite `modes.json` are the ComfyUI dropdown values (stable ids).
- Use `\n` in JSON strings for multi-line instructions.
- Invalid JSON falls back to built-in minimal defaults and is logged.
