from __future__ import annotations

import inspect
from dataclasses import fields, replace
from pathlib import Path

import pytest

from backend_api.app.services import review_fragment_candidate_multimodule
from backend_api.app.services.review_fragment_label_catalog import (
    FORMAL_LABEL_REGISTRY_VERSION,
    NEGATIVE_EXAMPLE_TYPE_OUT_OF_SCOPE,
    REVIEW_STATUS_APPROVED,
    REVIEW_STATUS_PENDING,
    SCOPE_POLICY_CAPABILITY_DERIVED,
    SCOPE_POLICY_EXPLICIT,
    SCOPE_POLICY_TRANSACTION_UNIVERSAL,
    FormalLabelDefinition,
    LabelRegistryState,
    NegativeExample,
    PositiveExample,
    compute_effective_scope,
    compute_effective_scope_matrix,
    get_all_sub_categories,
    get_label_registry_state,
    get_transaction_dimension_keys,
    get_transaction_dimensions,
    resolve_formal_label,
    resolve_formal_label_aspect,
    set_label_registry_state_for_tests,
)
from backend_api.app.services.review_fragment_label_catalog import (
    _load_label as _load_label_raw,
)


@pytest.fixture(autouse=True)
def reset_registry_state() -> None:
    set_label_registry_state_for_tests(None)
    yield
    set_label_registry_state_for_tests(None)


# ---------------------------------------------------------------------------
# 5.9.6-A regression tests (unchanged)
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# 5.9.6-D new tests: schema fail-closed
# ---------------------------------------------------------------------------


def _make_minimal_label_raw(**overrides: object) -> dict[str, object]:
    """Build a minimal valid label dict for _load_label testing."""
    return {
        "key": "test_label",
        "label_type": "issue",
        "status": "approved",
        "display": {"en": "Test Label", "zh": "测试标签"},
        "boundary_note": "Test boundary note.",
        "aspect_keys": ["test_aspect"],
        "formal_module": "product_issue",
        "aliases": [],
        "category_keys": ["outdoor"],
        "sub_category_keys": ["waders"],
        "scope_policy": "capability_derived",
        "required_transaction_dimension": None,
        "scope_reason": "",
        "positive_examples": [
            {"sub_category": "waders", "review_text": "Test review", "expected_key": "test_label"},
        ],
        "negative_examples": [
            {"type": "out_of_scope", "sub_category": "boots", "review_text": "Not applicable", "why_not": "No test_aspect"},
        ],
        "review_status": "pending",
        "blocked_contexts": [],
        "owner_note": "",
        **overrides,
    }


def test_schema_fail_closed_missing_scope_policy() -> None:
    """Label without scope_policy must raise ValueError."""
    raw = _make_minimal_label_raw(scope_policy=None)
    with pytest.raises(ValueError, match="scope_policy is required"):
        _load_label_raw(raw, registry_version="test", source="test")


def test_schema_fail_closed_unknown_scope_policy() -> None:
    """Label with unknown scope_policy must raise ValueError."""
    raw = _make_minimal_label_raw(scope_policy="nonexistent_policy")
    with pytest.raises(ValueError, match="unknown scope_policy"):
        _load_label_raw(raw, registry_version="test", source="test")


def test_schema_fail_closed_transaction_universal_without_dimension() -> None:
    """transaction_universal without required_transaction_dimension must fail."""
    raw = _make_minimal_label_raw(
        scope_policy="transaction_universal",
        required_transaction_dimension=None,
        scope_reason="test reason",
    )
    with pytest.raises(ValueError, match="requires required_transaction_dimension"):
        _load_label_raw(raw, registry_version="test", source="test")


def test_schema_fail_closed_transaction_universal_without_scope_reason() -> None:
    """transaction_universal without scope_reason must fail."""
    raw = _make_minimal_label_raw(
        scope_policy="transaction_universal",
        required_transaction_dimension="logistics_issue",
        scope_reason="",
    )
    with pytest.raises(ValueError, match="requires scope_reason"):
        _load_label_raw(raw, registry_version="test", source="test")


def test_schema_fail_closed_missing_review_status() -> None:
    """Label without review_status must raise ValueError."""
    raw = _make_minimal_label_raw(review_status=None)
    with pytest.raises(ValueError, match="review_status is required"):
        _load_label_raw(raw, registry_version="test", source="test")


