from __future__ import annotations

import json
import re
import time
from typing import Any, Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.observability.jsonl_audit import log_model_call, log_tool_call
from app.services.auth_service import verify_access_token
from services.ai.llm_service import LLMService
from services.ai.prompts import (
    build_agentic_plan_prompt,
    build_agentic_repair_prompt,
    build_agentic_writer_prompt,
)
from services.news_sentiment_service import build_news_sentiment_report

from app.agentic.unified_evidence import build_normalized_evidence
from app.agents.orchestrator import run_buy_sell_with_agents
from app.core.config import settings
from app.memory import load_session, memory_profile_for_prompt, touch_agentic_session
from app.services.fundamental_service import get_fundamental_report
from services.history_service import get_history

router = APIRouter(prefix="/api/agentic-research", tags=["Agentic RAG"])
_llm = LLMService()


class AgenticResearchRequest(BaseModel):
    ticker: str = Field(..., min_length=1, max_length=16)
    question: str = Field(..., min_length=1, max_length=2000)
    session_id: str = Field(default="default", min_length=1, max_length=64)
    preferred_model: str = Field(default="gemini", description="gemini | llama | mistral")
    max_steps: int = Field(default=3, ge=2, le=4)
    include_buy_sell: bool = Field(default=True)
    include_news: bool = Field(default=True)
    include_fundamental: bool = Field(default=True)
    require_two_tools: bool = Field(default=True)
    secondary_ticker: str | None = Field(
        default=None,
        description="Optional second symbol; fundamentals + news evidence are merged for compare-style questions.",
        max_length=16,
    )
    access_token: str | None = Field(
        default=None,
        description="JWT bearer token; when present, verifies the user and scopes memory to email:session_id.",
    )


ToolName = Literal["fundamental", "news_sentiment", "buy_sell", "history"]


class PlanStep(BaseModel):
    tool: ToolName
    args: dict[str, Any] = Field(default_factory=dict)


class AgenticPlan(BaseModel):
    steps: list[PlanStep]


class CitationItem(BaseModel):
    title: str
    url: str
    source: str | None = None
    published_at: str | None = None


class AgenticResearchResponse(BaseModel):
    ticker: str
    question: str
    plan: AgenticPlan
    answer: str
    citations: list[CitationItem]
    citations_used: list[int]
    critic_passed: bool
    first_critic_passed: bool
    final_critic_passed: bool
    repair_attempted: bool = False
    plan_retry_attempted: bool = Field(
        default=False,
        description="True if the planner was called again after failure or too-few-tools plan.",
    )
    critic_notes: list[str]
    failed_checks: list[str] = Field(default_factory=list)
    memory_profile: dict[str, Any] = Field(
        default_factory=dict,
        description="Session long-horizon summary after this run (frequent_tickers, preferred_topics, risk_style).",
    )
    model_used: str | None = None
    provider: str | None = None
    latency_ms: float


_ADVICE_RE = re.compile(
    r"\b(should (?:you|i) (?:buy|sell|invest|hold)|"
    r"(?:strong )?(?:buy|sell) recommendation|"
    r"i (?:recommend|suggest) (?:buying|selling)|"
    r"definitely (?:buy|sell))\b",
    re.IGNORECASE,
)

_NEWS_FILING_CLAIM_RE = re.compile(
    r"\b(news|headlines?|articles?|reported|filing|sec\b|10-k|10-q|8-k|press release)\b",
    re.IGNORECASE,
)

_TICKER_IN_ANSWER_RE = re.compile(r"\b[A-Z]{1,5}\b")
_NUM_IN_ANSWER_RE = re.compile(r"\b\d+(?:\.\d+)?\b")

_TICKER_STOPWORDS = frozenset(
    {
        "I", "A", "OK", "US", "UK", "EU", "THE", "AND", "FOR", "ARE", "BUT", "NOT", "YOU",
        "ALL", "CAN", "HAS", "WAS", "ONE", "OUR", "OUT", "DAY", "GET", "USE", "MAN", "NEW",
        "NOW", "SEE", "WAY", "WHO", "BOY", "DID", "ITS", "LET", "PUT", "SAY", "SHE", "TOO",
        "BUY", "SELL", "HOLD", "ETF", "IPO", "EPS", "CEO", "CFO", "YTD", "ATH", "ATL",
    }
)


