from __future__ import annotations

import re
from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator

_EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


def _validate_password_strength(password: str) -> str:
    if not re.search(r"[a-zA-Z]", password):
        raise ValueError("Password must contain at least one letter")
    if not re.search(r"[0-9]", password):
        raise ValueError("Password must contain at least one number")
    if not re.search(r"[^a-zA-Z0-9]", password):
        raise ValueError("Password must contain at least one special character")
    if not re.search(r"[A-Z]", password):
        raise ValueError("Password must contain at least one uppercase letter")
    return password


class MeUpdateRequest(BaseModel):
    current_password: str = Field(min_length=6, max_length=128)
    username: str | None = Field(default=None, min_length=2, max_length=64)
    email: str | None = Field(default=None, min_length=3, max_length=255)
    new_password: str | None = Field(default=None, min_length=6, max_length=128)

    @field_validator("email")
    @classmethod
    def email_shape(cls, v: str | None) -> str | None:
        if v is None:
            return v
        candidate = v.strip()
        if not _EMAIL_RE.match(candidate):
            raise ValueError("Email format is invalid")
        return candidate

    @field_validator("new_password")
    @classmethod
    def password_strength(cls, v: str | None) -> str | None:
        if v is None:
            return v
        return _validate_password_strength(v)

    @model_validator(mode="after")
    def at_least_one_field(self) -> MeUpdateRequest:
        if not any((self.username, self.email, self.new_password)):
            raise ValueError("At least one of username / email / new_password must be provided")
        return self


class MeDeleteRequest(BaseModel):
    current_password: str = Field(min_length=6, max_length=128)
    confirm: str = Field(min_length=1, max_length=32)

    @field_validator("confirm")
    @classmethod
    def must_match_phrase(cls, v: str) -> str:
        candidate = v.strip()
        if candidate.upper() != "DELETE":
            raise ValueError('Confirm phrase must be exactly "DELETE"')
        return candidate


class MeExportUser(BaseModel):
    id: int
    username: str
    email: str = ""
    plan: str = "free"
    paddle_customer_id: str | None = None
    created_at: str | None = None
    updated_at: str | None = None


class MeExportPayload(BaseModel):
    exported_at: str
    schema_version: str = "1.0"
    user: MeExportUser
    subscription: dict[str, Any] | None = None
    sessions: list[dict[str, Any]] = Field(default_factory=list)
    products: list[dict[str, Any]] = Field(default_factory=list)
    product_variants: list[dict[str, Any]] = Field(default_factory=list)
    comments_count: int = 0
    actions: list[dict[str, Any]] = Field(default_factory=list)
    trackers: list[dict[str, Any]] = Field(default_factory=list)
    settings: list[dict[str, Any]] = Field(default_factory=list)
    asin_watchlist: list[dict[str, Any]] = Field(default_factory=list)


class MeMessageResponse(BaseModel):
    ok: bool = True
    message: str