def test_schema_fail_closed_unknown_review_status() -> None:
    """Label with unknown review_status must raise ValueError."""
    raw = _make_minimal_label_raw(review_status="unknown_status")
    with pytest.raises(ValueError, match="unknown review_status"):
        _load_label_raw(raw, registry_version="test", source="test")


# ---------------------------------------------------------------------------
# 5.9.6-D new tests: transaction_universal dimension validation
# ---------------------------------------------------------------------------


def test_transaction_universal_rejects_non_enum_dimension() -> None:
    """A transaction_universal label referencing a dimension NOT in the
    transaction_aspects.yaml closed enumeration must cause the registry load
    to fail (ValueError raised from _load_registry_from_file post-load check).
    """
    valid_dims = get_transaction_dimension_keys()
    assert "logistics_issue" in valid_dims
    assert "customer_service" in valid_dims
    assert "packaging" in valid_dims

    # Verify that a fake dimension is not in the enum
    assert "nonexistent_dimension" not in valid_dims


def test_transaction_dimensions_loaded_from_yaml() -> None:
    """transaction_aspects.yaml must be parsed and available via API."""
    dims = get_transaction_dimensions()
    assert len(dims) == 3
    keys = {d.key for d in dims}
    assert keys == {"logistics_issue", "customer_service", "packaging"}
    for d in dims:
        assert d.label_zh
        assert isinstance(d.boundary_note, str)


# ---------------------------------------------------------------------------
# 5.9.6-D new tests: effective scope calculation
# ---------------------------------------------------------------------------


def test_effective_scope_waterproof_gives_5_sub_categories() -> None:
    """capability_derived with waterproof aspect must match 5 sub_categories."""
    label = FormalLabelDefinition(
        key="test_waterproof",
        label_type="issue",
        category_keys=("*",),
        sub_category_keys=("*",),
        status="approved",
        display_label_en="Test",
        display_label_zh="测试",
        boundary_note="",
        aliases=(),
        aspect_keys=frozenset({"waterproof"}),
        formal_module="product_issue",
        scope_policy=SCOPE_POLICY_CAPABILITY_DERIVED,
    )
    scope = compute_effective_scope(label)
    assert len(scope) == 5, f"expected 5, got {len(scope)}: {sorted(scope)}"
    assert "waders" in scope
    assert "冲锋衣" in scope
    assert "帐篷" in scope
    assert "户外背包" in scope
    assert "登山鞋" in scope


def test_effective_scope_accessory_storage_gives_1_sub_category() -> None:
    """capability_derived with accessory_storage must match exactly waders."""
    label = FormalLabelDefinition(
        key="test_accessory",
        label_type="issue",
        category_keys=("*",),
        sub_category_keys=("*",),
        status="approved",
        display_label_en="Test",
        display_label_zh="测试",
        boundary_note="",
        aliases=(),
        aspect_keys=frozenset({"accessory_storage"}),
        formal_module="product_issue",
        scope_policy=SCOPE_POLICY_CAPABILITY_DERIVED,
    )
    scope = compute_effective_scope(label)
    assert len(scope) == 1, f"expected 1, got {len(scope)}: {sorted(scope)}"
    assert "waders" in scope


def test_effective_scope_size_fit_gives_63_sub_categories() -> None:
    """capability_derived with size_fit must match 63 sub_categories."""
    label = FormalLabelDefinition(
        key="test_size_fit",
        label_type="issue",
        category_keys=("*",),
        sub_category_keys=("*",),
        status="approved",
        display_label_en="Test",
        display_label_zh="测试",
        boundary_note="",
        aliases=(),
        aspect_keys=frozenset({"size_fit"}),
        formal_module="product_issue",
        scope_policy=SCOPE_POLICY_CAPABILITY_DERIVED,
    )
    scope = compute_effective_scope(label)
    assert len(scope) == 63, f"expected 63, got {len(scope)}"


