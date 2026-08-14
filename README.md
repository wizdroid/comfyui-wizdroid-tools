# comfyui-wizdroid-tools

ComfyUI custom nodes that talk to a local Ollama server.

Category in the UI: `Wizdroid/LLM`.

## Disclaimer

Most of this tree was generated with DeepSeek R4 and Grok 4.5.
It is AI slop. Read the code before you ship it. Do not file bugs about
"vibes". If something is wrong, the code is wrong -- fix it or ignore it.

## Requirements

- ComfyUI
- Python 3.10+
- Ollama running with at least one model pulled
- `requests` (see `requirements.txt`)

## Install

```bash
cd /path/to/ComfyUI/custom_nodes
git clone https://github.com/wizdroid/comfyui-wizdroid-tools.git
pip install -r comfyui-wizdroid-tools/requirements.txt
```

Restart ComfyUI. If you change dropdown JSON under `data/`, refresh the
browser page so `INPUT_TYPES` reloads.

Default Ollama URL: `http://localhost:11434`.

---

## Nodes

### 1. Prompt Generator

Class: `WizdroidLLMPromptGenerator`

Takes a short concept and expands it into one image-generation prompt.

| Input | Type | Notes |
|-------|------|--------|
| `ollama_url` | STRING | Ollama base URL |
| `ollama_model` | dropdown | Models from `/api/tags` |
| `user_prompt` | STRING (multiline) | Concept to expand |
| `spice` | INT 0-10 | SFW to explicit NSFW |
| `fantasy` | INT 0-10 | Photorealistic to surreal |
| `detail` | INT 0-10 | Minimal to hyper-detailed |
| `temperature` | FLOAT 0-2 | LLM temperature |
| `max_tokens` | INT 32-4096 | Output budget |
| `seed` | INT (optional) | 0 = let the model pick |

Output:

| Name | Type | Meaning |
|------|------|---------|
| `prompt` | STRING | Image prompt |

Guidance text for the three sliders lives in `data/prompts/spice.json`,
`fantasy.json`, and `detail.json`. System/user templates:
`data/prompts/system.json`.

---

### 2. Character Prompt Generator

Class: `WizdroidCharacterPrompt`

Build a character from dropdowns and free text, then emit one prompt.

Two modes:

- `use_ai=True` -- send a character JSON to Ollama, which expands it into a
  long cinematic portrait prompt (style anchor, materials, lighting, film
  language, quality + negatives). Spice / fantasy / detail still apply.
- `use_ai=False` -- concatenate resolved fields into plain English (no LLM)

If Ollama fails in AI mode, the node falls back to the template string and
appends:

```
# [AI unavailable — template fallback]
```

Every character dropdown ends with three special values:

| Value | Meaning |
|-------|---------|
| `random` | Uniform pick from the concrete list; seed is `seed + field_index` |
| `none` | Drop the field from the prompt |
| `increment` | `(seed + field_index) % len(choices)` -- deterministic walk |

Same seed and same widget values always resolve the same way.

Global inputs:

| Input | Type | Notes |
|-------|------|--------|
| `ollama_url` | STRING | Ollama base URL |
| `ollama_model` | dropdown | Models from `/api/tags` |
| `use_ai` | BOOLEAN | AI vs template (default True) |
| `seed` | INT 0..0xFFFFFFFF | Drives random/increment |
| `temperature` | FLOAT 0-2 | AI mode only |
| `max_tokens` | INT 64-4096 | AI mode only (default 1024 for the nine-layer portrait) |
| `spice` / `fantasy` / `detail` | INT 0-10 | AI mode only |

Character fields (dropdown unless noted):

| Group | Fields |
|-------|--------|
| Demographics | `gender`, `age_group`, `body_type`, `body_shape`, `height`, `skin_tone` |
| Head / face | `hair_color`, `hair_style`, `eye_color`, `face_shape`, `facial_hair`, `expression` |
| Free text | `extra_face`, `extra_hair`, `extra_jewellery`, `extra_accessories`, `lora_trigger` (STRING) |
| Camera | `camera_azimuth`, `camera_elevation`, `camera_distance` |
| Pose | `pose_position`, `pose_orientation`, `pose_style` |
| Outfit | `outfit_style`, `extra_outfit` (STRING) |
| Background | `background_setting`, `extra_background` (STRING) |
| Media | `media_type`, `media_style`, `extra_media` (STRING) |
| Override | `custom_input` (STRING multiline) |

