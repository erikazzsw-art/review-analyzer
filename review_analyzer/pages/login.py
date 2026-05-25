"""登录页面 — 还原 prototype 的紫蓝渐变 + 居中白色卡片设计"""

import streamlit as st

from review_analyzer.auth import login, register, request_password_reset, confirm_password_reset


def render_login_page() -> None:
    default_tab = st.session_state.pop("login_default_tab", "login")

    st.markdown("""
    <style>
    [data-testid="stSidebar"] { display: none; }
    .stApp {
        background: #f5f5f5;
    }
    </style>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 1.2, 1])
    with col2:
        st.markdown("""
        <div style="background:white;border-radius:12px;padding:48px 40px;
                    border:1px solid #e8e8e8;text-align:center;
                    margin-top:60px;">
            <div style="font-size:24px;font-weight:700;color:#202020;margin-bottom:4px;
                        font-family:'Montserrat',system-ui,sans-serif;letter-spacing:-0.02em;">ClueAI</div>
            <div style="font-size:14px;color:#4d4d4d;margin-bottom:32px;">跨境电商评论分析平台</div>
        </div>
        """, unsafe_allow_html=True)

        reset_step = st.session_state.get("reset_step", None)

        if reset_step == "input_email":
            st.subheader("找回密码")
            with st.form("reset_email_form"):
                reset_email = st.text_input("注册邮箱", placeholder="请输入注册时使用的邮箱")
                submitted = st.form_submit_button("发送验证码", use_container_width=True, type="primary")
                if submitted:
                    if not reset_email:
                        st.error("请输入邮箱")
                    else:
                        ok, msg = request_password_reset(reset_email)
                        if ok:
                            st.session_state["reset_email"] = reset_email
                            st.session_state["reset_step"] = "input_code"
                            st.rerun()
                        else:
                            st.error(msg)
            if st.button("← 返回登录", key="back_from_email"):
                st.session_state.pop("reset_step", None)
                st.rerun()

        elif reset_step == "input_code":
            st.subheader("输入验证码")
            reset_email = st.session_state.get("reset_email", "")
            st.caption(f"验证码已发送至 {reset_email}，10 分钟内有效")
            with st.form("reset_code_form"):
                code = st.text_input("验证码", placeholder="请输入 6 位验证码", max_chars=6)
                new_password = st.text_input("新密码", type="password", placeholder="至少 6 个字符")
                confirm_password = st.text_input("确认新密码", type="password", placeholder="再次输入新密码")
                submitted = st.form_submit_button("重置密码", use_container_width=True, type="primary")
                if submitted:
                    if new_password != confirm_password:
                        st.error("两次密码不一致")
                    elif not code or not new_password:
                        st.error("请填写完整信息")
                    else:
                        ok, msg = confirm_password_reset(reset_email, code, new_password)
                        if ok:
                            st.success(msg)
                            st.session_state.pop("reset_step", None)
                            st.session_state.pop("reset_email", None)
                            st.rerun()
                        else:
                            st.error(msg)
            if st.button("← 重新发送", key="back_to_email"):
                st.session_state["reset_step"] = "input_email"
                st.rerun()

        else:
            if default_tab == "register":
                tab_register, tab_login = st.tabs(["注册", "登录"])
            else:
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
                if st.button("忘记密码？", key="forgot_password"):
                    st.session_state["reset_step"] = "input_email"
                    st.rerun()

            with tab_register:
                with st.form("register_form"):
                    new_username = st.text_input("用户名", key="reg_username", placeholder="至少2个字符")
                    new_email = st.text_input("邮箱", key="reg_email", placeholder="用于找回密码（推荐填写）")
                    new_password = st.text_input("密码", type="password", key="reg_password", placeholder="至少6个字符")
                    confirm_password = st.text_input("确认密码", type="password", key="reg_confirm", placeholder="再次输入密码")
                    submitted = st.form_submit_button("注 册", use_container_width=True, type="primary")
                    if submitted:
                        if new_password != confirm_password:
                            st.error("两次密码不一致")
                        elif not new_username or not new_password:
                            st.error("请填写完整信息")
                        else:
                            ok, msg = register(new_username, new_password, new_email)
                            if ok:
                                st.rerun()
                            else:
                                st.error(msg)

        st.markdown("""
        <div style="text-align:center;margin-top:16px;font-size:13px;color:rgba(255,255,255,0.8);">
        </div>
        """, unsafe_allow_html=True)

        if st.button("← 返回首页", key="back_to_landing", use_container_width=True):
            st.session_state["show_page"] = "landing"
            st.rerun()
