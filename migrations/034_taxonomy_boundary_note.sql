-- 034: 为 category_aspect_taxonomy 增加 boundary_note 字段
-- 方案A: 每个标签可以携带边界说明，注入 prompt 帮助 LLM 区分易混淆标签

ALTER TABLE category_aspect_taxonomy
ADD COLUMN IF NOT EXISTS boundary_note TEXT;

COMMENT ON COLUMN category_aspect_taxonomy.boundary_note
IS '标签边界说明 — 写入 prompt 帮助 LLM 区分易混淆标签，例如"仅限产品本身材质评论，不含包装材料"';
