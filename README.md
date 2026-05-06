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
- RAG citations from news and SEC filings

### 3. Fundamental Analysis
- yfinance metrics: P/E, ROE, margins, debt/equity, growth
- Rule-based health verdict (strengths + risks)
- Optional LLM plain-English explanation via `include_llm=true` (Ollama Mistral/LLaMA or Gemini)

### 4. News Sentiment Analysis
- Finnhub news fetch (falls back to mock data when key absent)
- FinBERT classification per article (keyword heuristic fallback)
- LLM theme extraction and narrative summary
- Citations for all articles

### 5. Chatbot
- Intent detection: stock_explanation, sentiment_question, comparison_question, history_lookup, unknown
- Safety layer rejects direct buy/sell advice
- LLM grounded responses with news context
- Persistent thread history

### 6. Multi-Model Comparison
- `POST /api/evaluation/compare-models`
- Runs the same prompt through Gemini, LLaMA, and Mistral independently
- Returns latency, citation count, and safety status per model

### 7. Evaluation rubric harness
- **`backend/evaluation/eval_set.json`** — **89** cases (fundamental, buy/sell, news, chat, market movers, safety, auth, citations, memory, multi-model incl. `rub-087`–`rub-089`, **agentic chat** `rub-084`–`rub-086`, **agentic RAG** `rub-061`–`rub-075`)
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
| GET | `/api/analysis/fundamental?ticker=AAPL` | Fundamental analysis + optional LLM summary |
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
| `/history` | Research and chat history |
| `/login` | Authentication |

---

## Disclaimer

All outputs are for educational purposes only and are not financial advice. Always consult a licensed financial adviser before making investment decisions.
