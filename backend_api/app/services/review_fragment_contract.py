from __future__ import annotations

from collections.abc import Mapping
from typing import Any

REVIEW_FRAGMENT_CONTRACT_VERSION = "review-fragment-contract.5.9.1"
REVIEW_FRAGMENT_SAMPLE_SCHEMA_VERSION = "review-fragment-samples.5.9.1"

REVIEW_FRAGMENT_REQUIRED_FIELDS = (
    "fragment_text",
    "module",
    "aspect_key",
    "polarity",
    "evidence_span",
    "confidence",
    "current_product_scope",
    "can_aggregate",
    "reject_reason",
)

MODULE_PRODUCT_ISSUE = "product_issue"
MODULE_PRODUCT_HIGHLIGHT = "product_highlight"
MODULE_CONSUMER_PROFILE = "consumer_profile"
MODULE_PURCHASE_MOTIVE = "purchase_motive"
MODULE_UNMET_NEED = "unmet_need"
MODULE_COMPARISON_OR_OTHER_PRODUCT = "comparison_or_other_product"
MODULE_ACCESSORY_OR_BUNDLE = "accessory_or_bundle"
MODULE_LOGISTICS_SUPPORT = "logistics_support"
MODULE_OTHER_CANDIDATE = "other_candidate"
MODULE_AUDIT_FILTER = "audit_filter"

VALID_REVIEW_FRAGMENT_MODULES = {
    MODULE_PRODUCT_ISSUE,
    MODULE_PRODUCT_HIGHLIGHT,
    MODULE_CONSUMER_PROFILE,
    MODULE_PURCHASE_MOTIVE,
    MODULE_UNMET_NEED,
    MODULE_COMPARISON_OR_OTHER_PRODUCT,
    MODULE_ACCESSORY_OR_BUNDLE,
    MODULE_LOGISTICS_SUPPORT,
    MODULE_OTHER_CANDIDATE,
    MODULE_AUDIT_FILTER,
}

VALID_REVIEW_FRAGMENT_POLARITIES = {"positive", "negative", "mixed", "neutral"}

SCOPE_CURRENT_PRODUCT = "current_product"
SCOPE_CURRENT_PRODUCT_CONTEXT = "current_product_context"
SCOPE_NON_PRODUCT_CONTEXT = "non_product_context"
SCOPE_OTHER_PRODUCT = "other_product"
SCOPE_ACCESSORY_ONLY = "accessory_only"
SCOPE_LOGISTICS_SUPPORT = "logistics_support"
SCOPE_UNCLEAR = "unclear"

VALID_REVIEW_FRAGMENT_PRODUCT_SCOPES = {
    SCOPE_CURRENT_PRODUCT,
    SCOPE_CURRENT_PRODUCT_CONTEXT,
    SCOPE_NON_PRODUCT_CONTEXT,
    SCOPE_OTHER_PRODUCT,
    SCOPE_ACCESSORY_ONLY,
    SCOPE_LOGISTICS_SUPPORT,
    SCOPE_UNCLEAR,
}

VALID_REVIEW_FRAGMENT_REJECT_REASONS = {
    "accessory_only",
    "candidate_pending_review",
    "confidence_low",
    "evidence_missing",
    "evidence_not_found",
    "evidence_too_generic",
    "fragment_too_vague",
    "logistics_or_service",
    "not_current_product",
    "not_used_yet",
    "other_product_or_competitor",
    "schema_invalid",
    "taxonomy_missing",
    "taxonomy_out_of_scope",
}

