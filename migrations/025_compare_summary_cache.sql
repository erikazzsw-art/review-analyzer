-- Migration 025: 对比分析的 AI 总结 + 维度洞察缓存表
-- 创建时间: 2026-06-24 (对比页面优化: 总结永不过期 + 复用 group insights)
-- 说明:
--   按 (user_id, compare_type, normalized_filter_groups) 的 sha256 指纹缓存一次对比生成的
--   group_insights (per-group build_results_insights payload) 和 ai_summary。
--   永不过期: 同一筛选条件命中同一份, 直到用户改任一筛选才会重算。

-- ========== UP ==========

CREATE TABLE IF NOT EXISTS comparison_summary_cache (
    fingerprint TEXT PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    compare_type TEXT NOT NULL,
    filter_payload JSONB NOT NULL,
    group_insights JSONB,
    ai_summary JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_comparison_summary_cache_user
    ON comparison_summary_cache(user_id, created_at DESC);

COMMENT ON TABLE comparison_summary_cache IS '对比分析 group insights + AI 总结的指纹缓存, 永不过期';
COMMENT ON COLUMN comparison_summary_cache.fingerprint IS 'sha256(user_id|compare_type|normalized_groups)';
COMMENT ON COLUMN comparison_summary_cache.group_insights IS '每个 group 的 build_results_insights 结果, 数组与 filter_payload.groups 顺序一致';
COMMENT ON COLUMN comparison_summary_cache.ai_summary IS '{headline, summary[], recommendations[], risks[]}';

-- ========== DOWN ==========
-- DROP TABLE IF EXISTS comparison_summary_cache;
