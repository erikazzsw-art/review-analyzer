"""V4.5-T12 C2: Structured Job Trace for pipeline observability.

Each upload job records a trace JSONB with per-stage timing, counts, and errors.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any


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

    def begin_stage(self, name: str) -> None:
        self._current_stage = StageTrace(name=name, started_at=time.time())

    def end_stage(self, meta: dict[str, Any] | None = None, error: str | None = None) -> None:
        if self._current_stage is None:
            return
        self._current_stage.ended_at = time.time()
        self._current_stage.duration_ms = int(
            (self._current_stage.ended_at - self._current_stage.started_at) * 1000
        )
        if meta:
            self._current_stage.meta = meta
        if error:
            self._current_stage.error = error
        self.stages.append(self._current_stage)
        self._current_stage = None

    def finalize(self, error: str | None = None) -> None:
        if self._current_stage:
            self.end_stage(error=error or "interrupted")
        self.ended_at = time.time()
        self.total_duration_ms = int((self.ended_at - self.started_at) * 1000)
        if error:
            self.error = error

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
        }
