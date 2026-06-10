-- Migration 006: pgvector 向量检索
-- 创建时间: 2026-06-03 (V2-M3 RAG)
-- 说明: 评论 Embedding 向量用于 "Ask your reviews" 语义检索

-- ========== UP ==========

CREATE EXTENSION IF NOT EXISTS vector;

ALTER TABLE comments ADD COLUMN IF NOT EXISTS embedding vector(1536);

CREATE INDEX IF NOT EXISTS idx_comments_embedding
ON comments USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

-- ========== DOWN ==========
-- DROP INDEX IF EXISTS idx_comments_embedding;
-- ALTER TABLE comments DROP COLUMN IF EXISTS embedding;
-- DROP EXTENSION IF EXISTS vector;
