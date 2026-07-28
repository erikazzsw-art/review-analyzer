from __future__ import annotations

from backend_api.app.services.specific_issue import (
    CUSTOMER_LABEL_OCCURRENCE_RULESET_VERSION,
    CUSTOMER_LABEL_OCCURRENCE_SCHEMA_VERSION,
    CUSTOMER_LABEL_SCHEMA_VERSION,
    ISSUE_RULESET_VERSION,
    SPECIFIC_ISSUE_SCHEMA_VERSION,
    build_customer_highlight_rows,
    build_specific_issue_rows,
    customer_highlight_tags_for_comment,
    decorate_comment_customer_labels,
    enrich_aspects_json,
    iter_customer_highlight_occurrences,
    iter_specific_issue_occurrences,
)

_OCCURRENCE_REQUIRED_FIELDS = {
    "comment_id",
    "type",
    "raw_label",
    "canonical_label_key",
    "display_label_en",
    "display_label_zh",
    "aspect_key",
    "evidence_span",
    "evidence_start",
    "evidence_end",
    "confidence",
    "source",
    "evidence_verified",
    "cluster_propagated",
    "schema_version",
    "ruleset_version",
}


def _label_occurrence(
    *,
    label_type: str,
    canonical: str,
    display: str,
    aspect_key: str,
    evidence: str,
    comment_id: int | None = None,
) -> dict[str, object]:
    return {
        "comment_id": comment_id,
        "type": label_type,
        "raw_label": display,
        "canonical_label_key": canonical,
        "display_label_en": display,
        "display_label_zh": display,
        "aspect_key": aspect_key,
        "evidence_span": evidence,
        "evidence_start": -1,
        "evidence_end": -1,
        "confidence": "high",
        "source": "rule",
        "source_detail": "test_occurrence",
        "evidence_verified": True,
        "cluster_propagated": False,
        "schema_version": CUSTOMER_LABEL_OCCURRENCE_SCHEMA_VERSION,
        "ruleset_version": CUSTOMER_LABEL_OCCURRENCE_RULESET_VERSION,
        "display_allowed": True,
    }


def _comment_with_occurrences(
    *,
    comment_id: int,
    content: str,
    occurrences: list[dict[str, object]],
    sentiment: str = "neutral",
    sub_category: str = "outdoor",
) -> dict[str, object]:
    return {
        "id": comment_id,
        "content": content,
        "sentiment": sentiment,
        "aspects_json": {
            "customer_label_occurrence_schema_version": CUSTOMER_LABEL_OCCURRENCE_SCHEMA_VERSION,
            "sub_category": sub_category,
            "customer_label_occurrences": occurrences,
        },
    }


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


def test_enrich_aspects_json_adds_customer_label_occurrences_for_issue_and_highlight() -> None:
    content = "The hanger was missing, but the waders kept me dry."
    enriched = enrich_aspects_json(
        {
            "aspects": [
                {
                    "key": "accessory_storage",
                    "polarity": "negative",
                    "evidence_span": "hanger was missing",
                },
                {
                    "key": "waterproof",
                    "polarity": "positive",
                    "evidence_span": "kept me dry",
                },
            ]
        },
        sub_category="outdoor",
        content=content,
        locale="en",
        comment_id=10,
    )

    assert enriched is not None
    assert enriched["customer_label_occurrence_schema_version"] == CUSTOMER_LABEL_OCCURRENCE_SCHEMA_VERSION
    assert enriched["customer_label_occurrence_ruleset_version"] == CUSTOMER_LABEL_OCCURRENCE_RULESET_VERSION
    occurrences = enriched["customer_label_occurrences"]
    assert len(occurrences) == 2
    assert all(set(item) >= _OCCURRENCE_REQUIRED_FIELDS for item in occurrences)

    issue = next(item for item in occurrences if item["type"] == "issue")
    highlight = next(item for item in occurrences if item["type"] == "highlight")
    assert issue["comment_id"] == 10
    assert issue["canonical_label_key"] == "missing_wader_hanger"
    assert issue["display_label_en"] == "Missing Wader Hanger"
    assert issue["source"] == "rule"
    assert issue["source_detail"] == "regex_alias_rule"
    assert issue["evidence_verified"] is True
    assert content[issue["evidence_start"] : issue["evidence_end"]] == issue["evidence_span"]
    assert highlight["canonical_label_key"] == "keeps_water_out"
    assert highlight["display_label_en"] == "Keeps Water Out"
    assert content[highlight["evidence_start"] : highlight["evidence_end"]] == "kept me dry"


def test_occurrence_iterator_projects_new_payload_and_fills_comment_id() -> None:
    content = "The pocket gets wet whenever it rains."
    enriched = enrich_aspects_json(
        {
            "aspects": [
                {
                    "key": "accessory_storage",
                    "polarity": "negative",
                    "specific_issue": "Pocket Gets Wet",
                    "canonical_issue_key": "pocket_gets_wet",
                    "specific_issue_raw": "pocket gets wet",
                    "issue_confidence": "medium",
                    "display_allowed": True,
                    "evidence_span": "pocket gets wet",
                }
            ]
        },
        sub_category="outdoor",
        content=content,
        locale="en",
    )

    occurrences = iter_specific_issue_occurrences(
        {"id": 42, "content": content, "aspects_json": enriched},
        locale="en",
    )

    assert len(occurrences) == 1
    occurrence = occurrences[0]
    assert occurrence["comment_id"] == 42
    assert occurrence["type"] == "issue"
    assert occurrence["canonical_label_key"] == "pocket_gets_wet"
    assert occurrence["canonical_issue_key"] == "pocket_gets_wet"
    assert occurrence["specific_issue"] == "Pocket Gets Wet"
    assert occurrence["evidence_verified"] is True
    assert occurrence["verified_evidence"] is True
    assert content[occurrence["evidence_start"] : occurrence["evidence_end"]] == "pocket gets wet"


