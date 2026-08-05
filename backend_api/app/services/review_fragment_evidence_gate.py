from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from backend_api.app.services.review_fragment_contract import (
    MODULE_ACCESSORY_OR_BUNDLE,
    MODULE_AUDIT_FILTER,
    MODULE_COMPARISON_OR_OTHER_PRODUCT,
    MODULE_LOGISTICS_SUPPORT,
    MODULE_OTHER_CANDIDATE,
    MODULE_PRODUCT_HIGHLIGHT,
    MODULE_PRODUCT_ISSUE,
    SCOPE_ACCESSORY_ONLY,
    SCOPE_CURRENT_PRODUCT,
    SCOPE_LOGISTICS_SUPPORT,
    SCOPE_OTHER_PRODUCT,
    SCOPE_UNCLEAR,
)
from backend_api.app.services.review_fragment_taxonomy_whitelist import (
    ACCESSORY_PACKAGING_ASPECT_KEYS,
    TAXONOMY_STATUS_ALLOWED,
    ReviewFragmentTaxonomyWhitelist,
    validate_review_fragment_taxonomy,
)

REVIEW_FRAGMENT_EVIDENCE_GATE_VERSION = "review-fragment-evidence-gate.5.9.3"
REVIEW_FRAGMENT_EVIDENCE_FIXTURE_SCHEMA_VERSION = "review-fragment-evidence-gate-samples.5.9.3"

EVIDENCE_SOURCE_FRAGMENT_TEXT = "fragment_text"
EVIDENCE_SOURCE_REVIEW_TEXT = "review_text"
EVIDENCE_SOURCE_EMPTY = "empty"
EVIDENCE_SOURCE_NOT_FOUND = "not_found"

EVIDENCE_REJECT_MISSING = "evidence_missing"
EVIDENCE_REJECT_NOT_FOUND = "evidence_not_found"
EVIDENCE_REJECT_TOO_GENERIC = "evidence_too_generic"

FORMAL_EVIDENCE_GATE_MODULES = {
    MODULE_PRODUCT_ISSUE,
    MODULE_PRODUCT_HIGHLIGHT,
    MODULE_ACCESSORY_OR_BUNDLE,
    MODULE_LOGISTICS_SUPPORT,
}

PRODUCT_EXPERIENCE_MODULES = {MODULE_PRODUCT_ISSUE, MODULE_PRODUCT_HIGHLIGHT}

GENERIC_EVIDENCE_SPANS = {
    "amazing",
    "awesome",
    "bad",
    "excellent",
    "good",
    "good product",
    "great",
    "great product",
    "horrible",
    "i like it",
    "i love it",
    "love it",
    "nice",
    "nice product",
    "overall good",
    "poor",
    "terrible",
    "very good",
}

OLD_OR_COMPETITOR_MARKERS = (
    "brand x",
    "compared with",
    "compared to",
    "competitor",
    "last pair",
    "old airpod",
    "old pair",
    "old product",
    "old wader",
    "other brand",
    "previous pair",
    "previous wader",
)

ACCESSORY_MARKERS = (
    "accessory",
    "case cover",
    "hanger",
    "missing part",
    "missing parts",
    "patch",
    "phone case",
    "phone pouch",
    "phone protector",
    "pocket",
    "repair patch",
    "storage bag",
)

LOGISTICS_OR_SERVICE_MARKERS = (
    "arrived",
    "box",
    "customer service",
    "customer support",
    "delivered late",
    "delivery",
    "package",
    "packaging",
    "refund",
    "return",
    "return window",
    "returned",
    "seller",
    "shipping",
)

NOT_USED_MARKERS = (
    "have not used",
    "haven't used",
    "not tested",
    "not used",
    "not used yet",
)


@dataclass(frozen=True)
class ReviewFragmentEvidenceDecision:
    evidence_valid: bool
    evidence_source: str
    can_aggregate: bool
    reject_reason: str | None
    taxonomy_status: str | None


def _clean_string(value: Any) -> str:
    return str(value or "").strip()


def _normalize_text(value: Any) -> str:
    text = _clean_string(value).casefold()
    return re.sub(r"\s+", " ", text).strip()


