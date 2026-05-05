"""User history API with lightweight persistence."""

from fastapi import APIRouter, HTTPException

from app.schemas.history import (
    HistoryResponse,
    SavePromptRequest,
    SavePromptResponse,
    ThreadHistoryResponse,
)
from services.history_service import (
    get_history as get_history_payload,
    get_thread_history,
    save_prompt,
)

router = APIRouter(prefix="/api/history", tags=["History"])


@router.get("", response_model=HistoryResponse)
@router.get("/", response_model=HistoryResponse)
def get_history() -> HistoryResponse:
    """Return chat, research and saved prompt history."""
    return get_history_payload()


@router.get("/thread/{thread_id}", response_model=ThreadHistoryResponse)
def get_thread(thread_id: str) -> ThreadHistoryResponse:
    if not thread_id.strip():
        raise HTTPException(status_code=400, detail="thread_id is required")
    return get_thread_history(thread_id.strip())


@router.post("/save-prompt", response_model=SavePromptResponse)
def post_save_prompt(body: SavePromptRequest) -> SavePromptResponse:
    return save_prompt(body.title, body.prompt_text)
