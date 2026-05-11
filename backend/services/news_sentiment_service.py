"""
News Sentiment Service — Revati's module.

Pipeline:
  1. Fetch articles from Finnhub (falls back to mock data when key absent).
  2. Classify each article with FinBERT via the HF Inference API
     (keyword heuristic fallback when token absent or model cold).
  3. Generate top themes + narrative summary via LLMService
     (Gemini primary → Ollama LLaMA → Ollama Mistral).
"""

from __future__ import annotations

import json
import logging
import re
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
from services.ai.llm_service import LLMService
from app.rag import ingest_news_chunks, retrieve_chunks
from app.rag.embedding_index import sync_embeddings_for_ticker
from app.rag.store import load_chunks
from services.ai.prompts import (
    build_news_themes_prompt,
    build_news_themes_rag_prompt,
    build_news_themes_repair_prompt,
)
from services.history_service import save_research_run

logger = logging.getLogger(__name__)

_DISCLAIMER = "This is for educational purposes only and not financial advice."
_llm = LLMService()
_NEWS_CLAIM_RE = re.compile(r"\b(headlines?|articles?|reported|according to)\b", re.IGNORECASE)

# ── Date helpers ──────────────────────────────────────────────────────────────

def _parse_iso_date(s: str | None) -> date | None:
    if not s:
        return None
    try:
        return date.fromisoformat(s.strip()[:10])
    except ValueError:
        return None


def _article_in_range(
    item: dict[str, Any], d_from: date | None, d_to: date | None
) -> bool:
    if d_from is None and d_to is None:
        return True
    try:
        d = datetime.fromisoformat(
            item["published_at"].replace("Z", "+00:00")
        ).date()
    except (KeyError, ValueError):
        return True
    if d_from and d < d_from:
        return False
    if d_to and d > d_to:
        return False
    return True


# ── Mock data ─────────────────────────────────────────────────────────────────

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


# ── Sentiment classification ──────────────────────────────────────────────────

