from __future__ import annotations

"""Pydantic models for chat API contracts."""

from typing import Literal

from pydantic import BaseModel, Field

ChatIntent = Literal[
    "stock_explanation",
    "sentiment_question",
    "comparison_question",
    "history_lookup",
    "financial_advice_rejected",
    "unknown",
]


class ChatQueryRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=4000, description="User question")
    thread_id: str | None = Field(default=None, max_length=128)
    model_name: str | None = Field(
        default=None,
        description="LLM to use: gemini | llama | mistral (falls back to config default)",
    )


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
    safety_triggered: bool = False
    llm_model_used: str | None = None
