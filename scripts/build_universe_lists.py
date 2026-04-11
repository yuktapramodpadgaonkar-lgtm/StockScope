"""
Download index constituents from Wikipedia into data/universes/*.csv

Run from repo root (with backend venv activated):
  python scripts/build_universe_lists.py

Symbols are normalized for Yahoo Finance (BRK.B -> BRK-B).

Wikipedia often returns HTTP 403 to scripts without a browser User-Agent; we fetch
HTML with httpx then parse tables locally.
"""

from __future__ import annotations

import io
import sys
from pathlib import Path

import httpx
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "universes"

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml",
    "Accept-Language": "en-US,en;q=0.9",
}


def _yahoo_symbol(raw: str) -> str:
    s = str(raw).strip().upper().replace(".", "-")
    return s


def _fetch_html(url: str, timeout: float = 60.0) -> str:
    with httpx.Client(headers=_HEADERS, follow_redirects=True, timeout=timeout) as client:
        r = client.get(url)
        r.raise_for_status()
        return r.text


def _tables_from_url(url: str) -> list[pd.DataFrame]:
    html = _fetch_html(url)
    return pd.read_html(io.StringIO(html))


def _first_table_with_column(tables: list[pd.DataFrame], col_substrings: tuple[str, ...]) -> pd.DataFrame:
    """Pick the first table that looks like a constituents list (has Symbol/Ticker)."""
    for t in tables:
        cols_lower = [str(c).lower() for c in t.columns]
        for sub in col_substrings:
            if any(sub in c for c in cols_lower):
                return t
    raise RuntimeError("No suitable table found (expected Symbol/Ticker column)")


def _table(url: str) -> pd.DataFrame:
    tables = _tables_from_url(url)
    if not tables:
        raise RuntimeError(f"No tables from {url}")
    return tables[0]


def sp500() -> pd.DataFrame:
    df = _table("https://en.wikipedia.org/wiki/List_of_S%26P_500_companies")
    sym = df["Symbol"].map(_yahoo_symbol)
    name = df["Security"] if "Security" in df.columns else df.get("Company", "")
    out = pd.DataFrame({"symbol": sym, "company_name": name})
    return out.drop_duplicates(subset="symbol")


def dow30() -> pd.DataFrame:
    tables = _tables_from_url("https://en.wikipedia.org/wiki/Dow_Jones_Industrial_Average")
    df = _first_table_with_column(tables, ("symbol", "ticker"))
    # Table columns vary; find Symbol column
    col = next((c for c in df.columns if str(c).lower() in ("symbol", "ticker")), None)
    if col is None:
        raise RuntimeError("Could not find Symbol column in Dow table")
    sym = df[col].map(_yahoo_symbol)
    name_col = next((c for c in df.columns if "company" in str(c).lower() or "name" in str(c).lower()), df.columns[0])
    out = pd.DataFrame({"symbol": sym, "company_name": df[name_col].astype(str)})
    return out.drop_duplicates(subset="symbol")


def nasdaq100() -> pd.DataFrame:
    tables = _tables_from_url("https://en.wikipedia.org/wiki/Nasdaq-100")
    df = _first_table_with_column(tables, ("symbol", "ticker"))
    col = next((c for c in df.columns if str(c).lower() in ("symbol", "ticker")), None)
    if col is None:
        raise RuntimeError("Could not find Symbol column in Nasdaq-100 table")
    sym = df[col].map(_yahoo_symbol)
    name_col = next(
        (c for c in df.columns if "company" in str(c).lower()),
        df.columns[0],
    )
    out = pd.DataFrame({"symbol": sym, "company_name": df[name_col].astype(str)})
    return out.drop_duplicates(subset="symbol")


def russell1000() -> pd.DataFrame:
    tables = _tables_from_url("https://en.wikipedia.org/wiki/Russell_1000_Index")
    df = _first_table_with_column(tables, ("symbol", "ticker"))
    col = next((c for c in df.columns if str(c).lower() in ("symbol", "ticker")), None)
    if col is None:
        raise RuntimeError("Could not find Symbol column in Russell 1000 table")
    sym = df[col].map(_yahoo_symbol)
    name_col = next(
        (c for c in df.columns if "company" in str(c).lower()),
        df.columns[0],
    )
    out = pd.DataFrame({"symbol": sym, "company_name": df[name_col].astype(str)})
    return out.drop_duplicates(subset="symbol")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    builders = [
        ("sp500.csv", sp500),
        ("dow30.csv", dow30),
        ("nasdaq100.csv", nasdaq100),
        ("russell1000.csv", russell1000),
    ]
    merged: list[pd.DataFrame] = []
    for fname, fn in builders:
        print(f"Fetching {fname}…")
        df = fn()
        path = OUT / fname
        df.to_csv(path, index=False)
        print(f"  Wrote {len(df)} rows -> {path}")
        merged.append(df[["symbol", "company_name"]])

    all_df = pd.concat(merged, ignore_index=True)
    all_df = all_df.drop_duplicates(subset="symbol").sort_values("symbol")
    all_path = OUT / "all.csv"
    all_df.to_csv(all_path, index=False)
    print(f"Wrote merged universe -> {all_path} ({len(all_df)} unique symbols)")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
