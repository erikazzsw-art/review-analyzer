-- Migration 001: 初始用户表
-- 创建时间: 2026-05-10 (项目初始化)
-- 说明: 用户注册/登录基础表

-- ========== UP ==========

CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    api_key_encrypted TEXT,
    plan TEXT NOT NULL DEFAULT 'free',
    paddle_customer_id TEXT,
    email TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ========== DOWN ==========
-- DROP TABLE IF EXISTS users CASCADE;
