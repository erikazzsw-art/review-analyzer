from __future__ import annotations

from typing import Any

import pytest

from backend_api.app.services.customer_label_catalog import (
    CustomerLabelCatalogState,
    set_customer_label_catalog_state_for_tests,
)
from backend_api.app.services.customer_label_v2_frontstage import (
    READ_PATH_V1_CURRENT,
    READ_PATH_V2_SHADOW,
    CustomerLabelV2FrontstageFlag,
    build_customer_label_v2_frontstage_readiness_dry_run_report,
)
from backend_api.app.services.customer_label_v2_shadow import run_customer_label_v2_shadow
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
        "source_detail": "step7_5_v1_fixture",
        "evidence_verified": True,
        "cluster_propagated": False,
        "schema_version": CUSTOMER_LABEL_OCCURRENCE_SCHEMA_VERSION,
        "ruleset_version": CUSTOMER_LABEL_OCCURRENCE_RULESET_VERSION,
        "display_allowed": True,
    }


def _review_with_v1_zipper(*, review_id: str = "step75-review-waders") -> dict[str, Any]:
    return {
        "id": review_id,
        "session_id": "step75-session",
        "product_id": "TIDEWE-step75",
        "content": "The zipper broke on day one. They do not keep you dry, but the fit was perfect.",
        "rating": 1,
        "category": "outdoor",
        "sub_category": "waders",
        "aspects_json": {
            "customer_label_occurrence_schema_version": CUSTOMER_LABEL_OCCURRENCE_SCHEMA_VERSION,
            "sub_category": "waders",
            "customer_label_occurrences": [
                _v1_occurrence(
                    label_type="issue",
                    canonical="zipper_fails",
                    display_en="Zipper Fails",
                    display_zh="拉链容易故障",
                    aspect_key="zipper_quality",
                    evidence="zipper broke",
                    comment_id=review_id,
                )
            ],
        },
    }


def _review_without_v1(
    content: str,
    *,
    category: str = "outdoor",
    sub_category: str = "waders",
    review_id: str = "step75-review-no-v1",
) -> dict[str, Any]:
    return {
        "id": review_id,
        "session_id": "step75-session",
        "product_id": "TIDEWE-step75",
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
    display_en: str | None = None,
    display_zh: str | None = None,
    confidence: float = 0.9,
    subcategory_specificity: str = "sub_category",
) -> dict[str, Any]:
    display = display_en or " ".join(part.capitalize() for part in canonical.replace("candidate:", "").split("_"))
    return {
        "label_type": label_type,
        "canonical_label_key": canonical,
        "raw_label": display,
        "display_label_en": display,
        "display_label_zh": display_zh or display,
        "aspect_key": aspect_key,
        "polarity": "negative" if label_type == "issue" else "positive",
        "evidence_candidate": evidence,
        "confidence": confidence,
        "subcategory_specificity": subcategory_specificity,
        "reason": "step7.5 readiness fixture",
    }


def _with_stored_shadow(review: dict[str, Any], candidates: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        **review,
        "customer_label_v2_shadow_result": run_customer_label_v2_shadow(
            review,
            label_candidates=candidates,
        ),
    }


def _waders_flag(**overrides: Any) -> CustomerLabelV2FrontstageFlag:
    payload = {
        "enabled": True,
        "sub_categories": ("outdoor/waders",),
        "shadow_fixture_gate_passed": True,
        "allow_runtime_shadow": False,
    }
    payload.update(overrides)
    return CustomerLabelV2FrontstageFlag(**payload)


def _single_preview(report: dict[str, Any]) -> dict[str, Any]:
    return report["selected_read_path_preview"][0]


