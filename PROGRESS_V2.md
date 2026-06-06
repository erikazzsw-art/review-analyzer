# ClueAI V2 项目进度追踪

> 最后更新：2026-06-06  
> V2 目标：商业化升级，4 项核心功能跑通可运营  
> 时间窗口：2026-05-26 ~ 2026-06-20（4 周）  
> 每日投入：7 小时  
> 分工：技术实现由 AI 完成，Erika 负责产品需求定义、PRD、技术选型理解、验收、面试准备

---

## 总体进度

| 指标 | 数值 |
|------|------|
| 总模块数 | 4 |
| 已完成 | 4 |
| 进行中 | 0 |
| 未开始 | 0 |
| 总体进度 | 100% |

```
[████████████████████] 100%
```

---

## 模块进度明细

### V2-M1: 多产品仪表盘 (Multi-Product Dashboard)
- 分支: `develop`（已在主开发线实现）
- 状态: 已完成 | 进度: 100%
- 时间: 提前完成（V1 阶段已落地）
- 任务:
  - [x] 梳理现有 product_id 字段和数据结构
  - [x] 设计聚合查询（按产品聚合负面率、TOP问题、评论量）
  - [x] 实现总览页路由和基础 UI 框架
  - [x] 实现聚合查询后端逻辑
  - [x] 实现总览表格 UI（产品名、评论数、负面率、TOP1问题、最近更新）
  - [x] 实现点击跳转：总览→单产品详情（产品名可点击跳转）
  - [x] 边缘情况处理（0/1个产品、空数据）
  - [x] 置顶 toggle（☆ ↔ 📌）、搜索、删除二次确认

### V2-M2: 版本对比视图 (Version Comparison)
- 分支: `develop`（提前合并进主开发线）
- 状态: 已完成 | 进度: 100% | 依赖: V2-M1
- 时间: 2026-05-27（提前完成）
- 任务:
  - [x] 梳理 version 字段数据结构，设计对比查询逻辑
  - [x] 实现版本对比后端 API（sessions 表新增 version_notes 字段，database.py 新增 update_session_notes）
  - [x] 实现对比 UI：核心指标表 + 产品问题TOP变化 + 产品亮点TOP变化，带 ↑↓— 变化标注
  - [x] 版本选择器 UI（下拉选 V1/V2，并排显示）
  - [x] 环比分析与版本对比合并为统一区块"环比 / 版本对比"，通过对比模式 radio 切换
  - [x] 边缘情况：只有一个版本时的提示
  - [x] 版本升级说明可在结果页内联编辑（expander）
  - [x] 行动建议集成到对比输出

### V2-M3: RAG "Ask your reviews" (检索增强问答)
- 分支: `develop`（已在主开发线实现）
- 状态: 已完成 | 进度: 100% | 依赖: V2-M1
- 时间: 2026-06-03
- 新增技术: Embedding API + Supabase pgvector 余弦检索 + DeepSeek 生成回答；文本检索作为 fallback
- 任务:
  - [x] Supabase 开启 pgvector 扩展脚本
  - [x] comments 表新增 `embedding vector(1536)` 字段脚本
  - [x] 实现评论 embedding 生成与入库
  - [x] 上传评论后批量生成 embedding
  - [x] 历史评论提问时按需补齐 embedding
  - [x] 实现 pgvector 余弦相似度 Top-K 检索
  - [x] 实现稳定文本检索 Top-K（作为配置缺失或向量不可用时的 fallback）
  - [x] 实现 RAG 流程：向量检索→拼接→DeepSeek 生成→返回引用
  - [x] 实现"Ask your reviews"对话框 UI
  - [x] 集成到分析结果页
  - [x] Free 用户入口触发升级提示

### V2-M4: Paddle 计费 (Subscription & Paywall)
- 分支: `develop`（已在主开发线实现）
- 状态: 已完成 | 进度: 100% | 依赖: V2-M1, V2-M3
- 时间: 2026-06-03
- 新增技术: Paddle Checkout、Webhook
- 任务:
  - [x] users 表新增 `plan TEXT DEFAULT 'free'` 字段
  - [x] users 表新增 `paddle_customer_id` 字段
  - [x] 实现 Paddle Checkout 弹窗（升级按钮→支付页）
  - [x] 实现 Webhook 接收支付成功事件→更新 plan 字段
  - [x] 实现计费墙：添加第二产品时触发升级提示
  - [x] 实现计费墙：Ask your reviews 入口触发升级提示
  - [x] 本地语法检查通过
  - [x] V2 整体回归测试（四项功能协同）

---

## V2.5-V3.1 本地收口进展补充（2026-06-04）

- [x] 登录后全局 App Shell 已重新对齐 `clueai_v2_ui_prototype.html` 的柔和 V2 风格，导航、按钮、卡片、上传区和侧边栏视觉已统一
- [x] 新增统一页头层 `review_analyzer/page_shell.py`，核心页与高级页均可显示所属路径、当前说明和快捷回跳
- [x] `对比分析` 空态已补齐完整页头和回路按钮，避免数据不足时只出现提示信息
- [x] `全部功能` 页新增“演示清单”6 条典型路径，便于本地走查工作台、上传、结果、行动、复盘和高级入口
- [x] 今日工作台头部视觉已进一步回调到 V2 风格，和其余页面的体验更一致
- [x] 欢迎页、登录页、试用页已统一回调到系统内 V2 风格，登录前后视觉语气保持一致
- [x] 已登录状态下新增“预览欢迎页”本地验收入口，不必退出登录也能检查欢迎页 UI
- [x] 评论分析上传页已把“开始分析并查看结果”入口前置到文件解析成功后的首屏，并在结果页补上“刚分析完成”的承接提示
- [x] 一级导航已重构为：今日工作台、产品管理、上传评论、评论分析、问评论、行动中心、复盘追踪、宣传文案、推送设置，并移除用户可见的 `全部功能`
- [x] `评论分析` 已收口为容器页，内部只保留 `分析结果 / 对比分析 / 历史记录` 三个子页，旧 `results / compare / history / features` 入口统一归一
- [x] 上传完成后已固定跳转到 `评论分析 > 分析结果`，并自动带上当前 `view_session_id`
- [x] 分析结果页已按 6 段模块重构，前 5 段支持模块级翻译与 XLSX 下载，用户体验模块支持 5 种时间筛选
- [x] 对比分析页已支持三类标准对比 + 功能点定向对比，并补齐整页翻译和 XLSX 下载
- [x] `问评论` 已升级为独立一级导航 `评论问答知识库`，支持按 1-5 个产品聚合评论后做 RAG 问答并展示来源引用
- [x] 今日工作台、上传页、欢迎页、宣传文案页、推送设置页的跳转文案已对齐新的评论工作流结构

---

## 模块依赖图

```
V2-M1 (多产品仪表盘)
├─► V2-M2 (版本对比) ◄─ V2-M1
├─► V2-M3 (RAG) ◄─ V2-M1
└─► V2-M4 (Stripe) ◄─ V2-M1, V2-M3
```

开发顺序: V2-M1 → V2-M2 & V2-M3（M2 先做）→ V2-M4

---

## V2.5-V3.1 执行计划（基于 plan_V2.md）

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development
> or superpowers:executing-plans to implement this plan task-by-task.
> Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 ClueAI 从“评论分析工具”升级为“SKU 口碑改版追踪工具”，让运营、产研、质检和管理者能围绕产品档案完成评论分析、行动跟进和复盘验证。

**Architecture:** 保留现有 Streamlit + Supabase + DeepSeek + 飞书 + Paddle 架构，在当前 `users / sessions / comments / settings` 之上新增产品档案、变体、行动事项、复盘追踪和对比报告数据结构。页面入口从功能菜单升级为“今日工作台 + 产品管理 + 行动中心 + 复盘追踪 + 全部功能”。

**Tech Stack:** Python 3.10+、Streamlit、Supabase PostgreSQL、psycopg2、DeepSeek API、pgvector、飞书 Webhook、Paddle。

### 模块化原则（一个功能一个代码模块）

为降低改错后的回滚成本，V2.5 之后按“一个功能一个代码模块”实施：

- 每个功能优先创建独立 `review_analyzer/*_store.py`，不要继续把所有 CRUD 塞进 `database.py`。
- 每个功能优先创建独立页面文件，例如 `pages/products.py`、`pages/actions.py`、`pages/reviews.py`。
- `app.py` 只负责导航和页面分发，不承载业务逻辑。
- `supabase_schema.sql` 按模块分段追加 SQL，并用注释标记模块名，方便单独审查。
- 每个模块单独提交。若模块失败，只 revert 对应 commit，不影响其他模块。
- 新模块先接入现有 `product_id` 文本字段，逐步迁移到 `product_ref_id` / `variant_ref_id`，避免一次性大迁移。
- 跨模块调用只允许使用公开函数，不直接访问对方内部实现。

### 模块提交与回滚边界

| 模块 | 主要文件 | 提交前验收 | 回滚方式 |
|------|----------|------------|----------|
| 产品档案 | `product_store.py`、`pages/products.py` | 产品组和变体能显示，旧 SKU 数据不报错 | revert 产品档案相关 commit |
| 上传工作流 | `pages/upload.py`、`workflow_prompts.py` | 原上传分析仍可完成，新工作目的可保存 | revert 上传工作流 commit |
| 行动中心 | `action_store.py`、`pages/actions.py` | 可从 TOP 问题创建行动，状态可保存 | revert 行动中心 commit |
| 复盘追踪 | `review_store.py`、`pages/reviews.py` | 可从行动生成复盘，复盘结果可保存 | revert 复盘追踪 commit |
| 多产品对比 | `compare_store.py`、`pages/compare.py` | 可选择多个产品/变体并输出建议 | revert 对比模块 commit |
| 今日工作台 | `workspace_store.py`、`pages/dashboard.py` | 不同角色能看到不同任务入口 | revert 工作台 commit |
| 全部功能 | `pages/features.py` | 高级功能可找到，默认导航不拥挤 | revert 全部功能 commit |

### 范围检查

本计划覆盖 `plan_V2.md` 的 7 个落地阶段。每个阶段可独立开发、独立验收：

| 阶段 | 优先级 | 状态 | 目标 |
|------|--------|------|------|
| V2.5 | P0 | 进行中 | 产品管理：父体产品、变体 SKU、生命周期 |
| V2.6 | P0 | 进行中 | 上传流程：选择工作目的 + 绑定产品档案 |
| V2.7 | P0 | 进行中 | 行动中心：TOP 问题一键创建团队事项 |
| V2.8 | P0 | 进行中 | 复盘追踪：改进前后指标对比与完结 |
| V2.9 | P1 | 已完成（本地实现） | 多产品 / 多变体 / 多版本对比 |
| V3.0 | P1 | 已完成（本地实现） | 角色工作台：运营、产研、质检、管理者 |
| V3.1 | P2 | 已完成（本地实现） | 全部功能地图 + 高级入口收纳 |

