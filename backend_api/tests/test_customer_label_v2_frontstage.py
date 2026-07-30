from __future__ import annotations

from typing import Any

import pytest

from backend_api.app.services.customer_label_catalog import (
    CustomerLabelCatalogState,
    set_customer_label_catalog_state_for_tests,
)
from backend_api.app.services.customer_label_v2_frontstage import (
    FRONTSTAGE_CONSUMERS,
    READ_PATH_V1_CURRENT,
    READ_PATH_V2_SHADOW,
    CustomerLabelV2FrontstageFlag,
    build_customer_label_v2_frontstage_read_model,
    customer_label_v2_frontstage_contract_summary,
    frontstage_keys_from_read_model,
)
from backend_api.app.services.specific_issue import (
    CUSTOMER_LABEL_OCCURRENCE_RULESET_VERSION,
    CUSTOMER_LABEL_OCCURRENCE_SCHEMA_VERSION,
)


@pytest.fixture(autouse=True)
def reset_catalog_state() -> None:
    set_customer_label_catalog_state_for_tests(CustomerLabelCatalogState())
    yield
    set_customer_label_catalog_state_for_tests(None)


def _v1_occurrence(
    *,
    label_type: str,
    canonical: str,
    display_en: str,
    display_zh: str,
    aspect_key: str,
    evidence: str,
    comment_id: str,
) -> dict[str, Any]:
    return {
        "comment_id": comment_id,
        "type": label_type,
        "raw_label": display_en,
        "canonical_label_key": canonical,
        "display_label_en": display_en,
        "display_label_zh": display_zh,
        "aspect_key": aspect_key,
        "evidence_span": evidence,
        "evidence_start": -1,
        "evidence_end": -1,
        "confidence": "high",
        "source": "rule",
        "source_detail": "step6_v1_fixture",
        "evidence_verified": True,
        "cluster_propagated": False,
        "schema_version": CUSTOMER_LABEL_OCCURRENCE_SCHEMA_VERSION,
        "ruleset_version": CUSTOMER_LABEL_OCCURRENCE_RULESET_VERSION,
        "display_allowed": True,
    }


def _review_with_v1_zipper() -> dict[str, Any]:
    return {
        "id": "step6-review-waders",
        "session_id": "step6-session",
        "product_id": "TIDEWE-step6",
        "content": "The zipper broke on day one. They do not keep you dry.",
        "rating": 1,
        "category": "outdoor",
        "sub_category": "waders",
        "aspects_json": {
            "customer_label_occurrence_schema_version": CUSTOMER_LABEL_OCCURRENCE_SCHEMA_VERSION,
            "customer_label_occurrence_ruleset_version": CUSTOMER_LABEL_OCCURRENCE_RULESET_VERSION,
            "sub_category": "waders",
            "customer_label_occurrences": [
                _v1_occurrence(
                    label_type="issue",
                    canonical="zipper_fails",
                    display_en="Zipper Fails",
                    display_zh="拉链容易故障",
                    aspect_key="zipper_quality",
                    evidence="zipper broke",
                    comment_id="step6-review-waders",
                )
            ],
        },
    }


def _review_without_v1(
    content: str,
    *,
    category: str = "outdoor",
    sub_category: str = "waders",
    review_id: str = "step6-review-no-v1",
) -> dict[str, Any]:
    return {
        "id": review_id,
        "session_id": "step6-session",
        "product_id": "step6-product",
        "content": content,
        "rating": 2,
        "category": category,
        "sub_category": sub_category,
    }


def _candidate(
    *,
    label_type: str,
    canonical: str,
    evidence: str,
    aspect_key: str,
    confidence: float = 0.9,
    raw_label: str | None = None,
) -> dict[str, Any]:
    display = raw_label or " ".join(part.capitalize() for part in canonical.replace("candidate:", "").split("_"))
    return {
        "label_type": label_type,
        "canonical_label_key": canonical,
        "raw_label": display,
        "display_label_en": display,
        "display_label_zh": display,
        "aspect_key": aspect_key,
        "polarity": "negative" if label_type == "issue" else "positive",
        "evidence_candidate": evidence,
        "confidence": confidence,
        "reason": "step6 read-path fixture",
    }


