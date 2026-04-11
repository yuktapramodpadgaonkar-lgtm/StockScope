"""
Index constituent lists: try Wikipedia (MediaWiki API), then public CSV mirrors / seeds.

Polygon.io does not provide index membership lists; use scripts/fetch_universes_polygon.py
to validate symbols against Polygon reference tickers after building these lists.
"""

from __future__ import annotations

import io
import re
import time
from pathlib import Path

import httpx
import pandas as pd

_API = "https://en.wikipedia.org/w/api.php"
_HEADERS = {
    "User-Agent": "StockScope/1.0 (CMPE-258 course project; local development)",
    "Accept": "application/json",
}

SCRIPT_DIR = Path(__file__).resolve().parent

SP500_CSV_URL = (
    "https://raw.githubusercontent.com/datasets/s-and-p-500-companies/master/data/constituents.csv"
)
# Nasdaq-100 mirror (DataHub); if it moves, try Wikipedia or update URL.
NASDAQ100_CSV_URLS = (
    "https://pkgstore.datahub.io/core/nasdaq-100/nasdaq-100-csv/archive/refs/heads/main/constituents.csv",
    "https://datahub.io/core/nasdaq-100/r/constituents.csv",
)
DOW30_SEED = SCRIPT_DIR / "seeds" / "dow30_fallback.csv"
NASDAQ100_SEED = SCRIPT_DIR / "seeds" / "nasdaq100_fallback.csv"
NASDAQ100_BUNDLE = SCRIPT_DIR / "seeds" / "nasdaq-100-components.wiki.txt"
RUSSELL1000_BUNDLE = SCRIPT_DIR / "seeds" / "russell-1000-index.wiki.txt"


def _yahoo_symbol(raw: str) -> str:
    return str(raw).strip().upper().replace(".", "-")


def _http_get_text(url: str) -> str:
    with httpx.Client(
        headers=_HEADERS,
        timeout=120.0,
        follow_redirects=True,
    ) as client:
        r = client.get(url)
        r.raise_for_status()
        return r.text


def _fetch_parse_html(page: str) -> str:
    params = {
        "action": "parse",
        "page": page,
        "prop": "text",
        "format": "json",
        "formatversion": "2",
    }
    with httpx.Client(headers=_HEADERS, timeout=60.0, follow_redirects=True) as client:
        r = client.get(_API, params=params)
        r.raise_for_status()
        data = r.json()
    return data["parse"]["text"]


def pick_first_with_symbol_col(tables: list[pd.DataFrame]) -> pd.DataFrame:
    for t in tables:
        cols = [str(c).lower() for c in t.columns]
        if any("symbol" in c or c == "ticker" for c in cols):
            return t
    raise RuntimeError("No table with Symbol/Ticker column found")


def table_from_wiki_page(
    page: str,
    pause_s: float = 0.5,
) -> pd.DataFrame:
    time.sleep(pause_s)
    html = _fetch_parse_html(page)
    tables = pd.read_html(io.StringIO(html))
    if not tables:
        raise RuntimeError(f"No tables parsed from Wikipedia page: {page}")
    return pick_first_with_symbol_col(tables)


def sp500_dataframe() -> pd.DataFrame:
    try:
        df = table_from_wiki_page("List of S&P 500 companies")
        sym_col = next(c for c in df.columns if str(c).lower() == "symbol")
        name_col = "Security" if "Security" in df.columns else df.columns[1]
        out = pd.DataFrame(
            {
                "symbol": df[sym_col].map(_yahoo_symbol),
                "company_name": df[name_col].astype(str),
            }
        )
        return out.drop_duplicates(subset="symbol")
    except Exception:
        raw = _http_get_text(SP500_CSV_URL)
        df = pd.read_csv(io.StringIO(raw))
        sym_col = "Symbol" if "Symbol" in df.columns else df.columns[0]
        name_col = "Security" if "Security" in df.columns else "Name"
        out = pd.DataFrame(
            {
                "symbol": df[sym_col].map(_yahoo_symbol),
                "company_name": df[name_col].astype(str),
            }
        )
        return out.drop_duplicates(subset="symbol")


def dow30_dataframe() -> pd.DataFrame:
    try:
        df = table_from_wiki_page("Dow Jones Industrial Average")
        sym_col = next(c for c in df.columns if str(c).lower() in ("symbol", "ticker"))
        name_col = next(
            (c for c in df.columns if "company" in str(c).lower()),
            df.columns[0],
        )
        out = pd.DataFrame(
            {
                "symbol": df[sym_col].map(_yahoo_symbol),
                "company_name": df[name_col].astype(str),
            }
        )
        return out.drop_duplicates(subset="symbol")
    except Exception:
        if not DOW30_SEED.exists():
            raise RuntimeError(
                f"Wikipedia unavailable and missing seed file: {DOW30_SEED}",
            )
        df = pd.read_csv(DOW30_SEED)
        return df


