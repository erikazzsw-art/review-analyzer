from __future__ import annotations

import hashlib
import logging
import time
from datetime import datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel

from backend_api.app.deps import get_current_user
from backend_api.app.schemas.analysis import (
    AnalysisCompareGroupPayload,
    AnalysisComparePayload,
    AnalysisHistoryPayload,
    AnalysisHistoryProductPayload,
    AnalysisHistorySessionPayload,
    AnalysisResultModulePayload,
    AnalysisResultsPayload,
    AnalysisSessionPayload,
    AnalysisSessionResultsPayload,
)
from backend_api.app.services.locale import get_analysis_locale
from review_analyzer.compare_store import build_compare_group_specs, get_comparison_dataset
from review_analyzer.database import (
    delete_session,
    get_comments,
    get_session_by_id,
    get_sessions,
    get_upload_jobs_by_session,
    reset_session_analysis,
    update_upload_job,
)
from review_analyzer.insight_engine import build_results_insights
from review_analyzer.product_store import get_product_overview_rows
from review_analyzer.quota import InsufficientCreditsError, credit_consume
from workers.jobs import enqueue_upload_job_task

router = APIRouter(prefix="/analysis", tags=["analysis"])

_LOGGER = logging.getLogger(__name__)

# Phase 2: 进程内聚合结果缓存 — key = (user_id, product_id, start, end, comment_ids_hash)
# 命中相同筛选条件秒返;重启失效可接受。
_INSIGHTS_CACHE: dict[str, tuple[float, dict[str, Any]]] = {}
_INSIGHTS_CACHE_TTL = 60 * 30  # 30 分钟
_INSIGHTS_CACHE_MAX = 256


def _cache_key(
    user_id: int,
    product_id: str,
    start: str,
    end: str,
    comment_ids: tuple[int, ...],
) -> str:
    raw = f"{user_id}|{product_id}|{start}|{end}|{len(comment_ids)}|{hash(comment_ids)}"
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()


def _cached_build_insights(
    user_id: int,
    product_id: str,
    start: str,
    end: str,
    comment_ids: tuple[int, ...],
    comments: list[dict[str, Any]],
    context: dict[str, Any],
    locale: str = "en",
) -> dict[str, Any]:
    key = _cache_key(user_id, product_id, start, end, comment_ids)
    now = time.time()
    cached = _INSIGHTS_CACHE.get(key)
    if cached and now - cached[0] < _INSIGHTS_CACHE_TTL:
        return cached[1]
    modules = build_results_insights(user_id, comments, context, locale=locale)
    # 淘汰最旧的条目
    if len(_INSIGHTS_CACHE) >= _INSIGHTS_CACHE_MAX:
        oldest = min(_INSIGHTS_CACHE.items(), key=lambda kv: kv[1][0])[0]
        _INSIGHTS_CACHE.pop(oldest, None)
    _INSIGHTS_CACHE[key] = (now, modules)
    return modules


