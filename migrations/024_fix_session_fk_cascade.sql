-- Migration 024: 修复 session 外键约束，允许删除 session
-- 创建时间: 2026-06-23
-- 说明: upload_jobs 和 action_items 的 session_id FK 缺少 ON DELETE SET NULL，
--       导致删除 session 时被外键约束阻止。

-- ========== UP ==========

-- upload_jobs.session_id
ALTER TABLE upload_jobs DROP CONSTRAINT IF EXISTS upload_jobs_session_id_fkey;
ALTER TABLE upload_jobs
    ADD CONSTRAINT upload_jobs_session_id_fkey
    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE SET NULL;

-- action_items.session_id
ALTER TABLE action_items DROP CONSTRAINT IF EXISTS action_items_session_id_fkey;
ALTER TABLE action_items
    ADD CONSTRAINT action_items_session_id_fkey
    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE SET NULL;

-- ========== DOWN ==========
-- ALTER TABLE upload_jobs DROP CONSTRAINT IF EXISTS upload_jobs_session_id_fkey;
-- ALTER TABLE upload_jobs ADD CONSTRAINT upload_jobs_session_id_fkey FOREIGN KEY (session_id) REFERENCES sessions(id);
-- ALTER TABLE action_items DROP CONSTRAINT IF EXISTS action_items_session_id_fkey;
-- ALTER TABLE action_items ADD CONSTRAINT action_items_session_id_fkey FOREIGN KEY (session_id) REFERENCES sessions(id);
