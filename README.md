# comfyui-wizdroid-tools

ComfyUI custom nodes that talk to a local Ollama server.

Category in the UI: `Wizdroid/LLM`.

## Disclaimer

Most of this tree was generated with DeepSeek R4 and Grok 4.5.
It is AI slop. Read the code before you ship it. Do not file bugs about
"vibes". If something is wrong, the code is wrong -- fix it or ignore it.

**This is work in progress.** Nodes can break at any time. If a node
malfunctions or shows stale inputs after an update, refresh your nodes in
ComfyUI (click the "Refresh" button on the node graph / press `R`, or
restart ComfyUI) before reporting an issue.

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

Takes a short concept and expands it into one [Krea 2](https://github.com/krea-ai/krea-2/blob/main/docs/prompting.md)
natural-language image prompt (subject → pose → setting → lighting → camera).

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
  long [Krea 2](https://github.com/krea-ai/krea-2/blob/main/docs/prompting.md)
  portrait paragraph (subject, materials, pose, lighting, camera). Spice /
  fantasy / detail still apply.
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

### 2b. High-Energy Portrait

Class: `WizdroidHighEnergyPortrait`

Fill the **Universal High-Energy Portrait Template** from slot inputs.
AI mode writes a [Krea 2](https://github.com/krea-ai/krea-2/blob/main/docs/prompting.md)
natural-language paragraph (subject → light → camera), not labeled sections.

Two modes:

- `use_ai=True` -- send the provided slots plus the template skeleton to
  Ollama, which formats a finished prompt. Empty slots are invented to
  match the genre; filled slots are never contradicted.
- `use_ai=False` -- mechanical fill of the template (JSON defaults for
  missing slots, no network).

If Ollama fails in AI mode, the node falls back to the mechanical fill
and appends `# [AI unavailable — template fallback]`.

`variant`:

| Value | Output |
|-------|--------|
| `full` | Section headers (Style / Genre Anchor, Subject & Energy, …) |
| `compact` | One dense paragraph, no headers |

Quick-fill fields map to the template's bracketed slots. Type a custom
style in `style_custom` to override the `style_genre` dropdown (e.g.
`cyberpunk neon noir`). Dropdowns support `none` / `random` / `increment`
like the character node. Wire preset fragments into `clothing`,
`accessories`, `hair`, or `makeup`.

| Group | Fields |
|-------|--------|
| Controls | `ollama_url`, `ollama_model`, `use_ai`, `variant`, `seed`, `temperature`, `max_tokens`, `spice` / `fantasy` / `detail`, `lora_trigger` |
| Style anchor | `style_genre`, `style_custom`, `adjective`, `character_type`, `shot_type` |
| Subject | `gender`, `presence`, `energy`, `facial_features` |
| Outfit | `clothing`, `materials`, `fabric_light`, `silhouette`, `cut_details` |
| Styling | `accessories`, `hair`, `makeup` |
| Pose | `pose_energy`, `pose_angle`, `body_language` |
| Light | `lighting_type`, `fill`, `colors`, `background`, `film_stock` |
| Extra | `extra_instructions` |

Output:

| Name | Type | Meaning |
|------|------|---------|
| `prompt` | STRING | High-energy portrait prompt |

Data: `data/portrait/choices.json`, `data/portrait/system.json`; spice /
fantasy / detail from `data/prompts/`.

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
clean_up, custom, qwen_image, qwen_image_en, qwen_image_zh, flux_klein,
flux_klein_edit, krea_2, photo_portrait, photo_editorial, photo_cinematic,
photo_candid, photo_studio, photo_beauty, photo_glamour, photo_boudoir,
photo_figure, photo_technical, photo_eroticize, photo_sexualize, formalize, easier_to_read, humanize,
professionalize, shorter, longer, way_longer, smarter, relaxed, casual,
undergrad_essay
```

`clean_up` only fixes grammar/structure. It does not invent content.
`custom` follows `custom_instruction`; empty instruction falls back to clean-up rules.

**Qwen-Image modes** (official [`rewrite()`](https://github.com/QwenLM/Qwen-Image/blob/a76c8a3873c369a097aafd7ea229b7404659043c/src/examples/tools/prompt_utils.py#L183)):

| Mode | What it does |
|------|----------------|
| `qwen_image` | Auto EN/ZH (CJK sniff) + official optimizer + magic suffix |
| `qwen_image_en` | Force English polish + `Ultra HD, 4K, cinematic composition` |
| `qwen_image_zh` | Force Chinese polish + `超清，4K，电影级构图` |

Wire `text` out into a Qwen-Image sampler. Templates live in
`data/qwen_image/system.json`.

**FLUX.2 [klein] 9B modes** (official prompt upsampling from the
[BFL Hugging Face space](https://huggingface.co/spaces/black-forest-labs/FLUX.2-klein-9B)):

| Mode | What it does |
|------|----------------|
| `flux_klein` | T2I upsample — more descriptive paragraphs, quoted on-image text, keep subject/intent |
| `flux_klein_edit` | Edit instruction — one concise 50–80 word instruction (what changes + what stays) |

Klein does **not** auto-enhance prompts, so this mode is the upsampler the
official 9B demo uses. Templates: `data/flux_klein/system.json`.

**Krea 2** (official [`expansion.txt`](https://github.com/krea-ai/krea-2/blob/main/docs/expansion.txt)
from the [prompting guide](https://github.com/krea-ai/krea-2/blob/main/docs/prompting.md)):

| Mode | What it does |
|------|----------------|
| `krea_2` | One long natural-language paragraph: subject → attributes → action → setting → lighting → camera → medium. Quote on-image text. |

Photography modes and the High-Energy Portrait AI writer use the same Krea 2
shape (one cohesive paragraph, no headers).

**Photography modes** (SFW and NSFW — they keep whatever the source already is,
and recast it as a shootable photograph):

| Mode | What it does |
|------|----------------|
| `photo_portrait` | Face-first portrait: shot scale, eye-line, key/fill/rim |
| `photo_editorial` | Fashion editorial: silhouette, fabric, styling, location |
| `photo_cinematic` | One movie still: blocking, lens, motivated light, grade |
| `photo_candid` | Documentary / street: available light, observed moment |
| `photo_studio` | Controlled setup: modifiers, Rembrandt / clamshell / etc. |
| `photo_beauty` | Tight beauty: skin, makeup, catchlights, DOF |
| `photo_glamour` | Glossy glamour (celebrity cover → adult glamour) |
| `photo_boudoir` | Intimate in-room: window light, fabric, skin |
| `photo_figure` | Body as form: pose, volume, figure-study light |
| `photo_technical` | Same scene, more camera/film/lens language |
| `photo_eroticize` | Add heat: sensual pose, skin, half-undress (medium explicit) |
| `photo_sexualize` | Push explicit: anatomy, sex act, fluids — still a still photo |

Shared SFW/NSFW rules live in `data/rewrite/system.json` (`photography_rules`).
Output shape follows the Krea 2 guide (one natural-language paragraph).

Data: `data/rewrite/modes.json`, `system.json`; model-specific wording in
`data/qwen_image/system.json`, `data/flux_klein/system.json`, and
`data/krea/system.json`.

---

### 8. Presets (plugin-style)

Simple non-AI nodes: one **dropdown** of catalog items + one **details**
text field (color, material, placement, …) + a `seed`. Output is a single
prompt fragment string.

Nodes are **generated from JSON**. Each file under `data/presets/` becomes
its own node, and the folder it lives in decides which submenu it appears
under. Drop in a new file, restart ComfyUI — no Python edits. That is the
plugin behaviour.

| Folder | Node category |
|--------|---------------|
| `parts/` | `🧙 Wizdroid/Presets/Parts` |
| `sets/female/` | `🧙 Wizdroid/Presets/Sets/Female` |
| `sets/male/` | `🧙 Wizdroid/Presets/Sets/Male` |
| `sets/unisex/` | `🧙 Wizdroid/Presets/Sets/Unisex` |
| root (`*.json`) | `🧙 Wizdroid/Presets` |

Shipped catalogs (file → node):

| Category | File | Node |
|----------|------|------|
| parts | `footwear.json` | 🧙 Footwear |
| parts | `headgear.json` | 🧙 Headgear |
| parts | `hairstyle_extras.json` | 🧙 Hairstyle Extras |
| parts | `expressions.json` | 🧙 Expressions |
| parts | `makeup.json` | 🧙 Makeup |
| parts | `eyewear.json` | 🧙 Eyewear |
| parts | `jewelry.json` | 🧙 Jewelry |
| parts | `piercings.json` | 🧙 Piercings |
| parts | `tattoos.json` | 🧙 Tattoos |
| parts | `body_markings.json` | 🧙 Body Markings |
| parts | `gloves.json` | 🧙 Gloves |
| parts | `nails.json` | 🧙 Nails |
| parts | `neckwear.json` | 🧙 Neckwear |
| parts | `tops.json` | 🧙 Tops |
| parts | `bottoms.json` | 🧙 Bottoms |
| parts | `outerwear.json` | 🧙 Outerwear |
| parts | `hosiery.json` | 🧙 Hosiery |
| parts | `bags.json` | 🧙 Bags |
| parts | `accessories.json` | 🧙 Accessories |
| parts | `props.json` | 🧙 Props |
| parts | `weapons.json` | 🧙 Weapons |
| sets/female | `goth_sets.json` | 🧙 Complete Goth Set |
| sets/female | `bollywood-80s.json` | 🧙 1980s Bollywood Disco Set |
| sets/female | `candid_mini_dresses.json` | 🧙 Candid Mini Dress Set |
| sets/female | `glamorous_bodycon_dresses.json` | 🧙 Glamorous Bodycon Dress Set |
| sets/female | `indian_casual_everyday.json` | 🧙 Indian Casual Everyday Set |
| sets/female | `indian_chudidar_sets.json` | 🧙 Indian Chudidar Set |
| sets/female | `indian_lehenga_sets.json` | 🧙 Indian Lehenga Set |
| sets/female | `indian_sari_drapes.json` | 🧙 Indian Sari Drape Set |
| sets/unisex | `characters.json` | 🧙 Character Set |
| sets/unisex | `anime_cosplay.json` | 🧙 Anime Cosplay Set |

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

### 14. Sampler × Scheduler Sweep

Category: `🧙 Wizdroid/Utils` — non-AI utility node.

Class: `WizdroidSamplerSchedulerSweep`

Run every `sampler × scheduler` pair **one at a time** (not a list-map),
sleep between combos so the GPU can cool down, burn `sampler | scheduler`
onto each image, and save:

`output/{prefix}/{sampler}__{scheduler}_00001_.png`

Keep **seed = fixed** so every combo uses the same noise.

| Input | Type | Notes |
|-------|------|--------|
| `model` / `positive` / `negative` / `latent_image` / `vae` | sockets | Same as KSampler + decode |
| `seed` | INT | Use `fixed` for a fair comparison |
| `steps` / `cfg` / `denoise` | INT / FLOAT | Turbo Krea2: 8 / 1 / 1 |
| `samplers` | STRING (multiline) | One sampler per line |
| `schedulers` | STRING (multiline) | One scheduler per line |
| `cooldown_seconds` | FLOAT | Pause after each combo (default 1s) |
| `overlay` | BOOLEAN | Stamp the pair name on the image |
| `filename_prefix` | STRING | Output subfolder, default `krea2-sweep` |
| `use_all_installed` (opt) | BOOLEAN | Ignore the lists; sweep every installed sampler/scheduler |
| `skip_names` (opt) | STRING | Always skip these (`dpm_adaptive` etc.) |
| `continue_on_error` (opt) | BOOLEAN | Skip a failing pair and keep going |

| Output | Type | Meaning |
|--------|------|---------|
| `images` | IMAGE | Successful labeled frames, batched |
| `report` | STRING | `OK` / `FAIL` / `OOM` / `SKIP` per pair |

---

## Data directory

Nothing important is hard-coded. Edit JSON, save, refresh the ComfyUI page
(for existing dropdowns). **New** preset files need a ComfyUI restart.

```
data/
  prompts/      # image prompt generator + character AI guidance
  character/    # character dropdowns + templates
  portrait/     # high-energy portrait template + slot dropdowns
  qwen_image/   # official Qwen-Image rewrite() / polish_edit_prompt templates
  flux_klein/   # official FLUX.2 [klein] 9B prompt upsampling
  krea/         # official Krea 2 expansion.txt
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
    portrait_prompts.py       # high-energy portrait template fill
    scene_prompts.py          # video scene text/VL templates
    vl_extract_prompts.py     # VL image extract modes
    lyrics_prompts.py
    rewrite_prompts.py
    qwen_image_prompts.py     # official Qwen-Image rewrite / edit polish
    flux_klein_prompts.py     # official FLUX.2 [klein] 9B upsampling
    krea_prompts.py           # official Krea 2 expansion
    presets.py                # discover + format preset catalogs
  nodes/
    llm_prompt_generator.py
    llm_character_prompt.py
    llm_high_energy_portrait.py  # Universal High-Energy Portrait Template
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
