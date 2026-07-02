-- 040: 翻译结果缓存表
-- P0 修复：为 /translate/module 提供服务端缓存，防止重复调用 LLM 烧钱
-- key = sha256(user_id + session_id + module_key + target_lang + content_hash)

CREATE TABLE IF NOT EXISTS translate_cache (
    cache_key TEXT PRIMARY KEY,
    user_id INTEGER NOT NULL,
    session_id INTEGER,
    module_key TEXT NOT NULL,
    target_lang TEXT NOT NULL,
    translated_json JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    accessed_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_translate_cache_user ON translate_cache(user_id);
CREATE INDEX IF NOT EXISTS idx_translate_cache_accessed ON translate_cache(accessed_at);
