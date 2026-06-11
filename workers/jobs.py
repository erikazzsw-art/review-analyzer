from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from backend_api.app.services.category_grouper import aspects_to_legacy_schema
from backend_api.app.services.deep_analyzer import analyze_batch as deep_analyze_batch
from backend_api.app.services.prompt_registry import DEFAULT_ANNOTATE_VERSION
from backend_api.app.services.taxonomy_loader import (
    render_aspects_block,
    resolve_aspects,
)
from review_analyzer.database import (
    add_comments_batch,
    create_session,
    get_unprocessed_comments,
    get_upload_job,
    update_comment_analysis,
    update_session_stats,
    update_upload_job,
)
from review_analyzer.product_store import create_product, get_product_by_parent_id
from review_analyzer.rag import embed_session_comments

from .queue import get_queue

# V4-T3 集成：worker 现在使用 backend_api/app/services/deep_analyzer (annotate v2.1, 92.1% 准确率)
# 旧 review_analyzer.analyzer.analyze_batch 仍保留供 Streamlit 直接调用，不在 worker 通道使用
PROMPT_VERSION = DEFAULT_ANNOTATE_VERSION  # "v2.1"
ANALYZER_VERSION = "v4_deep"

logger = logging.getLogger(__name__)


def _build_comments(
    payload_comments: list[dict[str, Any]],
    product_id: str,
    version: str,
) -> list[dict[str, Any]]:
    comments: list[dict[str, Any]] = []
    for comment in payload_comments:
        comments.append(
            {
                "product_id": product_id,
                "version": version,
                "content": str(comment.get("content") or ""),
                "rating": comment.get("rating"),
                "date": comment.get("date"),
                "reviewer": comment.get("reviewer"),
                "source": comment.get("source"),
                "content_hash": None,
            }
        )
    return comments


