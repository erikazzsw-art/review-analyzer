"""配额服务模块 — 用户配额校验、扣减、退还。

Single Source of Truth 见 QUOTA_TABLE.md。本文件的 PLAN_LIMITS 必须与该表同步。
"""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Any

from review_analyzer.database import get_connection, get_user_plan

PLAN_LIMITS: dict[str, dict[str, Any]] = {
    "review_analyze": {
        "unit": "条",
        "period": "monthly",
        "limits": {"free": 1500, "pro_early": 5000, "pro": 10000, "team": 50000},
        "type": "hard",
    },
    "ask_review": {
        "unit": "次",
        "period": "monthly",
        "limits": {"free": 10, "pro_early": 50, "pro": -1, "team": -1},
        "type": "hard",
    },
    "ad_copy": {
        "unit": "次",
        "period": "monthly",
        "limits": {"free": 10, "pro_early": 100, "pro": 300, "team": -1},
        "type": "hard",
    },
    "excel_export": {
        "unit": "次",
        "period": "monthly",
        "limits": {"free": 10, "pro_early": -1, "pro": -1, "team": -1},
        "type": "soft",
    },
    "compare_products": {
        "unit": "个",
        "period": "concurrent",
        "limits": {"free": 2, "pro_early": -1, "pro": -1, "team": -1},
        "type": "soft",
    },
    "webhook_count": {
        "unit": "个",
        "period": "forever",
        "limits": {"free": 3, "pro_early": -1, "pro": -1, "team": -1},
        "type": "soft",
    },
    "global_rules": {
        "unit": "条",
        "period": "forever",
        "limits": {"free": 3, "pro_early": -1, "pro": -1, "team": -1},
        "type": "soft",
    },
    "product_rules": {
        "unit": "条",
        "period": "forever",
        "limits": {"free": 1, "pro_early": -1, "pro": -1, "team": -1},
        "type": "soft",
        "scope": "per_product",
    },
    "upload_rows_per_file": {
        "unit": "条",
        "period": "per_request",
        "limits": {"free": 500, "pro_early": 5000, "pro": 5000, "team": 5000},
        "type": "hard",
    },
    "asin_fetch": {
        "unit": "次",
        "period": "daily",
        "limits": {"free": 1, "pro_early": 10, "pro": 10, "team": 50},
        "type": "hard",
    },
    "translate": {
        "unit": "次",
        "period": "daily",
        "limits": {"free": 20, "pro_early": 200, "pro": 200, "team": 500},
        "type": "hard",
    },
}

_OVER_QUOTA_MESSAGES: dict[str, str] = {
    "review_analyze": "本月评论分析配额已用完（{used}/{limit} 条），升级 Pro 解锁更多",
    "ask_review": "Ask reviews 本月已用完（{used}/{limit}），升级 Pro 解锁更多",
    "ad_copy": "广告文案本月已用完（{used}/{limit}），升级 Pro 解锁更多",
    "excel_export": "Excel 导出本月已用完（{used}/{limit}），升级 Pro 解锁不限",
    "compare_products": "Free 仅支持同时对比 {limit} 个产品，升级 Pro 解锁不限",
    "webhook_count": "Free 最多 {limit} 个 webhook，升级 Pro 解锁不限",
    "global_rules": "Free 最多 {limit} 条全局规则，升级 Pro 解锁不限",
    "product_rules": "Free 每产品最多 {limit} 条规则，升级 Pro 解锁不限",
    "upload_rows_per_file": "Free 单文件最多 {limit} 条，请拆分上传或升级 Pro",
    "asin_fetch": "今日 ASIN 自动拉取已用完（{used}/{limit} 次），明天再试或升级 Pro",
    "translate": "今日翻译次数已用完（{used}/{limit} 次），明天再试或升级 Pro",
}


def _current_period_start() -> date:
    """当月 1 号（UTC+8）。"""
    now = datetime.now(timezone(timedelta(hours=8)))
    return now.date().replace(day=1)


def _current_day_start() -> date:
    """当日（UTC+8）。"""
    now = datetime.now(timezone(timedelta(hours=8)))
    return now.date()


def _period_start_for(dimension: str) -> date:
    """根据维度的 period 类型返回对应周期起始日。"""
    dim = PLAN_LIMITS.get(dimension)
    if dim and dim["period"] == "daily":
        return _current_day_start()
    return _current_period_start()


def _get_limit(dimension: str, plan: str) -> int:
    """获取某维度对应套餐的限额。-1 表示不限。"""
    dim = PLAN_LIMITS.get(dimension)
    if dim is None:
        return -1
    return dim["limits"].get(plan, dim["limits"].get("free", 0))


