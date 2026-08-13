from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

CUSTOMER_LABEL_V2_MATURITY_CONTRACT_VERSION = "customer-label-v2-maturity.1"

MATURITY_L0_UNKNOWN = "L0_unknown"
MATURITY_L1_GENERIC = "L1_generic"
MATURITY_L2_CATEGORY = "L2_category"
MATURITY_L3_SUB_CATEGORY = "L3_sub_category"
MATURITY_LEVELS = (
    MATURITY_L0_UNKNOWN,
    MATURITY_L1_GENERIC,
    MATURITY_L2_CATEGORY,
    MATURITY_L3_SUB_CATEGORY,
)

_STATIC_CATEGORY_MAPPING_PATH = Path(__file__).parent.parent / "data" / "sub_category_categories.json"

L1_GENERIC_SAFE_LABEL_KEYS: dict[str, frozenset[str]] = {
    "issue": frozenset(),
    "highlight": frozenset(
        {
            "overall_satisfied",
            "good_material_quality",
            "looks_good",
            "first_impression_positive",
        }
    ),
}

L0_EXPLICIT_SAFE_LABEL_KEYS: dict[str, frozenset[str]] = {
    "issue": frozenset(),
    "highlight": frozenset(),
}

L2_CATEGORY_SAFE_LABEL_KEYS: dict[str, frozenset[str]] = {
    "issue": frozenset(
        {
            "arrived_damaged",
            "breaks_easily",
            "hard_to_assemble",
            "instructions_unclear",
            "missing_parts",
            "not_breathable",
            "not_worth_the_price",
            "poor_customer_service",
            "poor_value_for_money",
            "quality_problem",
            "size_fit_problem",
            "strong_chemical_smell",
        }
    ),
    "highlight": frozenset(
        {
            "arrives_on_time_and_intact",
            "comfortable_to_wear",
            "customer_service_helpful",
            "easy_to_clean",
            "fast_shipping",
            "first_impression_positive",
            "fits_as_expected",
            "good_material_quality",
            "good_value_for_the_price",
            "holds_up_well",
            "looks_good",
            "no_strong_odor",
            "overall_satisfied",
            "works_well_for_use_case",
        }
    ),
}

SUB_CATEGORY_SPECIFIC_LABEL_KEYS: dict[str, frozenset[str]] = {
    "issue": frozenset(
        {
            "accessories_not_as_advertised",
            "boots_too_stiff",
            "calf_area_too_tight",
            "feels_thin_and_flimsy",
            "missing_accessories",
            "missing_wader_hanger",
            "not_for_heavy_brush",
            "not_for_long_walks",
            "pocket_not_waterproof",
            "pocket_too_small",
            "poor_traction",
            "seam_leaks",
            "soft_soles",
            "uncomfortable_fit",
            "water_leaks_through",
            "zipper_fails",
        }
    ),
    "highlight": frozenset(
        {
            "breathes_well",
            "feels_well_made",
            "good_traction",
            "keeps_warm",
            "keeps_water_out",
            "lightweight_waders",
            "not_used_yet",
            "petite_friendly",
            "plus_size_friendly",
            "useful_accessories",
            "useful_storage_space",
            "women_friendly_fit",
        }
    ),
}

CATEGORY_MATURITY_LEVELS: dict[str, str] = {
    "home": MATURITY_L2_CATEGORY,
    "3c": MATURITY_L2_CATEGORY,
    "apparel": MATURITY_L2_CATEGORY,
    "baby": MATURITY_L1_GENERIC,
    "pet": MATURITY_L1_GENERIC,
    "outdoor": MATURITY_L2_CATEGORY,
    "beauty": MATURITY_L2_CATEGORY,
    "kitchen": MATURITY_L2_CATEGORY,
    "automotive": MATURITY_L1_GENERIC,
    "office": MATURITY_L1_GENERIC,
}

SUB_CATEGORY_MATURITY_OVERRIDES: dict[tuple[str, str], str] = {
    ("outdoor", "waders"): MATURITY_L3_SUB_CATEGORY,
}

MIN_CONFIDENCE_BY_LEVEL: dict[str, float] = {
    MATURITY_L0_UNKNOWN: 0.95,
    MATURITY_L1_GENERIC: 0.86,
    MATURITY_L2_CATEGORY: 0.78,
    MATURITY_L3_SUB_CATEGORY: 0.65,
}


