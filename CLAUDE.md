# CLAUDE.md

This file provides guidance to Claude Code when working with code in this repository.

## 核心会话规则

1. **决策确认**：遇到不确定的设计问题，必须先询问 Erika
2. **代码兼容性**：不写兼容性代码，除非明确要求

## 项目概述

评论分析 Web 系统 V4 — 跨境电商评论智能分析 SaaS

- 当前技术栈：Next.js 15 + React 19 + Tailwind（前端）/ FastAPI + Pydantic（API）/ RQ + Redis（异步任务）/ Supabase PostgreSQL（数据库）/ DeepSeek API（LLM 分析）/ nginx + 阿里云 ECS（部署）
- 完整需求和执行计划：详见 `PROGRESS_V2.md`

## 扩展规范（按需加载）

遇到以下场景时，请先读取对应的规范文件，再执行任务：

| 场景 | 规范文件 |
|------|---------|
| 写 Python 代码 | `docs/python-style.md` |
| 开发 Next.js 页面 | `frontend/` 下现有组件风格 |
| 修改端口 / 环境变量 / 部署链路 | `docs/PORT_MIGRATION_CHECKLIST.md` |
| 操作 PostgreSQL 数据库 | `docs/database-guide.md` |
| 调用 DeepSeek API | `docs/api-guide.md` |
| 涉及安全相关代码 | `docs/security-guide.md` |
| 提交 Git 代码 | `docs/git-commit.md` （含 push 拆分规则：按模块拆 commit + message body 必备"做了什么/为什么/影响范围"） |
| 添加错误处理 | `docs/error-handling.md` |
| 处理文件编码/解析 | `docs/file-guide.md` |

## 文档自动更新规则（强制）

每次任务完成后，**必须**按下表更新对应文档，无需用户提醒：

| 触发动作 | 必须更新的文档 | 更新内容 |
|---------|-------------|---------|
| Bug 修复完成 | `TEST_LOG.md` | 在修复记录表追加一行：日期、问题描述、解决方案 |
| 新功能 / 需求变更 | `PROGRESS_V2.md` | 在对应 Step/Task 下更新状态或追加条目 |
| 模块任务完成 | `PROGRESS_V2.md` | 将对应任务的 `[ ]` 改为 `[x]` |

**执行顺序**：先更新文档，再提交 Git。文档更新和代码提交合并为同一个 commit。

## Git 工作流与进度追踪

- 项目进度文件：`PROGRESS_V2.md`
- 分支策略：main（稳定）→ develop（开发主线）→ feature/mX-*（模块分支）
- 模块完成后合并到 develop，验证通过后合并到 main
- CI：push 到 develop/main 后 GitHub Actions 自动跑 ruff lint + tsc typecheck + next build

## 协作审查流程（强制）

### 当前模式（Solo + AI 阶段）

| 角色 | 职责 |
|------|------|
| Claude Code（开发） | 写代码、跑测试、push 到 develop |
| Claude Code（审查） | 每次 push 前执行 `/code-review`，自查代码质量、安全、架构一致性 |
| Erika（验收） | 大功能模块完成后，通过预览环境确认功能实现是否符合预期 |

### 执行规则

1. **小改动（bug fix、样式微调、单文件重构）**：AI 自写自审，CI 通过后直接合入 develop，无需通知 Erika
2. **大模块完成**：当一个完整功能模块（如 PROGRESS_V2.md 中的 V4.5-T2、V5-M1 等 Task 级别）全部完成时，必须通知 Erika 进行验收
3. **高风险变更 — 即使是小改动也必须通知 Erika**：
   - 数据库 migration（新增/删除/修改表结构）
   - 安全相关（认证、加密、权限）
   - 付费逻辑（Paddle webhook、计费墙、套餐）
   - 生产环境配置（docker-compose、nginx、域名）
   - 端口、反向代理、健康检查、环境变量的运行时变更
4. **AI 自审标准**（每次 push 前 Claude Code 必须检查）：
   - 无安全漏洞（SQL 注入、XSS、硬编码密钥）
   - 与现有架构一致（不引入重复抽象）
   - 类型检查 + lint 通过
   - 不破坏现有功能（关键路径回归）

