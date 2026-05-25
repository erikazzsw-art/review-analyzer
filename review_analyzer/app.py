"""ClueAI — Streamlit 主入口"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st

from review_analyzer.database import init_db
from review_analyzer.auth import is_logged_in, get_current_username, logout
from review_analyzer.pages.login import render_login_page
from review_analyzer.pages.landing import render_landing_page
from review_analyzer.pages.trial import render_trial_page
from review_analyzer.pages.dashboard import render_dashboard
from review_analyzer.pages.upload import render_upload
from review_analyzer.pages.results import render_results, render_history
from review_analyzer.pages.copywriter import render_copywriter
from review_analyzer.pages.settings import render_settings

st.set_page_config(
    page_title="ClueAI - 评论分析系统",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded",
)

init_db()

# ============================================================
# 全局 CSS — 还原 prototype 设计系统
# ============================================================

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=Montserrat:wght@400;700;800&display=swap');

:root {
    --pri: #ff682c;
    --pri-l: #ff8f66;
    --pri-d: #e55520;
    --grn: #2ecc71;
    --red: #e74c3c;
    --yel: #f39c12;
    --blu: #3498db;
    --bg: #ffffff;
    --card: #ffffff;
    --card-alt: #efefef;
    --txt: #202020;
    --txt-l: #4d4d4d;
    --txt-m: #828282;
    --bdr: #e8e8e8;
    --shd: none;
    --r: 8px;
    --font-body: 'Inter', system-ui, sans-serif;
    --font-heading: 'Montserrat', system-ui, sans-serif;
}

/* 隐藏 Streamlit 默认元素（保留 header 以确保侧边栏展开按钮可用） */
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
[data-testid="stToolbar"] {display: none !important;}
[data-testid="stDecoration"] {display: none !important;}
[data-testid="stStatusWidget"] {display: none !important;}

/* 侧边栏展开按钮 — 确保在白色背景上可见 */
[data-testid="collapsedControl"],
[data-testid="stSidebarCollapsedControl"] {
    background: #202020 !important;
    border-radius: 0 8px 8px 0 !important;
    padding: 10px !important;
    border: none !important;
}
[data-testid="collapsedControl"] svg,
[data-testid="stSidebarCollapsedControl"] svg {
    color: #ffffff !important;
    fill: #ffffff !important;
    width: 20px !important;
    height: 20px !important;
}
/* Streamlit 1.56 可能用 button 包裹 */
[data-testid="stSidebar"] + section [data-testid="collapsedControl"] button,
header button[kind="header"] {
    background: #202020 !important;
    color: #ffffff !important;
    border-radius: 0 8px 8px 0 !important;
}

/* 隐藏标题旁的锚点链接按钮 */
.stMarkdown h1 a, .stMarkdown h2 a, .stMarkdown h3 a,
.stMarkdown h4 a, .stMarkdown h5 a, .stMarkdown h6 a,
[data-testid="stHeaderActionElements"] {
    display: none !important;
}

/* 页面背景 */
.stApp {
    background: var(--bg);
    font-family: var(--font-body);
}

/* 全局字体 */
.stMarkdown, .stText, p, span, div, label {
    font-family: var(--font-body);
}
h1, h2, h3 {
    font-family: var(--font-heading);
    letter-spacing: -0.02em;
    color: var(--txt);
}

/* 侧边栏样式 */
[data-testid="stSidebar"] {
    background: #f5f5f5;
    border-right: 1px solid var(--bdr);
    width: 260px !important;
}

[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p {
    font-size: 14px;
}

/* 自定义按钮 */
.stButton > button {
    border-radius: 20px;
    font-weight: 500;
    font-size: 14px;
    padding: 8px 20px;
    transition: all 0.15s;
    font-family: var(--font-body);
    border: 1px solid var(--bdr);
}

/* 主色按钮 — ghost 风格 */
.stButton > button[kind="primary"] {
    background: transparent;
    color: var(--txt);
    border: 2px solid var(--txt);
}
.stButton > button[kind="primary"]:hover {
    background: var(--txt);
    color: #ffffff;
}

/* 表单输入框 */
.stTextInput > div > div > input,
.stSelectbox > div > div,
.stDateInput > div > div > input {
    border: 1px solid var(--bdr);
    border-radius: 8px;
    font-size: 14px;
    font-family: var(--font-body);
}
.stTextInput > div > div > input:focus {
    border-color: var(--txt);
    box-shadow: none;
}

/* 指标卡片 */
.metric-card {
    background: var(--card-alt);
    border-radius: var(--r);
    padding: 28px;
    position: relative;
    overflow: hidden;
}
.metric-card::before {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    width: 4px;
    height: 100%;
    border-radius: 4px 0 0 4px;
}
.metric-card.purple::before { background: var(--pri); }
.metric-card.green::before { background: var(--grn); }
.metric-card.red::before { background: var(--red); }
.metric-card.yellow::before { background: var(--yel); }
.metric-icon { font-size: 16px; margin-bottom: 12px; color: var(--txt-m); }
.metric-val { font-size: 32px; font-weight: 800; color: var(--txt); font-family: var(--font-heading); letter-spacing: -0.02em; }
.metric-label { font-size: 13px; color: var(--txt-l); margin-top: 6px; font-weight: 500; }
.metric-change { font-size: 12px; margin-top: 8px; display: inline-block; padding: 3px 10px; border-radius: 20px; font-weight: 500; }
.metric-change.up { background: #e8f8f0; color: var(--grn); }
.metric-change.down { background: #fdeaea; color: var(--red); }

/* 标签 */
.tag { display: inline-block; padding: 4px 12px; border-radius: 20px; font-size: 12px; font-weight: 500; margin: 2px; }
.tag-pos { background: #e8f8f0; color: var(--grn); }
.tag-neg { background: #fdeaea; color: var(--red); }
.tag-neu { background: #fef3e0; color: #e67e22; }
.tag-topic { background: #fff0eb; color: var(--pri); }
.tag-platform { background: #eef6ff; color: #2d6cdf; }

/* 环比条 */
.compare-bar {
    background: var(--card-alt);
    border-radius: var(--r);
    padding: 16px 20px;
    margin-bottom: 12px;
    display: flex;
    align-items: center;
    gap: 20px;
    flex-wrap: wrap;
    font-size: 14px;
}
.compare-bar.version { border-left: 4px solid var(--pri); }
.compare-bar.time { border-left: 4px solid var(--blu); }

/* 行动建议卡 */
.action-card {
    background: var(--card-alt);
    border-radius: var(--r);
    padding: 20px;
    margin-top: 20px;
    border-left: 4px solid var(--pri);
}
.action-card.danger {
    background: #fdeaea;
    border-left-color: var(--red);
}

/* 产品卡片 */
.product-block {
    background: var(--card);
    border-radius: 12px;
    padding: 32px;
    margin-bottom: 28px;
    border: 1px solid var(--bdr);
}

/* 数据表格 */
.dataframe {
    font-size: 14px !important;
    font-family: var(--font-body) !important;
}
.dataframe th {
    background: #f5f5f5 !important;
    color: var(--txt-l) !important;
    font-weight: 600 !important;
}
.dataframe tr:hover td {
    background: #f5f5f5 !important;
}

/* 上传区 */
[data-testid="stFileUploader"] {
    border: 2px dashed var(--bdr);
    border-radius: var(--r);
    padding: 20px;
    background: #f5f5f5;
}
[data-testid="stFileUploader"]:hover {
    border-color: var(--pri);
    background: #fff0eb;
}

/* 步骤指示器 */
.step-indicator {
    display: flex;
    gap: 0;
    margin-bottom: 28px;
}
.step-item {
    flex: 1;
    text-align: center;
    padding: 12px;
    font-size: 14px;
    font-weight: 500;
    color: var(--txt-m);
    background: var(--card);
    border-bottom: 3px solid var(--bdr);
    font-family: var(--font-body);
}
.step-item.active {
    color: var(--txt);
    border-bottom-color: var(--pri);
    background: #fff0eb;
}
.step-item.done {
    color: var(--grn);
    border-bottom-color: var(--grn);
}

/* 图表卡片 */
.chart-card {
    background: var(--card);
    border-radius: var(--r);
    padding: 20px;
    border: 1px solid var(--bdr);
}

/* 设置区块 */
.settings-section {
    background: var(--card);
    border-radius: var(--r);
    padding: 24px;
    border: 1px solid var(--bdr);
    margin-bottom: 20px;
}

/* 平台卡片 */
.platform-card {
    background: #f5f5f5;
    border: 1px solid var(--bdr);
    border-radius: 8px;
    padding: 16px 12px;
    text-align: center;
    cursor: pointer;
    transition: all 0.15s;
}
.platform-card:hover {
    border-color: var(--pri);
    background: #fff0eb;
}
.platform-card.active {
    border-color: var(--pri);
    background: #fff0eb;
}

/* 文案卡片 */
.copy-card {
    background: #f5f5f5;
    border-radius: 8px;
    padding: 20px;
    margin-bottom: 14px;
}

/* 合规徽章 */
.compliance-badge {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    padding: 3px 10px;
    border-radius: 20px;
    font-size: 11px;
    font-weight: 600;
}
.compliance-badge.pass { background: #e8f8f0; color: var(--grn); border: 1px solid #b8f0d8; }
.compliance-badge.warn { background: #fef3e0; color: #e67e22; border: 1px solid #fddcb0; }

/* 历史记录布局 */
.hist-sku-item {
    padding: 10px 14px;
    border-radius: 8px;
    cursor: pointer;
    font-size: 14px;
    transition: all 0.15s;
    margin-bottom: 4px;
}
.hist-sku-item:hover { background: #fff0eb; }
.hist-sku-item.active { background: #fff0eb; color: var(--pri); font-weight: 600; }

/* 批次卡片 */
.batch-card {
    background: var(--card);
    border-radius: var(--r);
    padding: 16px 20px;
    border: 1px solid var(--bdr);
    margin-bottom: 12px;
    display: flex;
    align-items: center;
    justify-content: space-between;
}

/* 关键词云 */
.keyword { padding: 6px 14px; border-radius: 20px; font-size: 13px; background: #fff0eb; color: var(--pri); display: inline-block; margin: 4px; }
.keyword.lg { font-size: 18px; font-weight: 600; padding: 8px 18px; }
.keyword.md { font-size: 15px; font-weight: 500; }
.keyword.sm { font-size: 12px; }

/* 浮动操作栏 */
.float-bar {
    position: sticky;
    bottom: 0;
    background: var(--card);
    border-top: 2px solid var(--pri);
    padding: 12px 20px;
    border-radius: 8px 8px 0 0;
    box-shadow: 0 -4px 20px rgba(0, 0, 0, 0.06);
    z-index: 5;
}

/* 原文展开面板 */
.source-panel {
    background: var(--card);
    border-radius: var(--r);
    padding: 20px;
    border: 1px solid var(--bdr);
    margin-top: 16px;
    border-left: 4px solid var(--pri);
}

/* 进度条 */
.stProgress > div > div > div {
    background: var(--pri);
}

/* 侧边栏导航项 */
.nav-item {
    padding: 12px 20px;
    display: flex;
    align-items: center;
    gap: 12px;
    cursor: pointer;
    transition: all 0.15s;
    font-size: 15px;
    color: var(--txt-l);
    margin: 2px 8px;
    border-radius: 8px;
    text-decoration: none;
    font-family: var(--font-body);
}
.nav-item:hover { background: #fff0eb; color: var(--pri); }
.nav-item.active { background: #fff0eb; color: var(--pri); font-weight: 600; }
</style>
""", unsafe_allow_html=True)


