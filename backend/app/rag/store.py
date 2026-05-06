from __future__ import annotations

import json
import time
from collections import defaultdict
from pathlib import Path
from typing import Any

RAG_DIR = Path(__file__).resolve().parents[3] / "data" / "rag"
CHUNKS_PATH = RAG_DIR / "chunks.jsonl"
TICKER_EMBED_DIR = RAG_DIR / "index" / "by_ticker"


def ensure_store() -> None:
    RAG_DIR.mkdir(parents=True, exist_ok=True)
    if not CHUNKS_PATH.exists():
        CHUNKS_PATH.write_text("", encoding="utf-8")


def _clear_ticker_embedding_npz() -> None:
    if not TICKER_EMBED_DIR.exists():
        return
    for p in TICKER_EMBED_DIR.glob("*.npz"):
        try:
            p.unlink()
        except OSError:
            pass


def maybe_rotate_chunks_file() -> None:
    ensure_store()
    if not CHUNKS_PATH.exists():
        return
    try:
        size = CHUNKS_PATH.stat().st_size
    except OSError:
        return
    from app.core.config import settings

    if size < int(settings.rag_rotate_bytes):
        return
    archive = RAG_DIR / f"chunks_archive_{int(time.time())}.jsonl"
    try:
        CHUNKS_PATH.rename(archive)
    except OSError:
        return
    _clear_ticker_embedding_npz()
    CHUNKS_PATH.write_text("", encoding="utf-8")


def _recency_tuple(row: dict[str, Any]) -> tuple[float, str]:
    """Higher tuple sorts newer first."""
    ts = _parse_iso_ts(str(row.get("published_at") or ""))
    if ts is None:
        ts = _parse_iso_ts(str(row.get("ingested_at") or ""))
    if ts is None:
        ts = 0.0
    return (ts, str(row.get("chunk_id") or ""))


def _parse_iso_ts(s: str) -> float | None:
    if not s:
        return None
    t = s.replace("Z", "+00:00")
    try:
        from datetime import datetime

        return datetime.fromisoformat(t[:32]).timestamp()
    except ValueError:
        return None


def _prune_merged(merged: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    from app.core.config import settings

    max_per = max(10, int(settings.rag_max_chunks_per_ticker))
    max_total = max(100, int(settings.rag_max_total_chunks))

    by_sym: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in merged.values():
        sym = str(row.get("ticker") or "UNK").upper()
        by_sym[sym].append(row)

    trimmed: list[dict[str, Any]] = []
    for lst in by_sym.values():
        lst.sort(key=_recency_tuple, reverse=True)
        trimmed.extend(lst[:max_per])

    trimmed.sort(key=_recency_tuple, reverse=True)
    trimmed = trimmed[:max_total]
    out: dict[str, dict[str, Any]] = {}
    for row in trimmed:
        cid = str(row.get("chunk_id") or "")
        if cid:
            out[cid] = row
    return out


def load_chunks() -> list[dict[str, Any]]:
    ensure_store()
    out: list[dict[str, Any]] = []
    for line in CHUNKS_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
            if isinstance(row, dict):
                out.append(row)
        except json.JSONDecodeError:
            continue
    return out


def upsert_chunks(new_rows: list[dict[str, Any]]) -> int:
    """
    Upsert by chunk_id. Applies rotation (size cap), prune (counts), returns final row count.
    """
    maybe_rotate_chunks_file()
    ensure_store()
    merged: dict[str, dict[str, Any]] = {}
    for row in load_chunks():
        cid = str(row.get("chunk_id") or "")
        if cid:
            merged[cid] = row
    for row in new_rows:
        cid = str(row.get("chunk_id") or "")
        if cid:
            merged[cid] = row

    merged = _prune_merged(merged)

    with CHUNKS_PATH.open("w", encoding="utf-8", newline="\n") as f:
        for row in merged.values():
            f.write(json.dumps(row, ensure_ascii=True) + "\n")
    return len(merged)
