"""
LLM-powered explanation layer for the deterministic buy/sell scoring engine.

Explanation modes (Buy/Sell):
- Dropdown `finbert`: FinBERT + optional RAG (no generative prose).
- `hf_qwen` / `hf_mistral_instruct`: Hugging Face Inference instruction models.
- `gemini` / `llama` / `mistral`: LLMService (Google + local Ollama).

The scoring model is fully deterministic — this module only adds plain-English explanation.
"""

from __future__ import annotations

import logging
from typing import Any

from app.core.config import settings
from app.schemas.buy_sell_analysis import (
    DimensionRuleScore,
    LlmAgreement,
    LlmReview,
    LlmScoreSuggestion,
    OverallRuleScore,
)
from services.ai.llm_service import LLMService
from services.ai.prompts import build_buy_sell_explanation_prompt
from services.huggingface_inference_text import hf_generate_instruction_text

logger = logging.getLogger(__name__)
_llm = LLMService()

_FALLBACK_TEMPLATE = (
    "The deterministic scoring engine rated {ticker} as {recommendation} with an overall score of "
    "{overall_score}/100 (fundamental {fundamental_score}, technical {technical_score}, "
    "sentiment {sentiment_score}). This reflects the balance of rule-based signals across all three "
    "dimensions. This is for educational purposes only and is not financial advice."
)


def _layer1_item_snippet(item: dict[str, Any]) -> str:
    title = str(item.get("title") or item.get("headline") or "").strip()
    summary = str(item.get("summary") or item.get("text") or "").strip()
    combined = f"{title}. {summary}".strip()
    return (combined if combined else title)[:800]


def finbert_buy_sell_llm_review(
    ticker: str,
    overall: OverallRuleScore,
    f: DimensionRuleScore,
    t: DimensionRuleScore,
    s: DimensionRuleScore,
    bundle: dict[str, Any],
    retrieval_chunks: list[dict[str, Any]] | None,
    signals: list[str],
) -> LlmReview | None:
    """
    Build the optional AI explanation from FinBERT headline labels + scores + optional RAG chunks.

    Returns None when this mode is disabled or Hugging Face token / FinBERT is unavailable
    (caller falls back to generative LLM or HF text-gen path).
    """
    if not settings.buysell_explanation_use_finbert:
        return None
    # Narrative FinBERT mode is explicit in the dropdown (not the default HF instruction path).
    if not settings.finbert_enabled or not (settings.huggingface_api_token or "").strip():
        return None

    from services.news_sentiment_service import classify_finbert_batch

    ns = bundle.get("news_and_sentiment") or {}
    av = (ns.get("alpha_vantage") or {}).get("items") or []
    yf = (ns.get("headlines") or {}).get("items") or []
    sample = av if av else yf

    lines: list[str] = [
        f"FinBERT-guided narrative for {ticker.upper()} (model {settings.finbert_model_id} via Hugging Face "
        "Inference). This text summarizes neural headline sentiment labels and your deterministic scores — "
        "FinBERT classifies sentiment; it does not generate open-ended prose like a chat model. "
        "Educational only; not financial advice.",
        "",
        f"Rule-based summary: {overall.recommendation.value} with overall score "
        f"{int(round(overall.weighted_score))}/100 (confidence {overall.confidence}/100). "
        f"Dimensions — fundamental {f.score}/100, technical {t.score}/100, sentiment {s.score}/100.",
    ]

    texts: list[str] = []
    titles_short: list[str] = []
    for item in sample[:20]:
        if isinstance(item, dict):
            snip = _layer1_item_snippet(item)
            if snip:
                texts.append(snip)
                titles_short.append(str(item.get("title") or item.get("headline") or snip[:80]).strip()[:120])

    pos = neg = neu = 0
    labels: list[str] = []
    if texts:
        labels = classify_finbert_batch(texts)
        for lbl in labels:
            if lbl == "positive":
                pos += 1
            elif lbl == "negative":
                neg += 1
            else:
                neu += 1
        lines.append("")
        lines.append(
            f"Headlines analyzed with FinBERT: {len(texts)} snippet(s) — {pos} positive, {neg} negative, {neu} neutral."
        )
        for bucket, label in (("Positive", "positive"), ("Negative", "negative"), ("Neutral", "neutral")):
            examples = [titles_short[i] for i, lb in enumerate(labels) if lb == label][:2]
            if examples:
                lines.append(f"{bucket} examples: " + "; ".join(examples))
    else:
        lines.append("")
        lines.append(
            "No non-empty headlines were available for FinBERT; sentiment scoring may still use rules on raw feeds."
        )

    if signals:
        lines.append("")
        lines.append("Notable scoring signals: " + "; ".join(signals[:6]) + ".")

    chunks = list(retrieval_chunks or [])
    if chunks:
        lines.append("")
        lines.append("RAG context (when retrieval is enabled; align with report citations for sources):")
        for row in chunks[:6]:
            title = str(row.get("title") or row.get("doc_type") or "excerpt").strip()
            tx = str(row.get("text") or "").strip().replace("\n", " ")
            excerpt = (tx[:300] + "…") if len(tx) > 300 else tx
            if excerpt:
                lines.append(f"— {title}: {excerpt}")

    rationale = "\n".join(lines)
    cite_ids = [str(c.get("chunk_id")) for c in chunks[:12] if c.get("chunk_id")]

    warnings: list[str] = []
    if not texts:
        warnings.append("No headline text for FinBERT; explanation uses scores" + (" and RAG excerpts." if chunks else "."))

    return LlmReview(
        enabled=True,
        model="finbert",
        llm_score_suggestion=LlmScoreSuggestion(
            fundamental=f.score,
            technical=t.score,
            sentiment=s.score,
            overall=int(round(overall.weighted_score)),
            recommendation=overall.recommendation,
        ),
        agreement_with_rules=LlmAgreement(matches_recommendation=True, overall_score_delta=0),
        rationale=rationale,
        warnings=warnings,
        citations_used=cite_ids,
    )


