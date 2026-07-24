from __future__ import annotations

from backend_api.app.services.specific_issue import (
    CUSTOMER_LABEL_SCHEMA_VERSION,
    ISSUE_RULESET_VERSION,
    SPECIFIC_ISSUE_SCHEMA_VERSION,
    build_customer_highlight_rows,
    build_specific_issue_rows,
    customer_highlight_tags_for_comment,
    enrich_aspects_json,
    iter_customer_highlight_occurrences,
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
    assert aspect["specific_issue_zh"] == "容易进水"
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


def test_specific_issue_rows_use_requested_locale_for_customer_label() -> None:
    comments = [
        {
            "id": 1,
            "content": "The waders are not waterproof and water gets in.",
            "issue_tag": "Waterproof Performance",
            "aspects_json": enrich_aspects_json(
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
                content="The waders are not waterproof and water gets in.",
                locale="en",
            ),
        }
    ]

    assert build_specific_issue_rows(comments, locale="en")[0]["specific_issue"] == "Water Leaks Through"
    assert build_specific_issue_rows(comments, locale="zh")[0]["specific_issue"] == "容易进水"


def test_specific_issue_recovers_clear_negative_text_from_wrong_positive_polarity() -> None:
    rows = build_specific_issue_rows(
        [
            {
                "id": 1,
                "content": "Used them once and water enters through the boots.",
                "sentiment": "negative",
                "issue_tag": "Waterproof Performance",
                "aspects_json": enrich_aspects_json(
                    {
                        "aspects": [
                            {
                                "key": "waterproof",
                                "polarity": "positive",
                                "evidence_span": "water enters through the boots",
                            }
                        ]
                    },
                    sub_category="outdoor",
                    content="Used them once and water enters through the boots.",
                    locale="en",
                ),
            }
        ],
        locale="en",
    )

    assert len(rows) == 1
    assert rows[0]["specific_issue"] == "Water Leaks Through"
    assert rows[0]["issue_source"] == "sentiment_recovery_rule"
    assert rows[0]["representative_comments"] == ["Used them once and water enters through the boots."]


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


def test_old_aspects_without_specific_issue_payload_filters_broad_legacy_issue_tag() -> None:
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

    assert occurrences == []


def test_enrich_aspects_json_adds_customer_highlight_metadata() -> None:
    enriched = enrich_aspects_json(
        {
            "aspects": [
                {
                    "key": "waterproof",
                    "polarity": "positive",
                    "evidence_span": "kept me dry",
                }
            ]
        },
        sub_category="outdoor",
        content="These waders kept me dry all day with no leaks.",
        locale="en",
    )

    assert enriched is not None
    aspect = enriched["aspects"][0]
    assert enriched["customer_label_schema_version"] == CUSTOMER_LABEL_SCHEMA_VERSION
    assert aspect["customer_highlight"] == "Keeps Water Out"
    assert aspect["customer_highlight_zh"] == "防水可靠"
    assert aspect["canonical_highlight_key"] == "keeps_water_out"
    assert aspect["highlight_display_allowed"] is True


def test_customer_highlight_rows_filter_broad_aspects_and_keep_customer_labels() -> None:
    comments = [
        {
            "id": 1,
            "content": "Great quality for the price.",
            "sentiment": "positive",
            "highlight_tag": "Build Quality",
            "aspects_json": enrich_aspects_json(
                {
                    "aspects": [
                        {
                            "key": "build_quality",
                            "polarity": "positive",
                            "evidence_span": "Great quality",
                        }
                    ]
                },
                sub_category="outdoor",
                content="Great quality for the price.",
                locale="en",
            ),
        },
        {
            "id": 2,
            "content": "Nice product.",
            "sentiment": "positive",
            "highlight_tag": "Other",
            "aspects_json": {
                "customer_label_schema_version": CUSTOMER_LABEL_SCHEMA_VERSION,
                "sub_category": "outdoor",
                "aspects": [
                    {
                        "key": "other",
                        "polarity": "positive",
                        "evidence_span": "Nice product",
                    }
                ],
            },
        },
    ]

    rows = build_customer_highlight_rows(comments, locale="en", limit=10)

    assert len(rows) == 1
    assert rows[0]["customer_highlight"] == "Feels Well Made"
    assert rows[0]["canonical_highlight_key"] == "feels_well_made"
    assert rows[0]["representative_comments"] == ["Great quality for the price."]


def test_customer_highlight_legacy_fallback_is_locale_safe_and_conservative() -> None:
    assert customer_highlight_tags_for_comment(
        {"content": "很好", "highlight_tag": "防水可靠", "aspects_json": None},
        locale="en",
    ) == []
    assert customer_highlight_tags_for_comment(
        {"content": "很好", "highlight_tag": "防水可靠", "aspects_json": None},
        locale="zh",
    ) == ["防水可靠"]
    assert customer_highlight_tags_for_comment(
        {"content": "Great", "highlight_tag": "Build Quality,Good Value for the Price", "aspects_json": None},
        locale="en",
    ) == ["Good Value for the Price"]


def test_iter_customer_highlight_occurrences_derives_for_specific_issue_schema_session() -> None:
    occurrences = iter_customer_highlight_occurrences(
        {
            "id": 1,
            "content": "The boots fit perfect and kept me dry.",
            "highlight_tag": "Boot Fit,Waterproofing",
            "aspects_json": {
                "specific_issue_schema_version": SPECIFIC_ISSUE_SCHEMA_VERSION,
                "sub_category": "outdoor",
                "aspects": [
                    {
                        "key": "boot_fit",
                        "polarity": "positive",
                        "evidence_span": "boots fit perfect",
                    },
                    {
                        "key": "waterproof",
                        "polarity": "positive",
                        "evidence_span": "kept me dry",
                    },
                ],
            },
        },
        locale="en",
    )

    assert [item["customer_highlight"] for item in occurrences] == ["Fits as Expected", "Keeps Water Out"]


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


def test_specific_issue_rows_keep_cluster_propagated_only_rows_with_fallback_comment() -> None:
    content = "The pocket got wet again, but this was copied cluster evidence."
    rows = build_specific_issue_rows(
        [
            {
                "id": 1,
                "content": content,
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
            }
        ],
        locale="en",
        limit=10,
    )

    assert len(rows) == 1
    assert rows[0]["count"] == 1
    assert rows[0]["specific_issue"] == "Pocket Not Waterproof"
    assert rows[0]["representative_comments"] == [content]
    assert rows[0]["evidence_spans"] == []


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


def test_customer_highlight_rows_keep_cluster_propagated_only_rows_with_fallback_comment() -> None:
    content = "They kept my feet dry on a rainy hike."
    rows = build_customer_highlight_rows(
        [
            {
                "id": 1,
                "content": content,
                "sentiment": "positive",
                "aspects_json": {
                    "customer_label_schema_version": CUSTOMER_LABEL_SCHEMA_VERSION,
                    "sub_category": "outdoor",
                    "cluster_propagated": True,
                    "aspects": [
                        {
                            "key": "waterproof",
                            "polarity": "positive",
                            "customer_highlight": "Keeps Water Out",
                            "customer_highlight_zh": "防水可靠",
                            "canonical_highlight_key": "keeps_water_out",
                            "highlight_confidence": "medium",
                            "highlight_display_allowed": True,
                            "evidence_span": "kept me dry",
                        }
                    ],
                },
            }
        ],
        locale="en",
        limit=10,
    )

    assert len(rows) == 1
    assert rows[0]["count"] == 1
    assert rows[0]["customer_highlight"] == "Keeps Water Out"
    assert rows[0]["representative_comments"] == [content]
    assert rows[0]["evidence_spans"] == []
