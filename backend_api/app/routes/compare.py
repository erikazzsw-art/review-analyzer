from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import Response

from backend_api.app.deps import get_current_user
from backend_api.app.schemas.analysis import (
    AnalysisCompareGroupPayload,
    AnalysisComparePayload,
    CompareAiSummaryPayload,
    CompareDatasetRequest,
    CompareExportRequest,
    CompareFilterGroupPayload,
    CompareHistoryItemPayload,
    CompareHistoryPayload,
    CompareLatestPayload,
    ComparisonReportCreatePayload,
    ComparisonReportPayload,
    ComparisonReportResponse,
)
from backend_api.app.services.budget_guard import assert_budget
from backend_api.app.services.locale import get_analysis_locale
from review_analyzer.analysis_export import export_compare_page_to_xlsx
from review_analyzer.compare_store import (
    build_compare_group_specs,
    build_compare_specs_from_filters,
    build_group_insights,
    compute_compare_fingerprint,
    dataset_to_xlsx_payload,
    delete_compare_history,
    generate_ai_comparison_summary,
    get_comparison_dataset,
    list_compare_history,
    load_compare_cache,
    load_compare_history_entry,
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
    locale: str = "en",
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
            assert_budget(user_id)
            ai_summary = generate_ai_comparison_summary(user_id, dataset, locale=locale)
        except HTTPException:
            raise
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
    request: Request,
    current_user: dict = Depends(get_current_user),
) -> AnalysisComparePayload:
    user_id = int(current_user["id"])
    filters: dict[str, Any] = {
        "compare_type": payload.compare_type,
        "groups": _resolve_filter_groups(user_id, payload),
    }
    dataset = get_comparison_dataset(user_id, filters)
    insights, ai_summary = _enrich_dataset_with_cache(
        user_id, payload.compare_type, filters, dataset, locale=get_analysis_locale(request)
    )
    return _dataset_to_payload(dataset, payload.compare_type, insights, ai_summary)


