from __future__ import annotations

from typing import Any

from backend_api.app.services.review_signal_shadow import (
    ROUTE_AUDIT_FILTER,
    ROUTE_CONSUMER_PROFILE,
    ROUTE_CUSTOMER_ISSUE_CANDIDATE,
    ROUTE_CUSTOMER_LABEL_CANDIDATE,
    SIGNAL_ACCESSORY_ONLY,
    SIGNAL_AUDIENCE,
    SIGNAL_COMPARISON_OR_OTHER_PRODUCT,
    SIGNAL_GENERIC_OR_VAGUE,
    SIGNAL_PRODUCT_NEGATIVE,
    SIGNAL_PRODUCT_POSITIVE,
    SIGNAL_SHIPPING_SERVICE,
    build_signal_derived_routing_projection,
    compare_baseline_to_signal_shadow,
    normalize_review_signal_gold_fragment,
    review_signal_shadow_safety_flags,
    run_review_signal_shadow,
)
from scripts.review_signal_step9_1_shadow_replay import (
    _build_gold_assimilation_artifact,
    _build_routing_projection_and_comparison_artifacts,
    _fragment,
    _signal_candidate_from_gold,
    build_local_gold_review_specs,
)


def _project(review: dict[str, Any], fragments: list[dict[str, Any]], existing: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    shadow = run_review_signal_shadow(
        review,
        signal_candidates=[_signal_candidate_from_gold(fragment) for fragment in fragments],
    )
    return build_signal_derived_routing_projection(
        review,
        existing_occurrences=existing or [],
        review_signals=shadow["review_signals"],
        gold_fragments=fragments,
    )


def test_local_gold_assimilation_schema_and_source_boundaries() -> None:
    specs = build_local_gold_review_specs()
    artifact = _build_gold_assimilation_artifact(specs)

    assert artifact["status"] == "PASS"
    assert artifact["review_count"] >= 30
    assert artifact["fragment_count"] >= 100
    assert artifact["schema_errors"] == []
    assert artifact["gold_coverage"]["evidence_not_found_count"] == 0

    source_kinds = artifact["gold_coverage"]["source_kind_counts"]
    assert source_kinds["screenshot_derived_gold"] >= 1
    assert source_kinds["human_gold_fixture"] >= 1
    assert source_kinds["blind_regression_fixture"] >= 1
    assert source_kinds["production_readonly_local_copy"] >= 1
    assert source_kinds["candidate_pool_reviewed"] >= 1

    required = {
        "review_id",
        "evidence_span",
        "expected_signal_type",
        "expected_polarity",
        "expected_current_product_scope",
        "expected_route_to",
        "source",
        "gold_reason",
    }
    for fragment in artifact["gold_fragments"]:
        assert required <= fragment.keys(), fragment
        assert fragment["source_kind"] in source_kinds
        assert fragment["evidence_verified"] is True


def test_current_product_positive_and_negative_projection_in_five_star_mixed_review() -> None:
    review = {
        "id": "projection-five-star",
        "rating": 5,
        "content": "Great fit and the seams leaked after one trip. My son used them for river fishing.",
    }
    fragments = [
        _fragment("projection-five-star", "Great fit", SIGNAL_PRODUCT_POSITIVE, source="test", source_kind="local_shadow_probe", dataset="test", gold_reason="Current product fit praise.", segment="five_star_mixed_review", label_type="label", canonical_label_key="fits_as_expected"),
        _fragment("projection-five-star", "seams leaked", SIGNAL_PRODUCT_NEGATIVE, source="test", source_kind="local_shadow_probe", dataset="test", gold_reason="Current product leak complaint.", segment="five_star_mixed_review", label_type="issue", canonical_label_key="water_leaks_through"),
        _fragment("projection-five-star", "son", SIGNAL_AUDIENCE, source="test", source_kind="local_shadow_probe", dataset="test", gold_reason="Audience context.", segment="audience_context_motivation_expectation"),
    ]
    projection = _project(review, fragments)

    assert projection["signal_shadow_issue_keys"] == ["water_leaks_through"]
    assert projection["signal_shadow_label_keys"] == ["fits_as_expected"]
    assert projection["consumer_profile_signals"][0]["evidence_span"] == "son"
    assert projection["non_product_leakage_count"] == 0


def test_non_product_old_accessory_shipping_and_generic_are_audit_only() -> None:
    review = {
        "id": "projection-audit-only",
        "rating": 4,
        "content": "Old Simms leaked. The case looks cute. Shipping was fast. Nice product.",
    }
    fragments = [
        _fragment("projection-audit-only", "Old Simms leaked", SIGNAL_COMPARISON_OR_OTHER_PRODUCT, source="test", source_kind="local_shadow_probe", dataset="test", gold_reason="Other product context.", segment="old_or_other_product"),
        _fragment("projection-audit-only", "case looks cute", SIGNAL_ACCESSORY_ONLY, source="test", source_kind="local_shadow_probe", dataset="test", gold_reason="Accessory-only context.", segment="accessory"),
        _fragment("projection-audit-only", "Shipping was fast", SIGNAL_SHIPPING_SERVICE, source="test", source_kind="local_shadow_probe", dataset="test", gold_reason="Shipping context.", segment="shipping_service"),
        _fragment("projection-audit-only", "Nice product", SIGNAL_GENERIC_OR_VAGUE, source="test", source_kind="local_shadow_probe", dataset="test", gold_reason="Generic/vague praise.", segment="generic_vague"),
    ]
    projection = _project(review, fragments)

    assert projection["signal_derived_customer_issue_candidates"] == []
    assert projection["signal_derived_customer_label_candidates"] == []
    assert {signal["evidence_span"] for signal in projection["audit_filter_signals"]} == {
        "Old Simms leaked",
        "case looks cute",
        "Shipping was fast",
        "Nice product",
    }
    assert all(signal["route_to"] == [ROUTE_AUDIT_FILTER] for signal in projection["audit_filter_signals"])


def test_evidence_not_found_does_not_enter_issue_or_label_candidates() -> None:
    review = {"id": "missing-evidence", "content": "The fit is good.", "rating": 5}
    shadow = run_review_signal_shadow(
        review,
        signal_candidates=[
            {
                "signal_type": SIGNAL_PRODUCT_POSITIVE,
                "polarity": "positive",
                "evidence_span": "battery lasts all week",
                "current_product_scope": "current_product",
                "confidence": 0.9,
                "reason": "Missing evidence probe.",
            }
        ],
    )
    projection = build_signal_derived_routing_projection(
        review,
        review_signals=shadow["review_signals"],
        gold_fragments=[],
    )

    assert projection["signal_derived_customer_issue_candidates"] == []
    assert projection["signal_derived_customer_label_candidates"] == []
    assert projection["audit_filter_signals"][0]["route_blocked_reasons"] == ["evidence_not_found"]
    assert projection["evidence_not_found_count"] == 1


def test_baseline_vs_signal_shadow_fp_fn_split_metrics() -> None:
    review = {"id": "fp-fn-split", "content": "The hanger works great. Good traction.", "rating": 5}
    fragments = [
        _fragment("fp-fn-split", "hanger works great", SIGNAL_ACCESSORY_ONLY, source="test", source_kind="local_shadow_probe", dataset="test", gold_reason="Accessory-only positive context.", segment="accessory"),
        _fragment("fp-fn-split", "Good traction", SIGNAL_PRODUCT_POSITIVE, source="test", source_kind="local_shadow_probe", dataset="test", gold_reason="Current product traction praise.", segment="mixed_review", label_type="label", canonical_label_key="good_traction"),
    ]
    existing = [
        {"label_type": "issue", "canonical_label_key": "missing_wader_hanger", "evidence_span": "hanger works great"},
        {"label_type": "issue", "canonical_label_key": "poor_traction", "evidence_span": "Good traction"},
    ]
    projection = _project(review, fragments, existing)
    comparison = compare_baseline_to_signal_shadow(
        dataset="test",
        baseline_issue_keys=["missing_wader_hanger", "poor_traction"],
        baseline_label_keys=[],
        projection=projection,
        gold_fragments=[
            normalize_review_signal_gold_fragment(fragment, content_by_review_id={"fp-fn-split": review["content"]})
            for fragment in fragments
        ],
    )

    assert comparison["baseline"]["customer_issue"]["fp"] == 2
    assert comparison["baseline"]["customer_label"]["fn"] == 1
    assert comparison["signal_shadow"]["customer_issue"]["fp"] == 0
    assert comparison["signal_shadow"]["customer_label"]["fn"] == 0
    assert comparison["split_metrics"]["routing_fp"]["issue"] == 2
    assert comparison["split_metrics"]["label_extraction_fn"]["label"] == 1
    assert comparison["status"] == "PASS"


def test_unresolved_label_mapping_is_review_needed_not_pass() -> None:
    review = {"id": "unresolved", "content": "The fit is secure.", "rating": 5}
    fragments = [
        _fragment("unresolved", "fit is secure", SIGNAL_PRODUCT_POSITIVE, source="test", source_kind="local_shadow_probe", dataset="test", gold_reason="No canonical AirPods label key in local fixture.", segment="mixed_review", label_type="label"),
    ]
    projection = _project(review, fragments)
    comparison = compare_baseline_to_signal_shadow(
        dataset="test",
        baseline_issue_keys=[],
        baseline_label_keys=[],
        projection=projection,
        gold_fragments=[
            normalize_review_signal_gold_fragment(fragment, content_by_review_id={"unresolved": review["content"]})
            for fragment in fragments
        ],
    )

    assert projection["unresolved_mapping_count"] == 1
    assert comparison["split_metrics"]["unresolved_mapping_count"] == 1
    assert comparison["status"] == "REVIEW_NEEDED"


def test_phase_2_3_artifacts_keep_routing_leakage_zero_and_mark_mapping_review_needed() -> None:
    specs = build_local_gold_review_specs()
    routing_artifact, fp_fn_artifact = _build_routing_projection_and_comparison_artifacts(specs)

    assert routing_artifact["routing_leakage"]["non_product_to_issue_label_leakage_count"] == 0
    assert fp_fn_artifact["overall"]["split_metrics"]["routing_fn"] == {"issue": 0, "label": 0}
    assert fp_fn_artifact["unresolved_mappings"]["unresolved_mapping_count"] > 0
    assert fp_fn_artifact["status"] == "REVIEW_NEEDED"
    assert fp_fn_artifact["decision"]["routing_layer_ready_for_controlled_gray_review"] is True
    assert fp_fn_artifact["decision"]["full_label_extraction_ready"] is False


def test_shadow_safety_flags_are_all_false() -> None:
    safety = review_signal_shadow_safety_flags()

    assert safety
    assert all(value is False for value in safety.values())
    assert ROUTE_CUSTOMER_ISSUE_CANDIDATE
    assert ROUTE_CUSTOMER_LABEL_CANDIDATE
    assert ROUTE_CONSUMER_PROFILE
