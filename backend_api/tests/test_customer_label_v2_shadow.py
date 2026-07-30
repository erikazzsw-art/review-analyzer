from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

import pytest

from backend_api.app.services.customer_label_catalog import (
    CustomerLabelCatalogState,
    set_customer_label_catalog_state_for_tests,
)
from backend_api.app.services.customer_label_v2_shadow import (
    display_keys_from_shadow,
    run_customer_label_v2_shadow,
    v1_display_keys_for_review,
)

FIXTURES_DIR = Path(__file__).parent / "fixtures"
SESSION120_GOLD = FIXTURES_DIR / "customer_label_waders_session120_human_gold.json"
SESSION121_BLIND = FIXTURES_DIR / "customer_label_waders_session121_blind_regression.json"


@pytest.fixture(autouse=True)
def reset_catalog_state() -> None:
    set_customer_label_catalog_state_for_tests(CustomerLabelCatalogState())
    yield
    set_customer_label_catalog_state_for_tests(None)


def _review(content: str, *, review_id: str = "shadow-review", rating: int = 3) -> dict[str, Any]:
    return {
        "id": review_id,
        "content": content,
        "rating": rating,
        "category": "outdoor",
        "sub_category": "waders",
    }


def _candidate(
    *,
    label_type: str,
    canonical: str,
    evidence: str,
    aspect_key: str,
    raw_label: str | None = None,
    confidence: float = 0.9,
) -> dict[str, Any]:
    display = raw_label or " ".join(part.capitalize() for part in canonical.split("_"))
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
        "reason": "fixture candidate",
    }


def _audit_reasons(result: dict[str, Any]) -> set[str]:
    return {
        str(reason)
        for occurrence in result["audit_occurrences"]
        for reason in occurrence.get("downgrade_reasons") or []
    }


def _display_keys(result: dict[str, Any]) -> dict[str, list[str]]:
    return display_keys_from_shadow(result)


def test_v2_shadow_invalid_json_is_audit_only() -> None:
    result = run_customer_label_v2_shadow(_review("No leaks."), llm_output="{not json")

    assert result["label_candidates"] == []
    assert result["display_occurrences"] == []
    assert _audit_reasons(result) == {"invalid_json"}
    assert result["shadow_safety"]["llm_called"] is False
    assert result["shadow_safety"]["production_db_write"] is False


def test_v2_verifier_confidence_low_is_audit_only() -> None:
    result = run_customer_label_v2_shadow(
        _review("They do not keep you dry.", rating=1),
        label_candidates=[
            _candidate(
                label_type="issue",
                canonical="water_leaks_through",
                evidence="do not keep you dry",
                aspect_key="waterproof",
                confidence=0.4,
            )
        ],
    )

    assert _display_keys(result) == {"issue": [], "highlight": []}
    assert result["verified_occurrences"]
    assert "confidence_low" in result["downgrade_reasons"]
    assert result["audit_occurrences"][0]["display_allowed"] is False


def test_v2_verifier_schema_invalid_is_audit_only() -> None:
    result = run_customer_label_v2_shadow(
        _review("They do not keep you dry.", rating=1),
        label_candidates=[
            {
                "label_type": "issue",
                "canonical_label_key": "water_leaks_through",
                "raw_label": "",
                "aspect_key": "waterproof",
                "polarity": "negative",
                "evidence_candidate": "do not keep you dry",
                "confidence": 0.9,
                "reason": "schema fixture",
            }
        ],
    )

    assert _display_keys(result) == {"issue": [], "highlight": []}
    assert result["verified_occurrences"] == []
    assert result["candidate_pool_items"] == []
    assert "schema_invalid" in result["downgrade_reasons"]


def test_v2_shadow_evidence_missing_and_not_found_are_never_displayed() -> None:
    review = _review("They do not keep you dry.", rating=1)
    candidates = [
        _candidate(
            label_type="issue",
            canonical="water_leaks_through",
            evidence="",
            aspect_key="waterproof",
        ),
        _candidate(
            label_type="issue",
            canonical="water_leaks_through",
            evidence="leaked through the seams",
            aspect_key="waterproof",
        ),
    ]

    result = run_customer_label_v2_shadow(review, label_candidates=candidates)

    assert result["display_occurrences"] == []
    assert {"evidence_missing", "evidence_not_found"} <= _audit_reasons(result)


def test_v2_verifier_source_review_blocked_is_audit_only() -> None:
    result = run_customer_label_v2_shadow(
        _review("My old waders leaked every trip; this pair fits fine.", rating=4),
        label_candidates=[
            _candidate(
                label_type="issue",
                canonical="water_leaks_through",
                evidence="old waders leaked",
                aspect_key="waterproof",
            )
        ],
    )

    assert _display_keys(result) == {"issue": [], "highlight": []}
    assert "source_review_blocked" in result["downgrade_reasons"]


