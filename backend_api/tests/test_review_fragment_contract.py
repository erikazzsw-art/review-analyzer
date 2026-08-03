from __future__ import annotations

import json
from pathlib import Path

from backend_api.app.services.review_fragment_contract import (
    REVIEW_FRAGMENT_REQUIRED_FIELDS,
    REVIEW_FRAGMENT_SAMPLE_SCHEMA_VERSION,
    validate_review_fragment,
    validate_review_fragment_fixture,
)

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "review_fragment_5_9_1_samples.json"


def _load_fixture() -> dict:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def test_review_fragment_5_9_1_fixture_matches_contract() -> None:
    fixture = _load_fixture()

    assert fixture["schema_version"] == REVIEW_FRAGMENT_SAMPLE_SCHEMA_VERSION
    assert validate_review_fragment_fixture(fixture) == []
    assert len(fixture["samples"]) == 5


def test_fragment_records_use_only_the_5_9_1_required_fields() -> None:
    fixture = _load_fixture()
    required_fields = set(REVIEW_FRAGMENT_REQUIRED_FIELDS)

    for sample in fixture["samples"]:
        for fragment in sample["fragments"]:
            assert set(fragment) == required_fields


def test_aggregatable_fragments_have_evidence_and_no_reject_reason() -> None:
    fixture = _load_fixture()

    aggregatable = [
        fragment
        for sample in fixture["samples"]
        for fragment in sample["fragments"]
        if fragment["can_aggregate"] is True
    ]

    assert aggregatable
    assert all(fragment["evidence_span"] in fragment["fragment_text"] for fragment in aggregatable)
    assert all(fragment["aspect_key"] for fragment in aggregatable)
    assert all(fragment["reject_reason"] is None for fragment in aggregatable)


def test_boundary_fragments_are_routed_but_not_aggregated() -> None:
    fixture = _load_fixture()
    blocked = [
        fragment
        for sample in fixture["samples"]
        for fragment in sample["fragments"]
        if fragment["reject_reason"]
    ]

    assert {
        "accessory_only",
        "fragment_too_vague",
        "not_used_yet",
        "other_product_or_competitor",
    } <= {fragment["reject_reason"] for fragment in blocked}
    assert all(fragment["can_aggregate"] is False for fragment in blocked)


def test_invalid_fragment_examples_fail_closed() -> None:
    candidate_that_tries_to_aggregate = {
        "fragment_text": "The boot seam leaked",
        "module": "other_candidate",
        "aspect_key": "candidate:boot_seam_leak",
        "polarity": "negative",
        "evidence_span": "boot seam leaked",
        "confidence": 0.8,
        "current_product_scope": "current_product",
        "can_aggregate": True,
        "reject_reason": None,
    }
    assert {
        "module_cannot_aggregate",
        "unapproved_aspect_cannot_aggregate",
    } <= set(validate_review_fragment(candidate_that_tries_to_aggregate))

    old_product_that_tries_to_aggregate = {
        "fragment_text": "my old waders leaked",
        "module": "comparison_or_other_product",
        "aspect_key": "water_leaks_through",
        "polarity": "negative",
        "evidence_span": "old waders leaked",
        "confidence": 0.9,
        "current_product_scope": "other_product",
        "can_aggregate": True,
        "reject_reason": None,
    }
    assert "module_cannot_aggregate" in validate_review_fragment(old_product_that_tries_to_aggregate)

    missing_evidence = {
        "fragment_text": "The fit is great",
        "module": "product_highlight",
        "aspect_key": "fits_as_expected",
        "polarity": "positive",
        "evidence_span": "battery lasts forever",
        "confidence": 0.9,
        "current_product_scope": "current_product",
        "can_aggregate": True,
        "reject_reason": None,
    }
    assert "evidence_span_not_in_fragment" in validate_review_fragment(missing_evidence)


def test_duplicate_aggregate_aspect_fails_closed_within_one_review() -> None:
    first_fragment = {
        "fragment_text": "the boots fit well",
        "module": "product_highlight",
        "aspect_key": "fits_as_expected",
        "polarity": "positive",
        "evidence_span": "boots fit well",
        "confidence": 0.9,
        "current_product_scope": "current_product",
        "can_aggregate": True,
        "reject_reason": None,
    }
    duplicate_fragment = {
        **first_fragment,
        "fragment_text": "the leg length fits perfectly",
        "evidence_span": "leg length fits perfectly",
    }
    sample = {
        "id": "duplicate-fit-highlight",
        "content": "The boots fit well and the leg length fits perfectly.",
        "category": "outdoor",
        "sub_category": "waders",
        "fragments": [first_fragment, duplicate_fragment],
    }

    errors = validate_review_fragment_fixture(
        {
            "schema_version": REVIEW_FRAGMENT_SAMPLE_SCHEMA_VERSION,
            "samples": [sample],
        }
    )

    assert "samples[0].fragments[1].duplicate_aggregate_aspect" in errors
