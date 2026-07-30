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
    build_candidate_pool_artifact,
    build_reviewed_candidate_pool_artifact,
)
from backend_api.app.services.customer_label_v2_maturity import (
    MATURITY_L0_UNKNOWN,
    MATURITY_L1_GENERIC,
    MATURITY_L2_CATEGORY,
    MATURITY_L3_SUB_CATEGORY,
    maturity_contract_summary,
    resolve_customer_label_maturity,
)
from backend_api.app.services.customer_label_v2_shadow import (
    display_keys_from_shadow,
    run_customer_label_v2_shadow,
)

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "customer_label_v2_maturity_rollout.json"


@pytest.fixture(autouse=True)
def reset_catalog_state() -> None:
    set_customer_label_catalog_state_for_tests(CustomerLabelCatalogState())
    yield
    set_customer_label_catalog_state_for_tests(None)


def _candidate(
    *,
    label_type: str,
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
        "reason": "maturity focused fixture",
    }


def _review(
    content: str,
    *,
    category: str,
    sub_category: str,
    review_id: str = "maturity-review",
    rating: int = 3,
) -> dict[str, Any]:
    return {
        "id": review_id,
        "session_id": "maturity-step5",
        "product_id": "synthetic-product",
        "content": content,
        "rating": rating,
        "category": category,
        "sub_category": sub_category,
    }


def _audit_reasons(result: dict[str, Any]) -> set[str]:
    return {
        str(reason)
        for occurrence in result["audit_occurrences"]
        for reason in occurrence.get("downgrade_reasons") or []
    }


def _fixture_payload() -> dict[str, Any]:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def test_maturity_contract_resolves_taxonomy_map_and_waders_override() -> None:
    contract = maturity_contract_summary()
    levels = contract["levels"]

    assert set(levels) == {MATURITY_L0_UNKNOWN, MATURITY_L1_GENERIC, MATURITY_L2_CATEGORY, MATURITY_L3_SUB_CATEGORY}
    assert len(contract["category_rollout"]) == 10
    assert contract["sub_category_overrides"] == {"outdoor/waders": MATURITY_L3_SUB_CATEGORY}
    assert resolve_customer_label_maturity(category="", sub_category="床架").level == MATURITY_L2_CATEGORY
    assert resolve_customer_label_maturity(category="outdoor", sub_category="waders").level == MATURITY_L3_SUB_CATEGORY


def test_l0_unknown_does_not_enter_display() -> None:
    result = run_customer_label_v2_shadow(
        _review("Great product.", category="toys", sub_category="Mystery Toy", rating=5),
        label_candidates=[
            _candidate(
                label_type="highlight",
                canonical="overall_satisfied",
                evidence="Great product",
                aspect_key="other",
            )
        ],
    )

    assert result["maturity_level"] == MATURITY_L0_UNKNOWN
    assert display_keys_from_shadow(result) == {"issue": [], "highlight": []}
    assert "maturity_blocked" in _audit_reasons(result)
    assert result["candidate_pool_items"][0]["downgrade_reasons"] == ["maturity_blocked"]


def test_l1_generic_allows_only_generic_safe_highlights() -> None:
    result = run_customer_label_v2_shadow(
        _review("Great product. The bib quality is poor.", category="baby", sub_category="Baby Bibs", rating=3),
        label_candidates=[
            _candidate(
                label_type="highlight",
                canonical="overall_satisfied",
                evidence="Great product",
                aspect_key="other",
                confidence=0.92,
            ),
            _candidate(
                label_type="issue",
                canonical="quality_problem",
                evidence="quality is poor",
                aspect_key="build_quality",
                confidence=0.92,
            ),
        ],
    )

    assert result["maturity_level"] == MATURITY_L1_GENERIC
    assert display_keys_from_shadow(result) == {"issue": [], "highlight": ["overall_satisfied"]}
    assert "maturity_blocked" in _audit_reasons(result)
    assert len(result["candidate_pool_items"]) == 1
    assert result["candidate_pool_items"][0]["canonical_label_key"] == "quality_problem"


def test_l2_category_allows_foundational_labels_but_keeps_verifier_gates() -> None:
    display = run_customer_label_v2_shadow(
        _review("The bed frame cracked after a week.", category="home", sub_category="床架", rating=2),
        label_candidates=[
            _candidate(
                label_type="issue",
                canonical="quality_problem",
                raw_label="Quality problem",
                evidence="frame cracked",
                aspect_key="build_quality",
                confidence=0.9,
            )
        ],
    )
    wrong_aspect = run_customer_label_v2_shadow(
        _review("The bed frame cracked after a week.", category="home", sub_category="床架", rating=2),
        label_candidates=[
            _candidate(
                label_type="issue",
                canonical="quality_problem",
                raw_label="Quality problem",
                evidence="frame cracked",
                aspect_key="waterproof",
                confidence=0.9,
            )
        ],
    )
    low_confidence = run_customer_label_v2_shadow(
        _review("The bed frame cracked after a week.", category="home", sub_category="床架", rating=2),
        label_candidates=[
            _candidate(
                label_type="issue",
                canonical="quality_problem",
                raw_label="Quality problem",
                evidence="frame cracked",
                aspect_key="build_quality",
                confidence=0.7,
            )
        ],
    )

    assert display["maturity_level"] == MATURITY_L2_CATEGORY
    assert display_keys_from_shadow(display) == {"issue": ["quality_problem"], "highlight": []}
    assert display["candidate_pool_items"] == []
    assert display_keys_from_shadow(wrong_aspect) == {"issue": [], "highlight": []}
    assert "aspect_blocked" in _audit_reasons(wrong_aspect)
    assert wrong_aspect["candidate_pool_items"] == []
    assert display_keys_from_shadow(low_confidence) == {"issue": [], "highlight": []}
    assert "confidence_low" in _audit_reasons(low_confidence)
    assert low_confidence["candidate_pool_items"] == []


