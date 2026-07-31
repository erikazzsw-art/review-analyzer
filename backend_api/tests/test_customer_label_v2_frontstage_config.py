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
    build_customer_label_v2_frontstage_observability_snapshot,
    build_customer_label_v2_frontstage_read_model,
    build_customer_label_v2_frontstage_readiness_dry_run_report,
    customer_label_v2_frontstage_flag_from_env,
    resolve_customer_label_v2_frontstage_config,
)
from backend_api.app.services.customer_label_v2_shadow import run_customer_label_v2_shadow


@pytest.fixture(autouse=True)
def reset_catalog_state() -> None:
    set_customer_label_catalog_state_for_tests(CustomerLabelCatalogState())
    yield
    set_customer_label_catalog_state_for_tests(None)


def _review(*, review_id: str = "step76-review") -> dict[str, Any]:
    return {
        "id": review_id,
        "session_id": "step76-session",
        "product_id": "TIDEWE-step76",
        "content": "They do not keep you dry.",
        "rating": 1,
        "category": "outdoor",
        "sub_category": "waders",
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
        "reason": "step7.6 config fixture",
    }


def _stored_shadow_review() -> dict[str, Any]:
    review = _review()
    return {
        **review,
        "customer_label_v2_shadow_result": run_customer_label_v2_shadow(
            review,
            label_candidates=[_candidate()],
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


def test_production_config_defaults_all_controls_off_and_runtime_shadow_off() -> None:
    resolution = resolve_customer_label_v2_frontstage_config({})
    flag = customer_label_v2_frontstage_flag_from_env({})

    assert resolution.valid is True
    assert resolution.fail_closed is False
    assert flag == resolution.effective_feature_flag
    assert flag.enabled is False
    assert flag.shadow_fixture_gate_passed is False
    assert flag.rollback is False
    assert flag.kill_switch is False
    assert flag.allow_runtime_shadow is False
    assert flag.enabled_maturity_levels == ("L3_sub_category",)
    assert flag.session_ids == ()
    assert flag.categories == ()
    assert flag.sub_categories == ()
    assert flag.category_sub_categories == ()


def test_production_config_parses_scope_fixture_maturity_rollback_and_kill_switches() -> None:
    resolution = resolve_customer_label_v2_frontstage_config(
        {
            "CUSTOMER_LABEL_V2_FRONTSTAGE_ENABLED": "true",
            "CUSTOMER_LABEL_V2_FRONTSTAGE_SESSION_IDS": "101, 102",
            "CUSTOMER_LABEL_V2_FRONTSTAGE_CATEGORIES": "outdoor",
            "CUSTOMER_LABEL_V2_FRONTSTAGE_SUB_CATEGORIES": "outdoor/waders,waders",
            "CUSTOMER_LABEL_V2_FRONTSTAGE_CATEGORY_SUB_CATEGORIES": "outdoor/waders",
            "CUSTOMER_LABEL_V2_FRONTSTAGE_SHADOW_FIXTURE_GATE_PASSED": "yes",
            "CUSTOMER_LABEL_V2_FRONTSTAGE_ENABLED_MATURITY_LEVELS": "L3_sub_category",
            "CUSTOMER_LABEL_V2_FRONTSTAGE_ROLLBACK_SESSION_IDS": "rollback-session",
            "CUSTOMER_LABEL_V2_FRONTSTAGE_KILL_SWITCH_CATEGORIES": "baby",
            "CUSTOMER_LABEL_V2_FRONTSTAGE_KILL_SWITCH_SUB_CATEGORIES": "pet/dog_food",
            "CUSTOMER_LABEL_V2_FRONTSTAGE_ALLOW_RUNTIME_SHADOW": "off",
        }
    )
    flag = resolution.effective_feature_flag

    assert resolution.valid is True
    assert flag.enabled is True
    assert flag.session_ids == ("101", "102")
    assert flag.categories == ("outdoor",)
    assert flag.sub_categories == ("outdoor/waders", "waders")
    assert flag.category_sub_categories == ("outdoor/waders",)
    assert flag.shadow_fixture_gate_passed is True
    assert flag.enabled_maturity_levels == ("L3_sub_category",)
    assert flag.rollback_session_ids == ("rollback-session",)
    assert flag.kill_switch_categories == ("baby",)
    assert flag.kill_switch_sub_categories == ("pet/dog_food",)
    assert flag.allow_runtime_shadow is False


def test_global_kill_switch_overrides_v2_selection_and_observability_counts_it() -> None:
    review = _stored_shadow_review()
    model = build_customer_label_v2_frontstage_read_model(
        review,
        flag=_waders_flag(kill_switch=True),
        shadow_result=review["customer_label_v2_shadow_result"],
    )
    snapshot = build_customer_label_v2_frontstage_observability_snapshot([model])

    assert model["read_path"] == READ_PATH_V1_CURRENT
    assert model["fallback_reason"] == "kill_switch_global"
    assert model["flag_decision"]["kill_switch_active"] is True
    assert snapshot["read_path_selected"] == {READ_PATH_V1_CURRENT: 1}
    assert snapshot["kill_switch_counters"]["kill_switch_selected_count"] == 1
    assert snapshot["kill_switch_counters"]["kill_switch_global_count"] == 1
    assert snapshot["selected_v2_occurrence_count"] == 0


def test_scoped_kill_switch_overrides_matching_category_scope() -> None:
    review = _stored_shadow_review()
    model = build_customer_label_v2_frontstage_read_model(
        review,
        flag=_waders_flag(kill_switch_categories=("outdoor",)),
        shadow_result=review["customer_label_v2_shadow_result"],
    )
    snapshot = build_customer_label_v2_frontstage_observability_snapshot([model])

    assert model["read_path"] == READ_PATH_V1_CURRENT
    assert model["fallback_reason"] == "kill_switch_category"
    assert snapshot["kill_switch_counters"]["kill_switch_scoped_count"] == 1


def test_invalid_config_fails_closed_to_v1_current_and_reports_validation_errors() -> None:
    report = build_customer_label_v2_frontstage_readiness_dry_run_report(
        [_stored_shadow_review()],
        env_config={
            "CUSTOMER_LABEL_V2_FRONTSTAGE_ENABLED": "true",
            "CUSTOMER_LABEL_V2_FRONTSTAGE_SUB_CATEGORIES": "outdoor/waders",
            "CUSTOMER_LABEL_V2_FRONTSTAGE_SHADOW_FIXTURE_GATE_PASSED": "true",
            "CUSTOMER_LABEL_V2_FRONTSTAGE_ENABLED_MATURITY_LEVELS": "L3_sub_category,L9_future",
            "CUSTOMER_LABEL_V2_FRONTSTAGE_CATEGORY_SUB_CATEGORIES": "outdoor",
        },
    )
    preview = report["selected_read_path_preview"][0]
    snapshot = report["observability_snapshot"]

    assert report["config_resolution"]["valid"] is False
    assert report["config_resolution"]["fail_closed"] is True
    assert preview["selected_read_path"] == READ_PATH_V1_CURRENT
    assert preview["fallback_reason"] == "config_invalid"
    assert "blocked_by_config_invalid" in preview["blocked_reasons"]
    assert preview["checks"]["config_valid"] is False
    assert report["observability"]["blocked_by_config_invalid"] == 1
    assert report["observability"]["config_validation_error_count"] == 2
    assert snapshot["config_validation_errors"]["count"] == 2
    assert snapshot["blocked_reason_counters"]["blocked_by_config_invalid"] == 1


def test_observability_snapshot_reports_v2_count_and_stored_shadow_availability() -> None:
    review = _stored_shadow_review()
    selected_v2 = build_customer_label_v2_frontstage_read_model(
        review,
        flag=_waders_flag(),
        shadow_result=review["customer_label_v2_shadow_result"],
    )
    missing_shadow = build_customer_label_v2_frontstage_read_model(
        _review(review_id="step76-missing-shadow"),
        flag=_waders_flag(),
        shadow_result=None,
    )
    snapshot = build_customer_label_v2_frontstage_observability_snapshot([selected_v2, missing_shadow])

    assert selected_v2["read_path"] == READ_PATH_V2_SHADOW
    assert missing_shadow["read_path"] == READ_PATH_V1_CURRENT
    assert snapshot["read_path_selected"] == {READ_PATH_V1_CURRENT: 1, READ_PATH_V2_SHADOW: 1}
    assert snapshot["selected_v2_occurrence_count"] == 1
    assert snapshot["stored_shadow_availability"]["available_count"] == 1
    assert snapshot["stored_shadow_availability"]["missing_count"] == 1
    assert snapshot["blocked_reason_counters"]["blocked_by_no_stored_shadow"] == 1
