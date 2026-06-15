-- Migration 016: 推送快照 + 升级状态
-- 创建时间: 2026-06-14 (V5-T3 Step 1)
-- 说明: 记录每次推送的 TOP 问题排名快照，追踪连续命中次数用于升级判定

-- ========== UP ==========

CREATE TABLE IF NOT EXISTS push_snapshots (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    product_id INTEGER REFERENCES products(id),
    snapshot_type TEXT NOT NULL CHECK (snapshot_type IN ('batch', 'periodic')),
    period_start DATE,
    period_end DATE,
    top_issues JSONB NOT NULL DEFAULT '[]',
    top_highlights JSONB DEFAULT '[]',
    summary_stats JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS issue_escalation_state (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    product_id INTEGER REFERENCES products(id),
    tag_name TEXT NOT NULL,
    dept TEXT NOT NULL DEFAULT 'other',
    consecutive_count INTEGER NOT NULL DEFAULT 0,
    last_snapshot_id INTEGER REFERENCES push_snapshots(id),
    escalated_at TIMESTAMPTZ,
    action_item_id INTEGER REFERENCES action_items(id),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(user_id, product_id, tag_name)
);

CREATE INDEX idx_push_snapshots_user_product ON push_snapshots(user_id, product_id);
CREATE INDEX idx_push_snapshots_created ON push_snapshots(user_id, product_id, created_at DESC);
CREATE INDEX idx_escalation_state_lookup ON issue_escalation_state(user_id, product_id);

-- ========== DOWN ==========
-- DROP TABLE IF EXISTS issue_escalation_state CASCADE;
-- DROP TABLE IF EXISTS push_snapshots CASCADE;
