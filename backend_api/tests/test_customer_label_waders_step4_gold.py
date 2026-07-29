from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from backend_api.app.services.customer_label_catalog import (
    CustomerLabelCatalogState,
    set_customer_label_catalog_state_for_tests,
)
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
from review_analyzer.exporter import _build_comments_data

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "customer_label_waders_step4_gold.json"

DISPLAY_META: dict[tuple[str, str], tuple[str, str, str]] = {
    ("issue", "water_leaks_through"): ("Water Leaks Through", "容易进水", "waterproof"),
    ("issue", "pocket_not_waterproof"): ("Pocket Not Waterproof", "口袋不防水", "accessory_storage"),
    ("issue", "breaks_easily"): ("Breaks Easily", "容易损坏", "durability"),
    ("issue", "boots_too_stiff"): ("Boots Too Stiff", "靴子过硬", "boot_fit"),
    ("issue", "missing_wader_hanger"): ("Missing Wader Hanger", "缺少涉水裤挂架", "accessory_storage"),
    ("issue", "overall_dissatisfied"): ("Overall Dissatisfied", "整体不满意", "other"),
    ("issue", "strong_chemical_smell"): ("Strong Chemical Smell", "化学气味重", "material"),
    ("issue", "feels_thin_and_flimsy"): ("Feels Thin and Flimsy", "材质偏薄不结实", "material"),
    ("issue", "inaccurate_size_chart"): ("Inaccurate Size Chart", "尺码不准", "size_fit"),
    ("issue", "runs_too_small"): ("Runs Too Small", "尺码偏小", "size_fit"),
    ("issue", "accessories_not_as_advertised"): (
        "Accessories Not as Advertised",
        "配件与描述不符",
        "accessory_storage",
    ),
    ("issue", "missing_accessories"): ("Missing Accessories", "配件缺失", "accessory_storage"),
    ("highlight", "fits_as_expected"): ("Fits as Expected", "尺码合适", "size_fit"),
    ("highlight", "keeps_water_out"): ("Keeps Water Out", "防水可靠", "waterproof"),
    ("highlight", "good_value_for_the_price"): ("Good Value for the Price", "性价比高", "value_for_money"),
    ("highlight", "holds_up_well"): ("Holds Up Well", "耐用性高", "durability"),
    ("highlight", "good_material_quality"): ("Good Material Quality", "材质质量好", "material"),
    ("highlight", "not_used_yet"): ("Not Used Yet", "未实际使用", "other"),
    ("highlight", "first_impression_positive"): ("First Impression Positive", "初步印象良好", "other"),
}


def _fixture_payload() -> dict[str, Any]:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def _title_from_key(key: str) -> str:
    return " ".join(part.capitalize() for part in key.split("_"))


def _occurrence(sample: dict[str, Any], row: dict[str, Any]) -> dict[str, Any]:
    label_type = str(row["type"])
    canonical = str(row["key"])
    default = DISPLAY_META.get((label_type, canonical))
    display_en, display_zh, default_aspect = default or (_title_from_key(canonical), _title_from_key(canonical), "other")
    content = str(sample["content"])
    evidence = str(row.get("evidence") or "")
    start = content.lower().find(evidence.lower()) if evidence else -1
    verified = bool(row.get("verified", start >= 0))
    cluster = bool(row.get("cluster_propagated"))
    return {
        "comment_id": sample["id"],
        "type": label_type,
        "raw_label": display_en,
        "canonical_label_key": canonical,
        "display_label_en": display_en,
        "display_label_zh": display_zh,
        "aspect_key": str(row.get("aspect_key") or default_aspect),
        "evidence_span": evidence,
        "evidence_start": start,
        "evidence_end": start + len(evidence) if start >= 0 else -1,
        "confidence": str(row.get("confidence") or "high"),
        "source": "llm",
        "source_detail": "session119_current_output",
        "evidence_verified": verified,
        "cluster_propagated": cluster,
        "schema_version": CUSTOMER_LABEL_OCCURRENCE_SCHEMA_VERSION,
        "ruleset_version": CUSTOMER_LABEL_OCCURRENCE_RULESET_VERSION,
        "display_allowed": True,
    }


