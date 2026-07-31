from __future__ import annotations

from typing import Any

from backend_api.app.services.customer_label_v2_maturity import MATURITY_L3_SUB_CATEGORY
from backend_api.app.services.customer_label_v2_shadow import FOCUS_WADERS_LABELS

CUSTOMER_LABEL_V2_FRONTSTAGE_GO_NO_GO_SCHEMA_VERSION = (
    "customer-label-v2-frontstage-go-no-go-acceptance.1"
)


def _nested(payload: dict[str, Any], path: tuple[str, ...], default: Any = None) -> Any:
    current: Any = payload
    for key in path:
        if not isinstance(current, dict):
            return default
        current = current.get(key)
    return current if current is not None else default


def _pass(value: bool) -> str:
    return "PASS" if value else "NO_GO"


def _criteria(key: str, passed: bool, evidence: dict[str, Any]) -> dict[str, Any]:
    return {
        "key": key,
        "status": _pass(passed),
        "evidence": evidence,
    }


def _focus_label_key(label_type: str, canonical: str) -> str:
    return f"{label_type}:{canonical}"


def _six_focus_label_metrics_zero(focus_label_metrics: dict[str, dict[str, int]]) -> tuple[bool, dict[str, Any]]:
    evidence: dict[str, Any] = {}
    passed = True
    for label_type, canonical in sorted(FOCUS_WADERS_LABELS):
        key = _focus_label_key(label_type, canonical)
        metrics = focus_label_metrics.get(key, {})
        tp = int(metrics.get("tp") or 0)
        fp = int(metrics.get("fp") or 0)
        fn = int(metrics.get("fn") or 0)
        evidence[key] = {"tp": tp, "fp": fp, "fn": fn}
        if fp or fn:
            passed = False
    return passed, evidence


