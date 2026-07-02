"""管理员成本看板 & 预算状态接口。

所有接口需 is_admin=true。
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import psycopg2.extras
from fastapi import APIRouter, Depends, Query

from backend_api.app.deps import get_admin_user
from backend_api.app.services.budget_guard import get_budget_status
from review_analyzer.database import get_connection

router = APIRouter(prefix="/admin", tags=["admin"])

_TZ = timezone(timedelta(hours=8))


@router.get("/spend-report")
def spend_report(
    days: int = Query(default=1, ge=1, le=90),
    top_n: int = Query(default=10, ge=1, le=100),
    _: dict = Depends(get_admin_user),
) -> dict:
    """全站花费概况 + top 用户排行 + 预算状态。"""
    since = datetime.now(_TZ) - timedelta(days=days)

    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """
                SELECT
                    COALESCE(SUM(cost_yuan), 0) AS total_cost_yuan,
                    COUNT(*) AS total_calls,
                    SUM(CASE WHEN cache_hit THEN 1 ELSE 0 END) AS cache_hits
                FROM llm_usage_log
                WHERE created_at >= %s
                """,
                (since,),
            )
            summary_row = cur.fetchone() or {}

            cur.execute(
                """
                SELECT l.user_id, u.username,
                       COALESCE(SUM(l.cost_yuan), 0) AS cost_yuan,
                       COUNT(*) AS call_count
                FROM llm_usage_log l
                LEFT JOIN users u ON u.id = l.user_id
                WHERE l.created_at >= %s
                GROUP BY l.user_id, u.username
                ORDER BY cost_yuan DESC
                LIMIT %s
                """,
                (since, top_n),
            )
            top_users = [
                {
                    "user_id": r["user_id"],
                    "username": r.get("username") or "",
                    "cost_yuan": round(float(r["cost_yuan"] or 0), 4),
                    "call_count": int(r["call_count"] or 0),
                }
                for r in cur.fetchall()
            ]

            cur.execute(
                """
                SELECT DATE(created_at AT TIME ZONE 'Asia/Shanghai') AS date,
                       COALESCE(SUM(cost_yuan), 0) AS cost_yuan,
                       COUNT(*) AS calls
                FROM llm_usage_log
                WHERE created_at >= %s
                GROUP BY DATE(created_at AT TIME ZONE 'Asia/Shanghai')
                ORDER BY date DESC
                """,
                (since,),
            )
            daily = [
                {
                    "date": str(r["date"]),
                    "cost_yuan": round(float(r["cost_yuan"] or 0), 4),
                    "calls": int(r["calls"] or 0),
                }
                for r in cur.fetchall()
            ]
    finally:
        conn.close()

    return {
        "range_days": days,
        "summary": {
            "total_cost_yuan": round(float(summary_row.get("total_cost_yuan") or 0), 4),
            "total_calls": int(summary_row.get("total_calls") or 0),
            "cache_hits": int(summary_row.get("cache_hits") or 0),
        },
        "top_users": top_users,
        "daily": daily,
        "budget": get_budget_status(),
    }


@router.get("/budget-status")
def budget_status(_: dict = Depends(get_admin_user)) -> dict:
    """当前预算使用情况（快速查询用）。"""
    return get_budget_status()
