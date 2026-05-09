"""欢迎页面 — 产品介绍 Landing Page"""

import streamlit as st


def render_landing_page() -> None:
    st.markdown("""
    <style>
    [data-testid="stSidebar"] { display: none; }
    .stApp { background: #FAFAFF; }
    section[data-testid="stMain"] > div { padding: 0 !important; max-width: 100% !important; }
    .land-nav {
        display: flex; align-items: center; justify-content: space-between;
        padding: 16px 60px; background: #fff; border-bottom: 1px solid #E8EAF0;
        position: sticky; top: 0; z-index: 20;
    }
    .land-nav-logo { display: flex; align-items: center; gap: 10px; font-size: 20px; font-weight: 700; color: #6C5CE7; }
    .land-hero {
        text-align: center; padding: 80px 60px 60px;
        background: linear-gradient(180deg, #F0EEFF 0%, #FAFAFF 100%);
    }
    .land-hero h1 { font-size: 42px; font-weight: 800; color: #2D3436; margin-bottom: 16px; line-height: 1.3; }
    .land-hero h1 em { font-style: normal; color: #6C5CE7; }
    .land-hero p { font-size: 18px; color: #636E72; max-width: 640px; margin: 0 auto 32px; }
    .land-section { padding: 60px; max-width: 1100px; margin: 0 auto; }
    .land-section h2 { font-size: 28px; font-weight: 700; text-align: center; margin-bottom: 8px; }
    .land-section .sub { font-size: 15px; color: #636E72; text-align: center; margin-bottom: 40px; }
    .pain-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 24px; }
    .pain-card { display: flex; gap: 16px; background: #fff; border-radius: 14px; padding: 24px; box-shadow: 0 2px 12px rgba(0,0,0,0.04); }
    .pain-card .icon { font-size: 32px; flex-shrink: 0; }
    .pain-card h3 { font-size: 15px; font-weight: 600; margin-bottom: 4px; }
    .pain-card p { font-size: 13px; color: #636E72; margin: 0; }
    .feature-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 24px; }
    .feature-card {
        background: #fff; border-radius: 14px; padding: 28px 24px;
        box-shadow: 0 2px 12px rgba(0,0,0,0.04); text-align: center; transition: transform 0.2s;
    }
    .feature-card:hover { transform: translateY(-4px); }
    .feature-card .icon { font-size: 40px; margin-bottom: 12px; }
    .feature-card h3 { font-size: 17px; font-weight: 600; margin-bottom: 8px; }
    .feature-card p { font-size: 14px; color: #636E72; margin: 0; }
    .benefit-row { display: grid; grid-template-columns: repeat(4, 1fr); gap: 20px; text-align: center; }
    .benefit-item .num { font-size: 36px; font-weight: 800; color: #6C5CE7; }
    .benefit-item .label { font-size: 14px; color: #636E72; margin-top: 4px; }
    .cta-banner {
        text-align: center; padding: 60px; border-radius: 20px; margin: 40px 60px 60px;
        background: linear-gradient(135deg, #6C5CE7 0%, #74B9FF 100%); color: #fff;
    }
    .cta-banner h2 { font-size: 28px; font-weight: 700; margin-bottom: 12px; color: #fff; }
    .cta-banner p { font-size: 16px; opacity: 0.85; margin-bottom: 24px; }
    @media(max-width: 768px) {
        .land-nav { padding: 16px 20px; }
        .land-hero { padding: 40px 20px; }
        .land-hero h1 { font-size: 28px; }
        .land-section { padding: 40px 20px; }
        .pain-grid, .feature-grid { grid-template-columns: 1fr; }
        .benefit-row { grid-template-columns: repeat(2, 1fr); }
        .cta-banner { margin: 20px; padding: 40px 20px; }
    }
    </style>
    """, unsafe_allow_html=True)

    # 顶部导航
    st.markdown("""
    <div class="land-nav">
        <div class="land-nav-logo"><span>🔍</span><span>ClueAI</span></div>
    </div>
    """, unsafe_allow_html=True)

    # Hero 区域
    st.markdown("""
    <div class="land-hero">
        <h1>跨境电商评论，<em>一键读懂</em></h1>
        <p>上传评论文件，AI 自动提取产品问题与亮点，帮你从海量评论中找到真正影响销量的关键因素</p>
    </div>
    """, unsafe_allow_html=True)

    # 登录/试用/注册按钮
    col_l, col_btn1, col_btn2, col_btn3, col_r = st.columns([1.5, 1.2, 1.2, 1.2, 1.5])
    with col_btn1:
        if st.button("立即免费试用", type="primary", use_container_width=True, key="landing_trial"):
            st.session_state["show_page"] = "trial"
            st.rerun()
    with col_btn2:
        if st.button("注册账号", use_container_width=True, key="landing_register"):
            st.session_state["show_page"] = "login"
            st.session_state["login_default_tab"] = "register"
            st.rerun()
    with col_btn3:
        if st.button("已有账号，登录", use_container_width=True, key="landing_login"):
            st.session_state["show_page"] = "login"
            st.session_state["login_default_tab"] = "login"
            st.rerun()

    # 痛点区域
    st.markdown("""
    <div class="land-section">
        <h2>为什么我们做了 ClueAI？</h2>
        <div class="sub">跨境卖家每天面对成百上千条多语言评论，人工阅读效率低、遗漏多、无法量化</div>
        <div class="pain-grid">
            <div class="pain-card"><div class="icon">😩</div><div><h3>人工读评论太慢</h3><p>一个 SKU 上千条评论，人工逐条阅读需要数小时，且容易遗漏关键信息</p></div></div>
            <div class="pain-card"><div class="icon">🌍</div><div><h3>多语言难以处理</h3><p>评论涉及英语、西班牙语、法语等多种语言，人工翻译成本高、效率低</p></div></div>
            <div class="pain-card"><div class="icon">📊</div><div><h3>无法量化问题严重程度</h3><p>知道有差评，但不知道哪个问题被提及最多、影响最大</p></div></div>
            <div class="pain-card"><div class="icon">🔄</div><div><h3>缺乏持续追踪</h3><p>改进产品后无法对比前后评论变化，不知道优化是否有效</p></div></div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # 核心优势
    st.markdown("""
    <div class="land-section" style="background:#fff;max-width:100%;padding:60px calc((100% - 1100px)/2);">
        <h2>相比竞品，我们的核心优势</h2>
        <div class="sub">不只是情感分析，而是直接告诉你「产品哪里好、哪里差、该怎么改」</div>
        <div class="feature-grid">
            <div class="feature-card"><div class="icon">🎯</div><h3>问题 & 亮点直接提取</h3><p>直接输出 TOP10 产品问题和亮点，附带原文溯源</p></div>
            <div class="feature-card"><div class="icon">📁</div><h3>支持文件批量上传</h3><p>直接上传 CSV/XLSX，支持 Amazon、Shopee、Temu 等平台格式</p></div>
            <div class="feature-card"><div class="icon">🔔</div><h3>飞书实时告警</h3><p>差评率超阈值自动推送飞书通知，第一时间响应</p></div>
            <div class="feature-card"><div class="icon">📈</div><h3>环比趋势追踪</h3><p>按批次自动对比，验证产品改进效果</p></div>
            <div class="feature-card"><div class="icon">💰</div><h3>成本仅为竞品 1/10</h3><p>专注评论分析，价格更亲民，功能更聚焦</p></div>
            <div class="feature-card"><div class="icon">🌐</div><h3>中英双语界面</h3><p>界面支持中英文切换，适合跨境团队协作</p></div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # 数据亮点
    st.markdown("""
    <div class="land-section">
        <h2>使用 ClueAI 后</h2>
        <div class="sub">数据驱动的评论分析，让每一次产品决策都有据可依</div>
        <div class="benefit-row">
            <div class="benefit-item"><div class="num">90%</div><div class="label">评论分析时间节省</div></div>
            <div class="benefit-item"><div class="num">TOP10</div><div class="label">精准定位核心问题</div></div>
            <div class="benefit-item"><div class="num">24h</div><div class="label">差评实时告警响应</div></div>
            <div class="benefit-item"><div class="num">30天</div><div class="label">环比追踪改进效果</div></div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # CTA
    st.markdown("""
    <div class="cta-banner">
        <h2>现在就开始分析你的评论</h2>
        <p>无需复杂配置，上传文件即可体验 AI 评论分析的效果</p>
    </div>
    """, unsafe_allow_html=True)

    # 底部 CTA 按钮
    col_l2, col_cta1, col_cta2, col_cta3, col_r2 = st.columns([1.5, 1.2, 1.2, 1.2, 1.5])
    with col_cta1:
        if st.button("免费试用", type="primary", use_container_width=True, key="landing_cta_trial"):
            st.session_state["show_page"] = "trial"
            st.rerun()
    with col_cta2:
        if st.button("注册账号", use_container_width=True, key="landing_cta_register"):
            st.session_state["show_page"] = "login"
            st.session_state["login_default_tab"] = "register"
            st.rerun()
    with col_cta3:
        if st.button("登录", use_container_width=True, key="landing_cta_login"):
            st.session_state["show_page"] = "login"
            st.session_state["login_default_tab"] = "login"
            st.rerun()
