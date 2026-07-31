from __future__ import annotations

from typing import Any

import pytest

from backend_api.app.services.customer_label_catalog import (
    CustomerLabelCatalogState,
    set_customer_label_catalog_state_for_tests,
)
from backend_api.app.services.customer_label_v2_frontstage import (
    READ_PATH_V2_SHADOW,
    CustomerLabelV2FrontstageFlag,
    customer_label_v2_frontstage_flag_from_env,
)
from backend_api.app.services.customer_label_v2_shadow import run_customer_label_v2_shadow
from backend_api.app.services.specific_issue import (
    CUSTOMER_LABEL_OCCURRENCE_RULESET_VERSION,
    CUSTOMER_LABEL_OCCURRENCE_SCHEMA_VERSION,
    build_customer_highlight_rows,
    build_specific_issue_rows,
    customer_highlight_tags_for_comment,
    customer_issue_tags_for_comment,
    decorate_comment_customer_labels,
    iter_customer_highlight_occurrences,
    iter_specific_issue_occurrences,
)
from review_analyzer.exporter import _build_comments_data


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
        "source_detail": "step7_v1_fixture",
        "evidence_verified": True,
        "cluster_propagated": False,
        "schema_version": CUSTOMER_LABEL_OCCURRENCE_SCHEMA_VERSION,
        "ruleset_version": CUSTOMER_LABEL_OCCURRENCE_RULESET_VERSION,
        "display_allowed": True,
    }


def _candidate(
    *,
    label_type: str,
    canonical: str,
    evidence: str,
    aspect_key: str,
    display_en: str,
    display_zh: str,
    confidence: float = 0.9,
    subcategory_specificity: str = "sub_category",
) -> dict[str, Any]:
    return {
        "label_type": label_type,
        "canonical_label_key": canonical,
        "raw_label": display_en,
        "display_label_en": display_en,
        "display_label_zh": display_zh,
        "aspect_key": aspect_key,
        "polarity": "negative" if label_type == "issue" else "positive",
        "evidence_candidate": evidence,
        "confidence": confidence,
        "subcategory_specificity": subcategory_specificity,
        "reason": "step7 integration fixture",
    }


