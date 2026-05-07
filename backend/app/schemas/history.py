from __future__ import annotations

"""Pydantic models for history APIs."""

from pydantic import BaseModel, Field


class ChatHistoryItem(BaseModel):
    thread_id: str
    title: str
    last_updated: str


class ResearchHistoryItem(BaseModel):
    id: str
    type: str
    ticker: str
    created_at: str
    model_used: str | None = None
    provider: str | None = None


class SavedPromptItem(BaseModel):
    id: str
    title: str
    prompt_text: str


class HistoryResponse(BaseModel):
    chat_history: list[ChatHistoryItem]
    research_history: list[ResearchHistoryItem]
    saved_prompts: list[SavedPromptItem]


class ThreadMessage(BaseModel):
    role: str
    text: str
    timestamp: str
    intent: str | None = None
    model_used: str | None = None
    provider: str | None = None
    fallback_used: bool | None = None


class ThreadHistoryResponse(BaseModel):
    thread_id: str
    messages: list[ThreadMessage]


class SavePromptRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=120)
    prompt_text: str = Field(..., min_length=1, max_length=2000)


class SavePromptResponse(BaseModel):
    saved_prompt: SavedPromptItem


class MemorySummaryResponse(BaseModel):
    """Long-horizon session memory for rubric D (style hints only; not investment advice)."""

    session_id: str = Field(default="default", max_length=64)
    frequent_tickers: list[str] = Field(default_factory=list)
    preferred_topics: list[str] = Field(default_factory=list)
    risk_style: str | None = None
    last_updated: str = ""
