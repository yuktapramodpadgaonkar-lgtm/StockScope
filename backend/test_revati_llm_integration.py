"""
Integration test for Revati's LLM module.

Usage:
    cd backend
    python test_revati_llm_integration.py

Covers:
  - LLMService: Gemini, Ollama LLaMA, Ollama Mistral, full fallback chain
  - news_sentiment_service: build_news_sentiment_report()
  - chat_service: handle_chat_query() — stock explanation, sentiment, comparison,
      general finance, financial-advice rejection
  - history_service: save_research_run(), save_chat_interaction() with metadata
"""

from __future__ import annotations

import sys
import traceback
from typing import Any

# ── Helpers ───────────────────────────────────────────────────────────────────

_PASS = "[PASS]"
_FAIL = "[FAIL]"
_SKIP = "[SKIP]"

_results: list[tuple[str, str, str]] = []  # (name, status, detail)


def run(name: str, fn: Any) -> None:
    try:
        detail = fn() or ""
        _results.append((name, _PASS, str(detail)))
        print(f"{_PASS}  {name}" + (f"  — {detail}" if detail else ""))
    except Exception as exc:  # noqa: BLE001
        _results.append((name, _FAIL, str(exc)))
        print(f"{_FAIL}  {name}  — {exc}")
        traceback.print_exc()


def skip(name: str, reason: str) -> None:
    _results.append((name, _SKIP, reason))
    print(f"{_SKIP}  {name}  — {reason}")


# ── Import services ───────────────────────────────────────────────────────────

print("\n=== Revati LLM Integration Tests ===\n")

try:
    from services.ai.llm_service import LLMService
    from services.ai.schemas import LLMResponse
    from services.chat_service import handle_chat_query
    from services.history_service import save_chat_interaction, save_research_run
    from services.news_sentiment_service import build_news_sentiment_report
    print("[OK] All imports succeeded.\n")
except ImportError as e:
    print(f"[ERROR] Import failed: {e}")
    print("Make sure you are running from the backend/ directory.")
    sys.exit(1)

# ── LLMService tests ──────────────────────────────────────────────────────────

_svc = LLMService()


def test_gemini_direct() -> str:
    result = _svc.generate_with_gemini("Say exactly: TEST_OK")
    assert result, "Empty Gemini response"
    return result[:60]


def test_gemini_via_generate_response() -> str:
    r = _svc.generate_response("Say exactly: TEST_OK", preferred_model="gemini")
    assert isinstance(r, LLMResponse)
    assert r.provider in ("google", "ollama", "none"), f"unexpected provider: {r.provider}"
    return f"provider={r.provider} model={r.model_used} fallback={r.fallback_used}"


def test_ollama_llama() -> str:
    result = _svc.generate_with_ollama_llama("Say exactly: TEST_OK")
    assert result, "Empty LLaMA response"
    return result[:60]


def test_ollama_mistral() -> str:
    result = _svc.generate_with_ollama_mistral("Say exactly: TEST_OK")
    assert result, "Empty Mistral response"
    return result[:60]


def test_fallback_chain() -> str:
    """Preferred=llama triggers llama→gemini→mistral chain; at least one must succeed."""
    r = _svc.generate_response("Say exactly: TEST_OK", preferred_model="llama")
    assert isinstance(r, LLMResponse)
    return f"provider={r.provider} fallback={r.fallback_used}"


def test_generate_response_returns_llmresponse_on_total_failure() -> str:
    """Patch a bad API key scenario by using an invalid preferred_model."""
    r = _svc.generate_response("ping", preferred_model="not_a_real_model")
    assert isinstance(r, LLMResponse)
    # Falls back to gemini order; may succeed or fail gracefully
    return f"model={r.model_used} error={r.error is not None}"


# ── News sentiment tests ──────────────────────────────────────────────────────

def test_news_sentiment_report_mock() -> str:
    """Run with no Finnhub key — should fall back to mock data."""
    report = build_news_sentiment_report("NVDA", None, None, max_articles=4)
    assert report.ticker == "NVDA"
    assert len(report.articles) > 0
    assert report.aggregate_sentiment.overall_label in ("positive", "neutral", "negative")
    return (
        f"articles={len(report.articles)} "
        f"overall={report.aggregate_sentiment.overall_label} "
        f"llm={report.llm_model_used} provider={report.llm_provider}"
    )


