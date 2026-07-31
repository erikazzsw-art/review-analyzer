from __future__ import annotations

import csv
import hashlib
import json
from collections import Counter
from collections.abc import Iterable
from pathlib import Path
from typing import Any

CUSTOMER_INSIGHTS_V3_LITE_SCHEMA_VERSION = "customer-insights-v3-lite-shadow.1"
CUSTOMER_INSIGHTS_V3_LITE_SOURCE = "customer_label_v2_display_occurrence_projection"
CATALOG_BACKLOG_DRAFT_SCHEMA_VERSION = "customer-label-catalog-backlog-draft.1"

CUSTOMER_INSIGHT_REQUIRED_FIELDS = (
    "insight_id",
    "review_id",
    "label_type",
    "canonical_label_key",
    "aspect_key",
    "evidence",
    "confidence",
    "maturity_level",
    "source_layer",
)
CATALOG_BACKLOG_REQUIRED_FIELDS = (
    "canonical_label_key",
    "label_type",
    "aspect_key",
    "evidence_candidate",
    "downgrade_reasons",
    "maturity_level",
    "review_status",
    "catalog_action",
)

CATALOG_BACKLOG_CSV_FIELDS = CATALOG_BACKLOG_REQUIRED_FIELDS + (
    "category",
    "sub_category",
    "raw_label",
    "display_label_en",
    "display_label_zh",
    "review_count",
    "occurrence_count",
    "source_types",
    "source_ids",
)


def _clean_text(value: Any) -> str:
    return str(value or "").strip()


def _safe_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _stable_hash(payload: dict[str, Any]) -> str:
    encoded = json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
    return hashlib.sha1(encoded.encode("utf-8")).hexdigest()[:16]


def _confidence(value: Any) -> float:
    if isinstance(value, (int, float)):
        return min(max(float(value), 0.0), 1.0)
    cleaned = _clean_text(value).lower()
    if cleaned == "high":
        return 0.92
    if cleaned == "medium":
        return 0.74
    if cleaned == "low":
        return 0.48
    try:
        return min(max(float(cleaned), 0.0), 1.0)
    except ValueError:
        return 0.0


def _dedupe_key(item: dict[str, Any]) -> tuple[str, str, str, str]:
    return (
        _clean_text(item.get("label_type")),
        _clean_text(item.get("canonical_label_key")),
        _clean_text(item.get("aspect_key")),
        _clean_text(item.get("evidence_candidate")).lower(),
    )


def _source_review_id(source: dict[str, Any], occurrence: dict[str, Any]) -> Any:
    return occurrence.get("review_id") or occurrence.get("comment_id") or source.get("review_id")


def project_customer_insights_from_shadow_result(shadow_result: dict[str, Any]) -> dict[str, Any]:
    """Project verified v2 display occurrences into the future customer_insights shape.

    This is intentionally one-way and shadow-only: audit occurrences, raw label
    candidates, and candidate-pool items are only counted as excluded layers.
    """
    insights: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str, str, str]] = set()
    maturity_level = _clean_text(shadow_result.get("maturity_level"))

    for occurrence in _safe_list(shadow_result.get("display_occurrences")):
        if not isinstance(occurrence, dict):
            continue
        review_id = _source_review_id(shadow_result, occurrence)
        label_type = _clean_text(occurrence.get("label_type") or occurrence.get("type"))
        canonical = _clean_text(occurrence.get("canonical_label_key"))
        aspect_key = _clean_text(occurrence.get("aspect_key"))
        evidence_span = _clean_text(occurrence.get("evidence_span"))
        key = (str(review_id), label_type, canonical, aspect_key, evidence_span)
        if not label_type or not canonical or not evidence_span or key in seen:
            continue
        seen.add(key)
        insight_hash = _stable_hash(
            {
                "review_id": review_id,
                "label_type": label_type,
                "canonical_label_key": canonical,
                "aspect_key": aspect_key,
                "evidence_span": evidence_span,
            }
        )
        insights.append(
            {
                "insight_id": f"ci:{insight_hash}",
                "review_id": review_id,
                "label_type": label_type,
                "canonical_label_key": canonical,
                "display_label_en": _clean_text(occurrence.get("display_label_en")),
                "display_label_zh": _clean_text(occurrence.get("display_label_zh")),
                "aspect_key": aspect_key,
                "polarity": _clean_text(occurrence.get("polarity")),
                "evidence": {
                    "span": evidence_span,
                    "start": occurrence.get("evidence_start"),
                    "end": occurrence.get("evidence_end"),
                    "verified": bool(occurrence.get("evidence_verified")),
                    "source_review_allowed": bool(occurrence.get("source_review_allowed")),
                },
                "confidence": _confidence(occurrence.get("confidence")),
                "maturity_level": maturity_level,
                "source_layer": "display_occurrences",
                "source_schema_version": _clean_text(shadow_result.get("schema_version")),
                "source_ruleset_version": _clean_text(shadow_result.get("ruleset_version")),
            }
        )

    return {
        "schema_version": CUSTOMER_INSIGHTS_V3_LITE_SCHEMA_VERSION,
        "source": CUSTOMER_INSIGHTS_V3_LITE_SOURCE,
        "review_id": shadow_result.get("review_id"),
        "category": _clean_text(shadow_result.get("category")),
        "sub_category": _clean_text(shadow_result.get("sub_category")),
        "maturity_level": maturity_level,
        "customer_insights": insights,
        "source_layer_counts": {
            "display_occurrences": len(_safe_list(shadow_result.get("display_occurrences"))),
            "audit_occurrences": len(_safe_list(shadow_result.get("audit_occurrences"))),
            "candidate_pool_items": len(_safe_list(shadow_result.get("candidate_pool_items"))),
            "label_candidates": len(_safe_list(shadow_result.get("label_candidates"))),
        },
        "excluded_from_customer_insights": [
            "audit_occurrences",
            "candidate_pool_items",
            "label_candidates",
        ],
        "safety": _shadow_safety(),
    }


