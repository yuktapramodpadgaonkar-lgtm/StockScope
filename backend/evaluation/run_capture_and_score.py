#!/usr/bin/env python3
"""
Capture multi-model LLM outputs into responses.json, run score_outputs scoring, write a short Markdown report.

1) Runs each multi_model_comparison case through Gemini, Llama, Mistral (same as compare-models).
2) Writes a responses list compatible with score_outputs.py (18 multi-model cases when using --subset full).
3) Calls score_saved_runs() for rule checks + optional LLM judge.
4) Writes eval_report_<stamp>.md with summary tables.

From repo root:
  python backend/evaluation/run_capture_and_score.py --subset core
  python backend/evaluation/run_capture_and_score.py --subset full --judge
  python backend/evaluation/run_capture_and_score.py --capture-only --subset full
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

EVAL_DIR = Path(__file__).resolve().parent
BACKEND_ROOT = EVAL_DIR.parent
RESULTS_DIR = EVAL_DIR / "results"

CORE_IDS = frozenset(f"rub-{n:03d}" for n in range(54, 61))


def _ensure_paths() -> None:
    sys.path.insert(0, str(BACKEND_ROOT))
    sys.path.insert(0, str(EVAL_DIR))


def _load_multi_cases(subset: str) -> list[dict]:
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


def _markdown_table(headers: list[str], rows: list[list[str]]) -> str:
    sep = ["---"] * len(headers)
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join(sep) + " |"]
    for r in rows:
        lines.append("| " + " | ".join(r) + " |")
    return "\n".join(lines)


def _build_report_md(
    *,
    stamp: str,
    subset: str,
    case_ids: list[str],
    responses_path: Path,
    scoring_path: Path | None,
    scoring_doc: dict | None,
) -> str:
    lines = [
        f"# StockScope evaluation capture — `{stamp}`",
        "",
        f"- **Subset:** {subset}",
        f"- **Cases:** {len(case_ids)} (`{case_ids[0]}` … `{case_ids[-1]}`)" if case_ids else "- **Cases:** 0",
        f"- **Responses:** `{responses_path}`",
    ]
    if scoring_path and scoring_doc:
        lines.append(f"- **Scoring JSON:** `{scoring_path}`")
        judge_on = bool(scoring_doc.get("judge_enabled"))
        lines.append(f"- **LLM judge:** {'yes' if judge_on else 'no'}")
        lines.append("")
        lines.append("## Summary by model")
        lines.append("")
        summ = scoring_doc.get("summary_by_model") or {}
        headers = [
            "Model",
            "Runs",
            "Rule pass rate",
            "Avg latency (ms)",
            "Error rate",
            "Judge (pass / fail)",
            "Avg judge (1–5)",
        ]
        table_rows: list[list[str]] = []
        for key in sorted(summ.keys()):
            s = summ[key]
            jp, jf = int(s.get("judge_passed") or 0), int(s.get("judge_failed") or 0)
            if judge_on and (jp or jf):
                judge_cell = f"{jp} / {jf}"
            elif judge_on:
                judge_cell = "0 / 0"
            else:
                judge_cell = "—"
            aj = s.get("avg_judge_score_1_to_5")
            table_rows.append(
                [
                    str(s.get("model", key)),
                    str(s.get("total_cases", "")),
                    str(s.get("rule_pass_rate", "—")),
                    str(s.get("avg_latency_ms", "—")),
                    str(s.get("error_rate", "—")),
                    judge_cell,
                    str(aj if aj is not None else "—"),
                ]
            )
        lines.append(_markdown_table(headers, table_rows))
        lines.append("")
        lines.append("## Heuristic metrics (avg per model)")
        lines.append("")
        h2 = ["Model", "Avg grounding", "Avg completeness", "Avg words", "Halluc. rate"]
        r2: list[list[str]] = []
        for key in sorted(summ.keys()):
            s = summ[key]
            r2.append(
                [
                    str(s.get("model", key)),
                    str(s.get("avg_grounding_score", "—")),
                    str(s.get("avg_completeness_score", "—")),
                    str(s.get("avg_word_count", "—")),
                    str(s.get("hallucination_rate", "—")),
                ]
            )
        lines.append(_markdown_table(h2, r2))
    else:
        lines.append("")
        lines.append("*Scoring skipped (`--capture-only` or error).*")
    lines.append("")
    lines.append("## Notes")
    lines.append("")
    lines.append("- Rule checks apply only when `eval_set.json` rows include `score_checks` for that case.")
    lines.append("- LLM judge requires `GEMINI_API_KEY` and `--judge`.")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Capture model outputs → score → Markdown report")
    parser.add_argument("--subset", choices=("core", "full"), default="full")
    parser.add_argument("--max-cases", type=int, default=0)
    parser.add_argument("--judge", action="store_true", help="Run Gemini LLM-as-judge during scoring")
    parser.add_argument(
        "--capture-only",
        action="store_true",
        help="Only write responses JSON (no scoring / no report)",
    )
    parser.add_argument(
        "--eval-set",
        default=str(EVAL_DIR / "eval_set.json"),
        help="Path to eval_set.json for scoring merge",
    )
    parser.add_argument(
        "--out-dir",
        default=str(RESULTS_DIR),
        help="Directory for responses, scoring, and report",
    )
    args = parser.parse_args()

    _ensure_paths()
    from app.api.evaluation import _call_single_model  # noqa: PLC0415
    from score_outputs import score_saved_runs  # noqa: PLC0415
    from services.ai.prompts import build_multi_model_comparison_prompt  # noqa: PLC0415

    cases = _load_multi_cases(args.subset)
    if args.max_cases > 0:
        cases = cases[: args.max_cases]
    if not cases:
        print("No cases matched.", file=sys.stderr)
        return 2

    models = ("gemini", "llama", "mistral")
    runs: list[dict] = []
    meta_runs: list[dict] = []

    for case in cases:
        cid = str(case.get("id") or "")
        inp = case.get("input") or {}
        task = str(inp.get("task") or "chat")
        sym = str(inp.get("ticker") or "AAPL").strip().upper()
        q = str(inp.get("query") or "Summarize for a student project")
        expected = str(case.get("expected_behavior") or "")
        score_checks = case.get("score_checks")
        score_meta = case.get("score_meta")
        prompt = build_multi_model_comparison_prompt(task=task, ticker=sym, query=q)

        for mname in models:
            res = _call_single_model(mname, prompt, eval_task=task)
            row = {
                "case_id": cid,
                "model": mname,
                "response_text": res.response or "",
                "latency_ms": res.latency_ms,
                "error": res.error,
                "expected_behavior": expected,
                "task": task,
                "reference_prompt": prompt,
                "metrics": res.metrics,
            }
            if isinstance(score_checks, list) and score_checks:
                row["score_checks"] = score_checks
            if isinstance(score_meta, dict) and score_meta:
                row["score_meta"] = score_meta
            runs.append(row)
            meta_runs.append(
                {
                    **row,
                    "task": task,
                    "ticker": sym,
                    "query": q[:200],
                    "safety_passed": getattr(res, "safety_passed", None),
                    "citation_count": getattr(res, "citation_count", None),
                }
            )

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%d-%H%M%S")
    responses_path = out_dir / f"captured_responses_{stamp}.json"
    bundle_path = out_dir / f"captured_bundle_{stamp}.json"
    scoring_path: Path | None = None
    report_path = out_dir / f"eval_report_{stamp}.md"

    responses_path.write_text(json.dumps(runs, indent=2), encoding="utf-8")
    bundle_path.write_text(
        json.dumps(
            {
                "stamp": stamp,
                "subset": args.subset,
                "case_ids": [str(c.get("id")) for c in cases],
                "runs": meta_runs,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"Wrote {responses_path}", file=sys.stderr)
    print(f"Wrote {bundle_path}", file=sys.stderr)

    scoring_doc = None
    if not args.capture_only:
        scoring_path = out_dir / f"scoring_{stamp}.json"
        scoring_doc = score_saved_runs(runs, eval_set_path=args.eval_set, judge=args.judge)
        scoring_path.write_text(json.dumps(scoring_doc, indent=2), encoding="utf-8")
        print(f"Wrote {scoring_path}", file=sys.stderr)

    report_md = _build_report_md(
        stamp=stamp,
        subset=args.subset,
        case_ids=[str(c.get("id")) for c in cases],
        responses_path=responses_path,
        scoring_path=scoring_path,
        scoring_doc=scoring_doc,
    )
    report_path.write_text(report_md, encoding="utf-8")
    print(f"Wrote {report_path}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
