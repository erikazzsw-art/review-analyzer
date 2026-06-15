-- V5-T1 Phase 1 Step 1: ASIN 监控列表
-- 支持用户绑定 ASIN，设置拉取频率，系统定时自动拉取评论

CREATE TABLE IF NOT EXISTS asin_watchlist (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    asin TEXT NOT NULL,
    marketplace TEXT NOT NULL DEFAULT 'us',
    product_name TEXT,
    product_id INTEGER REFERENCES products(id) ON DELETE SET NULL,
    fetch_frequency TEXT NOT NULL DEFAULT 'daily',
    last_fetched_at TIMESTAMPTZ,
    last_review_count INTEGER DEFAULT 0,
    new_review_count INTEGER DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'active',
    error_message TEXT,
    consecutive_empty INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(user_id, asin, marketplace)
);

CREATE INDEX IF NOT EXISTS idx_asin_watchlist_user_status
    ON asin_watchlist(user_id, status);

CREATE INDEX IF NOT EXISTS idx_asin_watchlist_schedule
    ON asin_watchlist(status, fetch_frequency)
    WHERE status = 'active';

COMMENT ON TABLE asin_watchlist IS '用户 ASIN 监控列表，定时自动拉取评论';
COMMENT ON COLUMN asin_watchlist.fetch_frequency IS 'daily / weekly / manual';
COMMENT ON COLUMN asin_watchlist.status IS 'active / paused / error';
COMMENT ON COLUMN asin_watchlist.consecutive_empty IS '连续无新增次数，达到 3 次自动降频';
