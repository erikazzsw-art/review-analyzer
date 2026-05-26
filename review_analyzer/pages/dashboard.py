"""仪表盘页面 — 按产品维度展示分析全貌"""

from __future__ import annotations

import streamlit as st
import plotly.graph_objects as go

from review_analyzer.auth import get_current_user_id
from review_analyzer.database import get_sessions, get_comments, get_product_stats_deduped, get_comments_deduped


def _get_products(user_id: int) -> list[dict]:
    """获取用户所有产品及其汇总数据（按 content_hash 去重统计）"""
    sessions = get_sessions(user_id)
    products: dict[str, dict] = {}
    for s in sessions:
        pid = s["product_id"]
        if pid not in products:
            stats = get_product_stats_deduped(user_id, pid)
            products[pid] = {
                "product_id": pid,
                "name": "",
                "platform": "",
                "category": s.get("category", ""),
                "sessions": [],
                "total_reviews": stats["total_reviews"],
                "positive_count": stats["positive_count"],
                "negative_count": stats["negative_count"],
                "unrecognizable_count": stats.get("unrecognizable_count", 0),
            }
        products[pid]["sessions"].append(s)
    return list(products.values())


def _render_metric_cards(product: dict) -> None:
    """渲染4个指标卡片"""
    total = product["total_reviews"]
    unrec = product.get("unrecognizable_count", 0)
    valid = total - unrec
    pos = product["positive_count"]
    neg = product["negative_count"]
    pos_rate = f"{pos / valid * 100:.1f}%" if valid > 0 else "0%"
    neg_rate = f"{neg / valid * 100:.1f}%" if valid > 0 else "0%"

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        invalid_note = f"<div style='font-size:11px;color:#e74c3c;margin-top:2px;'>无效 {unrec} 条</div>" if unrec > 0 else ""
        st.markdown(f"""
        <div class="metric-card purple">
            <div class="metric-icon">◆</div>
            <div class="metric-val">{valid:,}</div>
            <div class="metric-label">有效评论</div>
            {invalid_note}
        </div>
        """, unsafe_allow_html=True)
    with col2:
        st.markdown(f"""
        <div class="metric-card green">
            <div class="metric-icon">▲</div>
            <div class="metric-val">{pos_rate}</div>
            <div class="metric-label">正面率</div>
        </div>
        """, unsafe_allow_html=True)
    with col3:
        st.markdown(f"""
        <div class="metric-card red">
            <div class="metric-icon">▼</div>
            <div class="metric-val">{neg_rate}</div>
            <div class="metric-label">负面率</div>
        </div>
        """, unsafe_allow_html=True)
    with col4:
        st.markdown(f"""
        <div class="metric-card yellow">
            <div class="metric-icon">★</div>
            <div class="metric-val">—</div>
            <div class="metric-label">平均评分</div>
        </div>
        """, unsafe_allow_html=True)


def _render_charts(product: dict, idx: int) -> None:
    """渲染情感趋势和评分分布图表"""
    sessions = sorted(product["sessions"], key=lambda s: s["created_at"])

    col1, col2 = st.columns([1.2, 0.8])
    with col1:
        if len(sessions) > 0:
            labels = []
            pos_rates = []
            neg_rates = []
            for s in sessions:
                label = s.get("auto_title") or f"{s['version']} · {s.get('date_range_start', '')}"
                labels.append(label[:20])
                total = s.get("total_reviews", 0)
                if total > 0:
                    pos_rates.append(s.get("positive_count", 0) / total * 100)
                    neg_rates.append(s.get("negative_count", 0) / total * 100)
                else:
                    pos_rates.append(0)
                    neg_rates.append(0)

            fig = go.Figure()
            fig.add_trace(go.Bar(name="正面率", x=labels, y=pos_rates,
                                 marker_color="#2ecc71", marker_cornerradius=8))
            fig.add_trace(go.Bar(name="负面率", x=labels, y=neg_rates,
                                 marker_color="#e74c3c", marker_cornerradius=8))
            fig.update_layout(
                title="情感趋势（按批次）",
                barmode="group",
                height=280,
                margin=dict(l=20, r=20, t=40, b=20),
                legend=dict(orientation="h", yanchor="bottom", y=-0.2),
                yaxis=dict(range=[0, 100], ticksuffix="%"),
                plot_bgcolor="white",
                paper_bgcolor="white",
                font=dict(family="Inter, system-ui, sans-serif"),
            )
            st.plotly_chart(fig, use_container_width=True, key=f"trend_{idx}")
        else:
            st.info("暂无批次数据")

    with col2:
        user_id = get_current_user_id()
        if user_id and product["sessions"]:
            comments = get_comments_deduped(user_id, product["product_id"])
            ratings = [c["rating"] for c in comments if c.get("rating")]
            if ratings:
                from collections import Counter
                rating_counts = Counter(ratings)
                stars = ["1★", "2★", "3★", "4★", "5★"]
                counts = [rating_counts.get(i, 0) for i in range(1, 6)]
                colors = ["#e74c3c", "#f39c12", "#3498db", "#816729", "#2ecc71"]

                fig = go.Figure(go.Bar(
                    x=stars, y=counts,
                    marker_color=colors,
                    marker_cornerradius=8,
                ))
                fig.update_layout(
                    title="评分分布",
                    height=280,
                    margin=dict(l=20, r=20, t=40, b=20),
                    plot_bgcolor="white",
                    paper_bgcolor="white",
                    font=dict(family="Inter, system-ui, sans-serif"),
                )
                st.plotly_chart(fig, use_container_width=True, key=f"dist_{idx}")
            else:
                st.info("暂无评分数据")
        else:
            st.info("暂无数据")


