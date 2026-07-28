from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from backend_api.app.services.customer_label_quality import build_customer_label_quality_warnings
from backend_api.app.services.specific_issue import (
    CUSTOMER_LABEL_OCCURRENCE_RULESET_VERSION,
    CUSTOMER_LABEL_OCCURRENCE_SCHEMA_VERSION,
    build_customer_highlight_rows,
    build_specific_issue_rows,
    iter_customer_highlight_occurrences,
    iter_specific_issue_occurrences,
)
from review_analyzer.review_dates import normalize_comment_review_date

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "customer_label_50u_gold_samples.json"

_LABEL_META: dict[tuple[str, str], tuple[str, str, str]] = {
    ("issue", "water_leaks_through"): ("Water Leaks Through", "容易进水", "waterproof"),
    ("highlight", "keeps_water_out"): ("Keeps Water Out", "防水可靠", "waterproof"),
    ("issue", "value_for_money"): ("Value for Money", "性价比", "price_value"),
    ("highlight", "value_for_money"): ("Value for Money", "性价比", "price_value"),
    ("issue", "not_breathable"): ("Not Breathable", "不够透气", "breathability"),
    ("highlight", "comfortable_to_wear"): ("Comfortable To Wear", "穿着舒适", "comfort"),
    ("issue", "pocket_not_waterproof"): ("Pocket Not Waterproof", "口袋不防水", "accessory_storage"),
    ("highlight", "waterproof"): ("Waterproof", "防水性", "waterproof"),
    ("highlight", "quality"): ("Quality", "质量", "quality"),
    ("issue", "other"): ("Other", "其他", "other"),
    ("issue", "waterproofing"): ("Waterproofing", "防水性", "waterproofing"),
    ("issue", "zipper_fails"): ("Zipper Fails", "拉链故障", "zipper_quality"),
    ("highlight", "useful_storage_space"): ("Useful Storage Space", "收纳空间实用", "accessory_storage"),
    ("issue", "missing_parts"): ("Missing Parts", "缺少零件", "assembly"),
    ("highlight", "good_traction"): ("Good Traction", "抓地稳", "grip"),
    (
        "highlight",
        "arrives_on_time_and_intact",
    ): ("Arrives On Time and Intact", "到货及时完好", "shipping_damage"),
}


def _fixture_payload() -> dict[str, Any]:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def _occurrence(sample: dict[str, Any], label: dict[str, Any]) -> dict[str, Any]:
    label_type = str(label["type"])
    canonical = str(label["key"])
    display_en, display_zh, aspect_key = _LABEL_META[(label_type, canonical)]
    content = str(sample["content"])
    evidence = str(label.get("evidence") or "")
    start = content.find(evidence)
    return {
        "comment_id": sample["id"],
        "type": label_type,
        "raw_label": display_en,
        "canonical_label_key": canonical,
        "display_label_en": display_en,
        "display_label_zh": display_zh,
        "aspect_key": aspect_key,
        "evidence_span": evidence,
        "evidence_start": start,
        "evidence_end": start + len(evidence) if start >= 0 else -1,
        "confidence": str(label.get("confidence") or "high"),
        "source": str(label.get("source") or "human"),
        "source_detail": str(label.get("source_detail") or "50u_gold_sample"),
        "evidence_verified": bool(label.get("verified", start >= 0)),
        "cluster_propagated": bool(label.get("cluster_propagated")),
        "schema_version": CUSTOMER_LABEL_OCCURRENCE_SCHEMA_VERSION,
        "ruleset_version": CUSTOMER_LABEL_OCCURRENCE_RULESET_VERSION,
        "display_allowed": bool(label.get("display_allowed", True)),
    }


def _comments() -> list[dict[str, Any]]:
    comments: list[dict[str, Any]] = []
    for sample in _fixture_payload()["samples"]:
        labels = [_occurrence(sample, label) for label in sample.get("labels", [])]
        comments.append(
            {
                "id": sample["id"],
                "content": sample["content"],
                "date": sample.get("date"),
                "sentiment": sample.get("sentiment", "neutral"),
                "sub_category": sample.get("sub_category", ""),
                "aspects_json": {
                    "customer_label_occurrence_schema_version": CUSTOMER_LABEL_OCCURRENCE_SCHEMA_VERSION,
                    "customer_label_occurrence_ruleset_version": CUSTOMER_LABEL_OCCURRENCE_RULESET_VERSION,
                    "sub_category": sample.get("sub_category", ""),
                    "cluster_propagated": any(label.get("cluster_propagated") for label in labels),
                    "customer_label_occurrences": labels,
                },
            }
        )
    return comments


