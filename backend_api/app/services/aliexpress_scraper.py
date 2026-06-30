"""AliExpress 评论抓取 — 三级数据源自动 fallback。

主数据源：Apify CrowdPull AliExpress Reviews Scraper（付费，稳定）
备用数据源 1：feedback.aliexpress.com AJAX API（免费，可能被反爬封锁）
备用数据源 2：Playwright 无头浏览器抓取（最后兜底）
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

FEEDBACK_URL = "https://feedback.aliexpress.com/pc/searchEvaluation.do"
APIFY_ACTOR_URL = "https://api.apify.com/v2/acts/crowdpull~aliexpress-reviews-scraper/run-sync-get-dataset-items"

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
    """ASCII 比例 >80% 判定为英文。"""
    if not text:
        return False
    ascii_count = sum(1 for c in text if c.isascii() and c.isprintable())
    return ascii_count / len(text) > 0.80


def _parse_api_review(raw: dict[str, Any]) -> dict[str, Any] | None:
    """解析 feedback API 返回的单条评论。"""
    content = raw.get("buyerFeedback", "").strip()
    if not content or not _is_english(content):
        return None

    rating = raw.get("buyerEval", 5)
    date_str = ""
    eval_date = raw.get("evalDate", "")
    if eval_date:
        match = re.search(r"\d{4}-\d{2}-\d{2}", eval_date)
        if match:
            date_str = match.group(0)
        else:
            for fmt in ("%d %b %Y", "%b %d, %Y", "%d %B %Y"):
                try:
                    date_str = datetime.strptime(eval_date.strip(), fmt).strftime("%Y-%m-%d")
                    break
                except ValueError:
                    continue

    sku_info = raw.get("skuInfo", "") or raw.get("buyerProductFeedBack", "")

    return {
        "content": content,
        "rating": int(rating) if rating else 5,
        "date": date_str,
        "reviewer": raw.get("buyerName", ""),
        "title": "",
        "verified_purchase": True,
        "reviewer_id": "",
        "review_id": str(raw.get("evaluationId", "")),
        "sku_info": sku_info,
    }


async def _fetch_via_apify(
    item_id: str,
    *,
    max_reviews: int = 200,
    max_years: int = 2,
) -> list[dict[str, Any]]:
    """通过 Apify CrowdPull Actor 抓取评论（主数据源）。"""
    token = os.getenv("APIFY_API_TOKEN", "").strip()
    if not token:
        logger.debug("APIFY_API_TOKEN not set, skipping Apify source")
        return []

    payload = {
        "productIds": [item_id],
        "maxReviewsPerProduct": max_reviews,
        "includeProductStats": False,
        "sortBy": "default",
    }

    try:
        async with httpx.AsyncClient(timeout=180.0) as client:
            resp = await client.post(
                APIFY_ACTOR_URL,
                params={"token": token},
                json=payload,
            )
            if resp.status_code != 200:
                logger.warning(
                    "Apify Actor returned %d for item %s: %s",
                    resp.status_code, item_id, resp.text[:200],
                )
                return []

            items = resp.json()
            if not isinstance(items, list):
                logger.warning("Apify response is not a list for item %s", item_id)
                return []

    except (httpx.HTTPError, httpx.TimeoutException) as exc:
        logger.warning("Apify request failed for item %s: %s", item_id, exc)
        return []

    reviews: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()

    for raw in items:
        content = (raw.get("buyerFeedback") or "").strip()
        if not content or not _is_english(content):
            continue

        rating = raw.get("starRating") or 5
        eval_date = raw.get("evalDate") or ""
        date_str = ""
        if eval_date:
            match = re.search(r"\d{4}-\d{2}-\d{2}", eval_date)
            if match:
                date_str = match.group(0)
            else:
                for fmt in ("%d %b %Y", "%b %d, %Y", "%d %B %Y"):
                    try:
                        date_str = datetime.strptime(eval_date.strip(), fmt).strftime("%Y-%m-%d")
                        break
                    except ValueError:
                        continue

        if not _is_within_years(date_str, max_years):
            continue

        reviewer = raw.get("buyerCountry") or "Anonymous"
        dedup_key = (content[:80], reviewer)
        if dedup_key in seen:
            continue
        seen.add(dedup_key)

        reviews.append({
            "content": content,
            "rating": int(rating) if rating else 5,
            "date": date_str,
            "reviewer": reviewer,
            "title": "",
            "verified_purchase": True,
            "reviewer_id": "",
            "review_id": str(raw.get("reviewId") or ""),
            "sku_info": raw.get("skuInfo") or "",
        })

    logger.info("Apify CrowdPull: fetched %d reviews for item %s", len(reviews), item_id)
    return reviews


async def _fetch_via_api(
    item_id: str,
    *,
    max_pages: int = 5,
    max_years: int = 2,
) -> list[dict[str, Any]]:
    """通过 feedback API 抓取评论。"""
    seen: set[tuple[str, str]] = set()
    all_reviews: list[dict[str, Any]] = []

    headers = {
        "User-Agent": random.choice(USER_AGENTS),
        "Referer": f"https://www.aliexpress.com/item/{item_id}.html",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.9",
    }

    async with httpx.AsyncClient(timeout=20.0, headers=headers) as client:
        for page in range(1, max_pages + 1):
            params = {
                "productId": item_id,
                "page": str(page),
                "pageSize": "20",
                "lang": "en_US",
                "translate": "Y",
                "sort": "default",
            }

            for attempt in range(MAX_RETRIES):
                try:
                    resp = await client.get(FEEDBACK_URL, params=params)
                    if resp.status_code == 429 or resp.status_code == 503:
                        wait = (attempt + 1) * 3
                        logger.warning("AliExpress API rate limited (page=%d), retrying in %ds", page, wait)
                        await asyncio.sleep(wait)
                        continue
                    if resp.status_code == 403:
                        logger.warning("AliExpress API returned 403, stopping API fetch")
                        return all_reviews
                    break
                except httpx.HTTPError:
                    if attempt < MAX_RETRIES - 1:
                        await asyncio.sleep((attempt + 1) * 2)
                        continue
                    logger.warning("AliExpress API request failed for item %s page %d", item_id, page)
                    return all_reviews
            else:
                return all_reviews

            if resp.status_code != 200:
                break

            try:
                data = resp.json()
            except Exception:
                break

            eval_list = data.get("data", {}).get("evaluationList", [])
            if not eval_list:
                break

            for raw in eval_list:
                parsed = _parse_api_review(raw)
                if not parsed:
                    continue
                dedup_key = (parsed["content"][:80], parsed["reviewer"])
                if dedup_key in seen:
                    continue
                seen.add(dedup_key)
                if not _is_within_years(parsed["date"], max_years):
                    continue
                all_reviews.append(parsed)

            await asyncio.sleep(random.uniform(1.0, 3.0))

    logger.info("AliExpress API: fetched %d reviews for item %s", len(all_reviews), item_id)
    return all_reviews


async def _fetch_via_browser(
    item_id: str,
    *,
    max_pages: int = 5,
    max_years: int = 2,
) -> list[dict[str, Any]]:
    """通过 Playwright 无头浏览器抓取评论（fallback）。"""
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        logger.error("playwright not installed, cannot use browser fallback")
        return []

    seen: set[tuple[str, str]] = set()
    all_reviews: list[dict[str, Any]] = []
    product_title: str = ""

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent=random.choice(USER_AGENTS),
                locale="en-US",
            )
            page = await context.new_page()

            url = f"https://www.aliexpress.com/item/{item_id}.html"
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(2)

            # 尝试获取产品标题
            try:
                title_el = await page.query_selector("h1[data-pl='product-title']")
                if title_el:
                    product_title = (await title_el.inner_text()).strip()
            except Exception:
                pass

            # 点击 Reviews tab
            try:
                reviews_tab = await page.query_selector("[data-pl='product-reviewer']")
                if reviews_tab:
                    await reviews_tab.click()
                    await asyncio.sleep(2)
            except Exception:
                pass

            for _page_num in range(max_pages):
                try:
                    await page.wait_for_selector(
                        ".feedback-item, .review-item, [class*='review']",
                        timeout=10000,
                    )
                except Exception:
                    break

                review_els = await page.query_selector_all(
                    ".feedback-item, .review-item, [class*='reviewItem']"
                )

                if not review_els:
                    break

                for el in review_els:
                    try:
                        content_el = await el.query_selector(
                            ".buyer-feedback, .review-content, [class*='content']"
                        )
                        content = (await content_el.inner_text()).strip() if content_el else ""

                        if not content or not _is_english(content):
                            continue

                        rating = 5
                        star_els = await el.query_selector_all(
                            ".star-view .star-icon, [class*='starFilled'], svg[class*='star']"
                        )
                        if star_els:
                            rating = len(star_els)

                        reviewer = ""
                        reviewer_el = await el.query_selector(
                            ".user-name, [class*='userName'], [class*='reviewer']"
                        )
                        if reviewer_el:
                            reviewer = (await reviewer_el.inner_text()).strip()

                        date_str = ""
                        date_el = await el.query_selector(
                            ".r-time, [class*='time'], [class*='date']"
                        )
                        if date_el:
                            raw_date = (await date_el.inner_text()).strip()
                            match = re.search(r"\d{4}-\d{2}-\d{2}", raw_date)
                            if match:
                                date_str = match.group(0)
                            else:
                                match = re.search(r"(\d{2}\s\w+\s\d{4})", raw_date)
                                if match:
                                    try:
                                        date_str = datetime.strptime(
                                            match.group(1), "%d %b %Y"
                                        ).strftime("%Y-%m-%d")
                                    except ValueError:
                                        pass

                        sku_info = ""
                        sku_el = await el.query_selector(
                            ".sku-info, [class*='skuInfo'], [class*='variant']"
                        )
                        if sku_el:
                            sku_info = (await sku_el.inner_text()).strip()

                        dedup_key = (content[:80], reviewer)
                        if dedup_key in seen:
                            continue
                        seen.add(dedup_key)

                        if not _is_within_years(date_str, max_years):
                            continue

                        all_reviews.append({
                            "content": content,
                            "rating": min(max(rating, 1), 5),
                            "date": date_str,
                            "reviewer": reviewer,
                            "title": "",
                            "verified_purchase": True,
                            "reviewer_id": "",
                            "review_id": "",
                            "sku_info": sku_info,
                        })
                    except Exception:
                        continue

                # 翻页
                try:
                    next_btn = await page.query_selector(
                        "button.next-btn, [class*='pagination'] button:last-child, "
                        "a[class*='next']"
                    )
                    if next_btn and await next_btn.is_enabled():
                        await next_btn.click()
                        await asyncio.sleep(random.uniform(2.0, 4.0))
                    else:
                        break
                except Exception:
                    break

            await browser.close()

    except Exception as exc:
        logger.error("Playwright browser scraping failed for item %s: %s", item_id, exc)

    logger.info(
        "AliExpress browser: fetched %d reviews for item %s (title=%s)",
        len(all_reviews), item_id, product_title[:50],
    )
    return all_reviews


async def fetch_aliexpress_reviews(
    item_id: str,
    *,
    max_pages: int = 10,
    max_years: int = 2,
) -> list[dict[str, Any]]:
    """AliExpress 评论抓取统一入口 — 三级 fallback。

    优先级：Apify CrowdPull → feedback API → Playwright 浏览器
    """
    reviews = await _fetch_via_apify(item_id, max_reviews=200, max_years=max_years)
    if reviews:
        logger.info("Using Apify source: %d reviews for %s", len(reviews), item_id)
        return reviews

    logger.info("Apify returned 0 reviews for %s, trying feedback API", item_id)
    reviews = await _fetch_via_api(item_id, max_pages=max_pages, max_years=max_years)
    if reviews:
        logger.info("Using feedback API source: %d reviews for %s", len(reviews), item_id)
        return reviews

    logger.info("Feedback API returned 0 reviews for %s, falling back to browser", item_id)
    reviews = await _fetch_via_browser(item_id, max_pages=max_pages, max_years=max_years)

    if not reviews:
        logger.warning("No reviews found for AliExpress item %s via any source", item_id)

    return reviews
