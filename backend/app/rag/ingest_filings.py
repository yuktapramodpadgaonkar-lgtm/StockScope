from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Any

from app.rag.store import load_chunks, upsert_chunks

# Legacy fallback when filing has no structured `sections` (e.g. 8-K, odd HTML).
_CHUNK_LEGACY = 4000
# Cap per stored row; long sections split into part 0, 1, …
_MAX_SECTION_CHARS = 14_000


def _text_sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def ingest_filings_chunks(ticker: str, bundle: dict[str, Any]) -> dict[str, Any]:
    """
    Ingest filings from Layer1 (SEC EDGAR text).

    When items include `sections` from section-aware HTML parsing (10-K/10-Q Items),
    one chunk row per section (risk_factors, mdna, …) for better retrieval.
    Otherwise falls back to fixed-size windows on flat `text`.
    """
    sym = ticker.strip().upper()
    filings = bundle.get("filings_or_transcripts") or {}
    items = filings.get("items") or []
    ingested_at = datetime.now(timezone.utc).isoformat()
    rows: list[dict[str, Any]] = []

    for idx, item in enumerate(items):
        if not isinstance(item, dict):
            continue
        title = str(item.get("title") or f"filing-{idx}")
        url = str(item.get("url") or "")
        published = str(item.get("published_at") or item.get("date") or "")
        acc = str(item.get("accession") or idx)
        base_id = f"{sym}:filing:{acc}"
        sections = item.get("sections")

        if isinstance(sections, list) and sections:
            for sec in sections:
                if not isinstance(sec, dict):
                    continue
                body = str(sec.get("text") or "").strip()
                if not body:
                    continue
                sk = str(sec.get("section_key") or "unknown")
                stitle = str(sec.get("title") or sk)
                item_code = sec.get("item_code")
                for part, start in enumerate(range(0, len(body), _MAX_SECTION_CHARS)):
                    chunk_text = body[start : start + _MAX_SECTION_CHARS]
                    if not chunk_text.strip():
                        continue
                    chunk_id = f"{base_id}:{sk}" if part == 0 else f"{base_id}:{sk}:{part}"
                    row_title = stitle if part == 0 else f"{stitle} (part {part})"
                    rows.append(
                        {
                            "chunk_id": chunk_id,
                            "ticker": sym,
                            "doc_type": "filing",
                            "source": str(item.get("source") or "sec"),
                            "url": url or None,
                            "published_at": published or None,
                            "title": row_title,
                            "text": chunk_text,
                            "text_sha256": _text_sha256(chunk_text),
                            "ingested_at": ingested_at,
                            "section_key": sk,
                            "item_code": item_code,
                        }
                    )
            continue

        text = str(item.get("text") or item.get("content") or "").strip()
        if not text:
            continue

        for part, start in enumerate(range(0, len(text), _CHUNK_LEGACY)):
            chunk_text = text[start : start + _CHUNK_LEGACY]
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
