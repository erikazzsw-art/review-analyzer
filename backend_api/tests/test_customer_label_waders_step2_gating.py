from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from backend_api.app.services.specific_issue import (
    CUSTOMER_LABEL_OCCURRENCE_RULESET_VERSION,
    CUSTOMER_LABEL_OCCURRENCE_SCHEMA_VERSION,
    build_customer_highlight_rows,
    build_specific_issue_rows,
    customer_highlight_tags_for_comment,
    customer_issue_tags_for_comment,
    iter_customer_highlight_occurrences,
    iter_specific_issue_occurrences,
)
from review_analyzer.exporter import (
    _build_comments_data,
    _build_customer_highlight_top10_data,
    _build_specific_issue_top10_data,
)

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "customer_label_waders_step2_gating.json"

FOUR_PACK_HIGHLIGHTS = [
    "fits_as_expected",
    "good_value_for_the_price",
    "holds_up_well",
    "keeps_water_out",
]

LABEL_META: dict[tuple[str, str], tuple[str, str, str]] = {
    ("highlight", "fits_as_expected"): ("Fits as Expected", "尺码合适", "size_fit"),
    ("highlight", "good_value_for_the_price"): ("Good Value for the Price", "性价比高", "value_for_money"),
    ("highlight", "holds_up_well"): ("Holds Up Well", "耐用可靠", "durability"),
    ("highlight", "keeps_water_out"): ("Keeps Water Out", "防水可靠", "waterproof"),
    ("highlight", "works_well_for_use_case"): ("Works Well for Use Case", "场景适用", "other"),
    ("highlight", "good_material_quality"): ("Good Material Quality", "材质质量好", "material"),
    ("highlight", "not_used_yet"): ("Not Used Yet", "未实际使用", "other"),
    ("highlight", "first_impression_positive"): ("First Impression Positive", "初步印象好", "other"),
    ("highlight", "useful_storage_space"): ("Useful Storage Space", "储物设计好", "accessory_storage"),
    ("highlight", "petite_friendly"): ("Petite Friendly", "小个子友好", "size_fit"),
    ("highlight", "overall_satisfied"): ("Overall Satisfied", "整体满意", "other"),
    ("highlight", "lightweight_waders"): ("Lightweight Waders", "轻便", "weight"),
    ("issue", "water_leaks_through"): ("Water Leaks Through", "容易进水", "waterproof"),
    ("issue", "pocket_not_waterproof"): ("Pocket Not Waterproof", "口袋不防水", "accessory_storage"),
    ("issue", "strong_chemical_smell"): ("Strong Chemical Smell", "气味大", "material"),
    ("issue", "runs_too_small"): ("Runs Too Small", "尺码偏小", "size_fit"),
    ("issue", "breaks_easily"): ("Breaks Easily", "耐用性差", "durability"),
    ("issue", "feels_thin_and_flimsy"): ("Feels Thin and Flimsy", "材质偏薄不结实", "material"),
    ("issue", "poor_traction"): ("Poor Traction", "防滑性不足", "grip"),
    ("issue", "not_for_long_walks"): ("Not for Long Walks", "非长时间步行适用", "comfort"),
    ("issue", "missing_wader_hanger"): ("Missing Wader Hanger", "缺少涉水裤挂架", "accessory_storage"),
    ("issue", "missing_accessories"): ("Missing Accessories", "配件缺失", "accessory_storage"),
    ("issue", "soft_soles"): ("Soft Soles", "鞋底偏软", "grip"),
    ("issue", "not_petite_friendly"): ("Not Petite Friendly", "小个子不友好", "size_fit"),
    ("issue", "not_breathable"): ("Not Breathable", "透气性差", "breathability"),
    ("issue", "runs_too_large"): ("Runs Too Large", "尺码偏大", "size_fit"),
    ("issue", "pants_too_long"): ("Pants Too Long", "裤长偏长", "size_fit"),
    ("issue", "gets_hot_quickly"): ("Gets Hot Quickly", "升温快", "temperature_rating"),
    ("issue", "inaccurate_size_chart"): ("Inaccurate Size Chart", "尺码不准", "size_fit"),
}


