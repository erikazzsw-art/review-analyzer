"""Rainforest API 封装 — 按 ASIN 拉取 Amazon 评论。

Rainforest API (Traject Data): https://www.rainforestapi.com/docs
每次请求返回 10 条评论，支持翻页。
"""
from __future__ import annotations

import logging
import os
from typing import Any

import httpx

logger = logging.getLogger(__name__)

RAINFOREST_BASE_URL = "https://api.rainforestapi.com/request"

AMAZON_DOMAINS: dict[str, str] = {
    "us": "amazon.com",
    "uk": "amazon.co.uk",
    "de": "amazon.de",
    "fr": "amazon.fr",
    "jp": "amazon.co.jp",
    "ca": "amazon.ca",
    "it": "amazon.it",
    "es": "amazon.es",
    "au": "amazon.com.au",
    "in": "amazon.in",
    "mx": "amazon.com.mx",
    "br": "amazon.com.br",
    "sg": "amazon.sg",
    "nl": "amazon.nl",
    "sa": "amazon.sa",
    "ae": "amazon.ae",
}


class RainforestError(Exception):
    """Rainforest API 调用失败。"""

    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code


def _get_api_key() -> str:
    key = os.getenv("RAINFOREST_API_KEY", "")
    if not key:
        raise RainforestError("RAINFOREST_API_KEY not configured")
    return key


def _parse_review(raw: dict[str, Any]) -> dict[str, Any]:
    """将 Rainforest API 返回的单条 review 转为内部格式。"""
    date_field = raw.get("date", {})
    date_str = _extract_iso_date(date_field)
    profile = raw.get("profile", {}) or {}
    return {
        "content": raw.get("body", ""),
        "rating": raw.get("rating"),
        "date": date_str,
        "reviewer": profile.get("name", ""),
        "title": raw.get("title", ""),
        "verified_purchase": raw.get("verified_purchase", False),
        "reviewer_id": profile.get("id", ""),
        "review_id": raw.get("id", ""),
    }


def _extract_iso_date(date_field: Any) -> str:
    """从 Rainforest date 字段提取 ISO 日期 (YYYY-MM-DD)。

    Rainforest API 返回格式: {"raw": "Reviewed in ... on March 5, 2023", "utc": "2023-03-05T00:00:00.000Z"}
    优先用 utc 字段；fallback 尝试从 raw 文本解析。
    """
    if not isinstance(date_field, dict):
        s = str(date_field).strip()
        return s[:10] if s and s[:4].isdigit() else ""

    utc = str(date_field.get("utc", "")).strip()
    if utc and utc[:4].isdigit():
        return utc[:10]

    raw = str(date_field.get("raw", "")).strip()
    if raw and raw[:4].isdigit():
        return raw[:10]

    # 尝试从 "Reviewed in ... on September 29, 2024" 格式解析
    if " on " in raw:
        from datetime import datetime as _dt

        tail = raw.rsplit(" on ", 1)[-1].strip()
        for fmt in ("%B %d, %Y", "%d %B %Y", "%b %d, %Y"):
            try:
                return _dt.strptime(tail, fmt).strftime("%Y-%m-%d")
            except ValueError:
                continue

    return ""


async def fetch_reviews_by_asin(
    asin: str,
    *,
    marketplace: str = "us",
    max_pages: int = 5,
    sort_by: str = "most_recent",
) -> list[dict[str, Any]]:
    """拉取指定 ASIN 的全部评论（自动翻页）。

    Args:
        asin: Amazon 产品 ASIN
        marketplace: 站点代码 (us/uk/de/jp 等)
        max_pages: 最大翻页数（每页 10 条）
        sort_by: 排序方式 (most_recent / top_reviews)

    Returns:
        解析后的评论列表
    """
    api_key = _get_api_key()
    domain = AMAZON_DOMAINS.get(marketplace)
    if not domain:
        raise RainforestError(f"Unsupported marketplace: {marketplace}")

    all_reviews: list[dict[str, Any]] = []

    async with httpx.AsyncClient(timeout=30.0) as client:
        for page in range(1, max_pages + 1):
            params = {
                "api_key": api_key,
                "type": "reviews",
                "asin": asin,
                "amazon_domain": domain,
                "sort_by": sort_by,
                "page": str(page),
            }

            resp = await client.get(RAINFOREST_BASE_URL, params=params)

            if resp.status_code == 429:
                logger.warning("Rainforest API rate limited on page %d", page)
                break

            if resp.status_code == 503:
                logger.warning(
                    "Rainforest reviews endpoint unavailable (503), falling back to product top_reviews"
                )
                return await _fetch_reviews_via_product(client, api_key, asin, domain)

            if resp.status_code != 200:
                raise RainforestError(
                    f"Rainforest API error: {resp.status_code} - {resp.text[:200]}",
                    status_code=resp.status_code,
                )

            data = resp.json()
            reviews = data.get("reviews", [])

            if not reviews:
                break

            for raw in reviews:
                all_reviews.append(_parse_review(raw))

            total_pages = data.get("pagination", {}).get("total_pages", 1)
            if page >= total_pages:
                break

    logger.info(
        "Fetched %d reviews for ASIN %s (%s), %d pages",
        len(all_reviews), asin, marketplace, min(page, max_pages),
    )
    return all_reviews