`lora_trigger` is prepended when non-empty. Useful with Qwen Multiple-Angles
style triggers such as `<sks>`.

Output:

| Name | Type | Meaning |
|------|------|---------|
| `prompt` | STRING | Character image prompt |

Data:

- `data/character/choices.json` -- concrete dropdown values
- `data/character/system.json` -- AI system/user templates
- Reuses `data/prompts/{spice,fantasy,detail}.json` for AI guidance

---

### 3. Video Scene Generator (Text)

Class: `WizdroidLLMSceneGenerator`

Text-only scene package for AI **video** workflows (and a keyframe image prompt).

| Input | Type | Notes |
|-------|------|--------|
| `video_model` | dropdown | Target video model — picks model-specific meta prompts |
| `ollama_url` / `ollama_model` | STRING / dropdown | Text LLM (vision not required) |
| `user_prompt` | STRING multiline | Scene idea |
| `duration_seconds` | FLOAT 0.5–120 | Target clip length |
| `mood` | dropdown | From `data/scene/choices.json` |
| `style` | dropdown | cinematic, candid, anime, … |
| `temperature` / `max_tokens` | FLOAT / INT | Sampling |
| `extra_instructions` | STRING optional | Extra constraints |
| `seed` | INT optional | 0 = random |

`video_model` options: `Generic (any video model)` (default), `MiniMax
(Hailuo)`, `MiniMax H3 (Hailuo 03)`, `Hunyuan 3 (H3)`, `Wan 2.2`,
`Grok Imagine 1.5`, `LTX 2.3`. Each uses its own system/user meta prompts
tuned for that model; the generic option uses the shared templates. Add or
tweak models in `data/scene/video_models.json` (page refresh re-reads the
dropdown).

Outputs:

| Name | Meaning |
|------|---------|
| `scene_prompt` | Motion / camera / action for video models |
| `dialogue` | Spoken lines (empty if silent) |
| `image_prompt` | Still keyframe prompt (T2I → I2V) |
| `raw` | Full model response |

Data: `data/scene/choices.json`, `system.json`, `video_models.json`.

---

### 4. Video Scene Generator (Image)

Class: `WizdroidVLSceneGenerator`

Category: `🧙 Wizdroid/VL`

Vision-language scene package: **source image + user direction** → timed scene,
dialogue, and a refined keyframe prompt. Use a VL Ollama model
(`llava`, `qwen2.5-vl`, `gemma3`, `minicpm-v`, …).

| Input | Type | Notes |
|-------|------|--------|
| `video_model` | dropdown | Target video model — picks model-specific meta prompts |
| `image` | IMAGE | Source frame (ComfyUI IMAGE tensor) |
| `ollama_url` / `ollama_model` | STRING / dropdown | **Vision** model required |
| `user_prompt` | STRING multiline | Direction (empty = subtle natural motion) |
| `duration_seconds` | FLOAT 0.5–120 | Target clip length |
| `mood` / `style` | dropdown | Same catalogs as text scene node |
| `temperature` / `max_tokens` | FLOAT / INT | Sampling |
| `extra_instructions` | STRING optional | Extra constraints |
| `seed` | INT optional | 0 = random |
| `max_image_side` | INT optional | Downscale longest side before VL (default 1280) |

Same `video_model` options as the Video Scene Generator (Text) (generic +
per-model meta prompts from `data/scene/video_models.json`).

Outputs: same as Video Scene Generator (Text) (`scene_prompt`, `dialogue`,
`image_prompt`, `raw`).

---

### 5. Image Extract

Class: `WizdroidVLExtract`

Category: `🧙 Wizdroid/VL`

