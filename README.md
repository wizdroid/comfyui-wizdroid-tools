# Wizdroid Tools for ComfyUI

Utility nodes for ComfyUI powered by local Ollama LLMs.

## Features

### LLM Prompt Generator

Found under `Wizdroid/LLM`. Expands a short concept into a polished image
generation prompt using any local Ollama model. Three sliders control the output:

- **Spice** (0-10): SFW to explicit NSFW
- **Fantasy** (0-10): photorealistic to pure surreal fantasy
- **Detail** (0-10): minimalistic to hyper-detailed

### LLM Lyrics Generator (ACE-Step)

Found under `Wizdroid/LLM`. Turns a song theme into **ACE-Step 1.5** ready outputs:

| Output | Use for |
|--------|---------|
| `lyrics` | Structured sections (`[verse]`, `[chorus]`, …) + short singable lines |
| `tags` | Comma-separated audio keywords (genre, instruments, vocals, BPM) |

Wire both into ComfyUI's **TextEncodeAceStepAudio1.5** (`tags` + `lyrics`).

Inputs include theme, genre, mood, structure template, language marker, vocal
type, instrumental mode, BPM, rhyme scheme, and optional extra instructions.

### LLM Text Rewriter

Found under `Wizdroid/LLM`. Mode-based text converter (Perchance-style presets)
powered by your local Ollama model:

| Mode | Effect |
|------|--------|
| `clean_up` (default) | Fix grammar/spelling + restructure; **no new content** |
| `custom` | Follow free-form `custom_instruction` |
| Style presets | Formalize, easier to read, humanize, professional-ize, less snark / patronizing / hostile, shorter, longer, way longer, smarter, relaxed, casual, highschooler / undergrad (casual + essay), tipsy, drunk, pirate, UwU, gigabrain |

Optional `custom_instruction` also layers extra constraints on any preset.

## Install

Clone into your ComfyUI custom nodes directory:

```bash
cd /path/to/ComfyUI/custom_nodes
git clone https://github.com/wizdroid/comfyui-wizdroid-tools.git
pip install -r requirements.txt
```

Ollama must be running with at least one model pulled.

## How It Works

### Customizable meta-prompts (`data/`)

**All** system prompts, mode instructions, slider fragments, song structures, and
dropdown choices are JSON under `data/`. Python reloads them when files change
(mtime cache). Edit JSON → save → refresh the ComfyUI page.

| Path | Used by |
|------|---------|
| `data/prompts/*.json` | Image Prompt Generator (spice/fantasy/detail + templates) |
| `data/rewrite/modes.json` | Text Rewriter modes (add your own keys) |
| `data/rewrite/system.json` | Rewriter base rules, `mode_order`, user template |
| `data/lyrics/structures.json` | Song section templates |
| `data/lyrics/choices.json` | Languages, vocals, rhymes, BPM defaults, guidance |
| `data/lyrics/system.json` | ACE-Step system/user prompt templates |

See [`data/README.md`](data/README.md) for examples (new rewrite mode, new structure).

### Image prompts

Each slider maps to fragments in `data/prompts/{spice,fantasy,detail}.json`.

### Lyrics (ACE-Step)

```
Theme + genre/mood/structure --> Ollama --> lyrics + tags --> ACE-Step encoder
```

### Text rewrite

```
Text + mode [+ custom instruction] --> Ollama --> rewritten text
```

## Thinking Model Support

Models with reasoning capabilities (`gemma`, `qwen`, `deepseek-r1`, `deepseek`,
`qwq`, `openthinking`) are detected and the internal thinking budget is set to
zero, reserving all tokens for the response. Falls back to `message.content`
when the `response` field is empty.

## Project Structure

```
comfyui-wizdroid-tools/
├── __init__.py
├── data/
│   ├── README.md                   # How to edit / extend meta-prompts
│   ├── prompts/                    # Image prompt generator JSON
│   ├── rewrite/                    # Text rewriter modes + system JSON
│   └── lyrics/                     # ACE-Step structures + prompts JSON
├── lib/
│   ├── json_data.py                # mtime-cached JSON loader
│   ├── constants.py
│   ├── ollama_client.py
│   ├── prompts.py                  # Loads data/prompts/
│   ├── lyrics_prompts.py           # Loads data/lyrics/
│   └── rewrite_prompts.py          # Loads data/rewrite/
└── nodes/
    ├── llm_prompt_generator.py
    ├── llm_lyrics_generator.py
    └── llm_text_rewriter.py
```

## License

MIT
