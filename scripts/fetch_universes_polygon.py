"""
Build data/universes/*.csv using:
  1) Constituent symbol lists from Wikipedia (via MediaWiki API — reliable for scripts).
  2) Optional validation / company names from Polygon
     GET https://api.polygon.io/v3/reference/tickers/{ticker}

Polygon.io does NOT provide a REST endpoint that returns "all S&P 500 symbols" or
other index memberships. Industry practice is to use an index provider list
(Wikipedia/SEC/FTSE) and optionally validate against a market-data vendor.

Usage (repo root, venv activated):
  set POLYGON_API_KEY=your_key
  python scripts/fetch_universes_polygon.py

Wiki-only (no Polygon calls):
  python scripts/fetch_universes_polygon.py --wiki-only

Requires: httpx, pandas, lxml (for read_html)
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = Path(__file__).resolve().parent
OUT = ROOT / "data" / "universes"

if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--wiki-only",
        action="store_true",
        help="Skip Polygon; write CSVs from Wikipedia only (faster, no API key).",
    )
    parser.add_argument(
        "--polygon-delay",
        type=float,
        default=0.12,
        help="Seconds between Polygon requests (rate limits). Default: 0.12",
    )
    args = parser.parse_args()

    import pandas as pd

    from polygon_client import enrich_symbols, get_api_key
    from wiki_universe import (
        dow30_dataframe,
        nasdaq100_dataframe,
        russell1000_dataframe,
        sp500_dataframe,
    )

    OUT.mkdir(parents=True, exist_ok=True)

    builders: list[tuple[str, object]] = [
        ("sp500.csv", sp500_dataframe),
        ("dow30.csv", dow30_dataframe),
        ("nasdaq100.csv", nasdaq100_dataframe),
        ("russell1000.csv", russell1000_dataframe),
    ]

    merged: list[pd.DataFrame] = []
    api_key = None
    if not args.wiki_only:
        api_key = get_api_key()

    for fname, fn in builders:
        print(f"Building {fname} (Wikipedia constituents)…")
        base_df = fn()
        symbols = base_df["symbol"].astype(str).tolist()

        if args.wiki_only:
            out_df = base_df
        else:
            print(f"  Polygon reference lookup for {len(symbols)} symbols…")
            enriched = enrich_symbols(symbols, delay_s=args.polygon_delay, api_key=api_key)
            names = {e["symbol"].upper(): e.get("company_name") for e in enriched}
            out_df = base_df.copy()
            sym_u = out_df["symbol"].astype(str).str.upper()
            out_df["company_name"] = sym_u.map(names).where(sym_u.map(names).notna(), out_df["company_name"])
            missing = len(symbols) - len(names)
            if missing:
                print(f"  Note: {missing} symbols not found on Polygon (kept Wikipedia names).")

        path = OUT / fname
        out_df = out_df[["symbol", "company_name"]].drop_duplicates(subset="symbol")
        out_df.to_csv(path, index=False)
        print(f"  Wrote {len(out_df)} rows -> {path}")
        merged.append(out_df)

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
