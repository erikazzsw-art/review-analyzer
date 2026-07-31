from __future__ import annotations

import copy
from collections import Counter
from dataclasses import asdict, dataclass
from typing import Any

REVIEW_SIGNAL_SCHEMA_VERSION = "review-signals-shadow.1"
REVIEW_SIGNAL_GOLD_SCHEMA_VERSION = "review-signals-gold.1"
REVIEW_SIGNAL_PROJECTION_SCHEMA_VERSION = "review-signals-routing-projection.1"
REVIEW_SIGNAL_FP_FN_SCHEMA_VERSION = "review-signals-fp-fn-comparison.1"
REVIEW_SIGNAL_RULESET_VERSION = "2026-07-31-step9.1-minimal-routing"

ROUTE_USER_EXPERIENCE_POSITIVE = "user_experience.positive"
ROUTE_USER_EXPERIENCE_NEGATIVE = "user_experience.negative"
ROUTE_CUSTOMER_LABEL_CANDIDATE = "customer_label_candidate"
ROUTE_CUSTOMER_ISSUE_CANDIDATE = "customer_issue_candidate"
ROUTE_CONSUMER_PROFILE = "consumer_profile"
ROUTE_PURCHASE_MOTIVES = "purchase_motives"
ROUTE_UNMET_NEEDS = "unmet_needs"
ROUTE_AUDIT_FILTER = "audit.filter_only"

SIGNAL_PRODUCT_POSITIVE = "product_positive"
SIGNAL_PRODUCT_NEGATIVE = "product_negative"
SIGNAL_AUDIENCE = "audience"
SIGNAL_USAGE_LOCATION = "usage_location"
SIGNAL_USAGE_TIME = "usage_time"
SIGNAL_BEHAVIOR = "behavior"
SIGNAL_EXPECTATION = "expectation"
SIGNAL_PURCHASE_MOTIVATION = "purchase_motivation"
SIGNAL_COMPARISON_OR_OTHER_PRODUCT = "comparison_or_other_product"
SIGNAL_ACCESSORY_ONLY = "accessory_only"
SIGNAL_SHIPPING_SERVICE = "shipping_service"
SIGNAL_GENERIC_OR_VAGUE = "generic_or_vague"
SIGNAL_AUDIT_ONLY = "audit_only"

PRODUCT_SIGNAL_TYPES = {SIGNAL_PRODUCT_POSITIVE, SIGNAL_PRODUCT_NEGATIVE}
AUDIT_FILTER_SIGNAL_TYPES = {
    SIGNAL_COMPARISON_OR_OTHER_PRODUCT,
    SIGNAL_ACCESSORY_ONLY,
    SIGNAL_SHIPPING_SERVICE,
    SIGNAL_GENERIC_OR_VAGUE,
    SIGNAL_AUDIT_ONLY,
}
VALID_SIGNAL_TYPES = {
    SIGNAL_PRODUCT_POSITIVE,
    SIGNAL_PRODUCT_NEGATIVE,
    SIGNAL_AUDIENCE,
    SIGNAL_USAGE_LOCATION,
    SIGNAL_USAGE_TIME,
    SIGNAL_BEHAVIOR,
    SIGNAL_EXPECTATION,
    SIGNAL_PURCHASE_MOTIVATION,
    SIGNAL_COMPARISON_OR_OTHER_PRODUCT,
    SIGNAL_ACCESSORY_ONLY,
    SIGNAL_SHIPPING_SERVICE,
    SIGNAL_GENERIC_OR_VAGUE,
    SIGNAL_AUDIT_ONLY,
}
VALID_POLARITIES = {"positive", "negative", "mixed", "neutral"}
VALID_CURRENT_PRODUCT_SCOPES = {
    "current_product",
    "current_product_context",
    "non_product_context",
    "other_product",
    "accessory_only",
    "shipping_service",
    "unclear",
    "audit_only",
}
VALID_GOLD_SOURCE_KINDS = {
    "screenshot_derived_gold",
    "human_gold_fixture",
    "blind_regression_fixture",
    "production_readonly_local_copy",
    "candidate_pool_reviewed",
    "local_shadow_probe",
}

SHADOW_SAFETY_FLAGS = {
    "production_upload": False,
    "production_write_path": False,
    "production_db_write": False,
    "db_write": False,
    "credit_consumed": False,
    "llm_called": False,
    "frontstage_replaced": False,
    "frontstage_mutated": False,
    "production_feature_flag_enabled": False,
    "production_gray_run_executed": False,
    "insight_engine_runtime_connected": False,
}

