from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

from backend_api.app.services.review_fragment_contract import (
    MODULE_ACCESSORY_OR_BUNDLE,
    MODULE_COMPARISON_OR_OTHER_PRODUCT,
    MODULE_CONSUMER_PROFILE,
    MODULE_LOGISTICS_SUPPORT,
    MODULE_PRODUCT_HIGHLIGHT,
    MODULE_PRODUCT_ISSUE,
    SCOPE_ACCESSORY_ONLY,
    SCOPE_CURRENT_PRODUCT,
    SCOPE_LOGISTICS_SUPPORT,
    SCOPE_NON_PRODUCT_CONTEXT,
    SCOPE_OTHER_PRODUCT,
    validate_review_fragment,
)
from backend_api.app.services.review_fragment_taxonomy_whitelist import (
    AGGREGATABLE_TAXONOMY_MODULES,
    REVIEW_FRAGMENT_TAXONOMY_FIXTURE_SCHEMA_VERSION,
    REVIEW_FRAGMENT_TAXONOMY_WHITELIST_VERSION,
    TAXONOMY_STATUS_ALLOWED,
    TAXONOMY_STATUS_MISSING,
    TAXONOMY_STATUS_OUT_OF_SCOPE,
    apply_review_fragment_taxonomy_whitelist,
    resolve_review_fragment_taxonomy_whitelist,
    review_fragment_taxonomy_result_row,
    validate_review_fragment_taxonomy,
)

ROOT = Path(__file__).resolve().parent.parent.parent
FIXTURE_PATH = Path(__file__).parent / "fixtures" / "review_fragment_taxonomy_5_9_2_samples.json"
WADERS_TAXONOMY_PATH = ROOT / "data" / "taxonomy" / "v1.0" / "outdoor" / "waders.yaml"
BED_FRAME_TAXONOMY_PATH = ROOT / "data" / "taxonomy" / "v1.0" / "home" / "床架.yaml"


def _load_fixture() -> dict[str, Any]:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def _load_taxonomy_aspects(path: Path) -> list[dict[str, Any]]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return [
        {
            "key": item["key"],
            "label_zh": item.get("label_zh", ""),
            "boundary_note": item.get("boundary_note", ""),
        }
        for item in data["aspects"]
    ]


def _fixture_resolver(sub_category: str) -> tuple[list[dict[str, Any]], bool]:
    if sub_category == "waders":
        return _load_taxonomy_aspects(WADERS_TAXONOMY_PATH), True
    if sub_category == "床架":
        return _load_taxonomy_aspects(BED_FRAME_TAXONOMY_PATH), True
    return [
        {"key": "waterproof", "label_zh": "fallback bait"},
        {"key": "other", "label_zh": "other"},
    ], False


def _fragment(
    *,
    module: str = MODULE_PRODUCT_ISSUE,
    aspect_key: str = "waterproof",
    scope: str = SCOPE_CURRENT_PRODUCT,
    can_aggregate: bool = True,
    reject_reason: str | None = None,
) -> dict[str, Any]:
    return {
        "fragment_text": "the waders stayed dry",
        "module": module,
        "aspect_key": aspect_key,
        "polarity": "positive" if module == MODULE_PRODUCT_HIGHLIGHT else "negative",
        "evidence_span": "waders stayed dry",
        "confidence": 0.9,
        "current_product_scope": scope,
        "can_aggregate": can_aggregate,
        "reject_reason": reject_reason,
    }


def _actual_taxonomy_rows(sample: dict[str, Any]) -> list[dict[str, Any]]:
    whitelist = resolve_review_fragment_taxonomy_whitelist(
        category=sample.get("category"),
        sub_category=sample.get("sub_category"),
        aspect_resolver=_fixture_resolver,
    )
    seen: set[tuple[str, str, str]] = set()
    rows: list[dict[str, Any]] = []

    for fragment in sample["fragments"]:
        gated = apply_review_fragment_taxonomy_whitelist(fragment, whitelist)
        row = review_fragment_taxonomy_result_row(fragment, whitelist)
        aggregate_key = (
            str(fragment.get("module") or ""),
            str(fragment.get("aspect_key") or ""),
            str(fragment.get("polarity") or ""),
        )
        duplicate = False
        counted = False
        if gated["can_aggregate"] is True and aggregate_key[0] in AGGREGATABLE_TAXONOMY_MODULES:
            if aggregate_key in seen:
                duplicate = True
            else:
                seen.add(aggregate_key)
                counted = True
        rows.append(
            {
                "status": row["status"],
                "can_aggregate": gated["can_aggregate"],
                "reject_reason": gated["reject_reason"],
                "product_aggregate_counted": counted,
                "duplicate_aggregate_aspect": duplicate,
            }
        )

    return rows


