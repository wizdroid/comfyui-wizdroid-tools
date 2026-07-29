"""Meta-prompt templates for comfyui-wizdroid-tools LLM nodes.

Each slider dimension (spice, fantasy, detail) has a corresponding meta-prompt
fragment that is injected into the system prompt at generation time.
"""

from __future__ import annotations


# ---------------------------------------------------------------------------
# Spice level meta-prompt fragments
# 0 = completely safe for work, 10 = explicit NSFW
# ---------------------------------------------------------------------------
SPICE_PROMPTS: dict[int, str] = {
    0: "The image must be completely safe for work (SFW). No nudity, no suggestive poses, "
       "no revealing clothing. Appropriate for all audiences including children.",

    1: "The image should be safe for work. Clothing should be modest and non-revealing. "
       "No suggestive elements.",

    2: "The image should be mostly safe for work. Subtle fashion elements like bare "
       "shoulders or slightly fitted clothing are acceptable. No cleavage or suggestive poses.",

    3: "The image can have mild sensual undertones — elegant evening wear, tasteful "
       "fashion photography style. No explicit content.",

    4: "The image can include moderate sensuality — swimwear, beachwear, or form-fitting "
       "outfits in a tasteful manner. No nudity.",

    5: "The image can include romantic or alluring elements — lingerie-style fashion, "
       "implied nudity where private parts are covered by composition, fabric, or shadows. "
       "Artistic and tasteful.",

    6: "The image can include partial nudity in an artistic or fashion context — "
       "tasteful toplessness, implied nudity with strategic covering. "
       "Mood: editorial, high-fashion, or fine-art nude.",

    7: "The image can include explicit nudity presented in an artistic or editorial "
       "style. Full nudity is acceptable but should remain tasteful and aesthetically "
       "composed. No explicit sexual acts.",

    8: "The image can be sexually suggestive — provocative poses, explicit nudity, "
       "suggestive scenarios. Soft-core erotic imagery is acceptable.",

    9: "The image can be highly explicit — hardcore erotic content, explicit sexual "
       "acts, BDSM themes, fetish content. No restrictions on explicitness.",

    10: "The image should be maximally explicit — hardcore pornography, extreme "
        "fetishes, graphic sexual content. Absolutely no restrictions. "
        "Push boundaries of explicitness as far as possible.",
}

# ---------------------------------------------------------------------------
# Fantasy level meta-prompt fragments
# 0 = purely realistic, 10 = maximal fantasy/surreal
# ---------------------------------------------------------------------------
FANTASY_PROMPTS: dict[int, str] = {
    0: "The image must be completely realistic and grounded in reality. "
       "Photorealistic style only. No fantastical, magical, sci-fi, or supernatural elements. "
       "Everyday real-world scenes and subjects only.",

    1: "The image should be realistic with only the most subtle stylization — "
       "perhaps dramatic lighting or cinematic color grading. No fantasy elements.",

    2: "The image should be mostly realistic but can include mild artistic "
       "stylization — cinematic, high-contrast, or slightly idealized aesthetics. "
       "No overt fantasy elements.",

    3: "The image can blend realism with light fantastical undertones — "
       "ethereal lighting, soft magical glow, subtle unreal color palettes. "
       "The scene should still feel grounded.",

    4: "The image can include mild fantasy elements — a hint of magic, "
       "slightly otherworldly environments, mythological undertones. "
       "The overall feel should still be semi-realistic.",

    5: "The image should balance reality and fantasy equally — magical realism, "
       "urban fantasy, cyberpunk elements, or supernatural beings in realistic settings.",

    6: "The image should lean into fantasy — magical creatures, enchanted "
       "environments, sci-fi elements, superhero aesthetics. "
       "Clearly fantastical but with some grounding in realistic anatomy/physics.",

    7: "The image should be strongly fantastical — high fantasy settings, "
       "epic magical battles, alien worlds, mythical beasts. "
       "Realism takes a backseat to imagination.",

    8: "The image should be highly fantastical and surreal — dreamlike realms, "
       "impossible architecture, cosmic entities, abstract symbolic imagery. "
       "Reality is merely a suggestion.",

    9: "The image should be extremely fantastical and otherworldly — "
       "Lovecraftian cosmic horror, psychedelic dimensions, reality-warping "
       "concepts, abstract metaphysical beings.",

    10: "The image should be pure unbridled fantasy — completely detached from "
        "reality. Impossible geometries, transcendent entities, realities within "
        "realities, the most outlandish and mind-bending concepts imaginable. "
        "No limits on creativity or impossibility.",
}