def test_issue_mention_share_uses_all_issue_mentions_as_denominator() -> None:
    comments = [
        _comment_with_occurrences(
            comment_id=1,
            content="The pocket got wet in the rain.",
            occurrences=[
                _label_occurrence(
                    label_type="issue",
                    canonical="pocket_not_waterproof",
                    display="Pocket Not Waterproof",
                    aspect_key="accessory_storage",
                    evidence="pocket got wet",
                    comment_id=1,
                )
            ],
            sentiment="negative",
        ),
        _comment_with_occurrences(
            comment_id=2,
            content="The storage pocket leaked.",
            occurrences=[
                _label_occurrence(
                    label_type="issue",
                    canonical="pocket_not_waterproof",
                    display="Pocket Not Waterproof",
                    aspect_key="capacity",
                    evidence="pocket leaked",
                    comment_id=2,
                )
            ],
            sentiment="negative",
        ),
        _comment_with_occurrences(
            comment_id=3,
            content="The zipper broke after one trip.",
            occurrences=[
                _label_occurrence(
                    label_type="issue",
                    canonical="zipper_fails",
                    display="Zipper Fails",
                    aspect_key="zipper_quality",
                    evidence="zipper broke",
                    comment_id=3,
                )
            ],
            sentiment="negative",
        ),
        {"id": 4, "content": "No label here.", "sentiment": "neutral", "aspects_json": None},
    ]

    rows = build_specific_issue_rows(comments, locale="en", limit=10)
    pocket = next(row for row in rows if row["canonical_issue_key"] == "pocket_not_waterproof")
    zipper = next(row for row in rows if row["canonical_issue_key"] == "zipper_fails")

    assert pocket["mention_count"] == 2
    assert pocket["count"] == 2
    assert pocket["review_count"] == 2
    assert pocket["mention_share"] == 66.7
    assert pocket["pct"] == 66.7
    assert pocket["impact_review_share"] == 50.0
    assert pocket["raw_occurrence_count"] == 2
    assert zipper["mention_share"] == 33.3
    assert zipper["impact_review_share"] == 25.0


def test_highlight_mention_share_uses_all_highlight_mentions_as_denominator() -> None:
    comments = [
        _comment_with_occurrences(
            comment_id=1,
            content="They kept me dry.",
            occurrences=[
                _label_occurrence(
                    label_type="highlight",
                    canonical="keeps_water_out",
                    display="Keeps Water Out",
                    aspect_key="waterproof",
                    evidence="kept me dry",
                    comment_id=1,
                )
            ],
            sentiment="positive",
        ),
        _comment_with_occurrences(
            comment_id=2,
            content="Still kept my feet dry after hours.",
            occurrences=[
                _label_occurrence(
                    label_type="highlight",
                    canonical="keeps_water_out",
                    display="Keeps Water Out",
                    aspect_key="waterproof",
                    evidence="kept my feet dry",
                    comment_id=2,
                )
            ],
            sentiment="positive",
        ),
        _comment_with_occurrences(
            comment_id=3,
            content="The boots fit perfect.",
            occurrences=[
                _label_occurrence(
                    label_type="highlight",
                    canonical="fits_as_expected",
                    display="Fits as Expected",
                    aspect_key="boot_fit",
                    evidence="fit perfect",
                    comment_id=3,
                )
            ],
            sentiment="positive",
        ),
        {"id": 4, "content": "No label here.", "sentiment": "neutral", "aspects_json": None},
    ]

    rows = build_customer_highlight_rows(comments, locale="en", limit=10)
    dry = next(row for row in rows if row["canonical_highlight_key"] == "keeps_water_out")
    fit = next(row for row in rows if row["canonical_highlight_key"] == "fits_as_expected")

    assert dry["mention_count"] == 2
    assert dry["count"] == 2
    assert dry["review_count"] == 2
    assert dry["mention_share"] == 66.7
    assert dry["pct"] == 66.7
    assert dry["impact_review_share"] == 50.0
    assert dry["raw_occurrence_count"] == 2
    assert fit["mention_share"] == 33.3
    assert fit["impact_review_share"] == 25.0


def test_insight_rows_use_occurrences_without_overall_sentiment_filter(monkeypatch) -> None:
    from review_analyzer.insight_engine import build_results_insights

    monkeypatch.setattr(
        "review_analyzer.insight_engine._build_ai_results_payload",
        lambda *args, **kwargs: None,
    )
    comments = [
        _comment_with_occurrences(
            comment_id=1,
            content="I like the waders, but the zipper broke on day one.",
            occurrences=[
                _label_occurrence(
                    label_type="issue",
                    canonical="zipper_fails",
                    display="Zipper Fails",
                    aspect_key="zipper_quality",
                    evidence="zipper broke",
                    comment_id=1,
                )
            ],
            sentiment="positive",
        ),
        _comment_with_occurrences(
            comment_id=2,
            content="The fit was bad, but they kept me dry.",
            occurrences=[
                _label_occurrence(
                    label_type="highlight",
                    canonical="keeps_water_out",
                    display="Keeps Water Out",
                    aspect_key="waterproof",
                    evidence="kept me dry",
                    comment_id=2,
                )
            ],
            sentiment="negative",
        ),
    ]

    insights = build_results_insights(1, comments, {"product_id": "demo"}, locale="en")

    assert insights["user_experience"]["negative"][0]["canonical_issue_key"] == "zipper_fails"
    assert insights["user_experience"]["positive"][0]["canonical_highlight_key"] == "keeps_water_out"
    assert "customer label occurrences" in insights["purchase_motives"]["summary"]
    assert "customer label occurrences" in insights["unmet_needs"]["summary"]


