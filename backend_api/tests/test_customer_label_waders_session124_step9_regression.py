from __future__ import annotations

from typing import Any

import pytest

from backend_api.app.services.customer_label_catalog import (
    CustomerLabelCatalogState,
    set_customer_label_catalog_state_for_tests,
)
from backend_api.app.services.specific_issue import (
    CUSTOMER_LABEL_OCCURRENCE_RULESET_VERSION,
    CUSTOMER_LABEL_OCCURRENCE_SCHEMA_VERSION,
    iter_customer_highlight_occurrences,
    iter_specific_issue_occurrences,
)
from review_analyzer.exporter import _build_comments_data

DISPLAY_META: dict[tuple[str, str], tuple[str, str, str]] = {
    ("issue", "breaks_easily"): ("Breaks Easily", "容易损坏", "durability"),
    ("issue", "missing_wader_hanger"): ("Missing Wader Hanger", "缺少涉水裤挂架", "accessory_storage"),
    ("issue", "pocket_not_waterproof"): ("Pocket Not Waterproof", "口袋不防水", "accessory_storage"),
    ("issue", "poor_traction"): ("Poor Traction", "防滑性不足", "grip"),
    ("issue", "size_fit_problem"): ("Size/Fit Problem", "尺码/版型问题", "size_fit"),
    ("issue", "water_leaks_through"): ("Water Leaks Through", "容易进水", "waterproof"),
    ("highlight", "comfortable_to_wear"): ("Comfortable To Wear", "穿着舒适", "comfort"),
    ("highlight", "fits_as_expected"): ("Fits as Expected", "尺码合适", "size_fit"),
    ("highlight", "holds_up_well"): ("Holds Up Well", "耐用性高", "durability"),
}


@pytest.fixture(autouse=True)
def reset_catalog_state() -> None:
    set_customer_label_catalog_state_for_tests(CustomerLabelCatalogState())
    yield
    set_customer_label_catalog_state_for_tests(None)


