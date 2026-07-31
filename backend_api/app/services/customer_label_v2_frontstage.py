from __future__ import annotations

import copy
import json
import os
import re
from collections import Counter
from collections.abc import Mapping
from dataclasses import asdict, dataclass
from typing import Any

from backend_api.app.services.customer_label_v2_maturity import (
    MATURITY_L3_SUB_CATEGORY,
    resolve_customer_label_maturity,
)
from backend_api.app.services.customer_label_v2_shadow import run_customer_label_v2_shadow
from backend_api.app.services.specific_issue import (
    iter_customer_highlight_occurrences,
    iter_specific_issue_occurrences,
)

CUSTOMER_LABEL_V2_FRONTSTAGE_READ_PATH_CONTRACT_VERSION = "customer-label-v2-frontstage-read-path.1"
CUSTOMER_LABEL_V2_FRONTSTAGE_READ_MODEL_FIELD = "customer_label_v2_frontstage_read_model"
READ_PATH_V1_CURRENT = "v1_current"
READ_PATH_V2_SHADOW = "v2_shadow"
FRONTSTAGE_CONSUMERS = (
    "results_top10",
    "single_review_detail",
    "raw_review_export",
    "single_tag_download",
)


@dataclass(frozen=True)
class CustomerLabelV2FrontstageFlag:
    enabled: bool = False
    session_ids: tuple[Any, ...] = ()
    categories: tuple[str, ...] = ()
    sub_categories: tuple[str, ...] = ()
    category_sub_categories: tuple[str, ...] = ()
    shadow_fixture_gate_passed: bool = False
    enabled_maturity_levels: tuple[str, ...] = (MATURITY_L3_SUB_CATEGORY,)
    rollback: bool = False
    rollback_session_ids: tuple[Any, ...] = ()
    rollback_categories: tuple[str, ...] = ()
    rollback_sub_categories: tuple[str, ...] = ()
    rollback_category_sub_categories: tuple[str, ...] = ()
    allow_runtime_shadow: bool = True

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def _truthy_env(value: Any, *, default: bool = False) -> bool:
    if value is None:
        return default
    return str(value).strip().lower() in {"1", "true", "yes", "on", "enabled"}


def _env_values(env: Mapping[str, str], name: str) -> tuple[str, ...]:
    raw = str(env.get(name) or "").strip()
    if not raw:
        return ()
    return tuple(item.strip() for item in raw.split(",") if item.strip())


def customer_label_v2_frontstage_flag_from_env(
    env: Mapping[str, str] | None = None,
) -> CustomerLabelV2FrontstageFlag:
    """Build the production-safe read-path flag from environment configuration.

    Every control defaults to off. Runtime shadow execution is also off here so
    merely enabling a flag cannot synthesize a live replacement without a shadow
    result or explicit local fixture.
    """
    source = env or os.environ
    return CustomerLabelV2FrontstageFlag(
        enabled=_truthy_env(source.get("CUSTOMER_LABEL_V2_FRONTSTAGE_ENABLED")),
        session_ids=_env_values(source, "CUSTOMER_LABEL_V2_FRONTSTAGE_SESSION_IDS"),
        categories=_env_values(source, "CUSTOMER_LABEL_V2_FRONTSTAGE_CATEGORIES"),
        sub_categories=_env_values(source, "CUSTOMER_LABEL_V2_FRONTSTAGE_SUB_CATEGORIES"),
        category_sub_categories=_env_values(source, "CUSTOMER_LABEL_V2_FRONTSTAGE_CATEGORY_SUB_CATEGORIES"),
        shadow_fixture_gate_passed=_truthy_env(source.get("CUSTOMER_LABEL_V2_FRONTSTAGE_SHADOW_FIXTURE_GATE_PASSED")),
        enabled_maturity_levels=_env_values(source, "CUSTOMER_LABEL_V2_FRONTSTAGE_ENABLED_MATURITY_LEVELS")
        or (MATURITY_L3_SUB_CATEGORY,),
        rollback=_truthy_env(source.get("CUSTOMER_LABEL_V2_FRONTSTAGE_ROLLBACK")),
        rollback_session_ids=_env_values(source, "CUSTOMER_LABEL_V2_FRONTSTAGE_ROLLBACK_SESSION_IDS"),
        rollback_categories=_env_values(source, "CUSTOMER_LABEL_V2_FRONTSTAGE_ROLLBACK_CATEGORIES"),
        rollback_sub_categories=_env_values(source, "CUSTOMER_LABEL_V2_FRONTSTAGE_ROLLBACK_SUB_CATEGORIES"),
        rollback_category_sub_categories=_env_values(
            source,
            "CUSTOMER_LABEL_V2_FRONTSTAGE_ROLLBACK_CATEGORY_SUB_CATEGORIES",
        ),
        allow_runtime_shadow=_truthy_env(
            source.get("CUSTOMER_LABEL_V2_FRONTSTAGE_ALLOW_RUNTIME_SHADOW"),
            default=False,
        ),
    )