@dataclass(frozen=True)
class CustomerLabelMaturity:
    category: str
    sub_category: str
    level: str
    source: str
    category_from_taxonomy: str | None
    contract_version: str = CUSTOMER_LABEL_V2_MATURITY_CONTRACT_VERSION

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class MaturityGateDecision:
    allowed: bool
    minimum_confidence: float
    allowed_scope: str
    reason: str

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def _normalize_key(value: Any) -> str:
    value = str(value or "").strip().lower().replace("&", " and ")
    value = re.sub(r"[^a-z0-9]+", "_", value)
    return re.sub(r"_+", "_", value).strip("_")


def _clean_label_type(value: Any) -> str:
    cleaned = str(value or "").strip().lower()
    return cleaned if cleaned in {"issue", "highlight"} else ""


@lru_cache(maxsize=1)
def _load_static_category_mapping() -> dict[str, Any]:
    try:
        return json.loads(_STATIC_CATEGORY_MAPPING_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {
            "taxonomy_version": "unknown",
            "category_labels": {},
            "sub_category_to_category": {},
            "total_sub_categories": 0,
        }


def _sub_category_to_category_map() -> dict[str, str]:
    mapping = _load_static_category_mapping().get("sub_category_to_category")
    return mapping if isinstance(mapping, dict) else {}


def infer_category_from_sub_category(sub_category: str) -> str | None:
    mapping = _sub_category_to_category_map()
    if sub_category in mapping:
        return str(mapping[sub_category])

    lowered = str(sub_category or "").strip().lower()
    for key, category in mapping.items():
        if str(key).strip().lower() == lowered:
            return str(category)

    normalized = _normalize_key(sub_category)
    if normalized:
        for key, category in mapping.items():
            if _normalize_key(key) == normalized:
                return str(category)
    return None


def resolve_customer_label_maturity(
    *,
    category: str = "",
    sub_category: str = "",
    explicit_level: str | None = None,
) -> CustomerLabelMaturity:
    inferred_category = infer_category_from_sub_category(sub_category)
    category_key = _normalize_key(category)
    if category_key not in CATEGORY_MATURITY_LEVELS and inferred_category:
        category_key = _normalize_key(inferred_category)
    sub_category_key = _normalize_key(sub_category)

    if explicit_level:
        level = explicit_level if explicit_level in MATURITY_LEVELS else MATURITY_L0_UNKNOWN
        source = "explicit" if explicit_level in MATURITY_LEVELS else "explicit_invalid_fallback"
    elif (category_key, sub_category_key) in SUB_CATEGORY_MATURITY_OVERRIDES:
        level = SUB_CATEGORY_MATURITY_OVERRIDES[(category_key, sub_category_key)]
        source = "sub_category_override"
    elif category_key in CATEGORY_MATURITY_LEVELS:
        level = CATEGORY_MATURITY_LEVELS[category_key]
        source = "category_rollout"
    else:
        level = MATURITY_L0_UNKNOWN
        source = "default_unknown"

    return CustomerLabelMaturity(
        category=category_key or "unknown",
        sub_category=sub_category_key or "unknown",
        level=level,
        source=source,
        category_from_taxonomy=_normalize_key(inferred_category) if inferred_category else None,
    )


def maturity_gate_decision(
    *,
    label_type: str,
    canonical_label_key: str,
    maturity: CustomerLabelMaturity,
    subcategory_specificity: str = "",
    risk_flags: list[str] | tuple[str, ...] | None = None,
) -> MaturityGateDecision:
    cleaned_type = _clean_label_type(label_type)
    canonical = str(canonical_label_key or "").strip()
    risk_flags = list(risk_flags or [])
    minimum_confidence = MIN_CONFIDENCE_BY_LEVEL.get(maturity.level, 0.95)

    if not cleaned_type or not canonical:
        return MaturityGateDecision(
            allowed=False,
            minimum_confidence=minimum_confidence,
            allowed_scope="none",
            reason="schema_invalid",
        )
    if canonical.startswith("candidate:"):
        return MaturityGateDecision(
            allowed=False,
            minimum_confidence=minimum_confidence,
            allowed_scope="candidate_pool",
            reason="unknown_label",
        )
    if risk_flags:
        return MaturityGateDecision(
            allowed=False,
            minimum_confidence=minimum_confidence,
            allowed_scope="audit",
            reason="risk_flag_blocked",
        )
    if maturity.level == MATURITY_L3_SUB_CATEGORY:
        return MaturityGateDecision(
            allowed=True,
            minimum_confidence=minimum_confidence,
            allowed_scope="sub_category",
            reason="l3_sub_category_catalog",
        )
    if maturity.level == MATURITY_L2_CATEGORY:
        if canonical in L2_CATEGORY_SAFE_LABEL_KEYS.get(cleaned_type, frozenset()):
            return MaturityGateDecision(
                allowed=True,
                minimum_confidence=minimum_confidence,
                allowed_scope="category",
                reason="l2_category_safe_label",
            )
        if str(subcategory_specificity or "").strip().lower() == "generic" and canonical in L1_GENERIC_SAFE_LABEL_KEYS.get(
            cleaned_type,
            frozenset(),
        ):
            return MaturityGateDecision(
                allowed=True,
                minimum_confidence=minimum_confidence,
                allowed_scope="generic",
                reason="l2_generic_safe_label",
            )
        return MaturityGateDecision(
            allowed=False,
            minimum_confidence=minimum_confidence,
            allowed_scope="candidate_pool",
            reason="l2_blocks_sub_category_or_uncataloged_label",
        )
    if maturity.level == MATURITY_L1_GENERIC:
        if canonical in L1_GENERIC_SAFE_LABEL_KEYS.get(cleaned_type, frozenset()):
            return MaturityGateDecision(
                allowed=True,
                minimum_confidence=minimum_confidence,
                allowed_scope="generic",
                reason="l1_generic_safe_label",
            )
        return MaturityGateDecision(
            allowed=False,
            minimum_confidence=minimum_confidence,
            allowed_scope="candidate_pool",
            reason="l1_blocks_non_generic_label",
        )
    if canonical in L0_EXPLICIT_SAFE_LABEL_KEYS.get(cleaned_type, frozenset()):
        return MaturityGateDecision(
            allowed=True,
            minimum_confidence=minimum_confidence,
            allowed_scope="explicit_safe",
            reason="l0_explicit_safe_label",
        )
    return MaturityGateDecision(
        allowed=False,
        minimum_confidence=minimum_confidence,
        allowed_scope="candidate_pool",
        reason="l0_default_audit_candidate_pool",
    )


def maturity_contract_summary() -> dict[str, Any]:
    mapping = _load_static_category_mapping()
    category_labels = mapping.get("category_labels") if isinstance(mapping.get("category_labels"), dict) else {}
    return {
        "schema_version": CUSTOMER_LABEL_V2_MATURITY_CONTRACT_VERSION,
        "taxonomy_mapping_source": "backend_api/app/data/sub_category_categories.json",
        "taxonomy_version": str(mapping.get("taxonomy_version") or "unknown"),
        "taxonomy_total_sub_categories": int(mapping.get("total_sub_categories") or 0),
        "levels": {
            MATURITY_L0_UNKNOWN: {
                "meaning": "Unknown or unvalidated category/sub_category. Default to audit/candidate pool.",
                "frontstage": "No display by default; explicit safe labels hook is currently empty.",
                "minimum_confidence": MIN_CONFIDENCE_BY_LEVEL[MATURITY_L0_UNKNOWN],
            },
            MATURITY_L1_GENERIC: {
                "meaning": "Category has only generic-safe display confidence.",
                "frontstage": "Generic safe highlights only; issues and category/sub_category labels go to audit/candidate pool.",
                "minimum_confidence": MIN_CONFIDENCE_BY_LEVEL[MATURITY_L1_GENERIC],
            },
            MATURITY_L2_CATEGORY: {
                "meaning": "Category-level taxonomy/aspect boundaries are usable.",
                "frontstage": "High-confidence category-safe labels only; sub_category-specific labels stay in audit/candidate pool.",
                "minimum_confidence": MIN_CONFIDENCE_BY_LEVEL[MATURITY_L2_CATEGORY],
            },
            MATURITY_L3_SUB_CATEGORY: {
                "meaning": "Sub_category catalog has gold/replay validation.",
                "frontstage": "Sub_category catalog and verifier display are allowed.",
                "minimum_confidence": MIN_CONFIDENCE_BY_LEVEL[MATURITY_L3_SUB_CATEGORY],
            },
        },
        "category_rollout": {
            category: {
                "level": level,
                "label": category_labels.get(category, category),
            }
            for category, level in sorted(CATEGORY_MATURITY_LEVELS.items())
        },
        "sub_category_overrides": {
            f"{category}/{sub_category}": level
            for (category, sub_category), level in sorted(SUB_CATEGORY_MATURITY_OVERRIDES.items())
        },
        "allowed_label_sets": {
            "l1_generic_safe": {key: sorted(value) for key, value in L1_GENERIC_SAFE_LABEL_KEYS.items()},
            "l2_category_safe": {key: sorted(value) for key, value in L2_CATEGORY_SAFE_LABEL_KEYS.items()},
            "l0_explicit_safe": {key: sorted(value) for key, value in L0_EXPLICIT_SAFE_LABEL_KEYS.items()},
        },
        "safety": {
            "production_upload": False,
            "production_write_path": False,
            "production_db_write": False,
            "credit_consumed": False,
            "llm_called": False,
            "frontstage_replaced": False,
        },
    }
