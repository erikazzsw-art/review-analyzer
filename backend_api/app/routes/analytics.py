"""V4.5-T12 C3: Observability Dashboard API."""
from __future__ import annotations

import json
import logging
from typing import Any

import psycopg2.extras
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field

from backend_api.app.deps import get_current_user
from backend_api.app.services.llm_router import get_router
from backend_api.app.services.observability_alerts import (
    DEFAULT_ALERT_CONFIG,
    get_alert_dashboard,
    save_alert_config,
)
from review_analyzer.database import get_connection, get_llm_usage_stats

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/analytics", tags=["analytics"])


class AlertConfigPayload(BaseModel):
    enabled: bool = True
    webhook_enabled: bool = False
    webhook_platform: str = "feishu"
    webhook_url: str = ""
    webhook_secret: str = ""
    webhook_group_name: str = ""
    dedupe_ttl_seconds: int = Field(default=3600, ge=60, le=86400)
    thresholds: dict[str, Any] = Field(default_factory=lambda: dict(DEFAULT_ALERT_CONFIG["thresholds"]))


def _analytics_window_sql(window_hours: int | None, days: int) -> tuple[str, str, list[int]]:
    """Return bucket expression, created_at filter, and params for hour/day windows."""
    if window_hours is not None:
        return (
            "DATE_TRUNC('hour', created_at)",
            "created_at >= NOW() - (%s * INTERVAL '1 hour')",
            [window_hours],
        )

    return (
        "DATE(created_at)",
        "created_at >= NOW() - (%s * INTERVAL '1 day')",
        [days],
    )


@router.get("/alert-config")
def get_alert_config(
    user: dict = Depends(get_current_user),
) -> dict:
    """Alert config, active alerts, recent history, and last sent timestamps."""
    return get_alert_dashboard(user["id"])


@router.put("/alert-config")
def put_alert_config(
    payload: AlertConfigPayload,
    user: dict = Depends(get_current_user),
) -> dict:
    """Update alert thresholds, switches, webhook target, and Redis dedupe TTL."""
    config = save_alert_config(user["id"], payload.model_dump())
    return get_alert_dashboard(user["id"], config)


@router.get("/llm-costs")
def get_llm_costs(
    days: int = Query(default=30, ge=1, le=365),
    window_hours: int | None = Query(default=None, ge=1, le=72),
    user: dict = Depends(get_current_user),
) -> dict:
    rows = get_llm_usage_stats(user_id=user["id"], days=days, window_hours=window_hours)
    total_cost = sum(float(r.get("total_cost_yuan") or 0) for r in rows)
    total_calls = sum(int(r.get("call_count") or 0) for r in rows)
    cache_hits = sum(int(r.get("cache_hits") or 0) for r in rows)

    return {
        "summary": {
            "total_cost_yuan": round(total_cost, 4),
            "total_calls": total_calls,
            "cache_hits": cache_hits,
            "cache_rate": round(cache_hits / total_calls * 100, 1) if total_calls else 0,
            "avg_cost_per_call": round(total_cost / (total_calls - cache_hits), 6) if (total_calls - cache_hits) > 0 else 0,
        },
        "daily": [
            {
                "date": str(r["date"]),
                "model": r["model_name"],
                "calls": r["call_count"],
                "tokens_in": r["total_tokens_in"],
                "tokens_out": r["total_tokens_out"],
                "cost_yuan": float(r["total_cost_yuan"] or 0),
                "cache_hits": r["cache_hits"],
            }
            for r in rows
        ],
    }


