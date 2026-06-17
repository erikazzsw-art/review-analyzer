from __future__ import annotations

import os
import random
import string
from datetime import datetime, timedelta, timezone

import bcrypt
from cryptography.fernet import Fernet, InvalidToken
from dotenv import load_dotenv

from review_analyzer.database import (
    create_reset_token,
    create_user,
    get_user_by_email,
    get_user_by_id,
    get_user_by_username,
    get_valid_reset_token,
    mark_token_used,
    update_user_api_key,
    update_user_password,
)
from review_analyzer.mailer import send_reset_code

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
    except InvalidToken as err:
        raise ValueError("API Key 解密失败，密钥可能已变更") from err


# ============================================================
# 注册 / 登录
# ============================================================

def register(username: str, password: str, email: str = "") -> tuple[bool, str]:
    if len(username.strip()) < 2:
        return False, "用户名至少 2 个字符"
    if len(password) < 6:
        return False, "密码至少 6 个字符"
    if get_user_by_username(username.strip()):
        return False, "用户名已存在"
    password_hash = hash_password(password)
    create_user(username.strip(), password_hash, email.strip())
    return True, "注册成功"


def login(username: str, password: str) -> tuple[bool, str]:
    user = get_user_by_username(username.strip())
    if not user:
        return False, "用户名或密码错误"
    if not verify_password(password, user["password_hash"]):
        return False, "用户名或密码错误"
    return True, "登录成功"


# ============================================================
# 密码重置
# ============================================================

def request_password_reset(email: str) -> tuple[bool, str]:
    user = get_user_by_email(email.strip())
    if not user:
        return False, "该邮箱未注册，请先注册账号或使用正确的注册邮箱"
    code = "".join(random.choices(string.digits, k=6))
    expires_at = (datetime.now(timezone.utc) + timedelta(minutes=10)).isoformat()
    create_reset_token(email.strip(), code, expires_at)
    ok, err = send_reset_code(email.strip(), code)
    if not ok:
        return False, f"验证码发送失败：{err}"
    return True, "验证码已发送，请查收邮件（注意检查垃圾邮件）"


def confirm_password_reset(email: str, code: str, new_password: str) -> tuple[bool, str]:
    if len(new_password) < 6:
        return False, "密码至少 6 个字符"
    token_row = get_valid_reset_token(email.strip(), code.strip())
    if not token_row:
        return False, "验证码无效或已过期"
    user = get_user_by_email(email.strip())
    if not user:
        return False, "用户不存在"
    mark_token_used(token_row["id"])
    update_user_password(user["id"], hash_password(new_password))
    return True, "密码重置成功，请用新密码登录"


# ============================================================
# API Key 存取（结合数据库）
# ============================================================

def save_user_api_key(user_id: int, api_key: str) -> None:
    if not api_key.strip():
        update_user_api_key(user_id, None)
        return
    encrypted = encrypt_api_key(api_key)
    update_user_api_key(user_id, encrypted)


def load_user_api_key(user_id: int) -> str | None:
    user = get_user_by_id(user_id)
    if not user or not user.get("api_key_encrypted"):
        return None
    return decrypt_api_key(user["api_key_encrypted"])
