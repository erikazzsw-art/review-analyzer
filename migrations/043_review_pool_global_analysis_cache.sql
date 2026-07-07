-- Migration 043: 跨用户 LLM 分析结果复用（Global Analysis Cache）
--
-- 目的：让 workers/jobs.py 的 L1 缓存 lookup 除了查用户自己的 comments，
-- 也查全局 review_pool（migration 038 已建）里 analyzed_at IS NOT NULL 的行。
--
-- 收益：多用户上传同一 ASIN 或同款热门评论时，直接复用已有分析结果，
-- 消除重复 DeepSeek 调用。用户额度仍按上传条数扣（quota 在上传时消费），
-- 只省服务器成本。
--
-- 关联需求：跨用户 A/B/C 上传重叠评论时复用命中。

BEGIN;

-- ============================================================
-- 1) review_pool 新增 content_hash 部分索引
-- ============================================================
-- 已有索引 idx_pool_product_lookup (platform, product_key, marketplace)
-- 支持"同商品同 marketplace" 场景。本索引支持纯 content_hash 查询，
-- 用于 workers/jobs.py L1 全局 lookup。
-- 使用部分索引（analyzed_at IS NOT NULL）大幅减小索引体积，
-- 只覆盖已完成分析的行。

CREATE INDEX IF NOT EXISTS idx_pool_content_hash_analyzed
    ON review_pool (content_hash)
    WHERE analyzed_at IS NOT NULL;

-- ============================================================
-- 2) comments 新增 cache_hit_source 列
-- ============================================================
-- 已有 cache_hit_level (L1/L2/L3) 和 cache_source_id 列。
-- 新增 cache_hit_source 区分命中来源：
--   'user'   — 复用用户自己历史分析
--   'global' — 复用跨用户 review_pool
--   NULL     — 未命中缓存（走了 LLM）
-- 用于 llm_usage_log 统计"跨用户节约成本"指标。

ALTER TABLE comments
    ADD COLUMN IF NOT EXISTS cache_hit_source VARCHAR(20);

COMMENT ON COLUMN comments.cache_hit_source IS
    'L1 缓存命中来源: user=本人历史 | global=跨用户 review_pool | NULL=未命中';

COMMIT;
