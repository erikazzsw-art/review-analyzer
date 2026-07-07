from __future__ import annotations

import asyncio
import logging
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
    update_comment_cluster,
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
from review_analyzer.quota import quota_consume
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
    trace = JobTrace(job_id=job_id, user_id=user_id)
    try:
        trace.begin_stage("init")
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
        # V6-locale: 从 payload 取 locale，无则默认 en（海外优先）
        locale = str(payload.get("locale") or "en")

        update_upload_job(user_id, job_id, {"status": "processing"})

        # 断点续跑：如果 job 已有 session_id，跳过创建阶段直接续跑未处理评论
        existing_session_id = job.get("session_id")
        if existing_session_id:
            session_id = int(existing_session_id)
            logger.info("upload_job %s: resuming session %d", job_id, session_id)
        else:
            batch_hash = payload.get("batch_hash")
            if not batch_hash and comments_payload:
                batch_hash = compute_batch_hash(comments_payload)

            # batch_hash 重复时复用已有 session（同一用户+产品+相同评论集）
            if batch_hash:
                dup_session = find_session_by_batch_hash(user_id, product_id, batch_hash)
                if dup_session:
                    session_id = int(dup_session["id"])
                    logger.info("upload_job %s: batch_hash duplicate, reusing session %d", job_id, session_id)
                    update_upload_job(user_id, job_id, {
                        "status": "done",
                        "session_id": session_id,
                        "total_rows": dup_session.get("total_reviews") or len(comments_payload),
                        "positive_count": dup_session.get("positive_count") or 0,
                        "negative_count": dup_session.get("negative_count") or 0,
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
                    "batch_hash": batch_hash,
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
        cluster_count = 0
        trace.end_stage(meta={"review_count": len(unprocessed)})

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

            sub_category = str(payload.get("category") or "家具家居")
            aspects, taxonomy_hit = resolve_aspects(sub_category)
            aspects_block = render_aspects_block(aspects)
            calibration_block = build_calibration_block(sub_category)
            if calibration_block:
                aspects_block += "\n\n" + calibration_block
            allowed_aspects = [a["key"] for a in aspects]

            # --- V4-T4 Step 3: 多级缓存 ---
            trace.begin_stage("cache")
            # L1: 收集当前 batch 的 content_hash，查询已有分析结果
            # migration 043: 除用户自己历史，同时查全局 review_pool 支持跨用户复用
            content_hashes = [
                compute_content_hash(c.get("content", ""), c.get("rating"))
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
                            {"content": c.get("content", ""), "rating": c.get("rating"), "title": c.get("title", "")}
                            for c in llm_comments
                        ],
                        sub_category=sub_category,
                        prompt_version=PROMPT_VERSION,
                        aspects_block=aspects_block,
                        allowed_aspects=allowed_aspects,
                        progress_callback=llm_progress,
                        user_id=user_id,
                        locale=locale,
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
                            logger.exception(
                                "update_comment_cluster failed for comment_id=%s user_id=%s",
                                cid, user_id,
                            )

                    for c, r in zip(llm_emb_comments, v4_results):
                        id_to_v4[c["id"]] = r

                    # 没 embedding 但需要 LLM 的评论
                    emb_id_set = {c["id"] for c in llm_emb_comments}
                    non_emb_comments = [c for c in need_llm if c["id"] not in emb_id_set]
                    if non_emb_comments:
                        llm_progress = _make_llm_progress(len(v4_llm_results))
                        non_emb_results = deep_analyze_batch(
                            comments=[
                                {"content": c.get("content", ""), "rating": c.get("rating"), "title": c.get("title", "")}
                                for c in non_emb_comments
                            ],
                            sub_category=sub_category,
                            prompt_version=PROMPT_VERSION,
                            aspects_block=aspects_block,
                            allowed_aspects=allowed_aspects,
                            progress_callback=llm_progress,
                            user_id=user_id,
                            locale=locale,
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
                        progress_callback=_make_llm_progress(0),
                        user_id=user_id,
                        locale=locale,
                    )
                    for c, r in zip(need_llm, llm_results):
                        id_to_v4[c["id"]] = r

            # 按 unprocessed 顺序组装最终结果
            llm_count = sum(1 for v in id_to_v4.values() if not v.get("cache_hit_level"))
            trace.end_stage(meta={"llm_calls": llm_count, "need_llm": len(need_llm) if need_llm else 0})

            trace.begin_stage("post_process")
            ordered_v4_results = [id_to_v4.get(c["id"], {"error": "no_result"}) for c in unprocessed]

            _progress_callback(len(unprocessed), len(unprocessed))
        else:
            ordered_v4_results = []

        # 增量写入：每条评论分析完立即持久化，崩溃不丢进度
        positive_count = 0
        negative_count = 0
        results = []
        for comment, v4 in zip(unprocessed, ordered_v4_results):
            if v4.get("error"):
                result = {
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
                }
            else:
                result = aspects_to_legacy_schema(
                    aspects=v4.get("aspects", []),
                    sentiment=v4.get("sentiment", "neutral"),
                    content=comment.get("content", ""),
                    pain_points=v4.get("pain_points", []),
                    highlights=v4.get("highlights", []),
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
                result["analyzer_version"] = ANALYZER_VERSION
                result["cache_hit_level"] = v4.get("cache_hit_level")
                result["cache_source_id"] = v4.get("cache_source_id")

            rating = comment.get("rating")
            if rating is not None:
                try:
                    rating_val = int(float(rating))
                    result["sentiment"] = "negative" if rating_val <= 3 else "positive"
                except (TypeError, ValueError):
                    pass

            update_comment_analysis(user_id, int(comment["id"]), result)
            results.append(result)

            if result.get("sentiment") == "positive":
                positive_count += 1
            elif result.get("sentiment") == "negative":
                negative_count += 1

        update_session_stats(user_id, session_id, len(unprocessed), positive_count, negative_count)

        # 扣减 review_analyze 月度额度
        quota_consume(user_id, "review_analyze", len(unprocessed))

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
        if taxonomy_warnings:
            trace_dict["warnings"] = taxonomy_warnings

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
                # 首先写入 review_pool（若 CSV 是新数据，pool_write 会 upsert）
                # 再回填分析结果
                pool_write(
                    _backfill_platform, _backfill_key, _backfill_market,
                    unprocessed,
                    scraper_source=payload.get("source_channel") or "csv",
                )
                pool_backfill_analysis(
                    _backfill_platform, _backfill_key, _backfill_market,
                    unprocessed, analyzer_version=ANALYZER_VERSION,
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
    from review_analyzer.department_router import route_issues_by_department
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
        from review_analyzer.push_snapshot_store import get_recent_snapshots, mark_escalated
        from review_analyzer.aspect_taxonomy import get_aspect_label_zh

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
                    "suggested_action": "已写入行动中心",
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

    product_ref_id = upsert_product_from_api(user_id, {
        "parent_product_id": asin,
        "name": product_info.get("title") or payload.get("product_name") or f"ASIN: {asin}",
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
                    "content": r["content"],
                    "rating": r.get("rating"),
                    "date": r.get("date") or r.get("review_date", ""),
                    "reviewer": r.get("reviewer", ""),
                    "source": "AliExpress",
                    "source_variant_asin": r.get("sku_info") or r.get("source_variant", ""),
                }
                for r in unique_reviews
            ]
        elif platform == "ebay":
            source_label = "eBay"
            comments_payload = [
                {
                    "content": r["content"],
                    "rating": r.get("rating"),
                    "date": r.get("date") or r.get("review_date", ""),
                    "reviewer": r.get("reviewer", ""),
                    "source": "eBay",
                    "source_variant_asin": "",
                }
                for r in unique_reviews
            ]
        elif platform == "walmart":
            source_label = "Walmart"
            comments_payload = [
                {
                    "content": r["content"],
                    "rating": r.get("rating"),
                    "date": r.get("date") or r.get("review_date", ""),
                    "reviewer": r.get("reviewer", ""),
                    "source": "Walmart",
                    "source_variant_asin": "",
                }
                for r in unique_reviews
            ]
        elif platform == "shopee":
            source_label = "Shopee"
            comments_payload = [
                {
                    "content": r["content"],
                    "rating": r.get("rating"),
                    "date": r.get("date") or r.get("review_date", ""),
                    "reviewer": r.get("reviewer", ""),
                    "source": "Shopee",
                    "source_variant_asin": r.get("sku_info") or r.get("source_variant", ""),
                }
                for r in unique_reviews
            ]
        else:
            source_label = f"Amazon {marketplace.upper()}"
            comments_payload = [
                {
                    "content": r["content"],
                    "rating": r.get("rating"),
                    "date": r.get("date") or r.get("review_date", ""),
                    "reviewer": r.get("reviewer", ""),
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