def project_customer_insights_artifact(
    shadow_results: Iterable[dict[str, Any]],
    *,
    scope: str,
    source_artifacts: list[str] | None = None,
) -> dict[str, Any]:
    projections = [project_customer_insights_from_shadow_result(result) for result in shadow_results]
    insight_count = sum(len(item["customer_insights"]) for item in projections)
    display_occurrence_count = sum(item["source_layer_counts"]["display_occurrences"] for item in projections)
    coverage = round(insight_count / display_occurrence_count, 4) if display_occurrence_count else 1.0
    violations = _projection_contract_violations(projections)
    return {
        "schema_version": CUSTOMER_INSIGHTS_V3_LITE_SCHEMA_VERSION,
        "scope": scope,
        "status": "PASS" if coverage >= 0.98 and not violations else "REVIEW_NEEDED",
        "projection_source": CUSTOMER_INSIGHTS_V3_LITE_SOURCE,
        "review_count": len(projections),
        "frontstage_display_occurrence_count": display_occurrence_count,
        "customer_insight_count": insight_count,
        "frontstage_display_occurrence_coverage": coverage,
        "required_fields": list(CUSTOMER_INSIGHT_REQUIRED_FIELDS),
        "contract_violations": violations,
        "projections": projections,
        "source_artifacts": list(source_artifacts or []),
        "safety": _shadow_safety(),
    }


