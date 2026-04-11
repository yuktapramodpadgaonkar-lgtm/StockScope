"""User activity history API (Week 1 mock)."""

from fastapi import APIRouter

from app.schemas.history import HistoryResponse
from services.history_service import get_mock_history

router = APIRouter(prefix="/api/history", tags=["History"])


@router.get("", response_model=HistoryResponse)
def get_history() -> HistoryResponse:
    """
    Return sample chat, research, and saved-prompt records.

    TODO: Load from persistent store scoped to authenticated user.
    """
    return get_mock_history()
