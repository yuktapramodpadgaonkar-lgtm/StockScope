"""
Chatbot service — Agentic Chat (Planner → Executor → Writer → Critic).

This upgrades the chatbot from intent-routed single prompts to a tool-using agent:
  1) Safety gate: reject direct financial advice requests.
  2) Planner: LLM chooses a short tool plan (JSON steps).
  3) Executor: runs tools, builds normalized evidence + citations.
  4) Writer: LLM writes {answer, bullets, citations_used} JSON.
  5) Critic: rule checks for safety + grounding; one repair pass if needed.
"""

from __future__ import annotations

import json
import re
import uuid
from datetime import datetime, timezone

from app.schemas.chat import ChatCitation, ChatIntent, ChatQueryResponse
from app.agentic.unified_evidence import build_normalized_evidence
from app.observability.jsonl_audit import log_model_call, log_tool_call
from app.services.fundamental_service import get_fundamental_report
from app.agents.orchestrator import run_buy_sell_with_agents
from services.ai.llm_service import LLMService
from services.ai.prompts import (
    build_agentic_chat_plan_prompt,
    build_agentic_chat_repair_prompt,
    build_agentic_chat_writer_prompt,
)
from services.history_service import get_history, save_chat_interaction
from services.news_sentiment_service import build_news_sentiment_report

_DISCLAIMER = "This response is for educational purposes only and is not financial advice."
_TICKER_RE = re.compile(r"\b[A-Z]{1,5}\b")
_llm = LLMService()
_NUM_RE = re.compile(r"\b\d+(?:\.\d+)?\b")

_NEWS_CLAIM_RE = re.compile(
    r"\b(news|headlines?|articles?|reported|according to|filing|sec\b|10-k|10-q|8-k|press release)\b",
    re.IGNORECASE,
)

_STOPWORDS = frozenset(
    {"WHY", "WHAT", "HOW", "THE", "AND", "IS", "ARE", "FOR", "CAN", "YOU",
     "ME", "MY", "ON", "IN", "AT", "TO", "OF", "IT", "THIS", "THAT", "DO",
     "DOES", "GET", "HELP", "TELL", "SHOW", "GIVE", "WILL", "WAS", "HAS",
     "BUY", "SELL", "HOLD", "NEWS"}
)


# ── Helpers ──────────────────────────────────────────────────────────────────

def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _extract_tickers(query: str) -> list[str]:
    dedup: list[str] = []
    for m in _TICKER_RE.finditer(query.upper()):
        t = m.group(0)
        if t not in _STOPWORDS and t not in dedup:
            dedup.append(t)
    return dedup[:4]


# ── Safety layer ──────────────────────────────────────────────────────────────

_ADVICE_PATTERNS = re.compile(
    r"\b(should i (buy|sell|invest|hold|short)|what (should i|do i) (buy|sell|invest|pick)|"
    r"best stock(s)? to buy|recommend(ation)?s? (for|to) (buy|invest)|"
    r"is .{1,30} a good (buy|investment|stock)|"
    r"tell me what to (buy|invest|trade)|give me (stock )?(picks|tips|advice)|"
    r"what (stock|shares?) should i|top (stocks|picks) (to|for) (buy|invest))\b",
    re.IGNORECASE,
)


def _is_financial_advice(query: str) -> bool:
    return bool(_ADVICE_PATTERNS.search(query))


# ── Intent detection ──────────────────────────────────────────────────────────

def _detect_intent(query: str) -> ChatIntent:
    q = query.lower().strip()
    padded = f" {q} "

    if any(m in padded for m in (" compare ", " vs ", " versus ", " vs. ", " better than ")):
        return "comparison_question"
    if "history" in q or "previous" in q or "last time" in q:
        return "history_lookup"

    sentiment_markers = (
        "sentiment", "bullish", "bearish", "news tone", "headlines",
        "how is the market feeling",
    )
    if any(m in q for m in sentiment_markers):
        return "sentiment_question"

    explanation_markers = (
        "why ", "why is", "how come", "what caused", "explain",
        " up today", " down today", "moving",
    )
    if any(m in q for m in explanation_markers) or re.search(
        r"\b(up|down|rise|fall|surge|drop)\b", q
    ):
        return "stock_explanation"

    return "unknown"

def _parse_json_strict(raw: str) -> dict:
    s = (raw or "").strip()
    if s.startswith("```"):
        parts = s.split("```")
        if len(parts) >= 2:
            s = parts[1].strip()
        if s.lower().startswith("json"):
            s = s[4:].strip()
    start, end = s.find("{"), s.rfind("}")
    if start == -1 or end <= start:
        raise ValueError("No JSON object found")
    return json.loads(s[start : end + 1])


