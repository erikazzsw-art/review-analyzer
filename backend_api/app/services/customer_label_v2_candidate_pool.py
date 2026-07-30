from __future__ import annotations

import csv
import hashlib
import json
from collections.abc import Iterable
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

CANDIDATE_POOL_MVP_SCHEMA_VERSION = "customer-label-v2-candidate-pool-mvp.1"
REVIEWED_CANDIDATE_POOL_MVP_SCHEMA_VERSION = "customer-label-v2-candidate-pool-reviewed-mvp.1"
CANDIDATE_POOL_PENDING_STATUS = "pending"
DETERMINISTIC_REVIEWED_AT = "2026-07-30T00:00:00Z"
CANDIDATE_POOL_REQUIRED_FIELDS = (
    "candidate_id",
    "review_id",
    "session_id",
    "product_id",
    "category",
    "sub_category",
    "label_type",
    "canonical_label_key",
    "raw_label",
    "evidence_candidate",
    "confidence",
    "downgrade_reasons",
    "top_impact_score",
    "review_status",
)
CANDIDATE_POOL_DEDUPE_FIELDS = (
    "canonical_label_key",
    "raw_label",
    "sub_category",
    "downgrade_reasons",
)
CANDIDATE_POOL_REVIEW_ACTIONS = {
    "accept",
    "reject",
    "correct_label",
    "correct_evidence",
    "needs_new_label",
    "ignore",
}
CANDIDATE_POOL_REVIEW_STATUS_BY_ACTION = {
    "accept": "accepted",
    "reject": "rejected",
    "ignore": "ignored",
    "correct_label": "corrected_label",
    "correct_evidence": "corrected_evidence",
    "needs_new_label": "needs_new_label",
}
VALID_LABEL_TYPES = {"issue", "highlight"}

DOWNGRADE_REASON_PRIORITY = {
    "unknown_label": 100,
    "maturity_blocked": 90,
    "aspect_blocked": 70,
    "source_review_blocked": 60,
    "context_blocked": 50,
    "confidence_low": 40,
    "evidence_not_found": 30,
    "evidence_missing": 30,
    "evidence_too_generic": 20,
    "schema_invalid": 10,
    "invalid_json": 10,
    "cluster_propagated": 5,
    "legacy_fallback": 5,
}

CSV_EXPORT_FIELDS = CANDIDATE_POOL_REQUIRED_FIELDS + (
    "review_count",
    "candidate_count",
    "max_confidence",
    "avg_confidence",
    "downgrade_reason_priority",
    "review_ids",
    "session_ids",
    "product_ids",
    "source_candidate_ids",
)
REVIEWED_CSV_EXPORT_FIELDS = CSV_EXPORT_FIELDS + (
    "source_review_status",
    "action",
    "action_applied",
    "validation_errors",
    "reviewed_at",
    "reviewer",
    "note",
    "output_label_type",
    "output_canonical_label_key",
    "output_raw_label",
    "output_evidence_candidate",
)


