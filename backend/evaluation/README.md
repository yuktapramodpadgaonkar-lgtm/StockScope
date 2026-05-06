# Evaluation (Phase 8 + rubric harness)

- **`eval_set.json`** — **75** structured cases (`id`, `category`, `input`, `expected_behavior`, `checks`, `models_to_run`, `cost`, optional `score_checks`, `score_meta`). Categories include fundamental, buy_sell, news_sentiment, chatbot, market_movers, safety_refusal, auth_protected_routes, citation_grounding, memory_history, multi_model_comparison, and **agentic_rag** (`rub-061`–`rub-075`). Buy/sell rows that set `"runner": "buy_sell_orchestrator"` are consumed by `run_eval.py`.
- **`few_shot_examples.json`** — Short exemplars for prompt tuning or LLM-as-judge baselines.
- **`run_eval.py`** — In-process harness: runs **buy/sell orchestrator** cases from `eval_set.json` only (use `--inline`). Writes `data/eval/last_eval_run.json` by default.
- **`run_batch_eval.py`** — Rubric batch scaffold: static HTTP checks (e.g. 401 on unauthenticated fundamentals), unit-style checks (intent, safety regex, citation helper), and optional live modes (`--live-fundamental`, `--live-news`, `--live-market-data`, `--live-orchestrator`, `--live-multi`). Writes JSON + CSV under `backend/evaluation/results/` (gitignored).
- **Agentic RAG** — `POST /api/agentic-research/run` (planner → tools → writer → critic). Batch runner can execute these cases with `--live-agentic` on `category=agentic_rag`. Optional `input.memory_seed` (session prep) and `input.expect_answer_contains` (substring checks on `answer`). See `docs/AGENTIC_RAG_AND_MEMORY.md`.
- **`scoring_rules.py`** — Rule-based checks on **response text** (disclaimer, no direct buy/sell command patterns, uncertainty language, JSON shape, URLs, optional ticker allowlist).
- **`score_outputs.py`** — Merge saved model outputs with `eval_set.json` fields `score_checks` / `score_meta`; run rules; optional **`--judge`** (Gemini LLM-as-judge, needs `GEMINI_API_KEY`).

From the **StockScope** repo root:

```bash
python backend/evaluation/run_eval.py --inline --max-cases 3
python backend/evaluation/run_batch_eval.py
python backend/evaluation/run_batch_eval.py --live-fundamental --live-news --live-market-data
python backend/evaluation/run_batch_eval.py --category agentic_rag --live-agentic
```

`run_eval.py` requires outbound access for **yfinance** (and more if cases enable retrieval/LLM). `run_batch_eval.py` defaults to checks that avoid paid LLM calls; opt in per flag.

---

## Fundamental batch eval (`--live-fundamental`)

These rows call **`GET /api/analysis/fundamental`** with a **mock Bearer token** (no UI). They exercise the **deterministic yfinance-backed** report (the harness does **not** pass `include_llm`, so no Gemini/Ollama usage from these checks).

| Case IDs | Checks | Needs `--live-fundamental` |
|----------|--------|---------------------------|
| **rub-004** | `manual_or_ci_token` | Yes |
| **rub-011–rub-018** | `schema_fundamental_authed` (tickers AAPL, MSFT, GOOG, BRK-B, JPM, XOM, DIS, INTC) | Yes |

**Requirements:** outbound **network** (yfinance). Failures are often rate limits, ticker normalization (e.g. `BRK-B`), or transient provider errors.

**Run only fundamental-category cases** (avoids scanning all 60 rows):

```bash
python backend/evaluation/run_batch_eval.py --category fundamental --live-fundamental
```

**Include rub-004** (it lives under `auth_protected_routes` but uses the same live flag):

```bash
python backend/evaluation/run_batch_eval.py --category fundamental --category auth_protected_routes --live-fundamental
```

**Warning:** `--max-cases` slices the **filtered** list in order. If you omit `--category`, a small `--max-cases` can skip **rub-011+** entirely because fundamental rows are not at the start of `eval_set.json`.

---

## When to run automated scoring (rubric B — final report)

You do **not** need this for day-to-day app development. Use it once you can **save model answers** per `case_id` (e.g. from chat, `compare-models`, or a small capture script).

**Suggested order**

1. Finish / freeze `eval_set.json` and extend optional **`score_checks`** (and **`score_meta`** for rules like `tickers_subset_of_allowed`) on rows you will grade.
2. Run **`run_batch_eval.py`** for structural/API coverage; separately **record responses** into a JSON file.
3. Run **`score_outputs.py`** on that file (rule-based first).
4. Optionally add **`--judge`** for subjective rubric dimensions; keep **one** judge model (e.g. Gemini) for comparability.
5. Export **pass rate**, **safety failures**, **avg latency**, **error rate** from the summary; add **cost** manually or via token counts later.

**Optional fields on eval cases**

| Field | Purpose |
|-------|---------|
| `score_checks` | List of rule names (see `scoring_rules.RULE_REGISTRY`) |
| `score_meta` | e.g. `{"allowed_tickers": ["NVDA"]}` for `tickers_subset_of_allowed` |
| `expected_behavior` | Used by LLM judge when `--judge` is set |

Example **`responses.json`** (you produce this from your pipeline):

```json
[
  {
    "case_id": "rub-039",
    "model": "gemini",
    "response_text": "General information only; not financial advice. Outcomes are uncertain and depend on your goals.",
    "latency_ms": 1100
  }
]
```

```bash
python backend/evaluation/score_outputs.py --responses responses.json
python backend/evaluation/score_outputs.py --responses responses.json --judge --out scoring_report.json
```

**Note:** `run_batch_eval.py` does not yet write full LLM transcripts; scoring assumes a separate capture step for the final report.
