#!/usr/bin/env python3
"""
Run the shared multi-model comparison cases from eval_set.json (same prompt → Gemini, Llama, Mistral).

Prints a markdown-friendly summary table: avg latency, safety pass rate, avg citation count,
optional LLM-as-judge score (Gemini; needs GEMINI_API_KEY).

From repo root:
  python backend/evaluation/run_multi_model_comparison_summary.py --subset core
  python backend/evaluation/run_multi_model_comparison_summary.py --subset full
  python backend/evaluation/run_multi_model_comparison_summary.py --subset full --judge
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

EVAL_DIR = Path(__file__).resolve().parent
BACKEND_ROOT = EVAL_DIR.parent
REPO_ROOT = BACKEND_ROOT.parent
RESULTS_DIR = EVAL_DIR / "results"

CORE_IDS = frozenset(f"rub-{n:03d}" for n in range(54, 61))


def _ensure_paths() -> None:
    sys.path.insert(0, str(BACKEND_ROOT))
    sys.path.insert(0, str(EVAL_DIR))


def _load_cases(subset: str) -> list[dict]:
    raw = json.loads((EVAL_DIR / "eval_set.json").read_text(encoding="utf-8"))
    multi = [c for c in raw if c.get("category") == "multi_model_comparison"]
    if subset == "core":
        multi = [c for c in multi if str(c.get("id")) in CORE_IDS]
    elif subset == "full":
        pass
    else:
        raise ValueError("subset must be 'core' or 'full'")
    multi.sort(key=lambda c: str(c.get("id") or ""))
    return multi


def _fmt_pct(part: int, total: int) -> str:
    if total <= 0:
        return "—"
    return f"{100.0 * part / total:.0f}%"


def _fmt_s(ms: float) -> str:
    return f"{ms / 1000.0:.1f}s"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Aggregate multi-model comparison metrics for rubric reporting",
    )
    parser.add_argument(
        "--subset",
        choices=("core", "full"),
        default="full",
        help=(
            "core = rub-054–rub-060 (7 cases); "
            "full = all multi_model_comparison rows (18 cases: rub-054–060 + rub-076–083 + rub-087–089)"
        ),
    )
    parser.add_argument("--max-cases", type=int, default=0, help="Cap number of cases after filter (0=all)")
    parser.add_argument(
        "--judge",
        action="store_true",
        help="Call Gemini LLM-as-judge per response (slow; needs GEMINI_API_KEY)",
    )
    parser.add_argument("--out-json", default="", help="Write raw per-run + aggregates to this path")
    args = parser.parse_args()

    _ensure_paths()
    from app.api.evaluation import _call_single_model  # noqa: PLC0415
    from services.ai.prompts import build_multi_model_comparison_prompt  # noqa: PLC0415

    cases = _load_cases(args.subset)
    if args.max_cases > 0:
        cases = cases[: args.max_cases]

    if not cases:
        print("No cases matched.", file=sys.stderr)
        return 2

    models = ("gemini", "llama", "mistral")
    stats: dict[str, dict] = {
        m: {
            "latencies": [],
            "safety_hits": 0,
            "safety_total": 0,
            "citations": [],
            "judge_scores": [],
            "judge_clarity": [],
            "judge_correctness": [],
            "judge_grounding": [],
            "errors": 0,
        }
        for m in models
    }
    detail: list[dict] = []

    for case in cases:
        cid = str(case.get("id") or "")
        inp = case.get("input") or {}
        task = str(inp.get("task") or "chat")
        sym = str(inp.get("ticker") or "AAPL").strip().upper()
        q = str(inp.get("query") or "Summarize for a student project")
        expected = str(case.get("expected_behavior") or "")
        prompt = build_multi_model_comparison_prompt(task=task, ticker=sym, query=q)

        for mname in models:
            res = _call_single_model(mname, prompt, eval_task=task)
            st = stats[mname]
            st["latencies"].append(res.latency_ms)
            st["safety_total"] += 1
            if res.safety_passed:
                st["safety_hits"] += 1
            st["citations"].append(res.citation_count)
            if res.error:
                st["errors"] += 1

            judge_score = None
            judge_reason = None
            judge_detail = None
            if args.judge and res.response and not res.error:
                from score_outputs import _llm_judge  # noqa: PLC0415

                j = _llm_judge(
                    expected_behavior=expected or "Educational, safe, on-topic response.",
                    response_text=res.response,
                    model_label=mname,
                )
                judge_detail = j
                # Prefer judge_score (mean of subscores), fallback to legacy score.
                judge_score = j.get("judge_score")
                if not isinstance(judge_score, (int, float)):
                    judge_score = j.get("score")
                judge_reason = j.get("reason")

                if isinstance(judge_score, (int, float)):
                    st["judge_scores"].append(float(judge_score))
                for key, bucket in (
                    ("clarity", "judge_clarity"),
                    ("correctness", "judge_correctness"),
                    ("grounding", "judge_grounding"),
                ):
                    v = j.get(key)
                    if isinstance(v, (int, float)):
                        st[bucket].append(float(v))

            detail.append(
                {
                    "case_id": cid,
                    "model": mname,
                    "task": task,
                    "ticker": sym,
                    "latency_ms": res.latency_ms,
                    "safety_passed": res.safety_passed,
                    "citation_count": res.citation_count,
                    "error": res.error,
                    "metrics": res.metrics,
                    "judge_score": judge_score,
                    "judge_reason": judge_reason,
                    "judge_detail": judge_detail,
                }
            )

    rows = []
    for mname in models:
        st = stats[mname]
        n_lat = len(st["latencies"])
        avg_lat = sum(st["latencies"]) / n_lat if n_lat else 0.0
        safety_pct = _fmt_pct(st["safety_hits"], st["safety_total"])
        avg_cit = sum(st["citations"]) / len(st["citations"]) if st["citations"] else 0.0
        jscores = st["judge_scores"]
        avg_j = sum(jscores) / len(jscores) if jscores else None
        jclar = st["judge_clarity"]
        jcorr = st["judge_correctness"]
        jgnd = st["judge_grounding"]
        avg_jclar = sum(jclar) / len(jclar) if jclar else None
        avg_jcorr = sum(jcorr) / len(jcorr) if jcorr else None
        avg_jgnd = sum(jgnd) / len(jgnd) if jgnd else None
        err_note = f"{st['errors']} run errors" if st["errors"] else ""
        rows.append(
            {
                "model": mname.capitalize(),
                "avg_latency_s": round(avg_lat / 1000.0, 2),
                "safety_pass_pct": safety_pct,
                "avg_citations": round(avg_cit, 2),
                "avg_judge_1_to_5": round(avg_j, 2) if avg_j is not None else None,
                "avg_judge_clarity": round(avg_jclar, 2) if avg_jclar is not None else None,
                "avg_judge_correctness": round(avg_jcorr, 2) if avg_jcorr is not None else None,
                "avg_judge_grounding": round(avg_jgnd, 2) if avg_jgnd is not None else None,
                "notes": err_note,
            }
        )

    stamp = time.strftime("%Y%m%d-%H%M%S")
    out_payload = {
        "subset": args.subset,
        "case_ids": [str(c.get("id")) for c in cases],
        "case_count": len(cases),
        "judge_enabled": args.judge,
        "per_run": detail,
        "summary_rows": rows,
    }

    if args.out_json:
        Path(args.out_json).write_text(json.dumps(out_payload, indent=2), encoding="utf-8")
    else:
        RESULTS_DIR.mkdir(parents=True, exist_ok=True)
        default_path = RESULTS_DIR / f"multi_model_summary_{stamp}.json"
        default_path.write_text(json.dumps(out_payload, indent=2), encoding="utf-8")
        print(f"Wrote {default_path}", file=sys.stderr)

    # Markdown table (paste into report)
    headers = ["Model", "Avg latency", "Safety pass", "Avg citations"]
    if args.judge:
        headers.append("Avg judge (1–5)")
    headers.append("Notes")

    sep = ["---"] * len(headers)
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(sep) + " |",
    ]
    for r in rows:
        cells = [
            r["model"],
            _fmt_s(r["avg_latency_s"] * 1000),
            r["safety_pass_pct"],
            str(r["avg_citations"]),
        ]
        if args.judge:
            cells.append(str(r["avg_judge_1_to_5"]) if r["avg_judge_1_to_5"] is not None else "—")
        cells.append(r["notes"] or "—")
        lines.append("| " + " | ".join(cells) + " |")

    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