def _fixture_payload() -> dict[str, Any]:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def _title_from_key(key: str) -> str:
    return " ".join(part.capitalize() for part in key.split("_"))


def _occurrence(sample: dict[str, Any], label: dict[str, Any]) -> dict[str, Any]:
    label_type = str(label["type"])
    canonical = str(label["key"])
    display_en, display_zh, default_aspect = LABEL_META.get(
        (label_type, canonical),
        (_title_from_key(canonical), _title_from_key(canonical), "other"),
    )
    content = str(sample["content"])
    evidence = str(label.get("evidence") or "")
    start = content.lower().find(evidence.lower()) if evidence else -1
    aspect_key = str(label.get("aspect_key") or default_aspect)
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
        "source": str(label.get("source") or "llm"),
        "source_detail": str(label.get("source_detail") or "waders_step2_fixture"),
        "evidence_verified": bool(label.get("verified", start >= 0)),
        "cluster_propagated": bool(label.get("cluster_propagated")),
        "schema_version": CUSTOMER_LABEL_OCCURRENCE_SCHEMA_VERSION,
        "ruleset_version": CUSTOMER_LABEL_OCCURRENCE_RULESET_VERSION,
        "display_allowed": bool(label.get("display_allowed", True)),
    }


def _bad_highlight_occurrences(sample: dict[str, Any]) -> list[dict[str, Any]]:
    labels = sample.get("bad_highlights") or []
    return [
        _occurrence(
            sample,
            {"type": "highlight", "key": key, "evidence": "", "confidence": "low", "source_detail": "bad_four_pack"},
        )
        for key in labels
    ]


def _bad_issue_occurrences(sample: dict[str, Any]) -> list[dict[str, Any]]:
    labels = sample.get("bad_issues") or []
    return [
        _occurrence(
            sample,
            {"type": "issue", "key": key, "evidence": "", "confidence": "low", "source_detail": "bad_issue"},
        )
        for key in labels
    ]


def _comments() -> list[dict[str, Any]]:
    comments: list[dict[str, Any]] = []
    for sample in _fixture_payload()["samples"]:
        occurrences = (
            _bad_highlight_occurrences(sample)
            + _bad_issue_occurrences(sample)
            + [_occurrence(sample, label) for label in sample.get("labels", [])]
        )
        comments.append(
            {
                "id": sample["id"],
                "content": sample["content"],
                "sentiment": sample.get("sentiment", "neutral"),
                "sub_category": "waders",
                "aspects_json": {
                    "customer_label_occurrence_schema_version": CUSTOMER_LABEL_OCCURRENCE_SCHEMA_VERSION,
                    "customer_label_occurrence_ruleset_version": CUSTOMER_LABEL_OCCURRENCE_RULESET_VERSION,
                    "sub_category": "waders",
                    "cluster_propagated": any(item.get("cluster_propagated") for item in occurrences),
                    "customer_label_occurrences": occurrences,
                },
            }
        )
    return comments


def _source_review_keys(occurrences: list[dict[str, Any]], canonical_field: str) -> list[str]:
    keys: list[str] = []
    for occurrence in occurrences:
        if not occurrence.get("source_review_allowed"):
            continue
        assert occurrence.get("verified_evidence") is True
        assert occurrence.get("evidence_verified") is True
        assert occurrence.get("evidence_span")
        assert occurrence.get("cluster_propagated") is False
        assert occurrence.get("legacy_fallback") is False
        key = str(occurrence.get(canonical_field) or occurrence.get("canonical_label_key") or "")
        if key and key not in keys:
            keys.append(key)
    return keys


def test_waders_step2_single_review_detail_uses_verified_source_review_gate() -> None:
    samples = {sample["id"]: sample for sample in _fixture_payload()["samples"]}
    for comment in _comments():
        sample = samples[comment["id"]]
        issue_keys = _source_review_keys(iter_specific_issue_occurrences(comment, locale="en"), "canonical_issue_key")
        highlight_keys = _source_review_keys(
            iter_customer_highlight_occurrences(comment, locale="en"),
            "canonical_highlight_key",
        )

        assert issue_keys == sample["expected_issue_keys"], sample["id"]
        assert highlight_keys == sample["expected_highlight_keys"], sample["id"]
        assert len(customer_issue_tags_for_comment(comment, locale="en")) == len(issue_keys)
        assert len(customer_highlight_tags_for_comment(comment, locale="en")) == len(highlight_keys)