def test_flag_off_dry_run_selects_v1_current_and_counts_flag_off() -> None:
    report = build_customer_label_v2_frontstage_readiness_dry_run_report(
        [
            _with_stored_shadow(
                _review_with_v1_zipper(),
                [
                    _candidate(
                        label_type="issue",
                        canonical="water_leaks_through",
                        display_en="Water Leaks Through",
                        display_zh="防水性差",
                        aspect_key="waterproof",
                        evidence="do not keep you dry",
                    )
                ],
            )
        ],
        flag=CustomerLabelV2FrontstageFlag(),
    )

    assert report["status"] == "PASS"
    assert report["observability"]["v1_selected_count"] == 1
    assert report["observability"]["blocked_by_flag_off"] == 1
    assert _single_preview(report)["selected_read_path"] == READ_PATH_V1_CURRENT
    assert _single_preview(report)["fallback_reason"] == "flag_off"


def test_flag_on_scope_miss_dry_run_selects_v1_current_and_counts_scope() -> None:
    report = build_customer_label_v2_frontstage_readiness_dry_run_report(
        [
            _with_stored_shadow(
                _review_with_v1_zipper(),
                [
                    _candidate(
                        label_type="issue",
                        canonical="water_leaks_through",
                        aspect_key="waterproof",
                        evidence="do not keep you dry",
                    )
                ],
            )
        ],
        flag=CustomerLabelV2FrontstageFlag(
            enabled=True,
            categories=("home",),
            shadow_fixture_gate_passed=True,
            allow_runtime_shadow=False,
        ),
    )

    assert report["observability"]["blocked_by_scope"] == 1
    assert _single_preview(report)["selected_read_path"] == READ_PATH_V1_CURRENT
    assert _single_preview(report)["fallback_reason"] == "scope_not_matched"


def test_fixture_gate_fail_dry_run_selects_v1_current_and_counts_fixture_gate() -> None:
    report = build_customer_label_v2_frontstage_readiness_dry_run_report(
        [
            _with_stored_shadow(
                _review_with_v1_zipper(),
                [
                    _candidate(
                        label_type="issue",
                        canonical="water_leaks_through",
                        aspect_key="waterproof",
                        evidence="do not keep you dry",
                    )
                ],
            )
        ],
        flag=_waders_flag(shadow_fixture_gate_passed=False),
    )

    assert report["observability"]["blocked_by_fixture_gate"] == 1
    assert _single_preview(report)["selected_read_path"] == READ_PATH_V1_CURRENT
    assert _single_preview(report)["fallback_reason"] == "shadow_fixture_gate_blocked"