def test_no_leaks_does_not_create_water_leaks_issue() -> None:
    content = "These waders stayed dry all day with no leaks whatsoever."
    occurrences = iter_specific_issue_occurrences(
        {
            "id": 1,
            "content": content,
            "sentiment": "positive",
            "issue_tag": "Waterproof Performance",
            "aspects_json": enrich_aspects_json(
                {
                    "aspects": [
                        {
                            "key": "waterproof",
                            "polarity": "negative",
                            "evidence_span": "no leaks whatsoever",
                        }
                    ]
                },
                sub_category="outdoor",
                content=content,
                locale="en",
            ),
        },
        locale="en",
    )

    assert occurrences == []


def test_positive_dry_phrases_do_not_create_water_leaks_issue() -> None:
    for evidence in ("remained dry", "kept dry"):
        content = f"These waders {evidence} through the whole trip."
        occurrences = iter_specific_issue_occurrences(
            {
                "id": evidence,
                "content": content,
                "sentiment": "positive",
                "issue_tag": "Waterproof Performance",
                "aspects_json": enrich_aspects_json(
                    {
                        "aspects": [
                            {
                                "key": "waterproof",
                                "polarity": "negative",
                                "evidence_span": evidence,
                            }
                        ]
                    },
                    sub_category="outdoor",
                    content=content,
                    locale="en",
                ),
            },
            locale="en",
        )

        assert occurrences == []


def test_legacy_aspect_water_leak_hint_with_no_leakage_is_suppressed() -> None:
    content = "Worked great no leakage even at waist height. Great price."
    comment = {
        "id": 26302,
        "content": content,
        "sentiment": "positive",
        "issue_tag": "",
        "highlight_tag": "Waterproofing,Size & Fit",
        "aspects_json": {
            "specific_issue_schema_version": SPECIFIC_ISSUE_SCHEMA_VERSION,
            "customer_label_schema_version": CUSTOMER_LABEL_SCHEMA_VERSION,
            "sub_category": "outdoor",
            "aspects": [
                {
                    "key": "waterproof",
                    "polarity": "negative",
                    "specific_issue": "Water Leaks Through",
                    "canonical_issue_key": "water_leaks_through",
                    "specific_issue_raw": "Water Leaks Through",
                    "issue_confidence": "high",
                    "display_allowed": True,
                    "customer_highlight": "Keeps Water Out",
                    "canonical_highlight_key": "keeps_water_out",
                    "evidence_span": "no leakage",
                }
            ],
        },
    }

    assert iter_specific_issue_occurrences(comment, locale="en") == []
    assert build_specific_issue_rows([comment], locale="en", limit=10) == []


def test_occurrence_payload_water_leak_issue_with_no_leakage_is_suppressed_but_highlight_kept() -> None:
    content = "Got for my son and he loves them. No leakage and the fit is great."
    comment = _comment_with_occurrences(
        comment_id=26388,
        content=content,
        sentiment="positive",
        occurrences=[
            _label_occurrence(
                label_type="issue",
                canonical="water_leaks_through",
                display="Water Leaks Through",
                aspect_key="waterproof",
                evidence="No leakage",
                comment_id=26388,
            ),
            _label_occurrence(
                label_type="highlight",
                canonical="keeps_water_out",
                display="Keeps Water Out",
                aspect_key="waterproof",
                evidence="No leakage",
                comment_id=26388,
            ),
        ],
    )

    assert iter_specific_issue_occurrences(comment, locale="en") == []
    highlights = iter_customer_highlight_occurrences(comment, locale="en")
    assert len(highlights) == 1
    assert highlights[0]["canonical_highlight_key"] == "keeps_water_out"
    assert build_specific_issue_rows([comment], locale="en", limit=10) == []


def test_enrich_filters_existing_no_leakage_water_issue_occurrence() -> None:
    content = "Worked great no leakage even at waist height."
    enriched = enrich_aspects_json(
        {
            "aspects": [],
            "customer_label_occurrence_schema_version": CUSTOMER_LABEL_OCCURRENCE_SCHEMA_VERSION,
            "customer_label_occurrences": [
                _label_occurrence(
                    label_type="issue",
                    canonical="water_leaks_through",
                    display="Water Leaks Through",
                    aspect_key="waterproof",
                    evidence="no leakage",
                    comment_id=26302,
                )
            ],
        },
        sub_category="outdoor",
        content=content,
        locale="en",
        comment_id=26302,
    )

    assert enriched is not None
    assert enriched["customer_label_occurrences"] == []


def test_no_leakage_enriches_keeps_water_out_highlight_not_water_issue() -> None:
    content = "The waders had no leakage after standing waist deep in the creek."
    enriched = enrich_aspects_json(
        {
            "aspects": [
                {
                    "key": "waterproof",
                    "polarity": "positive",
                    "evidence_span": "no leakage",
                }
            ]
        },
        sub_category="outdoor",
        content=content,
        locale="en",
    )

    assert enriched is not None
    occurrences = enriched["customer_label_occurrences"]
    assert [item for item in occurrences if item["type"] == "issue"] == []
    highlight = next(item for item in occurrences if item["type"] == "highlight")
    assert highlight["canonical_label_key"] == "keeps_water_out"
    assert highlight["display_label_en"] == "Keeps Water Out"


