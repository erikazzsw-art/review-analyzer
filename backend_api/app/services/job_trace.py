"""Structured Job Trace for pipeline observability.

Each upload job records a trace JSONB with stage timing plus lightweight
decision/event/warning records. Trace helpers are intentionally best-effort:
observability must never block the main analysis path.
"""
from __future__ import annotations

import logging
import math
import time
from dataclasses import dataclass, field
from threading import Lock
from typing import Any

logger = logging.getLogger(__name__)

MAX_DECISIONS = 100
MAX_EVENTS = 250
MAX_WARNINGS = 100
MAX_COLLECTION_ITEMS = 40
MAX_STRING_LENGTH = 500


@dataclass
class StageTrace:
    name: str
    started_at: float = 0.0
    ended_at: float = 0.0
    duration_ms: int = 0
    meta: dict[str, Any] = field(default_factory=dict)
    error: str | None = None


@dataclass
class JobTrace:
    job_id: int
    user_id: int
    stages: list[StageTrace] = field(default_factory=list)
    decisions: list[dict[str, Any]] = field(default_factory=list)
    events: list[dict[str, Any]] = field(default_factory=list)
    warnings: list[dict[str, Any]] = field(default_factory=list)
    dropped_counts: dict[str, int] = field(default_factory=dict)
    started_at: float = field(default_factory=time.time)
    ended_at: float = 0.0
    total_duration_ms: int = 0
    review_count: int = 0
    llm_calls: int = 0
    cache_hits: int = 0
    cluster_count: int = 0
    total_cost_yuan: float = 0.0
    error: str | None = None

    _current_stage: StageTrace | None = field(default=None, repr=False)
    _lock: Any = field(default_factory=Lock, repr=False)

    def begin_stage(self, name: str) -> None:
        try:
            self._current_stage = StageTrace(name=name, started_at=time.time())
        except Exception as exc:
            logger.debug("job_trace begin_stage failed (non-fatal): %s", exc)

    def end_stage(self, meta: dict[str, Any] | None = None, error: str | None = None) -> None:
        try:
            if self._current_stage is None:
                return
            self._current_stage.ended_at = time.time()
            self._current_stage.duration_ms = int(
                (self._current_stage.ended_at - self._current_stage.started_at) * 1000
            )
            if meta:
                self._current_stage.meta = _safe_json_object(meta)
            if error:
                self._current_stage.error = str(error)[:MAX_STRING_LENGTH]
            self.stages.append(self._current_stage)
            self._current_stage = None
        except Exception as exc:
            logger.debug("job_trace end_stage failed (non-fatal): %s", exc)
            self._current_stage = None

    def record_decision(
        self,
        name: str,
        details: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        self._append("decisions", MAX_DECISIONS, name, details, kwargs)

    def record_event(
        self,
        name: str,
        details: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        self._append("events", MAX_EVENTS, name, details, kwargs)

    def record_warning(
        self,
        name: str,
        details: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        self._append("warnings", MAX_WARNINGS, name, details, kwargs)

    def _append(
        self,
        collection_name: str,
        limit: int,
        name: str,
        details: dict[str, Any] | None,
        extra: dict[str, Any],
    ) -> None:
        try:
            payload = {**(details or {}), **extra}
            entry = {
                "name": str(name)[:120],
                "at": time.time(),
                "details": _safe_json_object(payload),
            }
            with self._lock:
                collection = getattr(self, collection_name)
                if len(collection) >= limit:
                    self.dropped_counts[collection_name] = self.dropped_counts.get(collection_name, 0) + 1
                    return
                collection.append(entry)
        except Exception as exc:
            logger.debug("job_trace record %s failed (non-fatal): %s", collection_name, exc)

    def finalize(self, error: str | None = None) -> None:
        try:
            if self._current_stage:
                self.end_stage(error=error or "interrupted")
            self.ended_at = time.time()
            self.total_duration_ms = int((self.ended_at - self.started_at) * 1000)
            if error:
                self.error = str(error)[:MAX_STRING_LENGTH]
        except Exception as exc:
            logger.debug("job_trace finalize failed (non-fatal): %s", exc)

    def to_dict(self) -> dict[str, Any]:
        return {
            "job_id": self.job_id,
            "user_id": self.user_id,
            "started_at": self.started_at,
            "ended_at": self.ended_at,
            "total_duration_ms": self.total_duration_ms,
            "review_count": self.review_count,
            "llm_calls": self.llm_calls,
            "cache_hits": self.cache_hits,
            "cluster_count": self.cluster_count,
            "total_cost_yuan": self.total_cost_yuan,
            "error": self.error,
            "stages": [
                {
                    "name": s.name,
                    "duration_ms": s.duration_ms,
                    "meta": s.meta,
                    "error": s.error,
                }
                for s in self.stages
            ],
            "decisions": self.decisions,
            "events": self.events,
            "warnings": self.warnings,
            "dropped_counts": self.dropped_counts,
        }


def _safe_json_object(value: dict[str, Any]) -> dict[str, Any]:
    return {
        str(key)[:120]: _safe_json_value(item)
        for key, item in list(value.items())[:MAX_COLLECTION_ITEMS]
    }


def _safe_json_value(value: Any, depth: int = 0) -> Any:
    if depth > 4:
        return str(value)[:MAX_STRING_LENGTH]
    if value is None or isinstance(value, bool | int):
        return value
    if isinstance(value, float):
        return value if math.isfinite(value) else str(value)
    if isinstance(value, str):
        return value[:MAX_STRING_LENGTH]
    if isinstance(value, dict):
        return {
            str(key)[:120]: _safe_json_value(item, depth + 1)
            for key, item in list(value.items())[:MAX_COLLECTION_ITEMS]
        }
    if isinstance(value, list | tuple | set):
        return [_safe_json_value(item, depth + 1) for item in list(value)[:MAX_COLLECTION_ITEMS]]
    return str(value)[:MAX_STRING_LENGTH]
