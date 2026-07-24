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
    image_url: str | None = None
    name: str | None = None
    brand: str | None = None
    price: float | None = None
    price_currency: str | None = None
    sales_volume: int | None = None
    sales_revenue: float | None = None
    is_fba: bool | None = None
    listing_date: str | None = None
    review_count: int = 0
    latest_review_date: str | None = None


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
    session_versions: list[str] = []
    version_date_ranges: dict[str, dict[str, str | None]] = {}
    session_count: int
    pending_review_count: int
    latest_session_label: str | None = None
    latest_updated_at: datetime | None = None
    latest_review_date: str | None = None
    earliest_review_date: str | None = None
    image_url: str | None = None
    brand: str | None = None
    rating: float | None = None
    ratings_total: int | None = None
    reviews_total: int | None = None


class ProductsResponsePayload(BaseModel):
    items: list[ProductOverviewPayload]
    total: int
    generated_at: datetime


class ProductSearchVariantItem(BaseModel):
    child_asin: str
    name: str | None = None


class ProductSearchItem(BaseModel):
    id: int | None = None
    parent_product_id: str
    name: str | None = None
    variant_asins: list[str] = []
    variants: list[ProductSearchVariantItem] = []
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


# ── Step 11.5: Chrome 插件 Listing 上传 ──

class ListingDataPayload(BaseModel):
    """产品 listing 详情（由 Chrome 扩展抓取）。"""
    title: str | None = None
    price: float | None = None
    price_currency: str = "USD"
    original_price: float | None = None
    rating: float | None = None
    brand: str | None = None
    bullet_points: list[str] = []
    main_image_url: str | None = None
    description: str | None = None
    best_seller_rank: list[dict[str, object]] = []
    dimensions: str | None = None
    weight: str | None = None
    seller_name: str | None = None
    availability: str | None = None


class VariantPayload(BaseModel):
    """单个变体 ASIN + 属性。"""
    asin: str
    color: str | None = None
    size: str | None = None
    style: str | None = None
    material: str | None = None


class PluginListingUploadRequest(BaseModel):
    """Chrome 插件上传产品 listing 请求。"""
    parent_asin: str
    name: str  # 用户在 popup 中填写的产品名称（必填）
    marketplace: str = "us"
    platform: str = "amazon"
    listing: ListingDataPayload | None = None
    variants: list[VariantPayload] = []


class PluginListingUploadResponse(BaseModel):
    """Chrome 插件上传产品 listing 响应。"""
    product_id: int
    variant_count: int
    listing_updated: bool
    message: str
