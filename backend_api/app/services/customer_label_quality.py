from __future__ import annotations

from collections import defaultdict
from typing import Any

from backend_api.app.services.specific_issue import (
    build_customer_highlight_rows,
    build_specific_issue_rows,
    iter_customer_highlight_occurrences,
    iter_specific_issue_occurrences,
)

DEFAULT_LABEL_QUALITY_THRESHOLDS = {
    "single_label_min_mentions": 10,
    "single_label_share_pct": 95.0,
    "low_evidence_min_mentions": 3,
    "low_evidence_verified_ratio": 0.8,
    "high_cluster_min_total_occurrences": 5,
    "high_cluster_propagated_ratio": 0.6,
    "long_tail_min_reviews": 20,
    "long_tail_unique_label_review_ratio": 0.6,
}

_BROAD_INTERNAL_LABELS = {
    "accessories and storage",
    "accessory storage",
    "aesthetics",
    "assembly",
    "build quality",
    "capacity",
    "comfort",
    "durability",
    "ease of use",
    "grip",
    "material",
    "materials",
    "mobility",
    "organization",
    "other",
    "packaging",
    "quality",
    "product quality",
    "stability",
    "user experience",
    "waterproof",
    "waterproof performance",
    "waterproofing",
}


def _norm_label(value: Any) -> str:
    return " ".join(str(value or "").replace("&", " and ").lower().split())


def _warning(warning_type: str, **data: Any) -> dict[str, Any]:
    return {
        "type": warning_type,
        "severity": "warning",
        "message": warning_type.replace("_", " "),
        "data": data,
    }


def _label_rows(comments: list[dict[str, Any]], locale: str) -> dict[str, list[dict[str, Any]]]:
    limit = max(100, len(comments) * 4)
    return {
        "issue": build_specific_issue_rows(comments, locale=locale, limit=limit),
        "highlight": build_customer_highlight_rows(comments, locale=locale, limit=limit),
    }


def _occurrence_stats(
    comments: list[dict[str, Any]],
    *,
    label_type: str,
    locale: str,
) -> dict[tuple[str, str], dict[str, int]]:
    iterator = iter_specific_issue_occurrences if label_type == "issue" else iter_customer_highlight_occurrences
    canonical_field = "canonical_issue_key" if label_type == "issue" else "canonical_highlight_key"
    stats: dict[tuple[str, str], dict[str, int]] = defaultdict(
        lambda: {
            "total_occurrence_count": 0,
            "propagated_occurrence_count": 0,
            "frontstage_occurrence_count": 0,
            "verified_representative_occurrence_count": 0,
        }
    )

    for comment in comments:
        for occurrence in iterator(comment, locale=locale):
            canonical = str(occurrence.get(canonical_field) or occurrence.get("canonical_label_key") or "").strip()
            if not canonical:
                continue
            key = (str(occurrence.get("sub_category") or ""), canonical)
            item = stats[key]
            item["total_occurrence_count"] += 1
            if occurrence.get("cluster_propagated"):
                item["propagated_occurrence_count"] += 1
            is_frontstage = bool(
                not occurrence.get("cluster_propagated")
                and (occurrence.get("legacy_fallback") or occurrence.get("source_review_allowed"))
            )
            if is_frontstage:
                item["frontstage_occurrence_count"] += 1
                if occurrence.get("verified_evidence"):
                    item["verified_representative_occurrence_count"] += 1
    return stats


def _row_key(label_type: str, row: dict[str, Any]) -> tuple[str, str]:
    canonical_field = "canonical_issue_key" if label_type == "issue" else "canonical_highlight_key"
    return (str(row.get("sub_category") or ""), str(row.get(canonical_field) or "").strip())


def _row_label(label_type: str, row: dict[str, Any]) -> str:
    return str(row.get("specific_issue" if label_type == "issue" else "customer_highlight") or "")


def _broad_internal_label_in_row(label_type: str, row: dict[str, Any]) -> bool:
    label = _norm_label(_row_label(label_type, row))
    aspect_key = _norm_label(row.get("aspect_key"))
    canonical = _norm_label(str(row.get("canonical_label_key") or "").replace("_", " "))
    return bool(
        label in _BROAD_INTERNAL_LABELS
        or canonical in _BROAD_INTERNAL_LABELS
        or (aspect_key and label == aspect_key)
    )


