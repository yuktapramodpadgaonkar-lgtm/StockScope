"""Mock authentication for milestone 1 — no database, no OAuth, no password hashing."""

from __future__ import annotations

import base64
import json
import re

_TOKEN_PREFIX = "mock."

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def normalize_email(email: str) -> str:
    return email.strip().lower()


def login(email: str, password: str) -> tuple[str, str]:
    """
    Accept any non-empty password and a loosely valid-looking email.
    Returns (access_token, normalized_email). Raises ValueError on invalid input.
    """
    em = normalize_email(email)
    if not em or not password:
        raise ValueError("Email and password are required")
    if not _EMAIL_RE.match(em):
        raise ValueError("Enter a valid email address")
    token = _encode_mock_token(em)
    return token, em


def _encode_mock_token(email: str) -> str:
    payload = json.dumps({"email": email})
    b64 = base64.urlsafe_b64encode(payload.encode()).decode().rstrip("=")
    return f"{_TOKEN_PREFIX}{b64}"


def verify_access_token(token: str) -> str | None:
    """Return email if token is a valid mock token, else None."""
    if not token or not token.startswith(_TOKEN_PREFIX):
        return None
    b64 = token[len(_TOKEN_PREFIX) :]
    pad = (4 - len(b64) % 4) % 4
    padded = b64 + ("=" * pad)
    try:
        raw = base64.urlsafe_b64decode(padded.encode())
        data = json.loads(raw.decode())
        email = data.get("email")
        if isinstance(email, str) and email:
            return email
    except (json.JSONDecodeError, ValueError, UnicodeDecodeError):
        pass
    return None
