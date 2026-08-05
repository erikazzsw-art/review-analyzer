from __future__ import annotations

import inspect
from dataclasses import fields, replace
from pathlib import Path

import pytest

from backend_api.app.services import review_fragment_candidate_multimodule
from backend_api.app.services.review_fragment_label_catalog import (
    FORMAL_LABEL_REGISTRY_VERSION,
    FormalLabelDefinition,
    LabelRegistryState,
    get_label_registry_state,
    resolve_formal_label,
    resolve_formal_label_aspect,
    set_label_registry_state_for_tests,
)


@pytest.fixture(autouse=True)
def reset_registry_state() -> None:
    set_label_registry_state_for_tests(None)
    yield
    set_label_registry_state_for_tests(None)


def test_resolver_returns_issue_and_highlight_definitions() -> None:
    issue = resolve_formal_label(
        "water_leaks_through",
        label_type="issue",
        category_key="outdoor",
        sub_category_key="waders",
    )
    highlight = resolve_formal_label(
        "keeps_water_out",
        label_type="highlight",
        category_key="outdoor",
        sub_category_key="waders",
    )

    assert issue is not None
    assert issue.key == "water_leaks_through"
    assert issue.label_type == "issue"
    assert issue.status == "approved"
    assert issue.category_keys == ("*",)
    assert issue.sub_category_keys == ("*",)
    assert issue.display_label_en == "Water Leaks Through"
    assert issue.display_label_zh == "容易进水"
    assert issue.boundary_note
    assert issue.matched_alias is None
    assert issue.registry_version == FORMAL_LABEL_REGISTRY_VERSION

    assert highlight is not None
    assert highlight.key == "keeps_water_out"
    assert highlight.label_type == "highlight"
    assert highlight.status == "approved"
    assert highlight.display_label_en == "Keeps Water Out"


def test_alias_resolves_to_canonical_key_and_preserves_match() -> None:
    resolved = resolve_formal_label(
        "kept dry",
        label_type="highlight",
        sub_category_key="waders",
    )

    assert resolved is not None
    assert resolved.key == "keeps_water_out"
    assert resolved.matched_alias == "kept dry"
    assert resolved.alias == "kept dry"
    assert resolved.aliases


def test_shipping_issue_keys_use_logistics_issue_aspect() -> None:
    for key in ("late_shipping", "shipping_damage"):
        definition = resolve_formal_label(key, label_type="issue", sub_category_key="waders")
        assert definition is not None
        assert definition.aspect_keys == frozenset({"logistics_issue"})
        assert resolve_formal_label_aspect(
            key,
            source_aspect_key=key,
            allowed_aspect_keys={"logistics_issue"},
            label_type="issue",
            sub_category_key="waders",
        ) == "logistics_issue"

    state = get_label_registry_state()
    assert "shipping_damage" not in state.aspect_display_mapping


def test_non_approved_labels_do_not_resolve_into_formal_frontstage() -> None:
    state = get_label_registry_state()
    original = state.labels[0]
    candidate = replace(original, status="candidate")
    set_label_registry_state_for_tests(
        LabelRegistryState(
            labels=(candidate,),
            aspect_aliases=state.aspect_aliases,
            aspect_display_mapping=state.aspect_display_mapping,
            highlight_by_aspect=state.highlight_by_aspect,
            registry_version=state.registry_version,
            source=state.source,
        )
    )

    assert resolve_formal_label(candidate.key) is None
    assert resolve_formal_label(candidate.key, approved_only=False) is not None


def test_registry_core_model_excludes_deleted_action_and_normalization_identities() -> None:
    field_names = {field.name for field in fields(FormalLabelDefinition)}

    assert {
        "action_label_key",
        "normalized_label",
        "recommended_action_key",
    }.isdisjoint(field_names)
    assert all(label.status == "approved" for label in get_label_registry_state().labels)
    assert all("shipping_damage" not in label.aspect_keys for label in get_label_registry_state().labels)


def test_active_registry_has_no_experiment_label_constant_dependency() -> None:
    registry_source = inspect.getsource(
        __import__(
            "backend_api.app.services.review_fragment_label_catalog",
            fromlist=["review_fragment_label_catalog"],
        )
    )
    assert "review_fragment_candidate_multimodule" not in registry_source

    candidate_source = inspect.getsource(review_fragment_candidate_multimodule)
    assert "review_fragment_label_catalog" in candidate_source
    assert "APPROVED_FORMAL_LABELS: tuple[FormalLabel, ...] = (" not in candidate_source

    services_dir = Path(review_fragment_candidate_multimodule.__file__).parent
    for path in services_dir.glob("*.py"):
        if path.name == "review_fragment_candidate_multimodule.py":
            continue
        source = path.read_text(encoding="utf-8")
        assert "from backend_api.app.services.review_fragment_candidate_multimodule" not in source
        assert "import review_fragment_candidate_multimodule" not in source
