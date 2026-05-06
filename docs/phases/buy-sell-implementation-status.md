# Buy/Sell roadmap — implementation status by phase

This document tracks **Phases 1–8** from [`docs/BuySellAnalysis-roadmap.md`](../BuySellAnalysis-roadmap.md) against the **StockScope** codebase. It is the single place to see **done vs. not done** for the Kavout-style Buy/Sell analysis track.

**Last reviewed:** aligned with repo layout under `StockScope/` (backend FastAPI + Next.js frontend).

---

## Summary table

| Phase | Theme | Status |
|------:|--------|--------|
| **1** | Report skeleton (schema + UI + citations shell) | **Done** |
| **2** | Data tools / Layer 1 bundle | **Done** |
| **3** | Rule-based scoring | **Done** |
| **4** | LLM narrative / advisory review | **Done** (advisory `llm_review`; not full section-by-section LLM rewrite) |
| **5** | Retrieval (RAG) | **Done** (v1 + 5.1: hybrid BM25 + embeddings, SEC ingest, hygiene) |
| **6** | Planner / Executor / Critic | **Done** (v1: fixed DAG, rule-based critic, `agent_pipeline` on analyze) |
| **7** | Memory | **Done** (v1: file-backed sessions + REST + analyze integration) |
| **8** | Evaluation | **Done** (v1: eval set + few-shots + `run_eval.py` + metrics) |

---

## Phase 1 — Report skeleton (**done**)

| Roadmap item | Implementation |
|--------------|----------------|
| JSON schema | [`schemas/buy_sell_report.json`](../../schemas/buy_sell_report.json) |
| Pydantic models | [`backend/app/schemas/buy_sell_analysis.py`](../../backend/app/schemas/buy_sell_analysis.py) |
| Mock API | `GET /api/buy-sell/report/mock` in [`backend/app/api/buy_sell_analysis.py`](../../backend/app/api/buy_sell_analysis.py) |
| UI | [`frontend/app/buy-sell/page.tsx`](../../frontend/app/buy-sell/page.tsx), [`frontend/components/buy-sell/BuySellReportView.tsx`](../../frontend/components/buy-sell/BuySellReportView.tsx) |
| Types / client | [`frontend/lib/buy-sell-api.ts`](../../frontend/lib/buy-sell-api.ts) |
| Disclaimer / citations area | Present in report UI + schema (`citations` on `BuySellReport`) |

---

## Phase 2 — Data tools (**done**)

| Roadmap item | Implementation |
|--------------|----------------|
| Price history + technicals | [`backend/app/tools/price_history_tool.py`](../../backend/app/tools/price_history_tool.py), [`technical_tool.py`](../../backend/app/tools/technical_tool.py) |
| Fundamentals | [`backend/app/tools/fundamentals_tool.py`](../../backend/app/tools/fundamentals_tool.py) |
| News | [`backend/app/tools/news_tool.py`](../../backend/app/tools/news_tool.py), Alpha Vantage [`alpha_vantage_tool.py`](../../backend/app/tools/alpha_vantage_tool.py) |
| Analyst trends | [`backend/app/tools/finnhub_tool.py`](../../backend/app/tools/finnhub_tool.py) |
| Single pipeline | [`backend/app/tools/layer1_pipeline.py`](../../backend/app/tools/layer1_pipeline.py) — `get_layer1_for_llm()` |
| API | `GET /api/buy-sell/data/{ticker}` |
| Call ledger doc | [`docs/Layer1-api-call-ledger.md`](../Layer1-api-call-ledger.md) |

---

## Phase 3 — Rule-based scoring (**done**)

| Roadmap item | Implementation |
|--------------|----------------|
| Dimension scorers | [`backend/app/services/buy_sell_scoring.py`](../../backend/app/services/buy_sell_scoring.py) — `score_fundamentals`, `score_technicals`, `score_sentiment` |
| Overall recommendation + confidence / setup | `combine_scores()` + `OverallRuleScore` in same file |
| Wired to report | `build_buy_sell_report_from_layer1()` → `GET /api/buy-sell/analyze/{ticker}` |

