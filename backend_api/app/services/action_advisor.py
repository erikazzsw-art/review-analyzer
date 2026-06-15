"""V5-T3 Step 4: LLM 行动建议生成服务

升级触发时调用 DeepSeek 生成结构化行动建议，写入行动中心。
"""
from __future__ import annotations

import json
import logging
from typing import Any

from backend_api.app.services.llm_router import LLMRouter
from review_analyzer.action_store import create_action_item
from review_analyzer.department_router import get_dept_label

logger = logging.getLogger(__name__)

_router: LLMRouter | None = None


def _get_router() -> LLMRouter:
    global _router
    if _router is None:
        _router = LLMRouter()
    return _router


SYSTEM_PROMPT = """\
你是跨境电商产品改善顾问。根据评论分析数据生成可执行的行动建议。

要求：
- 建议必须具体、可操作，避免笼统表述
- 预期验证时间基于产品改善周期合理估算
- 输出严格 JSON 格式"""

USER_PROMPT_TEMPLATE = """\
以下产品问题已连续 {consecutive_count} 个分析周期位于 TOP 问题，需要生成行动建议。

## 问题信息
- 问题标签：{tag_name}（{tag_label}）
- 责任部门：{dept_label}
- 当前占比：{current_pct:.1f}%
- 占比趋势（近 {consecutive_count} 期）：{pct_trend}

## 产品信息
- 产品：{product_name}

## 代表性评论（最多 5 条）
{sample_reviews}

## 输出要求
请输出 JSON：
{{
  "action_title": "简短行动标题（<20字）",
  "suggested_action": "具体行动建议（含步骤，100-200字）",
  "expected_timeline": "预计验证时间（如：2周后 / 下一批评论 / 1个月后）",
  "priority": "high 或 medium"
}}"""


def generate_action_advice(
    tag_name: str,
    dept: str,
    current_pct: float,
    consecutive_count: int,
    pct_trend: list[float],
    product_name: str = "",
    sample_reviews: list[str] | None = None,
) -> dict[str, str] | None:
    """
    调用 LLM 生成行动建议。

    返回:
        {"action_title", "suggested_action", "expected_timeline", "priority"} 或 None（失败时）
    """
    from scripts.aspect_taxonomy import get_aspect_label_zh

    tag_label = get_aspect_label_zh(tag_name)
    dept_label = get_dept_label(dept)
    trend_str = " → ".join([f"{p:.1f}%" for p in pct_trend])

    reviews_text = "无"
    if sample_reviews:
        reviews_text = "\n".join(
            [f"{i+1}. {r[:200]}" for i, r in enumerate(sample_reviews[:5])]
        )

    user_prompt = USER_PROMPT_TEMPLATE.format(
        tag_name=tag_name,
        tag_label=tag_label,
        dept_label=dept_label,
        current_pct=current_pct,
        consecutive_count=consecutive_count,
        pct_trend=trend_str,
        product_name=product_name or "未知产品",
        sample_reviews=reviews_text,
    )

    router = _get_router()
    try:
        resp, model_used = router.completion(
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0.3,
            max_tokens=500,
        )

        content = resp.choices[0].message.content or ""
        result = json.loads(content)

        required_keys = {"action_title", "suggested_action", "expected_timeline", "priority"}
        if not required_keys.issubset(result.keys()):
            logger.warning("action_advisor: LLM output missing keys: %s", result.keys())
            return None

        if result["priority"] not in ("high", "medium"):
            result["priority"] = "high"

        logger.info(
            "action_advisor: generated advice for '%s' via %s",
            tag_name, model_used,
        )
        return result

    except Exception:
        logger.exception("action_advisor: failed to generate advice for '%s'", tag_name)
        return None


def create_escalation_action(
    user_id: int,
    product_id: int | None,
    tag_name: str,
    dept: str,
    current_pct: float,
    consecutive_count: int,
    pct_trend: list[float],
    product_name: str = "",
    sample_reviews: list[str] | None = None,
) -> int | None:
    """
    生成行动建议并写入行动中心。

    返回: action_item_id 或 None（失败时）
    """
    advice = generate_action_advice(
        tag_name=tag_name,
        dept=dept,
        current_pct=current_pct,
        consecutive_count=consecutive_count,
        pct_trend=pct_trend,
        product_name=product_name,
        sample_reviews=sample_reviews,
    )

    if not advice:
        return None

    action_data: dict[str, Any] = {
        "product_id": product_id,
        "title": advice["action_title"],
        "tag_name": tag_name,
        "tag_type": "issue",
        "current_pct": current_pct,
        "owner_role": get_dept_label(dept),
        "suggested_action": advice["suggested_action"],
        "expected_effect_batch": advice["expected_timeline"],
        "status": "todo",
    }

    try:
        action_id = create_action_item(user_id, action_data)
        logger.info(
            "action_advisor: created action_item #%d for '%s'", action_id, tag_name
        )
        return action_id
    except Exception:
        logger.exception("action_advisor: failed to create action_item for '%s'", tag_name)
        return None
