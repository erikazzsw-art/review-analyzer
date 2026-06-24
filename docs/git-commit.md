# Git 提交规范

## 提交信息格式
`<type>(<scope>): <简要描述>`

- `<scope>` 可选：`copywriter-api` / `frontend` / `db` / `docs` 等，表明影响哪个模块
- 简要描述写"做了什么"，message body 写"为什么 / 影响范围"

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

## Push 拆分规则（强制 · 默认）

> Erika 2026-06-24 约定：以后每次 push 都按此执行，不再每次重复要求。

一次任务完成后，按"功能 / 实现目标"拆为独立 commit，不要把多模块改动塞进同一个 commit。典型拆法：

| 模块 | 触发条件 | 独立 commit |
|------|---------|------------|
| 调研 / 资料文档 | 新增或更新 docs/*.md | `docs(<scope>): ...` |
| 后端数据/规则常量 | 改 PLATFORM_DATA、STYLES、taxonomy 等常量 | `feat(<scope>-api): ...` |
| 后端 API / schema | 新端点、新字段、改 request/response | `feat(api): ...` |
| 数据库迁移 | 新增 migrations/NNN_*.sql + 配套服务/缓存层 | `feat(db): ...` |
| 前端组件 / 页面 | 新增或重做 React 组件、page.tsx | `feat(frontend): ...` |
| 文档同步 | 更新 PROGRESS_V2.md / TEST_LOG.md（如果未与上面同 commit） | `docs: ...` |

### 每个 commit 的 message body 必备内容

- **做了什么**：列改动点（1–4 个 bullet）
- **为什么**：触发原因（用户需求 / 调研结论 / bug 触发等）
- **影响范围**：哪些页面 / API / 表 / 调用方受影响
- **回滚**：如果有破坏性变更（删字段、删端点），明确说明

示例 commit message：

```
feat(copywriter-api): 扩 TikTok 平台 + 收紧 Amazon 禁用词 + 新增风格兼容矩阵

做了什么:
- PLATFORM_DATA 新增 tiktok 平台 (in-feed / spark / brand name)
- Amazon prohibited 追加 today only / last chance / buy now / $ off
- 新增 STYLE_INCOMPATIBLE 矩阵, 紧迫促单在 amazon/walmart/google 灰显
- Schema 改造: CopywriterGenerateRequest 去掉 product_session_ids,
  改为 product_id + version + range; CopywriterGeneratedItem 增加
  compliance_notes

为什么:
宣传文案页面工作流从"按批次选"改为"按产品+版本"; 需要让每条文案输出
满足平台 2026-06 最新规则。

影响:
- POST /api/copywriter/generate 入参不兼容旧前端
- GET /api/copywriter/platforms 返回新字段 internal_estimate
- 前端在同 PR 内一并替换, 无外部调用方

回滚: revert 该 commit + 前端配套 commit
```

## 其他规则
- 每个功能完成后单独提交，不混合多个改动
- 不提交 `.env` 和 `*.db` 文件
- 同 commit 内允许且鼓励同步更新 PROGRESS_V2.md / TEST_LOG.md（见 CLAUDE.md「文档自动更新规则」）
