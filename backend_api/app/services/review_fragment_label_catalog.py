"""Unified 5.9.6-A catalog and resolver for formal review-fragment labels.

The registry fixture is the active-side migration target for the approved
labels, aspect aliases, and display mappings that previously lived in the
5.9.4 experiment module. This module deliberately has no dependency on that
experiment module.

5.9.6-D-wp2 (2026-08-06): extended FormalLabelDefinition with scope_policy,
required_transaction_dimension, scope_reason, positive_examples, negative_examples,
review_status, blocked_contexts, and owner_note. Added transaction_aspects.yaml
loading and effective scope computation.

5.9.6-D-wp4 (2026-08-06): resolver fail-closed refactoring. category_key and
sub_category_key are now required; _scope_matches() deleted; scope gating via
compute_effective_scope(); structured reject reasons; blocked_contexts wired.
"""
from __future__ import annotations

import enum
import logging
import re
from collections.abc import Collection, Mapping
from dataclasses import dataclass, field, replace
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)

FORMAL_LABEL_REGISTRY_VERSION = "review-fragment-label-registry.5.9.6-D.1"
FORMAL_LABEL_TYPES = frozenset({"issue", "highlight"})
FORMAL_LABEL_STATUSES = frozenset({"candidate", "approved", "merged", "deprecated", "blocked"})
APPROVED_LABEL_STATUS = "approved"

SCOPE_POLICY_TRANSACTION_UNIVERSAL = "transaction_universal"
SCOPE_POLICY_CAPABILITY_DERIVED = "capability_derived"
SCOPE_POLICY_EXPLICIT = "explicit"
SCOPE_POLICIES = frozenset({
    SCOPE_POLICY_TRANSACTION_UNIVERSAL,
    SCOPE_POLICY_CAPABILITY_DERIVED,
    SCOPE_POLICY_EXPLICIT,
})

NEGATIVE_EXAMPLE_TYPE_OUT_OF_SCOPE = "out_of_scope"
NEGATIVE_EXAMPLE_TYPE_OUT_OF_BOUNDARY = "out_of_boundary"
NEGATIVE_EXAMPLE_TYPES = frozenset({
    NEGATIVE_EXAMPLE_TYPE_OUT_OF_SCOPE,
    NEGATIVE_EXAMPLE_TYPE_OUT_OF_BOUNDARY,
})

REVIEW_STATUS_PENDING = "pending"
REVIEW_STATUS_APPROVED = "approved"
REVIEW_STATUS_REJECTED = "rejected"
REVIEW_STATUSES = frozenset({REVIEW_STATUS_PENDING, REVIEW_STATUS_APPROVED, REVIEW_STATUS_REJECTED})


class ResolutionRejectReason(enum.Enum):
    """Structured reason for resolver rejection.

    Gate ordering inside the resolver (fixed, cheapest-first):
      unknown_key → not_approved → scope_unavailable → out_of_scope → blocked_context

    INSUFFICIENT_EVIDENCE is NOT produced by the resolver. It is produced by
    callers that apply the 5.9.3 evidence gate BEFORE calling the resolver.
    The resolver resolves identity and scope only; evidence quality is the
    caller's responsibility.

    SCOPE_UNAVAILABLE vs OUT_OF_SCOPE (decision r, 5.9.6-D repair batch 0):
      OUT_OF_SCOPE      — the label genuinely does not apply to this
                          sub_category. A normal, expected business outcome.
      SCOPE_UNAVAILABLE — we cannot tell whether it applies; the scope
                          computation produced nothing usable (taxonomy failed
                          to load, aspect renamed without registry sync, empty
                          aspect_keys, or an explicit label with no stored
                          scope). This is a FAULT, not a business outcome.

    Keeping them separate is deliberate: if a taxonomy load failure surfaced as
    OUT_OF_SCOPE, a spike in rejections would read as "the scope gate is working
    well" — exactly backwards. Alert on SCOPE_UNAVAILABLE separately.

    These values are the input contract for work package 7 (mislabel reflux).
    Do not rename or reorder without updating the reflux pipeline.
    """

    UNKNOWN_KEY = "unknown_key"
    NOT_APPROVED = "not_approved"
    SCOPE_UNAVAILABLE = "scope_unavailable"
    OUT_OF_SCOPE = "out_of_scope"
    BLOCKED_CONTEXT = "blocked_context"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"


@dataclass(frozen=True)
class LabelResolutionResult:
    """Result of a formal label resolution with structured reject reason.

    When ``label`` is None, ``reject_reason`` explains why.
    When ``label`` is not None, ``reject_reason`` is always None.
    """

    label: FormalLabelDefinition | None
    reject_reason: str | None = None

    @property
    def is_resolved(self) -> bool:
        return self.label is not None

