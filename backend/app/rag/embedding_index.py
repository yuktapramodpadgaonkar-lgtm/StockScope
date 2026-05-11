from __future__ import annotations

from pathlib import Path
from typing import Any

import httpx
import numpy as np

from app.core.config import settings
from app.rag.store import RAG_DIR

TICKER_INDEX_DIR = RAG_DIR / "index" / "by_ticker"


def _ticker_npz_path(sym: str) -> Path:
    safe = "".join(c for c in sym.upper() if c.isalnum()) or "UNK"
    TICKER_INDEX_DIR.mkdir(parents=True, exist_ok=True)
    return TICKER_INDEX_DIR / f"{safe}.npz"


def _l2_normalize_rows(mat: np.ndarray) -> np.ndarray:
    if mat.size == 0:
        return mat
    norms = np.linalg.norm(mat, axis=1, keepdims=True)
    norms = np.where(norms == 0, 1.0, norms)
    return mat / norms


def _parse_hf_embeddings(data: Any, batch_len: int) -> list[list[float]]:
    """Normalize HF inference JSON into `batch_len` embedding rows."""
    # Some deployments wrap the payload once more.
    if isinstance(data, list) and len(data) == 1 and batch_len == 1:
        inner = data[0]
        if isinstance(inner, list) and inner and isinstance(inner[0], (int, float)):
            return [[float(x) for x in inner]]

    if batch_len == 1 and isinstance(data, list) and data and isinstance(data[0], (int, float)):
        return [[float(x) for x in data]]

    if isinstance(data, list) and data and isinstance(data[0], list) and data[0] and isinstance(data[0][0], list):
        out_mean: list[list[float]] = []
        for sent in data:
            if not isinstance(sent, list) or not sent:
                continue
            if isinstance(sent[0], list):
                arr = np.mean(np.asarray(sent, dtype=np.float32), axis=0)
                out_mean.append(arr.astype(float).tolist())
            elif isinstance(sent[0], (int, float)):
                out_mean.append([float(x) for x in sent])
        if len(out_mean) == batch_len:
            return out_mean

    if isinstance(data, list):
        out: list[list[float]] = []
        for row in data:
            if isinstance(row, list) and row and isinstance(row[0], (int, float)):
                out.append([float(x) for x in row])
            elif isinstance(row, dict) and isinstance(row.get("embedding"), list):
                emb = row["embedding"]
                if emb and isinstance(emb[0], (int, float)):
                    out.append([float(x) for x in emb])
        if len(out) == batch_len:
            return out

    raise RuntimeError("unexpected_embedding_shape")


def _hf_embed_batch(texts: list[str]) -> np.ndarray:
    """
    Embed a batch of texts via huggingface_hub.InferenceClient (routed inference).
    Replaces the deprecated /api-inference REST endpoint that 404s for sentence-transformers.
    Falls back to legacy REST only if the client import fails.
    """
    token = (settings.huggingface_api_token or "").strip()
    if not token:
        raise RuntimeError("missing_hf_token")

    model_id = (settings.rag_embedding_model or "").strip()
    if not model_id:
        raise RuntimeError("missing_embedding_model")

    try:
        from huggingface_hub import InferenceClient
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(f"huggingface_hub_import_failed: {exc!s}") from exc

    client = InferenceClient(api_key=token, timeout=60.0)
    out_rows: list[list[float]] = []

    for text in texts:
        snippet = (text or "")[:8000]
        try:
            vec = client.feature_extraction(snippet, model=model_id)
        except Exception as exc:  # noqa: BLE001
            raise RuntimeError(f"feature_extraction_failed: {exc!s}") from exc

        arr = np.asarray(vec, dtype=np.float32)
        # feature_extraction can return (dim,) or (tokens, dim) — mean-pool the latter.
        if arr.ndim == 2:
            arr = arr.mean(axis=0)
        elif arr.ndim == 3:
            arr = arr.reshape(-1, arr.shape[-1]).mean(axis=0)
        elif arr.ndim != 1:
            raise RuntimeError(f"unexpected_embedding_shape:{arr.shape}")

        out_rows.append(arr.astype(np.float32).tolist())

    return np.asarray(out_rows, dtype=np.float32)


def _load_ticker_npz(sym: str) -> tuple[dict[str, np.ndarray], dict[str, str]]:
    """Return vector_by_id (L2-normalized) and sha_by_id."""
    path = _ticker_npz_path(sym)
    if not path.exists():
        return {}, {}
    z = np.load(path, allow_pickle=True)
    ids = z["chunk_ids"].tolist()
    vecs = np.asarray(z["vectors"], dtype=np.float32)
    shas = z["shas"].tolist() if "shas" in z.files else [""] * len(ids)
    vec_map: dict[str, np.ndarray] = {}
    sha_map: dict[str, str] = {}
    for i, cid in enumerate(ids):
        cid_s = str(cid)
        vec_map[cid_s] = vecs[i].astype(np.float32, copy=False)
        sha_map[cid_s] = str(shas[i]) if i < len(shas) else ""
    vec_map = {k: v / max(1e-9, float(np.linalg.norm(v))) for k, v in vec_map.items()}
    return vec_map, sha_map


