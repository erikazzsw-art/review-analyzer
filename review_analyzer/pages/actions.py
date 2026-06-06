"""行动中心页面。"""

from __future__ import annotations

from typing import Any

import streamlit as st

from review_analyzer.action_store import (
    ACTION_STATUSES,
    get_action_item_by_id,
    get_action_items,
    update_action_status,
)
from review_analyzer.auth import get_current_user_id
from review_analyzer.i18n import action_status_label, pick, role_label, t
from review_analyzer.page_shell import navigate, render_page_header
from review_analyzer.review_store import create_review_tracker, get_review_tracker_by_action_id


ROLE_FILTER_OPTIONS = ["全部", "运营", "产研", "质检", "复盘"]
STATUS_FILTER_OPTIONS = ["全部", *ACTION_STATUSES]


def render_actions() -> None:
    user_id = get_current_user_id()
    if not user_id:
        st.warning(t("login_required"))
        return

    render_page_header(
        pick("行动中心", "Action Center"),
        pick("把 TOP 问题转成团队事项，持续跟踪状态并准备后续复盘。", "Turn top issues into team actions, track status, and prepare the next follow-up."),
        path=pick("核心工作流 / 行动中心", "Core Workflow / Action Center"),
    )

    flash_message = st.session_state.pop("action_center_flash", None)
    if flash_message:
        st.success(flash_message)

    col1, col2 = st.columns(2)
    with col1:
        status_filter = st.selectbox(
            pick("状态筛选", "Status Filter"),
            STATUS_FILTER_OPTIONS,
            format_func=lambda value: pick("全部状态", "All Statuses") if value == "全部" else action_status_label(value),
            key="action_status_filter",
        )
    with col2:
        role_filter = st.selectbox(pick("角色筛选", "Role Filter"), ROLE_FILTER_OPTIONS, format_func=lambda value: pick("全部角色", "All Roles") if value == "全部" else role_label(value), key="action_role_filter")

    items = get_action_items(
        user_id,
        status=None if status_filter == "全部" else status_filter,
        owner_role=None if role_filter == "全部" else role_filter,
    )

    if not items:
        st.info(pick("暂无行动事项。先在分析结果页从 TOP 问题创建一个动作。", "There are no action items yet. Create one from a top issue in the results page first."))
        return

    for item in items:
        _render_action_card(user_id, item)