def _parse_nasdaq_wiki_table(text: str) -> pd.DataFrame:
    """Parse wikitext table rows: | TICKER || [[Company]] ... or | TICKER || Plain name ..."""
    rows: list[tuple[str, str]] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line.startswith("|") or line.startswith("|-") or line.startswith("|}"):
            continue
        parts = [p.strip() for p in line.split("||")]
        cell0 = parts[0].lstrip("|").strip()
        if cell0.startswith("!") or cell0.lower() == "ticker":
            continue
        if not re.match(r"^[A-Z0-9.-]{1,10}$", cell0):
            continue
        sym = _yahoo_symbol(cell0)
        if len(parts) < 2:
            continue
        second = parts[1]
        if "[[" in second:
            m = re.search(r"\[\[(?:[^\]|]+\|)?([^\]]+)\]\]", second)
            name = (m.group(1) if m else second).strip()
            if "(" in second and name.endswith(")"):
                pass
        else:
            name = second.split("(")[0].strip()
        rows.append((sym, name))
    out = pd.DataFrame(rows, columns=["symbol", "company_name"])
    if len(out) < 50:
        raise RuntimeError(f"Wikitext parse produced too few rows: {len(out)}")
    return out.drop_duplicates(subset="symbol")


def _nasdaq100_from_wikitext_raw() -> pd.DataFrame:
    """Prefer live Wikipedia raw export; fall back to bundled snapshot in seeds/."""
    try:
        url = "https://en.wikipedia.org/w/index.php?title=Nasdaq-100&action=raw"
        text = _http_get_text(url)
        start = text.find("==Current components==")
        end = text.find("==Component changes==", start)
        if start == -1 or end == -1:
            raise RuntimeError("Could not find Current components section in wikitext")
        chunk = text[start:end]
        return _parse_nasdaq_wiki_table(chunk)
    except Exception:
        if not NASDAQ100_BUNDLE.exists():
            raise
        return _parse_nasdaq_wiki_table(NASDAQ100_BUNDLE.read_text(encoding="utf-8"))


def nasdaq100_dataframe() -> pd.DataFrame:
    try:
        df = table_from_wiki_page("Nasdaq-100")
        sym_col = next(c for c in df.columns if str(c).lower() in ("symbol", "ticker"))
        name_col = next(
            (c for c in df.columns if "company" in str(c).lower()),
            df.columns[0],
        )
        out = pd.DataFrame(
            {
                "symbol": df[sym_col].map(_yahoo_symbol),
                "company_name": df[name_col].astype(str),
            }
        )
        return out.drop_duplicates(subset="symbol")
    except Exception:
        try:
            return _nasdaq100_from_wikitext_raw()
        except Exception:
            pass
        if NASDAQ100_SEED.exists():
            return pd.read_csv(NASDAQ100_SEED)
        last: Exception | None = None
        for url in NASDAQ100_CSV_URLS:
            try:
                raw = _http_get_text(url)
                df = pd.read_csv(io.StringIO(raw))
                sym_col = next(
                    c for c in df.columns if str(c).lower() in ("symbol", "ticker")
                )
                name_col = next(
                    (c for c in df.columns if "name" in str(c).lower()),
                    df.columns[1] if len(df.columns) > 1 else df.columns[0],
                )
                out = pd.DataFrame(
                    {
                        "symbol": df[sym_col].map(_yahoo_symbol),
                        "company_name": df[name_col].astype(str),
                    }
                )
                return out.drop_duplicates(subset="symbol")
            except Exception as e:
                last = e
                continue
        raise RuntimeError(f"Could not load Nasdaq-100 from mirrors: {last!r}") from last


def _parse_russell_wiki_constituents(text: str) -> pd.DataFrame:
    """Parse '|| [[Company]] || SYM ||' rows from Russell 1000 wikitext."""
    rows: list[tuple[str, str]] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line.startswith("|") or line.startswith("|-") or line.startswith("|}"):
            continue
        m = re.match(
            r"^\|+\s*(.+?)\s*\|\|\s*([A-Z0-9][A-Z0-9.-]{0,10})\s*\|\|",
            line,
        )
        if not m:
            continue
        company_cell = m.group(1).strip()
        sym = _yahoo_symbol(m.group(2))
        if "[[" in company_cell:
            nm = re.search(r"\[\[(?:[^\]|]+\|)?([^\]]+)\]\]", company_cell)
            name = (nm.group(1) if nm else company_cell).strip()
        else:
            name = company_cell.split("||")[0].strip()
        rows.append((sym, name))
    out = pd.DataFrame(rows, columns=["symbol", "company_name"])
    if len(out) < 500:
        raise RuntimeError(f"Russell parse produced too few rows: {len(out)}")
    return out.drop_duplicates(subset="symbol")


def _russell1000_from_wikitext_raw() -> pd.DataFrame:
    try:
        url = "https://en.wikipedia.org/w/index.php?title=Russell_1000_Index&action=raw"
        text = _http_get_text(url)
    except Exception:
        if not RUSSELL1000_BUNDLE.exists():
            raise
        text = RUSSELL1000_BUNDLE.read_text(encoding="utf-8")
    start = text.find("==Components==")
    end = text.find("==See also==", start)
    if start == -1 or end == -1:
        raise RuntimeError("Could not find Components / See also in Russell wikitext")
    chunk = text[start:end]
    return _parse_russell_wiki_constituents(chunk)


def russell1000_dataframe() -> pd.DataFrame:
    try:
        df = table_from_wiki_page("Russell 1000 Index", pause_s=0.8)
        sym_col = next(c for c in df.columns if str(c).lower() in ("symbol", "ticker"))
        name_col = next(
            (c for c in df.columns if "company" in str(c).lower()),
            df.columns[0],
        )
        out = pd.DataFrame(
            {
                "symbol": df[sym_col].map(_yahoo_symbol),
                "company_name": df[name_col].astype(str),
            }
        )
        return out.drop_duplicates(subset="symbol")
    except Exception:
        return _russell1000_from_wikitext_raw()
