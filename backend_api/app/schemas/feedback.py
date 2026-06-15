from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class FeedbackCreatePayload(BaseModel):
    feedback_type: Literal["bug", "feature", "general"]
    mood: Literal["frustrated", "idea", "love"]
    message: str | None = Field(None, max_length=500)
    page_path: str
    user_agent: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class FeedbackResponse(BaseModel):
    id: int
    feedback_type: str
    mood: str
    message: str | None
    page_path: str
    status: str
    created_at: datetime
