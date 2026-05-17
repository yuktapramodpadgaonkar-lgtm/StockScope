#!/usr/bin/env python3
"""
Export multi-model evaluation metrics to a single CSV.

Input:
  - scoring_<stamp>.json (from run_capture_and_score.py / score_outputs.py)
  - captured_bundle_<stamp>.json (from run_capture_and_score.py; contains per-run task labels)

Output:
  - metrics_<stamp>.csv with BOTH overall and task-scoped rows.
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any


def _avg(xs: list[float]) -> float | None:
    return (sum(xs) / len(xs)) if xs else None


def _pct(num: int, den: int) -> float | None:
    return (100.0 * num / den) if den else None


def _fmt(v: float | None, nd: int = 3) -> str:
    if v is None:
        return ""
    return f"{v:.{nd}f}"


def _fmt_pct(v: float | None) -> str:
    if v is None:
        return ""
    return f"{v:.0f}"


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _case_task_map(bundle: dict[str, Any]) -> dict[str, str]:
    """
    captured_bundle_<stamp>.json shape:
      { stamp, subset, case_ids, runs:[{case_id, task, ...}, ...] }

    Prefer `feature` (feature_multimodel_eval) so rows aggregate by eval category
    (buy_sell, fundamental, news_sentiment, agentic_rag); fall back to `task`.
    """
    out: dict[str, str] = {}
    for r in bundle.get("runs") or []:
        if not isinstance(r, dict):
            continue
        cid = str(r.get("case_id") or "").strip()
        if not cid or cid in out:
            continue
        label = r.get("feature") or r.get("task") or "unknown"
        out[cid] = str(label)
    return out


def _aggregate_rows(
    details: list[dict[str, Any]],
    *,
    case_to_task: dict[str, str],
) -> list[dict[str, Any]]:
    # group by (scope, task, model)
    groups: dict[tuple[str, str, str], list[dict[str, Any]]] = {}
    for r in details:
        cid = str(r.get("case_id") or "")
        model = str(r.get("model") or "")
        task = case_to_task.get(cid, "unknown")
        # two scopes: overall + task
        groups.setdefault(("overall", "all", model), []).append(r)
        groups.setdefault(("task", task, model), []).append(r)

    out_rows: list[dict[str, Any]] = []
    for (scope, task, model), rows in sorted(groups.items()):
        # metrics
        lat_s = _avg([float(x["metrics"].get("latency_ms") or 0.0) for x in rows]) / 1000.0
        safety_pass_pct = _pct(sum(1 for x in rows if (x["metrics"]["safety"] or {}).get("passed")), len(rows))
        citations_avg = _avg([float(x["metrics"].get("citation_count") or 0.0) for x in rows])
        grounding_avg = _avg([float(x["metrics"].get("grounding_score") or 0.0) for x in rows])
        completeness_avg = _avg([float(x["metrics"].get("completeness_score") or 0.0) for x in rows])
        halluc_rate = _pct(sum(1 for x in rows if x["metrics"].get("hallucination_flag")), len(rows))

        # judge aggregates (only successful judge rows)
        judge_ok = [
            x
            for x in rows
            if isinstance(x.get("judge"), dict) and not x["judge"].get("judge_error")
        ]
        judge_ok_pct = _pct(len(judge_ok), len(rows))

        def _judge_nums(key: str) -> list[float]:
            vals: list[float] = []
            for x in judge_ok:
                v = x["judge"].get(key)
                if isinstance(v, (int, float)):
                    vals.append(float(v))
            return vals

        judge_overall = _avg(_judge_nums("judge_score"))
        judge_clarity = _avg(_judge_nums("clarity"))
        judge_correctness = _avg(_judge_nums("correctness"))
        judge_grounding = _avg(_judge_nums("grounding"))

        out_rows.append(
            {
                "scope": scope,
                "task": task,
                "model": model,
                "runs": len(rows),
                "avg_latency_s": _fmt(lat_s, 1),
                "safety_pass_pct": _fmt_pct(safety_pass_pct),
                "avg_citations": _fmt(citations_avg, 2),
                "avg_grounding_score": _fmt(grounding_avg, 3),
                "avg_completeness_score": _fmt(completeness_avg, 3),
                "hallucination_rate_pct": _fmt_pct(halluc_rate),
                "judge_ok_pct": _fmt_pct(judge_ok_pct),
                "judge_overall": _fmt(judge_overall, 2),
                "judge_clarity": _fmt(judge_clarity, 2),
                "judge_correctness": _fmt(judge_correctness, 2),
                "judge_grounding": _fmt(judge_grounding, 2),
            }
        )
    return out_rows


def main() -> int:
    parser = argparse.ArgumentParser(description="Export scoring + bundle to a single metrics CSV")
    parser.add_argument("--stamp", required=True, help="Run stamp like 20260507-022621")
    parser.add_argument(
        "--results-dir",
        default=str(Path(__file__).resolve().parent / "results"),
        help="backend/evaluation/results directory",
    )
    parser.add_argument("--out", default="", help="Optional output CSV path; default metrics_<stamp>.csv")
    args = parser.parse_args()

    results_dir = Path(args.results_dir)
    scoring_path = results_dir / f"scoring_{args.stamp}.json"
    bundle_path = results_dir / f"captured_bundle_{args.stamp}.json"

    if not scoring_path.exists():
        raise SystemExit(f"Missing scoring JSON: {scoring_path}")
    if not bundle_path.exists():
        raise SystemExit(f"Missing captured bundle JSON: {bundle_path}")

    scoring = _load_json(scoring_path)
    bundle = _load_json(bundle_path)

    details = scoring.get("details") or []
    if not isinstance(details, list) or not details:
        raise SystemExit("No scoring details found; did the run complete?")

    case_to_task = _case_task_map(bundle if isinstance(bundle, dict) else {})
    rows = _aggregate_rows(details, case_to_task=case_to_task)

    out_path = Path(args.out) if args.out else (results_dir / f"metrics_{args.stamp}.csv")
    out_path.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "scope",
        "task",
        "model",
        "runs",
        "avg_latency_s",
        "safety_pass_pct",
        "avg_citations",
        "avg_grounding_score",
        "avg_completeness_score",
        "hallucination_rate_pct",
        "judge_ok_pct",
        "judge_overall",
        "judge_clarity",
        "judge_correctness",
        "judge_grounding",
    ]
    with out_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in fieldnames})

    print(f"Wrote {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

