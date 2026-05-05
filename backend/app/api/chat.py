"""Chatbot API (Week 1 stub)."""

from fastapi import APIRouter, HTTPException

from app.schemas.chat import ChatQueryRequest, ChatQueryResponse
from services.chat_service import handle_chat_query

router = APIRouter(prefix="/api/chat", tags=["Chat"])


@router.post("/query", response_model=ChatQueryResponse)
def post_chat_query(body: ChatQueryRequest) -> ChatQueryResponse:
    """
    Accept a user question and return a structured mock chatbot response.

    TODO: Swap ``handle_chat_query`` for agent + retrieval pipeline.
    """
    try:
        return handle_chat_query(body.query, body.thread_id, model_name=body.model_name)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