def _evidence_corpus(normalized_evidence: list[dict[str, Any]]) -> str:
    parts: list[str] = []
    for e in normalized_evidence:
        parts.append(str(e.get("title") or ""))
        parts.append(str(e.get("text") or ""))
        parts.append(str(e.get("ticker") or ""))
        nf = e.get("numeric_facts") or {}
        if isinstance(nf, dict):
            parts.append(json.dumps(nf, ensure_ascii=False))
    return " ".join(parts)


def _tickers_in_answer(answer: str) -> set[str]:
    out: set[str] = set()
    for m in _TICKER_IN_ANSWER_RE.finditer(answer or ""):
        t = m.group(0)
        if t in _TICKER_STOPWORDS or len(t) < 2:
            continue
        out.add(t)
    return out


def _significant_numbers_in_answer(answer: str) -> list[str]:
    """Numbers that are plausible factual claims (skip years, tiny integers)."""
    found: list[str] = []
    for m in _NUM_IN_ANSWER_RE.finditer(answer or ""):
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


def _run_critic(
    *,
    answer: str,
    citations: list[CitationItem],
    citations_used: list[int],
    steps: list[PlanStep],
    require_two_tools: bool,
    normalized_evidence: list[dict[str, Any]],
    request_ticker: str,
) -> tuple[bool, list[str], list[str]]:
    critic_notes: list[str] = []
    failed_checks: list[str] = []

    if require_two_tools:
        used_tools = {s.tool for s in steps if s.tool != "history"}
        if len(used_tools) < 2:
            failed_checks.append("insufficient_distinct_tools")
            critic_notes.append("Plan used fewer than two non-history tools.")

    if _ADVICE_RE.search(answer or ""):
        failed_checks.append("direct_financial_advice_pattern")
        critic_notes.append("Answer matches direct buy/sell instruction heuristics.")

    if citations_used:
        if len(citations) == 0 or any(i < 1 or i > len(citations) for i in citations_used):
            failed_checks.append("citation_index_invalid")
            critic_notes.append("citations_used contains an invalid index or citations list is empty.")

    # Tickers mentioned in answer must appear in evidence (or match request ticker).
    ev_tickers = {str(e.get("ticker") or "").upper() for e in normalized_evidence if e.get("ticker")}
    req = request_ticker.strip().upper()
    bad_tickers = sorted(
        {tok for tok in _tickers_in_answer(answer) if tok != req and tok not in ev_tickers}
    )
    if bad_tickers:
        failed_checks.append("answer_ticker_not_in_evidence")
        critic_notes.append(
            f"Ticker(s) {bad_tickers} appear in the answer but not in normalized evidence tickers."
        )

    corpus = _evidence_corpus(normalized_evidence)
    for num in _significant_numbers_in_answer(answer):
        ok = num in corpus
        if not ok and "." in num:
            try:
                alt = str(float(num))
                ok = alt in corpus or alt.rstrip("0").rstrip(".") in corpus
            except ValueError:
                ok = False
        if not ok:
            failed_checks.append("numeric_claim_not_in_evidence")
            critic_notes.append(f"Numeric token '{num}' in answer not found in evidence text or numeric_facts.")
            break

    if _NEWS_FILING_CLAIM_RE.search(answer or "") and not citations_used:
        failed_checks.append("news_or_filing_claim_without_citation")
        critic_notes.append("Answer references news/filings but citations_used is empty.")

    passed = len(failed_checks) == 0
    return passed, critic_notes, failed_checks


def _parse_json_strict(raw: str) -> dict[str, Any]:
    s = (raw or "").strip()
    if s.startswith("```"):
        # tolerate fences but do not allow extra text
        parts = s.split("```")
        if len(parts) >= 2:
            s = parts[1].strip()
        if s.lower().startswith("json"):
            s = s[4:].strip()
    start, end = s.find("{"), s.rfind("}")
    if start == -1 or end <= start:
        raise ValueError("No JSON object found")
    return json.loads(s[start : end + 1])


def _parse_writer_json(raw: str) -> tuple[str, list[int]]:
    raw_out = _parse_json_strict(raw)
    answer = str(raw_out.get("answer") or "").strip()
    used = raw_out.get("citations_used") or []
    if not isinstance(used, list):
        used = []
    citations_used = [int(x) for x in used if str(x).isdigit()]
    return answer, citations_used


