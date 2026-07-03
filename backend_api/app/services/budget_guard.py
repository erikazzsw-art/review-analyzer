"""预算熔断（P1）— 全局 + 单用户成本 kill switch。

设计：
- 熔断状态存 Redis，key = "budget:global:daily:{YYYY-MM-DD}" 等
- 每次进入 LLM 路径的接口调用 assert_budget(user_id)，超限则抛 HTTP 429
- 熔断触发时同步发飞书告警（去重：每周期只告一次）

阈值来自环境变量（都用元/RMB）：
- BUDGET_DAILY_TOTAL_YUAN         全站每日预算
- BUDGET_MONTHLY_TOTAL_YUAN       全站每月预算
- BUDGET_USER_DAILY_YUAN          单用户每日预算
- BUDGET_USER_MONTHLY_YUAN        单用户每月预算

未设置视为不启用（放行）。
"""
from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import HTTPException, status

from review_analyzer.database import get_connection

logger = logging.getLogger(__name__)

_TZ = timezone(timedelta(hours=8))


def _today_str() -> str:
    return datetime.now(_TZ).strftime("%Y-%m-%d")


def _month_str() -> str:
    return datetime.now(_TZ).strftime("%Y-%m")


def _budget(env_name: str) -> float | None:
    raw = os.getenv(env_name, "").strip()
    if not raw:
        return None
    try:
        value = float(raw)
    except ValueError:
        return None
    return value if value > 0 else None


def _sum_cost(user_id: int | None, since: datetime) -> float:
    """从 llm_usage_log 汇总花费（元）。"""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            if user_id is None:
                cur.execute(
                    "SELECT COALESCE(SUM(cost_yuan), 0) FROM llm_usage_log "
                    "WHERE created_at >= %s",
                    (since,),
                )
            else:
                cur.execute(
                    "SELECT COALESCE(SUM(cost_yuan), 0) FROM llm_usage_log "
                    "WHERE user_id = %s AND created_at >= %s",
                    (user_id, since),
                )
            row = cur.fetchone()
            return float(row[0]) if row and row[0] is not None else 0.0
    finally:
        conn.close()


def _day_start() -> datetime:
    now = datetime.now(_TZ)
    return now.replace(hour=0, minute=0, second=0, microsecond=0)


def _month_start() -> datetime:
    now = datetime.now(_TZ)
    return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


def get_budget_status() -> dict[str, Any]:
    """当前全站预算使用情况（供管理员看板）。"""
    daily_cap = _budget("BUDGET_DAILY_TOTAL_YUAN")
    monthly_cap = _budget("BUDGET_MONTHLY_TOTAL_YUAN")

    daily_used = _sum_cost(None, _day_start())
    monthly_used = _sum_cost(None, _month_start())

    return {
        "daily": {
            "used_yuan": round(daily_used, 4),
            "cap_yuan": daily_cap,
            "remaining_yuan": round(daily_cap - daily_used, 4) if daily_cap else None,
            "tripped": daily_cap is not None and daily_used >= daily_cap,
        },
        "monthly": {
            "used_yuan": round(monthly_used, 4),
            "cap_yuan": monthly_cap,
            "remaining_yuan": round(monthly_cap - monthly_used, 4) if monthly_cap else None,
            "tripped": monthly_cap is not None and monthly_used >= monthly_cap,
        },
    }


def get_user_budget_status(user_id: int) -> dict[str, Any]:
    daily_cap = _budget("BUDGET_USER_DAILY_YUAN")
    monthly_cap = _budget("BUDGET_USER_MONTHLY_YUAN")

    daily_used = _sum_cost(user_id, _day_start())
    monthly_used = _sum_cost(user_id, _month_start())

    return {
        "user_id": user_id,
        "daily": {
            "used_yuan": round(daily_used, 4),
            "cap_yuan": daily_cap,
            "tripped": daily_cap is not None and daily_used >= daily_cap,
        },
        "monthly": {
            "used_yuan": round(monthly_used, 4),
            "cap_yuan": monthly_cap,
            "tripped": monthly_cap is not None and monthly_used >= monthly_cap,
        },
    }


