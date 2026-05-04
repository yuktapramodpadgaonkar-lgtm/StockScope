from __future__ import annotations

from typing import Any

from app.schemas.buy_sell_analysis import BuySellReport, CriticResult


def run_critic(
    *,
    report: BuySellReport,
    bundle: dict[str, Any] | None,
    retrieved: list[dict[str, Any]],
    include_retrieval: bool,
    include_llm_review: bool,
) -> CriticResult:
    """
    Rule-based quality gate: flags missing evidence, low confidence, or strong cross-dimension conflict.
    Does not change BUY/HOLD/SELL — only surfaces `flags` and `incomplete_evidence` for clients and UI.
    """
    flags: list[str] = []
    notes: list[str] = []
    rs = report.scoring_engine.rule_scores
    incomplete = False

    for name, dim in (
        ("fundamental", rs.fundamental),
        ("technical", rs.technical),
        ("sentiment", rs.sentiment),
    ):
        if dim.data_completeness < 0.35:
            incomplete = True
            flags.append(f"low_data_completeness:{name}")

    if report.confidence < 35:
        flags.append("low_confidence")
        notes.append("Overall confidence is low — favor HOLD-sized conviction or wait for cleaner data.")

    fa = [rs.fundamental.score, rs.technical.score, rs.sentiment.score]
    if max(fa) - min(fa) > 40:
        flags.append("high_dimension_dispersion")
        notes.append("Large gap between dimension scores — thesis may be mixed; align entries with risk tolerance.")

    if include_retrieval and len(retrieved) == 0:
        flags.append("retrieval_returned_zero_chunks")
        notes.append(
            "Retrieval was enabled but no chunks matched filters/query; narratives rely mostly on Layer 1 fields."
        )

    if include_llm_review and not report.llm_review.enabled:
        flags.append("llm_review_requested_but_disabled")
        notes.append("LLM review was requested but did not run (disabled in settings or provider error).")

    bundle = bundle or {}
    if (bundle.get("fundamentals") or {}).get("error") == "no_info":
        incomplete = True
        flags.append("layer1_missing_fundamentals")

    passed = not incomplete and report.confidence >= 40

    return CriticResult(
        passed=passed,
        incomplete_evidence=incomplete,
        flags=flags,
        notes=notes,
    )