def _get_used_count(user_id: int, dimension: str) -> int:
    """从 user_quota_usage 表查当期已用量。"""
    period_start = _period_start_for(dimension)
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT used_count FROM user_quota_usage "
                "WHERE user_id = %s AND dimension = %s AND period_start = %s",
                (user_id, dimension, period_start),
            )
            row = cur.fetchone()
            return int(row[0]) if row else 0
    finally:
        conn.close()


def _format_message(dimension: str, used: int, limit: int) -> str:
    tpl = _OVER_QUOTA_MESSAGES.get(dimension, "配额已用完（{used}/{limit}）")
    return tpl.format(used=used, limit=limit)


def quota_check(user_id: int, dimension: str, amount: int = 1) -> tuple[bool, str]:
    """校验配额是否充足。

    返回 (allowed, message)。allowed=False 时 message 是 UI 展示文案。
    per_request 类型仅做数值比较，不查数据库。
    """
    dim = PLAN_LIMITS.get(dimension)
    if dim is None:
        return True, ""

    plan = get_user_plan(user_id)
    limit = _get_limit(dimension, plan)
    if limit == -1:
        return True, ""

    period = dim["period"]

    if period == "per_request":
        if amount > limit:
            return False, _format_message(dimension, amount, limit)
        return True, ""

    if period in ("monthly", "daily", "forever"):
        used = _get_used_count(user_id, dimension)
        if used + amount > limit:
            return False, _format_message(dimension, used, limit)
        return True, ""

    # concurrent 类型 — 调用方应自行计算当前持有量后传入 amount=current_count
    if period == "concurrent":
        if amount >= limit:
            return False, _format_message(dimension, amount, limit)
        return True, ""

    return True, ""


def quota_check_atomic(user_id: int, dimension: str, amount: int) -> tuple[bool, str]:
    """原子完整校验：amount 必须一次性全部允许，否则整体拒绝。

    专用于 review_analyze 的批量上传场景，避免分析中途中断。
    """
    dim = PLAN_LIMITS.get(dimension)
    if dim is None:
        return True, ""

    plan = get_user_plan(user_id)
    limit = _get_limit(dimension, plan)
    if limit == -1:
        return True, ""

    used = _get_used_count(user_id, dimension)
    remaining = limit - used

    if remaining <= 0:
        return False, _format_message(dimension, used, limit)

    if amount > remaining:
        msg = (
            f"本次需要 {amount} {dim['unit']}，"
            f"但剩余配额仅 {remaining} {dim['unit']}（{used}/{limit}），"
            f"请拆分上传或升级 Pro"
        )
        return False, msg

    return True, ""


def quota_consume(user_id: int, dimension: str, amount: int = 1) -> None:
    """扣减配额。使用 UPSERT 保证并发安全。"""
    if amount <= 0:
        return
    dim = PLAN_LIMITS.get(dimension)
    if dim is None or dim["period"] == "per_request":
        return

    period_start = _period_start_for(dimension)
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO user_quota_usage (user_id, dimension, period_start, used_count, updated_at) "
                "VALUES (%s, %s, %s, %s, NOW()) "
                "ON CONFLICT (user_id, dimension, period_start) "
                "DO UPDATE SET used_count = user_quota_usage.used_count + %s, "
                "updated_at = NOW()",
                (user_id, dimension, period_start, amount, amount),
            )
        conn.commit()
    finally:
        conn.close()


def quota_refund(user_id: int, dimension: str, amount: int = 1) -> None:
    """退还已扣配额（LLM 调用失败时使用）。used_count 最低降到 0。"""
    dim = PLAN_LIMITS.get(dimension)
    if dim is None or dim["period"] == "per_request":
        return

    period_start = _period_start_for(dimension)
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE user_quota_usage "
                "SET used_count = GREATEST(used_count - %s, 0), updated_at = NOW() "
                "WHERE user_id = %s AND dimension = %s AND period_start = %s",
                (amount, user_id, dimension, period_start),
            )
        conn.commit()
    finally:
        conn.close()


def get_credit_ledger(user_id: int, limit: int = 30) -> list[dict[str, Any]]:
    """返回用户最近 N 条 credit 流水，供 UI 展示。"""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, delta, reason, ref_id, balance_after, created_at "
                "FROM credit_ledger WHERE user_id = %s "
                "ORDER BY created_at DESC LIMIT %s",
                (user_id, limit),
            )
            rows = cur.fetchall()
    finally:
        conn.close()

    return [
        {
            "id": row[0],
            "delta": int(row[1]),
            "reason": row[2],
            "ref_id": row[3],
            "balance_after": int(row[4]),
            "created_at": row[5].isoformat() if row[5] else None,
        }
        for row in rows
    ]
    """获取用户某维度的配额状态，供 API / UI 展示。"""
    dim = PLAN_LIMITS.get(dimension)
    if dim is None:
        return {"dimension": dimension, "error": "unknown_dimension"}

    plan = get_user_plan(user_id)
    limit = _get_limit(dimension, plan)
    period = dim["period"]

    if period == "per_request":
        return {
            "dimension": dimension,
            "limit": limit,
            "period": period,
            "plan": plan,
        }

    used = _get_used_count(user_id, dimension) if period in ("monthly", "daily", "forever") else 0

    return {
        "dimension": dimension,
        "used": used,
        "limit": limit,
        "remaining": max(limit - used, 0) if limit != -1 else -1,
        "unlimited": limit == -1,
        "period": period,
        "plan": plan,
        "unit": dim["unit"],
    }