def customer_label_v2_frontstage_cache_key(flag: CustomerLabelV2FrontstageFlag | None = None) -> str:
    payload = (flag or customer_label_v2_frontstage_flag_from_env()).as_dict()
    return json.dumps(payload, sort_keys=True, default=str, separators=(",", ":"))


def _normalize_key(value: Any) -> str:
    value = str(value or "").strip().lower().replace("&", " and ")
    value = re.sub(r"[^a-z0-9]+", "_", value)
    return re.sub(r"_+", "_", value).strip("_")


def _session_id_for_review(review: dict[str, Any]) -> str:
    for field in ("session_id", "analysis_session_id", "upload_session_id"):
        value = review.get(field)
        if value is not None and str(value).strip():
            return str(value).strip()
    return ""


def _scope_context(review: dict[str, Any]) -> dict[str, str]:
    maturity = resolve_customer_label_maturity(
        category=str(review.get("category") or ""),
        sub_category=str(review.get("sub_category") or ""),
    )
    category = _normalize_key(review.get("category")) or maturity.category
    sub_category = _normalize_key(review.get("sub_category")) or maturity.sub_category
    return {
        "session_id": _session_id_for_review(review),
        "category": category or "unknown",
        "sub_category": sub_category or "unknown",
        "category_sub_category": f"{category or 'unknown'}/{sub_category or 'unknown'}",
        "maturity_level": maturity.level,
    }


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


def _flag_match_decision(flag: CustomerLabelV2FrontstageFlag, review: dict[str, Any]) -> dict[str, Any]:
    context = _scope_context(review)
    if flag.rollback:
        return {
            **context,
            "v2_requested": False,
            "matched_scope": "rollback_global",
            "rollback_active": True,
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
            "v2_requested": False,
            "matched_scope": f"rollback_{rollback_scope}",
            "rollback_active": True,
            "reason": f"rollback_{rollback_scope}",
        }

    if not flag.enabled:
        return {
            **context,
            "v2_requested": False,
            "matched_scope": "none",
            "rollback_active": False,
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
            "v2_requested": True,
            "matched_scope": "global",
            "rollback_active": False,
            "reason": "flag_on_global",
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
        "v2_requested": bool(matched_scope),
        "matched_scope": matched_scope or "none",
        "rollback_active": False,
        "reason": f"flag_on_{matched_scope}" if matched_scope else "scope_not_matched",
    }


def _is_v1_frontstage_occurrence(occurrence: dict[str, Any]) -> bool:
    return bool(
        occurrence.get("display_allowed") is not False
        and occurrence.get("source_review_allowed")
        and occurrence.get("verified_evidence")
        and occurrence.get("evidence_span")
        and not occurrence.get("cluster_propagated")
        and not occurrence.get("legacy_fallback")
        and occurrence.get("aspect_allowed") is not False
        and occurrence.get("context_allowed") is not False
    )


