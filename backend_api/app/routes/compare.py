from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status

from backend_api.app.deps import get_current_user
from backend_api.app.schemas.analysis import (
    AnalysisCompareGroupPayload,
    AnalysisComparePayload,
    ComparisonReportCreatePayload,
    ComparisonReportPayload,
    ComparisonReportResponse,
)
from review_analyzer.compare_store import (
    build_compare_group_specs,
    generate_ai_comparison_summary,
    get_comparison_dataset,
    save_comparison_report,
)


router = APIRouter(prefix="/compare", tags=["compare"])


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
