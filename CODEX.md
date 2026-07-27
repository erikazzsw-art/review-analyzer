# CODEX.md

This file provides guidance to Codex when working with code in this repository.

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
| 提交 Git 代码 | `docs/git-commit.md` |
| 添加错误处理 | `docs/error-handling.md` |
| 处理文件编码/解析 | `docs/file-guide.md` |

## 文档自动更新规则（强制）

每次任务完成后，**必须**按下表更新对应文档，无需用户提醒：

| 触发动作 | 必须更新的文档 | 更新内容 |
|---------|-------------|---------|
| Bug 修复完成 | `TEST_LOG.md` | 在修复记录表追加一行：日期、问题描述、解决方案 |

**PROGRESS_V2.md 规则**（2026-07-27 变更 · 强制）：

- AI **禁止**自动添加、删除或修改 `PROGRESS_V2.md` 中的内容，除非 Erika 明确要求或先获得了 Erika 的同意
- `PROGRESS_V2.md` 每次修改跟随代码一起 commit 到 develop，不再仅本地留存
- **不再维护独立的「变更日志」段落**（已于 2026-07-27 移除）：每个模块的任务明细已通过 `[x]` + `状态/时间` 字段记录了完成状态和时间戳，任务完成后只需更新对应模块的任务明细行即可，无需在文档底部重复维护按时间排序的变更表

**Bug 与新功能分流规则**（2026-07-09 生效 · 强制）：

- **Bug 修复**：只更新 `TEST_LOG.md`（Bug 不是新功能，不属于进度追踪范畴）
- **新功能 / 需求变更 / 模块任务**：不更新 `TEST_LOG.md`（除非开发过程中发现并修复了 bug）；PROGRESS_V2 的更新见上方保护规则（须经 Erika 同意）
- **判断标准**：问题是"原本就该正常工作但坏了"→ Bug → TEST_LOG；任务是"新增能力/行为"→ 功能

**执行顺序**（2026-07-08 更新）：先更新文档 → 单独 commit 代码到 develop，**文档不再随代码 push**，只在本地留存。详见下方「文档推送策略」。

## Git 工作流与进度追踪

- 项目进度文件：`PROGRESS_V2.md`
- 分支策略：main（稳定）→ develop（开发主线）→ feature/mX-*（模块分支）
- 模块完成后合并到 develop，验证通过后合并到 main
- CI：push 到 develop/main 后 GitHub Actions 自动跑 ruff lint + tsc typecheck + next build

## 文档推送策略（2026-07-08 生效 · 强制）

**核心规则**：文档修改只在本地留存，**不再推送到 develop**；后期 push 只推送和本任务直接相关的**代码**到 develop。

> **例外**：`PROGRESS_V2.md` 自 2026-07-27 起每次修改跟随代码一起 commit 到 develop（见上方「PROGRESS_V2.md 规则」）。

### 范围界定

以下都算"文档"，本次生效后**禁止**通过 `git push origin develop` 推送新的改动：

- 根目录：`CLAUDE.md` / `CODEX.md` / `README.md` / `TEST_LOG.md` / `session-summary.md`
- `docs/` 目录下所有 `*.md`
- `需求记录/` 目录下所有 `*.md`（含 `CHANGELOG.md`）
- 任何位置的 `*.md`（不含代码内联注释）

以下算"代码"（可以 push 到 develop）：

- `frontend/` / `backend_api/` / `workers/` / `review_analyzer/` 下的 `.py` / `.ts` / `.tsx` / `.js` / `.jsx` / `.json` / `.sql` 等实际执行文件
- `migrations/` 下的 `.sql`
- `deploy/` 下除 `.env*` 之外的配置（`docker-compose.yml` / `nginx*` 等）
- `.github/workflows/` 下的 CI 配置

### 落地做法

1. 更新文档时**照常改**，本地保留即可；不要 `git add` 进推送 develop 的 commit
2. `git add` 时**只逐个添加代码文件**，禁止 `git add .` / `git add -A`
3. `git status -uno` 里看到有文档改动没被 add 是**正常**的，不用清理
4. 已经推送到 develop 的历史文档 commit **保持现状**，不做 revert 或整理
5. 如果文档改动包含 Erika 需要 review 的规则，在对话中把关键差异直接贴出来

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

# 5. 提交并推送到 develop（2026-07-08 更新：只 add/push 代码文件，文档留在工作区不 push）
git add <具体代码文件路径>              # ⚠️ 禁止 git add . / git add -A
git commit -m "fix: [简要描述修改内容]"
git push origin develop

# 6. push 后 GitHub Actions 自动跑 CI + CD 自动部署，无需手动触发
```

### 部署方式：GitHub Actions CD 自动部署（2026-07-15 生效）

**push 到 develop 即自动部署**，不再需要手动 SSH。链路见 `.github/workflows/deploy.yml`：

`push develop` → CI gate（ruff + tsc + next build）→ Configure SSH → Deploy（ECS `git reset --hard origin/develop` + `docker compose up -d --build --remove-orphans`）→ Health Check（API `python urllib` / frontend `node http`）→ 失败自动 Rollback → 邮件通知。

- Codex CLI **仍不执行任何 SSH 到 ECS 的操作**，部署完全交给 CD
- 健康检查用容器原生运行时（api 镜像无 `curl`、frontend 镜像无 `wget`）——**禁止改回 `curl`/`wget`**
- 改 `.github/workflows/*.yml` 前先通知 Erika（高风险生产链路）

### 每次 push 前必须先告知 Erika（强制 · 2026-07-15 生效）

**push develop 会立即触发真实生产部署**，执行 `git push origin develop` **之前**必须先告知 Erika，等确认后再 push：

1. 列出本次要 push 的**代码文件**（文档不 push）
2. 一句话说明改了什么、会重建哪些服务、是否含 migration
3. 高风险变更（migration / 认证 / 付费 / 生产配置 / CD workflow）额外标注
4. 等 Erika 说"可以"/"推吧"/"OK"或类似确认后再 push

### 手动部署 fallback（仅 CD 故障时 · 供 Erika 参考）

```bash
cd /opt/clueai/deploy && git pull origin develop && docker compose up -d --build <服务名> && docker compose exec nginx nginx -s reload
```

- `docker compose up -d --build` 和 `nginx -s reload` **必须用 `&&` 连接为一行**（防 502）
- 涉及 migration 时在 `--build` 之前加执行步骤（api 容器无 psql，用 Python + psycopg2）
