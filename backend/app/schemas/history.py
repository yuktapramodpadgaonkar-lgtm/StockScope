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


class ThreadHistoryResponse(BaseModel):
    thread_id: str
    messages: list[ThreadMessage]


class SavePromptRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=120)
    prompt_text: str = Field(..., min_length=1, max_length=2000)


class SavePromptResponse(BaseModel):
    saved_prompt: SavedPromptItem
