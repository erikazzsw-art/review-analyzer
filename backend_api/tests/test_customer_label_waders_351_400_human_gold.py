from __future__ import annotations

import json
from collections import Counter, defaultdict
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
from backend_api.app.services.customer_label_v2_shadow import (
    FOCUS_WADERS_LABELS,
    display_keys_from_shadow,
    run_customer_label_v2_shadow,
)
from backend_api.app.services.specific_issue import (
    CUSTOMER_LABEL_OCCURRENCE_RULESET_VERSION,
    CUSTOMER_LABEL_OCCURRENCE_SCHEMA_VERSION,
    build_customer_highlight_rows,
    customer_highlight_tags_for_comment,
    iter_customer_highlight_occurrences,
)

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "customer_label_waders_351_400_human_gold.json"


@pytest.fixture(autouse=True)
def reset_catalog_state() -> None:
    set_customer_label_catalog_state_for_tests(CustomerLabelCatalogState())
    yield
    set_customer_label_catalog_state_for_tests(None)


def _fixture_payload() -> dict[str, Any]:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def _review(sample: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": sample["id"],
        "session_id": 351,
        "product_id": "TIDEWE-下水服-WD001",
        "content": sample["content"],
        "rating": sample.get("rating") or 3,
        "category": "outdoor",
        "sub_category": "waders",
    }


def _candidate_from_new_label(item: dict[str, Any]) -> dict[str, Any]:
    evidence = str(item["evidence_spans"][0]["evidence_span"])
    label_type = str(item["label_type"])
    canonical = str(item["canonical_label_key"])
    return {
        "label_type": label_type,
        "canonical_label_key": canonical,
        "raw_label": str(item["raw_label_zh"]),
        "display_label_en": " ".join(part.capitalize() for part in canonical.replace("candidate:", "").split("_")),
        "display_label_zh": str(item["raw_label_zh"]),
        "aspect_key": "other",
        "polarity": "negative" if label_type == "issue" else "positive",
        "evidence_candidate": evidence,
        "confidence": 0.88,
        "reason": "waders 351-400 human gold needs_new_label fixture",
    }


def _content_occurrence(
    sample: dict[str, Any],
    group: dict[str, Any],
    span: dict[str, Any],
    display_meta: dict[str, Any],
) -> dict[str, Any]:
    label_type = str(group["label_type"])
    canonical = str(group["canonical_label_key"])
    meta = display_meta[f"{label_type}:{canonical}"]
    return {
        "comment_id": sample["id"],
        "type": label_type,
        "raw_label": meta["display_label_en"],
        "canonical_label_key": canonical,
        "display_label_en": meta["display_label_en"],
        "display_label_zh": meta["display_label_zh"],
        "aspect_key": meta["aspect_key"],
        "evidence_span": span["evidence_span"],
        "evidence_start": span["evidence_start"],
        "evidence_end": span["evidence_end"],
        "confidence": "high",
        "source": "llm",
        "source_detail": "waders_351_400_human_gold_synthetic",
        "evidence_verified": True,
        "cluster_propagated": False,
        "schema_version": CUSTOMER_LABEL_OCCURRENCE_SCHEMA_VERSION,
        "ruleset_version": CUSTOMER_LABEL_OCCURRENCE_RULESET_VERSION,
        "display_allowed": True,
    }


def _comment_with_occurrences(sample: dict[str, Any], occurrences: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "id": sample["id"],
        "content": sample["content"],
        "rating": sample.get("rating") or 3,
        "category": "outdoor",
        "sub_category": "waders",
        "aspects_json": {
            "customer_label_occurrence_schema_version": CUSTOMER_LABEL_OCCURRENCE_SCHEMA_VERSION,
            "customer_label_occurrence_ruleset_version": CUSTOMER_LABEL_OCCURRENCE_RULESET_VERSION,
            "sub_category": "waders",
            "customer_label_occurrences": occurrences,
        },
    }