### 文件结构映射

| 文件 | 动作 | 职责 |
|------|------|------|
| `supabase_schema.sql` | Modify | 新增 products、product_variants、product_versions、action_items、review_trackers、comparison_reports 表和索引 |
| `review_analyzer/database.py` | Modify | 仅保留共享连接、现有 comments/sessions/users CRUD；新功能不再集中写入此文件 |
| `review_analyzer/product_store.py` | Create | 产品组、变体 SKU、产品版本 CRUD |
| `review_analyzer/action_store.py` | Create | 行动事项 CRUD 与状态流转 |
| `review_analyzer/review_store.py` | Create | 复盘追踪 CRUD、复盘结果更新 |
| `review_analyzer/compare_store.py` | Create | 多产品、同产品、变体、版本对比数据聚合 |
| `review_analyzer/workspace_store.py` | Create | 今日工作台的角色任务、风险 SKU、待复盘摘要 |
| `review_analyzer/app.py` | Modify | 只更新侧边栏导航和页面分发 |
| `review_analyzer/pages/dashboard.py` | Modify | 从产品卡片仪表盘升级为“今日工作台”入口 |
| `review_analyzer/pages/products.py` | Create | 产品管理页：父体产品、变体 SKU、生命周期、版本和评论资产 |
| `review_analyzer/pages/upload.py` | Modify | 上传流程增加工作目的、产品组/变体/版本绑定 |
| `review_analyzer/pages/results.py` | Modify | TOP 问题/亮点增加创建行动、加入复盘入口 |
| `review_analyzer/pages/actions.py` | Create | 行动中心：团队事项列表、状态流转、负责人和复盘时间 |
| `review_analyzer/pages/reviews.py` | Create | 复盘追踪页：改进前后指标、复盘结论、完结/继续跟进 |
| `review_analyzer/pages/compare.py` | Create | 多产品、同产品、同变体、跨版本对比 |
| `review_analyzer/pages/features.py` | Create | 全部功能地图，高级入口收纳 |
| `review_analyzer/workflow_prompts.py` | Create | 根据工作目的输出不同结构的建议：竞品调研、新品监控、Listing 优化、质量复盘、改版验证 |
| `review_analyzer/analyzer.py` | Modify | 仅在必要时接入 workflow prompt，不承载页面或存储逻辑 |
| `review_analyzer/notifier.py` | Modify | 支持行动事项和复盘提醒推送到飞书 |
| `review_analyzer/exporter.py` | Modify | 支持行动事项、复盘报告、多产品对比导出 |
| `plan.md` | Modify | 需求变更日志追加实际落地变更 |
| `业务场景与用户洞察.md` | Modify | 补充新增业务场景和角色洞察 |
| `PROGRESS_V2.md` | Modify | 每完成一个任务更新 checkbox 和进度 |

---

### V2.5 Task 1: 数据模型升级

**Files:**
- Modify: `supabase_schema.sql`
- Create: `review_analyzer/product_store.py`
- Read-only dependency: `review_analyzer/database.py`（只复用 `get_connection`）

- [x] **Step 1: 新增产品档案表结构**

新增表：

```sql
CREATE TABLE IF NOT EXISTS products (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    parent_product_id TEXT NOT NULL,
    name TEXT,
    platform TEXT,
    category TEXT,
    lifecycle_stage TEXT DEFAULT 'growth',
    current_version TEXT DEFAULT 'V1',
    core_selling_points TEXT,
    owner_role TEXT,
    production_cycle_days INTEGER,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(user_id, parent_product_id)
);
```

- [x] **Step 2: 新增变体 SKU 表结构**

```sql
CREATE TABLE IF NOT EXISTS product_variants (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    product_id INTEGER NOT NULL REFERENCES products(id),
    variant_sku TEXT NOT NULL,
    child_asin TEXT,
    color TEXT,
    size TEXT,
    style TEXT,
    material TEXT,
    status TEXT DEFAULT 'active',
    launched_at TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(user_id, variant_sku)
);
```

- [x] **Step 3: 新增版本、行动、复盘、对比表结构**

新增 `product_versions`、`action_items`、`review_trackers`、`comparison_reports`，字段必须覆盖 `plan_V2.md` 第 8、9、10 章定义。

- [x] **Step 4: 在 product_store.py 新增 CRUD**

新增函数：

```python
def create_product(user_id: int, data: dict) -> int: ...
def get_products(user_id: int) -> list[dict]: ...
def get_product_by_id(user_id: int, product_id: int) -> dict | None: ...
def create_variant(user_id: int, product_id: int, data: dict) -> int: ...
def get_variants(user_id: int, product_id: int) -> list[dict]: ...
```

- [x] **Step 5: 验证产品模块可执行**

Run: `python3 -m py_compile review_analyzer/product_store.py`

Expected: PASS，无语法错误。

- [x] **Step 6: 回滚边界**

如果产品档案数据模型实现错误，只 revert 本任务 commit；受影响文件应仅为 `supabase_schema.sql`、`review_analyzer/product_store.py`、`PROGRESS_V2.md`。

- [ ] **Step 7: Commit**

```bash
git add supabase_schema.sql review_analyzer/product_store.py PROGRESS_V2.md
git commit -m "feat: add product and variant data model"
```

---

### V2.5 Task 2: 产品管理页

**Files:**
- Create: `review_analyzer/pages/products.py`
- Modify: `review_analyzer/app.py`
- Modify: `review_analyzer/product_store.py`
- Read-only dependency: `review_analyzer/database.py`（读取现有 sessions/comments 统计）

- [x] **Step 1: 新建产品管理页面骨架**

页面必须包含：

- 产品组列表。
- 产品组详情。
- 变体 SKU 列表。
- 生命周期阶段。
- 当前版本。
- 最大问题、最大亮点、待复盘事项。

- [x] **Step 2: app.py 增加导航**

新增导航项：

```python
"products": ("产品管理")
```

页面分发新增：

```python
elif page == "products":
    render_products()
```

- [x] **Step 3: 产品组视角统计**

从现有 `comments.product_id` / `sessions.product_id` 聚合评论数、好评率、差评率、TOP 问题、TOP 亮点。

- [x] **Step 4: 变体视角预留**

如果评论暂未绑定 `variant_id`，页面显示“未绑定变体”，不阻塞父体产品视图。

- [x] **Step 5: 空状态**

无产品时显示：

> 暂无产品档案。先上传评论，或新建一个产品组。

- [x] **Step 6: 验收**

Run: `streamlit run review_analyzer/app.py`

Expected:

- 侧边栏出现产品管理。
- 已有产品能按产品组展示。
- 无变体数据时页面不报错。

- [ ] **Step 7: 回滚边界**

如果产品管理页体验不符合预期，只 revert 本任务 commit；数据模型模块不回滚。

- [ ] **Step 8: Commit**

```bash
git add review_analyzer/pages/products.py review_analyzer/app.py review_analyzer/product_store.py PROGRESS_V2.md
git commit -m "feat: add product management page"
```

---

### V2.6 Task 3: 上传流程升级

**Files:**
- Modify: `review_analyzer/pages/upload.py`
- Modify: `supabase_schema.sql`
- Modify: `review_analyzer/product_store.py`
- Create: `review_analyzer/workflow_prompts.py`

- [x] **Step 1: 上传 Step 1 增加工作目的**

工作目的选项：

```python
WORKFLOW_PURPOSES = [
    "竞品调研",
    "新品上线监控",
    "日常评论分析",
    "Listing 优化",
    "质量问题复盘",
    "版本改版验证",
]
```

- [x] **Step 2: 上传 Step 1 增加产品绑定**

用户可选择：

- 选择已有产品组。
- 新建产品组。
- 选择变体 SKU。
- 不绑定变体，仅绑定产品组。

- [x] **Step 3: session_data 写入工作目的**

`sessions` 表新增 `workflow_purpose`、`product_ref_id`、`variant_ref_id` 字段。

- [x] **Step 4: 分析完成后按目的跳转**

- 竞品调研 → 分析结果页展示机会点。
- Listing 优化 → 分析结果页突出 Listing 动作。
- 质量问题复盘 → 自动提示加入复盘追踪。
- 版本改版验证 → 展示版本对比区域。

- [x] **Step 5: 验收**

Run: `streamlit run review_analyzer/app.py`

Expected:

- 上传页第一步先选择工作目的。
- 可绑定已有产品或新建产品。
- 评论仍能正常分析入库。

- [ ] **Step 6: 回滚边界**

如果上传流程改造影响原有上传体验，只 revert 本任务 commit；产品管理页和产品数据模型不回滚。

- [ ] **Step 7: Commit**

```bash
git add review_analyzer/pages/upload.py review_analyzer/product_store.py review_analyzer/workflow_prompts.py supabase_schema.sql PROGRESS_V2.md
git commit -m "feat: upgrade upload workflow with product binding"
```

---

### V2.7 Task 4: 行动中心

**Files:**
- Create: `review_analyzer/pages/actions.py`
- Modify: `review_analyzer/pages/results.py`
- Modify: `review_analyzer/app.py`
- Create: `review_analyzer/action_store.py`
- Modify: `supabase_schema.sql`

- [x] **Step 1: 新增 action_items 模块**

函数：

```python
def create_action_item(user_id: int, data: dict) -> int: ...
def get_action_items(user_id: int, status: str | None = None) -> list[dict]: ...
def update_action_status(user_id: int, action_id: int, status: str) -> None: ...
```

- [x] **Step 2: 结果页 TOP 问题增加按钮**

每个 TOP 问题增加：

- 创建运营动作。
- 创建产研动作。
- 创建质检动作。
- 加入复盘追踪。

- [x] **Step 3: 行动中心页面**

页面展示：

- 事项标题。
- 来源产品 / 变体 / 批次。
- 问题标签。
- 当前占比。
- 责任角色。
- 建议动作。
- 预计复盘时间。
- 状态。

- [x] **Step 4: 状态流转**

状态：

```text
待处理 → 处理中 → 待复盘 → 已完结
```

允许“继续跟进”回到处理中。

- [ ] **Step 5: 验收**

Expected:

- 从 TOP 问题创建行动成功。
- 行动中心能看到该事项。
- 状态修改后刷新不丢失。

- [ ] **Step 6: 回滚边界**

如果行动中心实现错误，只 revert 本任务 commit；上传流程、产品管理、产品数据模型不回滚。

- [ ] **Step 7: Commit**

```bash
git add review_analyzer/pages/actions.py review_analyzer/pages/results.py review_analyzer/app.py review_analyzer/action_store.py supabase_schema.sql PROGRESS_V2.md
git commit -m "feat: add action center"
```

---

### V2.8 Task 5: 复盘追踪