def _is_v2_frontstage_occurrence(occurrence: dict[str, Any]) -> bool:
    return bool(
        occurrence.get("display_allowed") is True
        and occurrence.get("source_review_allowed") is True
        and occurrence.get("evidence_verified") is True
        and occurrence.get("evidence_span")
        and occurrence.get("cluster_propagated") is False
        and occurrence.get("legacy_fallback") is False
        and occurrence.get("aspect_allowed") is True
        and occurrence.get("context_allowed") is True
        and occurrence.get("maturity_allowed") is True
    )


def _label_for_locale(en_label: Any, zh_label: Any, locale: str) -> str:
    en = str(en_label or "").strip()
    zh = str(zh_label or "").strip()
    return (zh or en) if locale.startswith("zh") else (en or zh)


def _normalize_v1_occurrence(occurrence: dict[str, Any], *, locale: str) -> dict[str, Any]:
    label_type = str(occurrence.get("type") or "").strip()
    canonical = str(
        occurrence.get("canonical_issue_key")
        or occurrence.get("canonical_highlight_key")
        or occurrence.get("canonical_label_key")
        or ""
    ).strip()
    if label_type == "issue":
        label = str(occurrence.get("specific_issue") or occurrence.get("display_label_en") or canonical).strip()
    else:
        label = str(occurrence.get("customer_highlight") or occurrence.get("display_label_en") or canonical).strip()
    return {
        "source_version": READ_PATH_V1_CURRENT,
        "review_id": occurrence.get("comment_id"),
        "label_type": label_type,
        "label": label,
        "display_label_en": str(occurrence.get("display_label_en") or label or canonical).strip(),
        "display_label_zh": str(occurrence.get("display_label_zh") or label or canonical).strip(),
        "canonical_label_key": canonical,
        "aspect_key": str(occurrence.get("aspect_key") or "").strip(),
        "dimension": str(occurrence.get("dimension") or "").strip(),
        "evidence_span": str(occurrence.get("evidence_span") or "").strip(),
        "evidence_start": occurrence.get("evidence_start"),
        "evidence_end": occurrence.get("evidence_end"),
        "confidence": occurrence.get("issue_confidence")
        if label_type == "issue"
        else occurrence.get("highlight_confidence") or occurrence.get("confidence"),
        "source": str(occurrence.get("source_detail") or occurrence.get("source") or "").strip(),
        "locale": locale,
        "source_review_allowed": bool(occurrence.get("source_review_allowed")),
        "evidence_verified": bool(occurrence.get("evidence_verified")),
        "verified_evidence": bool(occurrence.get("verified_evidence")),
        "display_allowed": occurrence.get("display_allowed") is not False,
        "cluster_propagated": bool(occurrence.get("cluster_propagated")),
        "legacy_fallback": bool(occurrence.get("legacy_fallback")),
        "aspect_allowed": occurrence.get("aspect_allowed") is not False,
        "context_allowed": occurrence.get("context_allowed") is not False,
        "maturity_allowed": True,
        "downgrade_reasons": [],
    }


def _normalize_v2_occurrence(occurrence: dict[str, Any], *, locale: str) -> dict[str, Any]:
    label_type = str(occurrence.get("label_type") or "").strip()
    canonical = str(occurrence.get("canonical_label_key") or "").strip()
    display_en = str(occurrence.get("display_label_en") or "").strip()
    display_zh = str(occurrence.get("display_label_zh") or "").strip()
    return {
        "source_version": READ_PATH_V2_SHADOW,
        "review_id": occurrence.get("review_id"),
        "label_type": label_type,
        "label": _label_for_locale(display_en, display_zh, locale) or canonical,
        "display_label_en": display_en or canonical,
        "display_label_zh": display_zh or display_en or canonical,
        "canonical_label_key": canonical,
        "aspect_key": str(occurrence.get("aspect_key") or "").strip(),
        "dimension": "",
        "evidence_span": str(occurrence.get("evidence_span") or "").strip(),
        "evidence_start": occurrence.get("evidence_start"),
        "evidence_end": occurrence.get("evidence_end"),
        "confidence": occurrence.get("confidence"),
        "source": str(occurrence.get("source") or "llm").strip(),
        "locale": locale,
        "source_review_allowed": bool(occurrence.get("source_review_allowed")),
        "evidence_verified": bool(occurrence.get("evidence_verified")),
        "verified_evidence": bool(occurrence.get("evidence_verified")),
        "display_allowed": occurrence.get("display_allowed") is True,
        "cluster_propagated": bool(occurrence.get("cluster_propagated")),
        "legacy_fallback": bool(occurrence.get("legacy_fallback")),
        "aspect_allowed": occurrence.get("aspect_allowed") is True,
        "context_allowed": occurrence.get("context_allowed") is True,
        "maturity_allowed": occurrence.get("maturity_allowed") is True,
        "downgrade_reasons": list(occurrence.get("downgrade_reasons") or []),
    }


