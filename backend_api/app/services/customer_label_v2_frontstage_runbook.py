from __future__ import annotations

from collections import Counter
from typing import Any

from backend_api.app.services.customer_label_v2_frontstage import (
    READ_PATH_V1_CURRENT,
    READ_PATH_V2_SHADOW,
    CustomerLabelV2FrontstageFlag,
    build_customer_label_v2_frontstage_observability_snapshot,
    build_customer_label_v2_frontstage_read_model,
    frontstage_keys_from_read_model,
)

CUSTOMER_LABEL_V2_FRONTSTAGE_GRAY_RUN_RUNBOOK_SCHEMA_VERSION = (
    "customer-label-v2-frontstage-gray-run-runbook.1"
)
CUSTOMER_LABEL_V2_FRONTSTAGE_ROLLBACK_DRILL_SCHEMA_VERSION = (
    "customer-label-v2-frontstage-rollback-drill.1"
)


def customer_label_v2_frontstage_gray_run_runbook() -> dict[str, Any]:
    """Return the read-only gray-run plan. This does not execute production controls."""
    return {
        "schema_version": CUSTOMER_LABEL_V2_FRONTSTAGE_GRAY_RUN_RUNBOOK_SCHEMA_VERSION,
        "scope": "5.9.9 Step 7.7 v2 frontstage gray-run runbook",
        "status": "READY_FOR_ERIKA_REVIEW",
        "production_execution": {
            "executed": False,
            "requires_erika_explicit_authorization": True,
            "authorization_phrase": "Erika must explicitly authorize production enablement.",
            "feature_flag_enabled_now": False,
        },
        "gray_run_steps": [
            {
                "step": "0_percent_baseline",
                "target": "all traffic",
                "config": {"enabled": False},
                "expected_read_path": READ_PATH_V1_CURRENT,
                "entry_gate": "current production default",
                "exit_gate": "readiness dry-run PASS, replay P0=0, six focus labels FP/FN=0",
            },
            {
                "step": "read_only_stored_shadow_audit",
                "target": "local/stored shadow payloads only",
                "config": {"enabled": False, "allow_runtime_shadow": False},
                "expected_read_path": READ_PATH_V1_CURRENT,
                "entry_gate": "stored shadow availability understood",
                "exit_gate": "no missing stored shadow surprises for chosen scope",
            },
            {
                "step": "scoped_session_gray",
                "target": "single authorized session_id",
                "config": {
                    "enabled": True,
                    "session_ids": ["<authorized-session-id>"],
                    "shadow_fixture_gate_passed": True,
                    "enabled_maturity_levels": ["L3_sub_category"],
                },
                "expected_read_path": "v2_shadow only for the authorized session and only with stored verified display",
                "entry_gate": "Erika separately authorizes the exact session scope",
                "exit_gate": "no P0, no candidate/audit leakage, rollback drill PASS",
            },
            {
                "step": "scoped_sub_category_gray",
                "target": "outdoor/waders",
                "config": {
                    "enabled": True,
                    "sub_categories": ["outdoor/waders"],
                    "shadow_fixture_gate_passed": True,
                    "enabled_maturity_levels": ["L3_sub_category"],
                },
                "expected_read_path": "v2_shadow only for L3 outdoor/waders with stored verified display",
                "entry_gate": "session gray is clean and Erika authorizes the sub_category scope",
                "exit_gate": "four frontstage consumers match selected display occurrences",
            },
            {
                "step": "scoped_category_observation",
                "target": "category scope as a future envelope",
                "config": {
                    "enabled": True,
                    "categories": ["outdoor"],
                    "shadow_fixture_gate_passed": True,
                    "enabled_maturity_levels": ["L3_sub_category"],
                },
                "expected_read_path": "v2_shadow only where maturity remains L3_sub_category",
                "entry_gate": "Erika separately authorizes category envelope; L1/L2 remain blocked",
                "exit_gate": "maturity blocked candidates stay out of frontstage",
            },
        ],
        "rollback_drill_required": [
            "global_rollback",
            "scoped_rollback",
            "global_kill_switch",
            "scoped_kill_switch",
            "flag_off",
        ],
        "hard_stops": [
            "config_invalid",
            "candidate_or_audit_layer_selected",
            "unknown_label_selected",
            "stored_shadow_missing_for_enabled_scope",
            "replay_p0_above_zero",
            "six_focus_label_fp_or_fn_above_zero",
        ],
        "safety": {
            "production_upload": False,
            "production_write_path": False,
            "production_db_write": False,
            "db_write": False,
            "credit_consumed": False,
            "llm_called": False,
            "frontstage_replaced": False,
            "frontstage_mutated": False,
        },
    }


