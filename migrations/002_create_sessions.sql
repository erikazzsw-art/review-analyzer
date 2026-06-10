-- Migration 002: 分析会话表
-- 创建时间: 2026-05-10 (项目初始化)
-- 说明: 每次上传分析对应一个 session

-- ========== UP ==========

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
    prompt_version TEXT,
    version_notes TEXT,
    workflow_purpose TEXT,
    product_ref_id INTEGER,
    variant_ref_id INTEGER,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON sessions(user_id);

-- ========== DOWN ==========
-- DROP TABLE IF EXISTS sessions CASCADE;
