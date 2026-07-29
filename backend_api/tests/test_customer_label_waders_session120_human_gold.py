from __future__ import annotations

import json
from collections import Counter, defaultdict
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
    iter_customer_highlight_occurrences,
    iter_specific_issue_occurrences,
)
from review_analyzer.exporter import _build_comments_data, _build_label_audit_data

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "customer_label_waders_session120_human_gold.json"

DISPLAY_META: dict[tuple[str, str], tuple[str, str, str]] = {
    ("issue", "water_leaks_through"): ("Water Leaks Through", "容易进水", "waterproof"),
    ("issue", "breaks_easily"): ("Breaks Easily", "容易损坏", "durability"),
    ("issue", "not_breathable"): ("Not Breathable", "透气性差", "breathability"),
    ("issue", "quality_control_storage_issue"): ("Quality Control / Storage Issue", "品控/仓储问题", "shipping_damage"),
    ("issue", "quality_problem"): ("Quality Problem", "质量问题", "build_quality"),
    ("issue", "size_fit_problem"): ("Size/Fit Problem", "尺码/版型问题", "size_fit"),
    ("issue", "soft_soles"): ("Soft Soles", "鞋底偏软", "grip"),
    ("issue", "strong_chemical_smell"): ("Strong Chemical Smell", "化学气味重", "material"),
    ("highlight", "fits_as_expected"): ("Fits as Expected", "尺码合适", "size_fit"),
    ("highlight", "good_material_quality"): ("Good Material Quality", "材质质量好", "material"),
    ("highlight", "good_value_for_the_price"): ("Good Value for the Price", "性价比高", "value_for_money"),
    ("highlight", "holds_up_well"): ("Holds Up Well", "耐用性高", "durability"),
    ("highlight", "keeps_water_out"): ("Keeps Water Out", "防水可靠", "waterproof"),
    ("highlight", "lightweight_waders"): ("Lightweight Waders", "轻便", "weight"),
    ("highlight", "looks_good"): ("Looks Good", "外观好看", "aesthetics"),
    ("highlight", "not_used_yet"): ("Not Used Yet", "未实际使用", "other"),
    ("highlight", "overall_satisfied"): ("Overall Satisfied", "整体满意", "other"),
    ("highlight", "useful_storage_space"): ("Useful Storage Space", "收纳空间实用", "accessory_storage"),
    ("highlight", "works_well_for_use_case"): ("Works Well for Use Case", "场景适用", "other"),
}


def _fixture_payload() -> dict[str, Any]:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def _title_from_key(key: str) -> str:
    return " ".join(part.capitalize() for part in key.split("_"))


def _occurrence(sample: dict[str, Any], label: dict[str, Any]) -> dict[str, Any]:
    label_type = str(label["type"])
    canonical = str(label["key"])
    display_en, display_zh, default_aspect = DISPLAY_META.get(
        (label_type, canonical),
        (_title_from_key(canonical), _title_from_key(canonical), "other"),
    )
    content = str(sample["content"])
    evidence = str(label.get("evidence") or "")
    start = content.lower().find(evidence.lower()) if evidence else -1
    return {
        "comment_id": sample["id"],
        "type": label_type,
        "raw_label": display_en,
        "canonical_label_key": canonical,
        "display_label_en": display_en,
        "display_label_zh": display_zh,
        "aspect_key": str(label.get("aspect_key") or default_aspect),
        "evidence_span": evidence,
        "evidence_start": start,
        "evidence_end": start + len(evidence) if start >= 0 else -1,
        "confidence": str(label.get("confidence") or "high"),
        "source": str(label.get("source") or "llm"),
        "source_detail": str(label.get("source_detail") or "session120_human_gold_synthetic"),
        "evidence_verified": bool(label.get("verified", start >= 0)),
        "cluster_propagated": bool(label.get("cluster_propagated")),
        "schema_version": CUSTOMER_LABEL_OCCURRENCE_SCHEMA_VERSION,
        "ruleset_version": CUSTOMER_LABEL_OCCURRENCE_RULESET_VERSION,
        "display_allowed": bool(label.get("display_allowed", True)),
    }


