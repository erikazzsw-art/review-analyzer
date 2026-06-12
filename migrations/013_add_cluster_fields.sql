-- V4-T4 Step 2: 聚类前置层字段
-- 2026-06-12

ALTER TABLE comments ADD COLUMN IF NOT EXISTS cluster_id INTEGER;
ALTER TABLE comments ADD COLUMN IF NOT EXISTS cluster_representative_id INTEGER;

COMMENT ON COLUMN comments.cluster_id IS 'HDBSCAN 聚类标签（session 内局部，-1=noise）';
COMMENT ON COLUMN comments.cluster_representative_id IS '该评论的聚类代表 comment ID（代表指向自己）';
