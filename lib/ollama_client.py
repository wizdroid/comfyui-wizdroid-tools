"""Ollama client for comfyui-wizdroid-tools.

Handles model discovery, text generation, vision (image) generation, and
thinking-model support.
"""

from __future__ import annotations

import base64
import io
import json
import logging
import time
from typing import Any, Dict, List, Optional, Sequence, Tuple

try:
    import requests  # type: ignore[import-not-found]
except ImportError:  # pragma: no cover
    requests = None

from .constants import DEFAULT_OLLAMA_URL, THINKING_MODEL_PREFIXES

logger = logging.getLogger(__name__)

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


def _build_generate_options(
    *,
    temperature: float,
    max_tokens: int,
    seed: int,
    model: str,
) -> Dict[str, Any]:
    opts: Dict[str, Any] = {
        "temperature": temperature,
        "num_predict": max_tokens,
    }
    if seed != 0:
        opts["seed"] = seed
        opts["random_seed"] = seed
    if _is_thinking_model(model):
        opts["think"] = 0
    return opts


def _extract_message_content(msg: Any) -> str:
    """Pull text from an Ollama message, handling list-shaped multimodal content."""
    if not isinstance(msg, dict):
        return ""
    content = msg.get("content")
    if isinstance(content, list):
        parts: List[str] = []
        for part in content:
            if isinstance(part, dict):
                parts.append(str(part.get("text", "")))
            else:
                parts.append(str(part))
        return "".join(parts).strip()
    return (content or "").strip()


def _extract_generate_text(data: Dict[str, Any], raw_text: str) -> str:
    """Pull response text from an Ollama generate/chat-shaped payload.

    Checks ``message.content`` (string or list of parts) then ``response``.
    It deliberately does NOT fall back to the raw JSON, so callers never see
    the raw payload (which previously polluted caption/output files), and it
    does NOT return the ``thinking`` trace — that lets the ``length`` retry in
    :func:`generate_text` give the model a bigger budget to finish a real answer.
    """
    out = _extract_message_content(data.get("message"))
    if out:
        return out
    out = (data.get("response") or "").strip()
    if out:
        return out
    return ""


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
    images: Optional[Sequence[str]] = None,
) -> Tuple[bool, str]:
    """Call Ollama /api/generate and return (ok, response_or_error).

    Handles thinking-capable models (gemma, qwen, deepseek, etc.) by:
    - Disabling the internal thinking budget so tokens are reserved for the
      actual response.
    - Falling back to message.content when the response field is empty.
    - Retrying with a higher token budget when done_reason == "length".

    Args:
        images: Optional list of base64-encoded images (no data-URI prefix)
            for vision-language models (llava, qwen2.5-vl, gemma3, etc.).
    """
    opts = _build_generate_options(
        temperature=temperature,
        max_tokens=max_tokens,
        seed=seed,
        model=model,
    )

    payload: Dict[str, Any] = {
        "model": model,
        "stream": False,
        "prompt": prompt,
        "system": system,
        "options": opts,
    }
    if images:
        # Ollama expects raw base64 strings (no data:image/... prefix)
        payload["images"] = [img for img in images if img]

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

    out = _extract_generate_text(data, raw_text)
    if out:
        return True, out

    # Thinking models (gemma/qwen/etc.) can burn the whole token budget on
    # internal reasoning before writing the answer (done_reason == "length"),
    # leaving `response` empty. Retry with a growing budget and think disabled
    # until there is room for a real answer (capped so we never loop forever).
    MAX_RETRY_TOKENS = 8192
    budget = opts.get("num_predict", 512)
    done_reason = (data.get("done_reason") or "").lower()
    while done_reason == "length" and budget < MAX_RETRY_TOKENS:
        budget = min(budget * 4, MAX_RETRY_TOKENS)
        opts["num_predict"] = budget
        opts["think"] = 0
        ok2, raw2, data2 = _do_request(opts)
        if not ok2 or not isinstance(data2, dict):
            break
        out2 = _extract_generate_text(data2, raw2)
        if out2:
            return True, out2
        done_reason = (data2.get("done_reason") or "").lower()

    return False, "empty_response"


