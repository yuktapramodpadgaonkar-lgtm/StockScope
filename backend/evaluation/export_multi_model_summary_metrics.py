#!/usr/bin/env python3
"""
Export metrics from multi_model_summary_<stamp>.json to CSV (overall + task rows).

Input:
  - multi_model_summary_<stamp>.json (from run_multi_model_comparison_summary.py)

Output:
  - multi_model_metrics_<stamp>.csv in backend/evaluation/results (unless --out is set)
"""

from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
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


def _aggregate_rows(per_run: list[dict[str, Any]]) -> list[dict[str, Any]]:
    # group by (scope, task, model)
    groups: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)

    for r in per_run:
        if not isinstance(r, dict):
            continue
        model = str(r.get("model") or "").strip()
        task = str(r.get("task") or "unknown").strip() or "unknown"
        if not model:
            continue
        groups[("overall", "all", model)].append(r)
        groups[("task", task, model)].append(r)

    out: list[dict[str, Any]] = []
    for (scope, task, model), rows in sorted(groups.items()):
        lat_s = _avg([float((x.get("latency_ms") or 0.0)) for x in rows])
        lat_s = (lat_s / 1000.0) if lat_s is not None else None

        safety_pass = sum(1 for x in rows if bool(x.get("safety_passed")))
        safety_pct = _pct(safety_pass, len(rows))

        avg_citations = _avg([float(x.get("citation_count") or 0.0) for x in rows])

        # count errors as "run errors" (timeouts/503/etc). In JSON: error is string or null.
        err_ct = sum(1 for x in rows if x.get("error"))

        # secondary metrics live under metrics.* (these are already computed by the runner)
        def _mfloat(x: dict[str, Any], key: str) -> float:
            m = x.get("metrics") or {}
            v = m.get(key)
            try:
                return float(v)
            except Exception:
                return 0.0

        grounding_avg = _avg([_mfloat(x, "grounding_score") for x in rows])
        completeness_avg = _avg([_mfloat(x, "completeness_score") for x in rows])

        halluc_rate = _pct(
            sum(1 for x in rows if bool((x.get("metrics") or {}).get("hallucination_flag"))),
            len(rows),
        )

        judge_scores: list[float] = []
        for x in rows:
            js = x.get("judge_score")
            if isinstance(js, (int, float)):
                judge_scores.append(float(js))
        judge_ok_pct = _pct(len(judge_scores), len(rows))
        judge_avg = _avg(judge_scores)

        out.append(
            {
                "scope": scope,
                "task": task,
                "model": model,
                "runs": len(rows),
                "avg_latency_s": _fmt(lat_s, 2),
                "safety_pass_pct": _fmt_pct(safety_pct),
                "avg_citations": _fmt(avg_citations, 2),
                "avg_grounding_score": _fmt(grounding_avg, 3),
                "avg_completeness_score": _fmt(completeness_avg, 3),
                "hallucination_rate_pct": _fmt_pct(halluc_rate),
                "judge_ok_pct": _fmt_pct(judge_ok_pct),
                "avg_judge_1_to_5": _fmt(judge_avg, 2),
                "run_errors": str(err_ct),
            }
        )
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description="Export multi_model_summary JSON to a task-wise metrics CSV")
    parser.add_argument(
        "--summary-json",
        required=True,
        help="Path to multi_model_summary_<stamp>.json",
    )
    parser.add_argument(
        "--out",
        default="",
        help="Optional output CSV path; default is backend/evaluation/results/multi_model_metrics_<stamp>.csv",
    )
    args = parser.parse_args()

    summary_path = Path(args.summary_json)
    payload = _load_json(summary_path)
    per_run = payload.get("per_run") or []
    if not isinstance(per_run, list) or not per_run:
        raise SystemExit("No per_run rows found in summary JSON.")

    stamp = summary_path.stem.replace("multi_model_summary_", "")
    default_out = summary_path.parent / f"multi_model_metrics_{stamp}.csv"
    out_path = Path(args.out) if args.out else default_out
    out_path.parent.mkdir(parents=True, exist_ok=True)

    rows = _aggregate_rows(per_run)

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
        "avg_judge_1_to_5",
        "run_errors",
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

