from __future__ import annotations

"""News sentiment analysis API (Week 1 mock)."""

from fastapi import APIRouter, HTTPException

from app.schemas.news_sentiment import NewsSentimentRequest, NewsSentimentResponse
from services.news_sentiment_service import build_news_sentiment_report

router = APIRouter(prefix="/api/analysis", tags=["News Sentiment"])


@router.post("/news-sentiment", response_model=NewsSentimentResponse)
def post_news_sentiment(body: NewsSentimentRequest) -> NewsSentimentResponse:
    """
    Return mock article-level sentiment and aggregates for a ticker.

    TODO: Live news fetch + model-based sentiment scoring.
    """
    try:
        return build_news_sentiment_report(
            body.ticker,
            body.date_from,
            body.date_to,
            max_articles=body.max_articles,
            model_name=body.model_name,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
