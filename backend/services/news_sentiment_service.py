"""
News sentiment service.

Pipeline:
  1. Fetch articles from Finnhub (falls back to mock data when key is absent).
  2. Classify each article with FinBERT via the HF Inference API
     (falls back to keyword heuristic when token is absent or the model is cold).
  3. Generate top themes + a narrative summary via the configured LLM
     (Gemini → LLaMA → Mistral, with automatic fallback).
"""

from __future__ import annotations

import json
from datetime import date, datetime, timedelta
from typing import Any

import httpx

from app.core.config import settings
from app.schemas.news_sentiment import (
    AggregateSentiment,
    CitationItem,
    NewsArticleItem,
    NewsSentimentResponse,
    SentimentLabel,
)
from app.services.llm_router import call_llm_with_fallback
from services.history_service import save_research_run

_DISCLAIMER = "This is for educational purposes only and not financial advice."

# ── Date helpers ─────────────────────────────────────────────────────────────

def _parse_iso_date(s: str | None) -> date | None:
    if not s:
        return None
    try:
        return date.fromisoformat(s.strip()[:10])
    except ValueError:
        return None


def _article_in_range(item: dict[str, Any], d_from: date | None, d_to: date | None) -> bool:
    if d_from is None and d_to is None:
        return True
    try:
        d = datetime.fromisoformat(item["published_at"].replace("Z", "+00:00")).date()
    except (KeyError, ValueError):
        return True
    if d_from and d < d_from:
        return False
    if d_to and d > d_to:
        return False
    return True


# ── Mock data (used when Finnhub key is absent) ──────────────────────────────

def _mock_articles(ticker: str) -> list[dict[str, Any]]:
    sym = ticker.upper()
    return [
        {
            "headline": f"{sym} gains as AI demand remains strong",
            "source": "Mock Finance News",
            "url": "https://example.com/article-1",
            "published_at": "2026-04-10T09:00:00Z",
            "summary": "Article discusses strong AI demand and bullish expectations.",
        },
        {
            "headline": "Mixed views emerge on semiconductor valuations",
            "source": "Mock Market Watch",
            "url": "https://example.com/article-2",
            "published_at": "2026-04-09T12:00:00Z",
            "summary": "Article highlights both upside and valuation concerns.",
        },
        {
            "headline": "Traders watch macro data ahead of key earnings week",
            "source": "Mock Wire",
            "url": "https://example.com/article-3",
            "published_at": "2026-04-08T15:30:00Z",
            "summary": "Article notes caution on rates and positioning into events.",
        },
        {
            "headline": f"Analysts lift estimates on {sym} data-center outlook",
            "source": "Mock Desk Research",
            "url": "https://example.com/article-4",
            "published_at": "2026-04-07T11:00:00Z",
            "summary": "Analyst commentary frames upside to estimates.",
        },
    ]


# ── Finnhub fetch ─────────────────────────────────────────────────────────────

def _fetch_finnhub_news(
    ticker: str,
    from_date: str,
    to_date: str,
    max_articles: int,
) -> list[dict[str, Any]]:
    if not settings.finnhub_api_key:
        return []
    url = "https://finnhub.io/api/v1/company-news"
    params = {
        "symbol": ticker,
        "from": from_date,
        "to": to_date,
        "token": settings.finnhub_api_key,
    }
    with httpx.Client(timeout=15) as client:
        res = client.get(url, params=params)
        res.raise_for_status()
        payload = res.json()
    if not isinstance(payload, list):
        return []

    normalized: list[dict[str, Any]] = []
    for item in payload[:max_articles]:
        headline = (item.get("headline") or "").strip()
        if not headline:
            continue
        iso_ts = (
            datetime.utcfromtimestamp(item.get("datetime") or 0)
            .replace(microsecond=0)
            .isoformat() + "Z"
        )
        normalized.append(
            {
                "headline": headline,
                "source": item.get("source") or "Finnhub",
                "url": item.get("url") or "https://finnhub.io/",
                "published_at": iso_ts,
                "summary": (item.get("summary") or headline)[:300],
            }
        )
    return normalized


# ── Sentiment classification ─────────────────────────────────────────────────

