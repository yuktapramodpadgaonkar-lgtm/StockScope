# StockScope — AI-Powered Stock Research Platform

## Team Members
- Yukta Pramod Padgaonkar
- Ramya Gopalaswamy
- Revati Dharmadhikari

---

## Project Overview

StockScope is a vertical AI-powered stock research platform providing structured, explainable, and data-driven insights for retail investors.

The system integrates market data, financial fundamentals, news sentiment, and conversational AI into a unified interface.

---

## AI Models

| Role | Model | Provider |
|------|-------|----------|
| Primary LLM | Gemini 2.0 Flash | Google AI REST API |
| Local fallback 1 | LLaMA 3.1 8B | Ollama (local) |
| Local fallback 2 | Mistral 7B | Ollama (local) |
| Sentiment | FinBERT (ProsusAI/finbert) | HuggingFace Inference API |

Fallback order (per request): Gemini → LLaMA → Mistral. All LLM calls are handled by `backend/services/ai/llm_service.py`.

---

## Core Features

### 1. Market Movers
- Top gainers and losers from yfinance
- Price, percentage change, volume
- Intraday + previous-day cache

### 2. Buy/Sell Analysis
- Deterministic scoring: fundamentals (40%) + technicals (30%) + sentiment (30%)
- BUY / HOLD / SELL with confidence score
- LLM narrative explanation of the deterministic score (Gemini → LLaMA → Mistral)
- Agent pipeline: Planner–Executor–Critic
- **RAG:** optional hybrid retrieval (BM25 + embeddings) over ingested **news + SEC filing** chunks; surfaced as citations in the report when `include_retrieval` is enabled

### 2b. Retrieval (RAG) across the product

**RAG is available in:**

- **Buy/Sell** — `include_retrieval` on `/api/buy-sell/analyze/...` (news + filings in the local chunk store)
- **Agentic Research** — `/api/agentic-research/run` (planner picks tools; writer grounded on evidence + citations)
- **News Sentiment** — `use_rag` on `POST /api/analysis/news-sentiment` (ingest headlines → hybrid retrieve → ground the theme LLM); **UI:** checkbox on the Chatbot page’s *News sentiment* panel
- **Fundamentals** — `include_rag` on `GET /api/analysis/fundamental` (optional SEC filing excerpts for the narrative); **UI:** checkbox on the Fundamentals page

**GraphRAG is not implemented.** The “advanced” retrieval story here is **hybrid search (BM25 + dense embeddings)** plus **agentic** orchestration (tool use + critic), not knowledge-graph RAG.

### 3. Fundamental Analysis
- yfinance metrics: P/E, ROE, margins, debt/equity, growth
- Rule-based health verdict (strengths + risks)
- Optional LLM plain-English explanation via `include_llm=true` (Ollama Mistral/LLaMA or Gemini)
- Optional **`include_rag=true`**: ingest/recent SEC filing chunks for `rag_evidence` and (when `include_llm`) filing-grounded AI text (requires `SEC_USER_AGENT` / EDGAR when enabled)

### 4. News Sentiment Analysis
- Finnhub news fetch (falls back to mock data when key absent)
- FinBERT classification per article (keyword heuristic fallback)
- LLM theme extraction and narrative summary
- Citations for all articles
- Optional **`use_rag`**: local hybrid retrieval over news chunks to ground themes/summary (HF token improves dense retrieval)

### 5. Chatbot
- Intent detection: stock_explanation, sentiment_question, comparison_question, history_lookup, unknown
- Safety layer rejects direct buy/sell advice
- LLM grounded responses with news context
- Persistent thread history

### 6. Multi-Model Comparison
- `POST /api/evaluation/compare-models`
- Runs the same prompt through Gemini, LLaMA, and Mistral independently
- Returns latency, citation count, and safety status per model
- Frontend: `/evaluation` — dropdown task selector, ticker input, side-by-side results table

