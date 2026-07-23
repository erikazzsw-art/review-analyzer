from __future__ import annotations

import threading
from datetime import datetime, timedelta
from typing import Any

from review_analyzer.action_store import get_action_items
from review_analyzer.database import get_sessions
from review_analyzer.product_store import get_product_overview_rows
from review_analyzer.review_store import get_review_trackers
from review_analyzer.workflow_prompts import get_workflow_purpose_label

ACTIVE_ACTION_STATUSES = {"todo", "in_progress", "pending_review"}
ACTIVE_TRACKER_STATUSES = {"pending", "follow_up"}

_ROLE_LABELS = {
    "运营": {"zh": "运营", "en": "Operations"},
    "产研": {"zh": "产研", "en": "Product & R&D"},
    "质检": {"zh": "质检", "en": "Quality Assurance"},
    "管理者": {"zh": "管理者", "en": "Manager"},
    "复盘": {"zh": "复盘", "en": "Follow-up"},
    "跨团队": {"zh": "跨团队", "en": "Cross-functional"},
}

_lang_var = threading.local()


def _set_lang(lang: str) -> None:
    _lang_var.value = lang


def pick(zh: str, en: str) -> str:
    return zh if getattr(_lang_var, "value", "zh") == "zh" else en


def role_label(value: str | None) -> str:
    if not value:
        return pick("未分配", "Unassigned")
    mapping = _ROLE_LABELS.get(value)
    if not mapping:
        return value
    lang = getattr(_lang_var, "value", "zh")
    return mapping.get(lang, mapping["zh"])

WORKSPACE_INTRO = {
    "headline": "今天先看最影响增长和口碑的评论信号。",
    "focus": "风险 SKU、未完结行动、复盘事项和最新批次会在这里汇总成同一套待办。",
}

WORKSPACE_INTRO_EN = {
    "headline": "Start with the review signals that most affect growth and reputation today.",
    "focus": "Risk SKUs, open actions, follow-up items, and recent batches are summarized into one shared task list.",
}


def get_workspace_summary(user_id: int, lang: str) -> dict[str, Any]:
    _set_lang(lang)
    products = get_product_overview_rows(user_id)
    actions = get_action_items(user_id)
    trackers = get_review_trackers(user_id)
    sessions = get_sessions(user_id)

    risk_products = _build_risk_products(products)
    open_actions = [item for item in actions if str(item.get("status")) in ACTIVE_ACTION_STATUSES]
    open_trackers = [item for item in trackers if str(item.get("result_status")) in ACTIVE_TRACKER_STATUSES]
    recent_upload_count = _count_recent_uploads(sessions, days=7)

    return {
        "intro": WORKSPACE_INTRO if lang == "zh" else WORKSPACE_INTRO_EN,
        "metrics": {
            "product_count": len(products),
            "risk_product_count": len(risk_products),
            "open_action_count": len(open_actions),
            "open_tracker_count": len(open_trackers),
            "recent_upload_count": recent_upload_count,
        },
        "today_tasks": _build_today_tasks(products, risk_products, open_actions, open_trackers, sessions),
        "risk_products": risk_products[:5],
        "pending_trackers": _build_pending_trackers(open_trackers)[:5],
        "role_action_summary": _build_role_action_summary(open_actions),
        "recent_sessions": _build_recent_sessions(sessions)[:5],
    }


def _build_risk_products(products: list[dict[str, Any]]) -> list[dict[str, Any]]:
    ranked = sorted(
        products,
        key=lambda row: (
            float(row.get("negative_rate") or 0.0),
            int(row.get("pending_review_count") or 0),
            int(row.get("review_count") or 0),
        ),
        reverse=True,
    )
    risk_rows: list[dict[str, Any]] = []
    for row in ranked:
        negative_rate = float(row.get("negative_rate") or 0.0)
        pending_reviews = int(row.get("pending_review_count") or 0)
        review_count = int(row.get("review_count") or 0)
        if review_count == 0:
            continue
        if negative_rate < 12 and pending_reviews == 0:
            continue
        risk_rows.append(
            {
                "product_id": row.get("parent_product_id"),
                "product_name": row.get("name") or row.get("parent_product_id"),
                "negative_rate": negative_rate,
                "top_issue": row.get("top_issue") or pick("待确认", "To confirm"),
                "pending_review_count": pending_reviews,
                "review_count": review_count,
                "latest_session_label": row.get("latest_session_label") or pick("未记录", "Not recorded"),
            }
        )
    return risk_rows


def _build_pending_trackers(trackers: list[dict[str, Any]]) -> list[dict[str, Any]]:
    ranked = sorted(
        trackers,
        key=lambda row: (
            0 if str(row.get("result_status")) == "pending" else 1,
            _safe_float(row.get("baseline_pct")),
            _safe_float(row.get("current_pct")),
        ),
        reverse=True,
    )
    result: list[dict[str, Any]] = []
    for row in ranked:
        result.append(
            {
                "title": row.get("tracker_title") or row.get("tag_name") or pick("未命名复盘", "Untitled tracker"),
                "product_name": row.get("product_name") or row.get("parent_product_id") or pick("未绑定产品", "Unassigned product"),
                "tag_name": row.get("tag_name") or pick("待确认问题", "Issue to confirm"),
                "status": row.get("result_status") or "pending",
                "baseline_pct": _safe_float(row.get("baseline_pct")),
                "current_pct": _safe_float(row.get("current_pct")),
                "review_scope": row.get("review_scope") or pick("未设置", "Not set"),
            }
        )
    return result


