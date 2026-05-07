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
| Primary LLM | Gemini 1.5 Flash | Google AI REST API |
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
- **`backend/evaluation/eval_set.json`** — **91** cases (fundamental, buy/sell, news, chat, market movers, safety, auth, citations, memory, multi-model incl. `rub-087`–`rub-089`, **agentic chat** `rub-084`–`rub-086`, **agentic RAG** `rub-061`–`rub-075`, **news RAG** `rub-091`, **fundamental RAG** `rub-090`)
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
- **LLMs:** Gemini 1.5 Flash (Google AI), LLaMA 3.1 8B + Mistral 7B (Ollama)
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
| `/login` | Authentication |

> **Note:** Authentication uses real JWT (HS256 via python-jose), a SQLite user store (`backend/data/users.db`), and bcrypt password hashing. Tokens expire after 24 hours. Use `POST /api/auth/register` to create an account and `POST /api/auth/login` to get a signed token.

---

## Disclaimer

All outputs are for educational purposes only and are not financial advice. Always consult a licensed financial adviser before making investment decisions.
