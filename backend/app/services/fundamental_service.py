"""Deterministic fundamental analysis using yfinance."""

from __future__ import annotations

import yfinance as yf

DISCLAIMER = (
    "This is automated, educational information only. It is not investment advice. "
    "Data may be incomplete or delayed. Verify figures independently before making decisions."
)


def _safe_float(value: object) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _pct_from_ratio(value: object) -> float | None:
    """yfinance often returns margins as decimals (e.g. 0.25 == 25%)."""
    x = _safe_float(value)
    if x is None:
        return None
    return x * 100.0 if abs(x) <= 1.0 else x


def extract_metrics(info: dict) -> dict[str, float | None]:
    """Pull a fixed set of metrics from ticker.info (deterministic keys)."""
    return {
        "market_cap": _safe_float(info.get("marketCap")),
        "trailing_pe": _safe_float(info.get("trailingPE")),
        "forward_pe": _safe_float(info.get("forwardPE")),
        "profit_margin_pct": _pct_from_ratio(info.get("profitMargins")),
        "operating_margin_pct": _pct_from_ratio(info.get("operatingMargins")),
        "roe_pct": _pct_from_ratio(info.get("returnOnEquity")),
        "debt_to_equity": _safe_float(info.get("debtToEquity")),
        "current_ratio": _safe_float(info.get("currentRatio")),
        "revenue_growth_yoy_pct": _pct_from_ratio(info.get("revenueGrowth")),
        "earnings_growth_yoy_pct": _pct_from_ratio(info.get("earningsGrowth")),
        "dividend_yield_pct": _pct_from_ratio(info.get("dividendYield")),
    }


def _rule_based_insights(metrics: dict[str, float | None]) -> tuple[list[str], list[str], str]:
    strengths: list[str] = []
    risks: list[str] = []

    pe = metrics.get("trailing_pe")
    if pe is not None and pe > 0 and pe < 18:
        strengths.append('Trailing P/E is below our simple "value" threshold (18).')
    if pe is not None and pe > 35:
        risks.append('Trailing P/E is above our simple "premium" threshold (35).')

    pm = metrics.get("profit_margin_pct")
    if pm is not None and pm >= 15:
        strengths.append("Profit margin looks solid versus a 15% reference.")
    if pm is not None and 0 <= pm < 5:
        risks.append("Profit margin is thin versus a 5% floor.")

    roe = metrics.get("roe_pct")
    if roe is not None and roe >= 15:
        strengths.append("Return on equity is strong versus a 15% reference.")
    if roe is not None and roe < 5:
        risks.append("Return on equity is weak versus a 5% floor.")

    dte = metrics.get("debt_to_equity")
    if dte is not None and dte <= 0.8:
        strengths.append("Debt-to-equity appears relatively low versus 0.8.")
    if dte is not None and dte > 2.0:
        risks.append("Debt-to-equity is elevated versus 2.0.")

    rev_g = metrics.get("revenue_growth_yoy_pct")
    if rev_g is not None and rev_g >= 8:
        strengths.append("Revenue growth is healthy versus an 8% YoY reference.")
    if rev_g is not None and rev_g < 0:
        risks.append("Revenue growth is negative year over year.")

    dy = metrics.get("dividend_yield_pct")
    if dy is not None and dy >= 2:
        strengths.append("Dividend yield is meaningful versus a 2% reference.")

    score = len(strengths) - len(risks)
    if score >= 2:
        verdict = "Favorable (simple rules)"
    elif score <= -1:
        verdict = "Cautious (simple rules)"
    else:
        verdict = "Mixed (simple rules)"

    if not strengths:
        strengths.append("No clear strengths flagged by the simple rules (or data missing).")
    if not risks:
        risks.append("No major risks flagged by the simple rules (or data missing).")

    return strengths, risks, verdict


def get_fundamental_report(symbol: str) -> dict:
    """
    Return structured fundamental analysis for a single ticker.
    Raises ValueError if the symbol appears invalid or data is unavailable.
    """
    sym = symbol.strip().upper()
    if not sym:
        raise ValueError("Ticker is required")

    t = yf.Ticker(sym)
    info = t.info or {}

    if not info:
        raise ValueError(f"No fundamental data found for '{sym}'")

    if (
        info.get("regularMarketPrice") is None
        and info.get("previousClose") is None
        and not info.get("shortName")
        and not info.get("longName")
        and not info.get("symbol")
    ):
        raise ValueError(f"No fundamental data found for '{sym}'")

    company_name = info.get("longName") or info.get("shortName") or sym
    sector = info.get("sector") or "Unknown"

    metrics = extract_metrics(info)
    strengths, risks, verdict = _rule_based_insights(metrics)

    return {
        "ticker": sym,
        "company_name": company_name,
        "sector": sector,
        "industry": info.get("industry") or "Unknown",
        "current_price": _safe_float(info.get("currentPrice") or info.get("regularMarketPrice")),
        "metrics": metrics,
        "strengths": strengths,
        "risks": risks,
        "verdict": verdict,
        "disclaimer": DISCLAIMER,
    }
