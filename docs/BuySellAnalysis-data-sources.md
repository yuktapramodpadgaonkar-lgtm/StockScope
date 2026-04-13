# Buy/Sell Analysis — Where the data comes from (Phase 2)

Phase 2 needs **structured** inputs: prices, derived technicals, fundamentals, news, and (later) filings/transcripts. Below: what **this repo uses first**, and **what you can swap in** for course demos or production.

---

## Default in StockScope: **yfinance**

[yfinance](https://github.com/ranaroussi/yfinance) pulls Yahoo Finance–backed data (unofficial). **No API key** for basic use.

| Need | yfinance support | Notes |
|------|------------------|--------|
| **Price / OHLCV history** | `Ticker.history()` | Good for daily/intraday bars; subject to Yahoo rate limits / breakage. |
| **Technical indicators** | *Not a direct feed* | Compute **locally** from OHLCV (RSI, MACD, MAs) — see `technical_indicators.py`. |
| **Fundamentals / ratios** | `Ticker.info` | Large dict; fields vary by ticker; can be incomplete or delayed. |
| **News headlines** | `Ticker.news` | Yahoo-curated list; structure can change. |

**Pros:** Fast to ship, already used for market movers.  
**Cons:** Unofficial, not for compliance-grade trading; news and `info` can be spotty.

---

## Other options (by category)

### 1. Price history & aggregates

| Provider | What you get | Auth |
|----------|----------------|------|
| **Polygon.io** | Trades, aggregates, websockets | API key — **optional future** source for prices; **not** used by Layer 1 today. In this repo Polygon is only used by **`scripts/`** to validate tickers when building universe CSVs (see `docs/API-keys.md`). |
| **Alpha Vantage** | Time series intraday/daily | Free tier API key, rate limits |
| **Twelve Data** | OHLC, many intervals | API key |
| **Stooq / public CSVs** | Historical only | Often no key |

**Technicals:** Prefer **computing indicators yourself** from OHLCV (pandas / TA-Lib / pandas-ta) so the pipeline is vendor-agnostic.

### 2. Fundamentals (financials, ratios, estimates)

| Provider | Notes |
|----------|--------|
| **Financial Modeling Prep (FMP)** | Popular for student projects; key-based. |
| **Alpha Vantage** | Overview + some ratios; rate limits. |
| **Finnhub** | Financials endpoints on paid tiers; free tier limited. |
| **SEC data** | **XBRL / company facts** via SEC APIs — authoritative but heavier to parse. |

### 3. News & sentiment

| Provider | Notes |
|----------|--------|
| **Finnhub** | Company news endpoint with symbol filter. |
| **NewsAPI.org**, **GNews** | General financial news; filter by query/ticker in app. |
| **Benzinga / Polygon news** | Often paid. |

yfinance news is fine for **MVP**; swap to a keyed API when you need reliability or licensing clarity.

### 4. Filings & earnings transcripts (for RAG)

| Source | Notes |
|--------|--------|
| **SEC EDGAR** | **10-K, 10-Q, 8-K** — free; use **company CIK**, not just ticker (mapping tables exist). Libraries: `edgartools`, `sec-api` (paid tiers). |
| **Earnings call transcripts** | Rarely free at quality; vendors (FactSet, S&P, etc.) or licensed datasets. For class projects, **short excerpts** from filings + news often suffice. |

Phase 2 in this repo uses a **stub** for filings/transcripts until the RAG ingest (Phase 5) is wired.

---

## What the code does today

- **`get_layer1_for_llm()`** in `backend/app/tools/layer1_pipeline.py` — **one** yfinance `history`, shared fundamentals `info`, optional **Alpha Vantage** news/sentiment, optional **Finnhub** recommendations, local RSI/MACD/MAs.
- **Granular tools** remain for debugging: `get_price_history`, `get_technical_indicators`, etc.
- **`GET /api/buy-sell/data/{ticker}`** — full Layer 1 JSON for the LLM, including **`call_ledger`** (per-provider call counts).

See **[`Layer1-api-call-ledger.md`](Layer1-api-call-ledger.md)** for the per-field source table and exact call totals.

For **SEC + press releases + general news** as a combined retrieval strategy (full text vs excerpts), see **[`BuySellAnalysis-retrieval-sources.md`](BuySellAnalysis-retrieval-sources.md)**.

---

## Practical recommendation for CMPE-258

1. **Ship Phase 2 with yfinance + computed technicals** (current approach).  
2. **Add one keyed provider** (Finnhub *or* Alpha Vantage *or* Polygon) for **either** news **or** a second opinion on fundamentals if the rubric asks for “multiple sources.”  
3. **RAG / filings:** ingest **SEC filing text** or **news** first; transcripts as stretch.  

This balances **working demos**, **citation story**, and **limited time**.
