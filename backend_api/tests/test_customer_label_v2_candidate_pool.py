from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from backend_api.app.services.customer_label_catalog import (
    CustomerLabelCatalogState,
    set_customer_label_catalog_state_for_tests,
)
from backend_api.app.services.customer_label_v2_candidate_pool import (
    CANDIDATE_POOL_REQUIRED_FIELDS,
    aggregate_candidate_pool_items,
    build_candidate_pool_artifact,
    build_reviewed_candidate_pool_artifact,
    candidate_pool_required_fields_present,
    collect_candidate_pool_items,
    validate_candidate_pool_review_action,
    write_candidate_pool_csv,
    write_candidate_pool_json_artifact,
    write_reviewed_candidate_pool_csv,
    write_reviewed_candidate_pool_json_artifact,
)
from backend_api.app.services.customer_label_v2_shadow import (
    display_keys_from_shadow,
    run_customer_label_v2_shadow,
)


@pytest.fixture(autouse=True)
def reset_catalog_state() -> None:
    set_customer_label_catalog_state_for_tests(CustomerLabelCatalogState())
    yield
    set_customer_label_catalog_state_for_tests(None)


def _review(
    content: str,
    *,
    review_id: str,
    session_id: int = 120,
    product_id: str = "TIDEWE-WD001",
    rating: int = 3,
) -> dict[str, Any]:
    return {
        "id": review_id,
        "session_id": session_id,
        "product_id": product_id,
        "content": content,
        "rating": rating,
        "category": "outdoor",
        "sub_category": "waders",
    }


def _candidate(
    *,
    label_type: str = "issue",
    canonical: str,
    evidence: str,
    aspect_key: str,
    raw_label: str | None = None,
    confidence: float = 0.9,
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
        "reason": "candidate pool fixture",
    }


def _pool_item(
    candidate_id: str,
    *,
    canonical: str = "candidate:boot_seam_leak",
    raw_label: str = "Boot seam leak",
    downgrade_reasons: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "candidate_id": candidate_id,
        "review_id": f"review-{candidate_id}",
        "session_id": 120,
        "product_id": "TIDEWE-WD001",
        "category": "outdoor",
        "sub_category": "waders",
        "label_type": "issue",
        "canonical_label_key": canonical,
        "raw_label": raw_label,
        "evidence_candidate": "boot seam leaked",
        "confidence": 0.86,
        "downgrade_reasons": downgrade_reasons or ["unknown_label"],
        "top_impact_score": 0.86,
        "review_status": "pending",
    }


def _unknown_result(review_id: str, *, confidence: float = 0.9) -> dict[str, Any]:
    return run_customer_label_v2_shadow(
        _review("The boot seam leaked on the first trip.", review_id=review_id, rating=1),
        label_candidates=[
            _candidate(
                canonical="candidate:boot_seam_leak",
                raw_label="Boot seam leak",
                evidence="boot seam leaked",
                aspect_key="seam_integrity",
                confidence=confidence,
            )
        ],
    )


def _maturity_blocked_result(review_id: str, *, confidence: float = 0.9) -> dict[str, Any]:
    return run_customer_label_v2_shadow(
        _review("They do not keep you dry.", review_id=review_id, rating=1),
        maturity_level="L0_unknown",
        label_candidates=[
            _candidate(
                canonical="water_leaks_through",
                raw_label="Water leaks through",
                evidence="do not keep you dry",
                aspect_key="waterproof",
                confidence=confidence,
            )
        ],
    )


def test_candidate_pool_unknown_label_aggregation_dedupes_by_contract_key() -> None:
    results = [_unknown_result("unknown-r1", confidence=0.78), _unknown_result("unknown-r2", confidence=0.91)]

    raw_items = collect_candidate_pool_items(results)
    aggregated = aggregate_candidate_pool_items(raw_items)

    assert len(raw_items) == 2
    assert len(aggregated) == 1
    item = aggregated[0]
    assert item["canonical_label_key"] == "candidate:boot_seam_leak"
    assert item["raw_label"] == "Boot seam leak"
    assert item["sub_category"] == "waders"
    assert item["downgrade_reasons"] == ["unknown_label"]
    assert item["review_count"] == 2
    assert item["candidate_count"] == 2
    assert item["confidence"] == 0.91


def test_candidate_pool_maturity_blocked_aggregation_dedupes() -> None:
    results = [
        _maturity_blocked_result("maturity-r1", confidence=0.8),
        _maturity_blocked_result("maturity-r2", confidence=0.85),
    ]

    aggregated = aggregate_candidate_pool_items(collect_candidate_pool_items(results))

    assert len(aggregated) == 1
    item = aggregated[0]
    assert item["canonical_label_key"] == "water_leaks_through"
    assert item["downgrade_reasons"] == ["maturity_blocked"]
    assert item["review_count"] == 2
    assert item["top_impact_score"] > item["confidence"]


