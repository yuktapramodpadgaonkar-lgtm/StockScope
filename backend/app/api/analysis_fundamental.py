from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.schemas.fundamental import FundamentalAnalysisResponse
from app.services.ai.fundamental_prompt import build_fundamental_prompt
from app.services.ai.llm_client import generate_text
from app.services.auth_service import verify_access_token
from app.services.fundamental_service import get_fundamental_report

router = APIRouter(prefix="/api/analysis/fundamental", tags=["Fundamental Analysis"])

LLM_UNAVAILABLE = "AI summary unavailable. Deterministic analysis is still provided."


def _ai_error_message(llm_detail: str | None) -> str:
    detail = (llm_detail or "").strip()
    if not detail:
        return LLM_UNAVAILABLE
    # Keep UI readable; full Gemini/Ollama hints help debug (model 404, bad key, etc.).
    cap = 320
    if len(detail) > cap:
        detail = detail[: cap - 1] + "…"
    return f"{LLM_UNAVAILABLE} ({detail})"
_bearer = HTTPBearer(auto_error=False)


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
    provider: str = Query(
        "ollama",
        description="LLM provider to use when include_llm is true (ollama|gemini).",
    ),
    model: str = Query(
        "mistral:7b",
        description="LLM model id. Examples: mistral:7b, llama3.1:8b, gemini-3-flash-preview.",
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
        result = generate_text(prompt, provider=provider, model=model)
        ai_model = result.get("model") or model
        ai_summary = result.get("text")
        if result.get("error"):
            ai_summary = None
            ai_error = _ai_error_message(str(result.get("error")))

    payload = {
        **data,
        "ai_summary": ai_summary,
        "ai_model": ai_model,
        "ai_error": ai_error,
    }
    return FundamentalAnalysisResponse.model_validate(payload)