def test_current_product_leak_text_recovers_water_issue_from_cluster_payload() -> None:
    content = (
        "I have had them for about 1 year now. Both feet are leaking around where "
        "the boot connects to the wader. The boot is also extremely uncomfortable."
    )
    occurrences = iter_specific_issue_occurrences(
        {
            "id": 26483,
            "content": content,
            "sentiment": "negative",
            "aspects_json": {
                "cluster_propagated": True,
                "customer_label_occurrence_schema_version": CUSTOMER_LABEL_OCCURRENCE_SCHEMA_VERSION,
                "customer_label_occurrences": [
                    {
                        "comment_id": 26483,
                        "type": "issue",
                        "raw_label": "Uncomfortable Fit",
                        "canonical_label_key": "uncomfortable_fit",
                        "display_label_en": "Uncomfortable Fit",
                        "display_label_zh": "穿着不舒服",
                        "aspect_key": "comfort",
                        "dimension_en": "Comfort",
                        "dimension_zh": "舒适度",
                        "sub_category": "waders",
                        "evidence_span": "stayed warm, dry and comfortable the whole time",
                        "evidence_start": -1,
                        "evidence_end": -1,
                        "confidence": "high",
                        "source": "rule",
                        "source_detail": "sentiment_recovery_rule",
                        "evidence_verified": False,
                        "cluster_propagated": True,
                        "schema_version": CUSTOMER_LABEL_OCCURRENCE_SCHEMA_VERSION,
                        "ruleset_version": CUSTOMER_LABEL_OCCURRENCE_RULESET_VERSION,
                        "display_allowed": True,
                    }
                ],
            },
        },
        locale="en",
    )

    water = next(item for item in occurrences if item["canonical_issue_key"] == "water_leaks_through")
    assert water["specific_issue"] == "Water Leaks Through"
    assert water["evidence_span"] == "Both feet are leaking around where the boot connects to the wader"
    assert water["verified_evidence"] is True
    assert water["cluster_propagated"] is False


def test_occurrence_level_cluster_flag_overrides_top_level_cluster_payload() -> None:
    content = "The seals were leaking a little bit after a year of use."
    occurrences = iter_specific_issue_occurrences(
        {
            "id": 469,
            "content": content,
            "sentiment": "negative",
            "aspects_json": {
                "cluster_propagated": True,
                "customer_label_occurrence_schema_version": CUSTOMER_LABEL_OCCURRENCE_SCHEMA_VERSION,
                "customer_label_occurrences": [
                    {
                        "comment_id": 469,
                        "type": "issue",
                        "raw_label": "Water Leaks Through",
                        "canonical_label_key": "water_leaks_through",
                        "display_label_en": "Water Leaks Through",
                        "display_label_zh": "漏水",
                        "aspect_key": "waterproof",
                        "dimension_en": "Waterproofing",
                        "dimension_zh": "防水",
                        "sub_category": "waders",
                        "evidence_span": "were leaking a little bit",
                        "confidence": "high",
                        "source": "rule",
                        "source_detail": "current_product_leak_text_rule",
                        "evidence_verified": True,
                        "cluster_propagated": False,
                        "schema_version": CUSTOMER_LABEL_OCCURRENCE_SCHEMA_VERSION,
                        "ruleset_version": CUSTOMER_LABEL_OCCURRENCE_RULESET_VERSION,
                        "display_allowed": True,
                    }
                ],
            },
        },
        locale="en",
    )

    water = next(item for item in occurrences if item["canonical_issue_key"] == "water_leaks_through")
    assert water["evidence_span"] == "were leaking a little bit"
    assert water["verified_evidence"] is True
    assert water["cluster_propagated"] is False


def test_old_product_leak_context_does_not_create_water_issue() -> None:
    for content in (
        "Got these for my boyfriend after the ones he had from another brand started leaking everywhere. These have kept him dry so far.",
        "I ordered these waders after my Magellan ones developed a slow leak. Boots fit well, didn't experience any leaking.",
        "The hand warmer pocket is great until water gets in there.",
    ):
        occurrences = iter_specific_issue_occurrences(
            {
                "id": content,
                "content": content,
                "sentiment": "positive",
                "aspects_json": {
                    "customer_label_occurrence_schema_version": CUSTOMER_LABEL_OCCURRENCE_SCHEMA_VERSION,
                    "customer_label_occurrences": [],
                },
            },
            locale="en",
        )

        assert [item for item in occurrences if item.get("canonical_issue_key") == "water_leaks_through"] == []


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
    assert occurrences[0]["type"] == "issue"
    assert occurrences[0]["source"] == "legacy"
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
    assert rows[0]["mention_count"] == 1
    assert rows[0]["review_count"] == 1
    assert rows[0]["mention_share"] == 100.0
    assert rows[0]["impact_review_share"] == 100.0
    assert rows[0]["representative_comments"] == []


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
    assert (
        customer_highlight_tags_for_comment(
            {"content": "很好", "highlight_tag": "防水可靠", "aspects_json": None},
            locale="en",
        )
        == []
    )
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
    assert outdoor["count"] == 2
    assert outdoor["pct"] == 66.7
    assert outdoor["aspect_key"] == "accessory_storage"
    assert outdoor["aspect_keys"] == ["accessory_storage", "capacity"]
    assert outdoor["dimension"] == "Accessories & Storage, Capacity"
    assert outdoor["dimensions"] == ["Accessories & Storage", "Capacity"]
    assert outdoor["canonical_issue_key"] == "pocket_not_waterproof"
    assert outdoor["representative_comments"] == [
        "The pocket got wet in light rain.",
        "Water seeped into the pocket and soaked my gear.",
    ]
    assert outdoor["cluster_propagated"] is False
    assert outdoor["has_cluster_propagated_occurrences"] is True
    assert outdoor["propagated_occurrence_count"] == 1
    assert outdoor["total_occurrence_count"] == 3
    assert outdoor["source_review_occurrence_count"] == 2
    assert travel["count"] == 1


def test_specific_issue_rows_drop_cluster_propagated_only_rows_from_frontstage_top() -> None:
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

    assert rows == []


