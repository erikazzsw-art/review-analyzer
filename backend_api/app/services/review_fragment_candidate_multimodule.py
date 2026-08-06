from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from backend_api.app.services.review_fragment_contract import (
    MODULE_ACCESSORY_OR_BUNDLE,
    MODULE_AUDIT_FILTER,
    MODULE_COMPARISON_OR_OTHER_PRODUCT,
    MODULE_CONSUMER_PROFILE,
    MODULE_LOGISTICS_SUPPORT,
    MODULE_OTHER_CANDIDATE,
    MODULE_PRODUCT_HIGHLIGHT,
    MODULE_PRODUCT_ISSUE,
    MODULE_PURCHASE_MOTIVE,
    MODULE_UNMET_NEED,
    VALID_REVIEW_FRAGMENT_MODULES,
    VALID_REVIEW_FRAGMENT_POLARITIES,
    VALID_REVIEW_FRAGMENT_REJECT_REASONS,
)
from backend_api.app.services.review_fragment_evidence_gate import (
    FORMAL_EVIDENCE_GATE_MODULES,
    validate_review_fragment_evidence,
)
from backend_api.app.services.review_fragment_label_catalog import (
    FormalLabelDefinition,
    get_approved_formal_labels,
    resolve_formal_label,
    resolve_formal_label_aspect,
    resolve_highlight_for_aspect,
)
from backend_api.app.services.review_fragment_taxonomy_whitelist import (
    AGGREGATABLE_TAXONOMY_MODULES,
    TAXONOMY_STATUS_ALLOWED,
    AspectResolver,
    ReviewFragmentTaxonomyWhitelist,
    resolve_review_fragment_taxonomy_whitelist,
    validate_review_fragment_taxonomy,
)
from backend_api.app.services.taxonomy_loader import resolve_aspects

REVIEW_FRAGMENT_CANDIDATE_MULTIMODULE_VERSION = "review-fragment-candidate-multimodule.5.9.5.1"
REVIEW_FRAGMENT_CANDIDATE_FIXTURE_SCHEMA_VERSION = "review-fragment-candidate-multimodule-samples.5.9.5.1"

MODULE_USE_CASE_SEED = "use_case"
MODULE_CUSTOMER_SERVICE = "customer_service"

CANDIDATE_REASON_TAXONOMY_OUT_OF_SCOPE = "taxonomy_out_of_scope"
CANDIDATE_REASON_TAXONOMY_MISSING = "taxonomy_missing"
CANDIDATE_REASON_CANDIDATE_PENDING_REVIEW = "candidate_pending_review"
CANDIDATE_REASON_SEED_OUT_OF_SCOPE = "seed_taxonomy_out_of_scope"
CANDIDATE_REASON_UNMET_NEED_FIRST = "unmet_need_candidate_first"

FORMAL_TOP10_MODULES = {
    MODULE_PRODUCT_ISSUE,
    MODULE_PRODUCT_HIGHLIGHT,
}
FINAL_ARTIFACT_MODULES = frozenset(
    {
        MODULE_PRODUCT_ISSUE,
        MODULE_PRODUCT_HIGHLIGHT,
        MODULE_CONSUMER_PROFILE,
        MODULE_PURCHASE_MOTIVE,
        MODULE_UNMET_NEED,
        MODULE_AUDIT_FILTER,
    }
)
COMPATIBILITY_INPUT_MODULES = frozenset(
    {
        MODULE_ACCESSORY_OR_BUNDLE,
        MODULE_LOGISTICS_SUPPORT,
        MODULE_COMPARISON_OR_OTHER_PRODUCT,
        MODULE_OTHER_CANDIDATE,
        MODULE_CUSTOMER_SERVICE,
    }
)
ARTIFACT_INPUT_MODULES = frozenset(VALID_REVIEW_FRAGMENT_MODULES) | COMPATIBILITY_INPUT_MODULES
VALID_ARTIFACT_REJECT_REASONS = frozenset(VALID_REVIEW_FRAGMENT_REJECT_REASONS) | {
    CANDIDATE_REASON_SEED_OUT_OF_SCOPE,
    CANDIDATE_REASON_UNMET_NEED_FIRST,
}
ARTIFACT_ROW_BUCKETS = (
    "formal_top10_rows",
    "module_seed_rows",
    "candidate_rows",
    "audit_rows",
)
ARTIFACT_ROUTE_BUCKETS = {
    "formal": "formal_top10_rows",
    "module": "module_seed_rows",
    "candidate": "candidate_rows",
    "audit": "audit_rows",
}

PRODUCT_USE_CASE_HINT_ASPECTS = {
    "best_for_use_case",
    "great_for_use_case",
    "use_case",
    "use_case_fit",
    "use_case_success",
    "works_well_for_use_case",
}


@dataclass(frozen=True)
class SeedLabel:
    key: str
    aliases: tuple[str, ...]


@dataclass(frozen=True)
class SeedMatch:
    module: str
    label: SeedLabel


FormalLabel = FormalLabelDefinition
APPROVED_ISSUE_KEYS = frozenset(
    label.key for label in get_approved_formal_labels() if label.label_type == "issue"
)
APPROVED_HIGHLIGHT_KEYS = frozenset(
    label.key for label in get_approved_formal_labels() if label.label_type == "highlight"
)

