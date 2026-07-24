from __future__ import annotations

import pytest

from backend_api.app.services.customer_label_catalog import (
    CustomerLabel,
    CustomerLabelAliasRule,
    CustomerLabelCatalogState,
    build_customer_label_candidate_payload,
    resolve_customer_label,
    set_customer_label_catalog_state_for_tests,
)
from backend_api.app.services.specific_issue import (
    SPECIFIC_ISSUE_SCHEMA_VERSION,
    build_specific_issue_rows,
    iter_specific_issue_occurrences,
)


@pytest.fixture(autouse=True)
def reset_catalog_state() -> None:
    set_customer_label_catalog_state_for_tests(CustomerLabelCatalogState())
    yield
    set_customer_label_catalog_state_for_tests(None)


def test_catalog_alias_resolves_raw_label_to_canonical_issue() -> None:
    set_customer_label_catalog_state_for_tests(
        CustomerLabelCatalogState(
            labels=(
                CustomerLabel(
                    id=1,
                    label_type="issue",
                    canonical_label_key="pocket_not_waterproof",
                    display_en="Pocket Not Waterproof",
                    display_zh="口袋不防水",
                    primary_aspect_key="accessory_storage",
                    aspect_keys=("accessory_storage",),
                ),
            ),
            alias_rules=(
                CustomerLabelAliasRule(
                    id=11,
                    label_type="issue",
                    rule_type="exact",
                    pattern="pocket gets wet",
                    canonical_label_key="pocket_not_waterproof",
                    aspect_key="accessory_storage",
                    confidence="high",
                    priority=20,
                ),
            ),
        )
    )

    resolved = resolve_customer_label(
        label_type="issue",
        canonical_label_key="pocket_gets_wet",
        display_en="Pocket Gets Wet",
        display_zh="口袋进水",
        raw_label="pocket gets wet",
        aspect_key="accessory_storage",
        sub_category_key="outdoor",
    )

    assert resolved.canonical_label_key == "pocket_not_waterproof"
    assert resolved.display_en == "Pocket Not Waterproof"
    assert resolved.display_zh == "口袋不防水"
    assert resolved.display_allowed is True
    assert resolved.confidence == "high"
    assert resolved.source == "catalog_alias_rule"
    assert resolved.matched_alias_rule_id == 11
    assert resolved.matched_catalog_id == 1


def test_sub_category_alias_overrides_global_alias() -> None:
    set_customer_label_catalog_state_for_tests(
        CustomerLabelCatalogState(
            labels=(
                CustomerLabel(
                    id=1,
                    label_type="issue",
                    canonical_label_key="runs_too_small",
                    display_en="Runs Too Small",
                    primary_aspect_key="size_fit",
                    aspect_keys=("size_fit",),
                ),
                CustomerLabel(
                    id=2,
                    label_type="issue",
                    canonical_label_key="boots_feel_too_tight",
                    display_en="Boots Feel Too Tight",
                    primary_aspect_key="boot_fit",
                    aspect_keys=("boot_fit",),
                    scope_level="sub_category",
                    sub_category_key="outdoor",
                ),
            ),
            alias_rules=(
                CustomerLabelAliasRule(
                    label_type="issue",
                    rule_type="exact",
                    pattern="fit issue",
                    canonical_label_key="runs_too_small",
                    aspect_key="*",
                    priority=10,
                ),
                CustomerLabelAliasRule(
                    label_type="issue",
                    rule_type="exact",
                    pattern="fit issue",
                    canonical_label_key="boots_feel_too_tight",
                    scope_level="sub_category",
                    sub_category_key="outdoor",
                    aspect_key="boot_fit",
                    priority=200,
                ),
            ),
        )
    )

    outdoor = resolve_customer_label(
        label_type="issue",
        canonical_label_key="fit_issue",
        display_en="Fit Issue",
        raw_label="fit issue",
        aspect_key="boot_fit",
        sub_category_key="outdoor",
    )
    generic = resolve_customer_label(
        label_type="issue",
        canonical_label_key="fit_issue",
        display_en="Fit Issue",
        raw_label="fit issue",
        aspect_key="size_fit",
        sub_category_key="apparel",
    )

    assert outdoor.canonical_label_key == "boots_feel_too_tight"
    assert outdoor.display_en == "Boots Feel Too Tight"
    assert generic.canonical_label_key == "runs_too_small"
    assert generic.display_en == "Runs Too Small"


