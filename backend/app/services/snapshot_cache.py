"""
In-process TTL cache for market snapshots.

Key is (universe, mode): one yfinance round-trip serves all mover types and limits
until the entry expires. For multiple uvicorn workers, each process has its own
cache; use Redis (or similar) if you need a shared cache in production.
"""

from __future__ import annotations

import time
from threading import Lock
from typing import Any, Callable, TypeVar

T = TypeVar("T")


class TtlCache:
    def __init__(self) -> None:
        self._store: dict[str, tuple[float, Any]] = {}
        self._lock = Lock()

    def get_or_set(self, key: str, ttl_seconds: float, factory: Callable[[], T]) -> T:
        with self._lock:
            hit = self._store.get(key)
            if hit is not None:
                expires_at, value = hit
                if time.monotonic() <= expires_at:
                    return value
                del self._store[key]

        value = factory()

        with self._lock:
            self._store[key] = (time.monotonic() + ttl_seconds, value)
        return value


snapshot_cache = TtlCache()