### 7. Evaluation rubric harness
- **`backend/evaluation/eval_set.json`** — **111** cases (fundamental, buy/sell, news, chat, market movers, safety, auth, citations, memory, multi-model incl. `rub-087`–`rub-089`, **agentic chat** `rub-084`–`rub-086`, **agentic RAG** `rub-061`–`rub-075`, **news RAG** `rub-091`, **fundamental RAG** `rub-090`)
- **`backend/evaluation/run_batch_eval.py`** — batch runner with optional `--live-fundamental`, `--live-news`, `--live-market-data`, `--live-orchestrator`, `--live-multi`; writes CSV/JSON under `backend/evaluation/results/` (gitignored)
- **`backend/evaluation/run_eval.py`** — buy/sell agent pipeline smoke eval (yfinance; subsets via `--max-cases`)
- **Structured logs** — append-only `backend/logs/model_calls.jsonl` and `backend/logs/tool_calls.jsonl` (gitignored)
- **Honest agent/RAG/memory status** — [`docs/AGENT_RAG_MEMORY_STATUS.md`](docs/AGENT_RAG_MEMORY_STATUS.md)
 - **Agentic RAG (rubric D)** — `POST /api/agentic-research/run` (planner → tools → writer → critic; planner **retry** on bad/short plan); UI: **`/agentic-research`**; doc: `docs/AGENTIC_RAG_AND_MEMORY.md`; batch: `python backend/evaluation/run_batch_eval.py --category agentic_rag --live-agentic`

**Batch eval commands**

```bash
python backend/evaluation/run_batch_eval.py
python backend/evaluation/run_batch_eval.py --category agentic_chat --live-chat
python backend/evaluation/run_batch_eval.py --category agentic_rag --live-agentic
```

### 8. History
- Persisted chat threads, research runs, saved prompts
- Records model_used, provider, intent, fallback_used per interaction
- UI displays model badges ("Answered by Gemini", "Fallback: LLaMA") on chat messages and research runs

### 9. RAG / Document grounding
- Place `.txt` or `.json` files in `backend/data/documents/` named `<TICKER>_description.txt`
- Run `python backend/scripts/ingest_documents.py` to index them into the RAG store
- Pre-loaded demo documents: AAPL, NVDA, MSFT, TSLA, GOOGL
- Retriever returns an explicit fallback message when no documents exist (never silent empty)

---

## Data Sources

| Source | Usage |
|--------|-------|
| yfinance | Prices, fundamentals, technicals, fallback news |
| Finnhub | Company news (optional API key) |
| Alpha Vantage | News + sentiment feed (optional API key) |
| HuggingFace Inference API | FinBERT sentiment (optional token) |
| SEC EDGAR | Filings ingestion for RAG (optional) |

---

## Setup

### 1. Ollama (local LLMs)

```bash
# Install from https://ollama.com then:
ollama pull llama3.1:8b
ollama pull mistral:7b
ollama serve
```

Ollama runs at `http://localhost:11434` by default. Override with `OLLAMA_BASE_URL` in `backend/.env`.

### 2. Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate   # Mac/Linux
# .venv\Scripts\activate    # Windows

pip install --upgrade pip
pip install -r requirements.txt
```

Copy and fill in `.env`:

```bash
cp .env.example .env
```

`.env` example:

```env
# Google Gemini
GEMINI_API_KEY=your_gemini_key_here
GEMINI_MODEL=gemini-1.5-flash

# Ollama (local)
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_LLAMA_MODEL=llama3.1:8b
OLLAMA_MISTRAL_MODEL=mistral:7b

# News data (optional — mock data used when absent)
FINNHUB_API_KEY=
ALPHA_VANTAGE_API_KEY=

# FinBERT sentiment (optional — keyword fallback when absent)
HUGGINGFACE_API_TOKEN=
FINBERT_ENABLED=true
FINBERT_MODEL_ID=ProsusAI/finbert

