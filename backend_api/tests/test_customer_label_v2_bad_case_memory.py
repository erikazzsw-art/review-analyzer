from __future__ import annotations

from typing import Any

import pytest

from backend_api.app.services.customer_label_catalog import (
    CustomerLabelCatalogState,
    set_customer_label_catalog_state_for_tests,
)
from backend_api.app.services.customer_label_v2_bad_case_memory import (
    build_customer_label_v2_bad_case_memory,
    build_customer_label_v2_bad_case_memory_debug_report,
    cluster_unknown_label_candidates,
    prioritize_maturity_blocked_candidates,
    search_similar_bad_cases,
)
from backend_api.app.services.customer_label_v2_frontstage import (
    READ_PATH_V2_SHADOW,
    CustomerLabelV2FrontstageFlag,
    build_customer_label_v2_frontstage_read_model,
)
from backend_api.app.services.customer_label_v2_shadow import run_customer_label_v2_shadow


@pytest.fixture(autouse=True)
def reset_catalog_state() -> None:
    set_customer_label_catalog_state_for_tests(CustomerLabelCatalogState())
    yield
    set_customer_label_catalog_state_for_tests(None)


def _candidate(
    *,
    canonical: str = "water_leaks_through",
    evidence: str = "do not keep you dry",
    raw_label: str = "Water Leaks Through",
    aspect_key: str = "waterproof",
    confidence: float = 0.9,
) -> dict[str, Any]:
    return {
        "label_type": "issue",
        "canonical_label_key": canonical,
        "raw_label": raw_label,
        "display_label_en": raw_label,
        "display_label_zh": raw_label,
        "aspect_key": aspect_key,
        "polarity": "negative",
        "evidence_candidate": evidence,
        "confidence": confidence,
        "reason": "step8 vector memory fixture",
    }


def _review(
    content: str = "They do not keep you dry.",
    *,
    review_id: str = "step8-review",
) -> dict[str, Any]:
    return {
        "id": review_id,
        "session_id": "step8-session",
        "product_id": "TIDEWE-step8",
        "content": content,
        "rating": 1,
        "category": "outdoor",
        "sub_category": "waders",
    }


def _reviewed_artifact() -> dict[str, Any]:
    return {
        "schema_version": "customer-label-v2-candidate-pool-reviewed-mvp.1",
        "reviewed_candidate_pool_items": [
            {
                "candidate_id": "pool:boot-seam-1",
                "review_status": "needs_new_label",
                "source_candidate_item": {
                    "candidate_id": "pool:boot-seam-1",
                    "category": "outdoor",
                    "sub_category": "waders",
                    "label_type": "issue",
                    "canonical_label_key": "candidate:boot_seam_leak",
                    "raw_label": "Boot seam leak",
                    "evidence_candidate": "boot seam leaked",
                    "confidence": 0.88,
                    "downgrade_reasons": ["unknown_label"],
                    "review_count": 2,
                    "top_impact_score": 3.2,
                },
                "action": {"action": "needs_new_label", "reviewer": "step8-test"},
                "review_output": {},
            },
            {
                "candidate_id": "pool:boot-seam-2",
                "review_status": "needs_new_label",
                "source_candidate_item": {
                    "candidate_id": "pool:boot-seam-2",
                    "category": "outdoor",
                    "sub_category": "waders",
                    "label_type": "issue",
                    "canonical_label_key": "candidate:boot_seam_leaking",
                    "raw_label": "Boot seam leaking",
                    "evidence_candidate": "seam leaked around the boot",
                    "confidence": 0.8,
                    "downgrade_reasons": ["unknown_label"],
                    "review_count": 1,
                    "top_impact_score": 1.4,
                },
                "action": {"action": "needs_new_label", "reviewer": "step8-test"},
                "review_output": {},
            },
            {
                "candidate_id": "pool:pocket-maturity",
                "review_status": "accepted",
                "source_candidate_item": {
                    "candidate_id": "pool:pocket-maturity",
                    "category": "home",
                    "sub_category": "bed_frame",
                    "label_type": "issue",
                    "canonical_label_key": "pocket_not_waterproof",
                    "raw_label": "Pocket not waterproof",
                    "evidence_candidate": "pocket is not waterproof",
                    "confidence": 0.9,
                    "downgrade_reasons": ["maturity_blocked"],
                    "review_count": 4,
                    "top_impact_score": 7.2,
                },
                "action": {"action": "accept", "reviewer": "step8-test"},
                "review_output": {},
            },
            {
                "candidate_id": "pool:value-maturity",
                "review_status": "accepted",
                "source_candidate_item": {
                    "candidate_id": "pool:value-maturity",
                    "category": "baby",
                    "sub_category": "baby_bibs",
                    "label_type": "issue",
                    "canonical_label_key": "quality_problem",
                    "raw_label": "Quality problem",
                    "evidence_candidate": "quality is poor",
                    "confidence": 0.7,
                    "downgrade_reasons": ["maturity_blocked"],
                    "review_count": 1,
                    "top_impact_score": 1.1,
                },
                "action": {"action": "accept", "reviewer": "step8-test"},
                "review_output": {},
            },
        ],
    }