def _waders_flag(**overrides: Any) -> CustomerLabelV2FrontstageFlag:
    payload = {
        "enabled": True,
        "sub_categories": ("outdoor/waders",),
        "shadow_fixture_gate_passed": True,
    }
    payload.update(overrides)
    return CustomerLabelV2FrontstageFlag(**payload)


def test_feature_flag_off_preserves_v1_current_frontstage() -> None:
    model = build_customer_label_v2_frontstage_read_model(
        _review_with_v1_zipper(),
        flag=CustomerLabelV2FrontstageFlag(),
        label_candidates=[
            _candidate(
                label_type="issue",
                canonical="water_leaks_through",
                evidence="do not keep you dry",
                aspect_key="waterproof",
            )
        ],
    )

    assert model["read_path"] == READ_PATH_V1_CURRENT
    assert model["fallback_reason"] == "flag_off"
    assert frontstage_keys_from_read_model(model) == model["v1_current"]["keys"]
    assert "zipper_fails" in model["v1_current"]["keys"]["issue"]
    assert model["v2_shadow"]["available"] is False
    assert model["safety"]["frontstage_replaced"] is False


def test_flag_on_l3_waders_consumes_only_verified_v2_display_occurrences() -> None:
    model = build_customer_label_v2_frontstage_read_model(
        _review_with_v1_zipper(),
        flag=_waders_flag(),
        label_candidates=[
            _candidate(
                label_type="issue",
                canonical="water_leaks_through",
                evidence="do not keep you dry",
                aspect_key="waterproof",
            ),
            _candidate(
                label_type="issue",
                canonical="water_leaks_through",
                evidence="missing seam evidence",
                aspect_key="waterproof",
            ),
        ],
    )

    assert model["read_path"] == READ_PATH_V2_SHADOW
    assert model["fallback_reason"] == ""
    assert "zipper_fails" in model["v1_current"]["keys"]["issue"]
    assert frontstage_keys_from_read_model(model) == {"issue": ["water_leaks_through"], "highlight": []}
    assert model["v2_shadow"]["audit_occurrence_count"] == 1
    assert all(item["source_version"] == READ_PATH_V2_SHADOW for item in model["frontstage_occurrences"])
    assert all(not item["downgrade_reasons"] for item in model["frontstage_occurrences"])
    for consumer in FRONTSTAGE_CONSUMERS:
        assert model["frontstage_consumers"][consumer]["read_path"] == READ_PATH_V2_SHADOW
        assert model["frontstage_consumers"][consumer]["issue_keys"] == ["water_leaks_through"]
        assert model["frontstage_consumers"][consumer]["audit_and_candidate_pool_excluded"] is True


def test_flag_on_without_fixture_gate_falls_back_to_v1_current() -> None:
    model = build_customer_label_v2_frontstage_read_model(
        _review_with_v1_zipper(),
        flag=_waders_flag(shadow_fixture_gate_passed=False),
        label_candidates=[
            _candidate(
                label_type="issue",
                canonical="water_leaks_through",
                evidence="do not keep you dry",
                aspect_key="waterproof",
            )
        ],
    )

    assert model["read_path"] == READ_PATH_V1_CURRENT
    assert model["fallback_reason"] == "shadow_fixture_gate_blocked"
    assert frontstage_keys_from_read_model(model) == model["v1_current"]["keys"]
    assert "zipper_fails" in model["v1_current"]["keys"]["issue"]
    assert model["v2_shadow"]["available"] is False