def _frontstage_keys(occurrences: list[dict[str, Any]], canonical_field: str) -> list[str]:
    keys: list[str] = []
    for occurrence in occurrences:
        if occurrence.get("cluster_propagated"):
            continue
        if not (occurrence.get("legacy_fallback") or occurrence.get("source_review_allowed")):
            continue
        key = str(occurrence.get(canonical_field) or occurrence.get("canonical_label_key") or "")
        if key and key not in keys:
            keys.append(key)
    return keys


def _row_by_key(rows: list[dict[str, Any]], canonical_field: str) -> dict[tuple[str, str], dict[str, Any]]:
    return {
        (str(row.get("sub_category") or ""), str(row.get(canonical_field) or "")): row
        for row in rows
    }


def _assert_representative_evidence_locatable(row: dict[str, Any]) -> None:
    comments = [str(comment) for comment in row["representative_comments"]]
    for evidence in row["evidence_spans"]:
        assert any(str(evidence) in comment for comment in comments), row


def test_50u_gold_sample_fixture_shape_and_amazon_review_dates() -> None:
    payload = _fixture_payload()
    samples = payload["samples"]
    assert 30 <= len(samples) <= 50
    assert len({sample["id"] for sample in samples}) == len(samples)
    assert set(payload["coverage"]) >= {
        "Water Leaks Through",
        "Keeps Water Out",
        "Value for Money",
        "Not Breathable",
        "missing evidence",
        "cluster-propagated evidence",
        "broad/internal label",
        "Amazon text date",
        "positive waterproof evidence excluded from Water Leaks Through",
    }

    labels = [label for sample in samples for label in sample.get("labels", [])]
    assert any(label.get("verified") is False for label in labels)
    assert any(label.get("cluster_propagated") is True for label in labels)
    assert {label["key"] for label in labels} >= {
        "water_leaks_through",
        "keeps_water_out",
        "value_for_money",
        "not_breathable",
        "waterproof",
        "quality",
        "other",
        "waterproofing",
    }

    amazon_samples = [sample for sample in samples if str(sample.get("date", "")).startswith("Reviewed in")]
    assert len(amazon_samples) >= 5
    for sample in samples:
        if sample.get("expected_review_date"):
            assert normalize_comment_review_date(sample["date"]) == sample["expected_review_date"]


def test_50u_gold_samples_match_expected_frontstage_labels_per_review() -> None:
    by_id = {sample["id"]: sample for sample in _fixture_payload()["samples"]}
    for comment in _comments():
        sample = by_id[comment["id"]]
        issue_keys = _frontstage_keys(
            iter_specific_issue_occurrences(comment, locale="en"),
            "canonical_issue_key",
        )
        highlight_keys = _frontstage_keys(
            iter_customer_highlight_occurrences(comment, locale="en"),
            "canonical_highlight_key",
        )

        assert issue_keys == sample["expected_issue_keys"], sample["id"]
        assert highlight_keys == sample["expected_highlight_keys"], sample["id"]


def test_50u_top_rows_do_not_recount_propagated_or_unverified_occurrences() -> None:
    comments = _comments()
    issue_rows = build_specific_issue_rows(comments, locale="en", limit=50)
    highlight_rows = build_customer_highlight_rows(comments, locale="en", limit=50)
    issues = _row_by_key(issue_rows, "canonical_issue_key")
    highlights = _row_by_key(highlight_rows, "canonical_highlight_key")

    water = issues[("outdoor", "water_leaks_through")]
    assert water["mention_count"] == 5
    assert water["raw_occurrence_count"] == 5
    assert water["total_occurrence_count"] == 8
    assert water["propagated_occurrence_count"] == 3
    assert water["has_cluster_propagated_occurrences"] is True
    assert water["evidence_spans"] == [
        "Water leaked through the boot seam",
        "water leaking in",
        "boots started filling with water",
        "leak appeared to be coming from a seam",
        "Moisture coming through",
    ]

    keeps_water_out = highlights[("outdoor", "keeps_water_out")]
    assert keeps_water_out["mention_count"] == 6
    assert keeps_water_out["raw_occurrence_count"] == 6
    assert keeps_water_out["total_occurrence_count"] == 9
    assert keeps_water_out["propagated_occurrence_count"] == 3
    assert keeps_water_out["has_cluster_propagated_occurrences"] is True

    assert issues[("apparel", "value_for_money")]["mention_count"] == 4
    assert highlights[("apparel", "value_for_money")]["mention_count"] == 4
    assert issues[("apparel", "not_breathable")]["mention_count"] == 4

    assert ("outdoor", "pocket_not_waterproof") not in issues
    assert ("apparel", "comfortable_to_wear") not in highlights
    assert ("outdoor", "waterproof") not in highlights
    assert ("outdoor", "quality") not in highlights
    assert ("outdoor", "other") not in issues
    assert ("outdoor", "waterproofing") not in issues

    for row in issue_rows + highlight_rows:
        _assert_representative_evidence_locatable(row)
        assert all("Cluster copy" not in comment for comment in row["representative_comments"])
        assert "comfortable all day" not in row["evidence_spans"]
        assert "copied pocket leak" not in row["evidence_spans"]
        assert row["cluster_propagated"] is False