CONSUMER_PROFILE_SEED_TAXONOMY: tuple[SeedLabel, ...] = (
    SeedLabel(
        key="family_buyer",
        aliases=(
            "child",
            "children",
            "daughter",
            "family",
            "husband",
            "kid",
            "kids",
            "my son",
            "son",
            "teenage son",
            "wife",
        ),
    ),
    SeedLabel(
        key="outdoor_recreation_user",
        aliases=(
            "angler",
            "fisherman",
            "fishing trip",
            "hunter",
            "outdoorsman",
            "river guide",
        ),
    ),
    SeedLabel(
        key="worker_or_professional",
        aliases=(
            "construction",
            "farm work",
            "for work",
            "job site",
            "worker",
        ),
    ),
    SeedLabel(
        key="student",
        aliases=(
            "college",
            "school",
            "student",
        ),
    ),
)

USE_CASE_SEED_TAXONOMY: tuple[SeedLabel, ...] = (
    SeedLabel(
        key="fishing",
        aliases=(
            "fly fishing",
            "fishing",
            "fishing trip",
            "river fishing",
            "surf fishing",
            "wade fishing",
        ),
    ),
    SeedLabel(
        key="hunting",
        aliases=(
            "duck hunting",
            "hunting",
        ),
    ),
    SeedLabel(
        key="camping",
        aliases=(
            "camping",
            "camping trip",
        ),
    ),
    SeedLabel(
        key="daily_use",
        aliases=(
            "daily use",
            "every day",
            "everyday",
        ),
    ),
    SeedLabel(
        key="travel",
        aliases=(
            "travel",
            "trip",
        ),
    ),
)

PURCHASE_MOTIVE_SEED_TAXONOMY: tuple[SeedLabel, ...] = (
    SeedLabel(
        key="price_value",
        aliases=(
            "affordable",
            "budget",
            "for the price",
            "great deal",
            "price was right",
            "value",
        ),
    ),
    SeedLabel(
        key="replacement",
        aliases=(
            "needed a new",
            "replace",
            "replaced my old",
            "replacement",
        ),
    ),
    SeedLabel(
        key="gift",
        aliases=(
            "bought as a gift",
            "bought for",
            "gift",
            "present",
        ),
    ),
    SeedLabel(
        key="feature_driven",
        aliases=(
            "because it has",
            "for the pockets",
            "phone pouch",
            "wanted the",
        ),
    ),
    SeedLabel(
        key="brand_trust",
        aliases=(
            "brand",
            "brand trust",
            "same brand",
        ),
    ),
)


def _clean_string(value: Any) -> str:
    return str(value or "").strip()


def _normalize_free_text(value: Any) -> str:
    text = _clean_string(value).casefold()
    return re.sub(r"\s+", " ", text).strip()


def _contains_any_marker(text: str, markers: Sequence[str]) -> bool:
    return any(_normalize_free_text(marker) in text for marker in markers)


def normalize_review_fragment_candidate_label(value: Any) -> str:
    text = _clean_string(value).casefold()
    for prefix in ("candidate:", "consumer_profile:", "purchase_motive:", "use_case:", "unmet_need:"):
        if text.startswith(prefix):
            text = text[len(prefix) :]
            break
    normalized = re.sub(r"[^a-z0-9]+", "_", text).strip("_")
    return normalized or "other"


def _candidate_label_from_fragment(fragment: Mapping[str, Any]) -> str:
    aspect_key = _clean_string(fragment.get("aspect_key"))
    if aspect_key and aspect_key != "other":
        return aspect_key.removeprefix("candidate:")

    evidence_span = _clean_string(fragment.get("evidence_span"))
    if evidence_span:
        return evidence_span

    fragment_text = _clean_string(fragment.get("fragment_text"))
    return fragment_text or "other"


def _seed_context(fragment: Mapping[str, Any]) -> str:
    parts = (
        _candidate_label_from_fragment(fragment),
        _clean_string(fragment.get("aspect_key")),
        _clean_string(fragment.get("evidence_span")),
        _clean_string(fragment.get("fragment_text")),
    )
    return _normalize_free_text(" ".join(part for part in parts if part))


def _seed_matches(fragment: Mapping[str, Any], seeds: Sequence[SeedLabel]) -> SeedLabel | None:
    context = _seed_context(fragment)
    normalized_candidate = normalize_review_fragment_candidate_label(_candidate_label_from_fragment(fragment))

    for seed in seeds:
        if normalized_candidate == seed.key:
            return seed
        for alias in seed.aliases:
            if normalize_review_fragment_candidate_label(alias) == normalized_candidate:
                return seed
            if _normalize_free_text(alias) in context:
                return seed
    return None


def _consumer_profile_seed_match(fragment: Mapping[str, Any]) -> SeedMatch | None:
    profile = _seed_matches(fragment, CONSUMER_PROFILE_SEED_TAXONOMY)
    if profile:
        return SeedMatch(module=MODULE_CONSUMER_PROFILE, label=profile)

    use_case = _seed_matches(fragment, USE_CASE_SEED_TAXONOMY)
    if use_case:
        return SeedMatch(module=MODULE_USE_CASE_SEED, label=use_case)

    return None


def _purchase_motive_seed_match(fragment: Mapping[str, Any]) -> SeedMatch | None:
    motive = _seed_matches(fragment, PURCHASE_MOTIVE_SEED_TAXONOMY)
    if motive:
        return SeedMatch(module=MODULE_PURCHASE_MOTIVE, label=motive)
    return None


