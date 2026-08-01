from __future__ import annotations

import copy
import json
import os
import re
from collections import Counter
from collections.abc import Mapping
from dataclasses import asdict, dataclass
from typing import Any

from backend_api.app.services.review_signal_shadow import (
    PRODUCT_SIGNAL_TYPES,
    ROUTE_AUDIT_FILTER,
    ROUTE_CONSUMER_PROFILE,
    ROUTE_CUSTOMER_ISSUE_CANDIDATE,
    ROUTE_CUSTOMER_LABEL_CANDIDATE,
    ROUTE_PURCHASE_MOTIVES,
    ROUTE_UNMET_NEEDS,
    SIGNAL_AUDIT_ONLY,
    SIGNAL_PRODUCT_NEGATIVE,
    SIGNAL_PRODUCT_POSITIVE,
    review_signal_shadow_safety_flags,
)

REVIEW_SIGNAL_FRONTSTAGE_READ_PATH_SCHEMA_VERSION = "review-signal-frontstage-read-path.1"
REVIEW_SIGNAL_FRONTSTAGE_CONFIG_SCHEMA_VERSION = "review-signal-frontstage-config.1"
REVIEW_SIGNAL_FRONTSTAGE_OBSERVABILITY_SCHEMA_VERSION = "review-signal-frontstage-observability.1"
REVIEW_SIGNAL_PHASE4_IMPLEMENTATION_SCHEMA_VERSION = "review-signal-phase4-implementation.1"

REVIEW_SIGNAL_STORED_SHADOW_FIELD = "review_signal_stored_shadow"
REVIEW_SIGNAL_FRONTSTAGE_READ_MODEL_FIELD = "review_signal_frontstage_read_model"
LOCAL_TEST_CUSTOMER_LABEL_V2_READ_MODEL_FIELD = "customer_label_v2_frontstage_read_model"

READ_PATH_V1_CURRENT = "v1_current"
READ_PATH_REVIEW_SIGNAL_STORED_SHADOW = "review_signal_stored_shadow"
LOCAL_TEST_ADAPTER_READ_PATH = "v2_shadow"
PRODUCTION_FRONTSTAGE_ALLOWED_SUB_CATEGORIES = ("waders",)

FRONTSTAGE_CONSUMERS = (
    "results_top10",
    "single_review_detail",
    "raw_review_export",
    "single_tag_download",
)

