"""Wizdroid Tools — Qwen Multi-Angles LoRA Prompt Builder.

Non-AI utility node that builds a properly formatted prompt string for the
fal/Qwen-Image-Edit-2511-Multiple-Angles-LoRA (96 camera poses).
"""

from __future__ import annotations

from typing import Any, Dict, Tuple

# ---------------------------------------------------------------------------
# Camera pose definitions (matches the LoRA's 96 poses)
# ---------------------------------------------------------------------------

AZIMUTHS: Dict[str, str] = {
    "front view (0°)": "front view",
    "front-right quarter view (45°)": "front-right quarter view",
    "right side view (90°)": "right side view",
    "back-right quarter view (135°)": "back-right quarter view",
    "back view (180°)": "back view",
    "back-left quarter view (225°)": "back-left quarter view",
    "left side view (270°)": "left side view",
    "front-left quarter view (315°)": "front-left quarter view",
}

ELEVATIONS: Dict[str, str] = {
    "low-angle shot (-30°)": "low-angle shot",
    "eye-level shot (0°)": "eye-level shot",
    "elevated shot (30°)": "elevated shot",
    "high-angle shot (60°)": "high-angle shot",
}

DISTANCES: Dict[str, str] = {
    "close-up (×0.6)": "close-up",
    "medium shot (×1.0)": "medium shot",
    "wide shot (×1.8)": "wide shot",
}


class WizdroidQwenMultiAngles:
    """Build a prompt string for the Qwen-Image-Edit-2511 Multiple-Angles LoRA.

    This is a **non-AI** node — it constructs the prompt purely from dropdown
    selections. Combine it with a Qwen-Image-Edit-2511 workflow that loads
    the LoRA weights from:
    https://huggingface.co/fal/Qwen-Image-Edit-2511-Multiple-Angles-LoRA

    Prompt format: ``<sks> [azimuth] [elevation] [distance]``
    """

    CATEGORY = "🧙 Wizdroid/Utils"
    RETURN_TYPES = ("STRING", "FLOAT", "STRING")
    RETURN_NAMES = ("prompt", "lora_strength", "camera_label")
    FUNCTION = "build_prompt"
    OUTPUT_NODE = False
    DESCRIPTION = (
        "Build a multi-angle camera prompt for the Qwen-Image-Edit-2511 "
        "Multiple-Angles LoRA (96 poses, non-AI)."
    )

    @classmethod
    def INPUT_TYPES(cls) -> Dict[str, Any]:
        return {
            "required": {
                "azimuth": (
                    list(AZIMUTHS.keys()),
                    {
                        "default": "front view (0°)",
                        "tooltip": (
                            "Horizontal camera rotation around the subject.\n"
                            "0° = front view, 90° = right side, 180° = back view, "
                            "270° = left side, etc."
                        ),
                    },
                ),
                "elevation": (
                    list(ELEVATIONS.keys()),
                    {
                        "default": "eye-level shot (0°)",
                        "tooltip": (
                            "Vertical camera angle.\n"
                            "-30° = low-angle (camera below, looking up)\n"
                            "0° = eye-level\n"
                            "30° = elevated\n"
                            "60° = high-angle (camera high, looking down)"
                        ),
                    },
                ),
                "distance": (
                    list(DISTANCES.keys()),
                    {
                        "default": "medium shot (×1.0)",
                        "tooltip": (
                            "Camera distance from the subject.\n"
                            "×0.6 = close-up (details, textures)\n"
                            "×1.0 = medium shot (balanced, standard)\n"
                            "×1.8 = wide shot (context, environment)"
                        ),
                    },
                ),
                "lora_strength": (
                    "FLOAT",
                    {
                        "default": 0.9,
                        "min": 0.0,
                        "max": 2.0,
                        "step": 0.05,
                        "tooltip": (
                            "LoRA strength. Recommended range: 0.8 – 1.0. "
                            "Lower = subtler effect, higher = stronger camera adherence."
                        ),
                    },
                ),
            },
        }

    def build_prompt(
        self,
        azimuth: str = "front view (0°)",
        elevation: str = "eye-level shot (0°)",
        distance: str = "medium shot (×1.0)",
        lora_strength: float = 0.9,
    ) -> Tuple[str, float, str]:
        """Build the LoRA prompt string.

        Returns:
            (prompt, lora_strength, camera_label)
        """
        az_label = AZIMUTHS.get(azimuth, azimuth)
        el_label = ELEVATIONS.get(elevation, elevation)
        dist_label = DISTANCES.get(distance, distance)

        prompt = f"<sks> {az_label} {el_label} {dist_label}"
        camera_label = f"{az_label} | {el_label} | {dist_label}"

        return (prompt, lora_strength, camera_label)


# ---------------------------------------------------------------------------
# Node registration mappings
# ---------------------------------------------------------------------------
NODE_CLASS_MAPPINGS = {
    "WizdroidQwenMultiAngles": WizdroidQwenMultiAngles,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "WizdroidQwenMultiAngles": "🧙 Qwen Multi-Angles LoRA Prompt",
}
