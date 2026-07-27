# Database Migrations

## 概述

本目录存放所有数据库 schema 变更，按编号顺序执行。每个文件是一个独立的、幂等的 migration。

## 文件命名规范

```
{NNN}_{描述}.sql
```

- `NNN`: 三位数序号，从 001 开始递增
- 描述: 小写英文，下划线分隔，简述变更内容

## 文件结构

每个 migration 文件包含两个区块：

```sql
-- Migration NNN: 标题
-- 创建时间: YYYY-MM-DD
-- 说明: 简述这个 migration 做了什么

-- ========== UP ==========
-- (正向变更 SQL，支持重复执行)

-- ========== DOWN ==========
-- (回滚 SQL，注释状态，手动执行时取消注释)
```

## 执行规则

1. **顺序执行**: 必须从 001 开始按编号依次执行
2. **幂等设计**: 所有 UP SQL 使用 `IF NOT EXISTS` / `IF EXISTS` 保证可重复执行
3. **环境隔离**: 先在 dev 库跑完整轮，验证无误后再上 prod
4. **备份优先**: prod 执行前必须先完成 `scripts/backup_to_oss.sh`

## 当前 Migration 清单

| 编号 | 文件 | 说明 | 对应版本 |
|------|------|------|------|
| 001 | `001_init_users.sql` | 用户表 | V1 初始 |
| 002 | `002_create_sessions.sql` | 分析会话表 | V1 初始 |
| 003 | `003_create_comments.sql` | 评论表 | V1 初始 |
| 004 | `004_create_upload_jobs.sql` | 上传任务队列 | NX-M3 |
| 005 | `005_create_settings_and_reset_tokens.sql` | 设置 + 密码重置 | V1.5 |
| 006 | `006_add_pgvector_embedding.sql` | 向量检索 | V2-M3 |
| 007 | `007_create_products.sql` | 产品档案体系 | V2.5 |
| 008 | `008_create_actions_and_trackers.sql` | 行动闭环 + 复盘 | V2.5 |
| 009 | `009_create_comparison_reports.sql` | 对比报告 | V2.5 |
| 010 | `010_standardize_fields.sql` | 字段标准化 + CHECK + 触发器 | V4-T2 |
| 011 | `011_create_quota_usage.sql` | 配额计数表 | V4-T2 |
| ... | *(012-043 待补全文档)* | 各功能模块迭代 | V4-V5 |
| 044 | `044_create_user_credits.sql` | Credit 定价体系基建（user_credits + credit_ledger） | V4-出海-M6 |
| 045 | `045_add_starter_plan.sql` | users.plan 约束添加 starter | V4-出海-M6 |
| 058 | `058_customer_label_catalog_alias_candidates.sql` | Customer Issue / Customer Label 统一数据层 | V5-T3 Phase 7 |
| 059 | `059_add_comments_review_date.sql` | comments normalized review_date + date range indexes | Phase 7 P2 |

## 新增 Migration 流程

1. 创建新文件: `{下一个编号}_{描述}.sql`
2. 在 dev 库执行并验证
3. 更新本 README 的清单
4. 提交 PR，code review 后合并
5. prod 执行（需备份 + 行数对比验证）

## 回滚流程

DOWN 区块默认注释状态。需要回滚时：

1. 备份当前 prod 数据
2. 取消目标 migration 的 DOWN 区块注释
3. 在 dev 库先跑一遍确认无数据丢失
4. prod 执行回滚
5. 验证业务功能正常
