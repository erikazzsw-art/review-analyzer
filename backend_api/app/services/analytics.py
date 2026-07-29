"""Analytics event tracking service.

Provides async event insertion that does not block the main request path.
"""

import json
import logging
from datetime import datetime, timezone

import psycopg2

from review_analyzer.database import get_connection

logger = logging.getLogger(__name__)


def track_event(user_id: int, event_name: str, properties: dict | None = None) -> None:
    """Insert an analytics event. Fails silently to avoid impacting business logic."""
    conn = None
    try:
        conn = get_connection()
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO analytics_events (user_id, event_name, properties, created_at)
                VALUES (%s, %s, %s, %s)
                """,
                [
                    user_id,
                    event_name,
                    json.dumps(properties or {}),
                    datetime.now(timezone.utc),
                ],
            )
        conn.commit()
    except (psycopg2.Error, Exception) as e:
        logger.warning("analytics track_event failed: %s", e)
    finally:
        if conn is not None:
            conn.close()


def track_llm_call(
    user_id: int,
    *,
    model: str,
    prompt_version: str,
    input_tokens: int,
    output_tokens: int,
    latency_ms: int,
    cost_yuan: float,
    success: bool,
    error_type: str | None = None,
    attempt: int | None = None,
    error_detail: str | None = None,
    schema_error: str | None = None,
    content_hash: str | None = None,
    sub_category: str | None = None,
    locale: str | None = None,
    retry_count: int | None = None,
    final_success: bool | None = None,
) -> None:
    properties = {
        "model": model,
        "prompt_version": prompt_version,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "latency_ms": latency_ms,
        "cost_yuan": cost_yuan,
        "success": success,
        "error_type": error_type,
    }
    optional = {
        "attempt": attempt,
        "error_detail": error_detail,
        "schema_error": schema_error,
        "content_hash": content_hash,
        "sub_category": sub_category,
        "locale": locale,
        "retry_count": retry_count,
        "final_success": final_success,
    }
    properties.update({key: value for key, value in optional.items() if value is not None})
    track_event(user_id, "llm_call", properties)


def track_analysis_complete(
    user_id: int,
    *,
    session_id: int,
    review_count: int,
    cluster_count: int,
    llm_calls: int,
    total_latency_ms: int,
    total_cost_yuan: float,
) -> None:
    savings_pct = round((1 - llm_calls / max(review_count, 1)) * 100, 1)
    track_event(user_id, "analysis_job_complete", {
        "session_id": session_id,
        "review_count": review_count,
        "cluster_count": cluster_count,
        "llm_calls": llm_calls,
        "llm_calls_saved": review_count - llm_calls,
        "savings_pct": savings_pct,
        "total_latency_ms": total_latency_ms,
        "total_cost_yuan": total_cost_yuan,
        "cost_per_review_yuan": round(total_cost_yuan / max(review_count, 1), 6),
    })


def track_quota_check(
    user_id: int,
    *,
    dimension: str,
    current_usage: int,
    limit: int,
    blocked: bool,
) -> None:
    track_event(user_id, "quota_check", {
        "dimension": dimension,
        "current_usage": current_usage,
        "limit": limit,
        "blocked": blocked,
    })
