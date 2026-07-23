from __future__ import annotations

import logging
import secrets
from datetime import datetime, timezone
from threading import Thread
from typing import Any

import bcrypt
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status

from backend_api.app.deps import clear_auth_cookies, get_current_user
from backend_api.app.schemas.auth import UserPayload
from backend_api.app.schemas.me import (
    MeDeleteRequest,
    MeExportPayload,
    MeExportUser,
    MeMessageResponse,
    MeUpdateRequest,
    OccupationTagUpdateRequest,
)
from backend_api.app.services.analytics import track_event
from review_analyzer.database import (
    anonymize_user,
    collect_user_data_for_export,
    get_connection,
    get_user_by_email,
    get_user_by_id,
    get_user_by_username,
    get_user_plan,
    update_user_occupation_tag,
    update_user_password,
    update_user_profile,
)
from review_analyzer.mailer import send_deletion_confirmed, send_verification_email

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


def _locale_from_request(request: Request) -> str:
    """从 Accept-Language / NEXT_LOCALE cookie 推断用户语言,mailer 会归一化。

    优先级:cookie(用户显式选择) > Accept-Language 首选 > 默认 en-US。
    """
    cookie_locale = request.cookies.get("NEXT_LOCALE")
    if cookie_locale:
        return cookie_locale
    accept = request.headers.get("accept-language", "")
    if accept:
        return accept.split(",")[0].strip()
    return "en-US"


def _user_payload_from_record(user: dict[str, Any], *, is_admin: bool | None = None) -> UserPayload:
    user_id = int(user["id"])
    return UserPayload(
        id=user_id,
        username=str(user.get("username") or ""),
        email=str(user.get("email") or ""),
        plan=get_user_plan(user_id),
        is_admin=_check_admin(user_id) if is_admin is None else is_admin,
        locale=str(user.get("locale") or "") or None,
        terms_accepted_at=_iso_or_none(user.get("terms_accepted_at")),
        terms_version=str(user.get("terms_version") or "") or None,
        occupation_tag=user.get("occupation_tag"),
        occupation_tag_status=str(user.get("occupation_tag_status") or "not_required"),
        occupation_tag_collected_at=_iso_or_none(user.get("occupation_tag_collected_at")),
        occupation_tag_skipped_at=_iso_or_none(user.get("occupation_tag_skipped_at")),
        occupation_tag_updated_at=_iso_or_none(user.get("occupation_tag_updated_at")),
    )


def _fire_and_forget(send_fn, *args, **kwargs) -> None:
    """把邮件发送放到后台线程,失败只记 WARNING,不阻断也不回滚主流程。

    邮件失败不该拖垮 PATCH/DELETE /me 的响应 —— 用户 PII 已经更新/匿名化,
    邮件是"事后通知",可容忍。生产环境后续可换成 RQ enqueue。
    """
    def _run():
        try:
            ok, err = send_fn(*args, **kwargs)
            if not ok:
                logger.warning("mailer %s failed: %s", send_fn.__name__, err)
        except Exception:
            logger.exception("mailer %s crashed", send_fn.__name__)

    Thread(target=_run, daemon=True).start()


@router.get("/me", response_model=UserPayload)
def get_me(current_user: dict = Depends(get_current_user)) -> UserPayload:
    user_id = int(current_user["id"])
    return _user_payload_from_record(current_user, is_admin=_check_admin(user_id))


@router.patch("/me/occupation-tag", response_model=UserPayload)
def update_me_occupation_tag(
    payload: OccupationTagUpdateRequest,
    current_user: dict = Depends(get_current_user),
) -> UserPayload:
    """保存或跳过职业标签采集。

    职业标签只用于用户行为路径观察，不参与权限、页面内容、Action Center 或推送分责。
    """
    user_id = int(current_user["id"])
    source = payload.source.strip() or "onboarding"

    if payload.skip:
        update_user_occupation_tag(user_id, occupation_tag=None, status="skipped")
        track_event(user_id, "occupation_tag_skipped", {"source": source})
    else:
        update_user_occupation_tag(
            user_id,
            occupation_tag=payload.occupation_tag,
            status="completed",
        )
        track_event(
            user_id,
            "occupation_tag_saved",
            {"source": source, "occupation_tag": payload.occupation_tag},
        )

    refreshed = get_user_by_id(user_id) or current_user
    return _user_payload_from_record(refreshed)


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
            occupation_tag=current_user.get("occupation_tag"),
            occupation_tag_status=current_user.get("occupation_tag_status"),
            occupation_tag_collected_at=_iso_or_none(current_user.get("occupation_tag_collected_at")),
            occupation_tag_skipped_at=_iso_or_none(current_user.get("occupation_tag_skipped_at")),
            occupation_tag_updated_at=_iso_or_none(current_user.get("occupation_tag_updated_at")),
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
    request: Request,
    current_user: dict = Depends(get_current_user),
) -> UserPayload:
    """更正权 (Right to Rectification) — 修改用户名 / 邮箱 / 密码。

    任何字段的修改都需要传入当前密码, 防止 cookie 被劫持后直接改邮箱转移账号。
    邮箱直接更新 (不做二次验证 flow), 后续可扩展 verification token 流程。
    改邮箱成功后会向新邮箱发一封变更通知邮件(fire-and-forget,失败不影响响应)。
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

    # 邮箱变更 → 通知新邮箱,让用户知道"发生了一次邮箱变更"。
    # 当前没有 verification flow,code 参数用一个 6 位随机数占位,后续 flow 上线后
    # 替换为真实 token + 存 DB。fire-and-forget,不阻断响应。
    if new_email is not None:
        placeholder_code = "".join(secrets.choice("0123456789") for _ in range(6))
        _fire_and_forget(
            send_verification_email,
            to_email=new_email,
            code=placeholder_code,
            new_email=new_email,
            locale=_locale_from_request(request),
        )

    refreshed = get_user_by_id(user_id) or current_user
    return _user_payload_from_record(refreshed, is_admin=_check_admin(user_id))


@router.delete("/me", response_model=MeMessageResponse)
def delete_me(
    payload: MeDeleteRequest,
    request: Request,
    response: Response,
    current_user: dict = Depends(get_current_user),
) -> MeMessageResponse:
    """遗忘权 (Right to be Forgotten) — GDPR Art. 17 / CCPA §1798.105.

    匿名化用户主表 (PII 清零 + password_hash 置随机 + deleted_at=NOW), 业务数据
    (sessions / comments / products) 保留 user_id 但已无法识别真实身份。有
    paddle_customer_id 时打 WARNING 日志, 提醒 Erika 手动 (未来自动) 到 Paddle
    后台取消订阅避免继续扣款。删除完成后向原邮箱发一封匿名化确认邮件。
    """
    user_id = int(current_user["id"])

    if not _verify_password(payload.current_password, str(current_user["password_hash"])):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Current password is incorrect.",
        )

    # 匿名化前先拿到原邮箱和 locale,因为 anonymize_user 会把 email 置空。
    original_email = str(current_user.get("email") or "")
    locale = _locale_from_request(request)

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

    if original_email:
        _fire_and_forget(
            send_deletion_confirmed,
            to_email=original_email,
            deleted_at=datetime.now(timezone.utc).isoformat(),
            locale=locale,
        )

    return MeMessageResponse(message="Account deletion completed.")
