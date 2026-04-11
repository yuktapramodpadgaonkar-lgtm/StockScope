"""
Week 1 stub chat: keyword intent routing and canned structured responses.

TODO: Replace with LangGraph / agent orchestration and grounded retrieval (RAG).
"""

from __future__ import annotations

import re
import uuid
from datetime import datetime, timezone
from app.schemas.chat import ChatCitation, ChatIntent, ChatQueryResponse

_DISCLAIMER = (
    "This response is for educational purposes only and is not financial advice."
)


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _detect_intent(query: str) -> ChatIntent:
    """Lightweight keyword router; no LLM."""
    q = query.lower().strip()

    comparison_markers = (" compare ", " vs ", " versus ", " vs. ", " better than ")
    padded = f" {q} "
    if any(m in padded for m in comparison_markers) or q.startswith("compare "):
        return "comparison_question"

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


def _response_for_intent(
    intent: ChatIntent,
    query: str,
    thread_id: str,
    ts: str,
) -> ChatQueryResponse:
    citations = _mock_citations()

    if intent == "stock_explanation":
        return ChatQueryResponse(
            thread_id=thread_id,
            detected_intent=intent,
            answer=(
                "From a Week 1 stub perspective, the move is framed as a mix of "
                "recent headlines and broad market momentum. Plug in real prices "
                "and news when integrations land."
            ),
            summary_bullets=[
                "Recent news coverage is summarized as supportive.",
                "Price action is described qualitatively as showing momentum.",
                "This is an educational explanation, not financial advice.",
            ],
            citations=citations,
            disclaimer=_DISCLAIMER,
            timestamp=ts,
        )

    if intent == "sentiment_question":
        return ChatQueryResponse(
            thread_id=thread_id,
            detected_intent=intent,
            answer=(
                "Sentiment is mocked as cautiously constructive: headlines skew "
                "positive but dispersion remains. Use the dedicated news-sentiment "
                "endpoint for structured article-level output."
            ),
            summary_bullets=[
                "Stub labels articles positive / neutral / negative.",
                "Aggregate mix is informational only.",
                "FinBERT + live feeds replace this in a later milestone.",
            ],
            citations=citations,
            disclaimer=_DISCLAIMER,
            timestamp=ts,
        )

    if intent == "comparison_question":
        return ChatQueryResponse(
            thread_id=thread_id,
            detected_intent=intent,
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

    return ChatQueryResponse(
        thread_id=thread_id,
        detected_intent="unknown",
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
    return _response_for_intent(intent, text, tid, ts)
