-- Migration 042: V4-出海-M3.5 数据保留策略 — inactivity 追踪字段
-- 创建时间: 2026-07-07
-- 目的: 为 workers/retention_cleanup.py 提供 6 个月 inactive 判定所需的时间戳。
--
-- 关联:
--   - CCPA/CPRA 要求"不能无限期保留数据",Privacy Policy 声明的保留期见
--     OVERSEAS_COMPLIANCE_PLAN.md 3.5 节。
--   - anonymize_user() 走 M3.2 已有的逻辑;这里只补两个字段。

-- ========== UP ==========

-- 用户最近一次成功登录时间。retention_cleanup 用它判定 6 个月 inactive。
-- 建表初值为 NULL,现存老用户在下面用 COALESCE(created_at) 兜底,避免全部误判为 inactive。
ALTER TABLE users ADD COLUMN IF NOT EXISTS last_login_at TIMESTAMPTZ;

-- Inactive 通知邮件的发送时间。发出后再等 90 天才匿名化;重新登录会清零。
ALTER TABLE users ADD COLUMN IF NOT EXISTS inactivity_notified_at TIMESTAMPTZ;

-- 老用户兜底:把 NULL 的 last_login_at 回填为 created_at,让"最近登录"至少不早于账号创建时间。
-- 未来 M3.5 首次运行 retention_cleanup 时,若某老用户从未登录过且 created_at 已超 6 个月,会正常进入通知流程。
UPDATE users
SET last_login_at = created_at
WHERE last_login_at IS NULL;

-- retention_cleanup 每日扫全表,给 last_login_at 加索引避免 seq scan。
-- deleted_at IS NULL 部分索引把已匿名化用户排除,减小索引体积。
CREATE INDEX IF NOT EXISTS idx_users_last_login_active
    ON users (last_login_at)
    WHERE deleted_at IS NULL;

-- 已通知但未匿名化的用户单独一个部分索引,清理任务只在很小的子集上扫描。
CREATE INDEX IF NOT EXISTS idx_users_inactivity_notified
    ON users (inactivity_notified_at)
    WHERE deleted_at IS NULL AND inactivity_notified_at IS NOT NULL;

COMMENT ON COLUMN users.last_login_at IS 'V4-出海-M3.5: 最近一次成功登录时间, retention_cleanup 判定 inactive 用';
COMMENT ON COLUMN users.inactivity_notified_at IS 'V4-出海-M3.5: inactivity 警告邮件发送时间, 发出 90 天后触发匿名化; 重新登录时清零';

-- ========== DOWN ==========
-- DROP INDEX IF EXISTS idx_users_inactivity_notified;
-- DROP INDEX IF EXISTS idx_users_last_login_active;
-- ALTER TABLE users DROP COLUMN IF EXISTS inactivity_notified_at;
-- ALTER TABLE users DROP COLUMN IF EXISTS last_login_at;
