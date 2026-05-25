"""分析结果页面 — 纵向单页布局"""

from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timedelta, date as date_type

import plotly.graph_objects as go
import streamlit as st

from review_analyzer.auth import get_current_user_id
from review_analyzer.database import get_sessions, get_comments, get_session_by_id, get_setting, delete_session, delete_product
from review_analyzer.exporter import export_to_xlsx
from review_analyzer.notifier import push_selected_items


def _get_top_tags(comments: list[dict], tag_field: str, pool_size: int) -> list[dict]:
    """统计 TOP10 标签"""
    tag_counter: Counter = Counter()
    for c in comments:
        tags = c.get(tag_field, "")
        if tags:
            seen_in_comment: set[str] = set()
            for tag in tags.split(","):
                tag = tag.strip()
                if tag and tag not in seen_in_comment:
                    seen_in_comment.add(tag)
                    tag_counter[tag] += 1

    top10 = tag_counter.most_common(10)
    result = []
    for rank, (tag, count) in enumerate(top10, 1):
        pct = count / pool_size * 100 if pool_size > 0 else 0
        result.append({"rank": rank, "tag": tag, "count": count, "pct": pct})
    return result


def _parse_comment_date(date_str: str) -> date_type | None:
    """尝试解析评论日期字符串"""
    if not date_str or not date_str.strip():
        return None
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%m/%d/%Y", "%d/%m/%Y", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(date_str.strip(), fmt).date()
        except ValueError:
            continue
    return None


def _apply_time_filter(comments: list[dict], session: dict, user_id: int) -> tuple[list[dict], str]:
    """时间筛选 — 返回筛选后的 comments 和筛选标签。超出当前 session 时合并同产品历史数据。"""
    all_dates = []
    for c in comments:
        d = _parse_comment_date(c.get("date", ""))
        if d:
            all_dates.append(d)

    if not all_dates:
        return comments, "全部"

    max_date = max(all_dates)
    min_date = min(all_dates)

    time_options = ["全部", "7天", "14天", "30天", "90天", "自定义"]
    col_filter = st.columns([1, 1, 1, 1, 1, 1])
    selected_option = st.session_state.get("time_filter_option", "全部")

    for i, opt in enumerate(time_options):
        with col_filter[i]:
            btn_type = "primary" if selected_option == opt else "secondary"
            if st.button(opt, key=f"time_filter_{opt}", use_container_width=True, type=btn_type):
                st.session_state["time_filter_option"] = opt
                if opt == "7天":
                    st.session_state["time_filter_start"] = max_date - timedelta(days=6)
                    st.session_state["time_filter_end"] = max_date
                elif opt == "14天":
                    st.session_state["time_filter_start"] = max_date - timedelta(days=13)
                    st.session_state["time_filter_end"] = max_date
                elif opt == "30天":
                    st.session_state["time_filter_start"] = max_date - timedelta(days=29)
                    st.session_state["time_filter_end"] = max_date
                elif opt == "90天":
                    st.session_state["time_filter_start"] = max_date - timedelta(days=89)
                    st.session_state["time_filter_end"] = max_date
                elif opt == "自定义":
                    st.session_state["time_filter_start"] = min_date
                    st.session_state["time_filter_end"] = max_date
                st.rerun()

    if selected_option == "全部":
        return comments, "全部"

    col_start, col_end = st.columns(2)
    default_start = st.session_state.get("time_filter_start", min_date)
    default_end = st.session_state.get("time_filter_end", max_date)

    with col_start:
        filter_start = st.date_input("开始日期", value=default_start, key="time_filter_date_start")
    with col_end:
        filter_end = st.date_input("结束日期", value=default_end, key="time_filter_date_end")

    # 判断是否需要跨 session 合并
    need_merge = filter_start < min_date
    merged_comments = comments

    if need_merge:
        product_id = session.get("product_id")
        all_sessions = get_sessions(user_id, product_id=product_id)
        other_session_ids = [s["id"] for s in all_sessions if s["id"] != session.get("id")]

        if other_session_ids:
            extra_comments = []
            for sid in other_session_ids:
                extra_comments.extend(get_comments(user_id, session_id=sid))
            # 去重（按 content_hash）
            seen_hashes = set()
            deduped = []
            for c in comments + extra_comments:
                h = c.get("content_hash", id(c))
                if h not in seen_hashes:
                    seen_hashes.add(h)
                    deduped.append(c)
            merged_comments = deduped
        else:
            st.warning(f"⚠️ 当前产品数据最早为 {min_date}，无更早的历史数据，无法覆盖 {filter_start} 起的时间范围。")

    # 筛选评论
    filtered = []
    for c in merged_comments:
        d = _parse_comment_date(c.get("date", ""))
        if d is None:
            continue
        if filter_start and d < filter_start:
            continue
        if filter_end and d > filter_end:
            continue
        filtered.append(c)

    if len(filtered) == 0:
        st.warning("所选时间范围内无评论数据")
        return comments, "全部"

    if need_merge and filtered:
        st.info(f"已合并历史数据，共 {len(filtered)} 条评论覆盖 {filter_start} ~ {filter_end}")

    label = f"{filter_start} ~ {filter_end}"
    return filtered, label


