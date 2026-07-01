-- Migration 038: 跨用户评论源数据缓存池（review_pool）
-- 全局共享的抓取结果缓存，消除重复第三方 API 调用。
-- 无 user_id — 数据全局可见，用户仍通过 comments 表持有自己的副本。

BEGIN;

-- ====== 评论池主表 ======
CREATE TABLE IF NOT EXISTS review_pool (
    id              BIGSERIAL PRIMARY KEY,
    platform        VARCHAR(20)  NOT NULL,
    product_key     VARCHAR(60)  NOT NULL,
    marketplace     VARCHAR(10)  NOT NULL DEFAULT 'us',
    content         TEXT         NOT NULL,
    rating          SMALLINT,
    review_date     TEXT,
    reviewer        TEXT,
    title           TEXT,
    review_id       TEXT,
    source_variant  TEXT,
    content_hash    TEXT         NOT NULL,
    sentiment       VARCHAR(20),
    aspects_json    JSONB,
    analyzed_at     TIMESTAMPTZ,
    analyzer_version VARCHAR(10),
    scraped_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    scraper_source  VARCHAR(40),

    CONSTRAINT uq_pool_product_content
        UNIQUE (platform, product_key, marketplace, content_hash)
);

CREATE INDEX idx_pool_product_lookup
    ON review_pool (platform, product_key, marketplace);

-- ====== 池元数据表（快速判断某产品是否已缓存） ======
CREATE TABLE IF NOT EXISTS review_pool_meta (
    id              SERIAL PRIMARY KEY,
    platform        VARCHAR(20)  NOT NULL,
    product_key     VARCHAR(60)  NOT NULL,
    marketplace     VARCHAR(10)  NOT NULL DEFAULT 'us',
    total_reviews   INTEGER      NOT NULL DEFAULT 0,
    last_scraped_at TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    scraper_source  VARCHAR(40),

    CONSTRAINT uq_pool_meta_product
        UNIQUE (platform, product_key, marketplace)
);

COMMIT;
