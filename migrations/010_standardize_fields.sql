-- Migration 010: 字段标准化 (V4-T2 Step 2.4)
-- 创建时间: 2026-06-10
-- 说明: 业务表统一加时间戳三件套 + CHECK 约束 + 复合索引

-- ========== UP ==========

-- 1. users 表: 加 updated_at + plan CHECK
ALTER TABLE users ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW();
ALTER TABLE users ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ;
ALTER TABLE users ADD COLUMN IF NOT EXISTS plan_locked_at TIMESTAMPTZ;
ALTER TABLE users DROP CONSTRAINT IF EXISTS chk_users_plan;
ALTER TABLE users ADD CONSTRAINT chk_users_plan CHECK (plan IN ('free', 'pro_early', 'pro', 'team'));

-- 2. sessions 表: 加 updated_at / deleted_at
ALTER TABLE sessions ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW();
ALTER TABLE sessions ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ;

-- 3. comments 表: 加 updated_at / deleted_at + CHECK 约束
ALTER TABLE comments ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW();
ALTER TABLE comments ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ;
ALTER TABLE comments DROP CONSTRAINT IF EXISTS chk_comments_rating;
ALTER TABLE comments ADD CONSTRAINT chk_comments_rating CHECK (rating IS NULL OR (rating BETWEEN 1 AND 5));
ALTER TABLE comments DROP CONSTRAINT IF EXISTS chk_comments_sentiment;
ALTER TABLE comments ADD CONSTRAINT chk_comments_sentiment CHECK (sentiment IS NULL OR sentiment IN ('positive', 'negative', 'neutral'));

-- 4. upload_jobs 表: 已有 updated_at，加 deleted_at
ALTER TABLE upload_jobs ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ;

-- 5. products 表: 加 updated_at / deleted_at
ALTER TABLE products ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW();
ALTER TABLE products ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ;

-- 6. product_variants 表: 加 updated_at / deleted_at
ALTER TABLE product_variants ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW();
ALTER TABLE product_variants ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ;

-- 7. action_items 表: 加 updated_at / deleted_at + status CHECK
ALTER TABLE action_items ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW();
ALTER TABLE action_items ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ;
ALTER TABLE action_items DROP CONSTRAINT IF EXISTS chk_action_items_status;
ALTER TABLE action_items ADD CONSTRAINT chk_action_items_status CHECK (status IN ('todo', 'in_progress', 'done', 'cancelled'));

-- 8. review_trackers 表: 加 updated_at / deleted_at
ALTER TABLE review_trackers ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW();
ALTER TABLE review_trackers ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ;

-- 9. updated_at 自动更新触发器
CREATE OR REPLACE FUNCTION trigger_set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DO $$
DECLARE
    tbl TEXT;
BEGIN
    FOR tbl IN SELECT unnest(ARRAY[
        'users', 'sessions', 'comments', 'upload_jobs',
        'products', 'product_variants', 'action_items', 'review_trackers'
    ]) LOOP
        EXECUTE format(
            'DROP TRIGGER IF EXISTS set_updated_at ON %I; '
            'CREATE TRIGGER set_updated_at BEFORE UPDATE ON %I '
            'FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();',
            tbl, tbl
        );
    END LOOP;
END $$;

-- 10. 高频查询复合索引
CREATE INDEX IF NOT EXISTS idx_comments_user_created ON comments(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_sessions_user_created ON sessions(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_action_items_user_created ON action_items(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_upload_jobs_user_created ON upload_jobs(user_id, created_at DESC);

-- ========== DOWN ==========
-- DROP INDEX IF EXISTS idx_upload_jobs_user_created;
-- DROP INDEX IF EXISTS idx_action_items_user_created;
-- DROP INDEX IF EXISTS idx_sessions_user_created;
-- DROP INDEX IF EXISTS idx_comments_user_created;
-- DROP TRIGGER IF EXISTS set_updated_at ON users;
-- ... (repeat for all tables)
-- DROP FUNCTION IF EXISTS trigger_set_updated_at();
-- ALTER TABLE users DROP CONSTRAINT IF EXISTS chk_users_plan;
-- ALTER TABLE comments DROP CONSTRAINT IF EXISTS chk_comments_rating;
-- ALTER TABLE comments DROP CONSTRAINT IF EXISTS chk_comments_sentiment;
-- ALTER TABLE action_items DROP CONSTRAINT IF EXISTS chk_action_items_status;
-- ALTER TABLE users DROP COLUMN IF EXISTS plan_locked_at;
-- ... (DROP updated_at / deleted_at for all tables)