def test_v2_shadow_blocks_old_product_and_other_brand_water_leak_candidates() -> None:
    cases = [
        (
            "Bought as a gift for my boyfriend who has had numerous pairs of waders in the past that have leaked. "
            "These were affordable and have not caused him any issues.",
            "leaked",
        ),
        (
            "These waders are awesome. I have spent hundreds of dollars on other neoprene waders that continue to "
            "leak. These waders are lightweight and keep you dry.",
            "continue to leak",
        ),
    ]

    for content, evidence in cases:
        result = run_customer_label_v2_shadow(
            _review(content),
            label_candidates=[
                _candidate(
                    label_type="issue",
                    canonical="water_leaks_through",
                    evidence=evidence,
                    aspect_key="waterproof",
                )
            ],
        )

        assert display_keys_from_shadow(result)["issue"] == []
        assert "source_review_blocked" in _audit_reasons(result)


def test_v2_shadow_blocks_accessory_leak_as_body_waterproof_issue_but_keeps_pocket_issue() -> None:
    review = _review(
        "The waders are fine and the measurements are very accurate. However, the waterproof phone case is not at "
        "all what it shows as. It is not waterproof; water leaks in very easily.",
    )
    result = run_customer_label_v2_shadow(
        review,
        label_candidates=[
            _candidate(
                label_type="issue",
                canonical="water_leaks_through",
                evidence="It is not waterproof",
                aspect_key="waterproof",
            ),
            _candidate(
                label_type="issue",
                canonical="pocket_not_waterproof",
                evidence="the waterproof phone case is not at all what it shows as",
                aspect_key="accessory_storage",
            ),
        ],
    )

    keys = display_keys_from_shadow(result)
    assert keys["issue"] == ["pocket_not_waterproof"]
    assert "source_review_blocked" in _audit_reasons(result)


def test_v2_shadow_splits_positive_no_leaks_from_negative_do_not_keep_dry() -> None:
    positive = run_customer_label_v2_shadow(
        _review("I wore these in cold water for hours. No leaks and they kept me dry.", rating=5),
        label_candidates=[
            _candidate(
                label_type="issue",
                canonical="water_leaks_through",
                evidence="No leaks",
                aspect_key="waterproof",
            ),
            _candidate(
                label_type="highlight",
                canonical="keeps_water_out",
                evidence="No leaks",
                aspect_key="waterproof",
            ),
        ],
    )
    negative = run_customer_label_v2_shadow(
        _review("They do not keep you dry.", rating=1),
        label_candidates=[
            _candidate(
                label_type="issue",
                canonical="water_leaks_through",
                evidence="do not keep you dry",
                aspect_key="waterproof",
            ),
            _candidate(
                label_type="highlight",
                canonical="keeps_water_out",
                evidence="keep you dry",
                aspect_key="waterproof",
            ),
        ],
    )

    assert display_keys_from_shadow(positive) == {"issue": [], "highlight": ["keeps_water_out"]}
    assert "context_blocked" in _audit_reasons(positive)
    assert display_keys_from_shadow(negative) == {"issue": ["water_leaks_through"], "highlight": []}
    assert "context_blocked" in _audit_reasons(negative)


def test_v2_verifier_context_blocked_positive_leak_claim_is_audit_only() -> None:
    result = run_customer_label_v2_shadow(
        _review("No leaks and they kept me dry.", rating=5),
        label_candidates=[
            _candidate(
                label_type="issue",
                canonical="water_leaks_through",
                evidence="No leaks",
                aspect_key="waterproof",
            )
        ],
    )

    assert _display_keys(result) == {"issue": [], "highlight": []}
    assert "context_blocked" in result["downgrade_reasons"]


def test_v2_verifier_aspect_blocked_is_audit_only() -> None:
    result = run_customer_label_v2_shadow(
        _review("They do not keep you dry.", rating=1),
        label_candidates=[
            _candidate(
                label_type="issue",
                canonical="water_leaks_through",
                evidence="do not keep you dry",
                aspect_key="value_for_money",
            )
        ],
    )

    assert _display_keys(result) == {"issue": [], "highlight": []}
    assert "aspect_blocked" in result["downgrade_reasons"]
    assert result["audit_occurrences"][0]["aspect_allowed"] is False


def test_v2_verifier_maturity_blocked_enters_candidate_pool() -> None:
    result = run_customer_label_v2_shadow(
        _review("They do not keep you dry.", rating=1),
        maturity_level="L0_unknown",
        label_candidates=[
            _candidate(
                label_type="issue",
                canonical="water_leaks_through",
                evidence="do not keep you dry",
                aspect_key="waterproof",
            )
        ],
    )

    assert _display_keys(result) == {"issue": [], "highlight": []}
    assert "maturity_blocked" in result["downgrade_reasons"]
    assert result["candidate_pool_items"]
    assert result["candidate_pool_items"][0]["review_status"] == "pending"