def test_specific_issue_rows_drop_missing_evidence_only_rows_from_frontstage_top() -> None:
    rows = build_specific_issue_rows(
        [
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
                            "evidence_span": "copied evidence from another review",
                        }
                    ],
                },
            }
        ],
        locale="en",
        limit=10,
    )

    assert rows == []


def test_new_occurrence_payload_keeps_missing_evidence_but_not_as_representative() -> None:
    comment = {
        "id": 1,
        "content": "The pocket got wet in light rain.",
        "sentiment": "negative",
        "aspects_json": {
            "customer_label_occurrence_schema_version": CUSTOMER_LABEL_OCCURRENCE_SCHEMA_VERSION,
            "customer_label_occurrences": [
                {
                    "comment_id": None,
                    "type": "issue",
                    "raw_label": "pocket gets wet",
                    "canonical_label_key": "pocket_not_waterproof",
                    "display_label_en": "Pocket Not Waterproof",
                    "display_label_zh": "口袋不防水",
                    "aspect_key": "accessory_storage",
                    "evidence_span": "copied evidence from another review",
                    "evidence_start": -1,
                    "evidence_end": -1,
                    "confidence": "high",
                    "source": "rule",
                    "source_detail": "regex_alias_rule",
                    "evidence_verified": False,
                    "cluster_propagated": False,
                    "schema_version": CUSTOMER_LABEL_OCCURRENCE_SCHEMA_VERSION,
                    "ruleset_version": CUSTOMER_LABEL_OCCURRENCE_RULESET_VERSION,
                    "display_allowed": True,
                }
            ],
        },
    }

    occurrences = iter_specific_issue_occurrences(comment, locale="en")
    rows = build_specific_issue_rows([comment], locale="en", limit=10)

    assert len(occurrences) == 1
    assert occurrences[0]["comment_id"] == 1
    assert occurrences[0]["evidence_verified"] is False
    assert occurrences[0]["verified_evidence"] is False
    assert rows == []


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
    assert breathable["mention_count"] == 1
    assert breathable["review_count"] == 1
    assert breathable["pct"] == 50.0
    assert breathable["mention_share"] == 50.0
    assert breathable["impact_review_share"] == 50.0
    assert breathable["raw_occurrence_count"] == 2
    assert breathable["aspect_keys"] == ["breathability", "mobility"]
    assert breathable["dimension"] == "Breathability, Mobility"
    assert breathable["representative_comments"] == [
        "The material was hot and not breathable. It was stiff and not breathable while walking."
    ]
    assert runs_small["count"] == 1
    assert runs_small["mention_count"] == 1
    assert runs_small["review_count"] == 1
    assert runs_small["raw_occurrence_count"] == 2
    assert runs_small["aspect_keys"] == ["size_fit", "boot_fit"]
    assert runs_small["dimension"] == "Size & Fit, Boot Fit"


def test_customer_highlight_rows_drop_cluster_propagated_only_rows_from_frontstage_top() -> None:
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

    assert rows == []


def test_new_occurrence_payload_keeps_cluster_propagated_for_audit_only() -> None:
    content = "They kept my feet dry on a rainy hike."
    comment = {
        "id": 1,
        "content": content,
        "sentiment": "positive",
        "aspects_json": {
            "cluster_propagated": True,
            "sub_category": "上衣",
            "customer_label_occurrence_schema_version": CUSTOMER_LABEL_OCCURRENCE_SCHEMA_VERSION,
            "customer_label_occurrences": [
                {
                    "comment_id": 1,
                    "type": "highlight",
                    "raw_label": "kept my feet dry",
                    "canonical_label_key": "keeps_water_out",
                    "display_label_en": "Keeps Water Out",
                    "display_label_zh": "防水可靠",
                    "aspect_key": "waterproof",
                    "evidence_span": "kept my feet dry",
                    "evidence_start": content.find("kept my feet dry"),
                    "evidence_end": content.find("kept my feet dry") + len("kept my feet dry"),
                    "confidence": "high",
                    "source": "rule",
                    "source_detail": "regex_alias_rule",
                    "evidence_verified": True,
                    "cluster_propagated": True,
                    "schema_version": CUSTOMER_LABEL_OCCURRENCE_SCHEMA_VERSION,
                    "ruleset_version": CUSTOMER_LABEL_OCCURRENCE_RULESET_VERSION,
                    "display_allowed": True,
                }
            ],
        },
    }

    occurrences = iter_customer_highlight_occurrences(comment, locale="en")
    rows = build_customer_highlight_rows([comment], locale="en", limit=10)

    assert len(occurrences) == 1
    assert occurrences[0]["evidence_verified"] is True
    assert occurrences[0]["verified_evidence"] is False
    assert occurrences[0]["cluster_propagated"] is True
    assert rows == []