def _parse_plan_steps(raw: str) -> list[dict]:
    obj = _parse_json_strict(raw)
    steps = obj.get("steps") or []
    if not isinstance(steps, list):
        return []
    out: list[dict] = []
    for s in steps[:6]:
        if not isinstance(s, dict):
            continue
        tool = str(s.get("tool") or "").strip()
        args = s.get("args") if isinstance(s.get("args"), dict) else {}
        if tool:
            out.append({"tool": tool, "args": dict(args)})
    return out


def _parse_writer(raw: str) -> tuple[str, list[str], list[int]]:
    obj = _parse_json_strict(raw)
    answer = str(obj.get("answer") or "").strip()
    bullets_raw = obj.get("bullets") or []
    bullets = [str(x).strip() for x in bullets_raw[:5] if str(x).strip()] if isinstance(bullets_raw, list) else []
    used = obj.get("citations_used") or []
    if not isinstance(used, list):
        used = []
    citations_used = [int(x) for x in used if str(x).isdigit()]
    return answer, bullets, citations_used


# ── Response builders ─────────────────────────────────────────────────────────

def _build_citation(c: object) -> ChatCitation:
    return ChatCitation(
        title=c.title,  # type: ignore[attr-defined]
        url=c.url,  # type: ignore[attr-defined]
        source=c.source,  # type: ignore[attr-defined]
        published_at=c.published_at,  # type: ignore[attr-defined]
    )

def _significant_numbers(text: str) -> list[str]:
    found: list[str] = []
    for m in _NUM_RE.finditer(text or ""):
        s = m.group(0)
        if "." in s:
            found.append(s)
            continue
        try:
            n = int(s)
        except ValueError:
            continue
        if 1990 <= n <= 2035:
            continue
        if n < 10:
            continue
        found.append(s)
    return found


def _evidence_corpus(evidence: list[dict]) -> str:
    parts: list[str] = []
    for e in evidence:
        parts.append(str(e.get("title") or ""))
        parts.append(str(e.get("text") or ""))
        nf = e.get("numeric_facts") or {}
        if isinstance(nf, dict):
            parts.append(json.dumps(nf, ensure_ascii=False))
    return " ".join(parts)


def _tickers_in_answer(answer: str) -> set[str]:
    out: set[str] = set()
    for m in _TICKER_RE.finditer((answer or "").upper()):
        t = m.group(0)
        if t not in _STOPWORDS and len(t) >= 2:
            out.add(t)
    return out


def _run_chat_critic(
    *,
    answer: str,
    citations: list[ChatCitation],
    citations_used: list[int],
    evidence: list[dict],
    request_tickers: list[str],
) -> tuple[bool, list[str], list[str]]:
    notes: list[str] = []
    failed: list[str] = []

    if _is_financial_advice(answer or ""):
        failed.append("direct_financial_advice_pattern")
        notes.append("Answer matches advice-seeking phrasing heuristics.")

    if citations_used and any(i < 1 or i > len(citations) for i in citations_used):
        failed.append("citation_index_invalid")
        notes.append("citations_used contains an invalid index.")

    ev_tickers = {str(e.get("ticker") or "").upper() for e in evidence if e.get("ticker")}
    allowed = set(t.upper() for t in request_tickers) | ev_tickers
    bad = sorted({t for t in _tickers_in_answer(answer) if t not in allowed})
    if bad:
        failed.append("answer_ticker_not_in_evidence")
        notes.append(f"Ticker(s) {bad} appear in the answer but not in evidence.")

    corpus = _evidence_corpus(evidence)
    for num in _significant_numbers(answer):
        if num not in corpus:
            failed.append("numeric_claim_not_in_evidence")
            notes.append(f"Numeric token '{num}' not found in evidence corpus.")
            break

    if _NEWS_CLAIM_RE.search(answer or "") and not citations_used:
        failed.append("news_or_filing_claim_without_citation")
        notes.append("Answer references news/filings but citations_used is empty.")

    return len(failed) == 0, notes, failed


def _response_advice_rejected(
    query: str,
    thread_id: str,
    ts: str,
    tickers: list[str],
) -> ChatQueryResponse:
    return ChatQueryResponse(
        thread_id=thread_id,
        detected_intent="financial_advice_rejected",
        tickers=tickers,
        answer=(
            "StockScope is an educational tool and cannot provide personalised "
            "investment advice or stock recommendations. "
            "Instead, try asking: 'Why is AAPL moving today?' or "
            "'What is the current sentiment for NVDA?'"
        ),
        summary_bullets=[
            "Providing specific buy/sell recommendations falls outside our scope.",
            "Use the news sentiment and buy-sell analysis features for objective data.",
            "Always consult a licensed financial adviser before making investment decisions.",
        ],
        citations=[],
        disclaimer=_DISCLAIMER,
        timestamp=ts,
        safety_triggered=True,
    )


