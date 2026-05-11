# Buy/Sell Analysis — Next Steps & Roadmap

**See also:** Per-phase implementation status (done vs. not done): [`docs/phases/buy-sell-implementation-status.md`](phases/buy-sell-implementation-status.md).

Citation-grounded **AI Equity Research Assistant** for buy/sell analysis. The **structured Buy/Sell report** is the **output contract**; the **agentic + RAG + tools** stack sits behind it.

---

## Principles

1. **Start from the output format, not the model** — define the JSON/report schema before agents or prompts.
2. **Do not** collapse the product into a single generic prompt — the rubric expects evaluation, agents, RAG, memory, and multi-model comparison.
3. **Winning combo:** Rich report UI on the front end, grounded multi-agent system on the back end.

---

## 1. Report schema (define first)

Lock the API/UI contract. Example structure (adjust field names in one place as you iterate):

| Area | Purpose |
|------|---------|
| `ticker` | Symbol |
| `recommendation` | BUY / HOLD / SELL |
| `confidence` | 0–100 |
| `optimal_timeframe` | e.g. `"3-6 months"` |
| `setup_quality` | 0–100 |
| `investment_thesis` | `summary`, `key_drivers[]` |
| `fundamental_analysis` | score, weight, narrative, valuation block, verdict |
| `technical_analysis` | score, weight, trend, indicators, verdict |
| `sentiment_analysis` | score, weight, developments, verdict |
| `final_verdict` | overall_score, rating, alignment, conflicts |
| `risk_assessment` | key risks, action plan (if own / if want to buy) |
| `citations` | grounded sources |

**Suggested weights (v1):** Fundamentals **40%**, Technicals **30%**, Sentiment **30%**.

**Suggested score → label:**

- **75–100** → BUY  
- **55–74** → HOLD  
- **0–54** → SELL  

**Formula:**  
`overall_score = 0.40 × fundamental + 0.30 × technical + 0.30 × sentiment`

---

## 2. Four system layers (build in this order conceptually)

| Layer | What it is |
|-------|------------|
| **Layer 1 — Data pipeline** | Structured fetches: prices, indicators, fundamentals, news, optional filings/transcripts. |
| **Layer 2 — Retrieval (RAG)** | Hybrid search (vector + keyword/BM25), metadata (`ticker`, `date`, `source`, `section`, doc type). |
| **Layer 3 — Multi-agent reasoning** | Planner → Executor → Critic (tools + verification). |
| **Layer 4 — Report generator** | Structured JSON + narrative + citations. |

---

## 3. Data pipeline — backend functions to implement

Implement **before** heavy prompting:

1. `get_price_history(ticker)`
2. `get_technical_indicators(ticker)`
3. `get_fundamentals(ticker)`
4. `get_recent_news(ticker)`
5. `get_filings_or_transcripts(ticker)` (optional in MVP; stub if needed)

**Goal:** Every downstream step consumes **structured** data, not ad hoc strings.

---

## 4. Retrieval layer (assignment: advanced RAG)

**Knowledge base may include:** earnings transcripts, SEC filing chunks, fundamentals summaries, finance news, analyst commentary (if allowed).

**Storage:** vector DB + metadata for filtering.

**Retrieval:** hybrid — semantic + keyword/BM25; **filter** by `ticker` and `date`.

---

## 5. Multi-agent pipeline

| Role | Responsibility |
|------|----------------|
| **Planner** | Decompose query: which tools, retrieval, scoring, citation checks, final report. |
| **Executor** | Run tools: technical, fundamentals, news, retrieval, calculator. |
| **Critic** | Missing evidence, unsupported claims, contradictions, missing citations, schema violations. |

---

## 6. Scoring dimensions (v1 — rule-based engine)

Each dimension outputs **0–100**.

**Fundamental:** revenue/EPS growth, margins, debt/equity, P/E vs peers, DCF upside/downside (where data exists).

**Technical:** price vs 50/200 DMA, RSI, MACD, trend, breakout/breakdown.

**Sentiment:** headline tone, earnings reaction, upgrades/downgrades, catalysts (from news + optional RAG).