def test_phase7_frontstage_top_rows_ignore_cluster_propagated_session114_shape() -> None:
    def occurrence(
        *,
        label_type: str,
        canonical: str,
        display: str,
        aspect_key: str,
        evidence: str,
        comment_id: int,
        cluster_propagated: bool = False,
    ) -> dict[str, object]:
        item = _label_occurrence(
            label_type=label_type,
            canonical=canonical,
            display=display,
            aspect_key=aspect_key,
            evidence=evidence,
            comment_id=comment_id,
        )
        item["cluster_propagated"] = cluster_propagated
        return item

    comments: list[dict[str, object]] = [
        _comment_with_occurrences(
            comment_id=1,
            content="The fabric is too hot during long walks.",
            occurrences=[
                occurrence(
                    label_type="issue",
                    canonical="not_breathable",
                    display="Not Breathable",
                    aspect_key="comfort",
                    evidence="too hot",
                    comment_id=1,
                )
            ],
            sentiment="negative",
            sub_category="apparel",
        ),
        _comment_with_occurrences(
            comment_id=2,
            content="These waders are comfortable to wear for hours.",
            occurrences=[
                occurrence(
                    label_type="highlight",
                    canonical="comfortable_to_wear",
                    display="Comfortable To Wear",
                    aspect_key="comfort",
                    evidence="comfortable to wear",
                    comment_id=2,
                )
            ],
            sentiment="positive",
            sub_category="apparel",
        ),
    ]
    for comment_id in range(3, 8):
        comments.append(
            _comment_with_occurrences(
                comment_id=comment_id,
                content=f"Cluster copied issue review {comment_id}: too hot after a walk.",
                occurrences=[
                    occurrence(
                        label_type="issue",
                        canonical="not_breathable",
                        display="Not Breathable",
                        aspect_key="comfort",
                        evidence="too hot",
                        comment_id=comment_id,
                        cluster_propagated=True,
                    )
                ],
                sentiment="negative",
                sub_category="apparel",
            )
        )
    for comment_id in range(8, 12):
        comments.append(
            _comment_with_occurrences(
                comment_id=comment_id,
                content=(f"Cluster copied highlight review {comment_id}: comfortable to wear around camp."),
                occurrences=[
                    occurrence(
                        label_type="highlight",
                        canonical="comfortable_to_wear",
                        display="Comfortable To Wear",
                        aspect_key="comfort",
                        evidence="comfortable to wear",
                        comment_id=comment_id,
                        cluster_propagated=True,
                    )
                ],
                sentiment="positive",
                sub_category="apparel",
            )
        )

    issue_rows = build_specific_issue_rows(comments, locale="en", limit=10)
    highlight_rows = build_customer_highlight_rows(comments, locale="en", limit=10)
    breathable = next(row for row in issue_rows if row["canonical_issue_key"] == "not_breathable")
    comfortable = next(row for row in highlight_rows if row["canonical_highlight_key"] == "comfortable_to_wear")

    assert breathable["mention_count"] == 1
    assert breathable["review_count"] == 1
    assert breathable["raw_occurrence_count"] == 1
    assert breathable["total_occurrence_count"] == 6
    assert breathable["propagated_occurrence_count"] == 5
    assert breathable["cluster_propagated"] is False
    assert breathable["has_cluster_propagated_occurrences"] is True
    assert breathable["evidence_spans"] == ["too hot"]
    assert breathable["representative_comments"] == ["The fabric is too hot during long walks."]
    assert "too hot" in breathable["representative_comments"][0]

    assert comfortable["mention_count"] == 1
    assert comfortable["review_count"] == 1
    assert comfortable["raw_occurrence_count"] == 1
    assert comfortable["total_occurrence_count"] == 5
    assert comfortable["propagated_occurrence_count"] == 4
    assert comfortable["cluster_propagated"] is False
    assert comfortable["has_cluster_propagated_occurrences"] is True
    assert comfortable["evidence_spans"] == ["comfortable to wear"]
    assert comfortable["representative_comments"] == ["These waders are comfortable to wear for hours."]
    assert "comfortable to wear" in comfortable["representative_comments"][0]


def test_cluster_sentiment_recovery_issue_with_missing_evidence_is_suppressed() -> None:
    content = (
        "I got this sweater in navy and it is much cuter than online. It is a great transition sweater and I love it."
    )
    comment = {
        "id": 1,
        "content": content,
        "sentiment": "positive",
        "aspects_json": {
            "cluster_propagated": True,
            "customer_label_occurrence_schema_version": CUSTOMER_LABEL_OCCURRENCE_SCHEMA_VERSION,
            "customer_label_occurrences": [
                {
                    "comment_id": 1,
                    "type": "issue",
                    "raw_label": "Not Breathable",
                    "canonical_label_key": "not_breathable",
                    "display_label_en": "Not Breathable",
                    "display_label_zh": "不够透气",
                    "aspect_key": "comfort",
                    "evidence_span": "flattering and comfortable",
                    "evidence_start": -1,
                    "evidence_end": -1,
                    "confidence": "high",
                    "source": "rule",
                    "source_detail": "sentiment_recovery_rule",
                    "evidence_verified": False,
                    "cluster_propagated": True,
                    "sub_category": "上衣",
                    "schema_version": CUSTOMER_LABEL_OCCURRENCE_SCHEMA_VERSION,
                    "ruleset_version": CUSTOMER_LABEL_OCCURRENCE_RULESET_VERSION,
                    "display_allowed": True,
                }
            ],
        },
    }

    assert iter_specific_issue_occurrences(comment, locale="en") == []
    assert build_specific_issue_rows([comment], locale="en", limit=10) == []


def test_waders_cluster_sentiment_recovery_issue_stays_audit_counted() -> None:
    content = "The waders stayed warm, dry and comfortable the whole time."
    comment = {
        "id": 1,
        "content": content,
        "sentiment": "positive",
        "aspects_json": {
            "cluster_propagated": True,
            "sub_category": "waders",
            "customer_label_occurrence_schema_version": CUSTOMER_LABEL_OCCURRENCE_SCHEMA_VERSION,
            "customer_label_occurrences": [
                {
                    "comment_id": 1,
                    "type": "issue",
                    "raw_label": "Not Breathable",
                    "canonical_label_key": "not_breathable",
                    "display_label_en": "Not Breathable",
                    "display_label_zh": "不够透气",
                    "aspect_key": "comfort",
                    "evidence_span": "copied cluster evidence",
                    "evidence_start": -1,
                    "evidence_end": -1,
                    "confidence": "high",
                    "source": "rule",
                    "source_detail": "sentiment_recovery_rule",
                    "evidence_verified": False,
                    "cluster_propagated": True,
                    "sub_category": "waders",
                    "schema_version": CUSTOMER_LABEL_OCCURRENCE_SCHEMA_VERSION,
                    "ruleset_version": CUSTOMER_LABEL_OCCURRENCE_RULESET_VERSION,
                    "display_allowed": True,
                }
            ],
        },
    }

    occurrences = iter_specific_issue_occurrences(comment, locale="en")
    rows = build_specific_issue_rows([comment], locale="en", limit=10)

    assert len(occurrences) == 1
    assert occurrences[0]["canonical_issue_key"] == "not_breathable"
    assert rows == []


