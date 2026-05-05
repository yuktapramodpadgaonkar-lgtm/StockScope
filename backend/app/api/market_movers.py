from __future__ import annotations

from fastapi import APIRouter, Query

from app.schemas.market_movers import MarketMoversResponse, MoverType, TimeMode, Universe
from app.services.market_movers_service import MarketMoversService

router = APIRouter(prefix="/api/market-movers", tags=["Market Movers"])
service = MarketMoversService()


@router.get("", response_model=MarketMoversResponse)
def get_market_movers(
    universe: Universe = Query(default=Universe.sp500),
    mode: TimeMode = Query(default=TimeMode.intraday),
    type: MoverType = Query(default=MoverType.gainers),
    limit: int = Query(default=25, ge=1, le=200),
) -> MarketMoversResponse:
    return service.get_market_movers(universe=universe, mode=mode, mover_type=type, limit=limit)
