"""登录页面。"""

from __future__ import annotations

import streamlit as st

from review_analyzer.auth import confirm_password_reset, login, register, request_password_reset
from review_analyzer.i18n import pick, t


def render_login_page() -> None:
    default_tab = st.session_state.pop("login_default_tab", "login")

    st.markdown(
        """
        <style>
        [data-testid="stSidebar"] { display: none; }
        .stApp { background: linear-gradient(180deg, #fffaf8 0%, #fff6f7 48%, #f8f4ff 100%); }
        section[data-testid="stMain"] > div { padding-top: 18px !important; }
        .auth-shell {
            max-width: 1140px;
            margin: 0 auto;
            padding: 0 12px 40px;
            font-family: 'Inter', system-ui, sans-serif;
        }
        .auth-topbar {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 16px;
            margin-bottom: 20px;
        }
        .auth-brand {
            display: inline-flex;
            align-items: center;
            gap: 12px;
        }
        .auth-mark {
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
        .auth-brand strong {
            display: block;
            font-family: 'Montserrat', system-ui, sans-serif;
            font-size: 20px;
            letter-spacing: -0.02em;
            color: #25212a;
        }
        .auth-brand span {
            display: block;
            margin-top: 2px;
            font-size: 13px;
            color: #7b7384;
        }
        .auth-note {
            display: inline-flex;
            align-items: center;
            padding: 8px 12px;
            border-radius: 999px;
            border: 1px solid #ebe4ee;
            background: rgba(255,255,255,0.8);
            color: #7b7384;
            font-size: 13px;
        }
        .auth-panel {
            background: rgba(255,255,255,0.86);
            border: 1px solid #ebe4ee;
            border-radius: 28px;
            box-shadow: 0 20px 52px rgba(96, 63, 88, 0.10);
            backdrop-filter: blur(10px);
            padding: 18px;
        }
        .auth-highlight {
            min-height: 100%;
            border-radius: 24px;
            padding: 28px 28px 24px;
            background: linear-gradient(135deg, #25212a 0%, #3b3147 52%, #5b4570 100%);
            color: #ffffff;
        }
        .auth-highlight .eyebrow {
            display: inline-flex;
            align-items: center;
            padding: 7px 12px;
            border-radius: 999px;
            background: rgba(255,255,255,0.12);
            color: rgba(255,255,255,0.86);
            font-size: 12px;
            font-weight: 700;
            margin-bottom: 16px;
        }
        .auth-highlight h1 {
            margin: 0;
            font-family: 'Montserrat', system-ui, sans-serif;
            font-size: 38px;
            line-height: 1.1;
            letter-spacing: -0.03em;
        }
        .auth-highlight p {
            margin: 14px 0 0;
            font-size: 14px;
            line-height: 1.78;
            color: rgba(255,255,255,0.78);
        }
        .auth-list {
            display: grid;
            gap: 12px;
            margin-top: 22px;
        }
        .auth-list-item {
            padding: 16px 16px 14px;
            border-radius: 18px;
            background: rgba(255,255,255,0.08);
            border: 1px solid rgba(255,255,255,0.10);
        }
        .auth-list-item strong {
            display: block;
            margin-bottom: 6px;
            font-size: 14px;
            color: #ffffff;
        }
        .auth-list-item span {
            display: block;
            font-size: 13px;
            line-height: 1.65;
            color: rgba(255,255,255,0.72);
        }
        .auth-card {
            padding: 28px;
            border-radius: 24px;
            background: linear-gradient(180deg, #ffffff 0%, #fff8fb 100%);
            border: 1px solid #eee5f1;
        }
        .auth-card h2 {
            margin: 0 0 8px;
            font-family: 'Montserrat', system-ui, sans-serif;
            font-size: 28px;
            color: #25212a;
            letter-spacing: -0.03em;
        }
        .auth-card p {
            margin: 0 0 18px;
            font-size: 14px;
            line-height: 1.72;
            color: #6f6877;
        }
        .auth-footer-note {
            margin-top: 16px;
            font-size: 13px;
            line-height: 1.68;
            color: #7b7384;
        }
        @media (max-width: 980px) {
            .auth-topbar {
                align-items: flex-start;
                flex-direction: column;
            }
            .auth-highlight h1 { font-size: 32px; }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        pick(
            """
        <div class="auth-shell">
            <div class="auth-topbar">
                <div class="auth-brand">
                    <div class="auth-mark">C</div>
                    <div>
                        <strong>ClueAI</strong>
                        <span>欢迎回来，继续你的评论闭环工作流</span>
                    </div>
                </div>
                <div class="auth-note">登录后进入今日工作台</div>
            </div>
        </div>
        """,
            """
        <div class="auth-shell">
            <div class="auth-topbar">
                <div class="auth-brand">
                    <div class="auth-mark">C</div>
                    <div>
                        <strong>ClueAI</strong>
                        <span>Welcome back. Continue your review workflow.</span>
                    </div>
                </div>
                <div class="auth-note">Log in to enter Today's Workspace</div>
            </div>
        </div>
        """,
        ),
        unsafe_allow_html=True,
    )

    _render_workspace_return()

    left_col, right_col = st.columns([1.03, 0.97], gap="large")
    with left_col:
        st.markdown(
            pick(
                """
            <div class="auth-panel">
                <div class="auth-highlight">
                    <div class="eyebrow">统一后的 V2 登录入口</div>
                    <h1>把欢迎页、登录页和系统内页，拉回同一套语言。</h1>
                    <p>
                        现在你在登录前也能感受到和系统内一致的卡片、圆角、配色和信息层次。
                        登录之后会直接进入“今日工作台”，继续处理上传、结果、动作和复盘。
                    </p>
                    <div class="auth-list">
                        <div class="auth-list-item">
                            <strong>更清楚的路径</strong>
                            <span>注册、登录、找回密码都保留原来行为，但视觉和文案更像同一个产品。</span>
                        </div>
                        <div class="auth-list-item">
                            <strong>更稳定的演示体验</strong>
                            <span>从欢迎页进来到登录页，不会再突然跳成另一套设计语气。</span>
                        </div>
                        <div class="auth-list-item">
                            <strong>更短的上手链路</strong>
                            <span>登录后默认进入今日工作台，再顺着主链路继续做评论分析和动作跟进。</span>
                        </div>
                    </div>
                </div>
            </div>
            """,
                """
            <div class="auth-panel">
                <div class="auth-highlight">
                    <div class="eyebrow">Unified V2 login entry</div>
                    <h1>Bring the landing page, login flow, and in-app pages back into one language system.</h1>
                    <p>
                        Even before logging in, you now get the same card structure, rounded corners, color language,
                        and information hierarchy as the main product. After login, you land directly in Today's Workspace
                        and continue with uploads, results, actions, and follow-ups.
                    </p>
                    <div class="auth-list">
                        <div class="auth-list-item">
                            <strong>Clearer path</strong>
                            <span>Register, log in, and reset your password with the same behavior, but in one consistent product voice.</span>
                        </div>
                        <div class="auth-list-item">
                            <strong>More stable demos</strong>
                            <span>Moving from the landing page to login no longer feels like jumping into a different product.</span>
                        </div>
                        <div class="auth-list-item">
                            <strong>Faster onboarding</strong>
                            <span>After login, continue in Today's Workspace and follow the main review-analysis workflow.</span>
                        </div>
                    </div>
                </div>
            </div>
            """,
            ),
            unsafe_allow_html=True,
        )

    with right_col:
        st.markdown(
            pick(
                """
            <div class="auth-panel">
                <div class="auth-card">
                    <h2>账号入口</h2>
                    <p>继续登录、创建账号，或通过邮箱验证码找回密码。</p>
                </div>
            </div>
            """,
                """
            <div class="auth-panel">
                <div class="auth-card">
                    <h2>Account Access</h2>
                    <p>Continue to log in, create an account, or reset your password with an email verification code.</p>
                </div>
            </div>
            """,
            ),
            unsafe_allow_html=True,
        )

        reset_step = st.session_state.get("reset_step")
        if reset_step == "input_email":
            _render_reset_email()
        elif reset_step == "input_code":
            _render_reset_code()
        else:
            _render_auth_tabs(default_tab)

        st.markdown(
            pick(
                "<div class='auth-footer-note'>登录前入口样式已与系统内 V2 版本统一。</div>",
                "<div class='auth-footer-note'>The pre-login entry now matches the in-app V2 experience.</div>",
            ),
            unsafe_allow_html=True,
        )

        if st.button(pick("返回首页", "Back to Landing"), key="back_to_landing", use_container_width=True):
            st.session_state["show_page"] = "landing"
            st.rerun()


def _render_auth_tabs(default_tab: str) -> None:
    if default_tab == "register":
        tab_register, tab_login = st.tabs([pick("注册", "Register"), pick("登录", "Log In")])
    else:
        tab_login, tab_register = st.tabs([pick("登录", "Log In"), pick("注册", "Register")])

    with tab_login:
        with st.form("login_form"):
            username = st.text_input(pick("用户名", "Username"), key="login_username", placeholder=pick("请输入用户名", "Enter your username"))
            password = st.text_input(pick("密码", "Password"), type="password", key="login_password", placeholder=pick("请输入密码", "Enter your password"))
            submitted = st.form_submit_button(pick("登录", "Log In"), use_container_width=True, type="primary")
            if submitted:
                if not username or not password:
                    st.error(pick("请输入用户名和密码", "Please enter both username and password."))
                else:
                    ok, msg = login(username, password)
                    if ok:
                        st.rerun()
                    else:
                        st.error(msg)
        if st.button(pick("忘记密码？", "Forgot password?"), key="forgot_password"):
            st.session_state["reset_step"] = "input_email"
            st.rerun()

    with tab_register:
        with st.form("register_form"):
            new_username = st.text_input(pick("用户名", "Username"), key="reg_username", placeholder=pick("至少 2 个字符", "At least 2 characters"))
            new_email = st.text_input(pick("邮箱", "Email"), key="reg_email", placeholder=pick("用于找回密码，建议填写", "Recommended for password recovery"))
            new_password = st.text_input(pick("密码", "Password"), type="password", key="reg_password", placeholder=pick("至少 6 个字符", "At least 6 characters"))
            confirm_password = st.text_input(pick("确认密码", "Confirm Password"), type="password", key="reg_confirm", placeholder=pick("再次输入密码", "Enter your password again"))
            submitted = st.form_submit_button(pick("注册账号", "Create Account"), use_container_width=True, type="primary")
            if submitted:
                if new_password != confirm_password:
                    st.error(pick("两次密码不一致", "The two passwords do not match."))
                elif not new_username or not new_password:
                    st.error(pick("请填写完整信息", "Please complete all required fields."))
                else:
                    ok, msg = register(new_username, new_password, new_email)
                    if ok:
                        st.rerun()
                    else:
                        st.error(msg)


def _render_reset_email() -> None:
    st.markdown(f"### {pick('找回密码', 'Reset Password')}")
    with st.form("reset_email_form"):
        reset_email = st.text_input(pick("注册邮箱", "Email Address"), placeholder=pick("请输入注册时使用的邮箱", "Enter the email used to register"))
        submitted = st.form_submit_button(pick("发送验证码", "Send Verification Code"), use_container_width=True, type="primary")
        if submitted:
            if not reset_email:
                st.error(pick("请输入邮箱", "Please enter your email address."))
            else:
                ok, msg = request_password_reset(reset_email)
                if ok:
                    st.session_state["reset_email"] = reset_email
                    st.session_state["reset_step"] = "input_code"
                    st.rerun()
                else:
                    st.error(msg)
    if st.button(pick("返回登录", "Back to Login"), key="back_from_email"):
        st.session_state.pop("reset_step", None)
        st.rerun()


def _render_reset_code() -> None:
    reset_email = st.session_state.get("reset_email", "")
    st.markdown(f"### {pick('输入验证码', 'Enter Verification Code')}")
    st.caption(
        pick(
            f"验证码已发送至 {reset_email}，10 分钟内有效",
            f"A verification code has been sent to {reset_email}. It is valid for 10 minutes.",
        )
    )
    with st.form("reset_code_form"):
        code = st.text_input(pick("验证码", "Verification Code"), placeholder=pick("请输入 6 位验证码", "Enter the 6-digit code"), max_chars=6)
        new_password = st.text_input(pick("新密码", "New Password"), type="password", placeholder=pick("至少 6 个字符", "At least 6 characters"))
        confirm_password = st.text_input(pick("确认新密码", "Confirm New Password"), type="password", placeholder=pick("再次输入新密码", "Enter the new password again"))
        submitted = st.form_submit_button(pick("重置密码", "Reset Password"), use_container_width=True, type="primary")
        if submitted:
            if new_password != confirm_password:
                st.error(pick("两次密码不一致", "The two passwords do not match."))
            elif not code or not new_password:
                st.error(pick("请填写完整信息", "Please complete all required fields."))
            else:
                ok, msg = confirm_password_reset(reset_email, code, new_password)
                if ok:
                    st.success(msg)
                    st.session_state.pop("reset_step", None)
                    st.session_state.pop("reset_email", None)
                    st.rerun()
                else:
                    st.error(msg)
    if st.button(pick("重新发送验证码", "Send Code Again"), key="back_to_email"):
        st.session_state["reset_step"] = "input_email"
        st.rerun()


def _render_workspace_return() -> None:
    if not st.session_state.get("is_logged_in"):
        return

    col_left, col_button = st.columns([4.2, 1.2])
    with col_button:
        if st.button(t("back_to_workspace"), key="login_back_to_workspace", use_container_width=True):
            st.session_state.pop("force_public_preview", None)
            st.session_state["current_page"] = "dashboard"
            st.rerun()
