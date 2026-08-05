from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

from backend_api.app.services.review_fragment_candidate_multimodule import (
    APPROVED_HIGHLIGHT_KEYS,
    APPROVED_ISSUE_KEYS,
    COMPATIBILITY_INPUT_MODULES,
    FINAL_ARTIFACT_MODULES,
    REVIEW_FRAGMENT_CANDIDATE_FIXTURE_SCHEMA_VERSION,
    REVIEW_FRAGMENT_CANDIDATE_MULTIMODULE_VERSION,
    build_review_fragment_candidate_artifact,
    review_fragment_module_enum_matrix,
    validate_review_fragment_candidate_artifact,
    validate_review_fragment_candidate_artifact_row,
    validate_review_fragment_module_enum_consistency,
)
from backend_api.app.services.review_fragment_contract import REVIEW_FRAGMENT_REQUIRED_FIELDS, validate_review_fragment

ROOT = Path(__file__).resolve().parent.parent.parent
FIXTURE_PATH = Path(__file__).parent / "fixtures" / "review_fragment_candidate_5_9_4_samples.json"
WADERS_TAXONOMY_PATH = ROOT / "data" / "taxonomy" / "v1.0" / "outdoor" / "waders.yaml"


def _load_fixture() -> dict[str, Any]:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def _load_taxonomy_aspects(path: Path) -> list[dict[str, Any]]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return [
        {
            "key": item["key"],
            "label_zh": item.get("label_zh", ""),
            "boundary_note": item.get("boundary_note", ""),
        }
        for item in data["aspects"]
    ]


def _fixture_resolver(sub_category: str) -> tuple[list[dict[str, Any]], bool]:
    if sub_category == "waders":
        return _load_taxonomy_aspects(WADERS_TAXONOMY_PATH), True
    return [{"key": "waterproof", "label_zh": "fallback bait"}], False


def _artifact() -> dict[str, Any]:
    fixture = _load_fixture()
    return build_review_fragment_candidate_artifact(fixture["samples"], aspect_resolver=_fixture_resolver)


def _summary(rows: list[dict[str, Any]], fields: tuple[str, ...]) -> list[dict[str, Any]]:
    return [{field: row[field] for field in fields} for row in rows]


def _row(rows: list[dict[str, Any]], *, module: str, normalized_label: str) -> dict[str, Any]:
    for row in rows:
        if row["module"] == module and row["normalized_label"] == normalized_label:
            return row
    raise AssertionError(f"missing row: {module}/{normalized_label}")


def test_review_fragment_candidate_fixture_matches_expected_artifact_summary() -> None:
    fixture = _load_fixture()
    artifact = build_review_fragment_candidate_artifact(fixture["samples"], aspect_resolver=_fixture_resolver)

    assert fixture["schema_version"] == REVIEW_FRAGMENT_CANDIDATE_FIXTURE_SCHEMA_VERSION
    assert fixture["candidate_version"] == REVIEW_FRAGMENT_CANDIDATE_MULTIMODULE_VERSION
    assert len(fixture["samples"]) == 11
    assert validate_review_fragment_module_enum_consistency() == []
    assert validate_review_fragment_candidate_artifact(artifact) == []
    assert {
        "use case and people signals route to consumer_profile",
        "purchase reason routes to purchase_motive",
        "expectation gap routes to unmet_need candidate-first",
        "approved seller-action labels promote from candidate or legacy routing",
        "water leak samples aggregate by one issue_key across taxonomy aspects",
        "formal taxonomy whitelist labels stay out of candidate artifact",
        "candidate and other retain evidence while can_aggregate=false",
        "non-product issue/highlight snippets do not become customer issue/customer label",
        "customer service response promotes from audit routing into formal seller issue",
        "positive customer service response routes to product_highlight",
    } <= set(fixture["coverage"])

    for sample in fixture["samples"]:
        for fragment in sample["fragments"]:
            assert set(fragment) == set(REVIEW_FRAGMENT_REQUIRED_FIELDS)
            assert validate_review_fragment(fragment) == []

    expected = fixture["expected_artifact_summary"]
    assert artifact["candidate_version"] == REVIEW_FRAGMENT_CANDIDATE_MULTIMODULE_VERSION
    assert _summary(
        artifact["formal_top10_rows"],
        ("module", "normalized_label", "count", "can_aggregate", "formal_top10_eligible"),
    ) == expected["formal_top10_rows"]
    assert _summary(
        artifact["module_seed_rows"],
        ("module", "seed_module", "normalized_label", "count", "can_aggregate", "formal_top10_eligible"),
    ) == expected["module_seed_rows"]
    assert _summary(
        artifact["candidate_rows"],
        ("module", "normalized_label", "reason", "count", "can_aggregate"),
    ) == expected["candidate_rows"]
    assert _summary(
        artifact["audit_rows"],
        ("module", "normalized_label", "reason", "count", "can_aggregate"),
    ) == expected["audit_rows"]


