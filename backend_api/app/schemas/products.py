from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class ProductVariantPayload(BaseModel):
    id: int | None = None
    user_id: int | None = None
    product_id: int | None = None
    variant_sku: str | None = None
    child_asin: str | None = None
    color: str | None = None
    size: str | None = None
    style: str | None = None
    material: str | None = None
    status: str | None = None
    launched_at: str | None = None
    created_at: datetime | None = None


class ProductVersionPayload(BaseModel):
    id: int | None = None
    user_id: int | None = None
    product_id: int | None = None
    variant_id: int | None = None
    version_name: str | None = None
    version_notes: str | None = None
    change_summary: str | None = None
    launched_at: str | None = None
    is_current: bool | None = None
    created_at: datetime | None = None


class ProductOverviewPayload(BaseModel):
    id: int | None = None
    parent_product_id: str
    name: str | None = None
    platform: str | None = None
    category: str | None = None
    lifecycle_stage: str | None = None
    current_version: str
    core_selling_points: str | None = None
    main_competitors: str | None = None
    owner_role: str | None = None
    production_cycle_days: int | None = None
    is_archived_from_sessions: bool
    review_count: int
    positive_rate: float
    negative_rate: float
    top_issue: str | None = None
    top_highlight: str | None = None
    variant_count: int
    variants: list[ProductVariantPayload]
    versions: list[ProductVersionPayload]
    session_count: int
    pending_review_count: int
    latest_session_label: str | None = None
    latest_updated_at: datetime | None = None
    latest_review_date: str | None = None


class ProductsResponsePayload(BaseModel):
    items: list[ProductOverviewPayload]
    total: int
    generated_at: datetime


class ProductSearchItem(BaseModel):
    parent_product_id: str
    name: str | None = None
    review_count: int = 0
    session_count: int = 0
    latest_session_id: int | None = None


class ProductSearchResponse(BaseModel):
    items: list[ProductSearchItem]
    total: int
    query: str = ""


class ProductVersionItem(BaseModel):
    """sessions 表里某产品已用过的版本（V1/V2/...），含评论汇总。"""
    version: str
    review_count: int = 0
    last_analyzed_at: datetime | None = None


class ProductVersionsResponse(BaseModel):
    items: list[ProductVersionItem]
    total: int
    product_id: str
