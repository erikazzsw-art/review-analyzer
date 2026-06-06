from __future__ import annotations

import streamlit as st

from review_analyzer.i18n import pick
from review_analyzer.page_shell import render_page_header
from review_analyzer.pages.compare import render_compare
from review_analyzer.pages.results import render_history, render_results


def _subpages() -> dict[str, str]:
    return {
        "results": pick("分析结果", "Results"),
        "compare": pick("对比分析", "Compare"),
        "history": pick("历史记录", "History"),
    }


def render_analysis_hub() -> None:
    current_subpage = _normalize_subpage(st.session_state.get("analysis_subpage"))
    render_page_header(
        pick("评论分析", "Review Analysis"),
        pick("集中查看分析结果、跨对象对比和历史批次回看。", "View results, compare across objects, and revisit historical batches in one place."),
        path=pick("核心工作流 / 评论分析", "Core Workflow / Review Analysis"),
    )
    _render_subpage_switcher(current_subpage)

    if current_subpage == "compare":
        render_compare()
        return
    if current_subpage == "history":
        render_history()
        return
    render_results()


def _render_subpage_switcher(current_subpage: str) -> None:
    subpages = _subpages()
    cols = st.columns(len(subpages))
    for index, (subpage_id, label) in enumerate(subpages.items()):
        with cols[index]:
            if st.button(
                label,
                key=f"analysis_hub_switch_{subpage_id}",
                type="primary" if current_subpage == subpage_id else "secondary",
                use_container_width=True,
            ):
                st.session_state["current_page"] = "analysis"
                st.session_state["analysis_subpage"] = subpage_id
                st.rerun()
    st.markdown("<br>", unsafe_allow_html=True)


def _normalize_subpage(raw_value: object) -> str:
    value = str(raw_value or "results").strip()
    if value not in _subpages():
        value = "results"
    st.session_state["analysis_subpage"] = value
    return value
