-- 问评论意图路由：为 qa_messages 增加 intent 与 aggregation_snapshot 字段
-- 用于回放历史对话时展示"回答类型"徽章、以及后续 A/B 分析路由效果。

ALTER TABLE qa_messages
    ADD COLUMN IF NOT EXISTS intent TEXT,
    ADD COLUMN IF NOT EXISTS aggregation_snapshot JSONB;