def _product_out_of_scope_seed_match(fragment: Mapping[str, Any]) -> SeedMatch | None:
    aspect_key = normalize_review_fragment_candidate_label(fragment.get("aspect_key"))
    if aspect_key not in PRODUCT_USE_CASE_HINT_ASPECTS:
        return None

    use_case = _seed_matches(fragment, USE_CASE_SEED_TAXONOMY)
    if use_case:
        return SeedMatch(module=MODULE_USE_CASE_SEED, label=use_case)
    return _consumer_profile_seed_match(fragment)


def _fragment_context(fragment: Mapping[str, Any]) -> str:
    return _normalize_free_text(
        " ".join(
            part
            for part in (
                _clean_string(fragment.get("fragment_text")),
                _clean_string(fragment.get("evidence_span")),
                _clean_string(fragment.get("aspect_key")),
            )
            if part
        )
    )


def _is_negative_or_mixed(fragment: Mapping[str, Any]) -> bool:
    return _clean_string(fragment.get("polarity")) in {"negative", "mixed"}


def _business_module_for_fragment(fragment: Mapping[str, Any], *, fallback: str = "") -> str:
    """Normalize legacy routing buckets into the six business modules."""

    source_module = _clean_string(fragment.get("module")) or fallback
    polarity = _clean_string(fragment.get("polarity"))
    if source_module == MODULE_COMPARISON_OR_OTHER_PRODUCT:
        return MODULE_AUDIT_FILTER
    if source_module == MODULE_OTHER_CANDIDATE:
        return MODULE_AUDIT_FILTER
    if source_module in {MODULE_ACCESSORY_OR_BUNDLE, MODULE_LOGISTICS_SUPPORT, MODULE_CUSTOMER_SERVICE}:
        return MODULE_PRODUCT_ISSUE if polarity in {"negative", "mixed"} else MODULE_PRODUCT_HIGHLIGHT
    if source_module in {MODULE_PRODUCT_ISSUE, MODULE_PRODUCT_HIGHLIGHT, MODULE_CONSUMER_PROFILE,
                         MODULE_PURCHASE_MOTIVE, MODULE_UNMET_NEED, MODULE_AUDIT_FILTER}:
        return source_module
    return MODULE_AUDIT_FILTER


def _approved_aspect_key(
    fragment: Mapping[str, Any],
    *,
    label: FormalLabel,
    whitelist: ReviewFragmentTaxonomyWhitelist,
    category_key: str = "",
) -> str | None:
    return resolve_formal_label_aspect(
        label.key,
        source_aspect_key=fragment.get("aspect_key"),
        allowed_aspect_keys=whitelist.allowed_aspect_keys,
        label_type=label.label_type,
        category_key=category_key,
        sub_category_key=whitelist.sub_category,
    )


def _approved_label(key: str, *, label_type: str, category_key: str, sub_category_key: str) -> FormalLabel | None:
    result = resolve_formal_label(
        key,
        label_type=label_type,
        category_key=category_key,
        sub_category_key=sub_category_key,
    )
    return result.label


