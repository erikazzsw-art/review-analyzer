from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any

import streamlit as st

from review_analyzer.action_store import get_action_items
from review_analyzer.database import get_sessions
from review_analyzer.i18n import get_lang, pick, role_label
from review_analyzer.product_store import get_product_overview_rows
from review_analyzer.review_store import get_review_trackers
from review_analyzer.workflow_prompts import get_workflow_purpose_label


ROLES = ["运营", "产研", "质检", "管理者"]
ACTIVE_ACTION_STATUSES = {"todo", "in_progress", "pending_review"}
ACTIVE_TRACKER_STATUSES = {"pending", "follow_up"}

ROLE_INTROS = {
    "运营": {
        "headline": "今天先处理最影响转化和口碑的评论问题。",
        "focus": "优先差评处理、Listing 优化和待复盘事项。",
    },
    "产研": {
        "headline": "今天先验证问题是否值得改版，以及哪些卖点值得继续放大。",
        "focus": "优先版本对比、功能缺口和竞品机会。",
    },
    "质检": {
        "headline": "今天先盯住高频质量客诉，避免问题继续放大。",
        "focus": "优先质量类动作、风险 SKU 和复盘闭环。",
    },
    "管理者": {
        "headline": "今天先看最危险的 SKU 和最该推进的闭环事项。",
        "focus": "优先风险排序、未完结事项和改版效果判断。",
    },
}

ROLE_INTROS_EN = {
    "运营": {
        "headline": "start with the review issues that most affect conversion and reputation today.",
        "focus": "Prioritize negative-review handling, listing optimization, and pending follow-up items.",
    },
    "产研": {
        "headline": "start by validating which problems deserve a product update and which selling points deserve more emphasis.",
        "focus": "Prioritize version comparison, feature gaps, and competitor opportunities.",
    },
    "质检": {
        "headline": "focus on recurring quality complaints before they spread further.",
        "focus": "Prioritize quality actions, risky SKUs, and the follow-up loop.",
    },
    "管理者": {
        "headline": "start with the riskiest SKUs and the most important loop items to push forward.",
        "focus": "Prioritize risk ranking, open items, and version-update outcomes.",
    },
}


@st.cache_data(ttl=30)
def get_workspace_summary(user_id: int, role: str, lang: str) -> dict[str, Any]:
    selected_role = role if role in ROLES else ROLES[0]
    products = get_product_overview_rows(user_id)
    actions = get_action_items(user_id)
    trackers = get_review_trackers(user_id)
    sessions = get_sessions(user_id)

    risk_products = _build_risk_products(products)
    open_actions = [item for item in actions if str(item.get("status")) in ACTIVE_ACTION_STATUSES]
    open_trackers = [item for item in trackers if str(item.get("result_status")) in ACTIVE_TRACKER_STATUSES]
    recent_upload_count = _count_recent_uploads(sessions, days=7)

    return {
        "role": selected_role,
        "intro": ROLE_INTROS[selected_role] if lang == "zh" else ROLE_INTROS_EN[selected_role],
        "metrics": {
            "product_count": len(products),
            "risk_product_count": len(risk_products),
            "open_action_count": len(open_actions),
            "open_tracker_count": len(open_trackers),
            "recent_upload_count": recent_upload_count,
        },
        "today_tasks": _build_today_tasks(selected_role, products, risk_products, open_actions, open_trackers, sessions, lang),
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
    role: str,
    products: list[dict[str, Any]],
    risk_products: list[dict[str, Any]],
    actions: list[dict[str, Any]],
    trackers: list[dict[str, Any]],
    sessions: list[dict[str, Any]],
    lang: str,
) -> list[dict[str, Any]]:
    builders = {
        "运营": _build_operator_tasks,
        "产研": _build_product_tasks,
        "质检": _build_quality_tasks,
        "管理者": _build_manager_tasks,
    }
    tasks = builders[role](products, risk_products, actions, trackers, sessions, lang)
    return tasks[:3]


