"""SEC filings / transcripts — stub until RAG ingest (Phase 5)."""

from __future__ import annotations

from typing import Any


def get_filings_or_transcripts(ticker: str, *, limit: int = 5) -> dict[str, Any]:
    """
    Placeholder: real implementation should map ticker→CIK and pull EDGAR indices
    or use a vendor API. Same return shape for the report pipeline.
    """
    _ = limit
    sym = ticker.strip().upper()
    return {
        "ticker": sym,
        "source": "none_yet",
        "items": [],
        "note": (
            "Filings and transcripts are not wired in Phase 2. "
            "Plan: SEC EDGAR or edgartools + chunking for RAG (see docs/BuySellAnalysis-data-sources.md)."
        ),
    }