def test_module_enum_matrix_keeps_legacy_values_as_compatibility_input_only() -> None:
    matrix = review_fragment_module_enum_matrix()

    assert matrix["validation_errors"] == []
    assert set(matrix["final_artifact_modules"]) == {
        "product_issue",
        "product_highlight",
        "consumer_profile",
        "purchase_motive",
        "unmet_need",
        "audit_filter",
    }
    assert {
        "accessory_or_bundle",
        "logistics_support",
        "comparison_or_other_product",
        "other_candidate",
        "customer_service",
    } <= set(matrix["compatibility_input_modules"])
    assert set(matrix["compatibility_input_modules"]).isdisjoint(matrix["final_artifact_modules"])


def test_artifact_rows_include_reject_reason_and_never_emit_legacy_modules() -> None:
    artifact = _artifact()
    legacy_modules = set(COMPATIBILITY_INPUT_MODULES)

    for bucket in ("formal_top10_rows", "module_seed_rows", "candidate_rows", "audit_rows"):
        for row in artifact[bucket]:
            assert row["module"] in FINAL_ARTIFACT_MODULES
            assert row["module"] not in legacy_modules
            assert "reject_reason" in row
            if row["can_aggregate"] is True:
                assert row["reject_reason"] is None
            else:
                assert row["reject_reason"] == row["reason"]


def test_artifact_row_validator_rejects_inconsistent_seller_keys_and_modules() -> None:
    valid_water_leak = _row(_artifact()["formal_top10_rows"], module="product_issue", normalized_label="water_leaks_through")

    leaked_module = {**valid_water_leak, "module": "customer_service"}
    assert {"module_invalid", "compatibility_module_leaked"} <= set(
        validate_review_fragment_candidate_artifact_row(leaked_module, bucket="formal")
    )

    highlight_with_action_key = {
        **_row(_artifact()["formal_top10_rows"], module="product_highlight", normalized_label="keeps_water_out"),
        "action_label_key": "waterproof",
    }
    assert "action_label_key_without_issue" in validate_review_fragment_candidate_artifact_row(
        highlight_with_action_key,
        bucket="formal",
    )


def test_validation_failure_degrades_to_audit_without_blocking_batch() -> None:
    bad_sample = {
        "id": "bad-polarity-local-degrade",
        "category": "outdoor",
        "sub_category": "waders",
        "content": "The waders stayed dry.",
        "fragments": [
            {
                "fragment_text": "The waders stayed dry",
                "module": "product_highlight",
                "aspect_key": "waterproof",
                "polarity": "surprised",
                "evidence_span": "waders stayed dry",
                "confidence": 0.91,
                "current_product_scope": "current_product",
                "can_aggregate": True,
                "reject_reason": None,
            }
        ],
    }

    artifact = build_review_fragment_candidate_artifact([bad_sample], aspect_resolver=_fixture_resolver)

    assert artifact["formal_top10_rows"] == []
    assert artifact["candidate_rows"] == []
    assert artifact["module_seed_rows"] == []
    assert len(artifact["audit_rows"]) == 1
    audit = artifact["audit_rows"][0]
    assert audit["module"] == "audit_filter"
    assert audit["reason"] == "schema_invalid"
    assert audit["reject_reason"] == "schema_invalid"
    assert audit["can_aggregate"] is False
    assert audit["degraded_from_bucket"] == "formal"
    assert "polarity_invalid" in audit["validation_errors"]
    assert validate_review_fragment_candidate_artifact(artifact) == []