def _comment(sample: dict[str, Any], extra_occurrences: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    occurrences = [_occurrence(sample, item) for item in extra_occurrences or []]
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


def _frontstage_occurrences(comment: dict[str, Any], label_type: str) -> list[dict[str, Any]]:
    iterator = iter_specific_issue_occurrences if label_type == "issue" else iter_customer_highlight_occurrences
    occurrences: list[dict[str, Any]] = []
    for occurrence in iterator(comment, locale="en"):
        if not occurrence.get("source_review_allowed"):
            continue
        assert occurrence.get("display_allowed") is True
        assert occurrence.get("verified_evidence") is True
        assert occurrence.get("evidence_verified") is True
        assert occurrence.get("cluster_propagated") is False
        assert occurrence.get("legacy_fallback") is False
        assert occurrence.get("aspect_allowed") is not False
        assert occurrence.get("context_allowed") is not False
        evidence = str(occurrence.get("evidence_span") or "")
        assert evidence
        assert evidence.lower() in str(comment["content"]).lower()
        occurrences.append(occurrence)
    return occurrences


def _frontstage_keys(comment: dict[str, Any], label_type: str) -> list[str]:
    canonical_field = "canonical_issue_key" if label_type == "issue" else "canonical_highlight_key"
    keys: list[str] = []
    for occurrence in _frontstage_occurrences(comment, label_type):
        key = str(occurrence.get(canonical_field) or "")
        if key and key not in keys:
            keys.append(key)
    return keys


def _split_export_keys(value: str) -> set[str]:
    return {item.strip() for item in str(value or "").split(",") if item.strip()}


def test_session120_human_gold_fixture_has_required_review_fields() -> None:
    payload = _fixture_payload()
    assert payload["expected_summary"]["review_count"] == 50
    assert len(payload["samples"]) == 50

    required_fields = {
        "id",
        "content",
        "human_issue_keys",
        "human_highlight_keys",
        "local_current_output",
        "false_positive",
        "false_negative",
        "wrong_aspect",
        "wrong_evidence",
    }
    for sample in payload["samples"]:
        assert required_fields <= sample.keys(), sample["id"]
        assert "issue_keys" in sample["local_current_output"], sample["id"]
        assert "highlight_keys" in sample["local_current_output"], sample["id"]
        assert isinstance(sample["wrong_aspect"], list), sample["id"]
        assert isinstance(sample["wrong_evidence"], list), sample["id"]


def test_session120_human_gold_exact_precision_and_recall() -> None:
    payload = _fixture_payload()
    comments = _comments()
    summary = Counter()

    for sample, comment in zip(payload["samples"], comments):
        expected_issue = set(sample["human_issue_keys"])
        expected_highlight = set(sample["human_highlight_keys"])
        actual_issue = set(_frontstage_keys(comment, "issue"))
        actual_highlight = set(_frontstage_keys(comment, "highlight"))
        fixture_issue = set(sample["local_current_output"]["issue_keys"])
        fixture_highlight = set(sample["local_current_output"]["highlight_keys"])

        assert actual_issue == fixture_issue, sample["id"]
        assert actual_highlight == fixture_highlight, sample["id"]
        assert actual_issue == expected_issue, sample["id"]
        assert actual_highlight == expected_highlight, sample["id"]
        assert not set(sample["false_positive"]["issue_keys"]), sample["id"]
        assert not set(sample["false_positive"]["highlight_keys"]), sample["id"]
        assert not set(sample["false_negative"]["issue_keys"]), sample["id"]
        assert not set(sample["false_negative"]["highlight_keys"]), sample["id"]

        summary["both_exact_set"] += int(actual_issue == expected_issue and actual_highlight == expected_highlight)
        summary["issue_exact_set"] += int(actual_issue == expected_issue)
        summary["highlight_exact_set"] += int(actual_highlight == expected_highlight)
        summary["issue_tp"] += len(actual_issue & expected_issue)
        summary["issue_fp"] += len(actual_issue - expected_issue)
        summary["issue_fn"] += len(expected_issue - actual_issue)
        summary["highlight_tp"] += len(actual_highlight & expected_highlight)
        summary["highlight_fp"] += len(actual_highlight - expected_highlight)
        summary["highlight_fn"] += len(expected_highlight - actual_highlight)

    for key, expected_value in payload["expected_summary"].items():
        if key == "review_count":
            continue
        assert summary[key] == expected_value, key


def test_session120_recall_cases_and_hard_negative_false_positives() -> None:
    by_id = {sample["id"]: sample for sample in _fixture_payload()["samples"]}

    recall_expectations = {
        "session120-row-1": ({"size_fit_problem"}, set()),
        "session120-row-2": ({"breaks_easily"}, {"good_value_for_the_price"}),
        "session120-row-5": ({"quality_control_storage_issue"}, set()),
        "session120-row-10": ({"size_fit_problem", "quality_problem"}, set()),
        "session120-row-19": ({"size_fit_problem", "strong_chemical_smell"}, set()),
        "session120-row-22": ({"soft_soles"}, {"keeps_water_out"}),
        "session120-row-33": ({"not_breathable"}, set()),
        "session120-row-44": (set(), {"works_well_for_use_case", "useful_storage_space"}),
    }
    for sample_id, (issue_keys, highlight_keys) in recall_expectations.items():
        comment = _comment(by_id[sample_id])
        assert issue_keys <= set(_frontstage_keys(comment, "issue")), sample_id
        assert highlight_keys <= set(_frontstage_keys(comment, "highlight")), sample_id

    fp_guards = {
        "session120-row-6": {"good_material_quality", "not_used_yet"},
        "session120-row-8": {"good_material_quality"},
        "session120-row-19": {"good_value_for_the_price", "works_well_for_use_case"},
        "session120-row-31": {"good_material_quality", "keeps_water_out", "not_used_yet"},
        "session120-row-42": {"works_well_for_use_case"},
    }
    for sample_id, blocked_highlights in fp_guards.items():
        comment = _comment(by_id[sample_id])
        assert not (set(_frontstage_keys(comment, "highlight")) & blocked_highlights), sample_id


def test_session120_not_used_yet_is_audit_only() -> None:
    audit_not_used_rows: set[str] = set()
    for sample in _fixture_payload()["samples"]:
        comment = _comment(sample)
        assert "not_used_yet" not in _frontstage_keys(comment, "highlight"), sample["id"]
        for occurrence in iter_customer_highlight_occurrences(comment, locale="en"):
            if occurrence.get("canonical_highlight_key") == "not_used_yet":
                assert occurrence.get("source_review_allowed") is False
                assert occurrence.get("context_allowed") is False
                audit_not_used_rows.add(sample["id"])

    assert {"session120-row-3", "session120-row-6", "session120-row-31"} <= audit_not_used_rows


def test_session120_old_raw_occurrence_false_positive_guards() -> None:
    by_id = {sample["id"]: sample for sample in _fixture_payload()["samples"]}
    cases = [
        (
            "session120-row-8",
            [{"type": "highlight", "key": "feels_well_made", "aspect_key": "material", "evidence": "appear well made"}],
            {"good_material_quality"},
        ),
        (
            "session120-row-19",
            [{"type": "highlight", "key": "works_well_for_use_case", "aspect_key": "other", "evidence": "Alaska"}],
            {"works_well_for_use_case"},
        ),
        (
            "session120-row-42",
            [{"type": "highlight", "key": "works_well_for_use_case", "aspect_key": "other", "evidence": "surf fishing"}],
            {"works_well_for_use_case"},
        ),
        (
            "session120-row-31",
            [{"type": "highlight", "key": "not_used_yet", "aspect_key": "other", "evidence": "never wore them in the water"}],
            {"not_used_yet"},
        ),
    ]
    for sample_id, extra_occurrences, blocked in cases:
        comment = _comment(by_id[sample_id], extra_occurrences=extra_occurrences)
        assert not (set(_frontstage_keys(comment, "highlight")) & blocked), sample_id


def test_session120_evidence_spans_are_locatable_and_cluster_is_audit_only() -> None:
    sample = next(item for item in _fixture_payload()["samples"] if item["id"] == "session120-row-3")
    comment = _comment(
        sample,
        extra_occurrences=[
            {
                "type": "highlight",
                "key": "keeps_water_out",
                "aspect_key": "waterproof",
                "evidence": "leakproof",
                "cluster_propagated": True,
            }
        ],
    )

    assert "keeps_water_out" not in _frontstage_keys(comment, "highlight")
    propagated = [
        occurrence
        for occurrence in iter_customer_highlight_occurrences(comment, locale="en")
        if occurrence.get("canonical_highlight_key") == "keeps_water_out"
    ]
    assert propagated
    assert all(occurrence.get("source_review_allowed") is False for occurrence in propagated)

    headers, rows = _build_comments_data([comment], include_specific_issue=True)
    audit_headers, audit_rows = _build_label_audit_data([comment])
    row = rows[0]
    audit_row = audit_rows[0]
    assert "防水可靠" not in row[headers.index("客户亮点")]
    assert "keeps_water_out" in audit_row[audit_headers.index("Audit Canonical Highlight Key")]
    assert "Highlight Cluster Propagated" not in headers
    assert "true" in audit_row[audit_headers.index("Audit Highlight Cluster Propagated")]


def test_session120_raw_top_and_single_tag_download_scope_are_consistent() -> None:
    comments = _comments()
    issue_by_key: dict[str, set[str]] = defaultdict(set)
    highlight_by_key: dict[str, set[str]] = defaultdict(set)

    for comment in comments:
        for occurrence in _frontstage_occurrences(comment, "issue"):
            issue_by_key[str(occurrence["canonical_issue_key"])].add(str(comment["id"]))
        for occurrence in _frontstage_occurrences(comment, "highlight"):
            highlight_by_key[str(occurrence["canonical_highlight_key"])].add(str(comment["id"]))

    headers, rows = _build_comments_data(comments, include_specific_issue=True)
    by_id = {comment["id"]: row for comment, row in zip(comments, rows)}
    for comment in comments:
        row = by_id[comment["id"]]
        assert _split_export_keys(row[headers.index("客户痛点")]) == {
            str(occurrence.get("specific_issue_zh") or occurrence["specific_issue"])
            for occurrence in _frontstage_occurrences(comment, "issue")
            if str(occurrence["canonical_issue_key"]) in issue_by_key
        }
        assert _split_export_keys(row[headers.index("客户亮点")]) == {
            str(occurrence.get("customer_highlight_zh") or occurrence["customer_highlight"])
            for occurrence in _frontstage_occurrences(comment, "highlight")
            if str(occurrence["canonical_highlight_key"]) in highlight_by_key
        }

    issue_rows = build_specific_issue_rows(comments, locale="en", limit=100)
    highlight_rows = build_customer_highlight_rows(comments, locale="en", limit=100)
    assert {row["canonical_issue_key"] for row in issue_rows} == set(issue_by_key)
    assert {row["canonical_highlight_key"] for row in highlight_rows} == set(highlight_by_key)
    for row in issue_rows:
        key = str(row["canonical_issue_key"])
        assert row["mention_count"] == len(issue_by_key[key])
        assert row["source_review_occurrence_count"] == len(issue_by_key[key])
    for row in highlight_rows:
        key = str(row["canonical_highlight_key"])
        assert row["mention_count"] == len(highlight_by_key[key])
        assert row["source_review_occurrence_count"] == len(highlight_by_key[key])