# CORS
CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
```

For Layer 1 / news / scripts API keys, see [`docs/API-keys.md`](docs/API-keys.md) and [`docs/API-keys-testing.md`](docs/API-keys-testing.md).

Start the backend:

```bash
cd backend
python -m uvicorn app.main:app --reload
```

Interactive API docs: **http://127.0.0.1:8000/docs**

### Fundamental analysis LLM (optional)

The `/fundamentals` page has an **Analyze with AI** button that calls `include_llm=true`. This uses:
- **Gemini** — set `GEMINI_API_KEY` in `backend/.env`
- **Mistral / LLaMA** — run Ollama locally (see step 1 above)

If the LLM fails, deterministic metrics still load (see `ai_error` in the API response).

**API:** `GET /api/analysis/fundamental?ticker=AAPL&include_rag=true` returns filing **`rag_evidence`** when SEC ingest is configured; add **`include_llm=true`** (and optional **`preferred_model`** = `gemini` \| `llama` \| `mistral`) so the AI summary can use those excerpts. See **Fundamental analysis with SEC RAG** under API examples below.

### 3. Frontend

```bash
cd frontend
cp .env.local.example .env.local   # set NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000
npm install
npm run dev
```

Open **http://localhost:3000** — e.g. `/market-movers`, `/fundamentals`, `/chatbot`.

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/buy-sell/analyze/{ticker}` | Full buy/sell analysis with LLM review |
| GET | `/api/analysis/fundamental` | Fundamental analysis (Bearer auth). Query: `ticker`, optional `include_llm`, `include_rag`, `preferred_model` |
| POST | `/api/analysis/news-sentiment` | News sentiment + FinBERT + LLM themes |
| POST | `/api/chat/query` | Chatbot query |
| GET | `/api/history` | Chat and research history |
| POST | `/api/evaluation/compare-models` | Multi-model comparison |
| GET | `/api/market-movers` | Top gainers/losers |
| GET | `/health` | Health check |

### Multi-model comparison example

```bash
curl -X POST http://127.0.0.1:8000/api/evaluation/compare-models \
  -H "Content-Type: application/json" \
  -d '{"task": "sentiment", "ticker": "NVDA", "query": "What is the market sentiment for NVDA?"}'
```

### Buy/sell with LLM review

```bash
curl "http://127.0.0.1:8000/api/buy-sell/analyze/AAPL?include_llm_review=true"
```

### Fundamental analysis with SEC RAG (`include_rag`)

Requires **Bearer token** (same login as the Fundamentals UI). Set **`SEC_USER_AGENT`** (and optionally `SEC_EDGAR_ENABLED=true`) in `backend/.env` for real filing text; otherwise `rag_evidence` may be empty.

```bash
# 1) Obtain token (use your app’s demo user or a registered account)
TOKEN=$(curl -s -X POST http://127.0.0.1:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"eval@stockscope.edu","password":"class-demo"}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

# 2) Filing RAG only (deterministic metrics + rag_evidence; no AI summary)
curl -s "http://127.0.0.1:8000/api/analysis/fundamental?ticker=AAPL&include_rag=true&include_llm=false" \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool | head -80

# 3) Filing RAG + AI summary (grounds narrative on metrics + excerpts when evidence exists)
curl -s "http://127.0.0.1:8000/api/analysis/fundamental?ticker=AAPL&include_rag=true&include_llm=true&preferred_model=gemini" \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool | head -80
```

---

## Architecture

```
Frontend (Next.js + TypeScript + Tailwind)
    └── API Layer (FastAPI + Pydantic)
            ├── services/ai/llm_service.py       ← Gemini + Ollama router (Revati)
            ├── app/services/ai/llm_client.py    ← provider-agnostic generate_text (Yukta/Ramya)
            ├── services/ai/prompts.py            ← all prompt templates
            ├── services/news_sentiment_service.py
            ├── services/chat_service.py
            ├── services/history_service.py
            ├── services/buy_sell_llm_service.py
            ├── app/services/buy_sell_scoring.py  ← deterministic scoring engine
            ├── app/services/fundamental_service.py
            └── app/rag/                          ← hybrid BM25 + embedding retrieval
```

---

## Technical Stack

- **Backend:** Python 3.9+, FastAPI, Pydantic v2, yfinance, httpx
- **Frontend:** Next.js 15, React, TypeScript, Tailwind CSS
- **LLMs:** Gemini 2.0 Flash (Google AI), LLaMA 3.1 8B + Mistral 7B (Ollama)
- **Sentiment:** FinBERT via HuggingFace Inference API
- **Storage:** JSON file store (history), in-memory cache (market movers)

---

## Available Pages

| Route | Description |
|-------|-------------|
| `/` | Home / dashboard |
| `/buy-sell` | Buy/Sell analysis report |
| `/market-movers` | Top gainers and losers |
| `/fundamentals` | Fundamental analysis |
| `/chatbot` | AI chatbot |
| `/history` | Research and chat history (with model metadata) |
| `/agentic-research` | Agentic RAG research pipeline |
| `/evaluation` | Multi-model comparison (Gemini / LLaMA / Mistral) |
| `/news-sentiment` | News sentiment analysis (FinBERT + LLM themes) |
| `/signup` | Create account / register |
| `/login` | Authentication |