_DEFAULT_POLARITY_BY_SIGNAL_TYPE = {
    SIGNAL_PRODUCT_POSITIVE: "positive",
    SIGNAL_PRODUCT_NEGATIVE: "negative",
    SIGNAL_AUDIENCE: "neutral",
    SIGNAL_USAGE_LOCATION: "neutral",
    SIGNAL_USAGE_TIME: "neutral",
    SIGNAL_BEHAVIOR: "neutral",
    SIGNAL_EXPECTATION: "neutral",
    SIGNAL_PURCHASE_MOTIVATION: "positive",
    SIGNAL_COMPARISON_OR_OTHER_PRODUCT: "mixed",
    SIGNAL_ACCESSORY_ONLY: "neutral",
    SIGNAL_SHIPPING_SERVICE: "neutral",
    SIGNAL_GENERIC_OR_VAGUE: "neutral",
    SIGNAL_AUDIT_ONLY: "neutral",
}

_DEFAULT_SCOPE_BY_SIGNAL_TYPE = {
    SIGNAL_PRODUCT_POSITIVE: "current_product",
    SIGNAL_PRODUCT_NEGATIVE: "current_product",
    SIGNAL_AUDIENCE: "non_product_context",
    SIGNAL_USAGE_LOCATION: "non_product_context",
    SIGNAL_USAGE_TIME: "non_product_context",
    SIGNAL_BEHAVIOR: "non_product_context",
    SIGNAL_EXPECTATION: "current_product_context",
    SIGNAL_PURCHASE_MOTIVATION: "current_product_context",
    SIGNAL_COMPARISON_OR_OTHER_PRODUCT: "other_product",
    SIGNAL_ACCESSORY_ONLY: "accessory_only",
    SIGNAL_SHIPPING_SERVICE: "shipping_service",
    SIGNAL_GENERIC_OR_VAGUE: "unclear",
    SIGNAL_AUDIT_ONLY: "audit_only",
}

_ROUTE_TO_BY_SIGNAL_TYPE = {
    SIGNAL_PRODUCT_POSITIVE: (ROUTE_USER_EXPERIENCE_POSITIVE, ROUTE_CUSTOMER_LABEL_CANDIDATE),
    SIGNAL_PRODUCT_NEGATIVE: (ROUTE_USER_EXPERIENCE_NEGATIVE, ROUTE_CUSTOMER_ISSUE_CANDIDATE),
    SIGNAL_AUDIENCE: (ROUTE_CONSUMER_PROFILE,),
    SIGNAL_USAGE_LOCATION: (ROUTE_CONSUMER_PROFILE,),
    SIGNAL_USAGE_TIME: (ROUTE_CONSUMER_PROFILE,),
    SIGNAL_BEHAVIOR: (ROUTE_CONSUMER_PROFILE,),
    SIGNAL_EXPECTATION: (ROUTE_UNMET_NEEDS,),
    SIGNAL_PURCHASE_MOTIVATION: (ROUTE_PURCHASE_MOTIVES,),
    SIGNAL_COMPARISON_OR_OTHER_PRODUCT: (ROUTE_AUDIT_FILTER,),
    SIGNAL_ACCESSORY_ONLY: (ROUTE_AUDIT_FILTER,),
    SIGNAL_SHIPPING_SERVICE: (ROUTE_AUDIT_FILTER,),
    SIGNAL_GENERIC_OR_VAGUE: (ROUTE_AUDIT_FILTER,),
    SIGNAL_AUDIT_ONLY: (ROUTE_AUDIT_FILTER,),
}


@dataclass(frozen=True)
class ReviewSignal:
    signal_type: str
    polarity: str
    evidence_span: str
    current_product_scope: str
    route_to: tuple[str, ...]
    confidence: float
    reason: str
    review_id: Any = None
    evidence_start: int = -1
    evidence_end: int = -1
    evidence_verified: bool = False
    route_blocked_reasons: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["route_to"] = list(self.route_to)
        payload["route_blocked_reasons"] = list(self.route_blocked_reasons)
        return payload


def review_signal_routing_table() -> dict[str, dict[str, Any]]:
    return {
        signal_type: {
            "signal_type": signal_type,
            "default_polarity": _DEFAULT_POLARITY_BY_SIGNAL_TYPE[signal_type],
            "default_current_product_scope": _DEFAULT_SCOPE_BY_SIGNAL_TYPE[signal_type],
            "route_to": list(route_to),
            "customer_issue_candidate": ROUTE_CUSTOMER_ISSUE_CANDIDATE in route_to,
            "customer_label_candidate": ROUTE_CUSTOMER_LABEL_CANDIDATE in route_to,
        }
        for signal_type, route_to in _ROUTE_TO_BY_SIGNAL_TYPE.items()
    }


def _coerce_confidence(value: Any) -> float:
    try:
        confidence = float(value)
    except (TypeError, ValueError):
        return 0.0
    return min(max(confidence, 0.0), 1.0)


def _locate_evidence(content: str, evidence_span: str) -> tuple[int, int, bool, str]:
    evidence = str(evidence_span or "").strip()
    if not evidence:
        return -1, -1, False, "evidence_missing"
    if not content:
        return -1, -1, False, "content_missing"
    start = content.find(evidence)
    if start < 0:
        start = content.lower().find(evidence.lower())
    if start < 0:
        return -1, -1, False, "evidence_not_found"
    return start, start + len(evidence), True, ""


