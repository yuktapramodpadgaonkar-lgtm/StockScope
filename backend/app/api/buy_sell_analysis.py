from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Query

from app.agents import run_buy_sell_with_agents
from app.core.config import settings
from app.memory import build_follow_up_context, load_session, memory_block_after_analyze, record_ticker_analysis
from app.schemas.buy_sell_analysis import BuySellReport, SCHEMA_VERSION, mock_buy_sell_report
from app.services.buy_sell_scoring import build_buy_sell_report_from_layer1
from app.tools import get_layer1_for_llm

router = APIRouter(prefix="/api/buy-sell", tags=["Buy / Sell Analysis"])


def _finalize_memory(report: BuySellReport, session_id: str, ticker: str) -> BuySellReport:
    record_ticker_analysis(session_id, ticker)
    mem = memory_block_after_analyze(session_id, ticker)
    return report.model_copy(update={"memory": mem, "schema_version": SCHEMA_VERSION})


@router.get("/report/mock", response_model=BuySellReport)
def get_mock_report() -> BuySellReport:
    """Phase 1: sample Kavout-style report for UI contract testing."""
    return mock_buy_sell_report()


@router.get("/data/{ticker}")
def get_data_bundle(
    ticker: str,
    period: str = Query(default="1y", description="yfinance history period"),
    interval: str = Query(default="1d", description="yfinance bar interval"),
    news_limit: int = Query(default=20, ge=1, le=50),
) -> dict[str, Any]:
    """
    Layer 1 bundle for LLM: single yfinance info+history (shared), local technicals,
    Alpha Vantage news/sentiment when `ALPHA_VANTAGE_API_KEY` is set, else yfinance news;
    Finnhub recommendation trends when `FINNHUB_API_KEY` is set, else analyst fields from info.
    See `docs/Layer1-api-call-ledger.md` and `call_ledger` in the response.
    """
    return get_layer1_for_llm(
        ticker,
        period=period,
        interval=interval,
        news_limit=news_limit,
    )


@router.get("/analyze/{ticker}", response_model=BuySellReport)
def analyze_ticker(
    ticker: str,
    period: str = Query(default="1y", description="yfinance history period"),
    interval: str = Query(default="1d", description="yfinance bar interval"),
    news_limit: int = Query(default=20, ge=1, le=50),
    include_llm_review: bool = Query(
        default=False,
        description="If true, include advisory llm_review block (phase 3 uses a stub until model client is wired).",
    ),
    include_retrieval: bool = Query(
        default=True,
        description="If true, run Phase 5 ingest + hybrid retrieval and attach retrieved citations.",
    ),
    retrieval_top_k: int = Query(default=6, ge=1, le=20),
    retrieval_max_age_days: int | None = Query(
        default=None,
        description="Freshness filter on published_at (parseable dates only). Omit for server default; -1 disables.",
    ),
    horizon: str | None = Query(
        default=None,
        description="Optional investment horizon label for the planner (e.g. '6-12 months'); overridden by session preference when memory is on.",
    ),
    use_agent_pipeline: bool = Query(
        default=True,
        description="If true (default), run Phase 6 planner/executor/critic and attach agent_pipeline metadata.",
    ),
    session_id: str = Query(
        default="default",
        description="Phase 7 session id for memory (alphanumeric, dot, dash, underscore).",
    ),
    use_memory: bool = Query(
        default=True,
        description="If true and memory is enabled, persist ticker to session and attach memory block to the report.",
    ),
    preferred_model: str = Query(
        default="gemini",
        description="Preferred LLM model for advisory review (gemini | llama | mistral).",
    ),
) -> BuySellReport:
    """
    Analyze endpoint: Layer1 → optional RAG → deterministic scores → optional LLM review.
    Default path runs Phase 6 agents (`agent_pipeline`). Phase 7 memory attaches `memory` when enabled.
    """
    eff_horizon = horizon
    mem_hint: str | None = None
    if use_memory and settings.memory_enabled:
        sess = load_session(session_id)
        if not (eff_horizon or "").strip() and sess.get("preferred_horizon"):
            eff_horizon = str(sess["preferred_horizon"])
        mem_hint = build_follow_up_context(sess, ticker) or None

    if use_agent_pipeline:
        report = run_buy_sell_with_agents(
            ticker=ticker,
            period=period,
            interval=interval,
            news_limit=news_limit,
            include_retrieval=include_retrieval,
            include_llm_review=include_llm_review,
            retrieval_top_k=retrieval_top_k,
            retrieval_max_age_days=retrieval_max_age_days,
            horizon=eff_horizon,
            retrieval_query=f"buy sell investment thesis risks catalysts for {ticker.strip().upper()}",
            memory_hint=mem_hint,
            preferred_model=preferred_model,
        )
    else:
        bundle = get_layer1_for_llm(
            ticker,
            period=period,
            interval=interval,
            news_limit=news_limit,
        )
        retrieved: list[dict[str, Any]] = []
        if include_retrieval:
            from app.rag import ingest_filings_chunks, ingest_news_chunks, retrieve_chunks
            from app.rag.embedding_index import sync_embeddings_for_ticker
            from app.rag.store import load_chunks

            ingest_news_chunks(ticker, bundle)
            ingest_filings_chunks(ticker, bundle)
            sym_u = ticker.strip().upper()
            ticker_rows = [c for c in load_chunks() if str(c.get("ticker") or "").upper() == sym_u]
            sync_embeddings_for_ticker(sym_u, ticker_rows)
            retrieved = retrieve_chunks(
                ticker=ticker,
                query=f"buy sell investment thesis risks catalysts for {ticker.upper()}",
                top_k=retrieval_top_k,
                max_age_days=retrieval_max_age_days,
            )
        report = build_buy_sell_report_from_layer1(
            ticker=ticker,
            bundle=bundle,
            include_llm_review=include_llm_review,
            retrieved_chunks=retrieved,
            preferred_model=preferred_model,
        )

    if use_memory and settings.memory_enabled:
        report = _finalize_memory(report, session_id, ticker)
    return report