def _current_shadow_metrics(payload: dict[str, Any]) -> tuple[dict[str, dict[str, int]], dict[str, dict[str, int]]]:
    totals: dict[str, Counter[str]] = {"issue": Counter(), "highlight": Counter()}
    focus: dict[str, Counter[str]] = defaultdict(Counter)
    for label_type, canonical in FOCUS_WADERS_LABELS:
        focus.setdefault(f"{label_type}:{canonical}", Counter())

    for sample in payload["samples"]:
        actual = display_keys_from_shadow(run_customer_label_v2_shadow(_review(sample)))
        expected = {
            "issue": list(sample["expected_issue_keys"]),
            "highlight": list(sample["expected_highlight_keys"]),
        }
        for label_type in ("issue", "highlight"):
            actual_set = set(actual[label_type])
            expected_set = set(expected[label_type])
            totals[label_type]["tp"] += len(actual_set & expected_set)
            totals[label_type]["fp"] += len(actual_set - expected_set)
            totals[label_type]["fn"] += len(expected_set - actual_set)
            totals[label_type]["exact_set"] += int(actual_set == expected_set)
            for canonical in actual_set | expected_set:
                key = f"{label_type}:{canonical}"
                focus[key]["tp"] += int(canonical in actual_set and canonical in expected_set)
                focus[key]["fp"] += int(canonical in actual_set and canonical not in expected_set)
                focus[key]["fn"] += int(canonical not in actual_set and canonical in expected_set)

    normalized_focus = {
        key: {
            "tp": int(counter.get("tp", 0)),
            "fp": int(counter.get("fp", 0)),
            "fn": int(counter.get("fn", 0)),
        }
        for key, counter in sorted(focus.items())
    }
    return ({label_type: dict(counter) for label_type, counter in totals.items()}, normalized_focus)


def test_waders_351_400_fixture_schema_and_evidence_locatable() -> None:
    payload = _fixture_payload()
    assert payload["review_count"] == 50
    assert len(payload["samples"]) == 50
    assert len(payload["fixture_validation_errors"]) == payload["expected_summary"]["fixture_validation_error_count"]

    required = {
        "id",
        "content",
        "rating",
        "human_issue_labels_zh",
        "human_highlight_labels_zh",
        "expected_issue_keys",
        "expected_highlight_keys",
        "evidence_spans",
        "needs_new_label",
        "blocked_issue_keys",
        "blocked_highlight_keys",
        "notes",
    }
    for sample in payload["samples"]:
        assert required <= sample.keys(), sample["id"]
        content = sample["content"]
        expected_by_type = {
            "issue": set(sample["expected_issue_keys"]),
            "highlight": set(sample["expected_highlight_keys"]),
        }
        evidence_by_type: dict[str, set[str]] = {"issue": set(), "highlight": set()}
        for group in sample["evidence_spans"]:
            label_type = group["label_type"]
            canonical = group["canonical_label_key"]
            evidence_by_type[label_type].add(canonical)
            assert canonical in expected_by_type[label_type], sample["id"]
            assert group["evidence_spans"], (sample["id"], canonical)
            for span in group["evidence_spans"]:
                start = span["evidence_start"]
                end = span["evidence_end"]
                evidence = span["evidence_span"]
                assert start >= 0 and end > start, (sample["id"], canonical, evidence)
                assert content[start:end] == evidence, (sample["id"], canonical, evidence)
        assert expected_by_type["issue"] <= evidence_by_type["issue"], sample["id"]
        assert expected_by_type["highlight"] <= evidence_by_type["highlight"], sample["id"]

        for item in sample["needs_new_label"]:
            assert str(item["canonical_label_key"]).startswith("candidate:"), sample["id"]
            assert item["review_status"] == "needs_new_label", sample["id"]
            for span in item["evidence_spans"]:
                start = span["evidence_start"]
                end = span["evidence_end"]
                assert content[start:end] == span["evidence_span"], (sample["id"], item["raw_label_zh"])

    for error in payload["fixture_validation_errors"]:
        assert {"review_id", "source_no", "raw_label_zh", "error"} <= error.keys()
        assert error["error"] == "manual_column_label_without_locatable_evidence_or_annotation"


