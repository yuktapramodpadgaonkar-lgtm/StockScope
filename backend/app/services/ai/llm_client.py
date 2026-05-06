"""Provider-agnostic text generation for optional AI explanations.

Deterministic analysis must remain the source of truth; this module is best-effort.
"""

from __future__ import annotations

import time
from typing import Any

import httpx

from app.core.config import settings

DEFAULT_TIMEOUT_SEC = 120.0


class OllamaClientError(Exception):
    """Ollama is unreachable, timed out, or returned an unusable response."""


class GeminiClientError(Exception):
    """Gemini is not configured, unreachable, or returned an unusable response."""


def _now_ms() -> float:
    return time.perf_counter() * 1000.0


def _ollama_generate_text(prompt: str, model: str) -> str:
    base_url = (settings.ollama_base_url or "http://localhost:11434").rstrip("/")
    url = f"{base_url}/api/generate"

    payload = {"model": model, "prompt": prompt, "stream": False}

    try:
        with httpx.Client(timeout=DEFAULT_TIMEOUT_SEC) as client:
            res = client.post(url, json=payload)
    except httpx.ConnectError as e:
        raise OllamaClientError(f"Cannot connect to Ollama at {base_url} (is it running?)") from e
    except httpx.TimeoutException as e:
        raise OllamaClientError("Ollama request timed out") from e
    except httpx.RequestError as e:
        raise OllamaClientError(f"Ollama request failed: {e}") from e

    if res.status_code != 200:
        snippet = (res.text or "")[:300]
        raise OllamaClientError(f"Ollama returned HTTP {res.status_code}: {snippet}".strip())

    try:
        data = res.json()
    except ValueError as e:
        raise OllamaClientError("Ollama returned a non-JSON body") from e

    text = data.get("response")
    if not isinstance(text, str) or not text.strip():
        raise OllamaClientError("Ollama returned an empty response")

    return text.strip()


def _gemini_generate_text(prompt: str, model: str) -> str:
    api_key = (settings.gemini_api_key or "").strip()
    if not api_key:
        raise GeminiClientError("GEMINI_API_KEY is not set (add it to backend/.env)")

    # Generative Language API (Google AI Studio key). Use v1beta; model IDs change over time
    # (e.g. gemini-1.5-flash may 404 — prefer a current Flash model).
    # Same host/path as https://ai.google.dev/gemini-api/docs/quickstart (REST).
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    headers = {
        "x-goog-api-key": api_key,
        "Content-Type": "application/json",
    }
    # Single-turn: same "contents" shape as the quickstart curl example.
    payload: dict[str, Any] = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.2},
    }

    try:
        with httpx.Client(timeout=DEFAULT_TIMEOUT_SEC) as client:
            res = client.post(url, headers=headers, json=payload)
    except httpx.TimeoutException as e:
        raise GeminiClientError("Gemini request timed out") from e
    except httpx.RequestError as e:
        raise GeminiClientError(f"Gemini request failed: {e}") from e

    try:
        data = res.json()
    except ValueError:
        data = {}

    if res.status_code != 200:
        err = data.get("error") if isinstance(data.get("error"), dict) else None
        msg = err.get("message") if err else None
        snippet = (msg or res.text or "")[:400]
        raise GeminiClientError(f"Gemini HTTP {res.status_code}: {snippet}".strip())

    pf = data.get("promptFeedback")
    if isinstance(pf, dict) and pf.get("blockReason"):
        raise GeminiClientError(f"Gemini blocked the prompt: {pf.get('blockReason')}")

    # Expected shape: { candidates: [ { content: { parts: [ { text: "..." } ] } } ] }
    candidates = data.get("candidates")
    if not isinstance(candidates, list) or not candidates:
        raise GeminiClientError("Gemini returned no candidates (check model name and API key)")

    cand0 = candidates[0] if isinstance(candidates[0], dict) else {}
    if cand0.get("finishReason") and cand0.get("finishReason") not in ("STOP", "MAX_TOKENS"):
        raise GeminiClientError(f"Gemini finish reason: {cand0.get('finishReason')}")

    content = cand0.get("content") if isinstance(cand0.get("content"), dict) else None
    parts = content.get("parts") if isinstance(content, dict) else None
    if not isinstance(parts, list) or not parts:
        raise GeminiClientError("Gemini returned an empty content")
    text = parts[0].get("text") if isinstance(parts[0], dict) else None
    if not isinstance(text, str) or not text.strip():
        raise GeminiClientError("Gemini returned an empty response")
    return text.strip()


def generate_text(
    prompt: str,
    provider: str = "ollama",
    model: str = "mistral:7b",
) -> dict:
    """
    Best-effort text generation wrapper.

    Returns:
      {"text","provider","model","latency_ms","error"}
    """
    prov = (provider or "ollama").strip().lower()
    mod = (model or "mistral:7b").strip()

    if not prompt or not prompt.strip():
        return {
            "text": None,
            "provider": prov,
            "model": mod,
            "latency_ms": None,
            "error": "Prompt is empty",
        }

    start_ms = _now_ms()
    try:
        if prov == "ollama":
            text = _ollama_generate_text(prompt, mod)
        elif prov == "gemini":
            text = _gemini_generate_text(prompt, mod)
        else:
            return {
                "text": None,
                "provider": prov,
                "model": mod,
                "latency_ms": None,
                "error": f"Unsupported provider '{prov}'",
            }
    except (OllamaClientError, GeminiClientError) as e:
        return {
            "text": None,
            "provider": prov,
            "model": mod,
            "latency_ms": int(_now_ms() - start_ms),
            "error": str(e),
        }

    return {
        "text": text,
        "provider": prov,
        "model": mod,
        "latency_ms": int(_now_ms() - start_ms),
        "error": None,
    }


def call_ollama(prompt: str, model: str = "llama3.1:8b") -> str:
    """
    Call Ollama's non-streaming generate API. Raises OllamaClientError on failure.
    """
    return _ollama_generate_text(prompt, model)
