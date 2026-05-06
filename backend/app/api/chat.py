from __future__ import annotations

"""Chatbot API — intent-routed LLM responses with safety layer."""

from fastapi import APIRouter, HTTPException

from app.schemas.chat import ChatQueryRequest, ChatQueryResponse
from services.chat_service import handle_chat_query

router = APIRouter(prefix="/api/chat", tags=["Chat"])


@router.post("/query", response_model=ChatQueryResponse)
def post_chat_query(body: ChatQueryRequest) -> ChatQueryResponse:
    """Accept a user question and return a structured LLM-backed chatbot response."""
    try:
        return handle_chat_query(body.query, body.thread_id, model_name=body.model_name)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