def test_resolve_review_fragment_taxonomy_whitelist_uses_taxonomy_hit_only() -> None:
    whitelist = resolve_review_fragment_taxonomy_whitelist(
        category="outdoor",
        sub_category="waders",
        aspect_resolver=_fixture_resolver,
    )

    assert whitelist.taxonomy_source == "category_aspect_taxonomy"
    assert whitelist.taxonomy_hit is True
    assert "waterproof" in whitelist.allowed_aspect_keys
    assert "seam_integrity" in whitelist.allowed_aspect_keys
    assert "other" not in whitelist.allowed_aspect_keys

    missing = resolve_review_fragment_taxonomy_whitelist(
        category="electronics",
        sub_category="earbuds",
        aspect_resolver=_fixture_resolver,
    )
    assert missing.taxonomy_hit is False
    assert missing.allowed_aspect_keys == frozenset()
    assert missing.taxonomy_source == "taxonomy_missing:category_aspect_taxonomy"

    empty = resolve_review_fragment_taxonomy_whitelist(
        category="outdoor",
        sub_category="",
        aspect_resolver=_fixture_resolver,
    )
    assert empty.taxonomy_hit is False
    assert empty.allowed_aspect_keys == frozenset()
    assert empty.taxonomy_source == "taxonomy_missing:sub_category_empty"


def test_allowed_product_issue_and_highlight_can_continue() -> None:
    whitelist = resolve_review_fragment_taxonomy_whitelist(
        category="outdoor",
        sub_category="waders",
        aspect_resolver=_fixture_resolver,
    )

    issue = validate_review_fragment_taxonomy(_fragment(aspect_key="waterproof"), whitelist)
    assert issue.status == TAXONOMY_STATUS_ALLOWED
    assert issue.can_aggregate is True
    assert issue.reject_reason is None

    highlight = validate_review_fragment_taxonomy(
        _fragment(module=MODULE_PRODUCT_HIGHLIGHT, aspect_key="size_fit"),
        whitelist,
    )
    assert highlight.status == TAXONOMY_STATUS_ALLOWED
    assert highlight.can_aggregate is True
    assert highlight.reject_reason is None


def test_out_of_scope_candidate_other_and_missing_fail_closed() -> None:
    """A seller-facing issue key is not a taxonomy aspect at the whitelist boundary."""

    whitelist = resolve_review_fragment_taxonomy_whitelist(
        category="outdoor",
        sub_category="waders",
        aspect_resolver=_fixture_resolver,
    )

    out_of_library = apply_review_fragment_taxonomy_whitelist(
        _fragment(aspect_key="water_leaks_through"),
        whitelist,
    )
    assert out_of_library["can_aggregate"] is False
    assert out_of_library["reject_reason"] == "taxonomy_out_of_scope"

    candidate = apply_review_fragment_taxonomy_whitelist(
        _fragment(aspect_key="candidate:boot_seam_leak"),
        whitelist,
    )
    assert candidate["can_aggregate"] is False
    assert candidate["reject_reason"] == "candidate_pending_review"

    other = apply_review_fragment_taxonomy_whitelist(_fragment(aspect_key="other"), whitelist)
    assert other["can_aggregate"] is False
    assert other["reject_reason"] == "taxonomy_out_of_scope"

    missing_whitelist = resolve_review_fragment_taxonomy_whitelist(
        category="electronics",
        sub_category="earbuds",
        aspect_resolver=_fixture_resolver,
    )
    missing = validate_review_fragment_taxonomy(_fragment(aspect_key="waterproof"), missing_whitelist)
    assert missing.status == TAXONOMY_STATUS_MISSING
    assert missing.can_aggregate is False
    assert missing.reject_reason == "taxonomy_missing"


