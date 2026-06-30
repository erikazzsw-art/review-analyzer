-- 037: 重建 category_aspect_taxonomy 表
-- 原表 schema (category/aspect/level) 已过时；新 import 流水线期望
-- 以 sub_category 为主键维度，携带统计字段 + boundary_note
--
-- 旧表数据全为空行（total/count 均为 0），直接 DROP + CREATE 无数据损失

DROP TABLE IF EXISTS category_aspect_taxonomy;

CREATE TABLE category_aspect_taxonomy (
    id               SERIAL PRIMARY KEY,
    sub_category     VARCHAR(120) NOT NULL,
    aspect_key       VARCHAR(80)  NOT NULL,
    label_zh         VARCHAR(120) NOT NULL DEFAULT '',
    boundary_note    TEXT,
    total_count      INTEGER      NOT NULL DEFAULT 0,
    positive_count   INTEGER      NOT NULL DEFAULT 0,
    negative_count   INTEGER      NOT NULL DEFAULT 0,
    neutral_count    INTEGER      NOT NULL DEFAULT 0,
    negative_rate    NUMERIC(5,2) NOT NULL DEFAULT 0,
    top_phrases      JSONB        NOT NULL DEFAULT '[]',
    sample_review_ids JSONB       NOT NULL DEFAULT '[]',
    taxonomy_version VARCHAR(20)  NOT NULL DEFAULT 'v1.0',
    updated_at       TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_taxonomy_sub_aspect_ver
        UNIQUE (sub_category, aspect_key, taxonomy_version)
);

CREATE INDEX idx_taxonomy_sub_category ON category_aspect_taxonomy (sub_category);
CREATE INDEX idx_taxonomy_version      ON category_aspect_taxonomy (taxonomy_version);

COMMENT ON TABLE category_aspect_taxonomy IS
'子品类维度标签表：每行 = 一个子品类 × 一个 aspect，携带统计计数和 boundary_note。';
