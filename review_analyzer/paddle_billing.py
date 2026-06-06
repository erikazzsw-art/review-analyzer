"""Paddle 计费集成 — Overlay Checkout + 计费状态查询"""

from __future__ import annotations

import json
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

PADDLE_CLIENT_TOKEN = os.getenv("PADDLE_CLIENT_TOKEN", "")
PADDLE_PRICE_ID = os.getenv("PADDLE_PRICE_ID", "")
PADDLE_ENVIRONMENT = os.getenv("PADDLE_ENVIRONMENT", "production")


def is_billing_configured() -> bool:
    """检查 Paddle 前端支付所需配置是否完整。"""
    return bool(PADDLE_CLIENT_TOKEN and PADDLE_PRICE_ID)


def get_checkout_html(user_id: int, user_email: str, success_url: str) -> str:
    """生成 Paddle.js overlay checkout 的 HTML 片段，嵌入 Streamlit 页面"""
    environment_line = 'Paddle.Environment.set("sandbox");' if PADDLE_ENVIRONMENT == "sandbox" else ""
    return f"""
    <script src="https://cdn.paddle.com/paddle/v2/paddle.js"></script>
    <script type="text/javascript">
      {environment_line}
      Paddle.Initialize({{
        token: {json.dumps(PADDLE_CLIENT_TOKEN)}
      }});
      Paddle.Checkout.open({{
        items: [{{ priceId: {json.dumps(PADDLE_PRICE_ID)}, quantity: 1 }}],
        customer: {{ email: {json.dumps(user_email)} }},
        customData: {{ user_id: {json.dumps(str(user_id))} }},
        settings: {{
          successUrl: {json.dumps(success_url)}
        }}
      }});
    </script>
    """


def is_pro_user(user_id: int) -> bool:
    from .database import get_user_plan
    return get_user_plan(user_id) == "pro"
