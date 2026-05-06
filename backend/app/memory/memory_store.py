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


def _default_memory_profile() -> dict[str, Any]:
    """Long-horizon summary JSON — derived from session activity, surfaced to agentic RAG."""
    return {
        "frequent_tickers": [],
        "preferred_topics": ["fundamentals", "news"],
        "risk_style": "balanced",
    }


def _analysis_style_to_risk_style(style: str) -> str:
    s = (style or "balanced").strip().lower()
    if s == "growth":
        return "moderate"
    if s in ("income", "value"):
        return "cautious"
    return "balanced"


def recompute_memory_profile(sess: dict[str, Any]) -> dict[str, Any]:
    """Refresh memory_profile from recent_tickers, session_summary, and analysis_style."""
    mp = dict(sess.get("memory_profile") or _default_memory_profile())
    recent = [str(x).upper() for x in (sess.get("recent_tickers") or []) if x]
    mp["frequent_tickers"] = recent[:10]

    topics: set[str] = set(mp.get("preferred_topics") or []) if isinstance(mp.get("preferred_topics"), list) else set()
    summ = (sess.get("session_summary") or "").lower()
    for key, label in (
        ("news", "news"),
        ("sentiment", "news"),
        ("headline", "news"),
        ("fundamental", "fundamentals"),
        ("valuation", "fundamentals"),
        ("earnings", "fundamentals"),
        ("technical", "technicals"),
        ("chart", "technicals"),
    ):
        if key in summ:
            topics.add(label)
    if not topics:
        topics = {"fundamentals", "news"}
    mp["preferred_topics"] = sorted(topics)

    mp["risk_style"] = _analysis_style_to_risk_style(str(sess.get("analysis_style") or "balanced"))
    sess["memory_profile"] = mp
    return mp


def memory_profile_for_prompt(sess: dict[str, Any]) -> str:
    """Compact JSON string for planner/writer context."""
    mp = sess.get("memory_profile") or recompute_memory_profile(sess)
    try:
        return json.dumps(mp, ensure_ascii=True)
    except (TypeError, ValueError):
        return "{}"


def apply_eval_memory_seed(session_id: str, seed: dict[str, Any]) -> dict[str, Any]:
    """Merge seed into session for batch eval (frequent_tickers, memory_profile fields)."""
    if not settings.memory_enabled:
        return _default_session_payload(_sanitize_session_id(session_id))
    sid = _sanitize_session_id(session_id)
    data = _read_all()
    sess = data["sessions"].get(sid) or _default_session_payload(sid)
    if freq := seed.get("frequent_tickers"):
        if isinstance(freq, list):
            sess["recent_tickers"] = [str(x).upper() for x in freq if x][:30]
    if isinstance(seed.get("memory_profile"), dict):
        base = dict(sess.get("memory_profile") or _default_memory_profile())
        base.update(seed["memory_profile"])
        sess["memory_profile"] = base
    if seed.get("session_summary") is not None:
        sess["session_summary"] = str(seed["session_summary"])[:4000]
    if seed.get("analysis_style") is not None:
        s = str(seed["analysis_style"]).strip().lower()
        if s in ("balanced", "growth", "income", "value"):
            sess["analysis_style"] = s
    recompute_memory_profile(sess)
    if isinstance(seed.get("memory_profile"), dict):
        mp = dict(sess["memory_profile"])
        for k, v in seed["memory_profile"].items():
            if v is not None:
                mp[k] = v
        sess["memory_profile"] = mp
    sess["updated_at"] = datetime.now(timezone.utc).isoformat()
    data["sessions"][sid] = sess
    _write_all(data)
    return sess


def touch_agentic_session(session_id: str, ticker: str, question: str) -> dict[str, Any]:
    """After an agentic run: bump recent tickers and topic hints from the question."""
    if not settings.memory_enabled:
        return _default_session_payload(_sanitize_session_id(session_id))
    record_ticker_analysis(session_id, ticker)
    sid = _sanitize_session_id(session_id)
    data = _read_all()
    sess = data["sessions"].get(sid) or _default_session_payload(sid)
    merge_topics_from_question(sess, question)
    recompute_memory_profile(sess)
    sess["updated_at"] = datetime.now(timezone.utc).isoformat()
    data["sessions"][sid] = sess
    _write_all(data)
    return sess


def merge_topics_from_question(sess: dict[str, Any], question: str) -> None:
    q = (question or "").lower()
    mp = dict(sess.get("memory_profile") or _default_memory_profile())
    topics = set(mp.get("preferred_topics") or []) if isinstance(mp.get("preferred_topics"), list) else set()
    if not topics:
        topics = {"fundamentals", "news"}
    if any(x in q for x in ("news", "headline", "sentiment", "article")):
        topics.add("news")
    if any(x in q for x in ("fundamental", "pe ratio", "valuation", "earnings", "margin")):
        topics.add("fundamentals")
    if any(x in q for x in ("technical", "chart", "momentum", "moving average")):
        topics.add("technicals")
    if any(x in q for x in ("compare", "versus", " vs ")):
        topics.add("comparison")
    mp["preferred_topics"] = sorted(topics)
    sess["memory_profile"] = mp


def _default_session_payload(session_id: str) -> dict[str, Any]:
    now = datetime.now(timezone.utc).isoformat()
    return {
        "session_id": session_id,
        "recent_tickers": [],
        "preferred_horizon": None,
        "analysis_style": "balanced",
        "session_summary": "",
        "memory_profile": _default_memory_profile(),
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
    migrated = False
    if "memory_profile" not in sess or not isinstance(sess.get("memory_profile"), dict):
        sess["memory_profile"] = _default_memory_profile()
        recompute_memory_profile(sess)
        migrated = True
    if migrated:
        data["sessions"][sid] = sess
        _write_all(data)
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
    sess.setdefault("memory_profile", _default_memory_profile())
    recompute_memory_profile(sess)
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
    sess.setdefault("memory_profile", _default_memory_profile())
    recompute_memory_profile(sess)
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
    recompute_memory_profile(fresh)
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
    mp = sess.get("memory_profile")
    if not isinstance(mp, dict):
        mp = {}
    return MemoryBlock(
        session_id=str(sess.get("session_id") or session_id),
        recent_tickers=[str(x).upper() for x in (sess.get("recent_tickers") or []) if x],
        preferred_horizon=sess.get("preferred_horizon"),
        analysis_style=str(sess.get("analysis_style") or "balanced"),
        session_summary=str(sess.get("session_summary") or ""),
        follow_up_context=build_follow_up_context(sess, ticker),
        memory_profile=dict(mp),
    )
