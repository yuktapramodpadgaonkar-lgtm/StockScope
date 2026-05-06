"""
Chatbot service — Planner → Executor → Critic (lightweight).

Flow per query:
  1. Safety check  — reject financial-advice requests immediately.
  2. Intent detect — classify query into a known intent via keyword router.
  3. Tool select   — pull relevant data (news sentiment, history).
  4. LLM generate  — craft answer + bullets via LLMService (Gemini → LLaMA → Mistral).
  5. Fallback      — if all LLMs fail, return a safe keyword-based response.
"""

from __future__ import annotations

import json
import re
import uuid
from datetime import datetime, timezone

from app.schemas.chat import ChatCitation, ChatIntent, ChatQueryResponse
from services.ai.llm_service import LLMService
from services.ai.prompts import (
    build_comparison_prompt,
    build_general_finance_prompt,
    build_sentiment_question_prompt,
    build_stock_explanation_prompt,
)
from services.history_service import get_history, save_chat_interaction
from services.news_sentiment_service import build_news_sentiment_report

_DISCLAIMER = "This response is for educational purposes only and is not financial advice."
_TICKER_RE = re.compile(r"\b[A-Z]{1,5}\b")
_llm = LLMService()

_STOPWORDS = frozenset(
    {"WHY", "WHAT", "HOW", "THE", "AND", "IS", "ARE", "FOR", "CAN", "YOU",
     "ME", "MY", "ON", "IN", "AT", "TO", "OF", "IT", "THIS", "THAT", "DO",
     "DOES", "GET", "HELP", "TELL", "SHOW", "GIVE", "WILL", "WAS", "HAS",
     "BUY", "SELL", "HOLD"}
)


# ── Helpers ──────────────────────────────────────────────────────────────────

def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _extract_tickers(query: str) -> list[str]:
    dedup: list[str] = []
    for m in _TICKER_RE.finditer(query.upper()):
        t = m.group(0)
        if t not in _STOPWORDS and t not in dedup:
            dedup.append(t)
    return dedup[:4]


# ── Safety layer ──────────────────────────────────────────────────────────────

_ADVICE_PATTERNS = re.compile(
    r"\b(should i (buy|sell|invest|hold|short)|what (should i|do i) (buy|sell|invest|pick)|"
    r"best stock(s)? to buy|recommend(ation)?s? (for|to) (buy|invest)|"
    r"is .{1,30} a good (buy|investment|stock)|"
    r"tell me what to (buy|invest|trade)|give me (stock )?(picks|tips|advice)|"
    r"what (stock|shares?) should i|top (stocks|picks) (to|for) (buy|invest))\b",
    re.IGNORECASE,
)


def _is_financial_advice(query: str) -> bool:
    return bool(_ADVICE_PATTERNS.search(query))


# ── Intent detection ──────────────────────────────────────────────────────────

def _detect_intent(query: str) -> ChatIntent:
    q = query.lower().strip()
    padded = f" {q} "

    if any(m in padded for m in (" compare ", " vs ", " versus ", " vs. ", " better than ")):
        return "comparison_question"
    if "history" in q or "previous" in q or "last time" in q:
        return "history_lookup"

    sentiment_markers = (
        "sentiment", "bullish", "bearish", "news tone", "headlines",
        "how is the market feeling",
    )
    if any(m in q for m in sentiment_markers):
        return "sentiment_question"

    explanation_markers = (
        "why ", "why is", "how come", "what caused", "explain",
        " up today", " down today", "moving",
    )
    if any(m in q for m in explanation_markers) or re.search(
        r"\b(up|down|rise|fall|surge|drop)\b", q
    ):
        return "stock_explanation"

    return "unknown"


# ── LLM answer helper ─────────────────────────────────────────────────────────

def _parse_llm_json(raw: str) -> dict:
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    start, end = raw.find("{"), raw.rfind("}")
    if start != -1 and end > start:
        return json.loads(raw[start : end + 1])
    raise ValueError("No JSON object found in LLM output.")


def _llm_answer(
    prompt: str,
    preferred: str | None,
) -> tuple[str, list[str], str | None, str | None, bool]:
    """
    Call LLMService, parse JSON response.

    Returns (answer, bullets, model_used, provider, fallback_used).
    Raises RuntimeError if all providers fail or JSON is malformed.
    """
    result = _llm.generate_response(prompt, preferred_model=preferred or "gemini")
    if result.error or not result.response:
        raise RuntimeError(result.error or "Empty LLM response")
    parsed = _parse_llm_json(result.response)
    answer = str(parsed.get("answer", "")).strip()
    bullets = [str(b) for b in parsed.get("bullets", [])[:5]]
    return answer, bullets, result.model_used, result.provider, result.fallback_used


# ── Response builders ─────────────────────────────────────────────────────────

