-- V4-T4 Step 5: LLM 用量日志表（Token 成本看板）
-- 2026-06-12

CREATE TABLE IF NOT EXISTS llm_usage_log (
    id BIGSERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    session_id INTEGER,
    comment_id INTEGER,
    model_name VARCHAR(32) NOT NULL,
    tokens_in INTEGER NOT NULL DEFAULT 0,
    tokens_out INTEGER NOT NULL DEFAULT 0,
    cost_yuan NUMERIC(10, 6) NOT NULL DEFAULT 0,
    sub_category VARCHAR(64),
    cache_hit BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_llm_usage_user_date
    ON llm_usage_log (user_id, created_at);

CREATE INDEX IF NOT EXISTS idx_llm_usage_model_date
    ON llm_usage_log (model_name, created_at);

COMMENT ON TABLE llm_usage_log IS '每次 LLM 调用的 token 用量和成本记录';
COMMENT ON COLUMN llm_usage_log.cost_yuan IS '本次调用的估算成本（人民币元）';
COMMENT ON COLUMN llm_usage_log.cache_hit IS '是否命中缓存（命中时 tokens=0, cost=0）';