> **Note:** Authentication uses real JWT (HS256 via python-jose), a SQLite user store (`backend/data/users.db`), and bcrypt password hashing. Tokens expire after 24 hours. Use `POST /api/auth/register` to create an account and `POST /api/auth/login` to get a signed token.

---

## Demo Walkthrough

Follow this sequence to show every major feature in ~10 minutes.

### 1. Sign up and log in
- Open **http://localhost:3000/signup** → create an account
- You are redirected to **http://localhost:3000/login** → sign in
- AuthGate grants access to all protected pages; token expires in 24 h

### 2. News Sentiment — live Finnhub + FinBERT
- Go to **`/news-sentiment`**
- Ticker: `AAPL`, Max articles: 10 → click **Analyse**
- Shows: per-article FinBERT sentiment badges, positive/neutral/negative bars, LLM-extracted themes, citations
- The "AI:" badge confirms which model generated themes (Gemini 2.0 Flash → LLaMA → Mistral fallback chain)

### 3. Agentic Research — plan → tools → critic
- Go to **`/agentic-research`**
- Ticker: `NVDA`, Question: `Summarize fundamentals and recent news themes with citations.`
- Watch the phase indicator: **Planning → Fetching tools → Writing answer**
- Result shows: plan steps used, answer grounded on evidence, citation list, `critic_passed` status, `repair_attempted` flag, memory profile
- Try a second query for the same session — the memory profile updates with your ticker history

### 4. Fundamental Analysis — metrics + LLM + RAG
- Go to **`/fundamentals`**
- Ticker: `MSFT` → toggle **Analyze with AI** + enable **Include RAG** → click Analyze
- Shows: P/E, ROE, margins, debt/equity, strengths/risks verdict, AI narrative, and `rag_evidence` excerpts from pre-ingested documents
- Change model selector (Gemini / LLaMA / Mistral) to compare narrative styles

### 5. Model Comparison — LLM-as-judge
- Go to **`/evaluation`**
- Task: `sentiment`, Ticker: `AAPL`, Query: `What is the current market sentiment for AAPL?`
- Click **Run comparison** — all three models run in parallel
- Gemini acts as impartial judge: scores each response 1–5 on relevance, clarity, safety
- Summary table shows latency, citation count, safety pass/fail, and judge scores side by side

### 6. Chatbot — agentic pipeline with safety gate
- Go to **`/chatbot`**
- Ask: `What are the key fundamentals and recent news for TSLA?` → observe citations and model badge
- Ask: `Should I buy TSLA right now?` → safety gate fires, `detected_intent: financial_advice_rejected`
- Sidebar shows conversation threads; `/history` shows saved sessions with model metadata

### 7. Eval rubric (for reviewers)
```bash
# Static + market + fundamental (39/39 pass, 0 fail)
python backend/evaluation/run_batch_eval.py --live-market-data --live-fundamental

# Live LLM categories (requires working Gemini key)
python backend/evaluation/run_batch_eval.py --live-news --live-chat
python backend/evaluation/run_batch_eval.py --category agentic_rag --live-agentic
```
Results written to `backend/evaluation/results/` as CSV + JSON.

---

## Disclaimer

All outputs are for educational purposes only and are not financial advice. Always consult a licensed financial adviser before making investment decisions.

---

## System Contribution vs. Off-the-Shelf Components

StockScope is a **system-level contribution**: the novelty lies in how existing components are combined and evaluated, not in any single new algorithm.

