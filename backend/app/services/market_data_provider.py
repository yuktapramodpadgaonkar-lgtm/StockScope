from __future__ import annotations

from pathlib import Path
import pandas as pd
import yfinance as yf

from app.schemas.market_movers import TimeMode, Universe


DATA_DIR = Path(__file__).resolve().parents[3] / "data" / "universes"


class MarketDataProvider:
    def get_symbols(self, universe: Universe) -> list[str]:
        if universe == Universe.all:
            path = DATA_DIR / "all.csv"
            if not path.exists():
                return ["AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "TSLA", "META", "JPM"]
            df = pd.read_csv(path)
            if "symbol" not in df.columns:
                return []
            return df["symbol"].dropna().astype(str).str.upper().unique().tolist()

        file_map = {
            Universe.sp500: "sp500.csv",
            Universe.dow30: "dow30.csv",
            Universe.nasdaq100: "nasdaq100.csv",
            Universe.russell1000: "russell1000.csv",
        }
        csv_name = file_map.get(universe)
        if not csv_name:
            return []

        csv_path = DATA_DIR / csv_name
        if not csv_path.exists():
            return []

        df = pd.read_csv(csv_path)
        if "symbol" not in df.columns:
            return []
        return df["symbol"].dropna().astype(str).str.upper().unique().tolist()

    def fetch_market_snapshot(self, symbols: list[str], mode: TimeMode = TimeMode.intraday) -> list[dict]:
        """
        Batch-download OHLCV for all symbols in one yf.download() call instead of
        calling ticker.info per symbol, which triggers Yahoo Finance rate limits at scale.
        """
        if not symbols:
            return []

        try:
            raw = yf.download(
                tickers=" ".join(symbols),
                period="5d",
                interval="1d",
                auto_adjust=True,
                progress=False,
                threads=False,
            )
        except Exception:
            return []

        if raw is None or raw.empty:
            return []

        multi = len(symbols) > 1
        records: list[dict] = []

        for symbol in symbols:
            try:
                if multi:
                    close_series = raw["Close"][symbol]
                    volume_series = raw["Volume"][symbol]
                else:
                    close_series = raw["Close"]
                    volume_series = raw["Volume"]

                closes = close_series.dropna()
                volumes = volume_series.dropna()

                if closes.empty:
                    continue

                price = float(closes.iloc[-1])
                volume = int(volumes.iloc[-1]) if not volumes.empty else None

                if len(closes) >= 2:
                    prev_close = float(closes.iloc[-2])
                    change = price - prev_close
                    change_percent = (change / prev_close) * 100 if prev_close != 0 else None
                else:
                    change = change_percent = None

                # For previous_day mode use the last completed session vs the one before it
                if mode == TimeMode.previous_day and len(closes) >= 3:
                    last = float(closes.iloc[-2])
                    prior = float(closes.iloc[-3])
                    if prior != 0:
                        change = last - prior
                        change_percent = (change / prior) * 100
                        price = last

                records.append(
                    {
                        "symbol": symbol,
                        "company_name": None,
                        "price": price,
                        "change": change,
                        "change_percent": change_percent,
                        "volume": volume,
                        "market_cap": None,
                        "sector": None,
                        "industry": None,
                        "high_52w": None,
                        "low_52w": None,
                    }
                )
            except Exception:
                continue

        return records
