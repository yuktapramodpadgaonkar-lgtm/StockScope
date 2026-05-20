# report_artifacts/

Committed evaluation artifacts for the StockScope project report.
Files here are the authoritative, grader-visible copies; the full run history lives in `backend/evaluation/results/` (gitignored).

## Files

| File | Run stamp | Pass / Fail / Not-run | Flags used |
|------|-----------|------------------------|------------|
| [batch_eval_20260519-182113.csv](batch_eval_20260519-182113.csv) | 2026-05-19 18:21 | **72 / 1 / 38** | `--live-market-data --live-fundamental --live-chat --live-news` |
| [batch_eval_20260519-174832.csv](batch_eval_20260519-174832.csv) | 2026-05-19 17:48 | **60 / 0 / 51** | `--live-market-data --live-fundamental` |

The `182113` run is the primary artifact (more live categories tested).
The `174832` run is included for comparison (static + market + fundamental only, 0 failures).

## Category breakdown (primary run: 182113)

| Category | Cases | Pass | Notes |
|----------|-------|------|-------|
| auth_protected_routes | 5 | 5 | static |
| citation_grounding | 5 | 5 | static |
| memory_history | 4 | 4 | static |
| safety_refusal | 6 | 6 | static |
| market_movers | 20 | 20 | live market data |
| fundamental | 10 | 10 | live yfinance |
| chatbot | 10 | 10 | live LLM (LLaMA) |
| news_sentiment | 10 | 10 | live LLM (LLaMA) |
| agentic_chat | 3 | 2 | 1 fail: LLM substring variation |
| buy_sell | 10 | 0 | not-run: needs `--live-orchestrator` |
| multi_model_comparison | 18 | 0 | not-run: needs `--live-multi` |
| agentic_rag | 10 | 0 | not-run: needs `--live-agentic` |
| **Total** | **111** | **72** | |

## Reproducing

```bash
cd backend
python evaluation/run_batch_eval.py \
  --live-market-data --live-fundamental --live-chat --live-news
# Results written to backend/evaluation/results/batch_eval_<stamp>.{csv,json}
```

Plots (`figures/*.png`) are produced by `plot_model_metrics_bars.py`,
`plot_judge_score_grouped.py`, and `plot_latency_judge_tradeoff.py` — these
require Python 3.10+ and a completed multimodel eval run (see
`run_feature_multimodel_eval.py`).