def test_use_case_and_people_route_to_consumer_profile_not_product_highlight() -> None:
    artifact = _artifact()
    module_rows = artifact["module_seed_rows"]
    formal_rows = artifact["formal_top10_rows"]
    candidate_rows = artifact["candidate_rows"]

    family = _row(module_rows, module="consumer_profile", normalized_label="family_buyer")
    fishing = _row(module_rows, module="consumer_profile", normalized_label="fishing")

    assert family["seed_module"] == "consumer_profile"
    assert family["count"] == 2
    assert fishing["seed_module"] == "use_case"
    assert fishing["evidence_span"] == "fly fishing"
    assert fishing["formal_top10_eligible"] is False
    assert not any(row["normalized_label"] == "works_well_for_use_case" for row in formal_rows)
    assert not any(row["normalized_label"] == "works_well_for_use_case" for row in candidate_rows)


def test_purchase_reason_routes_to_purchase_motive_seed_taxonomy() -> None:
    artifact = _artifact()
    motives = [
        row["normalized_label"]
        for row in artifact["module_seed_rows"]
        if row["module"] == "purchase_motive"
    ]

    assert motives == ["price_value", "replacement"]
    assert all(row["formal_top10_eligible"] is False for row in artifact["module_seed_rows"])


def test_unmet_need_is_candidate_first_with_evidence() -> None:
    artifact = _artifact()
    unmet_need = _row(artifact["candidate_rows"], module="unmet_need", normalized_label="built_in_fish_ruler")

    assert unmet_need["reason"] == "unmet_need_candidate_first"
    assert unmet_need["evidence_span"] == "built-in fish ruler"
    assert unmet_need["can_aggregate"] is False
    assert unmet_need["count"] == 1


def test_approved_issue_mapping_keeps_taxonomy_aspect_separate() -> None:
    artifact = _artifact()
    water_leak = _row(
        artifact["formal_top10_rows"],
        module="product_issue",
        normalized_label="water_leaks_through",
    )

    assert water_leak["issue_key"] == "water_leaks_through"
    assert water_leak["highlight_key"] is None
    assert water_leak["action_label_key"] == "improve_waterproofing"
    assert water_leak["aspect_key"] == "water_leaks_through"
    assert set(water_leak["aspect_keys"]) == {"water_leaks_through"}
    assert water_leak["count"] == 2
    assert water_leak["display_label_en"] == "Water Leaks Through"
    assert water_leak["display_label_zh"] == "容易进水"
    assert all(
        row["aspect_key"] != "water_leaks_through"
        for bucket in ("candidate_rows", "audit_rows")
        for row in artifact[bucket]
    )


def test_negative_waterproof_aspect_is_not_used_as_leak_identity() -> None:
    artifact = _artifact()
    assert not any(
        row["polarity"] in {"negative", "mixed"} and row["aspect_key"] == "waterproof"
        for row in artifact["formal_top10_rows"]
    )
    assert not any(
        row["issue_key"] == "water_leaks_through" and "waterproof" in row["aspect_keys"]
        for row in artifact["formal_top10_rows"]
    )


def test_customer_service_response_promotes_to_formal_seller_issue() -> None:
    artifact = _artifact()
    service = _row(
        artifact["formal_top10_rows"],
        module="product_issue",
        normalized_label="customer_service_unresponsive",
    )

    assert service["aspect_key"] == "customer_service"
    assert service["issue_key"] == "customer_service_unresponsive"
    assert service["highlight_key"] is None
    assert service["action_label_key"] == "improve_customer_service_response"
    assert service["formal_top10_eligible"] is True
    assert service["evidence_span"] == "refund request"
    assert service["representative_comments"] == ["Customer service never answered my refund request."]
    assert artifact["audit_rows"] == []


def test_positive_customer_service_routes_to_product_highlight() -> None:
    artifact = _artifact()
    service = _row(
        artifact["formal_top10_rows"],
        module="product_highlight",
        normalized_label="customer_service_helpful",
    )

    assert service["highlight_key"] == "customer_service_helpful"
    assert service["issue_key"] is None
    assert service["action_label_key"] is None
    assert service["aspect_key"] == "customer_service"
    assert service["formal_top10_eligible"] is True