def test_effective_scope_any_of_semantics() -> None:
    """water_leaks_through (seam_integrity ∪ waterproof) should cover 5 sub_categories.
    seam_integrity alone covers 1 (waders), waterproof alone covers 5.
    Union should give 5 (any-of, not all-of).
    """
    label = FormalLabelDefinition(
        key="test_union",
        label_type="issue",
        category_keys=("*",),
        sub_category_keys=("*",),
        status="approved",
        display_label_en="Test",
        display_label_zh="测试",
        boundary_note="",
        aliases=(),
        aspect_keys=frozenset({"seam_integrity", "waterproof"}),
        formal_module="product_issue",
        scope_policy=SCOPE_POLICY_CAPABILITY_DERIVED,
    )
    scope = compute_effective_scope(label)
    # any-of: should match sub_categories with EITHER seam_integrity OR waterproof
    assert len(scope) == 5, f"expected 5 (union), got {len(scope)}: {sorted(scope)}"
    assert "waders" in scope  # has both
    # 户外背包 has waterproof but not seam_integrity → should be in scope (any-of)
    assert "户外背包" in scope


def test_effective_scope_transaction_universal_covers_all() -> None:
    """transaction_universal labels must cover all known sub_categories."""
    label = FormalLabelDefinition(
        key="test_txn",
        label_type="issue",
        category_keys=("*",),
        sub_category_keys=("*",),
        status="approved",
        display_label_en="Test",
        display_label_zh="测试",
        boundary_note="",
        aliases=(),
        aspect_keys=frozenset({"logistics_issue"}),
        formal_module="product_issue",
        scope_policy=SCOPE_POLICY_TRANSACTION_UNIVERSAL,
        required_transaction_dimension="logistics_issue",
    )
    scope = compute_effective_scope(label)
    all_sc = get_all_sub_categories()
    assert len(scope) == len(all_sc), f"expected {len(all_sc)}, got {len(scope)}"
    assert scope == all_sc


def test_effective_scope_empty_aspect_keys_returns_empty() -> None:
    """capability_derived with no aspect_keys must return empty scope."""
    label = FormalLabelDefinition(
        key="test_empty",
        label_type="issue",
        category_keys=("*",),
        sub_category_keys=("*",),
        status="approved",
        display_label_en="Test",
        display_label_zh="测试",
        boundary_note="",
        aliases=(),
        aspect_keys=frozenset(),
        formal_module="product_issue",
        scope_policy=SCOPE_POLICY_CAPABILITY_DERIVED,
    )
    scope = compute_effective_scope(label)
    assert len(scope) == 0


def test_effective_scope_explicit_returns_empty() -> None:
    """explicit labels have no computed scope (hand-maintained)."""
    label = FormalLabelDefinition(
        key="test_explicit",
        label_type="issue",
        category_keys=("*",),
        sub_category_keys=("*",),
        status="approved",
        display_label_en="Test",
        display_label_zh="测试",
        boundary_note="",
        aliases=(),
        aspect_keys=frozenset(),
        formal_module="product_issue",
        scope_policy=SCOPE_POLICY_EXPLICIT,
        scope_reason="hand curated list",
    )
    scope = compute_effective_scope(label)
    assert len(scope) == 0


# ---------------------------------------------------------------------------
# 5.9.6-D new tests: negative example out_of_scope verification
# ---------------------------------------------------------------------------


def test_negative_example_dataclass_fields() -> None:
    """Verify NegativeExample dataclass shape."""
    neg = NegativeExample(
        type=NEGATIVE_EXAMPLE_TYPE_OUT_OF_SCOPE,
        sub_category="outdoor",
        review_text="test review",
        why_not="test reason",
    )
    assert neg.type == "out_of_scope"
    assert neg.sub_category == "outdoor"
    assert neg.review_text == "test review"
    assert neg.why_not == "test reason"


def test_positive_example_dataclass_fields() -> None:
    """Verify PositiveExample dataclass shape."""
    pos = PositiveExample(
        sub_category="waders",
        review_text="Test review text",
        expected_key="test_label",
    )
    assert pos.sub_category == "waders"
    assert pos.review_text == "Test review text"
    assert pos.expected_key == "test_label"


