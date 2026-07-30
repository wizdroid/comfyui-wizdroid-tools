"""Runtime JSON loading for meta-prompts under data/.

Files are re-read when their mtime changes so users can edit JSON and pick up
changes on the next node evaluation / UI refresh without restarting Python
(unless ComfyUI has already cached INPUT_TYPES — refresh the browser page).
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

logger = logging.getLogger(__name__)

# Package root: lib/ -> parent
_PACKAGE_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = _PACKAGE_ROOT / "data"

# path -> (mtime_ns, parsed_object)
_CACHE: Dict[str, Tuple[int, Any]] = {}


def data_path(*parts: str) -> Path:
    """Return an absolute path under the package data/ directory."""
    return DATA_DIR.joinpath(*parts)


def load_json(path: Path, *, default: Optional[Any] = None) -> Any:
    """Load JSON with mtime cache. Re-reads when the file changes on disk.

    Args:
        path: Absolute path to a .json file.
        default: Returned (and logged) if the file is missing or invalid.
                 If None and load fails, raises.

    Returns:
        Parsed JSON value.
    """
    key = str(path.resolve())
    try:
        mtime_ns = path.stat().st_mtime_ns
    except FileNotFoundError:
        if default is not None:
            logger.warning("JSON not found: %s — using default", path)
            return default
        raise

    cached = _CACHE.get(key)
    if cached is not None and cached[0] == mtime_ns:
        return cached[1]

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:  # noqa: BLE001
        if default is not None:
            logger.error("Failed to load %s: %s — using default", path, e)
            return default
        raise

    _CACHE[key] = (mtime_ns, data)
    logger.debug("Loaded JSON %s", path)
    return data


def load_data_json(*parts: str, default: Optional[Any] = None) -> Any:
    """Load JSON relative to data/ (e.g. load_data_json('rewrite', 'modes.json'))."""
    return load_json(data_path(*parts), default=default)


def clear_json_cache() -> None:
    """Drop all cached JSON (useful for tests)."""
    _CACHE.clear()
