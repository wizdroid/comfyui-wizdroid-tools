"""Fetch images from a web URL for the Wizdroid "image from URL" node.

Handles two cases:

1. **Direct image links** — ``https://example.com/photo.jpg``,
   ``https://i.pinimg.com/...`` etc. Download the bytes as-is.
2. **HTML pages** — e.g. a Pinterest pin page. Parse the page for its
   ``og:image`` meta tag and re-download that URL instead.

Pinterest (and similar sites) actively block plain scraper requests, so this
module sends a browser-like ``User-Agent`` and lets callers pass a ``Referer``
(e.g. ``https://www.pinterest.com/``) to defeat basic hotlink protection.
Direct ``*.pinimg.com`` image URLs are the most reliable source.
"""

from __future__ import annotations

import logging
import re
from typing import Tuple
from urllib.parse import urlparse

import requests

logger = logging.getLogger(__name__)

DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)

# Match <meta property="og:image" content="..."> (both attribute orders)
_OG_IMAGE_RE = re.compile(
    r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']',
    re.IGNORECASE,
)
_OG_IMAGE_RE_ALT = re.compile(
    r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:image["\']',
    re.IGNORECASE,
)


def _resolve_url(url: str, page_url: str) -> str:
    """Resolve protocol-relative (//) and root-relative (/x) URLs."""
    if url.startswith("//"):
        scheme = urlparse(page_url).scheme or "https"
        return f"{scheme}:{url}"
    if url.startswith("/"):
        parsed = urlparse(page_url)
        return f"{parsed.scheme}://{parsed.netloc}{url}"
    return url


def fetch_image_bytes(
    url: str,
    *,
    referer: str = "",
    user_agent: str = DEFAULT_USER_AGENT,
    timeout: float = 30.0,
    max_bytes: int = 64 * 1024 * 1024,
) -> Tuple[bytes, str, str]:
    """Download image bytes from ``url``.

    If the URL returns HTML (e.g. a Pinterest pin page), extracts the first
    ``og:image`` meta tag and downloads that instead.

    Returns:
        ``(image_bytes, final_url, content_type)``

    Raises:
        ``requests.HTTPError`` on HTTP errors (404, 403, …).
        ``ValueError`` when the response is not an image and no ``og:image``
        is found, or the payload exceeds ``max_bytes``.
    """
    headers = {
        "User-Agent": user_agent,
        "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    }
    if referer:
        headers["Referer"] = referer

    with requests.get(
        url,
        headers=headers,
        timeout=timeout,
        allow_redirects=True,
        stream=True,
    ) as resp:
        resp.raise_for_status()

        content_type = (resp.headers.get("Content-Type") or "").split(";")[0].strip().lower()

        # HTML page → pull the og:image URL and recurse
        if content_type in ("text/html", "application/xhtml+xml"):
            html = resp.text
            match = _OG_IMAGE_RE.search(html) or _OG_IMAGE_RE_ALT.search(html)
            if not match:
                raise ValueError(f"No og:image meta tag found on page: {url}")
            image_url = _resolve_url(match.group(1).strip(), resp.url)
            logger.info("Extracted og:image %s from %s", image_url, url)
            return fetch_image_bytes(
                image_url,
                referer=referer,
                user_agent=user_agent,
                timeout=timeout,
                max_bytes=max_bytes,
            )

        if not content_type.startswith("image/"):
            raise ValueError(
                f"URL returned content-type {content_type or 'unknown'}, "
                f"not an image: {url}"
            )

        # Stream with a size cap so a malicious link can't eat all RAM/disk
        chunks = []
        total = 0
        for chunk in resp.iter_content(chunk_size=8192):
            chunks.append(chunk)
            total += len(chunk)
            if total > max_bytes:
                raise ValueError(
                    f"Image too large (>{max_bytes // (1024 * 1024)} MB): {url}"
                )
        data = b"".join(chunks)

    return data, resp.url, content_type
