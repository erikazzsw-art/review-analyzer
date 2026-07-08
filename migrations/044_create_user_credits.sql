-- Migration 044: Credit 定价体系基建（user_credits + credit_ledger）
--
-- 目的：为海外 4 档套餐（Free/Starter/Pro/Team）建立统一 credit 池，
-- 替代现有 8 维独立限额，降低用户认知成本。
--
-- 保留 user_quota_usage 表，用于独立硬限（席位/API Keys/产品数/Webhook 数/规则数）。
-- 关联需求：V4-出海-M6 6.1

BEGIN;

-- ============================================================
-- 1) user_credits — 每个用户的 credit 钱包
-- ============================================================

CREATE TABLE IF NOT EXISTS user_credits (
    user_id       INT         PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    balance       INT         NOT NULL DEFAULT 0 CHECK (balance >= 0),
    monthly_grant INT         NOT NULL DEFAULT 300,
    trial_expires_at TIMESTAMPTZ,
    last_refill_at   TIMESTAMPTZ,
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

COMMENT ON TABLE  user_credits IS 'Credit 钱包：每用户一行，balance 当月剩余，monthly_grant 每月发放量';
COMMENT ON COLUMN user_credits.balance          IS '当前可用余额，不结转（每月 1 日重置为 monthly_grant）';
COMMENT ON COLUMN user_credits.monthly_grant    IS '套餐对应每月发放量：free=300 starter=5000 pro=15000 team=45000';
COMMENT ON COLUMN user_credits.trial_expires_at IS 'Trial 到期时间（注册后 +14 天），NULL 表示非 trial 状态';
COMMENT ON COLUMN user_credits.last_refill_at   IS '上次月度发放时间，防重复发放';

-- ============================================================
-- 2) credit_ledger — 每笔变动的流水账
-- ============================================================

CREATE TABLE IF NOT EXISTS credit_ledger (
    id            BIGSERIAL    PRIMARY KEY,
    user_id       INT          NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    delta         INT          NOT NULL,
    reason        VARCHAR(30)  NOT NULL,
    ref_id        TEXT,
    balance_after INT          NOT NULL,
    created_at    TIMESTAMPTZ  NOT NULL DEFAULT now()
);

COMMENT ON TABLE  credit_ledger IS 'Credit 流水：每次扣减/充值/退款记录一行';
COMMENT ON COLUMN credit_ledger.delta   IS '变动量：正数=充值/发放，负数=消费/扣减';
COMMENT ON COLUMN credit_ledger.reason  IS '动作类型：monthly_grant|trial|topup|refund|review_analyze|ask|insight|copywriter|translate|export|competitor';
COMMENT ON COLUMN credit_ledger.ref_id  IS '关联业务 ID（batch_id / ask_id / report_id 等），用于对账和退款';

-- reason 合法值约束
ALTER TABLE credit_ledger
    ADD CONSTRAINT chk_ledger_reason CHECK (
        reason IN (
            'monthly_grant', 'trial', 'topup', 'refund',
            'review_analyze', 'ask', 'insight',
            'copywriter', 'translate', 'export', 'competitor'
        )
    );

-- ============================================================
-- 3) 索引
-- ============================================================

-- 按用户时间倒序查近 30 条消费明细（ledger-drawer UI）
CREATE INDEX IF NOT EXISTS idx_ledger_user_time
    ON credit_ledger (user_id, created_at DESC);

-- 按 ref_id 查退款关联记录
CREATE INDEX IF NOT EXISTS idx_ledger_ref_id
    ON credit_ledger (ref_id)
    WHERE ref_id IS NOT NULL;

-- ============================================================
-- 4) updated_at 自动更新触发器
-- ============================================================

CREATE OR REPLACE FUNCTION update_user_credits_updated_at()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_user_credits_updated_at ON user_credits;
CREATE TRIGGER trg_user_credits_updated_at
    BEFORE UPDATE ON user_credits
    FOR EACH ROW EXECUTE FUNCTION update_user_credits_updated_at();

-- ============================================================
-- 5) Backfill：为所有现有用户初始化 user_credits
-- ============================================================
-- 按 users.plan 字段分配对应 monthly_grant，balance 初始化为 monthly_grant。
-- trial_expires_at=NULL（现有用户非 trial 状态）。

INSERT INTO user_credits (user_id, balance, monthly_grant, last_refill_at, updated_at)
SELECT
    id AS user_id,
    CASE
        WHEN plan = 'free' THEN 300
        WHEN plan = 'starter' THEN 5000
        WHEN plan = 'pro_early' THEN 15000
        WHEN plan = 'pro' THEN 15000
        WHEN plan = 'team' THEN 45000
        ELSE 300
    END AS balance,
    CASE
        WHEN plan = 'free' THEN 300
        WHEN plan = 'starter' THEN 5000
        WHEN plan = 'pro_early' THEN 15000
        WHEN plan = 'pro' THEN 15000
        WHEN plan = 'team' THEN 45000
        ELSE 300
    END AS monthly_grant,
    NOW() AS last_refill_at,
    NOW() AS updated_at
FROM users
ON CONFLICT (user_id) DO NOTHING;

-- 为 backfill 的每个用户写初始流水（reason='monthly_grant'）
INSERT INTO credit_ledger (user_id, delta, reason, balance_after, created_at)
SELECT
    user_id,
    balance AS delta,
    'monthly_grant' AS reason,
    balance AS balance_after,
    NOW() AS created_at
FROM user_credits
WHERE last_refill_at >= NOW() - INTERVAL '1 minute';

COMMIT;
