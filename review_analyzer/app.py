"""ClueAI — Streamlit 主入口"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st

from review_analyzer.auth import is_logged_in, get_current_username, logout
from review_analyzer.database import init_db
from review_analyzer.i18n import nav_items, set_lang, t
from review_analyzer.pages.login import render_login_page
from review_analyzer.pages.landing import render_landing_page
from review_analyzer.pages.trial import render_trial_page
from review_analyzer.pages.dashboard import render_dashboard
from review_analyzer.pages.products import render_products
from review_analyzer.pages.upload import render_upload
from review_analyzer.pages.analysis_hub import render_analysis_hub
from review_analyzer.pages.actions import render_actions
from review_analyzer.pages.reviews import render_reviews
from review_analyzer.pages.copywriter import render_copywriter
from review_analyzer.pages.rag_library import render_rag_library
from review_analyzer.pages.settings import render_settings

ANALYSIS_LEGACY_PAGES = {"results", "compare", "history", "features"}

st.set_page_config(
    page_title="ClueAI - Review Analysis System",
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
    --pri: #f36f8f;
    --pri-l: #ffd6e0;
    --pri-d: #d94d72;
    --grn: #4fb99f;
    --red: #db5b63;
    --yel: #d8963e;
    --blu: #5e93d8;
    --lav: #8d7be8;
    --bg: #fffaf8;
    --card: #ffffff;
    --card-alt: #fff6f7;
    --txt: #25212a;
    --txt-l: #6f6877;
    --txt-m: #9b94a5;
    --bdr: #ebe4ee;
    --shd: 0 18px 50px rgba(79, 58, 93, 0.12);
    --r: 22px;
    --font-body: 'Inter', system-ui, sans-serif;
    --font-heading: 'Montserrat', system-ui, sans-serif;
}

/* 隐藏 Streamlit 默认元素（保留 header 以确保侧边栏展开按钮可用） */
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
[data-testid="stToolbar"] {display: none !important;}
[data-testid="stDecoration"] {display: none !important;}
[data-testid="stStatusWidget"] {display: none !important;}
[data-testid="stToolbarActions"] {display: none !important;}
div[data-testid="stStatusWidget"] {display: none !important;}
.stApp > header [data-testid="stStatusWidget"] {display: none !important;}

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
    background: #fff6f7;
    border-right: 1px solid #f2dde5;
    width: 260px !important;
}

[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p {
    font-size: 14px;
}

/* 自定义按钮 */
.stButton > button {
    min-height: 44px;
    border-radius: 999px;
    font-weight: 700;
    font-size: 14px;
    padding: 0 18px;
    transition: transform 0.2s ease, box-shadow 0.2s ease, background 0.2s ease;
    font-family: var(--font-body);
    border: 1px solid var(--bdr);
    box-shadow: none;
}
.stButton > button:hover { transform: translateY(-1px); }

/* 主色按钮 */
.stButton > button[kind="primary"] {
    background: var(--txt);
    color: #ffffff;
    border-color: var(--txt);
    box-shadow: 0 12px 24px rgba(37, 33, 42, 0.16);
}
.stButton > button[kind="primary"]:hover {
    background: #1f1b24;
    border-color: #1f1b24;
}
.stButton > button[kind="secondary"] {
    background: #ffffff;
    color: var(--txt);
    border-color: var(--bdr);
}
.stButton > button[kind="secondary"]:hover {
    background: #fff6f7;
    border-color: #f2dde5;
}

/* 表单输入框 */
.stTextInput > div > div > input,
.stSelectbox > div > div,
.stDateInput > div > div > input {
    border: 1.5px solid var(--bdr);
    border-radius: 14px;
    font-size: 14px;
    font-family: var(--font-body);
    background: #ffffff;
}
.stTextInput > div > div > input:focus {
    border-color: var(--pri);
    box-shadow: none;
}

/* 指标卡片 */
.metric-card {
    background: #ffffff;
    border-radius: var(--r);
    padding: 18px 18px 16px;
    position: relative;
    overflow: hidden;
    border: 1px solid var(--bdr);
    box-shadow: 0 12px 28px rgba(88, 69, 97, 0.07);
}
.metric-card::before {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    width: 4px;
    height: 100%;
    border-radius: 8px 0 0 8px;
}
.metric-card.purple::before { background: var(--lav); }
.metric-card.green::before { background: var(--grn); }
.metric-card.red::before { background: var(--red); }
.metric-card.yellow::before { background: var(--yel); }
.metric-icon { font-size: 16px; margin-bottom: 12px; color: var(--txt-m); }
.metric-val { font-size: 28px; font-weight: 800; color: var(--txt); font-family: var(--font-heading); letter-spacing: -0.03em; }
.metric-label { font-size: 12px; color: var(--txt-l); margin-top: 6px; font-weight: 700; }
.metric-change { font-size: 12px; margin-top: 8px; display: inline-block; padding: 3px 10px; border-radius: 20px; font-weight: 500; }
.metric-change.up { background: #e8f8f0; color: var(--grn); }
.metric-change.down { background: #fdeaea; color: var(--red); }

/* 标签 */
.tag { display: inline-block; padding: 4px 12px; border-radius: 20px; font-size: 12px; font-weight: 500; margin: 2px; }
.tag-pos { background: #e8f8f0; color: var(--grn); }
.tag-neg { background: #fdeaea; color: var(--red); }
.tag-neu { background: #fef3e0; color: #e67e22; }
.tag-topic { background: #ffeaf0; color: var(--pri-d); }
.tag-platform { background: #edf4ff; color: #346eb8; }

/* 环比条 */
.compare-bar {
    background: #fff7fb;
    border-radius: var(--r);
    padding: 16px 20px;
    margin-bottom: 12px;
    display: flex;
    align-items: center;
    gap: 20px;
    flex-wrap: wrap;
    font-size: 14px;
    border: 1px solid var(--bdr);
    box-shadow: 0 10px 22px rgba(96, 63, 88, 0.06);
}
.compare-bar.version { border-left: 4px solid var(--lav); }
.compare-bar.time { border-left: 4px solid var(--blu); }

/* 行动建议卡 */
.action-card {
    background: linear-gradient(135deg, #fff4f7, #fff9ef 58%, #eef8f4);
    border-radius: var(--r);
    padding: 20px;
    margin-top: 20px;
    border: 1px solid var(--bdr);
    border-left: 4px solid var(--pri);
    box-shadow: 0 14px 32px rgba(94, 70, 92, 0.08);
}
.action-card.danger {
    background: linear-gradient(135deg, #fff1f3, #fff8f0);
    border-left-color: var(--red);
}

/* 产品卡片 */
.product-block {
    background: var(--card);
    border-radius: var(--r);
    padding: 32px;
    margin-bottom: 28px;
    border: 1px solid var(--bdr);
    box-shadow: var(--shd);
}

/* 数据表格 */
.dataframe {
    font-size: 14px !important;
    font-family: var(--font-body) !important;
}
.dataframe th {
    background: #fff7fb !important;
    color: var(--txt-l) !important;
    font-weight: 600 !important;
}
.dataframe tr:hover td {
    background: #fff9fc !important;
}

/* 上传区 */
[data-testid="stFileUploader"] {
    border: 1.5px dashed #e7b8c7;
    border-radius: var(--r);
    padding: 20px;
    background: #fff8fa;
}
[data-testid="stFileUploader"]:hover {
    border-color: var(--pri);
    background: #fff2f7;
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
    font-weight: 700;
    color: var(--txt-m);
    background: #ffffff;
    border: 1px solid var(--bdr);
    font-family: var(--font-body);
    border-radius: 18px;
}
.step-item.active {
    color: var(--txt);
    border-color: #ffc5d3;
    background: #fff5f7;
}
.step-item.done {
    color: var(--grn);
    border-color: #bfe8dc;
    background: #effaf6;
}

/* 图表卡片 */
.chart-card {
    background: var(--card);
    border-radius: var(--r);
    padding: 20px;
    border: 1px solid var(--bdr);
    box-shadow: 0 12px 28px rgba(88, 69, 97, 0.07);
}

/* 设置区块 */
.settings-section {
    background: var(--card);
    border-radius: var(--r);
    padding: 24px;
    border: 1px solid var(--bdr);
    margin-bottom: 20px;
    box-shadow: 0 12px 28px rgba(88, 69, 97, 0.07);
}

/* 平台卡片 */
.platform-card {
    background: #fff;
    border: 1px solid var(--bdr);
    border-radius: 18px;
    padding: 16px 12px;
    text-align: center;
    cursor: pointer;
    transition: all 0.15s;
    box-shadow: 0 10px 22px rgba(88, 69, 97, 0.05);
}
.platform-card:hover {
    border-color: var(--pri);
    background: #fff5f7;
}
.platform-card.active {
    border-color: var(--pri);
    background: #fff5f7;
}

/* 文案卡片 */
.copy-card {
    background: #ffffff;
    border-radius: 18px;
    padding: 20px;
    margin-bottom: 14px;
    border: 1px solid var(--bdr);
    box-shadow: 0 12px 28px rgba(88, 69, 97, 0.06);
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
    border-radius: 16px;
    cursor: pointer;
    font-size: 14px;
    transition: all 0.15s;
    margin-bottom: 4px;
}
.hist-sku-item:hover { background: #fff5f7; }
.hist-sku-item.active { background: #fff5f7; color: var(--pri-d); font-weight: 700; }

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
    box-shadow: 0 12px 24px rgba(88, 69, 97, 0.06);
}

/* 关键词云 */
.keyword { padding: 6px 14px; border-radius: 20px; font-size: 13px; background: #ffeaf0; color: var(--pri-d); display: inline-block; margin: 4px; }
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
    border-radius: 18px 18px 0 0;
    box-shadow: 0 -12px 28px rgba(88, 69, 97, 0.08);
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
    box-shadow: 0 12px 24px rgba(88, 69, 97, 0.06);
}

/* 进度条 */
.stProgress > div > div > div {
    background: linear-gradient(90deg, var(--pri), var(--lav));
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
    if "lang" not in st.session_state:
        st.session_state["lang"] = "zh"

    show_page = st.session_state.get("show_page", "landing")
    is_public_preview = bool(st.session_state.get("force_public_preview"))

    landing_preview_variant = str(st.session_state.get("landing_preview_variant", "current"))

    if not is_logged_in():
        st.session_state.pop("force_public_preview", None)
        if show_page == "login":
            render_login_page()
        elif show_page == "trial":
            render_trial_page()
        else:
            st.session_state["landing_preview_variant"] = "refresh"
            render_landing_page()
        return

    if is_public_preview and show_page in {"landing", "login", "trial"}:
        if show_page == "login":
            render_login_page()
        elif show_page == "trial":
            render_trial_page()
        else:
            st.session_state["landing_preview_variant"] = landing_preview_variant
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
        if st.button(t("brand_button"), key="brand_home_btn", use_container_width=True, type="secondary"):
            st.session_state.pop("force_public_preview", None)
            st.session_state["current_page"] = "dashboard"
            st.rerun()
        st.markdown("""
        <style>
        [data-testid="stSidebar"] button[kind="secondary"]:first-of-type {
            font-size: 18px;
            font-weight: 900;
            color: #25212a;
            font-family: 'Montserrat', system-ui, sans-serif;
            letter-spacing: -0.02em;
            background: transparent;
            border: none;
            border-bottom: 1px solid #ebe4ee;
            border-radius: 0;
            padding: 8px 0 16px;
            margin-bottom: 12px;
            text-align: left;
            justify-content: flex-start;
        }
        [data-testid="stSidebar"] button[kind="secondary"]:first-of-type:hover {
            color: #d94d72;
            background: transparent;
            border-bottom: 1px solid #ebe4ee;
        }
        [data-testid="stSidebar"] button[kind="primary"] {
            background: #ffffff !important;
            color: #25212a !important;
            border: 1px solid #ebe4ee !important;
            box-shadow: 0 8px 20px rgba(96, 63, 88, 0.08) !important;
        }
        [data-testid="stSidebar"] button[kind="secondary"] {
            background: transparent !important;
            color: #6f6877 !important;
            border: 1px solid transparent !important;
        }
        [data-testid="stSidebar"] button[kind="secondary"]:not(:first-of-type):hover {
            background: #ffffff !important;
            color: #25212a !important;
            border-color: #ebe4ee !important;
        }
        </style>
        """, unsafe_allow_html=True)

        if "current_page" not in st.session_state:
            st.session_state["current_page"] = "dashboard"

        current_page = str(st.session_state.get("current_page", "dashboard"))
        if current_page in ANALYSIS_LEGACY_PAGES:
            legacy_subpage = "results" if current_page == "features" else current_page
            st.session_state["current_page"] = "analysis"
            st.session_state["analysis_subpage"] = legacy_subpage

        for page_id, (icon, label) in nav_items().items():
            current_page = st.session_state["current_page"]
            is_active = current_page == page_id
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
            btn_type_zh = "primary" if st.session_state["lang"] == "zh" else "secondary"
            if st.button(t("language_zh"), key="lang_zh", use_container_width=True, type=btn_type_zh):
                set_lang("zh")
                st.rerun()
        with col_lang2:
            btn_type_en = "primary" if st.session_state["lang"] == "en" else "secondary"
            if st.button(t("language_en"), key="lang_en", use_container_width=True, type=btn_type_en):
                set_lang("en")
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

        if st.button(t("preview_landing"), key="preview_public_pages_btn", use_container_width=True):
            st.session_state["force_public_preview"] = True
            st.session_state["show_page"] = "landing"
            st.session_state["landing_preview_variant"] = "current"
            st.rerun()

        if st.button(t("preview_landing_new"), key="preview_public_pages_v2_btn", use_container_width=True):
            st.session_state["force_public_preview"] = True
            st.session_state["show_page"] = "landing"
            st.session_state["landing_preview_variant"] = "refresh"
            st.rerun()

        if st.button(t("logout"), key="logout_btn"):
            logout()
            st.rerun()

    # 页面分发
    page = st.session_state.get("current_page", "dashboard")
    if page == "dashboard":
        render_dashboard()
    elif page == "products":
        render_products()
    elif page == "upload":
        render_upload()
    elif page == "analysis":
        render_analysis_hub()
    elif page == "rag":
        render_rag_library()
    elif page == "actions":
        render_actions()
    elif page == "reviews":
        render_reviews()
    elif page == "copywriter":
        render_copywriter()
    elif page == "settings":
        render_settings()


if __name__ == "__main__":
    main()
