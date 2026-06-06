"""免费试用页面。"""

from __future__ import annotations

import os
import tempfile

import pandas as pd
import streamlit as st

from review_analyzer.i18n import pick, t
from review_analyzer.parser import parse_file


def render_trial_page() -> None:
    st.markdown(
        """
        <style>
        [data-testid="stSidebar"] { display: none; }
        .stApp { background: linear-gradient(180deg, #fffaf8 0%, #fff6f7 48%, #f8f4ff 100%); }
        .trial-shell {
            max-width: 1140px;
            margin: 0 auto;
            padding: 12px 12px 44px;
            font-family: 'Inter', system-ui, sans-serif;
        }
        .trial-topbar {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 16px;
            margin-bottom: 18px;
        }
        .trial-brand {
            display: inline-flex;
            align-items: center;
            gap: 12px;
        }
        .trial-mark {
            width: 42px;
            height: 42px;
            border-radius: 16px;
            background: linear-gradient(135deg, #f36f8f, #8d7be8);
            color: #ffffff;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            font-family: 'Montserrat', system-ui, sans-serif;
            font-weight: 800;
            font-size: 16px;
            box-shadow: 0 16px 34px rgba(121, 88, 137, 0.18);
        }
        .trial-brand strong {
            display: block;
            font-family: 'Montserrat', system-ui, sans-serif;
            font-size: 20px;
            letter-spacing: -0.02em;
            color: #25212a;
        }
        .trial-brand span {
            display: block;
            margin-top: 2px;
            font-size: 13px;
            color: #7b7384;
        }
        .trial-note {
            display: inline-flex;
            align-items: center;
            padding: 8px 12px;
            border-radius: 999px;
            border: 1px solid #ebe4ee;
            background: rgba(255,255,255,0.8);
            color: #7b7384;
            font-size: 13px;
        }
        .trial-card,
        .trial-hero {
            background: rgba(255,255,255,0.86);
            border: 1px solid #ebe4ee;
            border-radius: 28px;
            box-shadow: 0 20px 52px rgba(96, 63, 88, 0.10);
            backdrop-filter: blur(10px);
        }
        .trial-hero {
            padding: 30px 30px 24px;
            margin-bottom: 18px;
            background: linear-gradient(135deg, #ffffff 0%, #fff6f7 54%, #f6f2ff 100%);
        }
        .trial-eyebrow {
            display: inline-flex;
            align-items: center;
            padding: 7px 13px;
            border-radius: 999px;
            background: #fff1f5;
            color: #d94d72;
            font-size: 12px;
            font-weight: 700;
            margin-bottom: 14px;
        }
        .trial-hero h1 {
            margin: 0;
            font-family: 'Montserrat', system-ui, sans-serif;
            font-size: 38px;
            line-height: 1.08;
            letter-spacing: -0.03em;
            color: #25212a;
        }
        .trial-hero p {
            margin: 14px 0 0;
            max-width: 760px;
            font-size: 14px;
            line-height: 1.76;
            color: #6f6877;
        }
        .trial-limit {
            margin-top: 18px;
            padding: 16px 18px;
            border-radius: 20px;
            border: 1px solid #f0dfd1;
            background: linear-gradient(180deg, #fff8ef 0%, #fffefb 100%);
            color: #7b6f66;
            font-size: 13px;
            line-height: 1.7;
        }
        .trial-card {
            padding: 24px;
            margin-bottom: 16px;
        }
        .trial-card h2 {
            margin: 0 0 8px;
            font-family: 'Montserrat', system-ui, sans-serif;
            font-size: 24px;
            color: #25212a;
            letter-spacing: -0.03em;
        }
        .trial-card p {
            margin: 0 0 18px;
            font-size: 14px;
            line-height: 1.72;
            color: #6f6877;
        }
        .trial-divider {
            height: 1px;
            background: #eee5f1;
            margin: 20px 0;
        }
        .trial-result-section {
            margin-top: 16px;
        }
        @media (max-width: 980px) {
            .trial-topbar {
                align-items: flex-start;
                flex-direction: column;
            }
            .trial-hero h1 { font-size: 32px; }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        pick(
            """
        <div class="trial-shell">
            <div class="trial-topbar">
                <div class="trial-brand">
                    <div class="trial-mark">C</div>
                    <div>
                        <strong>ClueAI</strong>
                        <span>试用入口也已对齐系统内的 V2 风格</span>
                    </div>
                </div>
                <div class="trial-note">试用模式 · 单次体验，不保存历史</div>
            </div>
            <div class="trial-hero">
                <div class="trial-eyebrow">先熟悉流程，再进入完整工作台</div>
                <h1>上传一份评论文件，先体验核心分析链路。</h1>
                <p>试用版保留真实的上传、解析和结果预览逻辑，但不保存历史记录，也不开放导出、完整原文和环比对比。适合先确认界面和流程，再决定是否进入完整账号。</p>
                <div class="trial-limit">试用限制：单次最多读取 500 条评论，只展示简化版结果。登录后可解锁完整工作台、历史记录、对比分析和行动闭环。</div>
            </div>
        </div>
        """,
            """
        <div class="trial-shell">
            <div class="trial-topbar">
                <div class="trial-brand">
                    <div class="trial-mark">C</div>
                    <div>
                        <strong>ClueAI</strong>
                        <span>The trial entry now matches the in-app V2 style</span>
                    </div>
                </div>
                <div class="trial-note">Trial mode · one-time experience, no history saved</div>
            </div>
            <div class="trial-hero">
                <div class="trial-eyebrow">Learn the flow first, then move into the full workspace</div>
                <h1>Upload one review file and experience the core analysis workflow.</h1>
                <p>The trial preserves the real upload, parsing, and preview logic, but does not save history or unlock exports, full raw reviews, or comparison analysis. It is designed to help you confirm the flow before moving into a full account.</p>
                <div class="trial-limit">Trial limit: up to 500 reviews per run, with a simplified results view only. Log in to unlock the full workspace, history, comparisons, and action loop.</div>
            </div>
        </div>
        """,
        ),
        unsafe_allow_html=True,
    )

    _render_workspace_return()

    col_back, col_login = st.columns([4, 1])
    with col_login:
        if st.button(pick("去登录", "Go to Login"), key="trial_to_login", use_container_width=True):
            st.session_state["show_page"] = "login"
            st.rerun()

    st.markdown(
        pick(
            """
        <div class="trial-shell">
            <div class="trial-card">
                <h2>试用信息</h2>
                <p>先填最基本的产品信息，再上传文件。这个页面的行为保持原样，只是视觉和系统内统一了。</p>
            </div>
        </div>
        """,
            """
        <div class="trial-shell">
            <div class="trial-card">
                <h2>Trial Setup</h2>
                <p>Fill in the basic product info first, then upload your file. The flow stays the same, but now matches the in-app experience visually.</p>
            </div>
        </div>
        """,
        ),
        unsafe_allow_html=True,
    )

    col1, col2 = st.columns(2)
    with col1:
        trial_product_id = st.text_input(
            pick("产品编号 *", "Product ID *"),
            placeholder=pick("SKU 或任何可识别该产品的唯一编码", "SKU or any unique identifier for this product"),
            key="trial_product_id",
        )
    with col2:
        trial_product_name = st.text_input(pick("产品中文名称", "Product Name"), placeholder=pick("选填", "Optional"), key="trial_product_name")

    col3, col4 = st.columns(2)
    with col3:
        trial_platform = st.selectbox(
            pick("平台来源 *", "Platform *"),
            pick(["请选择...", "Amazon", "Shopee", "Temu", "eBay", "AliExpress", "Walmart"], ["Please select...", "Amazon", "Shopee", "Temu", "eBay", "AliExpress", "Walmart"]),
            key="trial_platform",
        )
    with col4:
        trial_category = st.selectbox(
            pick("产品类目 *", "Category *"),
            pick(
                ["请选择...", "电子产品", "服装鞋帽", "家居用品", "美妆个护", "运动户外", "食品保健", "母婴用品", "其他"],
                ["Please select...", "Electronics", "Fashion", "Home Goods", "Beauty & Personal Care", "Sports & Outdoors", "Food & Wellness", "Baby Products", "Other"],
            ),
            key="trial_category",
        )

    st.markdown("<div class='trial-divider'></div>", unsafe_allow_html=True)

    uploaded_file = st.file_uploader(
        pick("上传评论文件", "Upload Review File"),
        type=["csv", "xlsx", "xls"],
        key="trial_upload",
        help=pick("支持 CSV / XLSX，试用限制 500 条", "Supports CSV / XLSX. Trial limit: 500 reviews."),
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
                    st.warning(pick("试用模式限制 500 条，已截取前 500 条数据。", "Trial mode is limited to 500 reviews. The first 500 have been loaded."))
                st.session_state["trial_df"] = df
            except Exception as exc:
                st.error(pick(f"文件解析出错：{exc}", f"File parsing failed: {exc}"))
                return

        df = st.session_state["trial_df"]
        st.markdown(
            pick(
                """
            <div class="trial-card trial-result-section">
                <h2>文件预览</h2>
                <p>先确认解析出的字段是否正常，再开始试用分析。</p>
            </div>
            """,
                """
            <div class="trial-card trial-result-section">
                <h2>File Preview</h2>
                <p>Check that the parsed fields look correct before starting the trial analysis.</p>
            </div>
            """,
            ),
            unsafe_allow_html=True,
        )
        st.dataframe(df.head(5), use_container_width=True)
        st.caption(pick(f"当前已读取 {len(df)} 条评论", f"{len(df)} reviews loaded"))

        _, button_col = st.columns([3, 1])
        with button_col:
            analyze_clicked = st.button(pick("开始分析", "Start Analysis"), type="primary", use_container_width=True, key="trial_analyze")

        if analyze_clicked:
            if not trial_product_id:
                st.error(pick("请填写产品编号", "Please enter a product ID."))
            elif trial_platform == pick("请选择...", "Please select..."):
                st.error(pick("请选择平台来源", "Please select a platform."))
            elif trial_category == pick("请选择...", "Please select..."):
                st.error(pick("请选择产品类目", "Please select a category."))
            else:
                st.session_state["trial_analyzed"] = True
                st.rerun()

        if st.session_state.get("trial_analyzed"):
            _render_trial_results(df)


def _render_trial_results(df: pd.DataFrame) -> None:
    st.markdown(
        pick(
            """
        <div class="trial-card trial-result-section">
            <h2>试用结果概览</h2>
            <p>这里展示的是简化版结果，用来帮助你快速感受产品的结构和阅读方式。</p>
        </div>
        """,
            """
        <div class="trial-card trial-result-section">
            <h2>Trial Results Overview</h2>
            <p>This is a simplified results view to help you quickly understand the product structure and reading flow.</p>
        </div>
        """,
        ),
        unsafe_allow_html=True,
    )

    total = len(df)
    pos_rate = 68.5
    neg_rate = 21.2
    neu_rate = 10.3
    avg_rating = 3.9

    metric_cols = st.columns(4)
    with metric_cols[0]:
        st.metric(pick("总评论数", "Total Reviews"), f"{total:,}")
    with metric_cols[1]:
        st.metric(pick("正面率", "Positive Rate"), f"{pos_rate}%")
    with metric_cols[2]:
        st.metric(pick("负面率", "Negative Rate"), f"{neg_rate}%")
    with metric_cols[3]:
        st.metric(pick("平均评分", "Average Rating"), f"{avg_rating}")

    st.caption(pick(f"中性/其他占比 {neu_rate}%", f"Neutral / other: {neu_rate}%"))

    st.markdown(f"### {pick('TOP 5 产品问题', 'Top 5 Issues')}")
    issues_data = {
        "#": [1, 2, 3, 4, 5],
        pick("问题描述", "Issue"): ["产品质量差，容易损坏", "物流速度慢", "实物与图片不符", "尺寸偏差大", "包装简陋"] if pick(True, False) else ["Poor product quality and easy damage", "Slow shipping", "Product does not match photos", "Large size deviation", "Basic packaging"],
        pick("提及次数", "Mentions"): [52, 45, 38, 31, 28],
        pick("占比", "Share"): ["10.7%", "9.3%", "7.8%", "6.4%", "5.8%"],
    }
    st.dataframe(pd.DataFrame(issues_data), use_container_width=True, hide_index=True)

    st.markdown(f"### {pick('TOP 5 产品亮点', 'Top 5 Highlights')}")
    highlights_data = {
        "#": [1, 2, 3, 4, 5],
        pick("亮点描述", "Highlight"): ["性价比高", "外观设计好看", "材质舒适", "发货速度快", "颜色与图片一致"] if pick(True, False) else ["Great value for money", "Attractive design", "Comfortable materials", "Fast delivery", "Color matches the images"],
        pick("提及次数", "Mentions"): [68, 55, 42, 38, 33],
        pick("占比", "Share"): ["14.0%", "11.3%", "8.6%", "7.8%", "6.8%"],
    }
    st.dataframe(pd.DataFrame(highlights_data), use_container_width=True, hide_index=True)

    st.warning(
        pick(
            "试用版只展示简化结果。登录后可查看完整 TOP10、原文溯源、导出、历史记录和环比分析。",
            "The trial shows a simplified results view only. Log in to unlock the full Top 10, raw review traceability, exports, history, and comparison analysis.",
        )
    )

    col_left, col_login, col_right = st.columns([1.8, 1.2, 1.8])
    with col_login:
        if st.button(pick("登录解锁完整功能", "Log In to Unlock Full Features"), type="primary", use_container_width=True, key="trial_cta_login"):
            st.session_state["show_page"] = "login"
            st.rerun()


def _render_workspace_return() -> None:
    if not st.session_state.get("is_logged_in"):
        return

    col_left, col_button = st.columns([4.2, 1.2])
    with col_button:
        if st.button(t("back_to_workspace"), key="trial_back_to_workspace", use_container_width=True):
            st.session_state.pop("force_public_preview", None)
            st.session_state["current_page"] = "dashboard"
            st.rerun()
