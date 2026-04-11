# Market movers — logic, data flow, and caching

Market movers are computed **entirely on the FastAPI backend**. The UI calls one HTTP
endpoint; the server resolves a **symbol universe**, optionally **reuses a cached
snapshot** of prices, then **sorts** that snapshot to produce gainers, losers, or
“closest to 52-week high/low” lists.

## End-to-end flow

1. **Universe:** `MarketDataProvider.get_symbols()` loads tickers from CSVs under
   `data/universes/` (see below).
2. **Snapshot:** For each symbol, `fetch_market_snapshot()` uses **yfinance**
   (`yf.Ticker(symbol).info`, and daily history when `mode=previous_day`) to build one
   row with price, change %, 52-week range, volume, etc.
3. **Cache (optional):** The list of rows for `(universe, mode)` is stored in an
   in-memory TTL cache so switching **gainers ↔ losers** or changing **limit** does not
   refetch every ticker.
4. **Rank:** Rows are sorted according to `type` (gainers, losers, 52-week views).
5. **Slice:** The first `limit` rows are returned.

**Relevant modules:**

- `backend/app/api/market_movers.py`
- `backend/app/services/market_movers_service.py`
- `backend/app/services/market_data_provider.py`
- `backend/app/services/snapshot_cache.py`

## HTTP API

**`GET /api/market-movers`**

| Query param | Values | Meaning |
|-------------|--------|---------|
| `universe` | `all`, `sp500`, `dow30`, `nasdaq100`, `russell1000` | Which symbol list to use (see next section). |
| `mode` | `intraday`, `previous_day` | How **change** and **change_percent** are defined (see **Time modes** below). |
| `type` | `gainers`, `losers`, `52w_high`, `52w_low` | Sorting rule (see **Ranking** below). |
| `limit` | `1`–`200` | Max rows returned. |

Example:

```http
GET /api/market-movers?universe=sp500&mode=intraday&type=gainers&limit=25
```

OpenAPI / try-it: `http://127.0.0.1:8000/docs` once the API is running.

## Universe symbols (CSV files)

Symbols come from `data/universes/` at the repo root (paths are resolved from
`backend/app/services/market_data_provider.py`):

| `universe` | File | Notes |
|------------|------|--------|
| `sp500` | `sp500.csv` | |
| `dow30` | `dow30.csv` | |
| `nasdaq100` | `nasdaq100.csv` | |
| `russell1000` | `russell1000.csv` | |
| `all` | `all.csv` if present | Merged universe; if the file is missing, a small **hardcoded** fallback list is used so the app still runs. |

Each CSV is expected to have a `symbol` column. Refreshing these lists (e.g. after
running `scripts/fetch_universes_polygon.py`) updates what the movers feature scans.

## How data is fetched (yfinance)

For **each** symbol in the universe, the provider:

- Instantiates `yfinance.Ticker(symbol)` and reads **`ticker.info`** (Yahoo-backed
  metadata and quote fields).
- **Price:** `currentPrice` or `regularMarketPrice`.
- **Prior close (intraday mode):** `regularMarketPreviousClose` or `previousClose`.
- **52-week levels:** `fiftyTwoWeekHigh`, `fiftyTwoWeekLow`.
- **Other fields** on each row: `shortName`, `volume`, `marketCap`, `sector`, `industry`.

There is **no batch quote API** in this implementation: large universes imply many
sequential yfinance calls per cache miss, which is why caching matters.

## Time modes: `intraday` vs `previous_day`

- **`intraday`:** Change is **last price minus previous close** from quote info, and
  **change_percent** is that move as a percentage of previous close. This matches a
  typical “today vs yesterday’s close” view during the session.

- **`previous_day`:** The code prefers **completed daily bars**: it loads ~30 days of
  **1d** history, then compares the **prior completed session’s close** to the **session
  before that** (roughly: `Close[-2]` vs `Close[-3]`). If history is missing or too
  short, it **falls back** to the same price-minus-previous-close logic as intraday
  using fields from `info`.

Snapshots are keyed by `(universe, mode)`, so **intraday** and **previous_day** maintain
separate cache entries.

## Ranking by `type`

All sorts treat missing metrics as **worse** so incomplete rows sink to the bottom.

- **`gainers`:** Sort by **change_percent** descending (largest positive first).
- **`losers`:** Sort by **change_percent** ascending (largest negative first).
- **`52w_high`:** Among rows with both **price** and **high_52w**, rank by smallest
  `abs(price - high_52w)` (tickers trading nearest their 52-week high).
- **`52w_low`:** Same idea with **low_52w**: smallest `abs(price - low_52w)`.

After sorting, the API returns the **first `limit`** rows.

## Server-side cache

**Why:** Without caching, every UI change (gainers → losers, different `limit`, etc.)
would repeat a full yfinance pass over the entire universe.

**What is cached:** The **raw list of per-symbol dicts** returned by
`fetch_market_snapshot` — not the sorted leaderboard. **Cache key:** `"<universe>:<mode>"`
(e.g. `sp500:intraday`). **All** values of `type` and `limit` reuse that same snapshot
until the TTL expires.

**Implementation:** `backend/app/services/snapshot_cache.py` — a thread-safe **in-process**
TTL store (`TtlCache`), using `time.monotonic()` for expiry. This is **not** shared across
multiple uvicorn worker processes.

| Setting (in `backend/.env`) | Default | Role |
|----------------------------|---------|------|
| `MOVERS_CACHE_ENABLED` | `true` | Set `false` to disable caching (e.g. debugging). |
| `MOVERS_CACHE_TTL_INTRADAY_SECONDS` | `60` | TTL when `mode=intraday` (quotes change often). |
| `MOVERS_CACHE_TTL_PREVIOUS_DAY_SECONDS` | `300` | TTL when `mode=previous_day` (daily bars change more slowly). |

**Production note:** For **multiple API workers** or hosts, use **Redis** (or similar) if
you need a **shared** cache; otherwise each process keeps its own TTL map.

## Frontend behavior

The Market Movers page (`/market-movers`) requests:

`GET {NEXT_PUBLIC_API_BASE_URL}/api/market-movers?...`

with **`fetch(..., { cache: "no-store" })`** so the **browser** does not serve a stale
cached response. Throttling for **repeated** navigations can still be added client-side
(SWR, TanStack Query, etc.); the main cost control is the **server** snapshot cache above.

## Examples

**Top 10 S&P 500 gainers (intraday):**

```bash
curl "http://127.0.0.1:8000/api/market-movers?universe=sp500&mode=intraday&type=gainers&limit=10"
```

**Nasdaq-100 losers using previous completed session change:**

```bash
curl "http://127.0.0.1:8000/api/market-movers?universe=nasdaq100&mode=previous_day&type=losers&limit=15"
```

**Names closest to 52-week high (Russell 1000 universe file must exist):**

```bash
curl "http://127.0.0.1:8000/api/market-movers?universe=russell1000&mode=intraday&type=52w_high&limit=20"
```

PowerShell: wrap the URL in single quotes or escape `&` as `` `& ``.
