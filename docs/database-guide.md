# PostgreSQL 数据库操作规范

> 最后更新：2026-06-10（V4-T2 数据库基建升级）

---

## 一、环境隔离架构

```
┌─────────────────────────────────────────────────────┐
│                    Supabase 双项目                     │
├─────────────────────────┬───────────────────────────┤
│   Review_analyzer       │   clueai-dev              │
│   (PROD)                │   (DEV)                   │
│   Port: 5432            │   Port: 6543 (pooler)     │
│   .env → DATABASE_URL   │   .env → DEV_DATABASE_URL │
│   deploy/.env           │                           │
└─────────────────────────┴───────────────────────────┘
```

| 环境 | 用途 | 连接变量 | 谁能写 |
|------|------|---------|--------|
| prod | 线上用户流量 | `DATABASE_URL` | deploy docker-compose |
| dev | 开发测试、migration 验证 | `DEV_DATABASE_URL` | 本地开发 |

**规则：任何 schema 变更必须先在 dev 验证通过，再上 prod。**

---

## 二、连接方式

```python
from review_analyzer.database import get_connection

conn = get_connection()
try:
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute("SELECT ... WHERE user_id = %s", (user_id,))
        rows = [dict(r) for r in cur.fetchall()]
finally:
    conn.close()
```

核心规则：
- 所有业务查询必须带 `WHERE user_id = %s`（多租户隔离）
- 使用参数化查询 `%s`（psycopg2），禁止字符串拼接
- `get_connection()` 返回池化连接，`close()` 归还而非断开
- 写操作后必须 `conn.commit()`

---

## 三、Migrations 流程

### 文件位置

```
migrations/
├── 001_init_users.sql
├── 002_create_sessions.sql
├── ...
├── 011_create_quota_usage.sql
└── README.md
```

### 文件结构

```sql
-- Migration NNN: 标题
-- 创建时间: YYYY-MM-DD
-- 说明: 简述变更

-- ========== UP ==========
CREATE TABLE IF NOT EXISTS ...;

-- ========== DOWN ==========
-- DROP TABLE IF EXISTS ... CASCADE;
```

### 新增 Migration 步骤

1. 创建 `migrations/{下一个编号}_{描述}.sql`
2. 在 dev 库执行并验证：`psql $DEV_DATABASE_URL -f migrations/NNN_xxx.sql`
3. 更新 `migrations/README.md` 清单
4. 提交 PR
5. prod 执行前先跑 `scripts/backup_to_oss.sh`
6. prod 执行：记录执行前后行数对比

### 幂等要求

- `CREATE TABLE IF NOT EXISTS`
- `ALTER TABLE ... ADD COLUMN IF NOT EXISTS`
- `DROP CONSTRAINT IF EXISTS` → 再 `ADD CONSTRAINT`

---

## 四、备份恢复 SOP

### 自动备份

- 脚本：`scripts/backup_to_oss.sh`
- 频率：每周一 09:00（crontab）
- 存储：`oss://clueai-backup/weekly/clueai_prod_YYYYMMDD.sql.gz`
- 保留策略：近 4 周全量，更早按月保留 1 号那份

### 手动恢复

```bash
# 恢复最新备份到 dev
./scripts/restore_from_oss.sh

# 恢复指定日期
./scripts/restore_from_oss.sh 20260610

# 恢复到自定义目标
TARGET_DB_URL=<url> ./scripts/restore_from_oss.sh
```

### 恢复验证

```bash
psql $DEV_DATABASE_URL -c "SELECT COUNT(*) FROM users;"
psql $DEV_DATABASE_URL -c "SELECT COUNT(*) FROM comments;"
```

---

## 五、多租户隔离规范

### 第一道防线：应用层 user_id 过滤

所有业务 SQL 必须带 `WHERE user_id = %s`，例外：
- `users` 表自身操作（注册、登录、查用户）
- `password_reset_tokens`（通过 token 查询）
- `settings` 全局 KV

### 第二道防线：RLS Policy（后续启用）

