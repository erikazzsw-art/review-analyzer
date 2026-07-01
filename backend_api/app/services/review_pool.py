"""跨用户评论源数据缓存池 — 全局共享抓取结果。

在调用第三方 scraper 之前查询 pool，命中则跳过抓取；
抓取完成后写入 pool 供后续用户复用。分析完成后回填结果。
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Any

import psycopg2.extras

from backend_api.app.services.analysis_cache import compute_content_hash
from review_analyzer.database import get_connection

logger = logging.getLogger(__name__)


@dataclass
class PoolMeta:
    platform: str
    product_key: str
    marketplace: str
    total_reviews: int
    last_scraped_at: str
    scraper_source: str | None


POOL_MIN_THRESHOLD = 20


def get_pool_meta(
    platform: str,
    product_key: str,
    marketplace: str = "us",
) -> PoolMeta | None:
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """SELECT platform, product_key, marketplace, total_reviews,
                          last_scraped_at::text, scraper_source
                   FROM review_pool_meta
                   WHERE platform = %s AND product_key = %s AND marketplace = %s""",
                (platform, product_key, marketplace),
            )
            row = cur.fetchone()
    finally:
        conn.close()

    if not row:
        return None
    return PoolMeta(
        platform=row["platform"],
        product_key=row["product_key"],
        marketplace=row["marketplace"],
        total_reviews=row["total_reviews"],
        last_scraped_at=row["last_scraped_at"],
        scraper_source=row["scraper_source"],
    )


def pool_has_enough(meta: PoolMeta | None, min_reviews: int = POOL_MIN_THRESHOLD) -> bool:
    if meta is None:
        return False
    return meta.total_reviews >= min_reviews


def pool_lookup(
    platform: str,
    product_key: str,
    marketplace: str = "us",
    max_reviews: int = 100,
) -> tuple[list[dict[str, Any]], PoolMeta | None]:
    """查询缓存池，返回 (reviews, meta)。reviews 按 scraped_at DESC 截断到 max_reviews。"""
    meta = get_pool_meta(platform, product_key, marketplace)
    if not pool_has_enough(meta):
        return [], meta

    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """SELECT content, rating, review_date, reviewer, title,
                          review_id, source_variant, content_hash,
                          sentiment, aspects_json, analyzed_at, analyzer_version
                   FROM review_pool
                   WHERE platform = %s AND product_key = %s AND marketplace = %s
                   ORDER BY scraped_at DESC
                   LIMIT %s""",
                (platform, product_key, marketplace, max_reviews),
            )
            rows = cur.fetchall()
    finally:
        conn.close()

    reviews = [dict(r) for r in rows]
    return reviews, meta


def pool_write(
    platform: str,
    product_key: str,
    marketplace: str,
    reviews: list[dict[str, Any]],
    scraper_source: str = "",
) -> int:
    """将抓取结果写入池（ON CONFLICT 跳过重复）。返回新插入行数。"""
    if not reviews:
        return 0

    conn = get_connection()
    inserted = 0
    try:
        with conn.cursor() as cur:
            for r in reviews:
                content = r.get("content", "")
                rating = r.get("rating")
                content_hash = compute_content_hash(content, rating)
                try:
                    cur.execute(
                        """INSERT INTO review_pool
                           (platform, product_key, marketplace, content, rating,
                            review_date, reviewer, title, review_id,
                            source_variant, content_hash, scraper_source)
                           VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                           ON CONFLICT (platform, product_key, marketplace, content_hash)
                           DO NOTHING""",
                        (
                            platform, product_key, marketplace,
                            content, rating,
                            r.get("date") or r.get("review_date", ""),
                            r.get("reviewer", ""),
                            r.get("title", ""),
                            r.get("review_id", ""),
                            r.get("source_variant_asin") or r.get("sku_info", ""),
                            content_hash,
                            scraper_source,
                        ),
                    )
                    if cur.rowcount > 0:
                        inserted += 1
                except Exception:
                    logger.warning("pool_write: skip row due to error", exc_info=True)
                    conn.rollback()
                    continue

            # 更新 meta 表
            cur.execute(
                """INSERT INTO review_pool_meta (platform, product_key, marketplace, total_reviews, scraper_source)
                   VALUES (%s, %s, %s,
                           (SELECT count(*) FROM review_pool WHERE platform=%s AND product_key=%s AND marketplace=%s),
                           %s)
                   ON CONFLICT (platform, product_key, marketplace)
                   DO UPDATE SET
                       total_reviews = (SELECT count(*) FROM review_pool WHERE platform=%s AND product_key=%s AND marketplace=%s),
                       last_scraped_at = NOW(),
                       scraper_source = EXCLUDED.scraper_source""",
                (
                    platform, product_key, marketplace,
                    platform, product_key, marketplace,
                    scraper_source,
                    platform, product_key, marketplace,
                ),
            )
            conn.commit()
    except Exception:
        logger.error("pool_write failed", exc_info=True)
        conn.rollback()
    finally:
        conn.close()

    logger.info("pool_write: %s:%s/%s — inserted %d/%d", platform, product_key, marketplace, inserted, len(reviews))
    return inserted


def pool_backfill_analysis(
    platform: str,
    product_key: str,
    marketplace: str,
    analyzed_comments: list[dict[str, Any]],
    analyzer_version: str = "",
) -> int:
    """分析完成后，将 sentiment/aspects_json 回填到池中对应行。"""
    if not analyzed_comments:
        return 0

    conn = get_connection()
    updated = 0
    try:
        with conn.cursor() as cur:
            for c in analyzed_comments:
                content_hash = c.get("content_hash")
                if not content_hash:
                    continue
                sentiment = c.get("sentiment")
                aspects_json = c.get("aspects_json")
                if not sentiment and not aspects_json:
                    continue

                aspects_str = (
                    json.dumps(aspects_json, ensure_ascii=False)
                    if isinstance(aspects_json, dict)
                    else aspects_json
                )
                cur.execute(
                    """UPDATE review_pool
                       SET sentiment = %s,
                           aspects_json = %s,
                           analyzed_at = NOW(),
                           analyzer_version = %s
                       WHERE platform = %s AND product_key = %s AND marketplace = %s
                             AND content_hash = %s AND analyzed_at IS NULL""",
                    (
                        sentiment, aspects_str, analyzer_version,
                        platform, product_key, marketplace, content_hash,
                    ),
                )
                updated += cur.rowcount
            conn.commit()
    except Exception:
        logger.error("pool_backfill_analysis failed", exc_info=True)
        conn.rollback()
    finally:
        conn.close()

    logger.info("pool_backfill: %s:%s/%s — updated %d rows", platform, product_key, marketplace, updated)
    return updated