def test_candidate_pool_mixed_downgrade_reason_priority_controls_sort_order() -> None:
    unknown_low_confidence = _unknown_result("unknown-priority", confidence=0.4)
    maturity_high_confidence = _maturity_blocked_result("maturity-priority", confidence=0.95)

    aggregated = aggregate_candidate_pool_items(
        collect_candidate_pool_items([maturity_high_confidence, unknown_low_confidence])
    )

    assert [item["downgrade_reason_priority"] for item in aggregated] == [100, 90]
    assert aggregated[0]["canonical_label_key"] == "candidate:boot_seam_leak"
    assert aggregated[0]["downgrade_reasons"] == ["confidence_low", "unknown_label"]


def test_candidate_pool_item_required_fields_exist_in_shadow_and_artifact() -> None:
    result = _unknown_result("required-fields")
    shadow_item = result["candidate_pool_items"][0]
    assert candidate_pool_required_fields_present(shadow_item)

    artifact = build_candidate_pool_artifact([result])
    aggregate_item = artifact["candidate_pool_items"][0]
    assert set(CANDIDATE_POOL_REQUIRED_FIELDS) <= set(aggregate_item)
    assert candidate_pool_required_fields_present(aggregate_item)


def test_candidate_pool_review_action_validation_is_pure_schema_check() -> None:
    assert validate_candidate_pool_review_action({"candidate_id": "pool:1", "action": "accept"})["valid"] is True
    assert validate_candidate_pool_review_action({"candidate_id": "pool:1", "action": "reject"})["valid"] is True
    assert validate_candidate_pool_review_action({"candidate_id": "pool:1", "action": "ignore"})["valid"] is True

    invalid_action = validate_candidate_pool_review_action({"candidate_id": "pool:1", "action": "merge"})
    assert invalid_action["valid"] is False
    assert "action_invalid" in invalid_action["errors"]

    missing_label = validate_candidate_pool_review_action({"candidate_id": "pool:1", "action": "correct_label"})
    assert missing_label["valid"] is False
    assert {"label_type_required", "canonical_label_key_required"} <= set(missing_label["errors"])

    corrected_label = validate_candidate_pool_review_action(
        {
            "candidate_id": "pool:1",
            "action": "correct_label",
            "label_type": "issue",
            "canonical_label_key": "water_leaks_through",
        }
    )
    assert corrected_label["valid"] is True

    corrected_evidence = validate_candidate_pool_review_action(
        {"candidate_id": "pool:1", "action": "correct_evidence", "evidence_candidate": "boot seam leaked"}
    )
    assert corrected_evidence["valid"] is True

    needs_new_label = validate_candidate_pool_review_action({"candidate_id": "pool:1", "action": "needs_new_label"})
    assert needs_new_label["valid"] is False
    assert needs_new_label["errors"] == ["raw_label_required"]


def test_audit_only_occurrence_does_not_enter_candidate_pool_unless_unknown_or_maturity_gate() -> None:
    audit_only = run_customer_label_v2_shadow(
        _review("They do not keep you dry.", review_id="audit-only", rating=1),
        label_candidates=[
            {
                **_candidate(
                    canonical="water_leaks_through",
                    evidence="do not keep you dry",
                    aspect_key="waterproof",
                ),
                "cluster_propagated": True,
            }
        ],
    )
    assert audit_only["display_occurrences"] == []
    assert audit_only["candidate_pool_items"] == []
    assert collect_candidate_pool_items([audit_only]) == []

    unknown_audit = run_customer_label_v2_shadow(
        _review("The boot seam leaked on the first trip.", review_id="audit-unknown", rating=1),
        label_candidates=[
            {
                **_candidate(
                    canonical="candidate:boot_seam_leak",
                    raw_label="Boot seam leak",
                    evidence="boot seam leaked",
                    aspect_key="seam_integrity",
                ),
                "cluster_propagated": True,
            }
        ],
    )
    assert unknown_audit["display_occurrences"] == []
    assert len(unknown_audit["candidate_pool_items"]) == 1
    assert "unknown_label" in unknown_audit["candidate_pool_items"][0]["downgrade_reasons"]


def test_display_occurrence_does_not_enter_candidate_pool() -> None:
    result = run_customer_label_v2_shadow(
        _review("They do not keep you dry.", review_id="display-only", rating=1),
        label_candidates=[
            _candidate(
                canonical="water_leaks_through",
                evidence="do not keep you dry",
                aspect_key="waterproof",
            )
        ],
    )

    assert display_keys_from_shadow(result) == {"issue": ["water_leaks_through"], "highlight": []}
    assert result["candidate_pool_items"] == []
    assert collect_candidate_pool_items([result]) == []


