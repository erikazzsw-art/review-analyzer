-- Migration 036: asin_watchlist 多平台支持 + 静默重试
-- 新增 platform 列（默认 amazon），retry_count 列
-- 调整唯一约束适配多平台

BEGIN;

ALTER TABLE asin_watchlist ADD COLUMN IF NOT EXISTS platform TEXT NOT NULL DEFAULT 'amazon';
ALTER TABLE asin_watchlist ADD COLUMN IF NOT EXISTS retry_count INTEGER NOT NULL DEFAULT 0;

ALTER TABLE asin_watchlist DROP CONSTRAINT IF EXISTS asin_watchlist_user_id_asin_marketplace_key;

ALTER TABLE asin_watchlist ADD CONSTRAINT asin_watchlist_user_platform_asin_marketplace_key
    UNIQUE(user_id, platform, asin, marketplace);

CREATE INDEX IF NOT EXISTS idx_asin_watchlist_platform
    ON asin_watchlist(platform) WHERE status = 'active';

COMMIT;