def _heuristic_sentiment(text: str) -> SentimentLabel:
    """Keyword fallback when FinBERT is unavailable."""
    positive_markers = ("strong", "gain", "upside", "bullish", "upgrade", "beat", "optimism", "growth")
    negative_markers = ("risk", "caution", "downgrade", "bearish", "concern", "weak", "miss", "decline")
    text_l = text.lower()
    pos = sum(1 for w in positive_markers if w in text_l)
    neg = sum(1 for w in negative_markers if w in text_l)
    if pos > neg:
        return "positive"
    if neg > pos:
        return "negative"
    return "neutral"


def _classify_finbert_batch(texts: list[str]) -> list[SentimentLabel]:
    """
    Classify a batch of texts with ProsusAI/finbert via the HF Inference API.

    HF returns: [[{"label": "positive", "score": 0.97}, ...], ...]
    Falls back to heuristic for the whole batch on any error.
    """
    if not settings.finbert_enabled:
        return [_heuristic_sentiment(t) for t in texts]

    token = (settings.huggingface_api_token or "").strip()
    if not token:
        return [_heuristic_sentiment(t) for t in texts]

    url = f"https://api-inference.huggingface.co/models/{settings.finbert_model_id}"
    headers = {"Authorization": f"Bearer {token}"}
    # Send the full batch in one request to avoid N round-trips.
    payload = {"inputs": texts}

    try:
        with httpx.Client(timeout=20) as client:
            r = client.post(url, headers=headers, json=payload)
            r.raise_for_status()
        data = r.json()
    except Exception:  # noqa: BLE001
        return [_heuristic_sentiment(t) for t in texts]

    # data is a list-of-lists: one inner list of {label, score} per input text.
    if not isinstance(data, list):
        return [_heuristic_sentiment(t) for t in texts]

    results: list[SentimentLabel] = []
    for i, item in enumerate(data):
        try:
            # Pick the label with the highest confidence score.
            best = max(item, key=lambda x: x["score"])
            label = best["label"].lower()
            if label in ("positive", "negative", "neutral"):
                results.append(label)  # type: ignore[arg-type]
            else:
                results.append(_heuristic_sentiment(texts[i]))
        except Exception:  # noqa: BLE001
            results.append(_heuristic_sentiment(texts[i]))

    # If HF returned fewer items than inputs (shouldn't happen), fill gaps.
    while len(results) < len(texts):
        results.append("neutral")

    return results


# ── LLM-powered themes + summary ─────────────────────────────────────────────

_THEMES_PROMPT_TEMPLATE = """\
You are a financial analyst reviewing recent news for {ticker}.

Identify the 3 most important recurring themes from the headlines below.
Then write a 2-sentence market sentiment summary that explains the overall tone.

Rules:
- Themes must be short noun phrases (3–6 words each), e.g. "AI infrastructure spending".
- Summary must end with: "This is for educational purposes only."
- Return ONLY valid JSON — no markdown, no extra text.

JSON format:
{{"themes": ["...", "...", "..."], "summary": "..."}}

Headlines:
{headlines}
"""

_FALLBACK_THEMES = ["earnings expectations", "analyst commentary", "macro positioning"]


def _generate_themes_and_summary_llm(
    ticker: str,
    articles: list[dict[str, Any]],
    preferred_model: str | None,
) -> tuple[list[str], str, str | None]:
    """
    Ask an LLM to extract top themes and write a narrative summary.

    Returns (themes, summary, model_name_used).
    Falls back to hardcoded themes + heuristic summary on any LLM error.
    """
    headlines_text = "\n".join(
        f"- {a.get('headline', '')} ({a.get('sentiment', 'neutral')})"
        for a in articles[:10]
    )
    prompt = _THEMES_PROMPT_TEMPLATE.format(
        ticker=ticker.upper(),
        headlines=headlines_text,
    )

    try:
        raw, model_used = call_llm_with_fallback(prompt, preferred=preferred_model)
        # Parse JSON from response — strip markdown fences if present.
        raw = raw.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        start, end = raw.find("{"), raw.rfind("}")
        if start != -1 and end > start:
            raw = raw[start : end + 1]
        parsed = json.loads(raw)
        themes = [str(t) for t in parsed.get("themes", [])[:3]] or _FALLBACK_THEMES
        summary = str(parsed.get("summary", "")).strip() or _build_fallback_summary(ticker, articles)
        return themes, summary, model_used
    except Exception:  # noqa: BLE001
        return _FALLBACK_THEMES, _build_fallback_summary(ticker, articles), None


