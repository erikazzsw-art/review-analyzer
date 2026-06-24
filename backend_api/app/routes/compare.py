from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response

from backend_api.app.deps import get_current_user
from backend_api.app.schemas.analysis import (
    AnalysisCompareGroupPayload,
    AnalysisComparePayload,
    CompareAiSummaryPayload,
    CompareDatasetRequest,
    CompareExportRequest,
    ComparisonReportCreatePayload,
    ComparisonReportPayload,
    ComparisonReportResponse,
)
from review_analyzer.analysis_export import export_compare_page_to_xlsx
from review_analyzer.compare_store import (
    build_compare_group_specs,
    build_compare_specs_from_filters,
    build_group_insights,
    compute_compare_fingerprint,
    dataset_to_xlsx_payload,
    generate_ai_comparison_summary,
    get_comparison_dataset,
    load_compare_cache,
    save_compare_cache,
    save_comparison_report,
)

router = APIRouter(prefix="/compare", tags=["compare"])


def _resolve_filter_groups(
    user_id: int,
    payload: CompareDatasetRequest | CompareExportRequest,
) -> list[dict[str, Any]]:
    raw_groups = [group.model_dump(exclude_none=True) for group in payload.groups]
    return build_compare_specs_from_filters(user_id, payload.compare_type, raw_groups)


def _enrich_dataset_with_cache(
    user_id: int,
    compare_type: str,
    filters: dict[str, Any],
    dataset: dict[str, Any],
) -> tuple[list[dict[str, Any] | None], dict[str, Any] | None]:
    """Attach per-group insights + ai_summary, honoring fingerprint cache.

    Same (user_id, compare_type, normalized groups) → same fingerprint → same
    cached payload, forever. Cache miss runs build_results_insights once per
    group plus one AI summary call, then writes the result under the
    fingerprint so the next visit is instant.
    """
    group_specs = filters.get("groups", [])
    fingerprint = compute_compare_fingerprint(user_id, compare_type, group_specs)

    cached = load_compare_cache(fingerprint)
    if cached is not None:
        insights = cached.get("group_insights") or []
        # 规范化到与 groups 等长, 缺位用 None 占住。
        insights = list(insights) + [None] * max(0, len(dataset["groups"]) - len(insights))
        ai_summary = cached.get("ai_summary")
        return insights[: len(dataset["groups"])], ai_summary

    group_comments_list = dataset.get("_group_comments") or []
    insights: list[dict[str, Any] | None] = []
    for group, comments in zip(dataset["groups"], group_comments_list, strict=False):
        insights.append(build_group_insights(user_id, group, comments))

    ai_summary: dict[str, Any] | None = None
    groups_with_data = sum(1 for group in dataset["groups"] if group.get("review_count", 0) > 0)
    if groups_with_data >= 2:
        try:
            ai_summary = generate_ai_comparison_summary(user_id, dataset)
        except ValueError:
            ai_summary = None

    save_compare_cache(
        fingerprint=fingerprint,
        user_id=user_id,
        compare_type=compare_type,
        filter_payload={"compare_type": compare_type, "groups": group_specs},
        group_insights=insights,
        ai_summary=ai_summary,
    )
    return insights, ai_summary


def _dataset_to_payload(
    dataset: dict[str, Any],
    compare_type: str,
    insights: list[dict[str, Any] | None] | None = None,
    ai_summary: dict[str, Any] | None = None,
) -> AnalysisComparePayload:
    insights = insights or []
    group_payloads: list[AnalysisCompareGroupPayload] = []
    for idx, group in enumerate(dataset.get("groups", [])):
        group_payloads.append(
            AnalysisCompareGroupPayload(
                **group,
                insights=insights[idx] if idx < len(insights) else None,
            )
        )
    return AnalysisComparePayload(
        groups=group_payloads,
        compare_type=str(dataset.get("compare_type") or compare_type),
        comparison_rows=list(dataset.get("comparison_rows") or []),
        issue_differences=list(dataset.get("issue_differences") or []),
        highlight_differences=list(dataset.get("highlight_differences") or []),
        risk_groups=list(dataset.get("risk_groups") or []),
        opportunity_groups=list(dataset.get("opportunity_groups") or []),
        recommended_actions=list(dataset.get("recommended_actions") or []),
        empty_groups=list(dataset.get("empty_groups") or []),
        ai_summary=CompareAiSummaryPayload(**ai_summary) if ai_summary else None,
        generated_at=datetime.utcnow(),
    )


@router.post("/dataset", response_model=AnalysisComparePayload)
def compare_dataset(
    payload: CompareDatasetRequest,
    current_user: dict = Depends(get_current_user),
) -> AnalysisComparePayload:
    user_id = int(current_user["id"])
    filters: dict[str, Any] = {
        "compare_type": payload.compare_type,
        "groups": _resolve_filter_groups(user_id, payload),
    }
    dataset = get_comparison_dataset(user_id, filters)
    insights, ai_summary = _enrich_dataset_with_cache(
        user_id, payload.compare_type, filters, dataset
    )
    return _dataset_to_payload(dataset, payload.compare_type, insights, ai_summary)


@router.post("/export")
def compare_export(
    payload: CompareExportRequest,
    current_user: dict = Depends(get_current_user),
) -> Response:
    user_id = int(current_user["id"])
    filters: dict[str, Any] = {
        "compare_type": payload.compare_type,
        "groups": _resolve_filter_groups(user_id, payload),
    }
    dataset = get_comparison_dataset(user_id, filters)
    if not dataset.get("groups"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="当前筛选下没有可导出的对比对象，请放宽筛选范围。",
        )

    ai_summary: dict[str, Any] | None = None
    if payload.include_ai_summary:
        try:
            ai_summary = generate_ai_comparison_summary(user_id, dataset, payload.focus_feature)
        except ValueError:
            ai_summary = None

    xlsx_payload, context = dataset_to_xlsx_payload(dataset, ai_summary)
    binary, filename = export_compare_page_to_xlsx(xlsx_payload, context)
    return Response(
        content=binary,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/reports", response_model=ComparisonReportResponse)
def create_comparison_report(
    payload: ComparisonReportCreatePayload,
    current_user: dict = Depends(get_current_user),
) -> ComparisonReportResponse:
    user_id = int(current_user["id"])
    filters: dict[str, Any] = {
        "compare_type": payload.compare_type,
        "groups": build_compare_group_specs(
            user_id,
            payload.compare_type,
            payload.session_ids,
            payload.product_id,
        ),
        "focus_feature": payload.focus_feature,
    }
    dataset = get_comparison_dataset(user_id, filters)
    try:
        ai_summary = generate_ai_comparison_summary(user_id, dataset, payload.focus_feature)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    report = save_comparison_report(
        user_id=user_id,
        comparison_type=payload.compare_type,
        title=payload.title or _default_report_title(payload.compare_type, payload.focus_feature),
        filters=filters,
        dataset=dataset,
        ai_summary=ai_summary,
    )

    return ComparisonReportResponse(
        report=ComparisonReportPayload(**report),
        dataset=_dataset_to_payload(dataset, payload.compare_type, ai_summary=ai_summary),
        ai_summary=ai_summary,
    )


def _default_report_title(compare_type: str, focus_feature: str | None) -> str:
    base_title = {
        "same_product_time": "同产品时间对比报告",
        "same_product_version": "同产品版本对比报告",
        "same_parent_variants": "同父体变体对比报告",
        "multi_product": "多产品横向对比报告",
        "custom": "自定义对比报告",
    }.get(compare_type, "对比报告")
    if focus_feature:
        return f"{base_title} · {focus_feature}"
    return base_title
