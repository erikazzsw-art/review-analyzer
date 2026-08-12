"""V4-T3 深度分析服务（生产版）.

业界依据：
- Shulex / VOC AI 三层架构（业界领导者验证）
- 详见 docs/v4-t3-integration-plan-2026-06-06.md

设计目标：
- 调用 prompts/annotate_v2.1.md 的 prompt（92.1% Golden Set 准确率）
- 输出 V4-T3 schema：sentiment + 19 类 aspects + pain_points + highlights
- 与现有 review_analyzer.analyzer.analyze_batch 接口对齐
- 不映射回中文 11 类 category（由 category_grouper 完成）

模型选型（V4-T4 Step 4: 多模型 Fallback 链路 · 2026-08 更新）：
- 主：OpenAI gpt-4o-mini — API 稳定性最高
- 备：Gemini 2.0 Flash — 海外合规 + 成本更低
- 路由：llm_router.py 自动熔断切换，业务无感知

成本（Gemini 2.0 Flash 价格: $0.10/M input + $0.40/M output ≈ ¥0.7/M input + ¥2.9/M output）:
- 100 条评论: ~$0.005
- 10000 条评论: ~$0.50
"""
from __future__ import annotations

import json
import logging
import time
from collections import Counter
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

DEFAULT_MAX_WORKERS = 2


def _estimate_cost(model: str, tokens_in: int, tokens_out: int) -> float:
    """Rough cost estimation in yuan."""
    rates: dict[str, tuple[float, float]] = {
        "gemini-flash-latest": (0.7, 2.9),   # $0.10/$0.40 → ¥0.70/¥2.90 per M (pricing may vary by resolved version)
        "gpt-4o-mini": (1.05, 4.2),           # $0.15/$0.60 per M
    }
    r_in, r_out = rates.get(model, (1.0, 4.0))
    return (tokens_in * r_in + tokens_out * r_out) / 1_000_000


def _track_call(
    user_id: int | None,
    model: str,
    prompt_version: str,
    resp: Any,
    latency_ms: int,
    success: bool,
    error_type: str | None,
    *,
    attempt: int | None = None,
    error_detail: str | None = None,
    schema_error: str | None = None,
    content_hash: str | None = None,
    sub_category: str | None = None,
    locale: str | None = None,
    retry_count: int | None = None,
    final_success: bool | None = None,
) -> None:
    if user_id is None:
        return
    try:
        from backend_api.app.services.analytics import track_llm_call
        tokens_in = resp.usage.prompt_tokens if resp and resp.usage else 0
        tokens_out = resp.usage.completion_tokens if resp and resp.usage else 0
        track_llm_call(
            user_id,
            model=model,
            prompt_version=prompt_version,
            input_tokens=tokens_in,
            output_tokens=tokens_out,
            latency_ms=latency_ms,
            cost_yuan=_estimate_cost(model, tokens_in, tokens_out),
            success=success,
            error_type=error_type,
            attempt=attempt,
            error_detail=error_detail,
            schema_error=schema_error,
            content_hash=content_hash,
            sub_category=sub_category,
            locale=locale,
            retry_count=retry_count,
            final_success=final_success,
        )
    except Exception as e:
        logger.debug("_track_call failed (non-fatal): %s", e)


