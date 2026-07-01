"""定时自动抓取评论 — 请求/响应 Schema。"""
from __future__ import annotations

import re
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, model_validator

AMAZON_MARKETPLACES = ("us", "uk", "ca", "au")
SHOPEE_REGIONS = ("sg", "th")


class AsinWatchlistCreate(BaseModel):
    """添加产品编码到定时抓取（支持批量）。"""

    platform: Literal["amazon", "aliexpress", "ebay", "walmart", "shopee"] = "amazon"
    product_ids: list[str] = Field(..., min_length=1, max_length=20)
    marketplace: str = Field(default="us")
    fetch_frequency: str = Field(default="daily", pattern=r"^(daily|weekly|manual)$")

    @model_validator(mode="after")
    def validate_platform_fields(self) -> AsinWatchlistCreate:
        if self.platform == "amazon":
            if self.marketplace not in AMAZON_MARKETPLACES:
                raise ValueError(
                    f"Amazon marketplace must be one of {AMAZON_MARKETPLACES}"
                )
            cleaned = []
            for pid in self.product_ids:
                pid = pid.strip().upper()
                if not pid or len(pid) != 10 or not pid.isalnum():
                    raise ValueError(f"Invalid ASIN format: {pid}")
                cleaned.append(pid)
            self.product_ids = cleaned
        elif self.platform == "aliexpress":
            self.marketplace = "global"
            cleaned = []
            for pid in self.product_ids:
                pid = pid.strip()
                if not re.match(r"^\d{8,15}$", pid):
                    raise ValueError(f"Invalid AliExpress product ID: {pid}")
                cleaned.append(pid)
            self.product_ids = cleaned
        elif self.platform == "shopee":
            if self.marketplace not in SHOPEE_REGIONS:
                self.marketplace = "sg"
            cleaned = []
            for pid in self.product_ids:
                pid = pid.strip()
                if not re.match(r"^\d{5,15}\.\d{5,15}$", pid):
                    raise ValueError(f"Invalid Shopee product code: {pid} (格式：商品ID.店铺ID)")
                cleaned.append(pid)
            self.product_ids = cleaned
        elif self.platform == "ebay":
            self.marketplace = "global"
            cleaned = []
            for pid in self.product_ids:
                pid = pid.strip()
                if not re.match(r"^\d{9,15}$", pid):
                    raise ValueError(f"Invalid eBay Item Number: {pid}")
                cleaned.append(pid)
            self.product_ids = cleaned
        elif self.platform == "walmart":
            self.marketplace = "us"
            cleaned = []
            for pid in self.product_ids:
                pid = pid.strip()
                if not re.match(r"^[A-Za-z0-9]{6,13}$", pid):
                    raise ValueError(f"Invalid Walmart Product ID: {pid}")
                cleaned.append(pid)
            self.product_ids = cleaned
        return self


class AsinWatchlistUpdate(BaseModel):
    """修改监控项设置。"""

    fetch_frequency: str | None = Field(default=None, pattern=r"^(daily|weekly|manual)$")
    status: str | None = Field(default=None, pattern=r"^(active|paused)$")


class AsinWatchlistItem(BaseModel):
    """单条监控项响应。"""

    id: int
    platform: str = "amazon"
    asin: str
    marketplace: str
    product_name: str | None = None
    product_id: int | None = None
    fetch_frequency: str
    last_fetched_at: datetime | None = None
    last_review_count: int = 0
    new_review_count: int = 0
    status: str
    hint_message: str | None = None
    created_at: datetime


class AsinWatchlistResponse(BaseModel):
    """定时抓取列表响应。"""

    items: list[AsinWatchlistItem]
    total: int
    quota_used: int
    quota_limit: int
