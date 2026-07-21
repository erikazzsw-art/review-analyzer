-- Migration 051: product_listings 表 — Chrome 扩展产品 Listing 数据存储
-- 创建时间: 2026-07-21 (Step 11.5 Chrome插件产品Listing抓取)
-- 说明: 存储从 Amazon 产品页抓取的完整 listing 信息（标题/价格/评分/Bullet Points/变体ASIN等）
--       与 products 表通过 product_id 1:1 关联
-- 依赖: 007_create_products.sql

-- ========== UP ==========

CREATE TABLE IF NOT EXISTS product_listings (
    id SERIAL PRIMARY KEY,
    product_id INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    parent_asin TEXT NOT NULL,
    marketplace TEXT,
    title TEXT,
    price NUMERIC(10,2),
    price_currency TEXT DEFAULT 'USD',
    original_price NUMERIC(10,2),
    rating NUMERIC(3,1),
    ratings_total INTEGER,
    reviews_total INTEGER,
    bullet_points JSONB DEFAULT '[]'::jsonb,
    main_image_url TEXT,
    brand TEXT,
    description TEXT,
    best_seller_rank JSONB DEFAULT '[]'::jsonb,
    dimensions TEXT,
    weight TEXT,
    seller_name TEXT,
    availability TEXT,
    variation_asins JSONB DEFAULT '[]'::jsonb,
    scraped_at TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(product_id)
);

CREATE INDEX IF NOT EXISTS idx_product_listings_product_id ON product_listings(product_id);
CREATE INDEX IF NOT EXISTS idx_product_listings_parent_asin ON product_listings(parent_asin);

-- ========== DOWN ==========
-- DROP TABLE IF EXISTS product_listings CASCADE;
