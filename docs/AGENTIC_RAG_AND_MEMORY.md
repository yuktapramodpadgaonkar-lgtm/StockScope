# Agentic RAG and long-horizon memory

Rubric-facing summary for **D — Advanced RAG**, **Planner–Executor–Critic (P–E–C)**, and **memory**.

---

## What we implement: Agentic RAG (four roles)

We implement **Agentic RAG** as a **Planner → Executor → Writer → Critic** loop (with small fallbacks below):

1. **Planner** — An LLM selects an ordered list of **allowed tools** (JSON `steps`). It must use **at least two different non-`history` tools** when `require_two_tools` is true.
2. **Executor** — The backend runs each tool deterministically, collects structured outputs, and builds **normalized evidence** plus a **citation list** (URLs/titles where available).
3. **Writer** — An LLM produces a natural-language **answer** and **`citations_used`** (1-based indices into the citation list). Output is constrained to JSON.
4. **Critic** — **Rule-based** checks validate **safety** (e.g. direct buy/sell phrasing) and **grounding** (citation indices, tickers, numbers, news/filing claims vs citations). If the critic fails, **one repair** writer pass may run with the failed check codes and notes.

**Reliability additions**

- **Planner re-try:** If the planner **errors**, returns **invalid JSON**, or yields **fewer than two distinct non-history tools** (when required), the server runs the **planner a second time** with an explicit **correction hint** (and logs `agentic.plan_retry`). This is intentionally simple (one retry), not full iterative replanning.
- **Writer re-try (repair):** If the **critic** fails, **one** additional writer call (`agentic.write_repair`) may fix the answer before a final critic pass.

**HTTP:** `POST /api/agentic-research/run` — `backend/app/api/agentic_research.py`.

**UI:** `frontend/app/agentic-research/page.tsx` (navbar: **Agentic research**).

**Related (not the same loop):** The buy/sell pipeline uses a **fixed DAG** of agents plus its own critic; hybrid **BM25 + embedding** RAG over `data/rag/chunks.jsonl` runs **inside** the `buy_sell` tool when enabled—not as the agentic planner loop above.

---

## Executor tools (allowlist)

| Tool | Role |
|------|------|
| `fundamental` | Structured fundamentals (e.g. yfinance) + minimal quote URL citation. |
| `news_sentiment` | News/sentiment bundle + article URLs when available. |
| `buy_sell` | Full buy/sell report path (may include chunk RAG retrieval). |
| `history` | Read-only snapshot from the app history store (counts / metadata). |

Optional **`secondary_ticker`:** The server merges **fundamental + news** evidence for that symbol so **multi-ticker** questions have grounded text for both symbols.

---

## Critic (machine codes)

Examples: `insufficient_distinct_tools`, `direct_financial_advice_pattern`, `citation_index_invalid`, `answer_ticker_not_in_evidence`, `numeric_claim_not_in_evidence`, `news_or_filing_claim_without_citation`.

Response fields include `failed_checks`, `critic_notes`, `first_critic_passed`, `final_critic_passed`, `repair_attempted`, **`plan_retry_attempted`**; **`critic_passed` == `final_critic_passed`**.

---

## Long-horizon memory (session-based)

Session JSON in `data/memory/sessions.json` includes **`memory_profile`**:

```json
{
  "frequent_tickers": ["AAPL", "NVDA"],
  "preferred_topics": ["fundamentals", "news"],
  "risk_style": "cautious"
}
```

It is **written** on analyze / preferences / agentic runs, **summarized** from activity, and **injected** into planner/writer prompts as context (**not** as verified market facts). The API response echoes **`memory_profile`** after each agentic run.

---

## Limitations (read this for grading)

Stating these explicitly avoids losing marks for over-claiming:

| Limitation | Detail |
|------------|--------|
| **Grounding checks are heuristic** | The critic uses patterns and substring checks on evidence text / `numeric_facts`—not formal entailment, span alignment, or an LLM judge. |
| **Memory is session-based** | We persist a **structured JSON profile** and recent tickers per session id—not a global embedding memory store or semantic retrieval across all past sessions. |
| **GraphRAG is not implemented** | No knowledge-graph traversal or GraphRAG retrieval; the planner chooses **API tools**, not graph hops. |
| **One planner retry** | We do not run an open-ended replan loop; at most **one** extra planner call with a hint. |
| **Repair cannot add tools** | The repair writer cannot fetch new evidence; only the initial executor bundle is used unless you call the endpoint again. |

---

## Evaluation

Agentic live cases: **`rub-061`–`rub-075`** (`category: agentic_rag`, check `agentic_rag_live`).

```bash
python backend/evaluation/run_batch_eval.py --category agentic_rag --live-agentic
```

Optional `input` fields: `secondary_ticker`, `memory_seed`, `expect_answer_contains`.

See also: `docs/AGENT_RAG_MEMORY_STATUS.md`.
