# Layer 1 — Data sources & API call ledger

This document tracks **what** each field comes from and **how many logical provider calls** one `GET /api/buy-sell/data/{ticker}` makes. Implementation: `backend/app/tools/layer1_pipeline.py`.

**Design rules**

- **One source per field** where possible — no duplicate fetches for RSI/MACD/MAs (computed locally from one price history).
- **No second history download** — `Ticker.history` runs **once** and feeds both OHLCV rows and technical indicators.
- **Fallbacks only when needed** — if Alpha Vantage is missing or fails, use yfinance `Ticker.news` (+1 yfinance). If Finnhub is missing, use analyst fields already in `Ticker.info` (**no extra call**).
- **FMP** is reserved for later (DCF / transcripts); Layer 1 **does not** call FMP yet (`fmp_api_key` unused).

---

## Per-field source map

| Data block | Primary source | Fallback | Extra HTTP when fallback |
|------------|----------------|----------|---------------------------|
| OHLCV history | yfinance `Ticker.history` | — | — |
| RSI, MACD, SMA50/200, trend | **Local** pandas math on same `history` | — | 0 |
| Fundamentals subset (P/E, margins, etc.) | yfinance `Ticker.info` | Finnhub financials *(not wired in MVP)* | Future: only if key fields null |
| News + sentiment | Alpha Vantage `NEWS_SENTIMENT` | yfinance `Ticker.news` | +1 yfinance if AV absent/fails |
| Analyst **trend series** (buy/hold/sell by period) | Finnhub `/stock/recommendation` | yfinance `info` analyst fields only | 0 (reuse same `info`) |
| Filings / transcripts | Stub | SEC/RAG in Phase 5 | 0 |

---

## Call counts per request (typical)

Logical counts are returned in JSON as `call_ledger` and `call_ledger_summary`.

### A) Both optional API keys set (`ALPHA_VANTAGE_API_KEY`, `FINNHUB_API_KEY`)

| Provider | Calls | What each call does |
|----------|------:|----------------------|
| **yfinance** | **3** | (1) `Ticker.info` — fundamentals + embedded analyst consensus fields<br>(2) `Ticker.history` — single OHLCV series<br>(3) *skipped* when AV returns news — see below |
| **Alpha Vantage** | **1** | `NEWS_SENTIMENT` — news feed + sentiment metadata |
| **Finnhub** | **1** | `GET /stock/recommendation` — recommendation trend rows |
| **FMP** | **0** | Not used in Layer 1 MVP |
| **Local compute** | **1** | Batch: RSI/MACD/MAs from cached `DataFrame` (not HTTP) |

When Alpha Vantage succeeds, **yfinance `Ticker.news` is not called** (avoids duplicate headlines).

**Typical total external HTTP: 4** — yfinance **2** (`info` + `history`) + Alpha Vantage **1** + Finnhub **1**.

### B) No Alpha Vantage key (Finnhub optional)

| Provider | Calls | Notes |
|----------|------:|-------|
| **yfinance** | **3** | `info` + `history` + `news` |
| **Alpha Vantage** | **0** | Skipped |
| **Finnhub** | **0 or 1** | 1 if key set, else 0 |
| **Local compute** | **1** | Technicals |

**Minimum external HTTP (no Finnhub, no AV): 3** (yfinance only) + local compute.

### C) Finnhub missing — analyst block

- **0** Finnhub calls.
- Analyst **consensus** still populated from **`Ticker.info`** fields (`recommendationKey`, `recommendationMean`, etc.) using the **same** `info()` call already counted — **no extra yfinance call**.

---

## Summary table (one stock, Layer 1)

| Configuration | yfinance | Alpha Vantage | Finnhub | Total HTTP (approx.) |
|----------------|----------|---------------|---------|----------------------|
| AV + Finnhub keys | 2 | 1 | 1 | **4** |
| AV only | 2 | 1 | 0 | **3** |
| Finnhub only | 3 | 0 | 1 | **4** |
| Neither (MVP free) | 3 | 0 | 0 | **3** |

*+1 `local_compute` batch (not HTTP).*

---

## Rate limits (reminders)

- **Alpha Vantage** free tier: low daily quota (e.g. 25 calls/day on free keys) — **one** call per ticker for news/sentiment.
- **Finnhub** free tier: per-minute limits — **one** call per ticker for recommendations.
- **yfinance**: unofficial; throttle heavy batch jobs.

**Do not** add duplicate RSI/MACD API calls (e.g. Alpha Vantage technical endpoints) unless you explicitly need vendor validation — compute from candles instead.

---

## Related docs

- [`BuySellAnalysis-data-sources.md`](BuySellAnalysis-data-sources.md) — provider comparison.
- [`BuySellAnalysis-roadmap.md`](BuySellAnalysis-roadmap.md) — phases.
