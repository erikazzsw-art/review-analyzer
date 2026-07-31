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
)
from backend_api.app.services.customer_label_v2_frontstage_runbook import (
    build_customer_label_v2_frontstage_rollback_drill_report,
    customer_label_v2_frontstage_gray_run_runbook,
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


def _v1_occurrence(*, comment_id: str) -> dict[str, Any]:
    return {
        "comment_id": comment_id,
        "type": "issue",
        "raw_label": "Zipper Fails",
        "canonical_label_key": "zipper_fails",
        "display_label_en": "Zipper Fails",
        "display_label_zh": "拉链容易故障",
        "aspect_key": "zipper_quality",
        "evidence_span": "zipper broke",
        "evidence_start": -1,
        "evidence_end": -1,
        "confidence": "high",
        "source": "rule",
        "source_detail": "step7_7_v1_fixture",
        "evidence_verified": True,
        "cluster_propagated": False,
        "schema_version": CUSTOMER_LABEL_OCCURRENCE_SCHEMA_VERSION,
        "ruleset_version": CUSTOMER_LABEL_OCCURRENCE_RULESET_VERSION,
        "display_allowed": True,
    }


def _review() -> dict[str, Any]:
    review_id = "step77-review"
    return {
        "id": review_id,
        "session_id": "step77-session",
        "product_id": "TIDEWE-step77",
        "content": "The zipper broke on day one. They do not keep you dry.",
        "rating": 1,
        "category": "outdoor",
        "sub_category": "waders",
        "aspects_json": {
            "customer_label_occurrence_schema_version": CUSTOMER_LABEL_OCCURRENCE_SCHEMA_VERSION,
            "customer_label_occurrence_ruleset_version": CUSTOMER_LABEL_OCCURRENCE_RULESET_VERSION,
            "sub_category": "waders",
            "customer_label_occurrences": [_v1_occurrence(comment_id=review_id)],
        },
    }


def _candidate() -> dict[str, Any]:
    return {
        "label_type": "issue",
        "canonical_label_key": "water_leaks_through",
        "raw_label": "Water Leaks Through",
        "display_label_en": "Water Leaks Through",
        "display_label_zh": "防水性差",
        "aspect_key": "waterproof",
        "polarity": "negative",
        "evidence_candidate": "do not keep you dry",
        "confidence": 0.9,
        "reason": "step7.7 rollback drill fixture",
    }


def test_gray_run_runbook_is_read_only_and_requires_erika_authorization() -> None:
    runbook = customer_label_v2_frontstage_gray_run_runbook()
    steps = {step["step"]: step for step in runbook["gray_run_steps"]}

    assert runbook["production_execution"]["executed"] is False
    assert runbook["production_execution"]["requires_erika_explicit_authorization"] is True
    assert runbook["production_execution"]["feature_flag_enabled_now"] is False
    assert steps["0_percent_baseline"]["expected_read_path"] == READ_PATH_V1_CURRENT
    assert "scoped_session_gray" in steps
    assert "scoped_sub_category_gray" in steps
    assert "scoped_category_observation" in steps
    assert "global_kill_switch" in runbook["rollback_drill_required"]
    assert runbook["safety"]["production_db_write"] is False


def test_rollback_drill_returns_to_v1_for_rollback_kill_switch_and_flag_off() -> None:
    review = _review()
    shadow = run_customer_label_v2_shadow(review, label_candidates=[_candidate()])
    report = build_customer_label_v2_frontstage_rollback_drill_report(
        review,
        shadow_result=shadow,
    )
    cases = {case["case"]: case for case in report["cases"]}

    assert report["status"] == "PASS"
    assert report["case_count"] == 6
    assert report["selected_read_paths"] == {READ_PATH_V1_CURRENT: 5, READ_PATH_V2_SHADOW: 1}
    assert cases["baseline_v2_selected"]["actual_path"] == READ_PATH_V2_SHADOW
    assert cases["baseline_v2_selected"]["actual_keys"] == {"issue": ["water_leaks_through"], "highlight": []}
    assert cases["global_rollback"]["actual_path"] == READ_PATH_V1_CURRENT
    assert cases["global_rollback"]["fallback_reason"] == "rollback_global"
    assert cases["scoped_rollback"]["fallback_reason"] == "rollback_session"
    assert cases["global_kill_switch"]["fallback_reason"] == "kill_switch_global"
    assert cases["scoped_kill_switch"]["fallback_reason"] == "kill_switch_sub_category"
    assert cases["flag_off"]["fallback_reason"] == "flag_off"
    assert cases["flag_off"]["actual_keys"] == cases["flag_off"]["expected_keys"]
    assert "zipper_fails" in cases["flag_off"]["actual_keys"]["issue"]
    assert report["violations"] == []


def test_rollback_drill_observability_and_safety_contract() -> None:
    review = _review()
    shadow = run_customer_label_v2_shadow(review, label_candidates=[_candidate()])
    report = build_customer_label_v2_frontstage_rollback_drill_report(
        review,
        shadow_result=shadow,
    )
    snapshot = report["observability_snapshot"]

    assert snapshot["rollback_counters"]["rollback_selected_count"] == 2
    assert snapshot["kill_switch_counters"]["kill_switch_selected_count"] == 2
    assert snapshot["selected_v2_occurrence_count"] == 1
    assert snapshot["stored_shadow_availability"]["available_count"] == 6
    assert report["production_execution"]["executed"] is False
    assert report["production_execution"]["requires_erika_explicit_authorization"] is True
    assert report["safety"]["production_upload"] is False
    assert report["safety"]["production_write_path"] is False
    assert report["safety"]["llm_called"] is False
