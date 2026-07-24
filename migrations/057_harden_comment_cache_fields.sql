-- 057: Harden comment cache observability fields
-- Production safety net for environments where 014/043 were partially applied.

ALTER TABLE comments
    ADD COLUMN IF NOT EXISTS cache_hit_level VARCHAR(4);

ALTER TABLE comments
    ADD COLUMN IF NOT EXISTS cache_source_id INTEGER;

ALTER TABLE comments
    ADD COLUMN IF NOT EXISTS cache_hit_source VARCHAR(20);

CREATE INDEX IF NOT EXISTS idx_comments_cache_hit_level
    ON comments(cache_hit_level)
    WHERE cache_hit_level IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_comments_cache_hit_source
    ON comments(cache_hit_source)
    WHERE cache_hit_source IS NOT NULL;

COMMENT ON COLUMN comments.cache_hit_level IS
    'Cache hit level: L1=exact hash, L2=rule skip, L3=embedding similar, NULL=LLM/new analysis';

COMMENT ON COLUMN comments.cache_source_id IS
    'Cache source row id. For L1 user hits this is comments.id; for global hits this may be review_pool.id.';

COMMENT ON COLUMN comments.cache_hit_source IS
    'L1 cache source: user=own historical comments, global=review_pool, NULL=not an L1 hit or unavailable';
