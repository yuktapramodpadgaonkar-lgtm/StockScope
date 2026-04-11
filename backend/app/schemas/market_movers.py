from enum import Enum
from pydantic import BaseModel, Field


class Universe(str, Enum):
    all = "all"
    sp500 = "sp500"
    dow30 = "dow30"
    nasdaq100 = "nasdaq100"
    russell1000 = "russell1000"


class TimeMode(str, Enum):
    intraday = "intraday"
    previous_day = "previous_day"


class MoverType(str, Enum):
    gainers = "gainers"
    losers = "losers"
    high_52w = "52w_high"
    low_52w = "52w_low"


class MarketMoverItem(BaseModel):
    symbol: str
    company_name: str | None = None
    price: float | None = None
    change: float | None = None
    change_percent: float | None = None
    volume: int | None = None
    market_cap: float | None = None
    sector: str | None = None
    industry: str | None = None
    high_52w: float | None = None
    low_52w: float | None = None


class MarketMoversResponse(BaseModel):
    universe: Universe
    mode: TimeMode
    type: MoverType
    count: int = Field(..., ge=0)
    items: list[MarketMoverItem]
