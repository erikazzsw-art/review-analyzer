from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, Query

from backend_api.app.deps import get_current_user
from backend_api.app.schemas.workspace import WorkspaceSummaryPayload
from review_analyzer.workspace_store import get_workspace_summary

router = APIRouter(prefix="/workspace", tags=["workspace"])


def _safe_text(value: Any, fallback: str) -> str:
    return value if isinstance(value, str) and value.strip() else fallback


def _safe_int(value: Any, fallback: int = 0) -> int:
    return value if isinstance(value, int) else fallback


def _safe_float(value: Any, fallback: float = 0.0) -> float:
    return value if isinstance(value, (int, float)) else fallback


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _normalize_workspace_summary(summary: dict[str, Any]) -> dict[str, Any]:
    intro = _as_dict(summary.get("intro"))
    metrics = _as_dict(summary.get("metrics"))
    role_action_summary = summary.get("role_action_summary", [])
    responsibility_action_summary = summary.get("responsibility_action_summary", [])
    if not isinstance(role_action_summary, list):
        role_action_summary = []
    if not isinstance(responsibility_action_summary, list):
        responsibility_action_summary = []
    if not responsibility_action_summary:
        responsibility_action_summary = [
            {
                "responsibility": item.get("responsibility") or item.get("role"),
                "count": item.get("count"),
            }
            for item in role_action_summary
            if isinstance(item, dict)
        ]

    return {
        "intro": {
            "headline": _safe_text(intro.get("headline"), "欢迎回来"),
            "focus": _safe_text(intro.get("focus"), "工作台数据正在加载。"),
        },
        "metrics": {
            "product_count": _safe_int(metrics.get("product_count")),
            "risk_product_count": _safe_int(metrics.get("risk_product_count")),
            "open_action_count": _safe_int(metrics.get("open_action_count")),
            "open_tracker_count": _safe_int(metrics.get("open_tracker_count")),
            "recent_upload_count": _safe_int(metrics.get("recent_upload_count")),
        },
        "today_tasks": [
            {
                "category": _safe_text(task.get("category"), "未分类"),
                "title": _safe_text(task.get("title"), "待处理事项"),
                "description": _safe_text(task.get("description"), "暂无描述。"),
                "cta_label": _safe_text(task.get("cta_label"), "继续处理"),
                "page": _safe_text(task.get("page"), "/workspace"),
                "session_updates": task.get("session_updates") if isinstance(task.get("session_updates"), dict) else {},
            }
            for task in summary.get("today_tasks", [])
            if isinstance(task, dict)
        ],
        "risk_products": [
            {
                "product_id": item.get("product_id") if item.get("product_id") is None or isinstance(item.get("product_id"), str) else None,
                "product_name": _safe_text(item.get("product_name"), "未命名产品"),
                "negative_rate": _safe_float(item.get("negative_rate")),
                "top_issue": _safe_text(item.get("top_issue"), "暂无问题"),
                "pending_review_count": _safe_int(item.get("pending_review_count")),
                "review_count": _safe_int(item.get("review_count")),
                "latest_session_label": _safe_text(item.get("latest_session_label"), "最近批次"),
            }
            for item in summary.get("risk_products", [])
            if isinstance(item, dict)
        ],
        "pending_trackers": [
            {
                "title": _safe_text(item.get("title"), "待复盘事项"),
                "product_name": _safe_text(item.get("product_name"), "未命名产品"),
                "tag_name": _safe_text(item.get("tag_name"), "未分类"),
                "status": _safe_text(item.get("status"), "new"),
                "baseline_pct": item.get("baseline_pct") if isinstance(item.get("baseline_pct"), (int, float)) else None,
                "current_pct": item.get("current_pct") if isinstance(item.get("current_pct"), (int, float)) else None,
                "review_scope": _safe_text(item.get("review_scope"), "all"),
            }
            for item in summary.get("pending_trackers", [])
            if isinstance(item, dict)
        ],
        "responsibility_action_summary": [
            {
                "responsibility": _safe_text(item.get("responsibility") or item.get("role"), "未归属"),
                "count": _safe_int(item.get("count")),
            }
            for item in responsibility_action_summary
            if isinstance(item, dict)
        ],
        "role_action_summary": [
            {
                "role": _safe_text(item.get("role") or item.get("responsibility"), "未知"),
                "count": _safe_int(item.get("count")),
            }
            for item in role_action_summary
            if isinstance(item, dict)
        ],
        "recent_sessions": [
            {
                "session_id": _safe_int(item.get("session_id")),
                "title": _safe_text(item.get("title"), "未命名批次"),
                "product_id": _safe_text(item.get("product_id"), ""),
                "workflow_purpose": _safe_text(item.get("workflow_purpose"), "manual"),
                "created_at": _safe_text(item.get("created_at"), ""),
                "total_reviews": _safe_int(item.get("total_reviews")),
            }
            for item in summary.get("recent_sessions", [])
            if isinstance(item, dict)
        ],
    }


@router.get("/summary", response_model=WorkspaceSummaryPayload)
def get_workspace_summary_route(
    lang: str = Query(default="zh"),
    current_user: dict = Depends(get_current_user),
) -> WorkspaceSummaryPayload:
    selected_lang = lang if lang in {"zh", "en"} else "zh"
    summary = _normalize_workspace_summary(
        get_workspace_summary(
            int(current_user["id"]),
            selected_lang,
        )
    )
    return WorkspaceSummaryPayload(
        **summary,
        generated_at=datetime.utcnow(),
    )
