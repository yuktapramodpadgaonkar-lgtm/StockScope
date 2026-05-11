from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class PlannedStep:
    """A single node in the analysis task graph (v1 is a fixed DAG, not free-form LLM planning)."""

    id: str
    description: str


@dataclass
class AnalysisPlan:
    """
    Output of the planner: an ordered list of steps to run.
    v1: deterministic plan from flags (ticker-agnostic); future: query-conditioned decomposition.
    """

    planner_version: str = "phase6-v1"
    horizon: str = ""
    steps: list[PlannedStep] = field(default_factory=list)
    notes: str = ""


def plan_buy_sell_analysis(
    *,
    horizon: str | None,
    include_retrieval: bool,
    include_llm_review: bool,
) -> AnalysisPlan:
    """
    Build the execution DAG for `/api/buy-sell/analyze/{ticker}`.
    """
    h = (horizon or "").strip() or "unspecified"
    steps: list[PlannedStep] = [
        PlannedStep(
            "layer1_bundle",
            "Fetch Layer 1 bundle (yfinance history/info, news, analysts, filings stub or SEC)",
        ),
    ]
    if include_retrieval:
        steps.extend(
            [
                PlannedStep("rag_ingest", "Ingest news + filing chunks into local RAG store"),
                PlannedStep(
                    "rag_embed_sync",
                    "Sync per-ticker embedding index (HF token required for dense vectors)",
                ),
                PlannedStep(
                    "rag_retrieve",
                    "Hybrid BM25 + embedding retrieval for citation snippets",
                ),
            ]
        )
    steps.append(
        PlannedStep(
            "score_and_report",
            "Deterministic rule scores + structured Buy/Sell report assembly"
            + (" + advisory LLM review" if include_llm_review else ""),
        )
    )
    return AnalysisPlan(
        horizon=h,
        steps=steps,
        notes=(
            "Phase 6 v1 uses a fixed DAG. Retrieval substeps are skipped when include_retrieval=false."
        ),
    )