def _heuristic_sentiment(text: str) -> SentimentLabel:
    """Keyword fallback used when FinBERT is unavailable."""
    positive_markers = (
        "strong", "gain", "upside", "bullish", "upgrade",
        "beat", "optimism", "growth",
    )
    negative_markers = (
        "risk", "caution", "downgrade", "bearish", "concern",
        "weak", "miss", "decline",
    )
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
    Classify a batch of texts with ProsusAI/finbert via huggingface_hub.InferenceClient
    (routed inference; replaces the deprecated /api-inference REST endpoint).
    Falls back to heuristic per item on any error.
    """
    if not settings.finbert_enabled:
        return [_heuristic_sentiment(t) for t in texts]

    token = (settings.huggingface_api_token or "").strip()
    if not token:
        return [_heuristic_sentiment(t) for t in texts]

    try:
        from huggingface_hub import InferenceClient
    except Exception:  # noqa: BLE001
        return [_heuristic_sentiment(t) for t in texts]

    try:
        client = InferenceClient(api_key=token, timeout=30.0)
    except Exception:  # noqa: BLE001
        return [_heuristic_sentiment(t) for t in texts]

    results: list[SentimentLabel] = []
    for i, text in enumerate(texts):
        snippet = (text or "").strip()
        if not snippet:
            results.append("neutral")
            continue
        try:
            preds = client.text_classification(
                snippet[:2000],
                model=settings.finbert_model_id,
            )
            best = max(
                preds,
                key=lambda p: float(getattr(p, "score", 0.0) or 0.0),
            )
            label = str(getattr(best, "label", "")).lower()
            if label in ("positive", "negative", "neutral"):
                results.append(label)  # type: ignore[arg-type]
            else:
                results.append(_heuristic_sentiment(snippet))
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "FinBERT InferenceClient classification failed (%s); falling back to heuristic.",
                str(exc)[:200],
            )
            results.append(_heuristic_sentiment(snippet))

    while len(results) < len(texts):
        results.append("neutral")
    return results


def classify_finbert_batch(texts: list[str]) -> list[SentimentLabel]:
    """
    Classify headline/article snippets with FinBERT (HF Inference API) or heuristic fallback.

    Shared with Buy/Sell sentiment scoring; keeps one implementation for API + fallback behavior.
    """
    return _classify_finbert_batch(texts)


# ── LLM themes + summary ──────────────────────────────────────────────────────

_FALLBACK_THEMES = ["earnings expectations", "analyst commentary", "macro positioning"]


def _news_bundle_for_rag(sym: str, enriched: list[dict[str, Any]]) -> dict[str, Any]:
    """Minimal Layer1-shaped `news_and_sentiment` payload for `ingest_news_chunks`."""
    items: list[dict[str, Any]] = []
    for a in enriched:
        items.append(
            {
                "title": str(a.get("headline") or "").strip(),
                "summary": str(a.get("summary") or "").strip(),
                "source": str(a.get("source") or "news"),
                "published": str(a.get("published_at") or ""),
                "url": str(a.get("url") or ""),
            }
        )
    return {
        "news_and_sentiment": {
            "headlines": {
                "ticker": sym,
                "source": "news_sentiment_api",
                "items": items,
            }
        }
    }


def _format_news_rag_block(retrieved: list[dict[str, Any]]) -> str:
    lines: list[str] = []
    for r in retrieved:
        title = str(r.get("title") or "").strip() or "(untitled)"
        url = str(r.get("url") or "").strip()
        excerpt = str(r.get("text") or "").strip().replace("\n", " ")[:700]
        lines.append(f"- {title} | {url or 'n/a'} | {excerpt}")
    return "\n".join(lines) if lines else "(no passages)"


def _run_news_rag_pipeline(
    sym: str,
    enriched: list[dict[str, Any]],
    *,
    top_k: int = 8,
) -> tuple[list[dict[str, Any]], str | None]:
    """
    Ingest Finnhub-class articles into the chunk store, sync embeddings, hybrid-retrieve news chunks.
    Returns (retrieved_rows, error_message_or_none).
    """
    try:
        bundle = _news_bundle_for_rag(sym, enriched)
        ingest_news_chunks(sym, bundle)
        ticker_rows = [
            c
            for c in load_chunks()
            if str(c.get("ticker") or "").upper() == sym
        ]
        sync_embeddings_for_ticker(sym, ticker_rows)
        headlines_joined = " ".join(
            str(a.get("headline") or "") for a in enriched[:12]
        )
        q = (
            f"recent news sentiment themes risks catalysts analyst commentary for {sym}. "
            f"{headlines_joined}"[:2000]
        )
        retrieved = retrieve_chunks(
            ticker=sym,
            query=q,
            top_k=top_k,
            doc_types=["news"],
            max_age_days=None,
        )
        return retrieved, None
    except Exception as e:  # noqa: BLE001
        logger.warning("News RAG pipeline failed for %s: %s", sym, e)
        return [], str(e)[:500]


def _generate_themes_and_summary(
    ticker: str,
    enriched_articles: list[dict[str, Any]],
    preferred_model: str,
    *,
    rag_block: str | None = None,
) -> tuple[list[str], str, str | None, str | None, bool]:
    """
    Use LLMService to extract themes and write a narrative summary.

    Returns:
        (themes, summary, model_used, provider, fallback_used)
    """
    headlines_text = "\n".join(
        f"- [{a.get('sentiment', 'neutral')}] {a.get('headline', '')}"
        for a in enriched_articles[:10]
    )
    rb = (rag_block or "").strip()
    if rb and rb != "(no passages)":
        prompt = build_news_themes_rag_prompt(ticker, headlines_text, rb)
    else:
        prompt = build_news_themes_prompt(ticker, headlines_text)
    result = _llm.generate_response(prompt, preferred_model=preferred_model)

    if result.error or not result.response:
        logger.warning(
            "LLM theme generation failed for %s: %s", ticker, result.error
        )
        return (
            _FALLBACK_THEMES,
            _build_fallback_summary(ticker, enriched_articles),
            None, None, True,
        )

    # Parse JSON from LLM response; strip markdown fences if present.
    raw = result.response.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    start, end = raw.find("{"), raw.rfind("}")
    if start != -1 and end > start:
        raw = raw[start : end + 1]

    try:
        parsed = json.loads(raw)
        themes = [str(t) for t in parsed.get("themes", [])[:3]] or _FALLBACK_THEMES
        summary = str(parsed.get("summary", "")).strip() or _build_fallback_summary(
            ticker, enriched_articles
        )
    except (json.JSONDecodeError, ValueError):
        themes = _FALLBACK_THEMES
        summary = _build_fallback_summary(ticker, enriched_articles)

    rag_urls = "http" in (rag_block or "").lower()
    has_citations = any(
        (a.get("url") or "").strip().startswith("http") for a in enriched_articles
    ) or rag_urls
    if (not has_citations) and _NEWS_CLAIM_RE.search(summary or ""):
        # Critic: summary claims news specifics without citations. Attempt a single repair; then fallback.
        repair_prompt = build_news_themes_repair_prompt(
            ticker=ticker,
            headlines=headlines_text,
            previous=result.response or "",
            problem="news_claim_without_citations",
            has_citations=False,
            rag_block=rb or None,
        )
        repair = _llm.generate_response(repair_prompt, preferred_model=preferred_model)
        if not repair.error and repair.response:
            raw2 = repair.response.strip()
            if raw2.startswith("```"):
                raw2 = raw2.split("```")[1]
                if raw2.startswith("json"):
                    raw2 = raw2[4:]
            s2, e2 = raw2.find("{"), raw2.rfind("}")
            if s2 != -1 and e2 > s2:
                raw2 = raw2[s2 : e2 + 1]
            try:
                parsed2 = json.loads(raw2)
                themes = [str(t) for t in parsed2.get("themes", [])[:3]] or themes
                summary = str(parsed2.get("summary", "")).strip() or summary
            except (json.JSONDecodeError, ValueError):
                summary = _build_fallback_summary(ticker, enriched_articles)
        else:
            summary = _build_fallback_summary(ticker, enriched_articles)

    return themes, summary, result.model_used, result.provider, result.fallback_used


def _build_fallback_summary(ticker: str, articles: list[dict[str, Any]]) -> str:
    pos = sum(1 for a in articles if a.get("sentiment") == "positive")
    neg = sum(1 for a in articles if a.get("sentiment") == "negative")
    total = len(articles) or 1
    pct_pos = round(100 * pos / total)
    pct_neg = round(100 * neg / total)
    label = (
        "constructive" if pct_pos > pct_neg
        else "cautious" if pct_neg > pct_pos
        else "mixed"
    )
    return (
        f"Recent coverage for {ticker.upper()} is broadly {label} "
        f"({pct_pos}% positive, {pct_neg}% negative across {total} article(s)). "
        "This is for educational purposes only."
    )


# ── Aggregate ─────────────────────────────────────────────────────────────────

def _aggregate_counts(articles: list[NewsArticleItem]) -> AggregateSentiment:
    if not articles:
        return AggregateSentiment(
            positive=0, neutral=100, negative=0, overall_label="neutral"
        )
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
    return AggregateSentiment(
        positive=p_pct, neutral=n_pct, negative=neg_pct, overall_label=overall
    )


# ── Public entry point ────────────────────────────────────────────────────────

def build_news_sentiment_report(
    ticker: str,
    date_from: str | None,
    date_to: str | None,
    max_articles: int = 10,
    model_name: str | None = None,
    *,
    use_rag: bool = True,
) -> NewsSentimentResponse:
    """
    Build a structured news sentiment report for *ticker*.

    Steps:
      1. Fetch articles from Finnhub (or mock data on failure/missing key).
      2. Classify each article with FinBERT (or keyword heuristic fallback).
      3. Generate themes + summary via LLMService (Gemini → Ollama fallback).
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
    data_fallback_used = False
    try:
        raw = _fetch_finnhub_news(sym, from_str, to_str, max_articles=max_articles)
    except Exception:  # noqa: BLE001
        raw = []
    if not raw:
        raw = _mock_articles(sym)[:max_articles]
        data_fallback_used = True

    filtered = [a for a in raw if _article_in_range(a, d_from, d_to)] or raw
    filtered = filtered[:max_articles]

    # Step 2: FinBERT classification (batched)
    texts = [
        f"{a.get('headline', '')} {a.get('summary', '')}" for a in filtered
    ]
    sentiment_labels = _classify_finbert_batch(texts)
    enriched = [
        {**a, "sentiment": sentiment_labels[i]} for i, a in enumerate(filtered)
    ]

    articles = [NewsArticleItem.model_validate(a) for a in enriched]
    aggregate = _aggregate_counts(articles)

    rag_retrieved: int | None = None
    rag_error: str | None = None
    rag_block: str | None = None
    if use_rag and enriched:
        retrieved, rag_err = _run_news_rag_pipeline(sym, enriched)
        rag_retrieved = len(retrieved)
        rag_error = rag_err
        if retrieved:
            rag_block = _format_news_rag_block(retrieved)

    # Step 3: LLM themes + summary
    preferred = (model_name or settings.default_llm_provider or "gemini").strip().lower()
    themes, summary, llm_model, llm_provider, llm_fallback = (
        _generate_themes_and_summary(sym, enriched, preferred, rag_block=rag_block)
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

    save_research_run(
        "news_sentiment", sym,
        model_used=llm_model,
        provider=llm_provider,
    )

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
        fallback_used=data_fallback_used,
        llm_model_used=llm_model,
        llm_provider=llm_provider,
        llm_fallback_used=llm_fallback or False,
        rag_retrieved=rag_retrieved,
        rag_error=rag_error,
    )
