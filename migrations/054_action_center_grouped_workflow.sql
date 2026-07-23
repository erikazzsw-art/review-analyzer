-- Migration 054: Action Center grouped workflow
-- 创建时间: 2026-07-23
-- 说明:
--   1. 行动中心按产品/父体分组，支持产品备注和产品排序。
--   2. 行动事项支持同产品内排序、软移除、逐条 AI 建议编辑。
--   3. 长期状态收敛为处理中、复盘中、已完结；历史 todo 回填为处理中。

-- ========== UP ==========

BEGIN;

ALTER TABLE action_items
    ADD COLUMN IF NOT EXISTS sort_order INTEGER,
    ADD COLUMN IF NOT EXISTS ai_suggestions_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    ADD COLUMN IF NOT EXISTS removed_at TIMESTAMPTZ;

ALTER TABLE action_items
    ALTER COLUMN status SET DEFAULT 'in_progress';

UPDATE action_items
SET status = 'in_progress'
WHERE status = 'todo';

WITH ranked AS (
    SELECT
        id,
        ROW_NUMBER() OVER (
            PARTITION BY COALESCE(
                CASE WHEN product_id IS NOT NULL THEN 'product:' || product_id::text END,
                CASE WHEN NULLIF(source_product_id, '') IS NOT NULL THEN 'source:' || source_product_id END,
                CASE WHEN session_id IS NOT NULL THEN 'session:' || session_id::text END,
                'unbound'
            )
            ORDER BY created_at DESC, id DESC
        ) - 1 AS rn
    FROM action_items
    WHERE removed_at IS NULL
)
UPDATE action_items ai
SET sort_order = ranked.rn
FROM ranked
WHERE ai.id = ranked.id
  AND ai.sort_order IS NULL;

CREATE TABLE IF NOT EXISTS action_center_product_groups (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    product_group_key TEXT NOT NULL,
    note TEXT,
    sort_order INTEGER,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(user_id, product_group_key)
);

CREATE INDEX IF NOT EXISTS idx_action_items_user_removed
    ON action_items(user_id, removed_at);
CREATE INDEX IF NOT EXISTS idx_action_items_user_sort
    ON action_items(user_id, sort_order);
CREATE INDEX IF NOT EXISTS idx_action_center_product_groups_user
    ON action_center_product_groups(user_id, sort_order);

COMMIT;

-- ========== DOWN ==========
-- DROP TABLE IF EXISTS action_center_product_groups CASCADE;
-- ALTER TABLE action_items DROP COLUMN IF EXISTS removed_at;
-- ALTER TABLE action_items DROP COLUMN IF EXISTS ai_suggestions_json;
-- ALTER TABLE action_items DROP COLUMN IF EXISTS sort_order;
-- ALTER TABLE action_items ALTER COLUMN status SET DEFAULT 'todo';