def test_accessory_and_packaging_aspects_can_aggregate_when_taxonomy_allowed() -> None:
    whitelist = resolve_review_fragment_taxonomy_whitelist(
        category="outdoor",
        sub_category="waders",
        aspect_resolver=_fixture_resolver,
    )

    accessory = validate_review_fragment_taxonomy(
        _fragment(
            module=MODULE_ACCESSORY_OR_BUNDLE,
            aspect_key="accessory_storage",
            scope=SCOPE_ACCESSORY_ONLY,
            can_aggregate=True,
        ),
        whitelist,
    )
    assert accessory.status == TAXONOMY_STATUS_ALLOWED
    assert accessory.can_aggregate is True
    assert accessory.reject_reason is None

    packaging = validate_review_fragment_taxonomy(
        _fragment(
            module=MODULE_LOGISTICS_SUPPORT,
            aspect_key="packaging",
            scope=SCOPE_LOGISTICS_SUPPORT,
            can_aggregate=True,
        ),
        whitelist,
    )
    assert packaging.status == TAXONOMY_STATUS_ALLOWED
    assert packaging.can_aggregate is True
    assert packaging.reject_reason is None

    missing_parts = validate_review_fragment_taxonomy(
        _fragment(
            module=MODULE_ACCESSORY_OR_BUNDLE,
            aspect_key="missing_parts",
            scope=SCOPE_ACCESSORY_ONLY,
            can_aggregate=True,
        ),
        resolve_review_fragment_taxonomy_whitelist(
            category="home",
            sub_category="床架",
            aspect_resolver=_fixture_resolver,
        ),
    )
    assert missing_parts.status == TAXONOMY_STATUS_ALLOWED
    assert missing_parts.can_aggregate is True
    assert missing_parts.reject_reason is None


def test_non_product_or_wrong_attachment_aspects_cannot_force_current_product_aspects() -> None:
    whitelist = resolve_review_fragment_taxonomy_whitelist(
        category="outdoor",
        sub_category="waders",
        aspect_resolver=_fixture_resolver,
    )
    attempts = [
        (MODULE_ACCESSORY_OR_BUNDLE, SCOPE_ACCESSORY_ONLY, "taxonomy_out_of_scope"),
        (MODULE_COMPARISON_OR_OTHER_PRODUCT, SCOPE_OTHER_PRODUCT, "other_product_or_competitor"),
        (MODULE_LOGISTICS_SUPPORT, SCOPE_LOGISTICS_SUPPORT, "taxonomy_out_of_scope"),
        (MODULE_CONSUMER_PROFILE, SCOPE_NON_PRODUCT_CONTEXT, "not_current_product"),
    ]
    aspect_keys = {
        MODULE_ACCESSORY_OR_BUNDLE: "waterproof",
        MODULE_LOGISTICS_SUPPORT: "delivery_speed",
    }

    for module, scope, expected_reason in attempts:
        fragment = _fragment(
            module=module,
            aspect_key=aspect_keys.get(module, "waterproof"),
            scope=scope,
            can_aggregate=True,
            reject_reason=None,
        )
        decision = validate_review_fragment_taxonomy(fragment, whitelist)
        assert decision.status == TAXONOMY_STATUS_OUT_OF_SCOPE
        assert decision.can_aggregate is False
        assert decision.reject_reason == expected_reason


def test_review_fragment_taxonomy_fixture_matches_expected_hit_table() -> None:
    fixture = _load_fixture()

    assert fixture["schema_version"] == REVIEW_FRAGMENT_TAXONOMY_FIXTURE_SCHEMA_VERSION
    assert fixture["whitelist_version"] == REVIEW_FRAGMENT_TAXONOMY_WHITELIST_VERSION
    assert len(fixture["samples"]) == 10
    assert {
        "taxonomy allowed aspect",
        "out-of-library aspect",
        "candidate aspect",
        "other aspect",
        "taxonomy missing",
        "accessory taxonomy aggregation",
        "packaging taxonomy aggregation",
        "wrong attachment aspect blocked",
        "old product pollution",
        "same-review duplicate aspect",
    } <= set(fixture["coverage"])

    all_statuses: set[str] = set()
    duplicate_cases = 0
    for sample in fixture["samples"]:
        assert len(sample["fragments"]) == len(sample["expected_taxonomy"])
        for fragment in sample["fragments"]:
            assert validate_review_fragment(fragment) == []

        actual_rows = _actual_taxonomy_rows(sample)
        expected_rows = [
            {
                "status": item["status"],
                "can_aggregate": item["can_aggregate"],
                "reject_reason": item["reject_reason"],
                "product_aggregate_counted": item["product_aggregate_counted"],
                "duplicate_aggregate_aspect": item["duplicate_aggregate_aspect"],
            }
            for item in sorted(sample["expected_taxonomy"], key=lambda row: row["fragment_index"])
        ]
        assert actual_rows == expected_rows
        all_statuses.update(row["status"] for row in actual_rows)
        duplicate_cases += sum(1 for row in actual_rows if row["duplicate_aggregate_aspect"])

    assert {TAXONOMY_STATUS_ALLOWED, TAXONOMY_STATUS_OUT_OF_SCOPE, TAXONOMY_STATUS_MISSING} <= all_statuses
    assert duplicate_cases == 1
