from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from backend_api.app.services.review_fragment_contract import (
    MODULE_ACCESSORY_OR_BUNDLE,
    MODULE_AUDIT_FILTER,
    MODULE_COMPARISON_OR_OTHER_PRODUCT,
    MODULE_CONSUMER_PROFILE,
    MODULE_LOGISTICS_SUPPORT,
    MODULE_PRODUCT_HIGHLIGHT,
    MODULE_PRODUCT_ISSUE,
    SCOPE_ACCESSORY_ONLY,
    SCOPE_CURRENT_PRODUCT,
    SCOPE_LOGISTICS_SUPPORT,
    SCOPE_NON_PRODUCT_CONTEXT,
    SCOPE_OTHER_PRODUCT,
    SCOPE_UNCLEAR,
)
from backend_api.app.services.taxonomy_loader import resolve_aspects

REVIEW_FRAGMENT_TAXONOMY_WHITELIST_VERSION = "review-fragment-taxonomy-whitelist.5.9.2"
REVIEW_FRAGMENT_TAXONOMY_FIXTURE_SCHEMA_VERSION = "review-fragment-taxonomy-whitelist-samples.5.9.2"

TAXONOMY_STATUS_ALLOWED = "allowed"
TAXONOMY_STATUS_OUT_OF_SCOPE = "taxonomy_out_of_scope"
TAXONOMY_STATUS_MISSING = "taxonomy_missing"

PRODUCT_TAXONOMY_MODULES = {MODULE_PRODUCT_ISSUE, MODULE_PRODUCT_HIGHLIGHT}
ACCESSORY_PACKAGING_TAXONOMY_MODULES = {MODULE_ACCESSORY_OR_BUNDLE, MODULE_LOGISTICS_SUPPORT}
AGGREGATABLE_TAXONOMY_MODULES = PRODUCT_TAXONOMY_MODULES | ACCESSORY_PACKAGING_TAXONOMY_MODULES
ACCESSORY_PACKAGING_ASPECT_KEYS = {
    "accessory_storage",
    "missing_parts",
    "packaging",
    "shipping_damage",
}
BLOCKED_NON_PRODUCT_MODULES = {
    MODULE_AUDIT_FILTER,
    MODULE_COMPARISON_OR_OTHER_PRODUCT,
    MODULE_CONSUMER_PROFILE,
}

AspectResolver = Callable[[str], tuple[list[dict[str, Any]], bool]]


@dataclass(frozen=True)
class ReviewFragmentTaxonomyWhitelist:
    category: str
    sub_category: str
    taxonomy_hit: bool
    allowed_aspect_keys: frozenset[str]
    taxonomy_source: str


@dataclass(frozen=True)
class ReviewFragmentTaxonomyDecision:
    status: str
    can_aggregate: bool
    reject_reason: str | None
    aspect_key: str


def _clean_string(value: Any) -> str:
    return str(value or "").strip()


def _clean_reject_reason(value: Any) -> str | None:
    text = _clean_string(value)
    return text or None


def _aspect_key_from_mapping(aspect: Mapping[str, Any]) -> str:
    return _clean_string(aspect.get("key") or aspect.get("aspect_key"))


def normalize_review_fragment_sub_category(category: Any, sub_category: Any) -> str:
    """Return the current product sub_category used for taxonomy lookup.

    The category is accepted for audit symmetry, but it is not a fallback label
    source. Without a concrete sub_category, 5.9.2 must fail closed.
    """

    _ = category
    return _clean_string(sub_category)


def allowed_aspect_keys_from_taxonomy_aspects(aspects: Sequence[Mapping[str, Any]]) -> frozenset[str]:
    keys: list[str] = []
    for aspect in aspects:
        key = _aspect_key_from_mapping(aspect)
        if not key or key == "other" or key.startswith("candidate:"):
            continue
        keys.append(key)
    return frozenset(keys)


def resolve_review_fragment_taxonomy_whitelist(
    *,
    category: Any,
    sub_category: Any,
    aspect_resolver: AspectResolver = resolve_aspects,
) -> ReviewFragmentTaxonomyWhitelist:
    normalized_sub_category = normalize_review_fragment_sub_category(category, sub_category)
    normalized_category = _clean_string(category)

    if not normalized_sub_category:
        return ReviewFragmentTaxonomyWhitelist(
            category=normalized_category,
            sub_category="",
            taxonomy_hit=False,
            allowed_aspect_keys=frozenset(),
            taxonomy_source="taxonomy_missing:sub_category_empty",
        )

    aspects, taxonomy_hit = aspect_resolver(normalized_sub_category)
    if not taxonomy_hit:
        return ReviewFragmentTaxonomyWhitelist(
            category=normalized_category,
            sub_category=normalized_sub_category,
            taxonomy_hit=False,
            allowed_aspect_keys=frozenset(),
            taxonomy_source="taxonomy_missing:category_aspect_taxonomy",
        )

    allowed_keys = allowed_aspect_keys_from_taxonomy_aspects(aspects)
    return ReviewFragmentTaxonomyWhitelist(
        category=normalized_category,
        sub_category=normalized_sub_category,
        taxonomy_hit=bool(allowed_keys),
        allowed_aspect_keys=allowed_keys,
        taxonomy_source="category_aspect_taxonomy",
    )


