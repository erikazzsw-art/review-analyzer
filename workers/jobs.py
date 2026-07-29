from __future__ import annotations

import asyncio
import logging
from collections import Counter
from datetime import datetime
from typing import Any

from backend_api.app.services.analysis_cache import (
    CacheResult,
    apply_cache,
    compute_batch_hash,
    compute_content_hash,
)
from backend_api.app.services.analytics import track_analysis_complete
from backend_api.app.services.calibration_injector import build_calibration_block
from backend_api.app.services.category_grouper import aspects_to_legacy_schema
from backend_api.app.services.clustering import (
    MIN_BATCH_FOR_CLUSTERING,
    cluster_reviews,
    propagate_cluster_results,
)
from backend_api.app.services.deep_analyzer import analyze_batch as deep_analyze_batch
from backend_api.app.services.job_trace import JobTrace
from backend_api.app.services.prompt_registry import DEFAULT_ANNOTATE_VERSION
from backend_api.app.services.review_pool import (
    pool_backfill_analysis,
    pool_has_enough,
    pool_lookup,
    pool_write,
)
from backend_api.app.services.specific_issue import (
    CUSTOMER_LABEL_OCCURRENCE_RULESET_VERSION,
    CUSTOMER_LABEL_OCCURRENCE_SCHEMA_VERSION,
    CUSTOMER_LABEL_SCHEMA_VERSION,
    HIGHLIGHT_RULESET_VERSION,
    ISSUE_RULESET_VERSION,
    SPECIFIC_ISSUE_SCHEMA_VERSION,
    enrich_aspects_json,
)
from backend_api.app.services.sub_category_inference import infer_sub_category_from_payload
from backend_api.app.services.taxonomy_coverage_monitor import (
    build_coverage_warning,
    compute_taxonomy_coverage,
    format_ops_alert,
)
from backend_api.app.services.taxonomy_loader import (
    render_aspects_block,
    resolve_aspects,
)
from review_analyzer.database import (
    _estimate_cost_yuan,
    add_comments_batch,
    create_session,
    find_session_by_batch_hash,
    get_analyzed_by_content_hash,
    get_analyzed_with_embeddings,
    get_session_embeddings,
    get_unprocessed_comments,
    get_upload_job,
    log_llm_usage_batch,
    update_comment_analysis,
    update_comment_analysis_batch,
    update_comment_cluster,
    update_comment_clusters_batch,
    update_session_stats,
    update_session_warnings,
    update_upload_job,
)
from review_analyzer.product_store import (
    create_product,
    get_product_by_parent_id,
    upsert_product_from_api,
    upsert_variant_from_api,
)
from review_analyzer.quota import InsufficientCreditsError, credit_consume, quota_consume
from review_analyzer.rag import embed_session_comments

from .queue import get_queue

# V4-T3 集成：worker 现在使用 backend_api/app/services/deep_analyzer (annotate v2.1, 92.1% 准确率)
# 旧 review_analyzer.analyzer.analyze_batch 仍保留供 Streamlit 直接调用，不在 worker 通道使用
PROMPT_VERSION = DEFAULT_ANNOTATE_VERSION  # "v2.1"
ANALYZER_VERSION = "v4_deep"
COMMENT_ANALYSIS_WRITE_BATCH_SIZE = 50

logger = logging.getLogger(__name__)


def _trace_callback_for(trace: JobTrace):
    def _record(kind: str, name: str, details: dict[str, Any]) -> None:
        if kind == "decision":
            trace.record_decision(name, details)
        elif kind == "warning":
            trace.record_warning(name, details)
        else:
            trace.record_event(name, details)

    return _record


def _cache_observability_summary(
    cache_result: CacheResult,
    cache_input: list[dict[str, Any]],
    existing_analyses: dict[str, dict[str, Any]],
    reference_embeddings: list[list[float]] | None,
    reference_ids: list[int] | None,
    reference_results: dict[int, dict] | None,
) -> dict[str, Any]:
    source_counts: Counter[str] = Counter()
    level_counts: Counter[str] = Counter()
    miss_reasons: Counter[str] = Counter()
    miss_examples: dict[str, list[int]] = {}
    input_by_id = {int(c["id"]): c for c in cache_input if c.get("id") is not None}
    semantic_cache_available = bool(reference_embeddings and reference_ids and reference_results)

    for hit in cache_result.hits.values():
        level_counts[hit.level] += 1
        if hit.level == "L1":
            raw_source = str(hit.result.get("cache_hit_source") or "").lower()
            if raw_source == "user":
                source = "user_history"
            elif raw_source == "global":
                source = "global_review_pool"
            else:
                source = "exact_hash"
        elif hit.level == "L2":
            source = "short_text_rating_rule"
        elif hit.level == "L3":
            source = "semantic_similar"
        else:
            source = f"unknown_{hit.level}"
        source_counts[source] += 1

    for cid in cache_result.misses:
        comment = input_by_id.get(int(cid), {})
        if not comment.get("embedding"):
            reason = "embedding_missing"
        elif not semantic_cache_available:
            reason = "semantic_reference_unavailable"
        else:
            reason = "semantic_similarity_below_threshold"
        miss_reasons[reason] += 1
        examples = miss_examples.setdefault(reason, [])
        if len(examples) < 5:
            examples.append(int(cid))

    return {
        "checked_count": len(cache_input),
        "hit_count": cache_result.hit_count,
        "miss_count": cache_result.miss_count,
        "hit_levels": dict(level_counts),
        "hit_sources": dict(source_counts),
        "miss_reasons": dict(miss_reasons),
        "miss_examples": miss_examples,
        "l1_existing_analysis_count": len(existing_analyses),
        "global_review_pool_enabled": True,
        "semantic_cache_available": semantic_cache_available,
        "semantic_reference_count": len(reference_ids or []),
    }


def _llm_observability_summary(
    results: list[dict[str, Any]],
    *,
    prompt_version: str,
    locale: str,
    sub_category: str,
) -> dict[str, Any]:
    route_counts: Counter[str] = Counter()
    model_counts: Counter[str] = Counter()
    retry_distribution: Counter[str] = Counter()
    quality_counts: Counter[str] = Counter()
    direct_llm_count = 0

    for result in results:
        if result.get("cache_hit_level") or result.get("cluster_propagated"):
            continue
        if result.get("model_used") or result.get("error"):
            direct_llm_count += 1
        if result.get("model_used"):
            model_counts[str(result["model_used"])] += 1
        retry_count = result.get("retry_count")
        if retry_count is not None:
            try:
                retry_distribution[str(int(retry_count))] += 1
            except (TypeError, ValueError):
                retry_distribution[str(retry_count)] += 1
        quality_counts["json_decode"] += int(result.get("json_decode_count") or 0)
        quality_counts["schema_invalid"] += int(result.get("schema_invalid_count") or 0)
        quality_counts["exception"] += int(result.get("exception_count") or 0)
        if result.get("final_success") is True:
            quality_counts["final_success"] += 1
        elif result.get("error"):
            quality_counts["final_failure"] += 1
        route_counter = result.get("llm_route_counts")
        if isinstance(route_counter, dict):
            for name, count in route_counter.items():
                try:
                    route_counts[str(name)] += int(count)
                except (TypeError, ValueError):
                    route_counts[str(name)] += 1

    return {
        "prompt_version": prompt_version,
        "locale": locale,
        "sub_category": sub_category,
        "direct_llm_count": direct_llm_count,
        "model_counts": dict(model_counts),
        "route_events": dict(route_counts),
        "quality": dict(quality_counts),
        "retry_distribution": dict(retry_distribution),
        "retry_count_total": sum(
            int(bucket) * count
            for bucket, count in retry_distribution.items()
            if bucket.isdigit()
        ),
    }


