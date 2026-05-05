"""Pydantic models for news sentiment analysis API."""

from typing import Literal

from pydantic import BaseModel, Field

SentimentLabel = Literal["positive", "neutral", "negative"]


class NewsSentimentRequest(BaseModel):
    ticker: str = Field(..., min_length=1, max_length=32, description="Symbol, e.g. NVDA")
    date_from: str | None = Field(default=None, description="ISO date YYYY-MM-DD")
    date_to: str | None = Field(default=None, description="ISO date YYYY-MM-DD")
    max_articles: int = Field(default=10, ge=1, le=50)
    model_name: str | None = Field(
        default=None,
        description="LLM for theme generation: gemini | llama | mistral",
    )


class AggregateSentiment(BaseModel):
    positive: int = Field(..., ge=0, le=100)
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


class CitationItem(BaseModel):
    title: str
    url: str
    source: str
    published_at: str


class NewsSentimentResponse(BaseModel):
    ticker: str
    date_from: str | None
    date_to: str | None
    aggregate_sentiment: AggregateSentiment
    major_themes: list[str]
    articles: list[NewsArticleItem]
    summary: str
    citations: list[CitationItem]
    disclaimer: str
    fallback_used: bool
    llm_model_used: str | None = None
