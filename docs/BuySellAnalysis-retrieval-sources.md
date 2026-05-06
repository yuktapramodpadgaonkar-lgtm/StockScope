# Retrieval sources: SEC + press releases + general news

This document fixes the **evidence strategy** for citation-grounded buy/sell analysis: **full text** where licensing allows (SEC, many IR releases), plus **general news** as headlines/excerpts + URLs — not a substitute for long-form licensed article bodies from paywalled outlets.

---

## Three tiers (use all three)

| Tier | Role | Typical content | Full text? |
|------|------|-----------------|------------|
| **1 — SEC** | Ground truth for risks, financials, material events | 10-K, 10-Q, 8-K, exhibits | **Yes** (public domain government filing text) |
| **2 — Press releases** | Company-narrated catalysts, guidance, M&A | Issued via **issuer** IR / newsroom | **Often yes** (full PR text on company or wire pages — check each site’s terms for *your* use case) |
| **3 — General news** | Market narrative, sentiment, third-party interpretation | Aggregators (Alpha Vantage, Finnhub, yfinance, NewsAPI, etc.) | **Usually excerpts only** + link; treat as **supporting**, not primary legal/financial ground truth |

**Together:** SEC + PR give you **long, citable passages** for RAG. General news gives **breadth and timeliness** with **shorter** snippets; the LLM should cite URLs and avoid pretending a headline is the same as a 10-K paragraph.

---

## Tier 1 — SEC (prioritize for RAG chunks)

**Why:** Full structured filings; stable URLs on [SEC EDGAR](https://www.sec.gov/edgar); standard for academic and compliance-style narratives.

**Flow (high level):**

1. Map **ticker → CIK** (SEC company number). Use SEC’s [company tickers JSON](https://www.sec.gov/files/company_tickers.json) or a maintained mapping.
2. List filings: e.g. `submissions` API or `data.sec.gov` endpoints (follow SEC [fair access](https://www.sec.gov/os/webmaster-faq) guidance: User-Agent identifying your app, reasonable rate limits).
3. Fetch filing **full text** (HTML or converted text), **chunk** (e.g. 500–1,500 tokens with overlap), store with metadata: `ticker`, `cik`, `form` (10-K, 8-K, …), `filed_date`, `accession_number`, `section` if parsed.

**Libraries (examples):** `edgartools`, `sec-edgar-downloader`, or direct HTTP + BeautifulSoup — pick one and stay consistent.

**Not in the current Layer 1 API:** Filings are **stubbed** until you wire ingest; see roadmap Phase 5.

---

## Tier 2 — Press releases

**Why:** Timely company-authored text; good for “what management said” without parsing only third-party spin.

**Typical sources:**

- **Investor relations** “Press releases” or “News” on `investors.{company}.com` (many list **RSS** — often contains **full PR text** in `description` or `content:encoded`).
- **Wire services** (Business Wire, PR Newswire) — sometimes RSS or partner APIs; **read terms** before bulk storage.
- **Same ticker mapping** as rest of app; metadata: `source=press_release`, `published_at`, `url`.

**Ingestion:** Prefer **RSS first** (simple, often full text). Fallback: curated list of IR RSS URLs per ticker or sector templates (`https://.../rss/news.xml` patterns vary by host).

---

## Tier 3 — General news (text expectations)

**What you realistically get:**

- **Headline + short summary + URL + sentiment** (Alpha Vantage `NEWS_SENTIMENT`, Finnhub news, yfinance `news`).
- That **is** “general news text” for the pipeline — **short** text blocks, not necessarily full Reuters/WSJ articles.

**How to use it:**

- Feed excerpts into RAG as **small chunks** with `doc_type=news`, `url` required for citations.
- Do **not** scrape paywalled article pages by default (ToS / legal / brittleness). If you need longer third-party text, use vendors that **license** article bodies or stick to **excerpt + link**.

---

## Combined retrieval policy (for the report)

1. **Facts about the company’s legal/financial position** → prefer **SEC** citations.
2. **Recent company-framed events** → prefer **press release** chunks.
3. **Market tone, headlines, “what people are saying”** → **general news** excerpts + URL.

**Conflict handling:** If news conflicts with the 10-K, the model should **defer to SEC** for factual claims about reported numbers and risks, and phrase news as “reported by …” with citation.

---

## Implementation order (suggested)

1. **SEC ingest + chunk + metadata** (highest value for “full article” equivalent in your domain).
2. **IR RSS for press releases** for tickers you care about in the demo.
3. **Keep current Layer 1 news** (Alpha Vantage / yfinance) as Tier 3 for sentiment and breadth.

---

## Related docs

- [`BuySellAnalysis-data-sources.md`](BuySellAnalysis-data-sources.md) — provider comparison.
- [`BuySellAnalysis-roadmap.md`](BuySellAnalysis-roadmap.md) — Phase 5 RAG.
- [`Layer1-api-call-ledger.md`](Layer1-api-call-ledger.md) — current HTTP call budget.
