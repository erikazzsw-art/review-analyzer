-- Migration 053: review_pool 2-year retention + review_id dedupe
-- 创建时间: 2026-07-22
-- 说明:
--   1. 全局评论池只保留最近 2 年内、日期可解析的评论缓存。
--   2. 同一 platform/product_key/marketplace 下优先按 review_id 去重；
--      没有 review_id 时继续使用已有 content_hash 唯一约束。

-- ========== UP ==========

BEGIN;

DELETE FROM review_pool
WHERE substring(review_date from '^[0-9]{4}-[0-9]{2}-[0-9]{2}') IS NULL
   OR substring(review_date from '^[0-9]{4}-[0-9]{2}-[0-9]{2}')::date < CURRENT_DATE - INTERVAL '2 years';

WITH ranked AS (
    SELECT
        id,
        ROW_NUMBER() OVER (
            PARTITION BY platform, product_key, marketplace, review_id
            ORDER BY
                (analyzed_at IS NOT NULL) DESC,
                scraped_at DESC,
                id DESC
        ) AS rn
    FROM review_pool
    WHERE review_id IS NOT NULL AND review_id <> ''
)
DELETE FROM review_pool p
USING ranked r
WHERE p.id = r.id AND r.rn > 1;

CREATE UNIQUE INDEX IF NOT EXISTS uq_review_pool_product_review_id
    ON review_pool (platform, product_key, marketplace, review_id)
    WHERE review_id IS NOT NULL AND review_id <> '';

UPDATE review_pool_meta m
SET total_reviews = recent.total_reviews,
    last_scraped_at = COALESCE(recent.last_scraped_at, m.last_scraped_at),
    scraper_source = COALESCE(recent.scraper_source, m.scraper_source)
FROM (
    SELECT
        platform,
        product_key,
        marketplace,
        COUNT(*) AS total_reviews,
        MAX(scraped_at) AS last_scraped_at,
        MAX(scraper_source) AS scraper_source
    FROM review_pool
    WHERE substring(review_date from '^[0-9]{4}-[0-9]{2}-[0-9]{2}')::date >= CURRENT_DATE - INTERVAL '2 years'
    GROUP BY platform, product_key, marketplace
) recent
WHERE m.platform = recent.platform
  AND m.product_key = recent.product_key
  AND m.marketplace = recent.marketplace;

UPDATE review_pool_meta m
SET total_reviews = 0
WHERE NOT EXISTS (
    SELECT 1
    FROM review_pool p
    WHERE p.platform = m.platform
      AND p.product_key = m.product_key
      AND p.marketplace = m.marketplace
);

COMMIT;

-- ========== DOWN ==========
-- DROP INDEX IF EXISTS uq_review_pool_product_review_id;
