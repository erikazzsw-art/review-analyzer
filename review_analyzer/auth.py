import os

import bcrypt
from cryptography.fernet import Fernet, InvalidToken
from dotenv import load_dotenv
import streamlit as st

from review_analyzer.database import (
    create_user,
    get_user_by_username,
    get_user_by_id,
    update_user_api_key,
    init_db,
)

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

_AES_KEY = os.getenv("AES_SECRET_KEY", "")
_fernet = Fernet(_AES_KEY.encode()) if _AES_KEY else None


# ============================================================
# 密码哈希
# ============================================================

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))


# ============================================================
# API Key 加密 / 解密
# ============================================================

def encrypt_api_key(api_key: str) -> str:
    if not _fernet:
        raise RuntimeError("AES_SECRET_KEY 未配置，无法加密 API Key")
    return _fernet.encrypt(api_key.encode("utf-8")).decode("utf-8")


def decrypt_api_key(encrypted_key: str) -> str:
    if not _fernet:
        raise RuntimeError("AES_SECRET_KEY 未配置，无法解密 API Key")
    try:
        return _fernet.decrypt(encrypted_key.encode("utf-8")).decode("utf-8")
    except InvalidToken:
        raise ValueError("API Key 解密失败，密钥可能已变更")


# ============================================================
# 注册 / 登录
# ============================================================

def register(username: str, password: str) -> tuple[bool, str]:
    if len(username.strip()) < 2:
        return False, "用户名至少 2 个字符"
    if len(password) < 6:
        return False, "密码至少 6 个字符"
    if get_user_by_username(username.strip()):
        return False, "用户名已存在"
    password_hash = hash_password(password)
    user_id = create_user(username.strip(), password_hash)
    _set_session(user_id, username.strip())
    return True, "注册成功"


def login(username: str, password: str) -> tuple[bool, str]:
    user = get_user_by_username(username.strip())
    if not user:
        return False, "用户名或密码错误"
    if not verify_password(password, user["password_hash"]):
        return False, "用户名或密码错误"
    _set_session(user["id"], user["username"])
    return True, "登录成功"


def logout() -> None:
    for key in ["user_id", "username", "is_logged_in"]:
        st.session_state.pop(key, None)


# ============================================================
# Session State 管理
# ============================================================

def _set_session(user_id: int, username: str) -> None:
    st.session_state["user_id"] = user_id
    st.session_state["username"] = username
    st.session_state["is_logged_in"] = True


def is_logged_in() -> bool:
    return st.session_state.get("is_logged_in", False)


def get_current_user_id() -> int | None:
    return st.session_state.get("user_id")


def get_current_username() -> str | None:
    return st.session_state.get("username")


# ============================================================
# API Key 存取（结合数据库）
# ============================================================

def save_user_api_key(user_id: int, api_key: str) -> None:
    encrypted = encrypt_api_key(api_key)
    update_user_api_key(user_id, encrypted)


def load_user_api_key(user_id: int) -> str | None:
    user = get_user_by_id(user_id)
    if not user or not user.get("api_key_encrypted"):
        return None
    return decrypt_api_key(user["api_key_encrypted"])


# ============================================================
# Streamlit 认证 UI 组件
# ============================================================

def render_auth_page() -> None:
    init_db()

    if is_logged_in():
        return

    st.title("ClueAI")
    st.caption("跨境电商评论分析系统")

    tab_login, tab_register = st.tabs(["登录", "注册"])

    with tab_login:
        with st.form("login_form"):
            username = st.text_input("用户名", key="login_username")
            password = st.text_input("密码", type="password", key="login_password")
            submitted = st.form_submit_button("登录", use_container_width=True)
            if submitted:
                ok, msg = login(username, password)
                if ok:
                    st.rerun()
                else:
                    st.error(msg)

    with tab_register:
        with st.form("register_form"):
            new_username = st.text_input("用户名", key="reg_username")
            new_password = st.text_input("密码", type="password", key="reg_password")
            confirm_password = st.text_input("确认密码", type="password", key="reg_confirm")
            submitted = st.form_submit_button("注册", use_container_width=True)
            if submitted:
                if new_password != confirm_password:
                    st.error("两次密码不一致")
                else:
                    ok, msg = register(new_username, new_password)
                    if ok:
                        st.rerun()
                    else:
                        st.error(msg)
