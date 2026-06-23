-- Migration 023: 批次去重指纹
-- 创建时间: 2026-06-23
-- 说明: 为 sessions 添加 batch_hash，防止同一用户同一产品重复上传相同评论集合

-- ========== UP ==========

ALTER TABLE sessions ADD COLUMN IF NOT EXISTS batch_hash TEXT;

CREATE UNIQUE INDEX IF NOT EXISTS idx_sessions_user_product_batch_hash
    ON sessions(user_id, product_id, batch_hash)
    WHERE batch_hash IS NOT NULL;

-- ========== DOWN ==========
-- DROP INDEX IF EXISTS idx_sessions_user_product_batch_hash;
-- ALTER TABLE sessions DROP COLUMN IF EXISTS batch_hash;