@pytest.mark.parametrize(
    ("review", "candidate", "expected_maturity"),
    [
        (
            _review_without_v1(
                "Great product.",
                category="toys",
                sub_category="Mystery Toy",
                review_id="step75-l0",
            ),
            _candidate(
                label_type="highlight",
                canonical="overall_satisfied",
                evidence="Great product",
                aspect_key="other",
                subcategory_specificity="generic",
            ),
            "L0_unknown",
        ),
        (
            _review_without_v1(
                "The bib quality is poor.",
                category="baby",
                sub_category="Baby Bibs",
                review_id="step75-l1",
            ),
            _candidate(
                label_type="issue",
                canonical="quality_problem",
                evidence="quality is poor",
                aspect_key="build_quality",
                subcategory_specificity="category",
            ),
            "L1_generic",
        ),
        (
            _review_without_v1(
                "The storage pocket is not waterproof.",
                category="home",
                sub_category="Bed Frame",
                review_id="step75-l2",
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
def test_l0_l1_l2_dry_run_selects_v1_current_and_counts_maturity(
    review: dict[str, Any],
    candidate: dict[str, Any],
    expected_maturity: str,
) -> None:
    report = build_customer_label_v2_frontstage_readiness_dry_run_report(
        [_with_stored_shadow(review, [candidate])],
        flag=CustomerLabelV2FrontstageFlag(
            enabled=True,
            categories=(review["category"],),
            shadow_fixture_gate_passed=True,
            allow_runtime_shadow=False,
        ),
    )

    preview = _single_preview(report)
    assert report["observability"]["blocked_by_maturity"] == 1
    assert preview["selected_read_path"] == READ_PATH_V1_CURRENT
    assert preview["fallback_reason"] == "maturity_not_enabled_for_v2_frontstage"
    assert preview["checks"]["maturity_level"] == expected_maturity


def test_l3_waders_with_stored_shadow_previews_v2_shadow() -> None:
    report = build_customer_label_v2_frontstage_readiness_dry_run_report(
        [
            _with_stored_shadow(
                _review_with_v1_zipper(),
                [
                    _candidate(
                        label_type="issue",
                        canonical="water_leaks_through",
                        display_en="Water Leaks Through",
                        display_zh="防水性差",
                        aspect_key="waterproof",
                        evidence="do not keep you dry",
                    )
                ],
            )
        ],
        flag=_waders_flag(),
    )

    preview = _single_preview(report)
    assert report["observability"]["v2_selected_count"] == 1
    assert report["observability"]["frontstage_occurrence_count"] == 1
    assert preview["selected_read_path"] == READ_PATH_V2_SHADOW
    assert preview["selected_keys"] == {"issue": ["water_leaks_through"], "highlight": []}
    assert preview["checks"]["stored_shadow_available"] is True


def test_unknown_new_label_dry_run_stays_out_of_frontstage_and_counts_unknown() -> None:
    report = build_customer_label_v2_frontstage_readiness_dry_run_report(
        [
            _with_stored_shadow(
                _review_without_v1(
                    "The boot seam leaked on the first trip.",
                    review_id="step75-unknown",
                ),
                [
                    _candidate(
                        label_type="issue",
                        canonical="candidate:boot_seam_leak",
                        display_en="Boot Seam Leak",
                        display_zh="靴缝漏水",
                        aspect_key="seam_integrity",
                        evidence="boot seam leaked",
                    )
                ],
            )
        ],
        flag=_waders_flag(),
    )

    preview = _single_preview(report)
    assert report["observability"]["blocked_by_unknown_label"] == 1
    assert report["observability"]["frontstage_occurrence_count"] == 0
    assert preview["selected_read_path"] == READ_PATH_V2_SHADOW
    assert preview["selected_keys"] == {"issue": [], "highlight": []}
    assert "blocked_by_unknown_label" in preview["blocked_reasons"]


def test_no_stored_shadow_dry_run_blocks_v2_even_if_runtime_shadow_flag_is_true() -> None:
    report = build_customer_label_v2_frontstage_readiness_dry_run_report(
        [_review_with_v1_zipper()],
        flag=_waders_flag(allow_runtime_shadow=True),
    )

    preview = _single_preview(report)
    assert report["effective_feature_flag"]["allow_runtime_shadow"] is False
    assert report["observability"]["blocked_by_no_stored_shadow"] == 1
    assert report["safety"]["runtime_shadow_called"] is False
    assert preview["selected_read_path"] == READ_PATH_V1_CURRENT
    assert preview["fallback_reason"] == "v2_shadow_missing"
    assert preview["checks"]["stored_shadow_available"] is False


def test_rollback_dry_run_returns_v1_current_and_counts_rollback() -> None:
    report = build_customer_label_v2_frontstage_readiness_dry_run_report(
        [
            _with_stored_shadow(
                _review_with_v1_zipper(),
                [
                    _candidate(
                        label_type="issue",
                        canonical="water_leaks_through",
                        aspect_key="waterproof",
                        evidence="do not keep you dry",
                    )
                ],
            )
        ],
        flag=_waders_flag(rollback_session_ids=("step75-session",)),
    )

    preview = _single_preview(report)
    assert report["observability"]["rollback_selected_count"] == 1
    assert preview["selected_read_path"] == READ_PATH_V1_CURRENT
    assert preview["fallback_reason"] == "rollback_session"
    assert preview["checks"]["rollback_would_select_v1_current"] is True
