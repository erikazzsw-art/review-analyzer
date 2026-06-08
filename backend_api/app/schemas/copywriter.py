from __future__ import annotations

from datetime import datetime
from typing import Any

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


class CopywriterGenerateRequest(BaseModel):
    product_session_ids: list[int] = Field(default_factory=list)
    platform: str
    features_text: str = ""
    generate_ad_copy: bool = True
    generate_ideal_desc: bool = True
    style_by_type: dict[str, str] = Field(default_factory=dict)


class CopywriterGeneratedItemPayload(BaseModel):
    type_id: str
    type_name: str
    limit: int
    style: str
    en: str
    zh: str
    char_count: int
    compliant: bool


class CopywriterIdealProfilePayload(BaseModel):
    features: list[str] = Field(default_factory=list)
    price_range: str = ""
    logistics: str = ""
    packaging: str = ""
    service: str = ""
    summary: str = ""


class CopywriterGenerateResponse(BaseModel):
    platform: CopywriterPlatformPayload
    selected_sessions: list[CopywriterSessionPayload] = Field(default_factory=list)
    review_summary: str = ""
    generated_items: list[CopywriterGeneratedItemPayload] = Field(default_factory=list)
    ideal_profile: CopywriterIdealProfilePayload | None = None
    generated_at: datetime
