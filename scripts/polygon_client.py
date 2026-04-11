"""
Minimal Polygon.io REST client for reference ticker lookups.

Note: Polygon does not expose "index constituents" as a dedicated endpoint.
We use GET /v3/reference/tickers/{ticker} to validate symbols and prefer names.
"""

from __future__ import annotations

import os
import time
from typing import Any

import httpx

BASE = "https://api.polygon.io"


def get_api_key() -> str:
    key = os.environ.get("POLYGON_API_KEY", "").strip()
    if not key:
        raise RuntimeError(
            "Set POLYGON_API_KEY in the environment (see backend/.env.example).",
        )
    return key


def reference_ticker_details(ticker: str, api_key: str | None = None) -> dict[str, Any] | None:
    """GET /v3/reference/tickers/{ticker}. Returns None on 404."""
    key = api_key or get_api_key()
    url = f"{BASE}/v3/reference/tickers/{ticker.upper()}"
    params = {"apiKey": key}
    with httpx.Client(timeout=45.0) as client:
        r = client.get(url, params=params)
        if r.status_code == 404:
            return None
        r.raise_for_status()
        data = r.json()
    if data.get("status") not in ("OK", "DELAYED") and data.get("status"):
        pass
    return data.get("results")


def enrich_symbols(
    symbols: list[str],
    *,
    delay_s: float = 0.12,
    api_key: str | None = None,
) -> list[dict[str, Any]]:
    """
    For each symbol, fetch Polygon reference details. Skips missing tickers.
    Polygon free tier is rate-limited; small delay between calls.
    """
    key = api_key or get_api_key()
    rows: list[dict[str, Any]] = []
    for i, sym in enumerate(symbols):
        if i:
            time.sleep(delay_s)
        sym = sym.strip().upper()
        if not sym:
            continue
        try:
            info = reference_ticker_details(sym, api_key=key)
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                continue
            raise
        if not info:
            continue
        rows.append(
            {
                "symbol": info.get("ticker", sym),
                "company_name": info.get("name"),
            }
        )
    return rows
