"""V4.5-T12 C3: Observability Dashboard API."""
from __future__ import annotations

import json
import logging
from collections import Counter
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

HEALTH_STATUS_LABELS = {
    "normal": "健康",
    "attention": "注意",
    "abnormal": "异常",
    "critical": "严重",
}

HEALTH_STATUS_RANK = {
    "normal": 0,
    "attention": 1,
    "abnormal": 2,
    "critical": 3,
}

COST_WARNING_YUAN_PER_DAY = 5.0
COST_ABNORMAL_YUAN_PER_DAY = 10.0
COST_CRITICAL_YUAN_PER_DAY = 20.0
TOKEN_WARNING_THRESHOLD = 2_000
TOKEN_CRITICAL_THRESHOLD = 4_000
TRACE_JOB_LIMIT = 500

CACHE_LAYER_LABELS = {
    "l1_exact_hash": "L1 精确 hash",
    "user_history": "本人历史",
    "global_review_pool": "全局 review_pool",
    "semantic_similar": "语义相似",
    "short_text_rating_rule": "短文本规则",
    "cluster_saved": "聚类节省",
}

MISS_REASON_LABELS = {
    "embedding_missing": "缺少 embedding",
    "semantic_reference_unavailable": "无可用语义参考",
    "semantic_similarity_below_threshold": "相似度低于阈值",
}


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


def _window_filter_sql(column_name: str, window_hours: int | None, days: int) -> tuple[str, list[int]]:
    """Return a safe relative-time SQL filter for a known timestamp column."""
    if window_hours is not None:
        return f"{column_name} >= NOW() - (%s * INTERVAL '1 hour')", [window_hours]
    return f"{column_name} >= NOW() - (%s * INTERVAL '1 day')", [days]


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        if value is None:
            return default
        return int(float(value))
    except (TypeError, ValueError):
        return default


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _round_yuan(value: float, digits: int = 4) -> float:
    return round(float(value or 0), digits)


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
    total_tokens = sum(_safe_int(r.get("total_tokens_in")) + _safe_int(r.get("total_tokens_out")) for r in rows)

    partial_errors: list[dict[str, str]] = []
    try:
        trace_rows = _fetch_trace_jobs(user["id"], days=days, window_hours=window_hours)
        rankings = _build_job_cost_rankings(trace_rows)
    except Exception as exc:
        logger.warning("llm cost trace attribution failed (non-fatal): %s", exc, exc_info=True)
        partial_errors.append({"section": "trace_attribution", "message": str(exc)[:200]})
        rankings = {
            "summary": {"total_review_count": 0, "avg_cost_per_review": 0},
            "job_rankings": [],
            "cost_per_review_rankings": [],
            "model_switch_jobs": [],
        }

    try:
        token_anomalies = _get_token_anomalies(user["id"], days=days, window_hours=window_hours)
    except Exception as exc:
        logger.warning("llm cost token anomaly query failed (non-fatal): %s", exc, exc_info=True)
        partial_errors.append({"section": "token_anomalies", "message": str(exc)[:200]})
        token_anomalies = []

    return {
        "summary": {
            "total_cost_yuan": round(total_cost, 4),
            "total_calls": total_calls,
            "cache_hits": cache_hits,
            "cache_rate": round(cache_hits / total_calls * 100, 1) if total_calls else 0,
            "avg_cost_per_call": round(total_cost / (total_calls - cache_hits), 6) if (total_calls - cache_hits) > 0 else 0,
            "avg_cost_per_review": rankings["summary"]["avg_cost_per_review"],
            "trace_review_count": rankings["summary"]["total_review_count"],
            "total_tokens": total_tokens,
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
        "job_rankings": rankings["job_rankings"],
        "cost_per_review_rankings": rankings["cost_per_review_rankings"],
        "model_switches": _build_model_cost_changes(rows),
        "model_switch_jobs": rankings["model_switch_jobs"],
        "token_anomalies": token_anomalies,
        "partial_errors": partial_errors,
    }


@router.get("/pipeline-health")
def get_pipeline_health(
    days: int = Query(default=7, ge=1, le=90),
    window_hours: int | None = Query(default=None, ge=1, le=72),
    user: dict = Depends(get_current_user),
) -> dict:
    """Pipeline latency percentiles, error rate, and throughput."""
    return _query_pipeline_health(user["id"], days=days, window_hours=window_hours)


@router.get("/cache-effectiveness")
def get_cache_effectiveness(
    days: int = Query(default=7, ge=1, le=90),
    window_hours: int | None = Query(default=None, ge=1, le=72),
    user: dict = Depends(get_current_user),
) -> dict:
    """Cache hit rates from analysis_job_complete events."""
    result = _query_cache_effectiveness(user["id"], days=days, window_hours=window_hours)
    partial_errors: list[dict[str, str]] = []
    try:
        trace_rows = _fetch_trace_jobs(user["id"], days=days, window_hours=window_hours)
        result["layered"] = _aggregate_cache_layers_from_jobs(trace_rows)
    except Exception as exc:
        logger.warning("cache layered attribution failed (non-fatal): %s", exc, exc_info=True)
        partial_errors.append({"section": "layered_cache", "message": str(exc)[:200]})
        result["layered"] = _aggregate_cache_layers_from_jobs([])
    result["partial_errors"] = partial_errors
    return result


@router.get("/observability-summary")
def get_observability_summary(
    days: int = Query(default=7, ge=1, le=90),
    window_hours: int | None = Query(default=None, ge=1, le=72),
    user: dict = Depends(get_current_user),
) -> dict:
    """One-shot health conclusion, abnormal reasons, and investigation entry points."""
    return _build_observability_summary(user["id"], days=days, window_hours=window_hours)


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


def _trace_entries(trace: dict[str, Any], collection_name: str, name: str | None = None) -> list[dict[str, Any]]:
    collection = trace.get(collection_name)
    if not isinstance(collection, list):
        return []
    entries: list[dict[str, Any]] = []
    for item in collection:
        if not isinstance(item, dict):
            continue
        if name is not None and item.get("name") != name:
            continue
        entries.append(item)
    return entries


def _entry_details(entry: dict[str, Any]) -> dict[str, Any]:
    details = entry.get("details")
    return details if isinstance(details, dict) else {}


def _counter_from_mapping(value: Any) -> Counter[str]:
    counter: Counter[str] = Counter()
    if not isinstance(value, dict):
        return counter
    for key, count in value.items():
        counter[str(key)] += _safe_int(count)
    return counter


def _fetch_trace_jobs(
    user_id: int,
    *,
    days: int,
    window_hours: int | None,
    limit: int = TRACE_JOB_LIMIT,
) -> list[dict[str, Any]]:
    range_filter, range_params = _window_filter_sql("created_at", window_hours, days)
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                f"""
                SELECT id, status, created_at, updated_at, completed_at, trace_json,
                       total_rows, processed_rows, error_message, session_id,
                       product_id, product_ref_id, variant_ref_id,
                       EXTRACT(EPOCH FROM (NOW() - updated_at)) / 60 AS age_minutes
                FROM upload_jobs
                WHERE user_id = %s
                  AND {range_filter}
                ORDER BY created_at DESC
                LIMIT %s
                """,
                [user_id, *range_params, limit],
            )
            return [dict(row) for row in cur.fetchall()]
    finally:
        conn.close()


