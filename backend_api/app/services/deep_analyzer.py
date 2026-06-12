"""V4-T3 深度分析服务（生产版）.

业界依据：
- Shulex / VOC AI 三层架构（业界领导者验证）
- 详见 docs/v4-t3-integration-plan-2026-06-06.md

设计目标：
- 调用 prompts/annotate_v2.1.md 的 prompt（92.1% Golden Set 准确率）
- 输出 V4-T3 schema：sentiment + 19 类 aspects + pain_points + highlights
- 与现有 review_analyzer.analyzer.analyze_batch 接口对齐
- 不映射回中文 11 类 category（由 category_grouper 完成）

模型选型（V4-T4 Step 4: 多模型 Fallback 链路）：
- 主：DeepSeek-V3（deepseek-chat）— 中文优势 + 成本最低
- 备 1：OpenAI gpt-4o-mini — API 稳定性最高
- 备 2：Qwen-Plus — 国内可用性兜底
- 路由：llm_router.py 自动熔断切换，业务无感知

成本（DeepSeek 价格: ¥1/M input + ¥8/M output）:
- 100 条评论: ~¥0.03
- 10000 条评论: ~¥3
"""
from __future__ import annotations

import json
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

from backend_api.app.core.aspect_taxonomy import (
    ASPECT_KEYS,
    EVIDENCE_LEVELS,
    POLARITY_VALUES,
    SENTIMENT_VALUES,
)
from backend_api.app.services.llm_router import router_completion
from backend_api.app.services.prompt_registry import load_prompt

logger = logging.getLogger(__name__)

DEFAULT_MAX_WORKERS = 8


def _validate_annotation(obj: Any, allowed_aspects: set[str] | None = None) -> tuple[bool, str]:
    """后置校验 LLM 返回的 JSON 是否符合 V4-T3 schema.

    Args:
        obj: LLM 返回的 JSON 对象
        allowed_aspects: 允许的 aspect key 集合（v2.4 动态注入时传入）.
            None 时回退到硬编码 ASPECT_KEYS（v2.1/v2.3 旧行为）.
    """
    valid_keys = allowed_aspects if allowed_aspects else set(ASPECT_KEYS)

    if not isinstance(obj, dict):
        return False, "not_a_dict"
    if obj.get("sentiment") not in SENTIMENT_VALUES:
        return False, f"invalid_sentiment_{obj.get('sentiment')!r}"

    aspects = obj.get("aspects")
    if not isinstance(aspects, list):
        return False, "aspects_not_a_list"
    for i, a in enumerate(aspects):
        if not isinstance(a, dict):
            return False, f"aspect[{i}]_not_a_dict"
        if a.get("key") not in valid_keys:
            return False, f"aspect[{i}].key_invalid_{a.get('key')!r}"
        if a.get("polarity") not in POLARITY_VALUES:
            return False, f"aspect[{i}].polarity_invalid"
        if not isinstance(a.get("evidence_span"), str):
            return False, f"aspect[{i}].evidence_span_not_str"
        if a.get("evidence_level") not in EVIDENCE_LEVELS:
            return False, f"aspect[{i}].evidence_level_invalid"

    if not isinstance(obj.get("pain_points"), list):
        return False, "pain_points_not_a_list"
    if not isinstance(obj.get("highlights"), list):
        return False, "highlights_not_a_list"
    if obj.get("evidence_level_overall") not in EVIDENCE_LEVELS:
        return False, "evidence_level_overall_invalid"
    return True, ""


def _build_user_prompt(content: str, rating: int | None, sub_category: str, title: str = "") -> str:
    rating_str = f"{int(rating)} stars" if rating is not None else "N/A"
    return (
        f"Sub-category: {sub_category}\n"
        f"Rating: {rating_str}\n"
        f"Title: {title}\n"
        f"Content: {content}\n\n"
        f"Output JSON:"
    )


def analyze_one(
    content: str,
    rating: int | None,
    sub_category: str = "家具家居",
    title: str = "",
    prompt_version: str = "v2.1",
    max_retries: int = 1,
    aspects_block: str | None = None,
    allowed_aspects: list[str] | None = None,
    client: Any = None,
) -> dict[str, Any]:
    """对单条评论做 V4-T3 深度分析（通过 llm_router 自动 fallback）.

    client 参数仅用于单元测试注入 mock，生产代码不传。
    """
    p = load_prompt("annotate", prompt_version)
    system_prompt = p.system_prompt

    if "{{ASPECTS_BLOCK}}" in system_prompt:
        if aspects_block is None:
            from backend_api.app.services.taxonomy_loader import (
                get_fallback_aspects,
                render_aspects_block,
            )
            logger.warning(
                "deep_analyzer.analyze_one: prompt %s contains {{ASPECTS_BLOCK}} "
                "but no aspects_block was provided; using fallback base block",
                prompt_version,
            )
            aspects_block = render_aspects_block(get_fallback_aspects())
        system_prompt = system_prompt.replace("{{ASPECTS_BLOCK}}", aspects_block)

    allowed_set: set[str] | None = set(allowed_aspects) if allowed_aspects else None
    user_msg = _build_user_prompt(content, rating, sub_category, title)
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_msg},
    ]

    last_error = ""
    for _attempt in range(max_retries + 1):
        try:
            if client is not None:
                resp = client.chat.completions.create(
                    model="test",
                    messages=messages,
                    response_format={"type": "json_object"},
                    temperature=0,
                    max_tokens=800,
                )
                model_name = "test"
            else:
                resp, model_name = router_completion(
                    messages=messages,
                    response_format={"type": "json_object"},
                    temperature=0,
                    max_tokens=800,
                )
            raw = resp.choices[0].message.content
            try:
                obj = json.loads(raw)
            except json.JSONDecodeError as je:
                last_error = f"json_decode_failed: {je}"
                continue
            ok, err = _validate_annotation(obj, allowed_aspects=allowed_set)
            if not ok:
                last_error = f"schema_invalid: {err}"
                continue
            return {
                **obj,
                "tokens_in": resp.usage.prompt_tokens,
                "tokens_out": resp.usage.completion_tokens,
                "prompt_version": prompt_version,
                "model_used": model_name,
            }
        except Exception as e:
            last_error = str(e)[:200]
    logger.warning("deep_analyzer.analyze_one failed: %s", last_error)
    return {"error": last_error, "prompt_version": prompt_version}


def analyze_batch(
    comments: list[dict[str, Any]],
    sub_category: str = "家具家居",
    max_workers: int = DEFAULT_MAX_WORKERS,
    prompt_version: str = "v2.1",
    aspects_block: str | None = None,
    allowed_aspects: list[str] | None = None,
) -> list[dict[str, Any]]:
    """批量分析评论（通过 llm_router 自动 fallback）."""
    results: list[dict[str, Any] | None] = [None] * len(comments)

    def _process(idx: int, c: dict[str, Any]) -> tuple[int, dict[str, Any]]:
        return idx, analyze_one(
            content=c.get("content", ""),
            rating=c.get("rating"),
            sub_category=sub_category,
            title=c.get("title", ""),
            prompt_version=prompt_version,
            aspects_block=aspects_block,
            allowed_aspects=allowed_aspects,
        )

    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        futures = [ex.submit(_process, i, c) for i, c in enumerate(comments)]
        for fut in as_completed(futures):
            idx, result = fut.result()
            results[idx] = result

    return [r for r in results if r is not None]