**Files:**
- Create: `review_analyzer/pages/reviews.py`
- Create: `review_analyzer/review_store.py`
- Modify: `review_analyzer/pages/actions.py`
- Modify: `review_analyzer/pages/results.py`
- Modify: `review_analyzer/app.py`
- Modify: `supabase_schema.sql`

- [x] **Step 1: 新增 review_trackers 模块**

函数：

```python
def create_review_tracker(user_id: int, data: dict) -> int: ...
def get_review_trackers(user_id: int, status: str | None = None) -> list[dict]: ...
def update_review_tracker_result(user_id: int, tracker_id: int, data: dict) -> None: ...
```

- [x] **Step 2: 支持从行动事项生成复盘**

行动事项中可设置：

- 初始问题标签。
- 初始占比。
- 改进动作。
- 预计生效批次。
- 预计复盘时间。

- [x] **Step 3: 复盘页展示卡片**

每张卡展示：

- 跟进事项。
- 初始问题占比。
- 改进动作。
- 预计生效批次。
- 复盘评论范围。
- 当前占比。
- 结论：有效 / 未改善 / 继续跟进。

- [x] **Step 4: 上传新评论后自动提示可复盘**

当新上传评论的产品、问题标签、复盘时间匹配 tracker 时，分析结果页提示：

> 这批评论可用于复盘「包装破损」问题。

- [x] **Step 5: 验收**

Expected:

- 可从行动中心创建复盘。
- 可手动录入复盘结果。
- 可标记已改善、未改善、继续跟进、已完结。

- [ ] **Step 6: 回滚边界**

如果复盘追踪实现错误，只 revert 本任务 commit；行动中心保留，复盘入口可暂时隐藏。

- [ ] **Step 7: Commit**

```bash
git add review_analyzer/pages/reviews.py review_analyzer/review_store.py review_analyzer/pages/actions.py review_analyzer/pages/results.py review_analyzer/app.py supabase_schema.sql PROGRESS_V2.md
git commit -m "feat: add review tracking workflow"
```

---

### V2.9 Task 6: 多产品 / 多变体 / 多版本对比

**Files:**
- Create: `review_analyzer/pages/compare.py`
- Create: `review_analyzer/compare_store.py`
- Modify: `review_analyzer/app.py`
- Modify: `review_analyzer/workflow_prompts.py`
- Modify: `supabase_schema.sql`

- [x] **Step 1: 新增对比入口**

支持选择：

- 同产品时间对比。
- 同产品版本对比。
- 同父体变体对比。
- 多产品横向对比。
- 自定义对比。

- [x] **Step 2: 新增对比数据聚合模块**

函数：

```python
def get_comparison_dataset(user_id: int, filters: dict) -> dict: ...
```

返回评论数、好评率、差评率、TOP 问题、TOP 亮点、代表评论。

- [x] **Step 3: 多产品对比 UI**

展示：

- 对比表。
- 问题差异。
- 亮点差异。
- 风险产品。
- 推荐动作。

- [x] **Step 4: AI 输出可落地建议**

当前对比页已支持规则建议 + AI 总结双层输出：
- 规则建议负责稳定保底。
- AI 总结负责补充经营判断、风险提醒和推荐动作。

输出示例：

> 带灯床架适合作为高客单价主推款，基础床架适合做价格款，抽屉床架当前质量问题偏高，建议暂缓加大投放。

- [x] **Step 5: 验收**

Expected:

- 能选择 2 个以上产品对比。
- 能选择同父体下多个变体对比。
- 结果包含表格和行动建议。

- [x] **Step 6: 回滚边界**

如果对比页面输出不稳定，只 revert 本任务 commit；原有版本对比和产品管理不回滚。

- [ ] **Step 7: Commit**

```bash
git add review_analyzer/pages/compare.py review_analyzer/compare_store.py review_analyzer/app.py review_analyzer/workflow_prompts.py supabase_schema.sql PROGRESS_V2.md
git commit -m "feat: add product comparison workflows"
```

---

### V3.0 Task 7: 角色化今日工作台

**Files:**
- Modify: `review_analyzer/pages/dashboard.py`
- Create: `review_analyzer/workspace_store.py`
- Modify: `review_analyzer/app.py`

- [x] **Step 1: 仪表盘改为今日工作台**

默认显示：

- 今日最该处理的 1-3 件事。
- 高风险 SKU。
- 待复盘事项。
- 角色推荐动作。

- [x] **Step 2: 角色选择**

角色：

```python
ROLES = ["运营", "产研", "质检", "管理者"]
```

用户可在工作台切换角色视角。

- [x] **Step 3: 每个角色只展示 2-3 个核心入口**

- 运营：差评处理、Listing 优化、复盘。
- 产研：竞品分析、改版验证、新功能追踪。
- 质检：质量客诉、改进记录、复盘。
- 管理者：SKU 风险、未闭环事项、改版效果。

- [x] **Step 4: 验收**

Expected:

- 用户进入系统后先看到今日工作台。
- 不同角色看到不同任务入口。
- 主按钮指向行动中心、产品管理或复盘追踪。

- [x] **Step 5: 回滚边界**

当前首页工作台只改 `dashboard.py + workspace_store.py + app.py`：
- 若不满意，可只回滚这三个文件对应改动。
- 产品管理、行动中心、复盘追踪、对比分析页面仍保持独立可用。

如果今日工作台不符合使用习惯，只 revert 本任务 commit；已有产品管理、行动中心、复盘追踪页面仍可从导航进入。

- [ ] **Step 6: Commit**

```bash
git add review_analyzer/pages/dashboard.py review_analyzer/workspace_store.py review_analyzer/app.py PROGRESS_V2.md
git commit -m "feat: add role-based workspace"
```

---

### V3.1 Task 8: 全部功能地图

**Files:**
- Create: `review_analyzer/pages/features.py`
- Modify: `review_analyzer/app.py`

- [x] **Step 1: 新增全部功能页面**

按分组展示：

- 产品与数据。
- 评论分析。
- 竞品与研发。
- 行动闭环。
- 增长运营。
- 系统设置。

- [x] **Step 2: 默认导航保持克制**

侧边栏默认只保留：

- 今日工作台。
- 产品管理。
- 评论分析。
- 行动中心。
- 复盘追踪。
- 全部功能。

- [x] **Step 3: 高级功能从全部功能进入**

历史记录、宣传文案、飞书推送、Ask your reviews、导出中心不抢默认入口。

- [x] **Step 4: 验收**

Expected:

- 新用户能按工作台完成任务。
- 高级用户能在全部功能中找到完整能力。

- [x] **Step 5: 回滚边界**

当前 V3.1 只新增 `pages/features.py`，并在 `app.py` 收敛默认导航：
- 若功能地图不满意，可只回滚“全部功能页 + 默认导航”相关改动。
- 工作台、产品管理、行动中心、复盘追踪和评论分析主路径不受影响。
- 高级页当前会自动高亮归属到“全部功能”，避免用户误以为自己跳出了主导航体系。
- 当前已新增统一页头层 `page_shell.py`，核心页和高级页会显示所属路径与常用跳转，演示体验更完整。
- 当前登录后 App Shell 已按 `clueai_v2_ui_prototype.html` 回调到 V2 柔和风格，视觉方向与前面确认的原型重新对齐。

如果全部功能地图信息架构不清晰，只 revert 本任务 commit；默认导航不受影响。

- [ ] **Step 6: Commit**

```bash
git add review_analyzer/pages/features.py review_analyzer/app.py PROGRESS_V2.md
git commit -m "feat: add all features hub"
```

---

### 执行自检清单

- [ ] `plan_V2.md` 中每个 P0 需求都有对应任务。
- [ ] 新增表都有对应 CRUD。
- [ ] 新增页面都已加入 `app.py` 导航和页面分发。
- [ ] 上传、分析结果、行动中心、复盘追踪之间能串成闭环。
- [ ] 旧数据只有 `product_id` 时仍能显示，不强制用户立即迁移。
- [ ] Free / Pro 计费墙逻辑不被新产品管理破坏。
- [ ] 所有 Python 文件通过 `python3 -m py_compile`。
- [ ] 完整流程验收：新建产品组 → 添加变体 → 上传评论 → 分析 → 创建行动 → 加入复盘 → 上传复盘评论 → 完结。

---

## 下阶段商业化能力补齐清单

> 背景：对比 VOC AI / Shulex、Jungle Scout 等成熟商业化产品后，ClueAI 当前更适合先走“轻量 AI SaaS + SKU 口碑改版闭环”路线。不要一开始追求海量数据平台，而是先把“评论变行动，行动能复盘”做顺，再逐步补齐自动化、数据资产和企业级能力。

### 当前技术栈基线

| 层级 | 当前技术 | 当前成熟度 |
|------|----------|------------|
| 前端 / Web | Streamlit + HTML 原型 | MVP 可用，商业化 UI 仍需打磨 |
| 后端语言 | Python 3.10+ | 可支撑早期功能 |
| 数据库 | Supabase PostgreSQL | 可支撑早期 SaaS 和多用户 |
| 向量检索 | Supabase pgvector | 已具备 RAG 雏形 |
| AI 分析 | DeepSeek API | 已具备评论分析和建议生成能力 |
| RAG 问答 | embedding + pgvector + DeepSeek | 已具备当前产品评论问答 |
| 文件解析 | CSV / Excel / Word / TXT | 已覆盖手动上传场景 |
| 认证 | 自建登录注册 + bcrypt | 可用，后续需组织和权限 |
| 计费 | Paddle Checkout + Webhook | 已具备早期付费墙 |
| 通知 | 飞书 Webhook | 已具备基础团队通知 |

### 与成熟商业化产品的差距

| 维度 | ClueAI 当前 | 成熟商业化产品 | 下阶段策略 |
|------|-------------|----------------|------------|
| 数据来源 | 手动上传评论为主 | 自动抓取 / API / 大规模历史评论库 | 先做定时上传和半自动采集，再考虑平台 API |
| 数据规模 | 用户自己的 SKU 数据 | 海量评论、关键词、ASIN、类目、竞品库 | 先沉淀用户自己的产品口碑资产 |
| 自动化 | 上传后分析 | 定时监控、评分下降提醒、竞品变化提醒 | 先做定时分析和风险提醒 |
| 业务覆盖 | 评论分析、RAG、初步计费 | 选品、Listing、广告、竞品、客服、品牌保护 | 先聚焦 SKU 改版闭环 |
| 团队协作 | 行动中心规划中 | 权限、任务、团队、企业报表 | 先做角色、事项、状态、复盘 |
| UI 成熟度 | 原型 + Streamlit 页面 | 完整 SaaS 交互、引导、空状态、模板 | 统一为柔和清爽女性运营风格 |
| 数据可信度 | Prompt + 标签逻辑 | 长期数据资产、口径稳定、模型评估 | 增加标签准确率、Prompt 版本、复盘指标校验 |
| 商业化 | Paddle 初步接入 | 套餐、试用、用量限制、企业销售 | 先完善 Free / Pro / 团队版边界 |

