from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

from backend_api.app.services.review_fragment_contract import (
    MODULE_ACCESSORY_OR_BUNDLE,
    MODULE_AUDIT_FILTER,
    MODULE_LOGISTICS_SUPPORT,
    MODULE_OTHER_CANDIDATE,
    MODULE_PRODUCT_HIGHLIGHT,
    MODULE_PRODUCT_ISSUE,
    REVIEW_FRAGMENT_REQUIRED_FIELDS,
    SCOPE_ACCESSORY_ONLY,
    SCOPE_CURRENT_PRODUCT,
    SCOPE_LOGISTICS_SUPPORT,
)
from backend_api.app.services.review_fragment_evidence_gate import (
    EVIDENCE_SOURCE_REVIEW_TEXT,
    FORMAL_EVIDENCE_GATE_MODULES,
    REVIEW_FRAGMENT_EVIDENCE_FIXTURE_SCHEMA_VERSION,
    REVIEW_FRAGMENT_EVIDENCE_GATE_VERSION,
    apply_review_fragment_evidence_gate,
    review_fragment_evidence_result_row,
    validate_review_fragment_evidence,
)
from backend_api.app.services.review_fragment_taxonomy_whitelist import resolve_review_fragment_taxonomy_whitelist

ROOT = Path(__file__).resolve().parent.parent.parent
FIXTURE_PATH = Path(__file__).parent / "fixtures" / "review_fragment_evidence_5_9_3_samples.json"
WADERS_TAXONOMY_PATH = ROOT / "data" / "taxonomy" / "v1.0" / "outdoor" / "waders.yaml"


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
    return [{"key": "waterproof", "label_zh": "fallback bait"}], False


def _whitelist() -> Any:
    return resolve_review_fragment_taxonomy_whitelist(
        category="outdoor",
        sub_category="waders",
        aspect_resolver=_fixture_resolver,
    )


def _fragment(
    *,
    fragment_text: str = "The waders stayed dry",
    module: str = MODULE_PRODUCT_HIGHLIGHT,
    aspect_key: str = "waterproof",
    evidence_span: str = "waders stayed dry",
    scope: str = SCOPE_CURRENT_PRODUCT,
    can_aggregate: bool = True,
    reject_reason: str | None = None,
) -> dict[str, Any]:
    return {
        "fragment_text": fragment_text,
        "module": module,
        "aspect_key": aspect_key,
        "polarity": "positive" if module == MODULE_PRODUCT_HIGHLIGHT else "negative",
        "evidence_span": evidence_span,
        "confidence": 0.91,
        "current_product_scope": scope,
        "can_aggregate": can_aggregate,
        "reject_reason": reject_reason,
    }


def _actual_evidence_rows(sample: dict[str, Any]) -> list[dict[str, Any]]:
    whitelist = resolve_review_fragment_taxonomy_whitelist(
        category=sample.get("category"),
        sub_category=sample.get("sub_category"),
        aspect_resolver=_fixture_resolver,
    )
    seen: set[tuple[str, str, str]] = set()
    rows: list[dict[str, Any]] = []

    for fragment in sample["fragments"]:
        row = review_fragment_evidence_result_row(fragment, review_text=sample["content"], whitelist=whitelist)
        aggregate_key = (
            str(fragment.get("module") or ""),
            str(fragment.get("aspect_key") or ""),
            str(fragment.get("polarity") or ""),
        )
        counted = False
        if row["can_aggregate"] is True and aggregate_key[0] in FORMAL_EVIDENCE_GATE_MODULES:
            if aggregate_key not in seen:
                seen.add(aggregate_key)
                counted = True
        rows.append(
            {
                "evidence_valid": row["evidence_valid"],
                "evidence_source": row["evidence_source"],
                "can_aggregate": row["can_aggregate"],
                "reject_reason": row["reject_reason"],
                "taxonomy_status": row["taxonomy_status"],
                "formal_aggregate_counted": counted,
            }
        )

    return rows


