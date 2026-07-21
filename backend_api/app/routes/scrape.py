"""评论自动获取路由 — ASIN 自动拉取 + Chrome 插件上传。"""
from __future__ import annotations

from threading import Thread

from fastapi import APIRouter, Depends, HTTPException, Query, status

from backend_api.app.deps import get_current_user
from backend_api.app.schemas.scrape import (
    AsinFetchRequest,
    AsinFetchResponse,
    PluginUploadRequest,
    PluginUploadResponse,
)
from review_analyzer.database import (
    create_upload_job,
    get_existing_plugin_review_keys,
    update_upload_job,
)
from review_analyzer.quota import quota_check, quota_check_atomic
from workers.jobs import (
    enqueue_asin_fetch_task,
    enqueue_upload_job_task,
    process_asin_fetch_job,
    process_upload_job,
)

router = APIRouter(tags=["scrape"])


@router.post("/reviews/fetch-by-asin", response_model=AsinFetchResponse)
def fetch_by_asin(
    req: AsinFetchRequest,
    current_user: dict = Depends(get_current_user),
) -> AsinFetchResponse:
    """通过产品编码自动拉取评论（异步任务）。"""
    user_id = int(current_user["id"])

    allowed, msg = quota_check(user_id, "asin_fetch")
    if not allowed:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=msg)

    source_label = f"aliexpress:{req.asin}" if req.platform == "aliexpress" else f"rainforest:{req.asin}"

    job_id = create_upload_job(
        user_id,
        {
            "status": "queued",
            "source_filename": source_label,
            "product_id": req.asin,
            "source_channel": "api",
            "version": "V1",
            "total_rows": 0,
            "processed_rows": 0,
            "positive_count": 0,
            "negative_count": 0,
            "payload_json": {
                "asin": req.asin,
                "platform": req.platform,
                "marketplace": req.marketplace,
                "product_name": req.product_name,
                "max_pages": req.max_pages,
                "source_channel": "api",
                "fetch_all_variants": req.fetch_all_variants,
                "max_reviews": req.max_reviews,
                "force_refresh": req.force_refresh,
            },
        },
    )

    try:
        enqueue_asin_fetch_task(user_id, job_id)
    except RuntimeError:
        try:
            process_asin_fetch_job(user_id, job_id)
        except Exception as exc:
            update_upload_job(user_id, job_id, {"status": "failed", "error_message": str(exc)})
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Worker queue is unavailable.",
            ) from exc
    except Exception as exc:
        update_upload_job(user_id, job_id, {"status": "failed", "error_message": str(exc)})
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Worker queue is unavailable.",
        ) from exc

    return AsinFetchResponse(
        job_id=job_id,
        asin=req.asin,
        platform=req.platform,
        marketplace=req.marketplace,
        message=f"Fetch job queued for {req.platform}:{req.asin}",
    )


@router.post("/reviews/plugin-upload", response_model=PluginUploadResponse)
def plugin_upload(
    req: PluginUploadRequest,
    current_user: dict = Depends(get_current_user),
) -> PluginUploadResponse:
    """接收 Chrome 扩展直传的评论 JSON（Step 15）。

    流程：
    1. 配额校验（per_request: Free 100/Pro 1000 条/次）
    2. 月度分析额度预检
    3. 按 (reviewer + date) 去重
    4. 创建 upload_job + 入队分析
    """
    user_id = int(current_user["id"])

    # ── 配额：单次上传数量限制 ──
    total_count = len(req.reviews)
    allowed, msg = quota_check(user_id, "plugin_upload", total_count)
    if not allowed:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=msg)

    # ── 去重：按 (reviewer, date) 检查已有评论 ──
    existing_keys = get_existing_plugin_review_keys(user_id, req.asin)

    unique_reviews: list[dict] = []
    duplicate_count = 0
    for r in req.reviews:
        key = f"{r.reviewer or ''}|{r.date}"
        if key in existing_keys:
            duplicate_count += 1
            continue
        existing_keys.add(key)
        unique_reviews.append({
            "content": r.body,
            "rating": r.rating,
            "date": r.date,
            "reviewer": r.reviewer or "",
            "source": f"Amazon {req.marketplace.upper()}",
            "source_variant_asin": req.asin,
        })

    new_count = len(unique_reviews)

    if new_count == 0:
        return PluginUploadResponse(
            job_id=0,
            asin=req.asin,
            marketplace=req.marketplace,
            total_received=total_count,
            new_reviews=0,
            duplicate_count=duplicate_count,
            message=f"All {total_count} reviews are duplicates. No new reviews to process.",
        )

    # ── 月度分析额度预检 ──
    allowed, msg = quota_check_atomic(user_id, "review_analyze", new_count)
    if not allowed:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=msg)

    source_label = f"chrome_extension:{req.asin}"

    job_id = create_upload_job(
        user_id,
        {
            "status": "queued",
            "source_filename": source_label,
            "product_id": req.asin,
            "source_channel": "chrome_extension",
            "version": "V1",
            "total_rows": new_count,
            "processed_rows": 0,
            "positive_count": 0,
            "negative_count": 0,
            "payload_json": {
                "asin": req.asin,
                "marketplace": req.marketplace,
                "platform": req.platform,
                "product_name": req.product_name or f"Amazon {req.marketplace.upper()}: {req.asin}",
                "page_url": req.page_url,
                "source_channel": "chrome_extension",
                "comments": unique_reviews,
            },
        },
    )

    try:
        enqueue_upload_job_task(user_id, job_id)
    except RuntimeError:
        Thread(
            target=process_upload_job,
            args=(user_id, job_id),
            daemon=True,
        ).start()
    except Exception as exc:
        update_upload_job(
            user_id,
            job_id,
            {"status": "failed", "error_message": str(exc)},
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Worker queue is unavailable.",
        ) from exc

    return PluginUploadResponse(
        job_id=job_id,
        asin=req.asin,
        marketplace=req.marketplace,
        total_received=total_count,
        new_reviews=new_count,
        duplicate_count=duplicate_count,
        message=f"Plugin upload queued: {new_count} new reviews (skipped {duplicate_count} duplicates).",
    )


