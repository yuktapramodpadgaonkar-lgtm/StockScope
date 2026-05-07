from __future__ import annotations

import sqlite3
import sys
import uuid
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

_BACKEND = Path(__file__).resolve().parents[1]
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))


def _client() -> TestClient:
    from app.main import app  # noqa: WPS433

    return TestClient(app)


# Patch bcrypt (passlib 1.7.4 + bcrypt ≥4 incompatible) and use a temp DB so
# smoke auth tests are hermetic and don't require a specific bcrypt version.
@pytest.fixture(autouse=True)
def _smoke_auth_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from app.services import auth_service

    db_path = tmp_path / "smoke_users.db"

    def _connect_tmp():
        conn = sqlite3.connect(str(db_path), check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    monkeypatch.setattr(auth_service, "_DB_PATH", db_path)
    monkeypatch.setattr(auth_service, "_connect", _connect_tmp)
    auth_service._init_db()

    mock_pwd = MagicMock()
    mock_pwd.hash.side_effect = lambda pw, **_: f"stub:{pw}"
    mock_pwd.verify.side_effect = lambda pw, h: h == f"stub:{pw}"
    monkeypatch.setattr(auth_service, "_pwd", mock_pwd)


# ── Route/schema sanity ───────────────────────────────────────────────────────

def test_health_ok() -> None:
    r = _client().get("/health")
    assert r.status_code == 200
    assert r.json().get("status") == "ok"


def test_openapi_core_routes_present() -> None:
    paths = (_client().get("/openapi.json").json() or {}).get("paths") or {}
    for expected in (
        "/api/analysis/fundamental",
        "/api/evaluation/compare-models",
        "/api/agentic-research/run",
        "/api/auth/register",
        "/api/auth/login",
        "/api/buy-sell/report/mock",
        "/api/history",
        "/api/chat/query",
    ):
        assert expected in paths, f"Missing route: {expected}"


# ── Auth register → login round-trip ─────────────────────────────────────────

def test_auth_register_and_login() -> None:
    client = _client()
    # Use a unique email each run to avoid stale-DB conflicts across test sessions.
    email = f"smoke_{uuid.uuid4().hex[:8]}@example.com"
    password = "smoke-password-123"

    r = client.post("/api/auth/register", json={"email": email, "password": password})
    assert r.status_code in (200, 201), f"Register failed: {r.text}"

    r = client.post("/api/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, f"Login failed: {r.text}"
    body = r.json()
    assert "access_token" in body
    token = body["access_token"]
    assert isinstance(token, str) and len(token) > 20

    r = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    # /me returns {"user": {"email": ...}}
    me = r.json()
    assert (me.get("email") or (me.get("user") or {}).get("email")) == email


def test_login_wrong_password_returns_401() -> None:
    client = _client()
    r = client.post("/api/auth/login", json={"email": "nobody@example.com", "password": "wrong"})
    assert r.status_code in (401, 400)


# ── Buy/sell mock endpoint ────────────────────────────────────────────────────

def test_buy_sell_mock_returns_report() -> None:
    r = _client().get("/api/buy-sell/report/mock")
    assert r.status_code == 200
    body = r.json()
    assert "recommendation" in body
    assert body["recommendation"] in ("BUY", "HOLD", "SELL")
    assert "ticker" in body
    assert "investment_thesis" in body


# ── Chat query (anonymous) ────────────────────────────────────────────────────

def test_chat_query_anonymous_returns_structured_response() -> None:
    r = _client().post(
        "/api/chat/query",
        json={"query": "What is a P/E ratio?", "thread_id": None},
    )
    assert r.status_code == 200
    body = r.json()
    assert "answer" in body
    assert isinstance(body["answer"], str) and len(body["answer"]) > 0
    assert "disclaimer" in body


def test_chat_query_financial_advice_is_rejected() -> None:
    r = _client().post(
        "/api/chat/query",
        json={"query": "Should I buy AAPL right now?", "thread_id": None},
    )
    assert r.status_code == 200
    body = r.json()
    assert body.get("detected_intent") == "financial_advice_rejected"


# ── Market movers ─────────────────────────────────────────────────────────────

def test_market_movers_gainers_returns_list() -> None:
    r = _client().get("/api/market-movers", params={"type": "gainers"})
    # 429 / 503 means yfinance is rate-limited in CI — not a code defect.
    if r.status_code in (429, 503):
        pytest.skip("yfinance rate-limited; skipping live market-movers test")
    assert r.status_code == 200
    body = r.json()
    assert "items" in body
    assert isinstance(body["items"], list)


# ── History (unauthenticated returns empty, not 500) ─────────────────────────

def test_history_unauthenticated_returns_200() -> None:
    r = _client().get("/api/history")
    assert r.status_code == 200


# ── News sentiment (no API keys → fallback, not 500) ─────────────────────────

def test_news_sentiment_fallback_not_500() -> None:
    r = _client().post(
        "/api/analysis/news-sentiment",
        json={"ticker": "AAPL", "max_articles": 3, "use_rag": False},
    )
    assert r.status_code == 200
    body = r.json()
    assert body.get("ticker") == "AAPL"
    assert "aggregate_sentiment" in body
