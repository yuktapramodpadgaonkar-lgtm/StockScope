"""
Multi-model comparison endpoint.

Runs the same task/prompt through Gemini, LLaMA, and Mistral independently
and returns latency, citation count, and safety status for each.
"""

from __future__ import annotations

import time
from typing import Any, Literal

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.observability.jsonl_audit import log_model_call
from services.ai.llm_service import LLMService
from services.ai.prompts import build_multi_model_comparison_prompt
from services.ai.response_metrics import build_response_metrics

router = APIRouter(prefix="/api/evaluation", tags=["Evaluation"])

_llm = LLMService()

_DISCLAIMER = "Educational use only. Not financial advice."


# ── Schemas ───────────────────────────────────────────────────────────────────

class CompareRequest(BaseModel):
    task: Literal["chat", "sentiment", "buy_sell", "fundamental"]
    ticker: str = Field(..., min_length=1, max_length=16)
    query: str = Field(..., min_length=1, max_length=1000)


class ModelResult(BaseModel):
    model: str
    response: str
    latency_ms: int
    citation_count: int
    safety_passed: bool
    error: str | None = None
    metrics: dict[str, Any] | None = None


class CompareResponse(BaseModel):
    task: str
    ticker: str
    query: str
    results: list[ModelResult]
    disclaimer: str = _DISCLAIMER


# ── Helpers ───────────────────────────────────────────────────────────────────

def _call_single_model(
    model_name: str,
    prompt: str,
    *,
    eval_task: str = "compare",
) -> ModelResult:
    start = time.time()
    error: str | None = None
    response = ""
    try:
        if model_name == "gemini":
            response = _llm.generate_with_gemini(prompt)
        elif model_name == "llama":
            response = _llm.generate_with_ollama_llama(prompt)
        elif model_name == "mistral":
            response = _llm.generate_with_ollama_mistral(prompt)
        else:
            raise ValueError(f"Unknown model: {model_name}")
    except Exception as exc:  # noqa: BLE001
        error = str(exc)[:300]
        response = f"[Model unavailable: {error}]"

    latency_ms = int((time.time() - start) * 1000)
    provider = "google" if model_name == "gemini" else "ollama"
    log_model_call(
        provider=provider,
        model=model_name,
        task=f"evaluation.compare_models.{eval_task}",
        prompt=prompt,
        output=response if not error else None,
        latency_ms=latency_ms,
        error=error,
    )
    metrics = build_response_metrics(
        response,
        reference_text=prompt,
        task=eval_task,
        latency_ms=latency_ms,
    )
    return ModelResult(
        model=model_name,
        response=response,
        latency_ms=latency_ms,
        citation_count=int(metrics.get("citation_count") or 0),
        safety_passed=bool(metrics.get("safety", {}).get("passed")),
        error=error,
        metrics=metrics,
    )


# ── Endpoint ──────────────────────────────────────────────────────────────────

@router.post("/compare-models", response_model=CompareResponse)
def compare_models(body: CompareRequest) -> CompareResponse:
    """
    Run the same task prompt through Gemini, LLaMA, and Mistral.
    Returns latency, citation count, and safety status for each model.
    """
    ticker = body.ticker.strip().upper()
    prompt = build_multi_model_comparison_prompt(
        task=body.task,
        ticker=ticker,
        query=body.query.strip(),
    )

    results = [
        _call_single_model("gemini", prompt, eval_task=body.task),
        _call_single_model("llama", prompt, eval_task=body.task),
        _call_single_model("mistral", prompt, eval_task=body.task),
    ]

    return CompareResponse(
        task=body.task,
        ticker=ticker,
        query=body.query.strip(),
        results=results,
    )