```sql
-- 启用 RLS
ALTER TABLE sessions ENABLE ROW LEVEL SECURITY;

-- 策略：用户只能访问自己的数据
CREATE POLICY user_isolation ON sessions
    USING (user_id = current_setting('app.current_user_id')::int);
```

RLS 添加步骤：
1. dev 库启用 + 测试业务功能不受影响
2. 记录到 migration 文件
3. prod 启用后立即跑冒烟测试

### 审计

- 审计报告：`docs/audit_multi_tenant_2026_06_10.md`
- 新增 SQL 时 review 必须检查 user_id 过滤

---

## 六、Schema 约束清单

| 约束 | 表 | 规则 |
|------|---|------|
| `chk_users_plan` | users | `plan IN ('free', 'pro_early', 'pro', 'team')` |
| `chk_comments_rating` | comments | `rating IS NULL OR (rating BETWEEN 1 AND 5)` |
| `chk_comments_sentiment` | comments | `sentiment IN ('positive', 'negative', 'neutral')` |
| `chk_action_items_status` | action_items | `status IN ('todo', 'in_progress', 'pending_review', 'done', 'cancelled')` |

所有业务表含 `updated_at` 触发器（自动更新）+ `deleted_at`（软删除预留）。

---

## 七、配额系统

- 配额表：`user_quota_usage(user_id, dimension, period_start, used_count)`
- 配额服务：`review_analyzer/quota.py`
- API：`GET /quota`、`GET /quota/{dimension}`
- 维度定义：见 `QUOTA_TABLE.md`（Single Source of Truth）

---

## 八、环境配置

### 本地开发

```bash
# 根目录 .env
DATABASE_URL=postgresql://postgres:<password>@db.<ref>.supabase.co:5432/postgres
DEV_DATABASE_URL=postgresql://postgres.<ref>:<password>@aws-1-<region>.pooler.supabase.com:6543/postgres
```

### 线上部署

```bash
# deploy/.env（docker-compose 读取）
DATABASE_URL=postgresql://postgres:<password>@db.<ref>.supabase.co:5432/postgres
```

密码含特殊字符时须 URL 编码：`@` → `%40`，`#` → `%23`

---

## 九、ECS 容器内数据库调试

### 注意事项

api 容器 **没有安装 psql**，不要在容器内直接跑 `psql` 命令。用容器自带的 Python + psycopg2 代替。

### 常用操作

```bash
# 检查表是否存在
docker compose exec api python -c "
import os, psycopg2
conn = psycopg2.connect(os.environ['DATABASE_URL'])
cur = conn.cursor()
cur.execute(\"SELECT to_regclass('表名')\")
print(cur.fetchone()[0])
conn.close()
"

# 查询行数
docker compose exec api python -c "
import os, psycopg2
conn = psycopg2.connect(os.environ['DATABASE_URL'])
cur = conn.cursor()
cur.execute('SELECT COUNT(*) FROM 表名')
print(cur.fetchone()[0])
conn.close()
"

# 查看表结构
docker compose exec api python -c "
import os, psycopg2
conn = psycopg2.connect(os.environ['DATABASE_URL'])
cur = conn.cursor()
cur.execute(\"SELECT column_name, data_type FROM information_schema.columns WHERE table_name = '表名' ORDER BY ordinal_position\")
for row in cur.fetchall():
    print(f'{row[0]:30s} {row[1]}')
conn.close()
"

# 执行任意 SQL（只读查询）
docker compose exec api python -c "
import os, psycopg2
conn = psycopg2.connect(os.environ['DATABASE_URL'])
cur = conn.cursor()
cur.execute('你的SQL')
for row in cur.fetchall():
    print(row)
conn.close()
"
```

### 执行 migration

```bash
# 将 migration 文件复制到容器内执行
docker compose cp migrations/NNN_xxx.sql api:/tmp/
docker compose exec api python -c "
import os, psycopg2
conn = psycopg2.connect(os.environ['DATABASE_URL'])
cur = conn.cursor()
cur.execute(open('/tmp/NNN_xxx.sql').read())
conn.commit()
conn.close()
print('done')
"
```
