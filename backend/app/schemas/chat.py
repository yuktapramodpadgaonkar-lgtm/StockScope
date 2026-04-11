"""Pydantic models for the Week 1 chat API."""

from typing import Literal

from pydantic import BaseModel, Field


class ChatQueryRequest(BaseModel):
    """Inbound user message for the chatbot stub."""

    query: str = Field(..., min_length=1, max_length=4000, description="User question")
    thread_id: str | None = Field(
        default=None,
        max_length=128,
        description="Client-owned conversation id; generated if omitted",
    )


ChatIntent = Literal["stock_explanation", "sentiment_question", "comparison_question", "unknown"]


class ChatCitation(BaseModel):
    title: str
    url: str
    source: str
    published_at: str


class ChatQueryResponse(BaseModel):
    thread_id: str
    detected_intent: ChatIntent
    answer: str
    summary_bullets: list[str]
    citations: list[ChatCitation]
    disclaimer: str
    timestamp: str