### 通知 Erika 的格式

大模块完成或高风险变更时，用以下格式通知：

```
📋 验收请求
- 模块：[模块名称]
- 变更摘要：[1-2 句话]
- 预览方式：[本地运行命令 / 预览 URL]
- 影响范围：[哪些页面/功能受影响]
```

## 快速参考

- 类型注解：所有函数参数和返回值必须标注类型
- 参数化查询：SQL 必须用 `%s` 占位符（psycopg2），禁止拼接
- 密码存储：使用 `bcrypt`，禁止明文或 MD5
- API Key 加密：使用 `cryptography.fernet`
- 禁止提交：`.env`、`*.db` 文件

## 机密保护规则（强制 · 项目特定）

> 全局通用规则见 `~/.claude/CLAUDE.md` 的"机密保护规则"。本节是本项目的具体清单和已知雷区。

### 本项目的 4 类机密

| 机密类型 | 真实值绝不能进 git 的位置 | 占位符示例 |
|---------|---------------------------|-----------|
| `DEEPSEEK_API_KEY` | 任何代码、文档、配置 | `sk-<YOUR_DEEPSEEK_KEY>` |
| `AES_SECRET_KEY` / Fernet key | 任何代码、文档、配置 | `<FERNET_KEY_BASE64>` |
| `FEISHU_WEBHOOK` | 任何代码、文档、配置 | `https://open.feishu.cn/open-apis/bot/v2/hook/<TOKEN>` |
| `DATABASE_URL` / Supabase 密码 | 任何代码、文档、配置 | `postgresql://postgres.<REF>:<PASSWORD>@host:6543/postgres` |

### 禁止跟踪的文件清单

```
.env
.env.local
.env.production
review_analyzer/.env
backend_api/.env
deploy/.env*
*.db
```

`.gitignore` 必须覆盖以上全部。新增任何 `.env*` 文件前，先确认 `.gitignore` 已经匹配。

### 已知历史雷区（2026-06 排查结果）

- commit `37032b0` 在 `review_analyzer/.env` 中泄露过 DeepSeek key / AES key / Feishu webhook 三类机密（具体值不在此处复述，详见 PROGRESS_V2.md Step 2.0）
- commit `9c89af0` 在代码/文档里硬编码过 Supabase DB 密码（`Zhangxi@<REDACTED>` 格式，已计划在 Step 2.0 轮换）
- 远程 `origin = https://github.com/erikazzsw-art/review-analyzer.git` 是 **public**
- 上述 4 个机密均需轮换；轮换前禁止再做任何"清理 git 历史"的操作

### 每次 commit 前的强制扫描

```bash
# 一行扫描：staged 内容 + 待添加文件名
git diff --cached --name-only | grep -E "(\.env$|secrets\.toml$|credentials|\.pem$|\.key$)" && echo "❌ 含机密文件，停手" || echo "✅ 文件名 OK"
git diff --cached | grep -E "sk-[a-zA-Z0-9]{20,}|postgres(ql)?://[^@]+:[^@:]+@|AES_SECRET_KEY=[A-Za-z0-9+/=_-]{20,}|DEEPSEEK_API_KEY=sk-" && echo "❌ 含明文机密，停手" || echo "✅ 内容 OK"
```

任一行报 ❌ → **立即中止 commit，告诉 Erika 是哪一行**，不要尝试自动 fix。

### 处理 `git add .` 的规则

本项目**禁止** `git add .` / `git add -A`。原因：根目录历史上多次出现过 `.env`、`.DS_Store`、未跟踪机密草稿。

正确做法：
1. `git status` 看清单
2. `git add <具体文件名>` 逐个添加
3. 如果文件多，按目录分批：`git add backend_api/app/` 这种粒度

## Architecture