**Still optional later:** tune thresholds / backtest bands (roadmap already calls this iterative).

---

## Phase 4 — LLM section writer (**done**, scoped)

| Roadmap item | Implementation |
|--------------|----------------|
| Structured scores + evidence → LLM | [`backend/app/services/huggingface_llm.py`](../../backend/app/services/huggingface_llm.py); prompt includes rule scores + retrieval snippets |
| Advisory block (not replacing numeric engine) | `llm_review` on `BuySellReport`; `include_llm_review` + `BUYSELL_LLM_*` / HF env in [`backend/app/core/config.py`](../../backend/app/core/config.py) |
| Citations from tools + retrieval | Layer 1 citations + RAG chunk ids on `citations`; LLM `citations_used` constrained to retrieval ids in prompt |

**Gap vs. ideal roadmap wording:** the LLM today primarily drives the **`llm_review`** advisory JSON (rationale, suggested scores, warnings)—not a full **rewrite of every narrative section** of the Kavout-style report. Full “section writer” for each long-form field can be a future increment.

---

## Phase 5 — Retrieval / RAG (**done**, v1 + 5.1)

| Roadmap item | Implementation |
|--------------|----------------|
| News ingest | [`backend/app/rag/ingest_news.py`](../../backend/app/rag/ingest_news.py) |
| Filings ingest (from Layer1 items) | [`backend/app/rag/ingest_filings.py`](../../backend/app/rag/ingest_filings.py) |
| SEC → Layer1 filings | [`backend/app/tools/sec_edgar_tool.py`](../../backend/app/tools/sec_edgar_tool.py), [`filings_tool.py`](../../backend/app/tools/filings_tool.py) |
| Hybrid retrieval | [`backend/app/rag/hybrid_retriever.py`](../../backend/app/rag/hybrid_retriever.py) — BM25 + HF embeddings when token set |
| Embeddings persistence | [`backend/app/rag/embedding_index.py`](../../backend/app/rag/embedding_index.py), `data/rag/index/by_ticker/*.npz` |
| Store hygiene | [`backend/app/rag/store.py`](../../backend/app/rag/store.py) — prune + rotate |
| Analyze wiring | `include_retrieval`, `retrieval_top_k`, `retrieval_max_age_days`, `sync_embeddings_for_ticker` in analyze flow |
| Checklist | [`docs/Phase5-RAG-checklist.md`](../Phase5-RAG-checklist.md) |

**Optional “Phase 5.2” (not required for roadmap Phase 5 checklist):** IR/press RSS, section-aware SEC chunking, async embedding jobs, dedicated vector DB / ANN at large scale.

---

## Phase 6 — Planner / Executor / Critic (**done**, v1)

| Roadmap item | Implementation |
|--------------|----------------|
| 15 Planner | [`backend/app/agents/planner.py`](../../backend/app/agents/planner.py) — `plan_buy_sell_analysis()` builds a **fixed DAG** from flags (`include_retrieval`, `include_llm_review`) + optional `horizon` label |
| 16 Executor | [`backend/app/agents/executor.py`](../../backend/app/agents/executor.py) — `execute_buy_sell_pipeline()` runs Layer1 → optional RAG substeps → `build_buy_sell_report_from_layer1`; records **`PipelineStepTrace`** (timing, ok/skipped/error) |
| 17 Critic | [`backend/app/agents/critic.py`](../../backend/app/agents/critic.py) — **`run_critic()`** rule flags (completeness, confidence, dispersion, empty retrieval, LLM requested-but-off, missing fundamentals) |
| Orchestration | [`backend/app/agents/orchestrator.py`](../../backend/app/agents/orchestrator.py) — `run_buy_sell_with_agents()` attaches **`agent_pipeline`** to `BuySellReport` |
| API | `GET /api/buy-sell/analyze/{ticker}` defaults to **`use_agent_pipeline=true`**; set **`use_agent_pipeline=false`** for the legacy linear response without `agent_pipeline` |
| Schema | **`schema_version`** `1.2.0` default on analyze; optional **`agent_pipeline`** + **`memory`** on [`BuySellReport`](../../backend/app/schemas/buy_sell_analysis.py); JSON Schema in [`schemas/buy_sell_report.json`](../../schemas/buy_sell_report.json) |
| UI | [`frontend/components/buy-sell/BuySellReportView.tsx`](../../frontend/components/buy-sell/BuySellReportView.tsx) — **Execution trace** / **Session memory** when present on the payload |