def test_decorate_preserves_existing_waders_audit_only_issue_occurrence() -> None:
    content = "The waders stayed warm, dry and comfortable the whole time."
    comment = {
        "id": 1,
        "content": content,
        "sentiment": "positive",
        "aspects_json": {
            "specific_issue_schema_version": SPECIFIC_ISSUE_SCHEMA_VERSION,
            "cluster_propagated": True,
            "sub_category": "waders",
            "aspects": [
                {
                    "key": "comfort",
                    "polarity": "positive",
                    "evidence_span": "stayed warm, dry and comfortable the whole time",
                }
            ],
            "customer_label_occurrence_schema_version": CUSTOMER_LABEL_OCCURRENCE_SCHEMA_VERSION,
            "customer_label_occurrences": [
                {
                    "comment_id": 1,
                    "type": "issue",
                    "raw_label": "Not Breathable",
                    "canonical_label_key": "not_breathable",
                    "display_label_en": "Not Breathable",
                    "display_label_zh": "不够透气",
                    "aspect_key": "comfort",
                    "evidence_span": "stayed warm, dry and comfortable the whole time",
                    "evidence_start": -1,
                    "evidence_end": -1,
                    "confidence": "high",
                    "source": "rule",
                    "source_detail": "sentiment_recovery_rule",
                    "evidence_verified": False,
                    "cluster_propagated": True,
                    "sub_category": "waders",
                    "schema_version": CUSTOMER_LABEL_OCCURRENCE_SCHEMA_VERSION,
                    "ruleset_version": CUSTOMER_LABEL_OCCURRENCE_RULESET_VERSION,
                    "display_allowed": True,
                }
            ],
        },
    }

    decorated = decorate_comment_customer_labels(comment, locale="en")
    occurrences = iter_specific_issue_occurrences(decorated, locale="en")
    rows = build_specific_issue_rows([decorated], locale="en", limit=10)

    assert len(occurrences) == 1
    assert occurrences[0]["canonical_issue_key"] == "not_breathable"
    assert rows == []


def test_decorate_still_suppresses_existing_apparel_dirty_breathability_issue() -> None:
    content = "The sweater material is soft and the fit is cute."
    comment = {
        "id": 1,
        "content": content,
        "sentiment": "positive",
        "aspects_json": {
            "specific_issue_schema_version": SPECIFIC_ISSUE_SCHEMA_VERSION,
            "cluster_propagated": True,
            "sub_category": "上衣",
            "aspects": [
                {
                    "key": "comfort",
                    "polarity": "positive",
                    "evidence_span": "flattering and comfortable",
                }
            ],
            "customer_label_occurrence_schema_version": CUSTOMER_LABEL_OCCURRENCE_SCHEMA_VERSION,
            "customer_label_occurrences": [
                {
                    "comment_id": 1,
                    "type": "issue",
                    "raw_label": "Not Breathable",
                    "canonical_label_key": "not_breathable",
                    "display_label_en": "Not Breathable",
                    "display_label_zh": "不够透气",
                    "aspect_key": "comfort",
                    "evidence_span": "flattering and comfortable",
                    "evidence_start": -1,
                    "evidence_end": -1,
                    "confidence": "high",
                    "source": "rule",
                    "source_detail": "sentiment_recovery_rule",
                    "evidence_verified": False,
                    "cluster_propagated": True,
                    "sub_category": "上衣",
                    "schema_version": CUSTOMER_LABEL_OCCURRENCE_SCHEMA_VERSION,
                    "ruleset_version": CUSTOMER_LABEL_OCCURRENCE_RULESET_VERSION,
                    "display_allowed": True,
                }
            ],
        },
    }

    decorated = decorate_comment_customer_labels(comment, locale="en")

    assert build_specific_issue_rows([decorated], locale="en", limit=10) == []


def test_cluster_positive_comfort_sweater_text_does_not_recover_not_breathable() -> None:
    content = "Fun detail with the lace. The sweatshirt material is soft and the fit is cute."
    enriched = enrich_aspects_json(
        {
            "cluster_propagated": True,
            "aspects": [
                {
                    "key": "comfort",
                    "polarity": "positive",
                    "evidence_span": "flattering and comfortable",
                }
            ],
        },
        sub_category="上衣",
        content=content,
        locale="en",
        comment_id=1,
    )

    assert enriched is not None
    issue_occurrences = [item for item in enriched["customer_label_occurrences"] if item["type"] == "issue"]
    assert issue_occurrences == []


def test_comfort_sweat_word_recovers_not_breathable_without_sweater_false_hit() -> None:
    sweat_content = "The fabric traps heat and sweat during long walks."
    enriched = enrich_aspects_json(
        {
            "aspects": [
                {
                    "key": "comfort",
                    "polarity": "positive",
                    "evidence_span": "traps heat and sweat",
                }
            ],
        },
        sub_category="waders",
        content=sweat_content,
        locale="en",
        comment_id=1,
    )

    assert enriched is not None
    rows = build_specific_issue_rows(
        [{"id": 1, "content": sweat_content, "aspects_json": enriched}],
        locale="en",
        limit=10,
    )
    assert rows[0]["canonical_issue_key"] == "not_breathable"

    sweater_content = "The sweater material is soft and the fit is cute."
    sweater_enriched = enrich_aspects_json(
        {
            "aspects": [
                {
                    "key": "comfort",
                    "polarity": "positive",
                    "evidence_span": "soft and cute",
                }
            ],
        },
        sub_category="上衣",
        content=sweater_content,
        locale="en",
        comment_id=2,
    )

    assert sweater_enriched is not None
    issue_occurrences = [item for item in sweater_enriched["customer_label_occurrences"] if item["type"] == "issue"]
    assert issue_occurrences == []


