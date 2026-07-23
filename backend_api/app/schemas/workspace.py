from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class WorkspaceIntroPayload(BaseModel):
    headline: str
    focus: str


class WorkspaceMetricsPayload(BaseModel):
    product_count: int
    risk_product_count: int
    open_action_count: int
    open_tracker_count: int
    recent_upload_count: int


class WorkspaceTaskPayload(BaseModel):
    category: str
    title: str
    description: str
    cta_label: str
    page: str
    session_updates: dict[str, str | int | None]


class WorkspaceRiskProductPayload(BaseModel):
    product_id: str | None = None
    product_name: str
    negative_rate: float
    top_issue: str
    pending_review_count: int
    review_count: int
    latest_session_label: str


class WorkspacePendingTrackerPayload(BaseModel):
    title: str
    product_name: str
    tag_name: str
    status: str
    baseline_pct: float | None = None
    current_pct: float | None = None
    review_scope: str


class WorkspaceRoleActionPayload(BaseModel):
    role: str
    count: int


class WorkspaceResponsibilityActionPayload(BaseModel):
    responsibility: str
    count: int


class WorkspaceRecentSessionPayload(BaseModel):
    session_id: int
    title: str
    product_id: str
    workflow_purpose: str
    created_at: str
    total_reviews: int


class WorkspaceSummaryPayload(BaseModel):
    intro: WorkspaceIntroPayload
    metrics: WorkspaceMetricsPayload
    today_tasks: list[WorkspaceTaskPayload]
    risk_products: list[WorkspaceRiskProductPayload]
    pending_trackers: list[WorkspacePendingTrackerPayload]
    responsibility_action_summary: list[WorkspaceResponsibilityActionPayload]
    role_action_summary: list[WorkspaceRoleActionPayload]
    recent_sessions: list[WorkspaceRecentSessionPayload]
    generated_at: datetime
