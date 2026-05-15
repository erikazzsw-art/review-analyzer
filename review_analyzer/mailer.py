from __future__ import annotations

import resend
import streamlit as st


def send_reset_code(to_email: str, code: str) -> bool:
    resend.api_key = st.secrets["resend"]["api_key"]
    try:
        resend.Emails.send({
            "from": "ClueAI <noreply@clueai.app>",
            "to": [to_email],
            "subject": "ClueAI 密码重置验证码",
            "html": f"""
            <p>你好，</p>
            <p>你的密码重置验证码为：</p>
            <h2 style="letter-spacing:4px">{code}</h2>
            <p>验证码 10 分钟内有效，请勿泄露给他人。</p>
            <p>如非本人操作，请忽略此邮件。</p>
            """,
        })
        return True
    except Exception:
        return False
