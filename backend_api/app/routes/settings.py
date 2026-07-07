from __future__ import annotations

import json
import os
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status

from backend_api.app.deps import get_current_user
from backend_api.app.schemas.settings import (
    BillingCheckoutPayload,
    BillingCheckoutResponse,
    BillingWebhookResponse,
    ProductRulePayload,
    PushRulePayload,
    SettingsPayload,
    SettingsUpdatePayload,
    SmartPushSettingsPayload,
    SmartPushSettingsResponse,
)
from review_analyzer.auth import load_user_api_key, save_user_api_key
from review_analyzer.database import (
    get_setting,
    get_user_plan,
    set_setting,
    update_user_credits_monthly_grant,
    update_user_plan,
)
from review_analyzer.notifier import _test_webhook
from review_analyzer.paddle_billing import get_checkout_html, is_billing_configured
from review_analyzer.quota import credit_refund, get_all_quota_status

router = APIRouter(tags=["settings"])

_VALID_WEBHOOK_PLATFORMS = ("feishu", "dingtalk", "wechat")

DEFAULT_PUSH_SETTINGS = {
    "webhook_platform": "feishu",
    "webhook_url": "",
    "webhook_secret": "",
    "webhook_group_name": "",
    "rules": PushRulePayload().model_dump(),
    "product_rules": [],
}


def _clean_platform(value: Any) -> str:
    v = str(value or "feishu").strip().lower()
    return v if v in _VALID_WEBHOOK_PLATFORMS else "feishu"


def _normalize_push_settings(raw: dict[str, Any] | None) -> dict[str, Any]:
    payload = dict(DEFAULT_PUSH_SETTINGS)
    if raw:
        payload.update(
            {
                "webhook_platform": _clean_platform(raw.get("webhook_platform")),
                "webhook_url": str(raw.get("webhook_url") or ""),
                "webhook_secret": str(raw.get("webhook_secret") or ""),
                "webhook_group_name": str(raw.get("webhook_group_name") or ""),
                "rules": {
                    **DEFAULT_PUSH_SETTINGS["rules"],
                    **dict(raw.get("rules") or {}),
                },
                "product_rules": list(raw.get("product_rules") or []),
            }
        )
    return payload


def _load_settings(user_id: int) -> dict[str, Any]:
    raw_push = get_setting(user_id, "push_settings")
    push_settings: dict[str, Any] = {}
    if raw_push:
        try:
            push_settings = json.loads(raw_push)
        except json.JSONDecodeError:
            push_settings = {}

    return {
        **_normalize_push_settings(push_settings),
        "api_key": _load_api_key(user_id),
        "billing": {
            "plan": get_setting(user_id, "billing_plan") or "",
            "configured": is_billing_configured(),
        },
    }


def _load_api_key(user_id: int) -> str:
    user_key = load_user_api_key(user_id)
    if user_key:
        return user_key
    return str(get_setting(user_id, "api_key") or "")


def _verify_paddle_signature(raw_body: bytes, signature: str, secret: str) -> bool:
    if not signature or not secret:
        return False

    parts: dict[str, str] = {}
    for part in signature.split(";"):
        key, _, value = part.partition("=")
        parts[key.strip()] = value.strip()

    timestamp = parts.get("ts", "")
    h1 = parts.get("h1", "")
    if not timestamp or not h1:
        return False

    import hashlib
    import hmac

    signed_payload = f"{timestamp}:{raw_body.decode('utf-8')}"
    expected = hmac.new(secret.encode("utf-8"), signed_payload.encode("utf-8"), hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, h1)


@router.get("/settings", response_model=SettingsPayload)
def get_settings_route(current_user: dict = Depends(get_current_user)) -> SettingsPayload:
    user_id = int(current_user["id"])
    payload = _load_settings(user_id)
    return SettingsPayload(
        webhook_platform=_clean_platform(payload.get("webhook_platform")),
        webhook_url=str(payload.get("webhook_url") or ""),
        webhook_secret=str(payload.get("webhook_secret") or ""),
        webhook_group_name=str(payload.get("webhook_group_name") or ""),
        api_key=str(payload.get("api_key") or ""),
        rules=PushRulePayload(**dict(payload.get("rules") or {})),
        product_rules=[ProductRulePayload(**dict(item)) for item in payload.get("product_rules", [])],
        billing=dict(payload.get("billing") or {}),
        generated_at=datetime.utcnow(),
    )


