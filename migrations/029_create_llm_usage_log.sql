-- 029: 创建 llm_usage_log 表，记录每次 LLM 调用的用量和成本
CREATE TABLE IF NOT EXISTS llm_usage_log (
    id BIGSERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    session_id INTEGER,
    comment_id INTEGER,
    model_name VARCHAR(64) NOT NULL,
    tokens_in INTEGER NOT NULL DEFAULT 0,
    tokens_out INTEGER NOT NULL DEFAULT 0,
    cost_yuan NUMERIC(10, 6) NOT NULL DEFAULT 0,
    sub_category VARCHAR(64),
    cache_hit BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_llm_usage_log_user_id ON llm_usage_log (user_id);
CREATE INDEX IF NOT EXISTS idx_llm_usage_log_created_at ON llm_usage_log (created_at);
