"""今日工作台页面。"""

from __future__ import annotations

from datetime import date
from typing import Any

import streamlit as st

from review_analyzer.auth import get_current_user_id, get_current_username
from review_analyzer.i18n import get_lang, pick, role_label, t, tracker_status_label
from review_analyzer.page_shell import navigate
from review_analyzer.workspace_store import ROLES, get_workspace_summary

ROLE_BADGE_COLORS = {
    "运营": ("#fff0eb", "#ff682c"),
    "产研": ("#eef6ff", "#3498db"),
    "质检": ("#fdeaea", "#e74c3c"),
    "管理者": ("#e8f8f0", "#2ecc71"),
}

TRACKER_STATUS_LABELS = {
    "pending": "待复盘",
    "follow_up": "继续跟进",
    "improved": "已改善",
    "not_improved": "未改善",
    "done": "已完结",
}


def render_dashboard() -> None:
    user_id = get_current_user_id()
    if not user_id:
        st.warning(t("login_required"))
        return

    if "workspace_role" not in st.session_state:
        st.session_state["workspace_role"] = "运营"

    role = str(st.session_state.get("workspace_role") or "运营")
    if role not in ROLES:
        role = "运营"
        st.session_state["workspace_role"] = role

    summary = get_workspace_summary(user_id, role, get_lang())
    _render_workspace_header(summary)
    _render_role_switcher(role)
    _render_workspace_metrics(summary)
    _render_today_tasks(summary)
    _render_workspace_panels(summary)


def _render_workspace_header(summary: dict[str, Any]) -> None:
    username = get_current_username() or "Erika"
    today_text = date.today().strftime("%Y-%m-%d")
    role = summary["role"]
    badge_bg, badge_fg = ROLE_BADGE_COLORS.get(role, ("#fff0eb", "#ff682c"))

    st.markdown(
        f"""
        <div class="product-block" style="padding:30px 32px;margin-bottom:22px;background:linear-gradient(135deg,#ffffff 0%,#fff5f8 56%,#f5f2ff 100%);">
            <div style="display:flex;justify-content:space-between;gap:20px;align-items:flex-start;flex-wrap:wrap;">
                <div style="max-width:720px;">
                    <div style="display:inline-flex;align-items:center;padding:6px 12px;border-radius:999px;background:#fff1f5;color:#d94d72;font-size:12px;font-weight:700;margin-bottom:12px;">
                        {today_text} · {pick("今日工作台", "Today's Workspace")}
                    </div>
                    <div style="font-size:28px;font-weight:700;color:#25212a;font-family:'Montserrat',system-ui,sans-serif;letter-spacing:-0.02em;">
                        {username}{pick("，", ", ")}{summary['intro']['headline']}
                    </div>
                    <div style="font-size:14px;color:#6f6877;line-height:1.7;margin-top:10px;">
                        {summary['intro']['focus']}
                    </div>
                </div>
                <div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap;">
                    <span style="display:inline-flex;align-items:center;padding:8px 14px;border-radius:999px;background:{badge_bg};color:{badge_fg};font-size:13px;font-weight:700;">
                        {pick("当前视角：", "Current View: ")}{role_label(role)}
                    </span>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_role_switcher(current_role: str) -> None:
    st.markdown(f"### {pick('切换角色视角', 'Switch Role View')}")
    cols = st.columns(len(ROLES))
    for index, role in enumerate(ROLES):
        with cols[index]:
            if st.button(
                role_label(role),
                key=f"workspace_role_{role}",
                use_container_width=True,
                type="primary" if role == current_role else "secondary",
            ):
                st.session_state["workspace_role"] = role
                st.rerun()


def _render_workspace_metrics(summary: dict[str, Any]) -> None:
    metrics = summary["metrics"]
    card_items = [
        (pick("产品组", "Product Groups"), str(metrics["product_count"]), "◆"),
        (pick("高风险 SKU", "High-Risk SKUs"), str(metrics["risk_product_count"]), "▼"),
        (pick("未完结事项", "Open Items"), str(metrics["open_action_count"]), "◎"),
        (pick("待复盘", "Pending Follow-up"), str(metrics["open_tracker_count"]), "↺"),
        (pick("7天上传", "Uploads in 7 Days"), str(metrics["recent_upload_count"]), "▲"),
    ]

    cols = st.columns(5)
    for index, (label, value, icon) in enumerate(card_items):
        with cols[index]:
            st.markdown(
                f"""
                <div class="metric-card purple" style="padding:18px 20px;">
                    <div class="metric-icon">{icon}</div>
                    <div class="metric-val" style="font-size:24px;">{value}</div>
                    <div class="metric-label">{label}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )


def _render_today_tasks(summary: dict[str, Any]) -> None:
    st.markdown(f"### {pick('今日最该处理的 1-3 件事', 'Top 1-3 Things to Handle Today')}")
    tasks = summary.get("today_tasks", [])
    if not tasks:
        st.info(pick("当前还没有足够数据生成待办，先上传评论或创建行动事项。", "There is not enough data to generate tasks yet. Upload reviews or create an action item first."))
        return

    for index, task in enumerate(tasks):
        st.markdown(
            f"""
            <div class="product-block" style="padding:20px 22px;margin-bottom:14px;">
                <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:16px;flex-wrap:wrap;">
                    <div style="max-width:760px;">
                        <div style="font-size:12px;color:#828282;margin-bottom:8px;">{task['category']}</div>
                        <div style="font-size:18px;font-weight:700;color:#202020;">{task['title']}</div>
                        <div style="font-size:14px;color:#4d4d4d;line-height:1.7;margin-top:8px;">
                            {task['description']}
                        </div>
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if st.button(
            task["cta_label"],
            key=f"workspace_task_cta_{index}",
            type="primary",
            use_container_width=False,
        ):
            _navigate(task["page"], task.get("session_updates"))


def _render_workspace_panels(summary: dict[str, Any]) -> None:
    col_left, col_right = st.columns([1.15, 1], gap="large")
    with col_left:
        _render_risk_products(summary.get("risk_products", []))
        _render_recent_uploads(summary.get("recent_sessions", []))
    with col_right:
        _render_pending_trackers(summary.get("pending_trackers", []))
        _render_role_snapshot(summary.get("role_action_summary", []))


def _render_risk_products(items: list[dict[str, Any]]) -> None:
    st.markdown(f"### {pick('高风险 SKU', 'High-Risk SKUs')}")
    if not items:
        st.info(pick("当前没有明显高风险 SKU，适合继续用工作台做常规监控。", "There are no clearly high-risk SKUs right now. This is a good time to keep using the workspace for routine monitoring."))
        return

    for index, item in enumerate(items[:3]):
        st.markdown(
            f"""
            <div class="action-card danger" style="margin-top:0;margin-bottom:12px;">
                <div style="font-weight:700;color:#202020;">{item['product_name']}</div>
                <div style="font-size:13px;color:#4d4d4d;margin-top:6px;">
                    {pick("差评率", "Negative Rate")} {item['negative_rate']:.1f}% · {item['review_count']} {pick("条评论", "reviews")}
                </div>
                <div style="font-size:13px;color:#4d4d4d;margin-top:6px;">
                    {pick("核心问题：", "Core Issue: ")}{item['top_issue']} · {pick("待复盘", "Pending Follow-up")} {item['pending_review_count']} {pick("项", "items")}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if st.button(
            pick(f"查看 {item['product_name']}", f"View {item['product_name']}"),
            key=f"workspace_risk_product_{index}",
            use_container_width=True,
        ):
            _navigate("products", {"products_selected_parent_id": item["product_id"]})


def _render_pending_trackers(items: list[dict[str, Any]]) -> None:
    st.markdown(f"### {pick('待复盘事项', 'Pending Follow-up Items')}")
    if not items:
        st.info(pick("当前没有待复盘事项，团队动作相对干净。", "There are no pending follow-up items right now. The team action queue looks relatively clean."))
        return

    for index, item in enumerate(items[:3]):
        status_label = tracker_status_label(str(item.get("status")))
        baseline_text = "—" if item.get("baseline_pct") is None else f"{item['baseline_pct']:.1f}%"
        current_text = "—" if item.get("current_pct") is None else f"{item['current_pct']:.1f}%"
        st.markdown(
            f"""
            <div class="product-block" style="padding:18px 20px;margin-bottom:12px;">
                <div style="font-size:16px;font-weight:700;color:#202020;">{item['title']}</div>
                <div style="font-size:13px;color:#828282;margin-top:6px;">
                    {item['product_name']} · {item['tag_name']} · {status_label}
                </div>
                <div style="font-size:13px;color:#4d4d4d;margin-top:8px;">
                    {pick("初始占比", "Baseline Share")} {baseline_text} → {pick("当前占比", "Current Share")} {current_text}
                </div>
                <div style="font-size:13px;color:#4d4d4d;margin-top:6px;">
                    {pick("复盘范围：", "Follow-up Scope: ")}{item['review_scope']}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if st.button(
            pick(f"去更新复盘 {index + 1}", f"Update Follow-up {index + 1}"),
            key=f"workspace_tracker_{index}",
            use_container_width=True,
        ):
            _navigate("reviews")


def _render_recent_uploads(items: list[dict[str, Any]]) -> None:
    st.markdown(f"### {pick('最近上传', 'Recent Uploads')}")
    if not items:
        st.info(pick("最近还没有新的上传批次。", "There are no recent upload batches yet."))
        return

    for index, item in enumerate(items[:4]):
        st.markdown(
            f"""
            <div class="product-block" style="padding:16px 18px;margin-bottom:10px;">
                <div style="font-size:15px;font-weight:700;color:#202020;">{item['title']}</div>
                <div style="font-size:13px;color:#828282;margin-top:6px;">
                    {item['product_id']} · {item['workflow_purpose']} · {item['created_at']}
                </div>
                <div style="font-size:13px;color:#4d4d4d;margin-top:6px;">
                    {item['total_reviews']} {pick("条评论", "reviews")}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if st.button(
            pick(f"查看批次 {index + 1}", f"View Batch {index + 1}"),
            key=f"workspace_recent_session_{index}",
            use_container_width=True,
        ):
            _navigate(
                "analysis",
                {
                    "analysis_subpage": "results",
                    "view_session_id": item.get("session_id"),
                    "selected_product_id": item["product_id"],
                },
            )


def _render_role_snapshot(items: list[dict[str, Any]]) -> None:
    st.markdown(f"### {pick('团队事项概览', 'Team Item Overview')}")
    if not items:
        st.info(pick("当前没有未完结事项。", "There are no open items right now."))
        return

    cols = st.columns(len(items))
    for index, item in enumerate(items):
        with cols[index]:
            st.markdown(
                f"""
                <div class="metric-card yellow" style="padding:18px 16px;">
                    <div class="metric-val" style="font-size:22px;">{item['count']}</div>
                    <div class="metric-label">{item['role']}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    if st.button(pick("去行动中心统一推进", "Manage in Action Center"), key="workspace_go_actions", use_container_width=True):
        _navigate("actions")


def _navigate(page: str, session_updates: dict[str, Any] | None = None) -> None:
    navigate(page, session_updates)
