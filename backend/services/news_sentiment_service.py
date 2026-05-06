"""
News Sentiment Service — Revati's module.

Pipeline:
  1. Fetch articles from Finnhub (falls back to mock data when key absent).
  2. Classify each article with FinBERT via the HF Inference API
     (keyword heuristic fallback when token absent or model cold).
  3. Generate top themes + narrative summary via LLMService
     (Gemini primary → Ollama LLaMA → Ollama Mistral).
"""

from __future__ import annotations

import json
import logging
from datetime import date, datetime, timedelta
from typing import Any

import httpx

from app.core.config import settings
from app.schemas.news_sentiment import (
    AggregateSentiment,
    CitationItem,
    NewsArticleItem,
    NewsSentimentResponse,
    SentimentLabel,
)
from services.ai.llm_service import LLMService
from services.ai.prompts import build_news_themes_prompt
from services.history_service import save_research_run

logger = logging.getLogger(__name__)

_DISCLAIMER = "This is for educational purposes only and not financial advice."
_llm = LLMService()

# ── Date helpers ──────────────────────────────────────────────────────────────

def _parse_iso_date(s: str | None) -> date | None:
    if not s:
        return None
    try:
        return date.fromisoformat(s.strip()[:10])
    except ValueError:
        return None


def _article_in_range(
    item: dict[str, Any], d_from: date | None, d_to: date | None
) -> bool:
    if d_from is None and d_to is None:
        return True
    try:
        d = datetime.fromisoformat(
            item["published_at"].replace("Z", "+00:00")
        ).date()
    except (KeyError, ValueError):
        return True
    if d_from and d < d_from:
        return False
    if d_to and d > d_to:
        return False
    return True


# ── Mock data ─────────────────────────────────────────────────────────────────

def _mock_articles(ticker: str) -> list[dict[str, Any]]:
    sym = ticker.upper()
    return [
        {
            "headline": f"{sym} gains as AI demand remains strong",
            "source": "Mock Finance News",
            "url": "https://example.com/article-1",
            "published_at": "2026-04-10T09:00:00Z",
            "summary": "Article discusses strong AI demand and bullish expectations.",
        },
        {
            "headline": "Mixed views emerge on semiconductor valuations",
            "source": "Mock Market Watch",
            "url": "https://example.com/article-2",
            "published_at": "2026-04-09T12:00:00Z",
            "summary": "Article highlights both upside and valuation concerns.",
        },
        {
            "headline": "Traders watch macro data ahead of key earnings week",
            "source": "Mock Wire",
            "url": "https://example.com/article-3",
            "published_at": "2026-04-08T15:30:00Z",
            "summary": "Article notes caution on rates and positioning into events.",
        },
        {
            "headline": f"Analysts lift estimates on {sym} data-center outlook",
            "source": "Mock Desk Research",
            "url": "https://example.com/article-4",
            "published_at": "2026-04-07T11:00:00Z",
            "summary": "Analyst commentary frames upside to estimates.",
        },
    ]


# ── Finnhub fetch ─────────────────────────────────────────────────────────────

def _fetch_finnhub_news(
    ticker: str,
    from_date: str,
    to_date: str,
    max_articles: int,
) -> list[dict[str, Any]]:
    if not settings.finnhub_api_key:
        return []
    url = "https://finnhub.io/api/v1/company-news"
    params = {
        "symbol": ticker,
        "from": from_date,
        "to": to_date,
        "token": settings.finnhub_api_key,
    }
    with httpx.Client(timeout=15) as client:
        res = client.get(url, params=params)
        res.raise_for_status()
        payload = res.json()
    if not isinstance(payload, list):
        return []

    normalized: list[dict[str, Any]] = []
    for item in payload[:max_articles]:
        headline = (item.get("headline") or "").strip()
        if not headline:
            continue
        iso_ts = (
            datetime.utcfromtimestamp(item.get("datetime") or 0)
            .replace(microsecond=0)
            .isoformat() + "Z"
        )
        normalized.append(
            {
                "headline": headline,
                "source": item.get("source") or "Finnhub",
                "url": item.get("url") or "https://finnhub.io/",
                "published_at": iso_ts,
                "summary": (item.get("summary") or headline)[:300],
            }
        )
    return normalized


