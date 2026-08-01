from __future__ import annotations

from typing import Any

from backend_api.app.services.review_signal_frontstage import (
    READ_PATH_REVIEW_SIGNAL_STORED_SHADOW,
    READ_PATH_V1_CURRENT,
    ReviewSignalFrontstageFlag,
    attach_review_signal_frontstage_adapter_for_local_test,
    build_review_signal_frontstage_observability_snapshot,
    build_review_signal_frontstage_read_model,
    frontstage_keys_from_review_signal_read_model,
    resolve_review_signal_frontstage_config,
)
from backend_api.app.services.review_signal_shadow import (
    ROUTE_AUDIT_FILTER,
    ROUTE_CONSUMER_PROFILE,
    ROUTE_CUSTOMER_ISSUE_CANDIDATE,
    ROUTE_CUSTOMER_LABEL_CANDIDATE,
    ROUTE_PURCHASE_MOTIVES,
    ROUTE_UNMET_NEEDS,
    SIGNAL_ACCESSORY_ONLY,
    SIGNAL_AUDIENCE,
    SIGNAL_AUDIT_ONLY,
    SIGNAL_EXPECTATION,
    SIGNAL_PRODUCT_NEGATIVE,
    SIGNAL_PRODUCT_POSITIVE,
    SIGNAL_PURCHASE_MOTIVATION,
)
from backend_api.app.services.specific_issue import (
    CUSTOMER_LABEL_OCCURRENCE_RULESET_VERSION,
    CUSTOMER_LABEL_OCCURRENCE_SCHEMA_VERSION,
    build_customer_highlight_rows,
    build_specific_issue_rows,
    customer_highlight_tags_for_comment,
    customer_issue_tags_for_comment,
    iter_customer_highlight_occurrences,
    iter_specific_issue_occurrences,
)
from review_analyzer.exporter import _build_comments_data


def _v1_occurrence(
    *,
    label_type: str,
    canonical: str,
    display_en: str,
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
        "display_label_zh": display_en,
        "aspect_key": aspect_key,
        "evidence_span": evidence,
        "evidence_start": -1,
        "evidence_end": -1,
        "confidence": "high",
        "source": "rule",
        "source_detail": "phase4_v1_fixture",
        "evidence_verified": True,
        "cluster_propagated": False,
        "schema_version": CUSTOMER_LABEL_OCCURRENCE_SCHEMA_VERSION,
        "ruleset_version": CUSTOMER_LABEL_OCCURRENCE_RULESET_VERSION,
        "display_allowed": True,
        "source_review_allowed": True,
        "verified_evidence": True,
        "legacy_fallback": False,
        "aspect_allowed": True,
        "context_allowed": True,
    }


def _review_with_v1() -> dict[str, Any]:
    return {
        "id": "phase4-review-v1",
        "session_id": "phase4-session",
        "product_id": "phase4-product",
        "content": "The zipper broke on day one.",
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
                    aspect_key="zipper_quality",
                    evidence="zipper broke",
                    comment_id="phase4-review-v1",
                )
            ],
        },
    }


def _review_without_v1() -> dict[str, Any]:
    return {
        "id": "phase4-review-guarded",
        "session_id": "phase4-session",
        "product_id": "phase4-product",
        "content": (
            "The seams leaked after one trip. They are comfortable for long walks. "
            "My daughter used them for fishing. I bought them for spring creeks. "
            "I expected more traction on slick rocks. The hanger works great. "
            "Overall good, but the missing phrase is not here."
        ),
        "rating": 4,
        "category": "outdoor",
        "sub_category": "waders",
    }


def _stored_occurrence(
    *,
    label_type: str,
    canonical: str,
    signal_type: str,
    route_to: list[str],
    evidence: str,
    display_en: str,
    aspect_key: str = "fit",
    **overrides: Any,
) -> dict[str, Any]:
    payload = {
        "label_type": label_type,
        "canonical_label_key": canonical,
        "display_label_en": display_en,
        "display_label_zh": display_en,
        "signal_type": signal_type,
        "route_to": route_to,
        "evidence_span": evidence,
        "evidence_verified": True,
        "display_allowed": True,
        "source_review_allowed": True,
        "aspect_allowed": True,
        "context_allowed": True,
        "maturity_allowed": True,
        "cluster_propagated": False,
        "legacy_fallback": False,
        "mapping_status": "mapped",
        "confidence": 0.93,
        "aspect_key": aspect_key,
    }
    payload.update(overrides)
    return payload


