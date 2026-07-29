"""Ollama client for comfyui-wizdroid-tools.

Handles model discovery, text generation, and thinking-model support.
"""

from __future__ import annotations

import json
import time
from typing import Any, Dict, List, Optional, Tuple

try:
    import requests  # type: ignore[import-not-found]
except ImportError:  # pragma: no cover
    requests = None

from .constants import DEFAULT_OLLAMA_URL, THINKING_MODEL_PREFIXES

# ---------------------------------------------------------------------------
# Model cache with TTL to prevent UI blocking on repeated INPUT_TYPES calls
# ---------------------------------------------------------------------------
_MODELS_CACHE: Dict[str, List[str]] = {}
_MODELS_CACHE_TIME: Dict[str, float] = {}
_MODELS_TTL = 60.0


def collect_models(ollama_url: str, use_cache: bool = True) -> List[str]:
    """Discover available Ollama models with TTL caching.

    Args:
        ollama_url: Ollama server URL (e.g. http://localhost:11434)
        use_cache: If True, use TTL-based caching to avoid blocking the UI.

    Returns:
        List of model names, or a fallback list with an error description.
    """
    global _MODELS_CACHE, _MODELS_CACHE_TIME

    if requests is None:
        return ["install_requests_library"]

    cache_key = ollama_url

    if use_cache:
        cached = _MODELS_CACHE.get(cache_key)
        cache_time = _MODELS_CACHE_TIME.get(cache_key, 0)
        if cached and (time.time() - cache_time) < _MODELS_TTL:
            return cached

    try:
        resp = requests.get(f"{ollama_url.rstrip('/')}/api/tags", timeout=5)
        if resp.status_code != 200:
            fallback = _MODELS_CACHE.get(cache_key)
            return fallback or ["model_not_available"]
        data = resp.json()
        result = [m.get("name", "unknown") for m in data.get("models", [])]
        if not result:
            result = ["no_models_found"]

        _MODELS_CACHE[cache_key] = result
        _MODELS_CACHE_TIME[cache_key] = time.time()
        return result

    except Exception:  # noqa: BLE001
        return _MODELS_CACHE.get(cache_key) or ["ollama_not_running"]


def _is_thinking_model(model: str) -> bool:
    """Return True if the model supports the 'think' generation option."""
    model_lower = model.lower()
    return any(prefix in model_lower for prefix in THINKING_MODEL_PREFIXES)


def _safe_post(url: str, json_body: Dict[str, Any], timeout: int = 120) -> Tuple[bool, str]:
    """POST to an Ollama endpoint and return (ok, response_text)."""
    if requests is None:
        return False, "request_error: requests library not installed"

    try:
        resp = requests.post(url, json=json_body, timeout=timeout)
    except Exception as e:  # noqa: BLE001
        return False, f"request_error: {type(e).__name__}: {e}"

    if resp.status_code != 200:
        return False, f"http_error: status {resp.status_code}: {resp.text[:512]}"

    return True, resp.text


def generate_text(
    *,
    ollama_url: str,
    model: str,
    system: str,
    prompt: str,
    temperature: float = 0.7,
    max_tokens: int = 512,
    seed: int = 0,
    timeout: int = 120,
) -> Tuple[bool, str]:
    """Call Ollama /api/generate and return (ok, response_or_error).

    Handles thinking-capable models (gemma, qwen, deepseek, etc.) by:
    - Disabling the internal thinking budget so tokens are reserved for the
      actual response.
    - Falling back to message.content when the response field is empty.
    - Retrying with a higher token budget when done_reason == "length".
    """
    opts: Dict[str, Any] = {
        "temperature": temperature,
        "num_predict": max_tokens,
    }

    if seed != 0:
        opts["seed"] = seed
        # Also set a fixed seed to ensure reproducibility
        # Some models use 'seed', others use 'random_seed'
        opts["random_seed"] = seed

    # Disable thinking for thinking-capable models to reserve tokens for response
    if _is_thinking_model(model):
        opts["think"] = 0

    payload: Dict[str, Any] = {
        "model": model,
        "stream": False,
        "prompt": prompt,
        "system": system,
        "options": opts,
    }

    api_url = f"{ollama_url.rstrip('/')}/api/generate"

    def _do_request(local_opts: Dict[str, Any]) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        p = dict(payload)
        p["options"] = dict(local_opts)
        ok, text = _safe_post(api_url, p, timeout=timeout)
        if not ok:
            return False, text, None
        try:
            data = json.loads(text)
        except Exception:  # noqa: BLE001
            return True, text.strip(), None
        return True, text, data

    ok, raw_text, data = _do_request(opts)

    if not ok:
        return False, raw_text

    if not isinstance(data, dict):
        out = raw_text.strip()
        if out:
            return True, out
        return False, "empty_response"

    # Some models embed /api/chat style message inside /api/generate response
    msg = data.get("message")
    if isinstance(msg, dict):
        out = (msg.get("content") or "").strip()
        if out:
            return True, out

    out = (data.get("response") or "").strip()

    if out:
        return True, out

    # Check if thinking consumed all tokens — retry with higher budget
    done_reason = (data.get("done_reason") or "").lower()
    if done_reason == "length" and opts.get("num_predict", 512) < 4096:
        opts["num_predict"] = min(opts.get("num_predict", 512) * 2, 4096)
        # Also force disable thinking on retry
        opts["think"] = 0
        ok2, raw2, data2 = _do_request(opts)
        if ok2 and isinstance(data2, dict):
            out2 = (data2.get("response") or "").strip()
            if out2:
                return True, out2

    return False, "empty_response"
