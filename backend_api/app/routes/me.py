from __future__ import annotations

import logging
import secrets
from datetime import datetime, timezone
from typing import Any

import bcrypt
from fastapi import APIRouter, Depends, HTTPException, Response, status

from backend_api.app.deps import clear_auth_cookies, get_current_user
from backend_api.app.schemas.auth import UserPayload
from backend_api.app.schemas.me import (
    MeDeleteRequest,
    MeExportPayload,
    MeExportUser,
    MeMessageResponse,
    MeUpdateRequest,
)
from review_analyzer.database import (
    anonymize_user,
    collect_user_data_for_export,
    get_connection,
    get_user_by_email,
    get_user_by_id,
    get_user_by_username,
    get_user_plan,
    update_user_password,
    update_user_profile,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["me"])


def _check_admin(user_id: int) -> bool:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT is_admin FROM users WHERE id = %s", (user_id,))
            row = cur.fetchone()
            return bool(row and row[0])
    except Exception:
        return False
    finally:
        conn.close()


def _hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def _verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except (AttributeError, TypeError, ValueError):
        return False


def _iso_or_none(value: Any) -> str | None:
    if value is None:
        return None
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


@router.get("/me", response_model=UserPayload)
def get_me(current_user: dict = Depends(get_current_user)) -> UserPayload:
    user_id = int(current_user["id"])
    is_admin = _check_admin(user_id)
    return UserPayload(
        id=user_id,
        username=str(current_user["username"]),
        email=str(current_user.get("email") or ""),
        plan=get_user_plan(user_id),
        is_admin=is_admin,
    )


@router.get("/me/export", response_model=MeExportPayload)
def export_me(current_user: dict = Depends(get_current_user)) -> MeExportPayload:
    """数据可携权 (Data Portability) — GDPR Art. 20 / CCPA §1798.100.

    返回当前用户的可导出数据快照 (JSON)。评论明细因体量原因只返回计数,
    需要全量原文时走 /downloads 或 /export 端点。
    """
    user_id = int(current_user["id"])
    data = collect_user_data_for_export(user_id)

    return MeExportPayload(
        exported_at=datetime.now(timezone.utc).isoformat(),
        user=MeExportUser(
            id=user_id,
            username=str(current_user.get("username") or ""),
            email=str(current_user.get("email") or ""),
            plan=str(current_user.get("plan") or "free"),
            paddle_customer_id=current_user.get("paddle_customer_id"),
            created_at=_iso_or_none(current_user.get("created_at")),
            updated_at=_iso_or_none(current_user.get("updated_at")),
        ),
        subscription=data.get("subscription"),
        sessions=data.get("sessions", []),
        products=data.get("products", []),
        product_variants=data.get("product_variants", []),
        comments_count=int(data.get("comments_count") or 0),
        actions=data.get("actions", []),
        trackers=data.get("trackers", []),
        settings=data.get("settings", []),
        asin_watchlist=data.get("asin_watchlist", []),
    )


@router.patch("/me", response_model=UserPayload)
def update_me(
    payload: MeUpdateRequest,
    current_user: dict = Depends(get_current_user),
) -> UserPayload:
    """更正权 (Right to Rectification) — 修改用户名 / 邮箱 / 密码。

    任何字段的修改都需要传入当前密码, 防止 cookie 被劫持后直接改邮箱转移账号。
    邮箱直接更新 (不做二次验证 flow), 后续可扩展 verification token 流程。
    """
    user_id = int(current_user["id"])

    # 强制校验当前密码
    if not _verify_password(payload.current_password, str(current_user["password_hash"])):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Current password is incorrect.",
        )

    new_username: str | None = None
    if payload.username is not None:
        candidate = payload.username.strip()
        if candidate != str(current_user.get("username") or ""):
            existing = get_user_by_username(candidate)
            if existing and int(existing["id"]) != user_id:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Username already exists.",
                )
            new_username = candidate

    new_email: str | None = None
    if payload.email is not None:
        candidate = payload.email.strip()
        if candidate != str(current_user.get("email") or ""):
            existing = get_user_by_email(candidate)
            if existing and int(existing["id"]) != user_id:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Email already exists.",
                )
            new_email = candidate

    if new_username is not None or new_email is not None:
        update_user_profile(user_id, username=new_username, email=new_email)

    if payload.new_password is not None:
        update_user_password(user_id, _hash_password(payload.new_password))

    refreshed = get_user_by_id(user_id) or current_user
    return UserPayload(
        id=user_id,
        username=str(refreshed.get("username") or ""),
        email=str(refreshed.get("email") or ""),
        plan=str(refreshed.get("plan") or "free"),
        is_admin=_check_admin(user_id),
    )


@router.delete("/me", response_model=MeMessageResponse)
def delete_me(
    payload: MeDeleteRequest,
    response: Response,
    current_user: dict = Depends(get_current_user),
) -> MeMessageResponse:
    """遗忘权 (Right to be Forgotten) — GDPR Art. 17 / CCPA §1798.105.

    匿名化用户主表 (PII 清零 + password_hash 置随机 + deleted_at=NOW), 业务数据
    (sessions / comments / products) 保留 user_id 但已无法识别真实身份。有
    paddle_customer_id 时打 WARNING 日志, 提醒 Erika 手动 (未来自动) 到 Paddle
    后台取消订阅避免继续扣款。
    """
    user_id = int(current_user["id"])

    if not _verify_password(payload.current_password, str(current_user["password_hash"])):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Current password is incorrect.",
        )

    paddle_customer_id = current_user.get("paddle_customer_id")
    scrambled = _hash_password(secrets.token_urlsafe(32))
    anonymize_user(user_id, scrambled)

    if paddle_customer_id:
        logger.warning(
            "User %s deleted account with active Paddle subscription customer_id=%s "
            "-- manual cancellation required until webhook API is wired",
            user_id,
            paddle_customer_id,
        )

    clear_auth_cookies(response)

    return MeMessageResponse(message="Account deletion completed.")
