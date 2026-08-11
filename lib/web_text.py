"""Fetch readable text from a web page for the "prompt from website" node.

Downloads a page with a browser-like User-Agent and turns the HTML into plain
text: it prefers the ``og:title`` / ``og:description`` meta tags (many sites
populate these even when the body is JS-rendered) plus the visible body text,
then truncates to a sane size before it is fed to an LLM.

Limitations:
- Server-rendered / static HTML works well. Heavily JS-rendered single-page
  apps (e.g. Pinterest's client-rendered UI) may yield little or no text; for
  those, prefer a URL whose ``og:description`` is already populated.
"""

from __future__ import annotations

import html as html_lib
import logging
import re
from typing import Tuple

import requests

logger = logging.getLogger(__name__)

DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)

# Tags whose inner content should never appear as page text
_SKIP_TAGS_RE = re.compile(
    r"<(script|style|noscript|template|svg|canvas|iframe|form|head)"
    r"[^>]*>.*?</\1>",
    re.DOTALL | re.IGNORECASE,
)
_TAG_RE = re.compile(r"<[^>]+>")
_WHITESPACE_RE = re.compile(r"\s+")

_TITLE_TAG_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.DOTALL | re.IGNORECASE)


def _get_meta_content(html_text: str, prop: str) -> str:
    """Return the content of <meta property=prop> (either attribute order)."""
    prop = re.escape(prop)
    for pattern in (
        rf'<meta[^>]+property=["\']{prop}["\'][^>]+content=["\']([^"\']+)["\']',
        rf'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']{prop}["\']',
    ):
        match = re.search(pattern, html_text, re.IGNORECASE)
        if match:
            return html_lib.unescape(match.group(1)).strip()
    return ""


def _truncate(text: str, max_chars: int) -> str:
    """Cut ``text`` at a sentence boundary near ``max_chars``."""
    if not text:
        return ""
    if len(text) <= max_chars:
        return text
    cut = text[:max_chars]
    boundary = max(cut.rfind(". "), cut.rfind(".\n"), cut.rfind(": "))
    if boundary > int(max_chars * 0.5):
        return cut[: boundary + 1].rstrip()
    return cut.rstrip() + "…"


def extract_readable_text(html_text: str, max_chars: int = 4000) -> Tuple[str, str, str]:
    """Extract (text, title, description) from raw HTML.

    The returned ``text`` is a compact summary: og:title / og:description if
    present, then a cleaned slice of the visible body text.
    """
    title = _get_meta_content(html_text, "og:title")
    if not title:
        m = _TITLE_TAG_RE.search(html_text)
        if m:
            title = html_lib.unescape(m.group(1)).strip()
    description = _get_meta_content(html_text, "og:description")
    if not description:
        description = _get_meta_content(html_text, "description")

    body = _SKIP_TAGS_RE.sub(" ", html_text)
    body = _TAG_RE.sub(" ", body)
    body = html_lib.unescape(body)
    body = _WHITESPACE_RE.sub(" ", body).strip()

    parts: list[str] = []
    if title:
        parts.append(f"Title: {title}")
    if description:
        parts.append(f"Description: {description}")
    if body:
        parts.append(f"Page text:\n{body}")

    text = "\n\n".join(parts)
    return _truncate(text, max_chars), title, description


def fetch_page_text(
    url: str,
    *,
    max_chars: int = 4000,
    referer: str = "",
    user_agent: str = DEFAULT_USER_AGENT,
    timeout: float = 30.0,
    max_bytes: int = 16 * 1024 * 1024,
) -> Tuple[str, str, str, str]:
    """Download ``url`` and extract readable text.

    Returns:
        ``(readable_text, final_url, title, description)``

    Raises:
        ``requests.HTTPError`` on HTTP errors.
        ``ValueError`` when the response is neither HTML nor plain text, or
        the payload exceeds ``max_bytes``.
    """
    headers = {
        "User-Agent": user_agent,
        "Accept": "text/html,application/xhtml+xml,text/plain;q=0.9,*/*;q=0.8",
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

        # Read the body with a size cap
        chunks = []
        total = 0
        for chunk in resp.iter_content(chunk_size=65536):
            chunks.append(chunk)
            total += len(chunk)
            if total > max_bytes:
                raise ValueError(
                    f"Page too large (>{max_bytes // (1024 * 1024)} MB): {url}"
                )
        raw = b"".join(chunks)

    is_html = content_type.startswith("text/html") or "html" in content_type
    is_text = content_type.startswith("text/") or not content_type

    if is_html:
        html_text = raw.decode("utf-8", errors="replace")
        text, title, description = extract_readable_text(html_text, max_chars=max_chars)
        return text, resp.url, title, description

    if is_text:
        page_text = raw.decode("utf-8", errors="replace")
        page_text = _WHITESPACE_RE.sub(" ", page_text).strip()
        return _truncate(page_text, max_chars), resp.url, "", ""

    raise ValueError(
        f"URL returned content-type {content_type or 'unknown'}, not a page: {url}"
    )
