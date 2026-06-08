from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class PushRulePayload(BaseModel):
    issue_pct_enabled: bool = True
    issue_pct_threshold: int = 5
    neg_rate_enabled: bool = True
    neg_rate_threshold: int = 25
    neg_rate_compare_enabled: bool = True
    neg_rate_compare_threshold: int = 5
    neg_rate_compare_window: str = "30"
    neg_rate_compare_version: str = "same_version"
    issue_compare_enabled: bool = False
    issue_compare_threshold: int = 3
    issue_compare_window: str = "30"
    issue_compare_version: str = "same_version"
    highlight_pct_enabled: bool = False
    highlight_pct_threshold: int = 10
    highlight_compare_enabled: bool = False
    highlight_compare_threshold: int = 5
    highlight_compare_window: str = "30"
    highlight_compare_version: str = "same_version"
    auto_push_new_batch: bool = False


class ProductRulePayload(BaseModel):
    product_id: str
    name: str | None = None
    issue_pct: int = 5
    neg_rate: int = 25
    hl_pct: int = 10
    enabled: bool = True
    compare_window: str | None = None
    compare_version: str | None = None


class SettingsPayload(BaseModel):
    webhook_url: str = ""
    webhook_secret: str = ""
    webhook_group_name: str = ""
    api_key: str = ""
    rules: PushRulePayload = Field(default_factory=PushRulePayload)
    product_rules: list[ProductRulePayload] = Field(default_factory=list)
    billing: dict[str, Any] = Field(default_factory=dict)
    generated_at: datetime | None = None


class SettingsUpdatePayload(BaseModel):
    webhook_url: str = ""
    webhook_secret: str = ""
    webhook_group_name: str = ""
    api_key: str = ""
    rules: PushRulePayload = Field(default_factory=PushRulePayload)
    product_rules: list[ProductRulePayload] = Field(default_factory=list)


class BillingCheckoutPayload(BaseModel):
    success_url: str | None = None


class BillingCheckoutResponse(BaseModel):
    checkout_html: str
    configured: bool
    plan: str


class BillingWebhookPayload(BaseModel):
    event_type: str = ""
    customer_id: str | None = None
    user_id: int | None = None
    plan: str = "pro"
    raw_payload: dict[str, Any] = Field(default_factory=dict)
    signature: str | None = None


class BillingWebhookResponse(BaseModel):
    ok: bool = True
    message: str