def generate_buy_sell_explanation(
    ticker: str,
    recommendation: str,
    overall_score: int,
    fundamental_score: int,
    technical_score: int,
    sentiment_score: int,
    signals: list[str],
    finance_facts: list[str] | None = None,
    preferred_model: str | None = None,
) -> tuple[str, str | None, str | None]:
    """
    Generate a plain-English explanation for a deterministic buy/sell score.

    Returns:
        (rationale, model_used, provider)
    Never raises — returns a safe fallback string on total LLM failure.
    """
    model_pref = (preferred_model or "hf_qwen").strip().lower()
    fast_mode = model_pref in {"llama", "mistral"}
    prompt = build_buy_sell_explanation_prompt(
        ticker=ticker,
        recommendation=recommendation,
        overall_score=overall_score,
        fundamental_score=fundamental_score,
        technical_score=technical_score,
        sentiment_score=sentiment_score,
        signals=signals,
        finance_facts=finance_facts or [],
        fast_mode=fast_mode,
    )

    hf_map = {
        "hf_qwen": settings.hf_buy_sell_instruction_qwen_model_id.strip(),
        "hf_mistral_instruct": settings.hf_buy_sell_instruction_mistral_model_id.strip(),
    }
    if model_pref in hf_map:
        hid = hf_map[model_pref]
        try:
            text = hf_generate_instruction_text(
                prompt,
                model_id=hid,
                max_new_tokens=512,
                temperature=0.25,
            )
            return text.strip(), hid, "huggingface"
        except Exception as exc:
            logger.warning("HF buy/sell explanation (%s) failed for %s: %s", hid, ticker, exc)
            fallback = _FALLBACK_TEMPLATE.format(
                ticker=ticker.upper(),
                recommendation=recommendation,
                overall_score=overall_score,
                fundamental_score=fundamental_score,
                technical_score=technical_score,
                sentiment_score=sentiment_score,
            )
            return fallback + f" (HF model error: {hid})", None, None

    llm_pref = model_pref if model_pref in {"gemini", "llama", "mistral"} else "gemini"
    result = _llm.generate_response(
        prompt,
        preferred_model=llm_pref,
        ollama_timeout_seconds=settings.buysell_llm_timeout_seconds,
    )
    if result.error or not result.response:
        logger.warning("LLM buy/sell explanation failed for %s: %s", ticker, result.error)
        fallback = _FALLBACK_TEMPLATE.format(
            ticker=ticker.upper(),
            recommendation=recommendation,
            overall_score=overall_score,
            fundamental_score=fundamental_score,
            technical_score=technical_score,
            sentiment_score=sentiment_score,
        )
        return fallback, None, None

    return result.response.strip(), result.model_used, result.provider
