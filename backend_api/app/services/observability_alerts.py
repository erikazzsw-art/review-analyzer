"""Observability alert evaluation and persistence helpers."""
from __future__ import annotations

import json
import logging
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from typing import Any

import psycopg2.extras

from review_analyzer.database import get_connection, get_setting, set_setting

logger = logging.getLogger(__name__)

ALERT_CONFIG_SETTING_KEY = "observability_alert_config"
ALERT_EVENT_NAME = "observability_alert"
VALID_WEBHOOK_PLATFORMS = ("feishu", "dingtalk", "wechat")

_TZ = timezone(timedelta(hours=8))

DEFAULT_ALERT_CONFIG: dict[str, Any] = {
    "enabled": True,
    "webhook_enabled": False,
    "webhook_platform": "feishu",
    "webhook_url": "",
    "webhook_secret": "",
    "webhook_group_name": "",
    "dedupe_ttl_seconds": 3600,
    "thresholds": {
        "llm_error_rate_warning_pct": 5.0,
        "llm_error_rate_critical_pct": 20.0,
        "llm_p95_warning_ms": 15_000,
        "llm_p95_critical_ms": 30_000,
        "user_daily_cost_warning_yuan": 5.0,
        "user_daily_cost_critical_yuan": 20.0,
        "system_daily_cost_warning_yuan": 100.0,
        "system_daily_cost_critical_yuan": 200.0,
        "cache_savings_warning_pct": 50.0,
        "cache_savings_critical_pct": 20.0,
        "cache_min_reviews": 10,
        "stuck_job_warning_minutes": 15,
        "stuck_job_critical_minutes": 30,
    },
}


def _now_iso() -> str:
    return datetime.now(_TZ).isoformat()


def _day_start() -> datetime:
    now = datetime.now(_TZ)
    return now.replace(hour=0, minute=0, second=0, microsecond=0)


def _clean_platform(value: Any) -> str:
    platform = str(value or "feishu").strip().lower()
    return platform if platform in VALID_WEBHOOK_PLATFORMS else "feishu"


def _clean_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    return bool(value)


def _clean_float(value: Any, fallback: float) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return fallback
    return parsed if parsed >= 0 else fallback


def _clean_int(value: Any, fallback: int, *, min_value: int = 0, max_value: int | None = None) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return fallback
    if parsed < min_value:
        return fallback
    if max_value is not None and parsed > max_value:
        return max_value
    return parsed


def normalize_alert_config(raw: dict[str, Any] | None) -> dict[str, Any]:
    """Merge stored/user supplied config with safe defaults."""
    config = deepcopy(DEFAULT_ALERT_CONFIG)
    if raw:
        config.update(
            {
                "enabled": _clean_bool(raw.get("enabled", config["enabled"])),
                "webhook_enabled": _clean_bool(raw.get("webhook_enabled", config["webhook_enabled"])),
                "webhook_platform": _clean_platform(raw.get("webhook_platform")),
                "webhook_url": str(raw.get("webhook_url") or "").strip(),
                "webhook_secret": str(raw.get("webhook_secret") or "").strip(),
                "webhook_group_name": str(raw.get("webhook_group_name") or "").strip(),
                "dedupe_ttl_seconds": _clean_int(
                    raw.get("dedupe_ttl_seconds"),
                    config["dedupe_ttl_seconds"],
                    min_value=60,
                    max_value=24 * 3600,
                ),
            }
        )

        raw_thresholds = raw.get("thresholds") if isinstance(raw.get("thresholds"), dict) else {}
        for key, default_value in DEFAULT_ALERT_CONFIG["thresholds"].items():
            if isinstance(default_value, int):
                config["thresholds"][key] = _clean_int(
                    raw_thresholds.get(key),
                    int(default_value),
                    min_value=0,
                    max_value=365 * 24 * 60,
                )
            else:
                config["thresholds"][key] = _clean_float(raw_thresholds.get(key), float(default_value))

    return config


def load_alert_config(user_id: int) -> dict[str, Any]:
    raw = get_setting(user_id, ALERT_CONFIG_SETTING_KEY)
    if not raw:
        return normalize_alert_config(None)
    try:
        parsed = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        logger.warning("invalid alert config for user %s, falling back to defaults", user_id)
        return normalize_alert_config(None)
    return normalize_alert_config(parsed if isinstance(parsed, dict) else None)


def save_alert_config(user_id: int, payload: dict[str, Any]) -> dict[str, Any]:
    config = normalize_alert_config(payload)
    set_setting(user_id, ALERT_CONFIG_SETTING_KEY, json.dumps(config, ensure_ascii=False))
    return config


def _severity_for_upper(value: float, warning: float, critical: float) -> str | None:
    if value >= critical:
        return "critical"
    if value >= warning:
        return "warning"
    return None


