from __future__ import annotations

import hashlib
import json
import math
import re
from collections import Counter
from collections.abc import Iterable
from typing import Any

CUSTOMER_LABEL_V2_BAD_CASE_MEMORY_SCHEMA_VERSION = "customer-label-v2-bad-case-memory-lite.1"
CUSTOMER_LABEL_V2_BAD_CASE_MEMORY_REPORT_SCHEMA_VERSION = "customer-label-v2-bad-case-memory-report-lite.1"

_STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "but",
    "for",
    "in",
    "is",
    "it",
    "not",
    "of",
    "on",
    "or",
    "the",
    "these",
    "this",
    "to",
    "was",
    "were",
    "with",
}


def _clean_text(value: Any) -> str:
    return str(value or "").strip()


def _tokens(*values: Any) -> list[str]:
    text = " ".join(_clean_text(value).lower() for value in values if _clean_text(value))
    raw_tokens = re.findall(r"[a-z0-9]+", text)
    return [token for token in raw_tokens if token not in _STOPWORDS and len(token) > 1]


def _vectorize(*values: Any) -> dict[str, float]:
    counts = Counter(_tokens(*values))
    total = sum(counts.values()) or 1
    return {token: round(count / total, 6) for token, count in sorted(counts.items())}


def _norm(vector: dict[str, float]) -> float:
    return math.sqrt(sum(value * value for value in vector.values()))


def _cosine(left: dict[str, float], right: dict[str, float]) -> float:
    if not left or not right:
        return 0.0
    shared = set(left) & set(right)
    numerator = sum(left[token] * right[token] for token in shared)
    denominator = _norm(left) * _norm(right)
    return round(numerator / denominator, 6) if denominator else 0.0


def _stable_id(payload: dict[str, Any]) -> str:
    raw = json.dumps(payload, ensure_ascii=True, sort_keys=True, default=str, separators=(",", ":"))
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:16]


