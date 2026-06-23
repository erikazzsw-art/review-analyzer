from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response

from backend_api.app.deps import get_current_user
from backend_api.app.schemas.analysis import (
    AnalysisCompareGroupPayload,
    AnalysisComparePayload,
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
    dataset_to_xlsx_payload,
    generate_ai_comparison_summary,
    get_comparison_dataset,
    save_comparison_report,
)

router = APIRouter(prefix="/compare", tags=["compare"])


def _resolve_filter_groups(
    user_id: int,
    payload: CompareDatasetRequest | CompareExportRequest,
) -> list[dict[str, Any]]:
    raw_groups = [group.model_dump(exclude_none=True) for group in payload.groups]
    return build_compare_specs_from_filters(user_id, payload.compare_type, raw_groups)


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
    return AnalysisComparePayload(
        groups=[AnalysisCompareGroupPayload(**group) for group in dataset.get("groups", [])],
        compare_type=str(dataset.get("compare_type") or payload.compare_type),
        comparison_rows=list(dataset.get("comparison_rows") or []),
        issue_differences=list(dataset.get("issue_differences") or []),
        highlight_differences=list(dataset.get("highlight_differences") or []),
        risk_groups=list(dataset.get("risk_groups") or []),
        opportunity_groups=list(dataset.get("opportunity_groups") or []),
        recommended_actions=list(dataset.get("recommended_actions") or []),
        empty_groups=list(dataset.get("empty_groups") or []),
        generated_at=datetime.utcnow(),
    )


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
        dataset=AnalysisComparePayload(
            groups=[AnalysisCompareGroupPayload(**group) for group in dataset.get("groups", [])],
            compare_type=str(dataset.get("compare_type") or payload.compare_type),
            comparison_rows=list(dataset.get("comparison_rows") or []),
            issue_differences=list(dataset.get("issue_differences") or []),
            highlight_differences=list(dataset.get("highlight_differences") or []),
            risk_groups=list(dataset.get("risk_groups") or []),
            opportunity_groups=list(dataset.get("opportunity_groups") or []),
            recommended_actions=list(dataset.get("recommended_actions") or []),
            empty_groups=list(dataset.get("empty_groups") or []),
            generated_at=datetime.utcnow(),
        ),
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