def _build_citation(c: object) -> ChatCitation:
    return ChatCitation(
        title=c.title,  # type: ignore[attr-defined]
        url=c.url,  # type: ignore[attr-defined]
        source=c.source,  # type: ignore[attr-defined]
        published_at=c.published_at,  # type: ignore[attr-defined]
    )


def _response_stock_explanation(
    query: str,
    ticker: str,
    thread_id: str,
    ts: str,
    tickers: list[str],
    preferred_model: str | None,
) -> ChatQueryResponse:
    sentiment = build_news_sentiment_report(ticker, None, None, max_articles=5)
    headlines = "\n".join(
        f"- [{a.sentiment}] {a.headline}" for a in sentiment.articles[:5]
    )
    prompt = build_stock_explanation_prompt(
        query=query,
        ticker=ticker,
        news_context=headlines,
        positive=sentiment.aggregate_sentiment.positive,
        neutral=sentiment.aggregate_sentiment.neutral,
        negative=sentiment.aggregate_sentiment.negative,
        themes=", ".join(sentiment.major_themes[:3]),
    )

    llm_model: str | None = None
    llm_provider: str | None = None
    llm_fallback = False
    try:
        answer, bullets, llm_model, llm_provider, llm_fallback = _llm_answer(prompt, preferred_model)
    except Exception:  # noqa: BLE001
        answer = (
            f"{ticker} is reacting to recent coverage that skews "
            f"{sentiment.aggregate_sentiment.overall_label}. "
            "Full LLM analysis is unavailable right now."
        )
        bullets = [
            f"Aggregate sentiment: {sentiment.aggregate_sentiment.positive}% positive / "
            f"{sentiment.aggregate_sentiment.neutral}% neutral / "
            f"{sentiment.aggregate_sentiment.negative}% negative.",
            "Evidence is article-level; not a complete market-microstructure analysis.",
            "Educational explanation only — not financial advice.",
        ]

    return ChatQueryResponse(
        thread_id=thread_id,
        detected_intent="stock_explanation",
        tickers=tickers,
        answer=answer,
        summary_bullets=bullets,
        citations=[_build_citation(c) for c in sentiment.citations[:3]],
        disclaimer=_DISCLAIMER,
        timestamp=ts,
        llm_model_used=llm_model,
        llm_provider=llm_provider,
        llm_fallback_used=llm_fallback,
    )


def _response_sentiment(
    query: str,
    ticker: str,
    thread_id: str,
    ts: str,
    tickers: list[str],
    preferred_model: str | None,
) -> ChatQueryResponse:
    sentiment = build_news_sentiment_report(ticker, None, None, max_articles=5)
    headlines = "; ".join(a.headline for a in sentiment.articles[:3])
    prompt = build_sentiment_question_prompt(
        query=query,
        ticker=ticker,
        positive=sentiment.aggregate_sentiment.positive,
        neutral=sentiment.aggregate_sentiment.neutral,
        negative=sentiment.aggregate_sentiment.negative,
        n_articles=len(sentiment.articles),
        themes=", ".join(sentiment.major_themes[:3]),
        headlines=headlines,
    )

    llm_model: str | None = None
    llm_provider: str | None = None
    llm_fallback = False
    try:
        answer, bullets, llm_model, llm_provider, llm_fallback = _llm_answer(prompt, preferred_model)
    except Exception:  # noqa: BLE001
        answer = (
            f"Sentiment for {ticker} is {sentiment.aggregate_sentiment.overall_label}. "
            "LLM narrative unavailable; showing raw aggregates."
        )
        bullets = [
            f"Major themes: {', '.join(sentiment.major_themes[:3])}.",
            "Signal derived from FinBERT + fallback heuristics.",
            "Not investment advice.",
        ]

    return ChatQueryResponse(
        thread_id=thread_id,
        detected_intent="sentiment_question",
        tickers=tickers,
        answer=answer,
        summary_bullets=bullets,
        citations=[_build_citation(c) for c in sentiment.citations[:3]],
        disclaimer=_DISCLAIMER,
        timestamp=ts,
        llm_model_used=llm_model,
        llm_provider=llm_provider,
        llm_fallback_used=llm_fallback,
    )


def _response_comparison(
    query: str,
    thread_id: str,
    ts: str,
    tickers: list[str],
    preferred_model: str | None,
) -> ChatQueryResponse:
    prompt = build_comparison_prompt(
        query=query,
        tickers=", ".join(tickers) if tickers else "the mentioned tickers",
    )

    llm_model: str | None = None
    llm_provider: str | None = None
    llm_fallback = False
    try:
        answer, bullets, llm_model, llm_provider, llm_fallback = _llm_answer(prompt, preferred_model)
    except Exception:  # noqa: BLE001
        answer = (
            f"Comparison for {', '.join(tickers)} is not available right now — "
            "LLM provider unreachable. Try again shortly."
        )
        bullets = [
            "Side-by-side metrics require live fundamentals data.",
            "Risk/return tradeoffs should be model-driven.",
            "Educational use only — not a recommendation.",
        ]

    return ChatQueryResponse(
        thread_id=thread_id,
        detected_intent="comparison_question",
        tickers=tickers,
        answer=answer,
        summary_bullets=bullets,
        citations=[],
        disclaimer=_DISCLAIMER,
        timestamp=ts,
        llm_model_used=llm_model,
        llm_provider=llm_provider,
        llm_fallback_used=llm_fallback,
    )


