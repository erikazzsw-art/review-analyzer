from __future__ import annotations

from pydantic import BaseModel, Field


class AsinFetchRequest(BaseModel):
    asin: str = Field(..., min_length=10, max_length=10, pattern=r"^[A-Z0-9]{10}$")
    marketplace: str = Field(default="us", pattern=r"^[a-z]{2}$")
    product_name: str | None = None
    max_pages: int = Field(default=5, ge=1, le=10)


class AsinFetchResponse(BaseModel):
    ok: bool = True
    job_id: int
    asin: str
    marketplace: str
    message: str
