-- 033: Golden Set — 标签校准标杆数据
-- 存储人工标注的正确/错误标签示例，用于：
-- 1. 方案A: 统计各标签准确率
-- 2. 方案B: 精选 few-shot 注入 prompt
-- 3. 方案D(未来): 构建 aspect embedding 质心

CREATE TABLE IF NOT EXISTS golden_set (
    id              BIGSERIAL PRIMARY KEY,
    user_id         INTEGER NOT NULL REFERENCES users(id),
    comment_text    TEXT NOT NULL,
    aspect_key      TEXT NOT NULL,
    is_correct      BOOLEAN NOT NULL,
    reason          TEXT,
    correct_tag     TEXT,
    sub_category    TEXT NOT NULL DEFAULT '家具家居',
    source          TEXT NOT NULL DEFAULT 'manual',
    use_as_fewshot  BOOLEAN NOT NULL DEFAULT FALSE,
    batch_id        TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_golden_set_aspect
    ON golden_set(aspect_key, is_correct);

CREATE INDEX IF NOT EXISTS idx_golden_set_subcat
    ON golden_set(sub_category, aspect_key);

CREATE INDEX IF NOT EXISTS idx_golden_set_fewshot
    ON golden_set(use_as_fewshot, aspect_key)
    WHERE use_as_fewshot = TRUE;

COMMENT ON TABLE golden_set IS '标签校准标杆数据 — 人工标注的正确/错误示例';
COMMENT ON COLUMN golden_set.source IS 'manual=人工上传, auto_seed=历史高置信度自动填充';
COMMENT ON COLUMN golden_set.use_as_fewshot IS '是否被选为 few-shot 注入 prompt 的典型示例';
COMMENT ON COLUMN golden_set.batch_id IS '批次标识，同一次上传的记录共享';
