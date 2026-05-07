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


_MEMORY_TOPIC_ALLOWLIST = frozenset(
    {"fundamentals", "news", "buy_sell", "sentiment", "market_movers"},
)
_MEMORY_MAX_FREQUENT_TICKERS = 20

_CAUTIOUS_RISK_RE = re.compile(
    r"\b(cautious|conservative|risk-averse|risk averse|downside|drawdown|volatil|"
    r"worried|scared|safe(?:ty)?|capital preservation|don't lose|do not lose|"
    r"protect (?:my )?(?:money|capital)|low risk)\b",
    re.IGNORECASE,
)


def _utc_now_iso_ms() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _default_memory_summary() -> dict[str, Any]:
    return {
        "frequent_tickers": [],
        "preferred_topics": [],
        "risk_style": None,
        "last_updated": _utc_now_iso_ms(),
    }


def _default_memory_profile() -> dict[str, Any]:
    """Backward-compatible shape; kept in sync from memory_summary."""
    return {
        "frequent_tickers": [],
        "preferred_topics": [],
        "risk_style": None,
    }


def _coerce_topics(topics: list[Any]) -> list[str]:
    out: list[str] = []
    legacy = {
        "fundamental": "fundamentals",
        "technicals": "fundamentals",
        "comparison": "fundamentals",
    }
    for t in topics:
        s = str(t).strip().lower()
        s = legacy.get(s, s)
        if s in _MEMORY_TOPIC_ALLOWLIST and s not in out:
            out.append(s)
    return sorted(out)


def _ensure_memory_summary(sess: dict[str, Any]) -> dict[str, Any]:
    ms = sess.get("memory_summary")
    if not isinstance(ms, dict):
        ms = _default_memory_summary()
        sess["memory_summary"] = ms
    ms.setdefault("frequent_tickers", [])
    ms.setdefault("preferred_topics", [])
    if "risk_style" not in ms:
        ms["risk_style"] = None
    ms.setdefault("last_updated", _utc_now_iso_ms())
    if not isinstance(ms.get("frequent_tickers"), list):
        ms["frequent_tickers"] = []
    if not isinstance(ms.get("preferred_topics"), list):
        ms["preferred_topics"] = []
    return ms


def _migrate_profile_to_summary_if_needed(sess: dict[str, Any]) -> None:
    """One-time: copy legacy memory_profile into memory_summary when summary is empty."""
    ms = _ensure_memory_summary(sess)
    if (ms.get("frequent_tickers") or ms.get("preferred_topics")) and ms.get("last_updated"):
        return
    mp = sess.get("memory_profile")
    if not isinstance(mp, dict):
        return
    ft = mp.get("frequent_tickers")
    if isinstance(ft, list) and ft:
        ms["frequent_tickers"] = _coerce_tickers_list([str(x).upper() for x in ft if x])
    pt = mp.get("preferred_topics")
    if isinstance(pt, list) and pt:
        ms["preferred_topics"] = _coerce_topics(pt)
    rs = mp.get("risk_style")
    if rs in ("cautious", "moderate", "balanced") or rs is None:
        ms["risk_style"] = "cautious" if rs in ("cautious", "moderate") else None
    ms["last_updated"] = _utc_now_iso_ms()