@router.get("/pipeline-health")
def get_pipeline_health(
    days: int = Query(default=7, ge=1, le=90),
    window_hours: int | None = Query(default=None, ge=1, le=72),
    user: dict = Depends(get_current_user),
) -> dict:
    """Pipeline latency percentiles, error rate, and throughput."""
    bucket_expr, range_filter, range_params = _analytics_window_sql(window_hours, days)
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                f"""
                SELECT
                    COUNT(*) AS total,
                    COUNT(*) FILTER (WHERE (properties->>'success')::boolean = false) AS errors,
                    PERCENTILE_CONT(0.50) WITHIN GROUP (
                        ORDER BY (properties->>'latency_ms')::int
                    ) AS p50,
                    PERCENTILE_CONT(0.95) WITHIN GROUP (
                        ORDER BY (properties->>'latency_ms')::int
                    ) AS p95,
                    PERCENTILE_CONT(0.99) WITHIN GROUP (
                        ORDER BY (properties->>'latency_ms')::int
                    ) AS p99,
                    AVG((properties->>'latency_ms')::int) AS avg_latency
                FROM analytics_events
                WHERE event_name = 'llm_call'
                  AND user_id = %s
                  AND {range_filter}
                """,
                [user["id"], *range_params],
            )
            row = cur.fetchone()

            cur.execute(
                f"""
                SELECT {bucket_expr} AS date,
                       COUNT(*) AS calls,
                       COUNT(*) FILTER (WHERE (properties->>'success')::boolean = false) AS errors,
                       AVG((properties->>'latency_ms')::int) AS avg_latency
                FROM analytics_events
                WHERE event_name = 'llm_call'
                  AND user_id = %s
                  AND {range_filter}
                GROUP BY {bucket_expr}
                ORDER BY date DESC
                """,
                [user["id"], *range_params],
            )
            daily = [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()

    total = int(row["total"] or 0)
    errors = int(row["errors"] or 0)
    return {
        "summary": {
            "total_calls": total,
            "error_count": errors,
            "error_rate": round(errors / total * 100, 2) if total else 0,
            "p50_ms": int(row["p50"] or 0),
            "p95_ms": int(row["p95"] or 0),
            "p99_ms": int(row["p99"] or 0),
            "avg_latency_ms": int(row["avg_latency"] or 0),
        },
        "daily": [
            {
                "date": str(r["date"]),
                "calls": r["calls"],
                "errors": r["errors"],
                "avg_latency_ms": int(r["avg_latency"] or 0),
            }
            for r in daily
        ],
    }


@router.get("/cache-effectiveness")
def get_cache_effectiveness(
    days: int = Query(default=7, ge=1, le=90),
    window_hours: int | None = Query(default=None, ge=1, le=72),
    user: dict = Depends(get_current_user),
) -> dict:
    """Cache hit rates from analysis_job_complete events."""
    bucket_expr, range_filter, range_params = _analytics_window_sql(window_hours, days)
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                f"""
                SELECT
                    SUM((properties->>'review_count')::int) AS total_reviews,
                    SUM((properties->>'llm_calls')::int) AS total_llm_calls,
                    SUM((properties->>'llm_calls_saved')::int) AS total_saved,
                    AVG((properties->>'savings_pct')::float) AS avg_savings_pct,
                    SUM((properties->>'total_cost_yuan')::float) AS total_cost
                FROM analytics_events
                WHERE event_name = 'analysis_job_complete'
                  AND user_id = %s
                  AND {range_filter}
                """,
                [user["id"], *range_params],
            )
            summary = cur.fetchone()

            cur.execute(
                f"""
                SELECT {bucket_expr} AS date,
                       SUM((properties->>'review_count')::int) AS reviews,
                       SUM((properties->>'llm_calls')::int) AS llm_calls,
                       SUM((properties->>'llm_calls_saved')::int) AS saved,
                       AVG((properties->>'savings_pct')::float) AS savings_pct
                FROM analytics_events
                WHERE event_name = 'analysis_job_complete'
                  AND user_id = %s
                  AND {range_filter}
                GROUP BY {bucket_expr}
                ORDER BY date DESC
                """,
                [user["id"], *range_params],
            )
            daily = [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()

    total_reviews = int(summary["total_reviews"] or 0)
    total_saved = int(summary["total_saved"] or 0)
    return {
        "summary": {
            "total_reviews": total_reviews,
            "total_llm_calls": int(summary["total_llm_calls"] or 0),
            "cache_saves": total_saved,
            "savings_pct": round(float(summary["avg_savings_pct"] or 0), 1),
            "estimated_cost_saved_yuan": round(
                total_saved * 0.03 / 100, 4
            ),
        },
        "daily": [
            {
                "date": str(r["date"]),
                "reviews": r["reviews"],
                "llm_calls": r["llm_calls"],
                "saved": r["saved"],
                "savings_pct": round(float(r["savings_pct"] or 0), 1),
            }
            for r in daily
        ],
    }


@router.get("/model-status")
def get_model_status(
    user: dict = Depends(get_current_user),
) -> dict:
    """LLM router circuit breaker status per model."""
    return {"models": get_router().status()}


def _parse_trace_json(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return {}
        return parsed if isinstance(parsed, dict) else {}
    return {}


def _display_job_status(raw_status: str) -> str:
    if raw_status in {"done", "completed"}:
        return "completed"
    return raw_status


def _failure_stage(status_value: str, trace: dict[str, Any]) -> str | None:
    stages = trace.get("stages") if isinstance(trace.get("stages"), list) else []
    for stage in stages:
        if isinstance(stage, dict) and stage.get("error"):
            return str(stage.get("name") or "")
    if status_value in {"failed", "error"} and stages:
        last_stage = stages[-1]
        if isinstance(last_stage, dict):
            return str(last_stage.get("name") or "") or None
    return None


def _classify_error(error_message: str | None) -> str | None:
    if not error_message:
        return None
    text = error_message.lower()
    if "insufficient" in text or "credit" in text or "quota" in text:
        return "insufficient_credits"
    if "timeout" in text or "stuck" in text or "卡死" in text:
        return "timeout"
    if "circuit" in text or "breaker" in text or "熔断" in text:
        return "model_circuit"
    if "429" in text or "rate limit" in text or "too many" in text:
        return "rate_limit"
    if "json" in text or "decode" in text or "schema" in text:
        return "model_output_invalid"
    if "connection" in text or "network" in text or "requests" in text:
        return "network"
    if "database" in text or "psycopg" in text or "sql" in text:
        return "database"
    return "unknown"


@router.get("/job-traces")
def get_job_traces(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    status_filter: str | None = Query(default=None, alias="status"),
    user: dict = Depends(get_current_user),
) -> dict:
    """Paginated job traces with timing and error info."""
    where = ["user_id = %s"]
    params: list[Any] = [user["id"]]
    if status_filter and status_filter != "all":
        if status_filter == "completed":
            where.append("status IN ('done', 'completed')")
        else:
            where.append("status = %s")
            params.append(status_filter)
    where_sql = " AND ".join(where)

    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                f"""
                SELECT id, status, created_at, completed_at, trace_json,
                       total_rows, processed_rows, error_message, session_id,
                       product_id, product_ref_id, variant_ref_id,
                       EXISTS (
                           SELECT 1
                           FROM credit_ledger cl
                           WHERE cl.user_id = upload_jobs.user_id
                             AND cl.reason = 'review_analyze'
                             AND cl.ref_id = upload_jobs.id::text
                       ) AS credit_charged
                FROM upload_jobs
                WHERE {where_sql}
                ORDER BY created_at DESC
                LIMIT %s OFFSET %s
                """,
                [*params, limit, offset],
            )
            rows = cur.fetchall()

            cur.execute(
                f"SELECT COUNT(*) FROM upload_jobs WHERE {where_sql}",
                params,
            )
            total = cur.fetchone()["count"]
    finally:
        conn.close()

    traces = []
    for r in rows:
        trace = _parse_trace_json(r["trace_json"])
        raw_status = str(r["status"])
        error_message = trace.get("error") or r["error_message"]
        total_rows = int(r["total_rows"] or 0)
        processed_rows = int(r["processed_rows"] or 0)
        traces.append({
            "job_id": r["id"],
            "status": _display_job_status(raw_status),
            "raw_status": raw_status,
            "created_at": str(r["created_at"]),
            "completed_at": str(r["completed_at"]) if r["completed_at"] else None,
            "total_rows": total_rows,
            "processed_rows": processed_rows,
            "session_id": r["session_id"],
            "product_id": r["product_id"],
            "product_ref_id": r["product_ref_id"],
            "variant_ref_id": r["variant_ref_id"],
            "credit_charged": bool(r["credit_charged"]),
            "partial_completed": raw_status not in {"done", "completed"} and processed_rows > 0,
            "failure_stage": _failure_stage(raw_status, trace),
            "error_type": _classify_error(str(error_message) if error_message else None),
            "total_duration_ms": trace.get("total_duration_ms"),
            "llm_calls": trace.get("llm_calls"),
            "cache_hits": trace.get("cache_hits"),
            "total_cost_yuan": trace.get("total_cost_yuan"),
            "error": error_message,
            "stages": trace.get("stages", []),
        })

    return {"total": total, "traces": traces}