def _response_general_finance(
    query: str,
    thread_id: str,
    ts: str,
    tickers: list[str],
    preferred_model: str | None,
) -> ChatQueryResponse:
    prompt = build_general_finance_prompt(query=query)

    llm_model: str | None = None
    llm_provider: str | None = None
    llm_fallback = False
    try:
        answer, bullets, llm_model, llm_provider, llm_fallback = _llm_answer(prompt, preferred_model)
    except Exception:  # noqa: BLE001
        answer = (
            "I'm not sure how to classify that query yet. "
            "Try rephrasing with a ticker symbol, or ask about sentiment, "
            "a recent price move, or a comparison between two stocks."
        )
        bullets = [
            "Intent router is keyword-based; include a ticker for best results.",
            "Example: 'Why is TSLA down today?' or 'What is MSFT sentiment?'",
            "Educational use only — not financial advice.",
        ]

    return ChatQueryResponse(
        thread_id=thread_id,
        detected_intent="unknown",
        tickers=tickers,
        answer=answer,
        summary_bullets=bullets,
        citations=[],
        disclaimer=_DISCLAIMER,
        timestamp=ts,
        llm_model_used=llm_model,
        llm_provider=llm_provider,
        llm_fallback_used=llm_fallback,
    )


def _response_history(
    thread_id: str,
    ts: str,
    tickers: list[str],
) -> ChatQueryResponse:
    hist = get_history()
    recent = hist.chat_history[:3]
    titles = "; ".join(x.title for x in recent) or "No recent threads found."
    return ChatQueryResponse(
        thread_id=thread_id,
        detected_intent="history_lookup",
        tickers=tickers,
        answer=f"Found {len(recent)} recent thread(s): {titles}",
        summary_bullets=[
            "History is persisted in a local JSON store.",
            "Thread metadata includes title + last_updated timestamp.",
        ],
        citations=[],
        disclaimer=_DISCLAIMER,
        timestamp=ts,
    )


def _response_advice_rejected(
    query: str,
    thread_id: str,
    ts: str,
    tickers: list[str],
) -> ChatQueryResponse:
    return ChatQueryResponse(
        thread_id=thread_id,
        detected_intent="financial_advice_rejected",
        tickers=tickers,
        answer=(
            "StockScope is an educational tool and cannot provide personalised "
            "investment advice or stock recommendations. "
            "Instead, try asking: 'Why is AAPL moving today?' or "
            "'What is the current sentiment for NVDA?'"
        ),
        summary_bullets=[
            "Providing specific buy/sell recommendations falls outside our scope.",
            "Use the news sentiment and buy-sell analysis features for objective data.",
            "Always consult a licensed financial adviser before making investment decisions.",
        ],
        citations=[],
        disclaimer=_DISCLAIMER,
        timestamp=ts,
        safety_triggered=True,
    )


# ── Public entry point ────────────────────────────────────────────────────────

def handle_chat_query(
    query: str,
    thread_id: str | None,
    model_name: str | None = None,
) -> ChatQueryResponse:
    """
    Produce a structured chat response for the given user query.

    Raises:
        ValueError: if query is empty after strip.
    """
    text = query.strip()
    if not text:
        raise ValueError("query is required")

    tid = (thread_id or "").strip() or f"thread_{uuid.uuid4().hex[:12]}"
    ts = _utc_now_iso()
    tickers = _extract_tickers(text)
    primary = tickers[0] if tickers else "NVDA"

    # Step 1: Safety gate.
    if _is_financial_advice(text):
        response = _response_advice_rejected(text, tid, ts, tickers)
        save_chat_interaction(
            tid, text, response.answer,
            intent="financial_advice_rejected",
        )
        return response

    # Step 2 & 3: Route to the right handler.
    intent = _detect_intent(text)

    if intent == "stock_explanation":
        response = _response_stock_explanation(text, primary, tid, ts, tickers, model_name)
    elif intent == "sentiment_question":
        response = _response_sentiment(text, primary, tid, ts, tickers, model_name)
    elif intent == "comparison_question":
        response = _response_comparison(text, tid, ts, tickers, model_name)
    elif intent == "history_lookup":
        response = _response_history(tid, ts, tickers)
    else:
        response = _response_general_finance(text, tid, ts, tickers, model_name)

    save_chat_interaction(
        tid, text, response.answer,
        intent=response.detected_intent,
        model_used=response.llm_model_used,
        provider=response.llm_provider,
        fallback_used=response.llm_fallback_used if response.llm_fallback_used else None,
    )
    return response