# ── Sentiment classification ──────────────────────────────────────────────────

def _heuristic_sentiment(text: str) -> SentimentLabel:
    """Keyword fallback used when FinBERT is unavailable."""
    positive_markers = (
        "strong", "gain", "upside", "bullish", "upgrade",
        "beat", "optimism", "growth",
    )
    negative_markers = (
        "risk", "caution", "downgrade", "bearish", "concern",
        "weak", "miss", "decline",
    )
    text_l = text.lower()
    pos = sum(1 for w in positive_markers if w in text_l)
    neg = sum(1 for w in negative_markers if w in text_l)
    if pos > neg:
        return "positive"
    if neg > pos:
        return "negative"
    return "neutral"


def _classify_finbert_batch(texts: list[str]) -> list[SentimentLabel]:
    """
    Classify a batch of texts with ProsusAI/finbert via the HF Inference API.
    Falls back to heuristic for the whole batch on any error.
    """
    if not settings.finbert_enabled:
        return [_heuristic_sentiment(t) for t in texts]

    token = (settings.huggingface_api_token or "").strip()
    if not token:
        return [_heuristic_sentiment(t) for t in texts]

    url = f"https://api-inference.huggingface.co/models/{settings.finbert_model_id}"
    headers = {"Authorization": f"Bearer {token}"}

    try:
        with httpx.Client(timeout=20) as client:
            r = client.post(url, headers=headers, json={"inputs": texts})
            r.raise_for_status()
        data = r.json()
    except Exception:  # noqa: BLE001
        return [_heuristic_sentiment(t) for t in texts]

    if not isinstance(data, list):
        return [_heuristic_sentiment(t) for t in texts]

    results: list[SentimentLabel] = []
    for i, item in enumerate(data):
        try:
            best = max(item, key=lambda x: x["score"])
            label = best["label"].lower()
            if label in ("positive", "negative", "neutral"):
                results.append(label)  # type: ignore[arg-type]
            else:
                results.append(_heuristic_sentiment(texts[i]))
        except Exception:  # noqa: BLE001
            results.append(_heuristic_sentiment(texts[i]))

    while len(results) < len(texts):
        results.append("neutral")
    return results


# ── LLM themes + summary ──────────────────────────────────────────────────────

_FALLBACK_THEMES = ["earnings expectations", "analyst commentary", "macro positioning"]


def _generate_themes_and_summary(
    ticker: str,
    enriched_articles: list[dict[str, Any]],
    preferred_model: str,
) -> tuple[list[str], str, str | None, str | None, bool]:
    """
    Use LLMService to extract themes and write a narrative summary.

    Returns:
        (themes, summary, model_used, provider, fallback_used)
    """
    headlines_text = "\n".join(
        f"- [{a.get('sentiment', 'neutral')}] {a.get('headline', '')}"
        for a in enriched_articles[:10]
    )
    prompt = build_news_themes_prompt(ticker, headlines_text)
    result = _llm.generate_response(prompt, preferred_model=preferred_model)

    if result.error or not result.response:
        logger.warning(
            "LLM theme generation failed for %s: %s", ticker, result.error
        )
        return (
            _FALLBACK_THEMES,
            _build_fallback_summary(ticker, enriched_articles),
            None, None, True,
        )

    # Parse JSON from LLM response; strip markdown fences if present.
    raw = result.response.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    start, end = raw.find("{"), raw.rfind("}")
    if start != -1 and end > start:
        raw = raw[start : end + 1]

    try:
        parsed = json.loads(raw)
        themes = [str(t) for t in parsed.get("themes", [])[:3]] or _FALLBACK_THEMES
        summary = str(parsed.get("summary", "")).strip() or _build_fallback_summary(
            ticker, enriched_articles
        )
    except (json.JSONDecodeError, ValueError):
        themes = _FALLBACK_THEMES
        summary = _build_fallback_summary(ticker, enriched_articles)

    return themes, summary, result.model_used, result.provider, result.fallback_used