_REGISTRY_PATH = (
    Path(__file__).resolve().parents[3]
    / "data"
    / "taxonomy"
    / "registry"
    / "review_fragment_label_registry.yaml"
)

_TRANSACTION_ASPECTS_PATH = (
    Path(__file__).resolve().parents[3]
    / "data"
    / "taxonomy"
    / "shared"
    / "transaction_aspects.yaml"
)

_TAXONOMY_V1_ROOT = (
    Path(__file__).resolve().parents[3]
    / "data"
    / "taxonomy"
    / "v1.0"
)


@dataclass(frozen=True)
class PositiveExample:
    """A positive example anchoring a label to a concrete review."""

    sub_category: str
    review_text: str
    expected_key: str


@dataclass(frozen=True)
class NegativeExample:
    """A negative example defining when a label should NOT fire."""

    type: str  # out_of_scope | out_of_boundary
    sub_category: str
    review_text: str
    why_not: str


@dataclass(frozen=True)
class FormalLabelDefinition:
    """A formal issue/highlight definition returned by the registry."""

    key: str
    label_type: str
    status: str
    display_label_en: str
    display_label_zh: str
    boundary_note: str
    aliases: tuple[str, ...]
    aspect_keys: frozenset[str]
    formal_module: str
    registry_version: str = FORMAL_LABEL_REGISTRY_VERSION
    matched_alias: str | None = None
    source: str = "fixture"

    # 5.9.6-D new fields
    scope_policy: str = SCOPE_POLICY_CAPABILITY_DERIVED
    required_transaction_dimension: str | None = None
    scope_reason: str = ""
    blocked_contexts: tuple[str, ...] = ()
    positive_examples: tuple[PositiveExample, ...] = ()
    negative_examples: tuple[NegativeExample, ...] = ()
    review_status: str = REVIEW_STATUS_PENDING
    owner_note: str = ""

    @property
    def display_en(self) -> str:
        return self.display_label_en

    @property
    def display_zh(self) -> str:
        return self.display_label_zh

    @property
    def display(self) -> dict[str, str]:
        return {"en": self.display_label_en, "zh": self.display_label_zh}

    @property
    def alias(self) -> str | None:
        return self.matched_alias


# Public name for callers that want to make the resolver result type explicit.
LabelResolution = FormalLabelDefinition


@dataclass(frozen=True)
class TransactionDimension:
    """A transaction-layer aspect dimension from transaction_aspects.yaml."""

    key: str
    label_zh: str
    boundary_note: str


@dataclass(frozen=True)
class LabelRegistryState:
    labels: tuple[FormalLabelDefinition, ...] = ()
    aspect_aliases: Mapping[str, str] = field(default_factory=dict)
    aspect_display_mapping: Mapping[str, tuple[str, str]] = field(default_factory=dict)
    highlight_by_aspect: Mapping[str, str] = field(default_factory=dict)
    registry_version: str = FORMAL_LABEL_REGISTRY_VERSION
    source: str = "fixture"
    transaction_dimensions: tuple[TransactionDimension, ...] = ()


_TEST_STATE: LabelRegistryState | None = None


def _clean(value: Any) -> str:
    return str(value or "").strip()


def _string_tuple(value: Any, *, default: tuple[str, ...] = ()) -> tuple[str, ...]:
    if value is None:
        return default
    if isinstance(value, (list, tuple, set)):
        return tuple(_clean(item) for item in value if _clean(item))
    cleaned = _clean(value)
    return (cleaned,) if cleaned else default


def _lookup_text(value: Any) -> str:
    text = _clean(value).casefold().replace("&", " and ")
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", text)).strip()


# ---------------------------------------------------------------------------
# transaction_aspects.yaml loading
# ---------------------------------------------------------------------------