def _approved_formal_label_for_fragment(
    fragment: Mapping[str, Any],
    *,
    whitelist: ReviewFragmentTaxonomyWhitelist,
) -> tuple[FormalLabel, str] | None:
    polarity = _clean_string(fragment.get("polarity"))
    if polarity not in {"positive", "negative", "mixed"}:
        return None

    module = _clean_string(fragment.get("module"))
    scope = _clean_string(fragment.get("current_product_scope"))
    context = _fragment_context(fragment)
    if scope not in {"current_product", "current_product_context", "logistics_support", "accessory_only"}:
        return None

    category_key = whitelist.category
    sub_category_key = whitelist.sub_category

    service_context = _contains_any_marker(
        context,
        (
            "customer service",
            "customer support",
            "after-sales",
            "after sales",
        ),
    )
    if service_context and polarity == "positive":
        label = _approved_label("customer_service_helpful", label_type="highlight", category_key=category_key, sub_category_key=sub_category_key)
        if label:
            aspect_key = _approved_aspect_key(fragment, label=label, whitelist=whitelist, category_key=category_key)
            if aspect_key:
                return label, aspect_key

    if service_context and polarity in {"negative", "mixed"}:
        label = _approved_label("customer_service_unresponsive", label_type="issue", category_key=category_key, sub_category_key=sub_category_key)
        if label:
            aspect_key = _approved_aspect_key(fragment, label=label, whitelist=whitelist, category_key=category_key)
            if aspect_key:
                return label, aspect_key

    if polarity not in {"negative", "mixed"}:
        return None

    if module in {MODULE_LOGISTICS_SUPPORT, MODULE_PRODUCT_ISSUE, MODULE_OTHER_CANDIDATE} and _contains_any_marker(
        context,
        (
            "arrived crushed",
            "arrived damaged",
            "arrived used",
            "box arrived crushed",
            "box was crushed",
            "damaged on arrival",
            "package damaged",
            "shipping damage",
        ),
    ):
        label = _approved_label("shipping_damage", label_type="issue", category_key=category_key, sub_category_key=sub_category_key)
        if label:
            aspect_key = _approved_aspect_key(fragment, label=label, whitelist=whitelist, category_key=category_key)
            if aspect_key:
                return label, aspect_key

    if module in {MODULE_LOGISTICS_SUPPORT, MODULE_PRODUCT_ISSUE, MODULE_OTHER_CANDIDATE} and _contains_any_marker(
        context,
        (
            "shipping was late",
            "shipping late",
            "delivery was late",
            "delivered late",
            "late shipping",
            "shipping was delayed",
            "delivery was delayed",
            "arrived late",
        ),
    ):
        label = _approved_label("late_shipping", label_type="issue", category_key=category_key, sub_category_key=sub_category_key)
        if label:
            aspect_key = _approved_aspect_key(fragment, label=label, whitelist=whitelist, category_key=category_key)
            if aspect_key:
                return label, aspect_key

    if module in {MODULE_PRODUCT_ISSUE, MODULE_OTHER_CANDIDATE} and _contains_any_marker(
        context,
        (
            "sizing chart",
            "size chart",
            "sizing guide",
            "size guide",
        ),
    ) and _contains_any_marker(
        context,
        (
            "confusing",
            "unclear",
            "not clear",
            "inaccurate",
            "wrong",
            "misleading",
            "off",
        ),
    ):
        label = _approved_label("confusing_size_chart", label_type="issue", category_key=category_key, sub_category_key=sub_category_key)
        if label:
            aspect_key = _approved_aspect_key(fragment, label=label, whitelist=whitelist, category_key=category_key)
            if aspect_key:
                return label, aspect_key

    if module in {MODULE_ACCESSORY_OR_BUNDLE, MODULE_PRODUCT_ISSUE, MODULE_OTHER_CANDIDATE} and _contains_any_marker(
        context,
        (
            "missing accessory",
            "missing accessories",
            "missing part",
            "missing parts",
            "repair patch was missing",
            "patch was missing",
            "hanger was missing",
            "phone protector was missing",
            "not included",
        ),
    ) and _contains_any_marker(
        context,
        (
            "accessory",
            "accessories",
            "case",
            "hanger",
            "patch",
            "phone protector",
            "phone pouch",
            "repair",
        ),
    ):
        label = _approved_label("missing_accessory", label_type="issue", category_key=category_key, sub_category_key=sub_category_key)
        if label:
            aspect_key = _approved_aspect_key(fragment, label=label, whitelist=whitelist, category_key=category_key)
            if aspect_key:
                return label, aspect_key

    if module in {MODULE_ACCESSORY_OR_BUNDLE, MODULE_PRODUCT_ISSUE, MODULE_OTHER_CANDIDATE} and _contains_any_marker(
        context,
        (
            "phone case leaked",
            "phone pouch leaked",
            "phone protector leaked",
            "pocket leaked",
            "accessory leaked",
            "accessory leaks",
        ),
    ):
        label = _approved_label("accessory_leak", label_type="issue", category_key=category_key, sub_category_key=sub_category_key)
        if label:
            aspect_key = _approved_aspect_key(fragment, label=label, whitelist=whitelist, category_key=category_key)
            if aspect_key:
                return label, aspect_key

    if module == MODULE_PRODUCT_ISSUE and _contains_any_marker(
        context,
        (
            "leak",
            "leaked",
            "leaks",
            "water entered",
            "water got in",
        ),
        ):
        label = _approved_label("water_leaks_through", label_type="issue", category_key=category_key, sub_category_key=sub_category_key)
        if label:
            aspect_key = _approved_aspect_key(fragment, label=label, whitelist=whitelist, category_key=category_key)
            if aspect_key:
                return label, aspect_key

    return None


def _approved_highlight_label_for_aspect(aspect_key: str, *, category_key: str, sub_category_key: str) -> FormalLabel | None:
    result = resolve_highlight_for_aspect(aspect_key, category_key=category_key, sub_category_key=sub_category_key)
    return result.label


def _base_occurrence_row(
    *,
    fragment: Mapping[str, Any],
    review_text: Any,
    sub_category: str,
    can_aggregate: bool,
    aspect_key: str | None = None,
    reject_reason: str | None = None,
) -> dict[str, Any]:
    return {
        "evidence_span": _clean_string(fragment.get("evidence_span")),
        "aspect_key": aspect_key if aspect_key is not None else _clean_string(fragment.get("aspect_key")),
        "sub_category": sub_category,
        "polarity": _clean_string(fragment.get("polarity")),
        "can_aggregate": can_aggregate,
        "reject_reason": reject_reason,
        "count": 0,
        "representative_comments": [],
        "_review_text": _clean_string(review_text),
    }


def _append_occurrence(target: dict[tuple[str, ...], dict[str, Any]], key: tuple[str, ...], row: dict[str, Any]) -> None:
    current = target.get(key)
    if current is None:
        current = dict(row)
        target[key] = current

    current["count"] += 1
    if "aspect_keys" in current:
        aspect_key = _clean_string(row.get("aspect_key"))
        if aspect_key and aspect_key not in current["aspect_keys"]:
            current["aspect_keys"].append(aspect_key)
            current["aspect_keys"].sort()
    review_text = _clean_string(row.get("_review_text"))
    representative_comments = current["representative_comments"]
    if review_text and review_text not in representative_comments and len(representative_comments) < 3:
        representative_comments.append(review_text)