def test_blocklist_rule_disables_broad_customer_label() -> None:
    set_customer_label_catalog_state_for_tests(
        CustomerLabelCatalogState(
            alias_rules=(
                CustomerLabelAliasRule(
                    label_type="highlight",
                    rule_type="blocklist",
                    pattern="Quality",
                    display_allowed=False,
                    confidence="high",
                    priority=10,
                ),
            )
        )
    )

    resolved = resolve_customer_label(
        label_type="highlight",
        canonical_label_key="quality",
        display_en="Quality",
        raw_label="Quality",
        display_allowed=True,
    )

    assert resolved.display_allowed is False
    assert resolved.source == "catalog_blocklist"
    assert resolved.confidence == "high"


def test_disabled_catalog_label_is_not_display_allowed() -> None:
    set_customer_label_catalog_state_for_tests(
        CustomerLabelCatalogState(
            labels=(
                CustomerLabel(
                    label_type="issue",
                    canonical_label_key="too_generic",
                    display_en="Too Generic",
                    display_allowed=True,
                    status="disabled",
                ),
            )
        )
    )

    resolved = resolve_customer_label(
        label_type="issue",
        canonical_label_key="too_generic",
        display_en="Too Generic",
        raw_label="Too Generic",
    )

    assert resolved.display_allowed is False
    assert resolved.source == "catalog"


def test_candidate_payload_normalizes_scope_and_evidence_sample() -> None:
    payload = build_customer_label_candidate_payload(
        label_type="highlight",
        raw_label="  Great VALUE!! ",
        aspect_key="value_for_money",
        sub_category_key="outdoor",
        evidence_span="Great VALUE",
    )

    assert payload["label_type"] == "highlight"
    assert payload["raw_label"] == "Great VALUE!!"
    assert payload["normalized_raw_label"] == "great value"
    assert payload["category_key"] == "*"
    assert payload["sub_category_key"] == "outdoor"
    assert payload["sample_evidence_spans"] == ["Great VALUE"]


def test_specific_issue_pipeline_uses_catalog_alias_without_changing_legacy_schema() -> None:
    set_customer_label_catalog_state_for_tests(
        CustomerLabelCatalogState(
            labels=(
                CustomerLabel(
                    label_type="issue",
                    canonical_label_key="pocket_not_waterproof",
                    display_en="Pocket Not Waterproof",
                    display_zh="口袋不防水",
                    primary_aspect_key="accessory_storage",
                    aspect_keys=("accessory_storage",),
                ),
            ),
            alias_rules=(
                CustomerLabelAliasRule(
                    label_type="issue",
                    rule_type="exact",
                    pattern="pocket gets wet",
                    canonical_label_key="pocket_not_waterproof",
                    aspect_key="accessory_storage",
                    confidence="high",
                    priority=20,
                ),
            ),
        )
    )
    comment = {
        "id": 1,
        "content": "The pocket gets wet whenever it rains.",
        "sentiment": "negative",
        "aspects_json": {
            "specific_issue_schema_version": SPECIFIC_ISSUE_SCHEMA_VERSION,
            "sub_category": "outdoor",
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
            ],
        },
    }

    occurrences = iter_specific_issue_occurrences(comment, locale="en")
    rows = build_specific_issue_rows([comment], locale="en")

    assert occurrences[0]["specific_issue"] == "Pocket Not Waterproof"
    assert occurrences[0]["canonical_issue_key"] == "pocket_not_waterproof"
    assert occurrences[0]["issue_source"] == "llm_canonical_hint"
    assert occurrences[0]["customer_label_catalog_source"] == "catalog_alias_rule"
    assert rows[0]["specific_issue"] == "Pocket Not Waterproof"
    assert rows[0]["canonical_issue_key"] == "pocket_not_waterproof"