def comfy_image_to_base64_png(
    image: Any,
    *,
    max_side: int = 1280,
) -> Tuple[bool, str]:
    """Convert a ComfyUI IMAGE tensor (or batch) to a base64 PNG string.

    Expects shape ``[B, H, W, C]`` or ``[H, W, C]`` with values in ``[0, 1]``.
    Uses the first batch item when a batch is provided.

    Returns:
        ``(True, base64_png)`` or ``(False, error_message)``.
    """
    try:
        import numpy as np
    except ImportError:  # pragma: no cover
        return False, "numpy is required for vision image encoding"

    try:
        from PIL import Image
    except ImportError:  # pragma: no cover
        return False, "Pillow (PIL) is required for vision image encoding"

    try:
        # Torch tensor path (standard ComfyUI IMAGE)
        if hasattr(image, "detach"):
            t = image.detach().cpu()
            if hasattr(t, "numpy"):
                arr = t.numpy()
            else:
                arr = np.array(t)
        elif isinstance(image, np.ndarray):
            arr = image
        else:
            arr = np.array(image)

        arr = np.asarray(arr)
        if arr.ndim == 4:
            arr = arr[0]
        if arr.ndim != 3:
            return False, f"unsupported image shape: {getattr(arr, 'shape', None)}"

        # Channel-first [C,H,W] → [H,W,C]
        if arr.shape[0] in (1, 3, 4) and arr.shape[-1] not in (1, 3, 4):
            arr = np.transpose(arr, (1, 2, 0))

        if arr.dtype != np.uint8:
            arr = np.clip(arr.astype(np.float32), 0.0, 1.0)
            arr = (arr * 255.0).round().astype(np.uint8)

        if arr.shape[-1] == 1:
            arr = np.repeat(arr, 3, axis=-1)
        elif arr.shape[-1] == 4:
            # Drop alpha for VL models
            arr = arr[..., :3]
        elif arr.shape[-1] != 3:
            return False, f"unsupported channel count: {arr.shape[-1]}"

        pil = Image.fromarray(arr, mode="RGB")
        w, h = pil.size
        longest = max(w, h)
        if max_side > 0 and longest > max_side:
            scale = max_side / float(longest)
            new_size = (max(1, int(w * scale)), max(1, int(h * scale)))
            resample = getattr(Image, "Resampling", Image).LANCZOS
            try:
                pil = pil.resize(new_size, resample)
            except Exception:  # noqa: BLE001
                pil = pil.resize(new_size)

        buf = io.BytesIO()
        pil.save(buf, format="PNG", optimize=True)
        b64 = base64.b64encode(buf.getvalue()).decode("ascii")
        return True, b64
    except Exception as e:  # noqa: BLE001
        logger.exception("Failed to encode ComfyUI image for Ollama VL")
        return False, f"image_encode_error: {type(e).__name__}: {e}"


def generate_with_image(
    *,
    ollama_url: str,
    model: str,
    system: str,
    prompt: str,
    image: Any,
    temperature: float = 0.7,
    max_tokens: int = 1024,
    seed: int = 0,
    timeout: int = 180,
    max_side: int = 1280,
) -> Tuple[bool, str]:
    """Vision-language generate: encode a ComfyUI IMAGE and call Ollama.

    Prefer a VL model (e.g. ``llava``, ``qwen2.5-vl``, ``gemma3``, ``minicpm-v``).
    """
    ok, payload = comfy_image_to_base64_png(image, max_side=max_side)
    if not ok:
        return False, payload
    return generate_text(
        ollama_url=ollama_url,
        model=model,
        system=system,
        prompt=prompt,
        temperature=temperature,
        max_tokens=max_tokens,
        seed=seed,
        timeout=timeout,
        images=[payload],
    )