def _load_transaction_dimensions_from_file() -> tuple[TransactionDimension, ...]:
    """Load transaction-layer aspect dimensions from the shared YAML definition.

    Fail-closed: a missing or unparseable file returns an empty tuple and logs
    a warning. The validation script (validate_label_scope.py) enforces that
    transaction_universal labels reference valid dimensions at check time.
    """
    try:
        raw = yaml.safe_load(_TRANSACTION_ASPECTS_PATH.read_text(encoding="utf-8")) or {}
    except FileNotFoundError:
        logger.warning("transaction_aspects.yaml not found at %s", _TRANSACTION_ASPECTS_PATH)
        return ()
    except yaml.YAMLError as exc:
        logger.warning("transaction_aspects.yaml parse failed: %s", exc)
        return ()

    dimensions = raw.get("dimensions")
    if not isinstance(dimensions, list):
        logger.warning("transaction_aspects.yaml: dimensions must be a list")
        return ()

    result: list[TransactionDimension] = []
    seen_keys: set[str] = set()
    for item in dimensions:
        if not isinstance(item, Mapping):
            continue
        key = _clean(item.get("key"))
        if not key:
            continue
        if key in seen_keys:
            logger.warning("transaction_aspects.yaml: duplicate dimension key %r", key)
            continue
        seen_keys.add(key)
        result.append(TransactionDimension(
            key=key,
            label_zh=_clean(item.get("label_zh")),
            boundary_note=_clean(item.get("boundary_note")),
        ))
    return tuple(result)


# ---------------------------------------------------------------------------
# Registry loading
# ---------------------------------------------------------------------------


def _parse_positive_examples(raw: Any) -> tuple[PositiveExample, ...]:
    if not isinstance(raw, list):
        return ()
    examples: list[PositiveExample] = []
    for item in raw:
        if not isinstance(item, Mapping):
            continue
        sub_category = _clean(item.get("sub_category"))
        review_text = _clean(item.get("review_text"))
        expected_key = _clean(item.get("expected_key"))
        if not sub_category or not review_text or not expected_key:
            continue
        examples.append(PositiveExample(
            sub_category=sub_category,
            review_text=review_text,
            expected_key=expected_key,
        ))
    return tuple(examples)


def _parse_negative_examples(raw: Any) -> tuple[NegativeExample, ...]:
    if not isinstance(raw, list):
        return ()
    examples: list[NegativeExample] = []
    for item in raw:
        if not isinstance(item, Mapping):
            continue
        ntype = _clean(item.get("type"))
        if ntype not in NEGATIVE_EXAMPLE_TYPES:
            continue
        sub_category = _clean(item.get("sub_category"))
        review_text = _clean(item.get("review_text"))
        why_not = _clean(item.get("why_not"))
        if not sub_category or not review_text:
            continue
        examples.append(NegativeExample(
            type=ntype,
            sub_category=sub_category,
            review_text=review_text,
            why_not=why_not,
        ))
    return tuple(examples)


def _load_label(raw: Mapping[str, Any], *, registry_version: str, source: str) -> FormalLabelDefinition:
    display = raw.get("display") or {}
    label_type = _clean(raw.get("label_type")).lower()
    status = _clean(raw.get("status")).lower()
    aspect_keys = frozenset(_string_tuple(raw.get("aspect_keys")))
    if label_type not in FORMAL_LABEL_TYPES:
        raise ValueError(f"unsupported formal label type: {label_type!r}")
    if status not in FORMAL_LABEL_STATUSES:
        raise ValueError(f"unsupported formal label status: {status!r}")
    if "shipping_damage" in aspect_keys:
        raise ValueError("shipping_damage cannot be a formal artifact aspect_key")

    # --- 5.9.6-D new fields ---
    scope_policy = _clean(raw.get("scope_policy")).lower()
    if not scope_policy:
        raise ValueError(f"label {raw.get('key', '?')!r}: scope_policy is required")
    if scope_policy not in SCOPE_POLICIES:
        raise ValueError(f"label {raw.get('key', '?')!r}: unknown scope_policy {scope_policy!r}")

    required_transaction_dimension = _clean(raw.get("required_transaction_dimension")) or None
    if scope_policy == SCOPE_POLICY_TRANSACTION_UNIVERSAL and not required_transaction_dimension:
        raise ValueError(
            f"label {raw.get('key', '?')!r}: transaction_universal requires "
            f"required_transaction_dimension"
        )

    scope_reason = _clean(raw.get("scope_reason"))
    if scope_policy in (SCOPE_POLICY_TRANSACTION_UNIVERSAL, SCOPE_POLICY_EXPLICIT) and not scope_reason:
        raise ValueError(
            f"label {raw.get('key', '?')!r}: {scope_policy} requires scope_reason"
        )

    review_status = _clean(raw.get("review_status")).lower()
    if not review_status:
        raise ValueError(f"label {raw.get('key', '?')!r}: review_status is required")
    if review_status not in REVIEW_STATUSES:
        raise ValueError(f"label {raw.get('key', '?')!r}: unknown review_status {review_status!r}")

    positive_examples = _parse_positive_examples(raw.get("positive_examples"))
    negative_examples = _parse_negative_examples(raw.get("negative_examples"))
    blocked_contexts = _string_tuple(raw.get("blocked_contexts"))
    owner_note = _clean(raw.get("owner_note"))

    return FormalLabelDefinition(
        key=_clean(raw.get("key")),
        label_type=label_type,
        status=status,
        display_label_en=_clean(display.get("en")),
        display_label_zh=_clean(display.get("zh")),
        boundary_note=_clean(raw.get("boundary_note")),
        aliases=_string_tuple(raw.get("aliases")),
        aspect_keys=aspect_keys,
        formal_module=_clean(raw.get("formal_module")),
        registry_version=registry_version,
        source=source,
        scope_policy=scope_policy,
        required_transaction_dimension=required_transaction_dimension,
        scope_reason=scope_reason,
        blocked_contexts=blocked_contexts,
        positive_examples=positive_examples,
        negative_examples=negative_examples,
        review_status=review_status,
        owner_note=owner_note,
    )