def _contains_text(haystack: str, needle: str) -> bool:
    normalized_haystack = _normalize_text(haystack)
    normalized_needle = _normalize_text(needle)
    if not normalized_haystack or not normalized_needle:
        return False
    return normalized_needle in normalized_haystack


def _contains_any_marker(text: str, markers: tuple[str, ...]) -> bool:
    normalized = _normalize_text(text)
    return any(marker in normalized for marker in markers)


def _resolve_evidence_source(fragment_text: Any, review_text: Any, evidence_span: Any) -> tuple[bool, str]:
    evidence = _clean_string(evidence_span)
    if not evidence:
        return False, EVIDENCE_SOURCE_EMPTY
    if _contains_text(_clean_string(fragment_text), evidence):
        return True, EVIDENCE_SOURCE_FRAGMENT_TEXT
    if _contains_text(_clean_string(review_text), evidence):
        return True, EVIDENCE_SOURCE_REVIEW_TEXT
    return False, EVIDENCE_SOURCE_NOT_FOUND


def _evidence_not_found_reject_reason(evidence_source: str) -> str | None:
    if evidence_source == EVIDENCE_SOURCE_EMPTY:
        return EVIDENCE_REJECT_MISSING
    if evidence_source == EVIDENCE_SOURCE_NOT_FOUND:
        return EVIDENCE_REJECT_NOT_FOUND
    return None


def _is_generic_hard_split(fragment: Mapping[str, Any]) -> bool:
    module = _clean_string(fragment.get("module"))
    if module not in PRODUCT_EXPERIENCE_MODULES or fragment.get("can_aggregate") is not True:
        return False
    evidence = _normalize_text(fragment.get("evidence_span"))
    if evidence not in GENERIC_EVIDENCE_SPANS:
        return False
    aspect_key = _clean_string(fragment.get("aspect_key"))
    return aspect_key not in {"", "other", "overall_satisfied"}


def _delivery_quality_aspect(aspect_key: str) -> bool:
    return aspect_key in {"logistics_issue", "packaging"}


def _accessory_quality_aspect(aspect_key: str) -> bool:
    return aspect_key in ACCESSORY_PACKAGING_ASPECT_KEYS


def _scope_or_pollution_reject_reason(fragment: Mapping[str, Any]) -> str | None:
    module = _clean_string(fragment.get("module"))
    scope = _clean_string(fragment.get("current_product_scope"))
    aspect_key = _clean_string(fragment.get("aspect_key"))
    current_reason = _clean_string(fragment.get("reject_reason"))
    fragment_text = _clean_string(fragment.get("fragment_text"))
    evidence_span = _clean_string(fragment.get("evidence_span"))
    context = f"{fragment_text} {evidence_span}"

    if current_reason:
        return current_reason
    if module == MODULE_COMPARISON_OR_OTHER_PRODUCT or scope == SCOPE_OTHER_PRODUCT:
        return "other_product_or_competitor"
    if module == MODULE_AUDIT_FILTER or scope == SCOPE_UNCLEAR:
        return "fragment_too_vague"
    if module == MODULE_OTHER_CANDIDATE:
        return "candidate_pending_review"

    if module in PRODUCT_EXPERIENCE_MODULES:
        if scope != SCOPE_CURRENT_PRODUCT:
            if scope == SCOPE_ACCESSORY_ONLY:
                return "accessory_only"
            if scope == SCOPE_LOGISTICS_SUPPORT:
                return "logistics_or_service"
            return "not_current_product"
        if _contains_any_marker(context, OLD_OR_COMPETITOR_MARKERS):
            return "other_product_or_competitor"
        if _contains_any_marker(context, NOT_USED_MARKERS):
            return "not_used_yet"
        if _contains_any_marker(context, ACCESSORY_MARKERS):
            return "accessory_only"
        if _contains_any_marker(context, LOGISTICS_OR_SERVICE_MARKERS):
            return "logistics_or_service"

    if module == MODULE_ACCESSORY_OR_BUNDLE:
        if scope != SCOPE_ACCESSORY_ONLY:
            return "not_current_product"
        if not _accessory_quality_aspect(aspect_key):
            return "accessory_only"
        if not _contains_any_marker(context, ACCESSORY_MARKERS):
            return "accessory_only"

    if module == MODULE_LOGISTICS_SUPPORT:
        if scope != SCOPE_LOGISTICS_SUPPORT:
            return "not_current_product"
        if not _delivery_quality_aspect(aspect_key):
            return "logistics_or_service"
        if not _contains_any_marker(context, LOGISTICS_OR_SERVICE_MARKERS):
            return "logistics_or_service"

    return None


