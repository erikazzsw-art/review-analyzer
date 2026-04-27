# 文件与编码规范

- 所有 `.py` 文件使用 UTF-8 编码
- 文件解析（CSV/Excel/docx）统一输出 `pandas.DataFrame`
- 日期字段统一解析为 `YYYY-MM-DD` 格式字符串存入数据库
- MD5 哈希用于去重，基于评论内容生成：`hashlib.md5(content.encode()).hexdigest()`
