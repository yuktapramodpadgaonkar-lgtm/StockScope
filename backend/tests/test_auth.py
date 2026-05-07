"""
Integration tests for the /api/auth endpoints and verify_access_token helper.

Uses FastAPI TestClient — no real HTTP, no real SQLite (redirected to tmp_path).
Password context is replaced with a fast deterministic stub so the tests are
independent of the installed bcrypt version (passlib 1.7.x vs bcrypt >= 4.0).
"""
from __future__ import annotations

import sqlite3
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

_BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_BACKEND))

from app.main import app  # noqa: E402
from app.services import auth_service  # noqa: E402
from app.services.auth_service import verify_access_token  # noqa: E402

client = TestClient(app)


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def _in_memory_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Redirect auth_service to a fresh SQLite file per test (isolation)."""
    db_path = tmp_path / "test_users.db"
    monkeypatch.setattr(auth_service, "_DB_PATH", db_path)

    def _connect_tmp() -> sqlite3.Connection:
        db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(db_path), check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    monkeypatch.setattr(auth_service, "_connect", _connect_tmp)
    auth_service._init_db()


@pytest.fixture(autouse=True)
def _mock_pwd(monkeypatch: pytest.MonkeyPatch) -> None:
    """
    Replace the bcrypt CryptContext with a fast stub.

    passlib 1.7.4 + bcrypt >= 4.0 is incompatible: bcrypt 4.x removed __about__
    and rejects passwords > 72 bytes in hashpw, breaking passlib's detect_wrap_bug
    initialization. The stub makes tests independent of the installed bcrypt version.
    """
    mock = MagicMock()
    mock.hash.side_effect = lambda pw, **_: f"stub:{pw}"
    mock.verify.side_effect = lambda pw, h: h == f"stub:{pw}"
    monkeypatch.setattr(auth_service, "_pwd", mock)


# ── /register ─────────────────────────────────────────────────────────────────

def test_register_success_returns_token_and_email() -> None:
    res = client.post("/api/auth/register", json={"email": "alice@test.com", "password": "secret1"})
    assert res.status_code == 201
    body = res.json()
    assert "access_token" in body
    assert body["user"]["email"] == "alice@test.com"
    assert len(body["access_token"]) > 20


def test_register_duplicate_email_returns_400() -> None:
    payload = {"email": "bob@test.com", "password": "secret1"}
    client.post("/api/auth/register", json=payload)
    res = client.post("/api/auth/register", json=payload)
    assert res.status_code == 400
    assert "already exists" in res.json()["detail"].lower()


def test_register_password_too_short_returns_400_or_422() -> None:
    res = client.post("/api/auth/register", json={"email": "carol@test.com", "password": "abc"})
    assert res.status_code in (400, 422)


def test_register_invalid_email_returns_400_or_422() -> None:
    res = client.post("/api/auth/register", json={"email": "notanemail", "password": "secret1"})
    assert res.status_code in (400, 422)


def test_register_missing_fields_returns_422() -> None:
    res = client.post("/api/auth/register", json={"email": "nopass@test.com"})
    assert res.status_code == 422


# ── /login ────────────────────────────────────────────────────────────────────

def test_login_success_returns_token() -> None:
    client.post("/api/auth/register", json={"email": "dave@test.com", "password": "hunter2"})
    res = client.post("/api/auth/login", json={"email": "dave@test.com", "password": "hunter2"})
    assert res.status_code == 200
    body = res.json()
    assert "access_token" in body
    assert body["user"]["email"] == "dave@test.com"


def test_login_wrong_password_returns_401() -> None:
    client.post("/api/auth/register", json={"email": "eve@test.com", "password": "correct"})
    res = client.post("/api/auth/login", json={"email": "eve@test.com", "password": "wrong"})
    assert res.status_code == 401
    assert "invalid" in res.json()["detail"].lower()


def test_login_unknown_email_returns_401() -> None:
    res = client.post("/api/auth/login", json={"email": "ghost@test.com", "password": "secret1"})
    assert res.status_code == 401


def test_login_email_case_insensitive() -> None:
    """Registration normalizes email to lowercase; login should match."""
    client.post("/api/auth/register", json={"email": "Frank@Test.COM", "password": "secret1"})
    res = client.post("/api/auth/login", json={"email": "frank@test.com", "password": "secret1"})
    assert res.status_code == 200


# ── /me ───────────────────────────────────────────────────────────────────────

def test_me_with_valid_token_returns_email() -> None:
    reg = client.post("/api/auth/register", json={"email": "grace@test.com", "password": "secret1"})
    token = reg.json()["access_token"]
    res = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    assert res.json()["user"]["email"] == "grace@test.com"


def test_me_without_token_returns_401() -> None:
    res = client.get("/api/auth/me")
    assert res.status_code == 401


# ── verify_access_token ───────────────────────────────────────────────────────

def test_verify_access_token_returns_email_for_valid_token() -> None:
    token, email = auth_service.register("heidi@test.com", "secret1")
    assert verify_access_token(token) == "heidi@test.com"


def test_verify_access_token_returns_none_for_forged_token() -> None:
    assert verify_access_token("this.is.not.a.valid.jwt") is None


def test_verify_access_token_returns_none_for_empty_string() -> None:
    assert verify_access_token("") is None


def test_verify_access_token_returns_none_for_tampered_token() -> None:
    token, _ = auth_service.register("ivan@test.com", "secret1")
    tampered = token[:-4] + "xxxx"
    assert verify_access_token(tampered) is None
