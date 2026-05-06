from __future__ import annotations

import math
from collections import Counter
from typing import Sequence


def _avgdl(doc_lens: Sequence[int]) -> float:
    if not doc_lens:
        return 0.0
    return sum(doc_lens) / max(1, len(doc_lens))


def bm25_scores(
    query_tokens: list[str],
    doc_tokens: list[list[str]],
    *,
    k1: float = 1.5,
    b: float = 0.75,
    epsilon: float = 0.25,
) -> list[float]:
    """
    Okapi BM25+ over a small in-memory corpus (e.g. all chunks for one ticker).
    Returns one non-negative score per document, same length as doc_tokens.
    """
    n_docs = len(doc_tokens)
    if n_docs == 0:
        return []

    doc_lens = [len(d) for d in doc_tokens]
    avgdl = _avgdl(doc_lens)
    if avgdl <= 0:
        avgdl = 1.0

    df: dict[str, int] = {}
    for toks in doc_tokens:
        seen = set(toks)
        for t in seen:
            df[t] = df.get(t, 0) + 1

    idf: dict[str, float] = {}
    for term, freq in df.items():
        idf[term] = math.log((n_docs - freq + 0.5) / (freq + 0.5) + 1.0)

    q_counts = Counter(query_tokens)
    scores: list[float] = []

    for toks, dl in zip(doc_tokens, doc_lens):
        tf = Counter(toks)
        s = 0.0
        for q_term, qtf in q_counts.items():
            if q_term not in tf:
                continue
            freq = tf[q_term]
            idf_q = idf.get(q_term, 0.0)
            denom = freq + k1 * (1 - b + b * dl / avgdl)
            if denom <= 0:
                continue
            s += idf_q * ((freq * (k1 + 1)) / denom + epsilon)
        scores.append(max(0.0, s))

    return scores


def min_max_norm(values: list[float]) -> list[float]:
    if not values:
        return []
    lo = min(values)
    hi = max(values)
    if hi <= lo:
        return [1.0 if hi > 0 else 0.0 for _ in values]
    return [(v - lo) / (hi - lo) for v in values]
