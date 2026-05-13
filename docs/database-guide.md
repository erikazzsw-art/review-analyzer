# PostgreSQL (Supabase) 数据库操作规范

> 2026-05-13 迁移：SQLite → Supabase PostgreSQL

## 核心规则
- 所有查询函数必须接收 `user_id` 参数，SQL 强制带 `WHERE user_id = %s`
- 使用参数化查询 `%s` 占位符（psycopg2 格式），禁止字符串拼接 SQL（防注入）
- 连接管理：`conn = get_connection()` + `try/finally conn.close()`
- 表名、字段名使用 `snake_case`
- 写操作后必须 `conn.commit()`
- 查询结果使用 `psycopg2.extras.RealDictCursor` 返回字典

## 连接方式
```python
import psycopg2
import psycopg2.extras
import streamlit as st

def get_connection():
    db_url = st.secrets["database"]["url"]
    return psycopg2.connect(db_url)
```

## 正确示例
```python
def get_sessions(user_id: int) -> list[dict]:
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                "SELECT * FROM sessions WHERE user_id = %s ORDER BY created_at DESC",
                (user_id,)
            )
            return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()
```

## 与 SQLite 的主要差异
| 项目 | SQLite | PostgreSQL |
|------|--------|-----------|
| 占位符 | `?` | `%s` |
| 自增主键 | `INTEGER PRIMARY KEY AUTOINCREMENT` | `SERIAL PRIMARY KEY` |
| 获取插入 ID | `cursor.lastrowid` | `RETURNING id` |
| 时间默认值 | `datetime('now')` | `NOW()` |
| UPSERT | `ON CONFLICT ... DO UPDATE SET value = excluded.value` | `ON CONFLICT ... DO UPDATE SET value = EXCLUDED.value` |
| 子查询 | 可省略别名 | 必须加别名 `AS sub` |
| 布尔值 | 0/1 | 0/1（兼容） |

## Secrets 配置
- 本地开发：`.streamlit/secrets.toml`
- 线上部署：Streamlit Cloud → Settings → Secrets

```toml
[database]
url = "postgresql://postgres.[ref]:[password]@aws-0-[region].pooler.supabase.com:6543/postgres"
```

## 建表脚本
见仓库根目录 `supabase_schema.sql`
