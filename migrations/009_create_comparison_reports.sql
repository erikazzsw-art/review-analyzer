-- Migration 009: 对比报告表
-- 创建时间: 2026-06-05 (V2.5 多产品对比)
-- 说明: 存储版本对比 / 产品对比的快照结果

-- ========== UP ==========

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

CREATE INDEX IF NOT EXISTS idx_comparison_reports_user_id ON comparison_reports(user_id);

-- ========== DOWN ==========
-- DROP TABLE IF EXISTS comparison_reports CASCADE;