def test_similar_bad_case_retrieval_returns_historical_context_match() -> None:
    old_product_shadow = run_customer_label_v2_shadow(
        _review(
            (
                "My old waders leaked last season. These new waders are fine and have not "
                "caused any water problems."
            ),
            review_id="step8-old-product",
        ),
        label_candidates=[_candidate(evidence="old waders leaked")],
    )
    memory = build_customer_label_v2_bad_case_memory(
        audited_shadow_results=[old_product_shadow],
        gold_regression_cases=[],
        reviewed_candidate_pool_artifact=None,
    )

    results = search_similar_bad_cases("old waders leaked but these are fine", memory, top_k=1)

    assert results
    assert results[0]["source_type"] == "audited_bad_case"
    assert "source_review_blocked" in results[0]["downgrade_reasons"]


def test_unknown_label_candidate_clustering_groups_similar_reviewed_candidates() -> None:
    memory = build_customer_label_v2_bad_case_memory(
        reviewed_candidate_pool_artifact=_reviewed_artifact(),
    )

    clusters = cluster_unknown_label_candidates(memory)

    assert clusters
    assert clusters[0]["item_count"] == 2
    assert set(clusters[0]["canonical_label_keys"]) == {
        "candidate:boot_seam_leak",
        "candidate:boot_seam_leaking",
    }


def test_maturity_blocked_candidate_prioritization_uses_review_count_and_impact() -> None:
    memory = build_customer_label_v2_bad_case_memory(
        reviewed_candidate_pool_artifact=_reviewed_artifact(),
    )

    priorities = prioritize_maturity_blocked_candidates(memory)

    assert priorities[0]["canonical_label_key"] == "pocket_not_waterproof"
    assert priorities[0]["review_count"] == 4
    assert priorities[0]["priority_score"] > priorities[1]["priority_score"]


def test_vector_memory_cannot_bypass_display_gate() -> None:
    memory = build_customer_label_v2_bad_case_memory(
        reviewed_candidate_pool_artifact=_reviewed_artifact(),
    )
    search_results = search_similar_bad_cases("water leaks through and do not keep dry", memory, top_k=3)
    blocked_shadow = run_customer_label_v2_shadow(
        _review(),
        label_candidates=[_candidate(evidence="")],
    )
    read_model = build_customer_label_v2_frontstage_read_model(
        _review(),
        flag=CustomerLabelV2FrontstageFlag(
            enabled=True,
            sub_categories=("outdoor/waders",),
            shadow_fixture_gate_passed=True,
            allow_runtime_shadow=False,
        ),
        shadow_result=blocked_shadow,
    )

    assert search_results is not None
    assert blocked_shadow["display_occurrences"] == []
    assert "evidence_missing" in blocked_shadow["downgrade_reasons"]
    assert read_model["read_path"] == READ_PATH_V2_SHADOW
    assert read_model["frontstage_occurrences"] == []
    assert memory["display_contract"]["vector_memory_can_select_frontstage"] is False


def test_no_evidence_and_context_blocked_cases_still_do_not_enter_frontstage() -> None:
    no_evidence = run_customer_label_v2_shadow(
        _review(review_id="step8-no-evidence"),
        label_candidates=[_candidate(evidence="")],
    )
    context_blocked = run_customer_label_v2_shadow(
        _review(
            (
                "Bought as a gift for my boyfriend who has had numerous pairs of waders "
                "in the past that have leaked. These have not caused any issues."
            ),
            review_id="step8-context-blocked",
        ),
        label_candidates=[_candidate(evidence="leaked")],
    )
    memory = build_customer_label_v2_bad_case_memory(
        audited_shadow_results=[no_evidence, context_blocked],
        reviewed_candidate_pool_artifact=_reviewed_artifact(),
    )
    report = build_customer_label_v2_bad_case_memory_debug_report(
        memory,
        queries=["leaked old waders context"],
    )

    assert no_evidence["display_occurrences"] == []
    assert context_blocked["display_occurrences"] == []
    assert "evidence_missing" in no_evidence["downgrade_reasons"]
    assert "source_review_blocked" in context_blocked["downgrade_reasons"]
    assert report["display_contract"]["vector_memory_can_select_frontstage"] is False
