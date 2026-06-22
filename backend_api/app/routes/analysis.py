from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status

from backend_api.app.deps import get_current_user
from backend_api.app.schemas.analysis import (
    AnalysisCompareGroupPayload,
    AnalysisComparePayload,
    AnalysisHistoryPayload,
    AnalysisHistoryProductPayload,
    AnalysisHistorySessionPayload,
    AnalysisResultModulePayload,
    AnalysisSessionPayload,
    AnalysisSessionResultsPayload,
)
from review_analyzer.compare_store import build_compare_group_specs, get_comparison_dataset
from review_analyzer.database import get_comments, get_session_by_id, get_sessions
from review_analyzer.insight_engine import build_results_insights
from review_analyzer.product_store import get_product_overview_rows

router = APIRouter(prefix="/analysis", tags=["analysis"])


@router.get("/sessions/{session_id}/results", response_model=AnalysisSessionResultsPayload)
def get_session_results(
    session_id: int,
    current_user: dict = Depends(get_current_user),
) -> AnalysisSessionResultsPayload:
    user_id = int(current_user["id"])
    session = get_session_by_id(user_id, session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found.",
        )

    comments = get_comments(user_id, session_id=session_id)
    for c in comments:
        c.pop("embedding", None)
    context = _build_results_context(session)
    modules = build_results_insights(user_id, comments, context)

    return AnalysisSessionResultsPayload(
        session=_session_payload(session),
        context=context,
        modules={
            key: AnalysisResultModulePayload(**value) if isinstance(value, dict) else AnalysisResultModulePayload(summary=str(value))
            for key, value in modules.items()
        },
        comments=comments,
        generated_at=datetime.utcnow(),
    )


@router.get("/compare", response_model=AnalysisComparePayload)
def get_compare_dataset(
    compare_type: str = Query(default="custom"),
    session_ids: list[int] = Query(default_factory=list),
    product_id: str | None = Query(default=None),
    current_user: dict = Depends(get_current_user),
) -> AnalysisComparePayload:
    user_id = int(current_user["id"])
    filters: dict[str, Any] = {
        "compare_type": compare_type,
        "groups": _build_compare_specs(
            user_id,
            compare_type=compare_type,
            session_ids=session_ids,
            product_id=product_id,
        ),
    }
    dataset = get_comparison_dataset(user_id, filters)
    return AnalysisComparePayload(
        groups=[AnalysisCompareGroupPayload(**group) for group in dataset.get("groups", [])],
        compare_type=str(dataset.get("compare_type") or compare_type),
        comparison_rows=list(dataset.get("comparison_rows") or []),
        issue_differences=list(dataset.get("issue_differences") or []),
        highlight_differences=list(dataset.get("highlight_differences") or []),
        risk_groups=list(dataset.get("risk_groups") or []),
        opportunity_groups=list(dataset.get("opportunity_groups") or []),
        recommended_actions=list(dataset.get("recommended_actions") or []),
        empty_groups=list(dataset.get("empty_groups") or []),
        generated_at=datetime.utcnow(),
    )


@router.get("/history", response_model=AnalysisHistoryPayload)
def get_history(
    product_id: str | None = Query(default=None),
    current_user: dict = Depends(get_current_user),
) -> AnalysisHistoryPayload:
    return _build_history_payload(
        int(current_user["id"]),
        product_id=product_id,
        selected_session_id=None,
    )


@router.get("/sessions/{session_id}/history", response_model=AnalysisHistoryPayload)
def get_session_history(
    session_id: int,
    current_user: dict = Depends(get_current_user),
) -> AnalysisHistoryPayload:
    user_id = int(current_user["id"])
    session = get_session_by_id(user_id, session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found.",
        )
    return _build_history_payload(
        user_id,
        product_id=str(session.get("product_id") or ""),
        selected_session_id=session_id,
    )


def _session_payload(session: dict[str, Any]) -> AnalysisSessionPayload:
    return AnalysisSessionPayload(**session)


def _build_results_context(session: dict[str, Any]) -> dict[str, Any]:
    start = str(session.get("date_range_start") or "")
    end = str(session.get("date_range_end") or "")
    time_label = f"{start} ~ {end}" if start and end else "All Time"
    return {
        "product_id": str(session.get("product_id") or ""),
        "version": str(session.get("version") or "V1"),
        "time_label": time_label,
        "workflow_purpose": str(session.get("workflow_purpose") or ""),
    }


def _build_compare_specs(
    user_id: int,
    compare_type: str,
    session_ids: list[int],
    product_id: str | None,
) -> list[dict[str, Any]]:
    return build_compare_group_specs(user_id, compare_type, session_ids, product_id)


def _build_history_payload(
    user_id: int,
    product_id: str | None,
    selected_session_id: int | None,
) -> AnalysisHistoryPayload:
    sessions = get_sessions(user_id, product_id=product_id)
    products = {
        str(item.get("parent_product_id")): item
        for item in get_product_overview_rows(user_id)
        if item.get("parent_product_id")
    }
    items_map: dict[str, list[AnalysisHistorySessionPayload]] = {}
    for session in sessions:
        payload = AnalysisHistorySessionPayload(
            id=int(session["id"]),
            product_id=str(session.get("product_id") or ""),
            version=str(session.get("version") or "V1"),
            title=str(session.get("custom_title") or session.get("auto_title") or session.get("version") or "V1"),
            workflow_purpose=str(session.get("workflow_purpose") or ""),
            created_at=session["created_at"],
            total_reviews=int(session.get("total_reviews") or 0),
            positive_count=int(session.get("positive_count") or 0),
            negative_count=int(session.get("negative_count") or 0),
        )
        items_map.setdefault(payload.product_id, []).append(payload)

    items = [
        AnalysisHistoryProductPayload(
            product_id=group_product_id,
            product_name=str(products.get(group_product_id, {}).get("name") or group_product_id),
            session_count=len(product_sessions),
            latest_session_id=product_sessions[0].id if product_sessions else None,
            latest_session_title=product_sessions[0].title if product_sessions else None,
            latest_session_created_at=product_sessions[0].created_at if product_sessions else None,
            sessions=product_sessions,
        )
        for group_product_id, product_sessions in items_map.items()
    ]
    return AnalysisHistoryPayload(
        items=items,
        total=len(sessions),
        selected_session_id=selected_session_id,
        selected_product_id=product_id,
        generated_at=datetime.utcnow(),
    )
