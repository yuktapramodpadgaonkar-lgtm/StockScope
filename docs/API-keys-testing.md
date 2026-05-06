# Testing API keys and provider calls

Use this checklist to confirm keys are loaded, outbound calls succeed, and the Layer 1 bundle reflects the right providers for a **single stock** (e.g. `AAPL` or `MSFT`).

**Prerequisites**

1. Copy `backend/.env.example` → `backend/.env` and add your keys (never commit `.env`).
2. Start the API from the **repo root** with the venv activated:

   ```powershell
   uvicorn app.main:app --reload --app-dir backend
   ```

3. Default base URL below: `http://127.0.0.1:8000`.

---

## 1. Backend is up (no keys required)

```powershell
curl.exe -s "http://127.0.0.1:8000/health"
```

Expected: JSON like `{"status":"ok"}`.

---

## 2. Layer 1 bundle — primary test for Buy/Sell keys

This endpoint exercises **yfinance** always, and **Alpha Vantage** / **Finnhub** when keys are present in `backend/.env`.

```powershell
curl.exe -s "http://127.0.0.1:8000/api/buy-sell/data/MSFT" | ConvertFrom-Json | Select-Object -ExpandProperty call_ledger
```

Or open in a browser (ledger only):

`http://127.0.0.1:8000/api/buy-sell/data/MSFT`

In **Swagger**: `http://127.0.0.1:8000/docs` → **Buy / Sell Analysis** → `GET /api/buy-sell/data/{ticker}` → Try it out → `ticker`: `MSFT` → Execute.

### How to read `call_ledger`

The JSON includes `call_ledger` and `call_ledger_summary`. Counts are **logical** provider calls (see [`Layer1-api-call-ledger.md`](Layer1-api-call-ledger.md)).

| Situation | Typical `call_ledger` |
|-----------|------------------------|
| **No** `ALPHA_VANTAGE_API_KEY`, **no** `FINNHUB_API_KEY` | `yfinance`: **3** (info + history + news), `alpha_vantage`: **0**, `finnhub`: **0** |
| Both keys set and requests succeed | `yfinance`: **2**, `alpha_vantage`: **1**, `finnhub`: **1** |

**Signs keys work**

- **`alpha_vantage` is 1** and `news_and_sentiment.primary_source` is **`alpha_vantage`**, and `news_and_sentiment.alpha_vantage.skipped` is not `true` (unless the key is empty).
- **`finnhub` is 1** and `analyst_recommendations.primary_source` is **`finnhub`**, and `analyst_recommendations.finnhub.trend` is a **non-empty list** (for liquid names like `MSFT` / `AAPL`).

**Signs a key is missing or invalid**

- `alpha_vantage` stays **0** and `news_and_sentiment.alpha_vantage` shows `skipped: true` or an `error` / `detail` (e.g. rate-limit note from Alpha Vantage).
- `finnhub` stays **0** and `analyst_recommendations.finnhub` shows `skipped: true` — then consensus falls back to `yfinance_info` (still valid; no extra HTTP).

**Alpha Vantage rate limits (free tier)**  
If the key is correct but quota is exhausted, the API may return a message in the payload instead of `feed`. Check `news_and_sentiment.alpha_vantage.detail` or `error` fields.

---

## 3. Quick jq-style inspection (optional)

If you have `jq` installed:

```bash
curl -s "http://127.0.0.1:8000/api/buy-sell/data/AAPL" | jq ".call_ledger, .news_and_sentiment.primary_source, .analyst_recommendations.primary_source"
```

---

## 4. Direct provider tests (optional debugging)

These hit the **vendor** directly from your machine (not through StockScope). Use only to verify the key itself.

**Alpha Vantage — news sentiment** (replace `YOUR_KEY`):

```text
https://www.alphavantage.co/query?function=NEWS_SENTIMENT&tickers=IBM&apikey=YOUR_KEY
```

You should see a JSON object with a `feed` array (or an `Information` / `Note` field if the key or quota is wrong).

**Finnhub — recommendations** (replace `YOUR_KEY`):

```text
https://finnhub.io/api/v1/stock/recommendation?symbol=AAPL&token=YOUR_KEY
```

You should see a JSON **array** of objects with fields like `buy`, `hold`, `sell`, `period`.

---

## 5. Polygon (scripts only — not the FastAPI Layer 1 route)

Polygon is **not** used by `GET /api/buy-sell/data/{ticker}`. To test `POLYGON_API_KEY`, run from **repo root** with the variable set:

```powershell
$env:POLYGON_API_KEY = "your_key"
.\.venv\Scripts\python.exe scripts\fetch_universes_polygon.py --wiki-only
```

`--wiki-only` builds CSVs **without** Polygon. To test Polygon enrichment, run **without** `--wiki-only` and ensure the key is set; watch the script output for enrichment progress or errors.

---

## 6. Market movers (yfinance only)

Confirms the server reaches Yahoo-backed data (no Alpha Vantage / Finnhub):

```powershell
curl.exe -s "http://127.0.0.1:8000/api/market-movers?universe=sp500&mode=intraday&type=gainers&limit=5"
```

Expect `items` with symbols and quote fields.

---

## Summary

| Goal | What to run |
|------|----------------|
| Keys loaded + calls executed for **one stock** | `GET /api/buy-sell/data/{ticker}` and check **`call_ledger`** + **`primary_source`** fields |
| Alpha Vantage working | `alpha_vantage` = 1 and AV payload has items / feed behavior |
| Finnhub working | `finnhub` = 1 and `trend` non-empty when applicable |
| Polygon | Script + `POLYGON_API_KEY` in env, not the Buy/Sell JSON route |

For key placement, see [`API-keys.md`](API-keys.md).

---

## 7. Phase 4 LLM review (Hugging Face)

Set these in `backend/.env`:

- `BUYSELL_LLM_PROVIDER=huggingface`
- `BUYSELL_LLM_ENABLED=true`
- `HUGGINGFACE_API_TOKEN=...`
- For generic API mode: `HF_MODEL_ID=...`
- For endpoint mode (later): `HF_INFERENCE_URL=...` (if set, it takes priority)

Test call:

```powershell
curl.exe -s "http://127.0.0.1:8000/api/buy-sell/analyze/AAPL?include_llm_review=true"
```

Check response:

- `llm_review.enabled` should be `true` when HF call succeeds
- `llm_review.model` should show your HF model/endpoint
- If HF is not configured/fails, response still returns deterministic scores with warnings in `llm_review.warnings`
