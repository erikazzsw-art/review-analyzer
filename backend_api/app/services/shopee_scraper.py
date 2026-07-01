"""Shopee 评论抓取 — 双数据源自动 fallback。

主数据源：Apify zen-studio/shopee-product-reviews-scraper（付费，稳定）
备用数据源：Shopee 公开 Ratings API v2（免费，可能被反爬封锁）
"""
from __future__ import annotations

import asyncio
import logging
import os
import random
import re
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx

logger = logging.getLogger(__name__)

APIFY_ACTOR_URL = "https://api.apify.com/v2/acts/zen-studio~shopee-product-reviews-scraper/run-sync-get-dataset-items"

SHOPEE_DOMAINS: dict[str, str] = {
    "sg": "shopee.sg",
    "th": "shopee.co.th",
}

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:128.0) Gecko/20100101 Firefox/128.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
]

MAX_RETRIES = 3


def _is_within_years(date_str: str, years: int = 2) -> bool:
    if not date_str:
        return True
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        cutoff = datetime.now(timezone.utc) - timedelta(days=years * 365)
        return dt >= cutoff
    except ValueError:
        return True


def _is_english(text: str) -> bool:
    if not text:
        return False
    ascii_count = sum(1 for c in text if c.isascii() and c.isprintable())
    return ascii_count / len(text) > 0.80


async def _fetch_via_apify(
    item_id: str,
    shop_id: str,
    *,
    region: str = "sg",
    max_reviews: int = 200,
    max_years: int = 2,
) -> list[dict[str, Any]]:
    """通过 Apify Actor 抓取 Shopee 评论（主数据源）。"""
    token = os.getenv("APIFY_API_TOKEN", "").strip()
    if not token:
        logger.debug("APIFY_API_TOKEN not set, skipping Apify source")
        return []

    domain = SHOPEE_DOMAINS.get(region, "shopee.sg")
    product_url = f"https://{domain}/product-i.{shop_id}.{item_id}"

    payload = {
        "productUrls": [product_url],
        "maxReviewsPerProduct": max_reviews,
        "sortBy": "recent",
    }

    try:
        async with httpx.AsyncClient(timeout=180.0) as client:
            resp = await client.post(
                APIFY_ACTOR_URL,
                params={"token": token},
                json=payload,
            )
            if resp.status_code not in (200, 201):
                logger.warning(
                    "Apify Shopee Actor returned %d for item %s: %s",
                    resp.status_code, item_id, resp.text[:200],
                )
                return []

            items = resp.json()
            if not isinstance(items, list):
                logger.warning("Apify Shopee response is not a list for item %s", item_id)
                return []

    except (httpx.HTTPError, httpx.TimeoutException) as exc:
        logger.warning("Apify Shopee request failed for item %s: %s", item_id, exc)
        return []

    reviews: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()

    for raw in items:
        content = (raw.get("comment") or raw.get("reviewText") or "").strip()
        if not content or not _is_english(content):
            continue

        rating = raw.get("rating_star") or raw.get("rating") or 5
        date_str = ""
        mtime = raw.get("mtime") or raw.get("timestamp")
        if mtime and isinstance(mtime, (int, float)):
            date_str = datetime.fromtimestamp(mtime, tz=timezone.utc).strftime("%Y-%m-%d")
        elif isinstance(mtime, str):
            match = re.search(r"\d{4}-\d{2}-\d{2}", mtime)
            if match:
                date_str = match.group(0)

        if not _is_within_years(date_str, max_years):
            continue

        reviewer = raw.get("author_username") or raw.get("username") or ""
        dedup_key = (content[:80], reviewer)
        if dedup_key in seen:
            continue
        seen.add(dedup_key)

        sku_info = ""
        product_items = raw.get("product_items") or []
        if product_items and isinstance(product_items, list):
            model_name = product_items[0].get("model_name", "")
            if model_name:
                sku_info = model_name

        reviews.append({
            "content": content,
            "rating": min(max(int(rating), 1), 5),
            "date": date_str,
            "reviewer": reviewer,
            "title": "",
            "verified_purchase": True,
            "reviewer_id": "",
            "review_id": str(raw.get("cmtid") or raw.get("id") or ""),
            "sku_info": sku_info,
        })

    logger.info("Apify Shopee: fetched %d reviews for item %s", len(reviews), item_id)
    return reviews


