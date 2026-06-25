-- 028: upload_jobs 增加 retry_count 字段，支持自动重试卡死任务
ALTER TABLE upload_jobs
    ADD COLUMN IF NOT EXISTS retry_count INTEGER NOT NULL DEFAULT 0;