# ── 5.8.3: 亚马逊可用性检查 ──


@router.get("/reviews/check-asin-availability")
def check_asin_availability(
    asin: str = Query(..., min_length=1, max_length=20),
    platform: str = Query(default="amazon", max_length=20),
    marketplace: str = Query(default="us", max_length=5),
    current_user: dict = Depends(get_current_user),
) -> dict:
    """检查指定 ASIN 是否可通过自动抓取获取评论。

    返回:
    - available: 是否可自动抓取
    - suggestion: 不可用时的建议文案
    """
    from review_analyzer.database import get_connection

    user_id = int(current_user["id"])

    # 仅 Amazon 平台支持自动抓取
    if platform.lower() != "amazon":
        return {
            "asin": asin,
            "platform": platform,
            "available": False,
            "suggestion": "当前平台暂不支持自动抓取，请使用文件上传或 Chrome 插件。",
        }

    # 检查是否已有抓取记录（通过 upload_jobs 的 source_channel = 'api'）
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT COUNT(*) FROM upload_jobs
                   WHERE user_id = %s
                     AND source_filename = %s
                     AND source_channel = 'api'
                     AND status = 'done'""",
                (user_id, f"rainforest:{asin}"),
            )
            row = cur.fetchone()
            has_history = (row[0] if row else 0) > 0
    finally:
        conn.close()

    return {
        "asin": asin,
        "platform": platform,
        "marketplace": marketplace,
        "available": True,  # Amazon 默认标记为可尝试
        "has_prior_success": has_history,
        "suggestion": None if has_history else "该 ASIN 暂未通过自动抓取成功获取评论，若抓取失败建议使用 Chrome 插件。",
    }


# ── 5.8.4: 跨用户缓存复用 — platform + ASIN 联合查询 ──


@router.get("/reviews/asin-analysis-status")
def asin_analysis_status(
    asin: str = Query(..., min_length=1, max_length=20),
    platform: str = Query(default="amazon", max_length=20),
    current_user: dict = Depends(get_current_user),
) -> dict:
    """查询指定 platform+ASIN 的分析缓存状态（内部使用，前端不展示提示）。

    用于跨用户缓存复用：后台透明检查该 ASIN 是否已有分析结果，
    不暴露其他用户的分析内容，仅返回缓存命中统计。
    """
    from review_analyzer.database import get_connection
    import psycopg2.extras

    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            # 查询该 ASIN 下所有评论的缓存命中情况（不限制 user_id，跨用户复用）
            cur.execute(
                """SELECT
                    COUNT(*) as total_comments,
                    COUNT(*) FILTER (WHERE sentiment IS NOT NULL) as analyzed_comments,
                    COUNT(*) FILTER (WHERE is_cached = true) as cached_comments
                   FROM comments
                   WHERE product_id = %s
                     AND source_variant_asin = %s""",
                (asin, asin),
            )
            row = cur.fetchone()
            stats = dict(row) if row else {}

            return {
                "asin": asin,
                "platform": platform,
                "has_cached_analysis": (stats.get("analyzed_comments", 0) or 0) > 0,
                "total_comments": stats.get("total_comments", 0) or 0,
                "analyzed_comments": stats.get("analyzed_comments", 0) or 0,
                "cached_comments": stats.get("cached_comments", 0) or 0,
                # 不暴露其他用户信息，仅返回统计数字
            }
    finally:
        conn.close()