MODULE_CONTRACT_POLICY = {
    MODULE_PRODUCT_ISSUE: {
        "allowed_scopes": {SCOPE_CURRENT_PRODUCT},
        "allowed_polarities": {"negative", "mixed"},
        "can_aggregate": True,
    },
    MODULE_PRODUCT_HIGHLIGHT: {
        "allowed_scopes": {SCOPE_CURRENT_PRODUCT},
        "allowed_polarities": {"positive", "mixed"},
        "can_aggregate": True,
    },
    MODULE_CONSUMER_PROFILE: {
        "allowed_scopes": {SCOPE_NON_PRODUCT_CONTEXT},
        "allowed_polarities": {"neutral", "mixed"},
        "can_aggregate": True,
    },
    MODULE_PURCHASE_MOTIVE: {
        "allowed_scopes": {SCOPE_CURRENT_PRODUCT_CONTEXT, SCOPE_NON_PRODUCT_CONTEXT},
        "allowed_polarities": {"neutral", "positive", "mixed"},
        "can_aggregate": True,
    },
    MODULE_UNMET_NEED: {
        "allowed_scopes": {SCOPE_CURRENT_PRODUCT_CONTEXT},
        "allowed_polarities": {"neutral", "negative", "mixed"},
        "can_aggregate": True,
    },
    MODULE_COMPARISON_OR_OTHER_PRODUCT: {
        "allowed_scopes": {SCOPE_OTHER_PRODUCT},
        "allowed_polarities": {"neutral", "positive", "negative", "mixed"},
        "can_aggregate": False,
    },
    MODULE_ACCESSORY_OR_BUNDLE: {
        "allowed_scopes": {SCOPE_ACCESSORY_ONLY},
        "allowed_polarities": {"neutral", "positive", "negative", "mixed"},
        "can_aggregate": False,
    },
    MODULE_LOGISTICS_SUPPORT: {
        "allowed_scopes": {SCOPE_LOGISTICS_SUPPORT},
        "allowed_polarities": {"neutral", "positive", "negative", "mixed"},
        "can_aggregate": False,
    },
    MODULE_OTHER_CANDIDATE: {
        "allowed_scopes": {SCOPE_CURRENT_PRODUCT, SCOPE_CURRENT_PRODUCT_CONTEXT},
        "allowed_polarities": {"neutral", "positive", "negative", "mixed"},
        "can_aggregate": False,
    },
    MODULE_AUDIT_FILTER: {
        "allowed_scopes": {
            SCOPE_ACCESSORY_ONLY,
            SCOPE_LOGISTICS_SUPPORT,
            SCOPE_OTHER_PRODUCT,
            SCOPE_UNCLEAR,
        },
        "allowed_polarities": {"neutral", "positive", "negative", "mixed"},
        "can_aggregate": False,
    },
}


def _clean_text(value: Any) -> str:
    return str(value or "").strip()


def _contains_text(haystack: str, needle: str) -> bool:
    if not haystack or not needle:
        return False
    return needle in haystack or needle.lower() in haystack.lower()


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def validate_review_fragment(fragment: Mapping[str, Any]) -> list[str]:
    """Validate one 5.9.1 fragment contract record without touching runtime behavior."""

    errors: list[str] = []
    if not isinstance(fragment, Mapping):
        return ["fragment_not_object"]

    fields = set(fragment)
    for field in REVIEW_FRAGMENT_REQUIRED_FIELDS:
        if field not in fields:
            errors.append(f"missing_field:{field}")
    for field in sorted(fields - set(REVIEW_FRAGMENT_REQUIRED_FIELDS)):
        errors.append(f"unexpected_field:{field}")

    fragment_text = _clean_text(fragment.get("fragment_text"))
    evidence_span = _clean_text(fragment.get("evidence_span"))
    module = _clean_text(fragment.get("module"))
    aspect_key = _clean_text(fragment.get("aspect_key"))
    polarity = _clean_text(fragment.get("polarity"))
    scope = _clean_text(fragment.get("current_product_scope"))
    reject_reason = _clean_text(fragment.get("reject_reason"))
    can_aggregate = fragment.get("can_aggregate")
    confidence = fragment.get("confidence")

    if not fragment_text:
        errors.append("fragment_text_required")
    if not evidence_span:
        errors.append("evidence_span_required")
    elif fragment_text and not _contains_text(fragment_text, evidence_span):
        errors.append("evidence_span_not_in_fragment")

    if module not in VALID_REVIEW_FRAGMENT_MODULES:
        errors.append("module_invalid")
    if polarity not in VALID_REVIEW_FRAGMENT_POLARITIES:
        errors.append("polarity_invalid")
    if scope not in VALID_REVIEW_FRAGMENT_PRODUCT_SCOPES:
        errors.append("current_product_scope_invalid")
    if not _is_number(confidence) or not 0 <= float(confidence) <= 1:
        errors.append("confidence_out_of_range")
    if not isinstance(can_aggregate, bool):
        errors.append("can_aggregate_not_bool")

    if can_aggregate is True:
        if not aspect_key:
            errors.append("aspect_key_required_for_aggregate")
        if aspect_key == "other" or aspect_key.startswith("candidate:"):
            errors.append("unapproved_aspect_cannot_aggregate")
        if reject_reason:
            errors.append("reject_reason_must_be_empty_for_aggregate")
    elif can_aggregate is False:
        if not reject_reason:
            errors.append("reject_reason_required")
        elif reject_reason not in VALID_REVIEW_FRAGMENT_REJECT_REASONS:
            errors.append("reject_reason_invalid")

    policy = MODULE_CONTRACT_POLICY.get(module)
    if policy:
        if scope and scope not in policy["allowed_scopes"]:
            errors.append("scope_invalid_for_module")
        if polarity and polarity not in policy["allowed_polarities"]:
            errors.append("polarity_invalid_for_module")
        if can_aggregate is True and policy["can_aggregate"] is False:
            errors.append("module_cannot_aggregate")

    return errors