def test_v2_verifier_valid_display_occurrence_has_stable_fields() -> None:
    result = run_customer_label_v2_shadow(
        _review("They do not keep you dry.", rating=1),
        label_candidates=[
            _candidate(
                label_type="issue",
                canonical="water_leaks_through",
                evidence="do not keep you dry",
                aspect_key="waterproof",
            )
        ],
    )

    assert _display_keys(result) == {"issue": ["water_leaks_through"], "highlight": []}
    assert result["downgrade_reasons"] == []
    occurrence = result["display_occurrences"][0]
    assert {
        "label_type",
        "canonical_label_key",
        "evidence_span",
        "evidence_verified",
        "source_review_allowed",
        "aspect_allowed",
        "context_allowed",
        "maturity_allowed",
        "display_allowed",
        "downgrade_reasons",
    } <= occurrence.keys()
    assert occurrence["display_allowed"] is True
    assert occurrence["downgrade_reasons"] == []


def test_v2_verifier_audit_only_occurrence_never_enters_display() -> None:
    candidate = _candidate(
        label_type="issue",
        canonical="water_leaks_through",
        evidence="do not keep you dry",
        aspect_key="waterproof",
    )
    candidate["cluster_propagated"] = True

    result = run_customer_label_v2_shadow(_review("They do not keep you dry.", rating=1), label_candidates=[candidate])

    assert result["verified_occurrences"]
    assert result["display_occurrences"] == []
    assert result["audit_occurrences"][0]["display_allowed"] is False
    assert result["audit_occurrences"][0]["cluster_propagated"] is True
    assert "cluster_propagated" in result["downgrade_reasons"]


def test_v2_shadow_generic_praise_does_not_expand_to_four_pack() -> None:
    candidates = [
        _candidate(
            label_type="highlight",
            canonical=canonical,
            evidence="Great product",
            aspect_key=aspect_key,
        )
        for canonical, aspect_key in (
            ("fits_as_expected", "size_fit"),
            ("good_value_for_the_price", "value_for_money"),
            ("holds_up_well", "durability"),
            ("keeps_water_out", "waterproof"),
        )
    ]

    result = run_customer_label_v2_shadow(_review("Great product.", rating=5), label_candidates=candidates)

    assert display_keys_from_shadow(result) == {"issue": [], "highlight": []}
    assert _audit_reasons(result) == {"evidence_too_generic"}


def test_v2_shadow_unknown_label_enters_candidate_pool_only() -> None:
    result = run_customer_label_v2_shadow(
        _review("The boot seam leaked on the first trip.", rating=1),
        label_candidates=[
            _candidate(
                label_type="issue",
                canonical="candidate:boot_seam_leak",
                evidence="boot seam leaked",
                aspect_key="seam_integrity",
            )
        ],
    )

    assert result["display_occurrences"] == []
    assert result["candidate_pool_items"]
    pool_item = result["candidate_pool_items"][0]
    assert {
        "candidate_id",
        "review_id",
        "session_id",
        "product_id",
        "category",
        "sub_category",
        "label_type",
        "canonical_label_key",
        "raw_label",
        "evidence_candidate",
        "confidence",
        "downgrade_reasons",
        "top_impact_score",
        "review_status",
    } <= pool_item.keys()
    assert pool_item["review_status"] == "pending"
    assert "unknown_label" in _audit_reasons(result)


def test_v2_shadow_session120_human_gold_exact_replay() -> None:
    payload = json.loads(SESSION120_GOLD.read_text(encoding="utf-8"))

    for sample in payload["samples"]:
        result = run_customer_label_v2_shadow(_review(sample["content"], review_id=sample["id"]))
        keys = display_keys_from_shadow(result)
        assert set(keys["issue"]) == set(sample["human_issue_keys"]), sample["id"]
        assert set(keys["highlight"]) == set(sample["human_highlight_keys"]), sample["id"]


def test_v2_shadow_session121_blind_required_and_blocked_boundaries() -> None:
    payload = json.loads(SESSION121_BLIND.read_text(encoding="utf-8"))

    for sample in payload["samples"]:
        result = run_customer_label_v2_shadow(_review(sample["content"], review_id=sample["id"]))
        keys = display_keys_from_shadow(result)
        assert set(sample["required_issue_keys"]) <= set(keys["issue"]), sample["id"]
        assert set(sample["required_highlight_keys"]) <= set(keys["highlight"]), sample["id"]
        assert not (set(sample["blocked_issue_keys"]) & set(keys["issue"])), sample["id"]
        assert not (set(sample["blocked_highlight_keys"]) & set(keys["highlight"])), sample["id"]


def test_v2_shadow_does_not_mutate_v1_frontstage_payload() -> None:
    review = _review("They do not keep you dry.", review_id="mutation-guard", rating=1)
    before = copy.deepcopy(review)
    before_keys = v1_display_keys_for_review(review)

    result = run_customer_label_v2_shadow(review)

    assert review == before
    assert v1_display_keys_for_review(review) == before_keys
    assert display_keys_from_shadow(result)["issue"] == ["water_leaks_through"]