Vision-language **extract** from a source image: reverse prompt, outfit
flatlay, makeup, wardrobe breakdown, and more. Use a VL Ollama model
(`llava`, `qwen2.5-vl`, `gemma3`, `minicpm-v`, …).

| Input | Type | Notes |
|-------|------|--------|
| `image` | IMAGE | Source frame (ComfyUI IMAGE tensor) |
| `mode` | dropdown | What to extract (see modes below) |
| `ollama_url` / `ollama_model` | STRING / dropdown | **Vision** model required |
| `spice` | INT 0–10 | SFW → explicit NSFW (describes content *in* the image) |
| `detail` | INT 0–10 | Minimal → dense extract |
| `temperature` / `max_tokens` | FLOAT / INT | Sampling |
| `extra_instructions` | STRING optional | Focus / custom extract direction |
| `seed` | INT optional | 0 = random |
| `max_image_side` | INT optional | Downscale longest side before VL (default 1280) |

Modes (ids / labels from `data/vl_extract/modes.json`):

```
image_prompt          Image prompt (full reverse)
outfit_flatlay        Outfit / accessories flatlay
wardrobe_breakdown    Wardrobe breakdown (itemized)
makeup                Makeup description
hairstyle             Hairstyle description
accessories           Accessories inventory
jewelry_and_piercings Jewelry & piercings
tattoos_and_markings  Tattoos & body markings
pose_and_body         Pose & body
full_character        Full character appearance
scene_environment     Scene / environment
style_aesthetic       Style / aesthetic tags
custom                Custom extraction
```

`spice` reuses `data/prompts/spice.json` so high values allow accurate
adult/NSFW description of what is visible (still forbids illegal content).
Edit modes in JSON and refresh the ComfyUI page to extend the dropdown.

Outputs:

| Name | Type | Meaning |
|------|------|---------|
| `text` | STRING | Cleaned extract (prompt fragments / paragraph) |
| `raw` | STRING | Full model response before sanitize |

Data: `data/vl_extract/modes.json`, `system.json`; spice/detail from
`data/prompts/`.

---

### 6. Lyrics Generator

Class: `WizdroidLLMLyricsGenerator`

Generates ACE-Step 1.5 style lyrics and comma-separated audio tags.

Wire `lyrics` and `tags` into ComfyUI `TextEncodeAceStepAudio1.5`.

| Input | Type | Notes |
|-------|------|--------|
| `ollama_url` | STRING | Ollama base URL |
| `ollama_model` | dropdown | Models from `/api/tags` |
| `theme` | STRING (multiline) | What the song is about |
| `genre` | STRING | Tag genre |
| `mood` | STRING | Tag / lyric mood |
| `structure` | dropdown | Section layout from `data/lyrics/structures.json` |
| `language` | dropdown | Language marker; `none` skips markers |
| `vocal_type` | dropdown | Vocal tag style |
| `instrumental` | BOOLEAN | Markers only, no sung words |
| `bpm` | INT 0-220 | 0 = default for structure |
| `rhyme` | dropdown | Rhyme preference |
| `temperature` | FLOAT 0-2 | LLM temperature |
| `max_tokens` | INT 128-4096 | Output budget |
| `custom_sections` | STRING (optional) | Used when structure is `custom` |
| `extra_instructions` | STRING (optional) | Extra constraints |
| `seed` | INT (optional) | 0 = random |

Outputs:

| Name | Type | Meaning |
|------|------|---------|
| `lyrics` | STRING | Section markers + lines |
| `tags` | STRING | Comma-separated audio tags |

Data: `data/lyrics/structures.json`, `choices.json`, `system.json`.

---

### 7. Text Rewriter

Class: `WizdroidLLMTextRewriter`

Rewrites or restyles text by mode. Modes live in JSON; add your own if you want.

| Input | Type | Notes |
|-------|------|--------|
| `ollama_url` | STRING | Ollama base URL |
| `ollama_model` | dropdown | Models from `/api/tags` |
| `text` | STRING (multiline) | Source text |
| `mode` | dropdown | See modes below |
| `temperature` | FLOAT 0-2 | Lower for clean-up / formal |
| `max_tokens` | INT 64-8192 | Output budget |
| `custom_instruction` | STRING (optional) | Required for `custom`; extra rule on any mode |
| `seed` | INT (optional) | 0 = random |

