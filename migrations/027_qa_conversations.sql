-- 027_qa_conversations.sql
-- 多轮对话支持：对话表 + 消息表

CREATE TABLE IF NOT EXISTS qa_conversations (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    product_ids TEXT[] NOT NULL,
    title TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS qa_messages (
    id SERIAL PRIMARY KEY,
    conversation_id INTEGER NOT NULL REFERENCES qa_conversations(id) ON DELETE CASCADE,
    role TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
    content TEXT NOT NULL,
    citations JSONB,
    retrieval_method TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_qa_conv_user ON qa_conversations(user_id);
CREATE INDEX IF NOT EXISTS idx_qa_msg_conv ON qa_messages(conversation_id);