_ENV_PREFIX = "REVIEW_SIGNAL_FRONTSTAGE_"
_TRUTHY_CONFIG_VALUES = {"1", "true", "yes", "on", "enabled"}
_FALSY_CONFIG_VALUES = {"0", "false", "no", "off", "disabled"}
_BOOL_CONFIG_FIELDS = {
    "enabled": "ENABLED",
    "rollback": "ROLLBACK",
    "kill_switch": "KILL_SWITCH",
    "runtime_shadow_generation_allowed": "RUNTIME_SHADOW_GENERATION_ALLOWED",
}
_LIST_CONFIG_FIELDS = {
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


@dataclass(frozen=True)
class ReviewSignalFrontstageFlag:
    enabled: bool = False
    session_ids: tuple[Any, ...] = ()
    categories: tuple[str, ...] = ()
    sub_categories: tuple[str, ...] = ()
    category_sub_categories: tuple[str, ...] = ()
    rollback: bool = False
    rollback_session_ids: tuple[Any, ...] = ()
    rollback_categories: tuple[str, ...] = ()
    rollback_sub_categories: tuple[str, ...] = ()
    rollback_category_sub_categories: tuple[str, ...] = ()
    kill_switch: bool = False
    kill_switch_session_ids: tuple[Any, ...] = ()
    kill_switch_categories: tuple[str, ...] = ()
    kill_switch_sub_categories: tuple[str, ...] = ()
    kill_switch_category_sub_categories: tuple[str, ...] = ()
    runtime_shadow_generation_allowed: bool = False
    config_validation_errors: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ReviewSignalFrontstageConfigResolution:
    schema_version: str
    source: str
    valid: bool
    fail_closed: bool
    validation_errors: tuple[str, ...]
    raw_feature_flag: ReviewSignalFrontstageFlag
    effective_feature_flag: ReviewSignalFrontstageFlag

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def _normalize_key(value: Any) -> str:
    value = str(value or "").strip().lower().replace("&", " and ")
    value = re.sub(r"[^a-z0-9]+", "_", value)
    return re.sub(r"_+", "_", value).strip("_")


def _parse_config_bool(value: Any, *, field_name: str, default: bool = False) -> tuple[bool, list[str]]:
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


def _parse_config_values(value: Any, *, field_name: str) -> tuple[tuple[str, ...], list[str]]:
    if value is None:
        return (), []
    if isinstance(value, str):
        parts = [item.strip() for item in value.split(",")]
    elif isinstance(value, (list, tuple, set)):
        parts = [str(item).strip() for item in value]
    else:
        return (), [f"{field_name}:invalid_list"]
    return tuple(item for item in parts if item), []


def _config_value(config: Mapping[str, Any], logical_name: str, env_suffix: str) -> Any:
    if logical_name in config:
        return config.get(logical_name)
    env_name = f"{_ENV_PREFIX}{env_suffix}"
    if env_name in config:
        return config.get(env_name)
    return None


def _validate_scope_values(values: tuple[Any, ...], *, field_name: str, require_pair: bool = False) -> list[str]:
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
        elif not _normalize_key(cleaned) and not field_name.endswith("session_ids"):
            errors.append(f"{field_name}:invalid_scope:{cleaned}")
    return errors


def _validate_frontstage_flag(flag: ReviewSignalFrontstageFlag) -> list[str]:
    errors: list[str] = []
    if flag.runtime_shadow_generation_allowed:
        errors.append("runtime_shadow_generation_allowed:not_supported")
    for field_name in (
        "category_sub_categories",
        "rollback_category_sub_categories",
        "kill_switch_category_sub_categories",
    ):
        errors.extend(_validate_scope_values(getattr(flag, field_name), field_name=field_name, require_pair=True))
    for field_name in (
        "categories",
        "sub_categories",
        "rollback_categories",
        "rollback_sub_categories",
        "kill_switch_categories",
        "kill_switch_sub_categories",
    ):
        errors.extend(_validate_scope_values(getattr(flag, field_name), field_name=field_name))
    return errors


def resolve_review_signal_frontstage_config(
    config: Mapping[str, Any] | None = None,
    *,
    source: str = "env",
) -> ReviewSignalFrontstageConfigResolution:
    config = config or os.environ
    errors: list[str] = []
    bool_values: dict[str, bool] = {}
    list_values: dict[str, tuple[str, ...]] = {}

    for logical_name, env_suffix in _BOOL_CONFIG_FIELDS.items():
        parsed, parse_errors = _parse_config_bool(
            _config_value(config, logical_name, env_suffix),
            field_name=logical_name,
            default=False,
        )
        bool_values[logical_name] = parsed
        errors.extend(parse_errors)

    for logical_name, env_suffix in _LIST_CONFIG_FIELDS.items():
        values, parse_errors = _parse_config_values(
            _config_value(config, logical_name, env_suffix),
            field_name=logical_name,
        )
        list_values[logical_name] = values
        errors.extend(parse_errors)

    raw_flag = ReviewSignalFrontstageFlag(
        enabled=bool_values["enabled"],
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
        runtime_shadow_generation_allowed=bool_values["runtime_shadow_generation_allowed"],
    )
    errors.extend(_validate_frontstage_flag(raw_flag))
    validation_errors = tuple(dict.fromkeys(errors))
    effective_flag = raw_flag
    if validation_errors:
        effective_flag = ReviewSignalFrontstageFlag(config_validation_errors=validation_errors)

    return ReviewSignalFrontstageConfigResolution(
        schema_version=REVIEW_SIGNAL_FRONTSTAGE_CONFIG_SCHEMA_VERSION,
        source=source,
        valid=not validation_errors,
        fail_closed=bool(validation_errors),
        validation_errors=validation_errors,
        raw_feature_flag=raw_flag,
        effective_feature_flag=effective_flag,
    )


def review_signal_frontstage_flag_from_env(env: Mapping[str, str] | None = None) -> ReviewSignalFrontstageFlag:
    return resolve_review_signal_frontstage_config(env, source="env").effective_feature_flag


def review_signal_frontstage_cache_key(flag: ReviewSignalFrontstageFlag | None = None) -> str:
    payload = (flag or review_signal_frontstage_flag_from_env()).as_dict()
    return json.dumps(payload, sort_keys=True, default=str, separators=(",", ":"))


def _session_id_for_review(review: dict[str, Any]) -> str:
    for field in ("session_id", "analysis_session_id", "upload_session_id"):
        value = review.get(field)
        if value is not None and str(value).strip():
            return str(value).strip()
    return ""


def _scope_context(review: dict[str, Any]) -> dict[str, str]:
    category = _normalize_key(review.get("category")) or "unknown"
    sub_category = _normalize_key(review.get("sub_category")) or "unknown"
    return {
        "session_id": _session_id_for_review(review),
        "category": category,
        "sub_category": sub_category,
        "category_sub_category": f"{category}/{sub_category}",
    }


def _production_frontstage_scope_allowed(review: dict[str, Any], flag: ReviewSignalFrontstageFlag) -> bool:
    context = _scope_context(review)
    session_values = {str(value).strip() for value in flag.session_ids if str(value).strip()}
    return bool(
        context["session_id"]
        and context["session_id"] in session_values
        and context["sub_category"] in set(PRODUCTION_FRONTSTAGE_ALLOWED_SUB_CATEGORIES)
    )


def _normalized_scope_values(values: tuple[Any, ...]) -> set[str]:
    return {_normalize_key(value) for value in values if _normalize_key(value)}


def _normalized_pair_values(values: tuple[Any, ...]) -> set[str]:
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
    session_values = {str(value).strip() for value in session_ids if str(value).strip()}
    if session_id and session_id in session_values:
        return "session"
    if category and category in _normalized_scope_values(categories):
        return "category"
    sub_category_values = _normalized_pair_values(sub_categories)
    if sub_category and sub_category in sub_category_values:
        return "sub_category"
    if category_sub_category and category_sub_category in sub_category_values:
        return "sub_category"
    if category_sub_category and category_sub_category in _normalized_pair_values(category_sub_categories):
        return "category_sub_category"
    return None


def _flag_match_decision(flag: ReviewSignalFrontstageFlag, review: dict[str, Any]) -> dict[str, Any]:
    context = _scope_context(review)
    if flag.config_validation_errors:
        return {
            **context,
            "review_signal_requested": False,
            "matched_scope": "none",
            "rollback_active": False,
            "kill_switch_active": False,
            "reason": "config_invalid",
            "config_validation_errors": list(flag.config_validation_errors),
        }

    if flag.kill_switch:
        return {
            **context,
            "review_signal_requested": False,
            "matched_scope": "kill_switch_global",
            "rollback_active": False,
            "kill_switch_active": True,
            "reason": "kill_switch_global",
        }

    kill_switch_scope = _scope_match(
        session_id=context["session_id"],
        category=context["category"],
        sub_category=context["sub_category"],
        category_sub_category=context["category_sub_category"],
        session_ids=flag.kill_switch_session_ids,
        categories=flag.kill_switch_categories,
        sub_categories=flag.kill_switch_sub_categories,
        category_sub_categories=flag.kill_switch_category_sub_categories,
    )
    if kill_switch_scope:
        return {
            **context,
            "review_signal_requested": False,
            "matched_scope": f"kill_switch_{kill_switch_scope}",
            "rollback_active": False,
            "kill_switch_active": True,
            "reason": f"kill_switch_{kill_switch_scope}",
        }

    if flag.rollback:
        return {
            **context,
            "review_signal_requested": False,
            "matched_scope": "rollback_global",
            "rollback_active": True,
            "kill_switch_active": False,
            "reason": "rollback_global",
        }

    rollback_scope = _scope_match(
        session_id=context["session_id"],
        category=context["category"],
        sub_category=context["sub_category"],
        category_sub_category=context["category_sub_category"],
        session_ids=flag.rollback_session_ids,
        categories=flag.rollback_categories,
        sub_categories=flag.rollback_sub_categories,
        category_sub_categories=flag.rollback_category_sub_categories,
    )
    if rollback_scope:
        return {
            **context,
            "review_signal_requested": False,
            "matched_scope": f"rollback_{rollback_scope}",
            "rollback_active": True,
            "kill_switch_active": False,
            "reason": f"rollback_{rollback_scope}",
        }

    if not flag.enabled:
        return {
            **context,
            "review_signal_requested": False,
            "matched_scope": "none",
            "rollback_active": False,
            "kill_switch_active": False,
            "reason": "flag_off",
        }

    has_scopes = any(
        (
            flag.session_ids,
            flag.categories,
            flag.sub_categories,
            flag.category_sub_categories,
        )
    )
    if not has_scopes:
        return {
            **context,
            "review_signal_requested": False,
            "matched_scope": "none",
            "rollback_active": False,
            "kill_switch_active": False,
            "reason": "scope_not_matched",
        }

    matched_scope = _scope_match(
        session_id=context["session_id"],
        category=context["category"],
        sub_category=context["sub_category"],
        category_sub_category=context["category_sub_category"],
        session_ids=flag.session_ids,
        categories=flag.categories,
        sub_categories=flag.sub_categories,
        category_sub_categories=flag.category_sub_categories,
    )
    return {
        **context,
        "review_signal_requested": bool(matched_scope),
        "matched_scope": matched_scope or "none",
        "rollback_active": False,
        "kill_switch_active": False,
        "reason": f"flag_on_{matched_scope}" if matched_scope else "scope_not_matched",
    }


def _coerce_aspects_json(value: Any) -> dict[str, Any] | None:
    if isinstance(value, dict):
        return value
    if isinstance(value, str) and value.strip():
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return None
        return parsed if isinstance(parsed, dict) else None
    return None


def _stored_shadow_for_review(review: dict[str, Any]) -> dict[str, Any] | None:
    for field in (
        REVIEW_SIGNAL_STORED_SHADOW_FIELD,
        "review_signal_frontstage_stored_shadow",
        "review_signal_shadow_result",
    ):
        stored = review.get(field)
        if isinstance(stored, dict):
            return stored
    aspects_json = _coerce_aspects_json(review.get("aspects_json"))
    if not aspects_json:
        return None
    for field in (
        REVIEW_SIGNAL_STORED_SHADOW_FIELD,
        "review_signal_frontstage_stored_shadow",
        "review_signal_shadow_result",
    ):
        stored = aspects_json.get(field)
        if isinstance(stored, dict):
            return stored
    return None


def _locate_evidence(content: str, evidence_span: str) -> tuple[int, int, bool]:
    evidence = str(evidence_span or "").strip()
    if not evidence or not content:
        return -1, -1, False
    start = content.find(evidence)
    if start < 0:
        start = content.lower().find(evidence.lower())
    if start < 0:
        return -1, -1, False
    return start, start + len(evidence), True


def _normalize_label_type(value: Any) -> str:
    label_type = str(value or "").strip().lower()
    if label_type in {"issue", "customer_issue"}:
        return "issue"
    if label_type in {"label", "highlight", "customer_label", "customer_highlight"}:
        return "highlight"
    return ""


def _normalize_route_to(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value] if value else []
    if isinstance(value, (list, tuple, set)):
        return [str(route or "").strip() for route in value if str(route or "").strip()]
    return []


def _candidate_occurrences_from_stored_shadow(stored_shadow: dict[str, Any]) -> list[dict[str, Any]]:
    for field in ("frontstage_occurrences", "display_occurrences", "selected_occurrences", "occurrences"):
        occurrences = stored_shadow.get(field)
        if isinstance(occurrences, list):
            return [copy.deepcopy(item) for item in occurrences if isinstance(item, dict)]

    candidates: list[dict[str, Any]] = []
    issue_candidates = stored_shadow.get("signal_derived_customer_issue_candidates")
    label_candidates = stored_shadow.get("signal_derived_customer_label_candidates")
    if isinstance(issue_candidates, list):
        for item in issue_candidates:
            if isinstance(item, dict):
                candidates.append({**copy.deepcopy(item), "label_type": item.get("label_type") or "issue"})
    if isinstance(label_candidates, list):
        for item in label_candidates:
            if isinstance(item, dict):
                candidates.append({**copy.deepcopy(item), "label_type": item.get("label_type") or "highlight"})
    return candidates


def _display_label_for_occurrence(occurrence: dict[str, Any], canonical: str) -> str:
    display = str(
        occurrence.get("display_label_en")
        or occurrence.get("label")
        or occurrence.get("raw_label")
        or occurrence.get("specific_issue")
        or occurrence.get("customer_highlight")
        or ""
    ).strip()
    if display:
        return display
    return " ".join(part.capitalize() for part in canonical.split("_"))


def _mapping_status_blocks(occurrence: dict[str, Any], canonical: str) -> bool:
    status = str(
        occurrence.get("mapping_status")
        or occurrence.get("mapping_review_status")
        or occurrence.get("canonical_mapping_status")
        or ""
    ).strip()
    if not canonical:
        return True
    if not status:
        return False
    return status not in {"mapped", "approved", "approved_canonical", "map_to_existing_canonical"}


def _display_gate_blocks(
    occurrence: dict[str, Any],
    *,
    content: str,
    evidence_span: str,
) -> tuple[bool, int, int, bool]:
    start, end, located = _locate_evidence(content, evidence_span)
    explicit_evidence_verified = occurrence.get("evidence_verified", occurrence.get("verified_evidence"))
    evidence_verified = bool(explicit_evidence_verified) if explicit_evidence_verified is not None else located
    if occurrence.get("display_allowed", True) is False:
        return True, start, end, evidence_verified
    if occurrence.get("source_review_allowed", True) is False:
        return True, start, end, evidence_verified
    if not evidence_span or not located or not evidence_verified:
        return True, start, end, evidence_verified
    if occurrence.get("cluster_propagated", False) is True:
        return True, start, end, evidence_verified
    if occurrence.get("legacy_fallback", False) is True:
        return True, start, end, evidence_verified
    if occurrence.get("aspect_allowed", True) is False:
        return True, start, end, evidence_verified
    if occurrence.get("context_allowed", True) is False:
        return True, start, end, evidence_verified
    if occurrence.get("maturity_allowed", True) is False:
        return True, start, end, evidence_verified
    return False, start, end, evidence_verified


_NEGATED_BREATHABLE_PATTERNS = [
    r"\bnot\s+(?:very\s+|the\s+most\s+)?breathable\b",
    r"\b(?:do|does|did|don['’]?t|doesn['’]?t|didn['’]?t|cannot|can['’]?t)\s+(?:not\s+)?breath(?:e|es|ed|ing)?\b",
    r"\b(?:isn['’]?t|aren['’]?t|wasn['’]?t|weren['’]?t)\s+(?:very\s+|the\s+most\s+)?breathable\b",
    r"\b(?:less|least)\s+breathable\b",
]

_POSITIVE_BREATHABLE_PATTERNS = [
    r"\b(?:very|really|super|so|quite|pretty|extremely|highly)\s+breathable\b",
    r"\b(?:is|are|was|were|be|being)\s+(?:very\s+|really\s+|super\s+|so\s+|quite\s+|pretty\s+|extremely\s+|highly\s+)?breathable\b",
    r"\bbreathable\s+(?:due\s+to|because|since|and)\b",
]


def _is_positive_breathable_evidence(evidence_span: str, content: str) -> bool:
    evidence = str(evidence_span or "").strip()
    if not evidence:
        return False
    context = evidence
    if content:
        start, end, located = _locate_evidence(content, evidence)
        if located:
            left = (
                max(
                    content.rfind(".", 0, start),
                    content.rfind("!", 0, start),
                    content.rfind("?", 0, start),
                    content.rfind("\n", 0, start),
                )
                + 1
            )
            right_candidates = [
                index
                for index in (
                    content.find(".", end),
                    content.find("!", end),
                    content.find("?", end),
                    content.find("\n", end),
                )
                if index >= 0
            ]
            right = min(right_candidates) if right_candidates else len(content)
            context = content[left:right]
    if not re.search(r"\bbreath(?:able|e|es|ed|ing)\b", context, re.IGNORECASE):
        return False
    if any(re.search(pattern, context, re.IGNORECASE) for pattern in _NEGATED_BREATHABLE_PATTERNS):
        return False
    return any(re.search(pattern, context, re.IGNORECASE) for pattern in _POSITIVE_BREATHABLE_PATTERNS)


def _review_signal_route_gate_reasons(
    *,
    label_type: str,
    signal_type: str,
    route_to: list[str],
    occurrence: dict[str, Any],
    canonical: str = "",
    evidence_span: str = "",
    content: str = "",
) -> list[str]:
    reasons: list[str] = []
    if signal_type not in PRODUCT_SIGNAL_TYPES:
        reasons.append("blocked_by_non_product_signal")
    if (
        signal_type == SIGNAL_AUDIT_ONLY
        or occurrence.get("audit_only") is True
        or occurrence.get("route") == ROUTE_AUDIT_FILTER
        or route_to == [ROUTE_AUDIT_FILTER]
        or str(occurrence.get("action") or "") == "keep_audit_only"
    ):
        reasons.append("blocked_by_audit_only")
    if label_type == "issue":
        if signal_type != SIGNAL_PRODUCT_NEGATIVE or ROUTE_CUSTOMER_ISSUE_CANDIDATE not in route_to:
            reasons.append("blocked_by_display_gate")
    elif label_type == "highlight":
        if signal_type != SIGNAL_PRODUCT_POSITIVE or ROUTE_CUSTOMER_LABEL_CANDIDATE not in route_to:
            reasons.append("blocked_by_display_gate")
    else:
        reasons.append("blocked_by_display_gate")
    if label_type == "issue" and canonical == "not_breathable" and _is_positive_breathable_evidence(
        evidence_span,
        content,
    ):
        reasons.append("blocked_by_semantic_polarity")
    return reasons


def _normalize_frontstage_occurrence(
    occurrence: dict[str, Any],
    *,
    review: dict[str, Any],
    locale: str,
) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    content = str(review.get("content") or "")
    label_type = _normalize_label_type(occurrence.get("label_type") or occurrence.get("expected_label_type"))
    canonical = str(
        occurrence.get("canonical_label_key")
        or occurrence.get("expected_canonical_label_key")
        or occurrence.get("canonical_issue_key")
        or occurrence.get("canonical_highlight_key")
        or ""
    ).strip()
    signal_type = str(occurrence.get("signal_type") or occurrence.get("expected_signal_type") or "").strip()
    evidence_span = str(occurrence.get("evidence_span") or occurrence.get("evidence_candidate") or "").strip()
    route_to = _normalize_route_to(occurrence.get("route_to") or occurrence.get("expected_route_to"))
    route_reasons = _review_signal_route_gate_reasons(
        label_type=label_type,
        signal_type=signal_type,
        route_to=route_to,
        occurrence=occurrence,
        canonical=canonical,
        evidence_span=evidence_span,
        content=content,
    )
    display_blocks, start, end, evidence_verified = _display_gate_blocks(
        occurrence,
        content=content,
        evidence_span=evidence_span,
    )
    blocked_reasons = list(route_reasons)
    if canonical.startswith("candidate:"):
        blocked_reasons.append("blocked_by_candidate_key")
    elif _mapping_status_blocks(occurrence, canonical):
        blocked_reasons.append("blocked_by_mapping_unresolved")
    if display_blocks:
        blocked_reasons.append("blocked_by_display_gate")

    blocked_reasons = list(dict.fromkeys(blocked_reasons))
    if blocked_reasons:
        return None, {
            "review_id": review.get("id"),
            "label_type": label_type or None,
            "canonical_label_key": canonical or None,
            "signal_type": signal_type or None,
            "route_to": route_to,
            "evidence_span": evidence_span,
            "evidence_start": start,
            "evidence_end": end,
            "evidence_verified": evidence_verified,
            "blocked_reasons": blocked_reasons,
        }

    display_en = _display_label_for_occurrence(occurrence, canonical)
    display_zh = str(occurrence.get("display_label_zh") or display_en).strip()
    normalized = {
        "source_version": READ_PATH_REVIEW_SIGNAL_STORED_SHADOW,
        "review_id": review.get("id"),
        "session_id": _session_id_for_review(review),
        "label_type": label_type,
        "label": display_zh if locale.startswith("zh") else display_en,
        "display_label_en": display_en,
        "display_label_zh": display_zh,
        "canonical_label_key": canonical,
        "aspect_key": str(occurrence.get("aspect_key") or "").strip(),
        "dimension": str(occurrence.get("dimension") or "").strip(),
        "signal_type": signal_type,
        "route_to": route_to,
        "evidence_span": evidence_span,
        "evidence_start": occurrence.get("evidence_start", start),
        "evidence_end": occurrence.get("evidence_end", end),
        "confidence": occurrence.get("confidence", 0.9),
        "source": "review_signal_stored_shadow",
        "locale": locale,
        "source_review_allowed": True,
        "evidence_verified": True,
        "verified_evidence": True,
        "display_allowed": True,
        "cluster_propagated": False,
        "legacy_fallback": False,
        "aspect_allowed": True,
        "context_allowed": True,
        "maturity_allowed": True,
        "downgrade_reasons": [],
    }
    return normalized, None


def _occurrence_keys(occurrences: list[dict[str, Any]]) -> dict[str, list[str]]:
    keys: dict[str, list[str]] = {"issue": [], "highlight": []}
    for occurrence in occurrences:
        label_type = _normalize_label_type(occurrence.get("label_type"))
        canonical = str(occurrence.get("canonical_label_key") or "").strip()
        if label_type in keys and canonical and canonical not in keys[label_type]:
            keys[label_type].append(canonical)
    return keys


def _consumer_contract(read_path: str, occurrences: list[dict[str, Any]]) -> dict[str, Any]:
    keys = _occurrence_keys(occurrences)
    return {
        consumer: {
            "read_path": read_path,
            "occurrence_count": len(occurrences),
            "issue_keys": list(keys["issue"]),
            "highlight_keys": list(keys["highlight"]),
            "input_layer": "selected_product_derived_display_occurrences",
            "candidate_audit_and_non_product_excluded": True,
        }
        for consumer in FRONTSTAGE_CONSUMERS
    }


def frontstage_keys_from_review_signal_read_model(read_model: dict[str, Any]) -> dict[str, list[str]]:
    return _occurrence_keys(list(read_model.get("frontstage_occurrences") or []))


def build_review_signal_frontstage_read_model(
    review: dict[str, Any],
    *,
    flag: ReviewSignalFrontstageFlag | None = None,
    stored_shadow: dict[str, Any] | None = None,
    locale: str = "en",
    production_frontstage_connected: bool = False,
) -> dict[str, Any]:
    flag = flag or ReviewSignalFrontstageFlag()
    review_copy = copy.deepcopy(review)
    stored_shadow = copy.deepcopy(stored_shadow) if stored_shadow is not None else _stored_shadow_for_review(review_copy)
    flag_decision = _flag_match_decision(flag, review_copy)
    stored_shadow_available = stored_shadow is not None
    selected_read_path = READ_PATH_V1_CURRENT
    fallback_reason = flag_decision["reason"]
    selected_occurrences: list[dict[str, Any]] = []
    blocked_occurrences: list[dict[str, Any]] = []
    stored_input_occurrences: list[dict[str, Any]] = []

    if flag_decision["review_signal_requested"]:
        if stored_shadow is None:
            fallback_reason = "review_signal_stored_shadow_missing"
        else:
            fallback_reason = ""
            selected_read_path = READ_PATH_REVIEW_SIGNAL_STORED_SHADOW
            stored_input_occurrences = _candidate_occurrences_from_stored_shadow(stored_shadow)
            for occurrence in stored_input_occurrences:
                normalized, blocked = _normalize_frontstage_occurrence(
                    occurrence,
                    review=review_copy,
                    locale=locale,
                )
                if normalized is not None:
                    selected_occurrences.append(normalized)
                elif blocked is not None:
                    blocked_occurrences.append(blocked)

    if selected_read_path == READ_PATH_REVIEW_SIGNAL_STORED_SHADOW and not selected_occurrences:
        selected_read_path = READ_PATH_V1_CURRENT
        fallback_reason = "review_signal_no_readable_occurrences"

    keys = _occurrence_keys(selected_occurrences)
    frontstage_connected = bool(
        production_frontstage_connected and selected_read_path == READ_PATH_REVIEW_SIGNAL_STORED_SHADOW
    )
    return {
        "schema_version": REVIEW_SIGNAL_FRONTSTAGE_READ_PATH_SCHEMA_VERSION,
        "review_id": review_copy.get("id"),
        "session_id": _session_id_for_review(review_copy),
        "category": _scope_context(review_copy)["category"],
        "sub_category": _scope_context(review_copy)["sub_category"],
        "read_path": selected_read_path,
        "fallback_reason": fallback_reason,
        "flag_decision": flag_decision,
        "feature_flag": flag.as_dict(),
        "stored_shadow_input": {
            "field_name": REVIEW_SIGNAL_STORED_SHADOW_FIELD,
            "available": stored_shadow_available,
            "consumption_only": True,
            "runtime_shadow_generation_allowed": False,
            "runtime_shadow_generated": False,
            "input_occurrence_count": len(stored_input_occurrences),
        },
        "review_signal_stored_shadow": {
            "available": stored_shadow_available,
            "input_occurrence_count": len(stored_input_occurrences),
            "selected_occurrence_count": len(selected_occurrences),
            "blocked_occurrence_count": len(blocked_occurrences),
            "blocked_occurrences": blocked_occurrences,
            "keys": keys,
        },
        "frontstage_occurrences": selected_occurrences,
        "frontstage_keys": keys,
        "frontstage_consumers": _consumer_contract(selected_read_path, selected_occurrences),
        "excluded_routes": {
            "consumer_profile": True,
            "purchase_motives": True,
            "unmet_needs": True,
            "audit_filter_only": True,
            "candidate_keys": True,
        },
        "safety": {
            **review_signal_shadow_safety_flags(),
            "runtime_shadow_called": False,
            "production_frontstage_connected": frontstage_connected,
            "user_visible_results_changed": frontstage_connected,
        },
    }


def _zero_observability() -> dict[str, Any]:
    return {
        "selected_read_path": {
            READ_PATH_V1_CURRENT: 0,
            READ_PATH_REVIEW_SIGNAL_STORED_SHADOW: 0,
        },
        "blocked_by_flag_off": 0,
        "blocked_by_scope": 0,
        "blocked_by_no_stored_shadow": 0,
        "blocked_by_no_readable_data": 0,
        "blocked_by_config_invalid": 0,
        "blocked_by_mapping_unresolved": 0,
        "blocked_by_candidate_key": 0,
        "blocked_by_audit_only": 0,
        "blocked_by_non_product_signal": 0,
        "blocked_by_display_gate": 0,
        "blocked_by_semantic_polarity": 0,
        "rollback_selected": 0,
        "kill_switch_selected": 0,
        "issue_occurrence_count": 0,
        "label_occurrence_count": 0,
        "consumer_profile_signal_count": 0,
        "purchase_motive_signal_count": 0,
        "unmet_need_signal_count": 0,
        "audit_filter_signal_count": 0,
        "candidate_key_frontstage_count": 0,
        "routing_leakage_count": 0,
        "evidence_not_found_frontstage_count": 0,
        "runtime_shadow_generated_count": 0,
    }


def build_review_signal_frontstage_observability_snapshot(
    read_models: list[dict[str, Any]],
    *,
    scope: str = "5.9.9 Step 9.1 Phase 4 review-signal guarded read path",
) -> dict[str, Any]:
    counters = _zero_observability()
    blocked_reason_histogram: Counter[str] = Counter()

    for model in read_models:
        read_path = str(model.get("read_path") or "")
        if read_path in counters["selected_read_path"]:
            counters["selected_read_path"][read_path] += 1
        else:
            counters["selected_read_path"][read_path] = counters["selected_read_path"].get(read_path, 0) + 1

        fallback_reason = str(model.get("fallback_reason") or "")
        flag_decision = model.get("flag_decision") or {}
        if fallback_reason == "flag_off":
            counters["blocked_by_flag_off"] += 1
        if fallback_reason == "scope_not_matched":
            counters["blocked_by_scope"] += 1
        if fallback_reason == "review_signal_stored_shadow_missing":
            counters["blocked_by_no_stored_shadow"] += 1
        if fallback_reason == "review_signal_no_readable_occurrences":
            counters["blocked_by_no_readable_data"] += 1
        if fallback_reason == "config_invalid":
            counters["blocked_by_config_invalid"] += 1
        if bool(flag_decision.get("rollback_active")) or fallback_reason.startswith("rollback_"):
            counters["rollback_selected"] += 1
        if bool(flag_decision.get("kill_switch_active")) or fallback_reason.startswith("kill_switch_"):
            counters["kill_switch_selected"] += 1
        if (model.get("stored_shadow_input") or {}).get("runtime_shadow_generated"):
            counters["runtime_shadow_generated_count"] += 1

        for occurrence in model.get("frontstage_occurrences") or []:
            label_type = _normalize_label_type(occurrence.get("label_type"))
            signal_type = str(occurrence.get("signal_type") or "")
            canonical = str(occurrence.get("canonical_label_key") or "")
            if label_type == "issue":
                counters["issue_occurrence_count"] += 1
                if signal_type != SIGNAL_PRODUCT_NEGATIVE:
                    counters["routing_leakage_count"] += 1
            elif label_type == "highlight":
                counters["label_occurrence_count"] += 1
                if signal_type != SIGNAL_PRODUCT_POSITIVE:
                    counters["routing_leakage_count"] += 1
            else:
                counters["routing_leakage_count"] += 1
            if canonical.startswith("candidate:"):
                counters["candidate_key_frontstage_count"] += 1
            evidence_start = occurrence.get("evidence_start")
            try:
                evidence_start_int = int(evidence_start)
            except (TypeError, ValueError):
                evidence_start_int = -1
            if not occurrence.get("evidence_verified") or evidence_start_int < 0:
                counters["evidence_not_found_frontstage_count"] += 1

        for blocked in (model.get("review_signal_stored_shadow") or {}).get("blocked_occurrences") or []:
            route_to = blocked.get("route_to") or []
            if ROUTE_CONSUMER_PROFILE in route_to:
                counters["consumer_profile_signal_count"] += 1
            if ROUTE_PURCHASE_MOTIVES in route_to:
                counters["purchase_motive_signal_count"] += 1
            if ROUTE_UNMET_NEEDS in route_to:
                counters["unmet_need_signal_count"] += 1
            if ROUTE_AUDIT_FILTER in route_to:
                counters["audit_filter_signal_count"] += 1
            for reason in blocked.get("blocked_reasons") or []:
                if reason in counters and reason != "selected_read_path":
                    counters[reason] += 1
                    blocked_reason_histogram[reason] += 1

    return {
        "schema_version": REVIEW_SIGNAL_FRONTSTAGE_OBSERVABILITY_SCHEMA_VERSION,
        "scope": scope,
        "counters": counters,
        "thresholds": {
            "candidate_key_frontstage_count": 0,
            "routing_leakage_count": 0,
            "evidence_not_found_frontstage_count": 0,
            "runtime_shadow_generated_count": 0,
        },
        "blocked_reason_histogram": dict(sorted(blocked_reason_histogram.items())),
        "status": "PASS"
        if counters["candidate_key_frontstage_count"] == 0
        and counters["routing_leakage_count"] == 0
        and counters["evidence_not_found_frontstage_count"] == 0
        and counters["runtime_shadow_generated_count"] == 0
        else "REVIEW_NEEDED",
        "safety": {
            **review_signal_shadow_safety_flags(),
            "runtime_shadow_called": False,
            "production_frontstage_connected": False,
            "user_visible_results_changed": False,
        },
    }


def attach_review_signal_frontstage_read_model(
    review: dict[str, Any],
    *,
    flag: ReviewSignalFrontstageFlag | None = None,
    stored_shadow: dict[str, Any] | None = None,
    locale: str = "en",
    include_v1_fallback: bool = False,
) -> dict[str, Any]:
    decorated = dict(review)
    flag = flag or review_signal_frontstage_flag_from_env()
    if not flag.enabled and not include_v1_fallback:
        return decorated
    if not include_v1_fallback and not _production_frontstage_scope_allowed(decorated, flag):
        return decorated

    read_model = build_review_signal_frontstage_read_model(
        decorated,
        flag=flag,
        stored_shadow=stored_shadow,
        locale=locale,
        production_frontstage_connected=True,
    )
    if include_v1_fallback or read_model.get("read_path") == READ_PATH_REVIEW_SIGNAL_STORED_SHADOW:
        decorated[REVIEW_SIGNAL_FRONTSTAGE_READ_MODEL_FIELD] = read_model
    return decorated


def attach_review_signal_frontstage_adapter_for_local_test(
    review: dict[str, Any],
    read_model: dict[str, Any],
) -> dict[str, Any]:
    """Expose a review-signal read model to existing four-path helpers in tests only.

    The production decorators never call this function. It adapts selected
    review-signal occurrences to the existing v2 read-model shape so focused
    tests can exercise the real Top10, detail, raw export, and single-tag
    functions without enabling a production frontstage connection.
    """
    decorated = copy.deepcopy(review)
    if str(read_model.get("read_path") or "") != READ_PATH_REVIEW_SIGNAL_STORED_SHADOW:
        return decorated

    adapted_occurrences: list[dict[str, Any]] = []
    for occurrence in read_model.get("frontstage_occurrences") or []:
        if not isinstance(occurrence, dict):
            continue
        adapted = copy.deepcopy(occurrence)
        adapted["source_version"] = READ_PATH_REVIEW_SIGNAL_STORED_SHADOW
        adapted["source"] = "review_signal_stored_shadow_local_test_adapter"
        adapted_occurrences.append(adapted)

    review_signal_read_model = {
        "schema_version": REVIEW_SIGNAL_FRONTSTAGE_READ_PATH_SCHEMA_VERSION,
        "read_path": READ_PATH_REVIEW_SIGNAL_STORED_SHADOW,
        "review_signal_local_test_adapter": True,
        "sub_category": read_model.get("sub_category"),
        "frontstage_occurrences": adapted_occurrences,
    }
    decorated[REVIEW_SIGNAL_FRONTSTAGE_READ_MODEL_FIELD] = review_signal_read_model
    decorated[LOCAL_TEST_CUSTOMER_LABEL_V2_READ_MODEL_FIELD] = {
        **review_signal_read_model,
        "read_path": LOCAL_TEST_ADAPTER_READ_PATH,
        "review_signal_read_path": READ_PATH_REVIEW_SIGNAL_STORED_SHADOW,
        "frontstage_occurrences": [
            {**copy.deepcopy(occurrence), "source_version": LOCAL_TEST_ADAPTER_READ_PATH}
            for occurrence in adapted_occurrences
        ],
    }
    return decorated


def build_review_signal_phase4_implementation_artifact(
    read_models: list[dict[str, Any]],
    *,
    four_path_compatibility: dict[str, Any] | None = None,
    scope: str = "5.9.9 Step 9.1 Phase 4 review-signal guarded read path implementation",
) -> dict[str, Any]:
    observability = build_review_signal_frontstage_observability_snapshot(read_models, scope=scope)
    counters = observability["counters"]
    compatibility = four_path_compatibility or {"status": "NOT_RUN"}
    violations: list[dict[str, Any]] = []
    for field in (
        "candidate_key_frontstage_count",
        "routing_leakage_count",
        "evidence_not_found_frontstage_count",
        "runtime_shadow_generated_count",
    ):
        if counters[field] != 0:
            violations.append({"metric": field, "actual": counters[field], "expected": 0})
    if compatibility.get("status") not in {"PASS", "NOT_RUN"}:
        violations.append({"metric": "per_four_path_compatibility", "actual": compatibility.get("status")})

    return {
        "schema_version": REVIEW_SIGNAL_PHASE4_IMPLEMENTATION_SCHEMA_VERSION,
        "scope": scope,
        "status": "PASS" if not violations else "REVIEW_NEEDED",
        "read_model_count": len(read_models),
        "observability": observability,
        "four_path_compatibility": compatibility,
        "violations": violations,
        "phase5": {
            "status": "BLOCKED_PENDING_ERIKA_PRODUCTION_AUTH",
            "executed": False,
        },
        "unchanged_boundaries": {
            "production_db_write": False,
            "upload": False,
            "reanalysis": False,
            "credit": False,
            "real_llm": False,
            "feature_flag_enabled": False,
            "production_frontstage_connected": False,
            "production_user_visible_result_changed": False,
            "phase5_executed": False,
            "push_or_deploy": False,
        },
        "safety": {
            **review_signal_shadow_safety_flags(),
            "runtime_shadow_called": False,
            "production_frontstage_connected": False,
            "user_visible_results_changed": False,
        },
    }
