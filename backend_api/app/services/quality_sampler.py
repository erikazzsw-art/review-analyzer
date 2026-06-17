"""OPT-5: 线上标注质量抽样器.

每 N 条分析结果抽 1 条，异步用第二模型做二次评判，
结果写入 annotation_quality_log 表用于监控标注质量漂移。
"""
from __future__ import annotations

import json
import logging
import random
from typing import Any

from backend_api.app.services.llm_router import router_completion

logger = logging.getLogger(__name__)

SAMPLE_RATE = 200

JUDGE_SYSTEM_PROMPT = (
    "You are a quality auditor for review annotations. "
    "Given a customer review and its structured annotation (sentiment, aspects, pain_points, highlights), "
    "judge whether the annotation is correct. "
    "Output JSON: {\"verdict\": \"agree\"|\"disagree\", \"reason\": \"...\"}"
)


def should_sample() -> bool:
    return random.randint(1, SAMPLE_RATE) == 1


def judge_annotation(
    content: str,
    annotation: dict[str, Any],
) -> dict[str, Any] | None:
    """用 LLM 二次评判一条标注是否正确。"""
    user_msg = (
        f"Review content: {content[:2000]}\n\n"
        f"Annotation:\n{json.dumps(annotation, ensure_ascii=False)[:2000]}\n\n"
        "Judge this annotation. Output JSON."
    )
    messages = [
        {"role": "system", "content": JUDGE_SYSTEM_PROMPT},
        {"role": "user", "content": user_msg},
    ]
    try:
        resp, model_name = router_completion(
            messages=messages,
            response_format={"type": "json_object"},
            temperature=0,
            max_tokens=200,
        )
        raw = resp.choices[0].message.content
        result = json.loads(raw)
        result["judge_model"] = model_name
        return result
    except Exception as e:
        logger.warning("quality_sampler.judge_annotation failed: %s", str(e)[:200])
        return None


def log_quality_sample(
    user_id: int,
    comment_id: int,
    content: str,
    annotation: dict[str, Any],
    prompt_version: str,
) -> None:
    """抽样并记录质量评判结果（非阻塞，失败静默）。"""
    if not should_sample():
        return

    verdict = judge_annotation(content, annotation)
    if not verdict:
        return

    try:
        from review_analyzer.database import get_connection

        conn = get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """INSERT INTO annotation_quality_log
                       (user_id, comment_id, prompt_version, verdict, reason, judge_model)
                       VALUES (%s, %s, %s, %s, %s, %s)
                       ON CONFLICT DO NOTHING""",
                    (
                        user_id,
                        comment_id,
                        prompt_version,
                        verdict.get("verdict", "unknown"),
                        verdict.get("reason", ""),
                        verdict.get("judge_model", ""),
                    ),
                )
                conn.commit()
        finally:
            conn.close()
    except Exception as e:
        logger.debug("quality_sampler.log_quality_sample db write failed: %s", str(e)[:100])
