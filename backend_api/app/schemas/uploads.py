from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class AnalysisJobCreateRequest(BaseModel):
    source_filename: str
    product_id: str
    version: str = "V1"
    workflow_purpose: str | None = None
    product_name: str | None = None
    platform: str | None = None
    category: str | None = None
    date_start: str | None = None
    date_end: str | None = None
    version_notes: str | None = None
    product_ref_id: int | None = None
    variant_ref_id: int | None = None
    comments: list["AnalysisCommentPayload"]


class AnalysisCommentPayload(BaseModel):
    content: str
    date: str
    rating: int | None = None
    reviewer: str | None = None
    source: str | None = None
    raw_data: dict | None = None


class UploadJobPayload(BaseModel):
    id: int
    user_id: int
    status: str
    source_filename: str
    product_id: str
    version: str
    workflow_purpose: str | None = None
    product_ref_id: int | None = None
    variant_ref_id: int | None = None
    total_rows: int
    processed_rows: int
    positive_count: int
    negative_count: int
    session_id: int | None = None
    error_message: str | None = None
    payload_json: dict | None = None
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None = None


class UploadJobResponse(BaseModel):
    ok: bool = True
    job: UploadJobPayload
    message: str


AnalysisJobCreateRequest.model_rebuild()