def _v1_current_frontstage_occurrences(review: dict[str, Any], *, locale: str) -> list[dict[str, Any]]:
    occurrences: list[dict[str, Any]] = []
    for iterator in (iter_specific_issue_occurrences, iter_customer_highlight_occurrences):
        for occurrence in iterator(review, locale=locale):
            if _is_v1_frontstage_occurrence(occurrence):
                occurrences.append(_normalize_v1_occurrence(occurrence, locale=locale))
    return occurrences


def _v2_shadow_frontstage_occurrences(shadow_result: dict[str, Any], *, locale: str) -> list[dict[str, Any]]:
    occurrences: list[dict[str, Any]] = []
    for occurrence in shadow_result.get("display_occurrences") or []:
        if isinstance(occurrence, dict) and _is_v2_frontstage_occurrence(occurrence):
            occurrences.append(_normalize_v2_occurrence(occurrence, locale=locale))
    return occurrences


def _occurrence_keys(occurrences: list[dict[str, Any]]) -> dict[str, list[str]]:
    keys: dict[str, list[str]] = {"issue": [], "highlight": []}
    for occurrence in occurrences:
        label_type = str(occurrence.get("label_type") or "")
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
            "input_layer": "display_occurrences",
            "audit_and_candidate_pool_excluded": True,
        }
        for consumer in FRONTSTAGE_CONSUMERS
    }


def frontstage_keys_from_read_model(read_model: dict[str, Any]) -> dict[str, list[str]]:
    return _occurrence_keys(list(read_model.get("frontstage_occurrences") or []))


