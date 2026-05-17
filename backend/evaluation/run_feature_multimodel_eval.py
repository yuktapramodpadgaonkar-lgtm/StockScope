#!/usr/bin/env python3
"""
Run Gemini + Ollama Llama + Ollama Mistral on core eval categories using the
same JSON comparison prompt template as compare-models (`build_multi_model_comparison_prompt`).

Each eval case is mapped to (prompt_task, ticker, query) so all three models see identical prompts.
Then: capture → score_saved_runs (heuristic metrics + optional per-response judge) → Markdown report.

Uses up to 10 cases per category from eval_set.json (categories: buy_sell, fundamental,
news_sentiment, agentic_rag, chatbot).

From repo root:
  python backend/evaluation/run_feature_multimodel_eval.py --judge
  python backend/evaluation/export_metrics_csv.py --stamp <stamp>
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path

EVAL_DIR = Path(__file__).resolve().parent
BACKEND_ROOT = EVAL_DIR.parent
RESULTS_DIR = EVAL_DIR / "results"

FEATURE_CATEGORIES = (
    "buy_sell",
    "fundamental",
    "news_sentiment",
    "agentic_rag",
    "chatbot",
)

_CHAT_TICKER_PAT = re.compile(
    r"\b(AAPL|MSFT|GOOG|GOOGL|NVDA|TSLA|AMD|AMZN|META|JPM|SPY|XOM)\b",
    re.IGNORECASE,
)


def _ensure_paths() -> None:
    sys.path.insert(0, str(BACKEND_ROOT))
    sys.path.insert(0, str(EVAL_DIR))


def _ticker_from_chat_input(inp: dict) -> str:
    explicit = str(inp.get("ticker") or "").strip().upper()
    if explicit:
        return explicit
    q = str(inp.get("query") or "")
    m = _CHAT_TICKER_PAT.search(q)
    if m:
        return m.group(1).upper()
    return "AAPL"


def _mapping_for_case(case: dict) -> tuple[str, str, str, str, str]:
    """
    Returns (feature_category, metrics_task, prompt_task, ticker, query).

    feature_category groups CSV rows (buy_sell, fundamental, news_sentiment, agentic_rag, chatbot).
    metrics_task drives heuristic completeness keywords; prompt_task selects multi-model task hints.
    """
    cat = str(case.get("category") or "")
    inp = case.get("input") or {}

    if cat == "buy_sell":
        sym = str(inp.get("ticker") or "AAPL").strip().upper()
        q = str(inp.get("query") or f"Educational discussion of risk factors and signals for {sym}.")
        return cat, "buy_sell", "buy_sell", sym, q

    if cat == "fundamental":
        sym = str(inp.get("ticker") or "AAPL").strip().upper()
        q = str(
            inp.get("query")
            or "Summarize profitability, growth, balance sheet health, and key risks for educational context."
        )
        return cat, "fundamental", "fundamental", sym, q

    if cat == "news_sentiment":
        http = inp.get("http") or {}
        body = http.get("json") or {}
        sym = str(body.get("ticker") or "AAPL").strip().upper()
        q = str(
            inp.get("query")
            or "Summarize recent news sentiment, tone, and key themes for educational analysis."
        )
        return cat, "sentiment", "sentiment", sym, q

    if cat == "agentic_rag":
        sym = str(inp.get("ticker") or "AAPL").strip().upper()
        q = str(
            inp.get("question")
            or "Provide an educational overview of catalysts and risks using cautious language."
        )
        return cat, "chat", "chat", sym, q

    if cat == "chatbot":
        sym = _ticker_from_chat_input(inp)
        q = str(inp.get("query") or f"Educational overview for {sym}.")
        return cat, "chat", "chat", sym, q

    raise ValueError(f"unsupported category: {cat}")


def _load_cases(eval_path: Path, max_per: int) -> list[dict]:
    raw = json.loads(eval_path.read_text(encoding="utf-8"))
    out: list[dict] = []
    for c in FEATURE_CATEGORIES:
        rows = [r for r in raw if r.get("category") == c]
        rows.sort(key=lambda x: str(x.get("id") or ""))
        out.extend(rows[:max_per])
    return out


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Multi-model comparison metrics for buy/sell, fundamental, news, agentic, chatbot (eval_set)"
    )
    parser.add_argument(
        "--eval-set",
        default=str(EVAL_DIR / "eval_set.json"),
        help="Path to eval_set.json",
    )
    parser.add_argument(
        "--max-per-category",
        type=int,
        default=10,
        help="Max cases per feature category (default 10)",
    )
    parser.add_argument(
        "--judge",
        action="store_true",
        help="Run Gemini LLM-as-judge per response (needs GEMINI_API_KEY)",
    )
    parser.add_argument(
        "--out-dir",
        default=str(RESULTS_DIR),
        help="Directory for captured responses, scoring JSON, report",
    )
    args = parser.parse_args()

    _ensure_paths()
    from app.api.evaluation import _call_single_model  # noqa: PLC0415
    from score_outputs import score_saved_runs  # noqa: PLC0415
    from services.ai.prompts import build_multi_model_comparison_prompt  # noqa: PLC0415

    eval_path = Path(args.eval_set)
    cases = _load_cases(eval_path, args.max_per_category)
    if not cases:
        print("No cases matched categories / limits.", file=sys.stderr)
        return 2

    models = ("gemini", "llama", "mistral")
    runs: list[dict] = []
    meta_runs: list[dict] = []

    for case in cases:
        cid = str(case.get("id") or "")
        feature_cat, metrics_task, prompt_task, sym, q = _mapping_for_case(case)
        expected = str(case.get("expected_behavior") or "")
        prompt = build_multi_model_comparison_prompt(task=prompt_task, ticker=sym, query=q)

        for mname in models:
            res = _call_single_model(mname, prompt, eval_task=metrics_task)
            runs.append(
                {
                    "case_id": cid,
                    "model": mname,
                    "response_text": res.response or "",
                    "latency_ms": res.latency_ms,
                    "error": res.error,
                    "expected_behavior": expected,
                    "task": metrics_task,
                    "reference_prompt": prompt,
                    "metrics": res.metrics,
                }
            )
            meta_runs.append(
                {
                    "case_id": cid,
                    "feature": feature_cat,
                    "task": metrics_task,
                    "model": mname,
                    "ticker": sym,
                    "query": q[:200],
                }
            )

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%d-%H%M%S")
    responses_path = out_dir / f"captured_responses_{stamp}.json"
    bundle_path = out_dir / f"captured_bundle_{stamp}.json"
    scoring_path = out_dir / f"scoring_{stamp}.json"
    report_path = out_dir / f"eval_report_{stamp}.md"

    responses_path.write_text(json.dumps(runs, indent=2), encoding="utf-8")
    bundle_path.write_text(
        json.dumps(
            {
                "stamp": stamp,
                "mode": "feature_multimodel",
                "categories": list(FEATURE_CATEGORIES),
                "max_per_category": args.max_per_category,
                "case_ids": [str(c.get("id")) for c in cases],
                "runs": meta_runs,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"Wrote {responses_path}", file=sys.stderr)
    print(f"Wrote {bundle_path}", file=sys.stderr)

    scoring_doc = score_saved_runs(runs, eval_set_path=str(eval_path), judge=args.judge)
    scoring_path.write_text(json.dumps(scoring_doc, indent=2), encoding="utf-8")
    print(f"Wrote {scoring_path}", file=sys.stderr)

    summ = scoring_doc.get("summary_by_model") or {}
    lines = [
        f"# Feature multi-model eval — `{stamp}`",
        "",
        f"- **Categories:** {', '.join(FEATURE_CATEGORIES)}",
        f"- **Cases:** {len(cases)} × 3 models = {len(runs)} runs",
        f"- **Judge:** {'on' if args.judge else 'off'}",
        "",
        "## Summary by model",
        "",
        "| Model | Runs | Avg latency (ms) | Avg judge (1–5) | Avg grounding | Avg completeness | Halluc. rate |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for key in sorted(summ.keys()):
        s = summ[key]
        aj = s.get("avg_judge_score_1_to_5")
        lines.append(
            "| {model} | {tc} | {lat} | {judge} | {g} | {c} | {h} |".format(
                model=key,
                tc=s.get("total_cases", ""),
                lat=s.get("avg_latency_ms", "—"),
                judge=aj if aj is not None else "—",
                g=s.get("avg_grounding_score", "—"),
                c=s.get("avg_completeness_score", "—"),
                h=s.get("hallucination_rate", "—"),
            )
        )
    lines.extend(
        [
            "",
            "## Next step — metrics CSV (overall + per feature)",
            "",
            f"```bash",
            f"python backend/evaluation/export_metrics_csv.py --stamp {stamp}",
            f"```",
            "",
        ]
    )
    report_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {report_path}", file=sys.stderr)
    print(f"STAMP={stamp}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
