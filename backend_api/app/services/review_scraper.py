"""统一评论抓取入口 — 按平台分派到对应数据源。

支持平台：
- Amazon: woot.com 免费 API（~50 条/ASIN）
- AliExpress: feedback API + Playwright 浏览器 fallback
"""
from __future__ import annotations

import logging
from typing import Any

from backend_api.app.services.aliexpress_scraper import fetch_aliexpress_reviews
from backend_api.app.services.woot_scraper import fetch_woot_reviews

logger = logging.getLogger(__name__)


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
    else:
        reviews = await fetch_woot_reviews(product_id, max_years=max_years)
        if not reviews:
            logger.warning("No reviews found for ASIN %s via woot.com", product_id)

    return reviews