def _normalize_signal_type(value: Any) -> str:
    signal_type = str(value or "").strip().lower()
    return signal_type if signal_type in VALID_SIGNAL_TYPES else SIGNAL_AUDIT_ONLY


def _normalize_polarity(signal_type: str, value: Any) -> str:
    polarity = str(value or "").strip().lower()
    return polarity if polarity in VALID_POLARITIES else _DEFAULT_POLARITY_BY_SIGNAL_TYPE[signal_type]


def _normalize_scope(signal_type: str, value: Any) -> str:
    scope = str(value or "").strip().lower()
    return scope if scope in VALID_CURRENT_PRODUCT_SCOPES else _DEFAULT_SCOPE_BY_SIGNAL_TYPE[signal_type]


def _dedupe_reasons(reasons: list[str]) -> tuple[str, ...]:
    seen: set[str] = set()
    deduped: list[str] = []
    for reason in reasons:
        if reason and reason not in seen:
            deduped.append(reason)
            seen.add(reason)
    return tuple(deduped)


def review_signal_shadow_safety_flags() -> dict[str, bool]:
    return dict(SHADOW_SAFETY_FLAGS)


def _normalize_label_type(value: Any) -> str:
    label_type = str(value or "").strip().lower()
    if label_type in {"issue", "customer_issue"}:
        return "issue"
    if label_type in {"label", "highlight", "customer_label", "customer_highlight"}:
        return "label"
    return ""


def _expected_routes_for_signal_type(signal_type: str) -> list[str]:
    return list(_ROUTE_TO_BY_SIGNAL_TYPE.get(signal_type, (ROUTE_AUDIT_FILTER,)))


def _normalize_route_to(signal_type: str, value: Any) -> list[str]:
    if isinstance(value, str):
        route_to = [value]
    elif isinstance(value, (list, tuple)):
        route_to = [str(route or "").strip() for route in value]
    else:
        route_to = []
    route_to = [route for route in route_to if route]
    return route_to or _expected_routes_for_signal_type(signal_type)


def _normalize_source_kind(value: Any) -> str:
    source_kind = str(value or "").strip()
    return source_kind if source_kind in VALID_GOLD_SOURCE_KINDS else "local_shadow_probe"


def _normalize_key_set(values: Any) -> list[str]:
    if values is None:
        return []
    if isinstance(values, str):
        values = [item.strip() for item in values.split(",")]
    keys: list[str] = []
    for value in values if isinstance(values, (list, tuple, set)) else []:
        key = str(value or "").strip()
        if key and key not in keys:
            keys.append(key)
    return keys


def _signal_has_route(signal: dict[str, Any], route: str) -> bool:
    return route in (signal.get("route_to") or [])


def _mapping_status(label_type: str, canonical_label_key: str) -> str:
    if not label_type or not canonical_label_key:
        return "extraction_unresolved"
    if canonical_label_key.startswith("candidate:"):
        return "extraction_unresolved"
    return "mapped"


def _frontstage_occurrence_key(occurrence: dict[str, Any]) -> str:
    return str(
        occurrence.get("canonical_label_key")
        or occurrence.get("canonical_issue_key")
        or occurrence.get("canonical_highlight_key")
        or ""
    ).strip()


def _frontstage_occurrence_type(occurrence: dict[str, Any]) -> str:
    return _normalize_label_type(occurrence.get("label_type") or occurrence.get("type"))


def _normalized_signal_for_projection(
    signal: dict[str, Any],
    *,
    content: str,
    review_id: Any,
) -> dict[str, Any]:
    if "route_to" in signal and "evidence_verified" in signal and "route_blocked_reasons" in signal:
        normalized = copy.deepcopy(signal)
        normalized.setdefault("review_id", review_id)
        normalized.setdefault("route_blocked_reasons", [])
        return normalized
    return normalize_review_signal_candidate(signal, content=content, review_id=review_id).as_dict()