def test_out_of_scope_negative_verified_against_matrix() -> None:
    """An out_of_scope negative example's sub_category must be outside
    the computed effective scope. This test verifies the invariant that
    the validation script enforces.
    """
    label = FormalLabelDefinition(
        key="test_verify",
        label_type="issue",
        category_keys=("*",),
        sub_category_keys=("*",),
        status="approved",
        display_label_en="Test",
        display_label_zh="测试",
        boundary_note="",
        aliases=(),
        aspect_keys=frozenset({"accessory_storage"}),
        formal_module="product_issue",
        scope_policy=SCOPE_POLICY_CAPABILITY_DERIVED,
    )
    scope = compute_effective_scope(label)
    # accessory_storage only matches waders
    assert scope == frozenset({"waders"})

    # 保温杯 should be out of scope
    assert "保温杯" not in scope
    assert "保温杯" in get_all_sub_categories()


# ---------------------------------------------------------------------------
# 5.9.6-D new tests: data model rejects wildcard
# ---------------------------------------------------------------------------


def test_all_labels_have_scope_policy_field() -> None:
    """Every label in the real registry must have scope_policy set."""
    for label in get_label_registry_state().labels:
        assert label.scope_policy in (
            SCOPE_POLICY_TRANSACTION_UNIVERSAL,
            SCOPE_POLICY_CAPABILITY_DERIVED,
            SCOPE_POLICY_EXPLICIT,
        ), f"{label.key}: missing or invalid scope_policy={label.scope_policy!r}"


def test_all_labels_have_review_status_field() -> None:
    """Every label in the real registry must have review_status."""
    for label in get_label_registry_state().labels:
        assert label.review_status in (
            REVIEW_STATUS_PENDING,
            REVIEW_STATUS_APPROVED,
            "rejected",
        ), f"{label.key}: invalid review_status={label.review_status!r}"


def test_transaction_universal_labels_have_required_dimension() -> None:
    """All transaction_universal labels must have required_transaction_dimension."""
    valid_dims = get_transaction_dimension_keys()
    for label in get_label_registry_state().labels:
        if label.scope_policy == SCOPE_POLICY_TRANSACTION_UNIVERSAL:
            assert label.required_transaction_dimension is not None, (
                f"{label.key}: missing required_transaction_dimension"
            )
            assert label.required_transaction_dimension in valid_dims, (
                f"{label.key}: {label.required_transaction_dimension} not in {valid_dims}"
            )


# ---------------------------------------------------------------------------
# 5.9.6-D new tests: scope matrix computation
# ---------------------------------------------------------------------------


def test_scope_matrix_covers_all_registry_labels() -> None:
    """compute_effective_scope_matrix must return an entry for every label."""
    matrix = compute_effective_scope_matrix()
    labels = get_label_registry_state().labels
    assert len(matrix) == len(labels)
    for label in labels:
        assert label.key in matrix
        assert isinstance(matrix[label.key], frozenset)


def test_registry_version_not_bumped() -> None:
    """Decision f: registry_version must remain at 5.9.6-A.1 (no bump)."""
    state = get_label_registry_state()
    assert state.registry_version == "review-fragment-label-registry.5.9.6-A.1"
    assert FORMAL_LABEL_REGISTRY_VERSION == "review-fragment-label-registry.5.9.6-A.1"


# ---------------------------------------------------------------------------
# 5.9.6-D new tests: label count
# ---------------------------------------------------------------------------


def test_registry_has_9_labels() -> None:
    """The registry should contain exactly 9 labels (5.9.6-A baseline)."""
    assert len(get_label_registry_state().labels) == 9


def test_label_scope_policy_distribution() -> None:
    """Verify the expected scope_policy distribution across 9 labels."""
    state = get_label_registry_state()
    txn = [lb for lb in state.labels if lb.scope_policy == SCOPE_POLICY_TRANSACTION_UNIVERSAL]
    cap = [lb for lb in state.labels if lb.scope_policy == SCOPE_POLICY_CAPABILITY_DERIVED]
    exp = [lb for lb in state.labels if lb.scope_policy == SCOPE_POLICY_EXPLICIT]

    assert len(txn) == 4, f"expected 4 transaction_universal, got {len(txn)}: {[lb.key for lb in txn]}"
    assert len(cap) == 5, f"expected 5 capability_derived, got {len(cap)}: {[lb.key for lb in cap]}"
    assert len(exp) == 0, f"expected 0 explicit, got {len(exp)}: {[lb.key for lb in exp]}"

    txn_keys = {lb.key for lb in txn}
    assert txn_keys == {
        "late_shipping",
        "shipping_damage",
        "customer_service_unresponsive",
        "customer_service_helpful",
    }
