from __future__ import annotations

import json
import logging
import tempfile
from pathlib import Path
from threading import Thread
from typing import Any

import psycopg2
from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile, status
from fastapi.encoders import jsonable_encoder
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
from review_analyzer.product_store import (
    _detect_identifier_column,
    _extract_unique_identifiers,
    batch_upsert_variants_for_upload,
    resolve_product_reference_for_upload,
)
from review_analyzer.quota import quota_check, quota_check_atomic
from workers.jobs import enqueue_upload_job_task, process_upload_job

router = APIRouter(tags=["uploads"])
logger = logging.getLogger(__name__)


def _merged_raw_comment_row(comment: dict[str, Any]) -> dict[str, Any]:
    raw_data = comment.get("raw_data")
    raw: dict[str, Any] = {}
    if isinstance(raw_data, str) and raw_data.strip():
        try:
            parsed = json.loads(raw_data)
            if isinstance(parsed, dict):
                raw = parsed
        except json.JSONDecodeError:
            raw = {}
    elif isinstance(raw_data, dict):
        raw = raw_data
    return {**raw, **comment}


def _identifier_from_row(
    row: dict[str, Any],
    id_column: str,
    platform: str,
) -> str | None:
    values = _extract_unique_identifiers([row], id_column, platform)
    return values[0] if values else None


def _annotate_upload_variant_asins(
    comments: list[dict[str, Any]],
    platform: str | None,
    representative_asin: str | None = None,
) -> tuple[list[dict[str, Any]], list[str]]:
    if not platform or not comments:
        return comments, []

    rows = [_merged_raw_comment_row(comment) for comment in comments]
    column_names: list[str] = []
    seen: set[str] = set()
    for row in rows:
        for key in row:
            if key not in seen:
                seen.add(key)
                column_names.append(key)

    sample_values = [
        [str(row.get(col, "")) for row in rows[:5]]
        for col in column_names
    ]
    id_column = _detect_identifier_column(column_names, sample_values, platform)

    identifiers: list[str] = []
    seen_identifiers: set[str] = set()
    if id_column:
        for comment, row in zip(comments, rows):
            identifier = _identifier_from_row(row, id_column, platform)
            if not identifier:
                continue
            comment["source_variant_asin"] = identifier
            if identifier not in seen_identifiers:
                seen_identifiers.add(identifier)
                identifiers.append(identifier)

    if not identifiers and representative_asin:
        representative = _identifier_from_row(
            {"representative_asin": representative_asin},
            "representative_asin",
            platform,
        )
        if representative:
            identifiers.append(representative)

    return comments, identifiers


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
    representative_asin: str | None = Form(default=None),
    product_ref_id: int | None = Form(default=None),
    variant_ref_id: int | None = Form(default=None),
    current_user: dict = Depends(get_current_user),
) -> UploadJobResponse:
    user_id = int(current_user["id"])
    parent_product_name = (product_name or "").strip()
    if not parent_product_name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Product Name is required.",
        )
    product_id = parent_product_name
    product_name = parent_product_name

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
    comments, identifiers = _annotate_upload_variant_asins(
        comments,
        platform=platform,
        representative_asin=representative_asin,
    )

    batch_hash = compute_batch_hash(comments, category)

    # ── 5.8: 平台感知 — CSV 标识码自动识别与变体归并 ──
    variant_merge_result = None
    if platform and product_name and comments:
        if identifiers:
            try:
                variant_merge_result = batch_upsert_variants_for_upload(
                    user_id, platform, identifiers,
                    parent_name=product_name,
                    category=category,
                )
            except (
                psycopg2.errors.UndefinedColumn,
                psycopg2.errors.UndefinedTable,
                psycopg2.errors.InvalidColumnReference,
                psycopg2.IntegrityError,
            ) as exc:
                logger.warning(
                    "Skipping upload variant merge because product catalog is not ready or has legacy conflicts: %s",
                    exc,
                )

    resolved_product = resolve_product_reference_for_upload(
        user_id=user_id,
        parent_name=product_name,
        platform=platform,
        identifiers=identifiers,
    )
    if resolved_product:
        product_ref_id = int(resolved_product["id"])
        product_id = str(resolved_product["parent_product_id"])
        if variant_ref_id is None and resolved_product.get("variant_id") is not None:
            variant_ref_id = int(resolved_product["variant_id"])

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
        "representative_asin": representative_asin,
        "product_ref_id": product_ref_id,
        "variant_ref_id": variant_ref_id,
        "comments": comments,
        "batch_hash": batch_hash,
        "locale": get_analysis_locale(request),
    }

    response_data = _enqueue_upload_job(user_id, payload)

    # 附加变体归并结果到响应
    if variant_merge_result:
        new_count = sum(1 for r in variant_merge_result if r["action"] == "new")
        existing_count = sum(1 for r in variant_merge_result if r["action"] == "existing")
        merged_count = sum(1 for r in variant_merge_result if r["action"] == "merged_to_other")
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content=jsonable_encoder({
                "job": response_data.job.model_dump(),
                "message": response_data.message,
                "variant_merge": {
                    "identifiers_found": len(identifiers) if variant_merge_result else 0,
                    "new_variants": new_count,
                    "existing_variants": existing_count,
                    "merged_to_other": merged_count,
                    "details": variant_merge_result,
                },
            }),
        )

    return response_data


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