def test_50u_positive_waterproof_evidence_stays_out_of_water_leaks_issue() -> None:
    comments = _comments()
    positive_phrases = {
        "no leakage",
        "no leaks",
        "remained dry",
        "kept dry",
        "stayed dry",
        "keep you dry",
    }
    water_issue_evidence = [
        str(occurrence.get("evidence_span") or "").lower()
        for comment in comments
        for occurrence in iter_specific_issue_occurrences(comment, locale="en")
        if occurrence.get("canonical_issue_key") == "water_leaks_through"
    ]
    keeps_water_out_evidence = [
        str(occurrence.get("evidence_span") or "").lower()
        for comment in comments
        for occurrence in iter_customer_highlight_occurrences(comment, locale="en")
        if occurrence.get("canonical_highlight_key") == "keeps_water_out"
        and not occurrence.get("cluster_propagated")
    ]

    for phrase in positive_phrases:
        assert phrase not in water_issue_evidence
        assert phrase in keeps_water_out_evidence


def test_50u_gold_sample_quality_warning_gate_is_clean() -> None:
    assert build_customer_label_quality_warnings(_comments(), locale="en") == []


def test_customer_label_quality_warnings_detect_known_bad_shapes() -> None:
    dominant_comments = [
        {
            "id": f"dominant-{index}",
            "content": f"Water leaked through seam {index}.",
            "sentiment": "negative",
            "sub_category": "outdoor",
            "aspects_json": {
                "customer_label_occurrence_schema_version": CUSTOMER_LABEL_OCCURRENCE_SCHEMA_VERSION,
                "sub_category": "outdoor",
                "customer_label_occurrences": [
                    {
                        **_occurrence(
                            {
                                "id": f"dominant-{index}",
                                "content": f"Water leaked through seam {index}.",
                            },
                            {"type": "issue", "key": "water_leaks_through", "evidence": "Water leaked through"},
                        ),
                        "comment_id": f"dominant-{index}",
                    }
                ],
            },
        }
        for index in range(10)
    ]
    evidence_gap_comments = [
        {
            "id": f"evidence-gap-{index}",
            "content": "The product feels flimsy but does not mention the copied value text.",
            "sentiment": "negative",
            "sub_category": "apparel",
            "issue_tag": "Value for Money",
            "aspects_json": None,
        }
        for index in range(3)
    ]
    cluster_comments = [
        {
            "id": "cluster-source",
            "content": "The zipper broke on day one.",
            "sentiment": "negative",
            "sub_category": "outdoor",
            "aspects_json": {
                "customer_label_occurrence_schema_version": CUSTOMER_LABEL_OCCURRENCE_SCHEMA_VERSION,
                "sub_category": "outdoor",
                "customer_label_occurrences": [
                    _occurrence(
                        {"id": "cluster-source", "content": "The zipper broke on day one."},
                        {"type": "issue", "key": "zipper_fails", "evidence": "zipper broke"},
                    )
                ],
            },
        }
    ] + [
        {
            "id": f"cluster-copy-{index}",
            "content": f"Cluster copy {index} says the zipper broke.",
            "sentiment": "negative",
            "sub_category": "outdoor",
            "aspects_json": {
                "customer_label_occurrence_schema_version": CUSTOMER_LABEL_OCCURRENCE_SCHEMA_VERSION,
                "sub_category": "outdoor",
                "customer_label_occurrences": [
                    _occurrence(
                        {
                            "id": f"cluster-copy-{index}",
                            "content": f"Cluster copy {index} says the zipper broke.",
                        },
                        {
                            "type": "issue",
                            "key": "zipper_fails",
                            "evidence": "zipper broke",
                            "cluster_propagated": True,
                        },
                    )
                ],
            },
        }
        for index in range(5)
    ]
    long_tail_comments = [
        {
            "id": f"long-tail-{index}",
            "content": f"Unique label {index} appeared in this source review.",
            "sentiment": "negative",
            "sub_category": "demo",
            "issue_tag": f"Unique Label {index}",
            "aspects_json": None,
        }
        for index in range(20)
    ]

    dominance_warning_types = {
        warning["type"]
        for warning in build_customer_label_quality_warnings(dominant_comments, locale="en")
    }
    warning_types = {
        warning["type"]
        for warning in build_customer_label_quality_warnings(
            evidence_gap_comments + cluster_comments + long_tail_comments,
            locale="en",
        )
    }

    assert "customer_label_single_label_dominance" in dominance_warning_types
    assert "customer_label_low_representative_evidence_ratio" in warning_types
    assert "customer_label_high_cluster_propagated_ratio" in warning_types
    assert "customer_label_long_tail_expansion" in warning_types
