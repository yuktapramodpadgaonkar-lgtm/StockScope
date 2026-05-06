# Evaluation (Phase 8 + rubric harness)

- **`eval_set.json`** — **89** structured cases (`id`, `category`, `input`, `expected_behavior`, `checks`, `models_to_run`, `cost`, optional `score_checks`, `score_meta`). Categories include fundamental, buy_sell, news_sentiment, chatbot, market_movers, safety_refusal, auth_protected_routes, citation_grounding, memory_history, multi_model_comparison, **agentic_chat** (`rub-084`–`rub-086`), and **agentic_rag** (`rub-061`–`rub-075`). Buy/sell rows that set `"runner": "buy_sell_orchestrator"` are consumed by `run_eval.py`.
- **`few_shot_examples.json`** — Index pointing at **`few_shot/*.json`** (one file per feature: buy/sell, fundamental, news themes, chat, multi-model, agentic chat, agentic RAG). Loaded at runtime by `services/ai/few_shot_loader.py` and prepended into the matching LLM prompts.
- **`run_eval.py`** — In-process harness: runs **buy/sell orchestrator** cases from `eval_set.json` only (use `--inline`). Writes `data/eval/last_eval_run.json` by default.
- **`run_batch_eval.py`** — Rubric batch scaffold: static HTTP checks (e.g. 401 on unauthenticated fundamentals), unit-style checks (intent, safety regex, citation helper), and optional live modes (`--live-fundamental`, `--live-news`, `--live-market-data`, `--live-orchestrator`, `--live-multi`). Writes JSON + CSV under `backend/evaluation/results/` (gitignored).
- **Agentic RAG** — `POST /api/agentic-research/run` (planner → tools → writer → critic). Batch runner can execute these cases with `--live-agentic` on `category=agentic_rag`. Optional `input.memory_seed` (session prep) and `input.expect_answer_contains` (substring checks on `answer`). See `docs/AGENTIC_RAG_AND_MEMORY.md`.
- **Shared multi-model subset** — We treat `category=multi_model_comparison` (cases `rub-054`–`rub-060`, `rub-076`–`rub-083`, and `rub-087`–`rub-089`) as the **shared LLM evaluation subset** run across **all 3 models** via `POST /api/evaluation/compare-models` (Gemini + LLaMA + Mistral). This is the subset used to report latency/safety tradeoffs on the same prompts.
- **`scoring_rules.py`** — Rule-based checks on **response text** (disclaimer, no direct buy/sell command patterns, uncertainty language, JSON shape, URLs, optional ticker allowlist).
- **`score_outputs.py`** — Merge saved model outputs with `eval_set.json` fields `score_checks` / `score_meta`; run rules; optional **`--judge`** (Gemini LLM-as-judge, needs `GEMINI_API_KEY`).
- **`run_multi_model_comparison_summary.py`** — Runs the **same** `multi_model_comparison` prompts through all three models and prints a **summary table** (avg latency, safety pass %, avg citations; optional judge scores). Writes JSON under `backend/evaluation/results/` by default.
- **`run_capture_and_score.py`** — **Full pipeline:** captures every model output into `captured_responses_<stamp>.json` (+ `captured_bundle_<stamp>.json` with task/ticker metadata), runs **`score_saved_runs()`** from `score_outputs.py` (rules + optional `--judge`), writes `scoring_<stamp>.json`, and generates **`eval_report_<stamp>.md`**.
- **`services/ai/response_metrics.py`** — Heuristic **per-response metrics** attached to `compare-models` results and scoring details: `safety` object (`passed`, `has_disclaimer`, `advice_detected`), `grounding_score`, `completeness_score` (+ core keyword hits `risk`/`profit`/`growth`), `hallucination_flag` (numbers not in prompt), `response_length`, `word_count`. **`metric_summary`** on each scoring row matches the “best version” shape (plus `completeness_core` as `hits/3`). LLM judge returns **clarity / correctness / grounding** (1–5) and **`judge_score`** (mean).

From the **StockScope** repo root:

```bash
python backend/evaluation/run_eval.py --inline --max-cases 3
python backend/evaluation/run_batch_eval.py
python backend/evaluation/run_batch_eval.py --live-fundamental --live-news --live-market-data
python backend/evaluation/run_batch_eval.py --category agentic_chat --live-chat
python backend/evaluation/run_batch_eval.py --category agentic_rag --live-agentic
```

`run_eval.py` requires outbound access for **yfinance** (and more if cases enable retrieval/LLM). `run_batch_eval.py` defaults to checks that avoid paid LLM calls; opt in per flag.

---

## Multi-model comparison (clear subset + metrics table)

**Same prompts for every model:** each case supplies `input.task`, `input.ticker`, and `input.query`. The backend builds **one** prompt (`build_multi_model_comparison_prompt`) and runs it on **Gemini**, **LLaMA (Ollama)**, and **Mistral (Ollama)** — same as `POST /api/evaluation/compare-models`.

| Subset | Case IDs | Count |
|--------|-----------|-------|
| **Core** (minimal shared set) | `rub-054`–`rub-060` | 7 |
| **Full** shared LLM subset | `rub-054`–`rub-060`, `rub-076`–`rub-083`, `rub-087`–`rub-089` | 18 |

**Report these metrics** (all available from the comparison runner / summary script):

- **Latency** — mean per model (ms per case; table can show seconds).
- **Safety pass rate** — % of runs passing the same **regex** advisory check as `compare-models` (`safety_passed` in code).
- **Citation count** — mean URL count per response (heuristic: `https?://` matches).
- **Quality (optional)** — mean **LLM-as-judge** score 1–5 from `score_outputs.py` / `--judge` on the summary script (uses Gemini; keep one judge for comparability).

**Example summary table** (replace numbers with your run; “Notes” is free text for your report):

| Model | Avg latency | Safety pass | Avg citations | Avg judge (1–5) | Notes |
|-------|-------------|--------------|---------------|-----------------|-------|
| Gemini | 1.2s | 100% | 3.1 | 4.2 | … |
| Llama | 5.4s | 85% | 2.0 | 3.6 | … |
| Mistral | 3.8s | 90% | 2.5 | 3.9 | … |

**Generate the table + JSON** (needs `GEMINI_API_KEY` for Gemini, **Ollama** running for local models):

```bash
# Smallest shared subset (7 cases × 3 models)
python backend/evaluation/run_multi_model_comparison_summary.py --subset core

# Full shared subset (18 cases × 3 models)
python backend/evaluation/run_multi_model_comparison_summary.py --subset full

# Include optional judge column (extra Gemini calls)
python backend/evaluation/run_multi_model_comparison_summary.py --subset full --judge
```

Cost is optional in write-ups; if you use free tiers / local Ollama, state that and focus on **latency vs safety vs citations vs optional judge**.

### Capture + scoring + report (responses.json + `score_outputs`)

```bash
# Writes backend/evaluation/results/captured_responses_*.json, scoring_*.json, eval_report_*.md
python backend/evaluation/run_capture_and_score.py --subset core
python backend/evaluation/run_capture_and_score.py --subset full --judge

# Only save outputs (no Gemini judge / no rule pass summary)
python backend/evaluation/run_capture_and_score.py --subset full --capture-only
```

Re-score an existing capture without re-running models:

```bash
python backend/evaluation/score_outputs.py --responses backend/evaluation/results/captured_responses_<stamp>.json --judge --out backend/evaluation/results/rescore_<stamp>.json
```

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