def build_catalog_backlog_draft(
    *,
    shadow_results: Iterable[dict[str, Any]],
    reviewed_candidate_pool_artifact: dict[str, Any] | None = None,
    human_gold_fixture: dict[str, Any] | None = None,
    scope: str,
    source_artifacts: list[str] | None = None,
) -> dict[str, Any]:
    rows: dict[tuple[str, str, str, str], dict[str, Any]] = {}

    for result in shadow_results:
        for occurrence in _safe_list(result.get("display_occurrences")):
            if isinstance(occurrence, dict):
                _merge_backlog_row(
                    rows,
                    _backlog_row_from_display_occurrence(result, occurrence),
                    source_type="verified_waders_display",
                    source_id=_clean_text(result.get("review_id")),
                )

    if human_gold_fixture:
        for sample in _safe_list(human_gold_fixture.get("samples")):
            if not isinstance(sample, dict):
                continue
            for candidate in _safe_list(sample.get("needs_new_label")):
                if isinstance(candidate, dict):
                    _merge_backlog_row(
                        rows,
                        _backlog_row_from_human_new_label(sample, candidate),
                        source_type="waders_351_400_needs_new_label",
                        source_id=_clean_text(sample.get("id")),
                    )

    if reviewed_candidate_pool_artifact:
        for reviewed in _safe_list(reviewed_candidate_pool_artifact.get("reviewed_candidate_pool_items")):
            if isinstance(reviewed, dict):
                _merge_backlog_row(
                    rows,
                    _backlog_row_from_reviewed_candidate(reviewed),
                    source_type="candidate_pool_reviewed",
                    source_id=_clean_text(reviewed.get("candidate_id")),
                )

    backlog_items = sorted(
        rows.values(),
        key=lambda item: (
            item["catalog_action"],
            item["label_type"],
            item["canonical_label_key"],
            item["aspect_key"],
            item["evidence_candidate"],
        ),
    )
    action_counts = Counter(item["catalog_action"] for item in backlog_items)
    status_counts = Counter(item["review_status"] for item in backlog_items)
    violations = _catalog_backlog_violations(backlog_items)
    return {
        "schema_version": CATALOG_BACKLOG_DRAFT_SCHEMA_VERSION,
        "scope": scope,
        "status": "PASS" if not violations else "REVIEW_NEEDED",
        "item_count": len(backlog_items),
        "required_fields": list(CATALOG_BACKLOG_REQUIRED_FIELDS),
        "catalog_backlog_items": backlog_items,
        "summary": {
            "catalog_action_counts": dict(sorted(action_counts.items())),
            "review_status_counts": dict(sorted(status_counts.items())),
        },
        "contract_violations": violations,
        "runtime_generation_source": False,
        "source_artifacts": list(source_artifacts or []),
        "safety": _shadow_safety(),
    }