def test_waders_351_400_current_shadow_summary_matches_recorded_gold_diff() -> None:
    payload = _fixture_payload()
    totals, _focus = _current_shadow_metrics(payload)
    expected = payload["expected_summary"]["current_shadow_after_step4_6"]

    assert totals == {
        "issue": expected["issue"],
        "highlight": expected["highlight"],
    }


def test_waders_351_400_focus_labels_have_zero_fp_fn() -> None:
    payload = _fixture_payload()
    _totals, focus = _current_shadow_metrics(payload)
    expected_focus = payload["expected_summary"]["current_shadow_after_step4_6"]["focus_label_metrics"]

    for label_type, canonical in sorted(FOCUS_WADERS_LABELS):
        key = f"{label_type}:{canonical}"
        assert focus[key] == expected_focus[key]
        assert focus[key].get("fp", 0) == 0
        assert focus[key].get("fn", 0) == 0


def test_waders_351_400_duplicate_labels_dedupe_but_keep_verified_evidence() -> None:
    payload = _fixture_payload()
    sample = next(item for item in payload["samples"] if item["id"] == "waders-351-400-row-371")
    overall_group = next(
        item for item in sample["evidence_spans"] if item["canonical_label_key"] == "overall_satisfied"
    )
    occurrences = [
        _content_occurrence(sample, overall_group, span, payload["display_meta"])
        for span in overall_group["evidence_spans"]
    ]
    comment = _comment_with_occurrences(sample, occurrences)

    assert customer_highlight_tags_for_comment(comment, locale="en").count("Overall Satisfied") == 1
    projected = [
        item
        for item in iter_customer_highlight_occurrences(comment, locale="en")
        if item.get("canonical_highlight_key") == "overall_satisfied"
        and item.get("source_review_allowed")
        and item.get("verified_evidence")
    ]
    projected_spans = {item["evidence_span"] for item in projected}
    expected_spans = {span["evidence_span"] for span in overall_group["evidence_spans"]}
    assert expected_spans <= projected_spans

    rows = build_customer_highlight_rows([comment], locale="en", limit=20)
    overall_row = next(row for row in rows if row["canonical_highlight_key"] == "overall_satisfied")
    assert expected_spans <= set(overall_row["evidence_spans"])
    assert overall_row["mention_count"] == 1
    assert overall_row["raw_occurrence_count"] >= 2


def test_waders_351_400_needs_new_labels_enter_candidate_pool_only() -> None:
    payload = _fixture_payload()
    shadow_results: list[dict[str, Any]] = []
    for sample in payload["samples"]:
        for item in sample["needs_new_label"]:
            result = run_customer_label_v2_shadow(
                _review(sample),
                label_candidates=[_candidate_from_new_label(item)],
            )
            actual = display_keys_from_shadow(result)
            assert actual == {"issue": [], "highlight": []}, (sample["id"], item["raw_label_zh"])
            assert len(result["candidate_pool_items"]) == 1, (sample["id"], item["raw_label_zh"])
            pool_item = result["candidate_pool_items"][0]
            assert pool_item["canonical_label_key"] == item["canonical_label_key"]
            assert "unknown_label" in pool_item["downgrade_reasons"]
            shadow_results.append(result)

    assert len(shadow_results) == payload["expected_summary"]["needs_new_label_count"]
    artifact = build_candidate_pool_artifact(
        shadow_results,
        scope="5.9.9 Step 4.6 waders 351-400 human gold needs-new-label focused test",
        source_artifacts=[str(FIXTURE_PATH)],
    )
    assert artifact["raw_item_count"] == payload["expected_summary"]["needs_new_label_count"]
    assert artifact["item_count"] == payload["expected_summary"]["needs_new_label_count"]
    assert artifact["safety"]["production_db_write"] is False
    assert artifact["safety"]["llm_called"] is False
    assert artifact["safety"]["frontstage_replaced"] is False

    review_actions = [
        {
            "candidate_id": item["candidate_id"],
            "action": "needs_new_label",
            "raw_label": item["raw_label"],
            "reviewer": "step4.6-human-gold-focused-test",
            "note": "Catalog backlog only; do not display without maturity/verifier support.",
        }
        for item in artifact["candidate_pool_items"]
    ]
    reviewed = build_reviewed_candidate_pool_artifact(artifact, review_actions)
    assert reviewed["status"] == "PASS"
    assert reviewed["review_action_summary"]["status_counts"] == {
        "needs_new_label": payload["expected_summary"]["needs_new_label_count"]
    }
    assert all(
        item["review_status"] == "needs_new_label"
        for item in reviewed["reviewed_candidate_pool_items"]
    )


