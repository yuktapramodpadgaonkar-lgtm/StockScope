from typing import Any

from fastapi import APIRouter, Query

from app.schemas.buy_sell_analysis import BuySellReport, mock_buy_sell_report
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
