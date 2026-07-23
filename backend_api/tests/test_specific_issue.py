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


def test_legacy_issue_rows_are_marked_as_legacy_not_specific_issue_schema() -> None:
    rows = build_specific_issue_rows(
        [
            {
                "id": 1,
                "content": "The battery does not last long.",
                "issue_tag": "Battery Life",
                "aspects_json": None,
            }
        ],
        locale="en",
    )

    assert len(rows) == 1
    assert rows[0]["specific_issue"] == "Battery Life"
    assert rows[0]["legacy_fallback"] is True
    assert rows[0]["is_specific_issue"] is False
    assert rows[0]["specific_issue_schema_version"] == ""
    assert rows[0]["representative_comments"] == ["The battery does not last long."]


def test_specific_issue_dimension_uses_requested_locale_for_known_aspect_key() -> None:
    occurrences = iter_specific_issue_occurrences(
        {
            "id": 1,
            "content": "The product box was damaged.",
            "aspects_json": {
                "specific_issue_schema_version": SPECIFIC_ISSUE_SCHEMA_VERSION,
                "sub_category": "home",
                "aspects": [
                    {
                        "key": "shipping_damage",
                        "aspect_label": "运输损坏",
                        "polarity": "negative",
                        "specific_issue": "Arrived Damaged",
                        "canonical_issue_key": "arrived_damaged",
                        "issue_confidence": "high",
                        "display_allowed": True,
                        "evidence_span": "box was damaged",
                    }
                ],
            },
        },
        locale="en",
    )

    assert occurrences[0]["dimension"] == "Shipping Damage"


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


def test_old_aspects_without_specific_issue_payload_use_legacy_issue_tag_not_rule_issue() -> None:
    occurrences = iter_specific_issue_occurrences(
        {
            "id": 1,
            "content": "The product box arrived damaged.",
            "issue_tag": "Packaging",
            "aspects_json": {
                "sub_category": "home",
                "aspects": [
                    {
                        "key": "shipping_damage",
                        "aspect_label": "运输损坏",
                        "polarity": "negative",
                        "evidence_span": "arrived damaged",
                    }
                ],
            },
        },
        locale="en",
    )

    assert len(occurrences) == 1
    assert occurrences[0]["specific_issue"] == "Packaging"
    assert occurrences[0]["issue_source"] == "legacy_issue_tag"
    assert occurrences[0]["legacy_fallback"] is True


def test_build_specific_issue_rows_groups_by_subcategory_and_canonical_issue_for_display() -> None:
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
            "id": 4,
            "content": "Water seeped into the pocket and soaked my gear.",
            "sentiment": "negative",
            "aspects_json": {
                "specific_issue_schema_version": SPECIFIC_ISSUE_SCHEMA_VERSION,
                "sub_category": "outdoor",
                "aspects": [
                    {
                        "key": "capacity",
                        "aspect_label": "Capacity",
                        "polarity": "negative",
                        "specific_issue": "Pocket Not Waterproof",
                        "canonical_issue_key": "pocket_not_waterproof",
                        "issue_confidence": "high",
                        "display_allowed": True,
                        "evidence_span": "Water seeped into the pocket",
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
    assert outdoor["count"] == 3
    assert outdoor["pct"] == 75.0
    assert outdoor["aspect_key"] == "accessory_storage"
    assert outdoor["aspect_keys"] == ["accessory_storage", "capacity"]
    assert outdoor["dimension"] == "Accessories & Storage, Capacity"
    assert outdoor["dimensions"] == ["Accessories & Storage", "Capacity"]
    assert outdoor["canonical_issue_key"] == "pocket_not_waterproof"
    assert outdoor["representative_comments"] == [
        "The pocket got wet in light rain.",
        "Water seeped into the pocket and soaked my gear.",
    ]
    assert travel["count"] == 1


def test_build_specific_issue_rows_counts_same_canonical_once_per_comment_across_dimensions() -> None:
    comments = [
        {
            "id": 1,
            "content": "The material was hot and not breathable. It was stiff and not breathable while walking.",
            "sentiment": "negative",
            "aspects_json": {
                "specific_issue_schema_version": SPECIFIC_ISSUE_SCHEMA_VERSION,
                "sub_category": "apparel",
                "aspects": [
                    {
                        "key": "breathability",
                        "aspect_label": "Breathability",
                        "polarity": "negative",
                        "specific_issue": "Not Breathable",
                        "canonical_issue_key": "not_breathable",
                        "issue_confidence": "high",
                        "display_allowed": True,
                        "evidence_span": "hot and not breathable",
                    },
                    {
                        "key": "mobility",
                        "aspect_label": "Mobility",
                        "polarity": "negative",
                        "specific_issue": "Not Breathable",
                        "canonical_issue_key": "not_breathable",
                        "issue_confidence": "medium",
                        "display_allowed": True,
                        "evidence_span": "not breathable while walking",
                    },
                ],
            },
        },
        {
            "id": 2,
            "content": "The boot runs too small and the boot foot is tight.",
            "sentiment": "negative",
            "aspects_json": {
                "specific_issue_schema_version": SPECIFIC_ISSUE_SCHEMA_VERSION,
                "sub_category": "apparel",
                "aspects": [
                    {
                        "key": "size_fit",
                        "aspect_label": "Size & Fit",
                        "polarity": "negative",
                        "specific_issue": "Runs Too Small",
                        "canonical_issue_key": "runs_too_small",
                        "issue_confidence": "high",
                        "display_allowed": True,
                        "evidence_span": "runs too small",
                    },
                    {
                        "key": "boot_fit",
                        "aspect_label": "Boot Fit",
                        "polarity": "negative",
                        "specific_issue": "Runs Too Small",
                        "canonical_issue_key": "runs_too_small",
                        "issue_confidence": "high",
                        "display_allowed": True,
                        "evidence_span": "boot foot is tight",
                    },
                ],
            },
        },
    ]

    rows = build_specific_issue_rows(comments, locale="en", limit=10)

    assert len(rows) == 2
    breathable = next(row for row in rows if row["canonical_issue_key"] == "not_breathable")
    runs_small = next(row for row in rows if row["canonical_issue_key"] == "runs_too_small")
    assert breathable["count"] == 1
    assert breathable["pct"] == 50.0
    assert breathable["aspect_keys"] == ["breathability", "mobility"]
    assert breathable["dimension"] == "Breathability, Mobility"
    assert breathable["representative_comments"] == [
        "The material was hot and not breathable. It was stiff and not breathable while walking."
    ]
    assert runs_small["count"] == 1
    assert runs_small["aspect_keys"] == ["size_fit", "boot_fit"]
    assert runs_small["dimension"] == "Size & Fit, Boot Fit"
