from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.core.config import settings
from app.schemas.buy_sell_analysis import MemoryBlock

# backend/app/memory/memory_store.py -> parents[3] == StockScope/
_STOCKSCOPE_ROOT = Path(__file__).resolve().parents[3]
_MEMORY_DIR = _STOCKSCOPE_ROOT / "data" / "memory"
_STORE_PATH = _MEMORY_DIR / "sessions.json"

_SESSION_ID_RE = re.compile(r"^[a-zA-Z0-9._-]{1,64}$")


def _sanitize_session_id(session_id: str) -> str:
    s = (session_id or "default").strip() or "default"
    if not _SESSION_ID_RE.match(s):
        return "default"
    return s[:64]


def _ensure_store() -> None:
    _MEMORY_DIR.mkdir(parents=True, exist_ok=True)
    if not _STORE_PATH.exists():
        _STORE_PATH.write_text('{"sessions":{}}', encoding="utf-8")


def _read_all() -> dict[str, Any]:
    _ensure_store()
    try:
        data = json.loads(_STORE_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        data = {"sessions": {}}
    if not isinstance(data, dict):
        data = {"sessions": {}}
    data.setdefault("sessions", {})
    return data


def _write_all(data: dict[str, Any]) -> None:
    _ensure_store()
    tmp = _STORE_PATH.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=True, indent=2), encoding="utf-8")
    tmp.replace(_STORE_PATH)


def _default_session_payload(session_id: str) -> dict[str, Any]:
    now = datetime.now(timezone.utc).isoformat()
    return {
        "session_id": session_id,
        "recent_tickers": [],
        "preferred_horizon": None,
        "analysis_style": "balanced",
        "session_summary": "",
        "updated_at": now,
    }


def load_session(session_id: str) -> dict[str, Any]:
    if not settings.memory_enabled:
        return _default_session_payload(_sanitize_session_id(session_id))
    sid = _sanitize_session_id(session_id)
    data = _read_all()
    sess = data["sessions"].get(sid)
    if not isinstance(sess, dict):
        sess = _default_session_payload(sid)
        data["sessions"][sid] = sess
        _write_all(data)
    sess.setdefault("recent_tickers", [])
    sess.setdefault("analysis_style", "balanced")
    sess.setdefault("session_summary", "")
    sess.setdefault("preferred_horizon", None)
    sess.setdefault("updated_at", datetime.now(timezone.utc).isoformat())
    return sess


def update_session_preferences(
    session_id: str,
    *,
    preferred_horizon: str | None = None,
    analysis_style: str | None = None,
    session_summary: str | None = None,
) -> dict[str, Any]:
    if not settings.memory_enabled:
        return _default_session_payload(_sanitize_session_id(session_id))
    sid = _sanitize_session_id(session_id)
    data = _read_all()
    sess = data["sessions"].get(sid) or _default_session_payload(sid)
    if preferred_horizon is not None:
        v = preferred_horizon.strip()
        sess["preferred_horizon"] = v or None
    if analysis_style is not None:
        s = analysis_style.strip().lower()
        if s in ("balanced", "growth", "income", "value"):
            sess["analysis_style"] = s
    if session_summary is not None:
        sess["session_summary"] = session_summary.strip()[:4000]
    sess["updated_at"] = datetime.now(timezone.utc).isoformat()
    data["sessions"][sid] = sess
    _write_all(data)
    return sess


def record_ticker_analysis(session_id: str, ticker: str) -> dict[str, Any]:
    if not settings.memory_enabled:
        return _default_session_payload(_sanitize_session_id(session_id))
    sid = _sanitize_session_id(session_id)
    sym = ticker.strip().upper()
    data = _read_all()
    sess = data["sessions"].get(sid) or _default_session_payload(sid)
    recent: list[str] = [x for x in sess.get("recent_tickers", []) if isinstance(x, str)]
    recent = [x.upper() for x in recent if x.upper() != sym]
    recent.insert(0, sym)
    cap = max(1, int(settings.memory_max_recent_tickers))
    sess["recent_tickers"] = recent[:cap]
    if not (str(sess.get("session_summary") or "").strip()):
        sess["session_summary"] = _auto_summary(sess["recent_tickers"], "")
    sess["updated_at"] = datetime.now(timezone.utc).isoformat()
    data["sessions"][sid] = sess
    _write_all(data)
    return sess


def _auto_summary(recent: list[str], user_summary: str) -> str:
    if user_summary.strip():
        return user_summary.strip()[:2000]
    if not recent:
        return ""
    head = ", ".join(recent[:8])
    return f"Recent analyses (most recent first): {head}."


def reset_session(session_id: str) -> dict[str, Any]:
    if not settings.memory_enabled:
        return _default_session_payload(_sanitize_session_id(session_id))
    sid = _sanitize_session_id(session_id)
    data = _read_all()
    fresh = _default_session_payload(sid)
    data["sessions"][sid] = fresh
    _write_all(data)
    return fresh


def build_follow_up_context(session: dict[str, Any], current_ticker: str | None = None) -> str:
    """Short string for planner / future LLM turns (Phase 7 retrieval surface)."""
    parts: list[str] = []
    rh = session.get("preferred_horizon")
    if rh:
        parts.append(f"Preferred horizon: {rh}.")
    st = session.get("analysis_style")
    if st:
        parts.append(f"Analysis style preference: {st}.")
    summ = (session.get("session_summary") or "").strip()
    if summ:
        parts.append(f"Session note: {summ[:500]}")
    recent = session.get("recent_tickers") or []
    if isinstance(recent, list) and current_ticker and len(recent) > 1:
        others = [x for x in recent if str(x).upper() != current_ticker.upper()][:5]
        if others:
            parts.append(f"Other tickers in this session: {', '.join(str(x) for x in others)}.")
    return " ".join(parts).strip()


def memory_block_after_analyze(session_id: str, ticker: str) -> MemoryBlock:
    sess = load_session(session_id)
    return MemoryBlock(
        session_id=str(sess.get("session_id") or session_id),
        recent_tickers=[str(x).upper() for x in (sess.get("recent_tickers") or []) if x],
        preferred_horizon=sess.get("preferred_horizon"),
        analysis_style=str(sess.get("analysis_style") or "balanced"),
        session_summary=str(sess.get("session_summary") or ""),
        follow_up_context=build_follow_up_context(sess, ticker),
    )
