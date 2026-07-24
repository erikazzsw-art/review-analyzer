-- Migration 022: sessions 表增加 warnings_json 字段
-- 创建时间: 2026-06-17 (V4-T1.6 Step 3: taxonomy 覆盖率监控)
-- 说明: 存储分析完成后的告警信息（如 taxonomy 覆盖率不足），供前端展示

-- ========== UP ==========

ALTER TABLE sessions ADD COLUMN IF NOT EXISTS warnings_json JSONB;

COMMENT ON COLUMN sessions.warnings_json IS 'Analysis warnings (taxonomy coverage, etc.)';

-- ========== DOWN ==========
-- ALTER TABLE sessions DROP COLUMN IF EXISTS warnings_json;