def normalize_review_signal_gold_fragment(
    fragment: dict[str, Any],
    *,
    content_by_review_id: dict[str, str] | None = None,
) -> dict[str, Any]:
    content_lookup = content_by_review_id or {}
    review_id = fragment.get("review_id")
    review_id_key = str(review_id or "")
    signal_type = _normalize_signal_type(fragment.get("expected_signal_type"))
    polarity = _normalize_polarity(signal_type, fragment.get("expected_polarity"))
    current_product_scope = _normalize_scope(signal_type, fragment.get("expected_current_product_scope"))
    evidence_span = str(fragment.get("evidence_span") or "").strip()
    source_kind = _normalize_source_kind(fragment.get("source_kind"))
    label_type = _normalize_label_type(fragment.get("expected_label_type"))
    canonical_label_key = str(fragment.get("expected_canonical_label_key") or "").strip()
    route_to = _normalize_route_to(signal_type, fragment.get("expected_route_to"))
    content = str(fragment.get("review_content") or content_lookup.get(review_id_key) or "")
    evidence_start, evidence_end, evidence_verified, evidence_reason = _locate_evidence(content, evidence_span)

    schema_errors: list[str] = []
    required_fields = {
        "review_id",
        "evidence_span",
        "expected_signal_type",
        "expected_polarity",
        "expected_current_product_scope",
        "expected_route_to",
        "source",
        "gold_reason",
    }
    for field in sorted(required_fields):
        if fragment.get(field) in (None, "", []):
            schema_errors.append(f"{field}_missing")
    if evidence_reason:
        schema_errors.append(evidence_reason)
    if label_type and label_type not in {"issue", "label"}:
        schema_errors.append("expected_label_type_invalid")

    normalized = {
        **copy.deepcopy(fragment),
        "schema_version": REVIEW_SIGNAL_GOLD_SCHEMA_VERSION,
        "review_id": review_id,
        "evidence_span": evidence_span,
        "expected_signal_type": signal_type,
        "expected_polarity": polarity,
        "expected_current_product_scope": current_product_scope,
        "expected_route_to": route_to,
        "expected_label_type": label_type or None,
        "expected_canonical_label_key": canonical_label_key or None,
        "source_kind": source_kind,
        "evidence_start": evidence_start,
        "evidence_end": evidence_end,
        "evidence_verified": evidence_verified,
        "schema_errors": schema_errors,
        "mapping_status": _mapping_status(label_type, canonical_label_key) if label_type else "not_label_mapped",
    }
    return normalized


def normalize_review_signal_candidate(
    candidate: dict[str, Any],
    *,
    content: str,
    review_id: Any = None,
) -> ReviewSignal:
    raw_signal_type = str(candidate.get("signal_type") or "").strip().lower()
    signal_type = _normalize_signal_type(raw_signal_type)
    polarity = _normalize_polarity(signal_type, candidate.get("polarity"))
    current_product_scope = _normalize_scope(signal_type, candidate.get("current_product_scope"))
    evidence_span = str(candidate.get("evidence_span") or "").strip()
    confidence = _coerce_confidence(candidate.get("confidence", 0.0))
    reason = str(candidate.get("reason") or "").strip()

    evidence_start, evidence_end, evidence_verified, evidence_reason = _locate_evidence(content, evidence_span)
    blocked_reasons: list[str] = []
    if raw_signal_type not in VALID_SIGNAL_TYPES:
        blocked_reasons.append("signal_type_invalid")
    if not reason:
        blocked_reasons.append("reason_missing")
    if evidence_reason:
        blocked_reasons.append(evidence_reason)
    if confidence <= 0:
        blocked_reasons.append("confidence_invalid")
    if signal_type in PRODUCT_SIGNAL_TYPES and current_product_scope != "current_product":
        blocked_reasons.append("non_current_product_scope")

    route_to = _ROUTE_TO_BY_SIGNAL_TYPE[signal_type]
    if blocked_reasons:
        route_to = (ROUTE_AUDIT_FILTER,)

    return ReviewSignal(
        signal_type=signal_type,
        polarity=polarity,
        evidence_span=evidence_span,
        current_product_scope=current_product_scope,
        route_to=route_to,
        confidence=confidence,
        reason=reason,
        review_id=review_id,
        evidence_start=evidence_start,
        evidence_end=evidence_end,
        evidence_verified=evidence_verified,
        route_blocked_reasons=_dedupe_reasons(blocked_reasons),
    )


def _route_filter(signals: list[dict[str, Any]], route: str) -> list[dict[str, Any]]:
    return [signal for signal in signals if route in signal.get("route_to", [])]


def build_review_signal_routing_projection(review_signals: list[dict[str, Any]]) -> dict[str, Any]:
    customer_issue_candidates = _route_filter(review_signals, ROUTE_CUSTOMER_ISSUE_CANDIDATE)
    customer_label_candidates = _route_filter(review_signals, ROUTE_CUSTOMER_LABEL_CANDIDATE)
    consumer_profile_signals = _route_filter(review_signals, ROUTE_CONSUMER_PROFILE)
    purchase_motive_signals = _route_filter(review_signals, ROUTE_PURCHASE_MOTIVES)
    unmet_need_signals = _route_filter(review_signals, ROUTE_UNMET_NEEDS)
    audit_filter_signals = _route_filter(review_signals, ROUTE_AUDIT_FILTER)

    leakage_violations: list[dict[str, Any]] = []
    for signal in customer_issue_candidates:
        if signal.get("signal_type") != SIGNAL_PRODUCT_NEGATIVE:
            leakage_violations.append({"route": ROUTE_CUSTOMER_ISSUE_CANDIDATE, "signal": signal})
    for signal in customer_label_candidates:
        if signal.get("signal_type") != SIGNAL_PRODUCT_POSITIVE:
            leakage_violations.append({"route": ROUTE_CUSTOMER_LABEL_CANDIDATE, "signal": signal})

    return {
        "user_experience": {
            "positive": _route_filter(review_signals, ROUTE_USER_EXPERIENCE_POSITIVE),
            "negative": _route_filter(review_signals, ROUTE_USER_EXPERIENCE_NEGATIVE),
        },
        "customer_issue_candidates": customer_issue_candidates,
        "customer_label_candidates": customer_label_candidates,
        "consumer_profile_signals": consumer_profile_signals,
        "purchase_motive_signals": purchase_motive_signals,
        "unmet_need_signals": unmet_need_signals,
        "audit_filter_signals": audit_filter_signals,
        "leakage_violations": leakage_violations,
    }