def _comment(
    content: str,
    *,
    comment_id: str = "session124-step9-regression",
    occurrences: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    return {
        "id": comment_id,
        "content": content,
        "rating": 4,
        "category": "outdoor",
        "sub_category": "waders",
        "aspects_json": {
            "customer_label_occurrence_schema_version": CUSTOMER_LABEL_OCCURRENCE_SCHEMA_VERSION,
            "customer_label_occurrence_ruleset_version": CUSTOMER_LABEL_OCCURRENCE_RULESET_VERSION,
            "sub_category": "waders",
            "customer_label_occurrences": occurrences or [],
        },
    }


def _stored_occurrence(label_type: str, canonical: str, evidence: str, content: str) -> dict[str, Any]:
    display_en, display_zh, aspect_key = DISPLAY_META[(label_type, canonical)]
    start = content.lower().find(evidence.lower())
    return {
        "comment_id": "session124-step9-regression",
        "type": label_type,
        "raw_label": display_en,
        "canonical_label_key": canonical,
        "display_label_en": display_en,
        "display_label_zh": display_zh,
        "aspect_key": aspect_key,
        "evidence_span": evidence,
        "evidence_start": start,
        "evidence_end": start + len(evidence) if start >= 0 else -1,
        "confidence": "high",
        "source": "rule",
        "source_detail": "session124_stored_occurrence_fixture",
        "evidence_verified": start >= 0,
        "cluster_propagated": False,
        "schema_version": CUSTOMER_LABEL_OCCURRENCE_SCHEMA_VERSION,
        "ruleset_version": CUSTOMER_LABEL_OCCURRENCE_RULESET_VERSION,
        "display_allowed": True,
    }


def _frontstage_keys(comment: dict[str, Any], label_type: str) -> set[str]:
    iterator = iter_specific_issue_occurrences if label_type == "issue" else iter_customer_highlight_occurrences
    canonical_field = "canonical_issue_key" if label_type == "issue" else "canonical_highlight_key"
    keys: set[str] = set()
    for occurrence in iterator(comment, locale="en"):
        if not occurrence.get("source_review_allowed"):
            continue
        assert occurrence.get("verified_evidence") is True
        assert occurrence.get("evidence_verified") is True
        assert occurrence.get("cluster_propagated") is False
        assert occurrence.get("context_allowed") is not False
        keys.add(str(occurrence.get(canonical_field) or ""))
    return keys


def test_session124_step9_content_rules_block_high_confidence_false_positives() -> None:
    break_negation = _comment(
        "Pretty solid for the price. These hold up well and don't tear easily. No leaks."
    )
    assert "breaks_easily" not in _frontstage_keys(break_negation, "issue")
    assert "holds_up_well" in _frontstage_keys(break_negation, "highlight")

    good_hanger = _comment(
        "Worked great, no leaks. The hanger it comes with works great for drying and storage."
    )
    assert "missing_wader_hanger" not in _frontstage_keys(good_hanger, "issue")

    good_traction = _comment(
        "Nice quality for the price. They provide good traction on slippery rocks and keep water out."
    )
    assert "poor_traction" not in _frontstage_keys(good_traction, "issue")

    negated_water = _comment(
        "Overall, no rips or tears in the material and no water seeping in. It made me sweat in hot weather."
    )
    assert "water_leaks_through" not in _frontstage_keys(negated_water, "issue")

    later_negative_update = _comment(
        "So they fit great, boots seem very comfortable. UPDATE: after using them, the boots were horrible, "
        "super tight and uncomfortable. I do not recommend these waders and started the return process."
    )
    assert "fits_as_expected" not in _frontstage_keys(later_negative_update, "highlight")
    assert "comfortable_to_wear" not in _frontstage_keys(later_negative_update, "highlight")

    user_ordering_error = _comment(
        "Although I ordered the wrong size and have to return it. Just make sure you order the right shoe size. "
        "I made that mistake."
    )
    assert "size_fit_problem" not in _frontstage_keys(user_ordering_error, "issue")

    pocket_exists_only = _comment(
        "These are good quality and kept the water out nicely. There's a little breast pocket that I put my watch in."
    )
    assert "pocket_not_waterproof" not in _frontstage_keys(pocket_exists_only, "issue")


@pytest.mark.parametrize(
    ("label_type", "canonical", "evidence", "content"),
    [
        (
            "issue",
            "breaks_easily",
            "these hold up well and don't tear easily",
            "Pretty solid for the price. These hold up well and don't tear easily. No leaks.",
        ),
        (
            "issue",
            "missing_wader_hanger",
            "The hanger it comes with works great for drying and storage",
            "Worked great, no leaks. The hanger it comes with works great for drying and storage.",
        ),
        (
            "issue",
            "poor_traction",
            "provide good traction on slippery rocks",
            "Nice quality. They provide good traction on slippery rocks and keep water out.",
        ),
        (
            "issue",
            "water_leaks_through",
            "seeping in",
            "Overall, no rips or tears in the material and no water seeping in. It made me sweat.",
        ),
        (
            "highlight",
            "fits_as_expected",
            "fit great",
            "So they fit great. UPDATE: the boots were horrible, super tight and uncomfortable. "
            "I do not recommend these waders.",
        ),
        (
            "highlight",
            "comfortable_to_wear",
            "very comfortable",
            "Boots seem very comfortable. UPDATE: the boots were horrible, super tight and uncomfortable. "
            "I started the return process.",
        ),
        (
            "issue",
            "size_fit_problem",
            "I ordered the wrong size",
            "Although I ordered the wrong size and have to return it. I made that mistake.",
        ),
        (
            "issue",
            "pocket_not_waterproof",
            "There's a little breast pocket",
            "These kept the water out nicely. There's a little breast pocket that I put my watch in.",
        ),
    ],
)
def test_session124_step9_stored_occurrence_projection_blocks_bad_frontstage(
    label_type: str,
    canonical: str,
    evidence: str,
    content: str,
) -> None:
    comment = _comment(content, occurrences=[_stored_occurrence(label_type, canonical, evidence, content)])

    assert canonical not in _frontstage_keys(comment, label_type)


def test_session124_step9_raw_export_frontstage_fields_dedupe_duplicate_labels() -> None:
    content = "These held up great, and after several uses they still seem durable."
    comment = _comment(
        content,
        occurrences=[
            _stored_occurrence("highlight", "holds_up_well", "held up great", content),
            _stored_occurrence("highlight", "holds_up_well", "durable", content),
        ],
    )

    headers, rows = _build_comments_data([comment], include_specific_issue=True)
    row = rows[0]
    highlight_text = row[headers.index("客户亮点")]
    evidence_text = row[headers.index("亮点证据")]

    assert highlight_text == "耐用性高"
    assert evidence_text in {"held up great", "durable"}