def _severity_for_lower(value: float, warning: float, critical: float) -> str | None:
    if value <= critical:
        return "critical"
    if value < warning:
        return "warning"
    return None


def _threshold_for_severity(severity: str, warning: float, critical: float) -> float:
    return critical if severity == "critical" else warning


def _alert(
    *,
    alert_type: str,
    severity: str,
    title: str,
    message: str,
    metric_value: float | int,
    threshold: float | int,
    unit: str,
    scope: str,
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    alert_id = f"{scope}:{alert_type}"
    return {
        "id": alert_id,
        "type": alert_type,
        "severity": severity,
        "title": title,
        "message": message,
        "metric_value": metric_value,
        "threshold": threshold,
        "unit": unit,
        "scope": scope,
        "details": details or {},
        "triggered_at": _now_iso(),
        "dedupe_key": alert_id,
        "last_sent_at": None,
    }


def _llm_health(user_id: int) -> dict[str, Any]:
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """
                SELECT
                    COUNT(*) AS total_calls,
                    COUNT(*) FILTER (WHERE (properties->>'success')::boolean = false) AS error_count,
                    PERCENTILE_CONT(0.95) WITHIN GROUP (
                        ORDER BY (properties->>'latency_ms')::int
                    ) AS p95_ms
                FROM analytics_events
                WHERE event_name = 'llm_call'
                  AND user_id = %s
                  AND created_at >= NOW() - INTERVAL '1 hour'
                """,
                (user_id,),
            )
            row = cur.fetchone() or {}
    finally:
        conn.close()

    total = int(row.get("total_calls") or 0)
    errors = int(row.get("error_count") or 0)
    return {
        "total_calls": total,
        "error_count": errors,
        "error_rate": round(errors / total * 100, 2) if total else 0.0,
        "p95_ms": int(row.get("p95_ms") or 0),
    }


def _daily_cost(user_id: int | None) -> float:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            if user_id is None:
                cur.execute(
                    "SELECT COALESCE(SUM(cost_yuan), 0) FROM llm_usage_log WHERE created_at >= %s",
                    (_day_start(),),
                )
            else:
                cur.execute(
                    "SELECT COALESCE(SUM(cost_yuan), 0) FROM llm_usage_log WHERE user_id = %s AND created_at >= %s",
                    (user_id, _day_start()),
                )
            row = cur.fetchone()
            return round(float(row[0] if row and row[0] is not None else 0), 4)
    finally:
        conn.close()


def _cache_effectiveness(user_id: int) -> dict[str, Any]:
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """
                SELECT
                    SUM((properties->>'review_count')::int) AS total_reviews,
                    SUM((properties->>'llm_calls')::int) AS total_llm_calls,
                    AVG((properties->>'savings_pct')::float) AS savings_pct
                FROM analytics_events
                WHERE event_name = 'analysis_job_complete'
                  AND user_id = %s
                  AND created_at >= NOW() - INTERVAL '24 hours'
                """,
                (user_id,),
            )
            row = cur.fetchone() or {}
    finally:
        conn.close()

    return {
        "total_reviews": int(row.get("total_reviews") or 0),
        "total_llm_calls": int(row.get("total_llm_calls") or 0),
        "savings_pct": round(float(row.get("savings_pct") or 0), 1),
    }


def _stuck_jobs(user_id: int, threshold_minutes: int) -> dict[str, Any]:
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """
                SELECT id, session_id, product_id, status, created_at, updated_at,
                       total_rows, processed_rows, error_message, trace_json,
                       EXTRACT(EPOCH FROM (NOW() - updated_at)) / 60 AS stuck_minutes
                FROM upload_jobs
                WHERE user_id = %s
                  AND status = 'processing'
                  AND updated_at < NOW() - (%s * INTERVAL '1 minute')
                ORDER BY updated_at ASC
                LIMIT 10
                """,
                (user_id, threshold_minutes),
            )
            rows = [dict(row) for row in cur.fetchall()]
    finally:
        conn.close()

    max_minutes = max((float(row.get("stuck_minutes") or 0) for row in rows), default=0.0)
    return {
        "count": len(rows),
        "max_minutes": round(max_minutes, 1),
        "examples": [
            {
                "job_id": row.get("id"),
                "session_id": row.get("session_id"),
                "product_id": row.get("product_id"),
                "processed_rows": row.get("processed_rows"),
                "total_rows": row.get("total_rows"),
                "updated_at": str(row.get("updated_at")) if row.get("updated_at") else None,
                "stuck_minutes": round(float(row.get("stuck_minutes") or 0), 1),
            }
            for row in rows[:5]
        ],
    }