def _save_ticker_npz(
    sym: str,
    chunk_ids: list[str],
    vectors: np.ndarray,
    shas: list[str],
) -> None:
    path = _ticker_npz_path(sym)
    vectors = _l2_normalize_rows(np.asarray(vectors, dtype=np.float32))
    np.savez_compressed(
        path,
        chunk_ids=np.asarray(chunk_ids, dtype=object),
        vectors=vectors,
        shas=np.asarray(shas, dtype=object),
    )


def sync_embeddings_for_ticker(sym: str, chunk_rows: list[dict[str, Any]]) -> dict[str, Any]:
    """
    Ensure every chunk row for `sym` has an up-to-date embedding in the per-ticker npz.
    `chunk_rows` should already be filtered to this ticker and non-empty text.
    """
    sym_u = sym.strip().upper()
    vec_map, sha_map = _load_ticker_npz(sym_u)

    to_embed_ids: list[str] = []
    to_embed_texts: list[str] = []
    sha_by_id: dict[str, str] = {}

    for row in chunk_rows:
        cid = str(row.get("chunk_id") or "")
        text = str(row.get("text") or "").strip()
        if not cid or not text:
            continue
        sha = str(row.get("text_sha256") or "")
        sha_by_id[cid] = sha
        prev_sha = sha_map.get(cid, "")
        if cid not in vec_map or (sha and sha != prev_sha):
            to_embed_ids.append(cid)
            to_embed_texts.append(text[:8000])

    if not to_embed_ids:
        return {"synced": 0, "reason": "index_current"}

    try:
        new_vecs = _hf_embed_batch(to_embed_texts)
    except Exception as e:
        return {"synced": 0, "reason": "embed_failed", "detail": str(e)[:200]}

    if int(new_vecs.shape[0]) != len(to_embed_ids):
        return {"synced": 0, "reason": "embed_len_mismatch", "expected": len(to_embed_ids), "got": int(new_vecs.shape[0])}

    for cid, vec in zip(to_embed_ids, new_vecs):
        vec_map[cid] = vec.astype(np.float32, copy=False)

    def _backfill_missing(max_rounds: int = 4) -> int:
        filled = 0
        for _ in range(max_rounds):
            need = [
                r
                for r in chunk_rows
                if str(r.get("chunk_id") or "")
                and str(r.get("text") or "").strip()
                and str(r.get("chunk_id") or "") not in vec_map
            ]
            if not need:
                break
            batch = need[: max(1, int(settings.rag_embedding_batch_size))]
            ids_b = [str(r.get("chunk_id") or "") for r in batch]
            texts_b = [str(r.get("text") or "")[:8000] for r in batch]
            try:
                vecs_b = _hf_embed_batch(texts_b)
            except Exception:
                break
            if int(vecs_b.shape[0]) != len(ids_b):
                break
            for cid, vec in zip(ids_b, vecs_b):
                vec_map[cid] = vec.astype(np.float32, copy=False)
                filled += 1
        return filled

    extra = _backfill_missing()

    # Persist full set for this ticker present in chunk_rows
    ordered_ids: list[str] = []
    ordered_vecs: list[np.ndarray] = []
    ordered_shas: list[str] = []
    seen: set[str] = set()
    for row in chunk_rows:
        cid = str(row.get("chunk_id") or "")
        if not cid or cid in seen:
            continue
        seen.add(cid)
        vec = vec_map.get(cid)
        if vec is None:
            continue
        ordered_ids.append(cid)
        ordered_vecs.append(vec)
        ordered_shas.append(sha_by_id.get(cid, ""))

    if not ordered_ids:
        return {"synced": 0, "reason": "no_vectors"}

    mat = np.stack(ordered_vecs, axis=0)
    _save_ticker_npz(sym_u, ordered_ids, mat, ordered_shas)
    return {"synced": len(to_embed_ids) + int(extra), "persisted": len(ordered_ids)}


def embed_query_text(query: str) -> np.ndarray | None:
    try:
        q = _hf_embed_batch([query[:8000]])
        v = q[0].astype(np.float32, copy=False)
        n = float(np.linalg.norm(v))
        if n <= 0:
            return None
        return v / n
    except Exception:
        return None


def load_ticker_vectors(sym: str) -> dict[str, np.ndarray]:
    vec_map, _ = _load_ticker_npz(sym.strip().upper())
    return vec_map


def clear_ticker_embedding_index(sym: str) -> None:
    path = _ticker_npz_path(sym)
    if path.exists():
        path.unlink()


def clear_all_embedding_indexes() -> None:
    if not TICKER_INDEX_DIR.exists():
        return
    for p in TICKER_INDEX_DIR.glob("*.npz"):
        try:
            p.unlink()
        except OSError:
            pass