def _build_operator_tasks(
    products: list[dict[str, Any]],
    risk_products: list[dict[str, Any]],
    actions: list[dict[str, Any]],
    trackers: list[dict[str, Any]],
    sessions: list[dict[str, Any]],
    lang: str,
) -> list[dict[str, Any]]:
    tasks: list[dict[str, Any]] = []
    operator_actions = [item for item in actions if str(item.get("owner_role")) == "运营"]
    if operator_actions:
        action = operator_actions[0]
        tasks.append(
            _task(
                pick("行动中心", "Action Center"),
                pick(
                    f"先处理「{action.get('tag_name') or action.get('title') or '高频问题'}」",
                    f"Handle '{action.get('tag_name') or action.get('title') or 'recurring issue'}' first",
                ),
                pick(
                    f"{_display_product_name(action)} 当前已进入运营动作流，建议先推进状态并确认修改动作。",
                    f"{_display_product_name(action)} is already in the operations action flow. Update the status and confirm the next fix first.",
                ),
                pick("去行动中心", "Open Action Center"),
                "actions",
            )
        )
    if risk_products:
        risk = risk_products[0]
        tasks.append(
            _task(
                pick("Listing 优化", "Listing Optimization"),
                pick(
                    f"优先优化 {risk['product_name']} 的「{risk['top_issue']}」",
                    f"Prioritize {risk['top_issue']} for {risk['product_name']}",
                ),
                pick(
                    f"当前差评率 {risk['negative_rate']:.1f}%，适合先从描述澄清、安装说明或素材表达切入。",
                    f"The current negative rate is {risk['negative_rate']:.1f}%. Start with clearer descriptions, setup guidance, or creative messaging.",
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
    return tasks


def _build_product_tasks(
    products: list[dict[str, Any]],
    risk_products: list[dict[str, Any]],
    actions: list[dict[str, Any]],
    trackers: list[dict[str, Any]],
    sessions: list[dict[str, Any]],
    lang: str,
) -> list[dict[str, Any]]:
    tasks: list[dict[str, Any]] = []
    rd_actions = [item for item in actions if str(item.get("owner_role")) == "产研"]
    if rd_actions:
        action = rd_actions[0]
        tasks.append(
            _task(
                pick("产研动作", "Product & R&D"),
                pick(
                    f"先判断「{action.get('tag_name') or action.get('title') or '功能问题'}」是否需要改版",
                    f"Decide whether '{action.get('tag_name') or action.get('title') or 'feature issue'}' needs a version update",
                ),
                pick(
                    f"{_display_product_name(action)} 已经沉淀成产研事项，建议确认是否进入版本改版验证。",
                    f"{_display_product_name(action)} is already captured as a product task. Confirm whether it should move into version-validation work.",
                ),
                pick("去行动中心", "Open Action Center"),
                "actions",
            )
        )
    comparable_products = [row for row in products if int(row.get("session_count") or 0) >= 2]
    if comparable_products:
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
    if risk_products:
        risk = risk_products[0]
        tasks.append(
            _task(
                pick("问题机会", "Issue Opportunity"),
                pick(
                    f"研究 {risk['product_name']} 的「{risk['top_issue']}」根因",
                    f"Investigate the root cause of '{risk['top_issue']}' for {risk['product_name']}",
                ),
                pick(
                    "如果这是结构性问题，优先进入设计、材质或功能层面的改进清单。",
                    "If this is structural, move first into design, material, or feature-level improvements.",
                ),
                pick("看产品管理", "Open Product Management"),
                "products",
            )
        )
    if len(tasks) < 3:
        tasks.append(
            _task(
                pick("多产品机会", "Cross-Product Opportunity"),
                pick("用横向对比找更值得放大的卖点", "Use cross-product comparison to find stronger selling points"),
                pick(
                    "把不同产品或变体放到同一张表里，更容易发现值得主推的功能方向。",
                    "Putting products or variants into one table makes it easier to spot which feature direction deserves more emphasis.",
                ),
                pick("去对比分析", "Open Compare"),
                "analysis",
                {"analysis_subpage": "compare"},
            )
        )
    return tasks


def _build_quality_tasks(
    products: list[dict[str, Any]],
    risk_products: list[dict[str, Any]],
    actions: list[dict[str, Any]],
    trackers: list[dict[str, Any]],
    sessions: list[dict[str, Any]],
    lang: str,
) -> list[dict[str, Any]]:
    tasks: list[dict[str, Any]] = []
    qa_actions = [item for item in actions if str(item.get("owner_role")) == "质检"]
    if qa_actions:
        action = qa_actions[0]
        tasks.append(
            _task(
                pick("质量动作", "Quality Action"),
                pick(
                    f"优先处理 {_display_product_name(action)} 的「{action.get('tag_name') or '质量问题'}」",
                    f"Prioritize '{action.get('tag_name') or 'quality issue'}' for {_display_product_name(action)}",
                ),
                pick(
                    "这类事项最适合先确认是否已落地整改，再决定何时进入复盘。",
                    "These items are best handled by confirming whether the corrective action is already in place before moving into follow-up.",
                ),
                pick("去行动中心", "Open Action Center"),
                "actions",
            )
        )
    if risk_products:
        risk = risk_products[0]
        tasks.append(
            _task(
                pick("高风险 SKU", "High-Risk SKU"),
                pick(
                    f"盯住 {risk['product_name']} 的差评扩散",
                    f"Watch the negative-review spread for {risk['product_name']}",
                ),
                pick(
                    f"当前差评率 {risk['negative_rate']:.1f}%，核心问题是「{risk['top_issue']}」，建议优先抽检或排查批次。",
                    f"The negative rate is {risk['negative_rate']:.1f}%, centered on '{risk['top_issue']}'. Prioritize spot checks or batch investigation.",
                ),
                pick("看产品管理", "Open Product Management"),
                "products",
            )
        )
    if trackers:
        tracker = trackers[0]
        tasks.append(
            _task(
                pick("整改复盘", "Corrective Follow-up"),
                pick(
                    f"补齐「{tracker.get('tag_name') or tracker.get('title') or '问题'}」复盘结果",
                    f"Complete the follow-up result for '{tracker.get('tag_name') or tracker.get('title') or 'issue'}'",
                ),
                pick(
                    "只有把改进前后占比补齐，团队才能确认质量动作是否真的有效。",
                    "Only after the before-and-after rates are filled in can the team confirm whether the quality action really worked.",
                ),
                pick("去复盘追踪", "Open Follow-up Tracking"),
                "reviews",
            )
        )
    return tasks


def _build_manager_tasks(
    products: list[dict[str, Any]],
    risk_products: list[dict[str, Any]],
    actions: list[dict[str, Any]],
    trackers: list[dict[str, Any]],
    sessions: list[dict[str, Any]],
    lang: str,
) -> list[dict[str, Any]]:
    tasks: list[dict[str, Any]] = []
    if risk_products:
        risk = risk_products[0]
        tasks.append(
            _task(
                pick("风险优先级", "Risk Priority"),
                pick(
                    f"先看 {risk['product_name']} 是否需要降级处理",
                    f"Decide first whether {risk['product_name']} needs immediate mitigation",
                ),
                pick(
                    f"当前差评率 {risk['negative_rate']:.1f}%，且聚焦在「{risk['top_issue']}」，适合作为今天的第一优先级。",
                    f"The negative rate is {risk['negative_rate']:.1f}% and centers on '{risk['top_issue']}', making it a strong first priority for today.",
                ),
                pick("看产品管理", "Open Product Management"),
                "products",
            )
        )
    if actions:
        tasks.append(
            _task(
                pick("团队推进", "Team Progress"),
                pick(
                    f"今天还有 {len(actions)} 个未完结事项需要推进",
                    f"There are still {len(actions)} open items to move forward today",
                ),
                pick(
                    "优先看行动中心里还停留在待处理或处理中状态的事项，避免闭环停滞。",
                    "Start with items still marked To Do or In Progress in the Action Center to avoid stalled loops.",
                ),
                pick("去行动中心", "Open Action Center"),
                "actions",
            )
        )
    comparable_products = [row for row in products if int(row.get("session_count") or 0) >= 2]
    if comparable_products:
        tasks.append(
            _task(
                pick("改版效果", "Version Outcome"),
                pick("用对比分析判断哪些 SKU 可以继续加码", "Use comparison analysis to decide which SKUs deserve more push"),
                pick(
                    "管理视角更适合先看主推机会款、风险款和待观察款的分层结果。",
                    "From a management view, start with the layered outcome across priority products, risk products, and watch-list products.",
                ),
                pick("去对比分析", "Open Compare"),
                "analysis",
                {"analysis_subpage": "compare"},
            )
        )
    elif trackers:
        tasks.append(
            _task(
                pick("待复盘事项", "Pending Follow-up"),
                pick(
                    f"当前有 {len(trackers)} 个复盘项待判断是否完结",
                    f"There are {len(trackers)} follow-up items still waiting for closure",
                ),
                pick(
                    "先把待复盘项推进完，管理视角会更容易看清哪些动作真的产生了效果。",
                    "Finishing pending follow-up items first makes it much easier to see which actions truly worked.",
                ),
                pick("去复盘追踪", "Open Follow-up Tracking"),
                "reviews",
            )
        )
    return tasks


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