@pytest.mark.parametrize(
    ("review", "candidate", "expected_maturity"),
    [
        (
            _review_without_v1(
                "Great product.",
                category="toys",
                sub_category="Mystery Toy",
                review_id="step6-l0-toys",
            ),
            _candidate(
                label_type="highlight",
                canonical="overall_satisfied",
                evidence="Great product",
                aspect_key="other",
            ),
            "L0_unknown",
        ),
        (
            _review_without_v1(
                "Great product, but the bib quality is poor.",
                category="baby",
                sub_category="Baby Bibs",
                review_id="step6-l1-baby",
            ),
            _candidate(
                label_type="issue",
                canonical="quality_problem",
                evidence="quality is poor",
                aspect_key="build_quality",
            ),
            "L1_generic",
        ),
        (
            _review_without_v1(
                "The storage pocket is not waterproof.",
                category="home",
                sub_category="床架",
                review_id="step6-l2-home",
            ),
            _candidate(
                label_type="issue",
                canonical="pocket_not_waterproof",
                evidence="pocket is not waterproof",
                aspect_key="accessory_storage",
            ),
            "L2_category",
        ),
    ],
)
def test_l0_l1_l2_maturity_blocked_candidates_do_not_enter_frontstage(
    review: dict[str, Any],
    candidate: dict[str, Any],
    expected_maturity: str,
) -> None:
    model = build_customer_label_v2_frontstage_read_model(
        review,
        flag=CustomerLabelV2FrontstageFlag(
            enabled=True,
            categories=(review["category"],),
            shadow_fixture_gate_passed=True,
        ),
        label_candidates=[candidate],
    )

    assert model["read_path"] == READ_PATH_V1_CURRENT
    assert model["fallback_reason"] == "maturity_not_enabled_for_v2_frontstage"
    assert model["v2_shadow"]["maturity_level"] == expected_maturity
    assert model["v2_shadow"]["display_occurrence_count"] == 0
    assert model["v2_shadow"]["candidate_pool_item_count"] == 1
    assert "maturity_blocked" in model["v2_shadow"]["downgrade_reasons"]
    assert frontstage_keys_from_read_model(model) == {"issue": [], "highlight": []}


def test_unknown_new_label_stays_candidate_pool_only_when_v2_path_is_selected() -> None:
    model = build_customer_label_v2_frontstage_read_model(
        _review_without_v1(
            "The boot seam leaked on the first trip.",
            review_id="step6-unknown-label",
        ),
        flag=_waders_flag(),
        label_candidates=[
            _candidate(
                label_type="issue",
                canonical="candidate:boot_seam_leak",
                raw_label="Boot seam leak",
                evidence="boot seam leaked",
                aspect_key="seam_integrity",
            )
        ],
    )

    assert model["read_path"] == READ_PATH_V2_SHADOW
    assert frontstage_keys_from_read_model(model) == {"issue": [], "highlight": []}
    assert model["v2_shadow"]["candidate_pool_item_count"] == 1
    assert model["v2_shadow"]["downgrade_reasons"] == ["unknown_label"]
    assert model["frontstage_occurrences"] == []


def test_rollback_returns_to_v1_current_even_when_v2_scope_matches() -> None:
    model = build_customer_label_v2_frontstage_read_model(
        _review_with_v1_zipper(),
        flag=_waders_flag(rollback_session_ids=("step6-session",)),
        label_candidates=[
            _candidate(
                label_type="issue",
                canonical="water_leaks_through",
                evidence="do not keep you dry",
                aspect_key="waterproof",
            )
        ],
    )

    assert model["read_path"] == READ_PATH_V1_CURRENT
    assert model["fallback_reason"] == "rollback_session"
    assert model["flag_decision"]["rollback_active"] is True
    assert frontstage_keys_from_read_model(model) == model["v1_current"]["keys"]
    assert "zipper_fails" in model["v1_current"]["keys"]["issue"]


def test_feature_flag_contract_declares_default_off_scopes_and_safe_consumers() -> None:
    contract = customer_label_v2_frontstage_contract_summary()

    assert contract["default_read_path"] == READ_PATH_V1_CURRENT
    assert contract["feature_flag"]["default_enabled"] is False
    assert set(contract["feature_flag"]["controls"]) == {
        "session_id",
        "category",
        "sub_category",
        "category_sub_category",
    }
    assert contract["feature_flag"]["shadow_fixture_gate_required"] is True
    assert set(contract["frontstage_consumers"]) == set(FRONTSTAGE_CONSUMERS)
    assert {"audit_occurrences", "candidate_pool_items"} <= set(contract["excluded_from_frontstage"])
