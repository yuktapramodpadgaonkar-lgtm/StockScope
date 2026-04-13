# 📌 StockScope — AI-Powered Stock Research Platform

## 👥 Team Members
- Yukta Pramod Padgaonkar  
- Ramya Gopalaswamy  
- Revati Dharmadhikari  

---

## 📊 Project Overview

StockScope is a **vertical AI-powered stock research platform** designed to provide structured, explainable, and data-driven insights for retail investors.

The system integrates:
- market data
- financial fundamentals
- news sentiment
- conversational AI

into a unified interface for stock analysis and decision support.

---

## 🎯 Problem Statement

Retail investors rely on fragmented tools such as:
- price charts
- news feeds
- financial reports

These tools:
- lack integration
- provide unstructured insights
- do not explain reasoning clearly

StockScope addresses this by building an **evaluation-driven AI system** that combines deterministic analytics with AI-based reasoning.

---

## 🧠 Core Features

### 1. Market Movers
- Displays top gainers and losers
- Shows price, percentage change, and volume
- Interactive table UI for quick exploration
- Market movers (API, yfinance, ranking, caching): see docs/MARKET_MOVERS.md.
---

### 2. Buy/Sell Analysis (Phase 1 + Layer 1)
- Kavout-style structured report schema for BUY/HOLD/SELL outputs
- Mock report API + UI page for contract testing
- Layer 1 data bundle API with provider call ledger
- Local technical computation (RSI/MACD/MAs) from one shared history fetch
- Buy/sell roadmap and source strategy docs:
  - `docs/BuySellAnalysis-roadmap.md`
  - `docs/BuySellAnalysis-data-sources.md`
  - `docs/Layer1-api-call-ledger.md`

---

### 3. Fundamental Analysis
- Extracts financial metrics (P/E, ROE, margins, growth)
- Applies rule-based evaluation for financial health
- Generates structured report including:
  - strengths
  - risks
  - overall verdict

---

### 4. News Sentiment Analysis
- Retrieves recent news for a ticker
- Aggregates sentiment signals
- Identifies major themes affecting stock movement

---

### 5. Chatbot
- Natural language stock queries
- Planned agent-based reasoning system

---

### 6. History & Memory (In Progress)
- Stores chat history
- Tracks previous research queries
- Planned long-horizon memory

---


## 🗂️ Data Sources

- **yfinance**
  - stock prices / historical candles
  - fundamentals and company profile fields
  - fallback news headlines when Alpha Vantage is not configured

- **Alpha Vantage (implemented, optional via API key)**
  - `NEWS_SENTIMENT` feed for ticker news + sentiment metadata

- **Finnhub (implemented, optional via API key)**
  - analyst recommendation trend data (`/stock/recommendation`)

- **Polygon.io (implemented for scripts, not runtime API)**
  - ticker validation and name enrichment for universe CSV refresh scripts
  - does not provide full index-constituent lists via one REST endpoint

- **SEC EDGAR + Press Releases (planned for retrieval/RAG)**
  - filing-grounded evidence and company-issued event text

---

## ⚙️ Technical Architecture

### Frontend
- Next.js (React)
- TypeScript
- Tailwind CSS

### Backend
- FastAPI (Python)
- Service-based modular architecture
- Pydantic schemas for structured outputs

### AI Design (Planned)
- LLM integration (GPT / Llama / Mistral)
- Agent system (Planner–Executor–Critic)
- Hybrid RAG (vector + keyword retrieval)
- FinBERT sentiment model

---

## 🔄 System Flow

Frontend → API Layer → Service Layer → Schema Validation → Response

Example:

User → Fundamental API → yfinance → Rule Engine → Structured Output → UI

---

## 🧪 Evaluation Plan (Upcoming)

We will evaluate system performance using:

### Dataset
- 100+ test cases across:
  - price explanations
  - fundamental analysis
  - sentiment analysis
  - chatbot queries

### Metrics
- numerical accuracy
- response completeness
- hallucination rate
- latency and cost

### Model Comparison
- GPT-4o (baseline)
- Open-source model (Llama / Mistral)
- Secondary model (TBD)

---

## 🚧 Current Progress

### ✅ Completed
- Backend APIs for:
  - buy/sell analysis:
    - phase 1 report schema + mock endpoint
    - phase 2 layer1 data bundle endpoint (`/api/buy-sell/data/{ticker}`)
  - fundamental analysis
  - market movers
  - sentiment (basic)
  - chat (skeleton)
  - auth (mock)
- Frontend pages:
  - buy/sell report (mock)
  - market movers
  - fundamentals
  - chatbot
  - history
  - login
- Structured schemas for all modules
- Deterministic fundamental analysis engine
- Layer1 source docs and call-budget tracking:
  - `docs/API-keys.md`
  - `docs/API-keys-testing.md`
  - `docs/Layer1-api-call-ledger.md`

---

### 🔄 In Progress
- Buy/sell scoring engine (fundamental / technical / sentiment scores)
- Buy/sell report synthesis pipeline from Layer1 bundle
- News sentiment refinement and source fallback handling
- Retrieval source prep (SEC + press release ingestion design)
- Chatbot routing and responses

---

### ⏳ Pending
- LLM integration
- Agent-based reasoning system
- Hybrid RAG with citations
- Multi-model comparison
- Long-horizon memory
- Formal eval harness for 50+ buy/sell test cases

---

## 🔮 Next Steps

1. Complete Buy/Sell scoring + final recommendation mapping (see `docs/BuySellAnalysis-roadmap.md`)  
2. Integrate LLM section writer for buy/sell narratives with citations  
3. Implement Planner–Executor–Critic workflow for buy/sell + chat paths  
4. Add hybrid RAG over SEC + press release + general news sources  
5. Expand eval dataset and multi-model benchmarking  
6. Improve sentiment quality and fallback behavior  
7. Implement Google OAuth authentication  

Buy/Sell planning docs:
- `docs/BuySellAnalysis-roadmap.md`
- `docs/BuySellAnalysis-data-sources.md`
- `docs/BuySellAnalysis-retrieval-sources.md`

---

## 🚀 Setup & Running the Project

### 🔧 Backend Setup

```bash
python -m venv .venv
source .venv/bin/activate  # Mac/Linux
.venv\Scripts\activate    # Windows
```

```bash
pip install --upgrade pip
pip install -r backend/requirements.txt
```

---

### ▶️ Run Backend

```bash
uvicorn app.main:app --reload --app-dir backend
```

Open API docs:

http://127.0.0.1:8000/docs

---

### ⚠️ CORS Configuration

Ensure `backend/.env` contains:

CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000

### 🔑 API Keys

6. **API keys** (Alpha Vantage, Finnhub, Polygon for scripts, etc.): copy
   `backend/.env.example` to `backend/.env` and see [`docs/API-keys.md`](docs/API-keys.md).
   To test that keys work for a stock, see [`docs/API-keys-testing.md`](docs/API-keys-testing.md).

---

### 🌐 Frontend Setup

```bash
cd frontend
cp .env.local.example .env.local
npm install
npm run dev
```

Open:

http://localhost:3000

---

### 🔗 Backend–Frontend Connection

Backend: http://127.0.0.1:8000

Frontend uses:

NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000

---

### 📊 Available Pages

- /buy-sell
- /market-movers
- /fundamentals
- /chatbot
- /history
- /login

---