def build_customer_label_v2_frontstage_go_no_go_acceptance_pack(
    *,
    step6_read_path_artifact: dict[str, Any],
    step7_consumer_integration_artifact: dict[str, Any],
    step7_5_readiness_artifact: dict[str, Any],
    step7_6_config_artifact: dict[str, Any],
    step7_7_runbook_artifact: dict[str, Any],
    p0_count: int,
    focus_label_metrics: dict[str, dict[str, int]],
    scope: str = "5.9.9 Step 7.8 v2 frontstage go/no-go acceptance pack",
) -> dict[str, Any]:
    """Build a local go/no-go pack; it does not authorize production enablement."""
    feature_flag_default_off = (
        _nested(step6_read_path_artifact, ("contract", "feature_flag", "default_enabled")) is False
        and _nested(step7_6_config_artifact, ("safety", "production_feature_flag_enabled")) is False
    )
    readiness_pass = step7_5_readiness_artifact.get("status") == "PASS"
    kill_switch_pass = (
        step7_6_config_artifact.get("status") == "PASS"
        and int(_nested(step7_6_config_artifact, ("observability", "kill_switch_selected_count"), 0)) >= 2
        and not step7_6_config_artifact.get("case_expectation_violations")
    )
    rollback_drill_pass = (
        step7_7_runbook_artifact.get("status") == "PASS"
        and _nested(step7_7_runbook_artifact, ("rollback_drill", "status")) == "PASS"
        and not _nested(step7_7_runbook_artifact, ("rollback_drill", "violations"), [])
    )
    stored_shadow_availability_clear = (
        "stored_shadow_available_count" in (step7_5_readiness_artifact.get("observability") or {})
        and "stored_shadow_missing_count" in (step7_5_readiness_artifact.get("observability") or {})
        and "stored_shadow_availability" in (step7_6_config_artifact.get("observability_snapshot") or {})
    )
    l3_only_gate_clear = (
        _nested(
            step6_read_path_artifact,
            ("contract", "feature_flag", "enabled_maturity_levels_default"),
            [],
        )
        == [MATURITY_L3_SUB_CATEGORY]
        and int(_nested(step7_5_readiness_artifact, ("observability", "blocked_by_maturity"), 0)) >= 3
    )
    unknown_candidate_audit_excluded = (
        step6_read_path_artifact.get("status") == "PASS"
        and step7_consumer_integration_artifact.get("status") == "PASS"
        and not step6_read_path_artifact.get("violations")
        and not step7_consumer_integration_artifact.get("violations")
    )
    replay_p0_zero = int(p0_count) == 0
    six_focus_zero, focus_evidence = _six_focus_label_metrics_zero(focus_label_metrics)

    acceptance_criteria = [
        _criteria(
            "feature_flag_default_off",
            feature_flag_default_off,
            {
                "step6_default_enabled": _nested(
                    step6_read_path_artifact,
                    ("contract", "feature_flag", "default_enabled"),
                ),
                "production_feature_flag_enabled": _nested(
                    step7_6_config_artifact,
                    ("safety", "production_feature_flag_enabled"),
                ),
            },
        ),
        _criteria(
            "readiness_dry_run_pass",
            readiness_pass,
            {
                "status": step7_5_readiness_artifact.get("status"),
                "case_count": step7_5_readiness_artifact.get("case_count"),
                "violations": step7_5_readiness_artifact.get("case_expectation_violations"),
            },
        ),
        _criteria(
            "kill_switch_pass",
            kill_switch_pass,
            {
                "status": step7_6_config_artifact.get("status"),
                "kill_switch_counters": _nested(
                    step7_6_config_artifact,
                    ("observability_snapshot", "kill_switch_counters"),
                    {},
                ),
                "case_expectation_violations": step7_6_config_artifact.get("case_expectation_violations"),
            },
        ),
        _criteria(
            "rollback_drill_pass",
            rollback_drill_pass,
            {
                "status": _nested(step7_7_runbook_artifact, ("rollback_drill", "status")),
                "selected_read_paths": _nested(step7_7_runbook_artifact, ("rollback_drill", "selected_read_paths")),
                "violations": _nested(step7_7_runbook_artifact, ("rollback_drill", "violations"), []),
            },
        ),
        _criteria(
            "stored_shadow_availability_clear",
            stored_shadow_availability_clear,
            {
                "step7_5_observability": step7_5_readiness_artifact.get("observability"),
                "step7_6_stored_shadow_availability": _nested(
                    step7_6_config_artifact,
                    ("observability_snapshot", "stored_shadow_availability"),
                    {},
                ),
            },
        ),
        _criteria(
            "l3_only_gate_clear",
            l3_only_gate_clear,
            {
                "enabled_maturity_levels_default": _nested(
                    step6_read_path_artifact,
                    ("contract", "feature_flag", "enabled_maturity_levels_default"),
                    [],
                ),
                "blocked_by_maturity": _nested(step7_5_readiness_artifact, ("observability", "blocked_by_maturity")),
            },
        ),
        _criteria(
            "unknown_candidate_audit_not_frontstage",
            unknown_candidate_audit_excluded,
            {
                "step6_status": step6_read_path_artifact.get("status"),
                "step6_violations": step6_read_path_artifact.get("violations"),
                "step7_status": step7_consumer_integration_artifact.get("status"),
                "step7_violations": step7_consumer_integration_artifact.get("violations"),
                "excluded_layers": _nested(step6_read_path_artifact, ("contract", "excluded_from_frontstage"), []),
            },
        ),
        _criteria(
            "replay_p0_zero",
            replay_p0_zero,
            {"p0_count": int(p0_count)},
        ),
        _criteria(
            "six_focus_labels_fp_fn_zero",
            six_focus_zero,
            focus_evidence,
        ),
    ]
    no_go_items = [item for item in acceptance_criteria if item["status"] != "PASS"]
    return {
        "schema_version": CUSTOMER_LABEL_V2_FRONTSTAGE_GO_NO_GO_SCHEMA_VERSION,
        "scope": scope,
        "status": "PASS" if not no_go_items else "NO_GO",
        "go_no_go": "GO_READY_FOR_ERIKA_AUTHORIZED_GRAY_RUN_ONLY" if not no_go_items else "NO_GO",
        "acceptance_criteria": acceptance_criteria,
        "no_go_items": no_go_items,
        "source_steps": {
            "step6": step6_read_path_artifact.get("schema_version"),
            "step7": step7_consumer_integration_artifact.get("schema_version"),
            "step7_5": step7_5_readiness_artifact.get("schema_version"),
            "step7_6": step7_6_config_artifact.get("schema_version"),
            "step7_7": step7_7_runbook_artifact.get("schema_version"),
        },
        "production_authorization": {
            "feature_flag_enabled_now": False,
            "production_gray_run_executed": False,
            "requires_erika_explicit_authorization": True,
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