def test_review_fragment_evidence_fixture_matches_expected_gate_table() -> None:
    fixture = _load_fixture()

    assert fixture["schema_version"] == REVIEW_FRAGMENT_EVIDENCE_FIXTURE_SCHEMA_VERSION
    assert fixture["evidence_gate_version"] == REVIEW_FRAGMENT_EVIDENCE_GATE_VERSION
    assert len(fixture["samples"]) == 10
    assert {
        "original evidence exists and can aggregate",
        "evidence span not found in fragment or review",
        "empty evidence span",
        "generic praise hard-split into specific highlights",
        "old product or competitor evidence",
        "pure logistics or service pollution",
        "accessory evidence uses corresponding aspect",
        "accessory evidence cannot become main product waterproof issue",
        "packaging and arrival damage evidence can aggregate on corresponding aspect",
        "candidate and other retain evidence but do not enter formal Top10",
        "evidence can be sourced from raw review text when fragment text is summarized",
    } <= set(fixture["coverage"])

    all_reject_reasons: set[str] = set()
    all_sources: set[str] = set()
    aggregate_count = 0

    for sample in fixture["samples"]:
        assert len(sample["fragments"]) == len(sample["expected_evidence"])
        for fragment in sample["fragments"]:
            assert set(fragment) == set(REVIEW_FRAGMENT_REQUIRED_FIELDS)

        actual_rows = _actual_evidence_rows(sample)
        expected_rows = [
            {
                "evidence_valid": item["evidence_valid"],
                "evidence_source": item["evidence_source"],
                "can_aggregate": item["can_aggregate"],
                "reject_reason": item["reject_reason"],
                "taxonomy_status": item["taxonomy_status"],
                "formal_aggregate_counted": item["formal_aggregate_counted"],
            }
            for item in sorted(sample["expected_evidence"], key=lambda row: row["fragment_index"])
        ]
        assert actual_rows == expected_rows
        all_sources.update(row["evidence_source"] for row in actual_rows)
        all_reject_reasons.update(str(row["reject_reason"]) for row in actual_rows if row["reject_reason"])
        aggregate_count += sum(1 for row in actual_rows if row["formal_aggregate_counted"])

    assert {"fragment_text", "review_text", "not_found", "empty"} <= all_sources
    assert {
        "accessory_only",
        "candidate_pending_review",
        "evidence_missing",
        "evidence_not_found",
        "evidence_too_generic",
        "fragment_too_vague",
        "logistics_or_service",
        "other_product_or_competitor",
    } <= all_reject_reasons
    assert aggregate_count == 7


def test_evidence_source_can_fall_back_to_review_text() -> None:
    fragment = _fragment(fragment_text="Waterproof performance was good", evidence_span="waders stayed dry")
    decision = validate_review_fragment_evidence(
        fragment,
        review_text="The package looked rough. The waders stayed dry after two river crossings.",
        whitelist=_whitelist(),
    )

    assert decision.evidence_valid is True
    assert decision.evidence_source == EVIDENCE_SOURCE_REVIEW_TEXT
    assert decision.can_aggregate is True
    assert decision.reject_reason is None


def test_empty_and_rewritten_evidence_fail_before_taxonomy() -> None:
    empty = validate_review_fragment_evidence(
        _fragment(evidence_span=""),
        review_text="The waders stayed dry.",
        whitelist=_whitelist(),
    )
    assert empty.evidence_valid is False
    assert empty.evidence_source == "empty"
    assert empty.can_aggregate is False
    assert empty.reject_reason == "evidence_missing"
    assert empty.taxonomy_status is None

    rewritten = validate_review_fragment_evidence(
        _fragment(evidence_span="battery lasted forever"),
        review_text="The waders stayed dry.",
        whitelist=_whitelist(),
    )
    assert rewritten.evidence_valid is False
    assert rewritten.evidence_source == "not_found"
    assert rewritten.can_aggregate is False
    assert rewritten.reject_reason == "evidence_not_found"
    assert rewritten.taxonomy_status is None


def test_generic_praise_cannot_be_split_into_specific_highlights() -> None:
    waterproof = validate_review_fragment_evidence(
        _fragment(fragment_text="Great product", evidence_span="Great product", aspect_key="waterproof"),
        review_text="Great product.",
        whitelist=_whitelist(),
    )
    comfort = validate_review_fragment_evidence(
        _fragment(fragment_text="Great product", evidence_span="Great product", aspect_key="comfort"),
        review_text="Great product.",
        whitelist=_whitelist(),
    )

    assert waterproof.evidence_valid is False
    assert waterproof.can_aggregate is False
    assert waterproof.reject_reason == "evidence_too_generic"
    assert comfort.evidence_valid is False
    assert comfort.can_aggregate is False
    assert comfort.reject_reason == "evidence_too_generic"