**Not in v1 (future):** LLM-generated plans, parallel tool execution, critic that mutates or blocks the recommendation, persistent trace storage beyond the HTTP response.

---

## Phase 7 — Memory (**done**, v1)

| Roadmap item | Implementation |
|--------------|----------------|
| 18 Session / preferences | [`backend/app/memory/memory_store.py`](../../backend/app/memory/memory_store.py) — JSON file `StockScope/data/memory/sessions.json`; `MEMORY_ENABLED`, `MEMORY_MAX_RECENT_TICKERS` in [`config.py`](../../backend/app/core/config.py) |
| 19 Retrieve for follow-ups | `build_follow_up_context()` + **`memory`** block on analyze; REST [`backend/app/api/buy_sell_memory.py`](../../backend/app/api/buy_sell_memory.py) (`GET/PUT /api/buy-sell/memory/{session_id}`, reset, record, follow-up-context) |
| Analyze integration | `session_id`, `use_memory` on `GET /api/buy-sell/analyze/{ticker}`; merges **preferred_horizon** into planner when query omits horizon; **`memory_hint`** into Phase 6 plan summary |

**Not in v1:** per-user auth-bound sessions, server-side encryption, vector memory, cross-device sync.

---

## Phase 8 — Evaluation (**done**, v1)

| Roadmap item | Implementation |
|--------------|----------------|
| 20 `eval_set.json` | [`backend/evaluation/eval_set.json`](../../backend/evaluation/eval_set.json) (12 starter cases — grow toward 50+) |
| 21 `few_shot_examples.json` | [`backend/evaluation/few_shot_examples.json`](../../backend/evaluation/few_shot_examples.json) |
| 22 `run_eval.py` + metrics | [`backend/evaluation/run_eval.py`](../../backend/evaluation/run_eval.py) (`--inline`), [`backend/app/evaluation/metrics.py`](../../backend/app/evaluation/metrics.py) — writes `data/eval/last_eval_run.json` by default |
| 23 Multi-model comparison | **Not implemented** (requires additional provider wiring + eval protocol) |

See [`backend/evaluation/README.md`](../../backend/evaluation/README.md).

---

## Outside the numbered Buy/Sell phases (also in repo)

These support the product but are **not** the Phase 1–8 list above:

- **Market movers** (backend service + API + UI + [`docs/MARKET_MOVERS.md`](../MARKET_MOVERS.md))
- **Universe scripts** (Wikipedia / Polygon validation — see README + scripts)

---

## What is **yet to implement** (concise backlog)

1. **Phase 8 item 23** — Multi-model comparison harness (same eval across HF / OpenAI / etc.).  
2. **Phase 6 refinements** — LLM planner, richer critic (e.g. citation parity checks), durable trace logging.  
3. **Phase 7 refinements** — Auth-scoped sessions, encrypted store, semantic “memory retrieval” for chat.  
4. **Optional refinements** — Full LLM-driven rewrite of each long report section (beyond `llm_review`); RAG Phase 5.2 items; stale-data warnings surfaced in UI; expand `eval_set.json` with gold labels for automated scoring.

---

## Related documents

| Doc | Purpose |
|-----|---------|
| [`BuySellAnalysis-roadmap.md`](../BuySellAnalysis-roadmap.md) | Full phased spec + principles |
| [`Phase5-RAG-checklist.md`](../Phase5-RAG-checklist.md) | RAG file map + env notes |
| [`Layer1-api-call-ledger.md`](../Layer1-api-call-ledger.md) | Layer 1 provider call counts |
| [`API-keys.md`](../API-keys.md) | Environment variables overview |
