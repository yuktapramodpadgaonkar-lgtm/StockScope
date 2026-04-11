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
        records: list[dict] = []
        if not symbols:
            return records

        for symbol in symbols:
            ticker = yf.Ticker(symbol)
            info = ticker.info if ticker.info else {}

            price = info.get("currentPrice") or info.get("regularMarketPrice")
            prev_close = info.get("regularMarketPreviousClose") or info.get("previousClose")
            change = None
            change_percent = None

            if mode == TimeMode.previous_day:
                change, change_percent = self._previous_session_change(ticker, info, price)
            elif price is not None and prev_close:
                change = float(price) - float(prev_close)
                change_percent = (change / float(prev_close)) * 100 if prev_close else None

            records.append(
                {
                    "symbol": symbol,
                    "company_name": info.get("shortName"),
                    "price": float(price) if price is not None else None,
                    "change": change,
                    "change_percent": change_percent,
                    "volume": info.get("volume"),
                    "market_cap": info.get("marketCap"),
                    "sector": info.get("sector"),
                    "industry": info.get("industry"),
                    "high_52w": info.get("fiftyTwoWeekHigh"),
                    "low_52w": info.get("fiftyTwoWeekLow"),
                }
            )

        return records

    @staticmethod
    def _previous_session_change(
        ticker: yf.Ticker,
        info: dict,
        price: float | None,
    ) -> tuple[float | None, float | None]:
        """
        Daily % change for the last *completed* session vs the prior session,
        using daily bars (avoids reusing intraday vs prior close from quote info).
        """
        try:
            hist = ticker.history(period="30d", interval="1d", auto_adjust=True)
            if hist is None or hist.empty or len(hist) < 3:
                prev_close = info.get("regularMarketPreviousClose") or info.get("previousClose")
                if price is not None and prev_close:
                    ch = float(price) - float(prev_close)
                    pct = (ch / float(prev_close)) * 100
                    return ch, pct
                return None, None
            closes = hist["Close"].dropna()
            if len(closes) < 3:
                return None, None
            last_completed = float(closes.iloc[-2])
            prior = float(closes.iloc[-3])
            if prior == 0:
                return None, None
            ch = last_completed - prior
            pct = (ch / prior) * 100
            return ch, pct
        except Exception:
            prev_close = info.get("regularMarketPreviousClose") or info.get("previousClose")
            if price is not None and prev_close:
                ch = float(price) - float(prev_close)
                pct = (ch / float(prev_close)) * 100
                return ch, pct
            return None, None
