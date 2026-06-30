from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel, Field, model_validator


class AsinFetchRequest(BaseModel):
    platform: Literal["amazon", "aliexpress"] = "amazon"
    asin: str = Field(..., min_length=1, max_length=20)
    marketplace: str = Field(default="us", pattern=r"^[a-z]{2}$")
    product_name: str | None = None
    max_pages: int = Field(default=5, ge=1, le=10)
    fetch_all_variants: bool = False

    @model_validator(mode="after")
    def validate_product_code(self) -> AsinFetchRequest:
        if self.platform == "amazon":
            if not re.fullmatch(r"[A-Z0-9]{10}", self.asin):
                raise ValueError("Amazon ASIN 必须为 10 位字母数字组合")
        elif self.platform == "aliexpress":
            if not re.fullmatch(r"\d{12,16}", self.asin):
                raise ValueError("AliExpress Product ID 必须为 12-16 位数字")
        return self


class AsinFetchResponse(BaseModel):
    ok: bool = True
    job_id: int
    asin: str
    platform: str = "amazon"
    marketplace: str
    message: str
    variant_count: int | None = None