Output:

| Name | Type | Meaning |
|------|------|---------|
| `text` | STRING | Rewritten text |

Built-in modes (ids from `data/rewrite/modes.json`):

```
clean_up, custom, formalize, easier_to_read, humanize, professionalize,
less_snark, less_patronizing, less_hostile, shorter, longer, way_longer,
smarter, relaxed, casual, highschooler_casual, highschooler_essay,
undergrad_casual, undergrad_essay, tipsy, drunk, pirate, uwu, gigabrain
```

`clean_up` only fixes grammar/structure. It does not invent content.
`custom` follows `custom_instruction`; empty instruction falls back to clean-up rules.

Data: `data/rewrite/modes.json`, `system.json`.

---

### 8. Presets (plugin-style)

Category: `🧙 Wizdroid/Presets`

Simple non-AI nodes: one **dropdown** of catalog items + one **details**
text field (color, material, placement, …). Output is a single prompt
fragment string.

Nodes are **generated from JSON**. Each file under `data/presets/*.json`
becomes one node. Drop in a new file, restart ComfyUI — no Python edits.
That is the plugin behaviour.

Shipped catalogs (filenames → nodes):

| File | Node |
|------|------|
| `footwear.json` | 🧙 Footwear |
| `headgear.json` | 🧙 Headgear |
| `hairstyle_extras.json` | 🧙 Hairstyle Extras |
| `expressions.json` | 🧙 Expressions |
| `makeup.json` | 🧙 Makeup |
| `eyewear.json` | 🧙 Eyewear |
| `jewelry.json` | 🧙 Jewelry |
| `piercings.json` | 🧙 Piercings |
| `tattoos.json` | 🧙 Tattoos |
| `body_markings.json` | 🧙 Body Markings |
| `gloves.json` | 🧙 Gloves |
| `nails.json` | 🧙 Nails |
| `neckwear.json` | 🧙 Neckwear |
| `tops.json` | 🧙 Tops |
| `bottoms.json` | 🧙 Bottoms |
| `outerwear.json` | 🧙 Outerwear |
| `hosiery.json` | 🧙 Hosiery |
| `bags.json` | 🧙 Bags |
| `accessories.json` | 🧙 Accessories |
| `props.json` | 🧙 Props |
| `weapons.json` | 🧙 Weapons |
| `goth_sets.json` | 🧙 Complete Goth Set |
| `characters.json` | 🧙 Character Set |
| `anime_cosplay.json` | 🧙 Anime Cosplay Set |

| Input | Type | Notes |
|-------|------|--------|
| `item` | dropdown | Catalog entry; `none` / `random` / `increment` (same meaning as character dropdowns) |
| `details` | STRING | Free-text extras (color, material, …) |
| `seed` | INT 0..0xFFFFFFFF | Drives `random` and `increment` |

| Output | Type | Meaning |
|--------|------|---------|
| `text` | STRING | Fragment, e.g. `combat boots, matte black leather` |

See `data/presets/README.md` for schema and how to ship your own catalog.

---

### 9. Load Image from URL

Category: `🧙 Wizdroid/Utils` — non-AI utility node.

Downloads an image from a **web URL** and outputs a ComfyUI `IMAGE` + `MASK`
pair with the same shape as the core `LoadImage` node, so it plugs straight
into any existing workflow (img2img, ControlNet, VL image extract, …).

Works with:

- **Direct image links** — `https://i.pinimg.com/originals/.../photo.jpg`,
  any `*.jpg/png/webp/gif` URL.
- **Web pages** — paste a Pinterest pin page
  (`https://www.pinterest.com/pin/12345/`) and it auto-extracts the page's
  `og:image` meta tag (works for most sites with social previews).

Pinterest / hotlink-protected sites: pass `https://www.pinterest.com/` (or
the site root) as the **referer** to satisfy basic hotlink protection.
Direct `*.pinimg.com` image URLs are the most reliable path.