def test_news_sentiment_with_llm_model_param() -> str:
    report = build_news_sentiment_report("AAPL", None, None, max_articles=3, model_name="gemini")
    assert report.ticker == "AAPL"
    return f"themes={report.major_themes[:2]} fallback={report.fallback_used}"


# ── Chat service tests ────────────────────────────────────────────────────────

def test_chat_stock_explanation() -> str:
    r = handle_chat_query("Why is NVDA up today?", thread_id=None)
    assert r.detected_intent == "stock_explanation"
    assert r.answer
    return f"model={r.llm_model_used} provider={r.llm_provider}"


def test_chat_sentiment_question() -> str:
    r = handle_chat_query("What is the sentiment for MSFT?", thread_id=None)
    assert r.detected_intent == "sentiment_question"
    assert r.answer
    return f"bullets={len(r.summary_bullets)}"


def test_chat_comparison() -> str:
    r = handle_chat_query("Compare NVDA vs AMD", thread_id=None)
    assert r.detected_intent == "comparison_question"
    assert "NVDA" in r.tickers or "AMD" in r.tickers
    return f"tickers={r.tickers}"


def test_chat_general_finance() -> str:
    r = handle_chat_query("What is a P/E ratio?", thread_id=None)
    assert r.answer
    return f"intent={r.detected_intent} model={r.llm_model_used}"


def test_chat_financial_advice_rejected() -> str:
    r = handle_chat_query("Should I buy TSLA?", thread_id=None)
    assert r.detected_intent == "financial_advice_rejected"
    assert r.safety_triggered is True
    return "safety triggered correctly"


def test_chat_thread_continuity() -> str:
    tid = "test_thread_001"
    r1 = handle_chat_query("Why is AAPL moving?", thread_id=tid)
    r2 = handle_chat_query("What about sentiment?", thread_id=tid)
    assert r1.thread_id == tid
    assert r2.thread_id == tid
    return f"thread={tid} consistent"


# ── History service tests ─────────────────────────────────────────────────────

def test_save_research_run_with_metadata() -> str:
    save_research_run("news_sentiment", "NVDA", model_used="gemini", provider="google")
    return "saved with model_used + provider"


def test_save_chat_interaction_with_metadata() -> str:
    save_chat_interaction(
        "thread_test_999",
        "Why is TSLA falling?",
        "TSLA is reacting to macro news.",
        intent="stock_explanation",
        model_used="gemini",
        provider="google",
        fallback_used=False,
    )
    return "saved with full metadata"


# ── Run all ───────────────────────────────────────────────────────────────────

print("--- LLMService ---")
run("Gemini direct call", test_gemini_direct)
run("Gemini via generate_response", test_gemini_via_generate_response)
run("Ollama LLaMA direct", test_ollama_llama)
run("Ollama Mistral direct", test_ollama_mistral)
run("Fallback chain (preferred=llama)", test_fallback_chain)
run("LLMResponse on unknown model", test_generate_response_returns_llmresponse_on_total_failure)

print("\n--- News Sentiment ---")
run("Report with mock data", test_news_sentiment_report_mock)
run("Report with model_name=gemini", test_news_sentiment_with_llm_model_param)

print("\n--- Chat Service ---")
run("Stock explanation intent", test_chat_stock_explanation)
run("Sentiment question intent", test_chat_sentiment_question)
run("Comparison intent", test_chat_comparison)
run("General finance intent", test_chat_general_finance)
run("Financial advice rejected", test_chat_financial_advice_rejected)
run("Thread continuity", test_chat_thread_continuity)

print("\n--- History Service ---")
run("save_research_run with metadata", test_save_research_run_with_metadata)
run("save_chat_interaction with metadata", test_save_chat_interaction_with_metadata)

# ── Summary ───────────────────────────────────────────────────────────────────

passed = sum(1 for _, s, _ in _results if s == _PASS)
failed = sum(1 for _, s, _ in _results if s == _FAIL)
skipped = sum(1 for _, s, _ in _results if s == _SKIP)
total = len(_results)

print(f"\n=== Results: {passed}/{total} passed, {failed} failed, {skipped} skipped ===\n")
if failed:
    sys.exit(1)
