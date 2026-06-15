-- Migration 016: User Feedback table
-- 用户反馈浮窗组件存储

CREATE TABLE IF NOT EXISTS user_feedback (
    id BIGSERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    feedback_type TEXT NOT NULL,
    mood TEXT NOT NULL,
    message TEXT,
    page_path TEXT NOT NULL,
    user_agent TEXT,
    screenshot_url TEXT,
    metadata JSONB DEFAULT '{}',
    status TEXT NOT NULL DEFAULT 'new',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_feedback_user ON user_feedback(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_feedback_status ON user_feedback(status, created_at DESC);