def _load_registry_from_file() -> LabelRegistryState:
    try:
        raw = yaml.safe_load(_REGISTRY_PATH.read_text(encoding="utf-8")) or {}
        registry_version = _clean(raw.get("registry_version")) or FORMAL_LABEL_REGISTRY_VERSION
        source = _clean(raw.get("source")) or "fixture"
        transaction_dimensions = _load_transaction_dimensions_from_file()

        labels: list[FormalLabelDefinition] = []
        for item in raw.get("labels") or []:
            if not isinstance(item, Mapping):
                continue
            try:
                labels.append(_load_label(item, registry_version=registry_version, source=source))
            except ValueError as exc:
                logger.warning(
                    "review_fragment_label_catalog: skipping label %r: %s",
                    item.get("key", "?"), exc,
                )
        if len({(label.label_type, label.key) for label in labels}) != len(labels):
            raise ValueError("duplicate formal label identity")

        # Post-load validation: transaction_universal must reference a valid dimension
        valid_txn_dims = frozenset(d.key for d in transaction_dimensions)
        for label in labels:
            if label.scope_policy == SCOPE_POLICY_TRANSACTION_UNIVERSAL:
                if label.required_transaction_dimension not in valid_txn_dims:
                    raise ValueError(
                        f"label {label.key!r}: required_transaction_dimension "
                        f"{label.required_transaction_dimension!r} is not in "
                        f"transaction_aspects.yaml closed enumeration"
                    )

        display_mapping: dict[str, tuple[str, str]] = {}
        for key, value in (raw.get("aspect_display_mapping") or {}).items():
            if not isinstance(value, Mapping):
                raise ValueError(f"invalid aspect display mapping for {key!r}")
            aspect_key = _clean(key)
            if aspect_key == "shipping_damage":
                raise ValueError("shipping_damage cannot be a registered taxonomy aspect")
            display_mapping[aspect_key] = (_clean(value.get("en")), _clean(value.get("zh")))

        aspect_aliases = {
            _clean(key): _clean(value)
            for key, value in (raw.get("aspect_aliases") or {}).items()
            if _clean(key) and _clean(value)
        }
        highlight_by_aspect = {
            _clean(key): _clean(value)
            for key, value in (raw.get("highlight_by_aspect") or {}).items()
            if _clean(key) and _clean(value)
        }
        state = LabelRegistryState(
            labels=tuple(labels),
            aspect_aliases=aspect_aliases,
            aspect_display_mapping=display_mapping,
            highlight_by_aspect=highlight_by_aspect,
            registry_version=registry_version,
            source=source,
            transaction_dimensions=transaction_dimensions,
        )
        for aspect_key, label_key in state.highlight_by_aspect.items():
            label = next(
                (
                    item
                    for item in state.labels
                    if item.key == label_key and item.label_type == "highlight"
                ),
                None,
            )
            if label is None:
                raise ValueError(f"highlight mapping points to unknown label: {aspect_key} -> {label_key}")
        return state
    except Exception as exc:
        logger.error("review_fragment_label_catalog: cannot load registry fixture: %s", exc)
        return LabelRegistryState()


@lru_cache(maxsize=1)
def _load_registry_state() -> LabelRegistryState:
    return _load_registry_from_file()


def get_label_registry_state() -> LabelRegistryState:
    if _TEST_STATE is not None:
        return _TEST_STATE
    return _load_registry_state()


def clear_label_registry_cache() -> None:
    _load_registry_state.cache_clear()
    _load_taxonomy_aspect_index.cache_clear()


def set_label_registry_state_for_tests(state: LabelRegistryState | None) -> None:
    global _TEST_STATE
    _TEST_STATE = state
    clear_label_registry_cache()


