"""Wizdroid Tools — Load image from a web link (URL).

Downloads an image from a direct URL or from a web page (Pinterest, etc.,
via the page's ``og:image`` meta tag) and returns it as a ComfyUI IMAGE
tensor plus an optional MASK — the same output shape as the core LoadImage
node, so it can be dropped into any existing workflow.

Category: ``🧙 Wizdroid/Utils``.
"""

from __future__ import annotations

import hashlib
import io
import logging
from pathlib import Path
from typing import Any, Dict, Tuple

import numpy as np
import torch
from PIL import Image, ImageOps, ImageSequence

from lib.web_image import fetch_image_bytes

logger = logging.getLogger(__name__)

CATEGORY = "🧙 Wizdroid/Utils"

# ComfyUI temp dir for optional on-disk caching (falls back to None outside
# a ComfyUI runtime so the module can still be imported standalone).
try:
    import folder_paths

    _TEMP_DIR = Path(folder_paths.get_temp_directory())
except Exception:  # pragma: no cover - only outside ComfyUI
    _TEMP_DIR = None


class WizdroidImageFromURL:
    """Load an image from a web URL (direct link or page like Pinterest)."""

    CATEGORY = CATEGORY
    RETURN_TYPES = ("IMAGE", "MASK", "INT", "INT")
    RETURN_NAMES = ("image", "mask", "width", "height")
    FUNCTION = "load_image"
    OUTPUT_NODE = False
    DESCRIPTION = (
        "Download an image from a web URL — direct image links or pages "
        "like Pinterest (extracts og:image). Returns IMAGE + MASK + size, "
        "same output shape as the core LoadImage node."
    )

    @classmethod
    def INPUT_TYPES(cls) -> Dict[str, Any]:
        return {
            "required": {
                "url": (
                    "STRING",
                    {
                        "default": "",
                        "multiline": False,
                        "tooltip": (
                            "Image URL, e.g. https://i.pinimg.com/originals/.."
                            "/photo.jpg, or a page URL "
                            "(https://www.pinterest.com/pin/12345/...) whose "
                            "og:image will be extracted."
                        ),
                    },
                ),
            },
            "optional": {
                "referer": (
                    "STRING",
                    {
                        "default": "",
                        "multiline": False,
                        "tooltip": (
                            "HTTP Referer header. Some sites (Pinterest) only "
                            "serve images when a referer like "
                            "https://www.pinterest.com/ is sent."
                        ),
                    },
                ),
                "timeout": (
                    "INT",
                    {
                        "default": 30,
                        "min": 5,
                        "max": 300,
                        "step": 5,
                        "tooltip": "Request timeout in seconds.",
                    },
                ),
                "cache_to_disk": (
                    "BOOLEAN",
                    {
                        "default": True,
                        "tooltip": (
                            "Save a copy in the ComfyUI temp dir so the fetched "
                            "image shows up in the UI previews / is easy to inspect."
                        ),
                    },
                ),
            },
        }

    def load_image(
        self,
        url: str,
        referer: str = "",
        timeout: int = 30,
        cache_to_disk: bool = True,
    ) -> Tuple[Any, Any, int, int]:
        """Download ``url`` and convert to a ComfyUI IMAGE + MASK tensor."""
        url = url.strip()
        if not url:
            raise ValueError("Please provide an image URL.")

        data, final_url, _content_type = fetch_image_bytes(
            url,
            referer=referer,
            timeout=float(timeout),
        )

        img = Image.open(io.BytesIO(data))
        img = ImageOps.exif_transpose(img)

        # Same conversion as ComfyUI's core LoadImage (handles GIFs / alpha).
        output_images: list = []
        output_masks: list = []
        for frame in ImageSequence.Iterator(img):
            frame = ImageOps.exif_transpose(frame)
            if frame.mode == "I":
                frame = frame.point(lambda p: p * (1 / 255))
            rgb = frame.convert("RGB")
            arr = np.array(rgb).astype(np.float32) / 255.0
            image_t = torch.from_numpy(arr)[None,]
            if "A" in frame.getbands():
                alpha = np.array(frame.getchannel("A")).astype(np.float32) / 255.0
                mask_t = (1.0 - torch.from_numpy(alpha)).unsqueeze(0)
            else:
                mask_t = torch.ones(
                    (frame.size[1], frame.size[0]), dtype=torch.float32
                ).unsqueeze(0)
            output_images.append(image_t)
            output_masks.append(mask_t)

        image = torch.cat(output_images, dim=0)
        mask = torch.cat(output_masks, dim=0)
        width = int(image.shape[2])
        height = int(image.shape[1])

        if cache_to_disk:
            self._cache_to_disk(img, final_url)

        return (image, mask, width, height)

    # ------------------------------------------------------------------
    @staticmethod
    def _cache_to_disk(img: Image.Image, final_url: str) -> None:
        """Save a copy under the ComfyUI temp dir for preview/debugging."""
        if _TEMP_DIR is None:
            return
        try:
            digest = hashlib.sha1(final_url.encode("utf-8")).hexdigest()[:12]
            fmt = (getattr(img, "format", None) or "PNG").lower()
            ext = fmt if fmt in ("png", "jpg", "jpeg", "webp", "gif") else "png"
            path = _TEMP_DIR / f"wizdroid_url_{digest}.{ext}"
            img.save(str(path))
            logger.info("Cached image to %s", path)
        except Exception as exc:  # noqa: BLE001 - caching is best-effort
            logger.warning("Could not cache image to disk: %s", exc)


# ---------------------------------------------------------------------------
# Node registration mappings
# ---------------------------------------------------------------------------
NODE_CLASS_MAPPINGS = {
    "WizdroidImageFromURL": WizdroidImageFromURL,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "WizdroidImageFromURL": "🧙 Load Image from URL",
}
