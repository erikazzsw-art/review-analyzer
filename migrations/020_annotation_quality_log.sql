-- Migration 020: annotation_quality_log table for OPT-5 quality sampling
CREATE TABLE IF NOT EXISTS annotation_quality_log (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    comment_id INTEGER NOT NULL,
    prompt_version VARCHAR(20) NOT NULL,
    verdict VARCHAR(20) NOT NULL,
    reason TEXT DEFAULT '',
    judge_model VARCHAR(50) DEFAULT '',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(comment_id, prompt_version)
);

CREATE INDEX IF NOT EXISTS idx_quality_log_user_date
ON annotation_quality_log (user_id, created_at DESC);
