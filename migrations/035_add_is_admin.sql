-- 035: 用户表新增 is_admin 字段
-- 管理员可访问标签校准、可观测性等管理页面

ALTER TABLE users ADD COLUMN IF NOT EXISTS is_admin BOOLEAN NOT NULL DEFAULT FALSE;

-- 给测试账号 惜_clueai 管理者权限
UPDATE users SET is_admin = TRUE WHERE username = '惜_clueai';