def _render_product_search(user_id: int) -> tuple[int | None, bool]:
    """顶部产品搜索框 — 输入产品编码搜索并切换查看不同产品的分析结果。
    返回 (session_id, show_all_data): show_all_data=True 表示展示该产品全部数据。
    """
    sessions = get_sessions(user_id)
    if not sessions:
        return None, False

    # 收集所有产品编码
    all_product_ids = list(dict.fromkeys(s["product_id"] for s in sessions))

    st.markdown("""
    <div style="margin-bottom:16px;padding:16px 20px;background:#f9fafb;border-radius:12px;border:1px solid #e5e7eb;">
        <div style="font-size:13px;font-weight:600;color:#4d4d4d;margin-bottom:8px;">🔍 选择分析产品</div>
    """, unsafe_allow_html=True)

    search_input = st.text_input(
        "搜索产品编码",
        placeholder="输入产品编码搜索...",
        key="product_search_input",
        label_visibility="collapsed",
    )

    st.markdown("</div>", unsafe_allow_html=True)

    # 根据搜索词过滤产品
    if search_input:
        matched_products = [pid for pid in all_product_ids if search_input.lower() in pid.lower()]
    else:
        matched_products = all_product_ids

    if not matched_products and search_input:
        st.caption("未找到匹配的产品编码")
        return sessions[0]["id"], False

    # 确定当前选中的产品
    current_product = st.session_state.get("selected_product_id")
    if current_product and current_product not in matched_products:
        current_product = None
    if not current_product and matched_products:
        current_product = matched_products[0]

    # 显示匹配的产品列表供选择
    if matched_products:
        selected_product = st.selectbox(
            "选择产品",
            matched_products,
            index=matched_products.index(current_product) if current_product in matched_products else 0,
            key="product_select_box",
            label_visibility="collapsed",
        )

        if selected_product != st.session_state.get("selected_product_id"):
            st.session_state["selected_product_id"] = selected_product
            st.session_state.pop("selected_record_id", None)
            st.session_state["product_view_mode"] = "all"

        # 获取该产品的上传记录（最近5条）
        product_sessions = [s for s in sessions if s["product_id"] == selected_product][:5]

        if product_sessions:
            st.caption(f"最近上传记录（{selected_product}）— 点击可查看单次上传数据")

            # 全部数据选项 + 各条记录
            view_mode = st.session_state.get("product_view_mode", "all")

            col_all, col_sep = st.columns([2, 4])
            with col_all:
                btn_type = "primary" if view_mode == "all" else "secondary"
                if st.button("📊 全部数据", key="view_all_data", type=btn_type):
                    st.session_state["product_view_mode"] = "all"
                    st.session_state.pop("selected_record_id", None)
                    st.rerun()

            # 显示各条上传记录
            for s in product_sessions:
                title = s.get("custom_title") or s.get("auto_title") or s["version"]
                _ca = s.get("created_at")
                created = str(_ca)[:16] if _ca is not None else ""
                total = s.get("total_reviews", 0)
                is_selected = (view_mode == "record" and
                               st.session_state.get("selected_record_id") == s["id"])
                btn_type = "primary" if is_selected else "secondary"
                if st.button(
                    f"{title} · {s['version']} · {created} · {total}条",
                    key=f"record_btn_{s['id']}",
                    type=btn_type,
                ):
                    st.session_state["product_view_mode"] = "record"
                    st.session_state["selected_record_id"] = s["id"]
                    st.rerun()

            # 返回结果
            if view_mode == "all":
                # 返回最新 session，但标记为展示全部数据
                return product_sessions[0]["id"], True
            else:
                chosen_id = st.session_state.get("selected_record_id", product_sessions[0]["id"])
                return chosen_id, False

    if sessions:
        return sessions[0]["id"], False
    return None, False


