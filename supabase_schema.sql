-- Supabase PostgreSQL 建表脚本
-- 在 Supabase Dashboard > SQL Editor 中执行此脚本

CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    api_key_encrypted TEXT,
    plan TEXT NOT NULL DEFAULT 'free',
    paddle_customer_id TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS sessions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    product_id TEXT NOT NULL,
    version TEXT NOT NULL DEFAULT 'V1',
    auto_title TEXT,
    custom_title TEXT,
    date_range_start TEXT,
    date_range_end TEXT,
    total_reviews INTEGER DEFAULT 0,
    positive_count INTEGER DEFAULT 0,
    negative_count INTEGER DEFAULT 0,
    category TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS comments (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    product_id TEXT NOT NULL,
    version TEXT NOT NULL DEFAULT 'V1',
    content TEXT NOT NULL,
    rating INTEGER,
    date TEXT,
    reviewer TEXT,
    source TEXT,
    content_hash TEXT,
    sentiment TEXT,
    category TEXT,
    priority TEXT,
    reason TEXT,
    improvement TEXT,
    issue_tag TEXT DEFAULT '',
    highlight_tag TEXT DEFAULT '',
    is_processed INTEGER NOT NULL DEFAULT 0,
    session_id INTEGER REFERENCES sessions(id)
);

CREATE TABLE IF NOT EXISTS upload_jobs (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    status TEXT NOT NULL DEFAULT 'queued',
    source_filename TEXT NOT NULL,
    product_id TEXT NOT NULL,
    version TEXT NOT NULL DEFAULT 'V1',
    workflow_purpose TEXT,
    product_ref_id INTEGER REFERENCES products(id),
    variant_ref_id INTEGER REFERENCES product_variants(id),
    total_rows INTEGER NOT NULL DEFAULT 0,
    processed_rows INTEGER NOT NULL DEFAULT 0,
    positive_count INTEGER NOT NULL DEFAULT 0,
    negative_count INTEGER NOT NULL DEFAULT 0,
    session_id INTEGER REFERENCES sessions(id),
    error_message TEXT,
    payload_json JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS settings (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    key TEXT NOT NULL,
    value TEXT,
    UNIQUE(user_id, key)
);

-- 索引
CREATE INDEX IF NOT EXISTS idx_comments_user_id ON comments(user_id);
CREATE INDEX IF NOT EXISTS idx_comments_product_id ON comments(user_id, product_id);
CREATE INDEX IF NOT EXISTS idx_comments_session_id ON comments(session_id);
CREATE INDEX IF NOT EXISTS idx_comments_hash ON comments(user_id, content_hash);
CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_settings_user_key ON settings(user_id, key);
CREATE INDEX IF NOT EXISTS idx_upload_jobs_user_id ON upload_jobs(user_id);
CREATE INDEX IF NOT EXISTS idx_upload_jobs_status ON upload_jobs(user_id, status);

-- V2 RAG：评论向量检索（Supabase 需先启用 pgvector）
CREATE EXTENSION IF NOT EXISTS vector;
ALTER TABLE comments ADD COLUMN IF NOT EXISTS embedding vector(1536);
CREATE INDEX IF NOT EXISTS idx_comments_embedding
ON comments USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

-- V2 付费：Paddle 订阅状态
ALTER TABLE users ADD COLUMN IF NOT EXISTS plan TEXT NOT NULL DEFAULT 'free';
ALTER TABLE users ADD COLUMN IF NOT EXISTS paddle_customer_id TEXT;

-- 忘记密码功能（2026-05-15）
ALTER TABLE users ADD COLUMN IF NOT EXISTS email TEXT;

CREATE TABLE IF NOT EXISTS password_reset_tokens (
    id SERIAL PRIMARY KEY,
    email TEXT NOT NULL,
    token TEXT NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    used BOOLEAN NOT NULL DEFAULT FALSE
);
CREATE INDEX IF NOT EXISTS idx_reset_tokens_email ON password_reset_tokens(email);

-- V2 升级：新增 content_sentiment 字段（2026-05-25）
-- content_sentiment 基于评论文字内容判断，与评分无关，用于双版本正负率对比
ALTER TABLE comments ADD COLUMN IF NOT EXISTS content_sentiment TEXT;

-- V2 升级：新增 prompt_version 字段（2026-05-25）
-- 记录生成该批次分析结果时使用的 Prompt 版本，用于环比时检测口径一致性
ALTER TABLE sessions ADD COLUMN IF NOT EXISTS prompt_version TEXT;

-- V4-T3 升级：新增 V4 深度分析字段（2026-06-06）
-- aspects_json 存储 V4-T3 v2.1 prompt 完整输出（19 类 aspects + evidence_span + 多语言中立 canonical key）
-- analyzer_version 标识该评论使用哪个分析器版本：legacy（review_analyzer.analyzer）/ v4_deep（deep_analyzer）
-- 三层架构设计详见 docs/v4-t3-integration-plan-2026-06-06.md
ALTER TABLE comments ADD COLUMN IF NOT EXISTS aspects_json JSONB;
ALTER TABLE comments ADD COLUMN IF NOT EXISTS analyzer_version TEXT DEFAULT 'legacy';
CREATE INDEX IF NOT EXISTS idx_comments_analyzer_version ON comments(analyzer_version);

-- V2 升级：新增 version_notes 字段（2026-05-27）
-- 记录每个版本的升级说明，供版本对比视图展示
ALTER TABLE sessions ADD COLUMN IF NOT EXISTS version_notes TEXT;

-- ============================================================
-- V2.5 产品档案 / 行动闭环 / 复盘追踪
-- ============================================================

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
    platform TEXT,
    color TEXT,
    size TEXT,
    style TEXT,
    material TEXT,
    status TEXT DEFAULT 'active',
    launched_at TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(user_id, variant_sku)
);

