"""V4-T3 深度分析服务（生产版）.

业界依据：
- Shulex / VOC AI 三层架构（业界领导者验证）
- 详见 docs/v4-t3-integration-plan-2026-06-06.md

设计目标：
- 调用 prompts/annotate_v2.1.md 的 prompt（92.1% Golden Set 准确率）
- 输出 V4-T3 schema：sentiment + 19 类 aspects + pain_points + highlights
- 与现有 review_analyzer.analyzer.analyze_batch 接口对齐
- 不映射回中文 11 类 category（由 category_grouper 完成）

模型选型：
- DeepSeek-V4-flash（兼容 OpenAI SDK）
- json_object 模式 + 后置 schema 校验
- 失败重试 1 次

成本（DeepSeek 价格: ¥1/M input + ¥8/M output）:
- 100 条评论: ~¥0.03
- 10000 条评论: ~¥3
"""
from __future__ import annotations

import json
import logging
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

from openai import OpenAI

from backend_api.app.core.aspect_taxonomy import (
    ASPECT_KEYS,
    EVIDENCE_LEVELS,
    POLARITY_VALUES,
    SENTIMENT_VALUES,
)
from backend_api.app.services.prompt_registry import load_prompt

logger = logging.getLogger(__name__)

MODEL = "deepseek-chat"
BASE_URL = "https://api.deepseek.com"
DEFAULT_MAX_WORKERS = 8
DEFAULT_TIMEOUT_S = 30.0


def _validate_annotation(obj: Any) -> tuple[bool, str]:
    """后置校验 LLM 返回的 JSON 是否符合 V4-T3 schema."""
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
        if a.get("key") not in ASPECT_KEYS:
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


def _get_api_key() -> str:
    """从 env 或 .env 文件读取 DeepSeek API key."""
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if api_key:
        return api_key
    from pathlib import Path
    env_path = Path(__file__).parent.parent.parent.parent / ".env"
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            if line.startswith("DEEPSEEK_API_KEY="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    raise RuntimeError("DEEPSEEK_API_KEY not configured")


def analyze_one(
    content: str,
    rating: int | None,
    sub_category: str = "家具家居",
    title: str = "",
    client: OpenAI | None = None,
    prompt_version: str = "v2.1",
    max_retries: int = 1,
) -> dict[str, Any]:
    """对单条评论做 V4-T3 深度分析.

    Returns:
        成功: {sentiment, aspects, pain_points, highlights, evidence_level_overall,
              tokens_in, tokens_out, prompt_version}
        失败: {error, prompt_version}
    """
    if client is None:
        client = OpenAI(api_key=_get_api_key(), base_url=BASE_URL, timeout=DEFAULT_TIMEOUT_S)

    p = load_prompt("annotate", prompt_version)
    system_prompt = p.system_prompt
    user_msg = _build_user_prompt(content, rating, sub_category, title)

    last_error = ""
    for attempt in range(max_retries + 1):
        try:
            resp = client.chat.completions.create(
                model=MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_msg},
                ],
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
            ok, err = _validate_annotation(obj)
            if not ok:
                last_error = f"schema_invalid: {err}"
                continue
            return {
                **obj,
                "tokens_in": resp.usage.prompt_tokens,
                "tokens_out": resp.usage.completion_tokens,
                "prompt_version": prompt_version,
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
) -> list[dict[str, Any]]:
    """批量分析评论，与 review_analyzer.analyzer.analyze_batch 接口对齐.

    Args:
        comments: list of dict with at least {content, rating, title?}
        sub_category: 子品类（家具家居 / 床垫 / 床架 等，影响 prompt 上下文）
        max_workers: 并发线程数
        prompt_version: prompt 版本（默认 v2.1）

    Returns:
        list of dict, 每个元素是 analyze_one 的返回值（成功或失败）
    """
    client = OpenAI(api_key=_get_api_key(), base_url=BASE_URL, timeout=DEFAULT_TIMEOUT_S)
    results: list[dict[str, Any] | None] = [None] * len(comments)

    def _process(idx: int, c: dict[str, Any]) -> tuple[int, dict[str, Any]]:
        return idx, analyze_one(
            content=c.get("content", ""),
            rating=c.get("rating"),
            sub_category=sub_category,
            title=c.get("title", ""),
            client=client,
            prompt_version=prompt_version,
        )

    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        futures = [ex.submit(_process, i, c) for i, c in enumerate(comments)]
        for fut in as_completed(futures):
            idx, result = fut.result()
            results[idx] = result

    return [r for r in results if r is not None]
