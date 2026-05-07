from __future__ import annotations

"""Chatbot API — intent-routed LLM responses with safety layer."""

from fastapi import APIRouter, HTTPException, Request

from app.schemas.chat import ChatQueryRequest, ChatQueryResponse
from app.services.auth_service import verify_access_token
from services.chat_service import handle_chat_query

router = APIRouter(prefix="/api/chat", tags=["Chat"])


@router.post("/query", response_model=ChatQueryResponse)
def post_chat_query(body: ChatQueryRequest, request: Request) -> ChatQueryResponse:
    """Accept a user question and return a structured LLM-backed chatbot response."""
    email: str | None = None
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        email = verify_access_token(auth_header[7:])
    try:
        return handle_chat_query(body.query, body.thread_id, model_name=body.model_name, email=email)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