-- V2.6 上传流程升级：工作目的与产品绑定
ALTER TABLE sessions ADD COLUMN IF NOT EXISTS workflow_purpose TEXT;
ALTER TABLE sessions ADD COLUMN IF NOT EXISTS product_ref_id INTEGER REFERENCES products(id);
ALTER TABLE sessions ADD COLUMN IF NOT EXISTS variant_ref_id INTEGER REFERENCES product_variants(id);

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

CREATE TABLE IF NOT EXISTS action_items (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    product_id INTEGER REFERENCES products(id),
    variant_id INTEGER REFERENCES product_variants(id),
    session_id INTEGER REFERENCES sessions(id),
    source_product_id TEXT,
    source_version TEXT,
    source_batch_label TEXT,
    title TEXT NOT NULL,
    tag_name TEXT NOT NULL,
    tag_type TEXT NOT NULL DEFAULT 'issue',
    current_pct NUMERIC(8, 2),
    owner_role TEXT NOT NULL,
    suggested_action TEXT,
    expected_effect_batch TEXT,
    expected_review_at TEXT,
    status TEXT NOT NULL DEFAULT 'todo',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS review_trackers (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    action_item_id INTEGER REFERENCES action_items(id),
    product_id INTEGER REFERENCES products(id),
    variant_id INTEGER REFERENCES product_variants(id),
    tracker_title TEXT NOT NULL,
    tag_name TEXT NOT NULL,
    baseline_pct NUMERIC(8, 2),
    improvement_action TEXT,
    effective_batch TEXT,
    review_scope TEXT,
    current_pct NUMERIC(8, 2),
    result_status TEXT NOT NULL DEFAULT 'pending',
    conclusion TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    closed_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS comparison_reports (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    comparison_type TEXT NOT NULL,
    title TEXT,
    filters_json JSONB,
    result_snapshot JSONB,
    summary TEXT,
    recommendations TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_products_user_id ON products(user_id);
CREATE INDEX IF NOT EXISTS idx_products_parent_product_id ON products(user_id, parent_product_id);
CREATE INDEX IF NOT EXISTS idx_product_variants_user_id ON product_variants(user_id);
CREATE INDEX IF NOT EXISTS idx_product_variants_product_id ON product_variants(product_id);
CREATE INDEX IF NOT EXISTS idx_product_versions_user_id ON product_versions(user_id);
CREATE INDEX IF NOT EXISTS idx_product_versions_product_id ON product_versions(product_id);
CREATE INDEX IF NOT EXISTS idx_action_items_user_id ON action_items(user_id);
CREATE INDEX IF NOT EXISTS idx_action_items_product_id ON action_items(product_id);
CREATE INDEX IF NOT EXISTS idx_action_items_status ON action_items(user_id, status);
CREATE INDEX IF NOT EXISTS idx_review_trackers_user_id ON review_trackers(user_id);
CREATE INDEX IF NOT EXISTS idx_review_trackers_product_id ON review_trackers(product_id);
CREATE INDEX IF NOT EXISTS idx_review_trackers_status ON review_trackers(user_id, result_status);
CREATE INDEX IF NOT EXISTS idx_comparison_reports_user_id ON comparison_reports(user_id);

-- V5.8: product_variants platform 字段 + 联合唯一索引 (Migration 050)
ALTER TABLE product_variants ADD COLUMN IF NOT EXISTS platform TEXT;
DROP INDEX IF EXISTS uq_product_variants_user_child_asin;
CREATE UNIQUE INDEX IF NOT EXISTS uq_product_variants_user_platform_child_asin
    ON product_variants (user_id, platform, child_asin)
    WHERE platform IS NOT NULL AND child_asin IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_product_variants_platform
    ON product_variants (platform)
    WHERE platform IS NOT NULL;