def test_pure_service_pollution_does_not_become_current_product_issue_or_highlight() -> None:
    accessory_as_product = validate_review_fragment_evidence(
        _fragment(
            fragment_text="The phone case leaked",
            module=MODULE_PRODUCT_ISSUE,
            aspect_key="waterproof",
            evidence_span="phone case leaked",
        ),
        review_text="The phone case leaked, but the waders stayed dry.",
        whitelist=_whitelist(),
    )
    assert accessory_as_product.evidence_valid is True
    assert accessory_as_product.can_aggregate is False
    assert accessory_as_product.reject_reason == "accessory_only"

    service_as_durability = validate_review_fragment_evidence(
        _fragment(
            fragment_text="Customer service refused a refund",
            module=MODULE_PRODUCT_ISSUE,
            aspect_key="durability",
            evidence_span="Customer service refused a refund",
        ),
        review_text="Customer service refused a refund, but the waders were fine.",
        whitelist=_whitelist(),
    )
    assert service_as_durability.evidence_valid is True
    assert service_as_durability.can_aggregate is False
    assert service_as_durability.reject_reason == "logistics_or_service"

    old_product_as_current = validate_review_fragment_evidence(
        _fragment(
            fragment_text="My old Brand X waders leaked every trip",
            module=MODULE_PRODUCT_ISSUE,
            aspect_key="waterproof",
            evidence_span="old Brand X waders leaked",
        ),
        review_text="My old Brand X waders leaked every trip, but this pair stayed dry.",
        whitelist=_whitelist(),
    )
    assert old_product_as_current.evidence_valid is True
    assert old_product_as_current.can_aggregate is False
    assert old_product_as_current.reject_reason == "other_product_or_competitor"


def test_accessory_packaging_and_candidate_boundaries() -> None:
    accessory = apply_review_fragment_evidence_gate(
        _fragment(
            fragment_text="The phone case leaked",
            module=MODULE_ACCESSORY_OR_BUNDLE,
            aspect_key="accessory_storage",
            evidence_span="phone case leaked",
            scope=SCOPE_ACCESSORY_ONLY,
        ),
        review_text="The phone case leaked, but the waders stayed dry.",
        whitelist=_whitelist(),
    )
    assert accessory["evidence_valid"] is True
    assert accessory["can_aggregate"] is True
    assert accessory["reject_reason"] is None

    accessory_without_object = apply_review_fragment_evidence_gate(
        _fragment(
            fragment_text="The waders stayed dry",
            module=MODULE_ACCESSORY_OR_BUNDLE,
            aspect_key="accessory_storage",
            evidence_span="waders stayed dry",
            scope=SCOPE_ACCESSORY_ONLY,
        ),
        review_text="The waders stayed dry.",
        whitelist=_whitelist(),
    )
    assert accessory_without_object["evidence_valid"] is True
    assert accessory_without_object["can_aggregate"] is False
    assert accessory_without_object["reject_reason"] == "accessory_only"

    shipping_damage = apply_review_fragment_evidence_gate(
        _fragment(
            fragment_text="The box arrived crushed",
            module=MODULE_LOGISTICS_SUPPORT,
            aspect_key="shipping_damage",
            evidence_span="box arrived crushed",
            scope=SCOPE_LOGISTICS_SUPPORT,
        ),
        review_text="The box arrived crushed and one repair patch was missing.",
        whitelist=_whitelist(),
    )
    assert shipping_damage["evidence_valid"] is True
    assert shipping_damage["can_aggregate"] is True
    assert shipping_damage["reject_reason"] is None

    shipping_damage_without_object = apply_review_fragment_evidence_gate(
        _fragment(
            fragment_text="The waders stayed dry",
            module=MODULE_LOGISTICS_SUPPORT,
            aspect_key="shipping_damage",
            evidence_span="waders stayed dry",
            scope=SCOPE_LOGISTICS_SUPPORT,
        ),
        review_text="The waders stayed dry.",
        whitelist=_whitelist(),
    )
    assert shipping_damage_without_object["evidence_valid"] is True
    assert shipping_damage_without_object["can_aggregate"] is False
    assert shipping_damage_without_object["reject_reason"] == "logistics_or_service"

    candidate = apply_review_fragment_evidence_gate(
        _fragment(
            fragment_text="I wish these had a built-in fish ruler",
            module=MODULE_OTHER_CANDIDATE,
            aspect_key="candidate:built_in_fish_ruler",
            evidence_span="built-in fish ruler",
            can_aggregate=False,
            reject_reason="candidate_pending_review",
        ),
        review_text="I wish these had a built-in fish ruler.",
        whitelist=_whitelist(),
    )
    assert candidate["evidence_valid"] is True
    assert candidate["can_aggregate"] is False
    assert candidate["reject_reason"] == "candidate_pending_review"

    other = apply_review_fragment_evidence_gate(
        _fragment(
            fragment_text="Nice product",
            module=MODULE_AUDIT_FILTER,
            aspect_key="other",
            evidence_span="Nice product",
            scope="unclear",
            can_aggregate=False,
            reject_reason="fragment_too_vague",
        ),
        review_text="Nice product.",
        whitelist=_whitelist(),
    )
    assert other["evidence_valid"] is True
    assert other["can_aggregate"] is False
    assert other["reject_reason"] == "fragment_too_vague"
