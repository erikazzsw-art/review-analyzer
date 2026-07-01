"""评论自动获取路由 — ASIN 自动拉取 + Chrome 插件上传。"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from backend_api.app.deps import get_current_user
from backend_api.app.schemas.scrape import AsinFetchRequest, AsinFetchResponse
from review_analyzer.database import (
    create_upload_job,
    update_upload_job,
)
from review_analyzer.quota import quota_check
from workers.jobs import enqueue_asin_fetch_task, process_asin_fetch_job

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
