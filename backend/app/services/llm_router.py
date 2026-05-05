"""
Multi-provider LLM router: Gemini · LLaMA-3 (Groq) · Mistral (OpenRouter).

All three providers expose an HTTP API, so only `httpx` is required — no
extra SDK packages.  Caller picks a preferred model; `call_llm_with_fallback`
tries the full chain automatically so the app stays alive when one key is
missing or a provider is down.
"""

from __future__ import annotations

from typing import Callable

import httpx

from app.core.config import settings

# ── REST endpoints ────────────────────────────────────────────────────────────
_GEMINI_BASE = "https://generativelanguage.googleapis.com/v1beta/models"
_GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
_OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

_TIMEOUT = 30  # seconds


# ── Provider implementations ─────────────────────────────────────────────────

def _call_gemini(prompt: str) -> str:
    """Google Gemini via the generateContent REST API."""
    api_key = (settings.gemini_api_key or "").strip()
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is not configured.")

    model = (settings.gemini_model or "gemini-1.5-flash").strip()
    url = f"{_GEMINI_BASE}/{model}:generateContent?key={api_key}"
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.3, "maxOutputTokens": 1024},
    }

    with httpx.Client(timeout=_TIMEOUT) as client:
        r = client.post(url, json=payload)
        r.raise_for_status()

    data = r.json()
    try:
        return data["candidates"][0]["content"]["parts"][0]["text"].strip()
    except (KeyError, IndexError) as exc:
        raise RuntimeError(f"Unexpected Gemini response shape: {data}") from exc


def _openai_compatible(
    url: str,
    api_key: str,
    model: str,
    prompt: str,
    extra_headers: dict[str, str] | None = None,
) -> str:
    """Shared helper for any OpenAI-compatible chat-completions endpoint."""
    headers: dict[str, str] = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        **(extra_headers or {}),
    }
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.3,
        "max_tokens": 1024,
    }

    with httpx.Client(timeout=_TIMEOUT) as client:
        r = client.post(url, headers=headers, json=payload)
        r.raise_for_status()

    data = r.json()
    try:
        return data["choices"][0]["message"]["content"].strip()
    except (KeyError, IndexError) as exc:
        raise RuntimeError(f"Unexpected API response shape: {data}") from exc


def _call_llama_groq(prompt: str) -> str:
    """LLaMA-3 via Groq's OpenAI-compatible inference API."""
    api_key = (settings.groq_api_key or "").strip()
    if not api_key:
        raise RuntimeError("GROQ_API_KEY is not configured.")

    model = (settings.groq_model or "llama3-8b-8192").strip()
    return _openai_compatible(_GROQ_URL, api_key, model, prompt)


def _call_mistral_openrouter(prompt: str) -> str:
    """Mistral-7B-Instruct via OpenRouter."""
    api_key = (settings.openrouter_api_key or "").strip()
    if not api_key:
        raise RuntimeError("OPENROUTER_API_KEY is not configured.")

    model = (settings.openrouter_model or "mistralai/mistral-7b-instruct").strip()
    extra = {
        "HTTP-Referer": "https://stockscope.app",
        "X-Title": "StockScope",
    }
    return _openai_compatible(_OPENROUTER_URL, api_key, model, prompt, extra)


# ── Public API ────────────────────────────────────────────────────────────────

_PROVIDERS: dict[str, Callable[[str], str]] = {
    "gemini": _call_gemini,
    "llama": _call_llama_groq,
    "mistral": _call_mistral_openrouter,
}

PROVIDER_NAMES = list(_PROVIDERS.keys())


def call_llm(model_name: str, prompt: str) -> str:
    """
    Send *prompt* to the named LLM provider and return the response text.

    Args:
        model_name: ``"gemini"`` | ``"llama"`` | ``"mistral"``
        prompt:     The full prompt string.

    Raises:
        ValueError:   Unknown model_name.
        RuntimeError: Missing API key or provider HTTP error.
    """
    key = model_name.strip().lower()
    fn = _PROVIDERS.get(key)
    if fn is None:
        raise ValueError(
            f"Unknown LLM provider '{model_name}'. "
            f"Choose from: {PROVIDER_NAMES}"
        )
    return fn(prompt)


def call_llm_with_fallback(
    prompt: str,
    preferred: str | None = None,
) -> tuple[str, str]:
    """
    Try providers in priority order and return on the first success.

    Priority: ``preferred`` (if given) → ``settings.default_llm_provider``
    → gemini → llama → mistral.

    Returns:
        (response_text, model_name_used)

    Raises:
        RuntimeError: All providers failed.
    """
    seen: list[str] = []
    # Build ordered list: preferred first, then config default, then the rest
    for candidate in [
        preferred,
        settings.default_llm_provider,
        "gemini",
        "llama",
        "mistral",
    ]:
        name = (candidate or "").strip().lower()
        if name and name in _PROVIDERS and name not in seen:
            seen.append(name)

    last_err: Exception | None = None
    for name in seen:
        try:
            return call_llm(name, prompt), name
        except Exception as exc:  # noqa: BLE001  — intentional broad catch
            last_err = exc
            continue

    raise RuntimeError(
        f"All LLM providers failed. Last error: {last_err}"
    )