def _stored_shadow_with_mixed_occurrences() -> dict[str, Any]:
    return {
        "schema_version": "review-signal-stored-shadow.test",
        "frontstage_occurrences": [
            _stored_occurrence(
                label_type="issue",
                canonical="water_leaks_through",
                signal_type=SIGNAL_PRODUCT_NEGATIVE,
                route_to=["user_experience.negative", ROUTE_CUSTOMER_ISSUE_CANDIDATE],
                evidence="seams leaked",
                display_en="Water Leaks Through",
                aspect_key="waterproof",
            ),
            _stored_occurrence(
                label_type="highlight",
                canonical="comfortable_to_wear",
                signal_type=SIGNAL_PRODUCT_POSITIVE,
                route_to=["user_experience.positive", ROUTE_CUSTOMER_LABEL_CANDIDATE],
                evidence="comfortable",
                display_en="Comfortable To Wear",
                aspect_key="comfort",
            ),
            _stored_occurrence(
                label_type="issue",
                canonical="candidate:boot_seam_leak",
                signal_type=SIGNAL_PRODUCT_NEGATIVE,
                route_to=["user_experience.negative", ROUTE_CUSTOMER_ISSUE_CANDIDATE],
                evidence="seams leaked",
                display_en="Boot Seam Leak",
                aspect_key="seam_integrity",
            ),
            _stored_occurrence(
                label_type="highlight",
                canonical="",
                signal_type=SIGNAL_PRODUCT_POSITIVE,
                route_to=["user_experience.positive", ROUTE_CUSTOMER_LABEL_CANDIDATE],
                evidence="comfortable",
                display_en="Unresolved Comfort Variant",
                mapping_status="extraction_unresolved",
            ),
            _stored_occurrence(
                label_type="issue",
                canonical="family_use",
                signal_type=SIGNAL_AUDIENCE,
                route_to=[ROUTE_CONSUMER_PROFILE],
                evidence="daughter",
                display_en="Family Use",
            ),
            _stored_occurrence(
                label_type="highlight",
                canonical="purchase_reason",
                signal_type=SIGNAL_PURCHASE_MOTIVATION,
                route_to=[ROUTE_PURCHASE_MOTIVES],
                evidence="I bought them for spring creeks",
                display_en="Spring Creek Purchase",
            ),
            _stored_occurrence(
                label_type="issue",
                canonical="traction_expectation",
                signal_type=SIGNAL_EXPECTATION,
                route_to=[ROUTE_UNMET_NEEDS],
                evidence="I expected more traction on slick rocks",
                display_en="Traction Expectation",
            ),
            _stored_occurrence(
                label_type="issue",
                canonical="missing_wader_hanger",
                signal_type=SIGNAL_ACCESSORY_ONLY,
                route_to=[ROUTE_AUDIT_FILTER],
                evidence="hanger works great",
                display_en="Missing Wader Hanger",
            ),
            _stored_occurrence(
                label_type="highlight",
                canonical="overall_satisfied",
                signal_type=SIGNAL_AUDIT_ONLY,
                route_to=[ROUTE_AUDIT_FILTER],
                evidence="Overall good",
                display_en="Overall Satisfied",
                audit_only=True,
            ),
            _stored_occurrence(
                label_type="issue",
                canonical="water_leaks_through",
                signal_type=SIGNAL_PRODUCT_NEGATIVE,
                route_to=["user_experience.negative", ROUTE_CUSTOMER_ISSUE_CANDIDATE],
                evidence="missing seam evidence",
                display_en="Water Leaks Through",
                display_allowed=False,
            ),
        ],
    }


def _phase4_flag(**overrides: Any) -> ReviewSignalFrontstageFlag:
    payload = {"enabled": True, "session_ids": ("phase4-session",)}
    payload.update(overrides)
    return ReviewSignalFrontstageFlag(**payload)


