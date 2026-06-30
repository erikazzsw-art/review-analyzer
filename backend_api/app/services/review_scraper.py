"""统一评论抓取入口 — 协调多个数据源获取 Amazon 评论。

当前数据源优先级：
1. woot.com（免费，~50 条/ASIN）
2. ScrapingDog /amazon/reviews（付费，预留接口，待端点稳定后启用）
"""
from __future__ import annotations

import logging
from typing import Any

from backend_api.app.services.woot_scraper import fetch_woot_reviews

logger = logging.getLogger(__name__)


class ReviewScraperError(Exception):
    """评论抓取失败。"""

    def __init__(self, message: str):
        super().__init__(message)


async def fetch_reviews(
    asin: str,
    *,
    marketplace: str = "us",
    max_years: int = 2,
) -> list[dict[str, Any]]:
    """统一评论抓取入口。

    当前实现：仅使用 woot.com 免费源。
    后续扩展：woot.com 数量不足时自动切换到 ScrapingDog。
    """
    reviews = await fetch_woot_reviews(asin, max_years=max_years)

    if not reviews:
        logger.warning("No reviews found for ASIN %s via woot.com", asin)

    return reviews
