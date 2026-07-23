-- Migration 056: Add user occupation tag for onboarding analytics
-- 创建时间: 2026-07-23
-- 说明: 首次登录采集用户职业标签，仅用于后续行为路径观察，不参与权限、页面分流或推送分责。

-- ========== UP ==========

DO $$
DECLARE
    has_occupation_status BOOLEAN;
BEGIN
    SELECT EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_name = 'users'
          AND column_name = 'occupation_tag_status'
    ) INTO has_occupation_status;

    ALTER TABLE users ADD COLUMN IF NOT EXISTS occupation_tag TEXT;
    ALTER TABLE users ADD COLUMN IF NOT EXISTS occupation_tag_status TEXT NOT NULL DEFAULT 'pending';
    ALTER TABLE users ADD COLUMN IF NOT EXISTS occupation_tag_collected_at TIMESTAMPTZ;
    ALTER TABLE users ADD COLUMN IF NOT EXISTS occupation_tag_skipped_at TIMESTAMPTZ;
    ALTER TABLE users ADD COLUMN IF NOT EXISTS occupation_tag_updated_at TIMESTAMPTZ;

    -- 首次执行 migration 时，已有用户不弹窗；后续新注册用户使用 DEFAULT 'pending'。
    IF NOT has_occupation_status THEN
        UPDATE users
        SET occupation_tag_status = 'not_required',
            occupation_tag_updated_at = NOW()
        WHERE occupation_tag_status = 'pending';
    END IF;
END $$;

ALTER TABLE users DROP CONSTRAINT IF EXISTS chk_users_occupation_tag;
ALTER TABLE users ADD CONSTRAINT chk_users_occupation_tag
    CHECK (
        occupation_tag IS NULL OR occupation_tag IN (
            'operations',
            'product_manager',
            'management',
            'customer_service',
            'quality_control',
            'other'
        )
    );

ALTER TABLE users DROP CONSTRAINT IF EXISTS chk_users_occupation_tag_status;
ALTER TABLE users ADD CONSTRAINT chk_users_occupation_tag_status
    CHECK (occupation_tag_status IN ('pending', 'completed', 'skipped', 'not_required'));

CREATE INDEX IF NOT EXISTS idx_users_occupation_tag
    ON users (occupation_tag)
    WHERE occupation_tag IS NOT NULL;

COMMENT ON COLUMN users.occupation_tag IS '用户自选职业标签，仅用于行为分析，不参与权限、页面分流或推送分责';
COMMENT ON COLUMN users.occupation_tag_status IS '职业标签采集状态: pending/completed/skipped/not_required';
COMMENT ON COLUMN users.occupation_tag_collected_at IS '用户完成职业标签选择的时间';
COMMENT ON COLUMN users.occupation_tag_skipped_at IS '用户选择稍后再说的时间';
COMMENT ON COLUMN users.occupation_tag_updated_at IS '职业标签状态最近更新时间';

-- ========== DOWN ==========
-- DROP INDEX IF EXISTS idx_users_occupation_tag;
-- ALTER TABLE users DROP CONSTRAINT IF EXISTS chk_users_occupation_tag_status;
-- ALTER TABLE users DROP CONSTRAINT IF EXISTS chk_users_occupation_tag;
-- ALTER TABLE users DROP COLUMN IF EXISTS occupation_tag_updated_at;
-- ALTER TABLE users DROP COLUMN IF EXISTS occupation_tag_skipped_at;
-- ALTER TABLE users DROP COLUMN IF EXISTS occupation_tag_collected_at;
-- ALTER TABLE users DROP COLUMN IF EXISTS occupation_tag_status;
-- ALTER TABLE users DROP COLUMN IF EXISTS occupation_tag;