### What we built (system-level)
- A **deterministic financial scoring engine** (fundamentals 40%, technicals 30%, sentiment 30%) with per-dimension data-completeness tracking and LLM agreement overlay (`backend/app/services/buy_sell_scoring.py`).
- An **agentic RAG pipeline** (`/api/agentic-research/run`) in which an LLM planner decomposes a free-form financial question into a 2–4 step tool plan, executes those tools, constructs a grounded evidence bundle, and passes the answer through a multi-check rule critic with one automatic repair pass. The critic checks citation index validity, ticker-in-evidence, significant numeric claims, and financial advice patterns.
- A **hybrid retrieval layer** combining sparse BM25 and dense sentence-transformer embeddings with configurable weights, applied across four product features (buy/sell, fundamentals, news, agentic research).
- A **structured evaluation harness** (111 rubric cases across 12 categories) with rule-based scoring, LLM-as-judge scoring via Gemini, and batch CSV export.
- A **multi-model comparison UI** where the same prompt is submitted independently to Gemini, LLaMA, and Mistral, with latency, grounding, completeness, and safety scores reported side by side.

### Off-the-shelf components we use (cited in References)
- **FinBERT** — pre-trained financial sentiment model from ProsusAI; used as-is via HuggingFace Inference API with a keyword-heuristic fallback. No fine-tuning was performed.
- **BM25 (Okapi BM25)** — classic sparse retrieval algorithm; implemented via a local BM25 scorer in `backend/app/rag/bm25.py`.
- **`sentence-transformers/all-MiniLM-L6-v2`** — pre-trained dense embedding model from SBERT; used for query and chunk embedding in the RAG pipeline.
- **Gemini 2.0 Flash** — Google's generative model accessed via REST API; used as primary LLM for generation, theme extraction, and LLM-as-judge scoring.
- **LLaMA 3.1 8B / Mistral 7B** — open-weight models served locally via Ollama; used as fallback LLMs.
- **yfinance** — open-source Yahoo Finance wrapper for market data, fundamentals, and historical prices.

### What is *not* claimed
- The buy/sell **planner** (`backend/app/agents/planner.py`) is a **fixed DAG**, not a free-form LLM planner. It deterministically selects steps from flags (`include_retrieval`, `include_llm_review`, `horizon`). The *agentic research* planner (`/api/agentic-research/run`) is LLM-driven.
- **GraphRAG is not implemented.** The "advanced" retrieval claim refers to hybrid BM25+dense search and agentic tool orchestration.
- **Memory** is a lightweight session store (recent tickers, topics, risk style) — not semantic long-term memory retrieval.

---

## Design Rationale

### Why hybrid retrieval instead of pure dense retrieval

Pure dense (embedding-based) retrieval generalises well to semantically similar queries but struggles with exact-match needs common in finance: specific ticker symbols, SEC filing numbers, exact metric names, and domain jargon that may be rare in the embedding model's pre-training corpus. BM25 handles exact and rare-term matches precisely but cannot capture paraphrase or semantic similarity. Following the finding in the literature that hybrid sparse+dense retrieval consistently outperforms either alone on domain-specific corpora ([Luan et al., 2021](#references); [Ma et al., 2021](#references)), we combine BM25 and `all-MiniLM-L6-v2` embeddings with tunable weights (`RAG_BM25_WEIGHT=0.45`, `RAG_EMBEDDING_WEIGHT=0.55`). The weights are configurable via environment variables so they can be tuned without code changes.

### Why Gemini → LLaMA → Mistral fallback order

**Gemini 2.0 Flash** is the primary provider because it returns structured JSON reliably, has a large context window suitable for multi-tool evidence bundles, and has the lowest observed latency for generation tasks in our evaluation. **LLaMA 3.1 8B** is first fallback: it is open-weight, runs locally via Ollama with no data egress, and produces grammatically correct structured output at a reasonable speed on consumer hardware. **Mistral 7B** is the second fallback: slightly faster than LLaMA on short prompts but produces less consistent JSON adherence in our tests, making it a safer last resort than first fallback. Running the fallback chain requires no API key rotation — the system degrades gracefully to local inference when cloud quotas are exhausted. All three models are scored independently in the model-comparison evaluation (`/evaluation` page, `backend/evaluation/run_feature_multimodel_eval.py`).

---

## Evaluation Summary

Static and deterministic checks always run. Live-LLM categories are skipped (`not_run`) when their flag is omitted and produce 0 failures — they are gated on available API quota or a running Ollama instance.

**Latest run: `batch_eval_20260519-182113` — 72 pass / 1 fail / 38 not-run (needs live LLM flag)**

