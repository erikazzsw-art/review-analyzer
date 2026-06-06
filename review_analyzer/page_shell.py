from __future__ import annotations

from typing import Any

import streamlit as st

from review_analyzer.i18n import t


def navigate(page: str, session_updates: dict[str, Any] | None = None) -> None:
    for key, value in (session_updates or {}).items():
        if value is not None:
            st.session_state[key] = value
    legacy_analysis_map = {
        "results": "results",
        "compare": "compare",
        "history": "history",
    }
    if page in legacy_analysis_map:
        st.session_state["current_page"] = "analysis"
        st.session_state["analysis_subpage"] = legacy_analysis_map[page]
    elif page == "features":
        st.session_state["current_page"] = "analysis"
        st.session_state["analysis_subpage"] = "results"
    else:
        st.session_state["current_page"] = page
    st.rerun()


def render_page_header(
    title: str,
    description: str,
    *,
    path: str | None = None,
) -> None:
    path_html = ""
    if path:
        path_html = (
            "<div style='display:inline-flex;align-items:center;padding:6px 12px;border-radius:999px;"
            "background:#fff1f5;color:#d94d72;font-size:12px;font-weight:700;margin-bottom:12px;'>"
            f"{path}</div>"
        )

    st.markdown(
        f"""
        <div class="product-block" style="padding:24px 26px;margin-bottom:18px;background:linear-gradient(135deg,#ffffff 0%,#fff6f7 58%,#f6f2ff 100%);">
            {path_html}
            <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:18px;flex-wrap:wrap;">
                <div style="max-width:760px;">
                    <div style="font-size:24px;font-weight:700;color:#25212a;font-family:'Montserrat',system-ui,sans-serif;letter-spacing:-0.02em;">
                        {title}
                    </div>
                    <div style="font-size:14px;color:#6f6877;margin-top:8px;line-height:1.7;">
                        {description}
                    </div>
                </div>
                <div style="font-size:12px;color:#9b94a5;padding-top:4px;">
                    {t("continue_reading")}
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