@router.post("/export")
def compare_export(
    payload: CompareExportRequest,
    request: Request,
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
        ai_summary = _get_or_generate_ai_summary(
            user_id,
            payload.compare_type,
            filters,
            dataset,
            focus_feature=payload.focus_feature,
            locale=get_analysis_locale(request),
        )

    xlsx_payload, context = dataset_to_xlsx_payload(dataset, ai_summary)
    binary, filename = export_compare_page_to_xlsx(xlsx_payload, context)
    return Response(
        content=binary,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def _get_or_generate_ai_summary(
    user_id: int,
    compare_type: str,
    filters: dict[str, Any],
    dataset: dict[str, Any],
    focus_feature: str | None = None,
    locale: str = "en",
) -> dict[str, Any] | None:
    """走 fingerprint 缓存 → 命中直接返回；未命中才调 LLM。

    focus_feature 参与指纹，因为不同 feature 产出不同总结。
    """
    group_specs = filters.get("groups", [])
    fp_input = list(group_specs)
    if focus_feature:
        fp_input = [{"__focus__": focus_feature}, *group_specs]
    fingerprint = compute_compare_fingerprint(user_id, compare_type, fp_input)

    cached = load_compare_cache(fingerprint)
    if cached is not None and cached.get("ai_summary"):
        return cached["ai_summary"]

    assert_budget(user_id)
    try:
        ai_summary = generate_ai_comparison_summary(
            user_id, dataset, focus_feature, locale=locale
        )
    except ValueError:
        return None

    save_compare_cache(
        fingerprint=fingerprint,
        user_id=user_id,
        compare_type=compare_type,
        filter_payload={"compare_type": compare_type, "groups": group_specs, "focus_feature": focus_feature},
        group_insights=(cached or {}).get("group_insights") or [],
        ai_summary=ai_summary,
    )
    return ai_summary


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
    ai_summary = _get_or_generate_ai_summary(
        user_id,
        payload.compare_type,
        filters,
        dataset,
        focus_feature=payload.focus_feature,
    )
    if ai_summary is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="当前有效评论不足或 AI 服务暂不可用，请稍后再试。",
        )

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


# ---------------------------------------------------------------------------
# History endpoints
# ---------------------------------------------------------------------------


@router.get("/history", response_model=CompareHistoryPayload)
def get_compare_history(
    q: str | None = Query(None, description="产品名模糊搜索"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: dict = Depends(get_current_user),
) -> CompareHistoryPayload:
    user_id = int(current_user["id"])
    result = list_compare_history(user_id, q=q, limit=limit, offset=offset)
    items = [CompareHistoryItemPayload(**item) for item in result["items"]]
    return CompareHistoryPayload(items=items, total=result["total"])


@router.get("/latest", response_model=CompareLatestPayload | None)
def get_compare_latest(
    current_user: dict = Depends(get_current_user),
) -> CompareLatestPayload | None:
    user_id = int(current_user["id"])
    history = list_compare_history(user_id, q=None, limit=1, offset=0)
    if not history["items"]:
        return None
    fingerprint = history["items"][0]["fingerprint"]
    entry = load_compare_history_entry(user_id, fingerprint)
    if not entry:
        return None
    filter_payload = entry["filter_payload"]
    compare_type = entry["compare_type"]
    groups_raw = filter_payload.get("groups") or []

    filters: dict[str, Any] = {
        "compare_type": compare_type,
        "groups": groups_raw,
    }
    dataset = get_comparison_dataset(user_id, filters)
    insights = entry.get("group_insights") or []
    insights = list(insights) + [None] * max(0, len(dataset.get("groups", [])) - len(insights))
    ai_summary = entry.get("ai_summary")

    payload = _dataset_to_payload(
        dataset, compare_type, insights[: len(dataset.get("groups", []))], ai_summary
    )

    filter_groups = [
        CompareFilterGroupPayload(
            product_id=str(g.get("product_id") or ""),
            versions=list(g.get("versions") or []),
            date_start=g.get("date_start"),
            date_end=g.get("date_end"),
        )
        for g in groups_raw
    ]

    return CompareLatestPayload(
        dataset=payload,
        filter_groups=filter_groups,
        compare_type=compare_type,
    )


@router.get("/history/{fingerprint}", response_model=CompareLatestPayload)
def get_compare_history_entry(
    fingerprint: str,
    current_user: dict = Depends(get_current_user),
) -> CompareLatestPayload:
    user_id = int(current_user["id"])
    entry = load_compare_history_entry(user_id, fingerprint)
    if not entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="对比记录不存在或已被删除。",
        )
    filter_payload = entry["filter_payload"]
    compare_type = entry["compare_type"]
    groups_raw = filter_payload.get("groups") or []

    filters: dict[str, Any] = {
        "compare_type": compare_type,
        "groups": groups_raw,
    }
    dataset = get_comparison_dataset(user_id, filters)
    insights = entry.get("group_insights") or []
    insights = list(insights) + [None] * max(0, len(dataset.get("groups", [])) - len(insights))
    ai_summary = entry.get("ai_summary")

    payload = _dataset_to_payload(
        dataset, compare_type, insights[: len(dataset.get("groups", []))], ai_summary
    )

    filter_groups = [
        CompareFilterGroupPayload(
            product_id=str(g.get("product_id") or ""),
            versions=list(g.get("versions") or []),
            date_start=g.get("date_start"),
            date_end=g.get("date_end"),
        )
        for g in groups_raw
    ]

    return CompareLatestPayload(
        dataset=payload,
        filter_groups=filter_groups,
        compare_type=compare_type,
    )


@router.delete("/history/{fingerprint}")
def remove_compare_history(
    fingerprint: str,
    current_user: dict = Depends(get_current_user),
) -> dict[str, bool]:
    user_id = int(current_user["id"])
    deleted = delete_compare_history(user_id, fingerprint)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="对比记录不存在或已被删除。",
        )
    return {"deleted": True}
