"""Finnhub — analyst recommendation trends (one HTTP call when API key is set)."""

from __future__ import annotations

from typing import Any

import httpx

from app.core.config import settings

_FH_BASE = "https://finnhub.io/api/v1"


def fetch_recommendation_trends(ticker: str) -> tuple[dict[str, Any], int]:
    """
    GET /stock/recommendation. Returns (payload, http_calls_made).
    If API key is missing, returns skip marker and 0 calls (use yfinance info fields instead).
    """
    sym = ticker.strip().upper()
    token = (settings.finnhub_api_key or "").strip()
    if not token:
        return (
            {
                "ticker": sym,
                "source": "finnhub",
                "skipped": True,
                "reason": "FINNHUB_API_KEY not set — analyst consensus taken from yfinance info (no extra call).",
                "trend": [],
            },
            0,
        )

    url = f"{_FH_BASE}/stock/recommendation"
    params = {"symbol": sym, "token": token}
    with httpx.Client(timeout=30.0) as client:
        r = client.get(url, params=params)
        r.raise_for_status()
        raw = r.json()

    # API returns a list of {period, buy, hold, sell, strongBuy, strongSell}
    trend: list[dict[str, Any]] = []
    if isinstance(raw, list):
        for row in raw:
            if isinstance(row, dict):
                trend.append(row)

    return (
        {
            "ticker": sym,
            "source": "finnhub",
            "skipped": False,
            "trend": trend,
        },
        1,
    )
