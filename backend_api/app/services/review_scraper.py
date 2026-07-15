"""统一评论抓取入口 — 按平台分派到对应数据源。

支持平台：
- Amazon: woot.com 免费 API（~50 条/ASIN）
- AliExpress: Apify CrowdPull → feedback API → Playwright 浏览器
- eBay: Apify scrapier/ebay-review-scraper
- Walmart: Apify webscrapewizard/walmart-review-crawler
- Shopee: Apify zen-studio → 公开 Ratings API v2
"""
from __future__ import annotations

import logging
import os
from typing import Any

from backend_api.app.services.aliexpress_scraper import fetch_aliexpress_reviews
from backend_api.app.services.ebay_scraper import fetch_ebay_reviews
from backend_api.app.services.shopee_scraper import fetch_shopee_reviews
from backend_api.app.services.walmart_scraper import fetch_walmart_reviews
from backend_api.app.services.woot_scraper import fetch_woot_reviews

logger = logging.getLogger(__name__)


def _woot_enabled() -> bool:
    """woot.com 抓取仅限国内环境（US marketplace only，~50 条/ASIN）。

    出海 prod 默认禁用，需显式设置 ENABLE_WOOT_SCRAPER=true 才启用。
    """
    return os.getenv("ENABLE_WOOT_SCRAPER", "false").lower() == "true"


class ReviewScraperError(Exception):
    """评论抓取失败。"""

    def __init__(self, message: str):
        super().__init__(message)


async def fetch_reviews(
    product_id: str,
    *,
    platform: str = "amazon",
    marketplace: str = "us",
    max_years: int = 2,
) -> list[dict[str, Any]]:
    """统一评论抓取入口 — 按平台分派。"""
    if platform == "aliexpress":
        reviews = await fetch_aliexpress_reviews(product_id, max_years=max_years)
        if not reviews:
            logger.warning("No reviews found for AliExpress item %s", product_id)
    elif platform == "ebay":
        reviews = await fetch_ebay_reviews(product_id, max_years=max_years)
        if not reviews:
            logger.warning("No reviews found for eBay item %s", product_id)
    elif platform == "walmart":
        reviews = await fetch_walmart_reviews(product_id, max_years=max_years)
        if not reviews:
            logger.warning("No reviews found for Walmart item %s", product_id)
    elif platform == "shopee":
        parts = product_id.split(".", 1)
        if len(parts) != 2:
            logger.error("Invalid Shopee product_id format: %s (expected itemid.shopid)", product_id)
            return []
        item_id, shop_id = parts
        reviews = await fetch_shopee_reviews(
            item_id, shop_id, region=marketplace, max_years=max_years
        )
        if not reviews:
            logger.warning("No reviews found for Shopee item %s", product_id)
    else:
        if not _woot_enabled():
            logger.info(
                "woot.com scraper disabled (ENABLE_WOOT_SCRAPER != true); "
                "skipping ASIN %s — use Chrome extension upload instead",
                product_id,
            )
            return []
        reviews = await fetch_woot_reviews(product_id, max_years=max_years)
        if not reviews:
            logger.warning("No reviews found for ASIN %s via woot.com", product_id)

    return reviews