@router.patch("/settings", response_model=SettingsPayload)
def patch_settings_route(
    payload: SettingsUpdatePayload,
    current_user: dict = Depends(get_current_user),
) -> SettingsPayload:
    user_id = int(current_user["id"])
    # 保留 push_settings 里的其他字段（periodic_push / dept_contacts / escalation_rules / dept_mapping）
    raw_existing = get_setting(user_id, "push_settings")
    existing: dict[str, Any] = {}
    if raw_existing:
        try:
            existing = json.loads(raw_existing)
        except json.JSONDecodeError:
            existing = {}

    existing.update({
        "webhook_platform": _clean_platform(payload.webhook_platform),
        "webhook_url": payload.webhook_url.strip(),
        "webhook_secret": payload.webhook_secret.strip(),
        "webhook_group_name": payload.webhook_group_name.strip(),
        "rules": payload.rules.model_dump(),
        "product_rules": [item.model_dump() for item in payload.product_rules],
    })
    set_setting(user_id, "push_settings", json.dumps(existing, ensure_ascii=False))

    api_key = payload.api_key.strip()
    if api_key:
        save_user_api_key(user_id, api_key)
    else:
        set_setting(user_id, "api_key", "")

    return get_settings_route(current_user=current_user)


@router.post("/settings/test-webhook", response_model=dict[str, Any])
def test_webhook_route(
    payload: dict[str, Any],
    current_user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    webhook_url = str(payload.get("webhook_url") or "").strip()
    secret = str(payload.get("webhook_secret") or "").strip()
    platform = _clean_platform(payload.get("webhook_platform"))
    if not webhook_url:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Webhook URL is required.")
    return _test_webhook(webhook_url, platform, secret)


@router.get("/billing")
def get_billing_status(current_user: dict = Depends(get_current_user)) -> dict[str, Any]:
    """用户计费状态：当前套餐 + 各维度用量 + 是否可升级。"""
    user_id = int(current_user["id"])
    plan = get_user_plan(user_id)
    quota_status = get_all_quota_status(user_id)
    return {
        "user_id": user_id,
        "plan": plan,
        "is_pro": plan in ("pro_early", "pro", "team"),
        "quota": quota_status,
        "upgrade_available": plan == "free",
        "billing_configured": is_billing_configured(),
    }


@router.post("/billing/checkout", response_model=BillingCheckoutResponse)
def create_billing_checkout(
    payload: BillingCheckoutPayload,
    current_user: dict = Depends(get_current_user),
) -> BillingCheckoutResponse:
    user_id = int(current_user["id"])
    email = str(current_user.get("email") or "")
    success_url = payload.success_url or f"{os.getenv('FRONTEND_BASE_URL', 'http://localhost:3000')}/settings?billing=success"
    checkout_html = get_checkout_html(user_id, email, success_url)
    return BillingCheckoutResponse(
        checkout_html=checkout_html,
        configured=is_billing_configured(),
        plan="pro",
    )


@router.post("/billing/webhook", response_model=BillingWebhookResponse)
async def billing_webhook_route(request: Request) -> BillingWebhookResponse:
    try:
        raw_body = await request.body()
        body = json.loads(raw_body.decode("utf-8")) if raw_body else {}
    except Exception:
        raw_body = b""
        body = {}

    webhook_secret = str(os.getenv("PADDLE_WEBHOOK_SECRET") or "").strip()
    signature = str(request.headers.get("paddle-signature") or request.headers.get("Paddle-Signature") or "").strip()
    if webhook_secret and not _verify_paddle_signature(raw_body, signature, webhook_secret):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Paddle signature.")

    event_type = str(body.get("event_type") or body.get("eventType") or "")
    custom_data = body.get("data", {}).get("custom_data") or body.get("custom_data") or body.get("customData") or {}
    user_id_raw = custom_data.get("user_id") or body.get("user_id")
    customer_id = str(
        body.get("data", {}).get("customer_id")
        or body.get("customer_id")
        or body.get("customerId")
        or ""
    ) or None

    if user_id_raw is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing user id.")

    user_id = int(user_id_raw)

    if event_type in ("subscription.created", "subscription.activated") or event_type == "subscription.updated":
        plan = _resolve_plan_from_event(body)
        update_user_plan(user_id, plan, customer_id)
        update_user_credits_monthly_grant(user_id, plan)
    elif event_type in ("subscription.canceled", "subscription.paused"):
        update_user_plan(user_id, "free", customer_id)
        update_user_credits_monthly_grant(user_id, "free")
    elif event_type == "subscription.resumed":
        plan = _resolve_plan_from_event(body)
        update_user_plan(user_id, plan, customer_id)
        update_user_credits_monthly_grant(user_id, plan)
    elif event_type == "transaction.completed":
        # Add-on topup: Price custom_data contains {"topup": true, "credits": N}
        price_cd = _get_price_custom_data(body)
        if price_cd.get("topup"):
            topup_amount = int(price_cd.get("credits", 0))
            if topup_amount > 0:
                credit_refund(user_id, topup_amount, reason="topup")

    return BillingWebhookResponse(message=f"Processed {event_type}.")


def _get_price_custom_data(body: dict) -> dict:
    """从 webhook payload 中提取 Price 级别的 custom_data。"""
    items = body.get("data", {}).get("items") or []
    if items:
        return items[0].get("price", {}).get("custom_data") or {}
    return {}


_STARTER_PRICE_IDS: frozenset[str] = frozenset(filter(None, [
    os.getenv("PADDLE_STARTER_PRICE_ID", "pri_01kwxtav7n1vy5vc906v0ywnr"),
    os.getenv("PADDLE_STARTER_YEARLY_PRICE_ID", "pri_01kwxww4gbrptn4npp2n0ca5rc"),
]))
_PRO_PRICE_IDS: frozenset[str] = frozenset(filter(None, [
    os.getenv("PADDLE_PRICE_ID", "pri_01ksse9jag36fddk82x6ndevjs"),
    os.getenv("PADDLE_PRO_YEARLY_PRICE_ID", "pri_01kwxwyctdypajtpn9qh252b5h"),
]))
_TEAM_PRICE_IDS: frozenset[str] = frozenset(filter(None, [
    os.getenv("PADDLE_TEAM_PRICE_ID", "pri_01kwxx2svf6mm08dbpr6x211ct"),
    os.getenv("PADDLE_TEAM_YEARLY_PRICE_ID", "pri_01kwxx3s7fmx9hbwh30jzz2k5e"),
]))


def _resolve_plan_from_event(body: dict) -> str:
    """从 Paddle webhook data 中推断目标 plan。

    优先读 Price 级别 custom_data.plan，其次按 Price ID 匹配。
    """
    price_cd = _get_price_custom_data(body)
    plan_from_cd = str(price_cd.get("plan") or "")
    if plan_from_cd in ("starter", "pro", "team"):
        return plan_from_cd

    data = body.get("data", {})
    items = data.get("items") or []
    price_id = ""
    if items:
        price_id = str(items[0].get("price", {}).get("id") or items[0].get("price_id") or "")

    if price_id in _TEAM_PRICE_IDS:
        return "team"
    if price_id in _PRO_PRICE_IDS:
        return "pro"
    if price_id in _STARTER_PRICE_IDS:
        return "starter"
    return "pro"


# ============================================================
# V5-T3: 智能推送设置 API
# ============================================================

_DEFAULT_SMART_PUSH = {
    "periodic_push": {"enabled": False, "frequency": "weekly", "day_of_week": "monday", "day_of_month": 1, "time": "09:00", "timezone": "Asia/Shanghai"},
    "dept_contacts": {"qa": "", "product": "", "ops": "", "cs": "", "other": ""},
    "escalation_rules": {"consecutive_count": 3, "top_n": 3, "pct_threshold": 10.0},
    "dept_mapping": [],
}


@router.get("/settings/smart-push", response_model=SmartPushSettingsResponse)
def get_smart_push_settings(
    current_user: dict = Depends(get_current_user),
) -> SmartPushSettingsResponse:
    user_id = int(current_user["id"])
    raw = get_setting(user_id, "push_settings")
    settings: dict = {}
    if raw:
        try:
            settings = json.loads(raw)
        except json.JSONDecodeError:
            settings = {}

    from review_analyzer.department_router import DEFAULT_ASPECT_DEPT_MAP

    periodic = {**_DEFAULT_SMART_PUSH["periodic_push"], **(settings.get("periodic_push") or {})}
    contacts = {**_DEFAULT_SMART_PUSH["dept_contacts"], **(settings.get("dept_contacts") or {})}
    rules = {**_DEFAULT_SMART_PUSH["escalation_rules"], **(settings.get("escalation_rules") or {})}

    user_mapping = settings.get("dept_mapping") or []
    if not user_mapping:
        user_mapping = [{"aspect": k, "dept": v} for k, v in DEFAULT_ASPECT_DEPT_MAP.items()]

    return SmartPushSettingsResponse(
        periodic_push=periodic,
        dept_contacts=contacts,
        escalation_rules=rules,
        dept_mapping=user_mapping,
    )


@router.patch("/settings/smart-push", response_model=SmartPushSettingsResponse)
def patch_smart_push_settings(
    payload: SmartPushSettingsPayload,
    current_user: dict = Depends(get_current_user),
) -> SmartPushSettingsResponse:
    user_id = int(current_user["id"])

    raw = get_setting(user_id, "push_settings")
    existing: dict = {}
    if raw:
        try:
            existing = json.loads(raw)
        except json.JSONDecodeError:
            existing = {}

    existing["periodic_push"] = payload.periodic_push.model_dump()
    existing["dept_contacts"] = payload.dept_contacts.model_dump()
    existing["escalation_rules"] = payload.escalation_rules.model_dump()
    existing["dept_mapping"] = [item.model_dump() for item in payload.dept_mapping]

    set_setting(user_id, "push_settings", json.dumps(existing, ensure_ascii=False))

    return get_smart_push_settings(current_user=current_user)
