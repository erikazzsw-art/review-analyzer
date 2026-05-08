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
from review_analyzer.pages.results import render_results
from review_analyzer.pages.copywriter import render_copywriter
from review_analyzer.pages.history import render_history
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
:root {
    --pri: #6C5CE7;
    --pri-l: #A29BFE;
    --pri-d: #5A4BD1;
    --grn: #00B894;
    --red: #FF6B6B;
    --yel: #FDCB6E;
    --blu: #74B9FF;
    --bg: #F7F8FC;
    --card: #FFFFFF;
    --txt: #2D3436;
    --txt-l: #636E72;
    --bdr: #E8EAF0;
    --shd: 0 2px 12px rgba(108, 92, 231, 0.08);
    --r: 12px;
}

/* 隐藏 Streamlit 默认元素 */
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: hidden;}

/* 隐藏标题旁的锚点链接按钮 */
.stMarkdown h1 a, .stMarkdown h2 a, .stMarkdown h3 a,
.stMarkdown h4 a, .stMarkdown h5 a, .stMarkdown h6 a,
[data-testid="stHeaderActionElements"] {
    display: none !important;
}

/* 页面背景 */
.stApp {
    background: var(--bg);
}

/* 侧边栏样式 */
[data-testid="stSidebar"] {
    background: var(--card);
    border-right: 1px solid var(--bdr);
    width: 260px !important;
}