def test_waders_step2_top_rows_drop_no_evidence_cluster_legacy_and_context_conflicts() -> None:
    comments = _comments()
    issue_rows = build_specific_issue_rows(comments, locale="en", limit=50)
    highlight_rows = build_customer_highlight_rows(comments, locale="en", limit=50)
    issue_keys = {row["canonical_issue_key"] for row in issue_rows}
    highlight_keys = {row["canonical_highlight_key"] for row in highlight_rows}

    for key in FOUR_PACK_HIGHLIGHTS:
        row = next((item for item in highlight_rows if item["canonical_highlight_key"] == key), None)
        if row:
            assert row["source_review_occurrence_count"] == row["mention_count"]
            assert row["unverified_occurrence_count"] >= 0

    assert "water_leaks_through" in issue_keys
    water = next(row for row in issue_rows if row["canonical_issue_key"] == "water_leaks_through")
    assert water["mention_count"] == 4
    assert all("No leaks" not in span for span in water["evidence_spans"])
    assert all("leak proof" not in span.lower() for span in water["evidence_spans"])
    assert all("phone case" not in span.lower() for span in water["evidence_spans"])
    assert all("old pair" not in span.lower() and "old waders" not in span.lower() for span in water["evidence_spans"])

    pocket = next(row for row in issue_rows if row["canonical_issue_key"] == "pocket_not_waterproof")
    assert pocket["aspect_keys"] == ["accessory_storage"]
    assert "keeps_water_out" in highlight_keys
    assert "fits_as_expected" in highlight_keys
    assert "holds_up_well" in highlight_keys


def test_waders_step2_duplicate_occurrences_count_once_per_review_but_audit_raw_count() -> None:
    rows = build_specific_issue_rows(_comments(), locale="en", limit=50)
    runs_small = next(row for row in rows if row["canonical_issue_key"] == "runs_too_small")

    assert runs_small["mention_count"] == 3
    assert runs_small["raw_occurrence_count"] == 4
    assert "boot_fit" in runs_small["aspect_keys"]
    assert "size_fit" in runs_small["aspect_keys"]


def test_waders_step2_raw_and_top_export_include_highlight_occurrence_audit_fields() -> None:
    comments = _comments()
    headers, rows = _build_comments_data(comments, include_specific_issue=True)

    for header in (
        "客户亮点",
        "Canonical Highlight Key",
        "Highlight Confidence",
        "Highlight Evidence Verified",
        "Highlight Cluster Propagated",
    ):
        assert header in headers

    by_id = {comment["id"]: row for comment, row in zip(comments, rows)}
    row_15 = by_id["row-15-not-used"]
    assert "keeps_water_out" in row_15[headers.index("Canonical Highlight Key")]
    assert "false" in row_15[headers.index("Highlight Evidence Verified")]
    assert "未实际使用" in row_15[headers.index("亮点标签")]

    issue_headers, issue_rows = _build_specific_issue_top10_data(comments)
    highlight_headers, highlight_rows = _build_customer_highlight_top10_data(comments)
    assert "Canonical Issue Key" in issue_headers
    assert "Canonical Highlight Key" in highlight_headers

    issue_by_key = {row[issue_headers.index("Canonical Issue Key")]: row for row in issue_rows}
    highlight_by_key = {row[highlight_headers.index("Canonical Highlight Key")]: row for row in highlight_rows}
    water = issue_by_key["water_leaks_through"]
    keeps_water = highlight_by_key["keeps_water_out"]
    assert water[issue_headers.index("Evidence Verified")] == "true"
    assert water[issue_headers.index("Cluster Propagated")] == "false"
    assert keeps_water[highlight_headers.index("Evidence Verified")] == "true"
    assert keeps_water[highlight_headers.index("Cluster Propagated")] == "false"