@dataclass(frozen=True)
class CandidatePoolReviewAction:
    candidate_id: str
    action: str
    label_type: str | None = None
    canonical_label_key: str | None = None
    raw_label: str | None = None
    evidence_candidate: str | None = None
    reviewer: str | None = None
    note: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def _as_shadow_results(shadow_results: dict[str, Any] | Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    if isinstance(shadow_results, dict):
        return [shadow_results]
    return [result for result in shadow_results if isinstance(result, dict)]


def _clean_text(value: Any) -> str:
    return str(value or "").strip()


def _dedupe_text(value: Any) -> str:
    return " ".join(_clean_text(value).lower().split())


def _confidence(value: Any) -> float:
    try:
        confidence = float(value)
    except (TypeError, ValueError):
        return 0.0
    return min(max(confidence, 0.0), 1.0)


def _non_negative_float(value: Any) -> float:
    try:
        score = float(value)
    except (TypeError, ValueError):
        return 0.0
    return max(score, 0.0)


def _sorted_unique(values: Iterable[Any]) -> list[Any]:
    cleaned = [value for value in values if value is not None and _clean_text(value)]
    return sorted(cleaned, key=lambda value: _clean_text(value))


def _normalize_reasons(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    reasons: list[str] = []
    for reason in value:
        cleaned = _clean_text(reason)
        if cleaned and cleaned not in reasons:
            reasons.append(cleaned)
    return sorted(reasons)


def _reason_priority(reasons: Iterable[str]) -> int:
    return max((DOWNGRADE_REASON_PRIORITY.get(reason, 0) for reason in reasons), default=0)


def _review_count_for_items(items: list[dict[str, Any]]) -> int:
    review_keys = {
        _clean_text(item.get("review_id")) or _clean_text(item.get("candidate_id"))
        for item in items
        if _clean_text(item.get("review_id")) or _clean_text(item.get("candidate_id"))
    }
    return len(review_keys)


def normalize_candidate_pool_item(item: dict[str, Any]) -> dict[str, Any]:
    reasons = _normalize_reasons(item.get("downgrade_reasons"))
    confidence = _confidence(item.get("confidence"))
    normalized = {
        "candidate_id": _clean_text(item.get("candidate_id")),
        "review_id": item.get("review_id"),
        "session_id": item.get("session_id"),
        "product_id": item.get("product_id"),
        "category": _clean_text(item.get("category")) or "unknown",
        "sub_category": _clean_text(item.get("sub_category")) or "unknown",
        "label_type": _clean_text(item.get("label_type")),
        "canonical_label_key": _clean_text(item.get("canonical_label_key")),
        "raw_label": _clean_text(item.get("raw_label")),
        "evidence_candidate": _clean_text(item.get("evidence_candidate")),
        "confidence": confidence,
        "downgrade_reasons": reasons,
        "top_impact_score": _non_negative_float(
            item.get("top_impact_score") if item.get("top_impact_score") is not None else confidence
        ),
        "review_status": _clean_text(item.get("review_status")) or CANDIDATE_POOL_PENDING_STATUS,
    }
    return normalized


def candidate_pool_required_fields_present(item: dict[str, Any]) -> bool:
    return all(field in item for field in CANDIDATE_POOL_REQUIRED_FIELDS)


def collect_candidate_pool_items(
    shadow_results: dict[str, Any] | Iterable[dict[str, Any]],
) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for result in _as_shadow_results(shadow_results):
        for item in result.get("candidate_pool_items") or []:
            if isinstance(item, dict):
                items.append(normalize_candidate_pool_item(item))
    return items


def candidate_pool_dedupe_key(item: dict[str, Any]) -> tuple[str, str, str, tuple[str, ...]]:
    normalized = normalize_candidate_pool_item(item)
    return (
        _dedupe_text(normalized["canonical_label_key"]),
        _dedupe_text(normalized["raw_label"]),
        _dedupe_text(normalized["sub_category"]),
        tuple(normalized["downgrade_reasons"]),
    )


def _stable_candidate_id(dedupe_key: tuple[str, str, str, tuple[str, ...]]) -> str:
    payload = json.dumps(dedupe_key, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
    return f"pool:{hashlib.sha1(payload.encode('utf-8')).hexdigest()[:16]}"


def _impact_score(*, max_confidence: float, review_count: int, priority: int) -> float:
    priority_weight = 1.0 + (priority / 100.0)
    return round(max_confidence * max(1, review_count) * priority_weight, 3)


def aggregate_candidate_pool_items(items: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[tuple[str, str, str, tuple[str, ...]], list[dict[str, Any]]] = {}
    for item in items:
        normalized = normalize_candidate_pool_item(item)
        groups.setdefault(candidate_pool_dedupe_key(normalized), []).append(normalized)

    aggregated: list[dict[str, Any]] = []
    for dedupe_key, group_items in groups.items():
        representative = sorted(
            group_items,
            key=lambda item: (
                -_confidence(item.get("confidence")),
                _clean_text(item.get("review_id")),
                _clean_text(item.get("candidate_id")),
            ),
        )[0]
        reasons = list(dedupe_key[3])
        priority = _reason_priority(reasons)
        review_count = _review_count_for_items(group_items)
        confidences = [_confidence(item.get("confidence")) for item in group_items]
        max_confidence = max(confidences, default=0.0)
        avg_confidence = round(sum(confidences) / len(confidences), 4) if confidences else 0.0
        review_ids = _sorted_unique(item.get("review_id") for item in group_items)
        session_ids = _sorted_unique(item.get("session_id") for item in group_items)
        product_ids = _sorted_unique(item.get("product_id") for item in group_items)
        source_candidate_ids = _sorted_unique(item.get("candidate_id") for item in group_items)

        row = dict(representative)
        row.update(
            {
                "candidate_id": _stable_candidate_id(dedupe_key),
                "review_id": review_ids[0] if review_ids else representative.get("review_id"),
                "session_id": session_ids[0] if session_ids else representative.get("session_id"),
                "product_id": product_ids[0] if product_ids else representative.get("product_id"),
                "confidence": max_confidence,
                "downgrade_reasons": reasons,
                "top_impact_score": _impact_score(
                    max_confidence=max_confidence,
                    review_count=review_count,
                    priority=priority,
                ),
                "review_status": CANDIDATE_POOL_PENDING_STATUS,
                "review_count": review_count,
                "candidate_count": len(group_items),
                "max_confidence": max_confidence,
                "avg_confidence": avg_confidence,
                "downgrade_reason_priority": priority,
                "review_ids": review_ids,
                "session_ids": session_ids,
                "product_ids": product_ids,
                "source_candidate_ids": source_candidate_ids,
                "dedupe_key": {
                    "canonical_label_key": dedupe_key[0],
                    "raw_label": dedupe_key[1],
                    "sub_category": dedupe_key[2],
                    "downgrade_reasons": list(dedupe_key[3]),
                },
            }
        )
        aggregated.append(row)
    return sort_candidate_pool_items(aggregated)


def sort_candidate_pool_items(items: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        [normalize_aggregated_candidate_pool_item(item) for item in items],
        key=lambda item: (
            -int(item.get("downgrade_reason_priority") or _reason_priority(item.get("downgrade_reasons") or [])),
            -int(item.get("review_count") or 1),
            -float(item.get("top_impact_score") or 0.0),
            -float(item.get("confidence") or 0.0),
            _dedupe_text(item.get("sub_category")),
            _dedupe_text(item.get("canonical_label_key")),
            _dedupe_text(item.get("raw_label")),
        ),
    )


def normalize_aggregated_candidate_pool_item(item: dict[str, Any]) -> dict[str, Any]:
    normalized = normalize_candidate_pool_item(item)
    for field in (
        "review_count",
        "candidate_count",
        "max_confidence",
        "avg_confidence",
        "downgrade_reason_priority",
        "review_ids",
        "session_ids",
        "product_ids",
        "source_candidate_ids",
        "dedupe_key",
    ):
        if field in item:
            normalized[field] = item[field]
    return normalized


def build_candidate_pool_artifact(
    shadow_results: dict[str, Any] | Iterable[dict[str, Any]],
    *,
    scope: str = "5.9.9 Step 4 candidate pool MVP local artifact",
    source_artifacts: list[str] | None = None,
) -> dict[str, Any]:
    raw_items = collect_candidate_pool_items(shadow_results)
    aggregate_items = aggregate_candidate_pool_items(raw_items)
    return {
        "schema_version": CANDIDATE_POOL_MVP_SCHEMA_VERSION,
        "scope": scope,
        "status": "PASS",
        "raw_item_count": len(raw_items),
        "item_count": len(aggregate_items),
        "dedupe_fields": list(CANDIDATE_POOL_DEDUPE_FIELDS),
        "sort_priority": [
            "downgrade_reason_priority",
            "review_count",
            "top_impact_score",
            "confidence",
        ],
        "required_fields": list(CANDIDATE_POOL_REQUIRED_FIELDS),
        "candidate_pool_items": aggregate_items,
        "review_action_contract": candidate_pool_review_action_contract(),
        "source_artifacts": list(source_artifacts or []),
        "safety": {
            "production_upload": False,
            "production_write_path": False,
            "production_db_write": False,
            "credit_consumed": False,
            "llm_called": False,
            "frontstage_replaced": False,
        },
    }


def write_candidate_pool_json_artifact(path: Path, artifact: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(artifact, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def write_candidate_pool_csv(path: Path, items: Iterable[dict[str, Any]]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_EXPORT_FIELDS, extrasaction="ignore")
        writer.writeheader()
        for item in sort_candidate_pool_items(items):
            row = dict(item)
            for list_field in ("downgrade_reasons", "review_ids", "session_ids", "product_ids", "source_candidate_ids"):
                if list_field in row:
                    row[list_field] = "|".join(_clean_text(value) for value in row[list_field])
            writer.writerow(row)
    return path


def candidate_pool_review_action_contract() -> dict[str, Any]:
    return {
        "schema_version": "customer-label-v2-candidate-pool-review-action.1",
        "allowed_actions": sorted(CANDIDATE_POOL_REVIEW_ACTIONS),
        "required_fields": ["candidate_id", "action"],
        "conditional_required_fields": {
            "correct_label": ["label_type", "canonical_label_key"],
            "correct_evidence": ["evidence_candidate"],
            "needs_new_label": ["raw_label"],
        },
        "writes_db": False,
    }


def validate_candidate_pool_review_action(payload: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    if not isinstance(payload, dict):
        return {"valid": False, "errors": ["payload_must_be_object"], "action": None}

    candidate_id = _clean_text(payload.get("candidate_id"))
    action_name = _clean_text(payload.get("action"))
    label_type = _clean_text(payload.get("label_type")) or None
    canonical = _clean_text(payload.get("canonical_label_key")) or None
    raw_label = _clean_text(payload.get("raw_label")) or None
    evidence = _clean_text(payload.get("evidence_candidate")) or None

    if not candidate_id:
        errors.append("candidate_id_required")
    if action_name not in CANDIDATE_POOL_REVIEW_ACTIONS:
        errors.append("action_invalid")

    if action_name == "correct_label":
        if label_type not in VALID_LABEL_TYPES:
            errors.append("label_type_required")
        if not canonical:
            errors.append("canonical_label_key_required")
    if action_name == "correct_evidence" and not evidence:
        errors.append("evidence_candidate_required")
    if action_name == "needs_new_label" and not raw_label:
        errors.append("raw_label_required")

    action = CandidatePoolReviewAction(
        candidate_id=candidate_id,
        action=action_name,
        label_type=label_type,
        canonical_label_key=canonical,
        raw_label=raw_label,
        evidence_candidate=evidence,
        reviewer=_clean_text(payload.get("reviewer")) or None,
        note=_clean_text(payload.get("note")) or None,
    ).as_dict()
    return {"valid": not errors, "errors": errors, "action": action}


def _candidate_pool_items_from_input(candidate_pool: dict[str, Any] | Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    if isinstance(candidate_pool, dict):
        items = candidate_pool.get("candidate_pool_items")
        if isinstance(items, list):
            return [item for item in items if isinstance(item, dict)]
        if candidate_pool_required_fields_present(candidate_pool):
            return [candidate_pool]
        return []
    if isinstance(candidate_pool, (str, bytes)):
        return []
    return [item for item in candidate_pool if isinstance(item, dict)]


def _review_actions_from_input(review_actions: dict[str, Any] | Iterable[dict[str, Any]]) -> list[Any]:
    if isinstance(review_actions, dict):
        return [review_actions]
    if isinstance(review_actions, (str, bytes)):
        return [review_actions]
    return list(review_actions)


def _action_payload(action: Any) -> Any:
    if isinstance(action, CandidatePoolReviewAction):
        return action.as_dict()
    return action


def _review_output_for_action(source_item: dict[str, Any], action: dict[str, Any]) -> dict[str, Any]:
    action_name = _clean_text(action.get("action"))
    review_status = CANDIDATE_POOL_REVIEW_STATUS_BY_ACTION[action_name]
    output: dict[str, Any] = {"action_result": review_status}
    if action_name == "correct_label":
        output.update(
            {
                "label_type": action.get("label_type"),
                "canonical_label_key": action.get("canonical_label_key"),
                "raw_label": action.get("raw_label") or source_item.get("raw_label"),
                "evidence_candidate": action.get("evidence_candidate") or source_item.get("evidence_candidate"),
            }
        )
    elif action_name == "correct_evidence":
        output.update(
            {
                "label_type": source_item.get("label_type"),
                "canonical_label_key": source_item.get("canonical_label_key"),
                "raw_label": source_item.get("raw_label"),
                "evidence_candidate": action.get("evidence_candidate"),
            }
        )
    elif action_name == "needs_new_label":
        output.update(
            {
                "label_type": action.get("label_type") or source_item.get("label_type"),
                "canonical_label_key": action.get("canonical_label_key") or source_item.get("canonical_label_key"),
                "raw_label": action.get("raw_label"),
                "evidence_candidate": action.get("evidence_candidate") or source_item.get("evidence_candidate"),
            }
        )
    return output


def _reviewed_item_without_action(source_item: dict[str, Any]) -> dict[str, Any]:
    return {
        "candidate_id": source_item.get("candidate_id"),
        "source_candidate_item": dict(source_item),
        "review_status": source_item.get("review_status") or CANDIDATE_POOL_PENDING_STATUS,
        "reviewed_at": None,
        "action": None,
        "action_applied": False,
        "validation_errors": [],
        "review_output": {},
    }


def _apply_review_action_to_item(
    source_item: dict[str, Any],
    validation: dict[str, Any] | None,
    *,
    reviewed_at: str,
) -> dict[str, Any]:
    if not validation:
        return _reviewed_item_without_action(source_item)

    action = validation.get("action") or {}
    errors = list(validation.get("errors") or [])
    if not validation.get("valid"):
        reviewed = _reviewed_item_without_action(source_item)
        reviewed.update(
            {
                "reviewed_at": reviewed_at,
                "action": action,
                "validation_errors": errors,
            }
        )
        return reviewed

    action_name = _clean_text(action.get("action"))
    review_status = CANDIDATE_POOL_REVIEW_STATUS_BY_ACTION[action_name]
    return {
        "candidate_id": source_item.get("candidate_id"),
        "source_candidate_item": dict(source_item),
        "review_status": review_status,
        "reviewed_at": reviewed_at,
        "action": action,
        "action_applied": True,
        "validation_errors": [],
        "review_output": _review_output_for_action(source_item, action),
    }


def build_reviewed_candidate_pool_artifact(
    candidate_pool: dict[str, Any] | Iterable[dict[str, Any]],
    review_actions: dict[str, Any] | Iterable[dict[str, Any]],
    *,
    scope: str = "5.9.9 Step 4.5 candidate pool review entry MVP local artifact",
    reviewed_at: str = DETERMINISTIC_REVIEWED_AT,
    source_artifacts: list[str] | None = None,
) -> dict[str, Any]:
    source_items = sort_candidate_pool_items(_candidate_pool_items_from_input(candidate_pool))
    source_candidate_ids = {_clean_text(item.get("candidate_id")) for item in source_items}
    candidate_pool_schema = candidate_pool.get("schema_version") if isinstance(candidate_pool, dict) else None
    inherited_source_artifacts = candidate_pool.get("source_artifacts") if isinstance(candidate_pool, dict) else []
    reviewed_at = _clean_text(reviewed_at) or DETERMINISTIC_REVIEWED_AT

    validations: list[dict[str, Any]] = []
    action_by_candidate_id: dict[str, dict[str, Any]] = {}
    action_audit: list[dict[str, Any]] = []

    for index, raw_action in enumerate(_review_actions_from_input(review_actions)):
        validation = validate_candidate_pool_review_action(_action_payload(raw_action))
        action = validation.get("action") or {}
        candidate_id = _clean_text(action.get("candidate_id"))
        validation_record = {
            "index": index,
            "candidate_id": candidate_id,
            "action": _clean_text(action.get("action")),
            "valid": bool(validation.get("valid")),
            "errors": list(validation.get("errors") or []),
            "action_payload": action,
        }
        validations.append(validation_record)

        if not candidate_id or candidate_id not in source_candidate_ids:
            errors = list(validation_record["errors"])
            if candidate_id and candidate_id not in source_candidate_ids:
                errors.append("candidate_not_found")
            action_audit.append({**validation_record, "errors": errors, "reviewed_at": reviewed_at})
            continue
        if candidate_id in action_by_candidate_id:
            action_audit.append(
                {
                    **validation_record,
                    "errors": list(validation_record["errors"]) + ["duplicate_action_for_candidate"],
                    "reviewed_at": reviewed_at,
                }
            )
            continue
        action_by_candidate_id[candidate_id] = validation
        if not validation.get("valid"):
            action_audit.append({**validation_record, "reviewed_at": reviewed_at})

    reviewed_items = [
        _apply_review_action_to_item(
            item,
            action_by_candidate_id.get(_clean_text(item.get("candidate_id"))),
            reviewed_at=reviewed_at,
        )
        for item in source_items
    ]
    status_counts: dict[str, int] = {}
    for item in reviewed_items:
        status = _clean_text(item.get("review_status"))
        status_counts[status] = status_counts.get(status, 0) + 1

    source_artifact_paths = list(source_artifacts or [])
    if inherited_source_artifacts:
        source_artifact_paths.extend(str(path) for path in inherited_source_artifacts)

    return {
        "schema_version": REVIEWED_CANDIDATE_POOL_MVP_SCHEMA_VERSION,
        "source_schema_version": candidate_pool_schema or CANDIDATE_POOL_MVP_SCHEMA_VERSION,
        "scope": scope,
        "status": "PASS" if not action_audit else "REVIEW_NEEDED",
        "reviewed_at": reviewed_at,
        "source_item_count": len(source_items),
        "reviewed_item_count": len(reviewed_items),
        "reviewed_candidate_pool_items": reviewed_items,
        "review_action_contract": candidate_pool_review_action_contract(),
        "review_action_summary": {
            "action_count": len(validations),
            "valid_action_count": sum(1 for validation in validations if validation["valid"]),
            "invalid_action_count": sum(1 for validation in validations if not validation["valid"]),
            "applied_action_count": sum(1 for item in reviewed_items if item.get("action_applied")),
            "audit_error_count": len(action_audit),
            "status_counts": dict(sorted(status_counts.items())),
        },
        "action_audit": action_audit,
        "source_artifacts": source_artifact_paths,
        "safety": {
            "production_upload": False,
            "production_write_path": False,
            "production_db_write": False,
            "db_write": False,
            "credit_consumed": False,
            "llm_called": False,
            "frontstage_replaced": False,
            "frontstage_mutated": False,
        },
    }


def write_reviewed_candidate_pool_json_artifact(path: Path, artifact: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(artifact, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def _reviewed_items_from_input(reviewed_artifact: dict[str, Any] | Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    if isinstance(reviewed_artifact, dict):
        items = reviewed_artifact.get("reviewed_candidate_pool_items")
        if isinstance(items, list):
            return [item for item in items if isinstance(item, dict)]
        if "source_candidate_item" in reviewed_artifact:
            return [reviewed_artifact]
        return []
    if isinstance(reviewed_artifact, (str, bytes)):
        return []
    return [item for item in reviewed_artifact if isinstance(item, dict)]


def write_reviewed_candidate_pool_csv(
    path: Path,
    reviewed_artifact: dict[str, Any] | Iterable[dict[str, Any]],
) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=REVIEWED_CSV_EXPORT_FIELDS, extrasaction="ignore")
        writer.writeheader()
        for reviewed_item in _reviewed_items_from_input(reviewed_artifact):
            source = dict(reviewed_item.get("source_candidate_item") or {})
            action = dict(reviewed_item.get("action") or {})
            output = dict(reviewed_item.get("review_output") or {})
            row = dict(source)
            row["source_review_status"] = source.get("review_status")
            row["review_status"] = reviewed_item.get("review_status")
            row["action"] = action.get("action") or ""
            row["action_applied"] = reviewed_item.get("action_applied")
            row["validation_errors"] = "|".join(
                _clean_text(error) for error in reviewed_item.get("validation_errors") or []
            )
            row["reviewed_at"] = reviewed_item.get("reviewed_at") or ""
            row["reviewer"] = action.get("reviewer") or ""
            row["note"] = action.get("note") or ""
            row["output_label_type"] = output.get("label_type") or ""
            row["output_canonical_label_key"] = output.get("canonical_label_key") or ""
            row["output_raw_label"] = output.get("raw_label") or ""
            row["output_evidence_candidate"] = output.get("evidence_candidate") or ""
            for list_field in ("downgrade_reasons", "review_ids", "session_ids", "product_ids", "source_candidate_ids"):
                if list_field in row:
                    row[list_field] = "|".join(_clean_text(value) for value in row[list_field])
            writer.writerow(row)
    return path
