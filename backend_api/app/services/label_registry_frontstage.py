"""5.9.6-D WP6 + 5.9.7-T3.A: Feature flag for formal label registry frontstage integration.

Three-state flag controlling how the active read/display path consumes
the 5.9.6-D resolver (decision m):

  off     完全走旧路径，resolver 不参与（默认，部署即此态）
  shadow   旧路径决定展示，同时调 resolver 并记录差异，不影响用户可见结果
  enforce  resolver 决定展示，旧路径只作为 fallback 日志

Scope support (5.9.7-T3.A): session / category / sub_category / category-sub_category
grained control copied from customer_label_v2_frontstage.py. Default: all off.

Priority: kill_switch > rollback > mode + scope
"""

from __future__ import annotations

import contextvars
import json
import logging
import os
import re
from collections.abc import Mapping
from dataclasses import asdict, dataclass
from typing import Any

logger = logging.getLogger(__name__)

LABEL_REGISTRY_FRONTSTAGE_CONFIG_SCHEMA_VERSION = "label-registry-frontstage-config.2"

MODE_OFF = "off"
MODE_SHADOW = "shadow"
MODE_ENFORCE = "enforce"
VALID_MODES = frozenset({MODE_OFF, MODE_SHADOW, MODE_ENFORCE})

_ENV_PREFIX = "LABEL_REGISTRY_FRONTSTAGE_"
_TRUTHY_CONFIG_VALUES = {"1", "true", "yes", "on", "enabled"}
_FALSY_CONFIG_VALUES = {"0", "false", "no", "off", "disabled"}

# Repair batch 1b (Bug 5/6): independent env switch for audit event persistence.
# Default OFF — shadow diffs are logged but NOT written to the DB until this
# is explicitly enabled.
_AUDIT_PERSIST_ENV = "LABEL_REGISTRY_AUDIT_PERSIST"

# ---------------------------------------------------------------------------
# Boolean config fields (env → dataclass field mapping)
# ---------------------------------------------------------------------------
_BOOL_CONFIG_FIELDS: dict[str, str] = {
    "rollback": "ROLLBACK",
    "kill_switch": "KILL_SWITCH",
}

