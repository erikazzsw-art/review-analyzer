"""欢迎页面 — 产品介绍 Landing Page"""

import streamlit as st


def render_landing_page() -> None:
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=Montserrat:wght@400;700;800&display=swap');

    [data-testid="stSidebar"] { display: none; }
    .stApp { background: #ffffff; }
    section[data-testid="stMain"] > div { padding: 0 !important; max-width: 100% !important; }

    .land-nav {
        display: flex; align-items: center; justify-content: space-between;
        padding: 16px 60px; background: #ffffff; border-bottom: 1px solid #e8e8e8;
        position: sticky; top: 0; z-index: 20;
        font-family: 'Inter', system-ui, sans-serif;
    }
    .land-nav-logo {
        font-size: 20px; font-weight: 700; color: #202020;
        font-family: 'Montserrat', system-ui, sans-serif;
        letter-spacing: -0.02em;
    }
    .land-hero {
        display: flex; align-items: center; justify-content: space-between;
        padding: 80px 60px; max-width: 1200px; margin: 0 auto; gap: 60px;
    }
    .land-hero-text { flex: 1; }
    .land-hero-text h1 {
        font-size: 44px; font-weight: 800; color: #202020;
        margin-bottom: 20px; line-height: 1.15;
        font-family: 'Montserrat', system-ui, sans-serif;
        letter-spacing: -0.02em;
    }
    .land-hero-text h1 em { font-style: normal; color: #ff682c; }
    .land-hero-text p {
        font-size: 16px; color: #4d4d4d; max-width: 480px;
        margin-bottom: 32px; line-height: 1.6;
        font-family: 'Inter', system-ui, sans-serif;
    }
    .land-hero-visual {
        flex: 1; display: flex; align-items: center; justify-content: center;
    }
    .hero-illustration {
        width: 100%; max-width: 440px; aspect-ratio: 4/3;
        background: #f5f5f5; border-radius: 20px; padding: 32px;
        display: flex; flex-direction: column; gap: 12px;
    }
    .hero-card-row { display: flex; gap: 12px; }
    .hero-mini-card {
        flex: 1; background: #ffffff; border-radius: 8px; padding: 16px;
        border: 1px solid #e8e8e8;
    }
    .hero-mini-card .hmc-label { font-size: 11px; color: #828282; margin-bottom: 4px; }
    .hero-mini-card .hmc-val { font-size: 20px; font-weight: 700; color: #202020; font-family: 'Montserrat', system-ui, sans-serif; }
    .hero-mini-card .hmc-bar { height: 4px; border-radius: 2px; margin-top: 8px; }
    .hero-mini-card .hmc-bar.green { background: #2ecc71; width: 78%; }
    .hero-mini-card .hmc-bar.orange { background: #ff682c; width: 45%; }
    .hero-review-item {
        background: #ffffff; border-radius: 8px; padding: 14px 16px;
        border: 1px solid #e8e8e8; display: flex; align-items: center; gap: 12px;
    }
    .hero-review-item .avatar {
        width: 32px; height: 32px; border-radius: 50%; flex-shrink: 0;
        display: flex; align-items: center; justify-content: center;
        font-size: 14px; color: #fff;
    }
    .hero-review-item .review-text { font-size: 12px; color: #4d4d4d; line-height: 1.4; }
    .hero-review-item .stars { font-size: 11px; color: #f39c12; margin-top: 2px; }

    .land-section {
        padding: 80px 60px; max-width: 1100px; margin: 0 auto;
        font-family: 'Inter', system-ui, sans-serif;
    }
    .land-section h2 {
        font-size: 32px; font-weight: 700; text-align: center;
        margin-bottom: 12px; color: #202020;
        font-family: 'Montserrat', system-ui, sans-serif;
        letter-spacing: -0.02em;
    }
    .land-section .sub {
        font-size: 15px; color: #4d4d4d; text-align: center;
        margin-bottom: 48px; line-height: 1.5;
    }
</style>
""", unsafe_allow_html=True)

    # 第二段 CSS（拆分避免过长）
    st.markdown("""
<style>
    .pain-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 20px; }
    .pain-card {
        display: flex; gap: 20px; background: #f5f5f5;
        border-radius: 12px; padding: 32px;
    }
    .pain-card .icon-badge {
        width: 48px; height: 48px; border-radius: 12px;
        display: flex; align-items: center; justify-content: center;
        flex-shrink: 0; font-size: 20px;
    }
    .pain-card .icon-badge.ic-1 { background: #ffeee8; color: #ff682c; }
    .pain-card .icon-badge.ic-2 { background: #e8f4fd; color: #3498db; }
    .pain-card .icon-badge.ic-3 { background: #fef3e0; color: #f39c12; }
    .pain-card .icon-badge.ic-4 { background: #e8f8f0; color: #2ecc71; }
    .pain-card h3 { font-size: 15px; font-weight: 600; margin-bottom: 6px; color: #202020; }
    .pain-card p { font-size: 14px; color: #4d4d4d; margin: 0; line-height: 1.5; }

    .feature-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px; }
    .feature-card {
        background: #ffffff; border-radius: 12px; padding: 36px 24px;
        text-align: center; border: 1px solid #e8e8e8;
        transition: border-color 0.2s;
    }
    .feature-card:hover { border-color: #ff682c; }
    .feature-card .feat-icon {
        width: 56px; height: 56px; border-radius: 14px;
        display: flex; align-items: center; justify-content: center;
        margin: 0 auto 16px; font-size: 24px;
    }
    .feature-card .feat-icon.fi-1 { background: #ffeee8; color: #ff682c; }
    .feature-card .feat-icon.fi-2 { background: #e8f4fd; color: #3498db; }
    .feature-card .feat-icon.fi-3 { background: #fef3e0; color: #f39c12; }
    .feature-card .feat-icon.fi-4 { background: #e8f8f0; color: #2ecc71; }
    .feature-card .feat-icon.fi-5 { background: #f3eeff; color: #816729; }
    .feature-card .feat-icon.fi-6 { background: #eef6ff; color: #3498db; }
    .feature-card h3 { font-size: 16px; font-weight: 600; margin-bottom: 8px; color: #202020; }
    .feature-card p { font-size: 14px; color: #4d4d4d; margin: 0; line-height: 1.5; }

    .benefit-row { display: grid; grid-template-columns: repeat(4, 1fr); gap: 20px; text-align: center; }
    .benefit-item {
        background: #f5f5f5; border-radius: 12px; padding: 32px 16px;
    }
    .benefit-item .num {
        font-size: 36px; font-weight: 800; color: #ff682c;
        font-family: 'Montserrat', system-ui, sans-serif;
        letter-spacing: -0.02em;
    }
    .benefit-item .label { font-size: 14px; color: #4d4d4d; margin-top: 8px; }

    .social-proof {
        display: flex; gap: 16px; justify-content: center; flex-wrap: wrap;
        margin-top: 48px; padding: 0 20px;
    }
    .proof-card {
        background: #f5f5f5; border-radius: 12px; padding: 24px;
        max-width: 320px; flex: 1; min-width: 260px;
    }
    .proof-card .proof-stars { color: #f39c12; font-size: 14px; margin-bottom: 8px; }
    .proof-card .proof-text { font-size: 14px; color: #4d4d4d; line-height: 1.5; margin-bottom: 12px; }
    .proof-card .proof-author { font-size: 13px; color: #828282; font-weight: 500; }

    .cta-banner {
        text-align: center; padding: 80px 60px; border-radius: 20px;
        margin: 0 60px 60px; background: #202020; color: #ffffff;
    }
    .cta-banner h2 {
        font-size: 32px; font-weight: 700; margin-bottom: 16px; color: #ffffff;
        font-family: 'Montserrat', system-ui, sans-serif;
        letter-spacing: -0.02em;
    }
    .cta-banner p { font-size: 16px; opacity: 0.7; margin-bottom: 32px; }

    /* Streamlit 按钮覆盖 */
    .stButton > button[kind="primary"] {
        background: #ff682c !important;
        color: #ffffff !important;
        border: none !important;
        border-radius: 20px !important;
        font-family: 'Inter', system-ui, sans-serif;
        font-weight: 500; font-size: 15px;
    }
    .stButton > button[kind="primary"]:hover {
        background: #e55520 !important;
        color: #ffffff !important;
    }
    .stButton > button {
        border-radius: 20px !important;
        font-family: 'Inter', system-ui, sans-serif;
        font-weight: 500; color: #4d4d4d;
        border: 1px solid #e8e8e8 !important;
    }
    .stButton > button:hover {
        border-color: #202020 !important;
        color: #202020 !important;
    }

    @media(max-width: 768px) {
        .land-nav { padding: 16px 20px; }
        .land-hero { flex-direction: column; padding: 40px 20px; gap: 32px; }
        .land-hero-text h1 { font-size: 28px; }
        .land-section { padding: 60px 20px; }
        .pain-grid, .feature-grid { grid-template-columns: 1fr; }
        .benefit-row { grid-template-columns: repeat(2, 1fr); }
        .cta-banner { margin: 20px; padding: 40px 20px; }
        .social-proof { flex-direction: column; align-items: center; }
    }
</style>
    """, unsafe_allow_html=True)

    # 顶部导航
    st.markdown("""
    <div class="land-nav">
        <div class="land-nav-logo">ClueAI</div>
    </div>
    """, unsafe_allow_html=True)

    # Hero 区域 — 左文字右插图
    st.markdown("""
    <div class="land-hero">
        <div class="land-hero-text">
            <h1>跨境电商评论，<br><em>一键读懂</em></h1>
            <p>上传评论文件，AI 自动提取产品问题与亮点，帮你从海量评论中找到真正影响销量的关键因素</p>
        </div>
        <div class="land-hero-visual">
            <div class="hero-illustration">
                <div class="hero-card-row">
                    <div class="hero-mini-card">
                        <div class="hmc-label">正面率</div>
                        <div class="hmc-val">78%</div>
                        <div class="hmc-bar green"></div>
                    </div>
                    <div class="hero-mini-card">
                        <div class="hmc-label">问题提及率</div>
                        <div class="hmc-val">12%</div>
                        <div class="hmc-bar orange"></div>
                    </div>
                </div>
                <div class="hero-review-item">
                    <div class="avatar" style="background:#2ecc71;">A</div>
                    <div>
                        <div class="stars">★★★★★</div>
                        <div class="review-text">"Quality is amazing, fast delivery!"</div>
                    </div>
                </div>
                <div class="hero-review-item">
                    <div class="avatar" style="background:#ff682c;">M</div>
                    <div>
                        <div class="stars">★★★☆☆</div>
                        <div class="review-text">"包装有点简陋，但产品本身不错"</div>
                    </div>
                </div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # 按钮区域 — 居中
    col_l, col_btn1, col_btn2, col_btn3, col_r = st.columns([2, 1.2, 1.2, 1.2, 2])
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

    # 核心优势
    st.markdown("""
    <div class="land-section" style="background:#f5f5f5;max-width:100%;padding:80px calc((100% - 1100px)/2);">
        <h2>相比竞品，我们的核心优势</h2>
        <div class="sub">不只是情感分析，而是直接告诉你「产品哪里好、哪里差、该怎么改」</div>
        <div class="feature-grid">
            <div class="feature-card">
                <div class="feat-icon fi-1"><svg width="24" height="24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><path d="M12 16v-4"/><path d="M12 8h.01"/></svg></div>
                <h3>问题 & 亮点直接提取</h3><p>直接输出 TOP10 产品问题和亮点，附带原文溯源</p>
            </div>
            <div class="feature-card">
                <div class="feat-icon fi-2"><svg width="24" height="24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg></div>
                <h3>支持文件批量上传</h3><p>直接上传 CSV/XLSX，支持 Amazon、Shopee、Temu 等平台格式</p>
            </div>
            <div class="feature-card">
                <div class="feat-icon fi-3"><svg width="24" height="24" fill="none" stroke="currentColor" stroke-width="2"><path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"/><path d="M13.73 21a2 2 0 0 1-3.46 0"/></svg></div>
                <h3>飞书实时告警</h3><p>差评率超阈值自动推送飞书通知，第一时间响应</p>
            </div>
            <div class="feature-card">
                <div class="feat-icon fi-4"><svg width="24" height="24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg></div>
                <h3>环比趋势追踪</h3><p>按批次自动对比，验证产品改进效果</p>
            </div>
            <div class="feature-card">
                <div class="feat-icon fi-5"><svg width="24" height="24" fill="none" stroke="currentColor" stroke-width="2"><line x1="12" y1="1" x2="12" y2="23"/><path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/></svg></div>
                <h3>成本仅为竞品 1/10</h3><p>专注评论分析，价格更亲民，功能更聚焦</p>
            </div>
            <div class="feature-card">
                <div class="feat-icon fi-6"><svg width="24" height="24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><path d="M2 12h20"/><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/></svg></div>
                <h3>中英双语界面</h3><p>界面支持中英文切换，适合跨境团队协作</p>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # 数据亮点 + 用户评价
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
        <div class="social-proof">
            <div class="proof-card">
                <div class="proof-stars">★★★★★</div>
                <div class="proof-text">"以前一个 SKU 要花半天看评论，现在 5 分钟就能拿到完整的问题清单，效率提升太明显了。"</div>
                <div class="proof-author">— 深圳跨境卖家 · 3C 品类</div>
            </div>
            <div class="proof-card">
                <div class="proof-stars">★★★★★</div>
                <div class="proof-text">"多语言评论终于不用一条条翻译了，AI 直接提取关键问题，帮我们快速定位产品改进方向。"</div>
                <div class="proof-author">— 杭州运营团队 · 家居品类</div>
            </div>
            <div class="proof-card">
                <div class="proof-stars">★★★★☆</div>
                <div class="proof-text">"飞书告警功能很实用，差评一出现就能收到通知，响应速度比以前快了很多。"</div>
                <div class="proof-author">— 广州品牌方 · 美妆品类</div>
            </div>
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
    col_l2, col_cta1, col_cta2, col_cta3, col_r2 = st.columns([2, 1.2, 1.2, 1.2, 2])
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

    # 痛点区域
    st.markdown("""
    <div class="land-section">
        <h2>为什么我们做了 ClueAI？</h2>
        <div class="sub">跨境卖家每天面对成百上千条多语言评论，人工阅读效率低、遗漏多、无法量化</div>
        <div class="pain-grid">
            <div class="pain-card">
                <div class="icon-badge ic-1"><svg width="24" height="24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2"/></svg></div>
                <div><h3>人工读评论太慢</h3><p>一个 SKU 上千条评论，人工逐条阅读需要数小时，且容易遗漏关键信息</p></div>
            </div>
            <div class="pain-card">
                <div class="icon-badge ic-2"><svg width="24" height="24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><path d="M2 12h20"/><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/></svg></div>
                <div><h3>多语言难以处理</h3><p>评论涉及英语、西班牙语、法语等多种语言，人工翻译成本高、效率低</p></div>
            </div>
            <div class="pain-card">
                <div class="icon-badge ic-3"><svg width="24" height="24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M18 20V10"/><path d="M12 20V4"/><path d="M6 20v-6"/></svg></div>
                <div><h3>无法量化问题严重程度</h3><p>知道有差评，但不知道哪个问题被提及最多、影响最大</p></div>
            </div>
            <div class="pain-card">
                <div class="icon-badge ic-4"><svg width="24" height="24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="23 4 23 10 17 10"/><path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"/></svg></div>
                <div><h3>缺乏持续追踪</h3><p>改进产品后无法对比前后评论变化，不知道优化是否有效</p></div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)