### P0：当前阶段必须补齐

这些能力直接服务 ClueAI 的核心差异化，优先级最高。

| 编号 | 能力 | 目标 | 对应模块 |
|------|------|------|----------|
| P0-1 | 产品组 + 变体 SKU | 支持真实电商父体/子体结构 | V2.5 产品管理 |
| P0-2 | 工作目的上传 | 让用户按场景上传评论，不从功能开始 | V2.6 上传流程 |
| P0-3 | 行动中心 | TOP 问题能转成运营、产研、质检事项 | V2.7 行动中心 |
| P0-4 | 复盘追踪 | 改进动作能持续追踪并判断是否有效 | V2.8 复盘追踪 |
| P0-5 | 多产品/多变体对比 | 支持主推款、问题款、机会款判断 | V2.9 多产品对比 |
| P0-6 | UI 风格统一 | 全站使用 `clueai_v2_ui_prototype.html` 的柔和清爽风格 | V3.0 UI 重构 |

### P1：商业化体验增强

这些能力提升留存和付费转化，但不应抢在闭环能力前面。

| 编号 | 能力 | 目标 | 建议落地方式 |
|------|------|------|--------------|
| P1-1 | 定时分析 | 用户不用每次手动进入系统检查 | 后台定时任务 + 飞书提醒 |
| P1-2 | 风险提醒 | 负面率、TOP 问题、评分异常自动提醒 | 复用 notifier.py，增加规则类型 |
| P1-3 | 多产品 RAG | 支持“5 款床架一起问” | 从当前单产品 RAG 扩展过滤范围 |
| P1-4 | 组织和角色 | 支持运营、产研、质检、管理者角色 | users 增加 organization / role |
| P1-5 | 操作记录 | 记录谁创建/处理/完结了事项 | action_items 增加 audit 字段 |
| P1-6 | 导出报告 | 输出复盘报告、多产品对比报告 | exporter.py 增加报告类型 |
| P1-7 | Next.js 营销站（独立部署） | 拿到 SEO 流量、建立商业 SaaS 信任感、降低 CAC | 新建 `clueai.com` 主站，包含首页/定价/功能/案例/博客；app.clueai.com 仍由 Streamlit 提供；详见下文「前端架构与商业化落地路径」 |

### P2：长期商业化护城河

这些能力接近成熟商业平台，不建议在核心闭环未跑顺前投入太多。

| 编号 | 能力 | 目标 | 风险 |
|------|------|------|------|
| P2-1 | 自动抓取评论 | 降低用户上传成本 | 平台规则、稳定性、合规成本 |
| P2-2 | 大规模竞品库 | 建立数据资产 | 采集、清洗、存储和成本压力大 |
| P2-3 | 关键词 / Listing / 广告联动 | 从评论分析延伸到增长优化 | 容易变成大而全工具 |
| P2-4 | 客服话术 / 售后联动 | 将评论洞察接到客服体系 | 需要多平台工单和客服系统集成 |
| P2-5 | 企业级权限 | 支持大团队、部门、权限矩阵 | 需要更完整账号体系 |
| P2-6 | 产品层 Streamlit → Next.js 全迁移 | 提升 UI、性能和工程化，支持移动端 PWA / 嵌入式 widget / 团队版 | 仅在 MRR > $3k 后再考虑；营销层不在此范围（已拆到 P1-7） |

### 下阶段推荐执行顺序

| 顺序 | 阶段 | 做什么 | 为什么 |
|------|------|--------|--------|
| 1 | V2.5 | 产品组 + 变体 SKU | 没有产品档案，后续闭环无法稳定 |
| 2 | V2.6 | 工作目的上传 | 降低用户理解成本，避免功能堆叠 |
| 3 | V2.7 | 行动中心 | 让分析结果变成团队动作 |
| 4 | V2.8 | 复盘追踪 | 形成 ClueAI 最核心差异化 |
| 5 | V2.9 | 多产品 / 多变体对比 | 支持运营策略和主推款判断 |
| 6 | V3.0 | 角色化工作台 + UI 统一 | 让不同伙伴进来就知道做什么 |
| 7 | V3.1 | 全部功能地图 | 收纳高级能力，不打扰主流程 |
| 7.5 | V3.1.5 | **Next.js 营销站独立部署（拿到 3-5 个付费用户后立即启动）** | 跨境卖家 60-70% 来自 SEO，Streamlit 没有 SEO；营销页是付费转化的信任构建器 |
| 8 | V3.2 | 定时分析 + 风险提醒 | 提升留存和团队协作价值 |
| 9 | V3.3 | 组织角色 + 操作记录 | 为团队版/企业版做准备 |
| 10 | V4.0 | 自动采集 / 平台 API | 向成熟商业数据平台过渡 |
| 11 | V5.0 | 产品层 Streamlit → Next.js 全迁移（MRR > $3k 后再考虑） | UI 升级带动客单价、支持移动端 / 嵌入式 widget / 团队版 |

### 商业化判断

ClueAI 当前不应正面硬刚成熟平台的数据规模，而应先打一个更尖锐的切入点：

**中国跨境卖家的 SKU 口碑改版闭环工具。**

短期判断标准：

- [ ] 用户是否能在 3 步内从评论生成行动事项。
- [ ] 运营、产研、质检是否能在各自页面看到自己的待处理事项。
- [ ] 一个问题是否能从“发现”走到“复盘完结”。
- [ ] 多次进入系统时，用户是否能看到自己沉淀的产品口碑资产。
- [ ] 用户是否愿意为多产品管理、复盘追踪、Ask your reviews 付费。

---

## 前端架构与商业化落地路径（2026-06-04 新增）

> 背景：Erika 提出"是否需要从 Streamlit 切到 Next.js"。从**商业化盈利**的角度（不是面试角度）重新审视，结论不是"全切或全留"的二选一，而是**双层架构**。

### 商业化角度，Streamlit 的 3 个真实痛点

| 痛点 | 商业损失 | 严重程度 |
|------|----------|----------|
| 没有 SEO | 跨境卖家在 Google/百度搜"亚马逊评论分析工具"找不到 ClueAI → 获客只能靠付费投放，CAC 居高不下 | 🔴 致命 |
| 登录前页面"工具感"重 | 试用→付费转化率低，$19-49/月的产品需要"商业 SaaS 质感"建立信任 | 🟡 严重 |
| 移动端体验差 | 跨境卖家有大量在手机上看数据的场景（出差、晚上、临时查 SKU），Streamlit 移动端基本不可用 | 🟡 严重 |

### 推荐方案：双层架构（不是全切）

```
┌─────────────────────────────────────────┐
│  营销层 (Next.js / Framer / Webflow)     │
│  - clueai.com 主站 (SEO + 转化)          │
│  - /pricing /features /blog /case-studies│
│  - 注册 / 登录 / Paddle 结账落地页        │
└──────────────┬──────────────────────────┘
               │ 用户付费后跳转
               ▼
┌─────────────────────────────────────────┐
│  产品层 (保留 Streamlit)                  │
│  - app.clueai.com 已登录后的工作台         │
│  - 产品管理 / 上传 / 分析 / RAG / 行动中心 │
│  - 内部工具，UI 精致度要求低              │
└─────────────────────────────────────────┘
```

**为什么这样分：**

1. B2B SaaS 60-70% 的付费用户来自 SEO 和内容营销（"亚马逊差评分析"、"SKU 改版工具"、"跨境卖家 VOC"这类长尾词）—— Streamlit 一个都吃不到
2. 营销页是"信任构建器"，跨境卖家月付 $19-49 之前会反复看首页、定价、案例 —— 这一层必须像商业 SaaS
3. 产品层的用户已经付过钱了 —— 看重的是"分析准不准、行动闭环顺不顺"，不是 UI 多炫

### 按 MRR 里程碑触发的迁移路径（不按时间推进）

| 里程碑 | 该做什么 | 成本 | 预期收益 |
|--------|----------|------|----------|
| 0 付费用户 → 第 1 个付费用户 | 拿现有 Streamlit 找种子用户（社群、知乎、亚马逊卖家圈），手动 onboarding | 0 | 验证付费意愿 |
| MRR $0 → $500 | 新建 Next.js / Framer 营销站（5-7 个页面）。app 保持 Streamlit | 1-2 周或外包 ~$500 | 拿到第一批 SEO/口碑流量 |
| MRR $500 → $3k | 营销站补案例 + 博客内容 + 试用引导优化。app 仍保持 Streamlit | 持续 | 内容飞轮启动 |
| MRR $3k → $10k | 这时才考虑把 app 也迁到 Next.js（有钱投入 + UI 要求 + 团队版/嵌入式需求） | 3-4 周 | UI 升级带动客单价 |
| MRR > $10k | 全栈现代化，加移动端 PWA、嵌入式 widget、企业版 | - | 进入规模化 |

### V3.1.5 营销站最小可行范围（P1-7 的具体落地）

**前置条件：拿到 3-5 个付费用户后立即启动。**

页面清单（5-7 个）：

| 页面 | 目的 | 内容要点 |
|------|------|----------|
| `/` 首页 | 吸引 + 价值主张 | "跨境卖家的 SKU 口碑改版闭环工具"，3 个核心价值点 + demo 截图 + CTA |
| `/pricing` 定价页 | 转化 | Free / Pro / Team 三档，对照表 + FAQ + Paddle Checkout 按钮 |
| `/features` 功能页 | 教育 | 多产品仪表盘、版本对比、Ask your reviews、行动中心、复盘追踪 |
| `/case-studies` 案例页 | 信任 | 2-3 个种子用户案例（床架 SKU 改版、新品监控等） |
| `/blog` 博客 | SEO 飞轮 | "亚马逊差评分析"、"SKU 改版方法论"、"跨境卖家 VOC 实操"长尾词 |
| `/login` `/signup` | 入口 | 跳转到 app.clueai.com 的 Streamlit 登录页 |

技术栈选项：

| 选项 | 成本 | 适用 |
|------|------|------|
| Framer | $15-25/月 | Erika 自己拖拽搭建，最快 1 周上线，适合 MVP 验证 |
| Webflow | $14-39/月 | 同 Framer，但博客 CMS 更强 |
| Next.js + Tailwind + shadcn/ui | 0（代码自管） | AI 实现 1-2 周，可控性最高，未来可演进到产品层 |

**推荐路径：先用 Framer 起步（1 周上线），MRR $500 后再考虑迁 Next.js。** 不要在拿到付费验证前花精力做 Next.js 营销站。

### 一个反直觉的事实

很多 AI SaaS 创始人犯的错是"先把产品做精致再开始卖" —— 结果是 6 个月后产品很美但没人用。

ClueAI 现在该做的不是切 Next.js，是**先用现有 Streamlit 卖出去**：

