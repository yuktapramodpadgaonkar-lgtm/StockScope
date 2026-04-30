"""Pydantic models for chat API contracts."""

from typing import Literal

from pydantic import BaseModel, Field

ChatIntent = Literal[
    "stock_explanation",
    "sentiment_question",
    "comparison_question",
    "history_lookup",
    "unknown",
]


class ChatQueryRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=4000, description="User question")
    thread_id: str | None = Field(default=None, max_length=128)


class ChatCitation(BaseModel):
    title: str
    url: str
    source: str
    published_at: str


class ChatQueryResponse(BaseModel):
    thread_id: str
    detected_intent: ChatIntent
    tickers: list[str]
    answer: str
    summary_bullets: list[str]
    citations: list[ChatCitation]
    disclaimer: str
    timestamp: str