def _fallback_aspects_json_for_error(
    v4_result: dict[str, Any],
    *,
    sub_category: str,
    prompt_version: str,
) -> dict[str, Any]:
    """Build a structured, non-cacheable fallback for exhausted LLM analysis."""
    return {
        "sentiment": "unrecognizable",
        "aspects": [],
        "pain_points": [],
        "highlights": [],
        "evidence_level_overall": "low",
        "prompt_version": v4_result.get("prompt_version") or prompt_version,
        "cluster_propagated": False,
        "analysis_error": str(v4_result.get("error") or "analysis_failed")[:200],
        "analysis_fallback": True,
        "sub_category": sub_category,
        "specific_issue_schema_version": SPECIFIC_ISSUE_SCHEMA_VERSION,
        "customer_label_schema_version": CUSTOMER_LABEL_SCHEMA_VERSION,
        "customer_label_occurrence_schema_version": CUSTOMER_LABEL_OCCURRENCE_SCHEMA_VERSION,
        "customer_label_occurrence_ruleset_version": CUSTOMER_LABEL_OCCURRENCE_RULESET_VERSION,
        "customer_label_occurrences": [],
        "issue_ruleset_version": ISSUE_RULESET_VERSION,
        "highlight_ruleset_version": HIGHLIGHT_RULESET_VERSION,
    }


def _resolve_job_taxonomy(
    payload: dict[str, Any],
    product_id: str,
) -> tuple[str, list[dict[str, str]], bool]:
    """Resolve taxonomy for an upload job, with narrow product-text inference."""
    raw_sub_category = str(payload.get("category") or "").strip()
    if raw_sub_category:
        aspects, hit = resolve_aspects(raw_sub_category)
        if hit:
            return raw_sub_category, aspects, True
    else:
        aspects, hit = [], False

    inferred = infer_sub_category_from_payload(payload, product_id)
    if inferred and inferred != raw_sub_category:
        inferred_aspects, inferred_hit = resolve_aspects(inferred)
        if inferred_hit:
            logger.info(
                "upload taxonomy inferred: raw=%r inferred=%r product_id=%r",
                raw_sub_category or None,
                inferred,
                product_id,
            )
            return inferred, inferred_aspects, True

    if raw_sub_category:
        return raw_sub_category, aspects, False

    fallback = "家具家居"
    fallback_aspects, fallback_hit = resolve_aspects(fallback)
    return fallback, fallback_aspects, fallback_hit


def _build_comments(
    payload_comments: list[dict[str, Any]],
    product_id: str,
    version: str,
    category: str | None = None,
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
                "source_variant_asin": comment.get("source_variant_asin"),
                "source_channel": comment.get("source_channel"),
                "content_hash": compute_content_hash(content, rating, category),
            }
        )
    return comments


def _comments_payload_by_hash(
    payload_comments: list[dict[str, Any]],
    category: str | None = None,
) -> dict[str, dict[str, Any]]:
    by_hash: dict[str, dict[str, Any]] = {}
    for comment in payload_comments:
        content = str(comment.get("content") or "")
        rating = comment.get("rating")
        content_hash = compute_content_hash(content, rating, category)
        by_hash.setdefault(content_hash, comment)
    return by_hash


def _merge_pool_source_comments(
    db_comments: list[dict[str, Any]],
    payload_comments: list[dict[str, Any]],
    category: str | None = None,
) -> list[dict[str, Any]]:
    payload_by_hash = _comments_payload_by_hash(payload_comments, category)
    merged: list[dict[str, Any]] = []
    for comment in db_comments:
        content_hash = str(comment.get("content_hash") or "")
        payload_comment = payload_by_hash.get(content_hash, {})
        item = {**comment, **payload_comment}
        if content_hash:
            item["content_hash"] = content_hash
        merged.append(item)
    return merged