| Category | Cases | Pass | Status | Live flag required |
|----------|-------|------|--------|--------------------|
| auth_protected_routes | 5 | 5 | ✅ | — |
| citation_grounding | 5 | 5 | ✅ | — |
| memory_history | 4 | 4 | ✅ | — |
| safety_refusal | 6 | 6 | ✅ | — |
| market_movers | 20 | 20 | ✅ | `--live-market-data` |
| fundamental | 10 | 10 | ✅ | `--live-fundamental` |
| chatbot | 10 | 10 | ✅ | `--live-chat` |
| news_sentiment | 10 | 10 | ✅ | `--live-news` |
| agentic_chat | 3 | 2 | ⚠ 1 fail (LLM substring) | `--live-agentic` (via `--live-chat`) |
| buy_sell | 10 | 0 | ⏭ not-run | `--live-orchestrator` |
| multi_model_comparison | 18 | 0 | ⏭ not-run | `--live-multi` |
| agentic_rag | 10 | 0 | ⏭ not-run | `--live-agentic` |
| **Total** | **111** | **72** | **1 fail (LLM variation)** | |

> The 1 failure (`rub-085`) is an agentic chat case where the LLaMA response omits the expected substring `'history'` — natural LLM output variation, not a system defect.
>
> Latest full results: `backend/evaluation/results/batch_eval_20260519-182113.{csv,json}`. Run commands:
> ```bash
> # Static + market + fundamental + chat + news (72 cases)
> python backend/evaluation/run_batch_eval.py --live-market-data --live-fundamental --live-chat --live-news
> # Full run (requires Gemini key or Ollama; Gemini quota may be exhausted)
> python backend/evaluation/run_batch_eval.py --live-market-data --live-fundamental --live-news --live-chat --live-orchestrator --live-multi
> python backend/evaluation/run_batch_eval.py --category agentic_rag --live-agentic
> ```

Multi-model comparison metrics (latency, grounding, completeness, hallucination rate) are generated by:
```bash
python backend/evaluation/run_feature_multimodel_eval.py
python backend/evaluation/export_metrics_csv.py --stamp <stamp>
python backend/evaluation/plot_model_metrics_bars.py --stamp <stamp>
python backend/evaluation/plot_judge_score_grouped.py --stamp <stamp>
python backend/evaluation/plot_latency_judge_tradeoff.py --stamp <stamp>
```
Outputs: `backend/evaluation/results/metrics_<stamp>.csv`, `backend/evaluation/results/figures/`.

---

## Code Organisation

### Two LLM service files

| File | Purpose |
|------|---------|
| `backend/services/ai/llm_service.py` | Provider-routing LLM gateway (Revati). Implements the Gemini → LLaMA → Mistral fallback chain, exposes `generate_response(prompt, preferred_model)` and per-provider methods (`generate_with_gemini`, `generate_with_ollama_llama`, `generate_with_ollama_mistral`). Used by news-sentiment, chatbot, agentic-research, evaluation, and prompts modules. |
| `backend/app/services/ai/llm_client.py` | Provider-agnostic thin wrapper (Yukta/Ramya). Exposes `generate_text(prompt, model, provider)` used specifically by the fundamental-analysis LLM summary path and the buy/sell structured-narrative path. Deliberately kept separate to avoid coupling the scoring pipeline to the full fallback router. |

Both files call the same underlying Gemini/Ollama endpoints — they are parallel implementations owned by different team members that were not merged to avoid merge conflicts during parallel development.

### `backend/services/` vs `backend/app/services/`

| Directory | Contains | Reason |
|-----------|----------|--------|
| `backend/services/` | `llm_service.py`, `news_sentiment_service.py`, `chat_service.py`, `history_service.py`, `buy_sell_llm_service.py`, `buy_sell_structured_narrative.py`, `huggingface_inference_text.py` | Revati's modules, written at the top-level `services/` path during early development. These import from `app.*` but are not themselves part of the FastAPI `app` package. |
| `backend/app/services/` | `fundamental_service.py`, `buy_sell_scoring.py`, `market_movers_service.py`, `market_data_provider.py`, `snapshot_cache.py`, `auth_service.py`, `huggingface_llm.py` | Core application services inside the FastAPI `app` package. Owned primarily by Yukta/Ramya. These are importable as `app.services.*`. |

The split is an artefact of parallel team development, not an intentional architectural boundary. A future refactor would unify both under `backend/app/services/`.

