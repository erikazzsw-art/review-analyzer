-- Migration 045: 添加 starter 套餐到 users.plan 约束
-- 创建时间: 2026-07-07
-- 说明: V4-出海-M6 新增 Starter 档位，需要在 CHECK 约束中允许 'starter'

BEGIN;

-- ========== UP ==========

-- 1) 删除旧约束
ALTER TABLE users DROP CONSTRAINT IF EXISTS chk_users_plan;

-- 2) 添加新约束（包含 starter）
ALTER TABLE users ADD CONSTRAINT chk_users_plan
    CHECK (plan IN ('free', 'starter', 'pro_early', 'pro', 'team'));

COMMENT ON CONSTRAINT chk_users_plan ON users IS
    'Allowed plans: free (300 credits) | starter (5K) | pro_early (15K legacy) | pro (15K) | team (45K)';

COMMIT;

-- ========== DOWN ==========
-- ALTER TABLE users DROP CONSTRAINT IF EXISTS chk_users_plan;
-- ALTER TABLE users ADD CONSTRAINT chk_users_plan CHECK (plan IN ('free', 'pro_early', 'pro', 'team'));