def get_approved_formal_labels() -> tuple[FormalLabelDefinition, ...]:
    return tuple(
        label
        for label in get_label_registry_state().labels
        if label.status == APPROVED_LABEL_STATUS
    )


# ---------------------------------------------------------------------------
# Transaction dimensions public API
# ---------------------------------------------------------------------------


def get_transaction_dimensions() -> tuple[TransactionDimension, ...]:
    """Return the closed enumeration of transaction-layer aspect dimensions."""
    return get_label_registry_state().transaction_dimensions


def get_transaction_dimension_keys() -> frozenset[str]:
    """Return the set of valid transaction dimension keys (for validation)."""
    return frozenset(d.key for d in get_transaction_dimensions())


# ---------------------------------------------------------------------------
# Effective scope computation
# ---------------------------------------------------------------------------


@lru_cache(maxsize=1)
def _load_taxonomy_aspect_index() -> dict[str, frozenset[str]]:
    """Build a sub_category -> frozenset of aspect keys from all taxonomy YAML files.

    Cached in-process (lru_cache maxsize=1). The index maps each sub_category
    to the set of aspect keys declared in its taxonomy YAML. This is the
    foundation for capability_derived effective scope calculation.

    Fail-closed: if the taxonomy root doesn't exist or no YAML files are found,
    returns an empty dict. Since repair batch 0 an empty index makes the
    resolver reject EVERY label with SCOPE_UNAVAILABLE — including the four
    transaction_universal ones, whose "all sub_categories" set is derived from
    this same index. Before batch 0 the opposite was true (empty index meant
    every capability_derived label passed for all 89 sub_categories).

    Partial degradation is the dangerous case and is NOT covered by fail-closed:
    the per-file loop below skips unreadable or malformed files with a warning
    and continues, so 40 broken files out of 89 yields a smaller-but-non-empty
    index and a silently narrowed scope. assert_taxonomy_index_healthy() exists
    to catch that; call it at startup, because lru_cache would otherwise pin a
    transient failure for the life of the process.
    """
    index: dict[str, frozenset[str]] = {}
    taxonomy_root = _TAXONOMY_V1_ROOT
    if not taxonomy_root.exists():
        logger.warning("taxonomy v1.0 root not found at %s", taxonomy_root)
        return index

    for path in sorted(taxonomy_root.rglob("*.yaml")):
        relative = path.relative_to(taxonomy_root)
        if any(part.startswith("backup-") or part == "seeds" for part in relative.parts):
            continue
        try:
            raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        except yaml.YAMLError as exc:
            logger.warning("taxonomy YAML parse failed: %s: %s", path, exc)
            continue
        if not isinstance(raw, Mapping):
            continue
        sub_category = _clean(raw.get("sub_category"))
        if not sub_category:
            continue
        aspects = raw.get("aspects")
        if not isinstance(aspects, list):
            continue
        aspect_keys: set[str] = set()
        for aspect in aspects:
            if not isinstance(aspect, Mapping):
                continue
            key = _clean(aspect.get("key") or aspect.get("aspect_key"))
            if key:
                aspect_keys.add(key)
        if aspect_keys:
            # Merge: if the same sub_category appears in multiple files
            # (shouldn't happen), union the aspect sets.
            existing = index.get(sub_category)
            if existing is not None:
                index[sub_category] = existing | frozenset(aspect_keys)
            else:
                index[sub_category] = frozenset(aspect_keys)

    return index


def get_taxonomy_aspect_index() -> dict[str, frozenset[str]]:
    """Public accessor for the taxonomy aspect index (respects test state)."""
    if _TEST_STATE is not None:
        # In test mode, bypass cache and read directly
        return _load_taxonomy_aspect_index.__wrapped__()
    return _load_taxonomy_aspect_index()


def get_all_sub_categories() -> frozenset[str]:
    """Return the set of all known sub_category keys from taxonomy assets."""
    return frozenset(get_taxonomy_aspect_index().keys())


# Expected taxonomy sub_category count. Bump together with taxonomy assets.
# A floor rather than an equality check so that adding a sub_category does not
# break startup, while losing a chunk of the taxonomy does.
TAXONOMY_SUB_CATEGORY_FLOOR = 89

# Exact expected count for CI / validate_label_scope.py (decision u, batch 0).
# CI uses equality (== EXPECTED) rather than floor (>= FLOOR) because:
#   - CI equality failure costs zero (no production impact)
#   - CI equality forces "change taxonomy → update the constant" as a single step
#   - Floor would drift: taxonomy grows to 200, then 100 files break → 100 >= 89
#     still passes, and the silent narrowing that batch 0 exists to catch is back
# Must stay in sync with TAXONOMY_SUB_CATEGORY_FLOOR. When adding sub_categories,
# bump both constants together.
EXPECTED_TAXONOMY_SUB_CATEGORY_COUNT = 89


