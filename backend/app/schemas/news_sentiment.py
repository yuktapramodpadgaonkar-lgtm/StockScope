"""Pydantic models for the Week 1 news sentiment analysis API."""

from typing import Literal

from pydantic import BaseModel, Field


class NewsSentimentRequest(BaseModel):
    ticker: str = Field(..., min_length=1, max_length=32, description="Symbol, e.g. NVDA")
    date_from: str | None = Field(default=None, description="ISO date YYYY-MM-DD")
    date_to: str | None = Field(default=None, description="ISO date YYYY-MM-DD")


SentimentLabel = Literal["positive", "neutral", "negative"]


class AggregateSentiment(BaseModel):
    positive: int = Field(..., ge=0, le=100, description="Approximate share, percent")
    neutral: int = Field(..., ge=0, le=100)
    negative: int = Field(..., ge=0, le=100)
    overall_label: SentimentLabel


class NewsArticleItem(BaseModel):
    headline: str
    source: str
    url: str
    published_at: str
    sentiment: SentimentLabel
    summary: str


class NewsSentimentResponse(BaseModel):
    ticker: str
    date_from: str | None
    date_to: str | None
    aggregate_sentiment: AggregateSentiment
    major_themes: list[str]
    articles: list[NewsArticleItem]
    llm_summary: str
    disclaimer: str
