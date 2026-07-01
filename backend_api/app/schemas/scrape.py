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
