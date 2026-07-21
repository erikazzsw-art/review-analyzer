from __future__ import annotations

import random
import string
from datetime import datetime, timedelta, timezone
from typing import Any

import bcrypt
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status

from backend_api.app.deps import clear_auth_cookies, get_current_user, set_auth_cookies
from backend_api.app.schemas.auth import (
    AcceptTermsRequest,
    AuthResponse,
    LoginRequest,
    MessageResponse,
    PasswordResetConfirmRequest,
    PasswordResetRequest,
    RegisterRequest,
    UserPayload,
)
from review_analyzer.database import (
    DatabaseConnectionUnavailable,
    create_reset_token,
    create_user,
    get_connection,
    get_user_by_email,
    get_user_by_id,
    get_user_by_username,
    get_valid_reset_token,
    mark_token_used,
    mark_user_login,
    update_user_password,
)
from review_analyzer.mailer import send_reset_code

router = APIRouter(prefix="/auth", tags=["auth"])


def _hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def _verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except (AttributeError, TypeError, ValueError):
        # 旧账号或脏数据可能写入了非 bcrypt 格式的 hash；这类情况按认证失败处理。
        return False


def _init_trial_credits(user_id: int) -> None:
    """M6: 新用户注册时初始化 trial credits（3000 credits，14天有效期）"""
    conn = get_connection()
    try:
        trial_expires_at = datetime.now(timezone.utc) + timedelta(days=14)
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO user_credits (user_id, balance, monthly_grant, trial_expires_at) "
                "VALUES (%s, %s, %s, %s)",
                (user_id, 3000, 300, trial_expires_at),
            )
            cur.execute(
                "INSERT INTO credit_ledger (user_id, delta, reason, balance_after) "
                "VALUES (%s, %s, %s, %s)",
                (user_id, 3000, "trial", 3000),
            )
        conn.commit()
    finally:
        conn.close()


def _user_payload(user: dict[str, Any]) -> UserPayload:
    user_id = int(user["id"])
    plan = str(user.get("plan") or "free").strip() or "free"
    return UserPayload(
        id=user_id,
        username=str(user["username"]),
        email=str(user.get("email") or ""),
        plan=plan,
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

    # V4-出海-M2.5: 后端二次校验 — age_confirmed 必须为 True
    if not payload.age_confirmed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Age confirmation is required.",
        )

    user_id = create_user(
        username,
        _hash_password(payload.password),
        email,
        terms_version=payload.terms_version,
        age_confirmed=payload.age_confirmed,
        marketing_opt_in=payload.marketing_opt_in,
    )
    _init_trial_credits(user_id)
    user = get_user_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        )
    set_auth_cookies(response, user_id, username)
    return AuthResponse(
        user=_user_payload(user),
        message="Registration successful.",
    )


@router.post("/login", response_model=AuthResponse)
def login(payload: LoginRequest, response: Response) -> AuthResponse:
    username_or_email = payload.username.strip()
    try:
        # 支持邮箱登录：输入含 @ 则先按 email 查，找不到再按 username 查
        user = None
        if "@" in username_or_email:
            user = get_user_by_email(username_or_email)
        if not user:
            user = get_user_by_username(username_or_email)
    except DatabaseConnectionUnavailable as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service unavailable.",
        ) from exc
    if not user or not _verify_password(payload.password, str(user["password_hash"])):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password.",
        )
    # V4-出海-M3.2: 软删账号禁止登录, 即使凭证碰巧对上
    if user.get("deleted_at") is not None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Account has been deleted.",
        )

    user_id = int(user["id"])
    # V4-出海-M3.5: 刷新 last_login_at + 清零 inactivity_notified_at
    # (哪怕 DB 写失败也不阻塞登录,只记 warning。retention_cleanup 会在下次运行时补上)
    try:
        mark_user_login(user_id)
    except Exception:  # noqa: BLE001 — 登录成功路径不能被 last_login_at 记账挡下
        import logging
        logging.getLogger(__name__).warning(
            "mark_user_login failed for user_id=%s (login still successful)", user_id
        )
    set_auth_cookies(response, user_id, str(user["username"]))
    return AuthResponse(
        user=_user_payload(user),
        message="Login successful.",
    )


@router.post("/logout", response_model=MessageResponse)
def logout(response: Response) -> MessageResponse:
    clear_auth_cookies(response)
    return MessageResponse(message="Logout successful.")


@router.post("/password/reset/request", response_model=MessageResponse)
def request_password_reset(
    payload: PasswordResetRequest,
    request: Request,
) -> MessageResponse:
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

    # locale 优先级: 前端显式头 X-Locale > NEXT_LOCALE cookie > Accept-Language > 默认。
    # mailer._normalize_locale 会把 zh/zh-Hans/en/en-GB 等归一到 zh-CN/en-US。
    locale = (
        request.headers.get("x-locale")
        or request.cookies.get("NEXT_LOCALE")
        or (request.headers.get("accept-language", "").split(",")[0].strip() or None)
        or "en-US"
    )
    ok, error_message = send_reset_code(email, code, locale=locale)
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


# V4-出海-M2.5: Terms 版本常量，用于判断老用户是否需要补同意
CURRENT_TERMS_VERSION = "2.0"


@router.post("/accept-terms", response_model=MessageResponse)
def accept_terms(
    payload: AcceptTermsRequest,
    current_user: dict = Depends(get_current_user),
) -> MessageResponse:
    """接受 Terms of Service / Privacy Policy（幂等）。

    老用户登录后如 terms_version 为空/过期，前端弹出 Terms Gate modal，
    用户勾选同意后调用本端点。已接受同版本则直接返回 already_accepted。
    """
    user_id = int(current_user["id"])
    existing_version = current_user.get("terms_version")

    # 幂等：已接受同版本直接返回成功
    if existing_version == payload.terms_version:
        return MessageResponse(
            message="Terms already accepted for this version.",
        )

    from datetime import datetime, timezone

    now = datetime.now(timezone.utc)
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE users SET terms_accepted_at = %s, terms_version = %s WHERE id = %s",
                (now, payload.terms_version, user_id),
            )
        conn.commit()
    finally:
        conn.close()

    return MessageResponse(message="Terms accepted.")
