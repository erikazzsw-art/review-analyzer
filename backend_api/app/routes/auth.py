from __future__ import annotations

import random
import string
from datetime import datetime, timedelta, timezone

import bcrypt
from fastapi import APIRouter, HTTPException, Response, status

from backend_api.app.deps import clear_auth_cookies, set_auth_cookies
from backend_api.app.schemas.auth import (
    AuthResponse,
    LoginRequest,
    MessageResponse,
    PasswordResetConfirmRequest,
    PasswordResetRequest,
    RegisterRequest,
    UserPayload,
)
from review_analyzer.database import (
    create_reset_token,
    create_user,
    get_user_by_email,
    get_user_by_id,
    get_user_by_username,
    get_user_plan,
    get_valid_reset_token,
    mark_token_used,
    update_user_password,
)
from review_analyzer.mailer import send_reset_code

router = APIRouter(prefix="/auth", tags=["auth"])


def _hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def _verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))


def _user_payload(user_id: int) -> UserPayload:
    user = get_user_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        )
    return UserPayload(
        id=int(user["id"]),
        username=str(user["username"]),
        email=str(user.get("email") or ""),
        plan=get_user_plan(int(user["id"])),
    )


@router.post("/register", response_model=AuthResponse)
def register(payload: RegisterRequest, response: Response) -> AuthResponse:
    username = payload.username.strip()
    email = payload.email.strip()

    if get_user_by_username(username):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username already exists.",
        )

    if get_user_by_email(email):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already exists.",
        )

    user_id = create_user(username, _hash_password(payload.password), email)
    set_auth_cookies(response, user_id, username)
    return AuthResponse(
        user=_user_payload(user_id),
        message="Registration successful.",
    )


@router.post("/login", response_model=AuthResponse)
def login(payload: LoginRequest, response: Response) -> AuthResponse:
    username = payload.username.strip()
    user = get_user_by_username(username)
    if not user or not _verify_password(payload.password, str(user["password_hash"])):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password.",
        )

    user_id = int(user["id"])
    set_auth_cookies(response, user_id, str(user["username"]))
    return AuthResponse(
        user=_user_payload(user_id),
        message="Login successful.",
    )


@router.post("/logout", response_model=MessageResponse)
def logout(response: Response) -> MessageResponse:
    clear_auth_cookies(response)
    return MessageResponse(message="Logout successful.")


@router.post("/password/reset/request", response_model=MessageResponse)
def request_password_reset(payload: PasswordResetRequest) -> MessageResponse:
    email = payload.email.strip()
    user = get_user_by_email(email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Email is not registered.",
        )

    code = "".join(random.choices(string.digits, k=6))
    expires_at = (datetime.now(timezone.utc) + timedelta(minutes=10)).isoformat()
    create_reset_token(email, code, expires_at)
    ok, error_message = send_reset_code(email, code)
    if not ok:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Reset code delivery failed: {error_message}",
        )
    return MessageResponse(message="Reset code sent successfully.")


@router.post("/password/reset/confirm", response_model=MessageResponse)
def confirm_password_reset(payload: PasswordResetConfirmRequest) -> MessageResponse:
    email = payload.email.strip()
    token_row = get_valid_reset_token(email, payload.code.strip())
    if not token_row:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Reset code is invalid or expired.",
        )

    user = get_user_by_email(email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        )

    mark_token_used(int(token_row["id"]))
    update_user_password(int(user["id"]), _hash_password(payload.new_password))
    return MessageResponse(message="Password reset successful.")
