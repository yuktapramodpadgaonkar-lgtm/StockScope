# Phase 5 RAG — File-by-file implementation checklist

This checklist maps directly to the current `StockScope` repository structure.

## Backend files

### `backend/app/rag/store.py`
- `data/rag/chunks.jsonl` — JSONL chunk store
- **Rotation:** when file size exceeds `RAG_ROTATE_BYTES`, archive to `chunks_archive_<unix>.jsonl`, wipe active file, clear `data/rag/index/by_ticker/*.npz`
- **Prune:** `RAG_MAX_TOTAL_CHUNKS` + `RAG_MAX_CHUNKS_PER_TICKER` (recency from `published_at`, else `ingested_at`)

### `backend/app/rag/bm25.py`
- Okapi **BM25+** over in-memory per-ticker corpus + `min_max_norm`

### `backend/app/rag/embedding_index.py`
- Per-ticker compressed index: `data/rag/index/by_ticker/<SYMBOL>.npz` (`chunk_ids`, `vectors`, `shas`)
- **HF Inference API** embeddings via `POST /models/{RAG_EMBEDDING_MODEL}` (same `HUGGINGFACE_API_TOKEN` as LLM path)
- `sync_embeddings_for_ticker()` — upserts vectors; invalidates on `text_sha256` change; backfill for rare batch mismatches

### `backend/app/rag/ingest_news.py`
- News chunks + `text_sha256`, `ingested_at`

### `backend/app/rag/ingest_filings.py`
- Filing chunks (4000-char slices) + `text_sha256`, `ingested_at`

### `backend/app/rag/hybrid_retriever.py`
- **Hybrid:** normalized BM25 + normalized cosine (when embeddings exist)
- Weights: `RAG_BM25_WEIGHT`, `RAG_EMBEDDING_WEIGHT`; falls back to BM25-only if no vectors / no query embedding
- **Freshness:** `max_age_days` (API override) or `RAG_MAX_CHUNK_AGE_DAYS` in settings (`-1` = no filter)
- Exposes `retrieval_bm25`, `retrieval_cosine` on each hit for debugging

### `backend/app/rag/citation_checker.py`
- Citation id sanity helper

### `backend/app/tools/sec_edgar_tool.py`
- Cached `company_tickers.json` → CIK → `data.sec.gov/submissions` → recent **10-K / 10-Q / 8-K** primary HTML/text
- **Requires** `SEC_USER_AGENT` (SEC fair-access policy)
- Throttled with `SEC_REQUEST_DELAY_SECONDS`

### `backend/app/tools/filings_tool.py`
- Wires SEC bundle when `SEC_EDGAR_ENABLED` + `SEC_USER_AGENT`

### `backend/app/tools/layer1_pipeline.py`
- `call_ledger.sec_edgar` counts filing-related HTTP calls

### `backend/app/api/buy_sell_analysis.py`
- `retrieval_max_age_days` query param (`-1` disables filter)
- After ingest: `sync_embeddings_for_ticker` → `retrieve_chunks`

### `backend/app/services/buy_sell_scoring.py` / `huggingface_llm.py`
- Citations + LLM prompt evidence from retrieval (unchanged contract)

## What you need to configure

1. **`SEC_USER_AGENT`** — SEC blocks anonymous scraping; use a real identifying string with contact info.
2. **`HUGGINGFACE_API_TOKEN`** — Required for **dense retrieval** (embeddings). Without it, retrieval still works using **BM25 only**.
3. (Optional) Tune **`RAG_*`** / **`SEC_*`** in `backend/.env` — see `backend/.env.example`.

## Phase 5.2 (optional next)

- Dedicated vector DB / ANN index at scale
- Press-release / IR RSS ingest
- Stronger filing parsers (section-aware chunking, XBRL-aware excerpts)
- Async embedding jobs so `/analyze` does not wait on large HF batches

## Quick test

```powershell
curl.exe -s "http://127.0.0.1:8000/api/buy-sell/analyze/AAPL?include_retrieval=true&retrieval_top_k=5&retrieval_max_age_days=365"
```

Confirm `citations` include `AAPL:news:…` and, when SEC + HF are configured, `AAPL:filing:…` chunks and non-null `retrieval_cosine` on ranked hits when inspecting raw retrieval (e.g. temporary logging or a debug endpoint later).