def _reject_reason_for_non_current_scope(module: str, scope: str, current_reason: str | None) -> str:
    if current_reason:
        return current_reason
    if module == MODULE_COMPARISON_OR_OTHER_PRODUCT or scope == SCOPE_OTHER_PRODUCT:
        return "other_product_or_competitor"
    if module == MODULE_ACCESSORY_OR_BUNDLE or scope == SCOPE_ACCESSORY_ONLY:
        return "accessory_only"
    if module == MODULE_LOGISTICS_SUPPORT or scope == SCOPE_LOGISTICS_SUPPORT:
        return "logistics_or_service"
    if module == MODULE_AUDIT_FILTER or scope == SCOPE_UNCLEAR:
        return "fragment_too_vague"
    if module == MODULE_CONSUMER_PROFILE or scope == SCOPE_NON_PRODUCT_CONTEXT:
        return "not_current_product"
    return "not_current_product"


def validate_review_fragment_taxonomy(
    fragment: Mapping[str, Any],
    whitelist: ReviewFragmentTaxonomyWhitelist,
) -> ReviewFragmentTaxonomyDecision:
    """Decide whether one fragment may enter product issue/highlight aggregation."""

    module = _clean_string(fragment.get("module"))
    scope = _clean_string(fragment.get("current_product_scope"))
    aspect_key = _clean_string(fragment.get("aspect_key"))
    current_reason = _clean_reject_reason(fragment.get("reject_reason"))
    requested_aggregate = fragment.get("can_aggregate") is True

    if module not in AGGREGATABLE_TAXONOMY_MODULES:
        reject_reason = _reject_reason_for_non_current_scope(module, scope, current_reason)
        return ReviewFragmentTaxonomyDecision(
            status=TAXONOMY_STATUS_OUT_OF_SCOPE,
            can_aggregate=False,
            reject_reason=reject_reason,
            aspect_key=aspect_key,
        )

    if module in PRODUCT_TAXONOMY_MODULES and scope != SCOPE_CURRENT_PRODUCT:
        reject_reason = _reject_reason_for_non_current_scope(module, scope, current_reason)
        return ReviewFragmentTaxonomyDecision(
            status=TAXONOMY_STATUS_OUT_OF_SCOPE,
            can_aggregate=False,
            reject_reason=reject_reason,
            aspect_key=aspect_key,
        )

    if module == MODULE_ACCESSORY_OR_BUNDLE and scope != SCOPE_ACCESSORY_ONLY:
        return ReviewFragmentTaxonomyDecision(
            status=TAXONOMY_STATUS_OUT_OF_SCOPE,
            can_aggregate=False,
            reject_reason=_reject_reason_for_non_current_scope(module, scope, current_reason),
            aspect_key=aspect_key,
        )

    if module == MODULE_LOGISTICS_SUPPORT and scope != SCOPE_LOGISTICS_SUPPORT:
        return ReviewFragmentTaxonomyDecision(
            status=TAXONOMY_STATUS_OUT_OF_SCOPE,
            can_aggregate=False,
            reject_reason=_reject_reason_for_non_current_scope(module, scope, current_reason),
            aspect_key=aspect_key,
        )

    if aspect_key.startswith("candidate:"):
        return ReviewFragmentTaxonomyDecision(
            status=TAXONOMY_STATUS_OUT_OF_SCOPE,
            can_aggregate=False,
            reject_reason="candidate_pending_review",
            aspect_key=aspect_key,
        )

    if not aspect_key or aspect_key == "other":
        return ReviewFragmentTaxonomyDecision(
            status=TAXONOMY_STATUS_OUT_OF_SCOPE,
            can_aggregate=False,
            reject_reason="taxonomy_out_of_scope",
            aspect_key=aspect_key,
        )

    if module in ACCESSORY_PACKAGING_TAXONOMY_MODULES and aspect_key not in ACCESSORY_PACKAGING_ASPECT_KEYS:
        return ReviewFragmentTaxonomyDecision(
            status=TAXONOMY_STATUS_OUT_OF_SCOPE,
            can_aggregate=False,
            reject_reason=current_reason or "taxonomy_out_of_scope",
            aspect_key=aspect_key,
        )

    if not whitelist.taxonomy_hit:
        return ReviewFragmentTaxonomyDecision(
            status=TAXONOMY_STATUS_MISSING,
            can_aggregate=False,
            reject_reason="taxonomy_missing",
            aspect_key=aspect_key,
        )

    if aspect_key not in whitelist.allowed_aspect_keys:
        return ReviewFragmentTaxonomyDecision(
            status=TAXONOMY_STATUS_OUT_OF_SCOPE,
            can_aggregate=False,
            reject_reason="taxonomy_out_of_scope",
            aspect_key=aspect_key,
        )

    return ReviewFragmentTaxonomyDecision(
        status=TAXONOMY_STATUS_ALLOWED,
        can_aggregate=requested_aggregate,
        reject_reason=None if requested_aggregate else current_reason,
        aspect_key=aspect_key,
    )


def apply_review_fragment_taxonomy_whitelist(
    fragment: Mapping[str, Any],
    whitelist: ReviewFragmentTaxonomyWhitelist,
) -> dict[str, Any]:
    decision = validate_review_fragment_taxonomy(fragment, whitelist)
    gated = dict(fragment)
    gated["can_aggregate"] = decision.can_aggregate
    gated["reject_reason"] = decision.reject_reason
    return gated


def review_fragment_taxonomy_result_row(
    fragment: Mapping[str, Any],
    whitelist: ReviewFragmentTaxonomyWhitelist,
) -> dict[str, Any]:
    decision = validate_review_fragment_taxonomy(fragment, whitelist)
    return {
        "status": decision.status,
        "can_aggregate": decision.can_aggregate,
        "reject_reason": decision.reject_reason,
        "aspect_key": decision.aspect_key,
        "taxonomy_hit": whitelist.taxonomy_hit,
    }
