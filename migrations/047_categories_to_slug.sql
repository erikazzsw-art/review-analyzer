-- V4-M2-2.2.C 类别标签 i18n 化
-- 将 comments.category 从 11 个中文分类名迁移到稳定英文 slug
-- 展示层通过 messages/{zh,en}.json categoryLabels 命名空间做 i18n
--
-- 幂等性：二次运行 no-op（WHERE category = '中文' 不再命中已迁移的英文 slug）
-- 依赖：无（仅 UPDATE 现有列，不改 schema）
-- 影响面：comments 表所有历史评论的 category 字段
-- 编号说明：PROGRESS_V2 原写 046，但 046 已被 046_add_scraped_title.sql 占用，实际使用 047

BEGIN;

UPDATE comments SET category = 'product_quality'     WHERE category = '产品质量';
UPDATE comments SET category = 'packaging_logistics' WHERE category = '包装物流';
UPDATE comments SET category = 'user_experience'     WHERE category = '使用体验';
UPDATE comments SET category = 'customer_service'    WHERE category = '客服售后';
UPDATE comments SET category = 'value_for_money'     WHERE category = '性价比';
UPDATE comments SET category = 'feature_request'     WHERE category = '功能需求';
UPDATE comments SET category = 'positive_feedback'   WHERE category = '正面反馈';
UPDATE comments SET category = 'simple_praise'       WHERE category = '单纯好评';
UPDATE comments SET category = 'invalid_garbage'     WHERE category = '无效乱码';
UPDATE comments SET category = 'mixed'               WHERE category = '混合评价';
UPDATE comments SET category = 'other'               WHERE category = '其他';

COMMIT;

-- ============================================================
-- ROLLBACK（应急回滚，Erika 手动执行）
-- ============================================================
-- BEGIN;
-- UPDATE comments SET category = '产品质量'  WHERE category = 'product_quality';
-- UPDATE comments SET category = '包装物流'  WHERE category = 'packaging_logistics';
-- UPDATE comments SET category = '使用体验'  WHERE category = 'user_experience';
-- UPDATE comments SET category = '客服售后'  WHERE category = 'customer_service';
-- UPDATE comments SET category = '性价比'    WHERE category = 'value_for_money';
-- UPDATE comments SET category = '功能需求'  WHERE category = 'feature_request';
-- UPDATE comments SET category = '正面反馈'  WHERE category = 'positive_feedback';
-- UPDATE comments SET category = '单纯好评'  WHERE category = 'simple_praise';
-- UPDATE comments SET category = '无效乱码'  WHERE category = 'invalid_garbage';
-- UPDATE comments SET category = '混合评价'  WHERE category = 'mixed';
-- UPDATE comments SET category = '其他'      WHERE category = 'other';
-- COMMIT;