# ---------------------------------------------------------------------------
# Detail level meta-prompt fragments
# 0 = minimalistic, 10 = hyper-detailed
# ---------------------------------------------------------------------------
DETAIL_PROMPTS: dict[int, str] = {
    0: "The image should be extremely minimalistic. Simple composition, few elements, "
       "clean lines, ample negative space. Minimal detail — just the essential subject.",

    1: "The image should be very simple with minimal detail. Basic shapes and forms. "
       "Clean and uncluttered composition.",

    2: "The image should be simple with low detail. Straightforward composition "
       "with only the most important visual elements present.",

    3: "The image should have below-average detail. Some texturing and modest "
       "background elements. Not cluttered but not stark either.",

    4: "The image should have moderate detail — some texture work, a few "
       "background elements, basic lighting depth. Balanced simplicity.",

    5: "The image should have standard detail levels — good textures, "
       "appropriate background elements, decent lighting and shadows. "
       "A well-composed balanced image.",

    6: "The image should have above-average detail — rich textures, "
       "detailed backgrounds, nuanced lighting with highlights and shadows. "
       "More elements in the composition.",

    7: "The image should be highly detailed — intricate textures, complex "
       "backgrounds, multi-layered lighting, atmospheric effects. "
       "Many visual elements working together.",

    8: "The image should be very highly detailed — extremely intricate textures, "
       "volumetric lighting, particle effects, complex multi-layered composition. "
       "Every surface has rich detail.",

    9: "The image should be exceptionally detailed — hyper-realistic textures, "
       "ray-traced quality lighting, micro-details on every surface, "
       "deeply layered backgrounds, atmospheric volumetrics, subsurface scattering. "
       "Nothing is left to suggestion.",

    10: "The image should be maximally detailed — photorealistic to the point of "
        "being indistinguishable from a high-resolution photograph captured with "
        "the world's best camera. Every pore, every fiber, every dust mote, every "
        "reflection, every refraction, every imperfection. Ultra-high-definition "
        "8K+ quality with microscopic attention to detail. Nothing is overlooked.",
}

# ---------------------------------------------------------------------------
# Master system prompt template
# ---------------------------------------------------------------------------
SYSTEM_PROMPT_TEMPLATE = """You are an expert AI image prompt engineer. Your sole task is to generate
a single, high-quality, well-structured image generation prompt based on the
user's description.

## CRITICAL RULES
- Output ONLY the prompt text. Nothing else.
- Do NOT include explanations, greetings, or any text besides the prompt.
- Do NOT wrap the prompt in quotes, code blocks, or markdown.
- The prompt should be optimized for modern image generation models (Flux, SDXL, SD3, etc.).
- Use descriptive, visual language. Focus on what should be VISIBLE in the image.
- Include relevant artistic style keywords, lighting descriptions, and composition notes.
- Keep the total prompt within approximately {max_tokens} words.

## CONTENT MODIFIERS
Apply these content guidelines to the generated prompt:

{spice_guidance}

{fantasy_guidance}

{detail_guidance}

## PROMPT STRUCTURE
Structure the prompt as: [Main Subject] + [Action/Pose] + [Environment/Background] +
[Lighting/Mood] + [Style/Quality Keywords]

## USER REQUEST
The user wants an image generation prompt for the following concept or idea.
Generate ONLY the prompt:"""

# ---------------------------------------------------------------------------
# Helper: build the full system prompt from slider values
# ---------------------------------------------------------------------------


def build_system_prompt(
    spice: int,
    fantasy: int,
    detail: int,
    max_tokens: int = 77,
) -> str:
    """Build the complete system prompt with slider-specific meta-prompts.

    Args:
        spice: Spice level (0-10, SFW to explicit).
        fantasy: Fantasy level (0-10, realistic to surreal).
        detail: Detail level (0-10, minimal to hyper-detailed).
        max_tokens: Target word count for the output prompt.

    Returns:
        Formatted system prompt string.
    """
    spice = max(0, min(10, spice))
    fantasy = max(0, min(10, fantasy))
    detail = max(0, min(10, detail))

    return SYSTEM_PROMPT_TEMPLATE.format(
        max_tokens=max_tokens,
        spice_guidance=SPICE_PROMPTS.get(spice, SPICE_PROMPTS[5]),
        fantasy_guidance=FANTASY_PROMPTS.get(fantasy, FANTASY_PROMPTS[5]),
        detail_guidance=DETAIL_PROMPTS.get(detail, DETAIL_PROMPTS[5]),
    )