def _drill_case_payload(
    *,
    name: str,
    review: dict[str, Any],
    flag: CustomerLabelV2FrontstageFlag,
    shadow_result: dict[str, Any] | None,
    expected_path: str,
    expected_keys: dict[str, list[str]] | str,
) -> dict[str, Any]:
    model = build_customer_label_v2_frontstage_read_model(
        review,
        flag=flag,
        shadow_result=shadow_result,
        locale="en",
    )
    expected = model["v1_current"]["keys"] if expected_keys == "v1_current" else expected_keys
    actual_keys = frontstage_keys_from_read_model(model)
    errors: list[str] = []
    if model["read_path"] != expected_path:
        errors.append("read_path_mismatch")
    if actual_keys != expected:
        errors.append("selected_keys_mismatch")
    if expected_path == READ_PATH_V1_CURRENT and model["read_path"] != READ_PATH_V1_CURRENT:
        errors.append("rollback_did_not_fail_closed")
    return {
        "case": name,
        "expected_path": expected_path,
        "actual_path": model["read_path"],
        "fallback_reason": model["fallback_reason"],
        "expected_keys": expected,
        "actual_keys": actual_keys,
        "errors": errors,
        "read_model": model,
    }


def build_customer_label_v2_frontstage_rollback_drill_report(
    review: dict[str, Any],
    *,
    shadow_result: dict[str, Any],
    scope: str = "5.9.9 Step 7.7 v2 frontstage rollback drill",
) -> dict[str, Any]:
    """Verify local rollback/kill/flag-off behavior without mutating production state."""
    session_id = str(review.get("session_id") or "")
    category = str(review.get("category") or "")
    sub_category = str(review.get("sub_category") or "")
    scoped_flag = CustomerLabelV2FrontstageFlag(
        enabled=True,
        sub_categories=(f"{category}/{sub_category}",),
        shadow_fixture_gate_passed=True,
        allow_runtime_shadow=False,
    )
    cases = [
        _drill_case_payload(
            name="baseline_v2_selected",
            review=review,
            flag=scoped_flag,
            shadow_result=shadow_result,
            expected_path=READ_PATH_V2_SHADOW,
            expected_keys={"issue": ["water_leaks_through"], "highlight": []},
        ),
        _drill_case_payload(
            name="global_rollback",
            review=review,
            flag=CustomerLabelV2FrontstageFlag(
                enabled=True,
                sub_categories=(f"{category}/{sub_category}",),
                shadow_fixture_gate_passed=True,
                rollback=True,
                allow_runtime_shadow=False,
            ),
            shadow_result=shadow_result,
            expected_path=READ_PATH_V1_CURRENT,
            expected_keys="v1_current",
        ),
        _drill_case_payload(
            name="scoped_rollback",
            review=review,
            flag=CustomerLabelV2FrontstageFlag(
                enabled=True,
                sub_categories=(f"{category}/{sub_category}",),
                shadow_fixture_gate_passed=True,
                rollback_session_ids=(session_id,),
                allow_runtime_shadow=False,
            ),
            shadow_result=shadow_result,
            expected_path=READ_PATH_V1_CURRENT,
            expected_keys="v1_current",
        ),
        _drill_case_payload(
            name="global_kill_switch",
            review=review,
            flag=CustomerLabelV2FrontstageFlag(
                enabled=True,
                sub_categories=(f"{category}/{sub_category}",),
                shadow_fixture_gate_passed=True,
                kill_switch=True,
                allow_runtime_shadow=False,
            ),
            shadow_result=shadow_result,
            expected_path=READ_PATH_V1_CURRENT,
            expected_keys="v1_current",
        ),
        _drill_case_payload(
            name="scoped_kill_switch",
            review=review,
            flag=CustomerLabelV2FrontstageFlag(
                enabled=True,
                sub_categories=(f"{category}/{sub_category}",),
                shadow_fixture_gate_passed=True,
                kill_switch_sub_categories=(f"{category}/{sub_category}",),
                allow_runtime_shadow=False,
            ),
            shadow_result=shadow_result,
            expected_path=READ_PATH_V1_CURRENT,
            expected_keys="v1_current",
        ),
        _drill_case_payload(
            name="flag_off",
            review=review,
            flag=CustomerLabelV2FrontstageFlag(allow_runtime_shadow=False),
            shadow_result=shadow_result,
            expected_path=READ_PATH_V1_CURRENT,
            expected_keys="v1_current",
        ),
    ]
    read_models = [case["read_model"] for case in cases]
    violations = [
        {
            "case": case["case"],
            "errors": case["errors"],
            "expected_path": case["expected_path"],
            "actual_path": case["actual_path"],
            "fallback_reason": case["fallback_reason"],
        }
        for case in cases
        if case["errors"]
    ]
    selected_read_paths = Counter(str(case["actual_path"]) for case in cases)
    return {
        "schema_version": CUSTOMER_LABEL_V2_FRONTSTAGE_ROLLBACK_DRILL_SCHEMA_VERSION,
        "scope": scope,
        "status": "PASS" if not violations else "REVIEW_NEEDED",
        "case_count": len(cases),
        "selected_read_paths": dict(sorted(selected_read_paths.items())),
        "cases": cases,
        "violations": violations,
        "observability_snapshot": build_customer_label_v2_frontstage_observability_snapshot(
            read_models,
            scope=scope,
        ),
        "production_execution": {
            "executed": False,
            "requires_erika_explicit_authorization": True,
            "feature_flag_enabled_now": False,
        },
        "safety": {
            "production_upload": False,
            "production_write_path": False,
            "production_db_write": False,
            "db_write": False,
            "credit_consumed": False,
            "llm_called": False,
            "runtime_shadow_called": False,
            "frontstage_replaced": False,
            "frontstage_mutated": False,
        },
    }
