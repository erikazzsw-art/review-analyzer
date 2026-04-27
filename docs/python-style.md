cat > docs/python-style.md << 'EOF'
# Python 代码风格规范

## 基础规则
- 遵循 PEP 8，行宽上限 120 字符
- 缩进：4 空格，禁止 Tab
- 字符串：统一使用双引号 `"`，SQL 语句内部用单引号 `'`
- f-string 优先，避免 `%` 和 `.format()`
- 类型注解：所有函数参数和返回值必须标注类型

## 命名规范
- 变量 / 函数：`snake_case`
- 类名：`PascalCase`
- 常量：`UPPER_SNAKE_CASE`
- 私有方法 / 属性：单下划线前缀 `_internal_method`
- 布尔变量：`is_` / `has_` / `can_` 前缀

## 导入顺序
1. 标准库
2. 第三方库
3. 项目内部模块

每组之间空一行，组内按字母排序。
EOF
