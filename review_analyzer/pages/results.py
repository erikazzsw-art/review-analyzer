"""评论分析结果与历史记录页面。"""

from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, timedelta
from typing import Any

import pandas as pd
import streamlit as st

from review_analyzer.analysis_export import export_result_module_to_xlsx
from review_analyzer.auth import get_current_user_id
from review_analyzer.database import delete_session, get_comments, get_session_by_id, get_sessions
from review_analyzer.exporter import export_to_xlsx
from review_analyzer.i18n import pick
from review_analyzer.insight_engine import build_results_insights
from review_analyzer.page_shell import render_page_header
from review_analyzer.translation import translate_result_module
from review_analyzer.workflow_prompts import get_result_focus_hint, get_workflow_purpose_label


RESULT_MODULES = [
    ("consumer_profile", {"zh": "消费者画像", "en": "Consumer Profile"}),
    ("user_experience", {"zh": "用户体验", "en": "User Experience"}),
    ("purchase_motives", {"zh": "购买动机", "en": "Purchase Motives"}),
    ("unmet_needs", {"zh": "未被满足的需求", "en": "Unmet Needs"}),
    ("recommendations", {"zh": "综合建议", "en": "Recommendations"}),
]

TIME_MODE_OPTIONS = {
    "all": {"zh": "全部时间", "en": "All Time"},
    "30": {"zh": "30天", "en": "30 Days"},
    "60": {"zh": "60天", "en": "60 Days"},
    "90": {"zh": "90天", "en": "90 Days"},
    "custom": {"zh": "自定义", "en": "Custom"},
}


def _result_module_title(module_key: str) -> str:
    for key, labels in RESULT_MODULES:
        if key == module_key:
            return pick(labels["zh"], labels["en"])
    return module_key


def render_results() -> None:
    user_id = get_current_user_id()
    if not user_id:
        st.warning(pick("请先登录", "Please log in first."))
        return

    session = _resolve_active_session(user_id)
    if not session:
        _render_empty_results()
        return

    raw_comments = get_comments(user_id, session_id=int(session["id"]))
    if not raw_comments:
        st.info(pick("当前批次还没有可展示的评论数据。", "There is no review data to display for this batch yet."))
        return

    filtered_comments, time_context = _filter_comments_for_results(user_id, session, raw_comments)
    context = {
        "product_id": str(session.get("product_id") or ""),
        "version": str(session.get("version") or "V1"),
        "time_label": time_context["label"],
        "workflow_purpose": str(session.get("workflow_purpose") or ""),
    }
    insights = build_results_insights(user_id, filtered_comments, context)

    description = (
        f"{context['product_id']} · {context['version']} · {len(filtered_comments)} {pick('条评论', 'reviews')} · "
        f"{time_context['label']}"
    )
    render_page_header(
        pick("分析结果", "Results"),
        description,
        path=pick("评论分析 / 分析结果", "Review Analysis / Results"),
    )

    focus_hint = get_result_focus_hint(context["workflow_purpose"])
    if context["workflow_purpose"] and focus_hint:
        st.info(
            pick("当前工作目的：", "Current workflow purpose: ")
            + f"{get_workflow_purpose_label(context['workflow_purpose'])}. {focus_hint}"
        )

    _render_result_export(user_id, int(session["id"]))
    _render_results_controls(user_id, session)
    _render_consumer_profile_module(user_id, insights["consumer_profile"], context)
    _render_user_experience_module(user_id, insights["user_experience"], context)
    _render_standard_module(
        user_id,
        "purchase_motives",
        _result_module_title("purchase_motives"),
        insights["purchase_motives"],
        context,
    )
    _render_standard_module(
        user_id,
        "unmet_needs",
        _result_module_title("unmet_needs"),
        insights["unmet_needs"],
        context,
    )
    _render_standard_module(
        user_id,
        "recommendations",
        _result_module_title("recommendations"),
        insights["recommendations"],
        context,
    )
    _render_raw_reviews_section(filtered_comments)