def _extract_model_counts(trace: dict[str, Any]) -> Counter[str]:
    counts: Counter[str] = Counter()
    for entry in _trace_entries(trace, "decisions", "llm_prompt_quality"):
        counts.update(_counter_from_mapping(_entry_details(entry).get("model_counts")))
    for stage in trace.get("stages", []) if isinstance(trace.get("stages"), list) else []:
        if not isinstance(stage, dict):
            continue
        meta = stage.get("meta")
        if isinstance(meta, dict):
            counts.update(_counter_from_mapping(meta.get("model_counts")))
    return counts


def _dominant_counter_key(counter: Counter[str]) -> str | None:
    if not counter:
        return None
    return counter.most_common(1)[0][0]


def _job_cost_items(trace_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for row in trace_rows:
        trace = _parse_trace_json(row.get("trace_json"))
        review_count = _safe_int(trace.get("review_count")) or _safe_int(row.get("total_rows"))
        total_cost = _safe_float(trace.get("total_cost_yuan"))
        llm_calls = _safe_int(trace.get("llm_calls"))
        cache_hits = _safe_int(trace.get("cache_hits"))
        if total_cost <= 0 and review_count <= 0 and llm_calls <= 0:
            continue

        model_counts = _extract_model_counts(trace)
        fallback_count = len(_trace_entries(trace, "events", "llm_provider_fallback"))
        failure_count = len(_trace_entries(trace, "events", "llm_provider_failure"))
        item = {
            "job_id": row.get("id"),
            "session_id": row.get("session_id"),
            "product_id": row.get("product_id"),
            "created_at": str(row.get("created_at")) if row.get("created_at") else None,
            "completed_at": str(row.get("completed_at")) if row.get("completed_at") else None,
            "status": _display_job_status(str(row.get("status") or "")),
            "review_count": review_count,
            "llm_calls": llm_calls,
            "cache_hits": cache_hits,
            "total_cost_yuan": _round_yuan(total_cost),
            "cost_per_review_yuan": _round_yuan(total_cost / review_count, 6) if review_count else 0,
            "dominant_model": _dominant_counter_key(model_counts),
            "model_counts": dict(model_counts),
            "fallback_count": fallback_count,
            "provider_failure_count": failure_count,
        }
        items.append(item)
    return items


def _build_job_cost_rankings(trace_rows: list[dict[str, Any]]) -> dict[str, Any]:
    items = _job_cost_items(trace_rows)
    total_review_count = sum(_safe_int(item.get("review_count")) for item in items)
    total_cost = sum(_safe_float(item.get("total_cost_yuan")) for item in items)
    by_total = sorted(items, key=lambda item: item["total_cost_yuan"], reverse=True)[:10]
    by_review = sorted(items, key=lambda item: item["cost_per_review_yuan"], reverse=True)[:10]
    switch_jobs = sorted(
        [
            item
            for item in items
            if item["fallback_count"] > 0 or len(item["model_counts"]) > 1
        ],
        key=lambda item: (item["fallback_count"], item["total_cost_yuan"]),
        reverse=True,
    )[:10]
    return {
        "summary": {
            "total_review_count": total_review_count,
            "avg_cost_per_review": _round_yuan(total_cost / total_review_count, 6) if total_review_count else 0,
        },
        "job_rankings": by_total,
        "cost_per_review_rankings": by_review,
        "model_switch_jobs": switch_jobs,
    }


def _build_model_cost_changes(usage_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    buckets: dict[str, Counter[str]] = {}
    for row in usage_rows:
        model = str(row.get("model_name") or "")
        if not model or model == "cache":
            continue
        date_key = str(row.get("date"))
        buckets.setdefault(date_key, Counter())[model] += _safe_float(row.get("total_cost_yuan"))

    ordered = sorted(buckets.items(), key=lambda item: item[0])
    changes: list[dict[str, Any]] = []
    for (previous_date, previous_costs), (current_date, current_costs) in zip(ordered, ordered[1:], strict=False):
        previous_model = _dominant_counter_key(previous_costs)
        current_model = _dominant_counter_key(current_costs)
        if not previous_model or not current_model or previous_model == current_model:
            continue
        previous_total = sum(previous_costs.values())
        current_total = sum(current_costs.values())
        changes.append(
            {
                "date": current_date,
                "previous_date": previous_date,
                "previous_dominant_model": previous_model,
                "current_dominant_model": current_model,
                "previous_bucket_cost_yuan": _round_yuan(previous_total),
                "current_bucket_cost_yuan": _round_yuan(current_total),
                "total_cost_delta_yuan": _round_yuan(current_total - previous_total),
                "current_model_cost_delta_yuan": _round_yuan(
                    current_costs[current_model] - previous_costs.get(current_model, 0)
                ),
            }
        )
    return list(reversed(changes[-10:]))


def _get_token_anomalies(
    user_id: int,
    *,
    days: int,
    window_hours: int | None,
    limit: int = 10,
) -> list[dict[str, Any]]:
    range_filter, range_params = _window_filter_sql("l.created_at", window_hours, days)
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                f"""
                SELECT l.id, l.created_at, l.session_id, l.comment_id, l.model_name,
                       l.tokens_in, l.tokens_out, l.cost_yuan,
                       (COALESCE(l.tokens_in, 0) + COALESCE(l.tokens_out, 0)) AS total_tokens,
                       uj.id AS job_id
                FROM llm_usage_log l
                LEFT JOIN LATERAL (
                    SELECT id
                    FROM upload_jobs uj
                    WHERE uj.user_id = l.user_id
                      AND uj.session_id = l.session_id
                    ORDER BY uj.created_at DESC
                    LIMIT 1
                ) uj ON true
                WHERE l.user_id = %s
                  AND l.cache_hit = false
                  AND {range_filter}
                ORDER BY total_tokens DESC, l.cost_yuan DESC
                LIMIT %s
                """,
                [user_id, *range_params, limit],
            )
            rows = [dict(row) for row in cur.fetchall()]
    finally:
        conn.close()

    anomalies = []
    for row in rows:
        total_tokens = _safe_int(row.get("total_tokens"))
        if total_tokens >= TOKEN_CRITICAL_THRESHOLD:
            severity = "critical"
        elif total_tokens >= TOKEN_WARNING_THRESHOLD:
            severity = "warning"
        else:
            severity = "normal"
        anomalies.append(
            {
                "usage_id": row.get("id"),
                "job_id": row.get("job_id"),
                "session_id": row.get("session_id"),
                "comment_id": row.get("comment_id"),
                "model": row.get("model_name"),
                "tokens_in": _safe_int(row.get("tokens_in")),
                "tokens_out": _safe_int(row.get("tokens_out")),
                "total_tokens": total_tokens,
                "cost_yuan": _round_yuan(_safe_float(row.get("cost_yuan")), 6),
                "severity": severity,
                "created_at": str(row.get("created_at")) if row.get("created_at") else None,
            }
        )
    return anomalies


def _aggregate_cache_layers_from_jobs(trace_rows: list[dict[str, Any]]) -> dict[str, Any]:
    hit_sources: Counter[str] = Counter()
    hit_levels: Counter[str] = Counter()
    miss_reasons: Counter[str] = Counter()
    checked_count = 0
    hit_count = 0
    miss_count = 0
    cluster_saved_calls = 0
    cluster_propagated_count = 0

    for row in trace_rows:
        trace = _parse_trace_json(row.get("trace_json"))
        for entry in _trace_entries(trace, "decisions", "cache_lookup"):
            details = _entry_details(entry)
            checked_count += _safe_int(details.get("checked_count"))
            hit_count += _safe_int(details.get("hit_count"))
            miss_count += _safe_int(details.get("miss_count"))
            hit_sources.update(_counter_from_mapping(details.get("hit_sources")))
            hit_levels.update(_counter_from_mapping(details.get("hit_levels")))
            miss_reasons.update(_counter_from_mapping(details.get("miss_reasons")))

        for stage in trace.get("stages", []) if isinstance(trace.get("stages"), list) else []:
            if not isinstance(stage, dict) or stage.get("name") != "cache":
                continue
            meta = stage.get("meta") if isinstance(stage.get("meta"), dict) else {}
            if not hit_count and isinstance(meta.get("stats"), dict):
                hit_levels.update(_counter_from_mapping(meta["stats"]))
            if isinstance(meta.get("hit_sources"), dict):
                hit_sources.update(_counter_from_mapping(meta["hit_sources"]))
            if isinstance(meta.get("miss_reasons"), dict):
                miss_reasons.update(_counter_from_mapping(meta["miss_reasons"]))

        for entry in _trace_entries(trace, "decisions", "clustering"):
            details = _entry_details(entry)
            cluster_saved_calls += _safe_int(details.get("saved_llm_calls"))
            cluster_propagated_count += _safe_int(details.get("propagated_count"))

    l1_exact_hash = hit_levels.get("L1", 0)
    semantic_similar = hit_sources.get("semantic_similar", 0)
    layers = [
        {"key": "l1_exact_hash", "label": CACHE_LAYER_LABELS["l1_exact_hash"], "count": l1_exact_hash},
        {"key": "user_history", "label": CACHE_LAYER_LABELS["user_history"], "count": hit_sources.get("user_history", 0)},
        {
            "key": "global_review_pool",
            "label": CACHE_LAYER_LABELS["global_review_pool"],
            "count": hit_sources.get("global_review_pool", 0),
        },
        {"key": "semantic_similar", "label": CACHE_LAYER_LABELS["semantic_similar"], "count": semantic_similar},
        {
            "key": "short_text_rating_rule",
            "label": CACHE_LAYER_LABELS["short_text_rating_rule"],
            "count": hit_sources.get("short_text_rating_rule", 0),
        },
        {"key": "cluster_saved", "label": CACHE_LAYER_LABELS["cluster_saved"], "count": cluster_saved_calls},
    ]

    return {
        "checked_count": checked_count,
        "hit_count": hit_count,
        "miss_count": miss_count,
        "hit_levels": dict(hit_levels),
        "hit_sources": dict(hit_sources),
        "cluster_saved_calls": cluster_saved_calls,
        "cluster_propagated_count": cluster_propagated_count,
        "layers": layers,
        "miss_reasons": [
            {
                "reason": reason,
                "label": MISS_REASON_LABELS.get(reason, reason),
                "count": count,
            }
            for reason, count in miss_reasons.most_common(10)
        ],
    }


def _status_for_upper(value: float, warning: float, abnormal: float, critical: float) -> str:
    if value >= critical:
        return "critical"
    if value >= abnormal:
        return "abnormal"
    if value >= warning:
        return "attention"
    return "normal"


def _status_for_cache_savings(total_reviews: int, savings_pct: float) -> str:
    if total_reviews < DEFAULT_ALERT_CONFIG["thresholds"]["cache_min_reviews"]:
        return "normal"
    if savings_pct < 20:
        return "critical"
    if savings_pct < 35:
        return "abnormal"
    if savings_pct < 50:
        return "attention"
    return "normal"


def _worst_status(statuses: list[str]) -> str:
    if not statuses:
        return "normal"
    return max(statuses, key=lambda status: HEALTH_STATUS_RANK.get(status, 0))


def _daily_cost_pace(total_cost_yuan: float, *, days: int, window_hours: int | None) -> float:
    hours = window_hours if window_hours is not None else days * 24
    return (total_cost_yuan * 24 / hours) if hours > 0 else total_cost_yuan


def _query_pipeline_health(user_id: int, *, days: int, window_hours: int | None) -> dict[str, Any]:
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
                [user_id, *range_params],
            )
            row = cur.fetchone() or {}

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
                [user_id, *range_params],
            )
            daily = [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()

    total = _safe_int(row.get("total"))
    errors = _safe_int(row.get("errors"))
    return {
        "summary": {
            "total_calls": total,
            "error_count": errors,
            "error_rate": round(errors / total * 100, 2) if total else 0,
            "p50_ms": _safe_int(row.get("p50")),
            "p95_ms": _safe_int(row.get("p95")),
            "p99_ms": _safe_int(row.get("p99")),
            "avg_latency_ms": _safe_int(row.get("avg_latency")),
        },
        "daily": [
            {
                "date": str(r["date"]),
                "calls": r["calls"],
                "errors": r["errors"],
                "avg_latency_ms": _safe_int(r.get("avg_latency")),
            }
            for r in daily
        ],
    }


def _query_cache_effectiveness(user_id: int, *, days: int, window_hours: int | None) -> dict[str, Any]:
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
                [user_id, *range_params],
            )
            summary = cur.fetchone() or {}

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
                [user_id, *range_params],
            )
            daily = [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()

    total_reviews = _safe_int(summary.get("total_reviews"))
    total_saved = _safe_int(summary.get("total_saved"))
    return {
        "summary": {
            "total_reviews": total_reviews,
            "total_llm_calls": _safe_int(summary.get("total_llm_calls")),
            "cache_saves": total_saved,
            "savings_pct": round(_safe_float(summary.get("avg_savings_pct")), 1),
            "estimated_cost_saved_yuan": round(total_saved * 0.03 / 100, 4),
        },
        "daily": [
            {
                "date": str(r["date"]),
                "reviews": r["reviews"],
                "llm_calls": r["llm_calls"],
                "saved": r["saved"],
                "savings_pct": round(_safe_float(r.get("savings_pct")), 1),
            }
            for r in daily
        ],
    }


def _model_circuit_component() -> dict[str, Any]:
    model_status = get_router().status()
    configured = [name for name, info in model_status.items() if info.get("has_api_key")]
    open_models = [name for name, info in model_status.items() if info.get("circuit_open")]
    if open_models and configured and len(open_models) >= len(configured):
        status = "critical"
    elif open_models:
        status = "attention"
    else:
        status = "normal"
    return {
        "status": status,
        "open_models": open_models,
        "configured_model_count": len(configured),
        "models": model_status,
    }


def _job_failure_component(trace_rows: list[dict[str, Any]]) -> dict[str, Any]:
    failed_rows = [
        row
        for row in trace_rows
        if str(row.get("status") or "").lower() in {"failed", "error"}
    ]
    processing_rows = [
        row
        for row in trace_rows
        if str(row.get("status") or "").lower() == "processing"
    ]
    max_processing_minutes = max((_safe_float(row.get("age_minutes")) for row in processing_rows), default=0.0)
    stuck_count = sum(1 for row in processing_rows if _safe_float(row.get("age_minutes")) >= 15)
    if max_processing_minutes >= 30:
        status = "critical"
    elif stuck_count > 0 or len(failed_rows) >= 3:
        status = "abnormal"
    elif failed_rows:
        status = "attention"
    else:
        status = "normal"
    return {
        "status": status,
        "failed_count": len(failed_rows),
        "stuck_count": stuck_count,
        "max_processing_minutes": round(max_processing_minutes, 1),
        "examples": [
            {
                "job_id": row.get("id"),
                "status": row.get("status"),
                "session_id": row.get("session_id"),
                "product_id": row.get("product_id"),
                "error_type": _classify_error(str(row.get("error_message")) if row.get("error_message") else None),
                "created_at": str(row.get("created_at")) if row.get("created_at") else None,
            }
            for row in failed_rows[:5]
        ],
    }


def _component(
    *,
    key: str,
    label: str,
    status: str,
    value: float | int | str,
    unit: str = "",
    message: str,
    tab: str,
    entry: str,
) -> dict[str, Any]:
    return {
        "key": key,
        "label": label,
        "status": status,
        "status_label": HEALTH_STATUS_LABELS[status],
        "value": value,
        "unit": unit,
        "message": message,
        "suggested_tab": tab,
        "suggested_entry": entry,
    }


def _suggested_entries(reasons: list[dict[str, Any]]) -> list[dict[str, str]]:
    by_tab: dict[str, dict[str, str]] = {}
    for reason in reasons:
        tab = str(reason.get("suggested_tab") or "")
        if not tab or tab in by_tab:
            continue
        by_tab[tab] = {
            "tab": tab,
            "label": str(reason.get("suggested_entry") or tab),
            "reason": str(reason.get("message") or ""),
        }
    return list(by_tab.values())


def _build_observability_summary(
    user_id: int,
    *,
    days: int,
    window_hours: int | None,
) -> dict[str, Any]:
    partial_errors: list[dict[str, str]] = []

    def safe_section(section: str, fallback: Any, loader: Any) -> Any:
        try:
            return loader()
        except Exception as exc:
            logger.warning("observability summary %s failed (non-fatal): %s", section, exc, exc_info=True)
            partial_errors.append({"section": section, "message": str(exc)[:200]})
            return fallback

    pipeline = safe_section(
        "pipeline_health",
        {"summary": {"total_calls": 0, "error_count": 0, "error_rate": 0, "p95_ms": 0}, "daily": []},
        lambda: _query_pipeline_health(user_id, days=days, window_hours=window_hours),
    )
    usage_rows = safe_section(
        "llm_usage",
        [],
        lambda: get_llm_usage_stats(user_id=user_id, days=days, window_hours=window_hours),
    )
    trace_rows = safe_section(
        "job_traces",
        [],
        lambda: _fetch_trace_jobs(user_id, days=days, window_hours=window_hours),
    )
    cache = safe_section(
        "cache_effectiveness",
        {"summary": {"total_reviews": 0, "savings_pct": 0}, "daily": []},
        lambda: _query_cache_effectiveness(user_id, days=days, window_hours=window_hours),
    )
    circuit = safe_section("model_status", {"status": "normal", "open_models": []}, _model_circuit_component)

    total_cost = sum(_safe_float(row.get("total_cost_yuan")) for row in usage_rows)
    cost_pace = _daily_cost_pace(total_cost, days=days, window_hours=window_hours)
    failed_jobs = _job_failure_component(trace_rows)
    cache_summary = cache["summary"]

    error_status = _status_for_upper(
        _safe_float(pipeline["summary"].get("error_rate")),
        DEFAULT_ALERT_CONFIG["thresholds"]["llm_error_rate_warning_pct"],
        10.0,
        DEFAULT_ALERT_CONFIG["thresholds"]["llm_error_rate_critical_pct"],
    )
    p95_status = _status_for_upper(
        _safe_float(pipeline["summary"].get("p95_ms")),
        DEFAULT_ALERT_CONFIG["thresholds"]["llm_p95_warning_ms"],
        20_000,
        DEFAULT_ALERT_CONFIG["thresholds"]["llm_p95_critical_ms"],
    )
    cost_status = _status_for_upper(
        cost_pace,
        COST_WARNING_YUAN_PER_DAY,
        COST_ABNORMAL_YUAN_PER_DAY,
        COST_CRITICAL_YUAN_PER_DAY,
    )
    cache_status = _status_for_cache_savings(
        _safe_int(cache_summary.get("total_reviews")),
        _safe_float(cache_summary.get("savings_pct")),
    )

    components = [
        _component(
            key="llm_error_rate",
            label="综合错误率",
            status=error_status,
            value=_safe_float(pipeline["summary"].get("error_rate")),
            unit="%",
            message=f"LLM 错误 {pipeline['summary'].get('error_count', 0)} / 调用 {pipeline['summary'].get('total_calls', 0)}",
            tab="jobs",
            entry="任务 Tab / trace timeline",
        ),
        _component(
            key="llm_p95",
            label="P95 延迟",
            status=p95_status,
            value=_safe_int(pipeline["summary"].get("p95_ms")),
            unit="ms",
            message="P95 超过阈值时优先查看慢任务阶段和模型 fallback",
            tab="jobs",
            entry="任务 Tab / 模型路由事件",
        ),
        _component(
            key="model_circuit",
            label="模型熔断",
            status=str(circuit.get("status") or "normal"),
            value=len(circuit.get("open_models") or []),
            unit="models",
            message=(
                "、".join(circuit.get("open_models") or []) + " 熔断打开"
                if circuit.get("open_models")
                else "所有已配置模型熔断状态正常"
            ),
            tab="alerts",
            entry="告警 Tab / 模型状态",
        ),
        _component(
            key="cost",
            label="成本",
            status=cost_status,
            value=_round_yuan(cost_pace),
            unit="¥/day pace",
            message=f"当前窗口总成本 ¥{_round_yuan(total_cost)}，折算日成本 ¥{_round_yuan(cost_pace)}",
            tab="cost",
            entry="成本 Tab / 成本排行",
        ),
        _component(
            key="cache",
            label="缓存",
            status=cache_status,
            value=_safe_float(cache_summary.get("savings_pct")),
            unit="%",
            message=f"缓存节省率 {cache_summary.get('savings_pct', 0)}%，评论数 {cache_summary.get('total_reviews', 0)}",
            tab="cache",
            entry="缓存 Tab / 命中来源与 miss 原因",
        ),
        _component(
            key="failed_jobs",
            label="失败任务",
            status=failed_jobs["status"],
            value=failed_jobs["failed_count"] + failed_jobs["stuck_count"],
            unit="jobs",
            message=f"失败 {failed_jobs['failed_count']}，卡住 {failed_jobs['stuck_count']}",
            tab="jobs",
            entry="任务 Tab / 失败任务",
        ),
    ]
    reasons = [component for component in components if component["status"] != "normal"]
    worst = _worst_status([component["status"] for component in components])
    penalty = sum({"attention": 12, "abnormal": 28, "critical": 45}.get(reason["status"], 0) for reason in reasons)
    score = max(0, 100 - penalty)
    if worst == "normal" and partial_errors:
        worst = "attention"
        score = min(score, 88)

    if reasons:
        summary_text = f"发现 {len(reasons)} 个需要关注的可观测性信号，优先查看建议入口。"
    elif partial_errors:
        summary_text = "核心指标未见异常，但部分统计读取失败，需要稍后刷新确认。"
    else:
        summary_text = "当前窗口核心指标健康，暂无需要立即处理的异常。"

    return {
        "health": {
            "status": worst,
            "label": HEALTH_STATUS_LABELS[worst],
            "score": score,
            "summary": summary_text,
        },
        "components": components,
        "reasons": reasons,
        "suggested_entries": _suggested_entries(reasons),
        "metrics": {
            "total_calls": pipeline["summary"].get("total_calls", 0),
            "error_rate": pipeline["summary"].get("error_rate", 0),
            "p95_ms": pipeline["summary"].get("p95_ms", 0),
            "total_cost_yuan": _round_yuan(total_cost),
            "daily_cost_pace_yuan": _round_yuan(cost_pace),
            "cache_savings_pct": cache_summary.get("savings_pct", 0),
            "failed_job_count": failed_jobs["failed_count"],
            "stuck_job_count": failed_jobs["stuck_count"],
            "open_models": circuit.get("open_models", []),
        },
        "partial_errors": partial_errors,
    }


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
            "decisions": trace.get("decisions", []),
            "events": trace.get("events", []),
            "warnings": trace.get("warnings", []),
            "dropped_counts": trace.get("dropped_counts", {}),
        })

    return {"total": total, "traces": traces}
