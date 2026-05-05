"""History service with lightweight JSON persistence for Week 1."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Type, TypeVar

from pydantic import BaseModel

from app.schemas.history import (
    ChatHistoryItem,
    HistoryResponse,
    ResearchHistoryItem,
    SavePromptResponse,
    SavedPromptItem,
    ThreadHistoryResponse,
    ThreadMessage,
)

_STORE_PATH = Path(__file__).resolve().parents[1] / "data" / "history_store.json"

M = TypeVar("M", bound=BaseModel)


def _validated_rows(raw: list[Any], model: Type[M]) -> list[M]:
    """Skip invalid rows so one bad JSON entry cannot 500 the whole /api/history response."""
    out: list[M] = []
    for row in raw:
        if not isinstance(row, dict):
            continue
        try:
            out.append(model.model_validate(row))
        except Exception:
            continue
    return out


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _default_store() -> dict[str, Any]:
    return {
        "chat_history": [
            {
                "thread_id": "thread_001",
                "title": "Why is NVDA up today?",
                "last_updated": "2026-04-11T10:30:00Z",
            }
        ],
        "research_history": [
            {
                "id": "research_001",
                "type": "news_sentiment",
                "ticker": "NVDA",
                "created_at": "2026-04-10T14:00:00Z",
            }
        ],
        "saved_prompts": [
            {
                "id": "prompt_001",
                "title": "Compare AI chip stocks",
                "prompt_text": "Compare NVDA and AMD from a long-term growth perspective.",
            }
        ],
        "threads": {
            "thread_001": {
                "messages": [
                    {
                        "role": "user",
                        "text": "Why is NVDA up today?",
                        "timestamp": "2026-04-11T10:25:00Z",
                    },
                    {
                        "role": "assistant",
                        "text": "Recent sentiment was broadly constructive in this mock dataset.",
                        "timestamp": "2026-04-11T10:30:00Z",
                    },
                ]
            }
        },
    }


def _ensure_store() -> None:
    _STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
    if _STORE_PATH.exists():
        return
    _STORE_PATH.write_text(json.dumps(_default_store(), indent=2), encoding="utf-8")


def _load_store() -> dict[str, Any]:
    _ensure_store()
    try:
        return json.loads(_STORE_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        data = _default_store()
        _STORE_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return data


def _save_store(store: dict[str, Any]) -> None:
    _STORE_PATH.write_text(json.dumps(store, indent=2), encoding="utf-8")


def get_history() -> HistoryResponse:
    """Return persisted chat, research and saved prompt history."""
    store = _load_store()
    return HistoryResponse(
        chat_history=_validated_rows(list(store.get("chat_history", [])), ChatHistoryItem),
        research_history=_validated_rows(list(store.get("research_history", [])), ResearchHistoryItem),
        saved_prompts=_validated_rows(list(store.get("saved_prompts", [])), SavedPromptItem),
    )


def get_thread_history(thread_id: str) -> ThreadHistoryResponse:
    """Return messages for a thread id (empty if missing)."""
    store = _load_store()
    thread = store.get("threads", {}).get(thread_id, {})
    raw_messages = thread.get("messages", [])
    if not isinstance(raw_messages, list):
        raw_messages = []
    return ThreadHistoryResponse(
        thread_id=thread_id,
        messages=_validated_rows(raw_messages, ThreadMessage),
    )


def save_prompt(title: str, prompt_text: str) -> SavePromptResponse:
    store = _load_store()
    item = SavedPromptItem(id=f"prompt_{uuid.uuid4().hex[:8]}", title=title.strip(), prompt_text=prompt_text.strip())
    saved = store.setdefault("saved_prompts", [])
    saved.insert(0, item.model_dump())
    _save_store(store)
    return SavePromptResponse(saved_prompt=item)


def save_chat_interaction(thread_id: str, user_text: str, assistant_text: str) -> None:
    """Append user+assistant messages and keep chat history updated."""
    store = _load_store()
    ts = _utc_now_iso()
    threads = store.setdefault("threads", {})
    thread_entry = threads.setdefault(thread_id, {"messages": []})
    messages = thread_entry.setdefault("messages", [])
    messages.append({"role": "user", "text": user_text, "timestamp": ts})
    messages.append({"role": "assistant", "text": assistant_text, "timestamp": ts})

    chat_history = store.setdefault("chat_history", [])
    title = user_text.strip()[:90] or "Untitled question"
    existing = next((x for x in chat_history if x.get("thread_id") == thread_id), None)
    if existing:
        existing["last_updated"] = ts
        if not existing.get("title"):
            existing["title"] = title
    else:
        chat_history.insert(0, {"thread_id": thread_id, "title": title, "last_updated": ts})
    _save_store(store)


def save_research_run(kind: str, ticker: str) -> None:
    """Persist a research run marker for sentiment/fundamental workflows."""
    store = _load_store()
    runs = store.setdefault("research_history", [])
    runs.insert(
        0,
        {
            "id": f"research_{uuid.uuid4().hex[:8]}",
            "type": kind,
            "ticker": ticker.upper(),
            "created_at": _utc_now_iso(),
        },
    )
    _save_store(store)