# ---------------------------------------------------------------------------
# List config fields (env → dataclass field mapping)
# ---------------------------------------------------------------------------
_LIST_CONFIG_FIELDS: dict[str, str] = {
    "session_ids": "SESSION_IDS",
    "categories": "CATEGORIES",
    "sub_categories": "SUB_CATEGORIES",
    "category_sub_categories": "CATEGORY_SUB_CATEGORIES",
    "rollback_session_ids": "ROLLBACK_SESSION_IDS",
    "rollback_categories": "ROLLBACK_CATEGORIES",
    "rollback_sub_categories": "ROLLBACK_SUB_CATEGORIES",
    "rollback_category_sub_categories": "ROLLBACK_CATEGORY_SUB_CATEGORIES",
    "kill_switch_session_ids": "KILL_SWITCH_SESSION_IDS",
    "kill_switch_categories": "KILL_SWITCH_CATEGORIES",
    "kill_switch_sub_categories": "KILL_SWITCH_SUB_CATEGORIES",
    "kill_switch_category_sub_categories": "KILL_SWITCH_CATEGORY_SUB_CATEGORIES",
}


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
                only

    Scope fields (session/category/sub_category/category-sub_category):
      Empty = no scope restriction (global). When populated, only matching
      reviews get the resolver.

    kill_switch: global + scoped. Takes precedence over everything.
    rollback: global + scoped. Takes precedence over mode.
    """

    mode: str = MODE_OFF
    session_ids: tuple[str, ...] = ()
    categories: tuple[str, ...] = ()
    sub_categories: tuple[str, ...] = ()
    category_sub_categories: tuple[str, ...] = ()
    rollback: bool = False
    rollback_session_ids: tuple[str, ...] = ()
    rollback_categories: tuple[str, ...] = ()
    rollback_sub_categories: tuple[str, ...] = ()
    rollback_category_sub_categories: tuple[str, ...] = ()
    kill_switch: bool = False
    kill_switch_session_ids: tuple[str, ...] = ()
    kill_switch_categories: tuple[str, ...] = ()
    kill_switch_sub_categories: tuple[str, ...] = ()
    kill_switch_category_sub_categories: tuple[str, ...] = ()
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
        """True when the resolver should be called (shadow or enforce).

        NOTE: This is a *global* check that does not consider scope.
        For per-review scope-aware decisions, use effective_mode_for().
        """
        return self.mode in (MODE_SHADOW, MODE_ENFORCE)


# ---------------------------------------------------------------------------
# Config parsing (copied from customer_label_v2_frontstage.py)
# ---------------------------------------------------------------------------


def _config_value(config: Mapping[str, Any], logical_name: str, env_suffix: str) -> Any:
    """Look up a config value by logical name first, then by env name."""
    if logical_name in config:
        return config.get(logical_name)
    env_name = f"{_ENV_PREFIX}{env_suffix}"
    if env_name in config:
        return config.get(env_name)
    return None


def _parse_config_bool(
    value: Any, *, field_name: str, default: bool = False
) -> tuple[bool, list[str]]:
    """Parse a boolean config value. Fail-closed: invalid → default."""
    if value is None:
        return default, []
    if isinstance(value, bool):
        return value, []
    cleaned = str(value).strip().lower()
    if not cleaned:
        return default, []
    if cleaned in _TRUTHY_CONFIG_VALUES:
        return True, []
    if cleaned in _FALSY_CONFIG_VALUES:
        return False, []
    return False, [f"{field_name}:invalid_bool"]


def _parse_config_values(
    value: Any, *, field_name: str
) -> tuple[tuple[str, ...], list[str]]:
    """Parse a comma-separated or list config value."""
    if value is None:
        return (), []
    if isinstance(value, str):
        parts = [item.strip() for item in value.split(",")]
    elif isinstance(value, (list, tuple, set)):
        parts = [str(item).strip() for item in value]
    else:
        return (), [f"{field_name}:invalid_list"]

    values = tuple(item for item in parts if item)
    if not values and any(part == "" for part in parts):
        return (), []
    return values, []


def _normalize_key(value: Any) -> str:
    """Normalize a scope key for comparison."""
    value = str(value or "").strip().lower().replace("&", " and ")
    value = re.sub(r"[^a-z0-9]+", "_", value)
    return re.sub(r"_+", "_", value).strip("_")


def _validate_scope_values(
    values: tuple[Any, ...], *, field_name: str, require_pair: bool = False
) -> list[str]:
    """Validate scope values."""
    errors: list[str] = []
    for value in values:
        cleaned = str(value or "").strip()
        if not cleaned:
            continue
        if require_pair:
            if "/" not in cleaned:
                errors.append(f"{field_name}:invalid_category_sub_category:{cleaned}")
                continue
            left, right = cleaned.split("/", 1)
            if not _normalize_key(left) or not _normalize_key(right):
                errors.append(f"{field_name}:invalid_category_sub_category:{cleaned}")
        elif not _normalize_key(cleaned):
            errors.append(f"{field_name}:invalid_scope:{cleaned}")
    return errors


def _validate_flag(flag: LabelRegistryFrontstageFlag) -> list[str]:
    """Validate the flag configuration."""
    errors: list[str] = []

    # Validate mode
    if flag.mode not in VALID_MODES:
        errors.append(f"mode:invalid:{flag.mode}")

    # Validate scope values
    for field_name in (
        "category_sub_categories",
        "rollback_category_sub_categories",
        "kill_switch_category_sub_categories",
    ):
        errors.extend(
            _validate_scope_values(
                getattr(flag, field_name), field_name=field_name, require_pair=True
            )
        )
    for field_name in (
        "categories",
        "sub_categories",
        "rollback_categories",
        "rollback_sub_categories",
        "kill_switch_categories",
        "kill_switch_sub_categories",
    ):
        errors.extend(
            _validate_scope_values(getattr(flag, field_name), field_name=field_name)
        )

    return errors


# ---------------------------------------------------------------------------
# Flag resolution from environment
# ---------------------------------------------------------------------------


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

    Default is mode=off, all scopes empty, kill_switch/rollback off.
    Invalid values are fail-closed.
    """
    config = config or os.environ
    errors: list[str] = []

    # --- mode ---
    env_name = f"{_ENV_PREFIX}MODE"
    raw = config.get(env_name)
    if raw is None and isinstance(config, Mapping):
        raw = config.get("mode")
    mode, parse_errors = _parse_mode(raw)
    errors.extend(parse_errors)

    # 5.9.7-T3.B: enforce mode is now delivered.
    # No fallback — enforce passes through to callers who filter display.

    # --- boolean fields ---
    bool_values: dict[str, bool] = {}
    for logical_name, env_suffix in _BOOL_CONFIG_FIELDS.items():
        parsed, parse_errors = _parse_config_bool(
            _config_value(config, logical_name, env_suffix),
            field_name=logical_name,
            default=False,
        )
        bool_values[logical_name] = parsed
        errors.extend(parse_errors)

    # --- list fields ---
    list_values: dict[str, tuple[str, ...]] = {}
    for logical_name, env_suffix in _LIST_CONFIG_FIELDS.items():
        values, parse_errors = _parse_config_values(
            _config_value(config, logical_name, env_suffix),
            field_name=logical_name,
        )
        list_values[logical_name] = values
        errors.extend(parse_errors)

    flag = LabelRegistryFrontstageFlag(
        mode=mode,
        session_ids=list_values["session_ids"],
        categories=list_values["categories"],
        sub_categories=list_values["sub_categories"],
        category_sub_categories=list_values["category_sub_categories"],
        rollback=bool_values["rollback"],
        rollback_session_ids=list_values["rollback_session_ids"],
        rollback_categories=list_values["rollback_categories"],
        rollback_sub_categories=list_values["rollback_sub_categories"],
        rollback_category_sub_categories=list_values["rollback_category_sub_categories"],
        kill_switch=bool_values["kill_switch"],
        kill_switch_session_ids=list_values["kill_switch_session_ids"],
        kill_switch_categories=list_values["kill_switch_categories"],
        kill_switch_sub_categories=list_values["kill_switch_sub_categories"],
        kill_switch_category_sub_categories=list_values["kill_switch_category_sub_categories"],
    )

    # --- validate ---
    errors.extend(_validate_flag(flag))
    validation_errors = tuple(dict.fromkeys(errors))

    if validation_errors:
        # Fail-closed: invalid config → off
        return LabelRegistryFrontstageFlag(
            mode=MODE_OFF,
            config_validation_errors=validation_errors,
        )

    return LabelRegistryFrontstageFlag(
        mode=flag.mode,
        session_ids=flag.session_ids,
        categories=flag.categories,
        sub_categories=flag.sub_categories,
        category_sub_categories=flag.category_sub_categories,
        rollback=flag.rollback,
        rollback_session_ids=flag.rollback_session_ids,
        rollback_categories=flag.rollback_categories,
        rollback_sub_categories=flag.rollback_sub_categories,
        rollback_category_sub_categories=flag.rollback_category_sub_categories,
        kill_switch=flag.kill_switch,
        kill_switch_session_ids=flag.kill_switch_session_ids,
        kill_switch_categories=flag.kill_switch_categories,
        kill_switch_sub_categories=flag.kill_switch_sub_categories,
        kill_switch_category_sub_categories=flag.kill_switch_category_sub_categories,
        config_validation_errors=validation_errors,
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
# Scope matching (copied from customer_label_v2_frontstage.py)
# ---------------------------------------------------------------------------


def _normalized_scope_values(values: tuple[Any, ...]) -> set[str]:
    """Normalize a tuple of scope values into a set for matching."""
    return {_normalize_key(value) for value in values if _normalize_key(value)}


def _normalized_pair_values(values: tuple[Any, ...]) -> set[str]:
    """Normalize category/sub_category pair values."""
    pairs: set[str] = set()
    for value in values:
        cleaned = str(value or "").strip().lower()
        if not cleaned:
            continue
        if "/" in cleaned:
            left, right = cleaned.split("/", 1)
            pair = f"{_normalize_key(left)}/{_normalize_key(right)}"
            if pair != "/":
                pairs.add(pair)
            continue
        normalized = _normalize_key(cleaned)
        if normalized:
            pairs.add(normalized)
    return pairs


def _scope_match(
    *,
    session_id: str,
    category: str,
    sub_category: str,
    category_sub_category: str,
    session_ids: tuple[Any, ...],
    categories: tuple[str, ...],
    sub_categories: tuple[str, ...],
    category_sub_categories: tuple[str, ...],
) -> str | None:
    """Check if a review context matches any scope entry.

    Returns the matched scope type (session/category/sub_category/category_sub_category)
    or None if no match.
    """
    session_values = {
        str(value).strip() for value in session_ids if str(value).strip()
    }
    if session_id and session_id in session_values:
        return "session"
    if category and category in _normalized_scope_values(categories):
        return "category"
    sub_category_values = _normalized_pair_values(sub_categories)
    if sub_category and sub_category in sub_category_values:
        return "sub_category"
    if category_sub_category and category_sub_category in sub_category_values:
        return "sub_category"
    if (
        category_sub_category
        and category_sub_category in _normalized_pair_values(category_sub_categories)
    ):
        return "category_sub_category"
    return None


def effective_mode_for(
    flag: LabelRegistryFrontstageFlag,
    *,
    session_id: str = "",
    category: str = "",
    sub_category: str = "",
) -> str:
    """Return the effective mode (off/shadow/enforce) for a given review context.

    Priority: config_invalid > kill_switch > rollback > mode + scope.

    When the flag has no scope configured, mode applies globally.
    When scopes are configured, only matching reviews get the resolver.
    """
    # 1. Config invalid → off
    if flag.config_validation_errors:
        return MODE_OFF

    # 2. Kill switch global → off
    if flag.kill_switch:
        return MODE_OFF

    # 3. Kill switch scoped → off
    if _scope_match(
        session_id=session_id,
        category=category,
        sub_category=sub_category,
        category_sub_category=f"{category}/{sub_category}",
        session_ids=flag.kill_switch_session_ids,
        categories=flag.kill_switch_categories,
        sub_categories=flag.kill_switch_sub_categories,
        category_sub_categories=flag.kill_switch_category_sub_categories,
    ):
        return MODE_OFF

    # 4. Rollback global → off
    if flag.rollback:
        return MODE_OFF

    # 5. Rollback scoped → off
    if _scope_match(
        session_id=session_id,
        category=category,
        sub_category=sub_category,
        category_sub_category=f"{category}/{sub_category}",
        session_ids=flag.rollback_session_ids,
        categories=flag.rollback_categories,
        sub_categories=flag.rollback_sub_categories,
        category_sub_categories=flag.rollback_category_sub_categories,
    ):
        return MODE_OFF

    # 6. Mode is off → off
    if flag.mode == MODE_OFF:
        return MODE_OFF

    # 7. Mode is shadow/enforce — check scope
    has_scopes = any(
        (
            flag.session_ids,
            flag.categories,
            flag.sub_categories,
            flag.category_sub_categories,
        )
    )
    if not has_scopes:
        # No scope restriction → global
        return flag.mode

    matched = _scope_match(
        session_id=session_id,
        category=category,
        sub_category=sub_category,
        category_sub_category=f"{category}/{sub_category}",
        session_ids=flag.session_ids,
        categories=flag.categories,
        sub_categories=flag.sub_categories,
        category_sub_categories=flag.category_sub_categories,
    )
    if matched:
        return flag.mode

    return MODE_OFF


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
    """Log all accumulated shadow diffs, clear the accumulator, return diffs."""
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

    Fail-open: DB errors are logged, never raised.
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
        diffs = flush_shadow_diffs_to_log()
        _persist_shadow_diffs_to_audit(diffs)
        raise

    diffs = flush_shadow_diffs_to_log()
    _persist_shadow_diffs_to_audit(diffs)
    return response
