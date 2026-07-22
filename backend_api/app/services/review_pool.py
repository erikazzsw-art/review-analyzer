"""跨用户评论源数据缓存池 — 全局共享抓取结果。

在调用第三方 scraper 之前查询 pool，命中则跳过抓取；
抓取完成后写入 pool 供后续用户复用。分析完成后回填结果。
"""
from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from datetime import date, datetime, timezone
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
REVIEW_POOL_RETENTION_YEARS = 2


def _cutoff_date(years: int = REVIEW_POOL_RETENTION_YEARS) -> date:
    today = datetime.now(timezone.utc).date()
    try:
        return today.replace(year=today.year - years)
    except ValueError:
        return today.replace(year=today.year - years, day=28)


def _extract_review_date(value: Any) -> date | None:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = str(value or "").strip()
    if not text:
        return None

    iso_match = re.search(r"\d{4}-\d{2}-\d{2}", text)
    if iso_match:
        try:
            return datetime.strptime(iso_match.group(0), "%Y-%m-%d").date()
        except ValueError:
            return None

    month_match = re.search(
        r"(January|February|March|April|May|June|July|August|September|October|November|December)"
        r"\s+\d{1,2},?\s+\d{4}",
        text,
        re.IGNORECASE,
    )
    if month_match:
        try:
            return datetime.strptime(month_match.group(0).replace(",", ""), "%B %d %Y").date()
        except ValueError:
            return None
    return None


def _review_date_value(review: dict[str, Any]) -> Any:
    return review.get("date_iso") or review.get("date") or review.get("review_date")


def _normalize_review_date(review: dict[str, Any]) -> str | None:
    parsed = _extract_review_date(_review_date_value(review))
    if not parsed or parsed < _cutoff_date():
        return None
    return parsed.isoformat()


def _normalize_review_id(value: Any) -> str | None:
    text = str(value or "").strip()
    return text or None


def _recent_pool_date_sql() -> str:
    return "substring(review_date from '^[0-9]{4}-[0-9]{2}-[0-9]{2}')::date >= %s"


def get_pool_meta(
    platform: str,
    product_key: str,
    marketplace: str = "us",
) -> PoolMeta | None:
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                f"""SELECT
                          m.platform,
                          m.product_key,
                          m.marketplace,
                          COALESCE(r.total_reviews, 0) AS total_reviews,
                          COALESCE(r.last_scraped_at, m.last_scraped_at)::text AS last_scraped_at,
                          COALESCE(r.scraper_source, m.scraper_source) AS scraper_source
                   FROM review_pool_meta m
                   LEFT JOIN LATERAL (
                       SELECT COUNT(*) AS total_reviews,
                              MAX(scraped_at) AS last_scraped_at,
                              MAX(scraper_source) AS scraper_source
                       FROM review_pool
                       WHERE platform = m.platform
                         AND product_key = m.product_key
                         AND marketplace = m.marketplace
                         AND {_recent_pool_date_sql()}
                   ) r ON TRUE
                   WHERE m.platform = %s AND m.product_key = %s AND m.marketplace = %s""",
                (_cutoff_date(), platform, product_key, marketplace),
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
                     AND """ + _recent_pool_date_sql() + """
                   ORDER BY scraped_at DESC
                   LIMIT %s""",
                (platform, product_key, marketplace, _cutoff_date(), max_reviews),
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
    """将抓取结果写入池。

    规则:
    - 只写入可解析日期且在最近 2 年内的评论。
    - 同一 platform/marketplace/product_key 下优先按 review_id 去重。
    - 没有 review_id 时,按 content_hash 去重。
    """
    if not reviews:
        return 0

    conn = get_connection()
    inserted = 0
    seen_keys: set[str] = set()
    try:
        with conn.cursor() as cur:
            for r in reviews:
                content = r.get("content", "")
                rating = r.get("rating")
                content_hash = compute_content_hash(content, rating)
                review_date = _normalize_review_date(r)
                if not review_date:
                    continue
                review_id = _normalize_review_id(r.get("review_id"))
                dedupe_key = f"id:{review_id.lower()}" if review_id else f"hash:{content_hash}"
                if dedupe_key in seen_keys:
                    continue
                seen_keys.add(dedupe_key)
                cur.execute("SAVEPOINT _pool_write_row")
                try:
                    if review_id:
                        cur.execute(
                            """SELECT id
                               FROM review_pool
                               WHERE platform = %s
                                 AND product_key = %s
                                 AND marketplace = %s
                                 AND review_id = %s
                               LIMIT 1""",
                            (platform, product_key, marketplace, review_id),
                        )
                        if cur.fetchone():
                            cur.execute("RELEASE SAVEPOINT _pool_write_row")
                            continue

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
                            review_date,
                            r.get("reviewer", ""),
                            r.get("title", ""),
                            review_id,
                            r.get("source_variant_asin") or r.get("sku_info", ""),
                            content_hash,
                            scraper_source,
                        ),
                    )
                    if cur.rowcount > 0:
                        inserted += 1
                    cur.execute("RELEASE SAVEPOINT _pool_write_row")
                except Exception:
                    logger.warning("pool_write: skip row due to error", exc_info=True)
                    cur.execute("ROLLBACK TO SAVEPOINT _pool_write_row")
                    cur.execute("RELEASE SAVEPOINT _pool_write_row")
                    continue

            # 更新 meta 表
            cur.execute(
                f"""INSERT INTO review_pool_meta (platform, product_key, marketplace, total_reviews, scraper_source)
                   VALUES (%s, %s, %s,
                           (SELECT count(*) FROM review_pool
                            WHERE platform=%s AND product_key=%s AND marketplace=%s
                              AND {_recent_pool_date_sql()}),
                           %s)
                   ON CONFLICT (platform, product_key, marketplace)
                   DO UPDATE SET
                       total_reviews = (SELECT count(*) FROM review_pool
                                        WHERE platform=%s AND product_key=%s AND marketplace=%s
                                          AND {_recent_pool_date_sql()}),
                       last_scraped_at = NOW(),
                       scraper_source = EXCLUDED.scraper_source""",
                (
                    platform, product_key, marketplace,
                    platform, product_key, marketplace,
                    _cutoff_date(),
                    scraper_source,
                    platform, product_key, marketplace,
                    _cutoff_date(),
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
