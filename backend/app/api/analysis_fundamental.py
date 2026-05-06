from __future__ import annotations

import json
import re

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.schemas.fundamental import FundamentalAnalysisResponse
from app.services.ai.fundamental_prompt import build_fundamental_prompt, build_fundamental_repair_prompt
from app.services.auth_service import verify_access_token
from app.services.fundamental_service import get_fundamental_report
from services.ai.llm_service import LLMService

router = APIRouter(prefix="/api/analysis/fundamental", tags=["Fundamental Analysis"])

LLM_UNAVAILABLE = "AI summary unavailable. Deterministic analysis is still provided."
_bearer = HTTPBearer(auto_error=False)
_llm = LLMService()
_NUM_RE = re.compile(r"\b\d+(?:\.\d+)?\b")


def _ai_error_message(llm_detail: str | None) -> str:
    detail = (llm_detail or "").strip()
    if not detail:
        return LLM_UNAVAILABLE
    cap = 320
    if len(detail) > cap:
        detail = detail[: cap - 1] + "…"
    return f"{LLM_UNAVAILABLE} ({detail})"


def _significant_numbers(text: str) -> list[str]:
    out: list[str] = []
    for m in _NUM_RE.finditer(text or ""):
        s = m.group(0)
        if "." in s:
            out.append(s)
            continue
        try:
            n = int(s)
        except ValueError:
            continue
        # ignore likely years and tiny integers
        if 1990 <= n <= 2035:
            continue
        if n < 10:
            continue
        out.append(s)
    return out


def _fundamental_summary_needs_repair(summary: str, report: dict) -> bool:
    corpus = json.dumps(report, ensure_ascii=False)
    for num in _significant_numbers(summary):
        if num not in corpus:
            return True
    return False


def _require_bearer_email(creds: HTTPAuthorizationCredentials | None = Depends(_bearer)) -> str:
    if creds is None or not creds.credentials:
        raise HTTPException(status_code=401, detail="Not authenticated")
    email = verify_access_token(creds.credentials)
    if email is None:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return email


@router.get("", response_model=FundamentalAnalysisResponse)
def get_fundamental_analysis(
    ticker: str = Query(..., min_length=1, max_length=32, description="Stock symbol, e.g. AAPL"),
    include_llm: bool = Query(
        False,
        description="If true, request an optional AI explanation (best-effort).",
    ),
    preferred_model: str = Query(
        "gemini",
        description="Preferred LLM: gemini | llama | mistral (auto-fallback applies).",
    ),
    _email: str = Depends(_require_bearer_email),
) -> FundamentalAnalysisResponse:
    try:
        data = get_fundamental_report(ticker)
    except ValueError as e:
        msg = str(e)
        if "required" in msg.lower():
            raise HTTPException(status_code=400, detail=msg) from e
        raise HTTPException(status_code=404, detail=msg) from e

    ai_summary: str | None = None
    ai_model: str | None = None
    ai_error: str | None = None

    if include_llm:
        prompt = build_fundamental_prompt(data)
        llm_result = _llm.generate_response(prompt, preferred_model=preferred_model)
        if llm_result.error or not llm_result.response:
            ai_error = _ai_error_message(llm_result.error)
        else:
            ai_summary = llm_result.response
            ai_model = llm_result.model_used
            if isinstance(ai_summary, str) and ai_summary.strip() and _fundamental_summary_needs_repair(ai_summary, data):
                repair_prompt = build_fundamental_repair_prompt(
                    report=data,
                    previous_text=ai_summary,
                    problem="numeric_claim_not_in_deterministic_report",
                )
                repair_result = _llm.generate_response(repair_prompt, preferred_model=preferred_model)
                if not repair_result.error and repair_result.response:
                    ai_summary = repair_result.response.strip()
                    ai_model = repair_result.model_used
                else:
                    ai_error = _ai_error_message("AI summary contained unsupported numeric claims; repair failed")

    payload = {
        **data,
        "ai_summary": ai_summary,
        "ai_model": ai_model,
        "ai_error": ai_error,
    }
    return FundamentalAnalysisResponse.model_validate(payload)
