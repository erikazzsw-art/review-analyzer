-- Migration 048: V4-出海-M2.3/2.5 — 合规字段 + 用户语言偏好
-- 创建时间: 2026-07-13
-- 目的: users 表新增 6 列，支撑后端 i18n 语言偏好 + 注册合规（Terms/年龄/Marketing）
--
-- 关联:
--   - M2.3 Backend i18n 基础层: locale 字段供 get_locale dependency 读取
--   - M2.5 注册流程: terms_accepted_at / terms_version / age_confirmed_at / marketing_opt_in
--   - OVERSEAS_COMPLIANCE_PLAN.md 2.5 节

-- ========== UP ==========

-- 用户 UI 语言偏好，默认 en-US（海外优先）。前端 next-intl 写入，后端读取。
ALTER TABLE users ADD COLUMN IF NOT EXISTS locale VARCHAR(10) DEFAULT 'en-US';

-- 条款接受时间。老用户为 NULL，登录后通过 terms-gate modal 补填。
ALTER TABLE users ADD COLUMN IF NOT EXISTS terms_accepted_at TIMESTAMPTZ;

-- 接受的条款版本号（如 "2.0"）。用于判定老用户是否需要重新同意。
ALTER TABLE users ADD COLUMN IF NOT EXISTS terms_version TEXT;

-- 年龄确认时间（18+）。注册时必须勾选。
ALTER TABLE users ADD COLUMN IF NOT EXISTS age_confirmed_at TIMESTAMPTZ;

-- 营销邮件 opt-in 开关。默认 OFF（GDPR/CCPA 要求 opt-in 而非 opt-out）。
ALTER TABLE users ADD COLUMN IF NOT EXISTS marketing_opt_in BOOLEAN DEFAULT FALSE;

-- opt-in 时间戳，用于审计 trail。
ALTER TABLE users ADD COLUMN IF NOT EXISTS marketing_opt_in_at TIMESTAMPTZ;

COMMENT ON COLUMN users.locale IS 'V4-出海-M2.3: 用户 UI 语言偏好 (en-US/zh-CN 等), 默认 en-US';
COMMENT ON COLUMN users.terms_accepted_at IS 'V4-出海-M2.5: 用户最近一次接受 Terms of Service 的时间';
COMMENT ON COLUMN users.terms_version IS 'V4-出海-M2.5: 用户已接受的 Terms 版本号 (如 2.0)';
COMMENT ON COLUMN users.age_confirmed_at IS 'V4-出海-M2.5: 用户确认年满 18 岁的时间';
COMMENT ON COLUMN users.marketing_opt_in IS 'V4-出海-M2.5: 用户是否同意接收营销邮件, 默认 OFF';
COMMENT ON COLUMN users.marketing_opt_in_at IS 'V4-出海-M2.5: 营销 opt-in 变更时间';

-- ========== DOWN ==========
-- ALTER TABLE users DROP COLUMN IF EXISTS marketing_opt_in_at;
-- ALTER TABLE users DROP COLUMN IF EXISTS marketing_opt_in;
-- ALTER TABLE users DROP COLUMN IF EXISTS age_confirmed_at;
-- ALTER TABLE users DROP COLUMN IF EXISTS terms_version;
-- ALTER TABLE users DROP COLUMN IF EXISTS terms_accepted_at;
-- ALTER TABLE users DROP COLUMN IF EXISTS locale;