def _build_role_action_summary(actions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    roles = ["运营", "产研", "质检", "复盘"]
    summary: list[dict[str, Any]] = []
    for role in roles:
        count = sum(1 for item in actions if str(item.get("owner_role")) == role)
        summary.append({"role": role_label(role), "count": count})
    return summary


def _build_recent_sessions(sessions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for session in sessions[:]:
        title = session.get("custom_title") or session.get("auto_title") or session.get("version") or pick("未命名批次", "Untitled batch")
        result.append(
            {
                "session_id": int(session.get("id") or 0),
                "title": str(title),
                "product_id": str(session.get("product_id") or pick("未绑定产品", "Unassigned product")),
                "workflow_purpose": get_workflow_purpose_label(str(session.get("workflow_purpose") or "日常评论分析")),
                "created_at": str(session.get("created_at") or "")[:16],
                "total_reviews": int(session.get("total_reviews") or 0),
            }
        )
    return result


def _build_today_tasks(
    products: list[dict[str, Any]],
    risk_products: list[dict[str, Any]],
    actions: list[dict[str, Any]],
    trackers: list[dict[str, Any]],
    sessions: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    tasks: list[dict[str, Any]] = []
    if actions:
        action = actions[0]
        tasks.append(
            _task(
                pick("行动中心", "Action Center"),
                pick(
                    f"先推进「{action.get('tag_name') or action.get('title') or '高频问题'}」",
                    f"Move '{action.get('tag_name') or action.get('title') or 'recurring issue'}' forward first",
                ),
                pick(
                    f"{_display_product_name(action)} 已有未完结行动，建议先确认负责人、状态和下一步。",
                    f"{_display_product_name(action)} has an open action. Confirm the owner, status, and next step first.",
                ),
                pick("去行动中心", "Open Action Center"),
                "actions",
            )
        )
    if risk_products:
        risk = risk_products[0]
        tasks.append(
            _task(
                pick("风险 SKU", "Risk SKU"),
                pick(f"优先查看 {risk['product_name']} 的「{risk['top_issue']}」", f"Review '{risk['top_issue']}' for {risk['product_name']}"),
                pick(
                    f"当前差评率 {risk['negative_rate']:.1f}%，适合先判断是否需要进入行动中心或复盘追踪。",
                    f"The current negative rate is {risk['negative_rate']:.1f}%. Decide whether this needs an action item or follow-up tracking.",
                ),
                pick("看产品管理", "Open Product Management"),
                "products",
            )
        )
    if trackers:
        tracker = trackers[0]
        tasks.append(
            _task(
                pick("复盘追踪", "Follow-up Tracking"),
                pick(
                    f"回看「{tracker.get('tag_name') or tracker.get('title') or '核心问题'}」改善效果",
                    f"Review whether '{tracker.get('tag_name') or tracker.get('title') or 'core issue'}' is improving",
                ),
                pick(
                    f"{tracker.get('product_name') or '当前产品'} 已进入复盘期，建议尽快补齐当前占比和结论。",
                    f"{tracker.get('product_name') or 'The current product'} is now in follow-up. Fill in the current rate and final conclusion next.",
                ),
                pick("去复盘追踪", "Open Follow-up Tracking"),
                "reviews",
            )
        )
    comparable_products = [row for row in products if int(row.get("session_count") or 0) >= 2]
    if len(tasks) < 3 and comparable_products:
        row = comparable_products[0]
        tasks.append(
            _task(
                pick("版本验证", "Version Validation"),
                pick(
                    f"对比 {row.get('name') or row.get('parent_product_id')} 的不同版本表现",
                    f"Compare different versions of {row.get('name') or row.get('parent_product_id')}",
                ),
                pick(
                    "如果旧问题下降但新问题出现，就可以更快判断当前改版是否值得继续推进。",
                    "If older issues decline but new ones appear, you can judge the version update much faster.",
                ),
                pick("去对比分析", "Open Compare"),
                "analysis",
                {"analysis_subpage": "compare"},
            )
        )
    if len(tasks) < 3 and sessions:
        latest = sessions[0]
        tasks.append(
            _task(
                pick("最新批次", "Latest Batch"),
                pick(
                    f"查看最近上传的 {latest.get('product_id') or '产品'} 评论",
                    f"Review the latest upload for {latest.get('product_id') or 'this product'}",
                ),
                pick(
                    "新评论最适合先判断新增问题、误用场景和亮点是否变化。",
                    "Use the newest reviews to judge newly emerging issues, misuse scenarios, and changing highlights.",
                ),
                pick("看分析结果", "Open Results"),
                "analysis",
                {
                    "analysis_subpage": "results",
                    "selected_product_id": latest.get("product_id"),
                    "view_session_id": latest.get("id"),
                },
            )
        )
    return tasks[:3]


def _task(
    category: str,
    title: str,
    description: str,
    cta_label: str,
    page: str,
    session_updates: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "category": category,
        "title": title,
        "description": description,
        "cta_label": cta_label,
        "page": page,
        "session_updates": session_updates or {},
    }


def _display_product_name(item: dict[str, Any]) -> str:
    return str(
        item.get("product_name")
        or item.get("parent_product_id")
        or item.get("source_product_id")
        or pick("当前产品", "Current product")
    )


def _count_recent_uploads(sessions: list[dict[str, Any]], days: int) -> int:
    threshold = datetime.now() - timedelta(days=days)
    count = 0
    for session in sessions:
        created_at = _to_datetime(session.get("created_at"))
        if created_at and created_at >= threshold:
            count += 1
    return count


def _safe_float(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _to_datetime(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.replace(tzinfo=None) if value.tzinfo else value

    text = str(value).strip()
    if not text:
        return None
    for fmt in (
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d %H:%M:%S.%f",
        "%Y-%m-%dT%H:%M:%S.%f",
    ):
        try:
            return datetime.strptime(text[:26], fmt)
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).replace(tzinfo=None)
    except ValueError:
        return None
