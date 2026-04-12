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
  Market movers (API, yfinance, ranking, caching): see docs/MARKET_MOVERS.md.
---

### 2. Fundamental Analysis
- Extracts financial metrics (P/E, ROE, margins, growth)
- Applies rule-based evaluation for financial health
- Generates structured report including:
  - strengths
  - risks
  - overall verdict

---

### 3. News Sentiment Analysis
- Retrieves recent news for a ticker
- Aggregates sentiment signals
- Identifies major themes affecting stock movement

---

### 4. Chatbot
- Natural language stock queries
- Planned agent-based reasoning system

---

### 5. History & Memory (In Progress)
- Stores chat history
- Tracks previous research queries
- Planned long-horizon memory

---


## 🗂️ Data Sources

- **yfinance**
  - stock prices
  - financial metrics
  - company profile

- **Finnhub (partial / planned)**
  - company news
  - sentiment signals

- **SEC EDGAR (planned)**
  - filings for advanced RAG

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
  - fundamental analysis
  - market movers
  - sentiment (basic)
  - chat (skeleton)
  - auth (mock)
- Frontend pages:
  - market movers
  - fundamentals
  - chatbot
  - history
  - login
- Structured schemas for all modules
- Deterministic fundamental analysis engine

---

### 🔄 In Progress
- News sentiment refinement
- Chatbot routing and responses
- Authentication improvements

---

### ⏳ Pending
- LLM integration
- Agent-based reasoning system
- Hybrid RAG with citations
- Multi-model comparison
- Long-horizon memory

---

## 🔮 Next Steps

1. Integrate LLM for explanation generation  
2. Implement Planner–Executor–Critic workflow  
3. Add hybrid RAG for grounded responses  
4. Improve sentiment analysis using FinBERT  
5. Implement Google OAuth authentication  
6. Build evaluation dataset and benchmarking  

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

- /market-movers
- /fundamentals
- /chatbot
- /history
- /login

---
