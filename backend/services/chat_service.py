"""Chat service with lightweight routing + evidence-aware responses."""

from __future__ import annotations

import re
import uuid
from datetime import datetime, timezone

from app.schemas.chat import ChatCitation, ChatIntent, ChatQueryResponse
from services.history_service import get_history, save_chat_interaction
from services.news_sentiment_service import build_news_sentiment_report

_DISCLAIMER = (
    "This response is for educational purposes only and is not financial advice."
)
_TICKER_RE = re.compile(r"\b[A-Z]{1,5}\b")


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _detect_intent(query: str) -> ChatIntent:
    """Lightweight keyword router; no LLM."""
    q = query.lower().strip()

    comparison_markers = (" compare ", " vs ", " versus ", " vs. ", " better than ")
    padded = f" {q} "
    if any(m in padded for m in comparison_markers) or q.startswith("compare "):
        return "comparison_question"
    if "history" in q or "previous" in q or "last time" in q:
        return "history_lookup"

    sentiment_markers = (
        "sentiment",
        "bullish",
        "bearish",
        "news tone",
        "headlines",
        "how is the market feeling",
    )
    if any(m in q for m in sentiment_markers):
        return "sentiment_question"

    explanation_markers = (
        "why ",
        "why is",
        "how come",
        "what caused",
        "explain",
        " up today",
        " down today",
        "moving",
    )
    if any(m in q for m in explanation_markers) or re.search(
        r"\b(up|down|rise|fall|surge|drop)\b", q
    ):
        return "stock_explanation"

    return "unknown"


def _mock_citations() -> list[ChatCitation]:
    return [
        ChatCitation(
            title="Sample News Article",
            url="https://example.com/article",
            source="Mock Source",
            published_at="2026-04-11T10:00:00Z",
        )
    ]


def _extract_tickers(query: str) -> list[str]:
    matches = [m.group(0) for m in _TICKER_RE.finditer(query.upper())]
    dedup: list[str] = []
    for m in matches:
        if m in {"WHY", "WHAT", "HOW", "THE", "AND", "IS", "ARE"}:
            continue
        if m not in dedup:
            dedup.append(m)
    return dedup[:4]


def _response_for_intent(
    intent: ChatIntent,
    query: str,
    thread_id: str,
    ts: str,
    tickers: list[str],
) -> ChatQueryResponse:
    citations = _mock_citations()
    primary_ticker = tickers[0] if tickers else "NVDA"

    if intent == "stock_explanation":
        sentiment = build_news_sentiment_report(primary_ticker, None, None, max_articles=5)
        citations = [
            ChatCitation(
                title=c.title,
                url=c.url,
                source=c.source,
                published_at=c.published_at,
            )
            for c in sentiment.citations[:3]
        ]
        return ChatQueryResponse(
            thread_id=thread_id,
            detected_intent=intent,
            tickers=tickers,
            answer=(
                f"{primary_ticker} appears to be reacting to recent coverage that skews "
                f"{sentiment.aggregate_sentiment.overall_label}. This explanation is "
                "based on lightweight sentiment signals rather than full event attribution."
            ),
            summary_bullets=[
                f"Aggregate sentiment: {sentiment.aggregate_sentiment.positive}% positive / "
                f"{sentiment.aggregate_sentiment.neutral}% neutral / "
                f"{sentiment.aggregate_sentiment.negative}% negative.",
                "Evidence is article-level and not a complete market microstructure analysis.",
                "Educational explanation only; not financial advice.",
            ],
            citations=citations,
            disclaimer=_DISCLAIMER,
            timestamp=ts,
        )

    if intent == "sentiment_question":
        sentiment = build_news_sentiment_report(primary_ticker, None, None, max_articles=5)
        return ChatQueryResponse(
            thread_id=thread_id,
            detected_intent=intent,
            tickers=tickers,
            answer=(
                f"Recent sentiment for {primary_ticker} is "
                f"{sentiment.aggregate_sentiment.overall_label}. "
                "Confidence is moderate because scoring is heuristic when model services are unavailable."
            ),
            summary_bullets=[
                f"Major themes: {', '.join(sentiment.major_themes[:3])}.",
                "Signal combines available news feed + fallback scoring.",
                "Use with caution; not investment advice.",
            ],
            citations=[
                ChatCitation(
                    title=c.title,
                    url=c.url,
                    source=c.source,
                    published_at=c.published_at,
                )
                for c in sentiment.citations[:3]
            ],
            disclaimer=_DISCLAIMER,
            timestamp=ts,
        )

    if intent == "comparison_question":
        return ChatQueryResponse(
            thread_id=thread_id,
            detected_intent=intent,
            tickers=tickers,
            answer=(
                f"You asked: “{query.strip()[:120]}”. Week 1 returns a placeholder "
                "comparison narrative until fundamentals and peer data are wired in."
            ),
            summary_bullets=[
                "Side-by-side metrics will come from your data providers.",
                "Risk/return tradeoffs should be model-driven, not stub text.",
                "Educational use only—not a recommendation.",
            ],
            citations=citations,
            disclaimer=_DISCLAIMER,
            timestamp=ts,
        )
    if intent == "history_lookup":
        hist = get_history()
        recent = hist.chat_history[:3]
        titles = "; ".join(x.title for x in recent) or "No recent threads found."
        return ChatQueryResponse(
            thread_id=thread_id,
            detected_intent=intent,
            tickers=tickers,
            answer=f"I found {len(recent)} recent threads: {titles}",
            summary_bullets=[
                "History is persisted in a local JSON store for this course milestone.",
                "Thread metadata includes title + last_updated timestamps.",
                "TODO: Move to user-scoped DB records with auth controls.",
            ],
            citations=[],
            disclaimer=_DISCLAIMER,
            timestamp=ts,
        )

    return ChatQueryResponse(
        thread_id=thread_id,
        detected_intent="unknown",
        tickers=tickers,
        answer=(
            "I’m not sure how to classify that yet. Try rephrasing with a ticker, "
            "or ask about sentiment, a price move, or a comparison between two names."
        ),
        summary_bullets=[
            "Intent router is keyword-based for Week 1.",
            "Unknown intents fall back to this safe response.",
            "TODO: add LLM-based intent + tool routing.",
        ],
        citations=citations,
        disclaimer=_DISCLAIMER,
        timestamp=ts,
    )


def handle_chat_query(query: str, thread_id: str | None) -> ChatQueryResponse:
    """
    Produce a structured chat response for the given user query.

    Raises:
        ValueError: if query is empty after strip (routes should validate too).
    """
    text = query.strip()
    if not text:
        raise ValueError("query is required")

    tid = (thread_id or "").strip() or f"thread_{uuid.uuid4().hex[:12]}"
    ts = _utc_now_iso()
    intent: ChatIntent = _detect_intent(text)
    tickers = _extract_tickers(text)
    response = _response_for_intent(intent, text, tid, ts, tickers)
    save_chat_interaction(tid, text, response.answer)
    return response
