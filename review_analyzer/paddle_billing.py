"""Paddle 计费集成 — Overlay Checkout + 计费状态查询"""

from __future__ import annotations

import json
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

# Fix E: 兼容 PADDLE_CLIENT_TOKEN 和 NEXT_PUBLIC_PADDLE_CLIENT_TOKEN 两种命名
PADDLE_CLIENT_TOKEN = os.environ.get("PADDLE_CLIENT_TOKEN") or os.environ.get("NEXT_PUBLIC_PADDLE_CLIENT_TOKEN") or ""
PADDLE_PRICE_ID = os.getenv("PADDLE_PRICE_ID", "")

# Fix E: 兼容 PADDLE_ENVIRONMENT 和 NEXT_PUBLIC_PADDLE_ENV 两种命名
_env = os.environ.get("PADDLE_ENVIRONMENT") or os.environ.get("NEXT_PUBLIC_PADDLE_ENV") or "production"

# 各 tier × period 的 price_id（Step 0 由 Erika 补齐到 .env）
PADDLE_PRO_YEARLY_PRICE_ID = os.getenv("PADDLE_PRO_YEARLY_PRICE_ID", "")
PADDLE_STARTER_PRICE_ID = os.getenv("PADDLE_STARTER_PRICE_ID", "")
PADDLE_STARTER_YEARLY_PRICE_ID = os.getenv("PADDLE_STARTER_YEARLY_PRICE_ID", "")
PADDLE_TEAM_PRICE_ID = os.getenv("PADDLE_TEAM_PRICE_ID", "")
PADDLE_TEAM_YEARLY_PRICE_ID = os.getenv("PADDLE_TEAM_YEARLY_PRICE_ID", "")


def _resolve_price_id(plan_key: str, period: str) -> str:
    """根据 plan_key + period 解析对应的 Paddle price_id。"""
    mapping: dict[tuple[str, str], str] = {
        ("starter", "monthly"): PADDLE_STARTER_PRICE_ID,
        ("starter", "annual"): PADDLE_STARTER_YEARLY_PRICE_ID,
        ("pro", "monthly"): PADDLE_PRICE_ID,  # 旧命名兼容
        ("pro", "annual"): PADDLE_PRO_YEARLY_PRICE_ID,
        ("team", "monthly"): PADDLE_TEAM_PRICE_ID,
        ("team", "annual"): PADDLE_TEAM_YEARLY_PRICE_ID,
    }
    return mapping.get((plan_key, period), "")


def is_billing_configured() -> bool:
    """检查 Paddle 前端支付所需配置是否完整。"""
    return bool(PADDLE_CLIENT_TOKEN and PADDLE_PRICE_ID)


def get_checkout_html(
    user_id: int,
    user_email: str,
    success_url: str,
    plan_key: str = "pro",
    period: str = "monthly",
    paddle_customer_id: str | None = None,
) -> str:
    """生成 Paddle.js overlay checkout 的 HTML 片段。

    根据 plan_key + period 解析 price_id；若对应 price_id 为空则返回空字符串，
    触发前端 !configured 分支。

    paddle_customer_id 用于 Paddle Retain：回头客识别，传入已登录用户的 Paddle customer ID。
    """
    price_id = _resolve_price_id(plan_key, period)
    if not price_id:
        return ""
    environment_line = 'Paddle.Environment.set("sandbox");' if _env == "sandbox" else ""
    pw_customer_line = ""
    if paddle_customer_id:
        pw_customer_line = f"\n        pwCustomer: {{ id: {json.dumps(paddle_customer_id)} }},"
    return f"""
    <script src="https://cdn.paddle.com/paddle/v2/paddle.js"></script>
    <script type="text/javascript">
      {environment_line}
      Paddle.Initialize({{{pw_customer_line}
        token: {json.dumps(PADDLE_CLIENT_TOKEN)}
      }});
      Paddle.Checkout.open({{
        items: [{{ priceId: {json.dumps(price_id)}, quantity: 1 }}],
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
    return get_user_plan(user_id) in ("pro_early", "pro", "team")
