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
    iter_customer_highlight_occurrences,
    iter_specific_issue_occurrences,
)
from review_analyzer.exporter import _build_comments_data

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "customer_label_waders_session121_blind_regression.json"


def _fixture_payload() -> dict[str, Any]:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def _comment(sample: dict[str, Any]) -> dict[str, Any]:
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
            "customer_label_occurrences": [],
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
        assert occurrence.get("legacy_fallback") is False
        assert occurrence.get("aspect_allowed") is not False
        assert occurrence.get("context_allowed") is not False
        evidence = str(occurrence.get("evidence_span") or "")
        assert evidence
        assert evidence.lower() in str(comment["content"]).lower()
        key = str(occurrence.get(canonical_field) or "")
        if key and key not in keys:
            keys.append(key)
    return keys


def test_session121_blind_regression_frontstage_keys() -> None:
    for sample, comment in zip(_fixture_payload()["samples"], _comments()):
        issue_keys = set(_frontstage_keys(comment, "issue"))
        highlight_keys = set(_frontstage_keys(comment, "highlight"))

        assert set(sample["required_issue_keys"]) <= issue_keys, sample["id"]
        assert set(sample["required_highlight_keys"]) <= highlight_keys, sample["id"]
        assert not (issue_keys & set(sample["blocked_issue_keys"])), sample["id"]
        assert not (highlight_keys & set(sample["blocked_highlight_keys"])), sample["id"]


def test_session121_blind_regression_top_and_raw_scope() -> None:
    comments = _comments()
    issue_rows = build_specific_issue_rows(comments, locale="en", limit=50)
    highlight_rows = build_customer_highlight_rows(comments, locale="en", limit=50)
    issue_keys = {row["canonical_issue_key"] for row in issue_rows}
    highlight_keys = {row["canonical_highlight_key"] for row in highlight_rows}

    assert "water_leaks_through" in issue_keys
    assert "pocket_not_waterproof" in issue_keys
    assert "fits_as_expected" in highlight_keys
    assert all(row.get("evidence_verified") for row in issue_rows + highlight_rows)
    assert not any(row.get("cluster_propagated") for row in issue_rows + highlight_rows)

    headers, rows = _build_comments_data(comments, include_specific_issue=True)
    by_id = {comment["id"]: row for comment, row in zip(comments, rows)}
    negative_dry = by_id["session121-did-not-keep-dry"]
    assert "容易进水" in negative_dry[headers.index("客户痛点")]
    assert "防水可靠" not in negative_dry[headers.index("客户亮点")]
    pocket = by_id["session121-pocket-not-waterproof"]
    assert "口袋不防水" in pocket[headers.index("客户痛点")]
    assert "容易进水" not in pocket[headers.index("客户痛点")]
