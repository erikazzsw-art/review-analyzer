-- 041: 推送快照 + 问题升级状态表
-- 修复 P2-B: relation "push_snapshots" does not exist
-- 为 _post_analysis_smart_push 提供持久化存储

CREATE TABLE IF NOT EXISTS push_snapshots (
    id              SERIAL PRIMARY KEY,
    user_id         INTEGER NOT NULL,
    product_id      INTEGER,
    snapshot_type   TEXT    NOT NULL DEFAULT 'batch',
    period_start    TIMESTAMPTZ,
    period_end      TIMESTAMPTZ,
    top_issues      JSONB   NOT NULL DEFAULT '[]',
    top_highlights  JSONB   NOT NULL DEFAULT '[]',
    summary_stats   JSONB   NOT NULL DEFAULT '{}',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_push_snapshots_user_product
    ON push_snapshots(user_id, product_id, created_at DESC);

-- issue_escalation_state 也由同一模块管理，一并建表
CREATE TABLE IF NOT EXISTS issue_escalation_state (
    id                  SERIAL PRIMARY KEY,
    user_id             INTEGER NOT NULL,
    product_id          INTEGER,
    tag_name            TEXT    NOT NULL,
    dept                TEXT    NOT NULL DEFAULT '',
    consecutive_count   INTEGER NOT NULL DEFAULT 0,
    last_snapshot_id    INTEGER REFERENCES push_snapshots(id) ON DELETE SET NULL,
    escalated_at        TIMESTAMPTZ,
    action_item_id      INTEGER,
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    -- NULLS NOT DISTINCT: product_id=NULL 时仍能命中 ON CONFLICT（PG15+）
    UNIQUE NULLS NOT DISTINCT (user_id, product_id, tag_name)
);

CREATE INDEX IF NOT EXISTS idx_escalation_state_user_product
    ON issue_escalation_state(user_id, product_id);