def test_l3_waders_does_not_regress_to_category_gate() -> None:
    result = run_customer_label_v2_shadow(
        _review("They do not keep you dry.", category="outdoor", sub_category="waders", rating=1),
        label_candidates=[
            _candidate(
                label_type="issue",
                canonical="water_leaks_through",
                evidence="do not keep you dry",
                aspect_key="waterproof",
            )
        ],
    )

    assert result["maturity_level"] == MATURITY_L3_SUB_CATEGORY
    assert display_keys_from_shadow(result) == {"issue": ["water_leaks_through"], "highlight": []}
    assert result["candidate_pool_items"] == []


def test_unknown_label_stays_candidate_pool_only_independent_of_maturity() -> None:
    result = run_customer_label_v2_shadow(
        _review("The desk hinge squeaks loudly.", category="home", sub_category="床架", rating=2),
        label_candidates=[
            _candidate(
                label_type="issue",
                canonical="candidate:desk_hinge_squeaks",
                raw_label="Desk hinge squeaks",
                evidence="hinge squeaks",
                aspect_key="hardware_noise",
            )
        ],
    )

    assert result["maturity_level"] == MATURITY_L2_CATEGORY
    assert display_keys_from_shadow(result) == {"issue": [], "highlight": []}
    assert result["candidate_pool_items"]
    assert result["candidate_pool_items"][0]["downgrade_reasons"] == ["unknown_label"]
    assert "maturity_blocked" not in _audit_reasons(result)


def test_maturity_blocked_candidate_pool_aggregation_and_review_artifact() -> None:
    results = [
        run_customer_label_v2_shadow(
            _review("The bib quality is poor.", category="baby", sub_category="Baby Bibs", review_id=review_id),
            label_candidates=[
                _candidate(
                    label_type="issue",
                    canonical="quality_problem",
                    raw_label="Quality problem",
                    evidence="quality is poor",
                    aspect_key="build_quality",
                )
            ],
        )
        for review_id in ("maturity-blocked-r1", "maturity-blocked-r2")
    ]
    pool = build_candidate_pool_artifact(results)
    item = pool["candidate_pool_items"][0]
    reviewed = build_reviewed_candidate_pool_artifact(
        pool,
        [{"candidate_id": item["candidate_id"], "action": "accept", "reviewer": "step5-focused-test"}],
    )

    assert pool["raw_item_count"] == 2
    assert pool["item_count"] == 1
    assert item["canonical_label_key"] == "quality_problem"
    assert item["downgrade_reasons"] == ["maturity_blocked"]
    assert item["review_count"] == 2
    assert reviewed["review_action_summary"]["status_counts"] == {"accepted": 1}
    assert reviewed["reviewed_candidate_pool_items"][0]["source_candidate_item"]["downgrade_reasons"] == [
        "maturity_blocked"
    ]
    assert reviewed["safety"]["production_db_write"] is False
    assert reviewed["safety"]["llm_called"] is False


def test_ten_category_l1_l2_rollout_fixture_display_audit_candidate_pool_split() -> None:
    payload = _fixture_payload()
    seen_categories: set[str] = set()
    blocked_pool_results: list[dict[str, Any]] = []

    for group in payload["categories"]:
        category = str(group["category"])
        seen_categories.add(category)
        sub_category = str(group["sub_category"])
        expected_level = str(group["expected_maturity_level"])
        for case in group["cases"]:
            result = run_customer_label_v2_shadow(
                _review(
                    str(case["content"]),
                    category=category,
                    sub_category=sub_category,
                    review_id=str(case["id"]),
                    rating=int(case.get("rating") or 3),
                ),
                label_candidates=[case["candidate"]],
            )

            assert result["maturity_level"] == expected_level, case["id"]
            assert display_keys_from_shadow(result) == case["expected_display"], case["id"]
            assert set(case["expected_audit_reasons"]) <= _audit_reasons(result), case["id"]
            expected_pool_reasons = list(case["expected_candidate_pool_reasons"])
            if expected_pool_reasons:
                assert result["candidate_pool_items"], case["id"]
                assert expected_pool_reasons == result["candidate_pool_items"][0]["downgrade_reasons"], case["id"]
                blocked_pool_results.append(result)
            else:
                assert result["candidate_pool_items"] == [], case["id"]

    assert seen_categories == {"home", "3c", "apparel", "baby", "pet", "outdoor", "beauty", "kitchen", "automotive", "office"}
    pool = build_candidate_pool_artifact(blocked_pool_results)
    assert pool["raw_item_count"] == len(blocked_pool_results)
    assert pool["item_count"] >= 1
    assert {tuple(item["downgrade_reasons"]) for item in pool["candidate_pool_items"]} == {("maturity_blocked",)}
