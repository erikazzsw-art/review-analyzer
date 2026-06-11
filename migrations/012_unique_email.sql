-- Migration 012: 邮箱唯一约束
-- 创建时间: 2026-06-11
-- 说明: 限制一个邮箱只能注册一个账号

-- ========== UP ==========

ALTER TABLE users ADD CONSTRAINT users_email_unique UNIQUE (email);

-- ========== DOWN ==========
-- ALTER TABLE users DROP CONSTRAINT users_email_unique;