def _emit_trace(
    trace_callback: Any,
    kind: str,
    name: str,
    **details: Any,
) -> None:
    if trace_callback is None:
        return
    try:
        trace_callback(kind, name, details)
    except Exception as exc:
        logger.debug("deep_analyzer trace callback failed (non-fatal): %s", exc)


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
    user_id: int | None = None,
    locale: str = "en",
    comment_id: int | None = None,
    content_hash: str | None = None,
    trace_callback: Any = None,
) -> dict[str, Any]:
    """对单条评论做 V4-T3 深度分析（通过 llm_router 自动 fallback）.

    client 参数仅用于单元测试注入 mock，生产代码不传。
    user_id 非空时自动调用 track_llm_call 记录到 analytics_events。
    locale: "en"/"zh" 均走 GPT-4o-mini → Gemini 双模型链（默认 en，海外优先）。
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
    quality_counts: Counter[str] = Counter()
    route_counts: Counter[str] = Counter()
    schema_errors: list[dict[str, Any]] = []  # 记录每次 schema 失败详情

    def _trace_details(**extra: Any) -> dict[str, Any]:
        base = {
            "comment_id": comment_id,
            "content_hash": content_hash,
            "prompt_version": prompt_version,
            "locale": locale,
            "sub_category": sub_category,
        }
        base.update(extra)
        return {key: value for key, value in base.items() if value is not None}

    def _route_trace(kind: str, name: str, details: dict[str, Any]) -> None:
        route_counts[name] += 1
        _emit_trace(trace_callback, kind, name, **_trace_details(**details))

    for _attempt in range(max_retries + 1):
        t0 = time.perf_counter()
        try:
            if client is not None:
                route_counts["llm_provider_attempt"] += 1
                _emit_trace(
                    trace_callback,
                    "event",
                    "llm_provider_attempt",
                    **_trace_details(
                        provider="test",
                        model="test",
                        provider_attempt=1,
                        retry_attempt=_attempt + 1,
                        max_retries=max_retries + 1,
                    ),
                )
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
                    locale=locale,
                    trace_callback=_route_trace,
                )
            latency_ms = int((time.perf_counter() - t0) * 1000)
            raw = resp.choices[0].message.content
            try:
                obj = json.loads(raw)
            except json.JSONDecodeError as je:
                last_error = f"json_decode_failed: {je}"
                quality_counts["json_decode"] += 1
                _emit_trace(
                    trace_callback,
                    "event",
                    "llm_quality",
                    **_trace_details(
                        model=model_name,
                        attempt=_attempt + 1,
                        retry_count=_attempt,
                        error_type="json_decode",
                        error_detail=str(je)[:200],
                        json_decode=True,
                        schema_invalid=False,
                        final_success=False,
                    ),
                )
                _track_call(
                    user_id,
                    model_name,
                    prompt_version,
                    resp,
                    latency_ms,
                    False,
                    "json_decode",
                    attempt=_attempt + 1,
                    error_detail=str(je)[:200],
                    content_hash=content_hash,
                    sub_category=sub_category,
                    locale=locale,
                    retry_count=_attempt,
                    final_success=False,
                )
                continue
            ok, err = _validate_annotation(obj, allowed_aspects=allowed_set)
            if not ok:
                last_error = f"schema_invalid: {err}"
                quality_counts["schema_invalid"] += 1
                schema_errors.append({
                    "attempt": _attempt + 1,
                    "error": err,
                    "model": model_name,
                })
                _emit_trace(
                    trace_callback,
                    "event",
                    "llm_quality",
                    **_trace_details(
                        model=model_name,
                        attempt=_attempt + 1,
                        retry_count=_attempt,
                        error_type="schema_invalid",
                        schema_error=err,
                        json_decode=False,
                        schema_invalid=True,
                        final_success=False,
                    ),
                )
                _track_call(
                    user_id,
                    model_name,
                    prompt_version,
                    resp,
                    latency_ms,
                    False,
                    "schema_invalid",
                    attempt=_attempt + 1,
                    schema_error=err,
                    content_hash=content_hash,
                    sub_category=sub_category,
                    locale=locale,
                    retry_count=_attempt,
                    final_success=False,
                )
                # 向 LLM 反馈校验错误，使重试有意义
                if _attempt < max_retries:
                    if allowed_set:
                        allowed_keys_sorted = sorted(allowed_set)
                        feedback = (
                            f"Your last JSON response was REJECTED by schema validation: {err}.\n"
                            f"The allowed aspect keys for this review are: {', '.join(allowed_keys_sorted)}.\n"
                            f"Allowed polarities: positive, negative, neutral.\n"
                            f"Allowed evidence_levels: certain, probable, uncertain.\n"
                            f"Please fix the error: replace any invalid key with the most appropriate key "
                            f"from the allowed list (or use \"other\" if no key fits), fix invalid polarity "
                            f"values, and ensure ALL fields match the schema. "
                            f"Output ONLY valid JSON."
                        )
                    else:
                        feedback = (
                            f"Your last JSON response was REJECTED by schema validation: {err}.\n"
                            f"Allowed polarities: positive, negative, neutral.\n"
                            f"Allowed evidence_levels: certain, probable, uncertain.\n"
                            f"Please fix the error and output ONLY valid JSON that matches "
                            f"the required schema exactly."
                        )
                    messages.append({"role": "user", "content": feedback})
                continue
            route_counts["llm_provider_success"] += 1 if client is not None else 0
            _emit_trace(
                trace_callback,
                "event",
                "llm_quality",
                **_trace_details(
                    model=model_name,
                    attempt=_attempt + 1,
                    retry_count=_attempt,
                    json_decode=False,
                    schema_invalid=False,
                    final_success=True,
                    latency_ms=latency_ms,
                    tokens_in=resp.usage.prompt_tokens,
                    tokens_out=resp.usage.completion_tokens,
                ),
            )
            _track_call(
                user_id,
                model_name,
                prompt_version,
                resp,
                latency_ms,
                True,
                None,
                attempt=_attempt + 1,
                content_hash=content_hash,
                sub_category=sub_category,
                locale=locale,
                retry_count=_attempt,
                final_success=True,
            )
            return {
                **obj,
                "tokens_in": resp.usage.prompt_tokens,
                "tokens_out": resp.usage.completion_tokens,
                "prompt_version": prompt_version,
                "model_used": model_name,
                "latency_ms": latency_ms,
                "retry_count": _attempt,
                "final_success": True,
                "json_decode_count": quality_counts["json_decode"],
                "schema_invalid_count": quality_counts["schema_invalid"],
                "exception_count": quality_counts["exception"],
                "llm_route_counts": dict(route_counts),
            }
        except Exception as e:
            latency_ms = int((time.perf_counter() - t0) * 1000)
            last_error = str(e)[:200]
            quality_counts["exception"] += 1
            _emit_trace(
                trace_callback,
                "event",
                "llm_quality",
                **_trace_details(
                    attempt=_attempt + 1,
                    retry_count=_attempt,
                    error_type="exception",
                    error_detail=last_error,
                    json_decode=False,
                    schema_invalid=False,
                    final_success=False,
                    latency_ms=latency_ms,
                ),
            )
            _track_call(
                user_id,
                "unknown",
                prompt_version,
                None,
                latency_ms,
                False,
                "exception",
                attempt=_attempt + 1,
                error_detail=last_error,
                content_hash=content_hash,
                sub_category=sub_category,
                locale=locale,
                retry_count=_attempt,
                final_success=False,
            )
    logger.warning("deep_analyzer.analyze_one failed: %s (schema_errors=%d)", last_error, len(schema_errors))
    if last_error.startswith("json_decode"):
        final_error_type = "json_decode"
    elif last_error.startswith("schema_invalid"):
        final_error_type = "schema_invalid"
    else:
        final_error_type = "exception"
    return {
        "error": last_error,
        "prompt_version": prompt_version,
        "retry_count": max_retries,
        "final_success": False,
        "json_decode_count": quality_counts["json_decode"],
        "schema_invalid_count": quality_counts["schema_invalid"],
        "exception_count": quality_counts["exception"],
        "error_type": final_error_type,
        "schema_errors": schema_errors,
        "llm_route_counts": dict(route_counts),
    }


def analyze_batch(
    comments: list[dict[str, Any]],
    sub_category: str = "家具家居",
    max_workers: int = DEFAULT_MAX_WORKERS,
    prompt_version: str = "v2.1",
    aspects_block: str | None = None,
    allowed_aspects: list[str] | None = None,
    progress_callback: Any = None,
    user_id: int | None = None,
    locale: str = "en",
    trace_callback: Any = None,
) -> list[dict[str, Any]]:
    """批量分析评论（通过 llm_router 自动 fallback）.

    locale: "en"/"zh" 均走 GPT-4o-mini → Gemini 双模型链（默认 en，海外优先）。
    """
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
            user_id=user_id,
            locale=locale,
            comment_id=c.get("id"),
            content_hash=c.get("content_hash"),
            trace_callback=trace_callback,
        )

    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        futures = [ex.submit(_process, i, c) for i, c in enumerate(comments)]
        done_count = 0
        total = len(futures)
        for fut in as_completed(futures):
            idx, result = fut.result()
            results[idx] = result
            done_count += 1
            if progress_callback:
                progress_callback(done_count, total)

    if progress_callback and comments:
        progress_callback(len(comments), len(comments))

    return [r for r in results if r is not None]
