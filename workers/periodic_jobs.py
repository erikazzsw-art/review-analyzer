"""V5-T3 Step 6: 周期汇总推送 job

由 scheduler 触发入队，执行：
1. 汇总该用户各产品在当前周期内的分析数据
2. 生成推送快照（snapshot_type='periodic'）
3. 运行升级判定
4. 触发升级时调用 LLM 生成行动建议
5. 发送富文本推送到飞书
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta
from typing import Any

from workers.queue import get_queue

logger = logging.getLogger(__name__)


def periodic_digest_job(user_id: int) -> dict[str, Any]:
    """
    周期汇总推送主函数。

    流程：
    1. 读取用户推送设置
    2. 遍历用户的活跃产品
    3. 对每个产品：汇总当期评论 → 生成 TOP issues/highlights → 写快照
    4. 更新升级状态 → 检查升级 → 触发 LLM 建议
    5. 构建富文本消息 → 发送飞书
    """
    from review_analyzer.database import get_comments, get_setting
    from review_analyzer.department_router import route_issues_by_department
    from review_analyzer.escalation import (
        EscalationConfig,
        check_escalations,
        update_escalation_states,
    )
    from review_analyzer.notifier import _get_top_issues, send_rich_push
    from review_analyzer.product_store import get_user_products
    from review_analyzer.push_snapshot_store import create_push_snapshot

    raw_settings = get_setting(user_id, "push_settings")
    if not raw_settings:
        return {"ok": False, "msg": "no push settings"}

    try:
        settings = json.loads(raw_settings)
    except json.JSONDecodeError:
        return {"ok": False, "msg": "invalid push settings"}

    webhook_url = settings.get("webhook_url", "")
    if not webhook_url:
        return {"ok": False, "msg": "no webhook url"}

    platform = settings.get("webhook_platform") or "feishu"

    periodic_config = settings.get("periodic_push", {})
    frequency = periodic_config.get("frequency", "weekly")
    period_days = {"daily": 1, "weekly": 7, "biweekly": 14, "monthly": 30}.get(frequency, 7)

    period_end = datetime.now().date()
    period_start = period_end - timedelta(days=period_days)

    escalation_config_raw = settings.get("escalation_rules", {})
    esc_config = EscalationConfig(
        consecutive_count=escalation_config_raw.get("consecutive_count", 3),
        top_n=escalation_config_raw.get("top_n", 3),
        pct_threshold=escalation_config_raw.get("pct_threshold", 10.0),
    )

    dept_contacts = settings.get("dept_contacts", {})
    user_dept_mapping = settings.get("dept_mapping")

    products = get_user_products(user_id)
    results: list[dict] = []

    for product in products:
        product_id = product.get("id")
        product_name = product.get("name") or product.get("parent_product_id") or "未知产品"

        comments = get_comments(user_id, product_id=product_id)
        period_comments = [
            c for c in comments
            if c.get("created_at") and c["created_at"].date() >= period_start
        ]

        if not period_comments:
            continue

        top_issues = _get_top_issues(period_comments, "negative")
        top_highlights = _get_top_issues(period_comments, "positive")

        for rank, issue in enumerate(top_issues, 1):
            issue["rank"] = rank

        total = len(period_comments)
        neg_count = sum(1 for c in period_comments if c.get("sentiment") == "negative")

        snapshot_id = create_push_snapshot(user_id, {
            "product_id": product_id,
            "snapshot_type": "periodic",
            "period_start": period_start.isoformat(),
            "period_end": period_end.isoformat(),
            "top_issues": top_issues[:10],
            "top_highlights": top_highlights[:5],
            "summary_stats": {
                "total_reviews": total,
                "negative_count": neg_count,
                "neg_rate": neg_count / total * 100 if total > 0 else 0,
            },
        })

        update_escalation_states(
            user_id, product_id, snapshot_id, top_issues[:10], user_dept_mapping
        )

        escalation_results = check_escalations(
            user_id, product_id, top_issues[:10], esc_config
        )

        escalation_actions: list[dict] = []
        if escalation_results:
            from backend_api.app.services.action_advisor import create_escalation_action
            from review_analyzer.push_snapshot_store import (
                get_recent_snapshots,
                mark_escalated,
            )

            for esc in escalation_results:
                recent = get_recent_snapshots(user_id, product_id, limit=esc_config.consecutive_count)
                pct_trend = []
                for snap in reversed(recent):
                    snap_issues = snap.get("top_issues") or []
                    if isinstance(snap_issues, str):
                        snap_issues = json.loads(snap_issues)
                    for si in snap_issues:
                        if si.get("tag") == esc.tag_name:
                            pct_trend.append(float(si.get("pct", 0)))
                            break
                pct_trend.append(esc.current_pct)

                sample_reviews = [
                    c.get("content", "")[:200]
                    for c in period_comments
                    if esc.tag_name in (c.get("issue_tag") or "")
                ][:5]

                action_id = create_escalation_action(
                    user_id=user_id,
                    product_id=product_id,
                    tag_name=esc.tag_name,
                    dept=esc.dept,
                    current_pct=esc.current_pct,
                    consecutive_count=esc.consecutive_count,
                    pct_trend=pct_trend,
                    product_name=product_name,
                    sample_reviews=sample_reviews,
                )

                if action_id:
                    mark_escalated(user_id, product_id, esc.tag_name, action_id)
                    from review_analyzer.aspect_taxonomy import get_aspect_label_zh
                    escalation_actions.append({
                        "tag_name": esc.tag_name,
                        "tag_label": get_aspect_label_zh(esc.tag_name),
                        "suggested_action": "已写入行动中心",
                        "expected_timeline": "",
                    })

        dept_issues = route_issues_by_department(top_issues[:10], user_dept_mapping)

        from review_analyzer.aspect_taxonomy import get_aspect_label_zh
        for dept_list in dept_issues.values():
            for issue in dept_list:
                issue["tag_label"] = get_aspect_label_zh(issue.get("tag", ""))
        for hl in top_highlights[:3]:
            hl["tag_label"] = get_aspect_label_zh(hl.get("tag", ""))

        period_label = f"{period_start.isoformat()} ~ {period_end.isoformat()}"
        secret = settings.get("webhook_secret", "")

        # B6: 获取 TOP 问题复盘进度
        from review_analyzer.notifier import _get_action_progress
        top_tag_names = [i.get("tag", "") for i in top_issues[:5] if i.get("tag")]
        action_progress = _get_action_progress(user_id, product_id, top_tag_names)

        push_result = send_rich_push(
            webhook_url=webhook_url,
            product_name=product_name,
            period_label=period_label,
            dept_issues=dept_issues,
            dept_contacts=dept_contacts,
            escalation_results=escalation_actions or None,
            top_highlights=top_highlights[:3],
            secret=secret,
            action_progress=action_progress or None,
            product_id=product_id,
            platform=platform,
        )

        results.append({
            "product_id": product_id,
            "product_name": product_name,
            "push_ok": push_result.get("ok", False),
            "escalations": len(escalation_results),
        })

    return {"ok": True, "products_pushed": len(results), "details": results}


def enqueue_periodic_digest(user_id: int) -> str:
    """入队周期推送任务"""
    queue = get_queue()
    job = queue.enqueue(
        periodic_digest_job,
        user_id,
        job_id=f"periodic-digest-{user_id}-{datetime.now().strftime('%Y%m%d%H%M')}",
        description=f"Periodic digest push for user {user_id}",
        result_ttl=3600,
        failure_ttl=7 * 24 * 60 * 60,
    )
    return job.id


# ============================================================
# Stale Job Scanner — Worker 挂死检测 + 飞书告警
# ============================================================

STALE_THRESHOLD_MINUTES = 15
MAX_AUTO_RETRY = 2


def scan_stale_jobs() -> dict[str, Any]:
    """扫描卡死任务：status='processing' 超过阈值未更新，自动重试或标记 failed + 告警。

    设计：
    - 每 5 分钟由 scheduler 入队一次
    - 查 upload_jobs WHERE status='processing' AND updated_at < now() - 15min
    - retry_count < MAX_AUTO_RETRY 的 job 重新入队（断点续跑）
    - 超过重试上限的标记为 failed
    - 汇总后发飞书运维告警
    """
    import psycopg2
    import psycopg2.extras

    from review_analyzer.database import get_connection, update_upload_job

    conn = get_connection()
    stale_jobs: list[dict] = []
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """SELECT id, user_id, session_id, status, created_at, updated_at,
                          COALESCE(retry_count, 0) AS retry_count
                   FROM upload_jobs
                   WHERE status = 'processing'
                     AND updated_at < NOW() - INTERVAL '%s minutes'""",
                (STALE_THRESHOLD_MINUTES,),
            )
            stale_jobs = [dict(row) for row in cur.fetchall()]
    finally:
        conn.close()

    if not stale_jobs:
        logger.info("scan_stale_jobs: no stale jobs found")
        return {"ok": True, "stale_count": 0}

    retried_jobs: list[dict] = []
    failed_jobs: list[dict] = []

    for job in stale_jobs:
        retry_count = int(job.get("retry_count") or 0)
        if retry_count < MAX_AUTO_RETRY and job.get("session_id"):
            update_upload_job(
                user_id=job["user_id"],
                job_id=job["id"],
                updates={
                    "status": "queued",
                    "retry_count": retry_count + 1,
                    "error_message": f"Auto-retry #{retry_count + 1}: job stuck >{STALE_THRESHOLD_MINUTES}min",
                },
            )
            try:
                queue = get_queue()
                from workers.jobs import process_upload_job
                queue.enqueue(
                    process_upload_job,
                    job["user_id"],
                    job["id"],
                    job_id=f"retry-{job['id']}-{retry_count + 1}",
                    description=f"Auto-retry upload job {job['id']} (attempt {retry_count + 2})",
                )
                retried_jobs.append(job)
                logger.info(
                    "scan_stale_jobs: re-enqueued job %d (user %d), retry #%d",
                    job["id"], job["user_id"], retry_count + 1,
                )
            except Exception:
                logger.exception("scan_stale_jobs: failed to re-enqueue job %d", job["id"])
                update_upload_job(
                    user_id=job["user_id"],
                    job_id=job["id"],
                    updates={
                        "status": "failed",
                        "error_message": f"Auto-retry enqueue failed after {retry_count + 1} attempts",
                    },
                )
                failed_jobs.append(job)
        else:
            update_upload_job(
                user_id=job["user_id"],
                job_id=job["id"],
                updates={
                    "status": "failed",
                    "error_message": f"Worker timeout: job stuck >{STALE_THRESHOLD_MINUTES}min, retries exhausted ({retry_count}/{MAX_AUTO_RETRY})",
                },
            )
            failed_jobs.append(job)
            logger.warning(
                "scan_stale_jobs: marked job %d (user %d) as failed — stuck since %s, retries exhausted",
                job["id"], job["user_id"], job["updated_at"],
            )

    if failed_jobs:
        _send_stale_alert(failed_jobs)

    return {
        "ok": True,
        "stale_count": len(stale_jobs),
        "retried": len(retried_jobs),
        "failed": len(failed_jobs),
        "job_ids": [j["id"] for j in stale_jobs],
    }


def _send_stale_alert(stale_jobs: list[dict]) -> None:
    """发送运维告警（走三平台分发）"""
    import os

    webhook_url = os.getenv("FEISHU_OPS_WEBHOOK")
    if not webhook_url:
        logger.warning("scan_stale_jobs: FEISHU_OPS_WEBHOOK not set, skipping alert")
        return

    lines = [
        "⚠️ Worker 卡死告警",
        "",
        f"检测到 {len(stale_jobs)} 个任务超过 {STALE_THRESHOLD_MINUTES} 分钟未完成，已自动标记为 failed：",
        "",
    ]
    for job in stale_jobs[:10]:
        lines.append(f"  - job_id={job['id']} user_id={job['user_id']} stuck since {job['updated_at']}")

    if len(stale_jobs) > 10:
        lines.append(f"  ... 共 {len(stale_jobs)} 个")

    lines.append("")
    lines.append("请检查 Worker 进程状态：docker logs clueai-worker")

    platform = os.getenv("OPS_WEBHOOK_PLATFORM", "feishu").strip().lower() or "feishu"
    secret = os.getenv("OPS_WEBHOOK_SECRET", "").strip()

    try:
        from review_analyzer.notifier import send_text_notification

        result = send_text_notification(platform, webhook_url, "\n".join(lines), secret)
        logger.info("scan_stale_jobs: alert sent, ok=%s msg=%s", result.get("ok"), result.get("msg"))
    except Exception as e:
        logger.error("scan_stale_jobs: alert failed: %s", e)


def enqueue_stale_job_scan() -> str:
    """入队卡死任务扫描（由 scheduler 每 5 分钟调用）"""
    queue = get_queue()
    job = queue.enqueue(
        scan_stale_jobs,
        job_id=f"stale-scan-{datetime.now().strftime('%Y%m%d%H%M')}",
        description="Scan for stale processing jobs",
        result_ttl=300,
        failure_ttl=24 * 60 * 60,
    )
    return job.id


# ============================================================
# Daily Cost Digest — 每日成本日报（推送到飞书运维群）
# ============================================================


def daily_cost_digest() -> dict[str, Any]:
    """汇总昨日 LLM 花费、top 用户，推送到运维群（三平台分发）。

    - 每天 UTC+8 09:07 由 scheduler 触发（避开 :00 :30）
    - 数据源：llm_usage_log 表
    - 无数据不推送
    - 环境变量：FEISHU_OPS_WEBHOOK / OPS_WEBHOOK_PLATFORM / OPS_WEBHOOK_SECRET
    """
    import os
    from datetime import timedelta as _td
    from datetime import timezone as _tz

    import psycopg2.extras

    from backend_api.app.services.budget_guard import get_budget_status
    from review_analyzer.database import get_connection
    from review_analyzer.notifier import send_text_notification

    tz = _tz(_td(hours=8))
    now = datetime.now(tz)
    day_start = now.replace(hour=0, minute=0, second=0, microsecond=0) - _td(days=1)
    day_end = day_start + _td(days=1)

    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """
                SELECT COALESCE(SUM(cost_yuan), 0) AS total, COUNT(*) AS calls
                FROM llm_usage_log
                WHERE created_at >= %s AND created_at < %s
                """,
                (day_start, day_end),
            )
            summary = cur.fetchone() or {}

            cur.execute(
                """
                SELECT l.user_id, u.username,
                       COALESCE(SUM(l.cost_yuan), 0) AS cost_yuan,
                       COUNT(*) AS calls
                FROM llm_usage_log l
                LEFT JOIN users u ON u.id = l.user_id
                WHERE l.created_at >= %s AND l.created_at < %s
                GROUP BY l.user_id, u.username
                ORDER BY cost_yuan DESC
                LIMIT 10
                """,
                (day_start, day_end),
            )
            top_users = list(cur.fetchall())
    finally:
        conn.close()

    total_cost = float(summary.get("total") or 0)
    total_calls = int(summary.get("calls") or 0)

    if total_calls == 0:
        logger.info("daily_cost_digest: no LLM calls yesterday, skipping")
        return {"ok": True, "skipped": True}

    webhook = os.getenv("FEISHU_OPS_WEBHOOK", "").strip()
    if not webhook:
        logger.warning("daily_cost_digest: FEISHU_OPS_WEBHOOK not set, skipping")
        return {"ok": False, "msg": "no webhook"}

    budget = get_budget_status()
    daily_cap = budget["daily"].get("cap_yuan")
    monthly = budget["monthly"]

    lines = [
        f"💰 ClueAI 昨日成本日报（{day_start.strftime('%Y-%m-%d')}）",
        "",
        f"总花费：¥{total_cost:.2f}",
        f"调用次数：{total_calls}",
    ]
    if daily_cap:
        pct = total_cost / daily_cap * 100 if daily_cap > 0 else 0
        lines.append(f"日预算用量：{pct:.1f}% (¥{total_cost:.2f} / ¥{daily_cap:.2f})")
    if monthly.get("cap_yuan"):
        month_pct = monthly["used_yuan"] / monthly["cap_yuan"] * 100 if monthly["cap_yuan"] > 0 else 0
        lines.append(
            f"月预算用量：{month_pct:.1f}% (¥{monthly['used_yuan']:.2f} / ¥{monthly['cap_yuan']:.2f})"
        )
    lines.append("")
    lines.append("Top 用户：")
    for r in top_users[:10]:
        uname = r.get("username") or f"user_{r['user_id']}"
        lines.append(f"  {uname}  ¥{float(r['cost_yuan']):.2f}  ({int(r['calls'])} 次)")

    platform = os.getenv("OPS_WEBHOOK_PLATFORM", "feishu").strip().lower() or "feishu"
    secret = os.getenv("OPS_WEBHOOK_SECRET", "").strip()

    result = send_text_notification(platform, webhook, "\n".join(lines), secret)
    if result.get("ok"):
        return {"ok": True, "total_cost_yuan": total_cost, "users": len(top_users)}
    logger.error("daily_cost_digest: push failed: %s", result.get("msg"))
    return {"ok": False, "msg": result.get("msg", "push failed")}


def enqueue_daily_cost_digest() -> str:
    """入队每日成本日报（由 scheduler 每天 09:07 UTC+8 调用一次）"""
    queue = get_queue()
    job = queue.enqueue(
        daily_cost_digest,
        job_id=f"cost-digest-{datetime.now().strftime('%Y%m%d')}",
        description="Daily LLM cost digest push",
        result_ttl=3600,
        failure_ttl=24 * 60 * 60,
    )
    return job.id
