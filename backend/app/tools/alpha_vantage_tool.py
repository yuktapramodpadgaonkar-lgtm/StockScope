"""Alpha Vantage — news + sentiment (one HTTP call per ticker bundle)."""

from __future__ import annotations

from typing import Any

import httpx

from app.core.config import settings

_AV_BASE = "https://www.alphavantage.co/query"


def fetch_news_sentiment(ticker: str, *, limit: int = 20) -> tuple[dict[str, Any], int]:
    """
    NEWS_SENTIMENT endpoint. Returns (payload, http_calls_made).
    If API key is missing, returns a skip marker and 0 calls.
    """
    sym = ticker.strip().upper()
    key = (settings.alpha_vantage_api_key or "").strip()
    if not key:
        return (
            {
                "ticker": sym,
                "source": "alpha_vantage",
                "skipped": True,
                "reason": "ALPHA_VANTAGE_API_KEY not set — use yfinance news fallback in layer1.",
                "items": [],
                "feed": [],
            },
            0,
        )

    params = {
        "function": "NEWS_SENTIMENT",
        "tickers": sym,
        "limit": str(max(1, min(limit, 50))),
        "apikey": key,
    }
    with httpx.Client(timeout=45.0) as client:
        r = client.get(_AV_BASE, params=params)
        r.raise_for_status()
        data = r.json()

    # Alpha Vantage uses "Information" or "Note" for rate-limit / invalid key messages
    if "feed" not in data:
        note = data.get("Note") or data.get("Information") or str(data)[:500]
        return (
            {
                "ticker": sym,
                "source": "alpha_vantage",
                "error": "unexpected_response",
                "detail": note,
                "items": [],
                "feed": [],
            },
            1,
        )

    feed = data.get("feed") or []
    items: list[dict[str, Any]] = []
    for row in feed[:limit]:
        if not isinstance(row, dict):
            continue
        items.append(
            {
                "title": row.get("title"),
                "url": row.get("url"),
                "source": row.get("source"),
                "published": row.get("time_published"),
                "summary": row.get("summary"),
                "overall_sentiment_label": row.get("overall_sentiment_label"),
                "ticker_sentiment": row.get("ticker_sentiment"),
            }
        )

    return (
        {
            "ticker": sym,
            "source": "alpha_vantage",
            "skipped": False,
            "items": items,
            "feed_meta": {
                "items_in_feed": len(feed),
            },
        },
        1,
    )
