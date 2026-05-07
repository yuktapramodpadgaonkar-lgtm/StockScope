from __future__ import annotations

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
    use_rag: bool = Field(
        default=True,
        description="If true, ingest news into the local chunk store, hybrid-retrieve top chunks, and ground the LLM themes prompt on retrieved text + URLs.",
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
    llm_provider: str | None = None
    llm_fallback_used: bool = False
    rag_retrieved: int | None = Field(
        default=None,
        description="Number of news chunks retrieved for LLM grounding (when use_rag).",
    )
    rag_error: str | None = Field(default=None, description="Set when RAG ingest/retrieve fails; LLM may still run on headlines only.")