def test_approved_issue_mapping_keeps_taxonomy_aspect_separate_for_existing_issue() -> None:
    artifact = _artifact()
    water_leak = _row(
        artifact["formal_top10_rows"],
        module="product_issue",
        normalized_label="water_leaks_through",
    )

    assert water_leak["issue_key"] == "water_leaks_through"
    assert water_leak["action_label_key"] == "improve_waterproofing"
    assert water_leak["aspect_key"] == "water_leaks_through"


def test_approved_accessory_size_and_shipping_issues_are_formal() -> None:
    artifact = _artifact()
    formal_issue_keys = {
        row["issue_key"]
        for row in artifact["formal_top10_rows"]
        if row["issue_key"]
    }

    assert formal_issue_keys == set(APPROVED_ISSUE_KEYS)
    assert _row(
        artifact["formal_top10_rows"],
        module="product_issue",
        normalized_label="accessory_leak",
    )["aspect_key"] == "accessory_storage"
    assert _row(
        artifact["formal_top10_rows"],
        module="product_issue",
        normalized_label="missing_accessory",
    )["aspect_key"] == "accessory_storage"
    assert _row(
        artifact["formal_top10_rows"],
        module="product_issue",
        normalized_label="confusing_size_chart",
    )["aspect_key"] == "size_fit"
    assert _row(
        artifact["formal_top10_rows"],
        module="product_issue",
        normalized_label="late_shipping",
    )["aspect_key"] == "shipping_damage"

    for bucket in ("candidate_rows", "audit_rows"):
        assert not {
            row["issue_key"] or row["action_label_key"] or row["normalized_label"]
            for row in artifact[bucket]
        } & APPROVED_ISSUE_KEYS


def test_candidate_and_other_rows_keep_evidence_but_never_enter_formal_top10() -> None:
    artifact = _artifact()
    formal_keys = {(row["module"], row["normalized_label"]) for row in artifact["formal_top10_rows"]}

    assert artifact["candidate_rows"]
    for row in artifact["candidate_rows"]:
        assert row["evidence_span"]
        assert row["representative_comments"]
        assert row["can_aggregate"] is False
        assert row["issue_key"] is None
        assert row["action_label_key"] is None
        assert (row["module"], row["normalized_label"]) not in formal_keys

    unmet_need = _row(
        artifact["candidate_rows"],
        module="unmet_need",
        normalized_label="built_in_fish_ruler",
    )
    assert unmet_need["evidence_span"] == "built-in fish ruler"
    assert unmet_need["reason"] == "unmet_need_candidate_first"


def test_non_product_issue_or_highlight_snippets_are_not_forced_into_product_labels() -> None:
    artifact = _artifact()
    assert any(row["issue_key"] == "late_shipping" for row in artifact["formal_top10_rows"])
    assert any(
        row["module"] == "product_issue" and row["normalized_label"] == "customer_service_unresponsive"
        for row in artifact["formal_top10_rows"]
    )


def test_formal_rows_use_only_final_business_modules() -> None:
    artifact = _artifact()
    formal_modules = {row["module"] for row in artifact["formal_top10_rows"]}
    assert formal_modules <= {"product_issue", "product_highlight"}
    assert all(row["module"] in {"consumer_profile", "purchase_motive", "unmet_need", "audit_filter"}
               for bucket in ("module_seed_rows", "candidate_rows", "audit_rows")
               for row in artifact[bucket] if row["module"] not in {"product_issue", "product_highlight"})
    assert "customer_service_helpful" in APPROVED_HIGHLIGHT_KEYS


def test_formal_highlights_use_action_label_mapping() -> None:
    artifact = _artifact()
    waterproof = _row(artifact["formal_top10_rows"], module="product_highlight", normalized_label="keeps_water_out")

    assert waterproof["aspect_key"] == "waterproof"
    assert waterproof["issue_key"] is None
    assert waterproof["highlight_key"] == "keeps_water_out"
    assert waterproof["action_label_key"] is None
    assert waterproof["display_label_en"] == "Keeps Water Out"
    assert waterproof["display_label_zh"] == "保持干燥"