def _tool_allowlist(body: AgenticResearchRequest) -> set[ToolName]:
    allowed: set[ToolName] = {"history"}
    if body.include_fundamental:
        allowed.add("fundamental")
    if body.include_news:
        allowed.add("news_sentiment")
    if body.include_buy_sell:
        allowed.add("buy_sell")
    return allowed


def _planner_example_json(*, ticker: str, non_history: list[str]) -> str:
    """Minimal two-step example for retry hints (respects allowlist)."""
    t = ticker.upper()
    a = non_history[0] if non_history else "fundamental"
    b = non_history[1] if len(non_history) > 1 else a
    if a == b:
        return f'{{"steps":[{{"tool":"{a}","args":{{"ticker":"{t}"}}}}]}}'
    if a == "fundamental" and b == "news_sentiment":
        return (
            '{"steps":['
            f'{{"tool":"fundamental","args":{{"ticker":"{t}"}}}},'
            f'{{"tool":"news_sentiment","args":{{"ticker":"{t}","max_articles":5}}}}'
            "]}"
        )
    if b == "news_sentiment":
        return (
            '{"steps":['
            f'{{"tool":"{a}","args":{{"ticker":"{t}"}}}},'
            f'{{"tool":"news_sentiment","args":{{"ticker":"{t}","max_articles":5}}}}'
            "]}"
        )
    if b == "buy_sell":
        return (
            '{"steps":['
            f'{{"tool":"{a}","args":{{"ticker":"{t}"}}}},'
            f'{{"tool":"buy_sell","args":{{"ticker":"{t}","include_retrieval":true}}}}'
            "]}"
        )
    return (
        '{"steps":['
        f'{{"tool":"{a}","args":{{"ticker":"{t}"}}}},'
        f'{{"tool":"{b}","args":{{"ticker":"{t}"}}}}'
        "]}"
    )


def _ingest_articles_to_rag(ticker: str, articles: list[dict]) -> int:
    """Convert news articles fetched by the news_sentiment tool into RAG chunks."""
    from app.rag.store import upsert_chunks  # local import — keep rag optional
    import hashlib
    from datetime import datetime, timezone as _tz

    rows: list[dict] = []
    ingested_at = datetime.now(_tz.utc).isoformat()
    for idx, art in enumerate(articles[:30]):
        headline = str(art.get("headline") or art.get("title") or "").strip()
        summary = str(art.get("summary") or "").strip()
        text = " ".join(x for x in [headline, summary] if x).strip()
        if not text:
            continue
        url = str(art.get("url") or "")
        published = str(art.get("published_at") or "")
        uid = f"{ticker}:news:{idx}:{abs(hash((headline, published))) % 10_000_000}"
        rows.append({
            "chunk_id": uid,
            "ticker": ticker,
            "doc_type": "news",
            "title": headline or None,
            "text": text[:2200],
            "url": url or None,
            "published_at": published or None,
            "ingested_at": ingested_at,
            "source": str(art.get("source") or "news"),
        })
    if not rows:
        return 0
    return upsert_chunks(rows)