def test_candidate_pool_json_and_csv_exports_are_local_artifacts(tmp_path: Path) -> None:
    artifact = build_candidate_pool_artifact([_unknown_result("artifact-r1")], source_artifacts=["fixture.json"])
    json_path = write_candidate_pool_json_artifact(tmp_path / "candidate-pool.json", artifact)
    csv_path = write_candidate_pool_csv(tmp_path / "candidate-pool.csv", artifact["candidate_pool_items"])

    loaded = json.loads(json_path.read_text(encoding="utf-8"))
    assert loaded["schema_version"] == artifact["schema_version"]
    assert loaded["item_count"] == 1
    assert loaded["safety"]["production_db_write"] is False
    assert "candidate_id,review_id,session_id,product_id" in csv_path.read_text(encoding="utf-8")


def test_candidate_pool_review_apply_accept_reject_ignore_status_transitions() -> None:
    items = [
        _pool_item("pool:accept", raw_label="Accept me"),
        _pool_item("pool:reject", raw_label="Reject me"),
        _pool_item("pool:ignore", raw_label="Ignore me"),
    ]

    artifact = build_reviewed_candidate_pool_artifact(
        {"candidate_pool_items": items},
        [
            {"candidate_id": "pool:accept", "action": "accept", "reviewer": "erika-fixture"},
            {"candidate_id": "pool:reject", "action": "reject"},
            {"candidate_id": "pool:ignore", "action": "ignore"},
        ],
    )

    by_id = {item["candidate_id"]: item for item in artifact["reviewed_candidate_pool_items"]}
    assert by_id["pool:accept"]["review_status"] == "accepted"
    assert by_id["pool:reject"]["review_status"] == "rejected"
    assert by_id["pool:ignore"]["review_status"] == "ignored"
    assert all(item["source_candidate_item"]["review_status"] == "pending" for item in by_id.values())
    assert artifact["review_action_summary"]["status_counts"] == {
        "accepted": 1,
        "ignored": 1,
        "rejected": 1,
    }


def test_candidate_pool_review_correct_label_required_fields_and_output() -> None:
    source = _pool_item("pool:correct-label")
    invalid = build_reviewed_candidate_pool_artifact(
        {"candidate_pool_items": [source]},
        [{"candidate_id": "pool:correct-label", "action": "correct_label"}],
    )
    invalid_item = invalid["reviewed_candidate_pool_items"][0]
    assert invalid_item["review_status"] == "pending"
    assert invalid_item["action_applied"] is False
    assert {"label_type_required", "canonical_label_key_required"} <= set(invalid_item["validation_errors"])

    valid = build_reviewed_candidate_pool_artifact(
        {"candidate_pool_items": [source]},
        [
            {
                "candidate_id": "pool:correct-label",
                "action": "correct_label",
                "label_type": "highlight",
                "canonical_label_key": "keeps_water_out",
                "raw_label": "Keeps water out",
            }
        ],
    )
    reviewed = valid["reviewed_candidate_pool_items"][0]
    assert reviewed["review_status"] == "corrected_label"
    assert reviewed["review_output"]["label_type"] == "highlight"
    assert reviewed["review_output"]["canonical_label_key"] == "keeps_water_out"
    assert reviewed["review_output"]["raw_label"] == "Keeps water out"
    assert reviewed["source_candidate_item"]["canonical_label_key"] == "candidate:boot_seam_leak"


def test_candidate_pool_review_correct_evidence_required_fields_and_output() -> None:
    source = _pool_item("pool:correct-evidence")
    invalid = build_reviewed_candidate_pool_artifact(
        {"candidate_pool_items": [source]},
        [{"candidate_id": "pool:correct-evidence", "action": "correct_evidence"}],
    )
    assert invalid["reviewed_candidate_pool_items"][0]["review_status"] == "pending"
    assert invalid["reviewed_candidate_pool_items"][0]["validation_errors"] == ["evidence_candidate_required"]

    valid = build_reviewed_candidate_pool_artifact(
        {"candidate_pool_items": [source]},
        [
            {
                "candidate_id": "pool:correct-evidence",
                "action": "correct_evidence",
                "evidence_candidate": "leaked on the first trip",
            }
        ],
    )
    reviewed = valid["reviewed_candidate_pool_items"][0]
    assert reviewed["review_status"] == "corrected_evidence"
    assert reviewed["review_output"]["canonical_label_key"] == source["canonical_label_key"]
    assert reviewed["review_output"]["evidence_candidate"] == "leaked on the first trip"
    assert reviewed["source_candidate_item"]["evidence_candidate"] == "boot seam leaked"


