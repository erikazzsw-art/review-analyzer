-- Migration 019: Add tsvector generated column + GIN index for hybrid RAG search (OPT-4)
-- Supports both English and Chinese full-text search via simple config
-- (zhparser not assumed on Supabase; simple config tokenizes on whitespace/punctuation which is adequate for mixed CJK+English)

ALTER TABLE comments
ADD COLUMN IF NOT EXISTS content_tsv tsvector
GENERATED ALWAYS AS (
    to_tsvector('simple', COALESCE(content, ''))
) STORED;

CREATE INDEX IF NOT EXISTS idx_comments_content_tsv
ON comments USING GIN (content_tsv);