def process_upload_job(user_id: int, job_id: int) -> None:
    trace = JobTrace(job_id=job_id, user_id=user_id)
    trace_callback = _trace_callback_for(trace)
    try:
        trace.begin_stage("init")
        job = get_upload_job(user_id, job_id)
        if not job:
            trace.record_warning("job_missing", job_id=job_id, user_id=user_id)
            trace.finalize(error="job_not_found")
            return

        payload = job.get("payload_json") or {}
        comments_payload = payload.get("comments") or []
        product_id = str(job.get("product_id") or payload.get("product_id") or "")
        version = str(job.get("version") or payload.get("version") or "V1")
        workflow_purpose = job.get("workflow_purpose") or payload.get("workflow_purpose")
        product_ref_id = job.get("product_ref_id") or payload.get("product_ref_id")
        variant_ref_id = job.get("variant_ref_id") or payload.get("variant_ref_id")
        # V6-locale: 从 payload 取 locale，无则默认 en（海外优先）
        locale = str(payload.get("locale") or "en")
        sub_category, aspects, taxonomy_hit = _resolve_job_taxonomy(payload, product_id)
        category_for_storage = (
            sub_category
            if taxonomy_hit
            else (str(payload.get("category") or "").strip() or None)
        )
        trace.record_decision(
            "job_context",
            product_id=product_id,
            version=version,
            locale=locale,
            payload_review_count=len(comments_payload),
            workflow_purpose=workflow_purpose,
        )
        trace.record_decision(
            "taxonomy",
            sub_category=sub_category,
            taxonomy_hit=taxonomy_hit,
            aspect_count=len(aspects),
            storage_category=category_for_storage,
        )

        update_upload_job(user_id, job_id, {"status": "processing"})

        # 断点续跑：如果 job 已有 session_id，跳过创建阶段直接续跑未处理评论
        existing_session_id = job.get("session_id")
        if existing_session_id:
            session_id = int(existing_session_id)
            logger.info("upload_job %s: resuming session %d", job_id, session_id)
        else:
            batch_hash = payload.get("batch_hash")
            if not batch_hash and comments_payload:
                batch_hash = compute_batch_hash(comments_payload, sub_category)

            # batch_hash 重复时复用已有 session（同一用户+产品+相同评论集）
            if batch_hash:
                dup_session = find_session_by_batch_hash(user_id, product_id, batch_hash)
                if dup_session:
                    session_id = int(dup_session["id"])
                    logger.info("upload_job %s: batch_hash duplicate, reusing session %d", job_id, session_id)
                    trace.record_decision(
                        "batch_dedupe",
                        duplicate=True,
                        reused_session_id=session_id,
                        batch_hash_present=True,
                    )
                    trace.end_stage(meta={"duplicate_session_id": session_id})
                    trace.finalize()
                    update_upload_job(user_id, job_id, {
                        "status": "done",
                        "session_id": session_id,
                        "total_rows": dup_session.get("total_reviews") or len(comments_payload),
                        "positive_count": dup_session.get("positive_count") or 0,
                        "negative_count": dup_session.get("negative_count") or 0,
                        "trace_json": trace.to_dict(),
                    })
                    return

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
                            "category": category_for_storage,
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
                    "category": category_for_storage,
                    "prompt_version": PROMPT_VERSION,
                    "version_notes": payload.get("version_notes"),
                    "workflow_purpose": workflow_purpose,
                    "product_ref_id": product_ref_id,
                    "variant_ref_id": variant_ref_id,
                    "batch_hash": batch_hash,
                },
            )

            comments_to_insert = _build_comments(
                comments_payload, product_id, version, sub_category
            )
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
        cluster_count = 0
        trace.end_stage(meta={"review_count": len(unprocessed)})
        trace.record_decision(
            "analysis_scope",
            session_id=session_id,
            unprocessed_count=len(unprocessed),
            resume=bool(existing_session_id),
        )

        if unprocessed:
            trace.begin_stage("embed")
            try:
                embed_session_comments(user_id, session_id)
            except Exception:
                logger.exception(
                    "embed_session_comments failed for user_id=%s session_id=%s",
                    user_id, session_id,
                )
            trace.end_stage(meta={"count": len(unprocessed)})

            def _progress_callback(current: int, total: int) -> None:
                try:
                    update_upload_job(
                        user_id,
                        job_id,
                        {
                            "processed_rows": current,
                        },
                    )
                except Exception:
                    logger.debug("progress_callback: DB write failed (non-fatal), current=%d", current)

            aspects_block = render_aspects_block(aspects)
            calibration_block = build_calibration_block(sub_category)
            if calibration_block:
                aspects_block += "\n\n" + calibration_block
            allowed_aspects = [a["key"] for a in aspects]
            trace.record_decision(
                "prompt_config",
                prompt_version=PROMPT_VERSION,
                locale=locale,
                sub_category=sub_category,
                allowed_aspects_count=len(allowed_aspects),
                calibration_enabled=bool(calibration_block),
            )

            # --- V4-T4 Step 3: 多级缓存 ---
            trace.begin_stage("cache")
            # L1: 收集当前 batch 的 content_hash，查询已有分析结果
            # migration 043: 除用户自己历史，同时查全局 review_pool 支持跨用户复用
            content_hashes = [
                c.get("content_hash")
                or compute_content_hash(c.get("content", ""), c.get("rating"), sub_category)
                for c in unprocessed
            ]
            existing_analyses = get_analyzed_by_content_hash(
                user_id,
                content_hashes,
                include_global=True,
                analyzer_version=ANALYZER_VERSION,
            )

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
                    "content_hash": c.get("content_hash"),
                    "category": sub_category,
                    "embedding": emb_by_id.get(c["id"]),
                })

            cache_result: CacheResult = apply_cache(
                comments=cache_input,
                existing_analyses=existing_analyses,
                reference_embeddings=reference_embeddings,
                reference_ids=reference_ids,
                reference_results=reference_results,
            )
            cache_summary = _cache_observability_summary(
                cache_result,
                cache_input,
                existing_analyses,
                reference_embeddings,
                reference_ids,
                reference_results,
            )
            trace.record_decision("cache_lookup", cache_summary)

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
                # migration 043: 记录命中来源（user=本人历史 / global=跨用户 pool）
                if isinstance(cached, dict) and cached.get("cache_hit_source"):
                    id_to_v4[cid]["cache_hit_source"] = cached["cache_hit_source"]

            logger.info(
                "upload_job %s: cache hit=%d miss=%d (stats=%s)",
                job_id, cache_result.hit_count, cache_result.miss_count, cache_result.stats(),
            )
            trace.end_stage(meta={
                "hit": cache_result.hit_count,
                "miss": cache_result.miss_count,
                "stats": cache_result.stats(),
                "hit_sources": cache_summary.get("hit_sources"),
                "miss_reasons": cache_summary.get("miss_reasons"),
            })

            # --- 对需要 LLM 的评论走聚类+LLM 管道 ---
            trace.begin_stage("llm_analysis")
            if need_llm:
                need_llm_ids = {c["id"] for c in need_llm}
                llm_emb_comments = [
                    c for c in (comments_with_emb or []) if c["id"] in need_llm_ids
                ]
                llm_emb_available = llm_emb_comments and all(
                    c.get("embedding") for c in llm_emb_comments
                )
                cached_count = len(cache_result.hits)
                llm_done_count = 0

                def _make_llm_progress(offset: int):
                    def _llm_progress(current: int, total: int) -> None:
                        nonlocal llm_done_count
                        llm_done_count = max(llm_done_count, offset + current)
                        _progress_callback(
                            min(len(unprocessed), cached_count + llm_done_count),
                            len(unprocessed),
                        )

                    return _llm_progress

                if llm_emb_available and len(llm_emb_comments) >= 10:
                    llm_progress = _make_llm_progress(0)
                    cluster_result = cluster_reviews(
                        comment_ids=[c["id"] for c in llm_emb_comments],
                        embeddings=[c["embedding"] for c in llm_emb_comments],
                    )
                    cluster_count = len(cluster_result.clusters)
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
                            {
                                "id": c.get("id"),
                                "content_hash": c.get("content_hash"),
                                "content": c.get("content", ""),
                                "rating": c.get("rating"),
                                "title": c.get("title", ""),
                            }
                            for c in llm_comments
                        ],
                        sub_category=sub_category,
                        prompt_version=PROMPT_VERSION,
                        aspects_block=aspects_block,
                        allowed_aspects=allowed_aspects,
                        progress_callback=llm_progress,
                        user_id=user_id,
                        locale=locale,
                        trace_callback=trace_callback,
                    )

                    v4_results = propagate_cluster_results(
                        cluster_result, llm_comments, v4_llm_results, llm_emb_comments,
                    )
                    propagated_count = sum(1 for r in v4_results if r.get("cluster_propagated"))
                    cluster_needs_llm_count = sum(1 for r in v4_results if r.get("needs_llm"))
                    trace.record_decision(
                        "clustering",
                        enabled=True,
                        skipped_reason=None,
                        input_count=len(llm_emb_comments),
                        cluster_count=cluster_count,
                        representatives_count=len(cluster_result.representatives),
                        noise_count=len(cluster_result.noise_ids),
                        llm_target_count=len(llm_comments),
                        saved_llm_calls=max(0, len(llm_emb_comments) - len(llm_comments)),
                        propagated_count=propagated_count,
                        needs_llm_count=cluster_needs_llm_count,
                    )
                    trace.record_event(
                        "cluster_propagation",
                        propagated_count=propagated_count,
                        needs_llm_count=cluster_needs_llm_count,
                        representative_ids=cluster_result.representatives[:10],
                        noise_count=len(cluster_result.noise_ids),
                    )
                    if cluster_needs_llm_count:
                        trace.record_warning(
                            "cluster_needs_llm",
                            needs_llm_count=cluster_needs_llm_count,
                            reason="low_cluster_similarity",
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

                    cluster_updates = [
                        {
                            "comment_id": cid,
                            "cluster_id": clabel,
                            "cluster_representative_id": rep_id,
                        }
                        for cid, (clabel, rep_id) in id_to_cluster.items()
                    ]
                    try:
                        update_comment_clusters_batch(user_id, cluster_updates)
                    except Exception:
                        logger.exception(
                            "update_comment_clusters_batch failed for user_id=%s count=%d",
                            user_id,
                            len(cluster_updates),
                        )
                        for row in cluster_updates:
                            try:
                                update_comment_cluster(
                                    user_id,
                                    int(row["comment_id"]),
                                    int(row["cluster_id"]),
                                    int(row["cluster_representative_id"]),
                                )
                            except Exception:
                                logger.exception(
                                    "update_comment_cluster failed for comment_id=%s user_id=%s",
                                    row["comment_id"],
                                    user_id,
                                )

                    for c, r in zip(llm_emb_comments, v4_results):
                        id_to_v4[c["id"]] = r

                    # 没 embedding 但需要 LLM 的评论
                    emb_id_set = {c["id"] for c in llm_emb_comments}
                    non_emb_comments = [c for c in need_llm if c["id"] not in emb_id_set]
                    if non_emb_comments:
                        trace.record_event(
                            "llm_non_embedding_batch",
                            count=len(non_emb_comments),
                            reason="embedding_missing_after_clustering",
                        )
                        llm_progress = _make_llm_progress(len(v4_llm_results))
                        non_emb_results = deep_analyze_batch(
                            comments=[
                                {
                                    "id": c.get("id"),
                                    "content_hash": c.get("content_hash"),
                                    "content": c.get("content", ""),
                                    "rating": c.get("rating"),
                                    "title": c.get("title", ""),
                                }
                                for c in non_emb_comments
                            ],
                            sub_category=sub_category,
                            prompt_version=PROMPT_VERSION,
                            aspects_block=aspects_block,
                            allowed_aspects=allowed_aspects,
                            progress_callback=llm_progress,
                            user_id=user_id,
                            locale=locale,
                            trace_callback=trace_callback,
                        )
                        for c, r in zip(non_emb_comments, non_emb_results):
                            id_to_v4[c["id"]] = r
                else:
                    # Fallback: 全量走 LLM
                    if not llm_emb_available:
                        cluster_skip_reason = "embeddings_unavailable"
                    elif len(llm_emb_comments) < MIN_BATCH_FOR_CLUSTERING:
                        cluster_skip_reason = "batch_too_small"
                    else:
                        cluster_skip_reason = "unknown"
                    trace.record_decision(
                        "clustering",
                        enabled=False,
                        skipped_reason=cluster_skip_reason,
                        input_count=len(need_llm),
                        embedding_candidate_count=len(llm_emb_comments),
                        embeddings_available=bool(llm_emb_available),
                        min_batch_for_clustering=MIN_BATCH_FOR_CLUSTERING,
                        cluster_count=0,
                        representatives_count=0,
                        needs_llm_count=len(need_llm),
                    )
                    logger.info(
                        "upload_job %s: clustering skipped for LLM batch (emb=%s, n=%d), full LLM",
                        job_id, bool(llm_emb_available), len(need_llm),
                    )
                    llm_results = deep_analyze_batch(
                        comments=[
                            {
                                "id": c.get("id"),
                                "content_hash": c.get("content_hash"),
                                "content": c.get("content", ""),
                                "rating": c.get("rating"),
                                "title": c.get("title", ""),
                            }
                            for c in need_llm
                        ],
                        sub_category=sub_category,
                        prompt_version=PROMPT_VERSION,
                        aspects_block=aspects_block,
                        allowed_aspects=allowed_aspects,
                        progress_callback=_make_llm_progress(0),
                        user_id=user_id,
                        locale=locale,
                        trace_callback=trace_callback,
                    )
                    for c, r in zip(need_llm, llm_results):
                        id_to_v4[c["id"]] = r
            else:
                trace.record_decision(
                    "clustering",
                    enabled=False,
                    skipped_reason="no_cache_misses",
                    input_count=0,
                    cluster_count=0,
                    representatives_count=0,
                    needs_llm_count=0,
                )

            # 按 unprocessed 顺序组装最终结果
            ordered_v4_results = [id_to_v4.get(c["id"], {"error": "no_result"}) for c in unprocessed]
            llm_summary = _llm_observability_summary(
                ordered_v4_results,
                prompt_version=PROMPT_VERSION,
                locale=locale,
                sub_category=sub_category,
            )
            cluster_propagated_count = sum(1 for v in ordered_v4_results if v.get("cluster_propagated"))
            trace.record_decision("llm_prompt_quality", llm_summary)
            trace.record_decision(
                "result_sources",
                cache_hit_count=cache_result.hit_count,
                cache_hit_sources=cache_summary.get("hit_sources"),
                cache_miss_count=cache_result.miss_count,
                cluster_propagated_count=cluster_propagated_count,
                direct_llm_count=llm_summary.get("direct_llm_count", 0),
                no_result_count=sum(1 for v in ordered_v4_results if v.get("error") == "no_result"),
            )
            quality = llm_summary.get("quality", {})
            if any(int(quality.get(key) or 0) for key in ("json_decode", "schema_invalid", "exception", "final_failure")):
                trace.record_warning(
                    "llm_quality",
                    json_decode=quality.get("json_decode", 0),
                    schema_invalid=quality.get("schema_invalid", 0),
                    exception=quality.get("exception", 0),
                    final_failure=quality.get("final_failure", 0),
                )
            trace.end_stage(meta={
                "llm_calls": llm_summary.get("direct_llm_count", 0),
                "need_llm": len(need_llm) if need_llm else 0,
                "model_counts": llm_summary.get("model_counts"),
                "route_events": llm_summary.get("route_events"),
                "quality": quality,
            })

            trace.begin_stage("post_process")

            _progress_callback(len(unprocessed), len(unprocessed))
        else:
            ordered_v4_results = []
            trace.record_decision(
                "result_sources",
                cache_hit_count=0,
                cache_miss_count=0,
                cluster_propagated_count=0,
                direct_llm_count=0,
                no_result_count=0,
                skipped_reason="no_unprocessed_comments",
            )

        # 小批量增量写入：降低连接/commit 压力，同时避免回到全量末尾才保存。
        def _flush_analysis_updates(updates: list[tuple[int, dict]]) -> None:
            if not updates:
                return
            try:
                update_comment_analysis_batch(user_id, updates)
            except Exception:
                logger.exception(
                    "update_comment_analysis_batch failed for user_id=%s count=%d; falling back to per-comment writes",
                    user_id,
                    len(updates),
                )
                for cid, analysis in updates:
                    try:
                        update_comment_analysis(user_id, cid, analysis)
                    except Exception:
                        logger.exception(
                            "update_comment_analysis failed for comment_id=%s user_id=%s",
                            cid,
                            user_id,
                        )

        positive_count = 0
        negative_count = 0
        results = []
        analysis_updates: list[tuple[int, dict]] = []
        for comment, v4 in zip(unprocessed, ordered_v4_results):
            if v4.get("error"):
                result = {
                    "sentiment": "unrecognizable",
                    "content_sentiment": "unrecognizable",
                    "category": "invalid_garbage",
                    "priority": "无",
                    "reason": "",
                    "improvement": "",
                    "issue_tag": "",
                    "highlight_tag": "",
                    "aspects_json": _fallback_aspects_json_for_error(
                        v4,
                        sub_category=sub_category,
                        prompt_version=PROMPT_VERSION,
                    ),
                    "analyzer_version": ANALYZER_VERSION,
                    "cache_hit_level": v4.get("cache_hit_level"),
                    "cache_source_id": v4.get("cache_source_id"),
                    "cache_hit_source": v4.get("cache_hit_source"),
                }
            else:
                result = aspects_to_legacy_schema(
                    aspects=v4.get("aspects", []),
                    sentiment=v4.get("sentiment", "neutral"),
                    content=comment.get("content", ""),
                    pain_points=v4.get("pain_points", []),
                    highlights=v4.get("highlights", []),
                    locale=locale,
                )
                result["aspects_json"] = {
                    "sentiment": v4.get("sentiment"),
                    "aspects": v4.get("aspects", []),
                    "pain_points": v4.get("pain_points", []),
                    "highlights": v4.get("highlights", []),
                    "evidence_level_overall": v4.get("evidence_level_overall"),
                    "prompt_version": v4.get("prompt_version", PROMPT_VERSION),
                    "cluster_propagated": v4.get("cluster_propagated", False),
                }
                result["aspects_json"] = enrich_aspects_json(
                    result["aspects_json"],
                    sub_category=sub_category,
                    content=comment.get("content", ""),
                    locale=locale,
                    comment_id=comment.get("id"),
                )
                result["analyzer_version"] = ANALYZER_VERSION
                result["cache_hit_level"] = v4.get("cache_hit_level")
                result["cache_source_id"] = v4.get("cache_source_id")
                result["cache_hit_source"] = v4.get("cache_hit_source")

            rating = comment.get("rating")
            if rating is not None:
                try:
                    rating_val = int(float(rating))
                    result["sentiment"] = "negative" if rating_val <= 3 else "positive"
                except (TypeError, ValueError):
                    pass

            analysis_updates.append((int(comment["id"]), result))
            if len(analysis_updates) >= COMMENT_ANALYSIS_WRITE_BATCH_SIZE:
                _flush_analysis_updates(analysis_updates)
                analysis_updates = []

            results.append(result)

            if result.get("sentiment") == "positive":
                positive_count += 1
            elif result.get("sentiment") == "negative":
                negative_count += 1

        _flush_analysis_updates(analysis_updates)
        update_session_stats(user_id, session_id, len(unprocessed), positive_count, negative_count)

        # M6: 扣减 credit（review_analyze = 1 credit/条）
        try:
            credit_consume(user_id, len(unprocessed), "review_analyze", str(job_id))
        except InsufficientCreditsError as e:
            logger.error("job %s: insufficient credits, needed=%d balance=%d", job_id, e.needed, e.balance)
            raise

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

        # V4.5-T12 C1: 追踪分析完成事件
        llm_call_count = sum(1 for r in usage_rows if not r.get("cache_hit"))
        total_cost = sum(float(r.get("cost_yuan") or 0) for r in usage_rows)
        total_latency = sum(
            v4.get("latency_ms", 0) for v4 in ordered_v4_results if v4.get("latency_ms")
        )
        try:
            track_analysis_complete(
                user_id,
                session_id=session_id,
                review_count=len(unprocessed),
                cluster_count=cluster_count,
                llm_calls=llm_call_count,
                total_latency_ms=total_latency,
                total_cost_yuan=total_cost,
            )
        except Exception:
            logger.warning("upload_job %s: track_analysis_complete failed (non-fatal)", job_id, exc_info=True)

        trace.end_stage()
        trace.review_count = len(unprocessed)
        trace.llm_calls = llm_call_count
        trace.cache_hits = len(usage_rows) - llm_call_count
        trace.cluster_count = cluster_count
        trace.total_cost_yuan = total_cost
        trace.finalize()

        # V4-T1.6 Step 3: Taxonomy 覆盖率监控
        taxonomy_warnings: list[dict] = []
        try:
            coverage = compute_taxonomy_coverage(ordered_v4_results, sub_category=sub_category)
            warning = build_coverage_warning(coverage)
            if warning:
                taxonomy_warnings.append(warning)
                trace.record_warning("taxonomy_coverage", warning)
                logger.warning(
                    "upload_job %s: taxonomy coverage low — other ratio %.1f%% for '%s'",
                    job_id, coverage["other_ratio"] * 100, sub_category,
                )
                try:
                    import json as _json

                    from review_analyzer.database import get_setting
                    from review_analyzer.notifier import send_text_notification

                    raw_settings = get_setting(user_id, "push_settings")
                    if raw_settings:
                        push_cfg = _json.loads(raw_settings)
                        webhook_url = push_cfg.get("webhook_url", "")
                        secret = push_cfg.get("webhook_secret") or push_cfg.get("secret", "")
                        platform = push_cfg.get("webhook_platform") or "feishu"
                        if webhook_url:
                            alert_text = format_ops_alert(warning, session_id, user_id)
                            send_text_notification(platform, webhook_url, alert_text, secret)
                except Exception:
                    logger.warning("upload_job %s: taxonomy alert failed (non-fatal)", job_id, exc_info=True)
        except Exception:
            logger.warning("upload_job %s: taxonomy coverage check failed (non-fatal)", job_id, exc_info=True)

        if taxonomy_warnings:
            try:
                update_session_warnings(user_id, session_id, taxonomy_warnings)
            except Exception:
                logger.warning("upload_job %s: update_session_warnings failed (non-fatal)", job_id, exc_info=True)

        trace_dict = trace.to_dict()

        update_upload_job(
            user_id,
            job_id,
            {
                "status": "done",
                "processed_rows": len(unprocessed),
                "positive_count": positive_count,
                "negative_count": negative_count,
                "trace_json": trace_dict,
            },
        )

        # ── 分析完成后回填到评论池 ──
        # migration 043: 拆除 source_channel=="api" 门禁，CSV 上传也回填 pool
        # 供跨用户复用，前提是 product_id 非空（避免污染池）
        try:
            _backfill_source = str(payload.get("platform") or "").lower()
            _backfill_platform = "amazon"
            for _p in ("aliexpress", "shopee", "ebay", "walmart"):
                if _p in _backfill_source:
                    _backfill_platform = _p
                    break
            _backfill_key = product_id
            _backfill_market = str(payload.get("marketplace") or "us")
            # 只要 product_id 非空即回填（CSV / API 都参与）
            if _backfill_key:
                pool_source_comments = _merge_pool_source_comments(
                    unprocessed,
                    comments_payload,
                    sub_category,
                )
                # 首先写入 review_pool（若 CSV 是新数据，pool_write 会 upsert）
                pool_write(
                    _backfill_platform, _backfill_key, _backfill_market,
                    pool_source_comments,
                    scraper_source=payload.get("source_channel") or "csv",
                )
                # 合并 content_hash（来自 unprocessed）和分析结果（来自 results）
                # pool_backfill_analysis 需要 content_hash + sentiment + aspects_json 才能回填
                backfill_data = []
                for comment, result in zip(unprocessed, results):
                    aspects_json = result.get("aspects_json")
                    if isinstance(aspects_json, dict) and aspects_json.get("analysis_error"):
                        continue
                    backfill_data.append({
                        "content_hash": comment.get("content_hash"),
                        "sentiment": result.get("sentiment"),
                        "aspects_json": aspects_json,
                    })
                pool_backfill_analysis(
                    _backfill_platform, _backfill_key, _backfill_market,
                    backfill_data, analyzer_version=ANALYZER_VERSION,
                )
        except Exception:
            logger.warning("upload_job %s: pool_backfill_analysis failed (non-fatal)", job_id, exc_info=True)

        # V5-T3 Step 9: 即时推送升级——写入快照 + 升级判定
        try:
            _post_analysis_smart_push(
                user_id=user_id,
                session_id=session_id,
                product_ref_id=product_ref_id,
                product_id=product_id,
                comments=unprocessed,
                results=results,
                positive_count=positive_count,
                negative_count=negative_count,
            )
        except Exception:
            logger.warning("upload_job %s: smart push failed (non-fatal)", job_id, exc_info=True)
    except Exception as exc:
        trace.finalize(error=str(exc)[:500])
        try:
            update_upload_job(
                user_id,
                job_id,
                {
                    "status": "failed",
                    "error_message": str(exc)[:500],
                    "trace_json": trace.to_dict(),
                },
            )
        except Exception:
            logger.error("upload_job %s: failed to mark job as failed (DB unavailable)", job_id)
        raise


def _post_analysis_smart_push(
    user_id: int,
    session_id: int,
    product_ref_id: int | None,
    product_id: str,
    comments: list[dict],
    results: list[dict],
    positive_count: int,
    negative_count: int,
) -> None:
    """分析完成后：写入推送快照 + 升级判定 + 触发富文本推送"""
    import json
    from collections import Counter

    from review_analyzer.database import get_setting
    from review_analyzer.department_router import get_dept_label, route_issues_by_department
    from review_analyzer.escalation import (
        EscalationConfig,
        check_escalations,
        update_escalation_states,
    )
    from review_analyzer.notifier import send_rich_push
    from review_analyzer.push_snapshot_store import create_push_snapshot

    raw_settings = get_setting(user_id, "push_settings")
    if not raw_settings:
        return
    try:
        settings = json.loads(raw_settings)
    except json.JSONDecodeError:
        return

    webhook_url = settings.get("webhook_url", "")
    if not webhook_url:
        return

    platform = settings.get("webhook_platform") or "feishu"

    total = len(comments)
    if total == 0:
        return

    neg_count = negative_count
    neg_rate = neg_count / total * 100

    tag_counter: Counter = Counter()
    for r in results:
        raw_tag = r.get("issue_tag", "")
        if raw_tag and r.get("sentiment") == "negative":
            for tag in raw_tag.split(","):
                tag = tag.strip()
                if tag:
                    tag_counter[tag] += 1

    neg_pool = neg_count or 1
    top_issues = [
        {"tag": tag, "count": count, "pct": count / neg_pool * 100, "rank": rank}
        for rank, (tag, count) in enumerate(tag_counter.most_common(10), 1)
    ]

    hl_counter: Counter = Counter()
    for r in results:
        raw_tag = r.get("highlight_tag", "")
        if raw_tag and r.get("sentiment") == "positive":
            for tag in raw_tag.split(","):
                tag = tag.strip()
                if tag:
                    hl_counter[tag] += 1

    pos_pool = positive_count or 1
    top_highlights = [
        {"tag": tag, "count": count, "pct": count / pos_pool * 100}
        for tag, count in hl_counter.most_common(5)
    ]

    snapshot_id = create_push_snapshot(user_id, {
        "product_id": product_ref_id,
        "snapshot_type": "batch",
        "top_issues": top_issues,
        "top_highlights": top_highlights,
        "summary_stats": {
            "total_reviews": total,
            "negative_count": neg_count,
            "neg_rate": neg_rate,
            "session_id": session_id,
        },
    })

    user_dept_mapping = settings.get("dept_mapping")
    if isinstance(user_dept_mapping, list):
        user_dept_mapping = {item["aspect"]: item["dept"] for item in user_dept_mapping if "aspect" in item and "dept" in item}

    update_escalation_states(
        user_id, product_ref_id, snapshot_id, top_issues, user_dept_mapping
    )

    escalation_config_raw = settings.get("escalation_rules", {})
    esc_config = EscalationConfig(
        consecutive_count=escalation_config_raw.get("consecutive_count", 3),
        top_n=escalation_config_raw.get("top_n", 3),
        pct_threshold=escalation_config_raw.get("pct_threshold", 10.0),
    )

    escalation_results = check_escalations(
        user_id, product_ref_id, top_issues, esc_config
    )

    escalation_actions: list[dict] = []
    if escalation_results:
        from backend_api.app.services.action_advisor import create_escalation_action
        from review_analyzer.aspect_taxonomy import get_aspect_label_zh
        from review_analyzer.push_snapshot_store import get_recent_snapshots, mark_escalated

        for esc in escalation_results:
            recent = get_recent_snapshots(user_id, product_ref_id, limit=esc_config.consecutive_count)
            pct_trend: list[float] = []
            for snap in reversed(recent):
                snap_issues = snap.get("top_issues") or []
                if isinstance(snap_issues, str):
                    snap_issues = json.loads(snap_issues)
                for si in snap_issues:
                    if si.get("tag") == esc.tag_name:
                        pct_trend.append(float(si.get("pct", 0)))
                        break
            pct_trend.append(esc.current_pct)

            sample_reviews = [
                c.get("content", "")[:200]
                for c, r in zip(comments, results)
                if esc.tag_name in (r.get("issue_tag") or "")
            ][:5]

            action_id = create_escalation_action(
                user_id=user_id,
                product_id=product_ref_id,
                tag_name=esc.tag_name,
                dept=esc.dept,
                current_pct=esc.current_pct,
                consecutive_count=esc.consecutive_count,
                pct_trend=pct_trend,
                product_name=product_id,
                sample_reviews=sample_reviews,
            )

            if action_id:
                mark_escalated(user_id, product_ref_id, esc.tag_name, action_id)
                escalation_actions.append({
                    "tag_name": esc.tag_name,
                    "tag_label": get_aspect_label_zh(esc.tag_name),
                    "dept": esc.dept,
                    "dept_label": get_dept_label(esc.dept),
                    "suggested_action": "已写入行动中心，并提醒对应责任方处理",
                    "expected_timeline": "",
                })

    dept_issues = route_issues_by_department(top_issues, user_dept_mapping)

    from review_analyzer.aspect_taxonomy import get_aspect_label_zh
    for dept_list in dept_issues.values():
        for issue in dept_list:
            issue["tag_label"] = get_aspect_label_zh(issue.get("tag", ""))
    for hl in top_highlights[:3]:
        hl["tag_label"] = get_aspect_label_zh(hl.get("tag", ""))

    dept_contacts = settings.get("dept_contacts", {})
    secret = settings.get("webhook_secret", "")

    from datetime import datetime
    period_label = datetime.now().strftime("%Y-%m-%d")

    # B6: 获取 TOP 问题复盘进度
    from review_analyzer.notifier import _get_action_progress
    top_tag_names = [i.get("tag", "") for i in top_issues[:5] if i.get("tag")]
    action_progress = _get_action_progress(user_id, product_id, top_tag_names)

    send_rich_push(
        webhook_url=webhook_url,
        product_name=product_id,
        period_label=period_label,
        dept_issues=dept_issues,
        dept_contacts=dept_contacts,
        escalation_results=escalation_actions or None,
        top_highlights=top_highlights[:3],
        secret=secret,
        action_progress=action_progress or None,
        product_id=product_id,
        platform=platform,
    )

    logger.info(
        "upload_job: smart push done for user %d, product %s, escalations=%d",
        user_id, product_id, len(escalation_results),
    )


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


def _fetch_aliexpress_path(
    loop: asyncio.AbstractEventLoop,
    user_id: int,
    job_id: int,
    item_id: str,
    payload: dict[str, Any],
    fetch_all_variants: bool,
) -> tuple[list[dict[str, Any]], int | None]:
    """AliExpress 抓取路径：无需 Rainforest，直接拉评论。"""
    from backend_api.app.services.review_scraper import fetch_reviews

    product_ref_id = upsert_product_from_api(user_id, {
        "parent_product_id": item_id,
        "name": payload.get("product_name") or f"AliExpress: {item_id}",
        "platform": "AliExpress",
        "category": payload.get("category"),
    })

    update_upload_job(user_id, job_id, {
        "status": "fetching",
        "error_message": "正在从 AliExpress 拉取评论...",
    })

    reviews = loop.run_until_complete(
        fetch_reviews(item_id, platform="aliexpress")
    )

    if reviews:
        ratings = [r.get("rating", 5) for r in reviews]
        avg_rating = sum(ratings) / len(ratings)
        upsert_product_from_api(user_id, {
            "parent_product_id": item_id,
            "name": payload.get("product_name") or f"AliExpress: {item_id}",
            "platform": "AliExpress",
            "rating": round(avg_rating, 1),
            "reviews_total": len(reviews),
        })

    return reviews, product_ref_id


def _fetch_ebay_path(
    loop: asyncio.AbstractEventLoop,
    user_id: int,
    job_id: int,
    item_id: str,
    payload: dict[str, Any],
    fetch_all_variants: bool,
) -> tuple[list[dict[str, Any]], int | None]:
    """eBay 抓取路径：Apify scrapier Actor。"""
    from backend_api.app.services.review_scraper import fetch_reviews

    product_ref_id = upsert_product_from_api(user_id, {
        "parent_product_id": item_id,
        "name": payload.get("product_name") or f"eBay: {item_id}",
        "platform": "eBay",
        "category": payload.get("category"),
    })

    update_upload_job(user_id, job_id, {
        "status": "fetching",
        "error_message": "正在从 eBay 拉取评论...",
    })

    reviews = loop.run_until_complete(
        fetch_reviews(item_id, platform="ebay")
    )

    if reviews:
        ratings = [r.get("rating", 5) for r in reviews]
        avg_rating = sum(ratings) / len(ratings)
        upsert_product_from_api(user_id, {
            "parent_product_id": item_id,
            "name": payload.get("product_name") or f"eBay: {item_id}",
            "platform": "eBay",
            "rating": round(avg_rating, 1),
            "reviews_total": len(reviews),
        })

    return reviews, product_ref_id


def _fetch_walmart_path(
    loop: asyncio.AbstractEventLoop,
    user_id: int,
    job_id: int,
    item_id: str,
    payload: dict[str, Any],
    fetch_all_variants: bool,
) -> tuple[list[dict[str, Any]], int | None]:
    """Walmart 抓取路径：Apify webscrapewizard Actor。"""
    from backend_api.app.services.review_scraper import fetch_reviews

    product_ref_id = upsert_product_from_api(user_id, {
        "parent_product_id": item_id,
        "name": payload.get("product_name") or f"Walmart: {item_id}",
        "platform": "Walmart",
        "category": payload.get("category"),
    })

    update_upload_job(user_id, job_id, {
        "status": "fetching",
        "error_message": "正在从 Walmart 拉取评论...",
    })

    reviews = loop.run_until_complete(
        fetch_reviews(item_id, platform="walmart")
    )

    if reviews:
        ratings = [r.get("rating", 5) for r in reviews]
        avg_rating = sum(ratings) / len(ratings)
        upsert_product_from_api(user_id, {
            "parent_product_id": item_id,
            "name": payload.get("product_name") or f"Walmart: {item_id}",
            "platform": "Walmart",
            "rating": round(avg_rating, 1),
            "reviews_total": len(reviews),
        })

    return reviews, product_ref_id


def _fetch_shopee_path(
    loop: asyncio.AbstractEventLoop,
    user_id: int,
    job_id: int,
    product_code: str,
    marketplace: str,
    payload: dict[str, Any],
    fetch_all_variants: bool,
) -> tuple[list[dict[str, Any]], int | None]:
    """Shopee 抓取路径：Apify → 公开 API fallback。"""
    from backend_api.app.services.review_scraper import fetch_reviews

    product_ref_id = upsert_product_from_api(user_id, {
        "parent_product_id": product_code,
        "name": payload.get("product_name") or f"Shopee: {product_code}",
        "platform": "Shopee",
        "category": payload.get("category"),
    })

    update_upload_job(user_id, job_id, {
        "status": "fetching",
        "error_message": "正在从 Shopee 拉取评论...",
    })

    reviews = loop.run_until_complete(
        fetch_reviews(product_code, platform="shopee", marketplace=marketplace)
    )

    if reviews:
        ratings = [r.get("rating", 5) for r in reviews]
        avg_rating = sum(ratings) / len(ratings)
        upsert_product_from_api(user_id, {
            "parent_product_id": product_code,
            "name": payload.get("product_name") or f"Shopee: {product_code}",
            "platform": "Shopee",
            "rating": round(avg_rating, 1),
            "reviews_total": len(reviews),
        })

    return reviews, product_ref_id


def _fetch_amazon_path(
    loop: asyncio.AbstractEventLoop,
    user_id: int,
    job_id: int,
    asin: str,
    marketplace: str,
    payload: dict[str, Any],
    fetch_all_variants: bool,
    max_variants: int,
) -> tuple[list[dict[str, Any]], int | None]:
    """Amazon 抓取路径：Rainforest 产品信息 + woot.com 评论。"""
    from backend_api.app.services.rainforest import fetch_product_variants
    from backend_api.app.services.review_scraper import fetch_reviews

    product_info, variants_list = loop.run_until_complete(
        fetch_product_variants(asin, marketplace=marketplace)
    )
    if product_info.get("title") and not payload.get("scraped_title"):
        payload["scraped_title"] = product_info.get("title")
    if product_info.get("category") and not payload.get("category"):
        payload["category"] = product_info.get("category")

    user_product_name = payload.get("product_name") or f"ASIN: {asin}"

    product_ref_id = upsert_product_from_api(user_id, {
        "parent_product_id": asin,
        "name": user_product_name,
        "scraped_title": product_info.get("title"),
        "platform": f"Amazon {marketplace.upper()}",
        "category": product_info.get("category"),
        "brand": product_info.get("brand"),
        "image_url": product_info.get("image_url"),
        "rating": product_info.get("rating"),
        "ratings_total": product_info.get("ratings_total"),
        "reviews_total": product_info.get("reviews_total"),
    })

    for v in variants_list[:max_variants]:
        try:
            upsert_variant_from_api(user_id, product_ref_id, {
                "child_asin": v["asin"],
                "name": v.get("title", ""),
                "brand": product_info.get("brand"),
                "image_url": v.get("image_url", ""),
                "price": v.get("price"),
                "price_currency": "USD",
            })
        except Exception:
            logger.warning("Failed to upsert variant %s (non-fatal)", v.get("asin"))

    if fetch_all_variants and variants_list:
        target_asins = [v["asin"] for v in variants_list[:max_variants]]
        if asin not in target_asins:
            target_asins.insert(0, asin)
    else:
        target_asins = [asin]

    all_reviews: list[dict[str, Any]] = []
    for idx, target_asin in enumerate(target_asins, 1):
        update_upload_job(user_id, job_id, {
            "status": "fetching",
            "error_message": f"正在拉取变体评论 ({idx}/{len(target_asins)})",
        })
        try:
            reviews = loop.run_until_complete(
                fetch_reviews(target_asin, platform="amazon", marketplace=marketplace)
            )
        except Exception:
            logger.warning("Failed to fetch reviews for variant %s, skipping", target_asin)
            continue

        for r in reviews:
            r["source_variant_asin"] = target_asin
        all_reviews.extend(reviews)

    return all_reviews, product_ref_id


def process_asin_fetch_job(user_id: int, job_id: int) -> None:
    """Worker 任务：拉取评论 → 存储 → 触发分析。

    支持平台：Amazon / AliExpress / eBay / Walmart / Shopee
    """
    MAX_VARIANTS = 20

    try:
        job = get_upload_job(user_id, job_id)
        if not job:
            return

        payload = job.get("payload_json") or {}
        asin = payload.get("asin", "")
        platform = payload.get("platform", "amazon")
        marketplace = payload.get("marketplace", "us")
        fetch_all_variants = payload.get("fetch_all_variants", False)
        max_reviews: int = int(payload.get("max_reviews") or 100)
        force_refresh: bool = bool(payload.get("force_refresh", False))

        update_upload_job(user_id, job_id, {"status": "fetching"})

        # ── 池缓存查询（fetch_all_variants 时跳过，需抓完整变体） ──
        pool_cache_hit = False
        product_ref_id: int | None = None
        if not force_refresh and not fetch_all_variants:
            cached_reviews, pool_meta = pool_lookup(platform, asin, marketplace, max_reviews)
            if pool_has_enough(pool_meta):
                all_reviews = cached_reviews
                pool_cache_hit = True
                logger.info("review_pool HIT: %s:%s/%s (%d reviews)", platform, asin, marketplace, len(cached_reviews))

        if not pool_cache_hit:
            loop = asyncio.new_event_loop()
            try:
                if platform == "aliexpress":
                    all_reviews, product_ref_id = _fetch_aliexpress_path(
                        loop, user_id, job_id, asin, payload, fetch_all_variants,
                    )
                elif platform == "ebay":
                    all_reviews, product_ref_id = _fetch_ebay_path(
                        loop, user_id, job_id, asin, payload, fetch_all_variants,
                    )
                elif platform == "walmart":
                    all_reviews, product_ref_id = _fetch_walmart_path(
                        loop, user_id, job_id, asin, payload, fetch_all_variants,
                    )
                elif platform == "shopee":
                    all_reviews, product_ref_id = _fetch_shopee_path(
                        loop, user_id, job_id, asin, marketplace, payload, fetch_all_variants,
                    )
                else:
                    all_reviews, product_ref_id = _fetch_amazon_path(
                        loop, user_id, job_id, asin, marketplace, payload, fetch_all_variants, MAX_VARIANTS,
                    )
            finally:
                loop.close()

        if not all_reviews:
            update_upload_job(
                user_id, job_id,
                {"status": "done", "total_rows": 0, "error_message": f"No reviews found for {platform}:{asin}"},
            )
            return

        # 去重（review_id 或 content[:80]+reviewer 组合）
        seen_keys: set[str] = set()
        unique_reviews: list[dict[str, Any]] = []
        for r in all_reviews:
            rid = r.get("review_id", "")
            if rid:
                key = rid
            else:
                key = f"{r.get('content', '')[:80]}|{r.get('reviewer', '')}"
            if key in seen_keys:
                continue
            seen_keys.add(key)
            unique_reviews.append(r)

        # ── 新鲜抓取后写入池（缓存命中时跳过） ──
        if not pool_cache_hit and unique_reviews:
            try:
                pool_write(platform, asin, marketplace, unique_reviews, scraper_source=platform)
            except Exception:
                logger.warning("pool_write failed, continuing without cache write", exc_info=True)

        quota_consume(user_id, "asin_fetch")

        if platform == "aliexpress":
            source_label = "AliExpress"
            comments_payload = [
                {
                    "review_id": r.get("review_id", ""),
                    "content": r["content"],
                    "rating": r.get("rating"),
                    "date": r.get("date") or r.get("review_date", ""),
                    "date_iso": r.get("date_iso"),
                    "reviewer": r.get("reviewer", ""),
                    "title": r.get("title", ""),
                    "source": "AliExpress",
                    "source_variant_asin": r.get("sku_info") or r.get("source_variant", ""),
                }
                for r in unique_reviews
            ]
        elif platform == "ebay":
            source_label = "eBay"
            comments_payload = [
                {
                    "review_id": r.get("review_id", ""),
                    "content": r["content"],
                    "rating": r.get("rating"),
                    "date": r.get("date") or r.get("review_date", ""),
                    "date_iso": r.get("date_iso"),
                    "reviewer": r.get("reviewer", ""),
                    "title": r.get("title", ""),
                    "source": "eBay",
                    "source_variant_asin": "",
                }
                for r in unique_reviews
            ]
        elif platform == "walmart":
            source_label = "Walmart"
            comments_payload = [
                {
                    "review_id": r.get("review_id", ""),
                    "content": r["content"],
                    "rating": r.get("rating"),
                    "date": r.get("date") or r.get("review_date", ""),
                    "date_iso": r.get("date_iso"),
                    "reviewer": r.get("reviewer", ""),
                    "title": r.get("title", ""),
                    "source": "Walmart",
                    "source_variant_asin": "",
                }
                for r in unique_reviews
            ]
        elif platform == "shopee":
            source_label = "Shopee"
            comments_payload = [
                {
                    "review_id": r.get("review_id", ""),
                    "content": r["content"],
                    "rating": r.get("rating"),
                    "date": r.get("date") or r.get("review_date", ""),
                    "date_iso": r.get("date_iso"),
                    "reviewer": r.get("reviewer", ""),
                    "title": r.get("title", ""),
                    "source": "Shopee",
                    "source_variant_asin": r.get("sku_info") or r.get("source_variant", ""),
                }
                for r in unique_reviews
            ]
        else:
            source_label = f"Amazon {marketplace.upper()}"
            comments_payload = [
                {
                    "review_id": r.get("review_id", ""),
                    "content": r["content"],
                    "rating": r.get("rating"),
                    "date": r.get("date") or r.get("review_date", ""),
                    "date_iso": r.get("date_iso"),
                    "reviewer": r.get("reviewer", ""),
                    "title": r.get("title", ""),
                    "source": source_label,
                    "source_variant_asin": r.get("source_variant_asin") or r.get("source_variant", asin),
                }
                for r in unique_reviews
            ]

        comments_payload = comments_payload[:max_reviews]

        update_upload_job(
            user_id, job_id,
            {
                "status": "queued",
                "total_rows": len(comments_payload),
                "product_ref_id": product_ref_id,
                "payload_json": {
                    **payload,
                    "comments": comments_payload,
                    "product_name": payload.get("product_name") or f"{platform.title()}: {asin}",
                    "platform": source_label,
                    "source_channel": "api",
                    "product_ref_id": product_ref_id,
                    "variant_count": None if platform == "aliexpress" else payload.get("variant_count"),
                },
            },
        )

        process_upload_job(user_id, job_id)

    except Exception as exc:
        update_upload_job(
            user_id, job_id,
            {"status": "failed", "error_message": str(exc)},
        )
        raise


def enqueue_asin_fetch_task(user_id: int, job_id: int) -> str:
    queue = get_queue()
    queued_job = queue.enqueue(
        process_asin_fetch_job,
        user_id,
        job_id,
        job_id=f"asin-fetch-{job_id}",
        description=f"Fetch reviews by ASIN (job {job_id})",
        result_ttl=0,
        failure_ttl=7 * 24 * 60 * 60,
    )
    return queued_job.id
