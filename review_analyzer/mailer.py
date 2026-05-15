from __future__ import annotations

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import streamlit as st


def send_reset_code(to_email: str, code: str) -> tuple[bool, str]:
    cfg = st.secrets["email"]
    smtp_host = cfg.get("smtp_host", "smtp.gmail.com")
    smtp_port = int(cfg.get("smtp_port", 587))
    sender = cfg["sender"]
    password = cfg["password"]

    msg = MIMEMultipart("alternative")
    msg["Subject"] = "ClueAI 密码重置验证码"
    msg["From"] = f"ClueAI <{sender}>"
    msg["To"] = to_email

    html = f"""
    <p>你好，</p>
    <p>你的密码重置验证码为：</p>
    <h2 style="letter-spacing:4px;font-family:monospace">{code}</h2>
    <p>验证码 10 分钟内有效，请勿泄露给他人。</p>
    <p>如非本人操作，请忽略此邮件。</p>
    """
    msg.attach(MIMEText(html, "html"))

    try:
        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.starttls()
            server.login(sender, password)
            server.sendmail(sender, to_email, msg.as_string())
        return True, ""
    except Exception as e:
        return False, str(e)
