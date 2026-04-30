"""News sentiment service with Finnhub integration + graceful fallback."""

from __future__ import annotations

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
from services.history_service import save_research_run

_DISCLAIMER = "This is for educational purposes only and not financial advice."


def _parse_iso_date(s: str | None) -> date | None:
    if not s:
        return None
    try:
        return date.fromisoformat(s.strip()[:10])
    except ValueError:
        return None


def _mock_articles(ticker: str) -> list[dict[str, Any]]:
    sym = ticker.upper()
    return [
        {
            "headline": f"{sym} gains as AI demand remains strong",
            "source": "Mock Finance News",
            "url": "https://example.com/nvda-1",
            "published_at": "2026-04-10T09:00:00Z",
            "summary": "Article discusses strong AI demand and bullish expectations.",
        },
        {
            "headline": "Mixed views emerge on semiconductor valuations",
            "source": "Mock Market Watch",
            "url": "https://example.com/nvda-2",
            "published_at": "2026-04-09T12:00:00Z",
            "summary": "Article highlights both upside and valuation concerns.",
        },
        {
            "headline": "Traders watch macro data ahead of key earnings week",
            "source": "Mock Wire",
            "url": "https://example.com/nvda-3",
            "published_at": "2026-04-08T15:30:00Z",
            "summary": "Article notes caution on rates and positioning into events.",
        },
        {
            "headline": f"Analysts lift estimates on {sym} data-center outlook",
            "source": "Mock Desk Research",
            "url": "https://example.com/nvda-4",
            "published_at": "2026-04-07T11:00:00Z",
            "summary": "Analyst commentary frames upside to estimates.",
        },
    ]


def _article_in_range(item: dict[str, Any], d_from: date | None, d_to: date | None) -> bool:
    if d_from is None and d_to is None:
        return True
    try:
        d = datetime.fromisoformat(item["published_at"].replace("Z", "+00:00")).date()
    except ValueError:
        return True
    if d_from and d < d_from:
        return False
    if d_to and d > d_to:
        return False
    return True


def _score_sentiment(text: str) -> SentimentLabel:
    """
    Fallback sentiment heuristic.

    TODO: Swap this with FinBERT classification if model is configured.
    """
    positive_markers = (
        "strong",
        "gain",
        "upside",
        "bullish",
        "upgrade",
        "beat",
        "optimism",
        "growth",
    )
    negative_markers = (
        "risk",
        "caution",
        "downgrade",
        "bearish",
        "concern",
        "weak",
        "miss",
        "decline",
    )
    text_l = text.lower()
    pos = sum(1 for w in positive_markers if w in text_l)
    neg = sum(1 for w in negative_markers if w in text_l)
    if pos > neg:
        return "positive"
    if neg > pos:
        return "negative"
    return "neutral"


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
    return AggregateSentiment(positive=p_pct, neutral=n_pct, negative=neg_pct, overall_label=overall)


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
        iso_ts = datetime.utcfromtimestamp(item.get("datetime") or 0).replace(microsecond=0).isoformat() + "Z"
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


def build_news_sentiment_report(
    ticker: str,
    date_from: str | None,
    date_to: str | None,
    max_articles: int = 10,
) -> NewsSentimentResponse:
    """
    Return structured mock sentiment for ``ticker``, optionally filtered by dates.

    Invalid date strings are ignored for filtering (articles still returned).
    """
    sym = ticker.strip().upper()
    if not sym:
        raise ValueError("ticker is required")

    d_from = _parse_iso_date(date_from)
    d_to = _parse_iso_date(date_to)

    today = datetime.utcnow().date()
    default_from = (today - timedelta(days=10)).isoformat()
    from_str = date_from or default_from
    to_str = date_to or today.isoformat()

    fallback_used = False
    try:
        raw = _fetch_finnhub_news(sym, from_str, to_str, max_articles=max_articles)
    except Exception:
        raw = []
    if not raw:
        raw = _mock_articles(sym)[:max_articles]
        fallback_used = True

    filtered = [a for a in raw if _article_in_range(a, d_from, d_to)]
    if not filtered:
        filtered = raw

    enriched = []
    for a in filtered[:max_articles]:
        text = f"{a.get('headline', '')} {a.get('summary', '')}"
        enriched.append({**a, "sentiment": _score_sentiment(text)})

    articles = [NewsArticleItem.model_validate(a) for a in enriched]
    aggregate = _aggregate_counts(articles)

    themes = [
        "AI demand optimism",
        "analyst upgrades",
        "earnings expectations",
    ]

    summary = (
        f"Coverage for {sym} skews {aggregate.overall_label}: "
        f"{aggregate.positive}% positive, {aggregate.neutral}% neutral, "
        f"{aggregate.negative}% negative. "
        "This is derived from lightweight article scoring and should be treated as directional context."
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
    save_research_run("news_sentiment", sym)

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
        fallback_used=fallback_used,
    )
