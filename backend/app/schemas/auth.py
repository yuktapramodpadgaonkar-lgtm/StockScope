from __future__ import annotations

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    email: str = Field(min_length=1, max_length=254, description="User email")
    password: str = Field(min_length=1, max_length=256, description="Password (validated by mock rules)")


class UserPublic(BaseModel):
    email: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserPublic


class MeResponse(BaseModel):
    user: UserPublic


class LogoutResponse(BaseModel):
    ok: bool = True
    detail: str = "Mock auth is stateless; discard the token on the client."