@router.get("/sessions/{session_id}/results", response_model=AnalysisSessionResultsPayload)
def get_session_results(
    session_id: int,
    request: Request,
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
    modules = build_results_insights(
        user_id, comments, context, locale=get_analysis_locale(request)
    )

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


@router.get("/results", response_model=AnalysisResultsPayload)
def get_aggregated_results(
    request: Request,
    product_id: str = Query(..., min_length=1),
    range: str | None = Query(default="default"),
    start: str | None = Query(default=None),
    end: str | None = Query(default=None),
    session_id: int | None = Query(default=None),
    version: str | None = Query(default=None),
    current_user: dict = Depends(get_current_user),
) -> AnalysisResultsPayload:
    """按产品 + 时间范围跨 session 聚合评论 → 跑 LLM 分析 → 返回。

    - range: default | 7d | 14d | 30d | all | custom
    - default: 若 session_id 提供,用该 session 的 date_range;否则等同 30d
    - custom: start / end 必须 ISO YYYY-MM-DD
    """
    user_id = int(current_user["id"])
    start_iso, end_iso, range_label = _resolve_range(
        user_id, product_id, range or "default", start, end, session_id
    )

    comments = get_comments(
        user_id,
        product_id=product_id,
        session_id=session_id,
        version=version or None,
        date_start=start_iso or None,
        date_end=end_iso or None,
    )
    for c in comments:
        c.pop("embedding", None)

    time_label = _fmt_time_label(range_label, start_iso, end_iso)
    context = {
        "product_id": product_id,
        "version": "AGGREGATED",
        "time_label": time_label,
        "workflow_purpose": "",
    }

    if comments:
        comment_ids = tuple(int(c["id"]) for c in comments if c.get("id") is not None)
        modules_raw = _cached_build_insights(
            user_id, product_id, start_iso or "", end_iso or "", comment_ids, comments, context,
            locale=get_analysis_locale(request),
        )
        if modules_raw:
            try:
                credit_consume(user_id, 6, "insight", product_id)
            except InsufficientCreditsError as e:
                raise HTTPException(status_code=402, detail=f"Not enough credits: {e.needed} needed, {e.balance} left") from e
    else:
        modules_raw = {}

    modules = {
        key: AnalysisResultModulePayload(**value)
        if isinstance(value, dict)
        else AnalysisResultModulePayload(summary=str(value))
        for key, value in (modules_raw or {}).items()
    }

    synthetic_session = _build_synthetic_session(
        user_id, product_id, comments, start_iso, end_iso, session_id
    )

    return AnalysisResultsPayload(
        session=synthetic_session,
        context=context,
        modules=modules,
        comments=comments,
        generated_at=datetime.utcnow(),
        range=range_label,
        range_start=start_iso or None,
        range_end=end_iso or None,
        is_aggregated=True,
    )


@router.get("/compare", response_model=AnalysisComparePayload)
def get_compare_dataset(
    compare_type: str = Query(default="custom"),
    session_ids: list[int] = Query(default_factory=list),
    product_id: str | None = Query(default=None),
    current_user: dict = Depends(get_current_user),
) -> AnalysisComparePayload:
    user_id = int(current_user["id"])
    try:
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
    except Exception:
        logging.getLogger(__name__).exception("compare dataset failed")
        dataset = {}
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


@router.delete("/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_session_endpoint(
    session_id: int,
    current_user: dict = Depends(get_current_user),
) -> None:
    user_id = int(current_user["id"])
    session = get_session_by_id(user_id, session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found.",
        )
    delete_session(user_id, session_id)


class ReanalyzeRequest(BaseModel):
    session_id: int


class ReanalyzeResponse(BaseModel):
    job_id: int
    session_id: int
    reset_count: int
    message: str


@router.post("/reanalyze", response_model=ReanalyzeResponse)
def reanalyze_session(
    req: ReanalyzeRequest,
    current_user: dict = Depends(get_current_user),
) -> ReanalyzeResponse:
    """重置 session 评论的分析状态并重新入队分析任务。"""
    user_id = int(current_user["id"])
    session = get_session_by_id(user_id, req.session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found.",
        )

    reset_count = reset_session_analysis(user_id, req.session_id)
    if reset_count == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No comments found in this session.",
        )

    jobs = get_upload_jobs_by_session(user_id, req.session_id)
    if not jobs:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No upload job found for this session.",
        )
    job_id = int(jobs[0]["id"])

    update_upload_job(user_id, job_id, {"status": "queued", "error_message": None})
    _invalidate_insights_cache(user_id, str(session.get("product_id") or ""))

    try:
        enqueue_upload_job_task(user_id, job_id)
    except Exception as exc:
        _LOGGER.warning("reanalyze enqueue failed, running inline: %s", exc)
        from workers.jobs import process_upload_job
        process_upload_job(user_id, job_id)

    return ReanalyzeResponse(
        job_id=job_id,
        session_id=req.session_id,
        reset_count=reset_count,
        message=f"Reset {reset_count} comments and re-queued analysis job {job_id}.",
    )


def _invalidate_insights_cache(user_id: int, product_id: str) -> None:
    """清除缓存结果，确保重分析后返回最新数据。"""
    _INSIGHTS_CACHE.clear()


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