Then **`overall_recommendation()`** maps weighted score to BUY/HOLD/SELL using the bands above.

---

## 7. Safety & guardrails (finance domain)

1. **Disclaimer:** not financial advice.  
2. **No unsupported claims** — tie factual statements to `citations`.  
3. **Stale-data warning** when inputs are old.  
4. **Critic** may block or mark **incomplete** if a dimension lacks evidence.  
5. Optional rule: **no final BUY/SELL** without evidence from all three dimensions unless explicitly **incomplete**.

---

## 8. Phased build order (numbered roadmap)

### Phase 1 — Report skeleton

1. Freeze **JSON schema** (version in repo, e.g. `schemas/buy_sell_report.json`).
2. Build **report UI** that renders every section (empty/mock data OK).
3. Add **disclaimer** and placeholder **citations** area.

**Status (implemented):** `schemas/buy_sell_report.json` + Pydantic `BuySellReport` in `backend/app/schemas/buy_sell_analysis.py`; mock API `GET /api/buy-sell/report/mock`; UI at `/buy-sell` loads mock from API.

### Phase 2 — Data tools

4. Implement **price history** + **technical indicators** (Layer 1).
5. Implement **fundamentals** tool.
6. Implement **news** tool.
7. Wire tools to a single **`analyze_stock(ticker, horizon=...)`** internal pipeline (stub LLM OK).

**Status (implemented):** `backend/app/tools/` — granular helpers plus **`get_layer1_for_llm()`** (single history fetch, local technicals, AV news/sentiment when keyed, Finnhub recommendations when keyed). **Ledger:** [`Layer1-api-call-ledger.md`](Layer1-api-call-ledger.md). **API:** `GET /api/buy-sell/data/{ticker}` returns bundle + `call_ledger`.

### Phase 3 — Rule-based scoring

8. Implement `fundamental_score()`, `technical_score()`, `sentiment_score()`.
9. Implement `overall_recommendation()` + confidence/setup_quality heuristics (iterate later).

### Phase 4 — LLM section writer

10. Pass **structured evidence + scores** into an LLM to produce polished **section text** (still schema-validated).
11. Enforce **citations** array populated from tool + retrieval outputs.

### Phase 5 — Retrieval

12. Ingest **news** (and later filings/transcripts).
13. Implement **hybrid retriever** + metadata filters.
14. Merge retrieved chunks into section prompts with explicit **source IDs**.

**Status (implemented, v1 + 5.1):** `backend/app/rag/` — chunk store with **prune + size-based rotation**, **BM25 + HF embedding** hybrid retrieval (per-ticker `data/rag/index/by_ticker/*.npz`), **freshness** (`retrieval_max_age_days` / `RAG_MAX_CHUNK_AGE_DAYS`), **SEC EDGAR** filings in Layer 1 when `SEC_USER_AGENT` is set, and analyze-endpoint wiring (`include_retrieval`, `retrieval_top_k`, embedding sync). See `docs/Phase5-RAG-checklist.md`.

### Phase 6 — Planner / Executor / Critic

15. Implement **planner** (task graph from user query).
16. Implement **executor** (tool + retrieval calls, logging).
17. Implement **critic** (gates or flags before returning report).

**Status (implemented, v1):** `backend/app/agents/` — fixed DAG planner (`planner.py`), timed executor trace (`executor.py`), rule-based critic (`critic.py`), orchestrator `run_buy_sell_with_agents()` attaching **`agent_pipeline`** to `BuySellReport` on `GET /api/buy-sell/analyze/{ticker}` (`use_agent_pipeline` default true). Report schema **`1.2.0`** when memory is attached. See [`docs/phases/buy-sell-implementation-status.md`](phases/buy-sell-implementation-status.md).

### Phase 7 — Memory

18. Store **recent tickers**, **preferred horizon**, **analysis style**, **session summary**.
19. Expose **retrieve** for follow-up turns (“same as last time but shorter”).

**Status (implemented, v1):** `backend/app/memory/` + `GET/PUT /api/buy-sell/memory/{session_id}`; analyze params **`session_id`**, **`use_memory`**; optional **`memory`** block on `BuySellReport`; `data/memory/sessions.json`.

