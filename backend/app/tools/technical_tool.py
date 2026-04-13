"""Technical indicators — computed from OHLCV (yfinance history), not a separate vendor."""

from __future__ import annotations

from typing import Any

import pandas as pd
import yfinance as yf


def compute_technicals_from_history(
    hist: pd.DataFrame,
    sym: str,
    *,
    period: str,
    interval: str,
) -> dict[str, Any]:
    """
    RSI / MACD / MAs from a pre-fetched history DataFrame (no yfinance call).
    """
    if hist is None or hist.empty or "Close" not in hist.columns:
        return {
            "ticker": sym,
            "source": "computed_locally",
            "error": "no_history",
            "indicators": {},
        }

    close = hist["Close"].astype(float)
    last_price = float(close.iloc[-1]) if len(close) else None

    ma_50 = float(close.rolling(50).mean().iloc[-1]) if len(close) >= 50 else None
    ma_200 = float(close.rolling(200).mean().iloc[-1]) if len(close) >= 200 else None

    rsi_14 = _rsi(close, 14)

    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()
    macd_line = ema12 - ema26
    signal_line = macd_line.ewm(span=9, adjust=False).mean()
    macd_hist = macd_line - signal_line

    macd_val = float(macd_line.iloc[-1]) if len(macd_line) else None
    macd_sig = float(signal_line.iloc[-1]) if len(signal_line) else None
    macd_h = float(macd_hist.iloc[-1]) if len(macd_hist) else None

    macd_signal_str = "neutral"
    if macd_val is not None and macd_sig is not None:
        if macd_val > macd_sig and macd_h is not None and macd_h > 0:
            macd_signal_str = "bullish"
        elif macd_val < macd_sig:
            macd_signal_str = "bearish"

    price_vs_ma = "insufficient_data"
    if last_price is not None and ma_50 is not None and ma_200 is not None:
        if last_price >= ma_50 >= ma_200:
            price_vs_ma = "above_50_and_200"
        elif last_price >= ma_50:
            price_vs_ma = "above_50_below_200"
        elif last_price < ma_50 and last_price < ma_200:
            price_vs_ma = "below_50_and_200"
        else:
            price_vs_ma = "mixed"

    trend = "sideways"
    if len(close) >= 60:
        short = float(close.iloc[-1] / close.iloc[-20] - 1.0) if close.iloc[-20] != 0 else 0.0
        if short > 0.02:
            trend = "up"
        elif short < -0.02:
            trend = "down"

    return {
        "ticker": sym,
        "period": period,
        "interval": interval,
        "source": "computed_locally",
        "last_close": last_price,
        "indicators": {
            "rsi_14": rsi_14,
            "macd": macd_val,
            "macd_signal": macd_sig,
            "macd_histogram": macd_h,
            "macd_label": macd_signal_str,
            "sma_50": ma_50,
            "sma_200": ma_200,
            "price_vs_ma": price_vs_ma,
            "trend_short": trend,
        },
    }


def get_technical_indicators(
    ticker: str,
    *,
    period: str = "1y",
    interval: str = "1d",
) -> dict[str, Any]:
    """Standalone path (extra yfinance history call) — prefer layer1 single-fetch."""
    sym = ticker.strip().upper()
    t = yf.Ticker(sym)
    hist = t.history(period=period, interval=interval, auto_adjust=True)
    return compute_technicals_from_history(hist, sym, period=period, interval=interval)


def _rsi(close: pd.Series, period: int = 14) -> float | None:
    if len(close) < period + 1:
        return None
    delta = close.diff()
    gain = delta.where(delta > 0.0, 0.0)
    loss = (-delta).where(delta < 0.0, 0.0)
    avg_gain = gain.rolling(window=period, min_periods=period).mean()
    avg_loss = loss.rolling(window=period, min_periods=period).mean()
    rs = avg_gain / avg_loss.replace(0, float("nan"))
    rsi = 100.0 - (100.0 / (1.0 + rs))
    out = rsi.iloc[-1]
    if pd.isna(out):
        return None
    return float(out)