def _coerce_tickers_list(symbols: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for s in symbols:
        u = str(s).strip().upper()
        if u and u not in seen:
            seen.add(u)
            out.append(u)
    return out[:_MEMORY_MAX_FREQUENT_TICKERS]


def _prepend_tickers_memory_summary(sess: dict[str, Any], symbols: list[str]) -> None:
    if not symbols:
        return
    ms = _ensure_memory_summary(sess)
    cur = [str(x).upper() for x in ms.get("frequent_tickers") or [] if x]
    for s in reversed(_coerce_tickers_list(symbols)):
        if s in cur:
            cur.remove(s)
        cur.insert(0, s)
    ms["frequent_tickers"] = cur[:_MEMORY_MAX_FREQUENT_TICKERS]
    ms["last_updated"] = _utc_now_iso_ms()


def infer_preferred_topics(
    user_text: str,
    *,
    tools_used: list[str] | None = None,
    intent: str | None = None,
    session_summary_snippet: str | None = None,
) -> list[str]:
    """Map activity to rubric topic labels (subset of allowlist)."""
    parts = [user_text or "", session_summary_snippet or ""]
    blob = " ".join(parts).lower()

    found: set[str] = set()

    if tools_used:
        for t in tools_used:
            tt = str(t).strip().lower()
            if tt == "fundamental":
                found.add("fundamentals")
            elif tt == "news_sentiment":
                if any(x in blob for x in ("sentiment", "bullish", "bearish", "tone", "mood", "feeling")):
                    found.add("sentiment")
                found.add("news")
            elif tt == "buy_sell":
                found.add("buy_sell")
            elif tt == "history":
                pass

    if intent == "sentiment_question":
        found.add("sentiment")
    if intent == "comparison_question":
        found.add("fundamentals")
    if intent == "stock_explanation":
        found.add("news")

    if any(x in blob for x in ("market mover", "movers", "gainers", "losers", "most active", "biggest", "heatmap")):
        found.add("market_movers")
    if any(
        x in blob
        for x in (
            "sentiment",
            "bullish",
            "bearish",
            "fear",
            "greed",
            "mood",
            "tone of news",
        )
    ):
        found.add("sentiment")
    if any(
        x in blob
        for x in (
            "fundamental",
            "p/e",
            "pe ratio",
            "valuation",
            "earnings",
            "revenue",
            "margin",
            "balance sheet",
            "cash flow",
            "dividend yield",
        )
    ):
        found.add("fundamentals")
    if any(x in blob for x in ("news", "headline", "article", "story", "reported", "breaking")):
        found.add("news")
    if any(
        x in blob
        for x in (
            "should i buy",
            "should i sell",
            "buy or sell",
            "bull case",
            "bear case",
            "thesis",
            "price target",
        )
    ):
        found.add("buy_sell")

    return sorted(found & _MEMORY_TOPIC_ALLOWLIST)


def user_text_suggests_cautious_risk(user_text: str) -> bool:
    return bool(_CAUTIOUS_RISK_RE.search(user_text or ""))


def _analysis_style_implies_cautious(sess: dict[str, Any]) -> bool:
    s = str(sess.get("analysis_style") or "balanced").strip().lower()
    return s in ("income", "value")


def _sync_memory_profile_from_summary(sess: dict[str, Any]) -> dict[str, Any]:
    ms = _ensure_memory_summary(sess)
    mp = {
        "frequent_tickers": list(ms.get("frequent_tickers") or []),
        "preferred_topics": list(ms.get("preferred_topics") or []),
        "risk_style": ms.get("risk_style"),
    }
    sess["memory_profile"] = mp
    return mp


def recompute_memory_profile(sess: dict[str, Any]) -> dict[str, Any]:
    """Refresh memory_profile from memory_summary and session prefs (backward compat)."""
    _migrate_profile_to_summary_if_needed(sess)
    ms = _ensure_memory_summary(sess)
    if _analysis_style_implies_cautious(sess):
        ms["risk_style"] = "cautious"
        ms["last_updated"] = _utc_now_iso_ms()
    summ_topics = infer_preferred_topics(
        "",
        session_summary_snippet=(sess.get("session_summary") or "")[:2000],
    )
    if summ_topics:
        merged = _coerce_topics(list(ms.get("preferred_topics") or []) + summ_topics)
        ms["preferred_topics"] = merged
        ms["last_updated"] = _utc_now_iso_ms()
    return _sync_memory_profile_from_summary(sess)


def memory_summary_dict(sess: dict[str, Any]) -> dict[str, Any]:
    """Public memory_summary shape for APIs."""
    _migrate_profile_to_summary_if_needed(sess)
    ms = _ensure_memory_summary(sess)
    return {
        "frequent_tickers": [str(x).upper() for x in ms.get("frequent_tickers") or [] if x],
        "preferred_topics": list(ms.get("preferred_topics") or []),
        "risk_style": ms.get("risk_style"),
        "last_updated": str(ms.get("last_updated") or _utc_now_iso_ms()),
    }


def memory_summary_for_prompt(sess: dict[str, Any]) -> str:
    """JSON for planner/writer: preferences only, not a fact source."""
    try:
        return json.dumps(memory_summary_dict(sess), ensure_ascii=True)
    except (TypeError, ValueError):
        return "{}"


def memory_profile_for_prompt(sess: dict[str, Any]) -> str:
    """Alias: prompts use long-horizon user memory summary JSON."""
    return memory_summary_for_prompt(sess)


def merge_memory_after_interaction(
    sess: dict[str, Any],
    *,
    user_text: str,
    tickers: list[str],
    tools_used: list[str] | None = None,
    intent: str | None = None,
) -> dict[str, Any]:
    """Update memory_summary from one completed turn (chat or agentic)."""
    ms = _ensure_memory_summary(sess)
    _prepend_tickers_memory_summary(sess, tickers)
    new_topics = infer_preferred_topics(
        user_text,
        tools_used=tools_used,
        intent=intent,
        session_summary_snippet=(sess.get("session_summary") or "")[:1500],
    )
    if new_topics:
        ms["preferred_topics"] = _coerce_topics(list(ms.get("preferred_topics") or []) + new_topics)
    if user_text_suggests_cautious_risk(user_text):
        ms["risk_style"] = "cautious"
    if _analysis_style_implies_cautious(sess):
        ms["risk_style"] = "cautious"
    ms["last_updated"] = _utc_now_iso_ms()
    return _sync_memory_profile_from_summary(sess)


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
    if seed.get("session_summary") is not None:
        sess["session_summary"] = str(seed["session_summary"])[:4000]
    if seed.get("analysis_style") is not None:
        s = str(seed["analysis_style"]).strip().lower()
        if s in ("balanced", "growth", "income", "value"):
            sess["analysis_style"] = s

    ms = _ensure_memory_summary(sess)
    if freq and isinstance(freq, list):
        ms["frequent_tickers"] = _coerce_tickers_list([str(x).upper() for x in freq if x])
    if isinstance(seed.get("memory_summary"), dict):
        sm = seed["memory_summary"]
        if isinstance(sm.get("frequent_tickers"), list):
            ms["frequent_tickers"] = _coerce_tickers_list(
                [str(x).upper() for x in sm["frequent_tickers"] if x]
            )
        if isinstance(sm.get("preferred_topics"), list):
            ms["preferred_topics"] = _coerce_topics(sm["preferred_topics"])
        if sm.get("risk_style") is not None:
            ms["risk_style"] = sm["risk_style"]
    if isinstance(seed.get("memory_profile"), dict):
        mp_seed = seed["memory_profile"]
        if isinstance(mp_seed.get("frequent_tickers"), list):
            ms["frequent_tickers"] = _coerce_tickers_list(
                [str(x).upper() for x in mp_seed["frequent_tickers"] if x]
            )
        if isinstance(mp_seed.get("preferred_topics"), list):
            ms["preferred_topics"] = _coerce_topics(mp_seed["preferred_topics"])
        if mp_seed.get("risk_style") is not None:
            ms["risk_style"] = mp_seed["risk_style"]
    ms["last_updated"] = _utc_now_iso_ms()
    _sync_memory_profile_from_summary(sess)

    recompute_memory_profile(sess)
    if isinstance(seed.get("memory_profile"), dict):
        mp = dict(sess["memory_profile"])
        for k, v in seed["memory_profile"].items():
            if v is not None:
                mp[k] = v
        sess["memory_profile"] = mp
        _ensure_memory_summary(sess)
        if isinstance(mp.get("frequent_tickers"), list):
            ms["frequent_tickers"] = _coerce_tickers_list(
                [str(x).upper() for x in mp["frequent_tickers"] if x]
            )
        if isinstance(mp.get("preferred_topics"), list):
            ms["preferred_topics"] = _coerce_topics(mp["preferred_topics"])
        if mp.get("risk_style") is not None:
            ms["risk_style"] = mp.get("risk_style")
        ms["last_updated"] = _utc_now_iso_ms()
        _sync_memory_profile_from_summary(sess)

    sess["updated_at"] = datetime.now(timezone.utc).isoformat()
    data["sessions"][sid] = sess
    _write_all(data)
    return sess


def touch_chat_session(
    session_id: str,
    *,
    user_query: str,
    tickers: list[str],
    tools_used: list[str] | None,
    intent: str | None,
) -> dict[str, Any]:
    """After a chatbot turn: merge tickers/topics/risk hints into memory_summary."""
    if not settings.memory_enabled:
        return _default_session_payload(_sanitize_session_id(session_id))
    sid = _sanitize_session_id(session_id)
    data = _read_all()
    sess = data["sessions"].get(sid) or _default_session_payload(sid)
    merge_memory_after_interaction(
        sess,
        user_text=user_query or "",
        tickers=tickers,
        tools_used=tools_used,
        intent=intent,
    )
    recompute_memory_profile(sess)
    sess["updated_at"] = datetime.now(timezone.utc).isoformat()
    data["sessions"][sid] = sess
    _write_all(data)
    return sess


def touch_agentic_session(
    session_id: str,
    ticker: str,
    question: str,
    tools_used: list[str] | None = None,
) -> dict[str, Any]:
    """After an agentic run: bump recent tickers and merge question/tools into memory_summary."""
    if not settings.memory_enabled:
        return _default_session_payload(_sanitize_session_id(session_id))
    record_ticker_analysis(session_id, ticker)
    sid = _sanitize_session_id(session_id)
    data = _read_all()
    sess = data["sessions"].get(sid) or _default_session_payload(sid)
    merge_memory_after_interaction(
        sess,
        user_text=question or "",
        tickers=[ticker.strip().upper()] if ticker else [],
        tools_used=tools_used,
        intent=None,
    )
    recompute_memory_profile(sess)
    sess["updated_at"] = datetime.now(timezone.utc).isoformat()
    data["sessions"][sid] = sess
    _write_all(data)
    return sess


def merge_topics_from_question(sess: dict[str, Any], question: str) -> None:
    """Backward-compatible: merge topic hints from a natural-language question."""
    merge_memory_after_interaction(
        sess,
        user_text=question or "",
        tickers=[],
        tools_used=None,
        intent=None,
    )


def _default_session_payload(session_id: str) -> dict[str, Any]:
    now = datetime.now(timezone.utc).isoformat()
    summary = _default_memory_summary()
    return {
        "session_id": session_id,
        "recent_tickers": [],
        "preferred_horizon": None,
        "analysis_style": "balanced",
        "session_summary": "",
        "memory_summary": summary,
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
    needs_memory_summary_persist = "memory_summary" not in sess
    sess.setdefault("memory_summary", _default_memory_summary())
    _migrate_profile_to_summary_if_needed(sess)
    migrated = False
    if "memory_profile" not in sess or not isinstance(sess.get("memory_profile"), dict):
        sess["memory_profile"] = _default_memory_profile()
        recompute_memory_profile(sess)
        migrated = True
    else:
        _sync_memory_profile_from_summary(sess)
    if migrated or needs_memory_summary_persist:
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
    _ensure_memory_summary(sess)
    _prepend_tickers_memory_summary(sess, [sym])
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
