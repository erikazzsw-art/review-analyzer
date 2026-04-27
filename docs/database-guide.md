# SQLite 数据库操作规范

## 核心规则
- 所有查询函数必须接收 `user_id` 参数，SQL 强制带 `WHERE user_id = ?`
- 使用参数化查询 `?` 占位符，禁止字符串拼接 SQL（防注入）
- 连接管理：函数内 `with sqlite3.connect(DB_PATH) as conn` 自动提交/关闭
- 表名、字段名使用 `snake_case`
- 写操作后必须 `conn.commit()`

## 正确示例
```python
def get_sessions(user_id: int) -> list[dict]:
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.execute(
            "SELECT * FROM sessions WHERE user_id = ? ORDER BY created_at DESC",
            (user_id,)
        )
        return [dict(row) for row in cursor.fetchall()]
        