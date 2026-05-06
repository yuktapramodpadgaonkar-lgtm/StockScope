"""History service with lightweight JSON persistence.

Per-user isolation: when an email is provided, history is stored in a
user-specific file (data/history_<md5>.json).  When no email is given the
global history_store.json is used so unauthenticated calls keep working.
"""

from __future__ import annotations

import hashlib
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

_DATA_DIR = Path(__file__).resolve().parents[1] / "data"
_GLOBAL_STORE = _DATA_DIR / "history_store.json"

M = TypeVar("M", bound=BaseModel)


# ── Path helpers ──────────────────────────────────────────────────────────────

def _store_path(email: str | None = None) -> Path:
    if email:
        h = hashlib.md5(email.strip().lower().encode()).hexdigest()[:16]
        return _DATA_DIR / f"history_{h}.json"
    return _GLOBAL_STORE


def _validated_rows(raw: list[Any], model: Type[M]) -> list[M]:
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


def _ensure_store(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        return
    # New user files start empty; only the global file gets demo data
    if path == _GLOBAL_STORE:
        path.write_text(json.dumps(_default_store(), indent=2), encoding="utf-8")
    else:
        path.write_text(
            json.dumps({"chat_history": [], "research_history": [], "saved_prompts": [], "threads": {}}, indent=2),
            encoding="utf-8",
        )


def _load_store(email: str | None = None) -> dict[str, Any]:
    path = _store_path(email)
    _ensure_store(path)
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        data = _default_store() if path == _GLOBAL_STORE else {"chat_history": [], "research_history": [], "saved_prompts": [], "threads": {}}
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return data


def _save_store(store: dict[str, Any], email: str | None = None) -> None:
    _store_path(email).write_text(json.dumps(store, indent=2), encoding="utf-8")


# ── Public API ────────────────────────────────────────────────────────────────

def get_history(email: str | None = None) -> HistoryResponse:
    """Return chat, research and saved prompt history for this user (or global)."""
    store = _load_store(email)
    return HistoryResponse(
        chat_history=_validated_rows(list(store.get("chat_history", [])), ChatHistoryItem),
        research_history=_validated_rows(list(store.get("research_history", [])), ResearchHistoryItem),
        saved_prompts=_validated_rows(list(store.get("saved_prompts", [])), SavedPromptItem),
    )


def get_thread_history(thread_id: str, email: str | None = None) -> ThreadHistoryResponse:
    store = _load_store(email)
    thread = store.get("threads", {}).get(thread_id, {})
    raw_messages = thread.get("messages", [])
    if not isinstance(raw_messages, list):
        raw_messages = []
    return ThreadHistoryResponse(
        thread_id=thread_id,
        messages=_validated_rows(raw_messages, ThreadMessage),
    )


def save_prompt(title: str, prompt_text: str, email: str | None = None) -> SavePromptResponse:
    store = _load_store(email)
    item = SavedPromptItem(
        id=f"prompt_{uuid.uuid4().hex[:8]}",
        title=title.strip(),
        prompt_text=prompt_text.strip(),
    )
    store.setdefault("saved_prompts", []).insert(0, item.model_dump())
    _save_store(store, email)
    return SavePromptResponse(saved_prompt=item)


def save_chat_interaction(
    thread_id: str,
    user_text: str,
    assistant_text: str,
    intent: str | None = None,
    model_used: str | None = None,
    provider: str | None = None,
    fallback_used: bool | None = None,
    email: str | None = None,
) -> None:
    store = _load_store(email)
    ts = _utc_now_iso()

    threads = store.setdefault("threads", {})
    thread_entry = threads.setdefault(thread_id, {"messages": []})
    messages = thread_entry.setdefault("messages", [])
    messages.append({"role": "user", "text": user_text, "timestamp": ts})

    assistant_msg: dict[str, Any] = {"role": "assistant", "text": assistant_text, "timestamp": ts}
    if intent is not None:
        assistant_msg["intent"] = intent
    if model_used is not None:
        assistant_msg["model_used"] = model_used
    if provider is not None:
        assistant_msg["provider"] = provider
    if fallback_used is not None:
        assistant_msg["fallback_used"] = fallback_used
    messages.append(assistant_msg)

    chat_history = store.setdefault("chat_history", [])
    title = user_text.strip()[:90] or "Untitled question"
    existing = next((x for x in chat_history if x.get("thread_id") == thread_id), None)
    if existing:
        existing["last_updated"] = ts
        if not existing.get("title"):
            existing["title"] = title
    else:
        chat_history.insert(0, {"thread_id": thread_id, "title": title, "last_updated": ts})

    _save_store(store, email)


def save_research_run(
    kind: str,
    ticker: str,
    model_used: str | None = None,
    provider: str | None = None,
    email: str | None = None,
) -> None:
    store = _load_store(email)
    entry: dict[str, Any] = {
        "id": f"research_{uuid.uuid4().hex[:8]}",
        "type": kind,
        "ticker": ticker.upper(),
        "created_at": _utc_now_iso(),
    }
    if model_used is not None:
        entry["model_used"] = model_used
    if provider is not None:
        entry["provider"] = provider
    store.setdefault("research_history", []).insert(0, entry)
    _save_store(store, email)