class TaxonomyIndexUnhealthy(RuntimeError):
    """Raised at startup when the taxonomy index is empty or short."""


def assert_taxonomy_index_healthy(*, floor: int | None = None) -> int:
    """Fail loudly if the taxonomy index is empty or smaller than expected.

    Repair batch 0 items 0-2 / 0-3. Two failure shapes need catching:

    - Total failure (index empty). The resolver now fails closed on this, so
      every label would be rejected. Fail-closed is the right default but it is
      still silent: the visible symptom is "all labels vanished", with no
      indication why.
    - Partial degradation (index non-empty but short). Neither fail-open nor
      fail-closed catches this, because the index looks usable. Some
      sub_categories simply lose their scope. This is the more likely and more
      insidious failure, hence a count floor rather than a non-empty check.

    Call this during application startup. _load_taxonomy_aspect_index is
    lru_cached, so a transient filesystem failure on first access would
    otherwise be pinned for the lifetime of the process.

    Returns the observed count on success. Raises TaxonomyIndexUnhealthy
    otherwise.
    """
    expected = TAXONOMY_SUB_CATEGORY_FLOOR if floor is None else floor
    index = get_taxonomy_aspect_index()
    count = len(index)

    if count == 0:
        raise TaxonomyIndexUnhealthy(
            f"taxonomy aspect index is EMPTY (expected >= {expected}). "
            f"Every formal label will be rejected with scope_unavailable. "
            f"Check that the taxonomy assets are present at {_TAXONOMY_V1_ROOT}."
        )
    if count < expected:
        raise TaxonomyIndexUnhealthy(
            f"taxonomy aspect index has {count} sub_categories, expected at "
            f"least {expected}. Scope is silently narrowed for the missing "
            f"ones. Check for unreadable or malformed taxonomy YAML files."
        )

    logger.info("taxonomy aspect index healthy: %d sub_categories", count)
    return count


def compute_effective_scope(label: FormalLabelDefinition) -> frozenset[str]:
    """Compute the set of sub_categories where this label is in scope.

    The computation depends on scope_policy:

    - transaction_universal: all known sub_categories (minus blocked_contexts).
      For our business model (all categories are online physical goods), the
      universal set is derived from all taxonomy assets.

    - capability_derived: sub_categories whose taxonomy declares at least one
      of the label's aspect_keys (any-of semantic).

    - explicit: returns an empty set. WP5 deleted category_keys /
      sub_category_keys, so there is no field left in which a hand-maintained
      scope could live. Since batch 0, an empty scope makes the resolver reject
      with SCOPE_UNAVAILABLE rather than pass — so explicit labels currently
      resolve for nothing. This is intentional until explicit scope storage is
      designed; it prevents a new explicit label from silently going global.

    An empty return value from this function is ALWAYS a fail-closed signal to
    the resolver. It never means "applies everywhere" (see Gate 3a).

    The result is a frozenset; blocked_contexts are NOT subtracted here.
    Subtraction happens at resolve time (work package 4).
    """
    if label.scope_policy == SCOPE_POLICY_TRANSACTION_UNIVERSAL:
        return get_all_sub_categories()

    if label.scope_policy == SCOPE_POLICY_CAPABILITY_DERIVED:
        index = get_taxonomy_aspect_index()
        if not label.aspect_keys:
            return frozenset()
        in_scope: set[str] = set()
        for sub_category, taxonomy_aspects in index.items():
            if label.aspect_keys & taxonomy_aspects:
                in_scope.add(sub_category)
        return frozenset(in_scope)

    # explicit: scope is hand-maintained, not computed
    return frozenset()


def compute_effective_scope_matrix(
    labels: Collection[FormalLabelDefinition] | None = None,
) -> dict[str, frozenset[str]]:
    """Compute the effective scope for multiple labels at once.

    Returns a dict mapping label.key -> frozenset of sub_categories.
    If labels is None, computes for all labels in the registry.
    """
    if labels is None:
        labels = get_label_registry_state().labels
    return {label.key: compute_effective_scope(label) for label in labels}


# ---------------------------------------------------------------------------
# Resolver (5.9.6-D-wp4: fail-closed with structured reasons)
# ---------------------------------------------------------------------------