async def _fetch_reviews_via_product(
    client: httpx.AsyncClient,
    api_key: str,
    asin: str,
    domain: str,
) -> list[dict[str, Any]]:
    """Fallback: 通过 product 请求获取 top_reviews（reviews 端点不可用时）。"""
    params = {
        "api_key": api_key,
        "type": "product",
        "asin": asin,
        "amazon_domain": domain,
    }
    resp = await client.get(RAINFOREST_BASE_URL, params=params)

    if resp.status_code != 200:
        raise RainforestError(
            f"Rainforest product fallback error: {resp.status_code}",
            status_code=resp.status_code,
        )

    data = resp.json()
    product = data.get("product", {})
    top_reviews = product.get("top_reviews", [])

    reviews = [_parse_review(r) for r in top_reviews]
    logger.info(
        "Fallback: fetched %d top_reviews for ASIN %s via product endpoint",
        len(reviews), asin,
    )
    return reviews


async def fetch_product_info(
    asin: str,
    *,
    marketplace: str = "us",
) -> dict[str, Any]:
    """拉取 ASIN 对应的产品基本信息（名称、品类等）。"""
    api_key = _get_api_key()
    domain = AMAZON_DOMAINS.get(marketplace)
    if not domain:
        raise RainforestError(f"Unsupported marketplace: {marketplace}")

    async with httpx.AsyncClient(timeout=20.0) as client:
        params = {
            "api_key": api_key,
            "type": "product",
            "asin": asin,
            "amazon_domain": domain,
        }
        resp = await client.get(RAINFOREST_BASE_URL, params=params)

        if resp.status_code != 200:
            raise RainforestError(
                f"Rainforest API error: {resp.status_code}",
                status_code=resp.status_code,
            )

        product = resp.json().get("product", {})
        return {
            "title": product.get("title", ""),
            "category": product.get("categories_flat", ""),
            "brand": product.get("brand", ""),
            "rating": product.get("rating"),
            "ratings_total": product.get("ratings_total"),
            "reviews_total": product.get("reviews_total"),
        }


async def fetch_product_variants(
    asin: str,
    *,
    marketplace: str = "us",
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """拉取产品信息及其所有变体 ASIN 列表。

    Returns:
        (product_info, variants) — variants 为 [{"asin": "B0xxx", "title": "...", ...}, ...]
    """
    api_key = _get_api_key()
    domain = AMAZON_DOMAINS.get(marketplace)
    if not domain:
        raise RainforestError(f"Unsupported marketplace: {marketplace}")

    async with httpx.AsyncClient(timeout=30.0) as client:
        params = {
            "api_key": api_key,
            "type": "product",
            "asin": asin,
            "amazon_domain": domain,
        }
        resp = await client.get(RAINFOREST_BASE_URL, params=params)

        if resp.status_code != 200:
            raise RainforestError(
                f"Rainforest API error: {resp.status_code}",
                status_code=resp.status_code,
            )

        data = resp.json()
        product = data.get("product", {})

        main_image = product.get("main_image") or {}
        buybox = product.get("buybox_winner") or {}
        buybox_price = buybox.get("price", {}) if isinstance(buybox.get("price"), dict) else {}

        product_info = {
            "title": product.get("title", ""),
            "category": product.get("categories_flat", ""),
            "brand": product.get("brand", ""),
            "rating": product.get("rating"),
            "ratings_total": product.get("ratings_total"),
            "reviews_total": product.get("reviews_total"),
            "image_url": main_image.get("link", ""),
            "price": buybox.get("price") if isinstance(buybox.get("price"), (int, float)) else buybox_price.get("value"),
            "price_currency": buybox_price.get("currency", "USD") if buybox_price else "USD",
            "asin": asin,
        }

        raw_variants = product.get("variants", [])
        variants = []
        for v in raw_variants:
            v_asin = v.get("asin", "")
            if v_asin and len(v_asin) == 10:
                v_image = ""
                if isinstance(v.get("main_image"), dict):
                    v_image = v["main_image"].get("link", "")
                elif isinstance(v.get("image"), str):
                    v_image = v["image"]
                variants.append({
                    "asin": v_asin,
                    "title": v.get("title", ""),
                    "dimensions": v.get("dimensions", []),
                    "image_url": v_image,
                    "price": v.get("price", {}).get("value") if isinstance(v.get("price"), dict) else v.get("price"),
                })

        logger.info(
            "Discovered %d variants for ASIN %s (%s)",
            len(variants), asin, marketplace,
        )
        return product_info, variants
