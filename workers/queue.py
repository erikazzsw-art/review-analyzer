from __future__ import annotations

from functools import lru_cache

from backend_api.app.config import get_settings


def _import_redis() -> type:
    try:
        from redis import Redis
    except ImportError as exc:  # pragma: no cover - runtime dependency guard
        raise RuntimeError(
            "Redis support is not installed. Install `redis` and `rq` to run workers."
        ) from exc
    return Redis


def _import_queue() -> type:
    try:
        from rq import Queue
    except ImportError as exc:  # pragma: no cover - runtime dependency guard
        raise RuntimeError(
            "RQ support is not installed. Install `redis` and `rq` to run workers."
        ) from exc
    return Queue


@lru_cache(maxsize=1)
def get_redis_connection():
    settings = get_settings()
    redis_cls = _import_redis()
    return redis_cls.from_url(settings.redis_url, decode_responses=False)


@lru_cache(maxsize=4)
def get_queue(queue_name: str | None = None):
    settings = get_settings()
    queue_cls = _import_queue()
    connection = get_redis_connection()
    resolved_name = queue_name or settings.rq_queue_name
    return queue_cls(
        resolved_name,
        connection=connection,
        default_timeout=settings.rq_job_timeout_seconds,
    )

