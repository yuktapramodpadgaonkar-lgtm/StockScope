"""
LLMService for Revati's module (News Sentiment + Chatbot + History).

Providers:
  - Gemini (Google AI REST API)         — primary
  - Ollama LLaMA  (llama3.1:8b)        — local fallback
  - Ollama Mistral (mistral:7b)         — local fallback

Fallback order is caller-controlled via preferred_model.
Every public method is named generate_* or generate_response — never
call_llm or call_llm_with_fallback (those belong to the shared router).
"""

from __future__ import annotations

import logging
import time
from typing import Any

import httpx

from app.core.config import settings
from app.observability.jsonl_audit import log_model_call
from services.ai.schemas import LLMResponse

logger = logging.getLogger(__name__)

# ── Timeouts ──────────────────────────────────────────────────────────────────
_GEMINI_TIMEOUT = 30
_OLLAMA_TIMEOUT = 120   # local inference is slower

# ── Provider → (model_used label, provider label) ────────────────────────────
_PROVIDER_META: dict[str, tuple[str, str]] = {
    "gemini":  ("gemini",  "google"),
    "llama":   ("llama",   "ollama"),
    "mistral": ("mistral", "ollama"),
}

# ── Fallback orders ───────────────────────────────────────────────────────────
_FALLBACK_ORDERS: dict[str, list[str]] = {
    "gemini":  ["gemini", "llama", "mistral"],
    "llama":   ["llama",  "gemini", "mistral"],
    "mistral": ["mistral", "gemini", "llama"],
}


class LLMService:
    """
    Unified LLM gateway for Revati's News Sentiment + Chatbot pipeline.

    Usage:
        svc = LLMService()
        result = svc.generate_response(prompt, preferred_model="gemini")
        print(result.response, result.model_used, result.provider)
    """

    # ── Gemini ─────────────────────────────────────────────────────────────────

    def generate_with_gemini(self, prompt: str) -> str:
        """
        Call Google Gemini via the generateContent REST API.

        Raises:
            RuntimeError: if GEMINI_API_KEY is missing or the request fails.
        """
        api_key = (settings.gemini_api_key or "").strip()
        if not api_key:
            raise RuntimeError("GEMINI_API_KEY is not set in environment.")

        model = (settings.gemini_model or "gemini-1.5-flash").strip()
        # Use header auth (avoid leaking keys via URLs/logs).
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
        headers = {
            "x-goog-api-key": api_key,
            "Content-Type": "application/json",
        }
        payload: dict[str, Any] = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.3, "maxOutputTokens": 1024},
        }

        with httpx.Client(timeout=_GEMINI_TIMEOUT) as client:
            r = client.post(url, headers=headers, json=payload)
            r.raise_for_status()

        data = r.json()
        try:
            return data["candidates"][0]["content"]["parts"][0]["text"].strip()
        except (KeyError, IndexError) as exc:
            raise RuntimeError(
                f"Unexpected Gemini response shape: {data}"
            ) from exc

    # ── Ollama ─────────────────────────────────────────────────────────────────

    def _ollama_generate(self, model_id: str, prompt: str) -> str:
        """
        Call the local Ollama /api/generate endpoint.

        Raises:
            RuntimeError: if Ollama is unreachable or returns an error.
        """
        base_url = (settings.ollama_base_url or "http://localhost:11434").rstrip("/")
        url = f"{base_url}/api/generate"
        payload = {
            "model": model_id,
            "prompt": prompt,
            "stream": False,
        }

        try:
            with httpx.Client(timeout=_OLLAMA_TIMEOUT) as client:
                r = client.post(url, json=payload)
                r.raise_for_status()
        except httpx.ConnectError as exc:
            raise RuntimeError(
                f"Ollama is not running at {base_url}. "
                "Start it with: ollama serve"
            ) from exc
        except httpx.TimeoutException as exc:
            raise RuntimeError(
                f"Ollama timed out after {_OLLAMA_TIMEOUT}s for model '{model_id}'."
            ) from exc

        data = r.json()
        response_text = data.get("response", "").strip()
        if not response_text:
            raise RuntimeError(
                f"Ollama returned an empty response for model '{model_id}'."
            )
        return response_text

    def generate_with_ollama_llama(self, prompt: str) -> str:
        """
        Call Ollama with llama3.1:8b.

        Raises:
            RuntimeError: if Ollama is unreachable or the model is not pulled.
        """
        model_id = (settings.ollama_llama_model or "llama3.1:8b").strip()
        return self._ollama_generate(model_id, prompt)

    def generate_with_ollama_mistral(self, prompt: str) -> str:
        """
        Call Ollama with mistral:7b.

        Raises:
            RuntimeError: if Ollama is unreachable or the model is not pulled.
        """
        model_id = (settings.ollama_mistral_model or "mistral:7b").strip()
        return self._ollama_generate(model_id, prompt)

    # ── Unified entry point ────────────────────────────────────────────────────

    def generate_response(
        self,
        prompt: str,
        preferred_model: str = "gemini",
    ) -> LLMResponse:
        """
        Try providers in priority order; return on the first success.

        Fallback order:
          preferred_model="gemini"  → gemini → llama → mistral
          preferred_model="llama"   → llama  → gemini → mistral
          preferred_model="mistral" → mistral → gemini → llama

        Returns:
            LLMResponse with model_used, provider, response, fallback_used, error.
            On total failure, response is "" and error is set — never raises.
        """
        key = (preferred_model or "gemini").strip().lower()
        order = _FALLBACK_ORDERS.get(key, _FALLBACK_ORDERS["gemini"])

        _generators = {
            "gemini":  self.generate_with_gemini,
            "llama":   self.generate_with_ollama_llama,
            "mistral": self.generate_with_ollama_mistral,
        }

        last_error: str = ""
        for idx, name in enumerate(order):
            generator = _generators.get(name)
            if generator is None:
                continue
            model_label, provider_label = _PROVIDER_META[name]
            t0 = time.perf_counter()
            try:
                text = generator(prompt)
                ms = (time.perf_counter() - t0) * 1000.0
                log_model_call(
                    provider=provider_label,
                    model=model_label,
                    task="llm_service.generate_response",
                    prompt=prompt,
                    output=text,
                    latency_ms=round(ms, 2),
                    error=None,
                )
                return LLMResponse(
                    model_used=model_label,
                    provider=provider_label,
                    response=text,
                    fallback_used=(idx > 0),
                    error=None,
                )
            except Exception as exc:  # noqa: BLE001
                last_error = str(exc)
                ms = (time.perf_counter() - t0) * 1000.0
                log_model_call(
                    provider=provider_label,
                    model=model_label,
                    task="llm_service.generate_response",
                    prompt=prompt,
                    output=None,
                    latency_ms=round(ms, 2),
                    error=str(exc)[:500],
                )
                logger.warning("LLM provider '%s' failed: %s", name, exc)
                continue

        # All providers failed — return a safe empty response, never raise.
        logger.error("All LLM providers failed. Last error: %s", last_error)
        return LLMResponse(
            model_used="none",
            provider="none",
            response="",
            fallback_used=True,
            error=f"All providers failed. Last: {last_error}",
        )