def _gold_lookup_by_evidence(gold_fragments: list[dict[str, Any]]) -> dict[tuple[str, str], list[dict[str, Any]]]:
    lookup: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for fragment in gold_fragments:
        key = (
            str(fragment.get("review_id") or ""),
            str(fragment.get("evidence_span") or "").strip().lower(),
        )
        lookup.setdefault(key, []).append(fragment)
    return lookup


def _match_gold_fragment(
    signal: dict[str, Any],
    gold_lookup: dict[tuple[str, str], list[dict[str, Any]]],
) -> dict[str, Any] | None:
    review_id = str(signal.get("review_id") or "")
    evidence = str(signal.get("evidence_span") or "").strip().lower()
    key = (
        review_id,
        evidence,
    )
    candidates = gold_lookup.get(key) or []
    if not candidates and evidence:
        for (candidate_review_id, candidate_evidence), candidate_fragments in gold_lookup.items():
            if candidate_review_id != review_id:
                continue
            if evidence in candidate_evidence or candidate_evidence in evidence:
                candidates = candidate_fragments
                break
    if not candidates:
        return None
    signal_type = str(signal.get("signal_type") or "")
    for candidate in candidates:
        if candidate.get("expected_signal_type") == signal_type:
            return candidate
    return candidates[0]


def _candidate_from_signal(signal: dict[str, Any], gold: dict[str, Any] | None) -> dict[str, Any]:
    label_type = _normalize_label_type(
        (gold or {}).get("expected_label_type") or signal.get("expected_label_type")
    )
    canonical_label_key = str(
        (gold or {}).get("expected_canonical_label_key")
        or signal.get("expected_canonical_label_key")
        or ""
    ).strip()
    mapping_status = _mapping_status(label_type, canonical_label_key)
    projection_reason = "current_product_signal_allowed"
    if mapping_status != "mapped":
        projection_reason = "current_product_signal_allowed_but_extraction_unresolved"
    return {
        "review_id": signal.get("review_id"),
        "evidence_span": signal.get("evidence_span"),
        "signal_type": signal.get("signal_type"),
        "polarity": signal.get("polarity"),
        "current_product_scope": signal.get("current_product_scope"),
        "route_to": list(signal.get("route_to") or []),
        "expected_label_type": label_type or None,
        "expected_canonical_label_key": canonical_label_key or None,
        "mapping_status": mapping_status,
        "source": (gold or {}).get("source"),
        "source_kind": (gold or {}).get("source_kind"),
        "segment": (gold or {}).get("segment"),
        "projection_reason": projection_reason,
    }


def _keys_from_projection_candidates(candidates: list[dict[str, Any]], label_type: str) -> list[str]:
    keys: list[str] = []
    for candidate in candidates:
        if _normalize_label_type(candidate.get("expected_label_type")) != label_type:
            continue
        if candidate.get("mapping_status") != "mapped":
            continue
        key = str(candidate.get("expected_canonical_label_key") or "").strip()
        if key and key not in keys:
            keys.append(key)
    return sorted(keys)


def expected_customer_keys_from_gold(gold_fragments: list[dict[str, Any]]) -> dict[str, list[str]]:
    keys: dict[str, list[str]] = {"issue": [], "label": []}
    for fragment in gold_fragments:
        label_type = _normalize_label_type(fragment.get("expected_label_type"))
        canonical = str(fragment.get("expected_canonical_label_key") or "").strip()
        signal_type = str(fragment.get("expected_signal_type") or "")
        if label_type == "issue" and signal_type != SIGNAL_PRODUCT_NEGATIVE:
            continue
        if label_type == "label" and signal_type != SIGNAL_PRODUCT_POSITIVE:
            continue
        if _mapping_status(label_type, canonical) != "mapped":
            continue
        if canonical not in keys[label_type]:
            keys[label_type].append(canonical)
    return {label_type: sorted(values) for label_type, values in keys.items()}