def _strip_private_fields(rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    cleaned: list[dict[str, Any]] = []
    for row in rows:
        cleaned.append({key: value for key, value in row.items() if not key.startswith("_")})
    return cleaned


def _formal_identity_key(row: Mapping[str, Any]) -> str:
    return _clean_string(row.get("issue_key") or row.get("highlight_key"))


def validate_review_fragment_module_enum_consistency() -> list[str]:
    """Check that 5.9.4 accepts old routing inputs but emits only final modules."""

    errors: list[str] = []
    if not FORMAL_TOP10_MODULES <= FINAL_ARTIFACT_MODULES:
        errors.append("formal_top10_modules_not_final")
    if not AGGREGATABLE_TAXONOMY_MODULES <= ARTIFACT_INPUT_MODULES:
        errors.append("taxonomy_modules_not_accepted_by_artifact")
    if not FORMAL_EVIDENCE_GATE_MODULES <= ARTIFACT_INPUT_MODULES:
        errors.append("evidence_gate_modules_not_accepted_by_artifact")
    if not COMPATIBILITY_INPUT_MODULES <= ARTIFACT_INPUT_MODULES:
        errors.append("compatibility_modules_not_accepted_by_artifact")
    if COMPATIBILITY_INPUT_MODULES & FINAL_ARTIFACT_MODULES:
        errors.append("compatibility_modules_leak_into_final_modules")
    if MODULE_CUSTOMER_SERVICE in FINAL_ARTIFACT_MODULES:
        errors.append("customer_service_is_final_module")
    return errors


def review_fragment_module_enum_matrix() -> dict[str, Any]:
    return {
        "contract_input_modules": sorted(VALID_REVIEW_FRAGMENT_MODULES),
        "taxonomy_aggregatable_modules": sorted(AGGREGATABLE_TAXONOMY_MODULES),
        "evidence_gate_modules": sorted(FORMAL_EVIDENCE_GATE_MODULES),
        "compatibility_input_modules": sorted(COMPATIBILITY_INPUT_MODULES),
        "final_artifact_modules": sorted(FINAL_ARTIFACT_MODULES),
        "validation_errors": validate_review_fragment_module_enum_consistency(),
    }


def _row_reject_reason(row: Mapping[str, Any]) -> str | None:
    return _clean_string(row.get("reject_reason") if "reject_reason" in row else row.get("reason")) or None


def _key_value(row: Mapping[str, Any], key: str) -> str:
    return _clean_string(row.get(key))


def validate_review_fragment_candidate_artifact_row(
    row: Mapping[str, Any],
    *,
    bucket: str,
) -> list[str]:
    errors: list[str] = []
    if not isinstance(row, Mapping):
        return ["row_not_object"]

    module = _key_value(row, "module")
    aspect_key = _key_value(row, "aspect_key")
    polarity = _key_value(row, "polarity")
    evidence_span = _key_value(row, "evidence_span")
    issue_key = _key_value(row, "issue_key")
    highlight_key = _key_value(row, "highlight_key")
    reject_reason = _row_reject_reason(row)
    can_aggregate = row.get("can_aggregate")

    if "action_label_key" in row:
        errors.append("action_label_key_forbidden")
    if "normalized_label" in row:
        errors.append("normalized_label_forbidden")

    if module not in FINAL_ARTIFACT_MODULES:
        errors.append("module_invalid")
    if module in COMPATIBILITY_INPUT_MODULES:
        errors.append("compatibility_module_leaked")
    if polarity not in VALID_REVIEW_FRAGMENT_POLARITIES:
        errors.append("polarity_invalid")
    if not isinstance(can_aggregate, bool):
        errors.append("can_aggregate_not_bool")

    if can_aggregate is True:
        if reject_reason:
            errors.append("reject_reason_must_be_empty_for_aggregate")
        if not aspect_key:
            errors.append("aspect_key_required_for_aggregate")
        if aspect_key == "other" or aspect_key.startswith("candidate:"):
            errors.append("unapproved_aspect_cannot_aggregate")
    elif can_aggregate is False:
        if not reject_reason:
            errors.append("reject_reason_required")
        elif reject_reason not in VALID_ARTIFACT_REJECT_REASONS:
            errors.append("reject_reason_invalid")

    if not evidence_span and reject_reason not in {"evidence_missing", "schema_invalid"}:
        errors.append("evidence_span_required")

    if bucket == "formal":
        if module not in FORMAL_TOP10_MODULES:
            errors.append("formal_module_invalid")
        if can_aggregate is not True:
            errors.append("formal_can_aggregate_required")
        if sum(bool(value) for value in (issue_key, highlight_key)) > 1:
            errors.append("formal_identity_key_conflict")
        if not issue_key and not highlight_key:
            errors.append("formal_identity_key_required")
        row_category = _key_value(row, "category")
        row_sub_category = _key_value(row, "sub_category")
        if issue_key:
            approved_result = resolve_formal_label(
                issue_key,
                label_type="issue",
                category_key=row_category,
                sub_category_key=row_sub_category,
            )
            if not approved_result.label or approved_result.label.label_type != "issue":
                errors.append("issue_key_not_approved")
            else:
                if module != approved_result.label.formal_module:
                    errors.append("issue_key_module_mismatch")
                if aspect_key and aspect_key not in approved_result.label.aspect_keys:
                    errors.append("issue_aspect_key_mismatch")
            if polarity not in {"negative", "mixed"}:
                errors.append("issue_polarity_invalid")
        if highlight_key:
            if module != MODULE_PRODUCT_HIGHLIGHT:
                errors.append("highlight_key_module_invalid")
            if polarity not in {"positive", "mixed"}:
                errors.append("highlight_polarity_invalid")
            approved_hl_result = resolve_formal_label(
                highlight_key,
                label_type="highlight",
                category_key=row_category,
                sub_category_key=row_sub_category,
            )
            if not approved_hl_result.label:
                errors.append("highlight_key_unknown")
    else:
        if issue_key or highlight_key:
            errors.append("non_formal_seller_key_leaked")
        if bucket == "module" and module not in {MODULE_CONSUMER_PROFILE, MODULE_PURCHASE_MOTIVE}:
            errors.append("module_seed_module_invalid")
        if bucket == "candidate" and can_aggregate is not False:
            errors.append("candidate_can_aggregate_invalid")
        if bucket == "audit" and module != MODULE_AUDIT_FILTER:
            errors.append("audit_module_invalid")

    return errors


def validate_review_fragment_candidate_artifact(artifact: Mapping[str, Any]) -> list[str]:
    errors: list[str] = []
    if not isinstance(artifact, Mapping):
        return ["artifact_not_object"]
    if artifact.get("candidate_version") != REVIEW_FRAGMENT_CANDIDATE_MULTIMODULE_VERSION:
        errors.append("candidate_version_invalid")

    errors.extend(f"module_enum.{error}" for error in validate_review_fragment_module_enum_consistency())
    for bucket in ARTIFACT_ROW_BUCKETS:
        rows = artifact.get(bucket)
        if not isinstance(rows, list):
            errors.append(f"{bucket}.rows_not_list")
            continue
        route_bucket = bucket.removesuffix("_rows")
        if bucket == "formal_top10_rows":
            route_bucket = "formal"
        elif bucket == "module_seed_rows":
            route_bucket = "module"
        for index, row in enumerate(rows):
            row_errors = validate_review_fragment_candidate_artifact_row(row, bucket=route_bucket)
            errors.extend(f"{bucket}[{index}].{error}" for error in row_errors)
    return errors


def _candidate_row(
    *,
    fragment: Mapping[str, Any],
    review_text: Any,
    sub_category: str,
    module: str,
    reason: str,
) -> dict[str, Any]:
    candidate_label = _candidate_label_from_fragment(fragment)
    candidate_label_key = normalize_review_fragment_candidate_label(candidate_label)
    return {
        "module": _business_module_for_fragment(fragment, fallback=module),
        "candidate_label": candidate_label,
        "candidate_label_key": candidate_label_key,
        "issue_key": None,
        "highlight_key": None,
        "formal_top10_eligible": False,
        "reason": reason,
        **_base_occurrence_row(
            fragment=fragment,
            review_text=review_text,
            sub_category=sub_category,
            can_aggregate=False,
            reject_reason=reason,
        ),
    }


def _formal_row(
    *,
    fragment: Mapping[str, Any],
    review_text: Any,
    sub_category: str,
    approved_label: FormalLabel | None = None,
    aspect_key: str | None = None,
    category_key: str = "",
) -> dict[str, Any]:
    resolved_aspect_key = aspect_key or _clean_string(fragment.get("aspect_key"))
    issue_key = approved_label.key if approved_label and approved_label.label_type == "issue" else None
    approved_highlight = (
        approved_label
        if approved_label and approved_label.label_type == "highlight"
        else _approved_highlight_label_for_aspect(resolved_aspect_key, category_key=category_key, sub_category_key=sub_category)
        if not issue_key
        and _clean_string(fragment.get("module")) == MODULE_PRODUCT_HIGHLIGHT
        and _clean_string(fragment.get("polarity")) == "positive"
        else None
    )
    highlight_key = (
        approved_highlight.key
        if approved_highlight
        else None
    )
    identity_label = approved_label or approved_highlight
    label_key = issue_key or highlight_key
    display_label_en, display_label_zh = _display_label_for_key(
        label_key,
        approved_label=identity_label,
        category_key=category_key,
        sub_category_key=sub_category,
    )
    return {
        "module": (
            identity_label.formal_module
            if identity_label
            else _business_module_for_fragment(fragment)
        ),
        "issue_key": issue_key,
        "highlight_key": highlight_key,
        "display_label_en": display_label_en,
        "display_label_zh": display_label_zh,
        "aspect_keys": [resolved_aspect_key] if resolved_aspect_key else [],
        "formal_top10_eligible": True,
        **_base_occurrence_row(
            fragment=fragment,
            review_text=review_text,
            sub_category=sub_category,
            can_aggregate=True,
            aspect_key=resolved_aspect_key,
            reject_reason=None,
        ),
    }


def _module_seed_row(
    *,
    fragment: Mapping[str, Any],
    review_text: Any,
    sub_category: str,
    output_module: str,
    seed_match: SeedMatch,
) -> dict[str, Any]:
    return {
        "module": output_module,
        "seed_module": seed_match.module,
        "label": seed_match.label.key,
        "issue_key": None,
        "highlight_key": None,
        "formal_top10_eligible": False,
        **_base_occurrence_row(
            fragment=fragment,
            review_text=review_text,
            sub_category=sub_category,
            can_aggregate=True,
            reject_reason=None,
        ),
    }


def _audit_row(
    *,
    fragment: Mapping[str, Any],
    review_text: Any,
    sub_category: str,
    reason: str,
) -> dict[str, Any]:
    label = _candidate_label_from_fragment(fragment)
    return {
        "module": MODULE_AUDIT_FILTER,
        "label": label,
        "candidate_label_key": normalize_review_fragment_candidate_label(label),
        "issue_key": None,
        "highlight_key": None,
        "formal_top10_eligible": False,
        "reason": reason,
        **_base_occurrence_row(
            fragment=fragment,
            review_text=review_text,
            sub_category=sub_category,
            can_aggregate=False,
            reject_reason=reason,
        ),
    }


def _display_label_for_key(
    key: str,
    *,
    approved_label: FormalLabel | None = None,
    category_key: str = "",
    sub_category_key: str = "",
) -> tuple[str, str]:
    if approved_label:
        return approved_label.display_label_en, approved_label.display_label_zh
    result = resolve_formal_label(key, category_key=category_key, sub_category_key=sub_category_key)
    if result.label:
        return result.label.display_label_en, result.label.display_label_zh
    return "", ""


def _candidate_reason_from_taxonomy(status: str, reject_reason: str | None) -> str:
    if reject_reason:
        return reject_reason
    if status == CANDIDATE_REASON_TAXONOMY_MISSING:
        return CANDIDATE_REASON_TAXONOMY_MISSING
    return CANDIDATE_REASON_TAXONOMY_OUT_OF_SCOPE


def _should_candidate_from_evidence_reject(module: str, reason: str | None) -> bool:
    if not reason:
        return False
    if module == MODULE_ACCESSORY_OR_BUNDLE and reason == "accessory_only":
        return True
    return module == MODULE_LOGISTICS_SUPPORT and reason == "logistics_or_service"


def _route_fragment(
    fragment: Mapping[str, Any],
    *,
    review_text: Any,
    whitelist: ReviewFragmentTaxonomyWhitelist,
) -> tuple[str, dict[str, Any]]:
    module = _clean_string(fragment.get("module"))
    sub_category = whitelist.sub_category
    evidence_decision = validate_review_fragment_evidence(fragment, review_text=review_text, whitelist=None)

    if not evidence_decision.evidence_valid:
        reason = evidence_decision.reject_reason or "evidence_invalid"
        return "audit", _audit_row(fragment=fragment, review_text=review_text, sub_category=sub_category, reason=reason)

    if evidence_decision.reject_reason in {
        None,
        "accessory_only",
        "candidate_pending_review",
        "logistics_or_service",
    }:
        approved_mapping = _approved_formal_label_for_fragment(fragment, whitelist=whitelist)
        if approved_mapping:
            approved_label, aspect_key = approved_mapping
            return "formal", _formal_row(
                fragment=fragment,
                review_text=review_text,
                sub_category=sub_category,
                approved_label=approved_label,
                aspect_key=aspect_key,
                category_key=whitelist.category,
            )

    if module in AGGREGATABLE_TAXONOMY_MODULES:
        if evidence_decision.reject_reason:
            seed_match = _product_out_of_scope_seed_match(fragment)
            if seed_match:
                return "module", _module_seed_row(
                    fragment=fragment,
                    review_text=review_text,
                    sub_category=sub_category,
                    output_module=MODULE_CONSUMER_PROFILE,
                    seed_match=seed_match,
                )
            if _should_candidate_from_evidence_reject(module, evidence_decision.reject_reason):
                return "candidate", _candidate_row(
                    fragment=fragment,
                    review_text=review_text,
                    sub_category=sub_category,
                    module=module,
                    reason=evidence_decision.reject_reason,
                )
            return "audit", _audit_row(
                fragment=fragment,
                review_text=review_text,
                sub_category=sub_category,
                reason=evidence_decision.reject_reason,
            )

        taxonomy_decision = validate_review_fragment_taxonomy(fragment, whitelist)
        if taxonomy_decision.status == TAXONOMY_STATUS_ALLOWED and taxonomy_decision.can_aggregate is True:
            return "formal", _formal_row(fragment=fragment, review_text=review_text, sub_category=sub_category)

        seed_match = _product_out_of_scope_seed_match(fragment)
        if seed_match:
            return "module", _module_seed_row(
                fragment=fragment,
                review_text=review_text,
                sub_category=sub_category,
                output_module=MODULE_CONSUMER_PROFILE,
                seed_match=seed_match,
            )

        reason = _candidate_reason_from_taxonomy(taxonomy_decision.status, taxonomy_decision.reject_reason)
        return "candidate", _candidate_row(
            fragment=fragment,
            review_text=review_text,
            sub_category=sub_category,
            module=module,
            reason=reason,
        )

    if module == MODULE_CONSUMER_PROFILE:
        seed_match = _consumer_profile_seed_match(fragment)
        if seed_match:
            return "module", _module_seed_row(
                fragment=fragment,
                review_text=review_text,
                sub_category=sub_category,
                output_module=MODULE_CONSUMER_PROFILE,
                seed_match=seed_match,
            )
        return "candidate", _candidate_row(
            fragment=fragment,
            review_text=review_text,
            sub_category=sub_category,
            module=MODULE_CONSUMER_PROFILE,
            reason=CANDIDATE_REASON_SEED_OUT_OF_SCOPE,
        )

    if module == MODULE_PURCHASE_MOTIVE:
        seed_match = _purchase_motive_seed_match(fragment)
        if seed_match:
            return "module", _module_seed_row(
                fragment=fragment,
                review_text=review_text,
                sub_category=sub_category,
                output_module=MODULE_PURCHASE_MOTIVE,
                seed_match=seed_match,
            )
        return "candidate", _candidate_row(
            fragment=fragment,
            review_text=review_text,
            sub_category=sub_category,
            module=MODULE_PURCHASE_MOTIVE,
            reason=CANDIDATE_REASON_SEED_OUT_OF_SCOPE,
        )

    if module == MODULE_UNMET_NEED:
        return "candidate", _candidate_row(
            fragment=fragment,
            review_text=review_text,
            sub_category=sub_category,
            module=MODULE_UNMET_NEED,
            reason=CANDIDATE_REASON_UNMET_NEED_FIRST,
        )

    if module == MODULE_OTHER_CANDIDATE:
        reason = _clean_string(fragment.get("reject_reason")) or CANDIDATE_REASON_CANDIDATE_PENDING_REVIEW
        return "candidate", _candidate_row(
            fragment=fragment,
            review_text=review_text,
            sub_category=sub_category,
            module=MODULE_OTHER_CANDIDATE,
            reason=reason,
        )

    if module in {MODULE_AUDIT_FILTER, MODULE_COMPARISON_OR_OTHER_PRODUCT}:
        reason = _clean_string(fragment.get("reject_reason")) or "not_current_product"
        return "audit", _audit_row(fragment=fragment, review_text=review_text, sub_category=sub_category, reason=reason)

    return "candidate", _candidate_row(
        fragment=fragment,
        review_text=review_text,
        sub_category=sub_category,
        module=module or MODULE_OTHER_CANDIDATE,
        reason=CANDIDATE_REASON_SEED_OUT_OF_SCOPE,
    )


def _route_fragment_with_validation(
    fragment: Mapping[str, Any],
    *,
    review_text: Any,
    whitelist: ReviewFragmentTaxonomyWhitelist,
) -> tuple[str, dict[str, Any]]:
    bucket, row = _route_fragment(fragment, review_text=review_text, whitelist=whitelist)
    validation_errors = validate_review_fragment_candidate_artifact_row(row, bucket=bucket)
    if not validation_errors:
        return bucket, row

    degraded = _audit_row(
        fragment=fragment,
        review_text=review_text,
        sub_category=whitelist.sub_category,
        reason="schema_invalid",
    )
    if degraded["polarity"] not in VALID_REVIEW_FRAGMENT_POLARITIES:
        degraded["polarity"] = "neutral"
    degraded["degraded_from_bucket"] = bucket
    degraded["validation_errors"] = validation_errors
    retry_errors = validate_review_fragment_candidate_artifact_row(degraded, bucket="audit")
    if retry_errors:
        degraded["validation_errors"] = [*validation_errors, *retry_errors]
    return "audit", degraded


def build_review_fragment_candidate_artifact(
    samples: Sequence[Mapping[str, Any]],
    *,
    aspect_resolver: AspectResolver = resolve_aspects,
) -> dict[str, Any]:
    """Build the isolated 5.9.4 seller-action artifact from review fragments.

    Formal rows are the only rows eligible for seller-action TOP10 aggregation.
    Candidate rows always keep evidence and remain can_aggregate=false.
    """

    formal_rows: dict[tuple[str, ...], dict[str, Any]] = {}
    module_rows: dict[tuple[str, ...], dict[str, Any]] = {}
    candidate_rows: dict[tuple[str, ...], dict[str, Any]] = {}
    audit_rows: dict[tuple[str, ...], dict[str, Any]] = {}

    for sample in samples:
        whitelist = resolve_review_fragment_taxonomy_whitelist(
            category=sample.get("category"),
            sub_category=sample.get("sub_category"),
            aspect_resolver=aspect_resolver,
        )
        review_text = sample.get("content")

        for fragment in sample.get("fragments", []):
            if not isinstance(fragment, Mapping):
                continue
            bucket, row = _route_fragment_with_validation(fragment, review_text=review_text, whitelist=whitelist)
            if bucket == "formal":
                final_label_key = _formal_identity_key(row)
                key = (row["module"], final_label_key, row["sub_category"], row["polarity"])
                _append_occurrence(formal_rows, key, row)
            elif bucket == "module":
                key = (
                    row["module"],
                    row["seed_module"],
                    row["label"],
                    row["sub_category"],
                    row["polarity"],
                )
                _append_occurrence(module_rows, key, row)
            elif bucket == "candidate":
                key = (
                    row["module"],
                    row["candidate_label_key"],
                    row["sub_category"],
                    row["reason"],
                    row["polarity"],
                )
                _append_occurrence(candidate_rows, key, row)
            else:
                key = (
                    row["module"],
                    row["candidate_label_key"],
                    row["sub_category"],
                    row["reason"],
                    row["polarity"],
                )
                _append_occurrence(audit_rows, key, row)

    return {
        "candidate_version": REVIEW_FRAGMENT_CANDIDATE_MULTIMODULE_VERSION,
        "formal_top10_rows": _strip_private_fields(
            sorted(
                formal_rows.values(),
                key=lambda row: (
                    row["module"],
                    _formal_identity_key(row),
                    row["polarity"],
                ),
            )
        ),
        "module_seed_rows": _strip_private_fields(
            sorted(
                module_rows.values(),
                key=lambda row: (row["module"], row["seed_module"], row["label"], row["polarity"]),
            )
        ),
        "candidate_rows": _strip_private_fields(
            sorted(
                candidate_rows.values(),
                key=lambda row: (row["module"], row["candidate_label_key"], row["reason"], row["polarity"]),
            )
        ),
        "audit_rows": _strip_private_fields(
            sorted(audit_rows.values(), key=lambda row: (row["module"], row["candidate_label_key"], row["reason"]))
        ),
    }