| Input | Type | Notes |
|-------|------|--------|
| `url` | STRING | Image URL or page URL |
| `referer` (opt) | STRING | HTTP Referer header for hotlink-protected sites |
| `timeout` (opt) | INT | Seconds, default 30 |
| `cache_to_disk` (opt) | BOOLEAN | Save a copy to the ComfyUI temp dir |

| Output | Type | Meaning |
|--------|------|---------|
| `image` | IMAGE | RGB tensor, `[B, H, W, 3]` |
| `mask` | MASK | Alpha-derived mask (`1 - alpha`), ones if no alpha |
| `width` | INT | Image width |
| `height` | INT | Image height |

Note: this node downloads whatever URL you point it at — only use it with
links you are allowed to use.

---

### 10. Prompt from Website

Category: `🧙 Wizdroid/LLM`

Fetch a web page that describes a **character** (bio, lore page, wiki,
character sheet, …), extract its readable text, and let Ollama turn that
into a detailed **image prompt** for the character — using the same
`spice` / `fantasy` / `detail` meta-prompts as the Prompt Generator.

Pipeline: `URL → page text (og:title / og:description + body) → Ollama →
single-paragraph character image prompt`.

| Input | Type | Notes |
|-------|------|--------|
| `ollama_url` / `ollama_model` | STRING / dropdown | Ollama server + model |
| `url` | STRING | Website URL describing the character |
| `max_chars` | INT | Cap on extracted text sent to the LLM (default 4000) |
| `spice` | INT 0–10 | SFW → explicit NSFW |
| `fantasy` | INT 0–10 | Photoreal → pure fantasy |
| `detail` | INT 0–10 | Minimal → hyper-detailed |
| `temperature` | FLOAT | LLM sampling |
| `max_tokens` | INT | Output budget |
| `seed` (opt) | INT | 0 = random |
| `referer` (opt) | STRING | HTTP Referer for protected sites |

| Output | Type | Meaning |
|--------|------|---------|
| `prompt` | STRING | Generated character image prompt |
| `website_text` | STRING | Extracted page text (debugging / reuse) |