def build_customer_label_v2_frontstage_read_model(
    review: dict[str, Any],
    *,
    flag: CustomerLabelV2FrontstageFlag | None = None,
    shadow_result: dict[str, Any] | None = None,
    label_candidates: list[dict[str, Any]] | None = None,
    llm_output: str | dict[str, Any] | list[dict[str, Any]] | None = None,
    locale: str = "en",
) -> dict[str, Any]:
    """Select the local frontstage read path without mutating production state."""
    flag = flag or CustomerLabelV2FrontstageFlag()
    review_copy = copy.deepcopy(review)
    flag_decision = _flag_match_decision(flag, review_copy)
    v1_occurrences = _v1_current_frontstage_occurrences(review_copy, locale=locale)

    selected_read_path = READ_PATH_V1_CURRENT
    selected_occurrences = list(v1_occurrences)
    fallback_reason = flag_decision["reason"]
    v2_occurrences: list[dict[str, Any]] = []
    v2_shadow_summary: dict[str, Any] = {
        "available": False,
        "maturity_level": None,
        "display_occurrence_count": 0,
        "audit_occurrence_count": 0,
        "candidate_pool_item_count": 0,
        "downgrade_reasons": [],
    }

    if flag_decision["v2_requested"] and not flag_decision["rollback_active"]:
        if not flag.shadow_fixture_gate_passed:
            fallback_reason = "shadow_fixture_gate_blocked"
        else:
            if shadow_result is None and flag.allow_runtime_shadow:
                shadow_result = run_customer_label_v2_shadow(
                    review_copy,
                    label_candidates=label_candidates,
                    llm_output=llm_output,
                )
            if shadow_result is None:
                fallback_reason = "v2_shadow_missing"
            else:
                v2_occurrences = _v2_shadow_frontstage_occurrences(shadow_result, locale=locale)
                maturity_level = str(shadow_result.get("maturity_level") or flag_decision["maturity_level"])
                v2_shadow_summary = {
                    "available": True,
                    "maturity_level": maturity_level,
                    "display_occurrence_count": len(v2_occurrences),
                    "audit_occurrence_count": len(shadow_result.get("audit_occurrences") or []),
                    "candidate_pool_item_count": len(shadow_result.get("candidate_pool_items") or []),
                    "downgrade_reasons": list(shadow_result.get("downgrade_reasons") or []),
                }
                if maturity_level not in set(flag.enabled_maturity_levels):
                    fallback_reason = "maturity_not_enabled_for_v2_frontstage"
                else:
                    selected_read_path = READ_PATH_V2_SHADOW
                    selected_occurrences = list(v2_occurrences)
                    fallback_reason = ""
    elif flag_decision["rollback_active"]:
        fallback_reason = flag_decision["reason"]

    selected_keys = _occurrence_keys(selected_occurrences)
    contract_consumer = _consumer_contract(selected_read_path, selected_occurrences)
    return {
        "schema_version": CUSTOMER_LABEL_V2_FRONTSTAGE_READ_PATH_CONTRACT_VERSION,
        "review_id": review_copy.get("id"),
        "session_id": _session_id_for_review(review_copy),
        "category": flag_decision["category"],
        "sub_category": flag_decision["sub_category"],
        "read_path": selected_read_path,
        "fallback_reason": fallback_reason,
        "flag_decision": flag_decision,
        "feature_flag": flag.as_dict(),
        "v1_current": {
            "occurrence_count": len(v1_occurrences),
            "frontstage_occurrences": v1_occurrences,
            "keys": _occurrence_keys(v1_occurrences),
        },
        "v2_shadow": {
            **v2_shadow_summary,
            "frontstage_occurrences": v2_occurrences,
            "keys": _occurrence_keys(v2_occurrences),
        },
        "frontstage_occurrences": selected_occurrences,
        "frontstage_keys": selected_keys,
        "frontstage_consumers": contract_consumer,
        "excluded_layers": {
            "audit_occurrences": True,
            "candidate_pool_items": True,
            "label_candidates": True,
        },
        "safety": {
            "production_upload": False,
            "production_write_path": False,
            "production_db_write": False,
            "db_write": False,
            "credit_consumed": False,
            "llm_called": False,
            "frontstage_replaced": False,
            "frontstage_mutated": False,
        },
    }


def attach_customer_label_v2_frontstage_read_model(
    review: dict[str, Any],
    *,
    flag: CustomerLabelV2FrontstageFlag | None = None,
    shadow_result: dict[str, Any] | None = None,
    label_candidates: list[dict[str, Any]] | None = None,
    llm_output: str | dict[str, Any] | list[dict[str, Any]] | None = None,
    locale: str = "en",
    include_v1_fallback: bool = False,
) -> dict[str, Any]:
    decorated = dict(review)
    flag = flag or customer_label_v2_frontstage_flag_from_env()
    if not flag.enabled and not include_v1_fallback:
        return decorated

    read_model = build_customer_label_v2_frontstage_read_model(
        decorated,
        flag=flag,
        shadow_result=shadow_result,
        label_candidates=label_candidates,
        llm_output=llm_output,
        locale=locale,
    )
    if include_v1_fallback or read_model.get("read_path") == READ_PATH_V2_SHADOW:
        decorated[CUSTOMER_LABEL_V2_FRONTSTAGE_READ_MODEL_FIELD] = read_model
    return decorated


