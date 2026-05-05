from pydantic import BaseModel, Field


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
        description="Optional plain-language explanation from a local LLM; only the deterministic JSON is its source.",
    )
    ai_model: str | None = Field(default=None, description="Ollama model id when include_llm was requested.")
    ai_error: str | None = Field(
        default=None,
        description="Set when include_llm was true but the LLM call failed; deterministic fields are still valid.",
    )
