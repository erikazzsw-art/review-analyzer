-- Migration 011: 配额计数表 (V4-T2 Step 3)
-- 创建时间: 2026-06-10
-- 说明: 用户配额用量追踪，支持月度重置和原子校验

-- ========== UP ==========

CREATE TABLE IF NOT EXISTS user_quota_usage (
    user_id INTEGER NOT NULL REFERENCES users(id),
    dimension TEXT NOT NULL,
    period_start DATE NOT NULL,
    used_count INTEGER NOT NULL DEFAULT 0,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (user_id, dimension, period_start)
);

CREATE INDEX IF NOT EXISTS idx_quota_user ON user_quota_usage(user_id, period_start);
CREATE INDEX IF NOT EXISTS idx_quota_dimension ON user_quota_usage(user_id, dimension, period_start DESC);

-- ========== DOWN ==========
-- DROP TABLE IF EXISTS user_quota_usage CASCADE;
