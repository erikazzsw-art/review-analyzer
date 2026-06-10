-- Migration 008: 行动闭环 + 复盘追踪
-- 创建时间: 2026-06-05 (V2.5 行动中心)
-- 说明: 从分析结果生成待办 → 跟踪改进效果

-- ========== UP ==========

CREATE TABLE IF NOT EXISTS action_items (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    product_id INTEGER REFERENCES products(id),
    variant_id INTEGER REFERENCES product_variants(id),
    session_id INTEGER REFERENCES sessions(id),
    source_product_id TEXT,
    source_version TEXT,
    source_batch_label TEXT,
    title TEXT NOT NULL,
    tag_name TEXT NOT NULL,
    tag_type TEXT NOT NULL DEFAULT 'issue',
    current_pct NUMERIC(8, 2),
    owner_role TEXT NOT NULL,
    suggested_action TEXT,
    expected_effect_batch TEXT,
    expected_review_at TEXT,
    status TEXT NOT NULL DEFAULT 'todo',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS review_trackers (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    action_item_id INTEGER REFERENCES action_items(id),
    product_id INTEGER REFERENCES products(id),
    variant_id INTEGER REFERENCES product_variants(id),
    tracker_title TEXT NOT NULL,
    tag_name TEXT NOT NULL,
    baseline_pct NUMERIC(8, 2),
    improvement_action TEXT,
    effective_batch TEXT,
    review_scope TEXT,
    current_pct NUMERIC(8, 2),
    result_status TEXT NOT NULL DEFAULT 'pending',
    conclusion TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    closed_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_action_items_user_id ON action_items(user_id);
CREATE INDEX IF NOT EXISTS idx_action_items_product_id ON action_items(product_id);
CREATE INDEX IF NOT EXISTS idx_action_items_status ON action_items(user_id, status);
CREATE INDEX IF NOT EXISTS idx_review_trackers_user_id ON review_trackers(user_id);
CREATE INDEX IF NOT EXISTS idx_review_trackers_product_id ON review_trackers(product_id);
CREATE INDEX IF NOT EXISTS idx_review_trackers_status ON review_trackers(user_id, result_status);

-- ========== DOWN ==========
-- DROP TABLE IF EXISTS review_trackers CASCADE;
-- DROP TABLE IF EXISTS action_items CASCADE;