def _run_tool(step: PlanStep, *, ticker: str, session_id: str) -> tuple[dict[str, Any], list[CitationItem], float]:
    tool = step.tool
    args = step.args or {}
    t0 = time.perf_counter()
    citations: list[CitationItem] = []

    try:
        if tool == "fundamental":
            rep = get_fundamental_report(ticker)
            # deterministic report has no URLs; provide a minimal citation placeholder
            citations = [
                CitationItem(
                    title=f"{ticker.upper()} fundamentals (yfinance)",
                    url=f"https://finance.yahoo.com/quote/{ticker.upper()}",
                    source="yfinance",
                    published_at=None,
                )
            ]
            out = {"tool": "fundamental", "report": rep}
        elif tool == "news_sentiment":
            max_articles = int(args.get("max_articles") or 5)
            ns = build_news_sentiment_report(ticker, None, None, max_articles=max_articles, model_name=None)
            out = {"tool": "news_sentiment", "report": ns.model_dump(mode="json")}
            citations = [
                CitationItem(
                    title=str(c.get("title") or "news"),
                    url=str(c.get("url") or ""),
                    source=str(c.get("source") or ""),
                    published_at=str(c.get("published_at") or ""),
                )
                for c in (out["report"].get("citations") or [])
                if (c.get("url") or "").strip()
            ]
            # Side-effect: ingest fetched articles into RAG for grounded retrieval
            try:
                _ingest_articles_to_rag(ticker, out["report"].get("articles") or [])
            except Exception:  # noqa: BLE001
                pass  # RAG ingestion failure must not break the pipeline
        elif tool == "buy_sell":
            include_retrieval = bool(args.get("include_retrieval", True))
            rep = run_buy_sell_with_agents(
                ticker=ticker,
                period="6mo",
                interval="1d",
                news_limit=10,
                include_retrieval=include_retrieval,
                include_llm_review=False,
                retrieval_top_k=6,
                retrieval_max_age_days=None,
                horizon=str(args.get("horizon") or "") or None,
                retrieval_query=str(args.get("query") or f"thesis for {ticker}"),
                memory_hint=None,
            )
            d = rep.model_dump(mode="json")
            out = {"tool": "buy_sell", "report": d}
            # citations are a mixed bag; prefer url-like values if present
            raw_cits = d.get("citations") or []
            if isinstance(raw_cits, list):
                for c in raw_cits:
                    if isinstance(c, dict):
                        url = str(c.get("url") or "").strip()
                        if url.startswith("http"):
                            citations.append(
                                CitationItem(
                                    title=str(c.get("title") or c.get("source") or "citation"),
                                    url=url,
                                    source=str(c.get("source") or ""),
                                    published_at=str(c.get("published_at") or ""),
                                )
                            )
        elif tool == "history":
            hist = get_history()
            out = {"tool": "history", "history": hist.model_dump(mode="json"), "session_id": session_id}
        else:
            raise ValueError(f"unknown tool: {tool}")
    except Exception as e:  # noqa: BLE001
        ms = (time.perf_counter() - t0) * 1000.0
        log_tool_call(
            tool_name=f"agentic.{tool}",
            input_summary=f"ticker={ticker} args={list(args.keys())[:8]}",
            output_summary="error",
            latency_ms=round(ms, 2),
            error=str(e)[:500],
        )
        raise

    ms = (time.perf_counter() - t0) * 1000.0
    log_tool_call(
        tool_name=f"agentic.{tool}",
        input_summary=f"ticker={ticker} args={list(args.keys())[:8]}",
        output_summary="ok",
        latency_ms=round(ms, 2),
        error=None,
    )
    return out, citations, ms