def _render_batch_table(product: dict) -> None:
    """渲染批次记录表格"""
    sessions = sorted(product["sessions"], key=lambda s: s["created_at"], reverse=True)
    if not sessions:
        return

    st.markdown("**批次记录**")
    for s in sessions:
        total = s.get("total_reviews", 0)
        pos = s.get("positive_count", 0)
        pos_rate = f"{pos / total * 100:.1f}%" if total > 0 else "—"
        title = s.get("custom_title") or s.get("auto_title") or f"{s['version']}"
        date_range = ""
        if s.get("date_range_start") and s.get("date_range_end"):
            date_range = f"{s['date_range_start']} ~ {s['date_range_end']}"

        col1, col2, col3, col4, col5 = st.columns([2, 2, 1, 1, 1])
        with col1:
            st.write(f"**{title}**")
        with col2:
            st.write(date_range or "—")
        with col3:
            st.write(f"{total:,} 条")
        with col4:
            st.markdown(f'<span class="tag tag-pos">{pos_rate}</span>', unsafe_allow_html=True)
        with col5:
            if st.button("查看结果", key=f"view_{s['id']}"):
                st.session_state["current_page"] = "results"
                st.session_state["view_session_id"] = s["id"]
                st.rerun()


def _render_action_card(product: dict) -> None:
    """渲染行动建议卡"""
    total = product["total_reviews"]
    unrec = product.get("unrecognizable_count", 0)
    valid = total - unrec
    if valid == 0:
        return

    pos_rate = product["positive_count"] / valid * 100
    neg_rate = product["negative_count"] / valid * 100

    is_danger = neg_rate > 25 or pos_rate < 55
    card_class = "action-card danger" if is_danger else "action-card"
    title = "行动建议（需关注）" if is_danger else "行动建议"

    suggestions = []
    if pos_rate >= 70:
        suggestions.append(f"产品整体评价优秀，正面率 {pos_rate:.1f}%，建议持续监控并扩大宣传")
    elif pos_rate < 55:
        suggestions.append(f"正面率仅 {pos_rate:.1f}%，产品口碑正在恶化，需立即排查原因")
    if neg_rate > 25:
        suggestions.append(f"负面率 {neg_rate:.1f}% 超过警戒线，建议立即排查核心问题并优化产品")

    if not suggestions:
        suggestions.append("产品表现稳定，建议基于亮点优化 listing 文案")

    items_html = ""
    for text in suggestions:
        items_html += f'<div style="font-size:14px;padding:8px 0;border-bottom:1px solid #e8e8e8;">• {text}</div>'

    st.markdown(f"""
    <div class="{card_class}">
        <h4 style="font-size:15px;font-weight:600;margin-bottom:12px;">{title}</h4>
        {items_html}
    </div>
    """, unsafe_allow_html=True)