def test_waders_351_400_wrong_context_guards_still_hold() -> None:
    def candidate(label_type: str, canonical: str, evidence: str, aspect_key: str) -> dict[str, Any]:
        return {
            "label_type": label_type,
            "canonical_label_key": canonical,
            "raw_label": canonical,
            "display_label_en": canonical,
            "display_label_zh": canonical,
            "aspect_key": aspect_key,
            "polarity": "negative" if label_type == "issue" else "positive",
            "evidence_candidate": evidence,
            "confidence": 0.9,
            "reason": "waders 351-400 focused guard fixture",
        }

    old_product = run_customer_label_v2_shadow(
        {
            "id": "waders-351-400-old-product-leak",
            "content": (
                "Bought as a gift for my boyfriend who has had numerous pairs of waders in the past that have "
                "leaked. These were affordable and have not caused him any issues."
            ),
            "category": "outdoor",
            "sub_category": "waders",
        },
        label_candidates=[candidate("issue", "water_leaks_through", "leaked", "waterproof")],
    )
    assert display_keys_from_shadow(old_product) == {"issue": [], "highlight": []}
    assert "source_review_blocked" in old_product["audit_occurrences"][0]["downgrade_reasons"]

    accessory = run_customer_label_v2_shadow(
        {
            "id": "waders-351-400-accessory-phone-case-leak",
            "content": (
                "The waders are fine. However, the waterproof phone case is not at all what it shows as. "
                "It is not waterproof; water leaks in very easily."
            ),
            "category": "outdoor",
            "sub_category": "waders",
        },
        label_candidates=[
            candidate("issue", "water_leaks_through", "It is not waterproof", "waterproof"),
            candidate(
                "issue",
                "pocket_not_waterproof",
                "the waterproof phone case is not at all what it shows as",
                "accessory_storage",
            ),
        ],
    )
    assert display_keys_from_shadow(accessory) == {
        "issue": ["pocket_not_waterproof"],
        "highlight": [],
    }
    accessory_reasons = {
        item["canonical_label_key"]: set(item["downgrade_reasons"])
        for item in accessory["audit_occurrences"]
    }
    assert "source_review_blocked" in accessory_reasons["water_leaks_through"]

    not_used = run_customer_label_v2_shadow(
        {
            "id": "waders-351-400-not-tested-waterproof",
            "content": "Not tested in water yet, but they look waterproof.",
            "category": "outdoor",
            "sub_category": "waders",
        },
        label_candidates=[candidate("highlight", "keeps_water_out", "look waterproof", "waterproof")],
    )
    assert display_keys_from_shadow(not_used) == {"issue": [], "highlight": []}
    assert "context_blocked" in not_used["audit_occurrences"][0]["downgrade_reasons"]