def _review_with_v1_zipper(*, review_id: str = "step7-review-waders") -> dict[str, Any]:
    return {
        "id": review_id,
        "session_id": "step7-session",
        "product_id": "TIDEWE-step7",
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
    review_id: str = "step7-review-no-v1",
) -> dict[str, Any]:
    return {
        "id": review_id,
        "session_id": "step7-session",
        "product_id": "TIDEWE-step7",
        "content": content,
        "rating": 2,
        "category": category,
        "sub_category": sub_category,
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


def _with_stored_shadow(review: dict[str, Any], candidates: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        **review,
        "customer_label_v2_shadow_result": run_customer_label_v2_shadow(
            review,
            label_candidates=candidates,
        ),
    }


def _four_path_snapshot(comments: list[dict[str, Any]]) -> dict[str, Any]:
    issue_rows = build_specific_issue_rows(comments, locale="en", limit=20)
    highlight_rows = build_customer_highlight_rows(comments, locale="en", limit=20)
    _, raw_rows = _build_comments_data(comments, include_specific_issue=True)
    return {
        "top_issue_keys": [str(row.get("canonical_issue_key") or "") for row in issue_rows],
        "top_highlight_keys": [str(row.get("canonical_highlight_key") or "") for row in highlight_rows],
        "detail_issue_tags": [customer_issue_tags_for_comment(comment, locale="en") for comment in comments],
        "detail_highlight_tags": [customer_highlight_tags_for_comment(comment, locale="en") for comment in comments],
        "raw_issue_labels": [str(row[11]) for row in raw_rows],
        "raw_issue_evidence": [str(row[12]) for row in raw_rows],
        "raw_highlight_labels": [str(row[13]) for row in raw_rows],
        "raw_highlight_evidence": [str(row[14]) for row in raw_rows],
        "single_issue_keys": [
            str(occurrence.get("canonical_issue_key") or "")
            for comment in comments
            for occurrence in iter_specific_issue_occurrences(comment, locale="en")
        ],
        "single_highlight_keys": [
            str(occurrence.get("canonical_highlight_key") or "")
            for comment in comments
            for occurrence in iter_customer_highlight_occurrences(comment, locale="en")
        ],
    }


def test_env_flag_defaults_off_and_runtime_shadow_off() -> None:
    flag = customer_label_v2_frontstage_flag_from_env({})

    assert flag.enabled is False
    assert flag.shadow_fixture_gate_passed is False
    assert flag.allow_runtime_shadow is False
    assert flag.enabled_maturity_levels == ("L3_sub_category",)


def test_flag_off_four_paths_preserve_v1_current_even_when_stored_v2_shadow_exists() -> None:
    review = _with_stored_shadow(
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
    decorated = decorate_comment_customer_labels(
        review,
        locale="en",
        v2_frontstage_flag=CustomerLabelV2FrontstageFlag(),
    )
    baseline = decorate_comment_customer_labels(
        _review_with_v1_zipper(),
        locale="en",
        v2_frontstage_flag=CustomerLabelV2FrontstageFlag(),
    )

    snapshot = _four_path_snapshot([decorated])
    baseline_snapshot = _four_path_snapshot([baseline])

    assert "customer_label_v2_frontstage_read_model" not in decorated
    assert snapshot == baseline_snapshot
    assert "zipper_fails" in snapshot["single_issue_keys"]


def test_flag_on_l3_waders_four_paths_consume_only_verified_v2_display() -> None:
    review = _with_stored_shadow(
        _review_with_v1_zipper(),
        [
            _candidate(
                label_type="issue",
                canonical="water_leaks_through",
                display_en="Water Leaks Through",
                display_zh="防水性差",
                aspect_key="waterproof",
                evidence="do not keep you dry",
            ),
            _candidate(
                label_type="highlight",
                canonical="fits_as_expected",
                display_en="Fits as Expected",
                display_zh="尺码合适",
                aspect_key="size_fit",
                evidence="fit was perfect",
            ),
            _candidate(
                label_type="issue",
                canonical="water_leaks_through",
                display_en="Water Leaks Through",
                display_zh="防水性差",
                aspect_key="waterproof",
                evidence="not in this review",
            ),
        ],
    )
    decorated = decorate_comment_customer_labels(
        review,
        locale="en",
        v2_frontstage_flag=_waders_flag(),
    )

    snapshot = _four_path_snapshot([decorated])
    read_model = decorated["customer_label_v2_frontstage_read_model"]

    assert read_model["read_path"] == READ_PATH_V2_SHADOW
    assert read_model["v2_shadow"]["audit_occurrence_count"] == 1
    assert snapshot["top_issue_keys"] == ["water_leaks_through"]
    assert snapshot["top_highlight_keys"] == ["fits_as_expected"]
    assert snapshot["detail_issue_tags"] == [["Water Leaks Through"]]
    assert snapshot["detail_highlight_tags"] == [["Fits as Expected"]]
    assert snapshot["raw_issue_labels"] == ["防水性差"]
    assert snapshot["raw_issue_evidence"] == ["do not keep you dry"]
    assert snapshot["raw_highlight_labels"] == ["尺码合适"]
    assert snapshot["raw_highlight_evidence"] == ["fit was perfect"]
    assert snapshot["single_issue_keys"] == ["water_leaks_through"]
    assert snapshot["single_highlight_keys"] == ["fits_as_expected"]
    assert "zipper_fails" not in snapshot["single_issue_keys"]


@pytest.mark.parametrize(
    ("review", "candidate", "expected_maturity"),
    [
        (
            _review_without_v1(
                "Great product.",
                category="toys",
                sub_category="Mystery Toy",
                review_id="step7-l0",
            ),
            _candidate(
                label_type="highlight",
                canonical="overall_satisfied",
                display_en="Overall Satisfied",
                display_zh="整体满意",
                aspect_key="other",
                evidence="Great product",
                subcategory_specificity="generic",
            ),
            "L0_unknown",
        ),
        (
            _review_without_v1(
                "The bib quality is poor.",
                category="baby",
                sub_category="Baby Bibs",
                review_id="step7-l1",
            ),
            _candidate(
                label_type="issue",
                canonical="quality_problem",
                display_en="Quality Problem",
                display_zh="质量问题",
                aspect_key="build_quality",
                evidence="quality is poor",
                subcategory_specificity="category",
            ),
            "L1_generic",
        ),
        (
            _review_without_v1(
                "The storage pocket is not waterproof.",
                category="home",
                sub_category="Bed Frame",
                review_id="step7-l2",
            ),
            _candidate(
                label_type="issue",
                canonical="pocket_not_waterproof",
                display_en="Pocket Not Waterproof",
                display_zh="口袋不防水",
                aspect_key="accessory_storage",
                evidence="pocket is not waterproof",
            ),
            "L2_category",
        ),
    ],
)
def test_l0_l1_l2_maturity_blocked_do_not_enter_actual_frontstage_paths(
    review: dict[str, Any],
    candidate: dict[str, Any],
    expected_maturity: str,
) -> None:
    decorated = decorate_comment_customer_labels(
        _with_stored_shadow(review, [candidate]),
        locale="en",
        v2_frontstage_flag=CustomerLabelV2FrontstageFlag(
            enabled=True,
            categories=(review["category"],),
            shadow_fixture_gate_passed=True,
            allow_runtime_shadow=False,
        ),
    )

    snapshot = _four_path_snapshot([decorated])
    shadow = decorated["customer_label_v2_shadow_result"]

    assert shadow["maturity_level"] == expected_maturity
    assert "maturity_blocked" in shadow["downgrade_reasons"]
    assert "customer_label_v2_frontstage_read_model" not in decorated
    assert snapshot["top_issue_keys"] == []
    assert snapshot["top_highlight_keys"] == []
    assert snapshot["detail_issue_tags"] == [[]]
    assert snapshot["detail_highlight_tags"] == [[]]
    assert snapshot["raw_issue_labels"] == [""]
    assert snapshot["raw_highlight_labels"] == [""]
    assert snapshot["single_issue_keys"] == []
    assert snapshot["single_highlight_keys"] == []


def test_unknown_new_label_stays_out_of_actual_frontstage_paths_when_v2_selected() -> None:
    decorated = decorate_comment_customer_labels(
        _with_stored_shadow(
            _review_without_v1(
                "The boot seam leaked on the first trip.",
                review_id="step7-unknown",
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
        ),
        locale="en",
        v2_frontstage_flag=_waders_flag(),
    )

    snapshot = _four_path_snapshot([decorated])
    read_model = decorated["customer_label_v2_frontstage_read_model"]

    assert read_model["read_path"] == READ_PATH_V2_SHADOW
    assert read_model["v2_shadow"]["candidate_pool_item_count"] == 1
    assert read_model["v2_shadow"]["downgrade_reasons"] == ["unknown_label"]
    assert snapshot["top_issue_keys"] == []
    assert snapshot["detail_issue_tags"] == [[]]
    assert snapshot["raw_issue_labels"] == [""]
    assert snapshot["single_issue_keys"] == []


def test_rollback_returns_actual_frontstage_paths_to_v1_current() -> None:
    review = _with_stored_shadow(
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
    decorated = decorate_comment_customer_labels(
        review,
        locale="en",
        v2_frontstage_flag=_waders_flag(rollback_session_ids=("step7-session",)),
    )
    baseline = decorate_comment_customer_labels(
        _review_with_v1_zipper(),
        locale="en",
        v2_frontstage_flag=CustomerLabelV2FrontstageFlag(),
    )

    snapshot = _four_path_snapshot([decorated])
    baseline_snapshot = _four_path_snapshot([baseline])

    assert "customer_label_v2_frontstage_read_model" not in decorated
    assert snapshot == baseline_snapshot
    assert "zipper_fails" in snapshot["single_issue_keys"]
