"""Golden Set schemas."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class GoldenSetItem(BaseModel):
    """单条标注项（上传表格中的一行）."""

    comment_text: str
    aspect_key: str
    is_correct: bool
    reason: str | None = None
    correct_tag: str | None = None


class GoldenSetUpload(BaseModel):
    """批量上传请求体."""

    items: list[GoldenSetItem]
    sub_category: str = "家具家居"


class GoldenSetOut(BaseModel):
    """返回给前端的单条记录."""

    id: int
    comment_text: str
    aspect_key: str
    is_correct: bool
    reason: str | None
    correct_tag: str | None
    sub_category: str
    source: str
    use_as_fewshot: bool
    batch_id: str | None
    created_at: datetime


class AccuracyStat(BaseModel):
    """单标签准确率统计."""

    aspect_key: str
    total: int
    correct_count: int
    incorrect_count: int
    accuracy_pct: float | None