def validate_review_fragment_evidence(
    fragment: Mapping[str, Any],
    *,
    review_text: Any,
    whitelist: ReviewFragmentTaxonomyWhitelist | None = None,
) -> ReviewFragmentEvidenceDecision:
    """Apply the 5.9.3 original-text evidence gate to one experimental fragment."""

    evidence_valid, evidence_source = _resolve_evidence_source(
        fragment.get("fragment_text"),
        review_text,
        fragment.get("evidence_span"),
    )
    evidence_reject_reason = _evidence_not_found_reject_reason(evidence_source)
    if evidence_reject_reason:
        return ReviewFragmentEvidenceDecision(
            evidence_valid=False,
            evidence_source=evidence_source,
            can_aggregate=False,
            reject_reason=evidence_reject_reason,
            taxonomy_status=None,
        )

    if _is_generic_hard_split(fragment):
        return ReviewFragmentEvidenceDecision(
            evidence_valid=False,
            evidence_source=evidence_source,
            can_aggregate=False,
            reject_reason=EVIDENCE_REJECT_TOO_GENERIC,
            taxonomy_status=None,
        )

    scope_reject_reason = _scope_or_pollution_reject_reason(fragment)
    if scope_reject_reason:
        return ReviewFragmentEvidenceDecision(
            evidence_valid=evidence_valid,
            evidence_source=evidence_source,
            can_aggregate=False,
            reject_reason=scope_reject_reason,
            taxonomy_status=None,
        )

    if whitelist is not None:
        taxonomy_decision = validate_review_fragment_taxonomy(fragment, whitelist)
        if taxonomy_decision.status != TAXONOMY_STATUS_ALLOWED or taxonomy_decision.can_aggregate is not True:
            return ReviewFragmentEvidenceDecision(
                evidence_valid=evidence_valid,
                evidence_source=evidence_source,
                can_aggregate=False,
                reject_reason=taxonomy_decision.reject_reason,
                taxonomy_status=taxonomy_decision.status,
            )
        return ReviewFragmentEvidenceDecision(
            evidence_valid=evidence_valid,
            evidence_source=evidence_source,
            can_aggregate=True,
            reject_reason=None,
            taxonomy_status=taxonomy_decision.status,
        )

    requested_aggregate = fragment.get("can_aggregate") is True
    return ReviewFragmentEvidenceDecision(
        evidence_valid=evidence_valid,
        evidence_source=evidence_source,
        can_aggregate=requested_aggregate,
        reject_reason=None if requested_aggregate else _clean_string(fragment.get("reject_reason")) or None,
        taxonomy_status=None,
    )


def apply_review_fragment_evidence_gate(
    fragment: Mapping[str, Any],
    *,
    review_text: Any,
    whitelist: ReviewFragmentTaxonomyWhitelist | None = None,
) -> dict[str, Any]:
    decision = validate_review_fragment_evidence(fragment, review_text=review_text, whitelist=whitelist)
    gated = dict(fragment)
    gated["evidence_valid"] = decision.evidence_valid
    gated["evidence_source"] = decision.evidence_source
    gated["can_aggregate"] = decision.can_aggregate
    gated["reject_reason"] = decision.reject_reason
    return gated


def review_fragment_evidence_result_row(
    fragment: Mapping[str, Any],
    *,
    review_text: Any,
    whitelist: ReviewFragmentTaxonomyWhitelist | None = None,
) -> dict[str, Any]:
    decision = validate_review_fragment_evidence(fragment, review_text=review_text, whitelist=whitelist)
    return {
        "evidence_valid": decision.evidence_valid,
        "evidence_source": decision.evidence_source,
        "can_aggregate": decision.can_aggregate,
        "reject_reason": decision.reject_reason,
        "taxonomy_status": decision.taxonomy_status,
    }
