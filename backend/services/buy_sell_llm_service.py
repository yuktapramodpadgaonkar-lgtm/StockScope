"""
LLM-powered explanation layer for the deterministic buy/sell scoring engine.

The scoring model is fully deterministic — this module only adds a plain-English
explanation of what the scores mean. It never invents financial data or advice.
"""

from __future__ import annotations

import logging

from services.ai.llm_service import LLMService
from services.ai.prompts import build_buy_sell_explanation_prompt

logger = logging.getLogger(__name__)
_llm = LLMService()

_FALLBACK_TEMPLATE = (
    "The deterministic scoring engine rated {ticker} as {recommendation} with an overall score of "
    "{overall_score}/100 (fundamental {fundamental_score}, technical {technical_score}, "
    "sentiment {sentiment_score}). This reflects the balance of rule-based signals across all three "
    "dimensions. This is for educational purposes only and is not financial advice."
)


def generate_buy_sell_explanation(
    ticker: str,
    recommendation: str,
    overall_score: int,
    fundamental_score: int,
    technical_score: int,
    sentiment_score: int,
    signals: list[str],
    preferred_model: str = "gemini",
) -> tuple[str, str | None, str | None]:
    """
    Generate a plain-English explanation for a deterministic buy/sell score.

    Returns:
        (rationale, model_used, provider)
    Never raises — returns a safe fallback string on total LLM failure.
    """
    prompt = build_buy_sell_explanation_prompt(
        ticker=ticker,
        recommendation=recommendation,
        overall_score=overall_score,
        fundamental_score=fundamental_score,
        technical_score=technical_score,
        sentiment_score=sentiment_score,
        signals=signals,
    )

    result = _llm.generate_response(prompt, preferred_model=preferred_model)

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
