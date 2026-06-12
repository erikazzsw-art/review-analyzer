from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from backend_api.app.services.analysis_cache import (
    CacheResult,
    apply_cache,
    compute_content_hash,
)
from backend_api.app.services.category_grouper import aspects_to_legacy_schema
from backend_api.app.services.clustering import (
    cluster_reviews,
    propagate_cluster_results,
)
from backend_api.app.services.deep_analyzer import analyze_batch as deep_analyze_batch
from backend_api.app.services.prompt_registry import DEFAULT_ANNOTATE_VERSION
from backend_api.app.services.taxonomy_loader import (
    render_aspects_block,
    resolve_aspects,
)
from review_analyzer.database import (
    _estimate_cost_yuan,
    add_comments_batch,
    create_session,
    get_analyzed_by_content_hash,
    get_analyzed_with_embeddings,
    get_session_embeddings,
    get_unprocessed_comments,
    get_upload_job,
    log_llm_usage_batch,
    update_comment_analysis,
    update_comment_cluster,
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
        content = str(comment.get("content") or "")
        rating = comment.get("rating")
        comments.append(
            {
                "product_id": product_id,
                "version": version,
                "content": content,
                "rating": rating,
                "date": comment.get("date"),
                "reviewer": comment.get("reviewer"),
                "source": comment.get("source"),
                "content_hash": compute_content_hash(content, rating),
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

            sub_category = str(payload.get("category") or "家具家居")
            aspects, taxonomy_hit = resolve_aspects(sub_category)
            aspects_block = render_aspects_block(aspects)
            allowed_aspects = [a["key"] for a in aspects]

            # --- V4-T4 Step 3: 多级缓存 ---
            # L1: 收集当前 batch 的 content_hash，查询已有分析结果
            content_hashes = [
                compute_content_hash(c.get("content", ""), c.get("rating"))
                for c in unprocessed
            ]
            existing_analyses = get_analyzed_by_content_hash(user_id, content_hashes)

            # L3 准备：查询同产品已分析+有 embedding 的历史评论
            comments_with_emb = get_session_embeddings(user_id, session_id)
            embeddings_available = comments_with_emb and all(
                c.get("embedding") for c in comments_with_emb
            )

            reference_embeddings: list[list[float]] | None = None
            reference_ids: list[int] | None = None
            reference_results: dict[int, dict] | None = None

            if embeddings_available:
                ref_rows = get_analyzed_with_embeddings(user_id, product_id, limit=500)
                if ref_rows:
                    reference_embeddings = [r["embedding"] for r in ref_rows]
                    reference_ids = [r["id"] for r in ref_rows]
                    reference_results = {
                        r["id"]: {"aspects_json": r["aspects_json"], "sentiment": r["sentiment"], "source_id": r["id"]}
                        for r in ref_rows
                    }

            # 为缓存检查准备评论数据（带 embedding）
            emb_by_id = {c["id"]: c.get("embedding") for c in (comments_with_emb or [])}
            cache_input = []
            for c in unprocessed:
                cache_input.append({
                    "id": c["id"],
                    "content": c.get("content", ""),
                    "rating": c.get("rating"),
                    "embedding": emb_by_id.get(c["id"]),
                })

            cache_result: CacheResult = apply_cache(
                comments=cache_input,
                existing_analyses=existing_analyses,
                reference_embeddings=reference_embeddings,
                reference_ids=reference_ids,
                reference_results=reference_results,
            )

            # 分离：缓存命中 vs 需要 LLM 的评论
            need_llm = [c for c in unprocessed if c["id"] in cache_result.misses]
            id_to_v4: dict[int, dict] = {}

            # 缓存命中的评论直接用缓存结果
            for cid, hit in cache_result.hits.items():
                cached = hit.result
                if isinstance(cached.get("aspects_json"), dict):
                    id_to_v4[cid] = cached["aspects_json"]
                else:
                    id_to_v4[cid] = {
                        "sentiment": cached.get("sentiment"),
                        "aspects": cached.get("aspects", []),
                        "pain_points": cached.get("pain_points", []),
                        "highlights": cached.get("highlights", []),
                        "evidence_level_overall": cached.get("evidence_level_overall", "low"),
                        "prompt_version": cached.get("prompt_version", "cache"),
                    }
                id_to_v4[cid]["cache_hit_level"] = hit.level
                id_to_v4[cid]["cache_source_id"] = hit.source_comment_id

            logger.info(
                "upload_job %s: cache hit=%d miss=%d (stats=%s)",
                job_id, cache_result.hit_count, cache_result.miss_count, cache_result.stats(),
            )

            # --- 对需要 LLM 的评论走聚类+LLM 管道 ---
            if need_llm:
                need_llm_ids = {c["id"] for c in need_llm}
                llm_emb_comments = [
                    c for c in (comments_with_emb or []) if c["id"] in need_llm_ids
                ]
                llm_emb_available = llm_emb_comments and all(
                    c.get("embedding") for c in llm_emb_comments
                )

                if llm_emb_available and len(llm_emb_comments) >= 10:
                    cluster_result = cluster_reviews(
                        comment_ids=[c["id"] for c in llm_emb_comments],
                        embeddings=[c["embedding"] for c in llm_emb_comments],
                    )
                    llm_target_ids = set(cluster_result.llm_target_ids)
                    llm_comments = [c for c in llm_emb_comments if c["id"] in llm_target_ids]

                    logger.info(
                        "upload_job %s: clustering enabled, %d→%d LLM calls (saved %d)",
                        job_id,
                        len(llm_emb_comments),
                        len(llm_comments),
                        len(llm_emb_comments) - len(llm_comments),
                    )

                    v4_llm_results = deep_analyze_batch(
                        comments=[
                            {"content": c.get("content", ""), "rating": c.get("rating"), "title": c.get("title", "")}
                            for c in llm_comments
                        ],
                        sub_category=sub_category,
                        prompt_version=PROMPT_VERSION,
                        aspects_block=aspects_block,
                        allowed_aspects=allowed_aspects,
                    )

                    v4_results = propagate_cluster_results(
                        cluster_result, llm_comments, v4_llm_results, llm_emb_comments,
                    )

                    # 写入聚类元数据
                    id_to_cluster = {}
                    for label, member_ids in cluster_result.clusters.items():
                        rep_id = next(
                            (rid for rid in cluster_result.representatives if rid in member_ids),
                            member_ids[0],
                        )
                        for mid in member_ids:
                            id_to_cluster[mid] = (label, rep_id)
                    for nid in cluster_result.noise_ids:
                        id_to_cluster[nid] = (-1, nid)

                    for cid, (clabel, rep_id) in id_to_cluster.items():
                        try:
                            update_comment_cluster(user_id, cid, clabel, rep_id)
                        except Exception:
                            pass

                    for c, r in zip(llm_emb_comments, v4_results):
                        id_to_v4[c["id"]] = r

                    # 没 embedding 但需要 LLM 的评论
                    emb_id_set = {c["id"] for c in llm_emb_comments}
                    non_emb_comments = [c for c in need_llm if c["id"] not in emb_id_set]
                    if non_emb_comments:
                        non_emb_results = deep_analyze_batch(
                            comments=[
                                {"content": c.get("content", ""), "rating": c.get("rating"), "title": c.get("title", "")}
                                for c in non_emb_comments
                            ],
                            sub_category=sub_category,
                            prompt_version=PROMPT_VERSION,
                            aspects_block=aspects_block,
                            allowed_aspects=allowed_aspects,
                        )
                        for c, r in zip(non_emb_comments, non_emb_results):
                            id_to_v4[c["id"]] = r
                else:
                    # Fallback: 全量走 LLM
                    logger.info(
                        "upload_job %s: clustering skipped for LLM batch (emb=%s, n=%d), full LLM",
                        job_id, bool(llm_emb_available), len(need_llm),
                    )
                    llm_results = deep_analyze_batch(
                        comments=[
                            {"content": c.get("content", ""), "rating": c.get("rating"), "title": c.get("title", "")}
                            for c in need_llm
                        ],
                        sub_category=sub_category,
                        prompt_version=PROMPT_VERSION,
                        aspects_block=aspects_block,
                        allowed_aspects=allowed_aspects,
                    )
                    for c, r in zip(need_llm, llm_results):
                        id_to_v4[c["id"]] = r

            # 按 unprocessed 顺序组装最终结果
            ordered_v4_results = [id_to_v4.get(c["id"], {"error": "no_result"}) for c in unprocessed]

            _progress_callback(len(unprocessed), len(unprocessed))
            results = []
            for comment, v4 in zip(unprocessed, ordered_v4_results):
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
                        "cache_hit_level": v4.get("cache_hit_level"),
                        "cache_source_id": v4.get("cache_source_id"),
                    })
                    continue
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
                    "cluster_propagated": v4.get("cluster_propagated", False),
                }
                legacy["analyzer_version"] = ANALYZER_VERSION
                legacy["cache_hit_level"] = v4.get("cache_hit_level")
                legacy["cache_source_id"] = v4.get("cache_source_id")
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

        # V4-T4 Step 5: 记录 LLM 用量日志
        usage_rows: list[dict] = []
        for comment, v4 in zip(unprocessed, ordered_v4_results):
            if v4.get("cache_hit_level"):
                usage_rows.append({
                    "user_id": user_id,
                    "session_id": session_id,
                    "comment_id": comment["id"],
                    "model_name": "cache",
                    "tokens_in": 0,
                    "tokens_out": 0,
                    "cost_yuan": 0,
                    "sub_category": sub_category,
                    "cache_hit": True,
                })
            elif v4.get("tokens_in") or v4.get("tokens_out"):
                usage_rows.append({
                    "user_id": user_id,
                    "session_id": session_id,
                    "comment_id": comment["id"],
                    "model_name": v4.get("model_used", "deepseek-chat"),
                    "tokens_in": v4.get("tokens_in", 0),
                    "tokens_out": v4.get("tokens_out", 0),
                    "cost_yuan": _estimate_cost_yuan(
                        v4.get("model_used", "deepseek-chat"),
                        v4.get("tokens_in", 0),
                        v4.get("tokens_out", 0),
                    ),
                    "sub_category": sub_category,
                    "cache_hit": False,
                })
        if usage_rows:
            try:
                log_llm_usage_batch(usage_rows)
            except Exception:
                logger.warning("upload_job %s: failed to log LLM usage", job_id, exc_info=True)

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
