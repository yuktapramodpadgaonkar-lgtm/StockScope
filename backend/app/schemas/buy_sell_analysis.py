"""
Buy/Sell analysis report — Kavout-style output contract (schema v1).

See `schemas/buy_sell_report.json` at the repo root for the frozen JSON Schema (v1.2.0).
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


SCHEMA_VERSION = "1.2.0"


class Recommendation(str, Enum):
    BUY = "BUY"
    HOLD = "HOLD"
    SELL = "SELL"


class CitationItem(BaseModel):
    id: str
    title: str
    source: str
    url: str | None = None
    date: str | None = None
    snippet: str | None = None


class InvestmentThesis(BaseModel):
    summary: str = ""
    key_drivers: list[str] = Field(default_factory=list)


class ValuationAnalysis(BaseModel):
    pe: float | None = None
    dcf_value: float | None = None
    current_price: float | None = None
    implied_upside: float | None = None


class FundamentalAnalysis(BaseModel):
    score: int = Field(0, ge=0, le=100)
    weight: int = Field(40, ge=0, le=100)
    business_performance: str = ""
    valuation_analysis: ValuationAnalysis = Field(default_factory=ValuationAnalysis)
    bull_bear_integration: str = ""
    verdict: str = ""


class TechnicalIndicators(BaseModel):
    rsi: float | None = None
    macd_signal: str = ""
    ma_50: float | None = None
    ma_200: float | None = None
    price_vs_ma: str = ""


class TechnicalAnalysis(BaseModel):
    score: int = Field(0, ge=0, le=100)
    weight: int = Field(30, ge=0, le=100)
    trend_analysis: str = ""
    indicators: TechnicalIndicators = Field(default_factory=TechnicalIndicators)
    verdict: str = ""


class SentimentAnalysis(BaseModel):
    score: int = Field(0, ge=0, le=100)
    weight: int = Field(30, ge=0, le=100)
    recent_developments: list[str] = Field(default_factory=list)
    verdict: str = ""


class FinalVerdict(BaseModel):
    overall_score: int = Field(0, ge=0, le=100)
    rating: str = ""
    why_dimensions_align: str = ""
    conflicts: str = ""


class RiskActionPlan(BaseModel):
    if_you_own: str = ""
    if_you_want_to_buy: str = ""


class RiskAssessment(BaseModel):
    key_risks: list[str] = Field(default_factory=list)
    action_plan: RiskActionPlan = Field(default_factory=RiskActionPlan)


class ScoreSignal(BaseModel):
    name: str
    value: float | str | None = None
    points: float = 0.0
    reason: str = ""


class DimensionRuleScore(BaseModel):
    score: int = Field(0, ge=0, le=100)
    max_score: int = 100
    signals: list[ScoreSignal] = Field(default_factory=list)
    data_completeness: float = Field(0.0, ge=0.0, le=1.0)


class RuleScores(BaseModel):
    fundamental: DimensionRuleScore = Field(default_factory=DimensionRuleScore)
    technical: DimensionRuleScore = Field(default_factory=DimensionRuleScore)
    sentiment: DimensionRuleScore = Field(default_factory=DimensionRuleScore)


class ScoreWeights(BaseModel):
    fundamental: int = 40
    technical: int = 30
    sentiment: int = 30


class OverallRuleScore(BaseModel):
    weighted_score: float = Field(0.0, ge=0.0, le=100.0)
    recommendation: Recommendation = Recommendation.HOLD
    band: str = "55-74"
    confidence: int = Field(0, ge=0, le=100)
    setup_quality: int = Field(0, ge=0, le=100)


class ScoringEngineBlock(BaseModel):
    version: str = "phase3-rules-v1"
    weights: ScoreWeights = Field(default_factory=ScoreWeights)
    rule_scores: RuleScores = Field(default_factory=RuleScores)
    overall: OverallRuleScore = Field(default_factory=OverallRuleScore)


class LlmScoreSuggestion(BaseModel):
    fundamental: int = Field(0, ge=0, le=100)
    technical: int = Field(0, ge=0, le=100)
    sentiment: int = Field(0, ge=0, le=100)
    overall: int = Field(0, ge=0, le=100)
    recommendation: Recommendation = Recommendation.HOLD


class LlmAgreement(BaseModel):
    matches_recommendation: bool = True
    overall_score_delta: int = 0


class LlmReview(BaseModel):
    enabled: bool = False
    model: str = "not_configured"
    llm_score_suggestion: LlmScoreSuggestion = Field(default_factory=LlmScoreSuggestion)
    agreement_with_rules: LlmAgreement = Field(default_factory=LlmAgreement)
    rationale: str = ""
    warnings: list[str] = Field(default_factory=list)
    citations_used: list[str] = Field(default_factory=list)


class PlannedStepOut(BaseModel):
    """Planner DAG node (human-readable; mirrors agents.planner.PlannedStep)."""

    id: str
    description: str = ""


class PipelineStepTrace(BaseModel):
    """Executor timing record for one executed or skipped step."""

    step_id: str
    description: str = ""
    status: str = "ok"  # ok | skipped | error
    duration_ms: float = 0.0
    detail: str | None = None


class CriticResult(BaseModel):
    """Phase 6 critic — advisory flags; does not replace deterministic recommendation."""

    passed: bool = True
    incomplete_evidence: bool = False
    flags: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


class AgentPipelineBlock(BaseModel):
    """Phase 6 — planner output + executor trace + critic assessment."""

    planner_version: str = "phase6-v1"
    plan_summary: str = ""
    planned_steps: list[PlannedStepOut] = Field(default_factory=list)
    execution_trace: list[PipelineStepTrace] = Field(default_factory=list)
    critic: CriticResult = Field(default_factory=CriticResult)


class MemoryBlock(BaseModel):
    """Phase 7 — session memory echoed on analyze responses for follow-up UX / future chat."""

    session_id: str = "default"
    recent_tickers: list[str] = Field(default_factory=list)
    preferred_horizon: str | None = None
    analysis_style: str | None = "balanced"
    session_summary: str = ""
    follow_up_context: str = ""


class BuySellReport(BaseModel):
    schema_version: str = SCHEMA_VERSION
    ticker: str
    recommendation: Recommendation
    confidence: int = Field(0, ge=0, le=100)
    optimal_timeframe: str = ""
    setup_quality: int = Field(0, ge=0, le=100)
    investment_thesis: InvestmentThesis = Field(default_factory=InvestmentThesis)
    fundamental_analysis: FundamentalAnalysis = Field(default_factory=FundamentalAnalysis)
    technical_analysis: TechnicalAnalysis = Field(default_factory=TechnicalAnalysis)
    sentiment_analysis: SentimentAnalysis = Field(default_factory=SentimentAnalysis)
    final_verdict: FinalVerdict = Field(default_factory=FinalVerdict)
    risk_assessment: RiskAssessment = Field(default_factory=RiskAssessment)
    scoring_engine: ScoringEngineBlock = Field(default_factory=ScoringEngineBlock)
    llm_review: LlmReview = Field(default_factory=LlmReview)
    citations: list[CitationItem] = Field(default_factory=list)
    disclaimer: str = Field(
        default=(
            "This report is generated for educational and research purposes only "
            "and does not constitute financial, investment, or legal advice."
        )
    )
    agent_pipeline: AgentPipelineBlock | None = None
    memory: MemoryBlock | None = None


def mock_buy_sell_report() -> BuySellReport:
    """Placeholder report for Phase 1 UI — replace with pipeline output later."""
    return BuySellReport(
        schema_version=SCHEMA_VERSION,
        ticker="AAPL",
        recommendation=Recommendation.BUY,
        confidence=78,
        optimal_timeframe="3–6 months",
        setup_quality=72,
        investment_thesis=InvestmentThesis(
            summary=(
                "Large-cap platform with recurring services revenue and strong cash generation; "
                "valuation moderates upside unless growth reaccelerates."
            ),
            key_drivers=[
                "Services mix and gross margin resilience",
                "Capital returns via buybacks/dividends",
                "Regulatory and China demand overhangs",
            ],
        ),
        fundamental_analysis=FundamentalAnalysis(
            score=76,
            weight=40,
            business_performance=(
                "Revenue growth has normalized post-cycle; profitability remains robust vs peers."
            ),
            valuation_analysis=ValuationAnalysis(
                pe=28.5,
                dcf_value=210.0,
                current_price=195.0,
                implied_upside=7.7,
            ),
            bull_bear_integration=(
                "Bulls cite ecosystem lock-in; bears cite multiple compression if growth stays mid-single-digit."
            ),
            verdict="Fundamentals support a constructive bias with valuation as the main gating factor.",
        ),
        technical_analysis=TechnicalAnalysis(
            score=71,
            weight=30,
            trend_analysis="Price above rising 50-day average; 200-day slope positive but momentum mixed.",
            indicators=TechnicalIndicators(
                rsi=58.0,
                macd_signal="bullish crossover (sample)",
                ma_50=192.0,
                ma_200=185.0,
                price_vs_ma="Above both MAs",
            ),
            verdict="Trend structure constructive; watch for exhaustion if RSI extends into overbought.",
        ),
        sentiment_analysis=SentimentAnalysis(
            score=68,
            weight=30,
            recent_developments=[
                "Headlines skew neutral-to-positive on product cycle (sample).",
                "Analyst revisions mixed; no uniform upgrade wave (sample).",
            ],
            verdict="Sentiment supportive but not euphoric — room for headline volatility.",
        ),
        final_verdict=FinalVerdict(
            overall_score=72,
            rating="BUY",
            why_dimensions_align=(
                "Fundamentals and technicals agree on stability with upside optionality; sentiment is not a drag."
            ),
            conflicts=(
                "Valuation leaves less margin of safety if growth disappoints — size and horizon matter."
            ),
        ),
        risk_assessment=RiskAssessment(
            key_risks=[
                "Consumer demand and China exposure",
                "Regulatory / antitrust outcomes",
                "Multiple compression in a higher-rate regime",
            ],
            action_plan=RiskActionPlan(
                if_you_own="Consider position sizing vs portfolio risk; trail stops or rebalance on strength.",
                if_you_want_to_buy="Scale in over time; pair entry with predefined downside tolerance.",
            ),
        ),
        scoring_engine=ScoringEngineBlock(
            overall=OverallRuleScore(
                weighted_score=72.0,
                recommendation=Recommendation.BUY,
                band="55-74",
                confidence=78,
                setup_quality=72,
            )
        ),
        llm_review=LlmReview(
            enabled=False,
            model="not_configured",
            llm_score_suggestion=LlmScoreSuggestion(
                fundamental=76,
                technical=71,
                sentiment=68,
                overall=72,
                recommendation=Recommendation.BUY,
            ),
            agreement_with_rules=LlmAgreement(matches_recommendation=True, overall_score_delta=0),
            rationale="LLM review is disabled in the mock path; values mirror deterministic scores.",
            warnings=["Set up an LLM client to enable advisory review."],
            citations_used=["c1", "c2"],
        ),
        citations=[
            CitationItem(
                id="c1",
                title="Company filings / fundamentals snapshot (placeholder)",
                source="SEC EDGAR (to be wired)",
                url="https://www.sec.gov/edgar",
                date="2026-01-01",
                snippet="Replace with retrieved filing chunk in Phase 5.",
            ),
            CitationItem(
                id="c2",
                title="Market data / technicals (placeholder)",
                source="Yahoo Finance via yfinance (to be wired)",
                snippet="OHLC and indicators will cite tool outputs.",
            ),
        ],
    )
