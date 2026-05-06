#!/usr/bin/env python3
"""
Batch rubric evaluation scaffold for backend/evaluation/eval_set.json.

Default: static / cheap checks (HTTP status, unit helpers). Optional flags opt into
live yfinance, LLM multi-model runs, and authed fundamental calls.

Run from repo root:
  python backend/evaluation/run_batch_eval.py
  python backend/evaluation/run_batch_eval.py --category fundamental --live-fundamental
  python backend/evaluation/run_batch_eval.py --live-orchestrator --max-cases 2
  python backend/evaluation/run_batch_eval.py --live-multi --max-cases 1
  python backend/evaluation/run_batch_eval.py --live-fundamental
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
import time
from collections import defaultdict
from pathlib import Path
from typing import Any

EVAL_DIR = Path(__file__).resolve().parent
BACKEND_ROOT = EVAL_DIR.parent
REPO_ROOT = BACKEND_ROOT.parent
RESULTS_DIR = EVAL_DIR / "results"


def _ensure_import_path() -> None:
    sys.path.insert(0, str(BACKEND_ROOT))


def _mock_bearer() -> str:
    _ensure_import_path()
    from app.services.auth_service import login

    token, _ = login("eval@stockscope.edu", "class-demo")
    return token


def _run_http_check(client: Any, spec: dict) -> tuple[str, str | None, float]:
    method = (spec.get("method") or "GET").upper()
    path = spec.get("path") or "/"
    params = spec.get("params") or {}
    headers = spec.get("headers") or {}
    body = spec.get("json")
    expected = int(spec.get("expected_status") or 200)
    t0 = time.perf_counter()
    err: str | None = None
    status = "fail"
    try:
        if method == "GET":
            r = client.get(path, params=params, headers=headers)
        elif method == "POST":
            r = client.post(path, params=params, json=body, headers=headers)
        else:
            return "fail", f"unsupported method {method}", (time.perf_counter() - t0) * 1000.0
        if r.status_code == expected:
            status = "pass"
        else:
            err = f"expected {expected} got {r.status_code}: {(r.text or '')[:200]}"
    except Exception as e:  # noqa: BLE001
        err = str(e)[:400]
    ms = (time.perf_counter() - t0) * 1000.0
    return status, err, ms


def _market_movers_extra(client: Any, spec: dict) -> tuple[str, str | None]:
    method = (spec.get("method") or "GET").upper()
    path = spec.get("path") or ""
    if method != "GET" or path != "/api/market-movers":
        return "pass", None
    r = client.get(path, params=spec.get("params") or {})
    if r.status_code != 200:
        return "fail", f"market movers status {r.status_code}"
    try:
        data = r.json()
    except Exception as e:  # noqa: BLE001
        return "fail", f"invalid json {e}"
    for key in ("items", "count", "universe"):
        if key not in data:
            return "fail", f"missing key {key}"
    return "pass", None


def run_batch() -> int:
    _ensure_import_path()

    parser = argparse.ArgumentParser(description="StockScope batch eval scaffold")
    parser.add_argument("--max-cases", type=int, default=0, help="Limit cases after filters (0 = all)")
    parser.add_argument(
        "--category",
        action="append",
        dest="categories",
        metavar="NAME",
        help=(
            "Only run cases with this category (repeatable), e.g. fundamental, auth_protected_routes. "
            "Applied before --max-cases."
        ),
    )
    parser.add_argument("--live-orchestrator", action="store_true", help="Run buy_sell yfinance orchestrator cases")
    parser.add_argument("--live-multi", action="store_true", help="Run multi_model LLM comparison cases (slow)")
    parser.add_argument("--live-agentic", action="store_true", help="Run agentic RAG endpoint cases (slow; uses LLM + tools)")
    parser.add_argument("--live-fundamental", action="store_true", help="Run authed fundamental schema checks (yfinance)")
    parser.add_argument("--live-news", action="store_true", help="Run news sentiment POST cases (network)")
    parser.add_argument(
        "--live-market-data",
        action="store_true",
        help="Run /api/market-movers HTTP cases (may call external market data)",
    )
    parser.add_argument("--no-http", action="store_true", help="Skip FastAPI TestClient cases")
    args = parser.parse_args()

    cases: list[dict] = json.loads((EVAL_DIR / "eval_set.json").read_text(encoding="utf-8"))
    if args.categories:
        allowed = {c.strip().lower() for c in args.categories if c and str(c).strip()}
        cases = [
            row
            for row in cases
            if str(row.get("category") or "").strip().lower() in allowed
        ]
    if args.max_cases and args.max_cases > 0:
        cases = cases[: args.max_cases]

    from fastapi.testclient import TestClient

    from app.main import app

    client = TestClient(app)
    token = _mock_bearer()

    rows_out: list[dict] = []
    latency_by_model: dict[str, list[int]] = defaultdict(list)

    for case in cases:
        cid = case.get("id", "")
        cat = case.get("category", "")
        checks = case.get("checks") or []
        inp = case.get("input") or {}
        cost = case.get("cost", "static")
        status = "pass"
        err: str | None = None
        latency_ms: float | None = None
        notes = ""

        try:
            if "structure_only" in checks:
                notes = "documentation-only case"
                status = "pass"
            elif "manual_or_ci_token" in checks:
                if args.live_fundamental:
                    sym = "AAPL"
                    t0 = time.perf_counter()
                    r = client.get(
                        "/api/analysis/fundamental",
                        params={"ticker": sym},
                        headers={"Authorization": f"Bearer {token}"},
                    )
                    latency_ms = (time.perf_counter() - t0) * 1000.0
                    if r.status_code != 200:
                        status, err = "fail", f"fundamental {r.status_code}"
                    else:
                        data = r.json()
                        for key in ("ticker", "metrics", "verdict"):
                            if key not in data:
                                status, err = "fail", f"missing {key}"
                                break
                else:
                    status = "not_run"
                    notes = "use --live-fundamental"
            elif "chat_intent" in checks:
                from services.chat_service import _detect_intent

                q = str(inp.get("query") or "")
                exp = inp.get("expected_intent")
                got = _detect_intent(q)
                if exp and got != exp:
                    status, err = "fail", f"intent {got} != {exp}"
            elif "safety_financial_advice_flag" in checks:
                from services.chat_service import _is_financial_advice

                q = str(inp.get("query") or "")
                if not _is_financial_advice(q):
                    status, err = "fail", "expected advice-seeking pattern"
            elif "citation_grounding_unit" in checks:
                from app.rag.citation_checker import verify_citation_ids

                ids_ = inp.get("citation_ids") or []
                retr = inp.get("retrieved") or []
                exp_miss = int(inp.get("expected_missing") or 0)
                res = verify_citation_ids([str(x) for x in ids_], list(retr))
                if int(res.get("missing_count") or 0) != exp_miss:
                    status, err = "fail", str(res)
            elif "schema_fundamental_authed" in checks:
                if not args.live_fundamental:
                    status = "not_run"
                    notes = "use --live-fundamental"
                else:
                    sym = str(inp.get("ticker") or "AAPL").upper()
                    t0 = time.perf_counter()
                    r = client.get(
                        "/api/analysis/fundamental",
                        params={"ticker": sym},
                        headers={"Authorization": f"Bearer {token}"},
                    )
                    latency_ms = (time.perf_counter() - t0) * 1000.0
                    if r.status_code != 200:
                        status, err = "fail", f"{r.status_code}"
                    else:
                        data = r.json()
                        for key in ("ticker", "metrics", "verdict", "strengths", "risks"):
                            if key not in data:
                                status, err = "fail", f"missing {key}"
                                break
            elif "buy_sell_orchestrator" in checks:
                if not args.live_orchestrator:
                    status = "not_run"
                    notes = "use --live-orchestrator"
                else:
                    from app.agents.orchestrator import run_buy_sell_with_agents

                    t0 = time.perf_counter()
                    report = run_buy_sell_with_agents(
                        ticker=str(inp.get("ticker", "")).upper(),
                        period="3mo",
                        interval="1d",
                        news_limit=10,
                        include_retrieval=bool(inp.get("include_retrieval", False)),
                        include_llm_review=bool(inp.get("include_llm_review", False)),
                        retrieval_top_k=4,
                        retrieval_max_age_days=None,
                        horizon=str(inp.get("horizon") or "") or None,
                        retrieval_query=str(inp.get("query") or ""),
                        memory_hint=None,
                    )
                    latency_ms = (time.perf_counter() - t0) * 1000.0
                    d = report.model_dump(mode="json")
                    if not d.get("ticker"):
                        status, err = "fail", "no ticker in report"
            elif "multi_model_live" in checks:
                if not args.live_multi:
                    status = "not_run"
                    notes = "use --live-multi"
                else:
                    from app.api.evaluation import _call_single_model
                    from services.ai.prompts import build_multi_model_comparison_prompt

                    task = str(inp.get("task") or "chat")
                    sym = str(inp.get("ticker") or "AAPL").upper()
                    q = str(inp.get("query") or "test")
                    prompt = build_multi_model_comparison_prompt(task=task, ticker=sym, query=q)
                    for mname in ("gemini", "llama", "mistral"):
                        res = _call_single_model(mname, prompt, eval_task=task)
                        latency_by_model[mname].append(res.latency_ms)
                    notes = "see latency_summary"
            elif "agentic_rag_live" in checks:
                if not args.live_agentic:
                    status = "not_run"
                    notes = "use --live-agentic"
                else:
                    _ensure_import_path()
                    from app.memory import apply_eval_memory_seed

                    sid_agentic = str(inp.get("session_id") or "eval")
                    seed = inp.get("memory_seed")
                    if isinstance(seed, dict) and seed:
                        apply_eval_memory_seed(sid_agentic, seed)
                    t0 = time.perf_counter()
                    payload = {
                        "ticker": str(inp.get("ticker") or "AAPL"),
                        "question": str(inp.get("question") or ""),
                        "session_id": sid_agentic,
                        "preferred_model": str(inp.get("preferred_model") or "gemini"),
                        "max_steps": int(inp.get("max_steps") or 3),
                        "require_two_tools": bool(inp.get("require_two_tools", True)),
                        "include_buy_sell": bool(inp.get("include_buy_sell", True)),
                        "include_news": bool(inp.get("include_news", True)),
                        "include_fundamental": bool(inp.get("include_fundamental", True)),
                    }
                    sec = inp.get("secondary_ticker")
                    if sec:
                        payload["secondary_ticker"] = str(sec).strip().upper()
                    r = client.post("/api/agentic-research/run", json=payload)
                    latency_ms = (time.perf_counter() - t0) * 1000.0
                    if r.status_code != 200:
                        status, err = "fail", f"{r.status_code}: {(r.text or '')[:200]}"
                    else:
                        data = r.json()
                        # basic rubric checks: plan, citations, critic
                        if not data.get("plan") or not (data.get("plan") or {}).get("steps"):
                            status, err = "fail", "missing plan.steps"
                        elif payload.get("require_two_tools") and len(
                            {s.get("tool") for s in (data.get("plan") or {}).get("steps", []) if s.get("tool") != "history"}
                        ) < 2:
                            status, err = "fail", "planner_used_fewer_than_two_tools"
                        elif not isinstance(data.get("citations"), list):
                            status, err = "fail", "citations_not_list"
                        elif data.get("critic_passed") is not True:
                            status, err = "fail", f"critic_failed:{data.get('critic_notes')}"
                        else:
                            must_have = inp.get("expect_answer_contains") or []
                            if isinstance(must_have, list) and must_have:
                                ans = (data.get("answer") or "").lower()
                                for sub in must_have:
                                    if str(sub).lower() not in ans:
                                        status, err = "fail", f"answer_missing_substring:{sub!r}"
                                        break
            elif "http" in inp and not args.no_http:
                spec = inp["http"]
                path = spec.get("path") or ""
                if path == "/api/market-movers" and not args.live_market_data:
                    status = "not_run"
                    notes = "use --live-market-data"
                elif "http_status_optional" in checks:
                    st, e, ms = _run_http_check(client, spec)
                    latency_ms = ms
                    if st != "pass":
                        status, err = st, e
                elif "http_status" in checks and "json_non_empty" in checks:
                    if not args.live_news and cost == "network_optional":
                        status = "not_run"
                        notes = "use --live-news"
                    else:
                        st, e, ms = _run_http_check(client, spec)
                        latency_ms = ms
                        if st != "pass":
                            status, err = st, e
                        else:
                            r = client.post(
                                spec["path"],
                                json=spec.get("json"),
                                headers=spec.get("headers") or {},
                            )
                            exp = int(spec.get("expected_status") or 200)
                            if r.status_code != exp:
                                status, err = "fail", f"status {r.status_code}"
                            else:
                                body = r.json()
                                if "ticker" not in body or "aggregate_sentiment" not in body:
                                    status, err = "fail", "missing sentiment keys"
                elif "http_status" in checks:
                    st, e, ms = _run_http_check(client, spec)
                    latency_ms = ms
                    if st != "pass":
                        status, err = st, e
                    elif "json_has_keys" in checks:
                        st2, e2 = _market_movers_extra(client, spec)
                        if st2 != "pass":
                            status, err = st2, e2
            else:
                status = "not_run"
                notes = "no matching runner"
        except Exception as e:  # noqa: BLE001
            status, err = "fail", str(e)[:500]

        rows_out.append(
            {
                "case_id": cid,
                "category": cat,
                "status": status,
                "error": err,
                "latency_ms": round(latency_ms, 2) if latency_ms is not None else None,
                "notes": notes,
                "cost": cost,
            }
        )

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%d-%H%M%S")
    json_path = RESULTS_DIR / f"batch_eval_{stamp}.json"
    summary = {
        "total": len(rows_out),
        "passed": sum(1 for r in rows_out if r["status"] == "pass"),
        "failed": sum(1 for r in rows_out if r["status"] == "fail"),
        "not_run": sum(1 for r in rows_out if r["status"] == "not_run"),
        "latency_summary_ms": {
            m: {
                "count": len(v),
                "mean": round(sum(v) / len(v), 2) if v else None,
                "max": max(v) if v else None,
            }
            for m, v in latency_by_model.items()
        },
        "cases": rows_out,
    }
    json_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    csv_path = RESULTS_DIR / f"batch_eval_{stamp}.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(
            f,
            fieldnames=["case_id", "category", "status", "latency_ms", "error", "notes", "cost"],
        )
        w.writeheader()
        for r in rows_out:
            w.writerow({k: r.get(k) for k in w.fieldnames})

    print(json.dumps(summary, indent=2))
    print(f"Wrote {json_path}", file=sys.stderr)
    print(f"Wrote {csv_path}", file=sys.stderr)

    return 0 if summary["failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(run_batch())
