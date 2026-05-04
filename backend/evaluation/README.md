# Buy/Sell evaluation (Phase 8)

- **`eval_set.json`** — Case list (ticker, optional horizon, flags). Expand toward 50+ cases for course rubrics.
- **`few_shot_examples.json`** — Short exemplars for future prompt tuning or LLM-as-judge baselines.
- **`run_eval.py`** — In-process harness calling `run_buy_sell_with_agents` (use `--inline`). Writes `data/eval/last_eval_run.json` by default.

From the **StockScope** repo root:

```powershell
python backend/evaluation/run_eval.py --inline --max-cases 3
```

Requires outbound access for **yfinance** (and more if you enable retrieval/LLM per case).