- 写 3-5 篇内容（"我用 ClueAI 复盘了一个亚马逊床架的 SKU 改版"）
- 在亚马逊卖家群、Knowhere、雨果跨境社群发
- 拉 5 个种子用户免费用，换案例和反馈
- 如果 5 个种子用户里 1 个愿意付费 → 立刻做营销站（PMF 信号有了）
- 如果 5 个都不愿付费 → 不是 UI 问题，是产品问题，切 Next.js 也救不了

### 验收标准

| 阶段 | 验收信号 | 进入下一阶段的触发条件 |
|------|----------|------------------------|
| 当前（V3.1.5 启动前） | 5 个种子用户在用 Streamlit 版 | 至少 1 个种子用户愿意付费 → 启动 P1-7 营销站 |
| P1-7 营销站上线 | clueai.com 首页 + 定价 + 5 个功能页上线，Paddle Checkout 跑通 | 自然搜索月访问 > 500 / MRR > $500 → 加博客内容 |
| 营销站成熟 | 月新增付费 > 5 / MRR > $3k | 触发 V5.0 产品层迁移 Next.js |

---

## Next.js 迁移执行计划（2026-06-05 新增）

> 背景：在重新核对当前代码结构、`plan_V2.md`、`plan.md`、`业务场景与用户洞察.md` 以及成熟竞品的公开架构后，Erika 已明确采用新的迁移决策：
>
> ```text
> 全系统逐步迁到 Next.js
> 保留 Python 业务能力
> 双栈并行过渡
> 单模块独立实施、独立验收、独立回滚
> ```
>
> 这意味着 2026-06-04 的“营销站优先、产品层后置观察”判断，作为历史商业化讨论仍保留，但后续真正执行时，应以本节为最新口径。

### 新阶段目标

**Goal:** 在不破坏当前 Streamlit 主应用可用性的前提下，把 ClueAI 迁移为 `Next.js + FastAPI + Redis/RQ + Supabase` 架构。

**Architecture:** Next.js 负责前端、URL 路由和页面状态；FastAPI 逐步承接 Python 业务逻辑；Redis + RQ 负责长任务异步化；Streamlit 在迁移期间只保留为过渡壳和回退入口。

**Tech Stack:** Next.js App Router、TypeScript、Tailwind CSS、Radix primitives、FastAPI、Pydantic、Redis、RQ、Supabase PostgreSQL、Supabase Storage、Nginx。

### 模块化执行原则

- 每次只做一个迁移模块
- 当前模块未通过测试和人工验收，不进入下一个模块
- 每个模块必须有独立文件边界、独立运行命令、独立验收标准、独立回滚边界
- 新模块失败时，只回滚该模块，不允许把当前 Streamlit 主流程一起改坏
- 当前项目的主体代码默认继续可运行，迁移期间禁止“一次性切换”

### 文件与计划文档

- 迁移目标文档：`docs/nextjs-migration-target-2026-06-05.md`
- 迁移实施计划：`docs/superpowers/plans/2026-06-05-nextjs-migration-implementation-plan.md`

### Next.js 迁移模块总览

| 模块 | 状态 | 目标 | 回滚边界 |
|------|------|------|----------|
| `NX-M1` 前端工程骨架 | 已完成 | 新建 Next.js 工程、登录前页面、全局设计 Token | 仅回滚 `frontend/` |
| `NX-M2` FastAPI 骨架与认证 | 已完成 | 新建 API 服务、登录注册、HttpOnly Cookie 会话 | 仅回滚 `backend_api/` 与少量认证辅助改动 |
| `NX-M3` 工作台与产品管理迁移 | 已完成 | 打通 `/workspace` 与 `/products` 的 API + 页面 | 仅回滚工作台/产品相关新接口与新页面 |
| `NX-M4` 上传与分析任务异步化 | 已完成 | 上传拆分、分析 job 化、Redis + RQ 跑通 | 仅回滚上传/分析异步链路与 worker |
| `NX-M5` 结果/对比/历史迁移 | 已完成 | 迁移 `results / compare / history`，支持 URL 直达与显式对比报告生成 | 仅回滚分析阅读层 |
| `NX-M6` 问评论/行动/复盘迁移 | 已完成 | 迁移闭环能力与 RAG 页面 | 仅回滚闭环相关模块 |
| `NX-M7` 文案/设置/计费迁移 | 未开始 | 迁移低频高级页与 Paddle | 仅回滚商业化协同页 |
| `NX-M8` 部署与 Streamlit 下线路径 | 未开始 | ECS + Nginx + 容器化部署，明确下线条件 | 仅回滚部署配置 |

### 执行顺序

| 顺序 | 模块 | 为什么先做 |
|------|------|------------|
| 1 | `NX-M1` | 先建立新的前端壳层和登录前体验，不碰旧主流程 |
| 2 | `NX-M2` | 先把认证与会话从 `st.session_state` 中剥离出来 |
| 3 | `NX-M3` | 工作台和产品管理最适合先作为只读模块迁移 |
| 4 | `NX-M4` | 上传与分析是核心工作流，异步化是整个迁移的中轴 |
| 5 | `NX-M5` | 结果、对比、历史依赖上传与分析链路稳定后再迁 |
| 6 | `NX-M6` | 闭环能力在分析阅读层稳定后再接入 |
| 7 | `NX-M7` | 文案、设置、计费优先级低于核心工作流 |
| 8 | `NX-M8` | 所有主路径稳定后再做部署固化与 Streamlit 下线 |

### 当前迁移验收总标准

- [x] Next.js 登录前页面全部可访问，桌面端与移动端无布局错乱
- [x] FastAPI 登录、注册、退出、`/me` 可用，不依赖 `st.session_state`
- [ ] 上传、分析、结果跳转已完成异步 job 化
- [x] 结果页、对比页、历史页支持 URL 直达
- [x] 问评论、行动中心、复盘追踪形成完整闭环
- [ ] Paddle 计费链路在新架构下可用
- [ ] 阿里云部署结构可启动，Nginx 反代、域名与 HTTPS 可工作
- [ ] Streamlit 在迁移期间始终保留可回退主路径

### NX-M1: 前端工程骨架

- [x] 建立 `frontend/` 目录
- [x] 完成 `package.json / tsconfig / next.config / tailwind.config`
- [x] 建立 `layout.tsx` 和全局设计 Token
- [x] 建立 `/ /login /register /trial /pricing` 页面骨架
- [x] 本地跑通 `npm run dev`
- [x] 验收首页首屏 3 秒内说清“评论洞察 -> 行动跟进 -> 复盘验证”
- [x] 若失败，只回滚 `frontend/` 与本节进度勾选

NX-M1 验收记录：

- `npm run typecheck`：PASS
- `npm run build`：PASS
- `npm run dev -- --hostname 127.0.0.1 --port 3100`：PASS
- 当前新增公开页面：
  - `/`
  - `/login`
  - `/register`
  - `/trial`
  - `/pricing`
  - `/workspace`（占位页，供后续模块承接）
- 当前仅新增 `frontend/` 工程，不影响现有 Streamlit 主流程

### NX-M2: FastAPI 骨架与认证

- [x] 建立 `backend_api/` 目录
- [x] 建立 `main.py / config.py / deps.py`
- [x] 建立 `/auth/register /auth/login /auth/logout /me`
- [x] 继续复用现有用户表与 `bcrypt`
- [x] 建立 HttpOnly Cookie 会话
- [x] 本地跑通 `uvicorn backend_api.app.main:app --reload`
- [x] 若失败，只回滚 `backend_api/` 与认证迁移辅助改动

NX-M2 验收记录：

- `python3 -m py_compile backend_api/app/main.py backend_api/app/config.py backend_api/app/deps.py backend_api/app/routes/auth.py backend_api/app/routes/me.py backend_api/app/schemas/auth.py`：PASS
- `python3 -c "import fastapi, uvicorn; print('api-deps-ok')"`：PASS
- `python3 -m uvicorn backend_api.app.main:app --host 127.0.0.1 --port 8100`：PASS
- `GET /health`：PASS
- `POST /auth/register -> GET /me -> POST /auth/logout`：PASS
- 当前已建立的 API 边界：
  - `/health`
  - `/auth/register`
  - `/auth/login`
  - `/auth/logout`
  - `/auth/password/reset/request`
  - `/auth/password/reset/confirm`
  - `/me`
- 当前仍保留现有 Streamlit 登录主链路，FastAPI 认证层作为 Next.js 迁移专用新模块存在

### NX-M3: 工作台与产品管理迁移

- [x] 新增 `GET /workspace/summary`
- [x] 新增 `GET /products`
- [x] 建立 `/workspace` 页面
- [x] 建立 `/products` 页面
- [x] 验收数据口径与当前 Streamlit 页面一致
- [x] 若失败，只回滚工作台/产品模块

### NX-M4: 上传与分析任务异步化

- [x] 新增 `POST /uploads`
- [x] 新增 `POST /analysis/jobs`
- [x] 新增 `GET /analysis/jobs/{job_id}`
- [x] 建立 `workers/` 目录
- [x] 接入 Redis + RQ
- [x] 建立 `/upload` 页面
- [x] 验收上传 -> job -> 处理中 -> 结果跳转完整跑通
- [x] 若失败，只回滚异步链路与 worker

### NX-M5: 结果 / 对比 / 历史迁移

- [x] 新增 `GET /analysis/sessions/{session_id}/results`
- [x] 新增结果、对比、历史读取接口
- [x] 建立 `/analysis/results`
- [x] 建立 `/analysis/compare`
- [x] 建立 `/analysis/history`
- [x] 验收 URL 直达，不依赖页面内隐式状态
- [x] 若失败，只回滚阅读层模块

### NX-M6: 问评论 / 行动中心 / 复盘追踪迁移

- [x] 新增 `POST /qa/questions`
- [x] 新增 `GET/POST/PATCH /actions`
- [x] 新增 `GET/POST/PATCH /trackers`
- [x] 建立 `/qa`
- [x] 建立 `/actions`
- [x] 建立 `/reviews`
- [x] 验收从结果页创建 action，再生成 tracker，再回写复盘结果
- [x] 若失败，只回滚闭环模块

NX-M6 验收记录：

- `python3 -m py_compile backend_api/app/main.py backend_api/app/routes/analysis.py backend_api/app/routes/compare.py backend_api/app/routes/actions.py backend_api/app/routes/qa.py review_analyzer/action_store.py review_analyzer/review_store.py review_analyzer/insight_engine.py review_analyzer/translation.py review_analyzer/analysis_export.py`：PASS
- `cd frontend && npx tsc --noEmit`：PASS
- `/qa`：PASS，支持 1-5 个产品聚合问评论，并返回引用评论
- `/actions`：PASS，支持 action 列表、状态流转和一键加入复盘
- `/reviews`：PASS，支持 tracker 列表与复盘结果回写
- 从 `/analysis/results` 可直接创建 action，再把 action 生成 tracker，最后在复盘页回写结果：PASS