def _resolve_range(
    user_id: int,
    product_id: str,
    range_value: str,
    start: str | None,
    end: str | None,
    session_id: int | None,
) -> tuple[str, str, str]:
    """返回 (start_iso, end_iso, normalized_range_label)。空串表示不加该过滤。"""

    range_norm = (range_value or "default").strip().lower()
    today = datetime.utcnow().date()

    if range_norm == "all":
        return "", "", "all"

    if range_norm == "custom":
        if not (start and end):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="custom range requires start and end (YYYY-MM-DD).",
            )
        return start.strip(), end.strip(), "custom"

    if range_norm in ("7d", "14d", "30d", "90d"):
        days = int(range_norm.rstrip("d"))
        return (today - timedelta(days=days)).isoformat(), today.isoformat(), range_norm

    # default — 优先级：1) session.date_range；2) 该 session 评论的实际 min/max date；
    # 3) 产品最近 session 的 date_range；4) 该产品所有评论的 min/max；5) 最近 30 天兜底
    if session_id is not None:
        session = get_session_by_id(user_id, session_id)
        if session:
            s = str(session.get("date_range_start") or "").strip()
            e = str(session.get("date_range_end") or "").strip()
            if s and e:
                return s, e, "default"
            # session 没标 date_range:回退到该 session 评论的实际日期跨度
            s, e = _comments_date_span(user_id, session_id=int(session["id"]))
            if s and e:
                return s, e, "default"
            # session 存在但日期无法解析 — 不做日期过滤，靠 session_id 查询兜底
            return "", "", "all"

    # 找该产品最近一个 session 的 date_range
    sessions = get_sessions(user_id, product_id=product_id)
    if sessions:
        latest = sessions[0]
        s = str(latest.get("date_range_start") or "").strip()
        e = str(latest.get("date_range_end") or "").strip()
        if s and e:
            return s, e, "default"

    # 该产品全部评论的 min/max date
    s, e = _comments_date_span(user_id, product_id=product_id)
    if s and e:
        return s, e, "default"

    # 最后兜底：最近 30 天
    return (today - timedelta(days=30)).isoformat(), today.isoformat(), "30d"


def _comments_date_span(
    user_id: int,
    session_id: int | None = None,
    product_id: str | None = None,
) -> tuple[str, str]:
    """返回 (min_date, max_date)。无评论或无有效日期时返回 ('', '')。"""
    comments = get_comments(user_id, session_id=session_id, product_id=product_id)
    dates = [str(c.get("date") or "").strip() for c in comments]
    dates = [d for d in dates if d and d[:4].isdigit()]
    if not dates:
        return "", ""
    return min(dates)[:10], max(dates)[:10]


def _fmt_time_label(range_label: str, start_iso: str, end_iso: str) -> str:
    if range_label == "all" or (not start_iso and not end_iso):
        return "All Time"
    if range_label in ("7d", "14d", "30d", "90d"):
        return f"Last {range_label}"
    if start_iso and end_iso:
        return f"{start_iso} ~ {end_iso}"
    return start_iso or end_iso or "All Time"


def _build_synthetic_session(
    user_id: int,
    product_id: str,
    comments: list[dict[str, Any]],
    start_iso: str,
    end_iso: str,
    session_id: int | None,
) -> AnalysisSessionPayload:
    """聚合视图下,构造一个"虚拟" session 给前端渲染头部信息。"""

    positive = sum(1 for c in comments if str(c.get("sentiment") or "").lower() == "positive")
    negative = sum(1 for c in comments if str(c.get("sentiment") or "").lower() == "negative")

    # 取该产品最近一个 session 作为元信息参考
    sessions = get_sessions(user_id, product_id=product_id)
    ref = sessions[0] if sessions else {}

    return AnalysisSessionPayload(
        id=int(session_id or 0),
        user_id=user_id,
        product_id=product_id,
        version="AGGREGATED",
        auto_title=f"{product_id} · 聚合视图",
        custom_title=None,
        date_range_start=start_iso or None,
        date_range_end=end_iso or None,
        total_reviews=len(comments),
        positive_count=positive,
        negative_count=negative,
        category=str(ref.get("category") or "") or None,
        prompt_version=None,
        version_notes=None,
        workflow_purpose=str(ref.get("workflow_purpose") or "") or None,
        product_ref_id=ref.get("product_ref_id"),
        variant_ref_id=ref.get("variant_ref_id"),
        warnings_json=None,
        created_at=ref.get("created_at") or datetime.utcnow(),
    )