def _resolve_formal_label_impl(
    key_or_alias: Any,
    *,
    category_key: str,
    sub_category_key: str,
    label_type: str | None = None,
    approved_only: bool = True,
) -> LabelResolutionResult:
    """Core resolution logic with structured reject reasons.

    Gate sequence (fixed order, cheapest-first):
      1. unknown_key        — key/alias not found in registry
      2. not_approved       — label found but status != approved
      3a. scope_unavailable — computed scope is empty (fault, fail-closed)
      3b. out_of_scope      — label approved but sub_category not in scope
      4. blocked_context    — in scope but sub_category explicitly blocked

    Contract:
      Callers MUST pass evidence gate (5.9.3 validate_review_fragment_evidence)
      BEFORE calling this function. This function resolves identity and scope
      only; it does NOT judge evidence quality. The INSUFFICIENT_EVIDENCE
      reject reason is produced by callers, not by the resolver.

      Passing evidence_span or review_text to this function is a TypeError —
      the resolver has no use for them and accepting them would encourage
      callers to skip the upstream evidence gate.
    """
    requested = _clean(key_or_alias)
    if not requested:
        return LabelResolutionResult(
            label=None,
            reject_reason=ResolutionRejectReason.UNKNOWN_KEY.value,
        )

    requested_type = _clean(label_type).lower() or None
    if requested_type and requested_type not in FORMAL_LABEL_TYPES:
        return LabelResolutionResult(
            label=None,
            reject_reason=ResolutionRejectReason.UNKNOWN_KEY.value,
        )

    requested_lookup = _lookup_text(requested)
    requested_category = _clean(category_key)
    requested_sub_category = _clean(sub_category_key)

    if not requested_category:
        return LabelResolutionResult(
            label=None,
            reject_reason=ResolutionRejectReason.UNKNOWN_KEY.value,
        )
    if not requested_sub_category:
        return LabelResolutionResult(
            label=None,
            reject_reason=ResolutionRejectReason.UNKNOWN_KEY.value,
        )

    # --- Gate 1: unknown_key ---
    matches: list[tuple[FormalLabelDefinition, str | None]] = []
    for label in get_label_registry_state().labels:
        if requested_type and label.label_type != requested_type:
            continue
        if requested == label.key:
            matches.append((label, None))
            continue
        if requested_lookup and requested_lookup in {
            _lookup_text(alias) for alias in label.aliases
        }:
            matches.append((label, requested))

    if not matches:
        return LabelResolutionResult(
            label=None,
            reject_reason=ResolutionRejectReason.UNKNOWN_KEY.value,
        )

    distinct_keys = {label.key for label, _ in matches}
    if len(distinct_keys) > 1:
        logger.warning(
            "review_fragment_label_catalog: ambiguous alias=%r keys=%s",
            requested,
            sorted(distinct_keys),
        )
        return LabelResolutionResult(
            label=None,
            reject_reason=ResolutionRejectReason.UNKNOWN_KEY.value,
        )

    matched_label, matched_alias = matches[0]

    # --- Gate 2: not_approved ---
    if approved_only and matched_label.status != APPROVED_LABEL_STATUS:
        return LabelResolutionResult(
            label=None,
            reject_reason=ResolutionRejectReason.NOT_APPROVED.value,
        )

    # --- Gate 3a: scope_unavailable (fail-closed) ---
    #
    # 5.9.6-D repair batch 0 / Bug 1. This block previously read:
    #
    #     if (policy != EXPLICIT and effective_scope
    #         and requested_sub_category not in effective_scope):
    #
    # The `and effective_scope` term short-circuited the whole gate whenever the
    # computed scope was empty, so an empty scope meant "applies everywhere" —
    # a silent return of the `["*"]` behaviour that 5.9.6-D exists to remove.
    # An empty scope now fails CLOSED for every policy.
    #
    # Decision t (2026-08-07): when the taxonomy index is empty, ALL nine labels
    # — including transaction_universal and explicit — return SCOPE_UNAVAILABLE.
    #
    # transaction_universal: its "all sub_categories" set is derived from the
    # taxonomy index via get_all_sub_categories(), so a total load failure means
    # we cannot even confirm the sub_category exists. Passing a label at that
    # point is the same fail-open logic Bug 1 is about. A single aspect drift
    # (one file broken) does NOT affect transaction_universal — it does not
    # depend on aspect_keys.
    #
    # explicit: WP5 deleted category_keys / sub_category_keys, so there is
    # currently no field in which an explicit scope could be stored. Skipping
    # the gate for explicit would leave the same hole open by a different door.
    # The side effect is that explicit is temporarily unusable — whoever needs
    # it must first design the storage mechanism.
    effective_scope = compute_effective_scope(matched_label)
    if not effective_scope:
        logger.warning(
            "review_fragment_label_catalog: scope_unavailable label=%r "
            "policy=%r aspect_keys=%s — computed scope is empty, rejecting "
            "fail-closed. Check taxonomy load and registry/taxonomy aspect sync.",
            matched_label.key,
            matched_label.scope_policy,
            sorted(matched_label.aspect_keys),
        )
        return LabelResolutionResult(
            label=None,
            reject_reason=ResolutionRejectReason.SCOPE_UNAVAILABLE.value,
        )

    # --- Gate 3b: out_of_scope ---
    if requested_sub_category not in effective_scope:
        return LabelResolutionResult(
            label=None,
            reject_reason=ResolutionRejectReason.OUT_OF_SCOPE.value,
        )

    # --- Gate 4: blocked_context ---
    if requested_sub_category in matched_label.blocked_contexts:
        return LabelResolutionResult(
            label=None,
            reject_reason=ResolutionRejectReason.BLOCKED_CONTEXT.value,
        )

    resolved = (
        replace(matched_label, matched_alias=matched_alias)
        if matched_alias
        else matched_label
    )
    return LabelResolutionResult(label=resolved, reject_reason=None)


