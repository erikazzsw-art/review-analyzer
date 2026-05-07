"""分析结果页面 — 纵向单页布局"""

import json
from collections import Counter

import plotly.graph_objects as go
import streamlit as st

from review_analyzer.auth import get_current_user_id
from review_analyzer.database import get_sessions, get_comments, get_session_by_id, get_setting
from review_analyzer.exporter import export_to_xlsx
from review_analyzer.notifier import push_selected_items


def _get_top_tags(comments: list[dict], tag_field: str, pool_size: int) -> list[dict]:
    """统计 TOP10 标签"""
    tag_counter: Counter = Counter()
    for c in comments:
        tags = c.get(tag_field, "")
        if tags:
            for tag in tags.split(","):
                tag = tag.strip()
                if tag:
                    tag_counter[tag] += 1

    top10 = tag_counter.most_common(10)
    result = []
    for rank, (tag, count) in enumerate(top10, 1):
        pct = count / pool_size * 100 if pool_size > 0 else 0
        result.append({"rank": rank, "tag": tag, "count": count, "pct": pct})
    return result


def render_results() -> None:
    user_id = get_current_user_id()
    if not user_id:
        st.warning("请先登录")
        return

    # 确定要查看的 session
    session_id = st.session_state.get("view_session_id")

    # 如果没有指定 session，显示选择器
    if not session_id:
        sessions = get_sessions(user_id)
        if not sessions:
            st.markdown("""
            <div style="text-align:center;padding:60px 0;color:#636E72;">
                <div style="font-size:48px;margin-bottom:16px;">📋</div>
                <div style="font-size:18px;font-weight:600;margin-bottom:8px;">暂无分析结果</div>
                <div style="font-size:14px;">前往「上传用户评论」页面上传文件并分析</div>
            </div>
            """, unsafe_allow_html=True)
            return

        session_options = {
            f"{s.get('product_id')} · {s.get('version')} · {s.get('auto_title', '')}": s["id"]
            for s in sessions
        }
        selected = st.selectbox("选择分析记录", list(session_options.keys()), key="result_session_select")
        session_id = session_options[selected]

    session = get_session_by_id(user_id, session_id)
    if not session:
        st.error("未找到该分析记录")
        return

    comments = get_comments(user_id, session_id=session_id)

    # 页头
    total = session.get("total_reviews", len(comments))
    pos_count = session.get("positive_count", 0)
    neg_count = session.get("negative_count", 0)
    pos_rate = pos_count / total * 100 if total > 0 else 0
    neg_rate = neg_count / total * 100 if total > 0 else 0

    date_range = ""
    if session.get("date_range_start") and session.get("date_range_end"):
        date_range = f"{session['date_range_start']} ~ {session['date_range_end']}"

    st.markdown(f"""
    <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:24px;">
        <div>
            <div style="font-size:22px;font-weight:700;">分析结果</div>
            <div style="font-size:14px;color:#636E72;margin-top:2px;">
                {session.get('product_id', '')} · {session.get('version', '')}
                {(' · ' + date_range) if date_range else ''} · {total:,} 条评论
            </div>
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

    # 环比条（版本环比）
    sessions_same_product = get_sessions(user_id, product_id=session.get("product_id"))
    other_sessions = [s for s in sessions_same_product if s["id"] != session_id]

    if other_sessions:
        prev = other_sessions[0]
        prev_total = prev.get("total_reviews", 0)
        prev_pos = prev.get("positive_count", 0) / prev_total * 100 if prev_total > 0 else 0
        prev_neg = prev.get("negative_count", 0) / prev_total * 100 if prev_total > 0 else 0
        pos_diff = pos_rate - prev_pos
        neg_diff = neg_rate - prev_neg

        pos_arrow = "↑" if pos_diff >= 0 else "↓"
        neg_arrow = "↑" if neg_diff >= 0 else "↓"
        pos_color = "#00B894" if pos_diff >= 0 else "#FF6B6B"
        neg_color = "#00B894" if neg_diff <= 0 else "#FF6B6B"

        st.markdown(f"""
        <div class="compare-bar version">
            <span style="font-weight:600;">🔄 版本环比（{prev.get('version', '')} vs {session.get('version', '')}）</span>
            <span>正面率 <span style="color:#636E72;text-decoration:line-through;">{prev_pos:.1f}%</span>
            <span style="font-weight:700;color:{pos_color};">→ {pos_rate:.1f}% {pos_arrow}{abs(pos_diff):.1f}%</span></span>
            <span>负面率 <span style="color:#636E72;text-decoration:line-through;">{prev_neg:.1f}%</span>
            <span style="font-weight:700;color:{neg_color};">→ {neg_rate:.1f}% {neg_arrow}{abs(neg_diff):.1f}%</span></span>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div class="compare-bar version">
            <span style="font-weight:600;">🔄 版本环比</span>
            <span style="font-size:13px;color:#636E72;">暂无对比数据，上传同产品不同版本后自动生成。</span>
        </div>
        """, unsafe_allow_html=True)

    # 时间环比
    st.markdown("""
    <div class="compare-bar time">
        <span style="font-weight:600;">📅 时间环比</span>
        <span style="font-size:13px;color:#636E72;">暂无同版本不同时间段数据，上传后自动生成时间环比对比。</span>
    </div>
    """, unsafe_allow_html=True)

    # 4 指标卡片
    ratings = [c["rating"] for c in comments if c.get("rating")]
    avg_rating = sum(ratings) / len(ratings) if ratings else 0

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(f"""
        <div class="metric-card purple">
            <div class="metric-icon">💬</div>
            <div class="metric-val">{total:,}</div>
            <div class="metric-label">总评论数</div>
        </div>
        """, unsafe_allow_html=True)
    with col2:
        st.markdown(f"""
        <div class="metric-card green">
            <div class="metric-icon">😊</div>
            <div class="metric-val">{pos_rate:.1f}%</div>
            <div class="metric-label">正面率</div>
        </div>
        """, unsafe_allow_html=True)
    with col3:
        st.markdown(f"""
        <div class="metric-card red">
            <div class="metric-icon">😟</div>
            <div class="metric-val">{neg_rate:.1f}%</div>
            <div class="metric-label">负面率</div>
        </div>
        """, unsafe_allow_html=True)
    with col4:
        st.markdown(f"""
        <div class="metric-card yellow">
            <div class="metric-icon">⭐</div>
            <div class="metric-val">{avg_rating:.1f}</div>
            <div class="metric-label">平均评分</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # 图表：情感分布 + 关键词云
    col_chart1, col_chart2 = st.columns([1.2, 0.8])
    with col_chart1:
        neutral_count = total - pos_count - neg_count
        fig = go.Figure(go.Pie(
            labels=["正面", "中性", "负面"],
            values=[pos_count, neutral_count, neg_count],
            marker=dict(colors=["#00B894", "#FDCB6E", "#FF6B6B"]),
            hole=0.65,
            hoverinfo="label+percent+value",
        ))
        fig.update_layout(
            title="🎯 情感分布",
            height=300,
            margin=dict(l=20, r=20, t=40, b=20),
            legend=dict(orientation="h", yanchor="bottom", y=-0.15),
            paper_bgcolor="white",
        )
        st.plotly_chart(fig, use_container_width=True, key="result_pie")

    with col_chart2:
        st.markdown("**🏷️ 热门关键词**")
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
    <div style="font-size:18px;font-weight:700;margin:28px 0 16px;display:flex;align-items:center;gap:8px;">
        ❌ TOP 10 产品问题
        <span style="font-size:13px;font-weight:400;color:#636E72;margin-left:auto;">勾选后可推送到飞书</span>
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
    <div style="font-size:18px;font-weight:700;margin:28px 0 16px;display:flex;align-items:center;gap:8px;">
        ✅ TOP 10 产品亮点
        <span style="font-size:13px;font-weight:400;color:#636E72;margin-left:auto;">勾选后可推送到飞书</span>
    </div>
    """, unsafe_allow_html=True)

    if top_highlights:
        _render_top_table(top_highlights, "highlight", comments, positive_comments)
    else:
        st.info("暂无产品亮点数据")

    st.markdown("<br>", unsafe_allow_html=True)

    # 自定义环比对比
    _render_custom_compare(session, user_id)

    # 底部浮动操作栏
    _render_floating_bar(session_id, user_id, top_issues, top_highlights)


def _render_action_suggestions(pos_rate: float, neg_rate: float, comments: list[dict]) -> None:
    """渲染行动建议"""
    is_danger = neg_rate > 25 or pos_rate < 55
    card_class = "action-card danger" if is_danger else "action-card"
    title = "🚨 行动建议（需关注）" if is_danger else "💡 行动建议"

    suggestions = []
    if pos_rate >= 70:
        suggestions.append(("tag-pos", "↑ 改善", f"正面率 {pos_rate:.1f}%，产品改进方向正确，建议继续保持"))
    elif pos_rate < 55:
        suggestions.append(("tag-neg", "⚠️ 恶化", f"正面率仅 {pos_rate:.1f}%，产品口碑正在恶化，需立即排查"))

    if neg_rate > 25:
        suggestions.append(("tag-neg", "⚠️ 紧急", f"负面率 {neg_rate:.1f}% 超过警戒线，建议立即排查核心问题"))

    # 基于 TOP 问题生成建议
    negative_comments = [c for c in comments if c.get("sentiment") == "negative"]
    top_issues = _get_top_tags(negative_comments, "issue_tag", len(negative_comments))
    if top_issues and top_issues[0]["pct"] > 5:
        suggestions.append(("tag-neg", "⚠️ 关注",
                           f"「{top_issues[0]['tag']}」问题占比 {top_issues[0]['pct']:.1f}%，建议重点改进"))

    # 基于亮点生成营销建议
    positive_comments = [c for c in comments if c.get("sentiment") == "positive"]
    top_highlights = _get_top_tags(positive_comments, "highlight_tag", len(positive_comments))
    if top_highlights:
        suggestions.append(("tag-pos", "📢 营销",
                           f"「{top_highlights[0]['tag']}」亮点占比 {top_highlights[0]['pct']:.1f}%，建议在 listing 中强化"))

    if not suggestions:
        suggestions.append(("tag-pos", "👍 良好", "产品整体表现正常，建议持续监控"))

    items_html = ""
    for tag_cls, badge_text, text in suggestions:
        items_html += f"""
        <div style="font-size:14px;padding:8px 0;border-bottom:1px solid rgba(108,92,231,0.1);display:flex;gap:8px;">
            <span class="tag {tag_cls}">{badge_text}</span>
            <span>{text}</span>
        </div>"""

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
            source_comments = [c for c in pool_comments if item["tag"] in (c.get(tag_field) or "")][:20]
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


def _render_custom_compare(session: dict, user_id: int) -> None:
    """自定义环比对比板块"""
    st.markdown("""
    <div style="font-size:18px;font-weight:700;margin:28px 0 16px;display:flex;align-items:center;gap:8px;">
        🔄 自定义环比对比
    </div>
    """, unsafe_allow_html=True)

    all_sessions = get_sessions(user_id)
    product_sessions = [s for s in all_sessions if s["product_id"] == session["product_id"]]

    if len(product_sessions) < 2:
        st.info("需要至少 2 个批次才能进行环比对比。上传新批次后自动解锁。")
        return

    session_labels = {
        s["id"]: f"{s['version']} · {s.get('date_range_start', '?')}~{s.get('date_range_end', '?')} ({s.get('total_reviews', 0)}条)"
        for s in product_sessions
    }

    col_dim, col_base, col_target = st.columns(3)
    with col_dim:
        compare_dim = st.selectbox("对比维度", ["版本环比", "时间环比"], key="custom_compare_dim")
    with col_base:
        base_id = st.selectbox("基准批次", list(session_labels.keys()),
                               format_func=lambda x: session_labels[x], key="custom_compare_base")
    with col_target:
        target_id = st.selectbox("对比批次", list(session_labels.keys()),
                                 format_func=lambda x: session_labels[x], index=min(1, len(session_labels) - 1),
                                 key="custom_compare_target")

    if st.button("生成对比", type="primary", key="custom_compare_btn"):
        if base_id == target_id:
            st.warning("基准批次和对比批次不能相同")
        else:
            base_session = next((s for s in product_sessions if s["id"] == base_id), None)
            target_session = next((s for s in product_sessions if s["id"] == target_id), None)
            if base_session and target_session:
                _render_compare_result(base_session, target_session, user_id)


def _render_compare_result(base: dict, target: dict, user_id: int) -> None:
    """渲染环比对比结果"""
    base_total = base.get("total_reviews", 0) or 1
    target_total = target.get("total_reviews", 0) or 1
    base_pos = base.get("positive_count", 0) / base_total * 100
    target_pos = target.get("positive_count", 0) / target_total * 100
    base_neg = base.get("negative_count", 0) / base_total * 100
    target_neg = target.get("negative_count", 0) / target_total * 100
    diff_pos = target_pos - base_pos
    diff_neg = target_neg - base_neg

    col1, col2, col3 = st.columns(3)
    with col1:
        delta_color = "normal" if diff_pos >= 0 else "inverse"
        st.metric("正面率变化", f"{target_pos:.1f}%", f"{diff_pos:+.1f}%", delta_color=delta_color)
    with col2:
        delta_color = "inverse" if diff_neg > 0 else "normal"
        st.metric("负面率变化", f"{target_neg:.1f}%", f"{diff_neg:+.1f}%", delta_color=delta_color)
    with col3:
        st.metric("评论数变化", f"{target_total:,}", f"{target_total - base_total:+,}")

    # 问题环比表
    base_comments = get_comments(user_id, base["id"])
    target_comments = get_comments(user_id, target["id"])

    base_neg_comments = [c for c in base_comments if c.get("sentiment") == "negative"]
    target_neg_comments = [c for c in target_comments if c.get("sentiment") == "negative"]
    base_issues = _get_top_tags(base_neg_comments, "issue_tag", len(base_neg_comments))
    target_issues = _get_top_tags(target_neg_comments, "issue_tag", len(target_neg_comments))

    base_issue_map = {item["tag"]: item["pct"] for item in base_issues}
    target_issue_map = {item["tag"]: item["pct"] for item in target_issues}
    all_issue_tags = list(dict.fromkeys(
        [item["tag"] for item in target_issues] + [item["tag"] for item in base_issues]
    ))

    if all_issue_tags:
        st.markdown("**❌ 问题环比**")
        for tag in all_issue_tags[:10]:
            b_pct = base_issue_map.get(tag, 0)
            t_pct = target_issue_map.get(tag, 0)
            diff = t_pct - b_pct
            arrow = "↑" if diff > 0 else ("↓" if diff < 0 else "—")
            color = "#FF6B6B" if diff > 0 else "#00B894"
            st.markdown(
                f"- **{tag}**：{b_pct:.1f}% → {t_pct:.1f}% "
                f"<span style='color:{color};font-weight:600;'>{arrow}{abs(diff):.1f}%</span>",
                unsafe_allow_html=True,
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
                    <span style="font-size:13px;color:#636E72;">推送到：</span>
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
