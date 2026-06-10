-- Migration 003: 评论表
-- 创建时间: 2026-05-10 (项目初始化)
-- 说明: 存储用户上传的评论及 LLM 分析结果

-- ========== UP ==========

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
    content_sentiment TEXT,
    category TEXT,
    priority TEXT,
    reason TEXT,
    improvement TEXT,
    issue_tag TEXT DEFAULT '',
    highlight_tag TEXT DEFAULT '',
    is_processed INTEGER NOT NULL DEFAULT 0,
    session_id INTEGER REFERENCES sessions(id),
    aspects_json JSONB,
    analyzer_version TEXT DEFAULT 'legacy',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_comments_user_id ON comments(user_id);
CREATE INDEX IF NOT EXISTS idx_comments_product_id ON comments(user_id, product_id);
CREATE INDEX IF NOT EXISTS idx_comments_session_id ON comments(session_id);
CREATE INDEX IF NOT EXISTS idx_comments_hash ON comments(user_id, content_hash);
CREATE INDEX IF NOT EXISTS idx_comments_analyzer_version ON comments(analyzer_version);

-- ========== DOWN ==========
-- DROP TABLE IF EXISTS comments CASCADE;