### NX-M7: 宣传文案 / 设置 / 计费迁移

- [x] 新增 `GET /settings`
- [x] 新增 `PATCH /settings`
- [x] 新增 `POST /billing/checkout`
- [x] 新增 `POST /billing/webhook`
- [x] 建立 `/copywriter`
- [x] 建立 `/settings`
- [x] 验收设置、Paddle、文案页都可用
- [x] 若失败，只回滚低频高级页和计费模块

NX-M7 验收记录：

- `python3 -m py_compile backend_api/app/main.py backend_api/app/routes/settings.py backend_api/app/routes/copywriter.py backend_api/app/routes/billing.py review_analyzer/paddle_billing.py review_analyzer/pages/copywriter.py review_analyzer/pages/settings.py`：PASS
- `cd frontend && npx tsc --noEmit`：PASS
- `/copywriter`：PASS，文案页可读取批次并生成平台文案
- `/settings`：PASS，设置页可读取飞书、Paddle 和通知配置
- `POST /billing/checkout` 与 `POST /billing/webhook`：PASS，计费链路可创建并回写套餐状态
- 低频高级页和计费模块已按独立边界落地，主闭环不受影响

### NX-M8: 部署与 Streamlit 下线路径

- [x] 建立 `frontend / backend_api / workers` Dockerfile
- [x] 建立 `deploy/nginx.conf`
- [x] 建立 `deploy/docker-compose.yml`
- [x] 编写 `docs/deployment-nextjs-fastapi-aliyun.md`
- [x] 明确 `clueai.com / app.clueai.com / api.clueai.com` 域名结构
- [x] 明确 Streamlit 下线前置条件
- [x] 若失败，只回滚部署配置，不回滚产品代码

NX-M8 验收记录：

- `python3 -m py_compile backend_api/app/main.py backend_api/app/routes/settings.py backend_api/app/routes/copywriter.py backend_api/app/routes/uploads.py workers/runner.py workers/queue.py workers/jobs.py`：PASS
- `cd frontend && npx tsc --noEmit`：PASS
- `python3 -c "import pathlib, yaml; yaml.safe_load(pathlib.Path('deploy/docker-compose.yml').read_text())"`：PASS
- `docker compose -f deploy/docker-compose.yml config`：当前环境未安装 `docker`，无法执行；配置文件本身已通过 YAML 解析检查
- `https://clueai.com / https://app.clueai.com / https://api.clueai.com`：域名分层与回退口径已写入部署文档
- `robots.txt / sitemap.xml / opengraph-image`：营销站 SEO 基础已补齐，营销页可索引、应用页 noindex
- Streamlit 保留为回退口，部署层与业务层边界已明确

## 每日计划

### Week 1：多产品仪表盘（05/26-05/30）✅ 功能已提前完成

> M1 功能已在 V1 阶段实现，本周重心调整为：产品文档沉淀 + 技术选型理解 + 面试准备

| 日期 | 上午 10:00-12:00 | 下午 13:00-15:30 | 下午 15:30-17:30 | 复盘 17:30-18:00 |
|------|-----------------|-----------------|-----------------|-----------------|
| 05/26 周一 | ✅ 梳理 V2 整体规划，确认 4 模块依赖关系 | ✅ 版本对比功能需求讨论 + 业务场景设计 | 写多产品仪表盘 PRD（基于已实现功能反向写） | ✅ 面试题 Q9 |
| 05/27 周二 | ✅ 版本对比功能实现（AI 完成） | ✅ 环比分析与版本对比合并设计 | 完善仪表盘 PRD：补充指标定义、验收标准 | ✅ 面试题 Q14 |
| 05/28 周三 | 技术选型理解：Streamlit vs Next.js 边界（何时该换？） | 技术选型理解：Supabase（PostgreSQL）vs 专用向量库的取舍 | 整理 ClueAI 技术选型决策文档（面试素材） | ✅ 面试题 Q13 |
| 05/29 周四 | M3 RAG 预研：什么是 RAG？4 环节概念理解 | M3 RAG 预研：竞品调研（哪些产品用了 RAG？效果如何？） | 构思"问评论"功能的业务场景和交互设计 | 复盘本周进度 |
| 05/30 周五 | 截图记录 M1/M2 功能效果 + 写产品说明文字 | 项目叙事文档初稿：V1→V2 产品决策链 | 更新 PROGRESS_V2，规划下周 | 规划下周 |

### Week 2：版本对比视图（06/02-06/06）✅ 功能已提前完成

> M2 功能已于 05/27 完成，本周重心调整为：PRD 写作 + RAG 产品需求预研 + 项目叙事

| 日期 | 上午 10:00-12:00 | 下午 13:00-15:30 | 下午 15:30-17:30 | 复盘 17:30-18:00 |
|------|-----------------|-----------------|-----------------|-----------------|
| 06/02 周一 | 写版本对比功能 PRD（重点：业务场景、为什么这么设计） | PRD 细化：用户旅程图 + 异常流程 + 指标定义 | 技术选型理解：DeepSeek API vs OpenAI 的取舍（成本/效果/合规） | 面试题 Q12 |
| 06/03 周二 | M3 RAG 产品需求定义：用户是谁、什么场景、解决什么问题 | M3 RAG 交互设计：对话框 UI 草图、输入输出规范 | M3 RAG 成功指标定义：怎么衡量"回答得好"？ | 面试题 Q20 |
| 06/04 周三 | 技术选型理解：pgvector vs Pinecone vs Weaviate（PM 视角的边界对比） | M3 RAG PRD 初稿：功能范围、技术约束、验收标准 | 整理面试中如何讲解 RAG（用 ClueAI 作为案例） | 面试题 Q22 |
| 06/05 周四 | 项目叙事文档完善：补充 M1/M2 的决策过程和数据验证 | 准备作品集：核心截图 + 产品说明 + 数据效果 | 写用户引导文案（帮用户理解版本对比功能怎么用） | 复盘本周 |
| 06/06 周五 | 复盘 M1/M2：做了哪些产品决策？哪些是对的？哪些可以改进？ | 整理 RAG 学习资料清单（概念级，非代码） | 更新 PROGRESS_V2 + 确认 M3 开发计划 | 规划下周 |

### Week 3：RAG "Ask your reviews"（06/09-06/13）

> 技术实现由 AI 完成；你的重点是 RAG 概念理解（PM 面试必问）、产品需求把控、效果验收

| 日期 | 上午 10:00-12:00 | 下午 13:00-15:30 | 下午 15:30-17:30 | 复盘 17:30-18:00 |
|------|-----------------|-----------------|-----------------|-----------------|
| 06/09 周一 | RAG 理论学习：4 环节（切片→向量化→检索→生成），理解每步的作用 | AI 实现：Supabase 开启 pgvector + Embedding API 调通 | 写 RAG 理论笔记（用自己的话解释，面试能讲清楚） | 面试题 Q1 |
| 06/10 周二 | RAG 理论学习：RAG vs 微调（什么场景用哪个？ClueAI 为什么选 RAG？） | AI 实现：批量向量化 + 检索 + 生成回答 | 写 RAG 理论笔记（下）：RAG 的局限性和失效模式 | 面试题 Q6 |
| 06/11 周三 | 技术选型理解：pgvector vs Pinecone（成本/规模/运维的取舍） | AI 实现：端到端联调 | 体验测试：自己试用"问评论"功能，记录体验问题 | 面试题 Q2 |
| 06/12 周四 | RAG 进阶：HyDE、重排序是什么？什么时候需要？（概念级） | 效果验收：设计 20 个测试问题，评估回答质量 | 整理验收报告：哪些问题回答得好/不好，为什么 | 面试题 Q8 |
| 06/13 周五 | 整理"如何在面试中讲 RAG"（用 ClueAI 案例） | 截图记录 RAG 功能效果 + 写产品说明 | 更新 PROGRESS_V2 + 补 RAG 理论笔记 | 规划下周 |

### Week 4：Stripe 计费 + 整体测试（06/16-06/20）

> 技术实现由 AI 完成；你的重点是定价策略、商业模式设计、项目叙事文档

| 日期 | 上午 10:00-12:00 | 下午 13:00-15:30 | 下午 15:30-17:30 | 复盘 17:30-18:00 |
|------|-----------------|-----------------|-----------------|-----------------|
| 06/16 周一 | 学习 SaaS 定价策略：Freemium vs 试用期 vs 按量计费 | AI 实现：Stripe 集成（注册、Checkout、Webhook） | 写定价方案文档 + 单位经济模型（为什么 $19/月？） | 面试题 Q10 |
| 06/17 周二 | 研究计费墙设计：什么时候拦截？怎么让用户愿意付费？ | AI 实现：计费墙弹窗逻辑 | 写升级引导文案 + 价值主张（用户为什么该付费） | 面试题 Q16 |
| 06/18 周三 | 竞品定价调研：类似工具怎么定价？ClueAI 的差异化在哪？ | 端到端验收：Free→付款→Pro 功能解锁 | 记录验收结果 + 优化体验细节 | 面试题 Q18 |
| 06/19 周四 | V2 整体产品回顾：四项功能协同验证 | 写 ClueAI V2 项目叙事文档（完整版） | 准备作品集最终版：截图 + 数据 + 决策故事 | 复盘本周 |
| 06/20 周五 | 项目叙事文档打磨 + 录制产品 demo 视频 | 面试模拟：用 ClueAI 讲产品设计、技术选型、数据驱动 | 更新 PROGRESS_V2 最终版，V2 完结 | 总结 |

---

## Git 分支策略

| 分支 | 用途 |
|------|------|
| `main` | 稳定版本（V1） |
| `develop-v2` | V2 开发主线 |
| `feature/v2-mX-*` | 各模块独立分支 |

工作流: 模块分支 → 合并到 develop-v2 → 验证通过 → 合并到 main

---

## 变更日志