def render_dashboard() -> None:
    user_id = get_current_user_id()
    if not user_id:
        st.warning("请先登录")
        return

    # 页头
    st.markdown("""
    <style>
    .product-title-btn + div button {
        background: none !important;
        border: none !important;
        box-shadow: none !important;
        padding: 0 !important;
        font-size: 18px !important;
        font-weight: 700 !important;
        color: #6C5CE7 !important;
        text-align: left !important;
        justify-content: flex-start !important;
    }
    .product-title-btn + div button:hover {
        color: #5a4bd1 !important;
        text-decoration: underline !important;
        background: none !important;
    }
    </style>
    <div style="margin-bottom:32px;">
        <div style="font-size:28px;font-weight:700;color:#202020;font-family:'Montserrat',system-ui,sans-serif;letter-spacing:-0.02em;">仪表盘</div>
        <div style="font-size:14px;color:#4d4d4d;margin-top:6px;">按产品维度查看评论分析全貌</div>
    </div>
    """, unsafe_allow_html=True)

    products = _get_products(user_id)

    # 工具栏
    col_search, col_sort, col_count = st.columns([3, 1, 1])
    with col_search:
        search_term = st.text_input("搜索", placeholder="搜索 SKU 或产品名称...",
                                     label_visibility="collapsed", key="dash_search")
    with col_sort:
        st.button("排序：最近更新", key="dash_sort", use_container_width=True)
    with col_count:
        st.markdown(f'<div style="font-size:13px;color:#828282;padding-top:8px;">共 {len(products)} 个产品</div>',
                    unsafe_allow_html=True)

    if not products:
        st.markdown("""
        <div style="text-align:center;padding:80px 0;color:#4d4d4d;">
            <div style="font-size:28px;font-weight:700;color:#202020;margin-bottom:8px;font-family:'Montserrat',system-ui,sans-serif;">暂无产品数据</div>
            <div style="font-size:14px;">前往「上传用户评论」页面上传评论文件，开始分析</div>
        </div>
        """, unsafe_allow_html=True)
        return

    # 过滤
    if search_term:
        products = [p for p in products if search_term.lower() in p["product_id"].lower()
                    or search_term.lower() in p.get("name", "").lower()]

    # 置顶排序
    pinned = st.session_state.get("pinned_products", [])
    if pinned:
        pinned_products = [p for p in products if p["product_id"] in pinned]
        unpinned_products = [p for p in products if p["product_id"] not in pinned]
        products = pinned_products + unpinned_products

    # 渲染每个产品卡片
    for idx, product in enumerate(products):
        with st.container():
            col_title, col_pin, col_del = st.columns([5, 0.7, 0.6])
            with col_title:
                pid = product["product_id"]
                name = product.get("name", "")
                label = f"{pid}  {name}" if name else pid
                st.markdown('<div class="product-title-btn"></div>', unsafe_allow_html=True)
                if st.button(label, key=f"dash_title_{idx}", use_container_width=True):
                    st.session_state["selected_product_id"] = pid
                    st.session_state.pop("view_session_id", None)
                    st.session_state["current_page"] = "results"
                    st.rerun()
            with col_pin:
                pinned_list = st.session_state.get("pinned_products", [])
                is_pinned = product["product_id"] in pinned_list
                pin_label = "📌" if is_pinned else "☆"
                if st.button(pin_label, key=f"dash_pin_{idx}", use_container_width=True):
                    if "pinned_products" not in st.session_state:
                        st.session_state["pinned_products"] = []
                    pid = product["product_id"]
                    if pid in st.session_state["pinned_products"]:
                        st.session_state["pinned_products"].remove(pid)
                    else:
                        st.session_state["pinned_products"].insert(0, pid)
                    st.rerun()
            with col_del:
                if st.button("🗑️", key=f"dash_del_{idx}", use_container_width=True):
                    st.session_state[f"confirm_del_{idx}"] = True

            # 删除确认
            if st.session_state.get(f"confirm_del_{idx}"):
                st.warning(f"确定删除产品 **{product['product_id']}** 的所有数据？此操作不可撤销。")
                c1, c2, _ = st.columns([1, 1, 4])
                with c1:
                    if st.button("确认删除", key=f"dash_del_confirm_{idx}", type="primary"):
                        from review_analyzer.database import delete_product
                        delete_product(user_id, product["product_id"])
                        del st.session_state[f"confirm_del_{idx}"]
                        st.rerun()
                with c2:
                    if st.button("取消", key=f"dash_del_cancel_{idx}"):
                        del st.session_state[f"confirm_del_{idx}"]
                        st.rerun()

            # 环比条
            sessions = sorted(product["sessions"], key=lambda s: s["created_at"])
            if len(sessions) >= 2:
                s_old = sessions[-2]
                s_new = sessions[-1]
                old_total = s_old.get("total_reviews", 0)
                new_total = s_new.get("total_reviews", 0)
                old_pos = (s_old.get("positive_count", 0) / old_total * 100) if old_total > 0 else 0
                new_pos = (s_new.get("positive_count", 0) / new_total * 100) if new_total > 0 else 0
                diff = new_pos - old_pos
                arrow = "↑" if diff >= 0 else "↓"
                color = "#00B894" if diff >= 0 else "#FF6B6B"

                st.markdown(f"""
                <div class="compare-bar version">
                    <span style="font-weight:600;">🔄 版本环比（{s_old['version']} vs {s_new['version']}）</span>
                    <span>正面率 <span style="color:#636E72;text-decoration:line-through;">{old_pos:.1f}%</span>
                    <span style="font-weight:700;color:{color};">→ {new_pos:.1f}% {arrow}{abs(diff):.1f}%</span></span>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown("""
                <div class="compare-bar version">
                    <span style="font-weight:600;">🔄 版本环比</span>
                    <span style="font-size:13px;color:#636E72;">仅有 1 个批次，暂无环比数据。上传新批次后自动生成对比分析。</span>
                </div>
                """, unsafe_allow_html=True)

            _render_metric_cards(product)
            st.markdown("<br>", unsafe_allow_html=True)
            _render_charts(product, idx)
            _render_batch_table(product)
            _render_action_card(product)
            st.markdown("<br>", unsafe_allow_html=True)
