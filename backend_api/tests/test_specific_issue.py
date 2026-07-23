from __future__ import annotations

from backend_api.app.services.specific_issue import (
    ISSUE_RULESET_VERSION,
    SPECIFIC_ISSUE_SCHEMA_VERSION,
    build_specific_issue_rows,
    enrich_aspects_json,
    iter_specific_issue_occurrences,
)


def test_enrich_aspects_json_adds_rule_based_specific_issue_metadata() -> None:
    enriched = enrich_aspects_json(
        {
            "aspects": [
                {
                    "key": "waterproof_performance",
                    "polarity": "negative",
                    "evidence_span": "not waterproof",
                }
            ]
        },
        sub_category="outdoor",
        content="The bag is not waterproof and water gets in.",
        locale="en",
    )

    assert enriched is not None
    aspect = enriched["aspects"][0]
    assert enriched["specific_issue_schema_version"] == SPECIFIC_ISSUE_SCHEMA_VERSION
    assert enriched["issue_ruleset_version"] == ISSUE_RULESET_VERSION
    assert aspect["specific_issue"] == "Water Leaks Through"
    assert aspect["canonical_issue_key"] == "water_leaks_through"
    assert aspect["display_allowed"] is True
    assert aspect["issue_confidence"] == "high"


def test_iter_specific_issue_occurrences_filters_broad_new_schema_without_legacy_fallback() -> None:
    enriched = enrich_aspects_json(
        {
            "aspects": [
                {
                    "key": "durability",
                    "polarity": "negative",
                    "evidence_span": "could be better",
                }
            ]
        },
        sub_category="outdoor",
        content="Durability could be better.",
        locale="en",
    )

    occurrences = iter_specific_issue_occurrences(
        {
            "id": 1,
            "content": "Durability could be better.",
            "issue_tag": "Durability",
            "aspects_json": enriched,
        }
    )

    assert occurrences == []


def test_iter_specific_issue_occurrences_uses_legacy_issue_tag_for_old_session() -> None:
    occurrences = iter_specific_issue_occurrences(
        {
            "id": 1,
            "content": "The zipper broke after one use.",
            "issue_tag": "Zipper Quality",
            "aspects_json": None,
        }
    )

    assert len(occurrences) == 1
    assert occurrences[0]["specific_issue"] == "Zipper Quality"
    assert occurrences[0]["canonical_issue_key"] == "zipper_quality"
    assert occurrences[0]["aspect_key"] == ""
    assert occurrences[0]["legacy_fallback"] is True


def test_legacy_issue_tags_keep_non_ascii_labels_distinct() -> None:
    rows = build_specific_issue_rows(
        [
            {
                "id": 1,
                "content": "Water leaked through.",
                "issue_tag": "\u6f0f\u6c34",
                "aspects_json": None,
            },
            {
                "id": 2,
                "content": "The size was too small.",
                "issue_tag": "\u5c3a\u5bf8\u592a\u5c0f",
                "aspects_json": None,
            },
        ],
        locale="zh",
        limit=10,
    )

    assert {row["specific_issue"] for row in rows} == {"\u6f0f\u6c34", "\u5c3a\u5bf8\u592a\u5c0f"}
    assert {row["canonical_issue_key"] for row in rows} == {"\u6f0f\u6c34", "\u5c3a\u5bf8\u592a\u5c0f"}


def test_specific_issue_payload_without_schema_does_not_legacy_fallback_broad_issue() -> None:
    occurrences = iter_specific_issue_occurrences(
        {
            "id": 1,
            "content": "Durability could be better.",
            "issue_tag": "Durability",
            "aspects_json": {
                "aspects": [
                    {
                        "key": "durability",
                        "polarity": "negative",
                        "specific_issue": "Durability Issue",
                        "canonical_issue_key": "durability_issue",
                        "issue_source": "broad_fallback",
                        "display_allowed": False,
                    }
                ]
            },
        }
    )

    assert occurrences == []


def test_build_specific_issue_rows_groups_by_subcategory_aspect_and_canonical_issue() -> None:
    comments = [
        {
            "id": 1,
            "content": "The pocket got wet in light rain.",
            "sentiment": "negative",
            "aspects_json": {
                "specific_issue_schema_version": SPECIFIC_ISSUE_SCHEMA_VERSION,
                "sub_category": "outdoor",
                "aspects": [
                    {
                        "key": "accessory_storage",
                        "aspect_label": "Accessory Storage",
                        "polarity": "negative",
                        "specific_issue": "Pocket Not Waterproof",
                        "canonical_issue_key": "pocket_not_waterproof",
                        "issue_confidence": "high",
                        "display_allowed": True,
                        "evidence_span": "pocket got wet",
                    }
                ],
            },
        },
        {
            "id": 2,
            "content": "The pocket got wet again, but this was copied cluster evidence.",
            "sentiment": "negative",
            "aspects_json": {
                "specific_issue_schema_version": SPECIFIC_ISSUE_SCHEMA_VERSION,
                "sub_category": "outdoor",
                "cluster_propagated": True,
                "aspects": [
                    {
                        "key": "accessory_storage",
                        "aspect_label": "Accessory Storage",
                        "polarity": "negative",
                        "specific_issue": "Pocket Not Waterproof",
                        "canonical_issue_key": "pocket_not_waterproof",
                        "issue_confidence": "medium",
                        "display_allowed": True,
                        "evidence_span": "pocket got wet",
                    }
                ],
            },
        },
        {
            "id": 3,
            "content": "The pocket got wet on the travel pouch.",
            "sentiment": "negative",
            "aspects_json": {
                "specific_issue_schema_version": SPECIFIC_ISSUE_SCHEMA_VERSION,
                "sub_category": "travel",
                "aspects": [
                    {
                        "key": "accessory_storage",
                        "aspect_label": "Accessory Storage",
                        "polarity": "negative",
                        "specific_issue": "Pocket Not Waterproof",
                        "canonical_issue_key": "pocket_not_waterproof",
                        "issue_confidence": "high",
                        "display_allowed": True,
                        "evidence_span": "pocket got wet",
                    }
                ],
            },
        },
    ]

    rows = build_specific_issue_rows(comments, locale="en", limit=10)

    assert len(rows) == 2
    outdoor = next(row for row in rows if row["sub_category"] == "outdoor")
    travel = next(row for row in rows if row["sub_category"] == "travel")
    assert outdoor["count"] == 2
    assert outdoor["pct"] == 66.7
    assert outdoor["aspect_key"] == "accessory_storage"
    assert outdoor["canonical_issue_key"] == "pocket_not_waterproof"
    assert outdoor["representative_comments"] == ["The pocket got wet in light rain."]
    assert travel["count"] == 1
