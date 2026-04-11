"""
Week 1 mock news sentiment: static article list with per-article labels.

TODO: Finnhub / other news API + FinBERT (or hosted model) for real scoring.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from app.schemas.news_sentiment import (
    AggregateSentiment,
    NewsArticleItem,
    NewsSentimentResponse,
    SentimentLabel,
)

_DISCLAIMER = "Sentiment analysis is informational only and not financial advice."


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
            "sentiment": "positive",
            "summary": "Article discusses strong AI demand and bullish expectations.",
        },
        {
            "headline": "Mixed views emerge on semiconductor valuations",
            "source": "Mock Market Watch",
            "url": "https://example.com/nvda-2",
            "published_at": "2026-04-09T12:00:00Z",
            "sentiment": "neutral",
            "summary": "Article highlights both upside and valuation concerns.",
        },
        {
            "headline": "Traders watch macro data ahead of key earnings week",
            "source": "Mock Wire",
            "url": "https://example.com/nvda-3",
            "published_at": "2026-04-08T15:30:00Z",
            "sentiment": "negative",
            "summary": "Article notes caution on rates and positioning into events.",
        },
        {
            "headline": f"Analysts lift estimates on {sym} data-center outlook",
            "source": "Mock Desk Research",
            "url": "https://example.com/nvda-4",
            "published_at": "2026-04-07T11:00:00Z",
            "sentiment": "positive",
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
        positive=p_pct,
        neutral=n_pct,
        negative=neg_pct,
        overall_label=overall,
    )


def build_news_sentiment_report(
    ticker: str,
    date_from: str | None,
    date_to: str | None,
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

    raw = _mock_articles(sym)
    filtered = [a for a in raw if _article_in_range(a, d_from, d_to)]
    if not filtered:
        filtered = raw

    articles = [NewsArticleItem.model_validate(a) for a in filtered]
    aggregate = _aggregate_counts(articles)

    themes = [
        "AI demand optimism",
        "analyst upgrades",
        "earnings expectations",
    ]

    llm_summary = (
        f"Recent mock coverage for {sym} is mostly {aggregate.overall_label}, "
        "driven by optimism around demand themes, with some valuation caution "
        "from mixed industry pieces."
    )

    return NewsSentimentResponse(
        ticker=sym,
        date_from=date_from,
        date_to=date_to,
        aggregate_sentiment=aggregate,
        major_themes=themes,
        articles=articles,
        llm_summary=llm_summary,
        disclaimer=_DISCLAIMER,
    )