def validate_review_fragment_sample(sample: Mapping[str, Any]) -> list[str]:
    errors: list[str] = []
    if not isinstance(sample, Mapping):
        return ["sample_not_object"]

    for field in ("id", "content", "category", "sub_category", "fragments"):
        if field not in sample:
            errors.append(f"missing_sample_field:{field}")

    content = _clean_text(sample.get("content"))
    if not content:
        errors.append("sample_content_required")

    fragments = sample.get("fragments")
    if not isinstance(fragments, list) or not fragments:
        errors.append("sample_fragments_required")
        return errors

    seen_aggregate_keys: dict[tuple[str, str, str], int] = {}
    for index, fragment in enumerate(fragments):
        fragment_errors = validate_review_fragment(fragment)
        errors.extend(f"fragments[{index}].{error}" for error in fragment_errors)
        fragment_text = _clean_text(fragment.get("fragment_text") if isinstance(fragment, Mapping) else "")
        evidence_span = _clean_text(fragment.get("evidence_span") if isinstance(fragment, Mapping) else "")
        if content and fragment_text and not _contains_text(content, fragment_text):
            errors.append(f"fragments[{index}].fragment_text_not_in_review")
        if content and evidence_span and not _contains_text(content, evidence_span):
            errors.append(f"fragments[{index}].evidence_span_not_in_review")
        if isinstance(fragment, Mapping) and fragment.get("can_aggregate") is True:
            aggregate_key = (
                _clean_text(fragment.get("module")),
                _clean_text(fragment.get("aspect_key")),
                _clean_text(fragment.get("polarity")),
            )
            if all(aggregate_key):
                if aggregate_key in seen_aggregate_keys:
                    errors.append(f"fragments[{index}].duplicate_aggregate_aspect")
                else:
                    seen_aggregate_keys[aggregate_key] = index

    return errors


def validate_review_fragment_fixture(fixture: Mapping[str, Any]) -> list[str]:
    errors: list[str] = []
    if not isinstance(fixture, Mapping):
        return ["fixture_not_object"]

    schema_version = _clean_text(fixture.get("schema_version"))
    if schema_version != REVIEW_FRAGMENT_SAMPLE_SCHEMA_VERSION:
        errors.append("schema_version_invalid")

    samples = fixture.get("samples")
    if not isinstance(samples, list) or not samples:
        errors.append("samples_required")
        return errors

    for index, sample in enumerate(samples):
        sample_errors = validate_review_fragment_sample(sample)
        errors.extend(f"samples[{index}].{error}" for error in sample_errors)

    return errors
