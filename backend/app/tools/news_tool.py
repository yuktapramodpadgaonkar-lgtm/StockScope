"""Recent headlines — primary source: yfinance Ticker.news."""

from __future__ import annotations

from typing import Any

import yfinance as yf


def yfinance_news_from_ticker(t: yf.Ticker, sym: str, *, limit: int = 15) -> dict[str, Any]:
    """Use an existing Ticker instance (counts as one yfinance news fetch)."""
    raw = getattr(t, "news", None) or []
    items: list[dict[str, Any]] = []
    for n in raw[: max(1, min(limit, 50))]:
        if not isinstance(n, dict):
            continue
        items.append(
            {
                "title": n.get("title"),
                "publisher": n.get("publisher"),
                "link": n.get("link"),
                "published": n.get("providerPublishTime"),
            }
        )

    return {
        "ticker": sym,
        "source": "yfinance",
        "items": items,
        "count": len(items),
    }


def get_recent_news(ticker: str, *, limit: int = 15) -> dict[str, Any]:
    sym = ticker.strip().upper()
    t = yf.Ticker(sym)
    return yfinance_news_from_ticker(t, sym, limit=limit)
