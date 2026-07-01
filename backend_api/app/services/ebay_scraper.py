"""eBay 评论抓取 — Apify scrapier/ebay-review-scraper。

计费：$5.99 / 1,000 条（pay-per-event），共用 APIFY_API_TOKEN。
限制：eBay 评论无 1-5 星评分（仅 Positive/Neutral/Negative），无精确日期（仅相对时间）。
"""
from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx

logger = logging.getLogger(__name__)

EBAY_ACTOR_URL = "https://api.apify.com/v2/acts/scrapier~ebay-review-scraper/run-sync-get-dataset-items"

RATING_MAP: dict[str, int] = {
    "positive": 5,
    "neutral": 3,
    "negative": 1,
}


def _is_english(text: str) -> bool:
    if not text:
        return False
    ascii_count = sum(1 for c in text if c.isascii() and c.isprintable())
    return ascii_count / len(text) > 0.80


def _approx_date(date_range: str) -> str:
    """将 eBay 相对时间映射为近似日期 (YYYY-MM-DD)。"""
    now = datetime.now(timezone.utc)
    lower = date_range.lower().strip() if date_range else ""

    if "month" in lower and "6" not in lower:
        dt = now - timedelta(days=15)
    elif "6 month" in lower:
        dt = now - timedelta(days=90)
    elif "year" in lower:
        dt = now - timedelta(days=365)
    else:
        dt = now

    return dt.strftime("%Y-%m-%d")


async def fetch_ebay_reviews(
    item_id: str,
    *,
    max_reviews: int = 100,
    max_years: int = 2,
) -> list[dict[str, Any]]:
    """通过 Apify Actor 抓取 eBay 评论。"""
    token = os.getenv("APIFY_API_TOKEN", "").strip()
    if not token:
        logger.debug("APIFY_API_TOKEN not set, cannot fetch eBay reviews")
        return []

    url = f"https://www.ebay.com/itm/{item_id}"
    payload = {
        "ebayProductUrls": [url],
        "maxReviewsPerUrl": max_reviews,
        "sortReviewsBy": "TIME",
    }

    try:
        async with httpx.AsyncClient(timeout=180.0) as client:
            resp = await client.post(
                EBAY_ACTOR_URL,
                params={"token": token},
                json=payload,
            )
            if resp.status_code not in (200, 201):
                logger.warning(
                    "eBay Apify Actor returned %d for item %s: %s",
                    resp.status_code, item_id, resp.text[:200],
                )
                return []

            items = resp.json()
            if not isinstance(items, list):
                logger.warning("eBay Apify response is not a list for item %s", item_id)
                return []

    except (httpx.HTTPError, httpx.TimeoutException) as exc:
        logger.warning("eBay Apify request failed for item %s: %s", item_id, exc)
        return []

    reviews: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()

    for raw in items:
        content = (raw.get("ReviewComment") or "").strip()
        if not content or not _is_english(content):
            continue

        rating_type = (raw.get("ReviewRatingType") or "").lower()
        rating = 5
        for key, val in RATING_MAP.items():
            if key in rating_type:
                rating = val
                break

        date_range = raw.get("ReviewDateRange") or ""
        date_str = _approx_date(date_range)

        reviewer = (raw.get("ReviewerName") or "Anonymous").strip()
        verified = "verified" in (raw.get("IsVerifiedPurchase") or "").lower()

        dedup_key = (content[:80], reviewer)
        if dedup_key in seen:
            continue
        seen.add(dedup_key)

        reviews.append({
            "content": content,
            "rating": rating,
            "date": date_str,
            "reviewer": reviewer,
            "title": "",
            "verified_purchase": verified,
            "reviewer_id": "",
            "review_id": "",
            "sku_info": "",
        })

    logger.info("eBay Apify: fetched %d reviews for item %s", len(reviews), item_id)
    return reviews
