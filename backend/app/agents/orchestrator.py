from __future__ import annotations

from app.agents.critic import run_critic
from app.agents.executor import execute_buy_sell_pipeline
from app.agents.planner import plan_buy_sell_analysis
from app.schemas.buy_sell_analysis import (
    SCHEMA_VERSION,
    AgentPipelineBlock,
    BuySellReport,
    PlannedStepOut,
)


def run_buy_sell_with_agents(
    *,
    ticker: str,
    period: str,
    interval: str,
    news_limit: int,
    include_retrieval: bool,
    include_llm_review: bool,
    retrieval_top_k: int,
    retrieval_max_age_days: int | None,
    horizon: str | None = None,
    retrieval_query: str | None = None,
    memory_hint: str | None = None,
    preferred_model: str = "gemini",
) -> BuySellReport:
    """
    Phase 6 entrypoint: plan → execute → attach critic metadata to the report.
    """
    plan = plan_buy_sell_analysis(
        horizon=horizon,
        include_retrieval=include_retrieval,
        include_llm_review=include_llm_review,
    )
    outcome = execute_buy_sell_pipeline(
        ticker=ticker,
        period=period,
        interval=interval,
        news_limit=news_limit,
        include_retrieval=include_retrieval,
        include_llm_review=include_llm_review,
        retrieval_top_k=retrieval_top_k,
        retrieval_max_age_days=retrieval_max_age_days,
        retrieval_query=retrieval_query,
        preferred_model=preferred_model,
    )

    critic = run_critic(
        report=outcome.report,
        bundle=outcome.bundle,
        retrieved=outcome.retrieved,
        include_retrieval=include_retrieval,
        include_llm_review=include_llm_review,
    )

    planned = [PlannedStepOut(id=s.id, description=s.description) for s in plan.steps]
    summary_parts: list[str] = [
        f"horizon={plan.horizon}",
        f"steps_planned={len(plan.steps)}",
        f"steps_executed={len(outcome.steps)}",
    ]
    if memory_hint:
        summary_parts.append("memory_context=present")
    block = AgentPipelineBlock(
        planner_version=plan.planner_version,
        plan_summary="; ".join(summary_parts),
        planned_steps=planned,
        execution_trace=outcome.steps,
        critic=critic,
    )

    return outcome.report.model_copy(
        update={
            "schema_version": SCHEMA_VERSION,
            "agent_pipeline": block,
        }
    )