[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p {
    font-size: 14px;
}

/* 自定义按钮 */
.stButton > button {
    border-radius: 10px;
    font-weight: 600;
    font-size: 14px;
    padding: 8px 20px;
    transition: all 0.15s;
}

/* 主色按钮 */
.stButton > button[kind="primary"] {
    background: var(--pri);
    color: white;
    border: none;
}
.stButton > button[kind="primary"]:hover {
    background: var(--pri-d);
    transform: translateY(-1px);
}

/* 表单输入框 */
.stTextInput > div > div > input,
.stSelectbox > div > div,
.stDateInput > div > div > input {
    border: 2px solid var(--bdr);
    border-radius: 10px;
    font-size: 14px;
}
.stTextInput > div > div > input:focus {
    border-color: var(--pri);
    box-shadow: none;
}

/* 指标卡片 */
.metric-card {
    background: var(--card);
    border-radius: var(--r);
    padding: 20px;
    box-shadow: var(--shd);
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
.metric-icon { font-size: 28px; margin-bottom: 8px; }
.metric-val { font-size: 28px; font-weight: 700; color: var(--txt); }
.metric-label { font-size: 13px; color: var(--txt-l); margin-top: 2px; }
.metric-change { font-size: 12px; margin-top: 6px; display: inline-block; padding: 2px 8px; border-radius: 20px; }
.metric-change.up { background: #E8F8F5; color: var(--grn); }
.metric-change.down { background: #FFEAEA; color: var(--red); }

/* 标签 */
.tag { display: inline-block; padding: 4px 12px; border-radius: 20px; font-size: 12px; font-weight: 500; margin: 2px; }
.tag-pos { background: #E8F8F5; color: var(--grn); }
.tag-neg { background: #FFEAEA; color: var(--red); }
.tag-neu { background: #FFF3E0; color: #E17055; }
.tag-topic { background: #F0EEFF; color: var(--pri); }
.tag-platform { background: #E8F0FE; color: #2D6CDF; }

/* 环比条 */
.compare-bar {
    background: #F0EEFF;
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
    background: linear-gradient(135deg, #F0EEFF, #E8F8F5);
    border-radius: var(--r);
    padding: 20px;
    margin-top: 20px;
    border-left: 4px solid var(--pri);
}
.action-card.danger {
    background: linear-gradient(135deg, #FFEAEA, #FFF3E0);
    border-left-color: var(--red);
}

/* 产品卡片 */
.product-block {
    background: var(--card);
    border-radius: 16px;
    padding: 28px;
    box-shadow: var(--shd);
    margin-bottom: 24px;
    border: 1px solid var(--bdr);
}

/* 数据表格 */
.dataframe {
    font-size: 14px !important;
}
.dataframe th {
    background: #F7F8FC !important;
    color: var(--txt-l) !important;
    font-weight: 600 !important;
}
.dataframe tr:hover td {
    background: #FAFBFF !important;
}

/* 上传区 */
[data-testid="stFileUploader"] {
    border: 2px dashed var(--pri-l);
    border-radius: var(--r);
    padding: 20px;
    background: #FAFAFF;
}
[data-testid="stFileUploader"]:hover {
    border-color: var(--pri);
    background: #F0EEFF;
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
    font-weight: 600;
    color: var(--txt-l);
    background: var(--card);
    border-bottom: 3px solid var(--bdr);
}
.step-item.active {
    color: var(--pri);
    border-bottom-color: var(--pri);
    background: #F0EEFF;
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
    box-shadow: var(--shd);
}

/* 设置区块 */
.settings-section {
    background: var(--card);
    border-radius: var(--r);
    padding: 24px;
    box-shadow: var(--shd);
    margin-bottom: 20px;
}

/* 平台卡片 */
.platform-card {
    background: #F7F8FC;
    border: 2px solid var(--bdr);
    border-radius: 12px;
    padding: 16px 12px;
    text-align: center;
    cursor: pointer;
    transition: all 0.15s;
}
.platform-card:hover {
    border-color: var(--pri-l);
    background: #F0EEFF;
}
.platform-card.active {
    border-color: var(--pri);
    background: #F0EEFF;
    box-shadow: 0 0 0 3px rgba(108, 92, 231, 0.12);
}

/* 文案卡片 */
.copy-card {
    background: #F7F8FC;
    border-radius: 12px;
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
.compliance-badge.pass { background: #E8F8F0; color: #00B894; border: 1px solid #B8F0D8; }
.compliance-badge.warn { background: #FFF3E0; color: #E67E22; border: 1px solid #FDDCB0; }

/* 历史记录布局 */
.hist-sku-item {
    padding: 10px 14px;
    border-radius: 8px;
    cursor: pointer;
    font-size: 14px;
    transition: all 0.15s;
    margin-bottom: 4px;
}
.hist-sku-item:hover { background: #F0EEFF; }
.hist-sku-item.active { background: #F0EEFF; color: var(--pri); font-weight: 600; }

/* 批次卡片 */
.batch-card {
    background: var(--card);
    border-radius: var(--r);
    padding: 16px 20px;
    box-shadow: var(--shd);
    margin-bottom: 12px;
    display: flex;
    align-items: center;
    justify-content: space-between;
}

/* 关键词云 */
.keyword { padding: 6px 14px; border-radius: 20px; font-size: 13px; background: #F0EEFF; color: var(--pri); display: inline-block; margin: 4px; }
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
    border-radius: 12px 12px 0 0;
    box-shadow: 0 -4px 20px rgba(0, 0, 0, 0.1);
    z-index: 5;
}

/* 原文展开面板 */
.source-panel {
    background: var(--card);
    border-radius: var(--r);
    padding: 20px;
    box-shadow: var(--shd);
    margin-top: 16px;
    border-left: 4px solid var(--pri);
}

/* 进度条 */
.stProgress > div > div > div {
    background: linear-gradient(90deg, var(--pri), var(--blu));
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
    border-radius: 10px;
    text-decoration: none;
}
.nav-item:hover { background: #F0EEFF; color: var(--pri); }
.nav-item.active { background: #F0EEFF; color: var(--pri); font-weight: 600; }
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

    # 侧边栏
    with st.sidebar:
        if st.button("🔍 ClueAI", key="brand_home_btn", use_container_width=True, type="secondary"):
            st.session_state["current_page"] = "dashboard"
            st.rerun()
        st.markdown("""
        <style>
        [data-testid="stSidebar"] button[kind="secondary"]:first-of-type {
            font-size: 18px;
            font-weight: 700;
            color: #6C5CE7;
            background: transparent;
            border: none;
            border-bottom: 1px solid #E8EAF0;
            border-radius: 0;
            padding: 8px 0 16px;
            margin-bottom: 12px;
            text-align: left;
            justify-content: flex-start;
        }
        [data-testid="stSidebar"] button[kind="secondary"]:first-of-type:hover {
            color: #5A4BD1;
            background: transparent;
            border-bottom: 1px solid #E8EAF0;
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
            "copywriter": ("✍️", "宣传文案"),
            "history": ("🕐", "历史记录"),
            "settings": ("⚙️", "推送设置"),
        }
        nav_items_en = {
            "dashboard": ("📊", "Dashboard"),
            "upload": ("📤", "Upload"),
            "results": ("📋", "Results"),
            "copywriter": ("✍️", "Copywriter"),
            "history": ("🕐", "History"),
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
        <div style="display:flex;align-items:center;gap:10px;margin-top:12px;font-size:14px;color:#636E72;">
            <div style="width:32px;height:32px;border-radius:50%;background:#A29BFE;
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
    elif page == "copywriter":
        render_copywriter()
    elif page == "history":
        render_history()
    elif page == "settings":
        render_settings()


if __name__ == "__main__":
    main()