def build_customer_label_quality_warnings(
    comments: list[dict[str, Any]],
    *,
    locale: str = "en",
    thresholds: dict[str, float | int] | None = None,
) -> list[dict[str, Any]]:
    """Build deterministic local warnings for Top Issue/Label regression gates."""
    merged_thresholds = {**DEFAULT_LABEL_QUALITY_THRESHOLDS, **(thresholds or {})}
    rows_by_type = _label_rows(comments, locale)
    warnings: list[dict[str, Any]] = []

    for label_type, rows in rows_by_type.items():
        total_mentions = sum(int(row.get("mention_count") or 0) for row in rows)
        if (
            rows
            and total_mentions >= int(merged_thresholds["single_label_min_mentions"])
            and float(rows[0].get("mention_share") or 0) >= float(merged_thresholds["single_label_share_pct"])
        ):
            warnings.append(
                _warning(
                    "customer_label_single_label_dominance",
                    label_type=label_type,
                    label=_row_label(label_type, rows[0]),
                    mention_count=int(rows[0].get("mention_count") or 0),
                    mention_share=float(rows[0].get("mention_share") or 0),
                )
            )

        for row in rows:
            if _broad_internal_label_in_row(label_type, row):
                warnings.append(
                    _warning(
                        "customer_label_broad_internal_top_label",
                        label_type=label_type,
                        label=_row_label(label_type, row),
                        canonical_label_key=str(row.get("canonical_label_key") or ""),
                    )
                )

        stats = _occurrence_stats(comments, label_type=label_type, locale=locale)
        for row in rows:
            key = _row_key(label_type, row)
            item = stats.get(key)
            if not item:
                continue
            frontstage_count = item["frontstage_occurrence_count"]
            if frontstage_count >= int(merged_thresholds["low_evidence_min_mentions"]):
                ratio = (
                    item["verified_representative_occurrence_count"] / frontstage_count
                    if frontstage_count
                    else 0.0
                )
                if ratio < float(merged_thresholds["low_evidence_verified_ratio"]):
                    warnings.append(
                        _warning(
                            "customer_label_low_representative_evidence_ratio",
                            label_type=label_type,
                            label=_row_label(label_type, row),
                            canonical_label_key=str(row.get("canonical_label_key") or ""),
                            verified_ratio=round(ratio, 3),
                            frontstage_occurrence_count=frontstage_count,
                            verified_representative_occurrence_count=item[
                                "verified_representative_occurrence_count"
                            ],
                        )
                    )

            total_occurrences = item["total_occurrence_count"]
            if total_occurrences >= int(merged_thresholds["high_cluster_min_total_occurrences"]):
                propagated_ratio = item["propagated_occurrence_count"] / total_occurrences
                if propagated_ratio > float(merged_thresholds["high_cluster_propagated_ratio"]):
                    warnings.append(
                        _warning(
                            "customer_label_high_cluster_propagated_ratio",
                            label_type=label_type,
                            label=_row_label(label_type, row),
                            canonical_label_key=str(row.get("canonical_label_key") or ""),
                            propagated_ratio=round(propagated_ratio, 3),
                            propagated_occurrence_count=item["propagated_occurrence_count"],
                            total_occurrence_count=total_occurrences,
                        )
                    )

    if len(comments) >= int(merged_thresholds["long_tail_min_reviews"]):
        unique_labels = {
            (label_type, str(row.get("canonical_label_key") or ""))
            for label_type, rows in rows_by_type.items()
            for row in rows
            if row.get("canonical_label_key")
        }
        unique_ratio = len(unique_labels) / len(comments) if comments else 0.0
        if unique_ratio > float(merged_thresholds["long_tail_unique_label_review_ratio"]):
            warnings.append(
                _warning(
                    "customer_label_long_tail_expansion",
                    unique_label_count=len(unique_labels),
                    review_count=len(comments),
                    unique_label_review_ratio=round(unique_ratio, 3),
                )
            )

    return warnings
