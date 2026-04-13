"""
Layer 1 — single entry for LLM-bound market data.

Policy:
- One yfinance Ticker.info + one Ticker.history per request (no duplicate history).
- Technicals computed locally from that history (+1 logical local_compute).
- Alpha Vantage: single NEWS_SENTIMENT call when API key set; else yfinance news (+1 yfinance).
- Finnhub: single recommendation call when API key set; else analyst fields from info (0 extra calls).
"""

from __future__ import annotations

from typing import Any

import yfinance as yf

from app.tools.alpha_vantage_tool import fetch_news_sentiment
from app.tools.filings_tool import get_filings_or_transcripts
from app.tools.finnhub_tool import fetch_recommendation_trends
from app.tools.fundamentals_tool import extract_fundamental_fields
from app.tools.news_tool import yfinance_news_from_ticker
from app.tools.price_history_tool import price_history_dict_from_dataframe
from app.tools.technical_tool import compute_technicals_from_history


def _analyst_from_info_only(info: dict[str, Any]) -> dict[str, Any]:
    """Consensus fields already present in yfinance info — no extra HTTP."""
    return {
        "source": "yfinance_info",
        "note": "Finnhub disabled or unavailable — using analyst fields from the same info() response.",
        "recommendation_key": info.get("recommendationKey"),
        "recommendation_mean": info.get("recommendationMean"),
        "number_of_analyst_opinions": info.get("numberOfAnalystOpinions"),
        "target_mean_price": info.get("targetMeanPrice"),
    }


def get_layer1_for_llm(
    ticker: str,
    *,
    period: str = "1y",
    interval: str = "1d",
    news_limit: int = 20,
) -> dict[str, Any]:
    sym = ticker.strip().upper()
    ledger: dict[str, int] = {
        "yfinance": 0,
        "alpha_vantage": 0,
        "finnhub": 0,
        "fmp": 0,
        "local_compute": 0,
    }

    t = yf.Ticker(sym)
    info = t.info if t.info else {}
    ledger["yfinance"] += 1

    hist = t.history(period=period, interval=interval, auto_adjust=True)
    ledger["yfinance"] += 1

    price_history = price_history_dict_from_dataframe(hist, sym, period=period, interval=interval)
    technical_indicators = compute_technicals_from_history(
        hist, sym, period=period, interval=interval
    )
    ledger["local_compute"] += 1

    fundamentals = {
        "ticker": sym,
        "source": "yfinance",
        "fields": extract_fundamental_fields(info),
    }
    if not info:
        fundamentals["error"] = "no_info"

    # News + sentiment: Alpha Vantage preferred (1 call), else yfinance news (1 call)
    av_news: dict[str, Any]
    av_calls = 0
    try:
        av_news, av_calls = fetch_news_sentiment(sym, limit=news_limit)
    except Exception as e:
        av_news = {
            "ticker": sym,
            "source": "alpha_vantage",
            "error": "request_failed",
            "detail": str(e)[:300],
            "items": [],
        }
        av_calls = 0

    ledger["alpha_vantage"] += av_calls
    if av_calls == 0:
        yf_news = yfinance_news_from_ticker(t, sym, limit=news_limit)
        ledger["yfinance"] += 1
        news_and_sentiment: dict[str, Any] = {
            "primary_source": "yfinance",
            "alpha_vantage": av_news,
            "headlines": yf_news,
        }
    else:
        news_and_sentiment = {
            "primary_source": "alpha_vantage",
            "alpha_vantage": av_news,
            "headlines": {
                "ticker": sym,
                "source": "yfinance_skipped",
                "note": "Headlines/sentiment taken from Alpha Vantage to save duplicate fetches.",
                "items": [],
                "count": 0,
            },
        }

    # Analyst trends: Finnhub (1 call) or fields from info (0 extra)
    fh_rec: dict[str, Any]
    fh_calls = 0
    try:
        fh_rec, fh_calls = fetch_recommendation_trends(sym)
    except Exception as e:
        fh_rec = {
            "ticker": sym,
            "source": "finnhub",
            "error": "request_failed",
            "detail": str(e)[:300],
            "trend": [],
        }
        fh_calls = 0

    ledger["finnhub"] += fh_calls
    if fh_calls == 0:
        analyst_recommendations: dict[str, Any] = {
            "primary_source": "yfinance_info",
            "finnhub": fh_rec,
            "consensus": _analyst_from_info_only(info),
        }
    else:
        analyst_recommendations = {
            "primary_source": "finnhub",
            "finnhub": fh_rec,
            "consensus": _analyst_from_info_only(info),
        }

    filings = get_filings_or_transcripts(sym)

    data_lineage: dict[str, str] = {
        "price_history": "yfinance Ticker.history (single fetch shared with technicals)",
        "technical_indicators": "computed locally from same history (RSI, MACD, SMAs)",
        "fundamentals": "yfinance Ticker.info (subset of fields)",
        "news_sentiment": (
            "alpha_vantage NEWS_SENTIMENT"
            if av_calls
            else "yfinance Ticker.news"
        ),
        "analyst_trends": (
            "finnhub /stock/recommendation"
            if fh_calls
            else "yfinance info analyst fields (same info() call)"
        ),
        "filings_transcripts": filings.get("note", "stub"),
    }

    total_external = (
        ledger["yfinance"]
        + ledger["alpha_vantage"]
        + ledger["finnhub"]
        + ledger["fmp"]
    )

    return {
        "ticker": sym,
        "period": period,
        "interval": interval,
        "call_ledger": ledger,
        "call_ledger_summary": {
            "total_provider_http_calls": total_external,
            "local_derived_batches": ledger["local_compute"],
            "notes": (
                "Counts are logical HTTP calls to named providers. "
                "yfinance may batch internally; we count one per .info / .history / .news access."
            ),
        },
        "data_lineage": data_lineage,
        "price_history": price_history,
        "technical_indicators": technical_indicators,
        "fundamentals": fundamentals,
        "news_and_sentiment": news_and_sentiment,
        "analyst_recommendations": analyst_recommendations,
        "filings_or_transcripts": filings,
    }
