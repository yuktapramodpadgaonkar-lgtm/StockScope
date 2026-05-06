# API keys — where they go and what uses them

## Where to put keys

1. **Copy the example env file** (repo root):

   **Windows (PowerShell)**

   ```powershell
   copy backend\.env.example backend\.env
   ```

   **macOS / Linux**

   ```bash
   cp backend/.env.example backend/.env
   ```

2. **Edit `backend/.env`** and fill in values. **Do not commit `backend/.env`** — it is gitignored.

3. The **FastAPI app** loads `backend/.env` automatically via Pydantic Settings (`backend/app/core/config.py`). Start the API from the repo root as usual:

   ```powershell
   uvicorn app.main:app --reload --app-dir backend
   ```

Keys are read as environment variables (e.g. `ALPHA_VANTAGE_API_KEY`, `FINNHUB_API_KEY`). Names match the placeholders in `backend/.env.example`.

---

## What each key is for

| Variable | Used by | Required? |
|----------|---------|-----------|
| `CORS_ORIGINS` | FastAPI — browser origins allowed to call the API | Yes for local Next.js (`http://localhost:3000`, etc.) |
| `ALPHA_VANTAGE_API_KEY` | Buy/Sell Layer 1 — `NEWS_SENTIMENT` (news + sentiment), **1 call per ticker** when set | Optional |
| `FINNHUB_API_KEY` | Buy/Sell Layer 1 — analyst recommendation **trends** (`/stock/recommendation`), **1 call per ticker** when set | Optional |
| `FMP_API_KEY` | Reserved for future use (e.g. DCF / statements). **Not called** by Layer 1 yet | Optional |
| `BUYSELL_LLM_PROVIDER` | Buy/Sell Phase 4 provider switch (`none` or `huggingface`) | Optional |
| `BUYSELL_LLM_ENABLED` | Enables advisory `llm_review` generation in `/api/buy-sell/analyze/{ticker}` | Optional |
| `HUGGINGFACE_API_TOKEN` | Hugging Face auth token for generic API or endpoint mode; **also used for Phase 5.1 RAG embeddings** when set | Optional (required when HF LLM or embedding retrieval is enabled) |
| `HF_MODEL_ID` | Hugging Face model id for generic inference API mode | Optional (required if `HF_INFERENCE_URL` is empty) |
| `HF_INFERENCE_URL` | Dedicated HF endpoint URL (if set, used instead of generic model-id route) | Optional |
| `RAG_EMBEDDING_MODEL` | HF model id for **sentence embeddings** (feature extraction) used in hybrid retrieval | Optional (defaults in `backend/app/core/config.py`) |
| `SEC_USER_AGENT` | **Required by SEC** for EDGAR HTTP access — descriptive string with contact (e.g. `MyApp/1.0 (you@school.edu)`) | Optional for filings; if unset, Layer 1 filings block stays empty |
| `SEC_EDGAR_ENABLED` | When `true` and `SEC_USER_AGENT` is set, fetches recent 10-K / 10-Q / 8-K text into RAG | Optional |
| `POLYGON_API_KEY` | **Not used by the FastAPI server.** Used only by **Python scripts** under `scripts/` (see below) | Optional unless you run those scripts with Polygon enrichment |
| `MOVERS_CACHE_*` | Market movers snapshot cache TTLs | Optional (defaults exist) |
| `MEMORY_ENABLED` | Phase 7 — persist session memory under `data/memory/sessions.json` | Optional (`true` by default in code) |
| `MEMORY_MAX_RECENT_TICKERS` | Cap per session recent-ticker list | Optional |
| `EVAL_OUTPUT_DIR` | Phase 8 — optional override for eval JSON output directory | Optional (default `data/eval/`) |

---

## Polygon.io — have we “used” it in the app?

**In the running backend (FastAPI):** **No.** Buy/Sell Layer 1 and Market Movers do **not** call Polygon.

**In this repo, Polygon is used only for:**

- **`scripts/fetch_universes_polygon.py`** — optional enrichment: `GET /v3/reference/tickers/{ticker}` to **validate tickers** and fill **company names** when building `data/universes/*.csv`.
- **`scripts/polygon_client.py`** — small HTTP helper for that endpoint.

Polygon does **not** provide “give me all S&P 500 constituents” as a single REST call, so index lists still come from Wikipedia / bundled CSVs; Polygon only **checks** symbols you already have.

**Why it appears in docs:** `docs/BuySellAnalysis-data-sources.md` lists Polygon as a **possible** future source for **aggregates / trades** (alongside yfinance). That is **design guidance**, not current code. **`POLYGON_API_KEY` in `backend/.env.example`** is there so one file documents all keys; the **scripts** read `POLYGON_API_KEY` from the **process environment** — when you run a script from a terminal, either:

- Export the variable in that shell, or  
- Load the same values manually from `backend/.env`.

Example **without** putting the key in code:

**PowerShell (repo root)**

```powershell
$env:POLYGON_API_KEY = "your_key_here"
python scripts/fetch_universes_polygon.py
```

**Wiki-only (no Polygon calls)**

```powershell
python scripts/fetch_universes_polygon.py --wiki-only
```

---

## Frontend

The Next.js app uses **`frontend/.env.local`** (copy from `frontend/.env.local.example`). Typical entry:

- `NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000`

Only variables prefixed with `NEXT_PUBLIC_` are exposed to the browser.

---

## Quick checklist

- [ ] `backend/.env` exists (copied from `.env.example`) and is **not** committed  
- [ ] `CORS_ORIGINS` includes your frontend origin  
- [ ] Optional: `ALPHA_VANTAGE_API_KEY`, `FINNHUB_API_KEY` for Buy/Sell Layer 1  
- [ ] Optional: `POLYGON_API_KEY` in the **environment** when running universe scripts with Polygon enrichment  
- [ ] `frontend/.env.local` has `NEXT_PUBLIC_API_BASE_URL` if the UI calls the API  

For call-count details on Buy/Sell endpoints, see [`Layer1-api-call-ledger.md`](Layer1-api-call-ledger.md).

To **verify keys and live provider calls** for a ticker, see [`API-keys-testing.md`](API-keys-testing.md).
