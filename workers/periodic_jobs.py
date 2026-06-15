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
                    from scripts.aspect_taxonomy import get_aspect_label_zh
                    escalation_actions.append({
                        "tag_name": esc.tag_name,
                        "tag_label": get_aspect_label_zh(esc.tag_name),
                        "suggested_action": "已写入行动中心",
                        "expected_timeline": "",
                    })

        dept_issues = route_issues_by_department(top_issues[:10], user_dept_mapping)

        from scripts.aspect_taxonomy import get_aspect_label_zh
        for dept_list in dept_issues.values():
            for issue in dept_list:
                issue["tag_label"] = get_aspect_label_zh(issue.get("tag", ""))
        for hl in top_highlights[:3]:
            hl["tag_label"] = get_aspect_label_zh(hl.get("tag", ""))

        period_label = f"{period_start.isoformat()} ~ {period_end.isoformat()}"
        secret = settings.get("webhook_secret", "")

        push_result = send_rich_push(
            webhook_url=webhook_url,
            product_name=product_name,
            period_label=period_label,
            dept_issues=dept_issues,
            dept_contacts=dept_contacts,
            escalation_results=escalation_actions or None,
            top_highlights=top_highlights[:3],
            secret=secret,
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