def _build_fallback_summary(ticker: str, articles: list[dict[str, Any]]) -> str:
    pos = sum(1 for a in articles if a.get("sentiment") == "positive")
    neg = sum(1 for a in articles if a.get("sentiment") == "negative")
    total = len(articles) or 1
    pct_pos = round(100 * pos / total)
    pct_neg = round(100 * neg / total)
    label = "constructive" if pct_pos > pct_neg else "cautious" if pct_neg > pct_pos else "mixed"
    return (
        f"Recent coverage for {ticker.upper()} is broadly {label} "
        f"({pct_pos}% positive, {pct_neg}% negative across {total} article(s)). "
        "This is for educational purposes only."
    )


# ── Aggregate ─────────────────────────────────────────────────────────────────

def _aggregate_counts(articles: list[NewsArticleItem]) -> AggregateSentiment:
    if not articles:
        return AggregateSentiment(positive=0, neutral=100, negative=0, overall_label="neutral")
    pos = sum(1 for a in articles if a.sentiment == "positive")
    neu = sum(1 for a in articles if a.sentiment == "neutral")
    neg = sum(1 for a in articles if a.sentiment == "negative")
    total = len(articles)
    p_pct = round(100 * pos / total)
    n_pct = round(100 * neu / total)
    neg_pct = max(0, 100 - p_pct - n_pct)
    if neg > pos and neg >= neu:
        overall: SentimentLabel = "negative"
    elif pos >= neu and pos >= neg:
        overall = "positive"
    else:
        overall = "neutral"
    return AggregateSentiment(positive=p_pct, neutral=n_pct, negative=neg_pct, overall_label=overall)


# ── Public entry point ────────────────────────────────────────────────────────

def build_news_sentiment_report(
    ticker: str,
    date_from: str | None,
    date_to: str | None,
    max_articles: int = 10,
    model_name: str | None = None,
) -> NewsSentimentResponse:
    """
    Return a structured sentiment report for *ticker*.

    Steps:
      1. Fetch from Finnhub (or mock data on failure/missing key).
      2. Classify each article with FinBERT (or keyword heuristic fallback).
      3. Generate themes + summary via LLM (or static fallback).
    """
    sym = ticker.strip().upper()
    if not sym:
        raise ValueError("ticker is required")

    d_from = _parse_iso_date(date_from)
    d_to = _parse_iso_date(date_to)

    today = datetime.utcnow().date()
    from_str = date_from or (today - timedelta(days=10)).isoformat()
    to_str = date_to or today.isoformat()

    # Step 1: Fetch
    fallback_used = False
    try:
        raw = _fetch_finnhub_news(sym, from_str, to_str, max_articles=max_articles)
    except Exception:  # noqa: BLE001
        raw = []
    if not raw:
        raw = _mock_articles(sym)[:max_articles]
        fallback_used = True

    filtered = [a for a in raw if _article_in_range(a, d_from, d_to)] or raw
    filtered = filtered[:max_articles]

    # Step 2: FinBERT classification (batch)
    texts = [f"{a.get('headline', '')} {a.get('summary', '')}" for a in filtered]
    sentiment_labels = _classify_finbert_batch(texts)
    enriched = [
        {**a, "sentiment": sentiment_labels[i]}
        for i, a in enumerate(filtered)
    ]

    articles = [NewsArticleItem.model_validate(a) for a in enriched]
    aggregate = _aggregate_counts(articles)

    # Step 3: LLM themes + summary
    themes, summary, llm_model_used = _generate_themes_and_summary_llm(
        sym,
        enriched,
        preferred_model=model_name,
    )

    citations = [
        CitationItem(
            title=a.headline,
            url=a.url,
            source=a.source,
            published_at=a.published_at,
        )
        for a in articles
    ]

    save_research_run("news_sentiment", sym)

    return NewsSentimentResponse(
        ticker=sym,
        date_from=from_str,
        date_to=to_str,
        aggregate_sentiment=aggregate,
        major_themes=themes,
        articles=articles,
        summary=summary,
        citations=citations,
        disclaimer=_DISCLAIMER,
        fallback_used=fallback_used,
        llm_model_used=llm_model_used,
    )
