-- Migration 004: 上传任务队列表
-- 创建时间: 2026-06-01 (NX-M3 异步队列)
-- 说明: RQ worker 异步分析任务状态追踪

-- ========== UP ==========

CREATE TABLE IF NOT EXISTS upload_jobs (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    status TEXT NOT NULL DEFAULT 'queued',
    source_filename TEXT NOT NULL,
    product_id TEXT NOT NULL,
    version TEXT NOT NULL DEFAULT 'V1',
    workflow_purpose TEXT,
    product_ref_id INTEGER,
    variant_ref_id INTEGER,
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

CREATE INDEX IF NOT EXISTS idx_upload_jobs_user_id ON upload_jobs(user_id);
CREATE INDEX IF NOT EXISTS idx_upload_jobs_status ON upload_jobs(user_id, status);

-- ========== DOWN ==========
-- DROP TABLE IF EXISTS upload_jobs CASCADE;
