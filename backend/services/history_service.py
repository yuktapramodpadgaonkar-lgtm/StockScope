"""
Week 1 mock user history for frontend wiring.

TODO: Persist chat / research / saved prompts in a database keyed by user id.
"""

from __future__ import annotations

from app.schemas.history import (
    ChatHistoryItem,
    HistoryResponse,
    ResearchHistoryItem,
    SavedPromptItem,
)


def get_mock_history() -> HistoryResponse:
    """Return a fixed payload shaped for the History UI."""
    return HistoryResponse(
        chat_history=[
            ChatHistoryItem(
                thread_id="thread_001",
                title="Why is NVDA up today?",
                last_updated="2026-04-11T10:30:00Z",
            ),
            ChatHistoryItem(
                thread_id="thread_002",
                title="Compare NVDA vs AMD sentiment",
                last_updated="2026-04-10T18:12:00Z",
            ),
        ],
        research_history=[
            ResearchHistoryItem(
                id="research_001",
                type="news_sentiment",
                ticker="NVDA",
                created_at="2026-04-10T14:00:00Z",
            ),
            ResearchHistoryItem(
                id="research_002",
                type="fundamental",
                ticker="AAPL",
                created_at="2026-04-09T09:45:00Z",
            ),
        ],
        saved_prompts=[
            SavedPromptItem(
                id="prompt_001",
                title="Compare AI chip stocks",
                prompt_text="Compare NVDA and AMD from a long-term growth perspective.",
            ),
            SavedPromptItem(
                id="prompt_002",
                title="Macro check-in",
                prompt_text="Summarize how rates and inflation could affect large-cap tech.",
            ),
        ],
    )
