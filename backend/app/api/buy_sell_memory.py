from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.core.config import settings
from app.memory import (
    build_follow_up_context,
    load_session,
    record_ticker_analysis,
    reset_session,
    update_session_preferences,
)

router = APIRouter(prefix="/api/buy-sell/memory", tags=["Buy / Sell Memory"])


class MemoryPreferencesUpdate(BaseModel):
    preferred_horizon: str | None = None
    analysis_style: str | None = Field(
        default=None,
        description="One of: balanced, growth, income, value",
    )
    session_summary: str | None = None


@router.get("/{session_id}")
def get_memory(session_id: str) -> dict[str, Any]:
    """Phase 7: read session memory (recent tickers, horizon preference, notes)."""
    if not settings.memory_enabled:
        return {"memory_enabled": False, "note": "Set MEMORY_ENABLED=true when you wire env."}
    return load_session(session_id)


@router.put("/{session_id}", response_model=dict[str, Any])
def put_memory_preferences(session_id: str, body: MemoryPreferencesUpdate) -> dict[str, Any]:
    """Update horizon / style / free-text session summary."""
    if not settings.memory_enabled:
        return {"memory_enabled": False, "error": "memory_disabled"}
    return update_session_preferences(
        session_id,
        preferred_horizon=body.preferred_horizon,
        analysis_style=body.analysis_style,
        session_summary=body.session_summary,
    )


@router.post("/{session_id}/reset")
def post_reset_session(session_id: str) -> dict[str, Any]:
    """Clear recent tickers and session fields for this session id."""
    if not settings.memory_enabled:
        return {"memory_enabled": False, "error": "memory_disabled"}
    return reset_session(session_id)


@router.get("/{session_id}/follow-up-context")
def get_follow_up_context(session_id: str, ticker: str = "") -> dict[str, str]:
    """Plain-text bundle for debugging or future chat prompts."""
    if not settings.memory_enabled:
        return {"context": ""}
    sess = load_session(session_id)
    return {"context": build_follow_up_context(sess, ticker or None)}


@router.post("/{session_id}/record/{ticker}")
def post_record_ticker(session_id: str, ticker: str) -> dict[str, Any]:
    """Manually append a ticker to recent history (analyze already records automatically)."""
    if not settings.memory_enabled:
        return {"memory_enabled": False, "error": "memory_disabled"}
    return record_ticker_analysis(session_id, ticker)
