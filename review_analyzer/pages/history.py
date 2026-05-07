"""历史记录页面 — 按产品查看所有分析批次"""

import streamlit as st

from review_analyzer.auth import get_current_user_id
from review_analyzer.database import get_sessions, delete_session
from review_analyzer.exporter import export_to_xlsx


def render_history() -> None:
    user_id = get_current_user_id()
    if not user_id:
        st.warning("请先登录")
        return

    st.markdown("""
    <div style="margin-bottom:24px;">
        <div style="font-size:22px;font-weight:700;">历史记录</div>
        <div style="font-size:14px;color:#636E72;margin-top:2px;">按产品查看所有分析批次</div>
    </div>
    """, unsafe_allow_html=True)

    sessions = get_sessions(user_id)
    if not sessions:
        st.markdown("""
        <div style="text-align:center;padding:60px 0;color:#636E72;">
            <div style="font-size:48px;margin-bottom:16px;">🕐</div>
            <div style="font-size:18px;font-weight:600;margin-bottom:8px;">暂无历史记录</div>
            <div style="font-size:14px;">完成评论分析后，记录将自动保存在这里</div>
        </div>
        """, unsafe_allow_html=True)
        return

    # 按产品分组
    products: dict[str, list[dict]] = {}
    for s in sessions:
        pid = s["product_id"]
        if pid not in products:
            products[pid] = []
        products[pid].append(s)

    # 左右双栏布局
    col_sidebar, col_main = st.columns([1, 3])

    with col_sidebar:
        st.markdown(f"""
        <div style="font-size:13px;font-weight:600;color:#636E72;margin-bottom:12px;">
            产品列表（{len(products)}）
        </div>
        """, unsafe_allow_html=True)

        search_sku = st.text_input("搜索", placeholder="搜索 SKU...",
                                    label_visibility="collapsed", key="hist_search")

        if "hist_selected_product" not in st.session_state:
            st.session_state["hist_selected_product"] = list(products.keys())[0] if products else None

        for pid in products.keys():
            if search_sku and search_sku.lower() not in pid.lower():
                continue
            is_active = st.session_state.get("hist_selected_product") == pid
            btn_type = "primary" if is_active else "secondary"
            if st.button(f"**{pid}**", key=f"hist_sku_{pid}", use_container_width=True, type=btn_type):
                st.session_state["hist_selected_product"] = pid
                st.rerun()

    with col_main:
        selected_pid = st.session_state.get("hist_selected_product")
        if not selected_pid or selected_pid not in products:
            st.info("请从左侧选择一个产品")
            return

        product_sessions = products[selected_pid]
        st.markdown(f"""
        <div style="font-size:16px;font-weight:600;margin-bottom:4px;">{selected_pid}</div>
        <div style="font-size:13px;color:#636E72;margin-bottom:16px;">共 {len(product_sessions)} 个批次</div>
        """, unsafe_allow_html=True)

        for s in product_sessions:
            total = s.get("total_reviews", 0)
            pos = s.get("positive_count", 0)
            pos_rate = f"{pos / total * 100:.1f}%" if total > 0 else "—"
            title = s.get("custom_title") or s.get("auto_title") or f"{s['version']}"
            date_range = ""
            if s.get("date_range_start") and s.get("date_range_end"):
                date_range = f"{s['date_range_start']} ~ {s['date_range_end']}"

            col_info, col_actions = st.columns([3, 2.5])
            with col_info:
                st.markdown(f"**{title}**")
                st.markdown(f"<span style='font-size:13px;color:#636E72;'>{date_range or '—'} · {total:,} 条评论</span>",
                            unsafe_allow_html=True)
            with col_actions:
                btn_col1, btn_col2, btn_col3, btn_col4 = st.columns(4)
                with btn_col1:
                    st.markdown(f'<span class="tag tag-pos">{pos_rate}</span>', unsafe_allow_html=True)
                with btn_col2:
                    if st.button("查看结果", key=f"hist_view_{s['id']}"):
                        st.session_state["view_session_id"] = s["id"]
                        st.session_state["current_page"] = "results"
                        st.rerun()
                with btn_col3:
                    try:
                        xlsx_bytes, xlsx_fn = export_to_xlsx(s["id"], user_id)
                        st.download_button(
                            "📥 导出",
                            data=xlsx_bytes,
                            file_name=xlsx_fn,
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            key=f"hist_export_{s['id']}",
                        )
                    except Exception:
                        st.button("📥 导出", key=f"hist_export_{s['id']}", disabled=True)
                with btn_col4:
                    if st.button("🗑️", key=f"hist_del_{s['id']}"):
                        delete_session(user_id, s["id"])
                        st.rerun()

            st.markdown("<hr style='border:none;border-top:1px solid #E8EAF0;margin:8px 0;'>",
                        unsafe_allow_html=True)
