from __future__ import annotations

from pydantic import BaseModel, Field


class RagEvidenceItem(BaseModel):
    """One retrieved filing chunk used for optional fundamental RAG narrative."""

    chunk_id: str | None = None
    title: str | None = None
    url: str | None = None
    section_key: str | None = None
    text_preview: str = Field(..., description="Truncated chunk text for UI / transparency")
    retrieval_score: float | None = None


class FundamentalMetrics(BaseModel):
    market_cap: float | None = None
    trailing_pe: float | None = None
    forward_pe: float | None = None
    profit_margin_pct: float | None = None
    operating_margin_pct: float | None = None
    roe_pct: float | None = None
    debt_to_equity: float | None = None
    current_ratio: float | None = None
    revenue_growth_yoy_pct: float | None = None
    earnings_growth_yoy_pct: float | None = None
    dividend_yield_pct: float | None = None


class FundamentalAnalysisResponse(BaseModel):
    ticker: str
    company_name: str
    sector: str = Field(description="GICS-style sector or 'Unknown'")
    industry: str = Field(description="Industry or 'Unknown'")
    current_price: float | None = None
    metrics: FundamentalMetrics
    strengths: list[str]
    risks: list[str]
    verdict: str
    disclaimer: str
    ai_summary: str | None = Field(
        default=None,
        description="Optional plain-language explanation from an LLM; deterministic fields are the source of truth.",
    )
    ai_model: str | None = Field(default=None, description="Model id used for ai_summary.")
    ai_error: str | None = Field(
        default=None,
        description="Set when include_llm=true but the LLM call failed; deterministic fields are still valid.",
    )
    rag_evidence: list[RagEvidenceItem] | None = Field(
        default=None,
        description="Retrieved SEC filing chunks when include_rag=true (optional narrative context).",
    )
    rag_error: str | None = Field(
        default=None,
        description="Set when include_rag=true but ingest/retrieve failed; deterministic report is still valid.",
    )