def write_customer_insights_json_artifact(path: Path, artifact: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(artifact, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def write_catalog_backlog_csv(path: Path, items: Iterable[dict[str, Any]]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CATALOG_BACKLOG_CSV_FIELDS, extrasaction="ignore")
        writer.writeheader()
        for item in items:
            row = dict(item)
            for field in ("downgrade_reasons", "source_types", "source_ids"):
                row[field] = "|".join(_clean_text(value) for value in _safe_list(row.get(field)))
            writer.writerow(row)
    return path


def _backlog_row_from_display_occurrence(
    shadow_result: dict[str, Any],
    occurrence: dict[str, Any],
) -> dict[str, Any]:
    return {
        "canonical_label_key": _clean_text(occurrence.get("canonical_label_key")),
        "label_type": _clean_text(occurrence.get("label_type") or occurrence.get("type")),
        "aspect_key": _clean_text(occurrence.get("aspect_key")),
        "evidence_candidate": _clean_text(occurrence.get("evidence_span")),
        "downgrade_reasons": [],
        "maturity_level": _clean_text(shadow_result.get("maturity_level")),
        "review_status": "verified_display",
        "catalog_action": "keep_active",
        "category": _clean_text(shadow_result.get("category")),
        "sub_category": _clean_text(shadow_result.get("sub_category")),
        "raw_label": _clean_text(occurrence.get("raw_label")),
        "display_label_en": _clean_text(occurrence.get("display_label_en")),
        "display_label_zh": _clean_text(occurrence.get("display_label_zh")),
        "review_count": 1,
        "occurrence_count": 1,
    }


def _backlog_row_from_human_new_label(sample: dict[str, Any], candidate: dict[str, Any]) -> dict[str, Any]:
    evidence_spans = _safe_list(candidate.get("evidence_spans"))
    evidence = evidence_spans[0] if evidence_spans and isinstance(evidence_spans[0], dict) else {}
    return {
        "canonical_label_key": _clean_text(candidate.get("canonical_label_key")),
        "label_type": _clean_text(candidate.get("label_type")),
        "aspect_key": "unknown",
        "evidence_candidate": _clean_text(evidence.get("evidence_span")),
        "downgrade_reasons": [_clean_text(candidate.get("reason")) or "needs_new_label"],
        "maturity_level": "L3_sub_category",
        "review_status": _clean_text(candidate.get("review_status")) or "needs_new_label",
        "catalog_action": "propose_new_label",
        "category": "outdoor",
        "sub_category": "waders",
        "raw_label": _clean_text(candidate.get("raw_label") or candidate.get("raw_label_zh")),
        "display_label_en": _clean_text(candidate.get("raw_label")),
        "display_label_zh": _clean_text(candidate.get("raw_label_zh")),
        "review_count": 1,
        "occurrence_count": 1,
    }


def _backlog_row_from_reviewed_candidate(reviewed: dict[str, Any]) -> dict[str, Any]:
    source = reviewed.get("source_candidate_item") if isinstance(reviewed.get("source_candidate_item"), dict) else {}
    output = reviewed.get("review_output") if isinstance(reviewed.get("review_output"), dict) else {}
    review_status = _clean_text(reviewed.get("review_status")) or _clean_text(source.get("review_status"))
    canonical = _clean_text(output.get("canonical_label_key")) or _clean_text(source.get("canonical_label_key"))
    label_type = _clean_text(output.get("label_type")) or _clean_text(source.get("label_type"))
    action = "maturity_review" if review_status == "accepted" else "propose_new_label"
    return {
        "canonical_label_key": canonical,
        "label_type": label_type,
        "aspect_key": _clean_text(source.get("aspect_key")) or "unknown",
        "evidence_candidate": _clean_text(output.get("evidence_candidate")) or _clean_text(source.get("evidence_candidate")),
        "downgrade_reasons": list(source.get("downgrade_reasons") or []),
        "maturity_level": _clean_text(source.get("maturity_level")) or "unknown",
        "review_status": review_status,
        "catalog_action": action,
        "category": _clean_text(source.get("category")),
        "sub_category": _clean_text(source.get("sub_category")),
        "raw_label": _clean_text(output.get("raw_label")) or _clean_text(source.get("raw_label")),
        "display_label_en": _clean_text(output.get("raw_label")) or _clean_text(source.get("raw_label")),
        "display_label_zh": "",
        "review_count": int(source.get("review_count") or 1),
        "occurrence_count": int(source.get("candidate_count") or 1),
    }


def _merge_backlog_row(
    rows: dict[tuple[str, str, str, str], dict[str, Any]],
    row: dict[str, Any],
    *,
    source_type: str,
    source_id: str,
) -> None:
    if not row.get("canonical_label_key") or not row.get("label_type"):
        return
    key = _dedupe_key(row)
    existing = rows.get(key)
    if existing is None:
        row["source_types"] = [source_type]
        row["source_ids"] = [source_id] if source_id else []
        rows[key] = row
        return
    existing["review_count"] = int(existing.get("review_count") or 0) + int(row.get("review_count") or 0)
    existing["occurrence_count"] = int(existing.get("occurrence_count") or 0) + int(row.get("occurrence_count") or 0)
    for reason in row.get("downgrade_reasons") or []:
        if reason and reason not in existing["downgrade_reasons"]:
            existing["downgrade_reasons"].append(reason)
    if source_type not in existing["source_types"]:
        existing["source_types"].append(source_type)
    if source_id and source_id not in existing["source_ids"]:
        existing["source_ids"].append(source_id)
    if existing["catalog_action"] == "keep_active" and row["catalog_action"] != "keep_active":
        existing["catalog_action"] = row["catalog_action"]
        existing["review_status"] = row["review_status"]


def _projection_contract_violations(projections: list[dict[str, Any]]) -> list[dict[str, Any]]:
    violations: list[dict[str, Any]] = []
    for projection in projections:
        for insight in projection["customer_insights"]:
            missing = [field for field in CUSTOMER_INSIGHT_REQUIRED_FIELDS if field not in insight]
            if missing:
                violations.append(
                    {
                        "review_id": projection.get("review_id"),
                        "insight_id": insight.get("insight_id"),
                        "missing_fields": missing,
                    }
                )
            if insight.get("source_layer") != "display_occurrences":
                violations.append(
                    {
                        "review_id": projection.get("review_id"),
                        "insight_id": insight.get("insight_id"),
                        "source_layer": insight.get("source_layer"),
                    }
                )
    return violations


def _catalog_backlog_violations(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    violations: list[dict[str, Any]] = []
    for index, item in enumerate(items):
        missing = [field for field in CATALOG_BACKLOG_REQUIRED_FIELDS if field not in item]
        if missing:
            violations.append({"index": index, "missing_fields": missing})
        if item.get("catalog_action") not in {"keep_active", "propose_new_label", "maturity_review"}:
            violations.append({"index": index, "invalid_catalog_action": item.get("catalog_action")})
    return violations


def _shadow_safety() -> dict[str, bool]:
    return {
        "production_upload": False,
        "production_write_path": False,
        "production_db_write": False,
        "db_write": False,
        "credit_consumed": False,
        "llm_called": False,
        "prompt_changed": False,
        "frontstage_replaced": False,
        "frontstage_mutated": False,
        "runtime_generation_source": False,
    }
