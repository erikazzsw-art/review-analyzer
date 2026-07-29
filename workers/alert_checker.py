"""Periodic observability alert scanner.

Runs outside the request path. All notification and analytics writes are best effort:
alerting must never block the main analysis pipeline.
"""
from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Any

from backend_api.app.services.observability_alerts import (
    evaluate_alerts,
    load_alert_config,
    record_alert_event,
)
from review_analyzer.database import get_connection
from review_analyzer.notifier import send_text_notification
from workers.queue import get_queue, get_redis_connection

logger = logging.getLogger(__name__)

ALERT_SCAN_INTERVAL_SECONDS = 600
_TZ = timezone(timedelta(hours=8))


def _active_user_ids() -> list[int]:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            for sql in (
                """
                SELECT id
                FROM users
                WHERE COALESCE(is_active, true) = true
                  AND deleted_at IS NULL
                ORDER BY id
                """,
                """
                SELECT id
                FROM users
                WHERE COALESCE(is_active, true) = true
                ORDER BY id
                """,
                "SELECT id FROM users ORDER BY id",
            ):
                try:
                    cur.execute(sql)
                    break
                except Exception:
                    conn.rollback()
            return [int(row[0]) for row in cur.fetchall()]
    finally:
        conn.close()


def _history_dedupe_recently_seen(user_id: int, alert_id: str, ttl_seconds: int) -> bool:
    since = datetime.now(_TZ) - timedelta(seconds=ttl_seconds)
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT 1
                FROM analytics_events
                WHERE event_name = 'observability_alert'
                  AND user_id = %s
                  AND properties->>'id' = %s
                  AND created_at >= %s
                LIMIT 1
                """,
                (user_id, alert_id, since),
            )
            return cur.fetchone() is not None
    except Exception:
        logger.warning("alert_checker: history dedupe failed for user %s alert %s", user_id, alert_id, exc_info=True)
        return False
    finally:
        conn.close()


def _acquire_dedupe_lock(user_id: int, alert: dict[str, Any], ttl_seconds: int) -> bool:
    alert_id = str(alert.get("dedupe_key") or alert.get("id") or alert.get("type"))
    redis_key = f"observability_alert:{user_id}:{alert_id}"
    try:
        redis_conn = get_redis_connection()
        payload = json.dumps(
            {
                "user_id": user_id,
                "alert_id": alert_id,
                "severity": alert.get("severity"),
                "triggered_at": alert.get("triggered_at"),
            },
            ensure_ascii=False,
        )
        return bool(redis_conn.set(redis_key, payload, nx=True, ex=ttl_seconds))
    except Exception:
        logger.warning("alert_checker: redis dedupe failed, falling back to history", exc_info=True)
        return not _history_dedupe_recently_seen(user_id, alert_id, ttl_seconds)


def _notification_target(config: dict[str, Any]) -> tuple[str, str, str]:
    if config.get("webhook_enabled") and str(config.get("webhook_url") or "").strip():
        return (
            str(config.get("webhook_platform") or "feishu").strip().lower() or "feishu",
            str(config.get("webhook_url") or "").strip(),
            str(config.get("webhook_secret") or "").strip(),
        )
    return (
        os.getenv("OPS_WEBHOOK_PLATFORM", "feishu").strip().lower() or "feishu",
        os.getenv("FEISHU_OPS_WEBHOOK", "").strip(),
        os.getenv("OPS_WEBHOOK_SECRET", "").strip(),
    )


def _format_alert_text(user_id: int, alert: dict[str, Any]) -> str:
    severity_label = "严重" if alert.get("severity") == "critical" else "注意"
    lines = [
        f"ClueAI 可观测性告警 [{severity_label}]",
        "",
        f"用户 ID：{user_id}",
        f"告警类型：{alert.get('title') or alert.get('type')}",
        f"指标值：{alert.get('metric_value')} {alert.get('unit') or ''}",
        f"阈值：{alert.get('threshold')} {alert.get('unit') or ''}",
        f"说明：{alert.get('message') or ''}",
    ]

    details = alert.get("details") if isinstance(alert.get("details"), dict) else {}
    examples = details.get("examples") if isinstance(details.get("examples"), list) else []
    if examples:
        lines.append("")
        lines.append("示例任务：")
        for item in examples[:3]:
            lines.append(
                "  - "
                f"job_id={item.get('job_id')} "
                f"session_id={item.get('session_id') or '-'} "
                f"product_id={item.get('product_id') or '-'} "
                f"stuck={item.get('stuck_minutes') or '-'}min"
            )

    lines.append("")
    lines.append(f"时间：{datetime.now(_TZ).strftime('%Y-%m-%d %H:%M:%S %Z')}")
    return "\n".join(lines)


def _send_or_record(user_id: int, alert: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    ttl_seconds = int(config.get("dedupe_ttl_seconds") or 3600)
    if not _acquire_dedupe_lock(user_id, alert, ttl_seconds):
        return {"status": "deduped", "alert_id": alert.get("id")}

    platform, webhook_url, signing_key = _notification_target(config)
    if not webhook_url:
        record_alert_event(
            user_id,
            alert,
            notification_status="no_webhook",
            notification_message="No webhook configured",
        )
        return {"status": "no_webhook", "alert_id": alert.get("id")}

    try:
        result = send_text_notification(platform, webhook_url, _format_alert_text(user_id, alert), signing_key)
    except Exception as exc:
        logger.warning("alert_checker: notification failed for user %s", user_id, exc_info=True)
        record_alert_event(
            user_id,
            alert,
            notification_status="failed",
            notification_message=str(exc),
        )
        return {"status": "failed", "alert_id": alert.get("id"), "message": str(exc)}

    status = "sent" if result.get("ok") else "failed"
    record_alert_event(
        user_id,
        alert,
        notification_status=status,
        notification_message=str(result.get("msg") or ""),
    )
    return {"status": status, "alert_id": alert.get("id"), "message": result.get("msg")}


def check_alerts_for_user(user_id: int) -> dict[str, Any]:
    try:
        config = load_alert_config(user_id)
    except Exception:
        logger.warning("alert_checker: load config failed for user %s", user_id, exc_info=True)
        return {"user_id": user_id, "ok": False, "error": "load_config_failed"}

    if not config.get("enabled"):
        return {"user_id": user_id, "ok": True, "skipped": True, "reason": "disabled"}

    try:
        alerts = evaluate_alerts(user_id, config)
    except Exception:
        logger.warning("alert_checker: evaluate alerts failed for user %s", user_id, exc_info=True)
        return {"user_id": user_id, "ok": False, "error": "evaluate_failed"}

    results = []
    for alert in alerts:
        try:
            results.append(_send_or_record(user_id, alert, config))
        except Exception:
            logger.warning("alert_checker: send/record failed for user %s alert %s", user_id, alert.get("id"), exc_info=True)
            results.append({"status": "failed", "alert_id": alert.get("id")})

    return {
        "user_id": user_id,
        "ok": True,
        "triggered": len(alerts),
        "sent": sum(1 for item in results if item.get("status") == "sent"),
        "deduped": sum(1 for item in results if item.get("status") == "deduped"),
        "no_webhook": sum(1 for item in results if item.get("status") == "no_webhook"),
        "failed": sum(1 for item in results if item.get("status") == "failed"),
        "results": results,
    }


def run_alert_check() -> dict[str, Any]:
    """Scan all active users. Intended to run every 10 minutes from scheduler."""
    try:
        user_ids = _active_user_ids()
    except Exception:
        logger.warning("alert_checker: active user query failed", exc_info=True)
        return {"ok": False, "error": "active_user_query_failed"}

    per_user = [check_alerts_for_user(user_id) for user_id in user_ids]
    return {
        "ok": True,
        "users_scanned": len(user_ids),
        "triggered": sum(int(item.get("triggered") or 0) for item in per_user),
        "sent": sum(int(item.get("sent") or 0) for item in per_user),
        "deduped": sum(int(item.get("deduped") or 0) for item in per_user),
        "failed": sum(int(item.get("failed") or 0) for item in per_user),
        "details": per_user,
    }


def enqueue_alert_check() -> str:
    queue = get_queue()
    job = queue.enqueue(
        run_alert_check,
        job_id=f"alert-check-{datetime.now().strftime('%Y%m%d%H%M')}",
        description="Observability alert scan",
        result_ttl=3600,
        failure_ttl=24 * 3600,
    )
    return job.id
