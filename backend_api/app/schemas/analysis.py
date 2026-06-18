from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class AnalysisSessionPayload(BaseModel):
    id: int
    user_id: int
    product_id: str
    version: str
    auto_title: str | None = None
    custom_title: str | None = None
    date_range_start: str | None = None
    date_range_end: str | None = None
    total_reviews: int
    positive_count: int
    negative_count: int
    category: str | None = None
    prompt_version: str | None = None
    version_notes: str | None = None
    workflow_purpose: str | None = None
    product_ref_id: int | None = None
    variant_ref_id: int | None = None
    warnings_json: list[dict[str, Any]] | None = None
    created_at: datetime


class AnalysisResultModulePayload(BaseModel):
    summary: str = ""
    rows: list[dict[str, Any]] = Field(default_factory=list)
    evidence: list[str] = Field(default_factory=list)
    positive: list[dict[str, Any]] = Field(default_factory=list)
    negative: list[dict[str, Any]] = Field(default_factory=list)


class AnalysisSessionResultsPayload(BaseModel):
    session: AnalysisSessionPayload
    context: dict[str, Any]
    modules: dict[str, AnalysisResultModulePayload]
    comments: list[dict[str, Any]]
    generated_at: datetime


class AnalysisCompareGroupPayload(BaseModel):
    label: str
    description: str
    session_ids: list[int] = Field(default_factory=list)
    product_id: str | None = None
    versions: list[str] = Field(default_factory=list)
    product_ref_id: int | None = None
    variant_ref_id: int | None = None
    review_count: int
    valid_review_count: int
    positive_rate: float
    negative_rate: float
    avg_rating: float | None = None
    top_issue: str
    top_highlight: str
    top_issues: list[dict[str, Any]]
    top_highlights: list[dict[str, Any]]
    representative_reviews: dict[str, list[dict[str, Any]]]


class AnalysisComparePayload(BaseModel):
    compare_type: str
    groups: list[AnalysisCompareGroupPayload]
    comparison_rows: list[dict[str, Any]]
    issue_differences: list[dict[str, Any]]
    highlight_differences: list[dict[str, Any]]
    risk_groups: list[dict[str, Any]]
    opportunity_groups: list[dict[str, Any]]
    recommended_actions: list[str]
    empty_groups: list[str]
    generated_at: datetime


class AnalysisHistorySessionPayload(BaseModel):
    id: int
    product_id: str
    version: str
    title: str
    workflow_purpose: str
    created_at: datetime
    total_reviews: int
    positive_count: int
    negative_count: int


class AnalysisHistoryProductPayload(BaseModel):
    product_id: str
    product_name: str | None = None
    session_count: int
    latest_session_id: int | None = None
    latest_session_title: str | None = None
    latest_session_created_at: datetime | None = None
    sessions: list[AnalysisHistorySessionPayload]


class AnalysisHistoryPayload(BaseModel):
    items: list[AnalysisHistoryProductPayload]
    total: int
    selected_session_id: int | None = None
    selected_product_id: str | None = None
    generated_at: datetime


class ComparisonReportCreatePayload(BaseModel):
    compare_type: str = "custom"
    session_ids: list[int] = Field(default_factory=list)
    product_id: str | None = None
    focus_feature: str | None = None
    title: str | None = None


class ComparisonReportPayload(BaseModel):
    id: int
    user_id: int
    comparison_type: str
    title: str | None = None
    filters_json: dict[str, Any] | None = None
    result_snapshot: dict[str, Any] | None = None
    summary: str | None = None
    recommendations: str | None = None
    created_at: datetime


class ComparisonReportResponse(BaseModel):
    report: ComparisonReportPayload
    dataset: AnalysisComparePayload
    ai_summary: dict[str, Any] | None = None


class QaProductPayload(BaseModel):
    id: int | None = None
    parent_product_id: str
    name: str | None = None
    review_count: int = 0
    negative_rate: float = 0.0
    latest_session_label: str | None = None


class QaAskRequest(BaseModel):
    product_ids: list[str] = Field(default_factory=list)
    question: str
    top_k: int = 5


class QaCitationPayload(BaseModel):
    id: int | None = None
    product_id: str | None = None
    version: str | None = None
    session_id: int | None = None
    date: str | None = None
    rating: int | None = None
    content: str | None = None
    issue_tag: str | None = None
    highlight_tag: str | None = None
    sentiment: str | None = None


class QaAskResponse(BaseModel):
    answer: str
    retrieval_method: str
    selected_products: list[QaProductPayload] = Field(default_factory=list)
    citations: list[QaCitationPayload] = Field(default_factory=list)


class ActionItemCreatePayload(BaseModel):
    product_id: int | None = None
    variant_id: int | None = None
    session_id: int | None = None
    source_product_id: str | None = None
    source_version: str | None = None
    source_batch_label: str | None = None
    title: str
    tag_name: str | None = None
    tag_type: str = "issue"
    current_pct: float | None = None
    owner_role: str | None = None
    suggested_action: str | None = None
    expected_effect_batch: str | None = None
    expected_review_at: str | None = None
    status: str = "todo"


class ActionItemPayload(BaseModel):
    id: int
    user_id: int
    product_id: int | None = None
    variant_id: int | None = None
    session_id: int | None = None
    source_product_id: str | None = None
    source_version: str | None = None
    source_batch_label: str | None = None
    title: str
    tag_name: str | None = None
    tag_type: str | None = None
    current_pct: float | None = None
    owner_role: str | None = None
    suggested_action: str | None = None
    expected_effect_batch: str | None = None
    expected_review_at: str | None = None
    status: str
    created_at: datetime | None = None
    parent_product_id: str | None = None
    product_name: str | None = None
    variant_sku: str | None = None
    child_asin: str | None = None


class ActionItemsResponse(BaseModel):
    items: list[ActionItemPayload]
    total: int


class ActionStatusUpdatePayload(BaseModel):
    status: str


class ReviewTrackerCreatePayload(BaseModel):
    action_item_id: int | None = None
    product_id: int | None = None
    variant_id: int | None = None
    tracker_title: str
    tag_name: str | None = None
    baseline_pct: float | None = None
    improvement_action: str | None = None
    effective_batch: str | None = None
    review_scope: str | None = None
    current_pct: float | None = None
    result_status: str = "pending"
    conclusion: str | None = None


class ReviewTrackerPayload(BaseModel):
    id: int
    user_id: int
    action_item_id: int | None = None
    product_id: int | None = None
    variant_id: int | None = None
    tracker_title: str
    tag_name: str | None = None
    baseline_pct: float | None = None
    improvement_action: str | None = None
    effective_batch: str | None = None
    review_scope: str | None = None
    current_pct: float | None = None
    result_status: str
    conclusion: str | None = None
    closed_at: datetime | None = None
    created_at: datetime | None = None
    action_title: str | None = None
    source_product_id: str | None = None
    source_version: str | None = None
    expected_review_at: str | None = None
    parent_product_id: str | None = None
    product_name: str | None = None
    variant_sku: str | None = None
    child_asin: str | None = None


class ReviewTrackersResponse(BaseModel):
    items: list[ReviewTrackerPayload]
    total: int


class ReviewTrackerUpdatePayload(BaseModel):
    review_scope: str | None = None
    current_pct: float | None = None
    result_status: str
    conclusion: str | None = None


class ReviewTrackerFromActionResponse(BaseModel):
    tracker: ReviewTrackerPayload
    action: ActionItemPayload
