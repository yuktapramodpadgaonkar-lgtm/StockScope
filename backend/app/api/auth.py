from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.schemas.auth import (
    LoginRequest,
    LoginResponse,
    LogoutResponse,
    MeResponse,
    RegisterRequest,
    UserPublic,
)
from app.services.auth_service import login as auth_login
from app.services.auth_service import register as auth_register
from app.services.auth_service import verify_access_token

router = APIRouter(prefix="/api/auth", tags=["Auth"])
_bearer = HTTPBearer(auto_error=False)


@router.post("/register", response_model=LoginResponse, status_code=201)
def register(body: RegisterRequest) -> LoginResponse:
    """Register a new account and return a signed JWT."""
    try:
        token, email = auth_register(body.email, body.password)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return LoginResponse(access_token=token, user=UserPublic(email=email))


@router.post("/login", response_model=LoginResponse)
def login(body: LoginRequest) -> LoginResponse:
    """Verify credentials and return a signed JWT."""
    try:
        token, email = auth_login(body.email, body.password)
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e)) from e
    return LoginResponse(access_token=token, user=UserPublic(email=email))


@router.get("/me", response_model=MeResponse)
def me(creds: HTTPAuthorizationCredentials | None = Depends(_bearer)) -> MeResponse:
    if creds is None or not creds.credentials:
        raise HTTPException(status_code=401, detail="Not authenticated")
    email = verify_access_token(creds.credentials)
    if email is None:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return MeResponse(user=UserPublic(email=email))


@router.post("/logout", response_model=LogoutResponse)
def logout() -> LogoutResponse:
    return LogoutResponse()
