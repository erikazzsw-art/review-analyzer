-- Supabase PostgreSQL 建表脚本
-- 在 Supabase Dashboard > SQL Editor 中执行此脚本

CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    api_key_encrypted TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

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
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

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
    category TEXT,
    priority TEXT,
    reason TEXT,
    improvement TEXT,
    issue_tag TEXT DEFAULT '',
    highlight_tag TEXT DEFAULT '',
    is_processed INTEGER NOT NULL DEFAULT 0,
    session_id INTEGER REFERENCES sessions(id)
);

CREATE TABLE IF NOT EXISTS settings (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    key TEXT NOT NULL,
    value TEXT,
    UNIQUE(user_id, key)
);

-- 索引
CREATE INDEX IF NOT EXISTS idx_comments_user_id ON comments(user_id);
CREATE INDEX IF NOT EXISTS idx_comments_product_id ON comments(user_id, product_id);
CREATE INDEX IF NOT EXISTS idx_comments_session_id ON comments(session_id);
CREATE INDEX IF NOT EXISTS idx_comments_hash ON comments(user_id, content_hash);
CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_settings_user_key ON settings(user_id, key);

-- 忘记密码功能（2026-05-15）
ALTER TABLE users ADD COLUMN IF NOT EXISTS email TEXT;

CREATE TABLE IF NOT EXISTS password_reset_tokens (
    id SERIAL PRIMARY KEY,
    email TEXT NOT NULL,
    token TEXT NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    used BOOLEAN NOT NULL DEFAULT FALSE
);
CREATE INDEX IF NOT EXISTS idx_reset_tokens_email ON password_reset_tokens(email);

-- V2 升级：新增 content_sentiment 字段（2026-05-25）
-- content_sentiment 基于评论文字内容判断，与评分无关，用于双版本正负率对比
ALTER TABLE comments ADD COLUMN IF NOT EXISTS content_sentiment TEXT;