async def _fetch_via_api(
    item_id: str,
    shop_id: str,
    *,
    region: str = "sg",
    max_pages: int = 5,
    max_years: int = 2,
) -> list[dict[str, Any]]:
    """通过 Shopee 公开 Ratings API v2 抓取评论（备用数据源）。"""
    domain = SHOPEE_DOMAINS.get(region, "shopee.sg")
    base_url = f"https://{domain}/api/v2/item/get_ratings"

    headers = {
        "User-Agent": random.choice(USER_AGENTS),
        "Referer": f"https://{domain}/product-i.{shop_id}.{item_id}",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.9",
    }

    seen: set[tuple[str, str]] = set()
    all_reviews: list[dict[str, Any]] = []

    async with httpx.AsyncClient(timeout=20.0, headers=headers) as client:
        for page in range(max_pages):
            params = {
                "filter": "0",
                "flag": "1",
                "itemid": item_id,
                "shopid": shop_id,
                "limit": "20",
                "offset": str(page * 20),
                "type": "0",
            }

            for attempt in range(MAX_RETRIES):
                try:
                    resp = await client.get(base_url, params=params)
                    if resp.status_code in (429, 503):
                        wait = (attempt + 1) * 3
                        logger.warning(
                            "Shopee API rate limited (page=%d), retrying in %ds", page, wait
                        )
                        await asyncio.sleep(wait)
                        continue
                    if resp.status_code in (403, 404):
                        logger.warning(
                            "Shopee API returned %d for item %s, stopping", resp.status_code, item_id
                        )
                        return all_reviews
                    break
                except httpx.HTTPError:
                    if attempt < MAX_RETRIES - 1:
                        await asyncio.sleep((attempt + 1) * 2)
                        continue
                    logger.warning("Shopee API request failed for item %s page %d", item_id, page)
                    return all_reviews
            else:
                return all_reviews

            if resp.status_code != 200:
                break

            try:
                data = resp.json()
            except Exception:
                break

            # 错误码 90309999 = 需要 cookie / bot 检测
            if data.get("error") or (isinstance(data.get("error"), int) and data["error"] != 0):
                logger.warning(
                    "Shopee API returned error code for item %s: %s", item_id, data.get("error")
                )
                break

            rating_list = (data.get("data") or {}).get("ratings") or []
            if not rating_list:
                break

            for raw in rating_list:
                content = (raw.get("comment") or "").strip()
                if not content or not _is_english(content):
                    continue

                rating = raw.get("rating_star") or 5
                date_str = ""
                mtime = raw.get("mtime")
                if mtime and isinstance(mtime, (int, float)):
                    date_str = datetime.fromtimestamp(mtime, tz=timezone.utc).strftime("%Y-%m-%d")

                if not _is_within_years(date_str, max_years):
                    continue

                reviewer = raw.get("author_username") or str(raw.get("userid", ""))
                dedup_key = (content[:80], reviewer)
                if dedup_key in seen:
                    continue
                seen.add(dedup_key)

                sku_info = ""
                product_items = raw.get("product_items") or []
                if product_items and isinstance(product_items, list):
                    model_name = product_items[0].get("model_name", "")
                    if model_name:
                        sku_info = model_name

                all_reviews.append({
                    "content": content,
                    "rating": min(max(int(rating), 1), 5),
                    "date": date_str,
                    "reviewer": reviewer,
                    "title": "",
                    "verified_purchase": True,
                    "reviewer_id": str(raw.get("userid", "")),
                    "review_id": str(raw.get("cmtid") or ""),
                    "sku_info": sku_info,
                })

            await asyncio.sleep(random.uniform(1.0, 3.0))

    logger.info("Shopee API: fetched %d reviews for item %s", len(all_reviews), item_id)
    return all_reviews


async def fetch_shopee_reviews(
    item_id: str,
    shop_id: str,
    *,
    region: str = "sg",
    max_pages: int = 5,
    max_years: int = 2,
) -> list[dict[str, Any]]:
    """Shopee 评论抓取统一入口 — 先 Apify，失败则 fallback 公开 API。"""
    reviews = await _fetch_via_apify(
        item_id, shop_id, region=region, max_reviews=max_pages * 20, max_years=max_years
    )

    if reviews:
        logger.info("Using Apify source: %d reviews for Shopee item %s", len(reviews), item_id)
        return reviews

    logger.info("Apify returned 0 reviews for Shopee item %s, trying public API", item_id)
    reviews = await _fetch_via_api(
        item_id, shop_id, region=region, max_pages=max_pages, max_years=max_years
    )

    if not reviews:
        logger.warning("No reviews found for Shopee item %s via any source", item_id)

    return reviews
