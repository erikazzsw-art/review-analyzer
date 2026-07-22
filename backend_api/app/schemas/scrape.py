from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel, Field, model_validator


class AsinFetchRequest(BaseModel):
    platform: Literal["amazon", "aliexpress", "ebay", "walmart", "shopee"] = "amazon"
    asin: str = Field(..., min_length=1, max_length=31)
    marketplace: str = Field(default="us", pattern=r"^[a-z]{2}$")
    product_name: str | None = None
    max_pages: int = Field(default=5, ge=1, le=10)
    fetch_all_variants: bool = False
    max_reviews: int = Field(default=100, ge=1, le=500)
    force_refresh: bool = False

    @model_validator(mode="after")
    def validate_product_code(self) -> AsinFetchRequest:
        if self.platform == "amazon":
            if not re.fullmatch(r"[A-Z0-9]{10}", self.asin):
                raise ValueError("Amazon ASIN 必须为 10 位字母数字组合")
        elif self.platform == "aliexpress":
            if not re.fullmatch(r"\d{12,16}", self.asin):
                raise ValueError("AliExpress Product ID 必须为 12-16 位数字")
        elif self.platform == "shopee":
            if not re.fullmatch(r"\d{5,15}\.\d{5,15}", self.asin):
                raise ValueError("Shopee 产品编码格式：商品ID.店铺ID（如 23388006672.673355029）")
        elif self.platform == "ebay":
            if not re.fullmatch(r"\d{9,15}", self.asin):
                raise ValueError("eBay Item Number 必须为 9-15 位数字")
        elif self.platform == "walmart":
            if not re.fullmatch(r"[A-Za-z0-9]{6,13}", self.asin):
                raise ValueError("Walmart Product ID 必须为 6-13 位字母数字")
        return self


class AsinFetchResponse(BaseModel):
    ok: bool = True
    job_id: int
    asin: str
    platform: str = "amazon"
    marketplace: str
    message: str
    variant_count: int | None = None


# ── Step 15: Chrome 扩展插件上传 ──

class PluginReviewItem(BaseModel):
    """单条插件抓取的评论。"""
    review_id: str
    asin: str | None = Field(default=None, max_length=31, description="解析后的评论归属 ASIN")
    page_asin: str | None = Field(default=None, max_length=31, description="评论页 URL 中的 ASIN")
    review_variant_asin: str | None = Field(default=None, max_length=31, description="评论规格链接中的子 ASIN")
    variant_label: str | None = Field(default=None, max_length=255, description="评论规格文本，如 Color/Size")
    asin_match_source: str | None = Field(default=None, max_length=64, description="ASIN 匹配来源")
    body: str = Field(..., min_length=1, description="评论正文")
    rating: float | None = None
    date: str = Field(..., description="评论日期字符串")
    date_iso: str | None = Field(default=None, description="可选 ISO 日期，用于全局评论池 2 年保留窗口")
    reviewer: str | None = None
    title: str | None = None
    verified: bool | None = None
    helpful_count: int | None = None


class PluginUploadRequest(BaseModel):
    """Chrome 扩展直传评论的请求体。"""
    asin: str = Field(..., min_length=1, max_length=31, description="Amazon ASIN")
    marketplace: str = Field(default="us", pattern=r"^[a-z]{2}$")
    platform: str = Field(default="amazon", description="平台标识")
    product_name: str | None = None
    page_url: str | None = None
    reviews: list[PluginReviewItem] = Field(..., min_length=1, max_length=5000)


class PluginUploadResponse(BaseModel):
    ok: bool = True
    job_id: int
    asin: str
    marketplace: str
    total_received: int
    new_reviews: int
    duplicate_count: int
    message: str
