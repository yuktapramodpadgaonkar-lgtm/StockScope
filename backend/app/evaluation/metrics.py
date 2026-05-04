from __future__ import annotations

from typing import Any


def score_report_dict(report: dict[str, Any]) -> dict[str, Any]:
    """
    Lightweight Phase 8 metrics over a serialized BuySellReport (or model_dump).
    Extend later: citation overlap with eval gold, LLM-as-judge, cost tracking.
    """
    citations = report.get("citations") or []
    mem = report.get("memory") or {}
    pipe = report.get("agent_pipeline") or {}
    critic = pipe.get("critic") or {}

    return {
        "schema_version": report.get("schema_version"),
        "has_agent_pipeline": bool(pipe),
        "has_memory": bool(mem),
        "citation_count": len(citations) if isinstance(citations, list) else 0,
        "critic_passed": bool(critic.get("passed")),
        "critic_flag_count": len(critic.get("flags") or []),
        "recommendation": report.get("recommendation"),
        "confidence": report.get("confidence"),
    }
