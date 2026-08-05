"""Unified 5.9.6-A catalog and resolver for formal review-fragment labels.

The registry fixture is the active-side migration target for the approved
labels, aspect aliases, and display mappings that previously lived in the
5.9.4 experiment module. This module deliberately has no dependency on that
experiment module.
"""
from __future__ import annotations

import logging
import re
from collections.abc import Collection, Mapping
from dataclasses import dataclass, field, replace
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)

FORMAL_LABEL_REGISTRY_VERSION = "review-fragment-label-registry.5.9.6-A.1"
FORMAL_LABEL_TYPES = frozenset({"issue", "highlight"})
FORMAL_LABEL_STATUSES = frozenset({"candidate", "approved", "merged", "deprecated", "blocked"})
APPROVED_LABEL_STATUS = "approved"

_REGISTRY_PATH = (
    Path(__file__).resolve().parents[3]
    / "data"
    / "taxonomy"
    / "registry"
    / "review_fragment_label_registry.yaml"
)


@dataclass(frozen=True)
class FormalLabelDefinition:
    """A formal issue/highlight definition returned by the registry."""

    key: str
    label_type: str
    category_keys: tuple[str, ...]
    sub_category_keys: tuple[str, ...]
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
class LabelRegistryState:
    labels: tuple[FormalLabelDefinition, ...] = ()
    aspect_aliases: Mapping[str, str] = field(default_factory=dict)
    aspect_display_mapping: Mapping[str, tuple[str, str]] = field(default_factory=dict)
    highlight_by_aspect: Mapping[str, str] = field(default_factory=dict)
    registry_version: str = FORMAL_LABEL_REGISTRY_VERSION
    source: str = "fixture"


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

    return FormalLabelDefinition(
        key=_clean(raw.get("key")),
        label_type=label_type,
        category_keys=_string_tuple(raw.get("category_keys"), default=("*",)),
        sub_category_keys=_string_tuple(raw.get("sub_category_keys"), default=("*",)),
        status=status,
        display_label_en=_clean(display.get("en")),
        display_label_zh=_clean(display.get("zh")),
        boundary_note=_clean(raw.get("boundary_note")),
        aliases=_string_tuple(raw.get("aliases")),
        aspect_keys=aspect_keys,
        formal_module=_clean(raw.get("formal_module")),
        registry_version=registry_version,
        source=source,
    )


def _load_registry_from_file() -> LabelRegistryState:
    try:
        raw = yaml.safe_load(_REGISTRY_PATH.read_text(encoding="utf-8")) or {}
        registry_version = _clean(raw.get("registry_version")) or FORMAL_LABEL_REGISTRY_VERSION
        source = _clean(raw.get("source")) or "fixture"
        labels = tuple(
            _load_label(item, registry_version=registry_version, source=source)
            for item in raw.get("labels") or []
            if isinstance(item, Mapping)
        )
        if len({(label.label_type, label.key) for label in labels}) != len(labels):
            raise ValueError("duplicate formal label identity")

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
            labels=labels,
            aspect_aliases=aspect_aliases,
            aspect_display_mapping=display_mapping,
            highlight_by_aspect=highlight_by_aspect,
            registry_version=registry_version,
            source=source,
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


def _scope_matches(allowed_values: Collection[str], requested_value: str) -> bool:
    allowed = {value for value in (_clean(item) for item in allowed_values) if value}
    requested = _clean(requested_value)
    if "*" in allowed:
        return True
    return bool(requested and requested in allowed)


def resolve_formal_label(
    key_or_alias: Any,
    *,
    label_type: str | None = None,
    category_key: str = "",
    sub_category_key: str = "",
    approved_only: bool = True,
) -> LabelResolution | None:
    """Resolve a canonical key or alias to an approved formal definition."""

    requested = _clean(key_or_alias)
    if not requested:
        return None
    requested_type = _clean(label_type).lower() or None
    if requested_type and requested_type not in FORMAL_LABEL_TYPES:
        return None
    requested_lookup = _lookup_text(requested)
    matches: list[tuple[FormalLabelDefinition, str | None]] = []
    for label in get_label_registry_state().labels:
        if requested_type and label.label_type != requested_type:
            continue
        if approved_only and label.status != APPROVED_LABEL_STATUS:
            continue
        if not _scope_matches(label.category_keys, category_key):
            continue
        if not _scope_matches(label.sub_category_keys, sub_category_key):
            continue
        if requested == label.key:
            matches.append((label, None))
            continue
        if requested_lookup and requested_lookup in {_lookup_text(alias) for alias in label.aliases}:
            matches.append((label, requested))

    if not matches:
        return None
    distinct_keys = {label.key for label, _ in matches}
    if len(distinct_keys) > 1:
        logger.warning("review_fragment_label_catalog: ambiguous alias=%r keys=%s", requested, sorted(distinct_keys))
        return None
    label, matched_alias = matches[0]
    return replace(label, matched_alias=matched_alias)


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
    label_type: str | None = None,
    category_key: str = "",
    sub_category_key: str = "",
) -> str | None:
    """Resolve a formal label's taxonomy aspect without changing its identity."""

    label = resolve_formal_label(
        label_key_or_alias,
        label_type=label_type,
        category_key=category_key,
        sub_category_key=sub_category_key,
    )
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
    category_key: str = "",
    sub_category_key: str = "",
) -> LabelResolution | None:
    canonical_aspect = resolve_aspect_alias(aspect_key)
    label_key = get_label_registry_state().highlight_by_aspect.get(canonical_aspect)
    if not label_key:
        return None
    return resolve_formal_label(
        label_key,
        label_type="highlight",
        category_key=category_key,
        sub_category_key=sub_category_key,
    )


def resolve_aspect_display(aspect_key: Any, *, locale: str = "en") -> str:
    canonical_aspect = resolve_aspect_alias(aspect_key)
    display_en, display_zh = get_label_registry_state().aspect_display_mapping.get(
        canonical_aspect,
        ("", ""),
    )
    return display_zh if locale == "zh" else display_en