def render_results() -> None:
    user_id = get_current_user_id()
    if not user_id:
        st.warning("请先登录")
        return

    view_session_id = st.session_state.get("view_session_id")
    show_all_data = False

    if view_session_id:
        # 分析完成后直接跳转：只查这一条 session，跳过全量 get_sessions
        session = get_session_by_id(user_id, view_session_id)
        if not session:
            st.session_state.pop("view_session_id", None)
            st.error("未找到该分析记录")
            return
        session_id = view_session_id
        col_back, col_info = st.columns([1, 5])
        with col_back:
            if st.button("← 返回列表", key="back_to_search"):
                st.session_state.pop("view_session_id", None)
                st.rerun()
        with col_info:
            st.caption(f"当前查看：{session.get('product_id')} · {session.get('version')}")
    else:
        sessions = get_sessions(user_id)
        if not sessions:
            st.markdown("""
            <div style="text-align:center;padding:60px 0;color:#4d4d4d;">
                <div style="font-size:28px;font-weight:700;color:#202020;margin-bottom:8px;font-family:'Montserrat',system-ui,sans-serif;">暂无分析结果</div>
                <div style="font-size:14px;">前往「上传用户评论」页面上传文件并分析</div>
            </div>
            """, unsafe_allow_html=True)
            return
        session_id, show_all_data = _render_product_search(user_id)

        if not session_id:
            st.info("请选择一个产品查看分析结果")
            return

        session = get_session_by_id(user_id, session_id)
    if not session:
        st.error("未找到该分析记录")
        return

    # 加载评论数据：全部数据模式合并该产品所有 session 的评论
    if show_all_data:
        product_id = session.get("product_id")
        all_product_sessions = get_sessions(user_id, product_id=product_id)
        comments = []
        seen_hashes: set = set()
        for s in all_product_sessions:
            for c in get_comments(user_id, session_id=s["id"]):
                h = c.get("content_hash", id(c))
                if h not in seen_hashes:
                    seen_hashes.add(h)
                    comments.append(c)
    else:
        comments = get_comments(user_id, session_id=session_id)

    # 时间筛选（优化6）
    comments, filter_label = _apply_time_filter(comments, session, user_id)

    # 页头统计 — 排除 unrecognizable
    total = len(comments)
    unrecognizable_count = sum(1 for c in comments if c.get("sentiment") == "unrecognizable")
    valid_total = total - unrecognizable_count
    pos_count = sum(1 for c in comments if c.get("sentiment") == "positive")
    neg_count = sum(1 for c in comments if c.get("sentiment") == "negative")
    pos_rate = pos_count / valid_total * 100 if valid_total > 0 else 0
    neg_rate = neg_count / valid_total * 100 if valid_total > 0 else 0

    # 内容版正负率（基于 content_sentiment，有评分也按文字判断）
    has_content_sentiment = any(c.get("content_sentiment") for c in comments)
    if has_content_sentiment:
        content_valid = [c for c in comments if c.get("content_sentiment") not in ("unrecognizable", None, "")]
        content_valid_total = len(content_valid)
        content_pos_count = sum(1 for c in content_valid if c.get("content_sentiment") == "positive")
        content_neg_count = sum(1 for c in content_valid if c.get("content_sentiment") == "negative")
        content_pos_rate = content_pos_count / content_valid_total * 100 if content_valid_total > 0 else 0
        content_neg_rate = content_neg_count / content_valid_total * 100 if content_valid_total > 0 else 0
    else:
        content_valid_total = 0
        content_pos_rate = content_neg_rate = 0.0

    # 判断是否同时有评分和评论内容（决定是否展示双版本）
    has_rating = any(c.get("rating") for c in comments)
    has_text_content = any(c.get("content", "").strip() for c in comments)
    show_dual_rates = has_rating and has_text_content and has_content_sentiment

    date_range = ""
    if filter_label != "全部":
        date_range = filter_label
    elif session.get("date_range_start") and session.get("date_range_end"):
        date_range = f"{session['date_range_start']} ~ {session['date_range_end']}"

    invalid_note = f" · 无效评论 {unrecognizable_count} 条（不参与统计）" if unrecognizable_count > 0 else ""
    data_scope = "全部数据" if show_all_data else session.get('version', '')
    prompt_ver = session.get("prompt_version") or "v1.x"
    st.markdown(f"""
    <div style="margin-bottom:24px;">
        <div style="font-size:28px;font-weight:700;color:#202020;font-family:'Montserrat',system-ui,sans-serif;letter-spacing:-0.02em;">分析结果</div>
        <div style="font-size:14px;color:#4d4d4d;margin-top:6px;">
            {session.get('product_id', '')} · {data_scope}
            {(' · ' + date_range) if date_range else ''} · {valid_total:,} 条有效评论{invalid_note}
            · <span style="color:#828282;font-size:12px;">Prompt {prompt_ver}</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # 导出按钮
    col_export = st.columns([4, 1])
    with col_export[1]:
        try:
            xlsx_bytes, xlsx_filename = export_to_xlsx(session_id, user_id)
            st.download_button(
                "📥 导出报告",
                data=xlsx_bytes,
                file_name=xlsx_filename,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key="export_report",
            )
        except Exception as e:
            st.button("📥 导出报告", key="export_report", disabled=True)
            st.error(f"导出失败：{e}")

    # 4 指标卡片
    ratings = [c["rating"] for c in comments if c.get("rating")]
    avg_rating = sum(ratings) / len(ratings) if ratings else 0

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(f"""
        <div class="metric-card purple">
            <div class="metric-icon">◆</div>
            <div class="metric-val">{total:,}</div>
            <div class="metric-label">总评论数</div>
        </div>
        """, unsafe_allow_html=True)
    with col2:
        st.markdown(f"""
        <div class="metric-card green">
            <div class="metric-icon">▲</div>
            <div class="metric-val">{pos_rate:.1f}%</div>
            <div class="metric-label">正面率</div>
        </div>
        """, unsafe_allow_html=True)
    with col3:
        st.markdown(f"""
        <div class="metric-card red">
            <div class="metric-icon">▼</div>
            <div class="metric-val">{neg_rate:.1f}%</div>
            <div class="metric-label">负面率</div>
        </div>
        """, unsafe_allow_html=True)
    with col4:
        st.markdown(f"""
        <div class="metric-card yellow">
            <div class="metric-icon">★</div>
            <div class="metric-val">{avg_rating:.1f}</div>
            <div class="metric-label">平均评分</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # 双版本正负率对比（仅在同时有评分和评论文字时展示）
    if show_dual_rates:
        st.markdown("""
        <div style="margin-bottom:8px;font-size:13px;font-weight:600;color:#4d4d4d;">情感率双维度对比</div>
        """, unsafe_allow_html=True)
        rc1, rc2 = st.columns(2)
        with rc1:
            st.markdown(f"""
            <div style="background:#f8f9fa;border-radius:10px;padding:14px 18px;border-left:4px solid #6c63ff;">
                <div style="font-size:12px;color:#828282;margin-bottom:6px;">评分计算版（基于星级）</div>
                <span style="color:#2ecc71;font-weight:700;font-size:15px;">正面 {pos_rate:.1f}%</span>
                <span style="color:#828282;margin:0 8px;">·</span>
                <span style="color:#e74c3c;font-weight:700;font-size:15px;">负面 {neg_rate:.1f}%</span>
            </div>
            """, unsafe_allow_html=True)
        with rc2:
            st.markdown(f"""
            <div style="background:#f8f9fa;border-radius:10px;padding:14px 18px;border-left:4px solid #ff682c;">
                <div style="font-size:12px;color:#828282;margin-bottom:6px;">内容分析版（更真实反映产品口碑）</div>
                <span style="color:#2ecc71;font-weight:700;font-size:15px;">正面 {content_pos_rate:.1f}%</span>
                <span style="color:#828282;margin:0 8px;">·</span>
                <span style="color:#e74c3c;font-weight:700;font-size:15px;">负面 {content_neg_rate:.1f}%</span>
            </div>
            """, unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)

    # 图表：情感分布 + 关键词云
    col_chart1, col_chart2 = st.columns([1.2, 0.8])
    with col_chart1:
        neutral_count = valid_total - pos_count - neg_count
        fig = go.Figure(go.Pie(
            labels=["正面", "中性", "负面"],
            values=[pos_count, neutral_count, neg_count],
            marker=dict(colors=["#2ecc71", "#f39c12", "#e74c3c"]),
            hole=0.65,
            hoverinfo="label+percent+value",
        ))
        fig.update_layout(
            title="情感分布",
            height=300,
            margin=dict(l=20, r=20, t=40, b=20),
            legend=dict(orientation="h", yanchor="bottom", y=-0.15),
            paper_bgcolor="white",
            font=dict(family="Inter, system-ui, sans-serif"),
        )
        st.plotly_chart(fig, use_container_width=True, key="result_pie")

    with col_chart2:
        st.markdown("**热门关键词**")
        all_tags = []
        for c in comments:
            for field in ["issue_tag", "highlight_tag"]:
                tags = c.get(field, "")
                if tags:
                    all_tags.extend([t.strip() for t in tags.split(",") if t.strip()])

        if all_tags:
            tag_counts = Counter(all_tags).most_common(12)
            keywords_html = '<div style="display:flex;flex-wrap:wrap;gap:8px;padding:16px 0;">'
            for i, (tag, count) in enumerate(tag_counts):
                size_class = "lg" if i < 3 else ("md" if i < 6 else "sm")
                keywords_html += f'<span class="keyword {size_class}">{tag}</span>'
            keywords_html += '</div>'
            st.markdown(keywords_html, unsafe_allow_html=True)
        else:
            st.info("暂无关键词数据")

    st.markdown("<br>", unsafe_allow_html=True)

    # 行动建议
    _render_action_suggestions(pos_rate, neg_rate, comments)

    st.markdown("<br>", unsafe_allow_html=True)

    # TOP10 产品问题
    negative_comments = [c for c in comments if c.get("sentiment") == "negative"]
    top_issues = _get_top_tags(negative_comments, "issue_tag", len(negative_comments))

    st.markdown("""
    <div style="display:flex;align-items:center;gap:10px;margin:28px 0 16px;padding-bottom:10px;border-bottom:2px solid #ff682c;">
        <span style="background:#ff682c;color:#fff;width:24px;height:24px;border-radius:50%;display:inline-flex;align-items:center;justify-content:center;font-size:12px;font-weight:700;">1</span>
        <span style="font-size:16px;font-weight:600;color:#202020;">TOP 10 产品问题</span>
        <span style="font-size:12px;color:#828282;margin-left:4px;">勾选后可推送到飞书</span>
    </div>
    """, unsafe_allow_html=True)

    if top_issues:
        _render_top_table(top_issues, "issue", comments, negative_comments)
    else:
        st.info("暂无产品问题数据")

    st.markdown("<br>", unsafe_allow_html=True)

    # TOP10 产品亮点
    positive_comments = [c for c in comments if c.get("sentiment") == "positive"]
    top_highlights = _get_top_tags(positive_comments, "highlight_tag", len(positive_comments))

    st.markdown("""
    <div style="display:flex;align-items:center;gap:10px;margin:28px 0 16px;padding-bottom:10px;border-bottom:2px solid #ff682c;">
        <span style="background:#ff682c;color:#fff;width:24px;height:24px;border-radius:50%;display:inline-flex;align-items:center;justify-content:center;font-size:12px;font-weight:700;">2</span>
        <span style="font-size:16px;font-weight:600;color:#202020;">TOP 10 产品亮点</span>
        <span style="font-size:12px;color:#828282;margin-left:4px;">勾选后可推送到飞书</span>
    </div>
    """, unsafe_allow_html=True)

    if top_highlights:
        _render_top_table(top_highlights, "highlight", comments, positive_comments)
    else:
        st.info("暂无产品亮点数据")

    st.markdown("<br>", unsafe_allow_html=True)

    # 环比分析（优化7）
    _render_comparison_section(session, user_id)

    st.markdown("<br>", unsafe_allow_html=True)

    # 历史分析记录（优化5+8）
    _render_history_section(user_id, session_id)

    # 底部浮动操作栏
    _render_floating_bar(session_id, user_id, top_issues, top_highlights)


def _render_comparison_section(session: dict, user_id: int) -> None:
    """环比分析 — 支持时间粒度 + 版本筛选 + 跨 session 数据合并"""
    st.markdown("""
    <div style="display:flex;align-items:center;gap:10px;margin:28px 0 16px;padding-bottom:10px;border-bottom:2px solid #ff682c;">
        <span style="background:#ff682c;color:#fff;width:24px;height:24px;border-radius:50%;display:inline-flex;align-items:center;justify-content:center;font-size:12px;font-weight:700;">3</span>
        <span style="font-size:16px;font-weight:600;color:#202020;">环比分析</span>
    </div>
    """, unsafe_allow_html=True)

    product_id = session.get("product_id")
    all_sessions = get_sessions(user_id, product_id=product_id)

    if not all_sessions:
        st.info("暂无数据，上传评论后自动生成环比分析。")
        return

    # 收集该产品所有版本
    versions = list(dict.fromkeys(s["version"] for s in all_sessions))

    # 环比设置
    col_period, col_v1, col_v2 = st.columns(3)
    with col_period:
        period = st.selectbox("时间粒度", ["周环比（7天）", "双周环比（14天）", "月环比（30天）"], key="compare_period")
    with col_v1:
        version1 = st.selectbox("版本 1", versions, key="compare_v1")
    with col_v2:
        compare_mode = "同版本" if len(versions) == 1 else st.radio(
            "对比模式", ["同版本不同时间段", "跨版本对比"], key="compare_mode", horizontal=True
        )
        if compare_mode == "跨版本对比" or (isinstance(compare_mode, str) and "跨版本" in compare_mode):
            other_versions = [v for v in versions if v != version1]
            if other_versions:
                version2 = st.selectbox("版本 2", other_versions, key="compare_v2")
            else:
                st.info("只有一个版本，无法跨版本对比")
                version2 = None
        else:
            version2 = None

    if "7天" in period:
        days = 7
    elif "14天" in period:
        days = 14
    else:
        days = 30

    if st.button("生成环比", type="primary", key="run_comparison"):
        # 收集版本1的所有评论（跨 session）
        v1_sessions = [s for s in all_sessions if s["version"] == version1]
        v1_comments = []
        for s in v1_sessions:
            v1_comments.extend(get_comments(user_id, session_id=s["id"]))

        # 按日期排序
        v1_dated = []
        for c in v1_comments:
            d = _parse_comment_date(c.get("date", ""))
            if d:
                v1_dated.append((d, c))
        v1_dated.sort(key=lambda x: x[0])

        if not v1_dated:
            st.warning(f"版本 {version1} 无有效日期数据")
            return

        v1_max = max(d for d, _ in v1_dated)

        if version2:
            # 跨版本对比：版本1最近N天 vs 版本2最近N天
            v2_sessions = [s for s in all_sessions if s["version"] == version2]

            # 检查两组 session 的 Prompt 版本是否一致
            v1_prompt_versions = set(s.get("prompt_version") or "v1.x" for s in v1_sessions)
            v2_prompt_versions = set(s.get("prompt_version") or "v1.x" for s in v2_sessions)
            all_prompt_versions = v1_prompt_versions | v2_prompt_versions
            if len(all_prompt_versions) > 1:
                st.warning(
                    f"注意：两个版本使用了不同的 Prompt 版本（{', '.join(sorted(all_prompt_versions))}），"
                    "标签体系和分类口径可能不一致，环比数据仅供参考。"
                )

            v2_comments = []
            for s in v2_sessions:
                v2_comments.extend(get_comments(user_id, session_id=s["id"]))

            v2_dated = []
            for c in v2_comments:
                d = _parse_comment_date(c.get("date", ""))
                if d:
                    v2_dated.append((d, c))
            v2_dated.sort(key=lambda x: x[0])

            if not v2_dated:
                st.warning(f"版本 {version2} 无有效日期数据")
                return

            v2_max = max(d for d, _ in v2_dated)

            current_comments = [c for d, c in v1_dated if d >= v1_max - timedelta(days=days - 1)]
            prev_comments = [c for d, c in v2_dated if d >= v2_max - timedelta(days=days - 1)]

            label_current = f"{version1} 最近{days}天（{v1_max - timedelta(days=days-1)}~{v1_max}）"
            label_prev = f"{version2} 最近{days}天（{v2_max - timedelta(days=days-1)}~{v2_max}）"
        else:
            # 同版本时间环比：当期 vs 上期
            # 检查同版本内是否跨越了不同 Prompt 版本
            v1_prompt_versions = set(s.get("prompt_version") or "v1.x" for s in v1_sessions)
            if len(v1_prompt_versions) > 1:
                st.warning(
                    f"注意：该版本的历史数据包含不同 Prompt 版本（{', '.join(sorted(v1_prompt_versions))}），"
                    "当期与上期的分类口径可能不一致，环比数据仅供参考。"
                )
            current_start = v1_max - timedelta(days=days - 1)
            prev_end = current_start - timedelta(days=1)
            prev_start = prev_end - timedelta(days=days - 1)

            current_comments = [c for d, c in v1_dated if d >= current_start]
            prev_comments = [c for d, c in v1_dated if prev_start <= d <= prev_end]

            label_current = f"当期（{current_start}~{v1_max}）"
            label_prev = f"上期（{prev_start}~{prev_end}）"

            if not prev_comments:
                st.warning(f"上期（{prev_start}~{prev_end}）无数据，无法生成环比。")
                return

        # 计算指标
        def _calc(clist):
            t = len(clist)
            unrec = sum(1 for c in clist if c.get("sentiment") == "unrecognizable")
            valid = t - unrec
            p = sum(1 for c in clist if c.get("sentiment") == "positive")
            n = sum(1 for c in clist if c.get("sentiment") == "negative")
            return (p / valid * 100 if valid > 0 else 0, n / valid * 100 if valid > 0 else 0, t)

        cur_pos, cur_neg, cur_total = _calc(current_comments)
        prev_pos, prev_neg, prev_total = _calc(prev_comments)

        pos_diff = cur_pos - prev_pos
        neg_diff = cur_neg - prev_neg
        pos_color = "#2ecc71" if pos_diff >= 0 else "#e74c3c"
        neg_color = "#2ecc71" if neg_diff <= 0 else "#e74c3c"
        pos_arrow = "↑" if pos_diff >= 0 else "↓"
        neg_arrow = "↑" if neg_diff >= 0 else "↓"

        st.markdown(f"""
        <div class="compare-bar time">
            <span style="font-weight:600;">环比结果</span>
            <span style="font-size:12px;color:#828282;">{label_current}（{cur_total}条） vs {label_prev}（{prev_total}条）</span>
            <span>正面率 <span style="color:#828282;text-decoration:line-through;">{prev_pos:.1f}%</span>
            <span style="font-weight:700;color:{pos_color};">→ {cur_pos:.1f}% {pos_arrow}{abs(pos_diff):.1f}%</span></span>
            <span>负面率 <span style="color:#828282;text-decoration:line-through;">{prev_neg:.1f}%</span>
            <span style="font-weight:700;color:{neg_color};">→ {cur_neg:.1f}% {neg_arrow}{abs(neg_diff):.1f}%</span></span>
        </div>
        """, unsafe_allow_html=True)

        # TOP 问题变化
        cur_neg_c = [c for c in current_comments if c.get("sentiment") == "negative"]
        prev_neg_c = [c for c in prev_comments if c.get("sentiment") == "negative"]

        if cur_neg_c or prev_neg_c:
            cur_issues = _get_top_tags(cur_neg_c, "issue_tag", len(cur_neg_c))
            prev_issues = _get_top_tags(prev_neg_c, "issue_tag", len(prev_neg_c))
            cur_map = {i["tag"]: i["pct"] for i in cur_issues}
            prev_map = {i["tag"]: i["pct"] for i in prev_issues}
            all_tags = list(dict.fromkeys([i["tag"] for i in cur_issues] + [i["tag"] for i in prev_issues]))

            if all_tags:
                st.markdown("**TOP 问题环比变化**")
                for tag in all_tags[:8]:
                    b_pct = prev_map.get(tag, 0)
                    t_pct = cur_map.get(tag, 0)
                    diff = t_pct - b_pct
                    arrow = "↑" if diff > 0 else ("↓" if diff < 0 else "—")
                    color = "#e74c3c" if diff > 0 else "#2ecc71"
                    st.markdown(
                        f"- **{tag}**：{b_pct:.1f}% → {t_pct:.1f}% "
                        f"<span style='color:{color};font-weight:600;'>{arrow}{abs(diff):.1f}%</span>",
                        unsafe_allow_html=True,
                    )


def _render_action_suggestions(pos_rate: float, neg_rate: float, comments: list[dict]) -> None:
    """渲染行动建议（自然语言）"""
    is_danger = neg_rate > 25 or pos_rate < 55
    card_class = "action-card danger" if is_danger else "action-card"
    title = "行动建议（需关注）" if is_danger else "行动建议"

    suggestions = []
    if pos_rate >= 70:
        suggestions.append(f"正面率达到 {pos_rate:.1f}%，产品改进方向正确，建议继续保持当前策略。")
    elif pos_rate < 55:
        suggestions.append(f"正面率仅为 {pos_rate:.1f}%，产品口碑正在下滑，建议立即排查用户不满意的主要原因。")

    if neg_rate > 25:
        suggestions.append(f"负面率已达 {neg_rate:.1f}%，超过 25% 警戒线，建议优先处理用户反馈最集中的问题。")

    negative_comments = [c for c in comments if c.get("sentiment") == "negative"]
    top_issues = _get_top_tags(negative_comments, "issue_tag", len(negative_comments))
    if top_issues and top_issues[0]["pct"] > 5:
        suggestions.append(
            f"用户反馈最集中的问题是「{top_issues[0]['tag']}」，占负面评论的 {top_issues[0]['pct']:.1f}%，建议将其列为改进优先项。")

    positive_comments = [c for c in comments if c.get("sentiment") == "positive"]
    top_highlights = _get_top_tags(positive_comments, "highlight_tag", len(positive_comments))
    if top_highlights:
        suggestions.append(
            f"产品最受认可的亮点是「{top_highlights[0]['tag']}」，占正面评论的 {top_highlights[0]['pct']:.1f}%，建议在产品详情页和广告文案中重点突出。")

    if not suggestions:
        suggestions.append("产品整体表现正常，建议持续监控评论动态。")

    items_html = ""
    for i, text in enumerate(suggestions, 1):
        items_html += f'<div style="font-size:14px;padding:10px 0;border-bottom:1px solid #e8e8e8;line-height:1.6;">{i}. {text}</div>'

    st.markdown(f"""
    <div class="{card_class}">
        <h4 style="font-size:15px;font-weight:600;margin-bottom:12px;">{title}</h4>
        {items_html}
    </div>
    """, unsafe_allow_html=True)


def _render_top_table(top_items: list[dict], prefix: str, all_comments: list[dict],
                      pool_comments: list[dict]) -> None:
    """渲染 TOP10 表格"""
    tag_field = "issue_tag" if prefix == "issue" else "highlight_tag"

    # 表头
    cols = st.columns([0.5, 0.5, 3, 1, 1, 1.5])
    with cols[0]:
        st.markdown("**#**")
    with cols[1]:
        st.markdown("")
    with cols[2]:
        st.markdown("**描述**")
    with cols[3]:
        st.markdown("**提及次数**")
    with cols[4]:
        st.markdown("**占比**")
    with cols[5]:
        st.markdown("**操作**")

    for item in top_items:
        cols = st.columns([0.5, 0.5, 3, 1, 1, 1.5])
        with cols[0]:
            st.checkbox("", key=f"{prefix}_chk_{item['rank']}", label_visibility="collapsed")
        with cols[1]:
            st.write(str(item["rank"]))
        with cols[2]:
            st.write(item["tag"])
        with cols[3]:
            st.write(f"{item['count']} 条")
        with cols[4]:
            st.write(f"{item['pct']:.1f}%")
        with cols[5]:
            if st.button("📄 查看原文", key=f"{prefix}_src_{item['rank']}"):
                st.session_state[f"show_source_{prefix}_{item['rank']}"] = \
                    not st.session_state.get(f"show_source_{prefix}_{item['rank']}", False)

        # 原文展开面板
        if st.session_state.get(f"show_source_{prefix}_{item['rank']}", False):
            source_comments = [
                c for c in pool_comments
                if item["tag"] in [t.strip() for t in (c.get(tag_field) or "").split(",")]
            ][:20]
            if source_comments:
                st.markdown(f"""
                <div class="source-panel">
                    <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:12px;">
                        <h4 style="font-size:15px;font-weight:600;">📄 「{item['tag']}」— 代表性原文 TOP 20</h4>
                    </div>
                </div>
                """, unsafe_allow_html=True)

                for i, c in enumerate(source_comments, 1):
                    content_preview = (c.get("content", "")[:100] + "...") if len(c.get("content", "")) > 100 else c.get("content", "")
                    rating_str = f"⭐{c['rating']}" if c.get("rating") else "—"
                    st.markdown(
                        f"**{i}.** \"{content_preview}\" | {rating_str} | {c.get('date', '—')}",
                    )


def _render_floating_bar(session_id: int, user_id: int, top_issues: list[dict], top_highlights: list[dict]) -> None:
    """底部浮动操作栏 — 勾选 TOP10 项后显示"""
    selected_issues = [k for k in st.session_state if k.startswith("issue_chk_") and st.session_state[k]]
    selected_highlights = [k for k in st.session_state if k.startswith("highlight_chk_") and st.session_state[k]]
    total_selected = len(selected_issues) + len(selected_highlights)

    if total_selected > 0:
        st.markdown(f"""
        <div class="float-bar">
            <div style="display:flex;align-items:center;justify-content:space-between;">
                <span style="font-size:14px;font-weight:600;">
                    已选择 {total_selected} 项（问题 {len(selected_issues)} + 亮点 {len(selected_highlights)}）
                </span>
                <div style="display:flex;gap:8px;align-items:center;">
                    <span style="font-size:13px;color:#828282;">推送到：</span>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # 读取用户 Webhook 配置
        raw_settings = get_setting(user_id, "push_settings")
        webhook_url = ""
        webhook_secret = ""
        group_name = "默认群"
        if raw_settings:
            try:
                push_settings = json.loads(raw_settings)
                webhook_url = push_settings.get("webhook_url", "")
                webhook_secret = push_settings.get("webhook_secret", "")
                group_name = push_settings.get("webhook_group_name", "") or "默认群"
            except json.JSONDecodeError:
                pass

        col_group, col_push, _ = st.columns([2, 1, 2])
        with col_group:
            st.selectbox("选择飞书群", [group_name], key="push_group_select", label_visibility="collapsed")
        with col_push:
            if st.button("📤 推送到飞书", type="primary", key="push_to_feishu"):
                if not webhook_url:
                    st.error("请先在「推送设置」页配置飞书 Webhook")
                else:
                    selected_tags = []
                    for k in selected_issues:
                        rank = int(k.replace("issue_chk_", ""))
                        match = next((i for i in top_issues if i["rank"] == rank), None)
                        if match:
                            selected_tags.append(match["tag"])
                    tag_type = "issue"

                    selected_hl_tags = []
                    for k in selected_highlights:
                        rank = int(k.replace("highlight_chk_", ""))
                        match = next((i for i in top_highlights if i["rank"] == rank), None)
                        if match:
                            selected_hl_tags.append(match["tag"])

                    all_tags = selected_tags + selected_hl_tags
                    push_type = "issue" if selected_tags and not selected_hl_tags else (
                        "highlight" if selected_hl_tags and not selected_tags else "issue"
                    )

                    result = push_selected_items(
                        user_id=user_id,
                        webhook_url=webhook_url,
                        secret=webhook_secret,
                        session_id=session_id,
                        selected_tags=all_tags,
                        tag_type=push_type,
                    )
                    if result["ok"]:
                        st.success("推送成功 ✓")
                    else:
                        st.error(f"推送失败：{result['msg']}")


def _render_history_section(user_id: int, current_session_id: int) -> None:
    """历史分析记录 — 整合到结果页底部，直接展示"""
    sessions = get_sessions(user_id)
    if not sessions:
        return

    st.markdown("""
    <div style="display:flex;align-items:center;gap:10px;margin:28px 0 16px;padding-bottom:10px;border-bottom:2px solid #ff682c;">
        <span style="background:#ff682c;color:#fff;width:24px;height:24px;border-radius:50%;display:inline-flex;align-items:center;justify-content:center;font-size:12px;font-weight:700;">4</span>
        <span style="font-size:16px;font-weight:600;color:#202020;">历史分析记录</span>
    </div>
    """, unsafe_allow_html=True)

    # 按产品分组
    products: dict[str, list[dict]] = {}
    for s in sessions:
        pid = s["product_id"]
        if pid not in products:
            products[pid] = []
        products[pid].append(s)

    # 产品搜索框（直接可见）
    search_sku = st.text_input(
        "搜索产品编号",
        placeholder="输入 SKU 关键词快速筛选...",
        key="hist_search_in_results",
    )

    filtered_products = products
    if search_sku:
        filtered_products = {
            pid: sess for pid, sess in products.items()
            if search_sku.lower() in pid.lower()
        }

    if not filtered_products:
        st.info("未找到匹配的产品")
        return

    for pid, product_sessions in filtered_products.items():
        st.markdown(f"""
        <div style="font-size:14px;font-weight:600;margin:16px 0 8px;padding:8px 12px;
                    background:#f9f9f9;border-radius:8px;border:1px solid #e8e8e8;display:flex;align-items:center;justify-content:space-between;">
            <span>{pid}（{len(product_sessions)} 个批次）</span>
        </div>
        """, unsafe_allow_html=True)

        for s in product_sessions:
            total = s.get("total_reviews", 0)
            pos = s.get("positive_count", 0)
            pos_rate = f"{pos / total * 100:.1f}%" if total > 0 else "—"
            title = s.get("custom_title") or s.get("auto_title") or s["version"]
            is_current = s["id"] == current_session_id

            date_range = ""
            if s.get("date_range_start") and s.get("date_range_end"):
                date_range = f"{s['date_range_start']} ~ {s['date_range_end']}"

            current_badge = ' <span style="background:#ff682c;color:#fff;padding:2px 8px;border-radius:10px;font-size:11px;">当前</span>' if is_current else ""

            st.markdown(f"""
            <div style="font-size:13px;color:#4d4d4d;padding:4px 12px;">
                {title}{current_badge} · {date_range or '—'} · {total:,} 条评论 ·
                <span class="tag tag-pos">{pos_rate}</span>
            </div>
            """, unsafe_allow_html=True)

            col_view, col_export, col_del, _ = st.columns([1, 1, 1, 3])
            with col_view:
                if is_current:
                    st.button("当前查看", key=f"histR_view_{s['id']}", disabled=True)
                elif st.button("查看结果", key=f"histR_view_{s['id']}"):
                    st.session_state["view_session_id"] = s["id"]
                    st.rerun()
            with col_export:
                try:
                    xlsx_bytes, xlsx_fn = export_to_xlsx(s["id"], user_id)
                    st.download_button(
                        "📥 导出",
                        data=xlsx_bytes,
                        file_name=xlsx_fn,
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        key=f"histR_export_{s['id']}",
                    )
                except Exception:
                    st.button("📥 导出", key=f"histR_export_{s['id']}", disabled=True)
            with col_del:
                if st.button("🗑️ 删除", key=f"histR_del_{s['id']}"):
                    delete_session(user_id, s["id"])
                    if s["id"] == current_session_id:
                        st.session_state.pop("view_session_id", None)
                    st.rerun()

        st.markdown("<hr style='border:none;border-top:1px solid #e8e8e8;margin:8px 0;'>",
                    unsafe_allow_html=True)
