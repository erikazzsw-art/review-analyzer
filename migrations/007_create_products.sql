-- Migration 007: 产品档案体系
-- 创建时间: 2026-06-04 (V2.5 产品管理)
-- 说明: 产品 / 变体 / 版本三层结构，支持产品档案完整管理

-- ========== UP ==========

CREATE TABLE IF NOT EXISTS products (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    parent_product_id TEXT NOT NULL,
    name TEXT,
    platform TEXT,
    category TEXT,
    lifecycle_stage TEXT DEFAULT 'growth',
    current_version TEXT DEFAULT 'V1',
    core_selling_points TEXT,
    main_competitors TEXT,
    owner_role TEXT,
    production_cycle_days INTEGER,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(user_id, parent_product_id)
);

CREATE TABLE IF NOT EXISTS product_variants (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    product_id INTEGER NOT NULL REFERENCES products(id),
    variant_sku TEXT NOT NULL,
    child_asin TEXT,
    color TEXT,
    size TEXT,
    style TEXT,
    material TEXT,
    status TEXT DEFAULT 'active',
    launched_at TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(user_id, variant_sku)
);

CREATE TABLE IF NOT EXISTS product_versions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    product_id INTEGER NOT NULL REFERENCES products(id),
    variant_id INTEGER REFERENCES product_variants(id),
    version_name TEXT NOT NULL,
    version_notes TEXT,
    change_summary TEXT,
    launched_at TEXT,
    is_current BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(user_id, product_id, version_name)
);

CREATE INDEX IF NOT EXISTS idx_products_user_id ON products(user_id);
CREATE INDEX IF NOT EXISTS idx_products_parent_product_id ON products(user_id, parent_product_id);
CREATE INDEX IF NOT EXISTS idx_product_variants_user_id ON product_variants(user_id);
CREATE INDEX IF NOT EXISTS idx_product_variants_product_id ON product_variants(product_id);
CREATE INDEX IF NOT EXISTS idx_product_versions_user_id ON product_versions(user_id);
CREATE INDEX IF NOT EXISTS idx_product_versions_product_id ON product_versions(product_id);

-- upload_jobs 外键延后添加（004 创建时 products/product_variants 尚不存在）
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints
        WHERE constraint_name = 'fk_upload_jobs_product_ref'
    ) THEN
        ALTER TABLE upload_jobs ADD CONSTRAINT fk_upload_jobs_product_ref
            FOREIGN KEY (product_ref_id) REFERENCES products(id);
    END IF;
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints
        WHERE constraint_name = 'fk_upload_jobs_variant_ref'
    ) THEN
        ALTER TABLE upload_jobs ADD CONSTRAINT fk_upload_jobs_variant_ref
            FOREIGN KEY (variant_ref_id) REFERENCES product_variants(id);
    END IF;
END $$;

-- ========== DOWN ==========
-- DROP TABLE IF EXISTS product_versions CASCADE;
-- DROP TABLE IF EXISTS product_variants CASCADE;
-- DROP TABLE IF EXISTS products CASCADE;
