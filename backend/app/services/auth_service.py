"""Real JWT authentication with SQLite user store."""

from __future__ import annotations

import re
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

# DB lives at backend/data/users.db
_DB_PATH = Path(__file__).resolve().parents[2] / "data" / "users.db"

_pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")
_ALGORITHM = "HS256"
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


# ── DB bootstrap ──────────────────────────────────────────────────────────────

def _connect() -> sqlite3.Connection:
    _DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(_DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def _init_db() -> None:
    with _connect() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                email         TEXT    UNIQUE NOT NULL,
                password_hash TEXT    NOT NULL,
                created_at    TEXT    NOT NULL
            )
        """)
        conn.commit()


_init_db()


# ── Token helpers ─────────────────────────────────────────────────────────────

def _make_token(email: str) -> str:
    exp = datetime.now(timezone.utc) + timedelta(hours=settings.jwt_expire_hours)
    return jwt.encode(
        {"sub": email, "exp": exp},
        settings.jwt_secret_key,
        algorithm=_ALGORITHM,
    )


def normalize_email(email: str) -> str:
    return email.strip().lower()


# ── Public API ────────────────────────────────────────────────────────────────

def register(email: str, password: str) -> tuple[str, str]:
    """
    Create a new user. Returns (access_token, normalized_email).
    Raises ValueError on validation failure or duplicate email.
    """
    em = normalize_email(email)
    if not em or not _EMAIL_RE.match(em):
        raise ValueError("Enter a valid email address.")
    if not password or len(password) < 6:
        raise ValueError("Password must be at least 6 characters.")
    pw_hash = _pwd.hash(password)
    try:
        with _connect() as conn:
            conn.execute(
                "INSERT INTO users (email, password_hash, created_at) VALUES (?, ?, ?)",
                (em, pw_hash, datetime.now(timezone.utc).isoformat()),
            )
            conn.commit()
    except sqlite3.IntegrityError:
        raise ValueError("An account with this email already exists.")
    return _make_token(em), em


def login(email: str, password: str) -> tuple[str, str]:
    """
    Verify credentials. Returns (access_token, normalized_email).
    Raises ValueError on invalid credentials.
    """
    em = normalize_email(email)
    if not em or not password:
        raise ValueError("Email and password are required.")
    if not _EMAIL_RE.match(em):
        raise ValueError("Enter a valid email address.")
    with _connect() as conn:
        row = conn.execute(
            "SELECT password_hash FROM users WHERE email = ?", (em,)
        ).fetchone()
    if row is None or not _pwd.verify(password, row["password_hash"]):
        raise ValueError("Invalid email or password.")
    return _make_token(em), em


def verify_access_token(token: str) -> str | None:
    """
    Decode and validate a JWT. Returns the email (sub) or None if invalid/expired.
    Drop-in replacement for the old mock verify_access_token — same signature.
    """
    if not token:
        return None
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[_ALGORITHM])
        email = payload.get("sub")
        if isinstance(email, str) and email:
            return email
    except JWTError:
        pass
    return None
