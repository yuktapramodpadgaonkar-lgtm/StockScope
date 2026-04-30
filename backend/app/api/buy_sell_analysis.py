from typing import Any

from fastapi import APIRouter, Query

from app.schemas.buy_sell_analysis import BuySellReport, mock_buy_sell_report
from app.services.buy_sell_scoring import build_buy_sell_report_from_layer1
from app.tools import get_layer1_for_llm

router = APIRouter(prefix="/api/buy-sell", tags=["Buy / Sell Analysis"])


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
) -> BuySellReport:
    """
    Phase 3 analyze endpoint:
    Layer1 data bundle -> deterministic scoring engine -> BuySellReport.
    """
    bundle = get_layer1_for_llm(
        ticker,
        period=period,
        interval=interval,
        news_limit=news_limit,
    )
    return build_buy_sell_report_from_layer1(
        ticker=ticker,
        bundle=bundle,
        include_llm_review=include_llm_review,
    )
