"""Calibration API schemas."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class CalibrationCreate(BaseModel):
    comment_id: int | None = None
    session_id: str | None = None
    original_tag: str
    correct_tag: str | None = None
    note: str | None = None
    sub_category: str = "家具家居"


class CalibrationOut(BaseModel):
    id: int
    original_tag: str
    correct_tag: str | None
    note: str | None
    sub_category: str
    created_at: datetime
