-- Migration 050: product_variants 新增 platform 字段 + 联合唯一索引
-- 创建时间: 2026-07-20 (V5.8 产品管理功能增强)
-- 说明: 为变体表增加平台维度，支持跨平台同名 ASIN 共存；
--       历史数据 platform 为 NULL，不受新唯一约束影响（历史数据不迁移）。
-- 依赖: 007_create_products.sql (product_variants 表), 031_add_product_catalog_fields.sql (child_asin 唯一索引)

-- ========== UP ==========

-- 1. 新增 platform 字段
ALTER TABLE product_variants ADD COLUMN IF NOT EXISTS platform TEXT;

-- 2. 删除旧的 (user_id, child_asin) 唯一索引（仅约束 child_asin IS NOT NULL 的行）
--    031 创建了 uq_product_variants_user_child_asin，替换为下面的三字段联合索引
DROP INDEX IF EXISTS uq_product_variants_user_child_asin;

-- 3. 创建联合唯一索引 (user_id, platform, child_asin)
--    PostgreSQL 将 NULL 视为 distinct，故历史数据 (platform=NULL) 的多条同 child_asin 记录不会冲突
--    新增数据按 (user_id, platform, child_asin) 保证唯一性
CREATE UNIQUE INDEX IF NOT EXISTS uq_product_variants_user_platform_child_asin
    ON product_variants (user_id, platform, child_asin)
    WHERE platform IS NOT NULL AND child_asin IS NOT NULL;

-- 4. 为 platform 创建普通索引，加速按平台筛选查询
CREATE INDEX IF NOT EXISTS idx_product_variants_platform
    ON product_variants (platform)
    WHERE platform IS NOT NULL;

-- ========== DOWN ==========
-- DROP INDEX IF EXISTS idx_product_variants_platform;
-- DROP INDEX IF EXISTS uq_product_variants_user_platform_child_asin;
-- CREATE UNIQUE INDEX IF NOT EXISTS uq_product_variants_user_child_asin
--     ON product_variants (user_id, child_asin)
--     WHERE child_asin IS NOT NULL;
-- ALTER TABLE product_variants DROP COLUMN IF EXISTS platform;
