from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from app.schemas.fundamental import FundamentalAnalysisResponse
from app.services.fundamental_service import get_fundamental_report

router = APIRouter(prefix="/api/analysis/fundamental", tags=["Fundamental Analysis"])


@router.get("", response_model=FundamentalAnalysisResponse)
def get_fundamental_analysis(
    ticker: str = Query(..., min_length=1, max_length=32, description="Stock symbol, e.g. AAPL"),
) -> FundamentalAnalysisResponse:
    try:
        data = get_fundamental_report(ticker)
    except ValueError as e:
        msg = str(e)
        if "required" in msg.lower():
            raise HTTPException(status_code=400, detail=msg) from e
        raise HTTPException(status_code=404, detail=msg) from e
    return FundamentalAnalysisResponse.model_validate(data)
