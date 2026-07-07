from __future__ import annotations

import tempfile
from pathlib import Path
from threading import Thread
from typing import Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile, status
from fastapi.responses import JSONResponse

from backend_api.app.deps import get_current_user
from backend_api.app.schemas.uploads import (
    AnalysisJobCreateRequest,
    UploadJobPayload,
    UploadJobResponse,
)
from backend_api.app.services.analysis_cache import compute_batch_hash
from backend_api.app.services.locale import get_analysis_locale
from review_analyzer.database import (
    create_upload_job,
    find_session_by_batch_hash,
    get_upload_job,
    update_upload_job,
)
from review_analyzer.parser import parse_file
from review_analyzer.quota import quota_check, quota_check_atomic
from workers.jobs import enqueue_upload_job_task, process_upload_job

router = APIRouter(tags=["uploads"])


def _job_payload(job: dict[str, Any]) -> UploadJobPayload:
    payload = dict(job)
    payload["payload_json"] = job.get("payload_json")
    return UploadJobPayload(**payload)


def _enqueue_upload_job(user_id: int, payload: dict[str, Any]) -> UploadJobResponse:
    comments = payload.get("comments") or []
    comment_count = len(comments)

    # 单文件行数限制
    allowed, msg = quota_check(user_id, "upload_rows_per_file", comment_count)
    if not allowed:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=msg)

    # 月度评论分析额度预检
    allowed, msg = quota_check_atomic(user_id, "review_analyze", comment_count)
    if not allowed:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=msg)

    job_id = create_upload_job(
        user_id,
        {
            "status": "queued",
            "source_filename": payload["source_filename"],
            "product_id": payload["product_id"],
            "version": payload.get("version", "V1"),
            "workflow_purpose": payload.get("workflow_purpose"),
            "product_ref_id": payload.get("product_ref_id"),
            "variant_ref_id": payload.get("variant_ref_id"),
            "total_rows": len(payload.get("comments") or []),
            "processed_rows": 0,
            "positive_count": 0,
            "negative_count": 0,
            "payload_json": payload,
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
            {
                "status": "failed",
                "error_message": str(exc),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Worker queue is unavailable.",
        ) from exc

    job = get_upload_job(user_id, job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create upload job.",
        )
    return UploadJobResponse(job=_job_payload(job), message="Upload job created.")


@router.post("/uploads", response_model=UploadJobResponse)
def create_uploads(
    request: Request,
    source_file: UploadFile = File(...),
    product_id: str = Form(...),
    version: str = Form(default="V1"),
    workflow_purpose: str | None = Form(default=None),
    product_name: str | None = Form(default=None),
    platform: str | None = Form(default=None),
    category: str | None = Form(default=None),
    date_start: str | None = Form(default=None),
    date_end: str | None = Form(default=None),
    version_notes: str | None = Form(default=None),
    product_ref_id: int | None = Form(default=None),
    variant_ref_id: int | None = Form(default=None),
    current_user: dict = Depends(get_current_user),
) -> UploadJobResponse:
    user_id = int(current_user["id"])
    suffix = f".{source_file.filename.split('.')[-1]}" if source_file.filename and "." in source_file.filename else ""
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(source_file.file.read())
        tmp_path = tmp.name

    try:
        parsed_df = parse_file(tmp_path, suffix.lstrip(".") or "txt")
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    finally:
        Path(tmp_path).unlink(missing_ok=True)

    comments = parsed_df.to_dict(orient="records")

    batch_hash = compute_batch_hash(comments, category)

    payload = {
        "source_filename": source_file.filename or "upload",
        "product_id": product_id,
        "version": version,
        "workflow_purpose": workflow_purpose,
        "product_name": product_name,
        "platform": platform,
        "category": category,
        "date_start": date_start,
        "date_end": date_end,
        "version_notes": version_notes,
        "product_ref_id": product_ref_id,
        "variant_ref_id": variant_ref_id,
        "comments": comments,
        "batch_hash": batch_hash,
        "locale": get_analysis_locale(request),
    }
    return _enqueue_upload_job(user_id, payload)


@router.post("/analysis/jobs", response_model=UploadJobResponse)
def create_analysis_job(
    payload: AnalysisJobCreateRequest,
    request: Request,
    current_user: dict = Depends(get_current_user),
) -> UploadJobResponse:
    user_id = int(current_user["id"])
    data = payload.model_dump()
    data["locale"] = get_analysis_locale(request)
    comments = data.get("comments") or []
    if comments:
        batch_hash = compute_batch_hash(comments, data.get("category"))
        product_id = data.get("product_id") or ""
        existing = find_session_by_batch_hash(user_id, product_id, batch_hash)
        if existing:
            return JSONResponse(
                status_code=status.HTTP_409_CONFLICT,
                content={
                    "detail": "duplicate_batch",
                    "existing_session_id": existing["id"],
                    "existing_title": existing.get("custom_title") or existing.get("auto_title") or "",
                    "existing_created_at": str(existing.get("created_at") or ""),
                    "total_reviews": existing.get("total_reviews", 0),
                },
            )
        data["batch_hash"] = batch_hash
    return _enqueue_upload_job(user_id, data)


@router.get("/analysis/jobs/{job_id}", response_model=UploadJobResponse)
def get_analysis_job(
    job_id: int,
    current_user: dict = Depends(get_current_user),
) -> UploadJobResponse:
    user_id = int(current_user["id"])
    job = get_upload_job(user_id, job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Upload job not found.",
        )
    return UploadJobResponse(job=_job_payload(job), message="Upload job fetched.")
