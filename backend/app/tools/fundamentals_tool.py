"""Fundamentals snapshot — primary source: yfinance Ticker.info (subset)."""

from __future__ import annotations

from typing import Any

import yfinance as yf

# Keys we try to surface for scoring / LLM (presence varies by ticker)
_INFO_KEYS = (
    "shortName",
    "longName",
    "sector",
    "industry",
    "marketCap",
    "enterpriseValue",
    "trailingPE",
    "forwardPE",
    "priceToBook",
    "profitMargins",
    "operatingMargins",
    "grossMargins",
    "returnOnEquity",
    "returnOnAssets",
    "debtToEquity",
    "currentRatio",
    "quickRatio",
    "totalRevenue",
    "revenueGrowth",
    "earningsGrowth",
    "earningsQuarterlyGrowth",
    "ebitda",
    "dividendYield",
    "payoutRatio",
    "beta",
    "fiftyTwoWeekHigh",
    "fiftyTwoWeekLow",
    "targetMeanPrice",
    "numberOfAnalystOpinions",
    "recommendationKey",
    "currency",
    "exchange",
)


def extract_fundamental_fields(info: dict[str, Any]) -> dict[str, Any]:
    """Subset of info dict for LLM / scoring (no extra network calls)."""
    fields: dict[str, Any] = {}
    for k in _INFO_KEYS:
        v = info.get(k)
        if v is not None and v != "":
            if hasattr(v, "item"):
                try:
                    v = v.item()
                except Exception:
                    pass
            fields[k] = v
    return fields


def get_fundamentals(ticker: str) -> dict[str, Any]:
    sym = ticker.strip().upper()
    t = yf.Ticker(sym)
    info = t.info if t.info else {}
    if not info:
        return {
            "ticker": sym,
            "source": "yfinance",
            "error": "no_info",
            "fields": {},
        }

    return {
        "ticker": sym,
        "source": "yfinance",
        "fields": extract_fundamental_fields(info),
    }