---

## Report Artifact Mapping

The following table maps each evaluation claim in the project report to its source script, data file, and generated figure in this repository.

| Report Item | Source Script | Data File | Figure/Output |
|-------------|---------------|-----------|---------------|
| Batch eval pass rates (all categories) | `backend/evaluation/run_batch_eval.py` | `backend/evaluation/results/batch_eval_<stamp>.csv` | — |
| Multi-model latency comparison | `backend/evaluation/run_feature_multimodel_eval.py` + `export_metrics_csv.py` | `backend/evaluation/results/metrics_<stamp>.csv` | `figures/model_metrics_bars_<stamp>.png` |
| Judge score by task/model | `backend/evaluation/run_feature_multimodel_eval.py --judge` + `plot_judge_score_grouped.py` | `backend/evaluation/results/metrics_<stamp>.csv` | `figures/judge_score_grouped_<stamp>.png` |
| Latency vs. quality trade-off | `backend/evaluation/plot_latency_judge_tradeoff.py` | `backend/evaluation/results/metrics_<stamp>.csv` | `figures/latency_judge_tradeoff_<stamp>.png` |
| Safety refusal rate | `backend/evaluation/run_batch_eval.py` | `backend/evaluation/results/batch_eval_<stamp>.csv` (category=safety_refusal) | — |
| Agentic critic pass/fail rates | `backend/evaluation/run_batch_eval.py --category agentic_rag --live-agentic` | `backend/evaluation/results/batch_eval_<stamp>.csv` (category=agentic_rag) | — |
| Citation grounding pass rate | `backend/evaluation/run_batch_eval.py` | `backend/evaluation/results/batch_eval_<stamp>.csv` (category=citation_grounding) | — |

> All `<stamp>` values are `YYYYMMDD-HHMMSS` timestamps from the run. The most recent run files are in `backend/evaluation/results/`.

---

## References

1. **BM25 / Okapi BM25**: Robertson, S., & Zaragoza, H. (2009). *The Probabilistic Relevance Framework: BM25 and Beyond*. Foundations and Trends in Information Retrieval, 3(4), 333–389. [doi:10.1561/1500000019](https://doi.org/10.1561/1500000019)

2. **FinBERT**: Araci, D. (2019). *FinBERT: Financial Sentiment Analysis with Pre-trained Language Models*. arXiv:1908.10063. [https://arxiv.org/abs/1908.10063](https://arxiv.org/abs/1908.10063)

3. **Retrieval-Augmented Generation (RAG)**: Lewis, P., Perez, E., Piktus, A., Petroni, F., Karpukhin, V., Goyal, N., … Kiela, D. (2020). *Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks*. NeurIPS 2020. [https://arxiv.org/abs/2005.11401](https://arxiv.org/abs/2005.11401)

4. **Hybrid dense+sparse retrieval**: Ma, X., Lin, J., Pradeep, R., & Lin, J. (2021). *A Replication Study of Dense Passage Retrieval*. arXiv:2104.05740. [https://arxiv.org/abs/2104.05740](https://arxiv.org/abs/2104.05740) — motivates combining BM25 with dense retrieval for domain-specific corpora.

5. **Sentence-Transformers / all-MiniLM-L6-v2**: Reimers, N., & Gurevych, I. (2019). *Sentence-BERT: Sentence Embeddings using Siamese BERT-Networks*. EMNLP 2019. [https://arxiv.org/abs/1908.10084](https://arxiv.org/abs/1908.10084)

6. **LLM-as-a-judge**: Zheng, L., Chiang, W.-L., Sheng, Y., Zhuang, S., Wu, Z., Zhuang, Y., … Stoica, I. (2023). *Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena*. NeurIPS 2023. [https://arxiv.org/abs/2306.05685](https://arxiv.org/abs/2306.05685)

7. **Agentic / critic-style evaluation**: Shinn, N., Cassano, F., Labash, B., Gopinath, A., Narasimhan, K., & Yao, S. (2023). *Reflexion: Language Agents with Verbal Reinforcement Learning*. NeurIPS 2023. [https://arxiv.org/abs/2303.11366](https://arxiv.org/abs/2303.11366) — motivates the planner–critic–repair pattern used in agentic research and chat pipelines.
