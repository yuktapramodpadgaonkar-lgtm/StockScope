from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Callable

from app.rag import ingest_filings_chunks, ingest_news_chunks, retrieve_chunks
from app.rag.embedding_index import sync_embeddings_for_ticker
from app.rag.store import load_chunks
from app.schemas.buy_sell_analysis import BuySellReport, PipelineStepTrace
from app.services.buy_sell_scoring import build_buy_sell_report_from_layer1
from app.observability.jsonl_audit import log_tool_call
from app.tools import get_layer1_for_llm


@dataclass
class ExecutionResult:
    bundle: dict[str, Any]
    retrieved: list[dict[str, Any]]
    report: BuySellReport
    steps: list[PipelineStepTrace]


def _run_step(
    step_id: str,
    description: str,
    fn: Callable[[], Any],
) -> tuple[Any, PipelineStepTrace]:
    t0 = time.perf_counter()
    try:
        out = fn()
        ms = (time.perf_counter() - t0) * 1000.0
        trace = PipelineStepTrace(
            step_id=step_id,
            description=description,
            status="ok",
            duration_ms=round(ms, 2),
            detail=None,
        )
        out_sum = type(out).__name__
        if isinstance(out, dict):
            out_sum = f"dict(keys={list(out.keys())[:8]})"
        elif isinstance(out, list):
            out_sum = f"list(len={len(out)})"
        log_tool_call(
            tool_name=step_id,
            input_summary=description,
            output_summary=out_sum,
            latency_ms=trace.duration_ms,
            error=None,
        )
        return out, trace
    except Exception as e:
        ms = (time.perf_counter() - t0) * 1000.0
        trace = PipelineStepTrace(
            step_id=step_id,
            description=description,
            status="error",
            duration_ms=round(ms, 2),
            detail=str(e)[:500],
        )
        log_tool_call(
            tool_name=step_id,
            input_summary=description,
            output_summary="error",
            latency_ms=trace.duration_ms,
            error=trace.detail,
        )
        return None, trace


def execute_buy_sell_pipeline(
    *,
    ticker: str,
    period: str,
    interval: str,
    news_limit: int,
    include_retrieval: bool,
    include_llm_review: bool,
    retrieval_top_k: int,
    retrieval_max_age_days: int | None,
    retrieval_query: str | None = None,
) -> ExecutionResult:
    """
    Run Layer1 → optional RAG → report. Records per-step timing for the agent trace.
    """
    sym = ticker.strip().upper()
    q = (retrieval_query or "").strip() or (
        f"buy sell investment thesis risks catalysts for {sym}"
    )

    trace: list[PipelineStepTrace] = []

    bundle, st = _run_step(
        "layer1_bundle",
        "Load Layer 1 data bundle",
        lambda: get_layer1_for_llm(
            ticker,
            period=period,
            interval=interval,
            news_limit=news_limit,
        ),
    )
    trace.append(st)
    if st.status == "error" or bundle is None:
        raise RuntimeError(st.detail or "layer1_bundle failed")

    retrieved: list[dict[str, Any]] = []
    if include_retrieval:

        def _ingest_all() -> dict[str, Any]:
            return {
                "news": ingest_news_chunks(ticker, bundle),
                "filings": ingest_filings_chunks(ticker, bundle),
            }

        _, st_in = _run_step(
            "rag_ingest",
            "Ingest news and filing rows into RAG store",
            _ingest_all,
        )
        trace.append(st_in)

        def _embed() -> dict[str, Any]:
            rows = [c for c in load_chunks() if str(c.get("ticker") or "").upper() == sym]
            return sync_embeddings_for_ticker(sym, rows)

        emb, st_e = _run_step("rag_embed_sync", "Sync embedding index for ticker", _embed)
        if isinstance(emb, dict) and emb.get("detail"):
            st_e = st_e.model_copy(
                update={"detail": str(emb.get("detail"))[:500]},
            )
        elif isinstance(emb, dict) and emb.get("reason") in ("embed_failed", "missing_hf_token"):
            st_e = st_e.model_copy(
                update={
                    "detail": str(emb.get("detail") or emb.get("reason") or "")[:500],
                },
            )
        trace.append(st_e)

        def _retrieve() -> list[dict[str, Any]]:
            return retrieve_chunks(
                ticker=ticker,
                query=q,
                top_k=retrieval_top_k,
                max_age_days=retrieval_max_age_days,
            )

        rec, st_r = _run_step("rag_retrieve", "Retrieve top-k hybrid chunks", _retrieve)
        trace.append(st_r)
        if st_r.status == "error" or rec is None:
            raise RuntimeError(st_r.detail or "rag_retrieve failed")
        retrieved = rec
    else:
        for sid, desc in (
            ("rag_ingest", "Ingest news and filing rows into RAG store"),
            ("rag_embed_sync", "Sync embedding index for ticker"),
            ("rag_retrieve", "Retrieve top-k hybrid chunks"),
        ):
            trace.append(
                PipelineStepTrace(
                    step_id=sid,
                    description=desc,
                    status="skipped",
                    duration_ms=0.0,
                    detail="include_retrieval=false",
                )
            )

    def _report() -> BuySellReport:
        return build_buy_sell_report_from_layer1(
            ticker=ticker,
            bundle=bundle,  # type: ignore[arg-type]
            include_llm_review=include_llm_review,
            retrieved_chunks=retrieved,
        )

    rep, st_rep = _run_step("score_and_report", "Build BuySellReport", _report)
    trace.append(st_rep)
    if st_rep.status == "error" or rep is None:
        raise RuntimeError(st_rep.detail or "score_and_report failed")

    return ExecutionResult(
        bundle=bundle,  # type: ignore[arg-type]
        retrieved=retrieved,
        report=rep,
        steps=trace,
    )