def _raw_value(headers: list[str], row: list[str], header: str) -> str:
    return str(row[headers.index(header)])


def _four_path_snapshot(comments: list[dict[str, Any]]) -> dict[str, Any]:
    issue_rows = build_specific_issue_rows(comments, locale="en", limit=20)
    highlight_rows = build_customer_highlight_rows(comments, locale="en", limit=20)
    raw_headers, raw_rows = _build_comments_data(comments, include_specific_issue=True)
    return {
        "top_issue_keys": [str(row.get("canonical_issue_key") or "") for row in issue_rows],
        "top_highlight_keys": [str(row.get("canonical_highlight_key") or "") for row in highlight_rows],
        "detail_issue_tags": [customer_issue_tags_for_comment(comment, locale="en") for comment in comments],
        "detail_highlight_tags": [customer_highlight_tags_for_comment(comment, locale="en") for comment in comments],
        "raw_issue_labels": [_raw_value(raw_headers, row, "客户痛点") for row in raw_rows],
        "raw_issue_evidence": [_raw_value(raw_headers, row, "痛点证据") for row in raw_rows],
        "raw_highlight_labels": [_raw_value(raw_headers, row, "客户亮点") for row in raw_rows],
        "raw_highlight_evidence": [_raw_value(raw_headers, row, "亮点证据") for row in raw_rows],
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
        "single_issue_evidence_verified": [
            bool(occurrence.get("verified_evidence"))
            for comment in comments
            for occurrence in iter_specific_issue_occurrences(comment, locale="en")
        ],
        "single_highlight_evidence_verified": [
            bool(occurrence.get("verified_evidence"))
            for comment in comments
            for occurrence in iter_customer_highlight_occurrences(comment, locale="en")
        ],
    }


def test_results_top10_keeps_v1_current_when_review_signal_flag_off() -> None:
    review = _review_with_v1()
    model = build_review_signal_frontstage_read_model(
        review,
        flag=ReviewSignalFrontstageFlag(),
        stored_shadow=_stored_shadow_with_mixed_occurrences(),
    )
    decorated = attach_review_signal_frontstage_adapter_for_local_test(review, model)
    snapshot = _four_path_snapshot([decorated])

    assert model["read_path"] == READ_PATH_V1_CURRENT
    assert model["fallback_reason"] == "flag_off"
    assert frontstage_keys_from_review_signal_read_model(model) == {"issue": [], "highlight": []}
    assert snapshot["top_issue_keys"] == ["zipper_fails"]
    assert snapshot["detail_issue_tags"] == [["Zipper Fails"]]
    assert snapshot["raw_issue_labels"] == ["Zipper Fails"]
    assert snapshot["single_issue_keys"] == ["zipper_fails"]


def test_guarded_read_path_feeds_existing_four_paths_with_product_signals_only() -> None:
    review = _review_without_v1()
    model = build_review_signal_frontstage_read_model(
        review,
        flag=_phase4_flag(),
        stored_shadow=_stored_shadow_with_mixed_occurrences(),
    )
    decorated = attach_review_signal_frontstage_adapter_for_local_test(review, model)
    snapshot = _four_path_snapshot([decorated])
    observability = build_review_signal_frontstage_observability_snapshot([model])
    counters = observability["counters"]

    assert model["read_path"] == READ_PATH_REVIEW_SIGNAL_STORED_SHADOW
    assert frontstage_keys_from_review_signal_read_model(model) == {
        "issue": ["water_leaks_through"],
        "highlight": ["comfortable_to_wear"],
    }
    assert snapshot["top_issue_keys"] == ["water_leaks_through"]
    assert snapshot["top_highlight_keys"] == ["comfortable_to_wear"]
    assert snapshot["detail_issue_tags"] == [["Water Leaks Through"]]
    assert snapshot["detail_highlight_tags"] == [["Comfortable To Wear"]]
    assert snapshot["raw_issue_labels"] == ["Water Leaks Through"]
    assert snapshot["raw_issue_evidence"] == ["seams leaked"]
    assert snapshot["raw_highlight_labels"] == ["Comfortable To Wear"]
    assert snapshot["raw_highlight_evidence"] == ["comfortable"]
    assert snapshot["single_issue_keys"] == ["water_leaks_through"]
    assert snapshot["single_highlight_keys"] == ["comfortable_to_wear"]
    assert snapshot["single_issue_evidence_verified"] == [True]
    assert snapshot["single_highlight_evidence_verified"] == [True]

    assert counters["blocked_by_candidate_key"] == 1
    assert counters["blocked_by_mapping_unresolved"] == 1
    assert counters["blocked_by_audit_only"] >= 2
    assert counters["blocked_by_non_product_signal"] >= 4
    assert counters["blocked_by_display_gate"] >= 5
    assert counters["candidate_key_frontstage_count"] == 0
    assert counters["routing_leakage_count"] == 0
    assert counters["evidence_not_found_frontstage_count"] == 0
    assert counters["runtime_shadow_generated_count"] == 0
    assert observability["status"] == "PASS"