| 日期 | 模块 | 变更 |
|------|------|------|
| 2026-05-26 | - | 建立 V2 进度追踪系统 |
| 2026-05-27 | V2-M1 | 确认多产品仪表盘已在 V1 阶段完整实现，标记为完成 |
| 2026-05-27 | V2-M2 | 版本对比视图完成，与环比分析合并为统一区块 |
| 2026-06-03 | V2-M3 | Ask your reviews 升级为向量版 RAG：embedding 入库、pgvector 余弦检索、DeepSeek 回答、引用评论、Pro 计费墙 |
| 2026-06-03 | V2-M4 | Paddle 计费链路完成：plan 字段、Checkout、Webhook、第二产品限制 |
| 2026-06-03 | V2.5 | 本地完成产品档案数据模型与产品管理页首版，兼容旧 `product_id` 历史数据显示，未推送部署 |
| 2026-06-03 | V2.6 | 本地完成上传流程升级首版：工作目的、产品绑定、自动识别 ASIN/SKU 子变体、session 绑定上下文，未推送部署 |
| 2026-06-03 | V2.7 | 本地完成行动中心首版：独立 action store、结果页创建动作、行动中心状态流转，未推送部署 |
| 2026-06-03 | V2.8 | 本地完成复盘追踪首版：独立 review store、行动中心生成 tracker、复盘页结果录入、结果页复盘提醒，未推送部署 |
| 2026-06-04 | 商业化路径 | 新增「前端架构与商业化落地路径」章节：双层架构决策、按 MRR 里程碑触发的迁移路径、V3.1.5 营销站（P1-7）最小可行范围；P2-6 修订为"产品层 Streamlit → Next.js 全迁移"，仅在 MRR > $3k 后启动 |
| 2026-06-06 | NX-M7 | 本地完成宣传文案 / 设置 / 计费迁移收口：`/copywriter`、`/settings`、Paddle Checkout / Webhook、计费状态回写，文案与设置页可用 |
| 2026-06-06 | NX-M8 | 本地完成部署与 Streamlit 下线路径：`frontend / backend_api / workers` 容器、Nginx、docker-compose、阿里云部署说明、域名分层与回退边界；同时补齐营销站 SEO 基础 |
| 2026-06-06 | SEO | 本地补齐 Next.js 营销站可上线 SEO 基础：首页 / 定价 / 试用页独立 metadata、应用页 noindex、`robots.txt` / `sitemap.xml` / `opengraph-image` |
| 2026-06-04 | V4 技术路线 | 新增「V4 技术优化与商业化落地路线图」章节：基于 Shulex 竞品对比 + 10 万条多类目数据资产，规划 7 个核心任务（数据资产化、商业化基建、LLM 输出加固、成本优化、ABSA 小模型、用户反馈回路、Niche 商业化），目标 8 周内把单条成本降 85%、准确率提升至 95%、找到 5 个付费用户验证 PMF |

---

## V4 技术优化与商业化落地路线图（2026-06-04 新增）

> 背景：基于 Shulex / VOC AI 竞品技术选型对比，结合 10 万条多类目评论源数据资产，制定从「LLM+Prompt 单点架构」演进到「ABSA 小模型 + Embedding 聚类 + LLM 生成」三层架构的可商业化落地技术路线。
>
> 优化函数：商业化盈利（不是面试展示），目标按 ROI 排序。
>
> 总投入：8 周，与 V2.5-V3.1 业务功能并行推进。

### 核心思路（一句话）

把 Shulex 用 18 个月走完的路压缩到 8 周：先用 10 万条数据立起「评测基准 + 品类 Taxonomy + Bad Case 库」，再分阶段把 ABSA 任务从 LLM 收回到小模型，把 LLM 留给生成式任务，配合 Embedding 聚类做成本优化；同时完成商业化基建（收款、多租户、部署），让前 50 个付费用户可承接。

### 与 Shulex 的差距地图

| 维度 | 当前 V1/V2 | 目标 V4 | Shulex 现状 | 优先级 |
|------|---------|---------|------------|--------|
| 分析单元 | 逐条 LLM | Embedding 聚类 + LLM 打标签 | 同 | P0 |
| 输出格式 | Prompt 约束自由文本 | 强制 JSON Schema | 同 | P0 |
| Prompt 版本 | 无版本管理 | Git + DB 双层追踪 | LangSmith | P0 |
| ABSA 任务 | 纯 LLM | fine-tuned 小模型 | 同 | P1 |
| 反馈回路 | 无 | 用户纠错 → bad case 库 → few-shot | 同 | P1 |
| 成本模型 | 线性增长 | 聚类后近似固定 | 同 | P0 |
| Fallback | 单 DeepSeek | 三级链路 | 多模型 | P1 |

### 预期收益对比

| 指标 | 当前 V1 | 优化后 V4 | 提升幅度 |
|------|--------|----------|---------|
| 情感分类准确率 | ~90% | 95-97% | +5-7pp |
| 痛点分类准确率 | <85% | 90-93% | +5-8pp |
| 100 条评论分析耗时 | 31 秒 | 8-12 秒 | 降 60-70% |
| 单条评论成本 | ¥0.0002 | ¥0.00003 | 降 85% |
| 10 万条月分析成本 | ¥20-40 | ¥3-6 | SaaS 毛利可控 |
| Vendor 依赖 | 单 DeepSeek | 三级 fallback | SLA 可承诺 |

---

### V4-T1: 数据资产化（Week 1-2，最高 ROI）

**目标：** 把 10 万条原始数据加工成可复用的评测基准、品类 Taxonomy 和 Bad Case 库，作为后续所有优化的度量底座。

**Files:**
- Create: `data/golden_set/` 目录（评测基准集）
- Create: `data/taxonomy/` 目录（品类 Aspect 词典）
- Create: `review_analyzer/eval/` 模块（评测脚本）
- Create: `scripts/build_golden_set.py`、`scripts/build_taxonomy.py`

- [ ] **Step 1: 数据预处理**
  - 从 10 万条原始数据中按品类 × 情感 × 评分分层采样 2000 条
  - 清洗 unrecognizable / 空内容 / 重复评论
  - 输出 `data/golden_set/raw_2000.csv`

- [ ] **Step 2: 人工标注 Golden Set**
  - 标注字段：情感（正/负/中）、Aspect（如包装/功能/品控）、痛点分类
  - 标注协议：双人交叉标注，分歧由 Erika 仲裁
  - 拆分：1500 条训练集 + 500 条测试集
  - 锁版本：`data/golden_set/v1.0/`，永远不动

- [ ] **Step 3: 构建品类 Taxonomy**
  - 用 GPT-4o 对 10 万条做全量 Aspect 抽取
  - 按品类聚合（家居 / 3C / 服饰 / 母婴 / 宠物 / 小家电...）
  - 人工 review + 合并同义词（packaging damage / damaged packaging）
  - 存入 PostgreSQL `category_aspect_taxonomy` 表
  - 输出 `data/taxonomy/v1.0/{category}.yaml`

- [ ] **Step 4: 建立 Bad Case 库**
  - 把当前 V1/V2 测试中所有误判样本归档
  - 字段：原文、AI 输出、正确输出、错误类型、修复方案
  - 存入 PostgreSQL `bad_cases` 表，作为后续 few-shot 种子

- [ ] **Step 5: 评测自动化脚本**
  - 实现 `python3 -m review_analyzer.eval.run --prompt-version vX --golden-set v1.0`
  - 输出准确率、召回率、F1、混淆矩阵、Token 消耗
  - 集成到 GitHub Actions：每次改 Prompt 强制跑回归

- [ ] **Step 6: 验收标准**
  - Golden Set 500 条测试集准确率基线建立
  - Taxonomy 覆盖至少 5 个核心品类
  - Bad Case 库初始至少 50 条

---

### V4-T2: 商业化基建（Week 1-3，与 T1 并行）

**目标：** 让产品具备承接前 50 个付费用户的能力。

**Files:**
- Modify: `review_analyzer/database.py`（多租户隔离审计）
- Modify: `review_analyzer/auth.py`（配额计数）
- Create: `review_analyzer/quota.py`（用量限制）
- Modify: `review_analyzer/paddle_billing.py`（套餐档位）
- Create: `legal/privacy.md`、`legal/terms.md`

- [ ] **Step 1: 部署迁移**
  - 当前 Streamlit Cloud 免费版不允许商业用途
  - 迁移目标：Render / Railway / 自建 VPS
  - 配置自定义域名 `app.clueai.com`
  - 验收：HTTPS 正常、登录注册无误

- [ ] **Step 2: 多租户数据隔离审计**
  - 审计所有 SQL 查询是否带 `user_id` 过滤
  - 重点：comments、sessions、products、actions、trackers
  - Supabase 加 RLS（Row Level Security）兜底

- [ ] **Step 3: 套餐配额实现**
  - Free: 500 条/月、1 个产品、无 Ask reviews
  - Pro ¥99/月: 5000 条/月、10 个产品、Ask reviews
  - Team ¥299/月: 30000 条/月、不限产品、API、多账号
  - 实现 `quota.check(user_id, action)`，超额触发升级提示

- [ ] **Step 4: Paddle 三档商品配置**
  - 在 Paddle 后台创建 Pro / Team 两个 Product
  - Webhook 处理升级、降级、取消事件
  - 加用户中心页面：当前套餐、用量、续费、取消

- [ ] **Step 5: 法务底线**
  - 隐私协议（数据使用范围、第三方共享、删除流程）
  - 用户协议（服务范围、责任边界、终止条款）
  - GDPR / 中国个保法基础合规

- [ ] **Step 6: 验收**
  - 用户注册 → 试用 → 升级 → 用量到顶 → 续费完整链路跑通
  - 多租户隔离测试：A 用户看不到 B 用户任何数据

---

### V4-T3: LLM 输出加固（Week 3-4）

**目标：** 用最低成本把当前 LLM 输出的稳定性和准确率拉满，作为引入小模型前的过渡方案。

**Files:**
- Modify: `review_analyzer/analyzer.py`（强制 JSON Schema）
- Create: `review_analyzer/prompts/`（Prompt 文件按版本管理）
- Create: `review_analyzer/prompt_registry.py`（版本路由）
- Modify: `supabase_schema.sql`（comments 表加 `prompt_version` 字段）

- [ ] **Step 1: 强制 JSON Schema 输出**
  - DeepSeek API 已支持 `response_format={"type": "json_object"}`
  - 定义结构：`{sentiment, aspects[], pain_points[], highlights[], suggested_actions[]}`
  - 加 schema 校验，校验失败自动重试 1 次
  - 预期收益：解析错误率降 30%，category 措辞不一致问题基本消除

- [ ] **Step 2: Prompt 版本管理**
  - `prompts/sentiment_v1.0.md`、`prompts/aspect_v1.0.md`、`prompts/insight_v1.0.md`
  - 每个 Prompt 文件包含：版本号、生效日期、变更说明、Few-shot 示例
  - 数据库每条分析记录写入 `prompt_version` 字段
  - 改 Prompt 强制走 PR + Golden Set 回归

- [ ] **Step 3: 评分覆写规则强化**
  - 当前已有"≤3 判负面 / ≥4 判正面"
  - 补：评分缺失时才走 LLM 情感分析
  - 补：unrecognizable 评论从统计分母排除（已在 V1 做过，确认仍生效）

- [ ] **Step 4: Few-shot 注入 Bad Case**
  - 从 V4-T1 的 Bad Case 库中挑选 5-10 个高频错例
  - 注入 Prompt 末尾作为 few-shot 示例
  - 在 Golden Set 上 A/B 测试新旧 Prompt

- [ ] **Step 5: 验收标准**
  - 跑 V4-T1 Golden Set 500 条测试集
  - 情感准确率 ≥ 92%
  - 痛点分类准确率 ≥ 88%
  - JSON 解析失败率 < 1%

---

