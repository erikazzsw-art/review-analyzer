"""ASIN 监控列表 — 请求/响应 Schema。"""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field, field_validator


class AsinWatchlistCreate(BaseModel):
    """添加 ASIN 到监控列表（支持批量）。"""

    asins: list[str] = Field(..., min_length=1, max_length=20)
    marketplace: str = Field(default="us", pattern=r"^[a-z]{2}$")
    fetch_frequency: str = Field(default="daily", pattern=r"^(daily|weekly|manual)$")

    @field_validator("asins")
    @classmethod
    def validate_asins(cls, v: list[str]) -> list[str]:
        cleaned = []
        for asin in v:
            asin = asin.strip().upper()
            if not asin or len(asin) != 10 or not asin.startswith("B"):
                if not (len(asin) == 10 and asin.isalnum()):
                    raise ValueError(f"Invalid ASIN format: {asin}")
            cleaned.append(asin)
        return cleaned


class AsinWatchlistUpdate(BaseModel):
    """修改监控项设置。"""

    fetch_frequency: str | None = Field(default=None, pattern=r"^(daily|weekly|manual)$")
    status: str | None = Field(default=None, pattern=r"^(active|paused)$")


class AsinWatchlistItem(BaseModel):
    """单条监控项响应。"""

    id: int
    asin: str
    marketplace: str
    product_name: str | None = None
    product_id: int | None = None
    fetch_frequency: str
    last_fetched_at: datetime | None = None
    last_review_count: int = 0
    new_review_count: int = 0
    status: str
    error_message: str | None = None
    created_at: datetime


class AsinWatchlistResponse(BaseModel):
    """监控列表响应。"""

    items: list[AsinWatchlistItem]
    total: int
    quota_used: int
    quota_limit: int
