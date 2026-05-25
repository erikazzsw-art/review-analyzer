# CLAUDE.md

This file provides guidance to Claude Code when working with code in this repository.

## 核心会话规则

1. **决策确认**：遇到不确定的设计问题，必须先询问 Erika
2. **代码兼容性**：不写兼容性代码，除非明确要求

## 项目概述

评论分析 Web 系统 V1.0 — 跨境电商评论分析工具

- 技术栈：Python 3.10+ / Streamlit / Supabase (PostgreSQL) / DeepSeek API / 飞书 Webhook
- 完整需求和执行计划：详见 `plan.md`

## 扩展规范（按需加载）

遇到以下场景时，请先读取对应的规范文件，再执行任务：

| 场景 | 规范文件 |
|------|---------|
| 写 Python 代码 | `docs/python-style.md` |
| 开发 Streamlit 页面 | `docs/streamlit-guide.md` |
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
| 新功能 / 需求变更 | `plan.md` | 在需求变更日志对应日期下追加条目（格式见文件顶部规范） |
| 新功能 / 需求变更 | `业务场景与用户洞察.md` | 在对应章节补充新的业务需求、用户洞察或核心逻辑 |
| 模块任务完成 | `PROGRESS.md` | 将对应任务的 `[ ]` 改为 `[x]`，然后运行 `python3 update_progress.py` |

**执行顺序**：先更新文档，再提交 Git。文档更新和代码提交合并为同一个 commit。

## Git 工作流与进度追踪

- 项目进度文件：`PROGRESS.md`（8个模块，checkbox 驱动）
- 进度更新脚本：`python3 update_progress.py`
- 每次提交代码后，运行 `python3 update_progress.py` 更新进度
- 当模块内任务完成时，在 PROGRESS.md 中将 `[ ]` 改为 `[x]`，然后运行脚本
- 分支策略：main（稳定）→ develop（开发主线）→ feature/mX-*（模块分支）
- 模块完成后合并到 develop，验证通过后合并到 main

## 快速参考

- 类型注解：所有函数参数和返回值必须标注类型
- 参数化查询：SQL 必须用 `%s` 占位符（psycopg2），禁止拼接
- 密码存储：使用 `bcrypt`，禁止明文或 MD5
- API Key 加密：使用 `cryptography.fernet`
- 禁止提交：`.env`、`*.db` 文件

## Architecture
/review_analyzer             # Analysis modules (23 files)

## 项目文件说明（重要！）

### 线上网站入口文件
- **唯一入口**：`app.py`（Streamlit 主文件）
- 所有用户可见的页面内容（欢迎页面、注册按钮、登录按钮、图表、评论列表等）都写在 **Python 文件** 中，使用 Streamlit 组件
- **禁止修改**：`prototype.html` 是一个废弃的静态原型文件，不会被部署到线上

### 修改规则（强制）
1. 当用户要求修改"页面"、"按钮"、"欢迎页"、"注册/登录"、"图表"、"评论显示"等内容时
2. **必须修改 `app.py` 中的 Streamlit 代码**
3. **绝对不要修改 `prototype.html`**
4. 如果不确定修改哪个文件，先询问用户

## Git 分支与部署配置（重要！）

### 当前配置
- Streamlit Cloud 部署分支：**develop**
- 日常修改的目标分支：**develop**
- main 分支：仅用于稳定版本，不要直接推送

### 每次修改代码后的标准流程（强制）

当用户提出 bug 修改需求时，请按以下步骤执行：

```bash
# 1. 确认当前在 develop 分支
git checkout develop

# 2. 拉取最新代码（避免冲突）
git pull origin develop

# 3. 修改代码（修改 app.py）

# 4. 提交并推送到 develop
git add .
git commit -m "fix: [简要描述修改内容]"
git push origin develop