def get_all_quota_status(user_id: int) -> list[dict[str, Any]]:
    """获取用户所有维度的配额状态。"""
    return [get_quota_status(user_id, dim) for dim in PLAN_LIMITS]


# ============================================================
# Credit 体系（V4-出海-M6）
# ============================================================

class InsufficientCreditsError(Exception):
    def __init__(self, needed: int, balance: int) -> None:
        self.needed = needed
        self.balance = balance
        super().__init__(f"Not enough credits: {needed} needed, {balance} left")


def credit_check(user_id: int, amount: int) -> tuple[bool, str]:
    """校验 credit 余额是否足够（只读，不加锁）。"""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT balance FROM user_credits WHERE user_id = %s",
                (user_id,),
            )
            row = cur.fetchone()
            balance = int(row[0]) if row else 0
    finally:
        conn.close()

    if balance < amount:
        return False, f"Not enough credits: {amount} needed, {balance} left"
    return True, ""


def credit_consume(
    user_id: int, amount: int, reason: str, ref_id: str | None = None
) -> int:
    """原子扣减 credit，返回扣后余额。余额不足抛 InsufficientCreditsError。

    SELECT FOR UPDATE 防并发超扣；扣减与写流水在同一事务。
    """
    if amount <= 0:
        raise ValueError(f"credit_consume: amount must be positive, got {amount}")

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT balance FROM user_credits WHERE user_id = %s FOR UPDATE",
                (user_id,),
            )
            row = cur.fetchone()
            balance = int(row[0]) if row else 0

            if balance < amount:
                raise InsufficientCreditsError(amount, balance)

            new_balance = balance - amount
            cur.execute(
                "UPDATE user_credits SET balance = %s, updated_at = NOW() WHERE user_id = %s",
                (new_balance, user_id),
            )
            cur.execute(
                "INSERT INTO credit_ledger (user_id, delta, reason, ref_id, balance_after) "
                "VALUES (%s, %s, %s, %s, %s)",
                (user_id, -amount, reason, ref_id, new_balance),
            )
        conn.commit()
        return new_balance
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def credit_refund(
    user_id: int, amount: int, reason: str = "refund", ref_id: str | None = None
) -> None:
    """反向记账：退回已扣 credit（LLM 熔断失败时调用）。"""
    if amount <= 0:
        return

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE user_credits SET balance = balance + %s, updated_at = NOW() "
                "WHERE user_id = %s RETURNING balance",
                (amount, user_id),
            )
            row = cur.fetchone()
            new_balance = int(row[0]) if row else amount
            cur.execute(
                "INSERT INTO credit_ledger (user_id, delta, reason, ref_id, balance_after) "
                "VALUES (%s, %s, %s, %s, %s)",
                (user_id, amount, reason, ref_id, new_balance),
            )
        conn.commit()
    finally:
        conn.close()


def get_credit_balance(user_id: int) -> dict[str, Any]:
    """返回用户 credit 余额 + trial 状态，供 UI / API 展示。"""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT balance, monthly_grant, trial_expires_at "
                "FROM user_credits WHERE user_id = %s",
                (user_id,),
            )
            row = cur.fetchone()
    finally:
        conn.close()

    if row is None:
        return {
            "balance": 0,
            "monthly_grant": 300,
            "trial_expires_at": None,
            "days_left": None,
            "is_trial": False,
        }

    balance, monthly_grant, trial_expires_at = row[0], row[1], row[2]
    days_left: int | None = None
    is_trial = False
    if trial_expires_at is not None:
        now = datetime.now(timezone.utc)
        if trial_expires_at.tzinfo is None:
            trial_expires_at = trial_expires_at.replace(tzinfo=timezone.utc)
        delta = trial_expires_at - now
        if delta.total_seconds() > 0:
            days_left = delta.days
            is_trial = True

    return {
        "balance": int(balance),
        "monthly_grant": int(monthly_grant),
        "trial_expires_at": trial_expires_at.isoformat() if trial_expires_at else None,
        "days_left": days_left,
        "is_trial": is_trial,
    }
