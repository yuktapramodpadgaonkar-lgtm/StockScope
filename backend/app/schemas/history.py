"""Pydantic models for the Week 1 history API."""

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
