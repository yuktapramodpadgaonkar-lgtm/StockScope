from __future__ import annotations

import json
from typing import Any

import httpx

from app.core.config import settings
from app.schemas.buy_sell_analysis import (
    DimensionRuleScore,
    LlmAgreement,
    LlmReview,
    LlmScoreSuggestion,
    OverallRuleScore,
    Recommendation,
)


def _extract_json_object(raw: str) -> dict[str, Any]:
    raw = raw.strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass

    start = raw.find("{")
    end = raw.rfind("}")
    if start != -1 and end != -1 and end > start:
        chunk = raw[start : end + 1]
        return json.loads(chunk)
    raise ValueError("No JSON object found in model output.")


def _normalize_rec(v: Any, default: Recommendation) -> Recommendation:
    s = str(v or "").upper()
    if s == "BUY":
        return Recommendation.BUY
    if s == "SELL":
        return Recommendation.SELL
    if s == "HOLD":
        return Recommendation.HOLD
    return default


def _build_prompt(
    ticker: str,
    overall: OverallRuleScore,
    f: DimensionRuleScore,
    t: DimensionRuleScore,
    s: DimensionRuleScore,
    *,
    retrieval_evidence: list[dict[str, Any]] | None = None,
) -> str:
    context = {
        "ticker": ticker,
        "rule_scores": {
            "fundamental": f.model_dump(mode="json"),
            "technical": t.model_dump(mode="json"),
            "sentiment": s.model_dump(mode="json"),
            "overall": overall.model_dump(mode="json"),
        },
        # Phase 5: grounding snippets retrieved for this ticker (news/filings when available).
        "retrieval_evidence": retrieval_evidence or [],
        "task": (
            "You are an advisory reviewer. Do NOT replace rule scores. "
            "Return JSON only with keys: llm_score_suggestion, agreement_with_rules, rationale, warnings, citations_used."
        ),
        "constraints": {
            "score_range": "0-100 integers",
            "recommendation": ["BUY", "HOLD", "SELL"],
            "citations_used": (
                "array of chunk_id values taken ONLY from retrieval_evidence[].chunk_id "
                "when referencing claims; otherwise []"
            ),
            "warnings": "array of short strings",
        },
    }
    return (
        "Return ONLY valid JSON. No markdown, no extra text.\n"
        + json.dumps(context, ensure_ascii=True)
    )


def _hf_call(prompt: str) -> dict[str, Any]:
    token = (settings.huggingface_api_token or "").strip()
    if not token:
        raise RuntimeError("HUGGINGFACE_API_TOKEN is not configured.")

    model_id = (settings.hf_model_id or settings.buysell_llm_model or "").strip()
    endpoint_url = (settings.hf_inference_url or "").strip()
    if not endpoint_url and not model_id:
        raise RuntimeError("Set HF_MODEL_ID (generic API) or HF_INFERENCE_URL (endpoint mode).")

    url = endpoint_url or f"https://api-inference.huggingface.co/models/{model_id}"
    headers = {"Authorization": f"Bearer {token}"}
    payload = {
        "inputs": prompt,
        "parameters": {
            "max_new_tokens": 500,
            "temperature": 0.1,
            "return_full_text": False,
        },
    }

    with httpx.Client(timeout=float(settings.buysell_llm_timeout_seconds)) as client:
        r = client.post(url, headers=headers, json=payload)
        r.raise_for_status()
        data = r.json()

    # Common HF formats
    if isinstance(data, list) and data:
        first = data[0]
        if isinstance(first, dict):
            if "generated_text" in first:
                return _extract_json_object(str(first["generated_text"]))
            # Some endpoints may directly emit JSON object
            return first
    if isinstance(data, dict):
        if "generated_text" in data:
            return _extract_json_object(str(data["generated_text"]))
        return data
    raise RuntimeError("Unexpected Hugging Face response shape.")


def generate_hf_llm_review(
    *,
    ticker: str,
    overall: OverallRuleScore,
    fundamental: DimensionRuleScore,
    technical: DimensionRuleScore,
    sentiment: DimensionRuleScore,
    retrieval_chunks: list[dict[str, Any]] | None = None,
) -> LlmReview:
    ev: list[dict[str, Any]] = []
    for row in (retrieval_chunks or [])[:10]:
        if not isinstance(row, dict):
            continue
        ev.append(
            {
                "chunk_id": row.get("chunk_id"),
                "doc_type": row.get("doc_type"),
                "source": row.get("source"),
                "published_at": row.get("published_at"),
                "title": row.get("title"),
                "text": str(row.get("text") or "")[:900],
            }
        )

    prompt = _build_prompt(
        ticker,
        overall,
        fundamental,
        technical,
        sentiment,
        retrieval_evidence=ev,
    )
    parsed = _hf_call(prompt)

    s = parsed.get("llm_score_suggestion") or {}
    a = parsed.get("agreement_with_rules") or {}
    rec = _normalize_rec(s.get("recommendation"), overall.recommendation)

    suggestion = LlmScoreSuggestion(
        fundamental=int(max(0, min(100, s.get("fundamental", fundamental.score)))),
        technical=int(max(0, min(100, s.get("technical", technical.score)))),
        sentiment=int(max(0, min(100, s.get("sentiment", sentiment.score)))),
        overall=int(max(0, min(100, s.get("overall", int(round(overall.weighted_score)))))),
        recommendation=rec,
    )
    agreement = LlmAgreement(
        matches_recommendation=bool(a.get("matches_recommendation", suggestion.recommendation == overall.recommendation)),
        overall_score_delta=int(a.get("overall_score_delta", suggestion.overall - int(round(overall.weighted_score)))),
    )

    return LlmReview(
        enabled=True,
        model=(settings.hf_model_id or settings.buysell_llm_model or "huggingface-endpoint"),
        llm_score_suggestion=suggestion,
        agreement_with_rules=agreement,
        rationale=str(parsed.get("rationale") or "").strip(),
        warnings=[str(x) for x in (parsed.get("warnings") or [])][:5],
        citations_used=[str(x) for x in (parsed.get("citations_used") or [])][:10],
    )
