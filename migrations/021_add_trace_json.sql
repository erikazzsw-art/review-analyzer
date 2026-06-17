-- Migration 021: Add trace_json to upload_jobs for pipeline observability
-- UP

ALTER TABLE upload_jobs ADD COLUMN IF NOT EXISTS trace_json JSONB;

CREATE INDEX IF NOT EXISTS idx_upload_jobs_trace_duration
    ON upload_jobs ((trace_json->>'total_duration_ms')::int)
    WHERE trace_json IS NOT NULL;

-- DOWN
-- ALTER TABLE upload_jobs DROP COLUMN IF EXISTS trace_json;
-- DROP INDEX IF EXISTS idx_upload_jobs_trace_duration;