def _model_circuit_alerts() -> list[dict[str, Any]]:
    try:
        from backend_api.app.services.llm_router import get_router

        status = get_router().status()
    except Exception:
        logger.warning("failed to read model router status", exc_info=True)
        return []

    open_models = [name for name, info in status.items() if info.get("circuit_open")]
    if not open_models:
        return []

    configured_models = [name for name, info in status.items() if info.get("has_api_key")]
    severity = "critical" if configured_models and len(open_models) >= len(configured_models) else "warning"
    return [
        _alert(
            alert_type="model_circuit_open",
            severity=severity,
            title="模型熔断打开",
            message="、".join(open_models) + " 熔断器处于 open 状态",
            metric_value=len(open_models),
            threshold=1,
            unit="models",
            scope="system",
            details={"open_models": open_models, "models": status},
        )
    ]


def evaluate_alerts(
    user_id: int,
    config: dict[str, Any] | None = None,
    *,
    include_model_status: bool = True,
    include_system_cost: bool = True,
) -> list[dict[str, Any]]:
    """Evaluate active alerts for one user. This function is read-only."""
    resolved = normalize_alert_config(config)
    if not resolved.get("enabled"):
        return []

    thresholds = resolved["thresholds"]
    alerts: list[dict[str, Any]] = []

    health = _llm_health(user_id)
    if health["total_calls"] > 0:
        severity = _severity_for_upper(
            health["error_rate"],
            thresholds["llm_error_rate_warning_pct"],
            thresholds["llm_error_rate_critical_pct"],
        )
        if severity:
            alerts.append(
                _alert(
                    alert_type="llm_error_rate",
                    severity=severity,
                    title="LLM 错误率过高",
                    message=f"最近 1 小时错误率 {health['error_rate']}%，错误 {health['error_count']} / 调用 {health['total_calls']}",
                    metric_value=health["error_rate"],
                    threshold=_threshold_for_severity(
                        severity,
                        thresholds["llm_error_rate_warning_pct"],
                        thresholds["llm_error_rate_critical_pct"],
                    ),
                    unit="%",
                    scope="user",
                    details=health,
                )
            )

        severity = _severity_for_upper(
            health["p95_ms"],
            thresholds["llm_p95_warning_ms"],
            thresholds["llm_p95_critical_ms"],
        )
        if severity:
            alerts.append(
                _alert(
                    alert_type="llm_p95_latency",
                    severity=severity,
                    title="LLM P95 延迟过高",
                    message=f"最近 1 小时 P95 延迟 {health['p95_ms']}ms",
                    metric_value=health["p95_ms"],
                    threshold=_threshold_for_severity(
                        severity,
                        thresholds["llm_p95_warning_ms"],
                        thresholds["llm_p95_critical_ms"],
                    ),
                    unit="ms",
                    scope="user",
                    details=health,
                )
            )

    user_cost = _daily_cost(user_id)
    severity = _severity_for_upper(
        user_cost,
        thresholds["user_daily_cost_warning_yuan"],
        thresholds["user_daily_cost_critical_yuan"],
    )
    if severity:
        alerts.append(
            _alert(
                alert_type="user_daily_cost",
                severity=severity,
                title="单用户日成本过高",
                message=f"当前用户今日 LLM 成本 ¥{user_cost}",
                metric_value=user_cost,
                threshold=_threshold_for_severity(
                    severity,
                    thresholds["user_daily_cost_warning_yuan"],
                    thresholds["user_daily_cost_critical_yuan"],
                ),
                unit="yuan",
                scope="user",
                details={"cost_yuan": user_cost},
            )
        )

    if include_system_cost:
        system_cost = _daily_cost(None)
        severity = _severity_for_upper(
            system_cost,
            thresholds["system_daily_cost_warning_yuan"],
            thresholds["system_daily_cost_critical_yuan"],
        )
        if severity:
            alerts.append(
                _alert(
                    alert_type="system_daily_cost",
                    severity=severity,
                    title="系统日成本过高",
                    message=f"全站今日 LLM 成本 ¥{system_cost}",
                    metric_value=system_cost,
                    threshold=_threshold_for_severity(
                        severity,
                        thresholds["system_daily_cost_warning_yuan"],
                        thresholds["system_daily_cost_critical_yuan"],
                    ),
                    unit="yuan",
                    scope="system",
                    details={"cost_yuan": system_cost},
                )
            )

    cache = _cache_effectiveness(user_id)
    if cache["total_reviews"] >= int(thresholds["cache_min_reviews"]):
        severity = _severity_for_lower(
            cache["savings_pct"],
            thresholds["cache_savings_warning_pct"],
            thresholds["cache_savings_critical_pct"],
        )
        if severity:
            alerts.append(
                _alert(
                    alert_type="cache_savings_low",
                    severity=severity,
                    title="缓存节省率过低",
                    message=f"最近 24 小时缓存节省率 {cache['savings_pct']}%，评论 {cache['total_reviews']} 条",
                    metric_value=cache["savings_pct"],
                    threshold=_threshold_for_severity(
                        severity,
                        thresholds["cache_savings_warning_pct"],
                        thresholds["cache_savings_critical_pct"],
                    ),
                    unit="%",
                    scope="user",
                    details=cache,
                )
            )

    stuck = _stuck_jobs(user_id, int(thresholds["stuck_job_warning_minutes"]))
    if stuck["count"] > 0:
        severity = _severity_for_upper(
            stuck["max_minutes"],
            thresholds["stuck_job_warning_minutes"],
            thresholds["stuck_job_critical_minutes"],
        )
        if severity:
            alerts.append(
                _alert(
                    alert_type="stuck_jobs",
                    severity=severity,
                    title="存在卡死任务",
                    message=f"{stuck['count']} 个任务 processing 超过 {thresholds['stuck_job_warning_minutes']} 分钟",
                    metric_value=stuck["count"],
                    threshold=_threshold_for_severity(
                        severity,
                        thresholds["stuck_job_warning_minutes"],
                        thresholds["stuck_job_critical_minutes"],
                    ),
                    unit="jobs",
                    scope="user",
                    details=stuck,
                )
            )

    if include_model_status:
        alerts.extend(_model_circuit_alerts())

    return alerts


