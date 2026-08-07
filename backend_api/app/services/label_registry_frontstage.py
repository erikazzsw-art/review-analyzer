"""5.9.6-D WP6: Feature flag for formal label registry frontstage integration.

Three-state flag controlling how the active read/display path consumes
the 5.9.6-D resolver (decision m):

  off     完全走旧路径，resolver 不参与（默认，部署即此态）
  shadow   旧路径决定展示，同时调 resolver 并记录差异，不影响用户可见结果
  enforce  resolver 决定展示，旧路径只作为 fallback 日志

This module follows the existing flag convention from
customer_label_v2_frontstage.py and review_signal_frontstage.py.
"""
from __future__ import annotations

import contextvars
import json
import logging
import os
from collections.abc import Mapping
from dataclasses import asdict, dataclass
from typing import Any

logger = logging.getLogger(__name__)

LABEL_REGISTRY_FRONTSTAGE_CONFIG_SCHEMA_VERSION = "label-registry-frontstage-config.1"

MODE_OFF = "off"
MODE_SHADOW = "shadow"
MODE_ENFORCE = "enforce"
VALID_MODES = frozenset({MODE_OFF, MODE_SHADOW, MODE_ENFORCE})

_ENV_PREFIX = "LABEL_REGISTRY_FRONTSTAGE_"
_TRUTHY_CONFIG_VALUES = {"1", "true", "yes", "on", "enabled"}
_FALSY_CONFIG_VALUES = {"0", "false", "no", "off", "disabled"}

# Repair batch 1b (Bug 5/6): independent env switch for audit event persistence.
# Default OFF — shadow diffs are logged but NOT written to the DB until this
# is explicitly enabled. Writing to a table on the user read path (results page
# / export) must be opt-in so latency impact can be assessed first.
_AUDIT_PERSIST_ENV = "LABEL_REGISTRY_AUDIT_PERSIST"


def _is_audit_persist_enabled(env: Mapping[str, str] | None = None) -> bool:
    """Check whether audit event persistence is enabled."""
    env = env or os.environ
    raw = env.get(_AUDIT_PERSIST_ENV, "")
    return str(raw).strip().lower() in _TRUTHY_CONFIG_VALUES


@dataclass(frozen=True)
class LabelRegistryFrontstageFlag:
    """Feature flag controlling resolver integration into the active read path.

    mode: "off" | "shadow" | "enforce"
      off     — resolver not called; existing path unchanged (default)
      shadow  — existing path chooses what to display; resolver is called in
                parallel and differences are logged; user-visible output is
                identical to off mode
      enforce — resolver result determines display; existing path is fallback
                only (NOT delivered in WP6; reserved for 5.9.7+)
    """

    mode: str = MODE_OFF
    config_validation_errors: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)

    @property
    def is_off(self) -> bool:
        return self.mode == MODE_OFF

    @property
    def is_shadow(self) -> bool:
        return self.mode == MODE_SHADOW

    @property
    def is_enforce(self) -> bool:
        return self.mode == MODE_ENFORCE

    @property
    def resolver_active(self) -> bool:
        """True when the resolver should be called (shadow or enforce)."""
        return self.mode in (MODE_SHADOW, MODE_ENFORCE)


def _parse_mode(value: Any) -> tuple[str, list[str]]:
    """Parse mode value from env/config. Fail-closed: invalid → off."""
    if value is None:
        return MODE_OFF, []
    cleaned = str(value).strip().lower()
    if not cleaned:
        return MODE_OFF, []
    if cleaned in VALID_MODES:
        return cleaned, []
    return MODE_OFF, [f"mode:invalid:{cleaned}"]


def resolve_label_registry_frontstage_config(
    config: Mapping[str, Any] | None = None,
    *,
    source: str = "env",
) -> LabelRegistryFrontstageFlag:
    """Resolve the label registry frontstage flag from environment.

    Default is mode=off. Invalid mode values are fail-closed to off.
    """
    config = config or os.environ
    errors: list[str] = []

    env_name = f"{_ENV_PREFIX}MODE"
    raw = config.get(env_name)
    if raw is None and isinstance(config, Mapping):
        raw = config.get("mode")
    mode, parse_errors = _parse_mode(raw)
    errors.extend(parse_errors)

    if mode == MODE_ENFORCE:
        logger.warning(
            "label_registry_frontstage: enforce mode requested but not yet "
            "delivered in WP6 — falling back to shadow"
        )
        mode = MODE_SHADOW
        errors.append("mode:enforce_not_available")

    return LabelRegistryFrontstageFlag(
        mode=mode,
        config_validation_errors=tuple(dict.fromkeys(errors)),
    )


def label_registry_frontstage_flag_from_env(
    env: Mapping[str, str] | None = None,
) -> LabelRegistryFrontstageFlag:
    """Build the registry frontstage flag from environment configuration.

    Default is off. User-visible behaviour is unchanged when off.
    """
    return resolve_label_registry_frontstage_config(env, source="env")


def label_registry_frontstage_cache_key(
    flag: LabelRegistryFrontstageFlag | None = None,
) -> str:
    """Build a cache key segment that varies with the flag state.

    When off, this is a constant — cache entries are stable.
    When shadow/enforce, the mode appears in the key so cached
    results from off mode are not served to shadow mode callers.
    """
    effective = flag or label_registry_frontstage_flag_from_env()
    payload = effective.as_dict()
    return json.dumps(payload, sort_keys=True, default=str, separators=(",", ":"))


