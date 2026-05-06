from __future__ import annotations

import sys
from pathlib import Path

from fastapi.testclient import TestClient


def _client() -> TestClient:
    # Ensure `backend/` is on sys.path so `from app.main import app` works in CI.
    backend_root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(backend_root))
    from app.main import app  # noqa: WPS433

    return TestClient(app)


def test_routes_register_and_health_ok() -> None:
    client = _client()
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json().get("status") == "ok"

    # Sanity: core routers appear in OpenAPI paths
    openapi = client.get("/openapi.json")
    assert openapi.status_code == 200
    paths = (openapi.json() or {}).get("paths") or {}
    assert "/api/analysis/fundamental" in paths
    assert "/api/evaluation/compare-models" in paths
    assert "/api/agentic-research/run" in paths


def test_fundamental_requires_bearer_token() -> None:
    client = _client()
    r = client.get("/api/analysis/fundamental", params={"ticker": "AAPL"})
    assert r.status_code == 401

