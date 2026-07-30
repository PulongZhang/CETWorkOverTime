import pyotp
from fastapi import APIRouter, HTTPException, Request, status

from app.core.config import get_settings
from app.schemas.auth import LoginRequest, SessionResponse

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=SessionResponse)
def login(payload: LoginRequest, request: Request) -> SessionResponse:
    if not pyotp.TOTP(get_settings().totp_secret).verify(payload.code, valid_window=1):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="动态验证码错误或已失效",
        )
    request.session.clear()
    request.session["authenticated"] = True
    return SessionResponse(authenticated=True)


@router.post("/logout", response_model=SessionResponse)
def logout(request: Request) -> SessionResponse:
    request.session.clear()
    return SessionResponse(authenticated=False)


@router.get("/session", response_model=SessionResponse)
def session_status(request: Request) -> SessionResponse:
    return SessionResponse(authenticated=bool(request.session.get("authenticated")))