def _alert_key(scope: str, period: str) -> str:
    if period == "daily":
        return f"budget_alert:{scope}:daily:{_today_str()}"
    return f"budget_alert:{scope}:monthly:{_month_str()}"


def _should_alert(key: str) -> bool:
    """飞书告警去重：同一 key 每周期只发一次（Redis）。"""
    try:
        from workers.queue import get_redis_connection
    except ImportError:
        return True
    try:
        redis_conn = get_redis_connection()
        # NX + EX 30 天，覆盖月度周期
        return bool(redis_conn.set(key, "1", nx=True, ex=30 * 86400))
    except Exception:
        logger.exception("_should_alert: redis check failed, allowing alert")
        return True


def _send_ops_alert(text: str) -> None:
    """运维告警推送。走 send_text_notification 三平台分发。

    环境变量：
    - FEISHU_OPS_WEBHOOK: 运维推送 URL（历史变量名，语义已升级为通用运维 webhook）
    - OPS_WEBHOOK_PLATFORM: feishu (默认) / dingtalk / wechat
    - OPS_WEBHOOK_SECRET: 可选签名密钥（飞书/钉钉支持）
    """
    webhook = os.getenv("FEISHU_OPS_WEBHOOK", "").strip()
    if not webhook:
        logger.warning("budget_guard: FEISHU_OPS_WEBHOOK not set, skipping alert")
        return
    platform = os.getenv("OPS_WEBHOOK_PLATFORM", "feishu").strip().lower() or "feishu"
    secret = os.getenv("OPS_WEBHOOK_SECRET", "").strip()
    try:
        from review_analyzer.notifier import send_text_notification

        send_text_notification(platform, webhook, text, secret)
    except Exception:
        logger.exception("budget_guard: ops alert failed")


def assert_budget(user_id: int) -> None:
    """在 LLM 调用前调用；触发熔断则抛 429。"""
    global_status = get_budget_status()

    if global_status["daily"]["tripped"]:
        if _should_alert(_alert_key("global", "daily")):
            _send_ops_alert(
                f"🛑 全站每日预算触顶\n"
                f"今日已花费 ¥{global_status['daily']['used_yuan']} "
                f"/ 阈值 ¥{global_status['daily']['cap_yuan']}\n"
                f"所有 LLM 调用已暂停至次日 0 点（UTC+8）"
            )
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="系统繁忙，请稍后再试",
        )

    if global_status["monthly"]["tripped"]:
        if _should_alert(_alert_key("global", "monthly")):
            _send_ops_alert(
                f"🛑 全站本月预算触顶\n"
                f"本月已花费 ¥{global_status['monthly']['used_yuan']} "
                f"/ 阈值 ¥{global_status['monthly']['cap_yuan']}\n"
                f"所有 LLM 调用已暂停至下月 1 日（UTC+8）"
            )
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="系统繁忙，请稍后再试",
        )

    user_status = get_user_budget_status(user_id)

    if user_status["daily"]["tripped"]:
        if _should_alert(_alert_key(f"user_{user_id}", "daily")):
            _send_ops_alert(
                f"⚠️ 用户 {user_id} 今日预算触顶\n"
                f"已花费 ¥{user_status['daily']['used_yuan']} "
                f"/ 阈值 ¥{user_status['daily']['cap_yuan']}"
            )
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="您今日的 AI 使用额度已达上限，请明日再试",
        )

    if user_status["monthly"]["tripped"]:
        if _should_alert(_alert_key(f"user_{user_id}", "monthly")):
            _send_ops_alert(
                f"⚠️ 用户 {user_id} 本月预算触顶\n"
                f"已花费 ¥{user_status['monthly']['used_yuan']} "
                f"/ 阈值 ¥{user_status['monthly']['cap_yuan']}"
            )
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="您本月的 AI 使用额度已达上限，请升级 Pro 或下月再试",
        )
