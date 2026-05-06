"""
Integration tests for LLMService — Gemini + Ollama fallback chain.

Uses respx to mock httpx at the transport level so no real network calls are made.
Tests verify model_used, provider, fallback_used, and response content.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest
import respx
from httpx import Response

# Ensure backend/ is importable
_BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_BACKEND))

from app.core.config import settings              # noqa: E402
from services.ai.llm_service import LLMService   # noqa: E402

# ── Constants ─────────────────────────────────────────────────────────────────

_GEMINI_URL_PATTERN = "https://generativelanguage.googleapis.com/v1beta/models"
_OLLAMA_URL = "http://localhost:11434/api/generate"

_GEMINI_OK = {
    "candidates": [{"content": {"parts": [{"text": "Gemini answer here."}]}}]
}
_OLLAMA_LLAMA_OK = {"response": "LLaMA answer here."}
_OLLAMA_MISTRAL_OK = {"response": "Mistral answer here."}


# ── Fixture: inject a fake Gemini key so the key-guard passes ─────────────────

@pytest.fixture(autouse=True)
def _patch_gemini_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "gemini_api_key", "test-api-key-for-mocked-tests")


# ── Test 1: Gemini success → uses Gemini, no fallback ─────────────────────────

@respx.mock
def test_gemini_success_uses_gemini() -> None:
    respx.post(url__startswith=_GEMINI_URL_PATTERN).mock(
        return_value=Response(200, json=_GEMINI_OK)
    )

    result = LLMService().generate_response("Tell me about AAPL.", preferred_model="gemini")

    assert result.response == "Gemini answer here."
    assert result.model_used == "gemini"
    assert result.provider == "google"
    assert result.fallback_used is False
    assert result.error is None


# ── Test 2: Gemini fails → fallback to LLaMA ─────────────────────────────────

@respx.mock
def test_gemini_failure_falls_back_to_llama() -> None:
    respx.post(url__startswith=_GEMINI_URL_PATTERN).mock(
        return_value=Response(500, json={"error": "internal"})
    )
    respx.post(_OLLAMA_URL).mock(
        return_value=Response(200, json=_OLLAMA_LLAMA_OK)
    )

    result = LLMService().generate_response("Tell me about NVDA.", preferred_model="gemini")

    assert result.response == "LLaMA answer here."
    assert result.model_used == "llama"
    assert result.provider == "ollama"
    assert result.fallback_used is True
    assert result.error is None


# ── Test 3: Gemini + LLaMA fail → final fallback to Mistral ──────────────────

@respx.mock
def test_gemini_and_llama_fail_falls_back_to_mistral() -> None:
    call_count = 0

    def _ollama_handler(request: object) -> Response:
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return Response(500, json={"error": "llama error"})
        return Response(200, json=_OLLAMA_MISTRAL_OK)

    respx.post(url__startswith=_GEMINI_URL_PATTERN).mock(
        return_value=Response(503, json={"error": "unavailable"})
    )
    respx.post(_OLLAMA_URL).mock(side_effect=_ollama_handler)

    result = LLMService().generate_response("Tell me about MSFT.", preferred_model="gemini")

    assert result.response == "Mistral answer here."
    assert result.model_used == "mistral"
    assert result.provider == "ollama"
    assert result.fallback_used is True
    assert result.error is None


# ── Test 4: All providers fail → graceful empty response ─────────────────────

@respx.mock
def test_all_providers_fail_returns_empty_gracefully() -> None:
    respx.post(url__startswith=_GEMINI_URL_PATTERN).mock(
        return_value=Response(500, json={"error": "down"})
    )
    respx.post(_OLLAMA_URL).mock(
        return_value=Response(500, json={"error": "down"})
    )

    result = LLMService().generate_response("Tell me about TSLA.", preferred_model="gemini")

    assert result.response == ""
    assert result.model_used == "none"
    assert result.fallback_used is True
    assert result.error is not None and "failed" in result.error.lower()


# ── Test 5: Preferred model=llama → llama first, gemini as fallback ───────────

@respx.mock
def test_preferred_llama_tries_llama_first() -> None:
    call_count = 0

    def _ollama_fail(request: object) -> Response:
        nonlocal call_count
        call_count += 1
        return Response(500, json={"error": "llama down"})

    respx.post(_OLLAMA_URL).mock(side_effect=_ollama_fail)
    respx.post(url__startswith=_GEMINI_URL_PATTERN).mock(
        return_value=Response(200, json=_GEMINI_OK)
    )

    result = LLMService().generate_response("Stock question.", preferred_model="llama")

    # LLaMA was tried first (call_count >= 1), then fell back to Gemini
    assert call_count >= 1
    assert result.model_used == "gemini"
    assert result.fallback_used is True


# ── Test 6: Response always has all required fields ───────────────────────────

@respx.mock
def test_response_has_all_required_fields() -> None:
    respx.post(url__startswith=_GEMINI_URL_PATTERN).mock(
        return_value=Response(200, json=_GEMINI_OK)
    )

    result = LLMService().generate_response("Any question.", preferred_model="gemini")

    assert hasattr(result, "model_used")
    assert hasattr(result, "provider")
    assert hasattr(result, "response")
    assert hasattr(result, "fallback_used")
    assert hasattr(result, "error")
    assert isinstance(result.fallback_used, bool)