def _build_fallback_summary(ticker: str, articles: list[dict[str, Any]]) -> str:
    pos = sum(1 for a in articles if a.get("sentiment") == "positive")
    neg = sum(1 for a in articles if a.get("sentiment") == "negative")
    total = len(articles) or 1
    pct_pos = round(100 * pos / total)
    pct_neg = round(100 * neg / total)
    label = (
        "constructive" if pct_pos > pct_neg
        else "cautious" if pct_neg > pct_pos
        else "mixed"
    )
    return (
        f"Recent coverage for {ticker.upper()} is broadly {label} "
        f"({pct_pos}% positive, {pct_neg}% negative across {total} article(s)). "
        "This is for educational purposes only."
    )


# ── Aggregate ─────────────────────────────────────────────────────────────────

def _aggregate_counts(articles: list[NewsArticleItem]) -> AggregateSentiment:
    if not articles:
        return AggregateSentiment(
            positive=0, neutral=100, negative=0, overall_label="neutral"
        )
    pos = sum(1 for a in articles if a.sentiment == "positive")
    neu = sum(1 for a in articles if a.sentiment == "neutral")
    neg = sum(1 for a in articles if a.sentiment == "negative")
    total = len(articles)
    p_pct = round(100 * pos / total)
    n_pct = round(100 * neu / total)
    neg_pct = max(0, 100 - p_pct - n_pct)
    if neg > pos and neg >= neu:
        overall: SentimentLabel = "negative"
    elif pos >= neu and pos >= neg:
        overall = "positive"
    else:
        overall = "neutral"
    return AggregateSentiment(
        positive=p_pct, neutral=n_pct, negative=neg_pct, overall_label=overall
    )


# ── Public entry point ────────────────────────────────────────────────────────

def build_news_sentiment_report(
    ticker: str,
    date_from: str | None,
    date_to: str | None,
    max_articles: int = 10,
    model_name: str | None = None,
) -> NewsSentimentResponse:
    """
    Build a structured news sentiment report for *ticker*.

    Steps:
      1. Fetch articles from Finnhub (or mock data on failure/missing key).
      2. Classify each article with FinBERT (or keyword heuristic fallback).
      3. Generate themes + summary via LLMService (Gemini → Ollama fallback).
    """
    sym = ticker.strip().upper()
    if not sym:
        raise ValueError("ticker is required")

    d_from = _parse_iso_date(date_from)
    d_to = _parse_iso_date(date_to)
    today = datetime.utcnow().date()
    from_str = date_from or (today - timedelta(days=10)).isoformat()
    to_str = date_to or today.isoformat()

    # Step 1: Fetch
    data_fallback_used = False
    try:
        raw = _fetch_finnhub_news(sym, from_str, to_str, max_articles=max_articles)
    except Exception:  # noqa: BLE001
        raw = []
    if not raw:
        raw = _mock_articles(sym)[:max_articles]
        data_fallback_used = True

    filtered = [a for a in raw if _article_in_range(a, d_from, d_to)] or raw
    filtered = filtered[:max_articles]

    # Step 2: FinBERT classification (batched)
    texts = [
        f"{a.get('headline', '')} {a.get('summary', '')}" for a in filtered
    ]
    sentiment_labels = _classify_finbert_batch(texts)
    enriched = [
        {**a, "sentiment": sentiment_labels[i]} for i, a in enumerate(filtered)
    ]

    articles = [NewsArticleItem.model_validate(a) for a in enriched]
    aggregate = _aggregate_counts(articles)

    # Step 3: LLM themes + summary
    preferred = (model_name or "gemini").strip().lower()
    themes, summary, llm_model, llm_provider, llm_fallback = (
        _generate_themes_and_summary(sym, enriched, preferred)
    )

    citations = [
        CitationItem(
            title=a.headline,
            url=a.url,
            source=a.source,
            published_at=a.published_at,
        )
        for a in articles
    ]

    save_research_run(
        "news_sentiment", sym,
        model_used=llm_model,
        provider=llm_provider,
    )

    return NewsSentimentResponse(
        ticker=sym,
        date_from=from_str,
        date_to=to_str,
        aggregate_sentiment=aggregate,
        major_themes=themes,
        articles=articles,
        summary=summary,
        citations=citations,
        disclaimer=_DISCLAIMER,
        fallback_used=data_fallback_used,
        llm_model_used=llm_model,
        llm_provider=llm_provider,
        llm_fallback_used=llm_fallback or False,
    )
