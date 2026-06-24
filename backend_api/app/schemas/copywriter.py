from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class CopywriterSessionPayload(BaseModel):
    session_id: int
    product_id: str
    version: str
    label: str
    total_reviews: int
    positive_count: int
    negative_count: int
    created_at: datetime


class CopywriterProductPayload(BaseModel):
    product_id: str
    product_name: str | None = None
    sessions: list[CopywriterSessionPayload] = Field(default_factory=list)


class CopywriterTypePayload(BaseModel):
    id: str
    name_zh: str
    name_en: str
    limit: int
    internal_estimate: bool = False


class CopywriterPlatformPayload(BaseModel):
    id: str
    name_zh: str
    name_en: str
    icon: str
    label_zh: str
    label_en: str
    sub: str
    types: list[CopywriterTypePayload] = Field(default_factory=list)
    prohibited: list[str] = Field(default_factory=list)
    guidelines_zh: str
    guidelines_en: str


class CopywriterStylePayload(BaseModel):
    name: str
    incompatible_on: list[str] = Field(default_factory=list)


class CopywriterGenerateRequest(BaseModel):
    product_id: str
    version: str | None = None
    range: str = "all"
    start: str | None = None
    end: str | None = None
    platform: str
    ad_type_id: str | None = None
    style: str = "简洁专业"
    n_variants: int = 1
    features_text: str = ""
    generate_ad_copy: bool = True
    generate_ideal_desc: bool = True
    force_regen_profile: bool = False


class CopywriterGeneratedItemPayload(BaseModel):
    type_id: str
    type_name: str
    limit: int
    style: str
    en: str
    zh: str
    char_count: int
    compliant: bool
    compliance_notes: list[str] = Field(default_factory=list)


class CopywriterIdealProfilePayload(BaseModel):
    features: list[str] = Field(default_factory=list)
    price_range: str = ""
    logistics: str = ""
    packaging: str = ""
    service: str = ""
    summary: str = ""
    cached: bool = False
    generated_at: datetime | None = None
    comment_count_at_generation: int = 0


class CopywriterVersionPayload(BaseModel):
    version: str
    review_count: int = 0
    last_analyzed_at: datetime | None = None


class CopywriterGenerateResponse(BaseModel):
    platform: CopywriterPlatformPayload
    review_summary: str = ""
    review_count: int = 0
    generated_items: list[CopywriterGeneratedItemPayload] = Field(default_factory=list)
    ideal_profile: CopywriterIdealProfilePayload | None = None
    generated_at: datetime
