-- Migration 017: 评论来源渠道字段
-- 创建时间: 2026-06-15 (V5-T1 评论自动获取)
-- 说明: 区分评论来源渠道: manual(手动上传), plugin(Chrome插件), api(Rainforest API自动拉取)

-- ========== UP ==========

ALTER TABLE comments ADD COLUMN IF NOT EXISTS source_channel TEXT NOT NULL DEFAULT 'manual';
ALTER TABLE upload_jobs ADD COLUMN IF NOT EXISTS source_channel TEXT NOT NULL DEFAULT 'manual';

CREATE INDEX IF NOT EXISTS idx_comments_source_channel ON comments(user_id, source_channel);

-- ========== DOWN ==========
-- ALTER TABLE comments DROP COLUMN IF EXISTS source_channel;
-- ALTER TABLE upload_jobs DROP COLUMN IF EXISTS source_channel;
-- DROP INDEX IF EXISTS idx_comments_source_channel;
