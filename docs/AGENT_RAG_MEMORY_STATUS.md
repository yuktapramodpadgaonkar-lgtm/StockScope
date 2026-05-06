# Agent, RAG, and memory status (honest snapshot)

This document describes what StockScope implements today versus what remains aspirational for a research-grade agent stack. It is meant for rubric alignment and grading—not marketing.

## Planner–Executor–Critic (buy/sell pipeline)

| Role | Status | Implementation |
|------|--------|----------------|
| **Planner** | **Partial** | [`backend/app/agents/planner.py`](../backend/app/agents/planner.py) builds a **fixed DAG** from flags (`include_retrieval`, `include_llm_review`, `horizon`). It is not an LLM that decomposes arbitrary user goals. |
| **Executor** | **Done (for buy/sell)** | [`backend/app/agents/executor.py`](../backend/app/agents/executor.py) runs Layer 1 bundle → optional RAG ingest/embed/retrieve → deterministic scoring report; records per-step traces. |
| **Critic** | **Partial** | [`backend/app/agents/critic.py`](../backend/app/agents/critic.py) applies **rule-based** checks (data completeness, confidence, dimension dispersion, empty retrieval, LLM-off flags). It does not call an LLM “judge” today. |

**Orchestration entrypoint:** [`run_buy_sell_with_agents`](../backend/app/agents/orchestrator.py) — plan → execute → attach critic metadata on the report.

## Agentic RAG (planner uses tools)

| Component | Status | Implementation |
|----------|--------|----------------|
| **LLM Planner** | **Done (v1)** | `POST /api/agentic-research/run` ([`backend/app/api/agentic_research.py`](../backend/app/api/agentic_research.py)) — Gemini/Ollama plans a small JSON tool plan (2–4 steps) over an allowlist. |
| **Executor (tools)** | **Done (v1)** | Runs 2+ existing tools (fundamental, news sentiment, buy/sell, history) and builds an evidence bundle + citations list. |
| **Writer** | **Done (v1)** | LLM writes JSON `{answer, citations_used}` constrained to provided evidence and 1-indexed citations. |
| **Repair loop** | **Done (v1)** | If the rule critic fails, one **repair** LLM call (`agentic.write_repair`) reruns with `failed_checks` + notes + prior answer; critic runs again. Response includes `first_critic_passed`, `final_critic_passed`, `repair_attempted`; `critic_passed` matches the final round. |
| **Critic** | **Partial (rule-based)** | Checks: at least 2 non-history tools, direct buy/sell regex, **valid `citations_used` indices**, **tickers in answer ⊆ evidence tickers ∪ request ticker**, **significant numbers in answer appear in evidence text / `numeric_facts`**, **news/filing language ⇒ at least one citation index**, plus `failed_checks` codes on the API response. |

## Tools (conceptual mapping)

| Tool | Role | Notes |
|------|------|--------|
| Fundamental | Research | `/api/analysis/fundamental` + [`fundamental_service`](../backend/app/services/fundamental_service.py); optional LLM summary via [`llm_client.generate_text`](../backend/app/services/ai/llm_client.py). |
| Buy/sell | Research | `/api/buy-sell/analyze/{ticker}` + scoring + optional agent block. |
| Market data | Data | yfinance-backed Layer 1 and market movers; not a unified “tool SDK” abstraction. |
| News sentiment | Research | `/api/analysis/news-sentiment` + FinBERT/LLM themes. |
| Chat | Interaction | [`chat_service`](../backend/services/chat_service.py) with intents + LLM JSON answers. |
| History | Persistence | JSON-backed [`history_service`](../backend/services/history_service.py) + `/api/history`. |
| LLM | Model gateway | [`LLMService`](../backend/services/ai/llm_service.py) (Gemini + Ollama), plus [`llm_client`](../backend/app/services/ai/llm_client.py) for fundamental summaries. |
| Buy/sell memory | Session | [`app/memory`](../backend/app/memory/) + `/api/buy-sell/memory/...` — gated by `MEMORY_ENABLED`. |
| Agentic research | Agentic RAG | `/api/agentic-research/run` orchestrates multiple tools + citations + critic checks; **one planner retry** on failure or &lt;2 tools. **Rubric doc:** [`AGENTIC_RAG_AND_MEMORY.md`](./AGENTIC_RAG_AND_MEMORY.md). **UI:** `/agentic-research`. **Eval:** `rub-061`–`rub-075`. |

## RAG

| Topic | Status |
|-------|--------|
| **Data source** | **Partial** — Chunks derived from news + filing-oriented ingest tied to Layer 1 / stubs (see [`app/rag/`](../backend/app/rag/)); not a hosted production corpus. |
| **Chunking** | **Done (v1)** — Ingest modules produce structured chunks with metadata (ticker, source, `chunk_id`). |
| **Retrieval** | **Hybrid (when enabled)** — [`hybrid_retriever.py`](../backend/app/rag/hybrid_retriever.py): BM25 + dense embeddings when HF token/index available; otherwise BM25-weighted behavior per settings. |
| **Citations / grounding** | **Partial** — [`citation_checker.py`](../backend/app/rag/citation_checker.py) verifies citation ids against retrieved chunks; buy/sell prompts constrain LLM citation ids. Not full automated grounding against live filings for every answer. |
| **“Advanced” RAG (GraphRAG / agentic)** | **Agentic RAG implemented (v1)** via `/api/agentic-research/run` (planner → tools → writer → critic). GraphRAG is not implemented. |

## Memory

| Topic | Status |
|-------|--------|
| **What is stored** | Session fields (e.g. recent tickers, preferences, optional summary text) in the buy/sell memory store when enabled — see [`memory_store`](../backend/app/memory/memory_store.py). |
| **Summaries** | Optional `session_summary` updates via API; not a separate long-horizon summarization worker. |
| **Retrieval later** | **Partial** — `build_follow_up_context` can bundle session context for prompts; chat history is separate (`history_service`). No unified semantic memory retrieval across all modules. |

## Observability

- **Structured JSONL logs (append-only):** `backend/logs/model_calls.jsonl` and `backend/logs/tool_calls.jsonl`, written from [`jsonl_audit.py`](../backend/app/observability/jsonl_audit.py) hooks in LLM paths and buy/sell executor steps (and multi-model comparison calls).

## Pending (rubric-oriented)

- Batch scoring with gold labels and automated judges on the full eval set.
- Larger few-shot / eval expansion beyond structured cases.
- Optional: GraphRAG or explicit agentic retrieval planner.
- Stronger cross-module memory (chat ↔ buy/sell ↔ fundamentals) with retrieval.
