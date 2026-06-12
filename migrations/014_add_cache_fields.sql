-- V4-T4 Step 3: 多级缓存字段
-- 2026-06-12

-- 记录每条评论的缓存命中层级（NULL=未使用缓存/直接LLM分析）
ALTER TABLE comments ADD COLUMN IF NOT EXISTS cache_hit_level VARCHAR(4);
ALTER TABLE comments ADD COLUMN IF NOT EXISTS cache_source_id INTEGER;

COMMENT ON COLUMN comments.cache_hit_level IS '缓存命中层级: L1=hash精确/L2=短文本跳过/L3=embedding相似/NULL=LLM分析';
COMMENT ON COLUMN comments.cache_source_id IS '缓存来源评论 ID（L1/L3 复用的源评论）';

-- 为 L1 查找加速：content_hash + is_processed 联合索引
CREATE INDEX IF NOT EXISTS idx_comments_hash_processed
    ON comments (user_id, content_hash)
    WHERE content_hash IS NOT NULL AND is_processed = 1;

-- 为 L3 查找加速：product_id + embedding 非空 + 已处理
CREATE INDEX IF NOT EXISTS idx_comments_emb_analyzed
    ON comments (user_id, product_id)
    WHERE embedding IS NOT NULL AND is_processed = 1 AND aspects_json IS NOT NULL;
