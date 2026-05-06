"""Historical OHLCV — primary source: yfinance."""

from __future__ import annotations

from typing import Any

import pandas as pd
import yfinance as yf


def price_history_dict_from_dataframe(
    hist: pd.DataFrame,
    sym: str,
    *,
    period: str,
    interval: str,
) -> dict[str, Any]:
    """Serialize OHLCV from an existing history DataFrame (no extra yfinance call)."""
    if hist is None or hist.empty:
        return {
            "ticker": sym,
            "period": period,
            "interval": interval,
            "source": "yfinance",
            "rows": [],
            "error": "no_history",
        }

    h = hist.reset_index()
    date_col = h.columns[0]
    rows: list[dict[str, Any]] = []
    for _, row in h.iterrows():
        d = row[date_col]
        ts = d.isoformat() if hasattr(d, "isoformat") else str(d)
        rows.append(
            {
                "date": ts,
                "open": _f(row.get("Open")),
                "high": _f(row.get("High")),
                "low": _f(row.get("Low")),
                "close": _f(row.get("Close")),
                "volume": _i(row.get("Volume")),
            }
        )

    return {
        "ticker": sym,
        "period": period,
        "interval": interval,
        "source": "yfinance",
        "rows": rows,
        "row_count": len(rows),
    }


def get_price_history(
    ticker: str,
    *,
    period: str = "1y",
    interval: str = "1d",
) -> dict[str, Any]:
    """
    Return recent price history as structured rows.

    period: yfinance period e.g. 1d,5d,1mo,3mo,6mo,1y,2y,5y,ytd,max
    interval: 1m,2m,5m,15m,30m,60m,90m,1h,1d,5d,1wk,1mo,3mo
    """
    sym = ticker.strip().upper()
    t = yf.Ticker(sym)
    hist = t.history(period=period, interval=interval, auto_adjust=False)
    if hist is None or hist.empty:
        return {
            "ticker": sym,
            "period": period,
            "interval": interval,
            "source": "yfinance",
            "rows": [],
            "error": "no_history",
        }

    hist = hist.reset_index()
    # Normalize column names (Date vs Datetime)
    date_col = hist.columns[0]
    rows: list[dict[str, Any]] = []
    for _, row in hist.iterrows():
        d = row[date_col]
        ts = d.isoformat() if hasattr(d, "isoformat") else str(d)
        rows.append(
            {
                "date": ts,
                "open": _f(row.get("Open")),
                "high": _f(row.get("High")),
                "low": _f(row.get("Low")),
                "close": _f(row.get("Close")),
                "volume": _i(row.get("Volume")),
            }
        )

    return {
        "ticker": sym,
        "period": period,
        "interval": interval,
        "source": "yfinance",
        "rows": rows,
        "row_count": len(rows),
    }


def _f(x: Any) -> float | None:
    if x is None or (isinstance(x, float) and pd.isna(x)):
        return None
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def _i(x: Any) -> int | None:
    if x is None or (isinstance(x, float) and pd.isna(x)):
        return None
    try:
        return int(x)
    except (TypeError, ValueError):
        return None
