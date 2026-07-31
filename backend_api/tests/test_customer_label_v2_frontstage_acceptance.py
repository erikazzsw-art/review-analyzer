from __future__ import annotations

from typing import Any

from backend_api.app.services.customer_label_v2_frontstage_acceptance import (
    build_customer_label_v2_frontstage_go_no_go_acceptance_pack,
)
from backend_api.app.services.customer_label_v2_shadow import FOCUS_WADERS_LABELS


def _step6_artifact() -> dict[str, Any]:
    return {
        "schema_version": "customer-label-v2-frontstage-read-path.1",
        "status": "PASS",
        "violations": [],
        "contract": {
            "feature_flag": {
                "default_enabled": False,
                "enabled_maturity_levels_default": ["L3_sub_category"],
            },
            "excluded_from_frontstage": [
                "label_candidates",
                "audit_occurrences",
                "candidate_pool_items",
                "maturity_blocked_candidates",
                "unknown_label_candidates",
            ],
        },
    }


def _step7_artifact() -> dict[str, Any]:
    return {
        "schema_version": "customer-label-v2-frontstage-consumer-integration.1",
        "status": "PASS",
        "violations": [],
    }


def _step7_5_artifact() -> dict[str, Any]:
    return {
        "schema_version": "customer-label-v2-frontstage-readiness-dry-run-pack.1",
        "status": "PASS",
        "case_count": 10,
        "case_expectation_violations": [],
        "observability": {
            "blocked_by_maturity": 3,
            "stored_shadow_available_count": 9,
            "stored_shadow_missing_count": 1,
        },
    }


def _step7_6_artifact() -> dict[str, Any]:
    return {
        "schema_version": "customer-label-v2-frontstage-config-kill-switch-observability.1",
        "status": "PASS",
        "case_expectation_violations": [],
        "observability": {
            "kill_switch_selected_count": 2,
        },
        "observability_snapshot": {
            "kill_switch_counters": {
                "kill_switch_selected_count": 2,
                "kill_switch_global_count": 1,
                "kill_switch_scoped_count": 1,
            },
            "stored_shadow_availability": {
                "available_count": 8,
                "missing_count": 0,
            },
        },
        "safety": {
            "production_feature_flag_enabled": False,
        },
    }


def _step7_7_artifact() -> dict[str, Any]:
    return {
        "schema_version": "customer-label-v2-frontstage-gray-run-rollback-drill.1",
        "status": "PASS",
        "rollback_drill": {
            "status": "PASS",
            "case_count": 6,
            "selected_read_paths": {"v1_current": 5, "v2_shadow": 1},
            "violations": [],
        },
    }


def _focus_metrics_zero() -> dict[str, dict[str, int]]:
    return {
        f"{label_type}:{canonical}": {"tp": 1, "fp": 0, "fn": 0}
        for label_type, canonical in FOCUS_WADERS_LABELS
    }


def _build_pack(
    *,
    p0_count: int = 0,
    focus_label_metrics: dict[str, dict[str, int]] | None = None,
) -> dict[str, Any]:
    return build_customer_label_v2_frontstage_go_no_go_acceptance_pack(
        step6_read_path_artifact=_step6_artifact(),
        step7_consumer_integration_artifact=_step7_artifact(),
        step7_5_readiness_artifact=_step7_5_artifact(),
        step7_6_config_artifact=_step7_6_artifact(),
        step7_7_runbook_artifact=_step7_7_artifact(),
        p0_count=p0_count,
        focus_label_metrics=focus_label_metrics or _focus_metrics_zero(),
    )


def test_go_no_go_acceptance_pack_passes_when_all_gates_are_green() -> None:
    pack = _build_pack()

    assert pack["status"] == "PASS"
    assert pack["go_no_go"] == "GO_READY_FOR_ERIKA_AUTHORIZED_GRAY_RUN_ONLY"
    assert pack["no_go_items"] == []
    assert pack["production_authorization"]["feature_flag_enabled_now"] is False
    assert pack["production_authorization"]["requires_erika_explicit_authorization"] is True
    assert pack["safety"]["production_db_write"] is False


def test_go_no_go_acceptance_pack_contains_required_checklist_keys() -> None:
    pack = _build_pack()
    keys = {item["key"] for item in pack["acceptance_criteria"]}

    assert keys == {
        "feature_flag_default_off",
        "readiness_dry_run_pass",
        "kill_switch_pass",
        "rollback_drill_pass",
        "stored_shadow_availability_clear",
        "l3_only_gate_clear",
        "unknown_candidate_audit_not_frontstage",
        "replay_p0_zero",
        "six_focus_labels_fp_fn_zero",
    }


def test_go_no_go_acceptance_pack_blocks_p0_or_focus_label_regression() -> None:
    focus = _focus_metrics_zero()
    focus["issue:water_leaks_through"] = {"tp": 0, "fp": 1, "fn": 1}
    pack = _build_pack(p0_count=1, focus_label_metrics=focus)
    no_go_keys = {item["key"] for item in pack["no_go_items"]}

    assert pack["status"] == "NO_GO"
    assert pack["go_no_go"] == "NO_GO"
    assert {"replay_p0_zero", "six_focus_labels_fp_fn_zero"} <= no_go_keys