def _render_action_card(user_id: int, item: dict[str, Any]) -> None:
    product_display = item.get("product_name") or item.get("parent_product_id") or item.get("source_product_id") or pick("未绑定产品", "Unassigned product")
    variant_display = item.get("variant_sku") or item.get("child_asin") or pick("未绑定变体", "Unassigned variant")
    current_pct = f"{float(item['current_pct']):.1f}%" if item.get("current_pct") is not None else "—"
    status_label = action_status_label(str(item.get("status")))
    expected_review_at = item.get("expected_review_at") or pick("未设置", "Not set")
    source_batch = item.get("source_batch_label") or item.get("source_version") or pick("未记录", "Not recorded")

    st.markdown(
        f"""
        <div class="product-block" style="padding:22px 24px;margin-bottom:18px;">
            <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:16px;flex-wrap:wrap;">
                <div>
                    <div style="font-size:18px;font-weight:700;color:#202020;">{item.get("title")}</div>
                    <div style="font-size:13px;color:#828282;margin-top:6px;">
                        {product_display} · {variant_display} · {source_batch}
                    </div>
                </div>
                <div style="display:flex;gap:8px;flex-wrap:wrap;">
                    <span class="tag tag-topic">{role_label(str(item.get("owner_role") or ""))}</span>
                    <span class="tag tag-platform">{status_label}</span>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    info_cols = st.columns(4)
    with info_cols[0]:
        st.markdown(f"**{pick('问题标签', 'Issue Tag')}**  \n{item.get('tag_name') or '—'}")
    with info_cols[1]:
        st.markdown(f"**{pick('当前占比', 'Current Share')}**  \n{current_pct}")
    with info_cols[2]:
        st.markdown(f"**{pick('责任角色', 'Owner Role')}**  \n{role_label(str(item.get('owner_role') or ''))}")
    with info_cols[3]:
        st.markdown(f"**{pick('预计复盘时间', 'Expected Follow-up Time')}**  \n{expected_review_at}")

    if item.get("suggested_action"):
        st.markdown(f"**{pick('建议动作', 'Suggested Action')}**  \n{item['suggested_action']}")
    if item.get("expected_effect_batch"):
        st.markdown(f"**{pick('预计生效批次', 'Expected Effective Batch')}**  \n{item['expected_effect_batch']}")

    control_cols = st.columns([2, 1])
    with control_cols[0]:
        next_status = st.selectbox(
            pick("更新状态", "Update Status"),
            ACTION_STATUSES,
            index=ACTION_STATUSES.index(item.get("status") or "todo"),
            format_func=lambda value: action_status_label(value),
            key=f"action_status_select_{item['id']}",
        )
    with control_cols[1]:
        st.markdown("<div style='height:28px;'></div>", unsafe_allow_html=True)
        if st.button(pick("保存状态", "Save Status"), key=f"action_status_save_{item['id']}", type="primary", use_container_width=True):
            update_action_status(user_id, int(item["id"]), next_status)
            st.success(pick("状态已更新", "Status updated"))
            st.rerun()

    tracker = get_review_tracker_by_action_id(user_id, int(item["id"]))
    tracker_cols = st.columns([1, 1, 2])
    with tracker_cols[0]:
        if tracker:
            if st.button(pick("查看复盘", "View Follow-up"), key=f"action_view_tracker_{item['id']}", use_container_width=True):
                st.session_state["review_center_flash"] = pick(
                    f"已定位到「{tracker.get('tracker_title') or item.get('title')}」",
                    f"Focused on '{tracker.get('tracker_title') or item.get('title')}'",
                )
                navigate("reviews")
        else:
            if st.button(pick("加入复盘", "Add to Follow-up"), key=f"action_create_tracker_{item['id']}", use_container_width=True):
                _create_tracker_from_action(user_id, int(item["id"]))
    with tracker_cols[1]:
        if item.get("status") != "pending_review" and st.button(
            pick("标记待复盘", "Mark Pending Follow-up"),
            key=f"action_mark_pending_{item['id']}",
            use_container_width=True,
        ):
            update_action_status(user_id, int(item["id"]), "pending_review")
            st.success(pick("已标记为待复盘", "Marked as pending follow-up"))
            st.rerun()


def _create_tracker_from_action(user_id: int, action_id: int) -> None:
    action_item = get_action_item_by_id(user_id, action_id)
    if not action_item:
        st.error(pick("未找到对应行动事项", "The related action item was not found."))
        return

    existing_tracker = get_review_tracker_by_action_id(user_id, action_id)
    if existing_tracker:
        st.info(pick("该事项已生成复盘追踪", "A follow-up tracker has already been created for this item."))
        return

    tracker_title = pick(
        f"{action_item.get('tag_name') or action_item.get('title')}复盘",
        f"{action_item.get('tag_name') or action_item.get('title')} Follow-up",
    )
    create_review_tracker(
        user_id,
        {
            "action_item_id": action_id,
            "product_id": action_item.get("product_id"),
            "variant_id": action_item.get("variant_id"),
            "tracker_title": tracker_title,
            "tag_name": action_item.get("tag_name"),
            "baseline_pct": action_item.get("current_pct"),
            "improvement_action": action_item.get("suggested_action"),
            "effective_batch": action_item.get("expected_effect_batch"),
            "review_scope": action_item.get("expected_review_at"),
            "result_status": "pending",
            "conclusion": None,
        },
    )
    update_action_status(user_id, action_id, "pending_review")
    st.session_state["review_center_flash"] = pick(
        f"已创建「{tracker_title}」，可在复盘追踪里继续填写结果。",
        f"Created '{tracker_title}'. Continue filling in the result in Follow-up Tracking.",
    )
    navigate("reviews")
