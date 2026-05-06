"""SEC filings / transcripts — EDGAR when configured, else stub."""

from __future__ import annotations

from typing import Any

from app.core.config import settings
from app.tools.sec_edgar_tool import fetch_recent_filings_bundle


def get_filings_or_transcripts(ticker: str, *, limit: int = 5) -> dict[str, Any]:
    """
    When `SEC_EDGAR_ENABLED=true` and `SEC_USER_AGENT` is set, pulls recent 10-K / 10-Q / 8-K text from SEC EDGAR.
    Otherwise returns the Phase-2-compatible stub shape (empty items).
    """
    sym = ticker.strip().upper()
    lim = min(int(limit), max(1, int(settings.sec_filings_limit)))

    if settings.sec_edgar_enabled and (settings.sec_user_agent or "").strip():
        try:
            bundle, calls = fetch_recent_filings_bundle(sym, limit=lim)
            bundle["http_calls"] = int(calls)
            return bundle
        except Exception as e:
            return {
                "ticker": sym,
                "source": "sec_edgar",
                "items": [],
                "http_calls": 0,
                "error": "sec_fetch_failed",
                "detail": str(e)[:400],
            }

    return {
        "ticker": sym,
        "source": "none_yet",
        "items": [],
        "http_calls": 0,
        "note": (
            "Filings disabled or SEC_USER_AGENT unset. "
            "Enable with SEC_EDGAR_ENABLED=true and set SEC_USER_AGENT per SEC fair-access policy."
        ),
    }