@router.post("/run", response_model=AgenticResearchResponse)
def run_agentic_research(body: AgenticResearchRequest) -> AgenticResearchResponse:
    t0 = time.perf_counter()
    ticker = body.ticker.strip().upper()
    question = body.question.strip()

    # Scope memory to the authenticated user when a valid JWT is present.
    _email: str | None = None
    if body.access_token:
        _email = verify_access_token(body.access_token)
        if _email is None:
            raise HTTPException(status_code=401, detail="Invalid or expired token")
    _mem_key = f"{_email}:{body.session_id}" if _email else body.session_id

    mem_ctx = "{}"
    if settings.memory_enabled:
        mem_ctx = memory_profile_for_prompt(load_session(_mem_key))

    allowed = _tool_allowlist(body)
    allowed_sorted = sorted(allowed)
    non_history_tools = sorted(t for t in allowed if t != "history")

    plan_retry_attempted = False
    planner_hint = ""
    plan_resp = None
    steps: list[PlanStep] = []

    for plan_attempt in range(2):
        plan_prompt = build_agentic_plan_prompt(
            ticker=ticker,
            question=question,
            allowed_tools=allowed_sorted,
            max_steps=body.max_steps,
            require_two_tools=body.require_two_tools,
            memory_context=mem_ctx,
            planner_retry_hint=planner_hint,
        )

        plan_call_t0 = time.perf_counter()
        plan_resp = _llm.generate_response(plan_prompt, preferred_model=body.preferred_model)
        plan_ms = (time.perf_counter() - plan_call_t0) * 1000.0
        log_model_call(
            provider=plan_resp.provider or "none",
            model=plan_resp.model_used or "none",
            task="agentic.plan_retry" if plan_retry_attempted else "agentic.plan",
            prompt=plan_prompt,
            output=plan_resp.response,
            latency_ms=round(plan_ms, 2),
            error=plan_resp.error,
        )

        if plan_resp.error or not plan_resp.response:
            if plan_attempt == 0:
                plan_retry_attempted = True
                ex = _planner_example_json(ticker=ticker, non_history=non_history_tools)
                planner_hint = (
                    "Your previous planner output was empty or the model errored. "
                    "Reply with ONLY one JSON object matching this shape (use your allowlist tools): "
                    + ex
                )
                continue
            raise HTTPException(
                status_code=502,
                detail=f"Planner failed after retry: {plan_resp.error or 'empty'}",
            )

        try:
            raw_plan = _parse_json_strict(plan_resp.response)
            plan = AgenticPlan.model_validate(raw_plan)
        except Exception as e:  # noqa: BLE001
            if plan_attempt == 0:
                plan_retry_attempted = True
                ex = _planner_example_json(ticker=ticker, non_history=non_history_tools)
                planner_hint = (
                    "Your previous reply was not valid JSON or did not match the schema. "
                    f"Error hint: {str(e)[:120]}. Output ONLY a JSON object like: "
                    + ex
                    + " (tools must be from this allowlist: "
                    + ", ".join(allowed_sorted)
                    + ")."
                )
                continue
            raise HTTPException(
                status_code=502,
                detail=f"Planner returned invalid JSON after retry: {str(e)[:200]}",
            ) from e

        steps = [s for s in plan.steps if s.tool in allowed][: body.max_steps]
        if body.require_two_tools:
            non_history = [s for s in steps if s.tool != "history"]
            if len({s.tool for s in non_history}) < 2:
                if plan_attempt == 0:
                    plan_retry_attempted = True
                    planner_hint = (
                        "Your plan used fewer than TWO DIFFERENT non-history tools. "
                        "You MUST pick at least two distinct tools from: "
                        + ", ".join(non_history_tools)
                        + ". For example combine fundamental with news_sentiment, or fundamental with buy_sell — not history alone twice."
                    )
                    continue
                raise HTTPException(
                    status_code=400,
                    detail="Plan must use at least two distinct non-history tools after retry",
                )
        break

    step_bundles: list[tuple[str, dict[str, Any]]] = []
    citations: list[CitationItem] = []

    for step in steps:
        out, cits, _ = _run_tool(step, ticker=ticker, session_id=body.session_id)
        step_bundles.append((step.tool, out))
        citations.extend(cits)

    sec = (body.secondary_ticker or "").strip().upper()
    if sec and sec != ticker:
        f_step = PlanStep(tool="fundamental", args={"ticker": sec})
        out_f, cits_f, _ = _run_tool(f_step, ticker=sec, session_id=body.session_id)
        step_bundles.append(("fundamental", out_f))
        citations.extend(cits_f)
        n_step = PlanStep(tool="news_sentiment", args={"ticker": sec, "max_articles": 5})
        out_n, cits_n, _ = _run_tool(n_step, ticker=sec, session_id=body.session_id)
        step_bundles.append(("news_sentiment", out_n))
        citations.extend(cits_n)

    normalized_evidence = build_normalized_evidence(
        step_bundles,
        ticker=ticker,
        session_id=body.session_id,
    )

    writer_prompt = build_agentic_writer_prompt(
        ticker=ticker,
        question=question,
        evidence=normalized_evidence,
        citations=[c.model_dump(mode="json") for c in citations],
        memory_context=mem_ctx,
    )
    write_call_t0 = time.perf_counter()
    write_resp = _llm.generate_response(writer_prompt, preferred_model=body.preferred_model)
    write_ms = (time.perf_counter() - write_call_t0) * 1000.0
    log_model_call(
        provider=write_resp.provider or "none",
        model=write_resp.model_used or "none",
        task="agentic.write",
        prompt=writer_prompt,
        output=write_resp.response,
        latency_ms=round(write_ms, 2),
        error=write_resp.error,
    )
    if write_resp.error or not write_resp.response:
        raise HTTPException(status_code=502, detail=f"Writer failed: {write_resp.error or 'empty'}")

    try:
        answer, citations_used = _parse_writer_json(write_resp.response)
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"Writer returned invalid JSON: {str(e)[:200]}") from e

    first_passed, first_notes, first_failed = _run_critic(
        answer=answer,
        citations=citations,
        citations_used=citations_used,
        steps=steps,
        require_two_tools=body.require_two_tools,
        normalized_evidence=normalized_evidence,
        request_ticker=ticker,
    )

    repair_attempted = False
    final_passed = first_passed
    final_notes = list(first_notes)
    final_failed = list(first_failed)
    model_used = write_resp.model_used
    provider = write_resp.provider

    if not first_passed:
        repair_attempted = True
        repair_prompt = build_agentic_repair_prompt(
            ticker=ticker,
            question=question,
            evidence=normalized_evidence,
            citations=[c.model_dump(mode="json") for c in citations],
            previous_answer=answer,
            failed_checks=first_failed,
            critic_notes=first_notes,
            memory_context=mem_ctx,
        )
        repair_t0 = time.perf_counter()
        repair_resp = _llm.generate_response(repair_prompt, preferred_model=body.preferred_model)
        repair_ms = (time.perf_counter() - repair_t0) * 1000.0
        log_model_call(
            provider=repair_resp.provider or "none",
            model=repair_resp.model_used or "none",
            task="agentic.write_repair",
            prompt=repair_prompt,
            output=repair_resp.response,
            latency_ms=round(repair_ms, 2),
            error=repair_resp.error,
        )
        if repair_resp.error or not repair_resp.response:
            raise HTTPException(
                status_code=502,
                detail=f"Repair writer failed: {repair_resp.error or 'empty'}",
            )
        try:
            answer, citations_used = _parse_writer_json(repair_resp.response)
        except Exception as e:  # noqa: BLE001
            raise HTTPException(
                status_code=502,
                detail=f"Repair writer returned invalid JSON: {str(e)[:200]}",
            ) from e
        model_used = repair_resp.model_used
        provider = repair_resp.provider
        final_passed, final_notes, final_failed = _run_critic(
            answer=answer,
            citations=citations,
            citations_used=citations_used,
            steps=steps,
            require_two_tools=body.require_two_tools,
            normalized_evidence=normalized_evidence,
            request_ticker=ticker,
        )

    total_ms = (time.perf_counter() - t0) * 1000.0
    profile_out: dict[str, Any] = {}
    if settings.memory_enabled:
        sess_done = touch_agentic_session(
            _mem_key,
            ticker,
            question,
            tools_used=[s.tool for s in steps],
        )
        mp = sess_done.get("memory_profile")
        if isinstance(mp, dict):
            profile_out = dict(mp)

    return AgenticResearchResponse(
        ticker=ticker,
        question=question,
        plan=AgenticPlan(steps=steps),
        answer=answer,
        citations=citations,
        citations_used=citations_used,
        critic_passed=final_passed,
        first_critic_passed=first_passed,
        final_critic_passed=final_passed,
        repair_attempted=repair_attempted,
        plan_retry_attempted=plan_retry_attempted,
        critic_notes=final_notes,
        failed_checks=final_failed,
        memory_profile=profile_out,
        model_used=model_used,
        provider=provider,
        latency_ms=round(total_ms, 2),
    )


# ── Standalone ingest endpoint ────────────────────────────────────────────────

class IngestResponse(BaseModel):
    ticker: str
    ingested: int
    error: str | None = None


@router.post("/ingest", response_model=IngestResponse)
def ingest_ticker(ticker: str) -> IngestResponse:
    """
    Fetch latest news for a ticker and store it in the RAG knowledge base.
    Call this before running agentic research on a new ticker for best results.
    """
    sym = ticker.strip().upper()
    if not sym:
        raise HTTPException(status_code=400, detail="ticker query param is required")
    try:
        ns = build_news_sentiment_report(sym, None, None, max_articles=20, model_name=None)
        articles = [a.model_dump(mode="json") for a in (ns.articles or [])]
        ingested = _ingest_articles_to_rag(sym, articles)
        return IngestResponse(ticker=sym, ingested=ingested)
    except Exception as exc:  # noqa: BLE001
        return IngestResponse(ticker=sym, ingested=0, error=str(exc)[:300])

