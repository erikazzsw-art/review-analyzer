-- Migration 052: comments 增加 source_variant_asin
-- 创建时间: 2026-07-22
-- 说明: 保留评论来源子 ASIN，用于父体产品下展示各子 ASIN 的评论数量。

-- ========== UP ==========

ALTER TABLE comments ADD COLUMN IF NOT EXISTS source_variant_asin TEXT;

CREATE INDEX IF NOT EXISTS idx_comments_source_variant_asin
    ON comments(user_id, product_id, source_variant_asin)
    WHERE source_variant_asin IS NOT NULL;

-- Backfill plugin/API uploads that already carried source_variant_asin inside
-- upload_jobs.payload_json.comments before comments started persisting it.
UPDATE comments c
SET source_variant_asin = item.value->>'source_variant_asin'
FROM upload_jobs uj
CROSS JOIN LATERAL jsonb_array_elements(
    CASE
        WHEN jsonb_typeof(uj.payload_json->'comments') = 'array'
        THEN uj.payload_json->'comments'
        ELSE '[]'::jsonb
    END
) AS item(value)
WHERE c.user_id = uj.user_id
  AND c.session_id = uj.session_id
  AND c.source_variant_asin IS NULL
  AND COALESCE(item.value->>'source_variant_asin', '') <> ''
  AND c.content = item.value->>'content'
  AND COALESCE(c.reviewer, '') = COALESCE(item.value->>'reviewer', '')
  AND COALESCE(c.date, '') = COALESCE(item.value->>'date', '');

-- ========== DOWN ==========
-- DROP INDEX IF EXISTS idx_comments_source_variant_asin;
-- ALTER TABLE comments DROP COLUMN IF EXISTS source_variant_asin;
