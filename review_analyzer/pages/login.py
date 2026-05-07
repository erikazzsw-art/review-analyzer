"""登录页面 — 还原 prototype 的紫蓝渐变 + 居中白色卡片设计"""

import streamlit as st

from review_analyzer.auth import login, register


def render_login_page() -> None:
    st.markdown("""
    <style>
    [data-testid="stSidebar"] { display: none; }
    .stApp {
        background: linear-gradient(135deg, #A29BFE 0%, #6C5CE7 50%, #74B9FF 100%);
    }
    </style>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 1.2, 1])
    with col2:
        st.markdown("""
        <div style="background:white;border-radius:20px;padding:48px 40px;
                    box-shadow:0 20px 60px rgba(0,0,0,0.15);text-align:center;
                    margin-top:60px;">
            <div style="font-size:48px;margin-bottom:8px;">🔍</div>
            <div style="font-size:24px;font-weight:700;color:#6C5CE7;margin-bottom:4px;">ReviewLens</div>
            <div style="font-size:14px;color:#636E72;margin-bottom:32px;">跨境电商评论分析平台</div>
        </div>
        """, unsafe_allow_html=True)

        tab_login, tab_register = st.tabs(["登录", "注册"])

        with tab_login:
            with st.form("login_form"):
                username = st.text_input("用户名", key="login_username", placeholder="请输入用户名")
                password = st.text_input("密码", type="password", key="login_password", placeholder="请输入密码")
                submitted = st.form_submit_button("登 录", use_container_width=True, type="primary")
                if submitted:
                    if not username or not password:
                        st.error("请输入用户名和密码")
                    else:
                        ok, msg = login(username, password)
                        if ok:
                            st.rerun()
                        else:
                            st.error(msg)

        with tab_register:
            with st.form("register_form"):
                new_username = st.text_input("用户名", key="reg_username", placeholder="至少2个字符")
                new_password = st.text_input("密码", type="password", key="reg_password", placeholder="至少6个字符")
                confirm_password = st.text_input("确认密码", type="password", key="reg_confirm", placeholder="再次输入密码")
                submitted = st.form_submit_button("注 册", use_container_width=True, type="primary")
                if submitted:
                    if new_password != confirm_password:
                        st.error("两次密码不一致")
                    elif not new_username or not new_password:
                        st.error("请填写完整信息")
                    else:
                        ok, msg = register(new_username, new_password)
                        if ok:
                            st.rerun()
                        else:
                            st.error(msg)

        st.markdown("""
        <div style="text-align:center;margin-top:16px;font-size:13px;color:rgba(255,255,255,0.8);">
            还没有账号？切换到"注册"标签页创建账号
        </div>
        """, unsafe_allow_html=True)

        if st.button("← 返回首页", key="back_to_landing", use_container_width=True):
            st.session_state["show_page"] = "landing"
            st.rerun()