# ---------------------------------------------------------------------------
# Shadow diff recording (decision m)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ResolverShadowDiff:
    """A single diff entry recorded in shadow mode.

    Records one case where the resolver disagrees with (or would filter)
    the existing display path, so WP7 reflux has input data.
    """

    label_key: str
    sub_category: str
    category: str
    reject_reason: str  # ResolutionRejectReason value
    existing_display_label: str = ""
    context: str = ""  # free-text note (e.g. "would be removed from TOP10")


# Per-request shadow diff accumulator (repair batch 1b / Bug 6).
# ContextVar ensures isolation between concurrent requests. The previous
# module-level list mixed diffs from different tenants under concurrency.
_shadow_diffs: contextvars.ContextVar[list[ResolverShadowDiff] | None] = (
    contextvars.ContextVar("label_registry_shadow_diffs", default=None)
)


def _get_diffs() -> list[ResolverShadowDiff]:
    """Return the current request's diff list, initializing if needed."""
    diffs = _shadow_diffs.get()
    if diffs is None:
        diffs = []
        _shadow_diffs.set(diffs)
    return diffs


def record_shadow_diff(diff: ResolverShadowDiff) -> None:
    """Record a shadow diff for later inspection/logging."""
    _get_diffs().append(diff)


def collect_shadow_diffs() -> list[ResolverShadowDiff]:
    """Return all recorded shadow diffs for the current request."""
    diffs = _shadow_diffs.get()
    return list(diffs) if diffs else []


def clear_shadow_diffs() -> None:
    """Clear the shadow diff accumulator (call at request start)."""
    _shadow_diffs.set([])


def flush_shadow_diffs_to_log() -> list[ResolverShadowDiff]:
    """Log all accumulated shadow diffs, clear the accumulator, return diffs.

    Called at the end of a request to emit structured log entries that WP7
    reflux can consume. Returns the flushed diffs so callers can persist them
    to the audit table without a second read.

    Repair batch 1b (Bug 6): the return value is new. Previous version
    returned None, so callers had no way to get the diffs for audit
    persistence without re-reading the (now-cleared) accumulator.
    """
    diffs = _shadow_diffs.get()
    if not diffs:
        return []
    by_reason: dict[str, list[dict[str, str]]] = {}
    for diff in diffs:
        entry = {
            "label_key": diff.label_key,
            "sub_category": diff.sub_category,
            "category": diff.category,
            "existing_display_label": diff.existing_display_label,
            "context": diff.context,
        }
        by_reason.setdefault(diff.reject_reason, []).append(entry)

    logger.info(
        "label_registry_frontstage: shadow diffs count=%d breakdown=%s",
        len(diffs),
        {reason: len(items) for reason, items in by_reason.items()},
    )
    for reason, items in by_reason.items():
        for item in items[:5]:  # sample first 5 per reason to avoid log flood
            logger.debug(
                "label_registry_frontstage: shadow_diff reason=%s label=%s sub_category=%s",
                reason,
                item["label_key"],
                item["sub_category"],
            )
    _shadow_diffs.set([])
    return diffs


# ---------------------------------------------------------------------------
# Repair batch 1b: shadow → audit persistence middleware
# ---------------------------------------------------------------------------


def _persist_shadow_diffs_to_audit(
    diffs: list[ResolverShadowDiff],
) -> int:
    """Persist shadow diffs to label_registry_audit_events.

    Fail-open: DB errors are logged, never raised. Audit persistence is
    observational — losing a batch should not break the user request.

    Returns the number of successfully inserted rows.
    """
    if not diffs or not _is_audit_persist_enabled():
        return 0

    try:
        from backend_api.app.services.label_registry_audit import (
            AUDIT_EVENT_SHADOW_DIFF,
            AuditEvent,
            record_audit_events_batch,
        )

        events: list[AuditEvent] = []
        for diff in diffs:
            events.append(
                AuditEvent(
                    event_type=AUDIT_EVENT_SHADOW_DIFF,
                    label_key=diff.label_key,
                    sub_category=diff.sub_category,
                    category=diff.category,
                    reject_reason=diff.reject_reason,
                    existing_display_label=diff.existing_display_label,
                    context=diff.context,
                    source="shadow_middleware",
                )
            )
        inserted = record_audit_events_batch(events)
        if inserted < len(events):
            logger.warning(
                "label_registry_frontstage: audit persist batch: %d/%d inserted",
                inserted,
                len(events),
            )
        return inserted
    except Exception:
        logger.exception(
            "label_registry_frontstage: audit persist failed (%d diffs dropped)",
            len(diffs),
        )
        return 0


async def label_registry_shadow_middleware(request, call_next):
    """FastAPI middleware: clear shadow diffs at start, flush+persist at end.

    Only active when the frontstage mode is not 'off'. When mode='off',
    the resolver is never called so there are no diffs to flush, and we
    skip the overhead entirely.
    """
    flag = label_registry_frontstage_flag_from_env()
    if not flag.resolver_active:
        return await call_next(request)

    clear_shadow_diffs()
    try:
        response = await call_next(request)
    except Exception:
        # Flush even on error — diffs collected before the failure are
        # still valuable for debugging.
        diffs = flush_shadow_diffs_to_log()
        _persist_shadow_diffs_to_audit(diffs)
        raise

    diffs = flush_shadow_diffs_to_log()
    _persist_shadow_diffs_to_audit(diffs)
    return response
