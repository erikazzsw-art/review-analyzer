"""Mailer — Transactional 与 Marketing 双通道，中英双语模板。

设计原则:
- Transactional 邮件走 `noreply@clueai-reviewlens.com`(reset_code / verification /
  subscription_* / deletion),用户不可退订。
- Marketing 邮件走 `updates@clueai-reviewlens.com`(需 Erika 在 Resend 后台加发件人
  验证),发送前校验 `users.marketing_opt_in=TRUE`,并追加双语 unsubscribe footer。
  ⚠️ marketing_opt_in 字段依赖 migration 041(M2.5),041 上线前 send_marketing_email
  会因字段不存在报错并 fail-close(视作未 opt-in)。
- 模板集中在 `review_analyzer/email_templates/{zh-CN,en-US}/*.html`,使用 str.format
  简单占位符,无 Jinja 依赖。
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import os
from pathlib import Path
from typing import Any, Literal

import resend
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

logger = logging.getLogger(__name__)

Locale = Literal["zh-CN", "en-US"]

TEMPLATES_DIR = Path(__file__).parent / "email_templates"
SUPPORTED_LOCALES: tuple[Locale, ...] = ("zh-CN", "en-US")
DEFAULT_LOCALE: Locale = "en-US"

FROM_TRANSACTIONAL = "ClueAI <noreply@clueai-reviewlens.com>"
FROM_MARKETING = "ClueAI <updates@clueai-reviewlens.com>"

# 各语言的邮件标题(不写进模板 HTML 里,避免 <title> vs subject 双份维护)。
_SUBJECTS: dict[str, dict[Locale, str]] = {
    "reset_code": {
        "zh-CN": "ClueAI 密码重置验证码",
        "en-US": "Your ClueAI password reset code",
    },
    "verification": {
        "zh-CN": "ClueAI 邮箱变更通知",
        "en-US": "ClueAI email change notification",
    },
    "subscription_confirmed": {
        "zh-CN": "ClueAI 订阅已生效",
        "en-US": "Your ClueAI subscription is active",
    },
    "subscription_expiring": {
        "zh-CN": "ClueAI 订阅即将到期",
        "en-US": "Your ClueAI subscription is expiring soon",
    },
    "deletion_confirmed": {
        "zh-CN": "ClueAI 账号删除确认",
        "en-US": "Your ClueAI account has been deleted",
    },
    "inactivity_warning": {
        "zh-CN": "[ClueAI] 您的账号即将因长期未使用被清理",
        "en-US": "[ClueAI] Your inactive account will be deleted in 90 days",
    },
}

# 双语退订 footer,附加到所有 marketing 邮件末尾。
_UNSUBSCRIBE_FOOTER: dict[Locale, str] = {
    "zh-CN": (
        '<hr style="border:none;border-top:1px solid #e5e7eb;margin:24px 0;">'
        '<p style="color:#6b7280;font-size:12px;">'
        "你收到这封邮件是因为你在 ClueAI 订阅了产品更新。"
        '<a href="{unsubscribe_url}" style="color:#6b7280;">点此退订</a>。'
        "</p>"
    ),
    "en-US": (
        '<hr style="border:none;border-top:1px solid #e5e7eb;margin:24px 0;">'
        '<p style="color:#6b7280;font-size:12px;">'
        "You are receiving this email because you subscribed to ClueAI product updates. "
        '<a href="{unsubscribe_url}" style="color:#6b7280;">Unsubscribe</a>.'
        "</p>"
    ),
}


def _normalize_locale(locale: str | None) -> Locale:
    """把用户传入的 locale 归一化到 SUPPORTED_LOCALES 之一。

    容错:
    - 前端 next-intl 的 `zh` / `en` → `zh-CN` / `en-US`
    - `zh-hans`、`en-gb` 等大小写/变体 → 主语言匹配
    - 空 / 未支持 → DEFAULT_LOCALE (en-US)
    """
    if not locale:
        return DEFAULT_LOCALE
    normalized = locale.strip().lower().replace("_", "-")
    if normalized in {"zh-cn", "zh", "zh-hans", "zh-sg", "zh-hk", "zh-tw"}:
        return "zh-CN"
    if normalized.startswith("en"):
        return "en-US"
    return DEFAULT_LOCALE


def _render_template(name: str, locale: Locale, **context: Any) -> str:
    """读取 templates/{locale}/{name}.html 并做 str.format 替换。

    用 str.format 而非 Jinja 是有意的:模板只有单层占位符,没有循环/条件,
    引入 Jinja 反而增加依赖面。占位符缺失时抛 KeyError,便于测试时立刻暴露。
    """
    template_path = TEMPLATES_DIR / locale / f"{name}.html"
    template = template_path.read_text(encoding="utf-8")
    return template.format(**context)


def _resend_send(*, from_addr: str, to_email: str, subject: str, html: str) -> tuple[bool, str]:
    """薄封装:统一 API key 缺失时的返回值和异常处理。"""
    api_key = os.environ.get("RESEND_API_KEY", "")
    if not api_key:
        return False, "RESEND_API_KEY not configured"
    resend.api_key = api_key
    try:
        resend.Emails.send({
            "from": from_addr,
            "to": [to_email],
            "subject": subject,
            "html": html,
        })
        return True, ""
    except Exception as exc:
        logger.exception("Resend send failed to=%s subject=%r", to_email, subject)
        return False, str(exc)


# ---------------------------------------------------------------------------
# Transactional 邮件
# ---------------------------------------------------------------------------


def send_reset_code(
    to_email: str,
    code: str,
    locale: str | None = "zh-CN",
) -> tuple[bool, str]:
    """密码重置验证码。locale 默认 zh-CN 保持向后兼容。"""
    lc = _normalize_locale(locale)
    html = _render_template("reset_code", lc, code=code)
    return _resend_send(
        from_addr=FROM_TRANSACTIONAL,
        to_email=to_email,
        subject=_SUBJECTS["reset_code"][lc],
        html=html,
    )


def send_verification_email(
    to_email: str,
    code: str,
    new_email: str,
    locale: str | None = None,
) -> tuple[bool, str]:
    """邮箱变更验证码。当前定位为"变更通知 + 二次验证 code 承载"(实际
    verification flow 尚未挂接到 PATCH /me,先落地邮件通道)。"""
    lc = _normalize_locale(locale)
    html = _render_template("verification", lc, code=code, new_email=new_email)
    return _resend_send(
        from_addr=FROM_TRANSACTIONAL,
        to_email=to_email,
        subject=_SUBJECTS["verification"][lc],
        html=html,
    )


def send_subscription_confirmed(
    to_email: str,
    username: str,
    plan_name: str,
    next_billing_date: str,
    locale: str | None = None,
) -> tuple[bool, str]:
    """订阅生效通知,由 Paddle webhook 触发。"""
    lc = _normalize_locale(locale)
    html = _render_template(
        "subscription_confirmed",
        lc,
        username=username,
        plan_name=plan_name,
        next_billing_date=next_billing_date,
    )
    return _resend_send(
        from_addr=FROM_TRANSACTIONAL,
        to_email=to_email,
        subject=_SUBJECTS["subscription_confirmed"][lc],
        html=html,
    )


def send_subscription_expiring(
    to_email: str,
    username: str,
    plan_name: str,
    expires_at: str,
    days_left: int,
    locale: str | None = None,
) -> tuple[bool, str]:
    """订阅即将到期提醒,由定时任务触发。"""
    lc = _normalize_locale(locale)
    html = _render_template(
        "subscription_expiring",
        lc,
        username=username,
        plan_name=plan_name,
        expires_at=expires_at,
        days_left=days_left,
    )
    return _resend_send(
        from_addr=FROM_TRANSACTIONAL,
        to_email=to_email,
        subject=_SUBJECTS["subscription_expiring"][lc],
        html=html,
    )


def send_deletion_confirmed(
    to_email: str,
    deleted_at: str,
    locale: str | None = None,
) -> tuple[bool, str]:
    """DELETE /me 之后的匿名化确认邮件。"""
    lc = _normalize_locale(locale)
    html = _render_template("deletion_confirmed", lc, deleted_at=deleted_at)
    return _resend_send(
        from_addr=FROM_TRANSACTIONAL,
        to_email=to_email,
        subject=_SUBJECTS["deletion_confirmed"][lc],
        html=html,
    )


def send_inactivity_warning(
    to_email: str,
    username: str,
    deletion_date: str,
    locale: str | None = None,
) -> tuple[bool, str]:
    """M3.5: 6 个月未登录用户的清理预告邮件。

    Transactional 而非 Marketing —— 这是合规通知,不受 opt-out 控制,即使用户
    退订 marketing 邮件也必须收到。发出 90 天后再没登录才触发匿名化。
    """
    lc = _normalize_locale(locale)
    html = _render_template(
        "inactivity_warning",
        lc,
        username=username,
        deletion_date=deletion_date,
    )
    return _resend_send(
        from_addr=FROM_TRANSACTIONAL,
        to_email=to_email,
        subject=_SUBJECTS["inactivity_warning"][lc],
        html=html,
    )


# ---------------------------------------------------------------------------
# Marketing 邮件
# ---------------------------------------------------------------------------


UNSUBSCRIBE_BASE_URL = os.environ.get(
    "UNSUBSCRIBE_BASE_URL",
    "https://api.clueai-reviewlens.com/api/unsubscribe",
)


def generate_unsubscribe_token(user_id: int) -> str:
    """HMAC-SHA256(user_id) 截取前 16 hex 字符做退订 token。

    密钥复用 API_SESSION_SECRET(会话签名同一把密钥),避免为退订单独维护一份。
    截取 16 字符 → 64bit 熵,对"猜测 user_id"场景足够,同时缩短 URL。
    """
    secret = os.environ.get("API_SESSION_SECRET", "")
    if not secret:
        raise RuntimeError("API_SESSION_SECRET not configured, cannot sign unsubscribe token")
    digest = hmac.new(secret.encode("utf-8"), str(user_id).encode("utf-8"), hashlib.sha256)
    return digest.hexdigest()[:16]


def verify_unsubscribe_token(user_id: int, token: str) -> bool:
    """常数时间比对,避免 timing attack 泄露 user_id 是否命中。"""
    try:
        expected = generate_unsubscribe_token(user_id)
    except RuntimeError:
        return False
    return hmac.compare_digest(expected, token)


def build_unsubscribe_url(user_id: int) -> str:
    token = generate_unsubscribe_token(user_id)
    return f"{UNSUBSCRIBE_BASE_URL}?uid={user_id}&token={token}"


def _check_marketing_opt_in(user_id: int) -> bool:
    """查询 users.marketing_opt_in。

    ⚠️ 该字段依赖 migration 041(M2.5,尚未上线)。041 前会捕获 UndefinedColumn
    并返回 False —— fail-close 原则:字段缺失时不发 marketing 邮件,不误发。
    """
    try:
        from review_analyzer.database import get_connection  # 延迟导入,防止 mailer 顶层依赖 DB
    except Exception:
        logger.warning("marketing opt-in check: database module unavailable")
        return False
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT marketing_opt_in FROM users WHERE id = %s", (user_id,))
            row = cur.fetchone()
            return bool(row and row[0])
    except Exception as exc:  # noqa: BLE001 — 字段/表缺失都归为"未 opt-in"
        logger.warning("marketing opt-in check failed for user=%s: %s", user_id, exc)
        return False
    finally:
        conn.close()


def send_marketing_email(
    to_email: str,
    subject: str,
    html: str,
    locale: str | None,
    user_id: int,
) -> tuple[bool, str]:
    """Marketing 邮件统一入口。

    与 transactional 相比多两件事:
    1. 发送前校验 marketing_opt_in=TRUE,否则跳过并返回 (False, "opt-out")。
    2. 自动追加双语 unsubscribe footer(带一次性 HMAC token)。
    """
    if not _check_marketing_opt_in(user_id):
        return False, "user has not opted in to marketing emails"

    lc = _normalize_locale(locale)
    unsubscribe_url = build_unsubscribe_url(user_id)
    footer = _UNSUBSCRIBE_FOOTER[lc].format(unsubscribe_url=unsubscribe_url)
    final_html = html + footer

    return _resend_send(
        from_addr=FROM_MARKETING,
        to_email=to_email,
        subject=subject,
        html=final_html,
    )
