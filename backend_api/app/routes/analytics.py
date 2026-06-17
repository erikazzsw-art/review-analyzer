"""V4.5-T12 C3: Observability Dashboard API."""
from __future__ import annotations

import logging

import psycopg2.extras
from fastapi import APIRouter, Depends, Query

from backend_api.app.deps import get_current_user
from backend_api.app.services.llm_router import get_router
from review_analyzer.database import get_connection, get_llm_usage_stats

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/llm-costs")
def get_llm_costs(
    days: int = Query(default=30, ge=1, le=365),
    user: dict = Depends(get_current_user),
) -> dict:
    rows = get_llm_usage_stats(user_id=user["id"], days=days)
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
    user: dict = Depends(get_current_user),
) -> dict:
    """Pipeline latency percentiles, error rate, and throughput."""
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """
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
                  AND created_at >= NOW() - INTERVAL '%s days'
                """,
                [user["id"], days],
            )
            row = cur.fetchone()

            cur.execute(
                """
                SELECT DATE(created_at) AS date,
                       COUNT(*) AS calls,
                       COUNT(*) FILTER (WHERE (properties->>'success')::boolean = false) AS errors,
                       AVG((properties->>'latency_ms')::int) AS avg_latency
                FROM analytics_events
                WHERE event_name = 'llm_call'
                  AND user_id = %s
                  AND created_at >= NOW() - INTERVAL '%s days'
                GROUP BY DATE(created_at)
                ORDER BY date DESC
                """,
                [user["id"], days],
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
    user: dict = Depends(get_current_user),
) -> dict:
    """Cache hit rates from analysis_job_complete events."""
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """
                SELECT
                    SUM((properties->>'review_count')::int) AS total_reviews,
                    SUM((properties->>'llm_calls')::int) AS total_llm_calls,
                    SUM((properties->>'llm_calls_saved')::int) AS total_saved,
                    AVG((properties->>'savings_pct')::float) AS avg_savings_pct,
                    SUM((properties->>'total_cost_yuan')::float) AS total_cost
                FROM analytics_events
                WHERE event_name = 'analysis_job_complete'
                  AND user_id = %s
                  AND created_at >= NOW() - INTERVAL '%s days'
                """,
                [user["id"], days],
            )
            summary = cur.fetchone()

            cur.execute(
                """
                SELECT DATE(created_at) AS date,
                       SUM((properties->>'review_count')::int) AS reviews,
                       SUM((properties->>'llm_calls')::int) AS llm_calls,
                       SUM((properties->>'llm_calls_saved')::int) AS saved,
                       AVG((properties->>'savings_pct')::float) AS savings_pct
                FROM analytics_events
                WHERE event_name = 'analysis_job_complete'
                  AND user_id = %s
                  AND created_at >= NOW() - INTERVAL '%s days'
                GROUP BY DATE(created_at)
                ORDER BY date DESC
                """,
                [user["id"], days],
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


@router.get("/job-traces")
def get_job_traces(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    user: dict = Depends(get_current_user),
) -> dict:
    """Paginated job traces with timing and error info."""
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """
                SELECT id, status, created_at, completed_at, trace_json,
                       total_rows, processed_rows, error_message
                FROM upload_jobs
                WHERE user_id = %s AND trace_json IS NOT NULL
                ORDER BY created_at DESC
                LIMIT %s OFFSET %s
                """,
                [user["id"], limit, offset],
            )
            rows = cur.fetchall()

            cur.execute(
                "SELECT COUNT(*) FROM upload_jobs WHERE user_id = %s AND trace_json IS NOT NULL",
                [user["id"]],
            )
            total = cur.fetchone()["count"]
    finally:
        conn.close()

    traces = []
    for r in rows:
        trace = r["trace_json"] if isinstance(r["trace_json"], dict) else {}
        traces.append({
            "job_id": r["id"],
            "status": r["status"],
            "created_at": str(r["created_at"]),
            "completed_at": str(r["completed_at"]) if r["completed_at"] else None,
            "total_rows": r["total_rows"],
            "processed_rows": r["processed_rows"],
            "total_duration_ms": trace.get("total_duration_ms"),
            "llm_calls": trace.get("llm_calls"),
            "cache_hits": trace.get("cache_hits"),
            "total_cost_yuan": trace.get("total_cost_yuan"),
            "error": trace.get("error") or r["error_message"],
            "stages": trace.get("stages", []),
        })

    return {"total": total, "traces": traces}
