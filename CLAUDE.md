markdown
# CLAUDE.md

This file provides guidance to Claude Code when working with code in this repository.

## 核心会话规则

1. **决策确认**：遇到不确定的设计问题，必须先询问 Erika
2. **代码兼容性**：不写兼容性代码，除非明确要求

## 项目概述

评论分析 Web 系统 V1.0 — 跨境电商评论分析工具

- 技术栈：Python 3.10+ / Streamlit / SQLite / DeepSeek API / 飞书 Webhook
- 完整需求和执行计划：详见 `plan.md`


text

## 扩展规范（按需加载）

遇到以下场景时，请先读取对应的规范文件，再执行任务：

| 场景 | 规范文件 |
|------|---------|
| 写 Python 代码 | `docs/python-style.md` |
| 开发 Streamlit 页面 | `docs/streamlit-guide.md` |
| 操作 SQLite 数据库 | `docs/database-guide.md` |
| 调用 DeepSeek API | `docs/api-guide.md` |
| 涉及安全相关代码 | `docs/security-guide.md` |
| 提交 Git 代码 | `docs/git-commit.md` |
| 添加错误处理 | `docs/error-handling.md` |
| 处理文件编码/解析 | `docs/file-guide.md` |

## Git 工作流与进度追踪

- 项目进度文件：`PROGRESS.md`（8个模块，checkbox 驱动）
- 进度更新脚本：`python3 update_progress.py`
- 每次提交代码后，运行 `python3 update_progress.py` 更新进度
- 当模块内任务完成时，在 PROGRESS.md 中将 `[ ]` 改为 `[x]`，然后运行脚本
- 分支策略：main（稳定）→ develop（开发主线）→ feature/mX-*（模块分支）
- 模块完成后合并到 develop，验证通过后合并到 main

## 快速参考

- 类型注解：所有函数参数和返回值必须标注类型
- 参数化查询：SQL 必须用 `?` 占位符，禁止拼接
- 密码存储：使用 `bcrypt`，禁止明文或 MD5
- API Key 加密：使用 `cryptography.fernet`
- 禁止提交：`.env`、`*.db` 文件