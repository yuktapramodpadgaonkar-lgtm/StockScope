#!/usr/bin/env python3
"""
Phase 8 — smoke eval harness for Buy/Sell analyze pipeline.

Run from repo root (StockScope):
  python backend/evaluation/run_eval.py --inline --max-cases 3

Requires network for yfinance unless you mock later. Default cases use include_retrieval=false
to reduce flakiness in CI / classrooms.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
BACKEND = ROOT / "backend"
EVAL_DIR = Path(__file__).resolve().parent


def _ensure_path() -> None:
    sys.path.insert(0, str(BACKEND))


def main() -> int:
    _ensure_path()

    parser = argparse.ArgumentParser(description="StockScope Buy/Sell eval runner")
    parser.add_argument("--inline", action="store_true", help="Run orchestrator in-process")
    parser.add_argument("--max-cases", type=int, default=0, help="Limit cases (0 = all)")
    parser.add_argument("--out", type=str, default="", help="Write JSON results to this path")
    args = parser.parse_args()

    if not args.inline:
        print("Use --inline for the in-process harness (HTTP mode not implemented in v1).")
        return 2

    from app.agents.orchestrator import run_buy_sell_with_agents
    from app.evaluation.metrics import score_report_dict

    cases = json.loads((EVAL_DIR / "eval_set.json").read_text(encoding="utf-8"))
    if args.max_cases and args.max_cases > 0:
        cases = cases[: args.max_cases]

    results: list[dict] = []
    for row in cases:
        cid = row.get("id")
        ticker = str(row.get("ticker") or "").upper()
        t0 = time.perf_counter()
        err = None
        rep: dict | None = None
        try:
            report = run_buy_sell_with_agents(
                ticker=ticker,
                period="3mo",
                interval="1d",
                news_limit=10,
                include_retrieval=bool(row.get("include_retrieval", False)),
                include_llm_review=bool(row.get("include_llm_review", False)),
                retrieval_top_k=4,
                retrieval_max_age_days=None,
                horizon=str(row.get("horizon") or "") or None,
                retrieval_query=str(row.get("query") or f"thesis for {ticker}"),
                memory_hint=None,
            )
            rep = report.model_dump(mode="json")
        except Exception as e:
            err = str(e)[:500]
        ms = (time.perf_counter() - t0) * 1000.0
        m = score_report_dict(rep or {})
        results.append(
            {
                "case_id": cid,
                "ticker": ticker,
                "ok": err is None,
                "error": err,
                "latency_ms": round(ms, 2),
                "metrics": m if err is None else {},
            }
        )

    summary = {
        "total": len(results),
        "passed": sum(1 for r in results if r["ok"]),
        "failed": sum(1 for r in results if not r["ok"]),
        "cases": results,
    }
    print(json.dumps(summary, indent=2))

    out_path = args.out.strip()
    if not out_path:
        out_dir = ROOT / "data" / "eval"
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = str(out_dir / "last_eval_run.json")
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    Path(out_path).write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"Wrote: {out_path}", file=sys.stderr)

    return 0 if summary["failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
