from app.core.config import settings
from app.schemas.market_movers import MarketMoversResponse, MoverType, TimeMode, Universe
from app.services.market_data_provider import MarketDataProvider
from app.services.snapshot_cache import snapshot_cache


def _snapshot_cache_key(universe: Universe, mode: TimeMode) -> str:
    return f"{universe.value}:{mode.value}"


class MarketMoversService:
    def __init__(self, provider: MarketDataProvider | None = None) -> None:
        self.provider = provider or MarketDataProvider()

    def get_market_movers(
        self,
        universe: Universe,
        mode: TimeMode,
        mover_type: MoverType,
        limit: int,
    ) -> MarketMoversResponse:
        symbols = self.provider.get_symbols(universe)

        def load_snapshot() -> list[dict]:
            return self.provider.fetch_market_snapshot(symbols, mode=mode)

        if settings.movers_cache_enabled:
            ttl = (
                float(settings.movers_cache_ttl_intraday_seconds)
                if mode == TimeMode.intraday
                else float(settings.movers_cache_ttl_previous_day_seconds)
            )
            rows = snapshot_cache.get_or_set(_snapshot_cache_key(universe, mode), ttl, load_snapshot)
        else:
            rows = load_snapshot()

        if mover_type == MoverType.gainers:
            ranked = sorted(rows, key=lambda x: (x.get("change_percent") is None, -(x.get("change_percent") or 0)))
        elif mover_type == MoverType.losers:
            ranked = sorted(rows, key=lambda x: (x.get("change_percent") is None, x.get("change_percent") or 0))
        elif mover_type == MoverType.high_52w:
            ranked = sorted(
                rows,
                key=lambda x: (
                    x.get("high_52w") is None or x.get("price") is None,
                    abs((x.get("high_52w") or 0) - (x.get("price") or 0)),
                ),
            )
        else:
            ranked = sorted(
                rows,
                key=lambda x: (
                    x.get("low_52w") is None or x.get("price") is None,
                    abs((x.get("low_52w") or 0) - (x.get("price") or 0)),
                ),
            )

        items = ranked[:limit]
        return MarketMoversResponse(
            universe=universe,
            mode=mode,
            type=mover_type,
            count=len(items),
            items=items,
        )
