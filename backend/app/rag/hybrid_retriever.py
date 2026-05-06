from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any

import numpy as np

from app.core.config import settings
from app.rag.bm25 import bm25_scores, min_max_norm
from app.rag.embedding_index import embed_query_text, load_ticker_vectors
from app.rag.store import load_chunks

_WORD = re.compile(r"[A-Za-z0-9_]+")

_STOP = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "but",
    "by",
    "for",
    "from",
    "if",
    "in",
    "into",
    "is",
    "it",
    "its",
    "of",
    "on",
    "or",
    "the",
    "to",
    "was",
    "were",
    "with",
}


def _tokens(text: str) -> list[str]:
    return [
        m.group(0).lower()
        for m in _WORD.finditer(text or "")
        if m.group(0).lower() not in _STOP and len(m.group(0)) > 2
    ]


def _parse_published_ts(value: str | None) -> float | None:
    if not value:
        return None
    s = str(value).replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(s[:32])
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.timestamp()
    except ValueError:
        return None


def _within_max_age(row: dict[str, Any], max_age_days: int | None) -> bool:
    if max_age_days is None or max_age_days < 0:
        return True
    ts = _parse_published_ts(str(row.get("published_at") or "") or None)
    if ts is None:
        return True
    now = datetime.now(timezone.utc).timestamp()
    age_days = (now - ts) / 86400.0
    return age_days <= float(max_age_days)


def retrieve_chunks(
    *,
    ticker: str,
    query: str,
    top_k: int = 6,
    doc_types: list[str] | None = None,
    max_age_days: int | None = None,
) -> list[dict[str, Any]]:
    """
    Hybrid retrieval: BM25 (keyword) + dense cosine similarity when HF embeddings are available.
    `max_age_days` filters on `published_at` when parseable; rows without a date are kept.
    """
    sym = ticker.strip().upper()
    allowed = {d.lower() for d in (doc_types or [])}

    if max_age_days is None:
        d = int(settings.rag_max_chunk_age_days)
        eff_age: int | None = None if d < 0 else d
    else:
        eff_age = None if int(max_age_days) < 0 else int(max_age_days)

    rows = [
        r
        for r in load_chunks()
        if str(r.get("ticker") or "").upper() == sym
        and (not allowed or str(r.get("doc_type") or "").lower() in allowed)
        and _within_max_age(r, eff_age)
    ]

    if not rows:
        return []

    doc_tokens = [_tokens(str(r.get("text") or "")) for r in rows]
    q_tokens = _tokens(query)
    raw_bm25 = bm25_scores(q_tokens, doc_tokens)
    bm25_n = min_max_norm(raw_bm25)

    vec_by_id = load_ticker_vectors(sym)
    q_vec: np.ndarray | None = None
    if vec_by_id:
        q_vec = embed_query_text(query)

    cos_raw: list[float] = []
    for r in rows:
        cid = str(r.get("chunk_id") or "")
        v = vec_by_id.get(cid) if vec_by_id and cid else None
        if v is None or q_vec is None:
            cos_raw.append(0.0)
        else:
            cos_raw.append(float(v @ q_vec))
    cos_n = min_max_norm(cos_raw) if q_vec is not None else [0.0] * len(rows)

    w_b = float(settings.rag_bm25_weight)
    w_e = float(settings.rag_embedding_weight)
    if q_vec is None:
        w_b, w_e = 1.0, 0.0
    else:
        s = w_b + w_e
        if s > 0:
            w_b /= s
            w_e /= s

    scored: list[tuple[float, dict[str, Any]]] = []
    for i, r in enumerate(rows):
        hybrid = w_b * bm25_n[i] + w_e * cos_n[i]
        if hybrid <= 0 and raw_bm25[i] <= 0 and cos_raw[i] <= 0:
            continue
        out = dict(r)
        out["retrieval_score"] = round(float(hybrid), 5)
        out["retrieval_bm25"] = round(float(raw_bm25[i]), 5)
        out["retrieval_cosine"] = round(float(cos_raw[i]), 5) if q_vec is not None else None
        scored.append((hybrid, out))

    scored.sort(key=lambda x: x[0], reverse=True)
    if not scored and rows:
        k = max(1, min(top_k, 20))
        out: list[dict[str, Any]] = []
        for r in rows[:k]:
            d = dict(r)
            d["retrieval_score"] = 0.0
            d["retrieval_bm25"] = 0.0
            d["retrieval_cosine"] = None
            out.append(d)
        return out
    return [r for _, r in scored[: max(1, min(top_k, 20))]]
