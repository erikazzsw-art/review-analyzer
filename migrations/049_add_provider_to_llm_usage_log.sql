-- V4-出海-M4.3: log_llm_usage 增加 provider 字段，区分 OpenAI / DeepSeek / Qwen 调用量
ALTER TABLE llm_usage_log ADD COLUMN IF NOT EXISTS provider VARCHAR(32);

-- 从现有 model_name 反推 provider 值（向后兼容已有数据）
UPDATE llm_usage_log SET provider = 'deepseek' WHERE provider IS NULL AND model_name = 'deepseek-chat';
UPDATE llm_usage_log SET provider = 'openai'   WHERE provider IS NULL AND model_name = 'gpt-4o-mini';
UPDATE llm_usage_log SET provider = 'qwen'     WHERE provider IS NULL AND model_name = 'qwen-plus';