### Phase 8 — Evaluation

20. Build **`eval_set.json`** (50+ queries: large-cap tech, staples, volatile growth, dividends, contradictions, earnings surprises, guidance cuts, spillover, horizons).
21. Add **`few_shot_examples.json`** (10–20 report exemplars).
22. **`run_eval.py`** + **metrics**: citation correctness, groundedness, format, reasoning, latency, cost.
23. **Multi-model comparison:** e.g. OpenAI + Gemini or Claude + **one open-source** (Llama / Qwen / Mistral) on the same eval set.

**Status (implemented, v1 starter):** `backend/evaluation/eval_set.json` (12 cases to extend), `few_shot_examples.json`, `run_eval.py --inline`, `backend/app/evaluation/metrics.py`. **Item 23** (multi-model) not automated yet. See `backend/evaluation/README.md`.

---

## 9. Suggested project layout (modules)

```
backend/
  api/
    analyze.py          # POST analyze_stock
    chat.py             # optional conversational wrapper
  tools/
    technical_tool.py
    fundamentals_tool.py
    news_tool.py
    retrieval_tool.py
    calculator_tool.py
  rag/
    ingest_filings.py
    ingest_news.py
    hybrid_retriever.py
    citation_checker.py
  agents/
    planner.py
    executor.py
    critic.py
    report_writer.py
  memory/
    memory_store.py
    session_summary.py
    memory_retriever.py
  evaluation/
    eval_set.json
    few_shot_examples.json
    run_eval.py
    metrics.py
  logging/
    prompt_logger.py
    tool_logger.py
    output_logger.py
frontend/
  stock-report page
  chat page (optional)
  history / saved analyses
```

---

## 10. Dataset & evaluation (rubric alignment)

**Per-case example:**

```json
{
  "id": 1,
  "ticker": "AAPL",
  "query": "Should I buy AAPL for the next 6 months?",
  "expected_output_type": "buy_sell_report",
  "expected_dimensions": ["fundamental", "technical", "sentiment"],
  "requires_tools": true,
  "requires_citations": true
}
```

**Coverage goals:** mix of sectors, vol profiles, signal conflicts, events, horizons.

---

## 11. UI & engineering checklist

**UI:** ticker input, full report display, citations panel, session history, saved analyses.

**Engineering:** prompt logging, tool-call logging, model logging, output logging, safety checks.

---

## 12. First milestone (MVP definition)

**Done when:**

- One **report schema** is stable.
- One **`analyze_stock()`** (or `POST /api/analyze`) returns: recommendation, confidence, timeframe, setup quality, thesis, three weighted sections, final verdict, risks, action plan, **citations**.
- **Rule-based scores** + one **LLM narrative** path.
- Manual smoke test on **5 tickers**.

**Then** expand agents, RAG, memory, and eval harness.

---

## 13. This week — minimal checklist

1. **Freeze** output schema (JSON + TypeScript types if applicable).
2. **One endpoint:** `analyze_stock(ticker, horizon="6-12 months")` returning the structure above (mock tools allowed for 24h).
3. **One structured** Buy/Sell report page/card in the UI.
4. **Rule-based** `overall_score` + BUY/HOLD/SELL bands.
5. **LLM** fills narrative sections from structured inputs; **citations** array from sources you control.
6. **Test** on 5 stocks manually.
7. Only after that: **agent pipeline** + **eval set** expansion.

---

## 14. Problem formulation (for proposal / README)

> We build a **domain-specific AI equity research assistant** that generates **citation-grounded** buy/sell analysis reports by combining **financial data**, **retrieval** over earnings/news/filings, and **multi-agent** reasoning — not a general-purpose chatbot.

---

## 15. Optional next doc

- Day-by-day implementation calendar, or  
- **Architecture diagram** (Mermaid) + **prompt / scoring** appendix — add as `docs/BuySellAnalysis-architecture.md` when ready.

---

*Document version: 1.0 — aligns with the structured Buy/Sell output template + CMPE-258-style requirements (agents, RAG, memory, evaluation, multi-model).*