### V4-T4: 成本优化（Week 4-6，与 T3 并行）

**目标：** 用 Embedding 聚类前置层 + 多级缓存 + Fallback 链路，把单条评论成本降 85%。

**Files:**
- Create: `review_analyzer/embedding.py`（Embedding 生成）
- Create: `review_analyzer/clustering.py`（HDBSCAN 聚类）
- Modify: `review_analyzer/analyzer.py`（接入聚类前置层）
- Create: `review_analyzer/llm_router.py`（多模型 Fallback）
- Modify: `supabase_schema.sql`（comments 加 cluster_id、embedding 字段已有）

- [ ] **Step 1: Embedding 模型选型**
  - 候选 1: BGE-m3（开源，多语言，1024 维，本地 CPU 可跑，零成本）
  - 候选 2: OpenAI text-embedding-3-small（$0.02/1M tokens，质量稳定）
  - 推荐：BGE-m3 本地部署，用 ONNX Runtime 加速
  - 验收：100 条评论 Embedding 生成 < 3 秒

- [ ] **Step 2: HDBSCAN 聚类前置层**
  - 100 条评论先 Embedding → HDBSCAN 聚类（min_cluster_size=3）
  - 每个 cluster 选代表评论（中心向量最近的 1 条）
  - LLM 只对代表评论 + cluster 总数做分析（10-15 次调用）
  - 同 cluster 评论共享分析结果

- [ ] **Step 3: 多级缓存**
  - L1：评论 hash 命中（全字段 hash，节省 100% 成本）
  - L2：评分覆写（≤3/≥4 跳过 LLM）
  - L3：Embedding 相似度 > 0.95 复用最近邻分析结果
  - 缓存命中率监控写入 `analytics-tracking/`

- [ ] **Step 4: 多模型 Fallback 链路**
  - 主：DeepSeek-V3（中文优势 + 成本低）
  - 备 1：Qwen-Max（国内可用性高，与 DeepSeek 解耦）
  - 备 2：Claude Haiku 4.5（英文质量保险）
  - 熔断：连续 3 次失败自动切换，写入监控日志
  - 配置在 `llm_router.py`，业务代码无感知

- [ ] **Step 5: Token 成本看板**
  - 按用户 / 品类 / 时间聚合 API 消耗
  - 单用户单条评论平均成本指标
  - 异常用量告警（单用户日消耗 > 阈值）

- [ ] **Step 6: 验收标准**
  - 100 条评论分析耗时从 31 秒降到 8-12 秒
  - 单条评论平均成本从 ¥0.0002 降到 ¥0.00003
  - LLM 调用量降至原来的 15% 以下
  - 准确率不低于 V4-T3 基线

---

### V4-T5: ABSA 小模型 fine-tune（Week 6-8，可选）

**目标：** 把 ABSA（情感 + Aspect 抽取）这种结构化任务从 LLM 收回到 fine-tuned 小模型，是准确率天花板的真正解药。

**注意：** 这是高 ROI 但高投入的任务，建议在 V4-T1/T2/T3/T4 完成且拿到至少 5 个付费用户后再启动。如果 PMF 验证不通过，跳过此任务。

**Files:**
- Create: `ml/absa/` 目录（训练脚本、数据集、模型 checkpoint）
- Create: `ml/absa/train.py`、`ml/absa/infer.py`
- Create: `review_analyzer/absa_service.py`（FastAPI 推理服务）
- Modify: `review_analyzer/analyzer.py`（ABSA 走小模型，洞察生成留 LLM）

- [ ] **Step 1: 训练数据准备**
  - 标注数据 1.5 万条来源：Golden Set 1.5k + LLM 标注 1万 + 评分覆写 5k
  - 拆分：12k 训练 / 1.5k 验证 / 1.5k 测试
  - 多标签格式：情感 3 类 × Aspect N 类

- [ ] **Step 2: 模型选型**
  - 中文：`hfl/chinese-roberta-wwm-ext-large`
  - 英文：`microsoft/deberta-v3-base`
  - 微调方式：LoRA（节省显存，单卡 4090 可训）
  - 训练时长：单语言 4-6 小时

- [ ] **Step 3: 模型部署**
  - 转 ONNX 格式（CPU 推理，单条 50ms）
  - FastAPI 包装，部署到 Render / 自建 VPS
  - 与 Streamlit 主应用解耦，独立扩缩容

- [ ] **Step 4: A/B 切换**
  - 配置开关：`USE_ABSA_MODEL=true/false`
  - 灰度：先 10% 流量走小模型，监控准确率
  - 全量切换前 Golden Set 必须达标

- [ ] **Step 5: 验收标准**
  - 情感准确率 ≥ 95%
  - Aspect 分类准确率 ≥ 90%
  - 推理成本降至 ¥0.00001/条（降 95%）
  - 不再依赖 DeepSeek 可用性（情感 + Aspect 部分）

---

### V4-T6: 用户反馈回路（Week 5-7）

**目标：** 让用户纠错沉淀为产品改进的弹药，形成数据飞轮。

**Files:**
- Modify: `review_analyzer/pages/results.py`（评论旁加"分类错误"按钮）
- Create: `review_analyzer/feedback_store.py`（反馈 CRUD）
- Modify: `supabase_schema.sql`（新增 `user_feedback` 表）
- Create: `scripts/feedback_to_bad_case.py`（定时把反馈转成 bad case）

- [ ] **Step 1: UI 反馈入口**
  - 每条评论分析结果旁加"👎 分类错误"按钮
  - 点击弹出表单：错误类型、正确分类、备注
  - 提交后写入 `user_feedback` 表

- [ ] **Step 2: 反馈管理后台**
  - 仅管理员（Erika）可见
  - 列表展示：用户、原文、AI 输出、用户标注、状态
  - 状态：待审核 / 已采纳 / 已拒绝
  - 已采纳的反馈自动转 Bad Case 库

- [ ] **Step 3: Few-shot 自动迭代**
  - 每周定时任务：从 Bad Case 库选 Top 10 高频错例
  - 自动更新 Prompt 的 few-shot 示例
  - 必须先跑 Golden Set 回归，准确率不退化才合并

- [ ] **Step 4: 用户激励**
  - 每个有效反馈奖励 50 条免费分析额度
  - 反馈榜单展示在用户中心（鼓励高质量反馈）

- [ ] **Step 5: 验收标准**
  - 用户能在 5 秒内完成一次反馈提交
  - 反馈到 Bad Case 库的转化率 ≥ 30%
  - Prompt 月度迭代不影响 Golden Set 基线

---

### V4-T7: Niche 商业化启动（Week 4-8，与技术任务并行）

**目标：** 选定一个垂直品类，找到前 5 个付费用户，验证 PMF。

**Files:**
- Create: `marketing/whitepaper/` 目录（垂直品类白皮书）
- Create: `marketing/case_studies/` 目录（用户案例）
- Create: `marketing/seo_content/` 目录（SEO 内容）

- [ ] **Step 1: 选定垂直品类**
  - 候选品类（基于 10 万条数据分布）：
    - 小家电（咖啡机/榨汁机/扫地机）
    - 3C 配件（耳机/充电器/数据线）
    - 母婴用品
    - 宠物用品
  - 决策维度：用户付费意愿、SKU 迭代速度、Erika 运营经验匹配度
  - 由 Erika 拍板，不在此处决策

- [ ] **Step 2: 品类白皮书**
  - 用 10 万条数据跑出选定品类 TOP10 痛点报告
  - 包装成《2026 跨境电商 [品类] 用户痛点白皮书》
  - 在社群、知乎、公众号免费发放，留资换 PDF
  - 这是 1 人创业最高 ROI 的获客内容

- [ ] **Step 3: Demo 数据池**
  - 用 10 万条数据填充新用户首次登录的"示例报告"
  - 让用户 30 秒内看到产品价值，提高试用转化

- [ ] **Step 4: 种子用户招募**
  - 进 10 个跨境电商社群（雨果跨境 / 知无不言 / 知识星球）
  - 私信 50 个目标用户邀请试用
  - 提供 14 天全功能试用 + 半价首年（¥49/月）锁定前 20 个付费用户

- [ ] **Step 5: 1 对 1 跟进**
  - 每个试用用户主动建联（电话 / 微信）
  - 录用户反馈视频（后续作为案例）
  - 收集 bad case 反哺 V4-T3 / V4-T6

- [ ] **Step 6: SEO 内容种子**
  - 写 5 篇知乎 / 小红书种草文（"我用 ClueAI 复盘了一个亚马逊 [品类] 的 SKU 改版"）
  - 录制 3 分钟产品 demo 视频
  - 为 V3.1.5 营销站积累内容资产

- [ ] **Step 7: 验收标准**
  - 8 周内拿到 20 个免费试用用户

  - 5 个付费用户（约 ¥250-500 MRR）
  - 至少 1 个用户案例可公开使用

---

### V4 任务依赖关系

```
V4-T1 (数据资产化) ──┬──► V4-T3 (LLM 输出加固) ──┬──► V4-T5 (ABSA 小模型)
                     ├──► V4-T4 (成本优化)       │
                     └──► V4-T6 (反馈回路) ◄─────┘
                                                  
V4-T2 (商业化基建) ──► V4-T7 (Niche 商业化)
                       └──► (依赖 T3 + T4 完成)
```

执行顺序建议：
1. **Week 1-2:** T1（数据资产化）+ T2（商业化基建）并行启动 — 这是所有后续工作的地基
2. **Week 3-4:** T3（LLM 输出加固）+ T7 启动品类选定与白皮书
3. **Week 4-6:** T4（成本优化）+ T7 种子用户招募
4. **Week 5-7:** T6（反馈回路）+ T7 1对1 跟进
5. **Week 6-8:** T5（ABSA 小模型，可选）+ T7 转化付费

### V4 优先级精简版（如果只能做 3 件事）

1. **V4-T1 数据资产化（Week 1-2）** — 不做这个，后面所有优化都没法度量。零技术风险，纯运营投入。
2. **V4-T7 Niche 商业化（Week 4-8）** — 不做这个，技术优化全是沉没成本。商业化决定产品方向。
3. **V4-T4 成本优化（Week 4-6）** — 单点技改成本最低、降本最猛，让前 50 个用户的毛利可控。

### V4 阶段验收标准（商业化角度）

- [ ] 单条评论成本从 ¥0.0002 降到 ¥0.00003（降 85%）
- [ ] Golden Set 测试集情感准确率 ≥ 95%、痛点分类 ≥ 90%
- [ ] 有 ≥ 5 个付费用户（任一档位）
- [ ] 单用户月毛利 ≥ ¥80（按 ¥99 入门版计算）
- [ ] Prompt 改动不再造成历史口径漂移（版本管理生效）
- [ ] DeepSeek 故障 5 分钟内自动切换备用模型
- [ ] 至少 1 个垂直品类白皮书发布并产生留资

---
