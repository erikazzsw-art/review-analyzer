-- 032: Label Calibration Feedback Loop
-- 存储 Erika 对 LLM 标签的校准反馈，用于后续分析 prompt 注入 few-shot 样例

CREATE TABLE IF NOT EXISTS label_calibration (
    id            BIGSERIAL PRIMARY KEY,
    user_id       INTEGER NOT NULL REFERENCES users(id),
    comment_id    BIGINT,
    session_id    UUID,
    original_tag  TEXT NOT NULL,
    correct_tag   TEXT,
    note          TEXT,
    sub_category  TEXT NOT NULL DEFAULT '家具家居',
    status        TEXT NOT NULL DEFAULT 'active',
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_calibration_subcat_status
    ON label_calibration(sub_category, status);
