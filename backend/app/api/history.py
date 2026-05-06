from __future__ import annotations

"""User history API with lightweight per-user JSON persistence."""

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.schemas.history import (
    HistoryResponse,
    SavePromptRequest,
    SavePromptResponse,
    ThreadHistoryResponse,
)
from app.services.auth_service import verify_access_token
from services.history_service import (
    get_history as get_history_payload,
    get_thread_history,
    save_prompt,
)

router = APIRouter(prefix="/api/history", tags=["History"])
_bearer = HTTPBearer(auto_error=False)


def _optional_email(creds: HTTPAuthorizationCredentials | None = Depends(_bearer)) -> str | None:
    """Extract email from bearer token if present; return None without raising."""
    if creds and creds.credentials:
        return verify_access_token(creds.credentials)
    return None


@router.get("", response_model=HistoryResponse)
@router.get("/", response_model=HistoryResponse)
def get_history(email: str | None = Depends(_optional_email)) -> HistoryResponse:
    """Return chat, research and saved prompt history for the authenticated user."""
    return get_history_payload(email)


@router.get("/thread/{thread_id}", response_model=ThreadHistoryResponse)
def get_thread(
    thread_id: str,
    email: str | None = Depends(_optional_email),
) -> ThreadHistoryResponse:
    if not thread_id.strip():
        raise HTTPException(status_code=400, detail="thread_id is required")
    return get_thread_history(thread_id.strip(), email)


@router.post("/save-prompt", response_model=SavePromptResponse)
def post_save_prompt(
    body: SavePromptRequest,
    email: str | None = Depends(_optional_email),
) -> SavePromptResponse:
    return save_prompt(body.title, body.prompt_text, email)