Tip: for JS-rendered pages (e.g. Pinterest's client UI) prefer a URL whose
`og:description` is populated, since the body text may otherwise be empty.

---

### 11. Batch Image Captioner (LoRA dataset prep)

Category: `🧙 Wizdroid/VL`

Point at a **folder of images**; a vision-language model writes a
`<name>.txt` caption next to each image — exactly what you need to build a
training set for LoRA/dreambooth. Skips images that already have a caption
(unless overwrite is on), and can recurse into subfolders.

| Input | Type | Notes |
|-------|------|--------|
| `folder_path` | STRING | Absolute path to the image folder |
| `ollama_url` / `ollama_model` | STRING / dropdown | VL model required |
| `caption_mode` | dropdown | Booru tags / natural sentence / detailed / short (from `data/batch_caption/modes.json`) |
| `temperature` | FLOAT | Lower for faithful captions |
| `max_tokens` | INT | Caption length budget |
| `max_images` | INT | Cap per run |
| `max_image_side` | INT | Downscale before sending |
| `overwrite` | BOOLEAN | Re-caption existing `.txt` |
| `recursive` | BOOLEAN | Include subfolders |
| `extra_instructions` (opt) | STRING | e.g. `always include the character name` |

| Output | Type | Meaning |
|--------|------|---------|
| `report` | STRING | Counts + errors summary |
| `last_caption` | STRING | Last caption written |
| `processed` / `failed` | INT | Counts |

---

### 12. Image Critique

Category: `🧙 Wizdroid/VL`

Feed a generated **IMAGE** + the **prompt** that made it; a VL model critiques
it and writes a **revised, improved prompt**. Focus dropdown (general, anatomy,
composition, lighting, style fidelity) from `data/critique/modes.json`.

| Input | Type | Notes |
|-------|------|--------|
| `image` | IMAGE | Generated image to critique |
| `prompt` | STRING | The prompt used |
| `focus` | dropdown | Critique focus area |
| `extra_instructions` (opt) | STRING | e.g. `fix the hands` |
| `seed`, `max_image_side` (opt) | INT | Reproducibility / downscale |

| Output | Type | Meaning |
|--------|------|---------|
| `critique` | STRING | Concise critique bullet points |
| `revised_prompt` | STRING | Improved prompt |
| `raw` | STRING | Full model response |

---

### 13. Image Prompt Refiner

Category: `🧙 Wizdroid/LLM`

Iteratively refine an image prompt with a change request. Wire the
`refined_prompt` back into `current_prompt` for a loop, or turn on
**session memory** — the node remembers the last refined prompt per
`session_id` and uses it as the base on the next run. Optionally attach a
reference **IMAGE** so the VL model can see what it's iterating on.

| Input | Type | Notes |
|-------|------|--------|
| `current_prompt` | STRING | Prompt to refine (or stored one with memory) |
| `instruction` | STRING | What to change, e.g. `make the lighting dramatic` |
| `image` (opt) | IMAGE | Reference image (needs a VL model) |
| `use_session_memory` | BOOLEAN | Remember last refined prompt per `session_id` |
| `session_id` | STRING | Memory key |
| `clear_memory` (opt) | BOOLEAN | Reset the session before refining |
| `extra_instructions`, `seed`, `max_image_side` (opt) | – | Extras |

| Output | Type | Meaning |
|--------|------|---------|
| `refined_prompt` | STRING | The refined prompt |
| `revision_note` | STRING | One-line summary of what changed |
| `raw` | STRING | Full model response |

> **Note on thinking models (qwen3, gemma, …):** these can spend a large token
> budget on internal reasoning before answering. The Ollama client now retries
> automatically with a larger budget, so results are correct but can be slower.
> If a run times out, try a model with more headroom or lower `max_tokens`.

---

## Data directory

Nothing important is hard-coded. Edit JSON, save, refresh the ComfyUI page
(for existing dropdowns). **New** preset files need a ComfyUI restart.

```
data/
  prompts/      # image prompt generator + character AI guidance
  character/    # character dropdowns + templates
  scene/        # video scene mood/style + VL/text templates
  vl_extract/   # VL image extract modes + system templates
  lyrics/       # ACE-Step structures, choices, templates
  rewrite/      # text rewriter modes + templates
  website/      # website → character image prompt meta-prompts
  batch_caption/ # batch captioner modes + templates
  critique/     # image critique focus modes + templates
  refine/       # iterative prompt refiner templates
  presets/      # plugin-style preset catalogs (one JSON → one node)
```

JSON is reloaded when mtime changes. Invalid JSON falls back to small
in-code defaults and logs a warning. See `data/README.md` for edit examples.

## Ollama client notes

- Model list is cached briefly so the UI does not hammer `/api/tags`
- Thinking-style models (name contains `gemma`, `qwen`, `deepseek`, `qwq`,
  `openthinking`, etc.) get thinking disabled so tokens go to the answer
- Empty `response` may fall back to chat-style `message.content`

## Layout

```
comfyui-wizdroid-tools/
  __init__.py                 # node registration
  requirements.txt
  data/                       # all editable prompts and choices
  lib/
    ollama_client.py          # /api/tags + /api/generate (+ VL images)
    json_data.py              # mtime-cached JSON load
    constants.py
    prompts.py                # image prompt templates
    character_prompts.py      # character resolve + template
    scene_prompts.py          # video scene text/VL templates
    vl_extract_prompts.py     # VL image extract modes
    lyrics_prompts.py
    rewrite_prompts.py
    presets.py                # discover + format preset catalogs
  nodes/
    llm_prompt_generator.py
    llm_character_prompt.py
    llm_scene_generator.py    # text → video scene package
    llm_vl_scene_generator.py # image + text → video scene package
    llm_vl_extract.py         # image → prompt / flatlay / makeup / …
    llm_lyrics_generator.py
    llm_text_rewriter.py
    llm_qwen_multi_angles.py
    preset_nodes.py           # dynamic nodes from data/presets/
```

## License

MIT