# ============================================================
# 路由逻辑
# ============================================================

def main() -> None:
    if not is_logged_in():
        show_page = st.session_state.get("show_page", "landing")
        if show_page == "login":
            render_login_page()
        elif show_page == "trial":
            render_trial_page()
        else:
            render_landing_page()
        return

    # 侧边栏 — 强制覆盖 landing/login/trial 页面的隐藏样式
    st.markdown("""
    <style>
    section[data-testid="stSidebar"] {
        display: flex !important;
        visibility: visible !important;
        opacity: 1 !important;
        width: 260px !important;
        min-width: 260px !important;
        transform: none !important;
        position: relative !important;
    }
    section[data-testid="stSidebar"] > div {
        display: block !important;
        visibility: visible !important;
    }
    </style>
    """, unsafe_allow_html=True)

    with st.sidebar:
        if st.button("ClueAI", key="brand_home_btn", use_container_width=True, type="secondary"):
            st.session_state["current_page"] = "dashboard"
            st.rerun()
        st.markdown("""
        <style>
        [data-testid="stSidebar"] button[kind="secondary"]:first-of-type {
            font-size: 18px;
            font-weight: 700;
            color: #202020;
            font-family: 'Montserrat', system-ui, sans-serif;
            letter-spacing: -0.02em;
            background: transparent;
            border: none;
            border-bottom: 1px solid #e8e8e8;
            border-radius: 0;
            padding: 8px 0 16px;
            margin-bottom: 12px;
            text-align: left;
            justify-content: flex-start;
        }
        [data-testid="stSidebar"] button[kind="secondary"]:first-of-type:hover {
            color: #ff682c;
            background: transparent;
            border-bottom: 1px solid #e8e8e8;
        }
        </style>
        """, unsafe_allow_html=True)

        if "lang" not in st.session_state:
            st.session_state["lang"] = "zh"

        lang = st.session_state["lang"]

        nav_items_zh = {
            "dashboard": ("📊", "仪表盘"),
            "upload": ("📤", "上传评论"),
            "results": ("📋", "分析结果"),
            "history": ("🕘", "历史记录"),
            "copywriter": ("✍️", "宣传文案"),
            "settings": ("⚙️", "推送设置"),
        }
        nav_items_en = {
            "dashboard": ("📊", "Dashboard"),
            "upload": ("📤", "Upload"),
            "results": ("📋", "Results"),
            "history": ("🕘", "History"),
            "copywriter": ("✍️", "Copywriter"),
            "settings": ("⚙️", "Settings"),
        }
        nav_items = nav_items_zh if lang == "zh" else nav_items_en

        if "current_page" not in st.session_state:
            st.session_state["current_page"] = "dashboard"

        for page_id, (icon, label) in nav_items.items():
            is_active = st.session_state["current_page"] == page_id
            if st.button(
                f"{icon}  {label}",
                key=f"nav_{page_id}",
                use_container_width=True,
                type="primary" if is_active else "secondary",
            ):
                st.session_state["current_page"] = page_id
                st.rerun()

        st.markdown("---")

        # 语言切换
        col_lang1, col_lang2 = st.columns(2)
        with col_lang1:
            btn_type_zh = "primary" if lang == "zh" else "secondary"
            if st.button("中文", key="lang_zh", use_container_width=True, type=btn_type_zh):
                st.session_state["lang"] = "zh"
                st.rerun()
        with col_lang2:
            btn_type_en = "primary" if lang == "en" else "secondary"
            if st.button("EN", key="lang_en", use_container_width=True, type=btn_type_en):
                st.session_state["lang"] = "en"
                st.rerun()

        # 用户信息
        username = get_current_username() or "User"
        st.markdown(f"""
        <div style="display:flex;align-items:center;gap:10px;margin-top:12px;font-size:14px;color:#4d4d4d;">
            <div style="width:32px;height:32px;border-radius:50%;background:#ff682c;
                        display:flex;align-items:center;justify-content:center;
                        font-size:14px;color:#fff;">{username[0].upper()}</div>
            <span>{username}</span>
        </div>
        """, unsafe_allow_html=True)

        logout_label = "退出登录" if lang == "zh" else "Logout"
        if st.button(logout_label, key="logout_btn"):
            logout()
            st.rerun()

    # 页面分发
    page = st.session_state.get("current_page", "dashboard")
    if page == "dashboard":
        render_dashboard()
    elif page == "upload":
        render_upload()
    elif page == "results":
        render_results()
    elif page == "history":
        render_history()
    elif page == "copywriter":
        render_copywriter()
    elif page == "settings":
        render_settings()


if __name__ == "__main__":
    main()