def _memory_item(
    *,
    source_type: str,
    source_id: Any,
    category: Any = "",
    sub_category: Any = "",
    label_type: Any = "",
    canonical_label_key: Any = "",
    raw_label: Any = "",
    evidence: Any = "",
    content: Any = "",
    downgrade_reasons: Iterable[Any] = (),
    review_status: Any = "",
    review_count: Any = 1,
    confidence: Any = 0.0,
    top_impact_score: Any = 0.0,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    reasons = [_clean_text(reason) for reason in downgrade_reasons if _clean_text(reason)]
    vector = _vectorize(
        category,
        sub_category,
        label_type,
        canonical_label_key,
        raw_label,
        evidence,
        content,
        " ".join(reasons),
        review_status,
    )
    try:
        review_count_value = max(int(review_count), 1)
    except (TypeError, ValueError):
        review_count_value = 1
    try:
        confidence_value = float(confidence)
    except (TypeError, ValueError):
        confidence_value = 0.0
    try:
        impact_value = float(top_impact_score)
    except (TypeError, ValueError):
        impact_value = 0.0
    identity = {
        "source_type": source_type,
        "source_id": source_id,
        "canonical_label_key": _clean_text(canonical_label_key),
        "evidence": _clean_text(evidence),
        "downgrade_reasons": reasons,
    }
    return {
        "memory_id": f"badcase:{_stable_id(identity)}",
        "source_type": source_type,
        "source_id": source_id,
        "category": _clean_text(category) or "unknown",
        "sub_category": _clean_text(sub_category) or "unknown",
        "label_type": _clean_text(label_type),
        "canonical_label_key": _clean_text(canonical_label_key),
        "raw_label": _clean_text(raw_label),
        "evidence": _clean_text(evidence),
        "content": _clean_text(content),
        "downgrade_reasons": reasons,
        "review_status": _clean_text(review_status),
        "review_count": review_count_value,
        "confidence": round(max(0.0, min(confidence_value, 1.0)), 4),
        "top_impact_score": round(max(impact_value, 0.0), 4),
        "vector_terms": vector,
        "vector_norm": round(_norm(vector), 6),
        "metadata": dict(metadata or {}),
    }


def _reviewed_candidate_items(reviewed_candidate_pool_artifact: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not isinstance(reviewed_candidate_pool_artifact, dict):
        return []
    items = reviewed_candidate_pool_artifact.get("reviewed_candidate_pool_items")
    return [item for item in items if isinstance(item, dict)] if isinstance(items, list) else []


def _items_from_reviewed_candidate_pool(reviewed_candidate_pool_artifact: dict[str, Any] | None) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for reviewed in _reviewed_candidate_items(reviewed_candidate_pool_artifact):
        source = reviewed.get("source_candidate_item") or {}
        action = reviewed.get("action") or {}
        output = reviewed.get("review_output") or {}
        source_id = source.get("candidate_id") or reviewed.get("candidate_id")
        items.append(
            _memory_item(
                source_type="candidate_pool_reviewed",
                source_id=source_id,
                category=source.get("category"),
                sub_category=source.get("sub_category"),
                label_type=output.get("label_type") or source.get("label_type"),
                canonical_label_key=output.get("canonical_label_key") or source.get("canonical_label_key"),
                raw_label=output.get("raw_label") or source.get("raw_label"),
                evidence=output.get("evidence_candidate") or source.get("evidence_candidate"),
                downgrade_reasons=source.get("downgrade_reasons") or [],
                review_status=reviewed.get("review_status"),
                review_count=source.get("review_count") or 1,
                confidence=source.get("confidence") or source.get("max_confidence"),
                top_impact_score=source.get("top_impact_score"),
                metadata={
                    "action": action.get("action"),
                    "action_applied": reviewed.get("action_applied"),
                    "reviewer": action.get("reviewer"),
                },
            )
        )
    return items


def _items_from_shadow_audits(shadow_results: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for result in shadow_results:
        if not isinstance(result, dict):
            continue
        for index, audit in enumerate(result.get("audit_occurrences") or []):
            if not isinstance(audit, dict):
                continue
            items.append(
                _memory_item(
                    source_type="audited_bad_case",
                    source_id=f"{result.get('review_id')}:{index}",
                    category=result.get("category"),
                    sub_category=result.get("sub_category"),
                    label_type=audit.get("label_type"),
                    canonical_label_key=audit.get("canonical_label_key"),
                    raw_label=audit.get("raw_label"),
                    evidence=audit.get("evidence_span"),
                    downgrade_reasons=audit.get("downgrade_reasons") or result.get("downgrade_reasons") or [],
                    confidence=audit.get("confidence"),
                    metadata={
                        "ruleset_version": result.get("ruleset_version"),
                        "prompt_version": result.get("prompt_version"),
                    },
                )
            )
    return items


def _items_from_gold_regression(gold_regression_cases: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for index, case in enumerate(gold_regression_cases):
        if not isinstance(case, dict):
            continue
        expected_issue_keys = list(case.get("expected_issue_keys") or case.get("_expected_issue_keys") or [])
        expected_highlight_keys = list(
            case.get("expected_highlight_keys") or case.get("_expected_highlight_keys") or []
        )
        blocked_issue_keys = list(case.get("blocked_issue_keys") or case.get("_blocked_issue_keys") or [])
        blocked_highlight_keys = list(
            case.get("blocked_highlight_keys") or case.get("_blocked_highlight_keys") or []
        )
        label_keys = expected_issue_keys + expected_highlight_keys + blocked_issue_keys + blocked_highlight_keys
        items.append(
            _memory_item(
                source_type="gold_regression",
                source_id=case.get("id") or case.get("review_id") or index,
                category=case.get("category"),
                sub_category=case.get("sub_category"),
                canonical_label_key=" ".join(_clean_text(key) for key in label_keys),
                raw_label="gold regression expected/blocked labels",
                content=case.get("content"),
                downgrade_reasons=["gold_regression_reference"],
                review_status="locked",
                metadata={
                    "expected_issue_keys": expected_issue_keys,
                    "expected_highlight_keys": expected_highlight_keys,
                    "blocked_issue_keys": blocked_issue_keys,
                    "blocked_highlight_keys": blocked_highlight_keys,
                },
            )
        )
    return items


def _dedupe_memory_items(items: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    deduped: list[dict[str, Any]] = []
    for item in items:
        memory_id = str(item.get("memory_id") or "")
        if not memory_id or memory_id in seen:
            continue
        seen.add(memory_id)
        deduped.append(item)
    return sorted(deduped, key=lambda item: str(item.get("memory_id") or ""))


def build_customer_label_v2_bad_case_memory(
    *,
    audited_shadow_results: Iterable[dict[str, Any]] = (),
    gold_regression_cases: Iterable[dict[str, Any]] = (),
    reviewed_candidate_pool_artifact: dict[str, Any] | None = None,
    scope: str = "5.9.9 Step 8 vector bad case memory lite",
) -> dict[str, Any]:
    reviewed_items = _items_from_reviewed_candidate_pool(reviewed_candidate_pool_artifact)
    audit_items = _items_from_shadow_audits(audited_shadow_results)
    gold_items = _items_from_gold_regression(gold_regression_cases)
    items = _dedupe_memory_items(reviewed_items + audit_items + gold_items)
    source_counts = Counter(str(item.get("source_type") or "") for item in items)
    reason_counts = Counter(
        str(reason)
        for item in items
        for reason in item.get("downgrade_reasons") or []
        if str(reason)
    )
    return {
        "schema_version": CUSTOMER_LABEL_V2_BAD_CASE_MEMORY_SCHEMA_VERSION,
        "scope": scope,
        "status": "PASS",
        "item_count": len(items),
        "source_counts": dict(sorted(source_counts.items())),
        "downgrade_reason_counts": dict(sorted(reason_counts.items())),
        "memory_items": items,
        "display_contract": {
            "vector_memory_can_select_frontstage": False,
            "display_decision_source": "evidence_context_aspect_maturity_feature_flag_gates",
            "allowed_uses": [
                "similar_historical_bad_case_retrieval",
                "candidate_clustering",
                "review_prioritization",
                "audit_debug_report",
            ],
        },
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


def _memory_items(memory: dict[str, Any] | Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    if isinstance(memory, dict):
        items = memory.get("memory_items")
        return [item for item in items if isinstance(item, dict)] if isinstance(items, list) else []
    return [item for item in memory if isinstance(item, dict)]


def search_similar_bad_cases(
    query: str | dict[str, Any],
    memory: dict[str, Any] | Iterable[dict[str, Any]],
    *,
    top_k: int = 5,
    min_score: float = 0.0,
    downgrade_reason_filter: str | None = None,
) -> list[dict[str, Any]]:
    if isinstance(query, dict):
        query_vector = _vectorize(
            query.get("content"),
            query.get("evidence"),
            query.get("canonical_label_key"),
            query.get("raw_label"),
            " ".join(str(reason) for reason in query.get("downgrade_reasons") or []),
        )
    else:
        query_vector = _vectorize(query)
    results: list[dict[str, Any]] = []
    for item in _memory_items(memory):
        if downgrade_reason_filter and downgrade_reason_filter not in set(item.get("downgrade_reasons") or []):
            continue
        score = _cosine(query_vector, item.get("vector_terms") or {})
        if score < min_score:
            continue
        results.append(
            {
                "memory_id": item.get("memory_id"),
                "score": score,
                "source_type": item.get("source_type"),
                "canonical_label_key": item.get("canonical_label_key"),
                "raw_label": item.get("raw_label"),
                "evidence": item.get("evidence"),
                "downgrade_reasons": item.get("downgrade_reasons") or [],
                "review_status": item.get("review_status"),
            }
        )
    return sorted(results, key=lambda item: (-float(item["score"]), str(item["memory_id"])))[:top_k]


def cluster_unknown_label_candidates(
    memory: dict[str, Any] | Iterable[dict[str, Any]],
    *,
    min_similarity: float = 0.18,
) -> list[dict[str, Any]]:
    unknown_items = [
        item
        for item in _memory_items(memory)
        if "unknown_label" in set(item.get("downgrade_reasons") or [])
        or str(item.get("canonical_label_key") or "").startswith("candidate:")
    ]
    clusters: list[dict[str, Any]] = []
    for item in unknown_items:
        matched_cluster = None
        for cluster in clusters:
            representative = cluster["representative_item"]
            score = _cosine(item.get("vector_terms") or {}, representative.get("vector_terms") or {})
            if score >= min_similarity:
                matched_cluster = cluster
                break
        if matched_cluster is None:
            matched_cluster = {
                "cluster_id": f"unknown:{len(clusters) + 1}",
                "representative_item": item,
                "items": [],
            }
            clusters.append(matched_cluster)
        matched_cluster["items"].append(item)

    output: list[dict[str, Any]] = []
    for cluster in clusters:
        items = cluster["items"]
        output.append(
            {
                "cluster_id": cluster["cluster_id"],
                "item_count": len(items),
                "memory_ids": [item["memory_id"] for item in items],
                "canonical_label_keys": sorted(
                    {str(item.get("canonical_label_key") or "") for item in items if item.get("canonical_label_key")}
                ),
                "raw_labels": sorted({str(item.get("raw_label") or "") for item in items if item.get("raw_label")}),
                "representative_memory_id": cluster["representative_item"]["memory_id"],
            }
        )
    return sorted(output, key=lambda cluster: (-int(cluster["item_count"]), str(cluster["cluster_id"])))


def prioritize_maturity_blocked_candidates(
    memory: dict[str, Any] | Iterable[dict[str, Any]],
    *,
    top_k: int = 10,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for item in _memory_items(memory):
        if "maturity_blocked" not in set(item.get("downgrade_reasons") or []):
            continue
        priority_score = round(
            100.0
            + (float(item.get("review_count") or 1) * 10.0)
            + float(item.get("top_impact_score") or 0.0)
            + float(item.get("confidence") or 0.0),
            4,
        )
        rows.append(
            {
                "memory_id": item.get("memory_id"),
                "priority_score": priority_score,
                "review_count": item.get("review_count"),
                "top_impact_score": item.get("top_impact_score"),
                "confidence": item.get("confidence"),
                "canonical_label_key": item.get("canonical_label_key"),
                "raw_label": item.get("raw_label"),
                "downgrade_reasons": item.get("downgrade_reasons") or [],
            }
        )
    return sorted(rows, key=lambda item: (-float(item["priority_score"]), str(item["memory_id"])))[:top_k]


def build_customer_label_v2_bad_case_memory_debug_report(
    memory: dict[str, Any],
    *,
    queries: Iterable[str | dict[str, Any]] = (),
    scope: str = "5.9.9 Step 8 vector bad case memory lite debug report",
) -> dict[str, Any]:
    similar_history = [
        {
            "query_index": index,
            "results": search_similar_bad_cases(query, memory, top_k=5),
        }
        for index, query in enumerate(queries)
    ]
    return {
        "schema_version": CUSTOMER_LABEL_V2_BAD_CASE_MEMORY_REPORT_SCHEMA_VERSION,
        "scope": scope,
        "status": "PASS",
        "memory_schema_version": memory.get("schema_version"),
        "memory_item_count": memory.get("item_count"),
        "similar_history": similar_history,
        "unknown_candidate_clusters": cluster_unknown_label_candidates(memory),
        "maturity_blocked_priorities": prioritize_maturity_blocked_candidates(memory),
        "display_contract": memory.get("display_contract"),
        "safety": memory.get("safety"),
    }
