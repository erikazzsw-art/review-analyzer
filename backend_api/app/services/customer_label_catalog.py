"""Customer-facing label catalog resolver.

Phase 2 keeps this as a conservative data layer: catalog and alias rules can
normalize labels, but analysis still falls back to the existing in-code rules
when the DB tables are unavailable or empty.
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Any

logger = logging.getLogger(__name__)

CUSTOMER_LABEL_CATALOG_RULESET_VERSION = "2026-07-24-customer-label-catalog-v1"
LABEL_TYPES = {"issue", "highlight"}
SCOPE_LEVELS = {"global", "category", "sub_category"}
RULE_TYPES = {"exact", "contains", "regex", "blocklist"}


@dataclass(frozen=True)
class CustomerLabel:
    label_type: str
    canonical_label_key: str
    display_en: str
    display_zh: str = ""
    primary_aspect_key: str = ""
    aspect_keys: tuple[str, ...] = ()
    scope_level: str = "global"
    category_key: str = "*"
    sub_category_key: str = "*"
    display_allowed: bool = True
    status: str = "active"
    source: str = "system"
    ruleset_version: str = CUSTOMER_LABEL_CATALOG_RULESET_VERSION
    metadata: dict[str, Any] = field(default_factory=dict)
    id: int | None = None


@dataclass(frozen=True)
class CustomerLabelAliasRule:
    label_type: str
    rule_type: str
    pattern: str
    canonical_label_key: str | None = None
    normalized_pattern: str = ""
    scope_level: str = "global"
    category_key: str = "*"
    sub_category_key: str = "*"
    aspect_key: str = "*"
    display_allowed: bool = True
    confidence: str = "medium"
    priority: int = 100
    enabled: bool = True
    source: str = "system"
    ruleset_version: str = CUSTOMER_LABEL_CATALOG_RULESET_VERSION
    metadata: dict[str, Any] = field(default_factory=dict)
    id: int | None = None


@dataclass(frozen=True)
class CustomerLabelCatalogState:
    labels: tuple[CustomerLabel, ...] = ()
    alias_rules: tuple[CustomerLabelAliasRule, ...] = ()
    source: str = "fallback"


@dataclass(frozen=True)
class CustomerLabelResolution:
    label_type: str
    canonical_label_key: str
    display_en: str
    display_zh: str
    display_allowed: bool
    confidence: str
    source: str
    ruleset_version: str
    matched_catalog_id: int | None = None
    matched_alias_rule_id: int | None = None


_TEST_STATE: CustomerLabelCatalogState | None = None


def normalize_label_text(value: str) -> str:
    value = value.replace("&", " and ")
    value = re.sub(r"[^a-z0-9]+", " ", value.lower())
    return re.sub(r"\s+", " ", value).strip()


def _slug(value: str) -> str:
    normalized = normalize_label_text(value)
    return re.sub(r"[^a-z0-9]+", "_", normalized).strip("_") or "unspecified_label"


def _as_bool(value: Any, default: bool = True) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    if isinstance(value, str):
        return value.strip().lower() not in {"false", "0", "no"}
    return bool(value)


def _as_tuple(value: Any) -> tuple[str, ...]:
    if not value:
        return ()
    if isinstance(value, (list, tuple, set)):
        return tuple(str(item).strip() for item in value if str(item).strip())
    return (str(value).strip(),)


def _clean_label_type(label_type: str) -> str:
    cleaned = str(label_type or "").strip().lower()
    return cleaned if cleaned in LABEL_TYPES else "issue"


def _clean_scope(scope_level: str) -> str:
    cleaned = str(scope_level or "").strip().lower()
    return cleaned if cleaned in SCOPE_LEVELS else "global"


def _row_to_label(row: dict[str, Any]) -> CustomerLabel:
    return CustomerLabel(
        label_type=_clean_label_type(str(row.get("label_type") or "")),
        canonical_label_key=str(row.get("canonical_label_key") or "").strip(),
        display_en=str(row.get("display_en") or "").strip(),
        display_zh=str(row.get("display_zh") or "").strip(),
        primary_aspect_key=str(row.get("primary_aspect_key") or "").strip(),
        aspect_keys=_as_tuple(row.get("aspect_keys")),
        scope_level=_clean_scope(str(row.get("scope_level") or "")),
        category_key=str(row.get("category_key") or "*").strip() or "*",
        sub_category_key=str(row.get("sub_category_key") or "*").strip() or "*",
        display_allowed=_as_bool(row.get("display_allowed"), True),
        status=str(row.get("status") or "active").strip() or "active",
        source=str(row.get("source") or "system").strip() or "system",
        ruleset_version=str(row.get("ruleset_version") or CUSTOMER_LABEL_CATALOG_RULESET_VERSION),
        metadata=dict(row.get("metadata") or {}),
        id=int(row["id"]) if row.get("id") is not None else None,
    )


def _row_to_alias_rule(row: dict[str, Any]) -> CustomerLabelAliasRule:
    pattern = str(row.get("pattern") or "").strip()
    normalized = str(row.get("normalized_pattern") or "").strip() or normalize_label_text(pattern)
    return CustomerLabelAliasRule(
        label_type=_clean_label_type(str(row.get("label_type") or "")),
        rule_type=str(row.get("rule_type") or "").strip().lower(),
        pattern=pattern,
        normalized_pattern=normalized,
        canonical_label_key=str(row.get("canonical_label_key") or "").strip() or None,
        scope_level=_clean_scope(str(row.get("scope_level") or "")),
        category_key=str(row.get("category_key") or "*").strip() or "*",
        sub_category_key=str(row.get("sub_category_key") or "*").strip() or "*",
        aspect_key=str(row.get("aspect_key") or "*").strip() or "*",
        display_allowed=_as_bool(row.get("display_allowed"), True),
        confidence=str(row.get("confidence") or "medium").strip().lower() or "medium",
        priority=int(row.get("priority") or 100),
        enabled=_as_bool(row.get("enabled"), True),
        source=str(row.get("source") or "system").strip() or "system",
        ruleset_version=str(row.get("ruleset_version") or CUSTOMER_LABEL_CATALOG_RULESET_VERSION),
        metadata=dict(row.get("metadata") or {}),
        id=int(row["id"]) if row.get("id") is not None else None,
    )


def _load_catalog_state_from_db() -> CustomerLabelCatalogState | None:
    try:
        import psycopg2.extras

        from review_analyzer.database import get_connection
    except Exception as exc:
        logger.warning("customer_label_catalog: cannot import db deps: %s", exc)
        return None

    try:
        conn = get_connection()
    except Exception as exc:
        logger.warning("customer_label_catalog: get_connection failed: %s", exc)
        return None

    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """SELECT id, label_type, canonical_label_key, display_en, display_zh,
                          primary_aspect_key, aspect_keys, scope_level, category_key,
                          sub_category_key, display_allowed, status, source,
                          ruleset_version, metadata
                   FROM customer_label_catalog
                   WHERE status IN ('active', 'disabled', 'deprecated', 'merged')
                   ORDER BY label_type, scope_level, canonical_label_key"""
            )
            labels = tuple(_row_to_label(dict(row)) for row in cur.fetchall())
            cur.execute(
                """SELECT id, label_type, scope_level, category_key, sub_category_key,
                          aspect_key, rule_type, pattern, normalized_pattern,
                          canonical_label_key, display_allowed, confidence, priority,
                          enabled, source, ruleset_version, metadata
                   FROM customer_label_alias_rules
                   WHERE enabled = TRUE
                   ORDER BY label_type, scope_level, priority, id"""
            )
            alias_rules = tuple(_row_to_alias_rule(dict(row)) for row in cur.fetchall())
    except Exception as exc:
        logger.warning("customer_label_catalog: query failed: %s", exc)
        try:
            conn.rollback()
        except Exception:
            pass
        return None
    finally:
        try:
            conn.close()
        except Exception:
            pass

    return CustomerLabelCatalogState(labels=labels, alias_rules=alias_rules, source="db")


def _fallback_alias_rules() -> tuple[CustomerLabelAliasRule, ...]:
    broad = (
        "Accessories & Storage",
        "Accessory Storage",
        "Aesthetics",
        "Assembly",
        "Build Quality",
        "Capacity",
        "Comfort",
        "Durability",
        "Ease of Use",
        "Material",
        "Materials",
        "Other",
        "Packaging",
        "Product Quality",
        "Quality",
        "Waterproof",
        "Waterproof Performance",
        "Waterproofing",
    )
    return tuple(
        CustomerLabelAliasRule(
            label_type=label_type,
            rule_type="blocklist",
            pattern=pattern,
            normalized_pattern=normalize_label_text(pattern),
            display_allowed=False,
            confidence="high",
            priority=10,
            source="fallback",
        )
        for label_type in ("issue", "highlight")
        for pattern in broad
    )


def _fallback_catalog_state() -> CustomerLabelCatalogState:
    return CustomerLabelCatalogState(labels=(), alias_rules=_fallback_alias_rules(), source="fallback")


@lru_cache(maxsize=1)
def _load_catalog_state() -> CustomerLabelCatalogState:
    state = _load_catalog_state_from_db()
    if state and (state.labels or state.alias_rules):
        return state
    return _fallback_catalog_state()


def get_customer_label_catalog_state() -> CustomerLabelCatalogState:
    if _TEST_STATE is not None:
        return _TEST_STATE
    return _load_catalog_state()


def clear_customer_label_catalog_cache() -> None:
    _load_catalog_state.cache_clear()


def set_customer_label_catalog_state_for_tests(state: CustomerLabelCatalogState | None) -> None:
    global _TEST_STATE
    _TEST_STATE = state
    clear_customer_label_catalog_cache()


def _scope_rank(scope_level: str, category_key: str, sub_category_key: str, row_category: str, row_sub_category: str) -> int:
    scope_level = _clean_scope(scope_level)
    category = category_key or "*"
    sub_category = sub_category_key or "*"
    if scope_level == "sub_category":
        if row_sub_category not in {sub_category, "*"}:
            return -1
        return 30
    if scope_level == "category":
        if row_category not in {category, "*"}:
            return -1
        return 20
    return 10


def _aspect_rank(rule_aspect: str, aspect_key: str) -> int:
    rule_aspect = (rule_aspect or "*").strip()
    if rule_aspect == "*":
        return 0
    return 5 if rule_aspect == aspect_key else -1


def _label_aspect_rank(label: CustomerLabel, aspect_key: str) -> int:
    if not aspect_key:
        return 0
    aspect_keys = set(label.aspect_keys)
    if label.primary_aspect_key:
        aspect_keys.add(label.primary_aspect_key)
    if not aspect_keys:
        return 0
    return 5 if aspect_key in aspect_keys else 0


def _pattern_matches(rule: CustomerLabelAliasRule, raw_text: str, normalized_raw_text: str) -> bool:
    if not rule.enabled or rule.rule_type not in RULE_TYPES:
        return False
    pattern = rule.pattern.strip()
    normalized_pattern = rule.normalized_pattern or normalize_label_text(pattern)
    if not pattern and not normalized_pattern:
        return False
    if rule.rule_type in {"exact", "blocklist"}:
        return normalized_raw_text == normalized_pattern
    if rule.rule_type == "contains":
        return bool(normalized_pattern and normalized_pattern in normalized_raw_text)
    try:
        return bool(re.search(pattern, raw_text, re.IGNORECASE))
    except re.error:
        logger.warning("customer_label_catalog: invalid regex alias pattern=%r", pattern)
        return False


def _matching_alias_rules(
    state: CustomerLabelCatalogState,
    *,
    label_type: str,
    raw_text: str,
    normalized_raw_text: str,
    aspect_key: str,
    category_key: str,
    sub_category_key: str,
) -> list[tuple[int, int, CustomerLabelAliasRule]]:
    matches: list[tuple[int, int, CustomerLabelAliasRule]] = []
    for rule in state.alias_rules:
        if rule.label_type != label_type:
            continue
        scope = _scope_rank(
            rule.scope_level,
            category_key,
            sub_category_key,
            rule.category_key,
            rule.sub_category_key,
        )
        if scope < 0:
            continue
        aspect = _aspect_rank(rule.aspect_key, aspect_key)
        if aspect < 0:
            continue
        if _pattern_matches(rule, raw_text, normalized_raw_text):
            matches.append((scope, aspect, rule))
    return sorted(matches, key=lambda item: (-item[0], -item[1], item[2].priority, item[2].id or 0))


def _matching_catalog_labels(
    state: CustomerLabelCatalogState,
    *,
    label_type: str,
    canonical_label_key: str,
    aspect_key: str,
    category_key: str,
    sub_category_key: str,
) -> list[tuple[int, int, CustomerLabel]]:
    matches: list[tuple[int, int, CustomerLabel]] = []
    for label in state.labels:
        if label.label_type != label_type or label.canonical_label_key != canonical_label_key:
            continue
        scope = _scope_rank(
            label.scope_level,
            category_key,
            sub_category_key,
            label.category_key,
            label.sub_category_key,
        )
        if scope < 0:
            continue
        matches.append((scope, _label_aspect_rank(label, aspect_key), label))
    return sorted(matches, key=lambda item: (-item[0], -item[1], item[2].id or 0))


def resolve_customer_label(
    *,
    label_type: str,
    canonical_label_key: str,
    display_en: str,
    display_zh: str = "",
    raw_label: str = "",
    aspect_key: str = "",
    category_key: str = "",
    sub_category_key: str = "",
    confidence: str = "medium",
    display_allowed: bool = True,
) -> CustomerLabelResolution:
    cleaned_type = _clean_label_type(label_type)
    display_en = display_en.strip()
    display_zh = display_zh.strip()
    raw_text = (raw_label or display_en or canonical_label_key).strip()
    normalized_raw = normalize_label_text(raw_text)
    canonical = canonical_label_key.strip() or _slug(display_en or raw_text)
    allowed = bool(display_allowed)
    source = "catalog_passthrough"
    ruleset_version = CUSTOMER_LABEL_CATALOG_RULESET_VERSION
    matched_alias_id: int | None = None

    state = get_customer_label_catalog_state()
    alias_matches = _matching_alias_rules(
        state,
        label_type=cleaned_type,
        raw_text=raw_text,
        normalized_raw_text=normalized_raw,
        aspect_key=aspect_key.strip(),
        category_key=category_key.strip() or "*",
        sub_category_key=sub_category_key.strip() or "*",
    )
    if alias_matches:
        alias = alias_matches[0][2]
        matched_alias_id = alias.id
        ruleset_version = alias.ruleset_version
        if alias.rule_type == "blocklist":
            return CustomerLabelResolution(
                label_type=cleaned_type,
                canonical_label_key=canonical,
                display_en=display_en,
                display_zh=display_zh,
                display_allowed=False,
                confidence=alias.confidence or confidence,
                source="catalog_blocklist",
                ruleset_version=ruleset_version,
                matched_alias_rule_id=matched_alias_id,
            )
        if alias.canonical_label_key:
            canonical = alias.canonical_label_key
            confidence = alias.confidence or confidence
            allowed = allowed and alias.display_allowed
            source = "catalog_alias_rule"

    catalog_matches = _matching_catalog_labels(
        state,
        label_type=cleaned_type,
        canonical_label_key=canonical,
        aspect_key=aspect_key.strip(),
        category_key=category_key.strip() or "*",
        sub_category_key=sub_category_key.strip() or "*",
    )
    matched_catalog_id: int | None = None
    if catalog_matches:
        label = catalog_matches[0][2]
        matched_catalog_id = label.id
        display_en = label.display_en or display_en
        display_zh = label.display_zh or display_zh
        allowed = allowed and label.display_allowed and label.status == "active"
        ruleset_version = label.ruleset_version or ruleset_version
        if source == "catalog_passthrough":
            source = "catalog"

    return CustomerLabelResolution(
        label_type=cleaned_type,
        canonical_label_key=canonical,
        display_en=display_en,
        display_zh=display_zh,
        display_allowed=allowed,
        confidence=confidence,
        source=source,
        ruleset_version=ruleset_version,
        matched_catalog_id=matched_catalog_id,
        matched_alias_rule_id=matched_alias_id,
    )


def build_customer_label_candidate_payload(
    *,
    label_type: str,
    raw_label: str,
    aspect_key: str = "",
    category_key: str = "",
    sub_category_key: str = "",
    suggested_canonical_label_key: str | None = None,
    suggested_display_en: str | None = None,
    suggested_display_zh: str | None = None,
    evidence_span: str | None = None,
) -> dict[str, Any]:
    normalized = normalize_label_text(raw_label)
    return {
        "label_type": _clean_label_type(label_type),
        "raw_label": raw_label.strip(),
        "normalized_raw_label": normalized,
        "category_key": category_key.strip() or "*",
        "sub_category_key": sub_category_key.strip() or "*",
        "aspect_key": aspect_key.strip(),
        "suggested_canonical_label_key": suggested_canonical_label_key or None,
        "suggested_display_en": suggested_display_en or None,
        "suggested_display_zh": suggested_display_zh or None,
        "sample_evidence_spans": [evidence_span] if evidence_span else [],
    }


def upsert_customer_label_candidate(payload: dict[str, Any]) -> bool:
    """Persist a candidate raw label when callers opt in.

    This is deliberately best-effort so candidate collection never blocks the
    analysis pipeline.
    """
    if not payload.get("raw_label") or not payload.get("normalized_raw_label"):
        return False
    try:
        import psycopg2.extras

        from review_analyzer.database import get_connection
    except Exception as exc:
        logger.warning("customer_label_catalog: cannot import db deps for candidate: %s", exc)
        return False

    try:
        conn = get_connection()
    except Exception as exc:
        logger.warning("customer_label_catalog: get_connection failed for candidate: %s", exc)
        return False

    try:
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO customer_label_candidates (
                       label_type, raw_label, normalized_raw_label, category_key,
                       sub_category_key, aspect_key, suggested_canonical_label_key,
                       suggested_display_en, suggested_display_zh, occurrence_count,
                       review_count, sample_evidence_spans, last_seen_at
                   )
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 1, 1, %s, NOW())
                   ON CONFLICT (
                       label_type, normalized_raw_label, category_key, sub_category_key, aspect_key
                   )
                   DO UPDATE SET
                       occurrence_count = customer_label_candidates.occurrence_count + 1,
                       review_count = customer_label_candidates.review_count + 1,
                       sample_evidence_spans = CASE
                           WHEN jsonb_array_length(customer_label_candidates.sample_evidence_spans) >= 5
                           THEN customer_label_candidates.sample_evidence_spans
                           ELSE customer_label_candidates.sample_evidence_spans || EXCLUDED.sample_evidence_spans
                       END,
                       suggested_canonical_label_key = COALESCE(
                           customer_label_candidates.suggested_canonical_label_key,
                           EXCLUDED.suggested_canonical_label_key
                       ),
                       suggested_display_en = COALESCE(
                           customer_label_candidates.suggested_display_en,
                           EXCLUDED.suggested_display_en
                       ),
                       suggested_display_zh = COALESCE(
                           customer_label_candidates.suggested_display_zh,
                           EXCLUDED.suggested_display_zh
                       ),
                       last_seen_at = NOW(),
                       updated_at = NOW()""",
                (
                    payload["label_type"],
                    payload["raw_label"],
                    payload["normalized_raw_label"],
                    payload.get("category_key") or "*",
                    payload.get("sub_category_key") or "*",
                    payload.get("aspect_key") or "",
                    payload.get("suggested_canonical_label_key"),
                    payload.get("suggested_display_en"),
                    payload.get("suggested_display_zh"),
                    psycopg2.extras.Json(payload.get("sample_evidence_spans") or []),
                ),
            )
        conn.commit()
        return True
    except Exception as exc:
        logger.warning("customer_label_catalog: candidate upsert failed: %s", exc)
        try:
            conn.rollback()
        except Exception:
            pass
        return False
    finally:
        try:
            conn.close()
        except Exception:
            pass