def _event_props(row: dict[str, Any]) -> dict[str, Any]:
    props = row.get("properties") or {}
    if isinstance(props, dict):
        return props
    if isinstance(props, str):
        try:
            parsed = json.loads(props)
        except json.JSONDecodeError:
            return {}
        return parsed if isinstance(parsed, dict) else {}
    return {}


def record_alert_event(
    user_id: int,
    alert: dict[str, Any],
    *,
    notification_status: str,
    notification_message: str = "",
) -> None:
    """Persist alert history. Failures are logged and swallowed by design."""
    properties = {
        **alert,
        "notification_status": notification_status,
        "notification_message": notification_message[:300],
    }
    conn = None
    try:
        conn = get_connection()
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO analytics_events (user_id, event_name, properties, created_at)
                VALUES (%s, %s, %s, NOW())
                """,
                (user_id, ALERT_EVENT_NAME, psycopg2.extras.Json(properties)),
            )
        conn.commit()
    except Exception:
        logger.warning("record_alert_event failed for user %s", user_id, exc_info=True)
    finally:
        if conn is not None:
            conn.close()


def get_alert_history(user_id: int, limit: int = 50) -> list[dict[str, Any]]:
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """
                SELECT id, properties, created_at
                FROM analytics_events
                WHERE event_name = %s
                  AND user_id = %s
                ORDER BY created_at DESC
                LIMIT %s
                """,
                (ALERT_EVENT_NAME, user_id, limit),
            )
            rows = [dict(row) for row in cur.fetchall()]
    finally:
        conn.close()

    history: list[dict[str, Any]] = []
    for row in rows:
        props = _event_props(row)
        history.append(
            {
                "event_id": row["id"],
                "id": props.get("id") or props.get("type") or str(row["id"]),
                "type": props.get("type", ""),
                "severity": props.get("severity", "warning"),
                "title": props.get("title", ""),
                "message": props.get("message", ""),
                "metric_value": props.get("metric_value"),
                "threshold": props.get("threshold"),
                "unit": props.get("unit", ""),
                "scope": props.get("scope", "user"),
                "details": props.get("details") or {},
                "notification_status": props.get("notification_status", ""),
                "notification_message": props.get("notification_message", ""),
                "created_at": str(row["created_at"]),
            }
        )
    return history


def get_last_sent_at_by_alert(user_id: int) -> dict[str, str]:
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """
                SELECT DISTINCT ON (properties->>'id')
                       properties, created_at
                FROM analytics_events
                WHERE event_name = %s
                  AND user_id = %s
                  AND properties->>'notification_status' = 'sent'
                ORDER BY properties->>'id', created_at DESC
                """,
                (ALERT_EVENT_NAME, user_id),
            )
            rows = [dict(row) for row in cur.fetchall()]
    finally:
        conn.close()

    result: dict[str, str] = {}
    for row in rows:
        props = _event_props(row)
        alert_id = str(props.get("id") or props.get("type") or "")
        if alert_id:
            result[alert_id] = str(row["created_at"])
    return result


def get_alert_dashboard(user_id: int, config: dict[str, Any] | None = None) -> dict[str, Any]:
    resolved = normalize_alert_config(config or load_alert_config(user_id))
    current_alerts = evaluate_alerts(user_id, resolved)
    last_sent_at = get_last_sent_at_by_alert(user_id)
    for alert in current_alerts:
        alert["last_sent_at"] = last_sent_at.get(alert["id"])

    return {
        "config": resolved,
        "current_alerts": current_alerts,
        "history": get_alert_history(user_id, limit=50),
        "last_sent_at": last_sent_at,
    }
