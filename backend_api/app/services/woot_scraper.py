"""woot.com 免费评论抓取 — 通过 woot.com AJAX API 获取 Amazon 评论。

woot.com 托管了 Amazon 评论的镜像数据，支持按星级/排序分页。
每个 ASIN 通常可获取 40-50 条唯一评论（跨星级+排序组合去重）。

数据质量说明（2026-07-14 验证，ASIN B08BX7FV5L）：
- SubmissionDate: 始终为 /Date(0)/（epoch zero），不可用；实际日期在 OriginDescription
- SubmissionDateStr: 始终为 "January 01, 1970"（fallback 值），不可用
- Id: 始终为 null，无独立 review_id
- MediaUrls: 始终为空数组
- MarketplaceId: 始终为 null
- ImageUrls: 部分评论有值（m.media-amazon.com CDN），多数为空

扩展兼容性（Step 14-4）：
- Rating: 扩展从 "X.X out of 5 stars" 文本解析为 float，Woot API 返回 int (1-5)，
  统一格式中 rating 为数值类型，下游消费方需兼容 int/float
- Date: 两方均从 OriginDescription（"Reviewed in the United States on Month DD, YYYY"）
  解析为 ISO 8601，格式一致
- Helpful Count: 扩展从 "X people found this helpful" DOM 文本解析，Woot API 提供
  HelpfulVotes (int)，已映射为 helpful_count
- Verified: 扩展检测 DOM 元素，Woot API 提供 IsVerifiedPurchase (bool)，一致
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx

logger = logging.getLogger(__name__)

WOOT_REVIEW_URL = "https://www.woot.com/review/Reviews/{asin}"

SORT_OPTIONS = ["Helpfulness", "MostRecent"]
STAR_FILTERS = [0, 1, 2, 3, 4, 5]  # 0 = all stars
MAX_PAGES_PER_COMBO = 5


def _parse_date(origin_desc: str) -> str:
    """从 OriginDescription 提取 ISO 日期。

    格式: "Reviewed in the United States on May 2, 2026"
    """
    if " on " not in origin_desc:
        return ""
    tail = origin_desc.rsplit(" on ", 1)[-1].strip()
    for fmt in ("%B %d, %Y", "%b %d, %Y", "%d %B %Y"):
        try:
            return datetime.strptime(tail, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return ""


def _is_within_years(date_str: str, years: int = 2) -> bool:
    """判断日期是否在最近 N 年内。"""
    if not date_str:
        return True  # 无日期的评论保留
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        cutoff = datetime.now(timezone.utc) - timedelta(days=years * 365)
        return dt >= cutoff
    except ValueError:
        return True


def _parse_woot_review(raw: dict[str, Any]) -> dict[str, Any]:
    """将 woot.com 返回的评论转为内部统一格式。

    字段映射（Woot API → 统一格式）：
    - Author → reviewer
    - OverallRating (int) → rating
    - HelpfulVotes (int) → helpful_count
    - IsVerifiedPurchase (bool) → verified_purchase
    - OriginDescription → date (ISO 8601)
    - Text → content
    - Title → title
    - ImageUrls → image_urls
    - Id → review_id（woot.com 始终为 null）
    """
    origin = raw.get("OriginDescription", "")
    date_str = _parse_date(origin)
    return {
        "content": raw.get("Text", ""),
        "rating": raw.get("OverallRating"),
        "date": date_str,
        "reviewer": raw.get("Author", ""),
        "title": raw.get("Title", ""),
        "verified_purchase": raw.get("IsVerifiedPurchase", False),
        "helpful_count": raw.get("HelpfulVotes", 0),
        "image_urls": raw.get("ImageUrls", []),
        "reviewer_id": "",
        "review_id": "",
    }


async def fetch_woot_reviews(
    asin: str,
    *,
    max_years: int = 2,
) -> list[dict[str, Any]]:
    """通过 woot.com 拉取指定 ASIN 的评论（免费，无需 API key）。

    遍历 5 星级 × 2 排序组合，每组合最多 5 页，去重后返回。
    """
    seen: set[tuple[str, str]] = set()
    all_reviews: list[dict[str, Any]] = []

    async with httpx.AsyncClient(timeout=20.0) as client:
        for sort_by in SORT_OPTIONS:
            for star_filter in STAR_FILTERS:
                for page in range(1, MAX_PAGES_PER_COMBO + 1):
                    params: dict[str, str] = {
                        "page": str(page),
                        "sortBy": sort_by,
                    }
                    if star_filter > 0:
                        params["filter"] = str(star_filter)

                    url = WOOT_REVIEW_URL.format(asin=asin)
                    try:
                        resp = await client.get(url, params=params)
                    except httpx.HTTPError:
                        logger.warning(
                            "woot.com request failed for %s (sort=%s, star=%d, page=%d)",
                            asin, sort_by, star_filter, page,
                        )
                        break

                    if resp.status_code != 200:
                        break

                    data = resp.json()
                    reviews = data.get("Reviews", [])
                    if not reviews:
                        break

                    for raw in reviews:
                        parsed = _parse_woot_review(raw)
                        dedup_key = (parsed["content"][:80], parsed["reviewer"])
                        if dedup_key in seen:
                            continue
                        seen.add(dedup_key)

                        if not _is_within_years(parsed["date"], max_years):
                            continue

                        if parsed["content"].strip():
                            all_reviews.append(parsed)

                    if not data.get("PagingNext"):
                        break

    logger.info("woot.com: fetched %d unique reviews for ASIN %s", len(all_reviews), asin)
    return all_reviews