# ── Public entry point ────────────────────────────────────────────────────────

def handle_chat_query(
    query: str,
    thread_id: str | None,
    model_name: str | None = None,
) -> ChatQueryResponse:
    """
    Produce a structured chat response for the given user query.

    Raises:
        ValueError: if query is empty after strip.
    """
    text = query.strip()
    if not text:
        raise ValueError("query is required")

    tid = (thread_id or "").strip() or f"thread_{uuid.uuid4().hex[:12]}"
    ts = _utc_now_iso()
    tickers = _extract_tickers(text)
    intent = _detect_intent(text)

    # Step 1: Safety gate.
    if _is_financial_advice(text):
        response = _response_advice_rejected(text, tid, ts, tickers)
        save_chat_interaction(
            tid, text, response.answer,
            intent="financial_advice_rejected",
        )
        return response

    # Step 2: Agentic planner
    allowed: list[str] = ["fundamental", "news_sentiment"]
    if intent == "history_lookup" or "history" in text.lower():
        allowed.append("history")
    if tickers and any(x in text.lower() for x in ("thesis", "risk/reward", "buy/sell", "setup", "confidence")):
        allowed.append("buy_sell")
    allowed = sorted(set(allowed))
    planner_hint = ""
    plan_retry_attempted = False
    steps: list[dict] = []
    plan_result = None

    for attempt in range(2):
        plan_prompt = build_agentic_chat_plan_prompt(
            query=text,
            tickers_detected=tickers,
            allowed_tools=allowed,
            planner_retry_hint=planner_hint,
        )
        plan_result = _llm.generate_response(plan_prompt, preferred_model=model_name or "gemini")
        log_model_call(
            provider=plan_result.provider or "none",
            model=plan_result.model_used or "none",
            task="chat.plan_retry" if plan_retry_attempted else "chat.plan",
            prompt=plan_prompt,
            output=plan_result.response,
            latency_ms=round(plan_result.latency_ms or 0.0, 2) if hasattr(plan_result, "latency_ms") else None,
            error=plan_result.error,
        )
        if plan_result.error or not plan_result.response:
            if attempt == 0:
                plan_retry_attempted = True
                planner_hint = "Return ONLY valid JSON with at least 2 steps for ticker questions, e.g. fundamental + news_sentiment."
                continue
            break
        try:
            steps = [s for s in _parse_plan_steps(plan_result.response) if s.get("tool") in allowed][:4]
        except Exception:
            steps = []
        if tickers and len({s.get("tool") for s in steps if s.get("tool") != "history"}) < 2:
            if attempt == 0:
                plan_retry_attempted = True
                planner_hint = "You MUST use at least two distinct non-history tools: fundamental + news_sentiment."
                continue
        break

    # Step 3: Execute tools
    citations: list[ChatCitation] = []
    step_bundles: list[tuple[str, dict]] = []

    def _add_citation(title: str, url: str, source: str = "", published_at: str = "") -> None:
        if not url.strip():
            return
        citations.append(ChatCitation(title=title[:200], url=url, source=source or "", published_at=published_at or ""))

    for st in steps:
        tool = st.get("tool") or ""
        args = st.get("args") or {}
        try:
            if tool == "fundamental":
                sym = str(args.get("ticker") or (tickers[0] if tickers else "AAPL")).upper()
                rep = get_fundamental_report(sym)
                step_bundles.append(("fundamental", {"tool": "fundamental", "report": rep}))
                _add_citation(f"{sym} fundamentals (yfinance)", f"https://finance.yahoo.com/quote/{sym}", "yfinance", "")
                log_tool_call(tool_name="chat.fundamental", input_summary=f"ticker={sym}", output_summary="ok", latency_ms=None, error=None)
            elif tool == "news_sentiment":
                sym = str(args.get("ticker") or (tickers[0] if tickers else "AAPL")).upper()
                max_articles = int(args.get("max_articles") or 5)
                ns = build_news_sentiment_report(sym, None, None, max_articles=max_articles)
                step_bundles.append(("news_sentiment", {"tool": "news_sentiment", "report": ns.model_dump(mode="json")}))
                for c in ns.citations[:8]:
                    _add_citation(c.title, c.url, c.source, c.published_at)
                log_tool_call(tool_name="chat.news_sentiment", input_summary=f"ticker={sym} max_articles={max_articles}", output_summary="ok", latency_ms=None, error=None)
            elif tool == "buy_sell":
                sym = str(args.get("ticker") or (tickers[0] if tickers else "AAPL")).upper()
                rep = run_buy_sell_with_agents(
                    ticker=sym,
                    period="6mo",
                    interval="1d",
                    news_limit=10,
                    include_retrieval=bool(args.get("include_retrieval", True)),
                    include_llm_review=False,
                    retrieval_top_k=6,
                    retrieval_max_age_days=None,
                    horizon=None,
                    retrieval_query=f"thesis for {sym}",
                    memory_hint=None,
                )
                d = rep.model_dump(mode="json")
                step_bundles.append(("buy_sell", {"tool": "buy_sell", "report": d}))
                for c in (d.get("citations") or [])[:8]:
                    if isinstance(c, dict) and str(c.get("url") or "").startswith("http"):
                        _add_citation(str(c.get("title") or "citation"), str(c.get("url") or ""), str(c.get("source") or ""), str(c.get("published_at") or ""))
                log_tool_call(tool_name="chat.buy_sell", input_summary=f"ticker={sym}", output_summary="ok", latency_ms=None, error=None)
            elif tool == "history":
                h = get_history()
                step_bundles.append(("history", {"tool": "history", "history": h.model_dump(mode="json")}))
                log_tool_call(tool_name="chat.history", input_summary="{}", output_summary="ok", latency_ms=None, error=None)
        except Exception as e:  # noqa: BLE001
            log_tool_call(tool_name=f"chat.{tool}", input_summary=str(args)[:200], output_summary="error", latency_ms=None, error=str(e)[:300])

    normalized = build_normalized_evidence(step_bundles, ticker=(tickers[0] if tickers else "UNK"), session_id=tid)
    citations_json = [c.model_dump(mode="json") for c in citations]

    # Step 4: Writer + critic (+ optional repair)
    writer_prompt = build_agentic_chat_writer_prompt(query=text, evidence=normalized, citations=citations_json)
    write_res = _llm.generate_response(writer_prompt, preferred_model=model_name or "gemini")
    log_model_call(
        provider=write_res.provider or "none",
        model=write_res.model_used or "none",
        task="chat.write",
        prompt=writer_prompt,
        output=write_res.response,
        latency_ms=round(write_res.latency_ms or 0.0, 2) if hasattr(write_res, "latency_ms") else None,
        error=write_res.error,
    )
    answer = ""
    bullets: list[str] = []
    citations_used: list[int] = []
    if not write_res.error and write_res.response:
        try:
            answer, bullets, citations_used = _parse_writer(write_res.response)
        except Exception:
            answer = ""

    passed, notes, failed = _run_chat_critic(
        answer=answer,
        citations=citations,
        citations_used=citations_used,
        evidence=normalized,
        request_tickers=tickers,
    )
    model_used = write_res.model_used
    provider = write_res.provider
    fallback_used = write_res.fallback_used

    if not passed and (not write_res.error) and write_res.response:
        repair_prompt = build_agentic_chat_repair_prompt(
            query=text,
            evidence=normalized,
            citations=citations_json,
            previous_answer=answer,
            failed_checks=failed,
            critic_notes=notes,
        )
        rep = _llm.generate_response(repair_prompt, preferred_model=model_name or "gemini")
        log_model_call(
            provider=rep.provider or "none",
            model=rep.model_used or "none",
            task="chat.write_repair",
            prompt=repair_prompt,
            output=rep.response,
            latency_ms=round(rep.latency_ms or 0.0, 2) if hasattr(rep, "latency_ms") else None,
            error=rep.error,
        )
        if not rep.error and rep.response:
            try:
                answer2, bullets2, citations_used2 = _parse_writer(rep.response)
                passed2, notes2, failed2 = _run_chat_critic(
                    answer=answer2,
                    citations=citations,
                    citations_used=citations_used2,
                    evidence=normalized,
                    request_tickers=tickers,
                )
                answer, bullets, citations_used = answer2, bullets2, citations_used2
                passed, notes, failed = passed2, notes2, failed2
                model_used = rep.model_used
                provider = rep.provider
                fallback_used = rep.fallback_used
            except Exception:
                pass

    if not answer:
        answer = (
            "Evidence is insufficient to draw a conclusion. "
            "Try including a ticker symbol and asking about fundamentals or recent news."
        )
    if not bullets:
        bullets = [
            "I used available evidence only; if it's missing, I will say so.",
            "Ask with a ticker (e.g. AAPL) for best results.",
            "Educational use only — not financial advice.",
        ]

    response = ChatQueryResponse(
        thread_id=tid,
        detected_intent=intent,
        tickers=tickers,
        answer=answer,
        summary_bullets=bullets[:5],
        citations=citations[:10],
        disclaimer=_DISCLAIMER,
        timestamp=ts,
        llm_model_used=model_used,
        llm_provider=provider,
        llm_fallback_used=bool(fallback_used),
    )

    save_chat_interaction(
        tid, text, response.answer,
        intent=response.detected_intent,
        model_used=response.llm_model_used,
        provider=response.llm_provider,
        fallback_used=response.llm_fallback_used if response.llm_fallback_used else None,
    )
    return response