```
/frontend                    # Next.js 15 + React 19 + Tailwind（prod UI）
/backend_api                 # FastAPI + Pydantic（API 服务）
/workers                     # RQ worker（异步分析任务）
/review_analyzer             # 共享分析模块（LLM 调用、数据库操作）
/deploy                      # docker-compose + nginx 部署配置
/migrations                  # PostgreSQL 迁移文件（编号化）
/.github/workflows           # CI workflow（ruff + tsc + next build）
```

## 数据库环境分离（2026-06-11 生效）

| 环境 | Supabase 项目 | .env 位置 |
|------|--------------|-----------|
| 本地开发 | `clueai-dev`（`lbvbilkgequrvhldedqg`） | `review_analyzer/.env` |
| 生产部署 | prod（`inpgrbjwtpxgwungghnz`） | `deploy/.env` |

本地代码改动不会影响生产数据。

## 项目文件说明（重要！）

### 端口迁移提醒

如果要修改后端监听端口、前端开发端口、nginx upstream、Compose healthcheck、`.env` / `.env.local` / `deploy/.env`，必须先阅读 [`docs/PORT_MIGRATION_CHECKLIST.md`](docs/PORT_MIGRATION_CHECKLIST.md)。

- 优先确认这是不是“运行时配置”，不要把历史文档里的数字误当成现网配置
- 修改前先扫 `8100` / `8000` / `3000`
- 修改后运行 `bash scripts/check_port_migration.sh`
- 修改后同步更新 `TEST_LOG.md`

### 线上网站入口

> **历史回顾**：V1 时期是 Streamlit + Streamlit Cloud；V2 起 (NX-M2~M8) 全面迁移到 Next.js + FastAPI + ECS。**2026-06-16 Streamlit 代码已完全移除**。

- **当前 prod 架构**：Next.js 15 (`frontend/`) + FastAPI (`backend_api/`) + RQ worker (`workers/`) + Redis + Supabase Postgres + nginx，由 [deploy/docker-compose.yml](deploy/docker-compose.yml) 编排，部署在阿里云 ECS
- **用户 UI 入口**：`frontend/`（Next.js 15 + React 19 + Tailwind），nginx 默认 80/443 路由到 `frontend:3000`
- **API 入口**：`backend_api/app/main.py`（FastAPI），对外暴露 `api.clueai-reviewlens.com`
- **废弃文件**：`prototype.html` 是 V1 时期废弃的静态原型，禁止修改

### UI / 后端修改规则（强制）

1. 用户要求改"页面 / 按钮 / 欢迎页 / 注册登录 / 图表 / 评论显示 / 上传交互"等 **prod UI** → 改 `frontend/src/` 下的 Next.js 代码
2. 用户要求改"API 行为 / 后端业务逻辑 / 分析链路 / 数据库" → 改 `backend_api/app/` 或 `review_analyzer/`（共享分析模块）
3. 用户要求改"worker 任务 / 队列消费" → 改 `workers/`
4. 不要碰 `prototype.html`
5. 不确定改哪个 → 先问 Erika

## Git 分支与部署配置（重要！）

### 当前配置
- **prod 部署**：阿里云 ECS，通过 [deploy/docker-compose.yml](deploy/docker-compose.yml) 编排（nginx + frontend + api + worker + redis）
- 日常修改的目标分支：**develop**
- main 分支：仅用于稳定版本，不要直接推送

### 每次修改代码后的标准流程（强制）

当用户提出 bug 修改需求时，请按以下步骤执行：

```bash
# 1. 确认当前在 develop 分支
git checkout develop

# 2. 拉取最新代码（避免冲突）
git pull origin develop

# 3. 修改代码（按上一节「UI / 后端修改规则」定位到 frontend/ / backend_api/ / workers/ 之一）

# 4. 本地验证（push 前必做）
python3 -m ruff check backend_api/ workers/ review_analyzer/   # 后端 lint
cd frontend && npm run typecheck                                # 前端类型检查

# 5. 提交并推送到 develop（git add 用具体路径，不要 `git add .` —— 见「机密保护规则」）
git add <具体文件路径>
git commit -m "fix: [简要描述修改内容]"
git push origin develop

# 6. push 后 GitHub Actions 自动跑 CI（ruff + tsc + next build），无需手动触发