def test_candidate_pool_review_needs_new_label_required_fields_and_output() -> None:
    source = _pool_item("pool:new-label")
    invalid = build_reviewed_candidate_pool_artifact(
        {"candidate_pool_items": [source]},
        [{"candidate_id": "pool:new-label", "action": "needs_new_label"}],
    )
    assert invalid["reviewed_candidate_pool_items"][0]["review_status"] == "pending"
    assert invalid["reviewed_candidate_pool_items"][0]["validation_errors"] == ["raw_label_required"]

    valid = build_reviewed_candidate_pool_artifact(
        {"candidate_pool_items": [source]},
        [
            {
                "candidate_id": "pool:new-label",
                "action": "needs_new_label",
                "raw_label": "Boot seam leak",
                "note": "Promote to catalog backlog only.",
            }
        ],
    )
    reviewed = valid["reviewed_candidate_pool_items"][0]
    assert reviewed["review_status"] == "needs_new_label"
    assert reviewed["review_output"]["raw_label"] == "Boot seam leak"
    assert reviewed["review_output"]["evidence_candidate"] == source["evidence_candidate"]


def test_candidate_pool_review_invalid_action_is_audit_error_only() -> None:
    source = _pool_item("pool:invalid")
    artifact = build_reviewed_candidate_pool_artifact(
        {"candidate_pool_items": [source]},
        [{"candidate_id": "pool:invalid", "action": "merge"}],
    )
    reviewed = artifact["reviewed_candidate_pool_items"][0]

    assert artifact["status"] == "REVIEW_NEEDED"
    assert artifact["review_action_summary"]["applied_action_count"] == 0
    assert artifact["action_audit"][0]["errors"] == ["action_invalid"]
    assert reviewed["review_status"] == "pending"
    assert reviewed["action_applied"] is False
    assert reviewed["source_candidate_item"] == source


def test_candidate_pool_review_unknown_label_keeps_source_candidate_trace() -> None:
    pool = build_candidate_pool_artifact([_unknown_result("trace-r1"), _unknown_result("trace-r2")])
    source_item = pool["candidate_pool_items"][0]
    artifact = build_reviewed_candidate_pool_artifact(
        pool,
        [
            {
                "candidate_id": source_item["candidate_id"],
                "action": "needs_new_label",
                "raw_label": source_item["raw_label"],
            }
        ],
    )
    reviewed = artifact["reviewed_candidate_pool_items"][0]
    source = reviewed["source_candidate_item"]

    assert reviewed["review_status"] == "needs_new_label"
    assert source["canonical_label_key"] == "candidate:boot_seam_leak"
    assert source["downgrade_reasons"] == ["unknown_label"]
    assert source["review_ids"] == ["trace-r1", "trace-r2"]
    assert all(str(candidate_id).startswith("shadow:trace-r") for candidate_id in source["source_candidate_ids"])


def test_candidate_pool_review_maturity_blocked_keeps_downgrade_reasons() -> None:
    pool = build_candidate_pool_artifact([_maturity_blocked_result("maturity-review")])
    source_item = pool["candidate_pool_items"][0]
    artifact = build_reviewed_candidate_pool_artifact(
        pool,
        [{"candidate_id": source_item["candidate_id"], "action": "accept"}],
    )
    reviewed = artifact["reviewed_candidate_pool_items"][0]

    assert reviewed["review_status"] == "accepted"
    assert reviewed["source_candidate_item"]["canonical_label_key"] == "water_leaks_through"
    assert reviewed["source_candidate_item"]["downgrade_reasons"] == ["maturity_blocked"]
    assert reviewed["source_candidate_item"]["review_status"] == "pending"


def test_candidate_pool_review_artifact_and_exports_keep_safety_flags(tmp_path: Path) -> None:
    pool = build_candidate_pool_artifact([_unknown_result("safe-review")], source_artifacts=["candidate-pool.json"])
    source_item = pool["candidate_pool_items"][0]
    artifact = build_reviewed_candidate_pool_artifact(
        pool,
        [{"candidate_id": source_item["candidate_id"], "action": "ignore"}],
        source_artifacts=["waders-shadow-summary.json"],
    )
    json_path = write_reviewed_candidate_pool_json_artifact(tmp_path / "candidate-pool-reviewed.json", artifact)
    csv_path = write_reviewed_candidate_pool_csv(tmp_path / "candidate-pool-reviewed.csv", artifact)

    loaded = json.loads(json_path.read_text(encoding="utf-8"))
    assert loaded["schema_version"] == "customer-label-v2-candidate-pool-reviewed-mvp.1"
    assert loaded["safety"]["production_db_write"] is False
    assert loaded["safety"]["db_write"] is False
    assert loaded["safety"]["frontstage_mutated"] is False
    assert loaded["safety"]["llm_called"] is False
    assert "candidate_id,review_id,session_id,product_id" in csv_path.read_text(encoding="utf-8")
    assert "source_review_status,action,action_applied" in csv_path.read_text(encoding="utf-8")
