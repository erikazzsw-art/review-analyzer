# Git 提交规范

## 提交信息格式
`<type>: <简要描述>`

## type 类型
- `feat`: 新功能
- `fix`: 修复 bug
- `refactor`: 重构
- `docs`: 文档更新
- `style`: 代码格式调整
- `test`: 测试用例
- `chore`: 构建/工具变动

## 示例
- `feat: 添加 XLSX 多 Sheet 导出功能`
- `fix: 修复飞书推送重试逻辑`

## 其他规则
- 每个功能完成后单独提交，不混合多个改动
- 不提交 `.env` 和 `*.db` 文件