def test_guarded_read_path_fail_closed_controls_fallback_to_v1_current() -> None:
    review = _review_with_v1()
    matching_flag = _phase4_flag()
    invalid_flag = resolve_review_signal_frontstage_config({"enabled": "maybe"}, source="test").effective_feature_flag
    cases = [
        (
            "invalid_config",
            invalid_flag,
            _stored_shadow_with_mixed_occurrences(),
            "config_invalid",
        ),
        (
            "scope_miss",
            ReviewSignalFrontstageFlag(enabled=True, session_ids=("other-session",)),
            _stored_shadow_with_mixed_occurrences(),
            "scope_not_matched",
        ),
        ("stored_shadow_missing", matching_flag, None, "review_signal_stored_shadow_missing"),
        (
            "rollback",
            _phase4_flag(rollback_session_ids=("phase4-session",)),
            _stored_shadow_with_mixed_occurrences(),
            "rollback_session",
        ),
        ("kill_switch", _phase4_flag(kill_switch=True), _stored_shadow_with_mixed_occurrences(), "kill_switch_global"),
    ]
    models = [
        build_review_signal_frontstage_read_model(
            {**review, "id": case_name},
            flag=flag,
            stored_shadow=stored_shadow,
        )
        for case_name, flag, stored_shadow, _expected_reason in cases
    ]
    observability = build_review_signal_frontstage_observability_snapshot(models)
    counters = observability["counters"]

    assert [model["read_path"] for model in models] == [READ_PATH_V1_CURRENT] * len(cases)
    assert [model["fallback_reason"] for model in models] == [expected for *_rest, expected in cases]
    assert counters["blocked_by_config_invalid"] == 1
    assert counters["blocked_by_scope"] == 1
    assert counters["blocked_by_no_stored_shadow"] == 1
    assert counters["rollback_selected"] == 1
    assert counters["kill_switch_selected"] == 1
    assert counters["candidate_key_frontstage_count"] == 0
    assert counters["routing_leakage_count"] == 0
    assert counters["evidence_not_found_frontstage_count"] == 0
    assert counters["runtime_shadow_generated_count"] == 0


def test_single_tag_download_excludes_candidate_non_product_and_unverified_rows() -> None:
    review = _review_without_v1()
    model = build_review_signal_frontstage_read_model(
        review,
        flag=_phase4_flag(session_ids=(), category_sub_categories=("outdoor/waders",)),
        stored_shadow=_stored_shadow_with_mixed_occurrences(),
    )
    decorated = attach_review_signal_frontstage_adapter_for_local_test(review, model)
    snapshot = _four_path_snapshot([decorated])
    all_single_keys = snapshot["single_issue_keys"] + snapshot["single_highlight_keys"]

    assert model["flag_decision"]["matched_scope"] == "category_sub_category"
    assert all(not key.startswith("candidate:") for key in all_single_keys)
    assert "family_use" not in all_single_keys
    assert "purchase_reason" not in all_single_keys
    assert "traction_expectation" not in all_single_keys
    assert "missing_wader_hanger" not in all_single_keys
    assert "overall_satisfied" not in all_single_keys
    assert snapshot["single_issue_evidence_verified"] == [True]
    assert snapshot["single_highlight_evidence_verified"] == [True]