def resolve_formal_label(
    key_or_alias: Any,
    *,
    category_key: str,
    sub_category_key: str,
    label_type: str | None = None,
    approved_only: bool = True,
) -> LabelResolutionResult:
    """Resolve a canonical key or alias to a formal label definition.

    Args:
        key_or_alias: Canonical label key or alias string.
        category_key: Required. The category of the current product context.
        sub_category_key: Required. The sub_category of the current product context.
        label_type: Optional filter (``"issue"`` or ``"highlight"``).
        approved_only: If True (default), only approved labels are returned.

    Returns:
        ``LabelResolutionResult`` with ``.label`` set to the resolved definition
        and ``.reject_reason`` = None, or ``.label`` = None with a structured
        ``.reject_reason`` explaining why resolution failed.
    """
    return _resolve_formal_label_impl(
        key_or_alias,
        category_key=category_key,
        sub_category_key=sub_category_key,
        label_type=label_type,
        approved_only=approved_only,
    )


def resolve_aspect_alias(aspect_key: Any) -> str:
    """Map a legacy aspect value to the canonical taxonomy evidence dimension."""

    current = _clean(aspect_key)
    seen: set[str] = set()
    aliases = get_label_registry_state().aspect_aliases
    while current and current in aliases and current not in seen:
        seen.add(current)
        current = _clean(aliases[current])
    return current


def resolve_formal_label_aspect(
    label_key_or_alias: Any,
    *,
    source_aspect_key: Any,
    allowed_aspect_keys: Collection[str],
    category_key: str,
    sub_category_key: str,
    label_type: str | None = None,
) -> str | None:
    """Resolve a formal label's taxonomy aspect without changing its identity."""

    result = resolve_formal_label(
        label_key_or_alias,
        category_key=category_key,
        sub_category_key=sub_category_key,
        label_type=label_type,
    )
    label = result.label
    if label is None:
        return None

    source_aspect = _clean(source_aspect_key)
    allowed = {_clean(item) for item in allowed_aspect_keys if _clean(item)}
    resolved_aspect = resolve_aspect_alias(source_aspect)
    if resolved_aspect in label.aspect_keys and resolved_aspect in allowed:
        return resolved_aspect

    if (
        source_aspect in {"", "other"}
        or source_aspect.startswith("candidate:")
        or source_aspect == "durability"
    ) and len(label.aspect_keys) == 1:
        only_aspect = next(iter(label.aspect_keys))
        if only_aspect in allowed:
            return only_aspect
    return None


def resolve_highlight_for_aspect(
    aspect_key: Any,
    *,
    category_key: str,
    sub_category_key: str,
) -> LabelResolutionResult:
    canonical_aspect = resolve_aspect_alias(aspect_key)
    label_key = get_label_registry_state().highlight_by_aspect.get(canonical_aspect)
    if not label_key:
        return LabelResolutionResult(
            label=None,
            reject_reason=ResolutionRejectReason.UNKNOWN_KEY.value,
        )
    return resolve_formal_label(
        label_key,
        category_key=category_key,
        sub_category_key=sub_category_key,
        label_type="highlight",
    )


def resolve_aspect_display(aspect_key: Any, *, locale: str = "en") -> str:
    canonical_aspect = resolve_aspect_alias(aspect_key)
    display_en, display_zh = get_label_registry_state().aspect_display_mapping.get(
        canonical_aspect,
        ("", ""),
    )
    return display_zh if locale == "zh" else display_en
