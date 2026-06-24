-- Migration 026: 宣传文案理想产品画像缓存表
-- 创建时间: 2026-06-24 (Copywriter Revamp: 按产品+版本缓存 Ideal Profile)
-- 说明:
--   按 (user_id, product_id, version) 缓存一份理想产品画像 (LLM 生成)。
--   失效逻辑: 该 (产品, 版本) 范围内 latest_comment_id 变化时, generate 路由会 UPSERT 覆盖旧行。
--   version = 'ALL' 表示用户选择"全部版本"。

-- ========== UP ==========

CREATE TABLE IF NOT EXISTS ideal_profiles (
    id BIGSERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    product_id TEXT NOT NULL,
    version TEXT NOT NULL,
    comment_count_at_generation INTEGER NOT NULL,
    latest_comment_id_at_generation BIGINT NOT NULL,
    payload JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (user_id, product_id, version)
);

CREATE INDEX IF NOT EXISTS idx_ideal_profiles_lookup
    ON ideal_profiles (user_id, product_id, version);

COMMENT ON TABLE ideal_profiles IS '宣传文案页 Ideal Profile 缓存, 按用户/产品/版本去重';
COMMENT ON COLUMN ideal_profiles.version IS 'sessions.version, 或 ALL 表示用户选择全部版本';
COMMENT ON COLUMN ideal_profiles.latest_comment_id_at_generation IS '生成时该范围内最大 comment id, 用于增量失效';

-- ========== DOWN ==========
-- DROP TABLE IF EXISTS ideal_profiles;