def _comment(sample: dict[str, Any]) -> dict[str, Any]:
    occurrences = [_occurrence(sample, item) for item in sample.get("current_occurrences", [])]
    return {
        "id": sample["id"],
        "content": sample["content"],
        "rating": 3,
        "sub_category": "waders",
        "category": "waders",
        "aspects_json": {
            "customer_label_occurrence_schema_version": CUSTOMER_LABEL_OCCURRENCE_SCHEMA_VERSION,
            "customer_label_occurrence_ruleset_version": CUSTOMER_LABEL_OCCURRENCE_RULESET_VERSION,
            "sub_category": "waders",
            "customer_label_occurrences": occurrences,
        },
    }


def _comments() -> list[dict[str, Any]]:
    set_customer_label_catalog_state_for_tests(CustomerLabelCatalogState())
    return [_comment(sample) for sample in _fixture_payload()["samples"]]


def _frontstage_keys(comment: dict[str, Any], label_type: str) -> list[str]:
    iterator = iter_specific_issue_occurrences if label_type == "issue" else iter_customer_highlight_occurrences
    canonical_field = "canonical_issue_key" if label_type == "issue" else "canonical_highlight_key"
    keys: list[str] = []
    for occurrence in iterator(comment, locale="en"):
        if not occurrence.get("source_review_allowed"):
            continue
        assert occurrence.get("verified_evidence") is True
        assert occurrence.get("evidence_verified") is True
        assert occurrence.get("cluster_propagated") is False
        assert occurrence.get("evidence_span")
        assert str(occurrence["evidence_span"]).lower() in str(comment["content"]).lower()
        key = str(occurrence.get(canonical_field) or "")
        if key and key not in keys:
            keys.append(key)
    return keys


def test_waders_step4_gold_exact_sets_and_hard_negatives() -> None:
    samples = _fixture_payload()["samples"]
    for sample, comment in zip(samples, _comments()):
        issue_keys = _frontstage_keys(comment, "issue")
        highlight_keys = _frontstage_keys(comment, "highlight")

        assert set(issue_keys) == set(sample["expected_issue_keys"]), sample["id"]
        assert set(highlight_keys) == set(sample["expected_highlight_keys"]), sample["id"]
        assert len(issue_keys) == len(set(issue_keys)), sample["id"]
        assert len(highlight_keys) == len(set(highlight_keys)), sample["id"]
        assert not (set(issue_keys) & set(sample.get("blocked_issue_keys", []))), sample["id"]
        assert not (set(highlight_keys) & set(sample.get("blocked_highlight_keys", []))), sample["id"]
        assert len(customer_issue_tags_for_comment(comment, locale="en")) == len(issue_keys)
        assert len(customer_highlight_tags_for_comment(comment, locale="en")) == len(highlight_keys)


def test_waders_step4_precision_recall_summary_for_focused_gold() -> None:
    tp = fp = fn = 0
    for sample, comment in zip(_fixture_payload()["samples"], _comments()):
        actual = set(_frontstage_keys(comment, "issue")) | set(_frontstage_keys(comment, "highlight"))
        expected = set(sample["expected_issue_keys"]) | set(sample["expected_highlight_keys"])
        tp += len(actual & expected)
        fp += len(actual - expected)
        fn += len(expected - actual)

    assert fp == 0
    assert fn == 0
    assert tp >= 30


def test_waders_step4_top_rows_and_raw_export_are_frontstage_only() -> None:
    comments = _comments()
    issue_rows = build_specific_issue_rows(comments, locale="en", limit=50)
    highlight_rows = build_customer_highlight_rows(comments, locale="en", limit=50)

    issue_by_key = {row["canonical_issue_key"]: row for row in issue_rows}
    highlight_by_key = {row["canonical_highlight_key"]: row for row in highlight_rows}
    assert "water_leaks_through" in issue_by_key
    assert issue_by_key["water_leaks_through"]["propagated_occurrence_count"] == 0
    assert "fits_as_expected" in highlight_by_key
    assert highlight_by_key["fits_as_expected"]["source_review_occurrence_count"] == 5

    headers, rows = _build_comments_data(comments, include_specific_issue=True)
    by_id = {comment["id"]: row for comment, row in zip(comments, rows)}
    generic_negative = by_id["row-100-generic-negative"]
    assert generic_negative[headers.index("Canonical Highlight Key")] == ""
    assert "fits_as_expected" in generic_negative[headers.index("Audit Canonical Highlight Key")]
    assert "true" not in generic_negative[headers.index("Highlight Evidence Verified")]
    assert "true" in generic_negative[headers.index("Audit Highlight Cluster Propagated")]