def build_signal_derived_routing_projection(
    review: dict[str, Any],
    *,
    existing_occurrences: list[dict[str, Any]] | None = None,
    review_signals: list[dict[str, Any]] | None = None,
    gold_fragments: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    source_review = copy.deepcopy(review)
    review_id = source_review.get("id")
    content = str(source_review.get("content") or "")
    normalized_gold = [
        normalize_review_signal_gold_fragment(fragment, content_by_review_id={str(review_id): content})
        for fragment in gold_fragments or []
    ]
    gold_lookup = _gold_lookup_by_evidence(normalized_gold)
    normalized_signals = [
        _normalized_signal_for_projection(signal, content=content, review_id=review_id)
        for signal in review_signals or []
        if isinstance(signal, dict)
    ]

    signal_derived_issue_candidates: list[dict[str, Any]] = []
    signal_derived_label_candidates: list[dict[str, Any]] = []
    consumer_profile_signals: list[dict[str, Any]] = []
    purchase_motive_signals: list[dict[str, Any]] = []
    unmet_need_signals: list[dict[str, Any]] = []
    audit_filter_signals: list[dict[str, Any]] = []
    blocked_or_unmatched_occurrences: list[dict[str, Any]] = []
    projection_reasons: list[dict[str, Any]] = []
    leakage_violations: list[dict[str, Any]] = []

    for signal in normalized_signals:
        gold = _match_gold_fragment(signal, gold_lookup)
        route_to = list(signal.get("route_to") or [])
        signal_type = str(signal.get("signal_type") or "")
        if _signal_has_route(signal, ROUTE_CUSTOMER_ISSUE_CANDIDATE):
            candidate = _candidate_from_signal(signal, gold)
            signal_derived_issue_candidates.append(candidate)
            if signal_type != SIGNAL_PRODUCT_NEGATIVE:
                leakage_violations.append({"route": ROUTE_CUSTOMER_ISSUE_CANDIDATE, "signal": signal})
        if _signal_has_route(signal, ROUTE_CUSTOMER_LABEL_CANDIDATE):
            candidate = _candidate_from_signal(signal, gold)
            signal_derived_label_candidates.append(candidate)
            if signal_type != SIGNAL_PRODUCT_POSITIVE:
                leakage_violations.append({"route": ROUTE_CUSTOMER_LABEL_CANDIDATE, "signal": signal})
        if _signal_has_route(signal, ROUTE_CONSUMER_PROFILE):
            consumer_profile_signals.append(signal)
        if _signal_has_route(signal, ROUTE_PURCHASE_MOTIVES):
            purchase_motive_signals.append(signal)
        if _signal_has_route(signal, ROUTE_UNMET_NEEDS):
            unmet_need_signals.append(signal)
        if _signal_has_route(signal, ROUTE_AUDIT_FILTER):
            audit_filter_signals.append(signal)
        projection_reasons.append(
            {
                "review_id": review_id,
                "evidence_span": signal.get("evidence_span"),
                "signal_type": signal_type,
                "route_to": route_to,
                "blocked_reasons": list(signal.get("route_blocked_reasons") or []),
                "matched_gold": bool(gold),
            }
        )

    for occurrence in existing_occurrences or []:
        occurrence_type = _frontstage_occurrence_type(occurrence)
        evidence = str(occurrence.get("evidence_span") or "").strip()
        occurrence_key = _frontstage_occurrence_key(occurrence)
        start, end, evidence_verified, evidence_reason = _locate_evidence(content, evidence)
        matched_gold = _match_gold_fragment(
            {"review_id": review_id, "evidence_span": evidence, "signal_type": occurrence.get("signal_type")},
            gold_lookup,
        )
        reasons: list[str] = []
        if evidence_reason:
            reasons.append(evidence_reason)
        if not matched_gold:
            reasons.append("no_matching_gold_fragment")
        else:
            expected_signal_type = str(matched_gold.get("expected_signal_type") or "")
            expected_scope = str(matched_gold.get("expected_current_product_scope") or "")
            expected_label_type = _normalize_label_type(matched_gold.get("expected_label_type"))
            expected_key = str(matched_gold.get("expected_canonical_label_key") or "").strip()
            if occurrence_type == "issue" and expected_signal_type != SIGNAL_PRODUCT_NEGATIVE:
                reasons.append("signal_gate_blocks_customer_issue")
            if occurrence_type == "label" and expected_signal_type != SIGNAL_PRODUCT_POSITIVE:
                reasons.append("signal_gate_blocks_customer_label")
            if expected_scope != "current_product" and expected_signal_type in PRODUCT_SIGNAL_TYPES:
                reasons.append("non_current_product_scope")
            if expected_label_type and occurrence_type and expected_label_type != occurrence_type:
                reasons.append("label_type_mismatch")
            if expected_key and occurrence_key and expected_key != occurrence_key:
                reasons.append("canonical_mapping_mismatch")
            if matched_gold.get("mapping_status") == "extraction_unresolved":
                reasons.append("extraction_unresolved")
        if reasons:
            blocked_or_unmatched_occurrences.append(
                {
                    "review_id": review_id,
                    "label_type": occurrence_type or None,
                    "canonical_label_key": occurrence_key or None,
                    "evidence_span": evidence,
                    "evidence_start": start,
                    "evidence_end": end,
                    "evidence_verified": evidence_verified,
                    "blocked_reasons": list(_dedupe_reasons(reasons)),
                }
            )

    unresolved_candidates = [
        candidate
        for candidate in signal_derived_issue_candidates + signal_derived_label_candidates
        if candidate.get("mapping_status") == "extraction_unresolved"
    ]
    evidence_not_found_count = sum(
        1
        for signal in normalized_signals
        if "evidence_not_found" in (signal.get("route_blocked_reasons") or [])
    )
    evidence_not_found_count += sum(
        1
        for item in blocked_or_unmatched_occurrences
        if "evidence_not_found" in item.get("blocked_reasons", [])
    )

    return {
        "schema_version": REVIEW_SIGNAL_PROJECTION_SCHEMA_VERSION,
        "ruleset_version": REVIEW_SIGNAL_RULESET_VERSION,
        "review_id": review_id,
        "signal_derived_customer_issue_candidates": signal_derived_issue_candidates,
        "signal_derived_customer_label_candidates": signal_derived_label_candidates,
        "consumer_profile_signals": consumer_profile_signals,
        "purchase_motive_signals": purchase_motive_signals,
        "unmet_need_signals": unmet_need_signals,
        "audit_filter_signals": audit_filter_signals,
        "blocked_or_unmatched_occurrences": blocked_or_unmatched_occurrences,
        "projection_reasons": projection_reasons,
        "signal_shadow_issue_keys": _keys_from_projection_candidates(signal_derived_issue_candidates, "issue"),
        "signal_shadow_label_keys": _keys_from_projection_candidates(signal_derived_label_candidates, "label"),
        "evidence_not_found_count": evidence_not_found_count,
        "non_product_leakage_count": len(leakage_violations),
        "unresolved_mapping_count": len(unresolved_candidates),
        "leakage_violations": leakage_violations,
        "safety": review_signal_shadow_safety_flags(),
    }


def _key_metrics(actual_keys: Any, expected_keys: Any) -> dict[str, Any]:
    actual = set(_normalize_key_set(actual_keys))
    expected = set(_normalize_key_set(expected_keys))
    return {
        "keys": sorted(actual),
        "expected_keys": sorted(expected),
        "tp": len(actual & expected),
        "fp": len(actual - expected),
        "fn": len(expected - actual),
        "tp_keys": sorted(actual & expected),
        "fp_keys": sorted(actual - expected),
        "fn_keys": sorted(expected - actual),
    }


def compare_baseline_to_signal_shadow(
    *,
    dataset: str,
    baseline_issue_keys: Any,
    baseline_label_keys: Any,
    projection: dict[str, Any],
    gold_fragments: list[dict[str, Any]],
    expected_issue_keys: Any | None = None,
    expected_label_keys: Any | None = None,
) -> dict[str, Any]:
    expected_from_gold = expected_customer_keys_from_gold(gold_fragments)
    gold_issue_keys = _normalize_key_set(
        expected_issue_keys if expected_issue_keys is not None else expected_from_gold["issue"]
    )
    gold_label_keys = _normalize_key_set(
        expected_label_keys if expected_label_keys is not None else expected_from_gold["label"]
    )
    signal_issue_keys = projection.get("signal_shadow_issue_keys") or []
    signal_label_keys = projection.get("signal_shadow_label_keys") or []

    baseline_issue = _key_metrics(baseline_issue_keys, gold_issue_keys)
    baseline_label = _key_metrics(baseline_label_keys, gold_label_keys)
    shadow_issue = _key_metrics(signal_issue_keys, gold_issue_keys)
    shadow_label = _key_metrics(signal_label_keys, gold_label_keys)

    blocked_issue_keys = {
        str(item.get("canonical_label_key") or "")
        for item in projection.get("blocked_or_unmatched_occurrences", [])
        if _normalize_label_type(item.get("label_type")) == "issue"
        and (
            "signal_gate_blocks_customer_issue" in item.get("blocked_reasons", [])
            or "evidence_not_found" in item.get("blocked_reasons", [])
            or "non_current_product_scope" in item.get("blocked_reasons", [])
        )
    }
    blocked_label_keys = {
        str(item.get("canonical_label_key") or "")
        for item in projection.get("blocked_or_unmatched_occurrences", [])
        if _normalize_label_type(item.get("label_type")) == "label"
        and (
            "signal_gate_blocks_customer_label" in item.get("blocked_reasons", [])
            or "evidence_not_found" in item.get("blocked_reasons", [])
            or "non_current_product_scope" in item.get("blocked_reasons", [])
        )
    }
    baseline_issue_fp_keys = set(baseline_issue["fp_keys"])
    baseline_label_fp_keys = set(baseline_label["fp_keys"])
    issue_routing_fp_keys = sorted(baseline_issue_fp_keys & blocked_issue_keys)
    label_routing_fp_keys = sorted(baseline_label_fp_keys & blocked_label_keys)
    issue_label_extraction_fn_keys = sorted(set(baseline_issue["fn_keys"]) & set(shadow_issue["tp_keys"]))
    label_label_extraction_fn_keys = sorted(set(baseline_label["fn_keys"]) & set(shadow_label["tp_keys"]))

    split_metrics = {
        "routing_fp": {
            "issue": len(issue_routing_fp_keys),
            "label": len(label_routing_fp_keys),
            "issue_keys": issue_routing_fp_keys,
            "label_keys": label_routing_fp_keys,
        },
        "routing_fn": {
            "issue": shadow_issue["fn"],
            "label": shadow_label["fn"],
            "issue_keys": shadow_issue["fn_keys"],
            "label_keys": shadow_label["fn_keys"],
        },
        "label_extraction_fp": {
            "issue": len(baseline_issue_fp_keys - set(issue_routing_fp_keys)),
            "label": len(baseline_label_fp_keys - set(label_routing_fp_keys)),
            "issue_keys": sorted(baseline_issue_fp_keys - set(issue_routing_fp_keys)),
            "label_keys": sorted(baseline_label_fp_keys - set(label_routing_fp_keys)),
        },
        "label_extraction_fn": {
            "issue": len(issue_label_extraction_fn_keys),
            "label": len(label_label_extraction_fn_keys),
            "issue_keys": issue_label_extraction_fn_keys,
            "label_keys": label_label_extraction_fn_keys,
        },
        "evidence_not_found_count": int(projection.get("evidence_not_found_count") or 0),
        "non_product_leakage_count": int(projection.get("non_product_leakage_count") or 0),
        "unresolved_mapping_count": int(projection.get("unresolved_mapping_count") or 0),
    }
    status = "PASS"
    if split_metrics["non_product_leakage_count"] or split_metrics["routing_fn"]["issue"] or split_metrics["routing_fn"]["label"]:
        status = "REVIEW_NEEDED"
    if split_metrics["unresolved_mapping_count"]:
        status = "REVIEW_NEEDED"

    return {
        "schema_version": REVIEW_SIGNAL_FP_FN_SCHEMA_VERSION,
        "ruleset_version": REVIEW_SIGNAL_RULESET_VERSION,
        "dataset": dataset,
        "status": status,
        "baseline": {
            "customer_issue_keys": baseline_issue["keys"],
            "customer_label_keys": baseline_label["keys"],
            "customer_issue": baseline_issue,
            "customer_label": baseline_label,
        },
        "signal_shadow": {
            "customer_issue_keys": shadow_issue["keys"],
            "customer_label_keys": shadow_label["keys"],
            "customer_issue": shadow_issue,
            "customer_label": shadow_label,
        },
        "fp_fn_delta": {
            "issue_fp_delta": shadow_issue["fp"] - baseline_issue["fp"],
            "issue_fn_delta": shadow_issue["fn"] - baseline_issue["fn"],
            "label_fp_delta": shadow_label["fp"] - baseline_label["fp"],
            "label_fn_delta": shadow_label["fn"] - baseline_label["fn"],
        },
        "split_metrics": split_metrics,
        "safety": review_signal_shadow_safety_flags(),
    }


def run_review_signal_shadow(
    review: dict[str, Any] | None = None,
    *,
    content: str | None = None,
    rating: int | float | None = None,
    review_id: Any = None,
    signal_candidates: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    source_review = copy.deepcopy(review or {})
    if content is not None:
        source_review["content"] = content
    if rating is not None:
        source_review["rating"] = rating
    if review_id is not None:
        source_review["id"] = review_id

    source_content = str(source_review.get("content") or "")
    resolved_review_id = source_review.get("id")
    candidates = copy.deepcopy(signal_candidates if signal_candidates is not None else source_review.get("review_signals") or [])
    review_signals = [
        normalize_review_signal_candidate(candidate, content=source_content, review_id=resolved_review_id).as_dict()
        for candidate in candidates
        if isinstance(candidate, dict)
    ]
    projection = build_review_signal_routing_projection(review_signals)
    signal_counts = Counter(signal["signal_type"] for signal in review_signals)
    route_counts = Counter(route for signal in review_signals for route in signal.get("route_to", []))

    return {
        "review_id": resolved_review_id,
        "schema_version": REVIEW_SIGNAL_SCHEMA_VERSION,
        "ruleset_version": REVIEW_SIGNAL_RULESET_VERSION,
        "source": "fixture_shadow",
        "rating": source_review.get("rating"),
        "review_signals": review_signals,
        "routing_projection": projection,
        "signal_counts_by_type": dict(sorted(signal_counts.items())),
        "route_counts": dict(sorted(route_counts.items())),
        "shadow_safety": review_signal_shadow_safety_flags(),
    }