def render_history() -> None:
    user_id = get_current_user_id()
    if not user_id:
        st.warning(pick("请先登录", "Please log in first."))
        return

    render_page_header(
        pick("历史记录", "History"),
        pick("回看历史批次、导出结果或切换到某次分析继续阅读。", "Review past batches, export results, or reopen a previous analysis."),
        path=pick("评论分析 / 历史记录", "Review Analysis / History"),
    )

    sessions = get_sessions(user_id)
    if not sessions:
        st.info(pick("还没有历史分析批次。先去上传一批评论。", "There are no historical analysis batches yet. Upload a batch of reviews first."))
        return

    grouped_sessions: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for session in sessions:
        grouped_sessions[str(session.get("product_id") or pick("未命名产品", "Untitled Product"))].append(session)

    search = st.text_input(pick("搜索产品编号", "Search Product ID"), placeholder=pick("输入 SKU 或产品编号", "Enter a SKU or product ID"))
    for product_id, product_sessions in grouped_sessions.items():
        if search and search.lower() not in product_id.lower():
            continue
        st.markdown(f"### {product_id}")
        for session in product_sessions:
            date_range = _format_session_date_range(session)
            total_reviews = int(session.get("total_reviews") or 0)
            title = session.get("custom_title") or session.get("auto_title") or str(session.get("version") or "V1")
            st.markdown(
                f"""
                <div class="product-block" style="padding:16px 18px;margin-bottom:10px;">
                    <div style="font-size:16px;font-weight:700;color:#25212a;">{title}</div>
                    <div style="font-size:13px;color:#6f6877;margin-top:6px;">
                        {date_range} · {total_reviews} {pick('条评论', 'reviews')}
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            action_cols = st.columns([1.2, 1, 1, 1.4])
            with action_cols[0]:
                if st.button(pick("查看结果", "View Results"), key=f"history_view_{session['id']}", use_container_width=True):
                    st.session_state["view_session_id"] = int(session["id"])
                    st.session_state["current_page"] = "analysis"
                    st.session_state["analysis_subpage"] = "results"
                    st.rerun()
            with action_cols[1]:
                try:
                    xlsx_bytes, xlsx_name = export_to_xlsx(int(session["id"]), user_id)
                    st.download_button(
                        pick("导出", "Export"),
                        data=xlsx_bytes,
                        file_name=xlsx_name,
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        key=f"history_export_{session['id']}",
                        use_container_width=True,
                    )
                except ValueError:
                    st.button(pick("导出", "Export"), key=f"history_export_disabled_{session['id']}", disabled=True, use_container_width=True)
            with action_cols[2]:
                if st.button(pick("删除", "Delete"), key=f"history_delete_{session['id']}", use_container_width=True):
                    delete_session(user_id, int(session["id"]))
                    if st.session_state.get("view_session_id") == int(session["id"]):
                        st.session_state.pop("view_session_id", None)
                    st.rerun()
            with action_cols[3]:
                st.caption(f"{pick('版本', 'Version')}: {session.get('version') or 'V1'}")


def _resolve_active_session(user_id: int) -> dict[str, Any] | None:
    view_session_id = st.session_state.get("view_session_id")
    if view_session_id:
        session = get_session_by_id(user_id, int(view_session_id))
        if session:
            return session

    sessions = get_sessions(user_id)
    if not sessions:
        return None

    product_map: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for session in sessions:
        product_map[str(session.get("product_id") or pick("未命名产品", "Untitled Product"))].append(session)

    selected_product = st.selectbox(
        pick("选择产品", "Select Product"),
        list(product_map.keys()),
        key="results_selected_product",
    )
    selected_sessions = product_map[selected_product]
    selected_session_id = st.selectbox(
        pick("选择批次", "Select Batch"),
        [int(item["id"]) for item in selected_sessions],
        format_func=lambda value: _format_session_option(next(item for item in selected_sessions if int(item["id"]) == int(value))),
        key="results_selected_session",
    )
    session = get_session_by_id(user_id, int(selected_session_id))
    if session:
        st.session_state["view_session_id"] = int(selected_session_id)
    return session


def _render_empty_results() -> None:
    render_page_header(
        pick("分析结果", "Results"),
        pick("还没有可查看的分析结果，先去上传一批评论。", "There are no analysis results to view yet. Upload a batch of reviews first."),
        path=pick("评论分析 / 分析结果", "Review Analysis / Results"),
    )
    st.info(pick("暂无分析结果。", "No analysis results yet."))


def _render_result_export(user_id: int, session_id: int) -> None:
    export_cols = st.columns([5, 1.2])
    with export_cols[1]:
        try:
            xlsx_bytes, xlsx_name = export_to_xlsx(session_id, user_id)
            st.download_button(
                pick("下载整份结果", "Download Full Results"),
                data=xlsx_bytes,
                file_name=xlsx_name,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
                key=f"results_export_full_{session_id}",
            )
        except ValueError:
            st.button(pick("下载整份结果", "Download Full Results"), disabled=True, use_container_width=True, key=f"results_export_disabled_{session_id}")


def _render_results_controls(user_id: int, session: dict[str, Any]) -> None:
    current_session_id = int(session["id"])
    sessions = get_sessions(user_id, product_id=str(session.get("product_id") or ""))
    if len(sessions) <= 1:
        return
    st.caption(pick("可切换同一产品的其他历史批次查看结果。", "You can switch to other historical batches for the same product here."))
    selected_session_id = st.selectbox(
        pick("当前查看批次", "Current Batch"),
        [int(item["id"]) for item in sessions],
        index=next((index for index, item in enumerate(sessions) if int(item["id"]) == current_session_id), 0),
        format_func=lambda value: _format_session_option(next(item for item in sessions if int(item["id"]) == int(value))),
        key="results_control_session_switch",
    )
    if int(selected_session_id) != current_session_id:
        st.session_state["view_session_id"] = int(selected_session_id)
        st.rerun()


def _filter_comments_for_results(
    user_id: int,
    session: dict[str, Any],
    session_comments: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    date_values = [_parse_comment_date(comment.get("date")) for comment in session_comments]
    valid_dates = [value for value in date_values if value is not None]
    default_start = _parse_comment_date(session.get("date_range_start")) or (min(valid_dates) if valid_dates else date.today())
    default_end = _parse_comment_date(session.get("date_range_end")) or (max(valid_dates) if valid_dates else date.today())

    mode = st.selectbox(
        pick("用户体验时间周期", "User Experience Time Range"),
        list(TIME_MODE_OPTIONS.keys()),
        index=4,
        format_func=lambda value: pick(TIME_MODE_OPTIONS[value]["zh"], TIME_MODE_OPTIONS[value]["en"]),
        key=f"results_time_mode_{session['id']}",
    )

    all_product_comments = get_comments(user_id, product_id=str(session.get("product_id") or ""))
    all_dates = [_parse_comment_date(comment.get("date")) for comment in all_product_comments]
    all_valid_dates = [value for value in all_dates if value is not None]
    latest_date = max(all_valid_dates) if all_valid_dates else default_end

    if mode == "all":
        return _filter_by_date_range(all_product_comments, min(all_valid_dates, default=default_start), latest_date), {
            "label": pick("全部时间", "All Time"),
            "start": min(all_valid_dates, default=default_start),
            "end": latest_date,
        }
    if mode in {"30", "60", "90"}:
        days = int(mode)
        start = latest_date - timedelta(days=days - 1)
        return _filter_by_date_range(all_product_comments, start, latest_date), {
            "label": f"{start} ~ {latest_date}",
            "start": start,
            "end": latest_date,
        }

    col1, col2 = st.columns(2)
    with col1:
        start = st.date_input(pick("开始日期", "Start Date"), value=default_start, key=f"results_custom_start_{session['id']}")
    with col2:
        end = st.date_input(pick("结束日期", "End Date"), value=default_end, key=f"results_custom_end_{session['id']}")
    if start > end:
        st.warning(pick("开始日期不能晚于结束日期，已自动回退到当前批次。", "The start date cannot be later than the end date. Reverted to the current batch."))
        return session_comments, {"label": _format_session_date_range(session), "start": default_start, "end": default_end}
    filtered = _filter_by_date_range(all_product_comments, start, end)
    if not filtered:
        st.warning(pick("所选时间范围内没有评论，已回退到当前批次。", "No reviews were found in the selected time range. Reverted to the current batch."))
        return session_comments, {"label": _format_session_date_range(session), "start": default_start, "end": default_end}
    return filtered, {"label": f"{start} ~ {end}", "start": start, "end": end}


def _render_consumer_profile_module(
    user_id: int,
    payload: dict[str, Any],
    context: dict[str, Any],
) -> None:
    display_payload = _resolve_display_payload(user_id, "consumer_profile", payload, context)
    _render_module_header(user_id, "consumer_profile", _result_module_title("consumer_profile"), display_payload, context)
    st.caption(display_payload.get("summary", ""))
    rows = display_payload.get("rows", [])
    if rows:
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    evidence = display_payload.get("evidence", [])
    if evidence:
        with st.expander(pick("查看代表性评论证据", "View Representative Review Evidence"), expanded=False):
            for quote in evidence:
                st.write(f"- {quote}")


def _render_user_experience_module(
    user_id: int,
    payload: dict[str, Any],
    context: dict[str, Any],
) -> None:
    display_payload = _resolve_display_payload(user_id, "user_experience", payload, context)
    _render_module_header(user_id, "user_experience", _result_module_title("user_experience"), display_payload, context)
    st.caption(display_payload.get("summary", ""))
    col_positive, col_negative = st.columns(2, gap="large")
    with col_positive:
        st.markdown(f"#### {pick('正向反馈', 'Positive Feedback')}")
        positive_rows = display_payload.get("positive", [])
        if positive_rows:
            st.dataframe(pd.DataFrame(positive_rows), use_container_width=True, hide_index=True)
        else:
            st.info(pick("暂无稳定正向反馈。", "No stable positive feedback yet."))
    with col_negative:
        st.markdown(f"#### {pick('负向反馈', 'Negative Feedback')}")
        negative_rows = display_payload.get("negative", [])
        if negative_rows:
            st.dataframe(pd.DataFrame(negative_rows), use_container_width=True, hide_index=True)
        else:
            st.info(pick("暂无稳定负向反馈。", "No stable negative feedback yet."))


def _render_standard_module(
    user_id: int,
    module_key: str,
    title: str,
    payload: dict[str, Any],
    context: dict[str, Any],
) -> None:
    display_payload = _resolve_display_payload(user_id, module_key, payload, context)
    _render_module_header(user_id, module_key, title, display_payload, context)
    st.caption(display_payload.get("summary", ""))
    rows = display_payload.get("rows", [])
    if rows:
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    else:
        st.info(pick("暂无可展示内容。", "Nothing to display yet."))


def _render_module_header(
    user_id: int,
    module_key: str,
    title: str,
    payload: dict[str, Any],
    context: dict[str, Any],
) -> None:
    cols = st.columns([6, 1.1, 1.1])
    with cols[0]:
        st.markdown(f"## {title}")
    with cols[1]:
        button_label = pick("查看英文", "View English") if _module_language(module_key) == "zh" else pick("切换中文", "View Chinese")
        if st.button(button_label, key=f"results_translate_{module_key}", use_container_width=True):
            st.session_state[_module_language_key(module_key)] = "en" if _module_language(module_key) == "zh" else "zh"
            st.rerun()
    with cols[2]:
        try:
            xlsx_bytes, xlsx_name = export_result_module_to_xlsx(title, payload, context)
            st.download_button(
                pick("下载", "Download"),
                data=xlsx_bytes,
                file_name=xlsx_name,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key=f"results_download_{module_key}",
                use_container_width=True,
            )
        except ValueError:
            st.button(pick("下载", "Download"), disabled=True, use_container_width=True, key=f"results_download_disabled_{module_key}")


def _render_raw_reviews_section(comments: list[dict[str, Any]]) -> None:
    st.markdown(f"## {pick('评论原文', 'Raw Reviews')}")
    if not comments:
        st.info(pick("当前范围内没有评论原文。", "There are no raw reviews in the current range."))
        return

    table_rows = []
    for comment in comments:
        content = str(comment.get("content") or "").strip()
        table_rows.append(
            {
                pick("日期", "Date"): str(comment.get("date") or ""),
                pick("评分", "Rating"): str(comment.get("rating") or ""),
                pick("情感", "Sentiment"): str(comment.get("sentiment") or ""),
                pick("分类", "Category"): str(comment.get("category") or ""),
                pick("正向标签", "Highlight Tags"): str(comment.get("highlight_tag") or ""),
                pick("负向标签", "Issue Tags"): str(comment.get("issue_tag") or ""),
                pick("评论摘要", "Review Summary"): content[:120] + ("..." if len(content) > 120 else ""),
            }
        )
    st.dataframe(pd.DataFrame(table_rows), use_container_width=True, hide_index=True)

    for index, comment in enumerate(comments[:30], 1):
        with st.expander(
            f"{pick('评论', 'Review')} {index}｜{comment.get('date') or pick('无日期', 'No Date')}｜{comment.get('sentiment') or pick('未分析', 'Not Analyzed')}",
            expanded=False,
        ):
            st.write(str(comment.get("content") or ""))
            detail_rows = [
                (pick("评分", "Rating"), comment.get("rating") or pick("无评分", "No Rating")),
                (pick("情感", "Sentiment"), comment.get("sentiment") or "--"),
                (pick("内容情感", "Content Sentiment"), comment.get("content_sentiment") or "--"),
                (pick("分类", "Category"), comment.get("category") or "--"),
                (pick("优先级", "Priority"), comment.get("priority") or "--"),
                (pick("正向反馈", "Positive Feedback"), comment.get("highlight_tag") or "--"),
                (pick("负向反馈", "Negative Feedback"), comment.get("issue_tag") or "--"),
                (pick("分析原因", "Reason"), comment.get("reason") or "--"),
                (pick("改进建议", "Improvement Suggestion"), comment.get("improvement") or "--"),
            ]
            st.dataframe(pd.DataFrame(detail_rows, columns=[pick("字段", "Field"), pick("内容", "Content")]), use_container_width=True, hide_index=True)


def _resolve_display_payload(
    user_id: int,
    module_key: str,
    payload: dict[str, Any],
    context: dict[str, Any],
) -> dict[str, Any]:
    if _module_language(module_key) != "zh":
        return payload
    cache_key = (
        f"translated_module_payload_{module_key}_"
        f"{context.get('product_id', '--')}_{context.get('version', '--')}_{context.get('time_label', '--')}"
    )
    cached_payload = st.session_state.get(cache_key)
    if cached_payload is None:
        cached_payload = translate_result_module(user_id, payload, "zh")
        st.session_state[cache_key] = cached_payload
    return cached_payload


def _module_language(module_key: str) -> str:
    return str(st.session_state.get(_module_language_key(module_key), "en"))


def _module_language_key(module_key: str) -> str:
    return f"results_module_lang_{module_key}"


def _parse_comment_date(value: Any) -> date | None:
    if value in (None, ""):
        return None
    text = str(value).strip()
    if not text:
        return None
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%m/%d/%Y", "%d/%m/%Y", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


def _filter_by_date_range(comments: list[dict[str, Any]], start: date, end: date) -> list[dict[str, Any]]:
    filtered = []
    for comment in comments:
        comment_date = _parse_comment_date(comment.get("date"))
        if comment_date is None:
            continue
        if start <= comment_date <= end:
            filtered.append(comment)
    return filtered


def _format_session_option(session: dict[str, Any]) -> str:
    title = session.get("custom_title") or session.get("auto_title") or str(session.get("version") or "V1")
    return f"{title} · {_format_session_date_range(session)}"


def _format_session_date_range(session: dict[str, Any]) -> str:
    start = str(session.get("date_range_start") or "")
    end = str(session.get("date_range_end") or "")
    if start and end:
        return f"{start} ~ {end}"
    return pick("当前批次", "Current Batch")
