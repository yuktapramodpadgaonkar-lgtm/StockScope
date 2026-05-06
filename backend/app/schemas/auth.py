from __future__ import annotations

from pydantic import BaseModel, Field


class RegisterRequest(BaseModel):
    email: str = Field(min_length=1, max_length=254, description="User email")
    password: str = Field(min_length=6, max_length=256, description="Password (min 6 chars)")


class LoginRequest(BaseModel):
    email: str = Field(min_length=1, max_length=254, description="User email")
    password: str = Field(min_length=1, max_length=256, description="Password")


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
    detail: str = "Token is stateless; discard it on the client to log out."
