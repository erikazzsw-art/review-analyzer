from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    """Runtime settings for the API shell."""

    app_name: str
    app_env: str
    session_secret: str
    access_cookie_name: str
    refresh_cookie_name: str
    access_ttl_seconds: int
    refresh_ttl_seconds: int
    cookie_secure: bool
    cookie_domain: str | None
    redis_url: str
    rq_queue_name: str
    rq_job_timeout_seconds: int


def get_settings() -> Settings:
    raw_secret = (
        os.getenv("API_SESSION_SECRET")
        or os.getenv("AES_SECRET_KEY")
        or "clueai-dev-session-secret-change-me"
    )
    cookie_domain = os.getenv("API_COOKIE_DOMAIN", "").strip() or None
    return Settings(
        app_name="ClueAI Backend API",
        app_env=os.getenv("API_ENV", "development"),
        session_secret=raw_secret,
        access_cookie_name=os.getenv("API_ACCESS_COOKIE_NAME", "clueai_access"),
        refresh_cookie_name=os.getenv("API_REFRESH_COOKIE_NAME", "clueai_refresh"),
        access_ttl_seconds=int(os.getenv("API_ACCESS_TTL_SECONDS", "3600")),
        refresh_ttl_seconds=int(os.getenv("API_REFRESH_TTL_SECONDS", "1209600")),
        cookie_secure=os.getenv("API_COOKIE_SECURE", "false").lower() == "true",
        cookie_domain=cookie_domain,
        redis_url=os.getenv("REDIS_URL")
        or os.getenv("RQ_REDIS_URL")
        or "redis://localhost:6379/0",
        rq_queue_name=os.getenv("RQ_QUEUE_NAME", "clueai"),
        rq_job_timeout_seconds=int(os.getenv("RQ_JOB_TIMEOUT_SECONDS", "1800")),
    )
