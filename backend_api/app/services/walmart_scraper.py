"""Walmart 评论抓取 — Apify webscrapewizard/walmart-review-crawler。

计费：$6.00 / 1,000 条（pay-per-event），共用 APIFY_API_TOKEN。
注意：Actor 文档未提供精确输出字段名，字段映射基于文档描述推断，
     首次运行时通过日志确认实际字段名并调整。
"""
from __future__ import annotations

import logging
import os
import re
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx

logger = logging.getLogger(__name__)

WALMART_ACTOR_URL = "https://api.apify.com/v2/acts/webscrapewizard~walmart-review-crawler/run-sync-get-dataset-items"


def _is_english(text: str) -> bool:
    if not text:
        return False
    ascii_count = sum(1 for c in text if c.isascii() and c.isprintable())
    return ascii_count / len(text) > 0.80


def _is_within_years(date_str: str, years: int = 2) -> bool:
    if not date_str:
        return True
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        cutoff = datetime.now(timezone.utc) - timedelta(days=years * 365)
        return dt >= cutoff
    except ValueError:
        return True


def _extract_date(raw_date: str) -> str:
    """尝试从多种日期格式中提取 YYYY-MM-DD。"""
    if not raw_date:
        return ""
    match = re.search(r"\d{4}-\d{2}-\d{2}", raw_date)
    if match:
        return match.group(0)
    for fmt in ("%m/%d/%Y", "%B %d, %Y", "%b %d, %Y", "%d %b %Y", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(raw_date.strip()[:19], fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return ""


def _get_field(raw: dict, *keys: str) -> str:
    """尝试多个可能的字段名，返回第一个有值的。"""
    for k in keys:
        val = raw.get(k)
        if val is not None:
            return str(val).strip()
    return ""


async def fetch_walmart_reviews(
    item_id: str,
    *,
    max_reviews: int = 100,
    max_years: int = 2,
) -> list[dict[str, Any]]:
    """通过 Apify Actor 抓取 Walmart 评论。"""
    token = os.getenv("APIFY_API_TOKEN", "").strip()
    if not token:
        logger.debug("APIFY_API_TOKEN not set, cannot fetch Walmart reviews")
        return []

    payload = {
        "start_urls": [{"url": f"https://www.walmart.com/reviews/product/{item_id}"}],
        "max_depth": 1,
    }

    try:
        async with httpx.AsyncClient(timeout=180.0) as client:
            resp = await client.post(
                WALMART_ACTOR_URL,
                params={"token": token},
                json=payload,
            )
            if resp.status_code not in (200, 201):
                logger.warning(
                    "Walmart Apify Actor returned %d for item %s: %s",
                    resp.status_code, item_id, resp.text[:200],
                )
                return []

            items = resp.json()
            if not isinstance(items, list):
                logger.warning("Walmart Apify response is not a list for item %s", item_id)
                return []

    except (httpx.HTTPError, httpx.TimeoutException) as exc:
        logger.warning("Walmart Apify request failed for item %s: %s", item_id, exc)
        return []

    if items:
        logger.info(
            "Walmart raw response sample keys for item %s: %s",
            item_id, list(items[0].keys())[:20],
        )

    reviews: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()

    for raw in items:
        content = _get_field(
            raw, "reviewText", "review_text", "text", "comment", "reviewComment", "comments"
        )
        if not content or not _is_english(content):
            continue

        rating_str = _get_field(raw, "rating", "reviewRating", "review_rating", "stars", "starRating")
        try:
            rating = int(float(rating_str))
            rating = max(1, min(5, rating))
        except (ValueError, TypeError):
            rating = 5

        raw_date = _get_field(
            raw, "submissionTime", "date", "reviewDate", "review_date", "publicationDate", "datePublished"
        )
        date_str = _extract_date(raw_date)

        if not _is_within_years(date_str, max_years):
            continue

        reviewer = _get_field(raw, "authorName", "author", "reviewer", "userName", "username") or "Anonymous"
        title = _get_field(raw, "title", "reviewTitle", "review_title", "headline")
        review_id = _get_field(raw, "reviewId", "review_id", "id")

        dedup_key = (content[:80], reviewer)
        if dedup_key in seen:
            continue
        seen.add(dedup_key)

        reviews.append({
            "content": content,
            "rating": rating,
            "date": date_str,
            "reviewer": reviewer,
            "title": title,
            "verified_purchase": True,
            "reviewer_id": "",
            "review_id": review_id,
            "sku_info": "",
        })

    logger.info("Walmart Apify: fetched %d reviews for item %s", len(reviews), item_id)
    return reviews
