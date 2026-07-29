# Wizdroid Tools for ComfyUI

Utility nodes for ComfyUI powered by local Ollama LLMs.

## Features

### LLM Prompt Generator

Found under `Wizdroid Tools/LLM`. Expands a short concept into a polished image
generation prompt using any local Ollama model. Three sliders control the output:

- **Spice** (0-10): SFW to explicit NSFW
- **Fantasy** (0-10): photorealistic to pure surreal fantasy
- **Detail** (0-10): minimalistic to hyper-detailed

## Install

Clone into your ComfyUI custom nodes directory:

```bash
cd /path/to/ComfyUI/custom_nodes
git clone https://github.com/wizdroid/comfyui-wizdroid-tools.git
pip install -r requirements.txt
```

Ollama must be running with at least one model pulled.

## How It Works

Each slider maps to 11 distinct meta-prompt fragments injected into the system
prompt sent to the LLM. The node builds a system prompt encoding the requested
spice, fantasy, and detail levels, sends the user's concept as the generation
prompt, and returns only the final image prompt.

```
User Concept --> System Prompt (meta-prompts) --> Ollama LLM --> Image Prompt
                     ^
         +-----------+-----------+
       Spice      Fantasy     Detail
      (0-10)      (0-10)      (0-10)
```

## Thinking Model Support

Models with reasoning capabilities (`gemma`, `qwen`, `deepseek-r1`, `deepseek`,
`qwq`, `openthinking`) are detected and the internal thinking budget is set to
zero, reserving all tokens for the prompt response. Falls back to
`message.content` when the `response` field is empty.

## Project Structure

```
comfyui-wizdroid-tools/
├── __init__.py                  # Entry point, node registrations
├── pyproject.toml
├── requirements.txt
├── lib/
│   ├── constants.py             # Ollama URL, thinking model prefixes
│   ├── ollama_client.py         # Model discovery and text generation
│   └── prompts.py               # Meta-prompt system
└── nodes/
    └── llm_prompt_generator.py  # LLM Prompt Generator node
```

## License

MIT