def test_comfort_negative_heat_context_still_recovers_not_breathable() -> None:
    content = "The fabric is too hot and makes me sweat while walking."
    enriched = enrich_aspects_json(
        {
            "aspects": [
                {
                    "key": "comfort",
                    "polarity": "positive",
                    "evidence_span": "too hot",
                }
            ],
        },
        sub_category="apparel",
        content=content,
        locale="en",
        comment_id=1,
    )

    assert enriched is not None
    rows = build_specific_issue_rows(
        [{"id": 1, "content": content, "aspects_json": enriched}],
        locale="en",
        limit=10,
    )
    assert rows[0]["canonical_issue_key"] == "not_breathable"
    assert rows[0]["evidence_spans"] == ["too hot"]


def test_phase7_session96_legacy_value_for_money_rows_get_verified_source_review_evidence() -> None:
    comments = [
        {
            "id": 96_001,
            "content": "The fabric feels thin and is not worth the price.",
            "sentiment": "negative",
            "sub_category": "apparel",
            "issue_tag": "Value for Money",
            "aspects_json": {
                "sub_category": "apparel",
                "aspects": [
                    {
                        "key": "value_for_money",
                        "polarity": "negative",
                        "evidence_span": "not worth the price",
                    }
                ],
            },
        },
        {
            "id": 96_002,
            "content": "These are a good value for the money and fit well.",
            "sentiment": "positive",
            "sub_category": "apparel",
            "highlight_tag": "Value for Money",
            "aspects_json": {
                "sub_category": "apparel",
                "aspects": [
                    {
                        "key": "value_for_money",
                        "polarity": "positive",
                        "evidence_span": "good value for the money",
                    }
                ],
            },
        },
    ]

    issue = build_specific_issue_rows(comments, locale="en", limit=10)[0]
    highlight = build_customer_highlight_rows(comments, locale="en", limit=10)[0]

    assert issue["specific_issue"] == "Value for Money"
    assert issue["mention_count"] == 1
    assert issue["evidence_verified"] is True
    assert issue["evidence_spans"] == ["not worth the price"]
    assert issue["representative_comments"] == ["The fabric feels thin and is not worth the price."]
    assert issue["cluster_propagated"] is False

    assert highlight["customer_highlight"] == "Value for Money"
    assert highlight["mention_count"] == 1
    assert highlight["evidence_verified"] is True
    assert highlight["evidence_spans"] == ["good value for the money"]
    assert highlight["representative_comments"] == ["These are a good value for the money and fit well."]
    assert highlight["cluster_propagated"] is False


def test_phase7_legacy_value_for_money_without_source_span_stays_visible_without_representative_evidence() -> None:
    rows = build_specific_issue_rows(
        [
            {
                "id": 96_003,
                "content": "The fabric is thin and the sizing is off.",
                "sentiment": "negative",
                "sub_category": "apparel",
                "issue_tag": "Value for Money",
            }
        ],
        locale="en",
        limit=10,
    )

    assert rows[0]["specific_issue"] == "Value for Money"
    assert rows[0]["mention_count"] == 1
    assert rows[0]["evidence_verified"] is False
    assert rows[0]["evidence_spans"] == []
    assert rows[0]["representative_comments"] == []
    assert rows[0]["reason"] == ""


def test_phase7_session114_water_leaks_through_keeps_three_verified_source_review_evidence() -> None:
    comments = [
        _comment_with_occurrences(
            comment_id=114_001,
            content="Both feet are leaking around where the boot connects to the wader.",
            occurrences=[
                _label_occurrence(
                    label_type="issue",
                    canonical="water_leaks_through",
                    display="Water Leaks Through",
                    aspect_key="waterproof",
                    evidence="Both feet are leaking around where the boot connects to the wader",
                    comment_id=114_001,
                )
            ],
            sentiment="negative",
            sub_category="outdoor",
        ),
        _comment_with_occurrences(
            comment_id=114_002,
            content="After one trip I had water leaking in through the seams.",
            occurrences=[
                _label_occurrence(
                    label_type="issue",
                    canonical="water_leaks_through",
                    display="Water Leaks Through",
                    aspect_key="waterproof",
                    evidence="water leaking in",
                    comment_id=114_002,
                )
            ],
            sentiment="negative",
            sub_category="outdoor",
        ),
        _comment_with_occurrences(
            comment_id=114_003,
            content="There was a leak at the seams within minutes.",
            occurrences=[
                _label_occurrence(
                    label_type="issue",
                    canonical="water_leaks_through",
                    display="Water Leaks Through",
                    aspect_key="waterproof",
                    evidence="leak at the seams",
                    comment_id=114_003,
                )
            ],
            sentiment="negative",
            sub_category="outdoor",
        ),
    ]

    row = build_specific_issue_rows(comments, locale="en", limit=10)[0]

    assert row["canonical_issue_key"] == "water_leaks_through"
    assert row["mention_count"] == 3
    assert row["evidence_verified"] is True
    assert row["evidence_spans"] == [
        "Both feet are leaking around where the boot connects to the wader",
        "water leaking in",
        "leak at the seams",
    ]
    assert len(row["representative_comments"]) == 3
