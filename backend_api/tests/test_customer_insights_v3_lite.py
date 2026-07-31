from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from backend_api.app.services.customer_insights_v3_lite import (
    CATALOG_BACKLOG_REQUIRED_FIELDS,
    CUSTOMER_INSIGHT_REQUIRED_FIELDS,
    build_catalog_backlog_draft,
    project_customer_insights_artifact,
    project_customer_insights_from_shadow_result,
    write_catalog_backlog_csv,
)
from backend_api.app.services.customer_label_catalog import (
    CustomerLabelCatalogState,
    set_customer_label_catalog_state_for_tests,
)
from backend_api.app.services.customer_label_v2_shadow import run_customer_label_v2_shadow


@pytest.fixture(autouse=True)
def reset_catalog_state() -> None:
    set_customer_label_catalog_state_for_tests(CustomerLabelCatalogState())
    yield
    set_customer_label_catalog_state_for_tests(None)


def _review(content: str = "They do not keep you dry.") -> dict[str, Any]:
    return {
        "id": "v3-lite-review",
        "session_id": "v3-lite-session",
        "product_id": "TIDEWE-v3-lite",
        "content": content,
        "rating": 1,
        "category": "outdoor",
        "sub_category": "waders",
    }


def _candidate(
    *,
    canonical: str = "water_leaks_through",
    evidence: str = "do not keep you dry",
    raw_label: str = "Water Leaks Through",
    confidence: float = 0.9,
) -> dict[str, Any]:
    return {
        "label_type": "issue",
        "canonical_label_key": canonical,
        "raw_label": raw_label,
        "display_label_en": raw_label,
        "display_label_zh": raw_label,
        "aspect_key": "waterproof",
        "polarity": "negative",
        "evidence_candidate": evidence,
        "confidence": confidence,
        "reason": "v3-lite fixture",
    }


def test_customer_insights_projection_uses_only_verified_display_occurrences() -> None:
    shadow = run_customer_label_v2_shadow(
        _review(),
        label_candidates=[
            _candidate(),
            _candidate(evidence="missing evidence"),
            _candidate(canonical="candidate:boot_seam_leak", evidence="do not keep you dry"),
        ],
    )

    projection = project_customer_insights_from_shadow_result(shadow)

    assert len(shadow["display_occurrences"]) == 1
    assert len(shadow["audit_occurrences"]) == 2
    assert len(shadow["candidate_pool_items"]) == 1
    assert len(projection["customer_insights"]) == 1
    insight = projection["customer_insights"][0]
    assert set(CUSTOMER_INSIGHT_REQUIRED_FIELDS) <= set(insight)
    assert insight["source_layer"] == "display_occurrences"
    assert insight["canonical_label_key"] == "water_leaks_through"
    assert insight["evidence"]["verified"] is True
    assert projection["excluded_from_customer_insights"] == [
        "audit_occurrences",
        "candidate_pool_items",
        "label_candidates",
    ]


def test_customer_insights_artifact_reports_full_frontstage_display_coverage() -> None:
    shadows = [
        run_customer_label_v2_shadow(_review(), label_candidates=[_candidate()]),
        run_customer_label_v2_shadow(_review("Great product."), label_candidates=[]),
    ]

    artifact = project_customer_insights_artifact(shadows, scope="test v3-lite")

    assert artifact["status"] == "PASS"
    assert artifact["frontstage_display_occurrence_count"] == 1
    assert artifact["customer_insight_count"] == 1
    assert artifact["frontstage_display_occurrence_coverage"] == 1.0
    assert artifact["contract_violations"] == []
    assert artifact["safety"]["production_db_write"] is False
    assert artifact["safety"]["frontstage_mutated"] is False


def test_catalog_backlog_draft_aligns_required_governance_fields(tmp_path: Path) -> None:
    display_shadow = run_customer_label_v2_shadow(_review(), label_candidates=[_candidate()])
    reviewed_candidate_pool = {
        "reviewed_candidate_pool_items": [
            {
                "candidate_id": "pool:boot-seam",
                "review_status": "needs_new_label",
                "source_candidate_item": {
                    "canonical_label_key": "candidate:boot_seam_leak",
                    "label_type": "issue",
                    "category": "outdoor",
                    "sub_category": "waders",
                    "raw_label": "Boot seam leak",
                    "evidence_candidate": "boot seam leaked",
                    "downgrade_reasons": ["unknown_label"],
                    "review_count": 2,
                    "candidate_count": 2,
                },
                "review_output": {
                    "canonical_label_key": "candidate:boot_seam_leak",
                    "label_type": "issue",
                    "raw_label": "Boot seam leak",
                    "evidence_candidate": "boot seam leaked",
                },
            }
        ]
    }
    human_gold_fixture = {
        "samples": [
            {
                "id": "waders-351-400-row-365",
                "needs_new_label": [
                    {
                        "label_type": "highlight",
                        "canonical_label_key": "candidate:good_customer_service",
                        "raw_label_zh": "客服服务好",
                        "evidence_spans": [{"evidence_span": "Excellent customer service"}],
                        "review_status": "needs_new_label",
                        "reason": "new_or_boundary_label_not_in_display_catalog",
                    }
                ],
            }
        ]
    }

    artifact = build_catalog_backlog_draft(
        shadow_results=[display_shadow],
        reviewed_candidate_pool_artifact=reviewed_candidate_pool,
        human_gold_fixture=human_gold_fixture,
        scope="test v3-lite backlog",
    )

    assert artifact["status"] == "PASS"
    assert artifact["runtime_generation_source"] is False
    assert artifact["contract_violations"] == []
    assert artifact["summary"]["catalog_action_counts"]["keep_active"] == 1
    assert artifact["summary"]["catalog_action_counts"]["propose_new_label"] == 2
    for item in artifact["catalog_backlog_items"]:
        assert set(CATALOG_BACKLOG_REQUIRED_FIELDS) <= set(item)
        assert item["catalog_action"] in {"keep_active", "propose_new_label", "maturity_review"}

    csv_path = write_catalog_backlog_csv(tmp_path / "catalog-backlog-draft.csv", artifact["catalog_backlog_items"])
    assert csv_path.exists()
    assert "canonical_label_key,label_type,aspect_key" in csv_path.read_text(encoding="utf-8")
