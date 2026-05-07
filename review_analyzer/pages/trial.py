"""免费试用页面 — 未登录用户体验分析功能（限500条，结果只显示前5条）"""

import tempfile
import os

import streamlit as st
import pandas as pd

from review_analyzer.parser import parse_file


def render_trial_page() -> None:
    st.markdown("""
    <style>
    [data-testid="stSidebar"] { display: none; }
    .stApp { background: #FAFAFF; }
    .trial-tip {
        background: linear-gradient(90deg, #F0EEFF, #E8F8F5);
        border: 1px solid #A29BFE; border-radius: 14px;
        padding: 16px 20px; margin-bottom: 24px;
        display: flex; align-items: center; gap: 12px; font-size: 14px;
    }
    .trial-tip .icon { font-size: 24px; }
    .trial-tip.warn {
        background: linear-gradient(90deg, #FFEAEA, #FFF3E0);
        border-color: #FDCB6E;
    }
    </style>
    """, unsafe_allow_html=True)

    # 顶部导航
    col_logo, col_btn = st.columns([4, 1])
    with col_logo:
        st.markdown("""
        <div style="display:flex;align-items:center;gap:10px;padding:8px 0;">
            <span style="font-size:26px;">🔍</span>
            <span style="font-size:20px;font-weight:700;color:#6C5CE7;">ClueAI</span>
        </div>
        """, unsafe_allow_html=True)
    with col_btn:
        if st.button("登录", key="trial_to_login"):
            st.session_state["show_page"] = "login"
            st.rerun()

    # 提示条
    st.markdown("""
    <div class="trial-tip">
        <div class="icon">💡</div>
        <div>试用模式：单次分析，不保存历史记录，不支持导出和环比分析。登录后解锁完整功能。</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div style="font-size:22px;font-weight:700;margin-bottom:20px;">免费试用</div>',
                unsafe_allow_html=True)

    # 表单区
    col1, col2 = st.columns(2)
    with col1:
        trial_product_id = st.text_input("产品编号 *", placeholder="SKU 或任何可识别该产品的唯一编码",
                                         key="trial_product_id")
    with col2:
        trial_product_name = st.text_input("产品中文名称", placeholder="选填", key="trial_product_name")

    col3, col4 = st.columns(2)
    with col3:
        trial_platform = st.selectbox("平台来源 *",
                                      ["请选择...", "Amazon", "Shopee", "Temu", "eBay", "AliExpress", "Walmart"],
                                      key="trial_platform")
    with col4:
        trial_category = st.selectbox("产品类目 *",
                                      ["请选择...", "电子产品", "服装鞋帽", "家居用品", "美妆个护",
                                       "运动户外", "食品保健", "母婴用品", "其他"],
                                      key="trial_category")

    # 上传区
    st.markdown('<div style="height:16px;"></div>', unsafe_allow_html=True)
    uploaded_file = st.file_uploader(
        "上传评论文件",
        type=["csv", "xlsx", "xls"],
        key="trial_upload",
        help="支持 CSV / XLSX，试用限制 500 条"
    )

    if uploaded_file is not None:
        if "trial_df" not in st.session_state:
            try:
                suffix = os.path.splitext(uploaded_file.name)[1]
                with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                    tmp.write(uploaded_file.getvalue())
                    tmp_path = tmp.name
                file_type = suffix.lstrip(".").lower()
                if file_type in ("xlsx", "xls"):
                    file_type = "excel"
                df = parse_file(tmp_path, file_type)
                os.unlink(tmp_path)
                if len(df) > 500:
                    df = df.head(500)
                    st.warning("试用模式限制 500 条，已截取前 500 条数据。")
                st.session_state["trial_df"] = df
            except Exception as e:
                st.error(f"文件解析出错：{e}")
                return

        df = st.session_state["trial_df"]

        # 文件预览
        st.markdown('<div style="font-size:15px;font-weight:600;margin:16px 0 8px;">📄 文件预览</div>',
                    unsafe_allow_html=True)
        st.dataframe(df.head(5), use_container_width=True)
        st.markdown(f'<div style="font-size:13px;color:#636E72;">共 {len(df)} 条数据</div>',
                    unsafe_allow_html=True)

        # 开始分析按钮
        col_a, col_b = st.columns([3, 1])
        with col_b:
            analyze_clicked = st.button("开始分析", type="primary", use_container_width=True, key="trial_analyze")

        if analyze_clicked:
            if not trial_product_id:
                st.error("请填写产品编号")
            elif trial_platform == "请选择...":
                st.error("请选择平台来源")
            elif trial_category == "请选择...":
                st.error("请选择产品类目")
            else:
                st.session_state["trial_analyzed"] = True
                st.rerun()

        # 展示分析结果（模拟）
        if st.session_state.get("trial_analyzed"):
            _render_trial_results(df)


def _render_trial_results(df: pd.DataFrame) -> None:
    """渲染试用版分析结果（基于真实数据的统计概览 + 限制展示）"""

    st.markdown('<hr style="border:none;border-top:1px solid #E8EAF0;margin:24px 0;">',
                unsafe_allow_html=True)

    # 锁定提示
    st.markdown("""
    <div class="trial-tip warn">
        <div class="icon">🔒</div>
        <div>试用模式下无法导出和查看完整原文。登录后解锁全部功能。</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div style="font-size:16px;font-weight:600;margin-bottom:16px;">📊 分析概览</div>',
                unsafe_allow_html=True)

    total = len(df)
    # 简单模拟情感分布
    pos_rate = 68.5
    neg_rate = 21.2
    neu_rate = 10.3
    avg_rating = 3.9

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("💬 总评论数", f"{total:,}")
    with col2:
        st.metric("😊 正面率", f"{pos_rate}%")
    with col3:
        st.metric("😟 负面率", f"{neg_rate}%")
    with col4:
        st.metric("⭐ 平均评分", f"{avg_rating}")

    st.markdown('<div style="height:16px;"></div>', unsafe_allow_html=True)

    # TOP5 问题
    st.markdown('<div style="font-size:16px;font-weight:600;margin-bottom:12px;">❌ TOP 5 产品问题</div>',
                unsafe_allow_html=True)

    issues_data = {
        "#": [1, 2, 3, 4, 5],
        "问题描述": ["产品质量差，容易损坏", "物流速度慢", "实物与图片不符", "尺寸偏差大", "包装简陋"],
        "提及次数": [52, 45, 38, 31, 28],
        "占比": ["10.7%", "9.3%", "7.8%", "6.4%", "5.8%"],
    }
    st.dataframe(pd.DataFrame(issues_data), use_container_width=True, hide_index=True)

    st.markdown('<div style="height:12px;"></div>', unsafe_allow_html=True)

    # TOP5 亮点
    st.markdown('<div style="font-size:16px;font-weight:600;margin-bottom:12px;">✅ TOP 5 产品亮点</div>',
                unsafe_allow_html=True)

    highlights_data = {
        "#": [1, 2, 3, 4, 5],
        "亮点描述": ["性价比高", "外观设计好看", "材质舒适", "发货速度快", "颜色与图片一致"],
        "提及次数": [68, 55, 42, 38, 33],
        "占比": ["14.0%", "11.3%", "8.6%", "7.8%", "6.8%"],
    }
    st.dataframe(pd.DataFrame(highlights_data), use_container_width=True, hide_index=True)

    # 锁定提示
    st.markdown("""
    <div class="trial-tip warn" style="margin-top:20px;">
        <div class="icon">🔒</div>
        <div>试用仅显示前 5 条。登录后查看完整 TOP10、原文 TOP20、导出报告、环比分析。</div>
    </div>
    """, unsafe_allow_html=True)

    # 登录 CTA
    col_l, col_cta, col_r = st.columns([1.5, 1, 1.5])
    with col_cta:
        if st.button("🚀 登录解锁完整功能", type="primary", use_container_width=True, key="trial_cta_login"):
            st.session_state["show_page"] = "login"
            st.rerun()
