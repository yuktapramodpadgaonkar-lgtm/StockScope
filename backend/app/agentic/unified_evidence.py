"""
Normalized evidence items for Agentic RAG (Step 1).

Converts raw tool payloads into a single schema for the writer and critic.
Does not call external services — only shapes in-memory dicts.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class UnifiedEvidenceItem(BaseModel):
    source_id: str = ""
    tool: str
    ticker: str
    title: str
    text: str
    url: str | None = None
    timestamp: str | None = None
    numeric_facts: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


def _nf_clean(d: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in d.items() if v is not None}


def normalize_fundamental_bundle(bundle: dict[str, Any], *, ticker: str, source_id: str) -> list[UnifiedEvidenceItem]:
    rep = bundle.get("report") or {}
    sym = str(rep.get("ticker") or ticker).upper()
    lines: list[str] = [
        f"Verdict: {rep.get('verdict', '')}",
        f"Sector: {rep.get('sector', '')} | Industry: {rep.get('industry', '')}",
        "",
        "Strengths:",
        *[f"- {s}" for s in (rep.get("strengths") or [])],
        "",
        "Risks:",
        *[f"- {r}" for r in (rep.get("risks") or [])],
    ]
    metrics = rep.get("metrics") or {}
    nf = _nf_clean({str(k): v for k, v in dict(metrics).items() if isinstance(k, str)})
    if rep.get("current_price") is not None:
        nf["current_price"] = rep.get("current_price")
    return [
        UnifiedEvidenceItem(
            source_id=source_id,
            tool="fundamental",
            ticker=sym,
            title=f"Fundamentals: {rep.get('company_name') or sym}",
            text="\n".join(lines),
            url=f"https://finance.yahoo.com/quote/{sym}",
            timestamp=None,
            numeric_facts=nf,
            metadata={"disclaimer": (rep.get("disclaimer") or "")[:400]},
        )
    ]


def normalize_news_bundle(bundle: dict[str, Any], *, ticker: str, source_id_prefix: str) -> list[UnifiedEvidenceItem]:
    rep = bundle.get("report") or {}
    sym = str(rep.get("ticker") or ticker).upper()
    out: list[UnifiedEvidenceItem] = []
    agg = rep.get("aggregate_sentiment") or {}
    summary = str(rep.get("summary") or "")
    themes = rep.get("major_themes") or []
    out.append(
        UnifiedEvidenceItem(
            source_id=f"{source_id_prefix}_summary",
            tool="news_sentiment",
            ticker=sym,
            title=f"News sentiment aggregate ({sym})",
            text=summary or "(no summary text)",
            url=None,
            timestamp=None,
            numeric_facts=_nf_clean(
                {
                    "positive_pct": agg.get("positive"),
                    "neutral_pct": agg.get("neutral"),
                    "negative_pct": agg.get("negative"),
                }
            ),
            metadata={"major_themes": themes[:10], "overall_label": agg.get("overall_label")},
        )
    )
    for i, art in enumerate((rep.get("articles") or [])[:8]):
        if not isinstance(art, dict):
            continue
        url = (art.get("url") or "").strip() or None
        out.append(
            UnifiedEvidenceItem(
                source_id=f"{source_id_prefix}_article_{i}",
                tool="news_sentiment",
                ticker=sym,
                title=str(art.get("headline") or "Article"),
                text=str(art.get("summary") or art.get("headline") or ""),
                url=url,
                timestamp=str(art.get("published_at") or "") or None,
                numeric_facts={},
                metadata={"sentiment": art.get("sentiment"), "source": art.get("source")},
            )
        )
    return out


def normalize_buy_sell_bundle(bundle: dict[str, Any], *, ticker: str, source_id_prefix: str) -> list[UnifiedEvidenceItem]:
    d = bundle.get("report") or {}
    sym = str(d.get("ticker") or ticker).upper()
    se = d.get("scoring_engine") or {}
    overall = se.get("overall") or {}
    rs = se.get("rule_scores") or {}
    fund = rs.get("fundamental") or {}
    tech = rs.get("technical") or {}
    sent = rs.get("sentiment") or {}
    thesis = d.get("investment_thesis") or {}
    lines = [
        f"Deterministic recommendation: {d.get('recommendation', '')}",
        f"Confidence: {d.get('confidence', '')}",
        f"Overall rule score (weighted): {overall.get('weighted_score', '')}",
        f"Dimension scores — fundamental: {fund.get('score')}, technical: {tech.get('score')}, sentiment: {sent.get('score')}",
        "",
        "Thesis summary:",
        str(thesis.get("summary") or ""),
        "",
        "Key drivers:",
        *[f"- {x}" for x in (thesis.get("key_drivers") or [])[:8]],
    ]
    nf = _nf_clean(
        {
            "confidence": d.get("confidence"),
            "overall_weighted_score": overall.get("weighted_score"),
            "fundamental_score": fund.get("score"),
            "technical_score": tech.get("score"),
            "sentiment_score": sent.get("score"),
        }
    )
    out: list[UnifiedEvidenceItem] = [
        UnifiedEvidenceItem(
            source_id=f"{source_id_prefix}_report",
            tool="buy_sell",
            ticker=sym,
            title=f"Buy/sell deterministic report ({sym})",
            text="\n".join(lines),
            url=f"https://finance.yahoo.com/quote/{sym}",
            timestamp=None,
            numeric_facts=nf,
            metadata={
                "schema_version": d.get("schema_version"),
                "agent_pipeline_summary": (d.get("agent_pipeline") or {}).get("plan_summary"),
            },
        )
    ]
    for i, c in enumerate((d.get("citations") or [])[:12]):
        if not isinstance(c, dict):
            continue
        url = str(c.get("url") or "").strip()
        if not url.startswith("http"):
            continue
        out.append(
            UnifiedEvidenceItem(
                source_id=f"{source_id_prefix}_cite_{i}",
                tool="buy_sell",
                ticker=sym,
                title=str(c.get("title") or c.get("source") or "citation"),
                text=str(c.get("snippet") or c.get("title") or "")[:2000],
                url=url,
                timestamp=str(c.get("date") or "") or None,
                numeric_facts={},
                metadata={"citation_id": c.get("id"), "source": c.get("source")},
            )
        )
    return out


def normalize_history_bundle(bundle: dict[str, Any], *, ticker: str, session_id: str, source_id: str) -> list[UnifiedEvidenceItem]:
    h = bundle.get("history") or {}
    chats = h.get("chat_history") or []
    research = h.get("research_history") or []
    prompts = h.get("saved_prompts") or []
    text = (
        f"session_id={session_id}\n"
        f"chat_threads={len(chats)}, research_runs={len(research)}, saved_prompts={len(prompts)}\n"
        f"recent_research_tickers={[str(r.get('ticker')) for r in research[:5] if isinstance(r, dict)]}"
    )
    return [
        UnifiedEvidenceItem(
            source_id=source_id,
            tool="history",
            ticker=ticker.upper(),
            title="History store snapshot",
            text=text,
            url=None,
            timestamp=None,
            numeric_facts={
                "chat_threads": len(chats),
                "research_runs": len(research),
                "saved_prompts": len(prompts),
            },
            metadata={"session_id": session_id},
        )
    ]


def normalize_tool_bundle(
    tool: str,
    bundle: dict[str, Any],
    *,
    ticker: str,
    session_id: str,
    source_id_base: str,
) -> list[UnifiedEvidenceItem]:
    if tool == "fundamental":
        return normalize_fundamental_bundle(bundle, ticker=ticker, source_id=source_id_base)
    if tool == "news_sentiment":
        return normalize_news_bundle(bundle, ticker=ticker, source_id_prefix=source_id_base)
    if tool == "buy_sell":
        return normalize_buy_sell_bundle(bundle, ticker=ticker, source_id_prefix=source_id_base)
    if tool == "history":
        return normalize_history_bundle(bundle, ticker=ticker, session_id=session_id, source_id=source_id_base)
    return [
        UnifiedEvidenceItem(
            source_id=source_id_base,
            tool=str(tool),
            ticker=ticker.upper(),
            title="Unknown tool",
            text=str(bundle)[:2000],
            url=None,
            timestamp=None,
            numeric_facts={},
            metadata={},
        )
    ]


def build_normalized_evidence(
    step_bundles: list[tuple[str, dict[str, Any]]],
    *,
    ticker: str,
    session_id: str,
) -> list[dict[str, Any]]:
    """Assign monotonic source_ids: {tool}_{n} across all items (global n)."""
    out: list[dict[str, Any]] = []
    n = 0
    for tool, bundle in step_bundles:
        items = normalize_tool_bundle(
            tool,
            bundle,
            ticker=ticker,
            session_id=session_id,
            source_id_base=f"{tool}_{n}",
        )
        for it in items:
            it.source_id = f"{tool}_{n}"
            n += 1
            out.append(it.model_dump(mode="json"))
    return out
