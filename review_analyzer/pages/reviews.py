"""复盘追踪页面。"""

from __future__ import annotations

from typing import Any

import streamlit as st

from review_analyzer.auth import get_current_user_id
from review_analyzer.i18n import pick, t, tracker_status_label
from review_analyzer.page_shell import render_page_header
from review_analyzer.review_store import (
    REVIEW_TRACKER_STATUSES,
    get_review_trackers,
    update_review_tracker_result,
)

TRACKER_FILTER_OPTIONS = ["全部", *REVIEW_TRACKER_STATUSES]


def render_reviews() -> None:
    user_id = get_current_user_id()
    if not user_id:
        st.warning(t("login_required"))
        return

    render_page_header(
        pick("复盘追踪", "Follow-up Tracking"),
        pick("判断改进动作有没有真的改善评论反馈，并决定完结还是继续跟进。", "Decide whether the improvement really changed review feedback, and whether to close or keep tracking it."),
        path=pick("核心工作流 / 复盘追踪", "Core Workflow / Follow-up Tracking"),
    )

    flash_message = st.session_state.pop("review_center_flash", None)
    if flash_message:
        st.success(flash_message)

    status_filter = st.selectbox(
        pick("状态筛选", "Status Filter"),
        TRACKER_FILTER_OPTIONS,
        format_func=lambda value: pick("全部状态", "All Statuses") if value == "全部" else tracker_status_label(value),
        key="review_tracker_status_filter",
    )

    trackers = get_review_trackers(user_id, status=None if status_filter == "全部" else status_filter)
    if not trackers:
        st.info(pick("暂无复盘追踪项。先在行动中心把一个事项加入复盘。", "There are no follow-up trackers yet. Add one from the Action Center first."))
        return

    for tracker in trackers:
        _render_tracker_card(user_id, tracker)


def _render_tracker_card(user_id: int, tracker: dict[str, Any]) -> None:
    product_display = tracker.get("product_name") or tracker.get("parent_product_id") or tracker.get("source_product_id") or pick("未绑定产品", "Unassigned product")
    variant_display = tracker.get("variant_sku") or tracker.get("child_asin") or pick("未绑定变体", "Unassigned variant")
    baseline_pct = f"{float(tracker['baseline_pct']):.1f}%" if tracker.get("baseline_pct") is not None else "—"
    current_pct = f"{float(tracker['current_pct']):.1f}%" if tracker.get("current_pct") is not None else "—"
    status_label = tracker_status_label(str(tracker.get("result_status")))

    st.markdown(
        f"""
        <div class="product-block" style="padding:22px 24px;margin-bottom:18px;">
            <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:16px;flex-wrap:wrap;">
                <div>
                    <div style="font-size:18px;font-weight:700;color:#202020;">{tracker.get("tracker_title")}</div>
                    <div style="font-size:13px;color:#828282;margin-top:6px;">
                        {product_display} · {variant_display}
                    </div>
                </div>
                <div style="display:flex;gap:8px;flex-wrap:wrap;">
                    <span class="tag tag-topic">{tracker.get("tag_name") or "—"}</span>
                    <span class="tag tag-platform">{status_label}</span>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    metrics = st.columns(4)
    with metrics[0]:
        st.markdown(f"**{pick('初始问题占比', 'Baseline Issue Share')}**  \n{baseline_pct}")
    with metrics[1]:
        st.markdown(f"**{pick('当前占比', 'Current Share')}**  \n{current_pct}")
    with metrics[2]:
        st.markdown(f"**{pick('预计生效批次', 'Expected Effective Batch')}**  \n{tracker.get('effective_batch') or pick('未设置', 'Not set')}")
    with metrics[3]:
        st.markdown(f"**{pick('复盘评论范围', 'Follow-up Review Scope')}**  \n{tracker.get('review_scope') or pick('未设置', 'Not set')}")

    if tracker.get("improvement_action"):
        st.markdown(f"**{pick('改进动作', 'Improvement Action')}**  \n{tracker['improvement_action']}")
    if tracker.get("conclusion"):
        st.markdown(f"**{pick('复盘结论', 'Follow-up Conclusion')}**  \n{tracker['conclusion']}")

    form_key = f"review_tracker_form_{tracker['id']}"
    with st.form(form_key):
        input_cols = st.columns(3)
        with input_cols[0]:
            review_scope = st.text_input(
                pick("复盘评论范围", "Follow-up Review Scope"),
                value=tracker.get("review_scope") or "",
                key=f"review_scope_{tracker['id']}",
            )
        with input_cols[1]:
            current_pct_value = st.text_input(
                pick("当前占比（%）", "Current Share (%)"),
                value=str(tracker.get("current_pct") or ""),
                key=f"review_current_pct_{tracker['id']}",
            )
        with input_cols[2]:
            result_status = st.selectbox(
                pick("结论状态", "Conclusion Status"),
                REVIEW_TRACKER_STATUSES,
                index=REVIEW_TRACKER_STATUSES.index(tracker.get("result_status") or "pending"),
                format_func=lambda value: tracker_status_label(value),
                key=f"review_result_status_{tracker['id']}",
            )

        conclusion = st.text_area(
            pick("复盘结论", "Follow-up Conclusion"),
            value=tracker.get("conclusion") or "",
            key=f"review_conclusion_{tracker['id']}",
            height=90,
        )
        submitted = st.form_submit_button(pick("保存复盘结果", "Save Follow-up Result"), type="primary", use_container_width=True)
        if submitted:
            try:
                pct_value = float(current_pct_value) if str(current_pct_value).strip() else None
            except ValueError:
                st.error(pick("当前占比必须是数字，例如 9.0", "Current share must be a number, for example 9.0."))
                return

            update_review_tracker_result(
                user_id,
                int(tracker["id"]),
                {
                    "review_scope": review_scope.strip() or None,
                    "current_pct": pct_value,
                    "result_status": result_status,
                    "conclusion": conclusion.strip() or None,
                },
            )
            st.success(pick("复盘结果已保存", "Follow-up result saved"))
            st.rerun()
