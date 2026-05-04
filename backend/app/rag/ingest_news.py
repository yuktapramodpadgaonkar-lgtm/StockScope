from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Any

from app.rag.store import load_chunks, upsert_chunks


def _text_sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def ingest_news_chunks(ticker: str, bundle: dict[str, Any]) -> dict[str, Any]:
    """
    Convert Layer1 news payload into retrievable chunks and upsert local store.
    """
    sym = ticker.strip().upper()
    ns = bundle.get("news_and_sentiment") or {}
    av_items = ((ns.get("alpha_vantage") or {}).get("items") or []) if ns else []
    yf_items = ((ns.get("headlines") or {}).get("items") or []) if ns else []
    items = av_items if av_items else yf_items

    ingested_at = datetime.now(timezone.utc).isoformat()
    rows: list[dict[str, Any]] = []
    for idx, item in enumerate(items[:40]):
        if not isinstance(item, dict):
            continue
        title = str(item.get("title") or "").strip()
        summary = str(item.get("summary") or "").strip()
        text = " ".join(x for x in [title, summary] if x).strip()
        if not text:
            continue
        source = str(item.get("source") or item.get("publisher") or "news")
        published = str(item.get("published") or "")
        url = str(item.get("url") or item.get("link") or "")
        chunk_id = f"{sym}:news:{idx}:{abs(hash((title, published, url))) % 10_000_000}"
        rows.append(
            {
                "chunk_id": chunk_id,
                "ticker": sym,
                "doc_type": "news",
                "source": source,
                "url": url or None,
                "published_at": published or None,
                "title": title or None,
                "text": text[:2200],
                "text_sha256": _text_sha256(text[:2200]),
                "ingested_at": ingested_at,
            }
        )

    if not rows:
        return {"ingested": 0, "store_total": len(load_chunks())}
    total = upsert_chunks(rows)
    return {"ingested": len(rows), "store_total": total}
