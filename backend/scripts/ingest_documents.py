#!/usr/bin/env python3
"""
Lightweight RAG ingest script for demo documents.

Usage (from repo root):
    python backend/scripts/ingest_documents.py

  or from backend/:
    python scripts/ingest_documents.py

Reads .txt and .json files from backend/data/documents/ and writes chunks
to backend/data/rag/chunks.jsonl via the existing RAG store.

File naming convention:
  <TICKER>_<description>.txt    — entire file becomes one chunk for <TICKER>
  <TICKER>_<description>.json   — JSON array of {text, title?, published_at?, url?}
                                   OR a single JSON object with those fields
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

# Ensure `backend/` is importable regardless of working directory
_BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_BACKEND))

from app.rag.store import upsert_chunks  # noqa: E402

DOCS_DIR = _BACKEND / "data" / "documents"
_INGESTED_AT = datetime.now(timezone.utc).isoformat()


def _chunk_id(ticker: str, text: str) -> str:
    h = hashlib.sha1(f"{ticker}|{text[:200]}".encode()).hexdigest()[:16]
    return f"ingest_{ticker}_{h}"


def _ticker_from_stem(stem: str) -> str | None:
    """Extract ticker from filename stem, e.g. 'AAPL_overview' → 'AAPL'."""
    parts = stem.upper().split("_")
    candidate = parts[0]
    if 1 <= len(candidate) <= 8 and candidate.isalpha():
        return candidate
    return None


def _ingest_txt(path: Path, ticker: str) -> list[dict]:
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        return []
    return [
        {
            "chunk_id": _chunk_id(ticker, text),
            "ticker": ticker,
            "doc_type": "document",
            "title": path.stem.replace("_", " ").title(),
            "text": text,
            "published_at": None,
            "ingested_at": _INGESTED_AT,
            "source": path.name,
        }
    ]


def _ingest_json(path: Path, ticker: str) -> list[dict]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    items: list[dict] = raw if isinstance(raw, list) else [raw]
    chunks: list[dict] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        text = str(item.get("text") or item.get("content") or "").strip()
        if not text:
            continue
        sym = str(item.get("ticker") or ticker).upper()
        chunks.append(
            {
                "chunk_id": _chunk_id(sym, text),
                "ticker": sym,
                "doc_type": str(item.get("doc_type") or "document"),
                "title": str(item.get("title") or path.stem.replace("_", " ").title()),
                "text": text,
                "published_at": item.get("published_at"),
                "ingested_at": _INGESTED_AT,
                "source": path.name,
                "url": item.get("url"),
            }
        )
    return chunks


def main() -> None:
    if not DOCS_DIR.exists():
        print(f"[ingest] Documents directory not found: {DOCS_DIR}")
        print("[ingest] Create it and add files named <TICKER>_description.txt")
        sys.exit(1)

    all_chunks: list[dict] = []
    skipped: list[str] = []

    for path in sorted(DOCS_DIR.iterdir()):
        suffix = path.suffix.lower()
        ticker = _ticker_from_stem(path.stem)
        if ticker is None:
            skipped.append(path.name)
            continue
        try:
            if suffix == ".txt":
                chunks = _ingest_txt(path, ticker)
            elif suffix == ".json":
                chunks = _ingest_json(path, ticker)
            else:
                continue
        except Exception as exc:  # noqa: BLE001
            print(f"[ingest] SKIP {path.name}: {exc}")
            skipped.append(path.name)
            continue

        if chunks:
            print(f"[ingest] {path.name}  →  {len(chunks)} chunk(s) for {ticker}")
            all_chunks.extend(chunks)

    if not all_chunks:
        print("[ingest] No chunks produced — nothing to write.")
        if skipped:
            print(f"[ingest] Skipped (no recognisable ticker in filename): {', '.join(skipped)}")
        return

    total = upsert_chunks(all_chunks)
    tickers_seen = sorted({c["ticker"] for c in all_chunks})
    print(f"\n[ingest] Done. {len(all_chunks)} chunk(s) written for: {', '.join(tickers_seen)}")
    print(f"[ingest] RAG store now contains {total} total chunk(s).")
    if skipped:
        print(f"[ingest] Skipped: {', '.join(skipped)}")


if __name__ == "__main__":
    main()
