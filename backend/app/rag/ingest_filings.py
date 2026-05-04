from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Any

from app.rag.store import load_chunks, upsert_chunks

_CHUNK = 4000


def _text_sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def ingest_filings_chunks(ticker: str, bundle: dict[str, Any]) -> dict[str, Any]:
    """
    Ingest filings / transcript items from Layer1 when present (e.g. SEC EDGAR text).
    Long bodies are split into fixed-size chunks for retrieval.
    """
    sym = ticker.strip().upper()
    filings = bundle.get("filings_or_transcripts") or {}
    items = filings.get("items") or []
    ingested_at = datetime.now(timezone.utc).isoformat()
    rows: list[dict[str, Any]] = []

    for idx, item in enumerate(items):
        if not isinstance(item, dict):
            continue
        text = str(item.get("text") or item.get("content") or "").strip()
        if not text:
            continue
        title = str(item.get("title") or f"filing-{idx}")
        url = str(item.get("url") or "")
        published = str(item.get("published_at") or item.get("date") or "")
        acc = str(item.get("accession") or idx)
        base_id = f"{sym}:filing:{acc}"

        for part, start in enumerate(range(0, len(text), _CHUNK)):
            chunk_text = text[start : start + _CHUNK]
            if not chunk_text.strip():
                continue
            chunk_id = f"{base_id}:{part}"
            rows.append(
                {
                    "chunk_id": chunk_id,
                    "ticker": sym,
                    "doc_type": "filing",
                    "source": str(item.get("source") or "sec"),
                    "url": url or None,
                    "published_at": published or None,
                    "title": title if part == 0 else f"{title} (part {part})",
                    "text": chunk_text,
                    "text_sha256": _text_sha256(chunk_text),
                    "ingested_at": ingested_at,
                }
            )

    if not rows:
        return {"ingested": 0, "store_total": len(load_chunks())}
    total = upsert_chunks(rows)
    return {"ingested": len(rows), "store_total": total}