def process_upload_job(user_id: int, job_id: int) -> None:
    try:
        job = get_upload_job(user_id, job_id)
        if not job:
            return

        payload = job.get("payload_json") or {}
        comments_payload = payload.get("comments") or []
        product_id = str(job.get("product_id") or payload.get("product_id") or "")
        version = str(job.get("version") or payload.get("version") or "V1")
        workflow_purpose = job.get("workflow_purpose") or payload.get("workflow_purpose")
        product_ref_id = job.get("product_ref_id") or payload.get("product_ref_id")
        variant_ref_id = job.get("variant_ref_id") or payload.get("variant_ref_id")

        update_upload_job(user_id, job_id, {"status": "processing"})

        if product_ref_id is None:
            existing_product = get_product_by_parent_id(user_id, product_id)
            if existing_product:
                product_ref_id = int(existing_product["id"])
            else:
                product_ref_id = create_product(
                    user_id,
                    {
                        "parent_product_id": product_id,
                        "name": payload.get("product_name"),
                        "platform": payload.get("platform"),
                        "category": payload.get("category"),
                        "lifecycle_stage": "growth",
                        "current_version": version,
                        "owner_role": "运营",
                    },
                )

        session_id = create_session(
            user_id,
            {
                "product_id": product_id,
                "version": version,
                "auto_title": (
                    f"{datetime.now().strftime('%Y-%m-%d')} | {product_id} | "
                    f"{workflow_purpose or '日常评论分析'} | {len(comments_payload)}条"
                ),
                "date_range_start": payload.get("date_start"),
                "date_range_end": payload.get("date_end"),
                "total_reviews": len(comments_payload),
                "positive_count": 0,
                "negative_count": 0,
                "category": payload.get("category"),
                "prompt_version": PROMPT_VERSION,
                "version_notes": payload.get("version_notes"),
                "workflow_purpose": workflow_purpose,
                "product_ref_id": product_ref_id,
                "variant_ref_id": variant_ref_id,
            },
        )

        comments_to_insert = _build_comments(comments_payload, product_id, version)
        for comment in comments_to_insert:
            comment["session_id"] = session_id
        add_comments_batch(user_id, comments_to_insert)

        update_upload_job(
            user_id,
            job_id,
            {
                "session_id": session_id,
                "total_rows": len(comments_to_insert),
            },
        )

        unprocessed = get_unprocessed_comments(user_id, session_id)
        if unprocessed:
            try:
                embed_session_comments(user_id, session_id)
            except Exception:
                pass

            def _progress_callback(current: int, total: int) -> None:
                update_upload_job(
                    user_id,
                    job_id,
                    {
                        "processed_rows": current,
                    },
                )

            # V4-T3 v2.1 深度分析（92.1% 准确率，三层架构）
            sub_category = str(payload.get("category") or "家具家居")
            # V4-T1.5: 按 sub_category 查 category_aspect_taxonomy 注入动态 aspect 列表
            # taxonomy 未命中（用户上传非 5 类目） → resolve_aspects 自动 fallback 通用 base 块
            aspects, taxonomy_hit = resolve_aspects(sub_category)
            aspects_block = render_aspects_block(aspects)
            allowed_aspects = [a["key"] for a in aspects]
            logger.info(
                "upload_job %s: sub_category=%r taxonomy_hit=%s aspects_count=%d prompt=%s",
                job_id, sub_category, taxonomy_hit, len(aspects), PROMPT_VERSION,
            )
            v4_results = deep_analyze_batch(
                comments=[{"content": row.get("content", ""), "rating": row.get("rating"), "title": row.get("title", "")} for row in unprocessed],
                sub_category=sub_category,
                prompt_version=PROMPT_VERSION,
                aspects_block=aspects_block,
                allowed_aspects=allowed_aspects,
            )
            _progress_callback(len(unprocessed), len(unprocessed))
            results = []
            for comment, v4 in zip(unprocessed, v4_results):
                # V4 失败时降级为 legacy schema 占位
                if v4.get("error"):
                    results.append({
                        "sentiment": "unrecognizable",
                        "content_sentiment": "unrecognizable",
                        "category": "无效乱码",
                        "priority": "无",
                        "reason": "",
                        "improvement": "",
                        "issue_tag": "",
                        "highlight_tag": "",
                        "aspects_json": None,
                        "analyzer_version": ANALYZER_VERSION,
                    })
                    continue
                # V4 → legacy schema 转换（双写）
                legacy = aspects_to_legacy_schema(
                    aspects=v4.get("aspects", []),
                    sentiment=v4.get("sentiment", "neutral"),
                    content=comment.get("content", ""),
                    pain_points=v4.get("pain_points", []),
                    highlights=v4.get("highlights", []),
                )
                legacy["aspects_json"] = {
                    "sentiment": v4.get("sentiment"),
                    "aspects": v4.get("aspects", []),
                    "pain_points": v4.get("pain_points", []),
                    "highlights": v4.get("highlights", []),
                    "evidence_level_overall": v4.get("evidence_level_overall"),
                    "prompt_version": v4.get("prompt_version", PROMPT_VERSION),
                }
                legacy["analyzer_version"] = ANALYZER_VERSION
                results.append(legacy)
        else:
            results = []

        positive_count = 0
        negative_count = 0
        for comment, result in zip(unprocessed, results):
            rating = comment.get("rating")
            if rating is not None:
                try:
                    rating_val = int(float(rating))
                    result["sentiment"] = "negative" if rating_val <= 3 else "positive"
                except (TypeError, ValueError):
                    pass
            update_comment_analysis(user_id, int(comment["id"]), result)
            if result.get("sentiment") == "positive":
                positive_count += 1
            elif result.get("sentiment") == "negative":
                negative_count += 1

        update_session_stats(user_id, session_id, len(unprocessed), positive_count, negative_count)
        update_upload_job(
            user_id,
            job_id,
            {
                "status": "done",
                "processed_rows": len(unprocessed),
                "positive_count": positive_count,
                "negative_count": negative_count,
            },
        )
    except Exception as exc:
        update_upload_job(
            user_id,
            job_id,
            {
                "status": "failed",
                "error_message": str(exc),
            },
        )
        raise


def enqueue_upload_job_task(user_id: int, job_id: int) -> str:
    queue = get_queue()
    queued_job = queue.enqueue(
        process_upload_job,
        user_id,
        job_id,
        job_id=f"upload-job-{job_id}",
        description=f"Process upload job {job_id}",
        result_ttl=0,
        failure_ttl=7 * 24 * 60 * 60,
    )
    return queued_job.id
