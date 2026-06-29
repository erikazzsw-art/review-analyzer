-- 031: 产品目录增强 — 新增图片、品牌、评分、价格等字段
-- 用于 ASIN 抓取时自动保存产品信息到产品管理模块

-- products 表新增字段
ALTER TABLE products ADD COLUMN IF NOT EXISTS image_url TEXT;
ALTER TABLE products ADD COLUMN IF NOT EXISTS brand TEXT;
ALTER TABLE products ADD COLUMN IF NOT EXISTS rating NUMERIC(3,1);
ALTER TABLE products ADD COLUMN IF NOT EXISTS ratings_total INTEGER;
ALTER TABLE products ADD COLUMN IF NOT EXISTS reviews_total INTEGER;

-- product_variants 表新增字段
ALTER TABLE product_variants ADD COLUMN IF NOT EXISTS image_url TEXT;
ALTER TABLE product_variants ADD COLUMN IF NOT EXISTS name TEXT;
ALTER TABLE product_variants ADD COLUMN IF NOT EXISTS brand TEXT;
ALTER TABLE product_variants ADD COLUMN IF NOT EXISTS price NUMERIC(10,2);
ALTER TABLE product_variants ADD COLUMN IF NOT EXISTS price_currency TEXT DEFAULT 'USD';
ALTER TABLE product_variants ADD COLUMN IF NOT EXISTS sales_volume INTEGER;
ALTER TABLE product_variants ADD COLUMN IF NOT EXISTS sales_revenue NUMERIC(12,2);
ALTER TABLE product_variants ADD COLUMN IF NOT EXISTS is_fba BOOLEAN;
ALTER TABLE product_variants ADD COLUMN IF NOT EXISTS listing_date TEXT;

-- 为 child_asin 添加唯一约束（用于 upsert 冲突判断）
-- 同一用户下同一 child_asin 只对应一条变体记录
CREATE UNIQUE INDEX IF NOT EXISTS uq_product_variants_user_child_asin
    ON product_variants (user_id, child_asin)
    WHERE child_asin IS NOT NULL;