def build_frontstage_read_path_artifact(
    read_models: list[dict[str, Any]],
    *,
    scope: str = "5.9.9 Step 6 v2 frontstage feature flag read-path local contract",
) -> dict[str, Any]:
    violations: list[dict[str, Any]] = []
    selected_read_paths = Counter(str(model.get("read_path") or "") for model in read_models)
    for model in read_models:
        keys = frontstage_keys_from_read_model(model)
        consumer_paths = {
            consumer: payload.get("read_path")
            for consumer, payload in (model.get("frontstage_consumers") or {}).items()
            if isinstance(payload, dict)
        }
        if set(consumer_paths) != set(FRONTSTAGE_CONSUMERS):
            violations.append({"review_id": model.get("review_id"), "error": "consumer_contract_missing"})
        if any(path != model.get("read_path") for path in consumer_paths.values()):
            violations.append({"review_id": model.get("review_id"), "error": "consumer_read_path_mismatch"})
        if any(
            occurrence.get("downgrade_reasons")
            for occurrence in model.get("frontstage_occurrences") or []
            if occurrence.get("source_version") == READ_PATH_V2_SHADOW
        ):
            violations.append({"review_id": model.get("review_id"), "error": "downgraded_v2_occurrence_selected"})
        if not isinstance(keys.get("issue"), list) or not isinstance(keys.get("highlight"), list):
            violations.append({"review_id": model.get("review_id"), "error": "frontstage_keys_invalid"})

    return {
        "schema_version": CUSTOMER_LABEL_V2_FRONTSTAGE_READ_PATH_CONTRACT_VERSION,
        "scope": scope,
        "status": "PASS" if not violations else "REVIEW_NEEDED",
        "case_count": len(read_models),
        "selected_read_paths": dict(sorted(selected_read_paths.items())),
        "violations": violations,
        "read_models": read_models,
        "contract": customer_label_v2_frontstage_contract_summary(),
        "safety": {
            "production_upload": False,
            "production_write_path": False,
            "production_db_write": False,
            "db_write": False,
            "credit_consumed": False,
            "llm_called": False,
            "frontstage_replaced": False,
            "frontstage_mutated": False,
        },
    }


def customer_label_v2_frontstage_contract_summary() -> dict[str, Any]:
    return {
        "schema_version": CUSTOMER_LABEL_V2_FRONTSTAGE_READ_PATH_CONTRACT_VERSION,
        "default_read_path": READ_PATH_V1_CURRENT,
        "v2_read_path": READ_PATH_V2_SHADOW,
        "feature_flag": {
            "default_enabled": False,
            "env_prefix": "CUSTOMER_LABEL_V2_FRONTSTAGE_",
            "controls": [
                "session_id",
                "category",
                "sub_category",
                "category_sub_category",
            ],
            "shadow_fixture_gate_required": True,
            "enabled_maturity_levels_default": [MATURITY_L3_SUB_CATEGORY],
            "env_runtime_shadow_default": False,
            "rollback_controls": [
                "global",
                "session_id",
                "category",
                "sub_category",
                "category_sub_category",
            ],
        },
        "frontstage_consumers": {
            "results_top10": "Count selected display occurrences only.",
            "single_review_detail": "Render selected display occurrences only.",
            "raw_review_export": "Write selected display occurrences to frontstage columns only.",
            "single_tag_download": "Download selected verified evidence occurrences for the requested label only.",
        },
        "fallback": {
            "flag_off": READ_PATH_V1_CURRENT,
            "scope_not_matched": READ_PATH_V1_CURRENT,
            "shadow_fixture_gate_blocked": READ_PATH_V1_CURRENT,
            "v2_shadow_missing": READ_PATH_V1_CURRENT,
            "maturity_not_enabled_for_v2_frontstage": READ_PATH_V1_CURRENT,
            "rollback": READ_PATH_V1_CURRENT,
        },
        "excluded_from_frontstage": [
            "label_candidates",
            "audit_occurrences",
            "candidate_pool_items",
            "maturity_blocked_candidates",
            "unknown_label_candidates",
        ],
        "safety": {
            "production_upload": False,
            "production_write_path": False,
            "production_db_write": False,
            "db_write": False,
            "credit_consumed": False,
            "llm_called": False,
            "frontstage_replaced": False,
            "frontstage_mutated": False,
        },
    }
