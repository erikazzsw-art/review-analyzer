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

## 每次修改代码后的标准流程（强制）

```bash
# 1. 确认当前在 develop 分支
git checkout develop

# 2. 拉取最新代码（避免冲突）
git pull origin develop

# 3. 修改代码（按 CLAUDE.md「UI / 后端修改规则」定位到 frontend/ / backend_api/ / workers/ 之一）

# 4. 本地验证（push 前必做）
python3 -m ruff check backend_api/ workers/ review_analyzer/   # 后端 lint
cd frontend && npm run typecheck                                # 前端类型检查

# 5. 提交并推送到 develop（git add 用具体路径，禁止 `git add .`）
git add <具体文件路径>
git commit -m "fix: [简要描述修改内容]"
git push origin develop

# 6. push 后 GitHub Actions 自动跑 CI（ruff + tsc + next build），无需手动触发
```

## 其他规则
- 每个功能完成后单独提交，不混合多个改动
- 不提交 `.env` 和 `*.db` 文件（完整禁止清单见 CLAUDE.md「禁止跟踪的文件清单」）
- 同 commit 内允许且鼓励同步更新 PROGRESS_V2.md / TEST_LOG.md（见 CLAUDE.md「文档自动更新规则」）

## Pre-commit hook 安装 / 恢复（换机器 · 新 clone 必做）

本项目每次 `git commit` 会用 `.git/hooks/pre-commit` 自动扫描机密（详见 CLAUDE.md「机密保护规则」）。

**⚠️ `.git/hooks/` 是 git 内部目录，不进版本控制** — 换机器、新 clone、`git clone --depth=1` 后 hook 都会缺失。开新工作区第一步就装它，否则失去机密防线。

### 一键安装（直接贴到终端跑）

```bash
cd "/Users/zhangxi/Desktop/Claude Code/评论分析_Web_系统"   # 换机器改成实际路径

cat > .git/hooks/pre-commit <<'HOOK'
#!/usr/bin/env bash
# pre-commit — 本项目机密自动扫描（详见 CLAUDE.md「机密保护规则」）
# 绕过方式：git commit --no-verify（Claude Code 严禁使用）
set -u
RED='\033[0;31m'; GRN='\033[0;32m'; YLW='\033[1;33m'; NC='\033[0m'
failed=0

# 文件名扫描
staged_files=$(git diff --cached --name-only)
danger_files=$(printf '%s\n' "$staged_files" | grep -E "(^|/)(\.env(\.[^/]+)?$|secrets\.toml$|credentials.*\.json$|service-account.*\.json$|.*\.pem$|.*\.key$|.*\.p12$|.*\.pfx$|id_rsa($|\.))" | grep -v "\.env\.example$" || true)
if [ -n "$danger_files" ]; then
  printf "${RED}✘ 检测到机密文件被 staged：${NC}\n"
  printf '%s\n' "$danger_files" | sed 's/^/    /'
  printf "${YLW}    → 请从索引移除：git rm --cached <文件>${NC}\n\n"
  failed=1
fi

# 内容扫描
staged_content=$(git diff --cached -U0)
check_pattern() {
  local hits
  hits=$(printf '%s' "$staged_content" | grep -nE "$1" || true)
  if [ -n "$hits" ]; then
    printf "${RED}✘ 疑似 %s：${NC}\n" "$2"
    printf '%s\n' "$hits" | head -5 | sed 's/^/    /'
    failed=1
  fi
}
check_pattern '(api[_-]?key|secret|password|token)[[:space:]]*=[[:space:]]*['"'"'"]?[A-Za-z0-9_/+.=-]{16,}' "key/secret/password 明文"
check_pattern 'sk-[A-Za-z0-9]{20,}' "OpenAI/DeepSeek 风格 key"
check_pattern 'AIza[0-9A-Za-z_-]{20,}' "Google API key"
check_pattern 'ghp_[A-Za-z0-9]{20,}' "GitHub token"
check_pattern 'xox[baprs]-[A-Za-z0-9-]{10,}' "Slack token"
check_pattern 'postgres(ql)?://[^[:space:]:@<>]+:[^[:space:]@<>]+@' "PostgreSQL 明文密码"
check_pattern 'AES_SECRET_KEY[[:space:]]*=[[:space:]]*[A-Za-z0-9+/=_-]{20,}' "AES/Fernet key"
check_pattern 'open\.feishu\.cn/open-apis/bot/v2/hook/[A-Za-z0-9-]{20,}' "Feishu webhook token"

if [ "$failed" -eq 1 ]; then
  printf "\n${RED}✘ pre-commit 拒绝本次提交。${NC}\n"
  printf "${YLW}  误报请改占位符后重试；紧急绕过（不推荐）：git commit --no-verify${NC}\n"
  exit 1
fi
printf "${GRN}✔ 机密扫描通过${NC}\n"
HOOK

chmod +x .git/hooks/pre-commit
echo "✔ pre-commit hook 已安装：$(wc -l < .git/hooks/pre-commit) 行"
```

### 安装完立即冒烟测试

```bash
# 用 shell 变量拼接假 key，避免文档里出现完整格式的假密钥（否则会被 hook 自身拦下）
FAKE_KEY="sk-$(printf 'a%.0s' {1..25})"                # sk- + 25 个 a
echo "API_KEY = \"$FAKE_KEY\"" > hook_smoke_test.py
git add hook_smoke_test.py
.git/hooks/pre-commit && echo "❌ hook 失效（应该拒）" || echo "✔ hook 生效（拒绝了假密钥）"
git reset HEAD hook_smoke_test.py 2>/dev/null
rm -f hook_smoke_test.py
```

### Hook 覆盖的规则

| 检测项 | 触发示例 |
|-------|---------|
| 机密文件名 | `.env` / `.env.prod` / `*.pem` / `*.key` / `credentials.json` / `service-account*.json` / `secrets.toml` |
| OpenAI/DeepSeek key | `sk-abc123...`（≥20 位） |
| Google API key | `AIzaSyD...`（≥20 位） |
| GitHub token | `ghp_...`（≥20 位） |
| Slack token | `xox[baprs]-...` |
| PostgreSQL 明文密码 | postgres 连接串里 `user:realpwd@host` 形式（含尖括号占位符如 `<PWD>@` 不算） |
| AES/Fernet key | `AES_SECRET_KEY = <20+位>` |
| Feishu webhook | `open.feishu.cn/open-apis/bot/v2/hook/<token>` |
| 通用 key=value | `api_key = "..."` / `secret = ...` / `password = ...` / `token = ...`（值 ≥16 位） |

### 误报处理

- 文档里展示 postgres 连接串 → 用 `postgresql://user:<PASSWORD>@host` 占位（尖括号 `<>` 已加入 regex 白名单，不会误报）
- 文档里展示 API key → 用 `sk-<YOUR_API_KEY>` 或 `[REDACTED]`
- **禁止 `git commit --no-verify`**：Claude Code 严禁使用此逃生舱；Erika 手动执行需自担责任
