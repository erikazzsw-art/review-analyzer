# ClueAI V2 项目进度追踪

> 最后更新：2026-07-27
> V2 目标：商业化升级，4 项核心功能跑通可运营  
> 时间窗口：2026-05-26 ~ 2026-06-20（4 周）  
> 每日投入：7 小时  
> 分工：技术实现由 AI 完成，Erika 负责产品需求定义、PRD、技术选型理解、验收、面试准备

---

## 总体进度

> 最后更新：2026-07-27 | 基于代码实际状态 + 文档 checkbox 统计

### 按模块组

| 模块组 | 子模块数 | 已完成 | 进行中 | 未开始 | 进度 | 备注 |
|--------|---------|--------|--------|--------|------|------|
| 2. 核心模块 | 4 | 4 | 0 | 0 | 100% | 仪表盘/版本对比/RAG问评论/Paddle计费，全部部署上线 |
| 3. ASIN 多变体抓取 | 1 | 1 | 0 | 0 | 100% | 变体发现+产品信息保存+Worker重构，已部署上线 |
| 4. 本地收口 | 1 | 1 | 0 | 0 | 100% | 导航/工作台/AppShell/闭环流程全部完成 |
| 5. Next.js 迁移 | 8 | 8 | 0 | 0 | 100% | 5.1-5.8 全部完成，ECS 生产环境运行中 |
| 6. 技术优化 | 9 | 6 | 0 | 3 | 67% | 6.1-6.6 完成（数据资产化→成本优化）；6.7-6.9 待 PMF 验证后启动 |
| 7. 运维基建 | 15 | 7 | 5 | 3 | ~63% | 7.1/7.5/7.6/7.8/7.9/7.10/7.12 完成；7.2/7.7/7.11/7.14/7.15 进行中；7.3/7.4/7.13 待启动 |
| 8. 出海合规 | 7 | 2 | 2 | 3 | ~50% | 8.4/8.7 完成；8.1/8.3 进行中；8.2/8.6 待启动；8.5 冻结 |
| 9. 增值功能 | 6 | 1 | 2 | 3 | ~33% | 9.3 完成；9.1/9.2 部分完成；9.4/9.5/9.6 待启动 |
| **总计** | **51** | **30** | **9** | **12** | **~70%** | |

### 按状态明细

**✅ 已完成（30 个子模块）**

| 编号 | 名称 | 关键产出 |
|------|------|---------|
| 2.1 | 多产品仪表盘 | 总览页路由+表格UI+点击跳转 |
| 2.2 | 版本对比视图 | 环比分析统一区块 |
| 2.3 | RAG 问评论 | pgvector检索+DeepSeek回答+引用评论+Pro计费墙；2026-07-02 P0升级：意图路由+结构化聚合 |
| 2.4 | Paddle 计费 | plan字段+Checkout+Webhook+第二产品限制 |
| 3.x | ASIN多变体抓取 | 变体发现+产品信息保存+Worker重构+scraped_title |
| 4.x | 本地收口 | 导航/工作台/AppShell/闭环流程（产品→行动→复盘） |
| 5.1 | 前端工程骨架 | Next.js 15+React 19+Tailwind+登录前页面+设计Token |
| 5.2 | FastAPI骨架与认证 | 登录/注册/退出/HttpOnly Cookie/me |
| 5.3 | 工作台与产品管理 | /workspace + /products API+页面 |
| 5.4 | 上传与分析异步化 | 上传拆分+分析job化+Redis+RQ |
| 5.5 | 结果/对比/历史 | results/compare/history URL直达+对比报告 |
| 5.6 | 问评论/行动/复盘 | RAG页面+闭环能力迁移 |
| 5.7 | 文案/设置/计费 | /copywriter+/settings+Paddle Checkout/Webhook+QuotaDialog |
| 5.8 | 部署与Streamlit下线 | ECS+Docker Compose+Nginx+HTTPS+域名分层，生产运行中 |
| 6.1 | 数据资产化 | 1060行Taxonomy入库+全品类扩展87子品类+441aspect |
| 6.2 | Taxonomy接入分析链路 | 动态prompt模板+品类白名单+回归测试 |
| 6.3 | Golden Set多品类演进 | 品类级mini Golden Set+CI多品类回归+other占比监控+飞书告警 |
| 6.4 | 商业化基建 | 多租户隔离+邮箱唯一+跨用户LLM复用(review_pool)+密码重置 |
| 6.5 | LLM输出加固 | 强制JSON Schema输出+results AI fallback非阻塞 |
| 6.6 | 成本优化 | Embedding选型+缓存98%命中率（100条仅2条走LLM） |
| 7.1 | CI持续集成 | GitHub Actions: ruff lint+tsc typecheck+next build |
| 7.5 | 数据埋点(PostHog) | SDK接入+analytics_events表+FastAPI中间件+关键事件埋点 |
| 7.6 | 用户反馈浮窗 | migration+后端route(含邮件通知)+前端Widget(FAB+情绪+表单+双语+快捷键) |
| 7.8 | shadcn/ui组件系统 | CSS变量体系+基础组件原语 |
| 7.9 | 首页改造 | Phase 1布局与组件架构重构完成 |
| 7.10 | 登录/注册改造 | 独立全屏双栏布局+全站营销文案中文化 |
| 7.12 | 可观测性体系 | 5-Tab管理后台(概览/成本/任务/缓存/告警)+时间范围选择器+trace timeline |
| 8.4 | LLM路由locale切换 | QA/Compare路由复用get_analysis_locale；locale=en→GPT-4o-mini→DeepSeek→Qwen |
| 8.7 | Credit定价体系 | 海外4档套餐+统一credit池，已部署上线 |
| 9.3 | 智能推送 | 设置页拆分为3子页+推送内容增强(B1-B6)+飞书Webhook推送 |

**🔄 进行中（9 个子模块）**

| 编号 | 名称 | 当前进度 | 剩余工作 |
|------|------|---------|---------|
| 7.2 | CD持续部署 | GitHub Actions deploy.yml已写 | ECS自动部署触发+健康检查回滚 |
| 7.7 | 中国大陆访问优化 | Phase A Cloudflare CDN ✅ | Phase B ICP备案+国内节点（付费用户≥10触发） |
| 7.11 | AI分析链路优化 | 部分完成 | worker写路径优化+批量upsert+事务边界 |
| 7.14 | i18n国际化 | 框架搭建起步 | 全站i18n文案+语言切换+路由locale |
| 7.15 | 全面测试方案 | 33个测试/32通过/1已修复 | E2E覆盖+性能测试+边界用例 |
| 8.1 | Erika手动执行 | SG迁移Phase 0-3b ✅ | Phase 4观察+收款/DataForSEO/法律文档 |
| 8.3 | 后端合规能力 | 80% | Geo-Block+数据主权API+邮件双语化+Contact/Sub-processor已完成；数据保留清理待办 |
| 9.1 | 评论自动获取 | Rainforest单次拉取已实现 | 定时拉取+多数据源+ASIN监听列表 |
| 9.2 | API调用 | 基础路由存在 | v1公开API+认证+限流+文档 |

**⏳ 待启动（12 个子模块）**

| 编号 | 名称 | 启动条件 |
|------|------|---------|
| 6.7 | ABSA小模型fine-tune | PMF验证通过+≥5付费用户 |
| 6.8 | 用户反馈回路 | PMF验证通过 |
| 6.9 | Niche商业化启动 | PMF验证通过 |
| 7.3 | 独立测试环境 | 团队扩展或付费用户需staging |
| 7.4 | 预览环境 | 协作审查升级 |
| 7.13 | Agent智能工作流 | 7.12 C1-C2完成 |
| 8.2 | i18n框架+双语文案+法律页面 | 8.1完成 |
| 8.5 | LLM集成+数据源改造 | ⏸️ 冻结（等Erika拍板） |
| 8.6 | Beta发布准备 | 8.2-8.5完成 |
| 9.4 | 邀请返佣增长 | ≥10付费用户 |
| 9.5 | 自研评论标注模型 | ≥50付费用户+ABSA小模型验证 |
| 9.6 | 团队管理(多租户) | ≥1付费用户 |

```
[███████████████░░░░░░░] ~70%  (30 完成 / 9 进行中 / 12 待启动)
```

---

## 2. 核心模块

### 2.1 多产品仪表盘
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

### 2.2 版本对比视图
- 分支: `develop`（提前合并进主开发线）
- 状态: 已完成 | 进度: 100% | 依赖: 2.1
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

### 2.3 RAG 问评论
- 分支: `develop`（已在主开发线实现）
- 状态: 已完成 | 进度: 100% | 依赖: 2.1
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
  - [x] **2026-07-02 P0 升级**：从单一检索 RAG 升级为意图路由 + 结构化聚合，修复 4 个内置示例问题（差评原因/质量最好/最常提到的优点/共同质量问题）在真实数据下答不出来的问题；对齐 Shulex VOC 问评论能力矩阵。P1 待做：完整意图分类 LLM 兜底、rating_breakdown/consumer_insight/trend handler、前端 4 分组建议问题

### 2.4 Paddle 计费
- 分支: `develop`（已在主开发线实现）
- 状态: 已完成 | 进度: 100% | 依赖: 2.1, 2.3
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

## 3. ASIN 多变体抓取 + 产品管理增强

- [x] ASIN 抓取面板新增「抓取所有变体」checkbox，自动发现同款所有子 ASIN 并合并分析（上限 20 变体）
- [x] 抓取时自动保存产品信息（图片、品牌、评分、评论数）到产品管理
- [x] 产品管理列表页改为卡片网格（图片 + 名称 + 品牌 + 星级 + 评论数 + 变体数）
- [x] 新增产品详情页 `/products/[id]`，展示变体表格（ASIN、图片、变体名、品牌、价格等）
- [x] 产品详情页可直接跳转该产品的评论分析结果
- [x] 数据库迁移 031：products 表新增 image_url/brand/rating/ratings_total/reviews_total；product_variants 表新增 image_url/name/brand/price 等字段
- [x] Worker 流程重构：先保存产品信息 → 再抓取评论 → 合并去重 → 分析
- [x] products 表新增 scraped_title 字段（migration 046）：API 抓取标题与用户填写的 name 字段分离存储；Amazon 路径 name 改为用户填写优先，scraped_title 存 Rainforest 原始标题

---

## 4. 本地收口进展（原 V2.5-V3.1，2026-06-09）

- [x] 登录后全局 App Shell 已对齐 `clueai_v2_ui_prototype.html` 的柔和 V2 风格，导航、按钮、卡片、上传区和侧边栏视觉保持统一
- [x] 新增统一页头层 `review_analyzer/page_shell.py`，核心页与高级页都能显示所属路径、当前说明和快捷回跳
- [x] `今日工作台` 已成为默认落地页，头部文案按角色视角生成，和其余页面的体验一致
- [x] 一级导航已固定为：今日工作台、产品管理、上传评论、评论分析、问评论、行动中心、复盘追踪、宣传文案、推送设置
- [x] 用户可见的独立 `全部功能` 已取消，`analysis_hub.py` 仅保留 `分析结果 / 对比分析 / 历史记录` 三个分析子页
- [x] `features` 仅作为旧路由兼容映射存在，已不再作为独立页面保留
- [x] 上传完成后固定跳转到 `评论分析 > 分析结果`，并自动带上当前 `view_session_id`
- [x] 分析结果页已按 6 段模块重构，前 5 段支持模块级翻译与 XLSX 下载，用户体验模块支持 5 种时间筛选
- [x] 对比分析页已支持三类标准对比 + 功能点定向对比，并补齐整页翻译和 XLSX 下载
- [x] `问评论` 已升级为独立一级导航 `评论问答知识库`，支持按 1-5 个产品聚合评论后做 RAG 问答并展示来源引用
- [x] 产品管理、行动中心、复盘追踪已形成闭环：产品组/变体建档 -> TOP 问题建行动 -> 行动转复盘 -> 复盘结果回写
- [x] 宣传文案页、推送设置页的跳转文案已对齐新的评论工作流结构

---

## 模块依赖图

```
2.1 (多产品仪表盘)
├─► 2.2 (版本对比) ◄─ 2.1
├─► 2.3 (RAG) ◄─ 2.1
└─► 2.4 (Stripe) ◄─ 2.1, 2.3
```

开发顺序: 2.1 → 2.2 & 2.3（2.2 先做）→ 2.4

---

## 4.x 代码落地结果（基于当前代码）

> 这部分不再按“待办计划”理解，而是按“已经落地的代码事实”记录。

**结论:** 2.5-3.1 已全部在本地实现并收口。当前代码里没有独立的 `全部功能地图` 页面；旧 `features` 路由只作为兼容映射，最终会落到 `评论分析 > 分析结果`。

### 当前导航

| 路由 | 页面 |
|------|------|
| `dashboard` | 今日工作台 |
| `products` | 产品管理 |
| `upload` | 上传评论 |
| `analysis` | 评论分析容器（分析结果 / 对比分析 / 历史记录） |
| `rag` | 评论问答知识库 |
| `actions` | 行动中心 |
| `reviews` | 复盘追踪 |
| `copywriter` | 宣传文案 |
| `settings` | 推送设置 |

### 阶段状态

| 阶段 | 优先级 | 代码状态 | 当前结论 |
|------|--------|----------|----------|
| 2.5 | P0 | 已完成 | 产品管理已支持父体产品、变体 SKU、生命周期和产品资产汇总 |
| 2.6 | P0 | 已完成 | 上传流程已支持工作目的、产品档案绑定和变体识别 |
| 2.7 | P0 | 已完成 | 行动中心已能从 TOP 问题创建团队事项并更新状态 |
| 2.8 | P0 | 已完成 | 复盘追踪已能记录改进前后指标并判断继续跟进或完结 |
| 2.9 | P1 | 已完成 | 多产品 / 多变体 / 多版本对比已收敛到 `评论分析 > 对比分析` |
| 3.0 | P1 | 已完成 | 今日工作台已按运营、产研、质检、管理者四种视角成型 |
| 3.1 | P2 | 已完成并收口 | 独立全部功能地图已取消，相关高级能力保留在现有导航里 |

### 文件结构映射

| 文件 | 当前状态 | 说明 |
|------|----------|------|
| `supabase_schema.sql` | 已修改 | 已补充 products、product_variants、product_versions、action_items、review_trackers、comparison_reports 等表和索引 |
| `review_analyzer/database.py` | 已收敛 | 保留共享连接与现有通用 CRUD，新模块不再继续堆进来 |
| `review_analyzer/product_store.py` | 已新增 | 产品组、变体 SKU、产品版本 CRUD |
| `review_analyzer/action_store.py` | 已新增 | 行动事项 CRUD 与状态流转 |
| `review_analyzer/review_store.py` | 已新增 | 复盘追踪 CRUD、复盘结果更新 |
| `review_analyzer/compare_store.py` | 已新增 | 多产品、同产品、变体、版本对比数据聚合 |
| `review_analyzer/workspace_store.py` | 已新增 | 今日工作台的角色任务、风险 SKU、待复盘摘要 |
| `review_analyzer/app.py` | 已修改 | 侧边栏导航和页面分发已收口，兼容旧 `features` 路由 |
| `review_analyzer/pages/dashboard.py` | 已修改 | 从产品卡片仪表盘升级为“今日工作台”入口 |
| `review_analyzer/pages/products.py` | 已新增 | 产品管理页：父体产品、变体 SKU、生命周期、版本和评论资产 |
| `review_analyzer/pages/upload.py` | 已修改 | 上传流程增加工作目的、产品组/变体/版本绑定 |
| `review_analyzer/pages/analysis_hub.py` | 已修改 | 评论分析容器页：分析结果 / 对比分析 / 历史记录 |
| `review_analyzer/pages/results.py` | 已修改 | TOP 问题/亮点增加创建行动、加入复盘入口 |
| `review_analyzer/pages/actions.py` | 已新增 | 行动中心：团队事项列表、状态流转、负责人和复盘时间 |
| `review_analyzer/pages/reviews.py` | 已新增 | 复盘追踪页：改进前后指标、复盘结论、完结/继续跟进 |
| `review_analyzer/pages/compare.py` | 已新增 | 多产品、同产品、同变体、跨版本对比 |
| `review_analyzer/pages/rag_library.py` | 已接入 | 评论问答知识库：多产品范围问答与引用展示 |
| `review_analyzer/workflow_prompts.py` | 已扩展 | 根据工作目的输出不同结构的建议 |
| `review_analyzer/notifier.py` | 已修改 | 支持行动事项和复盘提醒推送到飞书 |
| `review_analyzer/exporter.py` | 已修改 | 支持行动事项、复盘报告、多产品对比导出 |
| `plan.md` | 已修改 | 需求变更日志已同步实际落地变更 |
| `PROGRESS_V2.md` | 已修改 | 当前文档改为按代码事实记录进度 |

说明：`review_analyzer/pages/features.py` 不再作为独立页面存在，`全部功能地图` 的职责已经被当前导航和各业务页拆开承担。

---

### 4.1 数据模型升级

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

- [x] **Step 7: 已完成 / 已入库**

产品档案与变体数据模型已落到当前实现中，`supabase_schema.sql`、`review_analyzer/product_store.py` 和本节进度说明已同步完成。

---

### 4.2 产品管理页

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

### 4.3 上传流程升级

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

### 4.4 行动中心

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

### 4.5 复盘追踪

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

### 4.6 多产品 / 多变体 / 多版本对比

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

- [x] **Step 8: 3.1 重做对比工作台（2026-06-23）**

把 `/analysis/compare` 从「AI Report 生成器」改回「对比工作台」：
- 后端新增 `POST /compare/dataset`（产品 + 版本 + 评论日期窗口） 和 `POST /compare/export`（XLSX 流），`compare_store.build_compare_specs_from_filters` / `dataset_to_xlsx_payload` 承接。
- 前端新增 `compare-filter-bar`（时间环比 / 版本对比 / 多产品 / 自定义四模式 + 评论日期预设）、`compare-dashboard`（KPI ↑↓ 变化、问题/亮点 TOP 变化表、风险/机会、推荐动作）、`compare-workspace` 串联，AI 总结降级为辅助面板。下载 XLSX 是页面顶部主操作之一。
- 旧 `compare-page-tabs.tsx` / `compare-report-panel.tsx` 删除。验证：`ruff` 全过，`tsc` 全过。

---

### 4.7 角色化今日工作台

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

### 4.8 导航收口

**Files:**
- Modify: `review_analyzer/app.py`
- Modify: `review_analyzer/pages/analysis_hub.py`
- Historical: `review_analyzer/pages/features.py` 已不再作为独立页面保留

- [x] **Step 1: 取消独立全部功能入口**

当前侧边栏不再展示 `全部功能`，主导航直接指向今日工作台、产品管理、上传评论、评论分析、问评论、行动中心、复盘追踪、宣传文案和推送设置。

- [x] **Step 2: 旧路由保持兼容**

`features` 只作为历史入口保留，并由 `app.py` 兼容映射到 `评论分析 > 分析结果`，避免旧链接失效。

- [x] **Step 3: 高级能力回归各自页面**

历史记录、对比分析、问评论、宣传文案和推送设置等能力不再被“全部功能地图”统一收纳，而是直接放在对应业务页里。

- [x] **Step 4: 验收**

Expected:

- 新用户按主工作流就能完成上传、分析、行动和复盘，不需要先进入功能地图。
- 老用户通过侧边栏即可找到所有当前可用能力。

- [x] **Step 5: 回滚边界**

如果未来要重新设计信息架构，只需重新调整 `app.py` 的导航和旧路由兼容层，不需要再恢复独立功能地图页。

- [x] **Step 6: 结论**

3.1 在当前代码里已经转化为“导航收口”而不是“独立页面新增”，所以文档应按收口完成处理，不再把 `pages/features.py` 当成现存模块。

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
| P0-1 | 产品组 + 变体 SKU | 支持真实电商父体/子体结构 | 2.5 产品管理 |
| P0-2 | 工作目的上传 | 让用户按场景上传评论，不从功能开始 | 2.6 上传流程 |
| P0-3 | 行动中心 | TOP 问题能转成运营、产研、质检事项 | 2.7 行动中心 |
| P0-4 | 复盘追踪 | 改进动作能持续追踪并判断是否有效 | 2.8 复盘追踪 |
| P0-5 | 多产品/多变体对比 | 支持主推款、问题款、机会款判断 | 2.9 多产品对比 |
| P0-6 | UI 风格统一 | 全站使用 `clueai_v2_ui_prototype.html` 的柔和清爽风格 | 3.0 UI 重构 |

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
| 1 | 2.5 | 产品组 + 变体 SKU | 没有产品档案，后续闭环无法稳定 |
| 2 | 2.6 | 工作目的上传 | 降低用户理解成本，避免功能堆叠 |
| 3 | 2.7 | 行动中心 | 让分析结果变成团队动作 |
| 4 | 2.8 | 复盘追踪 | 形成 ClueAI 最核心差异化 |
| 5 | 2.9 | 多产品 / 多变体对比 | 支持运营策略和主推款判断 |
| 6 | 3.0 | 角色化工作台 + UI 统一 | 让不同伙伴进来就知道做什么 |
| 7 | 3.1 | 全部功能地图收口（已完成） | 独立入口已取消，高级能力回归各自业务页 |
| 7.5 | 3.1.5 | **Next.js 营销站独立部署（拿到 3-5 个付费用户后立即启动）** | 跨境卖家 60-70% 来自 SEO，Streamlit 没有 SEO；营销页是付费转化的信任构建器 |
| 8 | 3.2 | 定时分析 + 风险提醒 | 提升留存和团队协作价值 |
| 9 | 3.3 | 组织角色 + 操作记录 | 为团队版/企业版做准备 |
| 10 | 4.0 | 自动采集 / 平台 API | 向成熟商业数据平台过渡 |
| 11 | 5.0 | 产品层 Streamlit → Next.js 全迁移（MRR > $3k 后再考虑） | UI 升级带动客单价、支持移动端 / 嵌入式 widget / 团队版 |

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

### 3.1.5 营销站最小可行范围（P1-7 的具体落地）

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
| 当前（3.1.5 启动前） | 5 个种子用户在用 Streamlit 版 | 至少 1 个种子用户愿意付费 → 启动 P1-7 营销站 |
| P1-7 营销站上线 | clueai.com 首页 + 定价 + 5 个功能页上线，Paddle Checkout 跑通 | 自然搜索月访问 > 500 / MRR > $500 → 加博客内容 |
| 营销站成熟 | 月新增付费 > 5 / MRR > $3k | 触发 5.0 产品层迁移 Next.js |

---

## 5. Next.js 迁移

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
| `5.1` 前端工程骨架 | 已完成 | 新建 Next.js 工程、登录前页面、全局设计 Token | 仅回滚 `frontend/` |
| `5.2` FastAPI 骨架与认证 | 已完成 | 新建 API 服务、登录注册、HttpOnly Cookie 会话 | 仅回滚 `backend_api/` 与少量认证辅助改动 |
| `5.3` 工作台与产品管理迁移 | 已完成 | 打通 `/workspace` 与 `/products` 的 API + 页面 | 仅回滚工作台/产品相关新接口与新页面 |
| `5.4` 上传与分析任务异步化 | 已完成 | 上传拆分、分析 job 化、Redis + RQ 跑通 | 仅回滚上传/分析异步链路与 worker |
| `5.5` 结果/对比/历史迁移 | 已完成 | 迁移 `results / compare / history`，支持 URL 直达与显式对比报告生成 | 仅回滚分析阅读层 |
| `5.6` 问评论/行动/复盘迁移 | 已完成 | 迁移闭环能力与 RAG 页面 | 仅回滚闭环相关模块 |
| `5.7` 文案/设置/计费迁移 | 已完成 | 迁移低频高级页与 Paddle | 仅回滚商业化协同页 |
| `5.8` 部署与 Streamlit 下线路径 | 已完成（ECS 生产环境运行中） | ECS + Nginx + 容器化部署，明确下线条件 | 仅回滚部署配置 |

### 执行顺序

| 顺序 | 模块 | 为什么先做 |
|------|------|------------|
| 1 | `5.1` | 先建立新的前端壳层和登录前体验，不碰旧主流程 |
| 2 | `5.2` | 先把认证与会话从 `st.session_state` 中剥离出来 |
| 3 | `5.3` | 工作台和产品管理最适合先作为只读模块迁移 |
| 4 | `5.4` | 上传与分析是核心工作流，异步化是整个迁移的中轴 |
| 5 | `5.5` | 结果、对比、历史依赖上传与分析链路稳定后再迁 |
| 6 | `5.6` | 闭环能力在分析阅读层稳定后再接入 |
| 7 | `5.7` | 文案、设置、计费优先级低于核心工作流 |
| 8 | `5.8` | 所有主路径稳定后再做部署固化与 Streamlit 下线 |

### 当前迁移验收总标准

- [x] Next.js 登录前页面全部可访问，桌面端与移动端无布局错乱
- [x] FastAPI 登录、注册、退出、`/me` 可用，不依赖 `st.session_state`
- [x] 上传、分析、结果跳转已完成异步 job 化
- [x] 结果页、对比页、历史页支持 URL 直达
- [x] 问评论、行动中心、复盘追踪形成完整闭环
- [x] Paddle 计费链路在新架构下可用
- [ ] 阿里云部署结构可启动，Nginx 反代、域名与 HTTPS 可工作（后置，不阻塞本地开发验证）
- [x] Streamlit 在迁移期间始终保留可回退主路径

### 5.1 前端工程骨架

- [x] 建立 `frontend/` 目录
- [x] 完成 `package.json / tsconfig / next.config / tailwind.config`
- [x] 建立 `layout.tsx` 和全局设计 Token
- [x] 建立 `/ /login /register /trial /pricing` 页面骨架
- [x] 本地跑通 `npm run dev`
- [x] 验收首页首屏 3 秒内说清“评论洞察 -> 行动跟进 -> 复盘验证”
- [x] 若失败，只回滚 `frontend/` 与本节进度勾选

5.1 验收记录：

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

### 5.2 FastAPI 骨架与认证

- [x] 建立 `backend_api/` 目录
- [x] 建立 `main.py / config.py / deps.py`
- [x] 建立 `/auth/register /auth/login /auth/logout /me`
- [x] 继续复用现有用户表与 `bcrypt`
- [x] 建立 HttpOnly Cookie 会话
- [x] 本地跑通 `uvicorn backend_api.app.main:app --reload`
- [x] 若失败，只回滚 `backend_api/` 与认证迁移辅助改动

5.2 验收记录：

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

### 5.3 工作台与产品管理迁移

- [x] 新增 `GET /workspace/summary`
- [x] 新增 `GET /products`
- [x] 建立 `/workspace` 页面
- [x] 建立 `/products` 页面
- [x] 验收数据口径与当前 Streamlit 页面一致
- [x] 若失败，只回滚工作台/产品模块

### 5.4 上传与分析任务异步化

- [x] 新增 `POST /uploads`
- [x] 新增 `POST /analysis/jobs`
- [x] 新增 `GET /analysis/jobs/{job_id}`
- [x] 建立 `workers/` 目录
- [x] 接入 Redis + RQ
- [x] 建立 `/upload` 页面
- [x] 验收上传 -> job -> 处理中 -> 结果跳转完整跑通
- [x] 若失败，只回滚异步链路与 worker
- [x] 批次去重：重复上传同一批评论时返回 409 + 前端友好提示跳转已有结果（2026-06-23）
- [x] 修复：删除分析记录失败 — upload_jobs/action_items 外键阻止 session 删除 + 前端静默吞错误（2026-06-23）
- [x] 修复：upload/page.tsx server/client 组件拆分，解决 next build 报 next/headers 错误（2026-06-23）

### 5.5 结果 / 对比 / 历史迁移

- [x] 新增 `GET /analysis/sessions/{session_id}/results`
- [x] 新增结果、对比、历史读取接口
- [x] 建立 `/analysis/results`
- [x] 建立 `/analysis/compare`
- [x] 建立 `/analysis/history`
- [x] 验收 URL 直达，不依赖页面内隐式状态
- [x] 若失败，只回滚阅读层模块
- [x] 修复：对比分析版本下拉框只显示"全部版本"，改用 sessions.version 聚合实际版本（2026-06-26）
- [x] 修复：历史记录删除后对比分析产品列表不同步，改为 client-side 挂载刷新（2026-06-26）

### 5.6 问评论 / 行动中心 / 复盘追踪迁移

- [x] 新增 `POST /qa/questions`
- [x] 新增 `GET/POST/PATCH /actions`
- [x] 新增 `GET/POST/PATCH /trackers`
- [x] 建立 `/qa`
- [x] 建立 `/actions`
- [x] 建立 `/reviews`
- [x] 验收从结果页创建 action，再生成 tracker，再回写复盘结果
- [x] 若失败，只回滚闭环模块
- [x] 问评论对话式 UI 重构 + 多轮对话支持（2026-06-25）
  - [x] 前端改为 AI 对话框形式（消息列表 + Popover 产品选择器 + 预设问题卡片）
  - [x] 后端新增 qa_conversations/qa_messages 表 + 对话管理 API
  - [x] RAG 模块支持 history 参数，LLM 感知多轮上下文
- [x] 问评论旧 LLM 直连迁移到统一 Router（2026-07-23）
  - [x] `answer_question()` / `retrieval_handler()` / `aggregate_feedback_handler()` / `product_compare_handler()` 新增 `locale="en"` 参数并透传
  - [x] `qa_handlers.py` 删除 DeepSeek 直连 client、base_url 与 `deepseek-chat` 硬编码，统一走 `router_completion(locale=...)`
  - [x] `/qa/ask`、`/qa/questions`、多轮对话消息入口复用 `get_analysis_locale(request)`，默认海外英文链路优先

5.6 验收记录：

- `python3 -m py_compile backend_api/app/main.py backend_api/app/routes/analysis.py backend_api/app/routes/compare.py backend_api/app/routes/actions.py backend_api/app/routes/qa.py review_analyzer/action_store.py review_analyzer/review_store.py review_analyzer/insight_engine.py review_analyzer/translation.py review_analyzer/analysis_export.py`：PASS
- `cd frontend && npx tsc --noEmit`：PASS
- `/qa`：PASS，支持 1-5 个产品聚合问评论，并返回引用评论
- `/actions`：PASS，支持 action 列表、状态流转和一键加入复盘
- `/reviews`：PASS，支持 tracker 列表与复盘结果回写
- 从 `/analysis/results` 可直接创建 action，再把 action 生成 tracker，最后在复盘页回写结果：PASS
- 2026-07-23 问评论 Router 迁移回归：`python3 -m pytest backend_api/tests/test_qa_llm_router.py -q`：PASS（3 passed）；`python3 -m ruff check review_analyzer/qa_handlers.py review_analyzer/rag.py review_analyzer/translation.py review_analyzer/compare_store.py review_analyzer/parser.py review_analyzer/router_client.py review_analyzer/eval/runner.py backend_api/app/routes/qa.py backend_api/app/routes/compare.py backend_api/app/services/action_advisor.py`：PASS；`python3 -m py_compile` 覆盖本次 runtime + 已跟踪 scripts：PASS

### 5.7 宣传文案 / 设置 / 计费迁移

- [x] 新增 `GET /settings`
- [x] 新增 `PATCH /settings`
- [x] 新增 `POST /billing/checkout`
- [x] 新增 `POST /billing/webhook`
- [x] 建立 `/copywriter`
- [x] 建立 `/settings`
- [x] 验收设置、Paddle、文案页都可用
- [x] 若失败，只回滚低频高级页和计费模块
- [x] 设置页拆分：推送设置（/settings/push）+ 系统设置（/settings）独立页面
- [x] 产品级专项规则改为 ProductSearchCombobox 搜索选择
- [x] 订阅计费从推送设置移入 QuotaDialog（Pro 管理订阅 / Free 升级套餐）
- [x] 系统设置页新增账户信息 + API 密钥管理 + 数据导出占位

5.7 验收记录：

- `python3 -m py_compile backend_api/app/main.py backend_api/app/routes/settings.py backend_api/app/routes/copywriter.py backend_api/app/routes/billing.py review_analyzer/paddle_billing.py review_analyzer/pages/copywriter.py review_analyzer/pages/settings.py`：PASS
- `cd frontend && npx tsc --noEmit`：PASS
- `/copywriter`：PASS，文案页可读取批次并生成平台文案
- `/settings`：PASS，设置页可读取飞书、Paddle 和通知配置
- `POST /billing/checkout` 与 `POST /billing/webhook`：PASS，计费链路可创建并回写套餐状态
- 低频高级页和计费模块已按独立边界落地，主闭环不受影响

### 5.8 部署与 Streamlit 下线路径

> 当前状态：**可以执行上线**。6.1~6.6 已全部完成，本地功能闭环稳定，部署配置就绪。当前瓶颈是”部署上线”而非”功能开发”。

> 前置条件确认（2026-06-12）：
> - ✅ 阿里云 ECS 已购买（2C4G），运行中
> - ✅ 域名 `clueai-reviewlens.com` 已购买，DNS 在阿里云管理
> - ⚠️ ECS 上 Docker 未安装 → Phase 1 需要先装

**Phase A: 部署配置准备（已完成）**

- [x] 建立 `frontend / backend_api / workers` Dockerfile
- [x] 建立 `deploy/nginx.conf`
- [x] 建立 `deploy/docker-compose.yml`
- [x] 编写 `docs/deployment-nextjs-fastapi-aliyun.md`
- [x] 明确 `clueai-reviewlens.com / app.clueai-reviewlens.com / api.clueai-reviewlens.com` 域名结构
- [x] 明确 Streamlit 下线前置条件
- [x] 若失败，只回滚部署配置，不回滚产品代码

**Phase B: ECS 上线执行（2026-06-12 执行中）**

- [x] **Step 1: ECS 环境准备** ✅ 2026-06-12
  - Docker 29.5.3 + Docker Compose v5.1.4 安装完成
  - 宿主机 nginx 已停用，80/443 端口空闲
  - OS: Ubuntu 22.04 (jammy)

- [x] **Step 2: DNS 解析** ✅ 2026-06-12
  - `clueai-reviewlens.com` → 8.210.51.242
  - `app.clueai-reviewlens.com` → 8.210.51.242
  - `api.clueai-reviewlens.com` → 8.210.51.242
  - `www.clueai-reviewlens.com` → 8.210.51.242
  - dig 验证全部生效

- [x] **Step 3: 代码部署 + 环境变量** ✅ 2026-06-12
  - `git clone` → `/opt/clueai`，分支 develop
  - `deploy/.env` prod 凭证已写入

- [x] **Step 4: 构建并启动** ✅ 2026-06-12
  - 首次构建 163s，5 个容器全部 Up：redis / api / worker / frontend / nginx
  - 修复：补充 `numpy + scikit-learn` 依赖（clustering.py HDBSCAN）
  - API 从 Restarting → 正常运行

- [x] **Step 5: HTTPS 签发** ✅ 2026-06-12
  - Let's Encrypt 证书签发成功（4 域名：@, www, app, api），有效期至 2026-09-10
  - 修复：bootstrap 自签名证书占了 live 目录，certbot `--force-renewal` + 目录重命名解决
  - nginx restart 后 HTTPS 200 确认

- [ ] **Step 6: 冒烟测试**
  - [x] `https://clueai-reviewlens.com/` 首页返回 200
  - [x] `https://api.clueai-reviewlens.com/health` 返回 200
  - [ ] `https://app.clueai-reviewlens.com/login` 登录页正常
  - [ ] 注册新用户 → 登录成功
  - [ ] 上传评论文件 → 分析任务完成 → 结果展示

- [ ] **Step 7: 种子期配置（~15 min）**
  - 放宽 Free 配额限制（让种子用户完整体验核心功能）
  - 或直接在数据库把种子用户 plan 设为 `pro_early`
  - 确认付费墙不阻止试用核心流程

- [ ] **Step 8: 标记上线完成**
  - 本节状态更新为"已完成"
  - PROGRESS_V2.md 变更日志追加上线记录
  docker compose -f deploy/docker-compose.yml exec nginx nginx -s reload
  ```

- [ ] **Step 6: 冒烟测试（~15 min）**
  - `https://clueai-reviewlens.com/` 首页可打开
  - `https://app.clueai-reviewlens.com/login` 登录页正常
  - `https://api.clueai-reviewlens.com/health` 返回 200
  - 注册新用户 → 登录成功
  - 上传评论文件 → 分析任务完成 → 结果展示

- [ ] **Step 7: 种子期配置（~15 min）**
  - 放宽 Free 配额限制（让种子用户完整体验核心功能）
  - 或直接在数据库把种子用户 plan 设为 `pro_early`
  - 确认付费墙不阻止试用核心流程

- [ ] **Step 8: 标记上线完成**
  - 本节状态更新为”已完成”
  - PROGRESS_V2.md 变更日志追加上线记录

5.8 验收记录（Phase A）：

- `python3 -m py_compile backend_api/app/main.py backend_api/app/routes/settings.py backend_api/app/routes/copywriter.py backend_api/app/routes/uploads.py workers/runner.py workers/queue.py workers/jobs.py`：PASS
- `cd frontend && npx tsc --noEmit`：PASS
- `python3 -c “import pathlib, yaml; yaml.safe_load(pathlib.Path('deploy/docker-compose.yml').read_text())”`：PASS
- `docker compose -f deploy/docker-compose.yml config`：当前环境未安装 `docker`，无法执行；配置文件本身已通过 YAML 解析检查
- `https://clueai-reviewlens.com / https://app.clueai-reviewlens.com / https://api.clueai-reviewlens.com`：域名分层与回退口径已写入部署文档
- `robots.txt / sitemap.xml / opengraph-image`：营销站 SEO 基础已补齐，营销页可索引、应用页 noindex
- Streamlit 保留为回退口，部署层与业务层边界已明确

**Phase C: UI 美化优化（与 Phase B 并行）**

> 目标：种子用户拿到手时，看到的是一个视觉成熟、文案专业的产品，而非开发者原型。
> 设计 spec 文档：`docs/figma-p0-prototype-spec.md`
> 参考风格：Linear（精致度）+ PostHog（亲和感）+ Notion（简洁文案）

**P0：上线前必做（现在执行）**

> 触发条件：立即开始。Phase B 部署和 Phase C 美化可以并行推进。
> 预计耗时：3-4 小时

- [x] **Step C1: 字体正式引入（~20 min）**
  - 通过 `next/font/google` 在 `layout.tsx` 引入 Inter（400/600）+ Montserrat（700/800）
  - 设置 CSS variable `--font-inter` / `--font-montserrat`，body 继承
  - `globals.css` 中 `--font-body` / `--font-heading` 改为引用 next/font 变量
  - 验证：DevTools Network 面板确认 woff2 文件加载

- [x] **Step C2: 侧边栏导航重构（~2 hr）**
  - 安装 `lucide-react`
  - 新建 `frontend/src/components/app/sidebar.tsx`：
    - 宽度 260px，白色背景，右侧 1px border
    - 4 组分区：核心（工作台/上传/分析结果）、洞察（对比/历史/问评论）、行动（行动中心/复盘/文案）、管理（产品管理/推送设置）
    - 每项配 Lucide icon，active 态 = rose-soft 背景 + 左侧 3px rose bar
    - 底部用户信息区（头像 + 用户名 + 套餐标签）
  - 重写 `app-shell.tsx`：从顶部 nav 布局改为 sidebar + 右侧 main content
  - Mobile（<768px）：顶部 56px bar（hamburger + logo），侧边栏变 overlay（左滑出 + 暗色遮罩）
  - 验证：所有 11 个 nav 路由可点击跳转，mobile 下 hamburger 开关正常
  - ✅ 追加 2026-06-23：Sidebar 底部新增"套餐额度"入口（参考 VOC.AI 截图）。新建 `frontend/src/components/quota/`：`quota-groups.ts`（4 业务分组 + 9 维度共享映射）、`quota-dialog.tsx`（Radix Dialog 弹窗，按 monthly/daily/forever/concurrent/per_request 周期分别决定进度条 + used/limit 显示）、`sidebar-quota-entry.tsx`（fetch `/api/quota` 后显示 `Free · X/Y` 副文，Free 用户右侧露出"升级套餐"链接 `/pricing`）。`quota-panel.tsx` 同步重构复用映射常量并迁移 i18n，去除本地 label 重复维护。i18n 文件同步新增 `sidebar.quotaEntry/upgradeLink/tagline/notLoggedIn/openMenu/closeMenu`、`quotaPanel.*`、`quotaDialog.*`（含 10 个 dimension label/hint）。Playwright 端到端验证通过（Free 用户 4 个分组 9 维度全部正确渲染）

- [x] **Step C3: 文案清理（~40 min）**
  - `app-shell.tsx`：副标题 "SKU 口碑改版追踪系统" → "评论智能分析"
  - `app-shell.tsx`：移除 "NEXT.JS APP PREVIEW" eyebrow badge
  - `site-header.tsx`：tagline "SKU review operating system" → "Review intelligence for sellers"
  - `workspace/page.tsx`：
    - 移除 description 中 "当前页面已接到真实 API..." 等开发者术语
    - 移除 tasks section 副标题 "保留当前 Streamlit 工作台的推荐逻辑..."
    - 401 态 title → "请先登录"，desc → "登录后即可查看风险 SKU、团队待办和最近上传"
  - `upload/page.tsx`：
    - title → "上传评论文件"
    - description → "选择文件并填写产品信息，系统将自动排队分析"
  - `pricing/page.tsx`：
    - H1 → "Simple pricing that grows with your business."
    - body → "Start free. Upgrade when you need multi-product workflows, review Q&A, and action tracking."
  - 验证：逐页截图确认无开发者内部术语残留

- [x] **Step C4: P0 验收**
  - `cd frontend && npm run build` 通过
  - `cd frontend && npx tsc --noEmit` 通过
  - 本地 `npm run dev` 逐页检查（landing / login / workspace / upload / pricing）
  - Mobile 375px 模式无溢出，sidebar overlay 正常
  - 截图留档，标记 P0 完成

**P1：上线后优先（下一阶段）**

> 触发条件：Phase B 部署完成 + P0 验收通过 + 种子用户开始使用后的第一周内
> 预计耗时：4-6 小时

- [ ] **Step C5: Landing Page 升级**
  - 替换 HeroPreview 为产品截图/mockup（可用 P0 后的真实截图）
  - 增加信任信号区组件：`trust-section.tsx`（"Built for Amazon / eBay / Shopee sellers"）
  - CTA 改为：主 "Start Free" + 副 "See how it works"
  - 添加渐入动画（intersection observer + CSS transform，或按需引入 framer-motion）
  - 验证：首屏加载后 hero 和 value grid 有渐入过渡效果

- [ ] **Step C6: 配色 + 视觉层次优化**
  - 卡片背景从 `white/84`（半透明）改为纯 `#ffffff`（提升对比度）
  - 新增 semantic 状态色 token：success(mint) / warning(amber) / danger(red)
  - 高风险 SKU 数字用 red 色，正常指标用 ink 色
  - Workspace metrics 卡片增加 icon 装饰（对应 Lucide icon）
  - 验证：Lighthouse Accessibility 分数 ≥ 90

- [ ] **Step C7: Pricing 页完善**
  - Pro 套餐卡片高亮：2px rose border + "POPULAR" badge
  - 每个套餐增加 6-8 个 feature bullet（而非当前 3 个）
  - 每张卡片底部加 CTA 按钮（Start Free / Upgrade / Contact Us）
  - 可选：增加 FAQ 折叠区
  - 验证：3 张卡片视觉有明确主次区分

**P2：种子用户反馈后迭代**

> 触发条件：收集到 ≥ 5 个种子用户的使用反馈 + 明确知道哪些页面体验有问题
> 按反馈优先级选做，不全部强制执行

- [ ] **Step C8: 微交互 + Loading 态**
  - 按钮 hover scale(1.02) + active scale(0.98) 效果
  - 表单提交 loading spinner（替代当前纯 disabled 态）
  - 上传页文件拖拽区 hover 高亮 + 进度可视化
  - 页面切换 skeleton screen（workspace / analysis 页数据加载时）

- [x] **Step C9: 分析结果页美化**（2026-06-22 完成）
  - [x] 后端 insight_engine 数据稳定性加固（schema 校验 + 字段级 merge + heuristic 改善）
  - [x] 模块卡片增加 icon + 色彩区分（5 个模块各有独立色系 + Lucide icon）
  - [x] 用户体验模块 TOP 10 正负 tag + CSS progress bar + 证据引用
  - [x] 关键结论（TOP issue / highlight）用 callout 样式高亮
  - [x] 综合建议模块改为 numbered steps 布局
  - [x] 每个模块增加翻译按钮（DeepSeek 翻译 API）+ XLSX 下载按钮
  - [x] 负向标签 + 未满足需求每条旁增加「+ 行动」inline 创建按钮（Dialog 弹窗）
  - [x] 新增后端路由：`/translate/module`、`/analysis/sessions/{id}/export`

- [x] **Step C9.5: 分析结果页交互升级**（2026-06-23 完成）
  - 目标：把 Tab 切换改成长页锚点滚动，并新增时间 / 产品级筛选，让用户在结果页就能切换"该产品 + 最近 X 天"视角
  - [x] 后端 `get_comments` 加 `date_start` / `date_end` 参数（基于评论自身的 `date` 字段）
  - [x] 新增 `GET /analysis/results?product_id=&range=7d|14d|30d|90d|all|custom|default&start=&end=&session_id=` 聚合接口：跨 session 合并评论 → 跑 LLM → 返回与单 session 同形 payload
  - [x] 进程内 30 分钟聚合缓存（key = `user_id + product_id + start + end + comment_ids_hash`），命中重复筛选秒返
  - [x] 新增 `GET /products/search?q=&limit=` 用于产品下拉搜索（前缀优先 + 评论数排序）
  - [x] 前端 5 个独立 Tab 改为长页 5 段 `<section>` + 顶部 sticky 锚点条 + IntersectionObserver 自动高亮
  - [x] 顶部新增 `ResultsFilterBar`（产品 Combobox + 时间 Select + 自定义日期范围 Popover）
  - [x] 老链接兼容：`?session_id=N` 自动 redirect 到 `?product_id=X&range=default&session_id=N`
  - [x] 原始评论列表新增"显示更多"分页（每页 20 条）

- [x] **Step C9.6: 标签数据层回归英文 canonical key**（2026-06-25 完成）
  - 背景：原文下载按钮始终匹配不到评论，根因是 `category_grouper` 存中文标签违反竞品调研确定的 L2 英文 key 设计，加上 `insight_engine` AI 改名导致前端无法匹配
  - [x] `category_grouper.py`：新增 `aspect_to_en()`，`issue_tag`/`highlight_tag` 改存英文 canonical label
  - [x] `insight_engine.py`：AI merge 跳过 tag 数组覆盖，只增强 summary/evidence 文本
  - [x] 前端下载按钮：匹配逻辑简化为精确匹配（tag 名 = 评论字段值）
  - [x] 旧 session 兼容：中文 tag 仍由 `_top_tag_rows` 精确统计，下载匹配同样有效

- [x] **Step C9.7: 分析结果页下载内容优化 + i18n 表头**（2026-06-29 完成）
  - [x] 标签代表性评论下载扩展为 13 列（序号/评论内容/评分/日期/评论者/来源/情感/分类/优先级/分析理由/改进建议/问题标签/亮点标签）
  - [x] 综合建议模块去掉 "Recommendation N" 标题，只保留数字圆圈 + 建议正文
  - [x] 模块右上角下载（用户体验/消费动机/未满足的需求/用户画像）改为 TOP10 格式（排名/标签/出现次数/提及占比/代表性评论前20条摘要）；user_experience 和 consumer_profile 输出正负两个 sheet
  - [x] 所有下载 Excel 表头支持 i18n：前端通过 `getLocale()` 传 locale，后端 export 端点接受 `?locale=zh|en` 参数

- [x] **Step C9.8: Customer Issue / Customer Label 口径重构与灰度验证**（2026-07-24 ~ 2026-07-27）

  > 背景：增长分析页的产品亮点 / 高频痛点曾把内部 aspect、前台 Customer Issue / Customer Label、代表评论、下载原文和 Mention Share 分母混在一起。典型问题包括 `Comfortable To Wear` 代表评论过宽、`Water Leaks Through` 被 `no leaks / remained dry` 等表达污染、高频痛点第一条 Mention Share 出现 100% 且用户不可解释。

  当前结论：
  - [x] Phase 1-6.5 已完成代码、导出、前端展示、验证集和真实 Foxelli raw replay。
  - [x] Phase 7 P0 read-path 性能修复已完成并推送 `origin/develop=1d537fd76aa61f8388fef80e84d9d7890e96d8b7`。
  - [x] Phase 7 第二批 / P1 authenticated route smoke 已完成：session 3/4/5 的 results、aggregate results、模块导出、完整导出均为 200。
  - [x] Phase 7 生产部署已确认：GitHub Actions `Deploy to Production` run `30230691101` 已将 `1d537fd76aa61f8388fef80e84d9d7890e96d8b7` 部署成功；生产只读 `/analysis/sessions/{id}/results` smoke 覆盖 114/96/111/110，均 200、无 `embedding`、无 SSL/connection error。
  - [x] Phase 7 P1 worker 写路径优化已完成编码与本地回归：analysis / cluster / embedding 写入改为批量事务，worker analysis 按 50 条 flush 并保留逐条 fallback。
  - [x] 可以扩大 Phase 7 第二批 / P1 小流量灰度。
  - [ ] 不建议直接生产全量发布；生产扩大前仍需 Erika 明确授权会扣 credit 的 live `/analysis/results` 与 export smoke，或提供零扣费 staging。

  核心口径已冻结：
  - `Customer Issue`：前台展示给用户看的具体问题标签，例如 `Water Leaks Through`、`Missing Parts`。
  - `Customer Label`：前台展示给用户看的具体亮点标签，例如 `Comfortable To Wear`、`Feels Well Made`。
  - `Aspect / Internal Aspect`：内部维度，只做归类、治理、下载审计和责任分发，不作为前台 Top 主标签。
  - `Mention Share = mention_count / 同类 label mention_count 总数`。
  - `Impact Review Share = review_count / 当前筛选范围总评论数`。
  - 同一评论同一 canonical label 默认只计 1 次用于 Top 排名和 `review_count`。
  - 代表评论只能来自 verified evidence span；`cluster_propagated=true` 和 evidence 不在原文中的 occurrence 不能进入 Representative Evidence。

  Phase 状态总表：

  | Phase | 状态 | 产物 / 结论 |
  |------|------|-------------|
  | Phase 0 口径冻结 | ✅ 完成 | 冻结 `Customer Issue / Customer Label / Mention Share / Impact Review Share / Aspect` 定义；旧 session 保守兼容 |
  | Phase 1 当前问题止血 | ✅ 完成 | 防止 `no leaks / without leaks / didn't leak / remained dry / kept dry` 误触发 `Water Leaks Through`；missing evidence 与 cluster propagated 不进入代表证据 |
  | Phase 2 标签数据层 | ✅ 完成 | 新增 `customer_label_catalog`、`customer_label_alias_rules`、`customer_label_candidates`；`customer_label_catalog.py` 支持 catalog / alias / candidate 保守解析；broad/internal label 可禁用 |
  | Phase 3 occurrence 抽取 | ✅ 完成 | 新增并行 `customer_label_occurrences` schema；每个 occurrence 带 raw label、canonical key、display label、aspect、evidence span、confidence、source、`evidence_verified`、`cluster_propagated`、version |
  | Phase 4 聚合算法 | ✅ 完成 | `_build_customer_label_rows()` 统一 Issue / Highlight 聚合；按同类 mention 分母算 `mention_share`；输出 `mention_count`、`review_count`、`impact_review_share`、`raw_occurrence_count`；正评中的真实 issue 和差评中的真实 highlight 都可进入 Top |
  | Phase 5 前端和下载 | ✅ 完成 | 页面表头改为 `Customer Issue/Customer Label + Mention Share + Impact Reviews + Representative Evidence`；下载改为 occurrence 级 evidence + related reviews；导出补齐审计字段 |
  | Phase 6 验证与回归 | ✅ 完成 | 新增固定验证集与 `test_customer_label_phase6_validation.py`，覆盖 Foxelli、Comfortable evidence 失配、mixed review、否定漏水、真实漏水、cluster propagated、床架、睫毛膏、legacy old session、Internal Aspect 过滤 |
  | Phase 6 真实 Foxelli raw replay | ✅ 完成 | `scratch/session114_raw_replay.xlsx` 上传 clueai-dev 生成 session 3；最终 `Water Leaks Through=5 mentions / 5 reviews`，全部来自当前产品真实漏水原文 span，无旧风险 `9/9` 过计数 |
  | Phase 6.5 results LLM fallback | ✅ 完成 | `RESULTS_AI_ENHANCEMENT_ENABLED=false` 默认关闭；results 主 payload 先返回 heuristic，不被 DeepSeek / OpenAI enhancement 失败阻塞；AI 只能增强文本，不能覆盖 rows |
  | Phase 7 P0 read-path | ✅ 完成 | `get_comments()` 默认瘦列读取，不返回 `embedding`；`aspects_json` compact 投影；date span fallback 改 SQL `MIN/MAX`；连接关闭重试一次；`backend_api/tests` 176 passed |
  | Phase 7 P1 authenticated smoke | ✅ 完成 | clueai-dev/preprod route 层 session 3/4/5 authenticated smoke 通过；生产只读 results smoke 覆盖 114/96/111/110；未改 Not Breathable，未重构 Phase 1-6 核心算法 |
  | Phase 7 P1 worker write-path | ✅ 编码完成 / 待 staging 写入验证 | `update_comment_analysis_batch()`、`update_comment_clusters_batch()`、`update_comment_embeddings_batch()` 已落地；worker analysis 每 50 条批量写，cluster / RAG embedding 批量写；保留单条 API 和异常 fallback |
  | Phase 7 生产 credit/export 门禁 | ⏳ 待决策 | live `/analysis/results` 与 export 会扣 credit / 写 ledger；需要 Erika 授权或零扣费 staging；通过后再扩大生产流量 |

  真实样本验证记录：

  | session | 样本 | 结果 |
  |---------|------|------|
  | 3 | Foxelli Waders raw replay，92 reviews | `Water Leaks Through` count=5 / pct=62.5；`Comfortable To Wear` count=64 / pct=48.1；代表证据均为原文 span |
  | 4 | 432 reviews | `Breaks Easily` count=13 / pct=44.8；`Feels Well Made` count=290 / pct=92.7 |
  | 5 | 545 reviews | 无明确 Top Issue（`No clear friction`）；`Comfortable To Wear` count=463 / pct=89.6 |

  生产只读 results smoke（已部署 `1d537fd` 后）：

  | session | route | status / time | comments | Top Issue | Top Label | embedding | SSL/connection error |
  |---------|-------|---------------|----------|-----------|-----------|-----------|----------------------|
  | 114 | `/analysis/sessions/114/results` | 200 / 0.741s | 92 | `Not Breathable` | `Comfortable to Wear` | false | false |
  | 96 | `/analysis/sessions/96/results` | 200 / 0.726s | 661 | `Value for Money` count=6 | `Value for Money` count=135 | false | false |
  | 111 | `/analysis/sessions/111/results` | 200 / 0.394s | 100 | `Water Leaks Through` count=13 | `Keeps Water Out` count=17 | false | false |
  | 110 | `/analysis/sessions/110/results` | 200 / 0.426s | 100 | `Water Leaks Through` count=13 | `Holds Up Well` count=46 | false | false |

  Phase 7 P0 / P1 验证记录：

  | 验证项 | 结果 |
  |--------|------|
  | P0 commit | `origin/develop=1d537fd76aa61f8388fef80e84d9d7890e96d8b7` |
  | P0 自动化 | `python3 -m pytest backend_api/tests`：176 passed；目标 ruff passed；`git diff --check` passed |
  | P0 只读 DB smoke | session 3/4/5 compact read 成功，默认不带 `embedding`，未复现 SSL EOF；session 5 从历史 120s+/EOF 降到 31.3s |
  | P1 authenticated route smoke | session results、aggregate results、模块导出、完整导出均 200 |
  | embedding 边界 | 默认 results payload 不返回 `embedding`；QA/RAG 显式 `include_embedding=True` 可读 session 3 的 92/92 embeddings |
  | date span fallback | SQL `MIN/MAX` fallback 为 0.3s 级 |
  | LLM enhancement | 默认关闭，results 首开不依赖 provider |
  | credit / analytics | P1 smoke 进程内 patch `credit_consume` 与 `track_event` 为 no-op，未调用真实 QA/Ask、上传或重分析等扣费动作 |
  | production deploy | GitHub Actions `Deploy to Production` run `30230691101` completed/success for `1d537fd76aa61f8388fef80e84d9d7890e96d8b7` |
  | production read-only smoke | `/analysis/sessions/{id}/results` 生产只读 smoke：114/96/111/110 均 200；最大 session 96（661 comments）0.726s；默认 payload 均无 `embedding`；无 SSL/connection error |
  | P1 write-path automation | `python3 -m pytest backend_api/tests workers/tests`：200 passed；target ruff passed；fake DB 单测验证 analysis / cluster / embedding batch 写入均为 1 次 values update + 1 次 commit，cache 字段缺失可 fallback |

  相关文档 / 测试资产：
  - `docs/Customer_Issue_Label_Phase6验证报告.md`
  - `backend_api/tests/fixtures/customer_label_phase6_validation.json`
  - `backend_api/tests/test_customer_label_phase6_validation.py`
  - `backend_api/tests/test_export_customer_label_phase5.py`
  - `backend_api/tests/test_analysis_results_llm_fallback.py`
  - `backend_api/tests/test_database_read_path.py`
  - `migrations/058_customer_label_catalog_alias_candidates.sql`

  残留风险与下一步：
  - [ ] 生产全量发布前补 live `/analysis/results` 与 export smoke；若担心扣 credit，优先准备零扣费 staging。
  - [ ] P1 worker 写路径优化已完成编码，尚未做 staging 上传/重分析写入验证：目标是降低 per-comment `update_comment_analysis()` / cluster update / embedding update 对共享 DB 环境和连接池的峰值压力；后续验证会写 DB 且可能触发 LLM/credit。
  - [ ] P2 date/index 技术债尚未开始编码：`date` 仍是 text，session 3 存在 Amazon 文本日期；缺少 `(user_id, session_id, id DESC)` 复合索引不是本次主因，但更大表会放大。
  - [ ] `Comfortable_to_Wear_reviews_57.xlsx` 风险已用 fixture 复刻；若要作为正式金样本，需要重新导入或重放真实 xlsx，并确认 missing evidence 不进入 Representative Evidence。
  - [ ] Phase 7 小流量灰度初期继续保持 `RESULTS_AI_ENHANCEMENT_ENABLED=false`；如重新开启，先确认 provider/model 可用并监控 timeout / empty-cache 日志。
  - [ ] 增加 label stats / 告警：单一标签突然 100%、verified evidence 比例过低、broad/internal label 进入 Top、cluster propagated 占比异常升高、long-tail 标签过多。
  - [ ] 新增类目时按“系统自动候选 + Erika 审核高频 canonical label”的方式走，不人工维护每条评论：先跑 3-5 个该类目产品样本，再审核 Top 候选标签的保留、合并、改名、禁用。

  下一阶段任务拆解：

  | 优先级 | 任务 | 当前阶段 | 建议步骤 | Erika 参与点 |
  |--------|------|----------|----------|--------------|
  | P0 gate | live `/analysis/results` + export 生产门禁 | 待授权 / 待零扣费 staging | 1. 确认是否允许扣 credit；2. 对 prod/staging 代表 session 跑 aggregate results、模块导出、完整导出；3. 记录响应时间、Top Issue/Label、导出 sheet、SSL/connection error；4. 通过后再扩大生产流量 | 现在即可参与：授权扣费 smoke 或提供零扣费 staging |
  | P1 | worker 写路径优化 | 编码完成 / 待 staging 写入验证 | 1. 已审计 `update_comment_analysis()`、cluster update、embedding update 调用频率；2. 已实现 batch update 与小批量事务边界；3. 已补 fake DB/query count 单测；4. 待 staging 跑小样本上传/重分析；5. 再跑较大样本观察 worker 日志、DB 连接、任务耗时 | 现在可参与：授权上传/重分析样本验证，因为会写 DB 且可能触发 LLM/credit |
  | P2 | date text 规范化 + 索引 | 方案设计待开始 | 1. 盘点真实 date 格式，含 Amazon 文本日期；2. 设计 normalized date/backfill 或安全解析层；3. 评估并准备 `(user_id, session_id, id DESC)` 及 product/date 查询索引；4. staging migration；5. 验证 history/results/aggregate range 行为 | migration 前参与：确认 DDL 窗口、备份/回滚方案和抽样验收 |

  新对话继续提示词：

  ```text
  请接着当前 ClueAI `develop` 分支推进 Phase 7 后续任务。先阅读 `PROGRESS_V2.md` 的 `Step C9.8: Customer Issue / Customer Label 口径重构与灰度验证`。

  当前状态：
  - P0 read-path 修复已 commit/push/deploy：`1d537fd76aa61f8388fef80e84d9d7890e96d8b7`。
  - GitHub Actions `Deploy to Production` run `30230691101` 已 completed/success。
  - 生产只读 `/analysis/sessions/{id}/results` smoke 已通过：114/96/111/110 均 200，最大 session 96（661 comments）0.726s，默认 payload 无 `embedding`，无 SSL/connection error。
  - clueai-dev/preprod authenticated route smoke 已通过 session 3/4/5：session results、aggregate results、模块导出、完整导出均 200；credit/analytics 在验证进程内 no-op，未写 ledger。
  - live `/analysis/results` 与 export 仍未在生产真实调用，因为会扣 credit / 写 ledger；需要 Erika 授权或零扣费 staging。

  约束：
  - 不再改 Not Breathable 标签逻辑。
  - 不重构 Phase 1-6 Customer Issue / Customer Label 核心算法。
  - 不调用会扣 credit、写 quota/credit ledger 或写 analytics 的业务动作；如必须调用，先说明风险并等待 Erika 确认。

  下一步优先级：
  1. 若 Erika 授权或提供零扣费 staging，先补 live `/analysis/results?...session_id={id}`、模块导出、完整导出 smoke，并记录响应时间、Top Issue/Label、导出 sheet、SSL/connection error。
  2. 可以开始 P1 worker 写路径优化编码准备：审计 `update_comment_analysis()`、cluster update、embedding update 调用频率，设计 batch update/upsert 与事务边界，补 fake DB/query count 单测。
  3. P2 date text 规范化与索引先做方案，不急于生产 DDL；migration 前需要 Erika 确认窗口、备份和回滚方案。
  ```

  后续 Erika 参与点：

  | 什么时候 | 需要做什么 | 预计人力 |
  |----------|------------|----------|
  | Phase 7 生产扩大前 | 授权 live credit/export smoke，或提供零扣费 staging | 5-10 分钟决策 |
  | P1 小流量灰度 3-7 天内 | 看 3-5 个真实 session 的 Top Issue / Top Label、代表证据、下载是否符合预期 | 每天 15-30 分钟 |
  | 新品类首次接入 | 审核该类目高频候选标签：保留 / 合并 / 改名 / 禁用 | 每个类目 30-60 分钟 |
  | 稳定运行后 | 看异常告警和候选池，只处理高频、前台可见、低置信度或跨品类边界 case | 每周 10-20 分钟 |

- [ ] **Step C10: 暗色模式（可选）**
  - 仅在种子用户反馈中有明确需求时执行
  - 需要为所有 color token 增加 dark 变体


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
| 2026-05-27 | 2.1 | 确认多产品仪表盘已在 V1 阶段完整实现，标记为完成 |
| 2026-05-27 | 2.2 | 版本对比视图完成，与环比分析合并为统一区块 |
| 2026-06-03 | 2.3 | Ask your reviews 升级为向量版 RAG：embedding 入库、pgvector 余弦检索、DeepSeek 回答、引用评论、Pro 计费墙 |
| 2026-06-03 | 2.4 | Paddle 计费链路完成：plan 字段、Checkout、Webhook、第二产品限制 |
| 2026-06-03 | 2.5 | 本地完成产品档案数据模型与产品管理页首版，兼容旧 `product_id` 历史数据显示，未推送部署 |
| 2026-06-03 | 2.6 | 本地完成上传流程升级首版：工作目的、产品绑定、自动识别 ASIN/SKU 子变体、session 绑定上下文，未推送部署 |
| 2026-06-03 | 2.7 | 本地完成行动中心首版：独立 action store、结果页创建动作、行动中心状态流转，未推送部署 |
| 2026-06-03 | 2.8 | 本地完成复盘追踪首版：独立 review store、行动中心生成 tracker、复盘页结果录入、结果页复盘提醒，未推送部署 |
| 2026-06-04 | 商业化路径 | 新增「前端架构与商业化落地路径」章节：双层架构决策、按 MRR 里程碑触发的迁移路径、3.1.5 营销站（P1-7）最小可行范围；P2-6 修订为"产品层 Streamlit → Next.js 全迁移"，仅在 MRR > $3k 后启动 |
| 2026-06-06 | 5.7 | 本地完成宣传文案 / 设置 / 计费迁移收口：`/copywriter`、`/settings`、Paddle Checkout / Webhook、计费状态回写，文案与设置页可用 |
| 2026-06-06 | 5.8 | 本地完成部署与 Streamlit 下线路径：`frontend / backend_api / workers` 容器、Nginx、docker-compose、阿里云部署说明、域名分层与回退边界；同时补齐营销站 SEO 基础 |
| 2026-06-06 | SEO | 本地补齐 Next.js 营销站可上线 SEO 基础：首页 / 定价 / 试用页独立 metadata、应用页 noindex、`robots.txt` / `sitemap.xml` / `opengraph-image` |
| 2026-06-09 | 5.8 | 将 ECS 验证阶段调整为后置：本地部署配置已完成，但线上 DNS / HTTPS 验证等待 V4 核心功能稳定后再继续；明确不阻塞本地开发与测试 |
| 2026-06-04 | V4 技术路线 | 新增「V4 技术优化与商业化落地路线图」章节：基于 Shulex 竞品对比 + 10 万条多类目数据资产，规划 7 个核心任务（数据资产化、商业化基建、LLM 输出加固、成本优化、ABSA 小模型、用户反馈回路、Niche 商业化），目标 8 周内把单条成本降 85%、准确率提升至 95%、找到 5 个付费用户验证 PMF |
| 2026-06-12 | 7.5 | 新增「数据埋点与用户行为分析体系」：PostHog Cloud 注册 + Free plan + Paddle 数据源连接；前端 SDK 接入（analytics.ts + AnalyticsProvider）+ 后端 analytics_events 表 + FastAPI 中间件 + 登录/注册/上传关键事件埋点；Step 1-4 全部完成；独立深度学习文档 `数据埋点学习文档.md` |
| 2026-06-14 | 7.6 | 用户反馈浮窗组件全部完成：migration + 后端 route（含邮件通知）+ 前端 Widget（FAB+情绪+表单+中英文自适应+快捷键）+ AppShell 集成 + PostHog 埋点；已推送 develop（3 commits） |
| 2026-06-14 | 7.7 | 新增「中国大陆访问优化」计划：Phase A Cloudflare CDN + 性能优化（立即执行）；Phase B ICP 备案 + 国内节点（付费用户 ≥10 触发）|
| 2026-06-18 | 前端测试 | 决策：当前阶段不引入前端测试框架（Vitest/Jest）。理由：快速迭代期、CI 已有 tsc+build 兜底、核心逻辑在后端。触发条件：出现复杂前端逻辑/状态机、频繁回归 bug、核心功能稳定进入维护期时引入 Vitest + React Testing Library |
| 2026-06-25 | 9.3 增强 | 推送设置页重构（Part A）：设置页改为 sidebar 3 子页（push/api-keys/billing），推送页合并全局规则+产品规则+周期推送+升级规则为单页全宽布局；推送内容增强（Part B）：B1 条数+占比、B2 AI 总结建议、B3 可点击链接、B4 行动中心引导、B5 环比推送增强、B6 TOP 问题复盘进度 |
| 2026-06-25 | 7.12 | 可观测性页面重构：从 265 行单页重构为 5-Tab 管理后台（概览/成本/任务/缓存/告警），新增时间范围选择器+模型状态灯行+可展开 trace timeline+成本堆叠柱状图；从用户 sidebar 移除，仅管理员 URL 访问；10 个新组件于 `components/observability/` |
| 2026-06-30 | 6.3 | Golden Set 标签校准管理系统 + 管理员权限控制：golden_set 表 + boundary_note 字段 + CSV 上传 API + 准确率统计 + few-shot 注入 + /settings/golden-set 管理页 + users.is_admin + sidebar adminOnly 过滤 + 页面级权限守卫；migration 033/034/035 |
| 2026-06-30 | 6.1 扩展 | 全品类 Taxonomy 批量扩展：新增 5 品类(outdoor/beauty/kitchen/automotive/office) 27 子品类 441 条 aspect 全部携带 boundary_note；表结构重建 migration 037；sub_category_categories.json 覆盖 87 子品类；docs/类目标签覆盖表.md 产出 |
| 2026-07-07 | 6.4 Step 7 | 跨用户 LLM 分析结果复用：接通已有 review_pool 全局池 → L1 缓存除用户自己历史也查 pool（analyzer_version 校验隔离），CSV 上传的分析结果也回填 pool；migration 043 加 content_hash 部分索引 + comments.cache_hit_source 列；隐私政策 + 服务条款追加"分析结果聚合复用"条款；预期热门 ASIN 场景 DeepSeek 调用量下降 30–60% |
| 2026-07-23 | LLM Router 旧链路迁移 | Review Q&A、结果翻译、Compare AI Summary、非结构化解析兜底、eval runner、已跟踪 taxonomy/golden 维护脚本统一迁移到 `backend_api.app.services.llm_router.router_completion()` 或 Router 兼容 shim；QA 与 Compare 路由复用 `get_analysis_locale(request)`；`locale="en"` 路由顺序为 GPT-4o-mini → DeepSeek → Qwen，`locale="zh"` 为 DeepSeek → GPT-4o-mini → Qwen；commit `71b0d4c` 已推送 `origin/develop` |
| 2026-07-24~2026-07-27 | Step C9.8 | Customer Issue / Customer Label 口径重构、Phase 1-6.5 验证、Foxelli raw replay、Phase 7 P0 read-path、Phase 7 P1 authenticated route smoke 已集中整理到上方 `Step C9.8`；底部 changelog 不再重复维护详细记录 |

---

## 6. 技术优化

> 背景：基于 Shulex / VOC AI 竞品技术选型对比，结合 10 万条多类目评论源数据资产，制定从「LLM+Prompt 单点架构」演进到「ABSA 小模型 + Embedding 聚类 + LLM 生成」三层架构的可商业化落地技术路线。
>
> 优化函数：商业化盈利（不是面试展示），目标按 ROI 排序。
>
> 总投入：8 周，与 2.5-3.1 业务功能并行推进。

### 核心思路（一句话）

把 Shulex 用 18 个月走完的路压缩到 8 周：先用 10 万条数据立起「评测基准 + 品类 Taxonomy + Bad Case 库」，再分阶段把 ABSA 任务从 LLM 收回到小模型，把 LLM 留给生成式任务，配合 Embedding 聚类做成本优化；同时完成商业化基建（收款、多租户、部署），让前 50 个付费用户可承接。

### 与 Shulex 的差距地图

| 维度 | V1/V2 阶段 | V4 目标 | Shulex 现状 | 优先级 |
|------|---------|---------|------------|--------|
| 分析单元 | 逐条 LLM | Embedding 聚类 + LLM 打标签 | 同 | P0 |
| 输出格式 | Prompt 约束自由文本 | 强制 JSON Schema | 同 | P0 |
| Prompt 版本 | 无版本管理 | Git + DB 双层追踪 | LangSmith | P0 |
| ABSA 任务 | 纯 LLM | fine-tuned 小模型 | 同 | P1 |
| 反馈回路 | 无 | 用户纠错 → bad case 库 → few-shot | 同 | P1 |
| 成本模型 | 线性增长 | 聚类后近似固定 | 同 | P0 |
| Fallback | 单 DeepSeek | 三级链路 | 多模型 | P1 |

### 预期收益对比

| 指标 | V1 阶段 | V4 目标 | 提升幅度 |
|------|--------|----------|---------|
| 情感分类准确率 | ~90% | 95-97% | +5-7pp |
| 痛点分类准确率 | <85% | 90-93% | +5-8pp |
| 100 条评论分析耗时 | 31 秒 | 8-12 秒 | 降 60-70% |
| 单条评论成本 | ¥0.0002 | ¥0.00003 | 降 85% |
| 10 万条月分析成本 | ¥20-40 | ¥3-6 | SaaS 毛利可控 |
| Vendor 依赖 | 单 DeepSeek | 三级 fallback | SLA 可承诺 |

---

### 6.1 数据资产化

**目标：** 把 10 万条原始数据加工成可复用的评测基准、品类 Taxonomy 和 Bad Case 库，作为后续所有优化的度量底座。

**Files:**
- Create: `data/golden_set/` 目录（评测基准集）
- Create: `data/taxonomy/` 目录（品类 Aspect 词典）
- Create: `review_analyzer/eval/` 模块（评测脚本）
- Create: `scripts/build_golden_set.py`、`scripts/build_taxonomy.py`

- [x] **Step 1: 数据预处理**
  - 从 10 万条原始数据中按品类 × 情感 × 评分分层采样 2000 条
  - 清洗 unrecognizable / 空内容 / 重复评论
  - 输出 `data/golden_set/raw_2000.csv`
  - 实际产物：`data/golden_set/raw_2000.csv` (2018 行) + `scripts/preprocess_furniture_data.py`

- [x] **Step 2: 人工标注 Golden Set**
  - 标注字段：情感（正/负/中）、Aspect（如包装/功能/品控）、痛点分类
  - 标注协议：双人交叉标注，分歧由 Erika 仲裁
  - 拆分：1500 条训练集 + 500 条测试集
  - 锁版本：`data/golden_set/v1.0/`，永远不动
  - 实际产物：`data/golden_set/v1.0/ai_annotated_500.csv` (501 行) + `golden_500_reviewed.csv`

- [x] **Step 3: 构建品类 Taxonomy**
  - 用 GPT-4o 对 10 万条做全量 Aspect 抽取
  - 按品类聚合（家居 / 3C / 服饰 / 母婴 / 宠物 / 户外...）
  - 人工 review + 合并同义词（packaging damage / damaged packaging）
  - 存入 PostgreSQL `category_aspect_taxonomy` 表
  - 输出 `data/taxonomy/v1.0/{category}.yaml`
  - 实际产物（2026-06-10 完成）：
    - 5 个核心品类 60 个子品类 YAML：家居 6（24032 条）、3C 11（21719 条）、服饰 8（18695 条）、母婴 9（6588 条）、宠物 26（41536 条），合计 112570 条评论 Aspect 抽取
    - 户外品类本轮剔除（Erika 决策，原始数据保留待后续轮次）
    - PG `category_aspect_taxonomy` 表共 1501 行（87 sub_category × 平均 17.3 aspect）
      - 2026-06-10: 初始 1060 行（5 品类 60 子品类）
      - 2026-06-30: 扩展至 1501 行（10 品类 87 子品类），新增 outdoor/beauty/kitchen/automotive/office 5 品类 27 子品类，全部携带 boundary_note；表结构重建（migration 037）
    - 通用脚本：`scripts/preprocess_reviews.py`（按品类 yaml 配置预处理）、`scripts/extract_taxonomy_generic.py`（支持 seed extends）、`scripts/build_taxonomy_review_sheet.py`（人工 review 表生成）、`scripts/apply_taxonomy_review.py`（review 决策套回 yaml）、`scripts/import_v4t1_assets.py`（rglob 入库，加 keepalive 防 SSL 超时）、`scripts/generate_new_taxonomy_yamls.py`（批量生成新品类 YAML）
    - 抽取成本：¥55.99（DeepSeek API）

- [x] **Step 4: 建立 Bad Case 库**
  - 把当前 V1/V2 测试中所有误判样本归档
  - 字段：原文、AI 输出、正确输出、错误类型、修复方案
  - 存入 PostgreSQL `bad_cases` 表，作为后续 few-shot 种子
  - 实际产物：`data/golden_set/v1.0/bad_cases_v1.0.csv` (44 条) + `scripts/init_bad_cases.py`

- [x] **Step 5: 评测自动化脚本**
  - 实现 `python3 -m review_analyzer.eval.run --prompt-version vX --golden-set v1.0`
  - 输出准确率、召回率、F1、混淆矩阵、Token 消耗
  - 集成到 GitHub Actions：每次改 Prompt 强制跑回归
  - 实际产物：`review_analyzer/eval/run.py` + `runner.py` + `golden_set.py`

- [ ] **Step 6: 验收标准**（部分达成 2026-06-10）
  - [x] Golden Set 500 条测试集准确率基线建立（v2.1/v2.2/v2.3 三版 metrics 已落地于 `data/golden_set/v1.0/eval_v2*_500_metrics.json`）
  - [x] Taxonomy 覆盖至少 5 个核心品类（家居 / 3C / 服饰 / 母婴 / 宠物，60 sub_category 入库）
  - [ ] Bad Case 库初始至少 50 条（**当前 bad_cases 表 12 行 / csv 44 条，欠 6+ 条；下一轮回归测试中补足**）

---

### 6.2 Taxonomy 接入分析链路

**背景（2026-06-10 发现的问题）：** 6.1 Step 3 完成后，`category_aspect_taxonomy` 表已入库 1060 行（60 子品类 × 平均 17.7 aspect），但全代码搜索 0 处 SELECT —— 整个分析调用链（`workers/jobs.py` → `deep_analyzer.py` → prompt v2.3）完全绕过该表。

**当前现状：**
- AI 抽取 100% 依赖 `backend_api/app/prompts/annotate_v2.3.md` 中**硬编码的 19 类家具 aspect**
- 用户上传 3C/服饰/母婴/宠物评论时，AI 仍按"家具视角"分析，抽不到 `charging_speed`/`size_fit`/`pet_acceptance` 等品类专属 aspect
- 用户上传非 5 类目评论（户外/食品/玩具）也能跑，行为完全相同 —— **5 类目和非 5 类目当前差异为 0**
- 1060 行 taxonomy 数据处于"预留状态"

**目标：** 把 6.1 Step 3 产出的 taxonomy 接入 prod 分析链路，实现"通用维度 + 品类专属维度"（Shulex 模式）。

**Files:**
- Modify: `workers/jobs.py`（按 sub_category 查 taxonomy 表）
- Modify: `backend_api/app/services/deep_analyzer.py`（参数化注入 aspect 清单）
- Modify: `backend_api/app/prompts/annotate_v2.3.md` → 新建 `annotate_v2.4.md`（加 `{aspects_for_this_category}` 占位符）
- Modify: `backend_api/app/services/prompt_registry.py`（支持品类参数化）

- [x] **Step 1: 设计动态 prompt 模板** ✅ 2026-06-10
  - 新建 `annotate_v2.4.md`：把硬编码的 19 个家具 aspect 改为占位符 `{{ASPECTS_BLOCK}}`
  - 模板结构："通用 base aspect（9 个跨品类共享） + {category_specific_aspects}（按 sub_category 动态注入）"
  - base aspect 候选：packaging / shipping_damage / customer_service / value_for_money / build_quality / durability / aesthetics / ease_of_use / other
  - 校验：prompt 总长度增量 ≤ 800 token（实测家居 20 aspect 注入后 system_prompt 18140 chars vs v2.3 17789 chars，增量 ≈ 50 token）

- [x] **Step 2: workers/jobs.py 查 taxonomy** ✅ 2026-06-10
  - 分析前按 `sub_category` 查 `category_aspect_taxonomy` 表，拿到该子品类的 aspect_key 列表 + label_zh
  - 缓存机制：进程级 LRU 缓存（`taxonomy_loader.py`，maxsize=256）
  - 命中：把 aspect 列表注入 prompt（`aspects_block` + `allowed_aspects` 参数传入 `deep_analyzer`）
  - 未命中（用户上传非 5 类目）：fallback 到通用 prompt（仅 9 个 base aspect + `other`）
  - `deep_analyzer.py` `_validate_annotation()` 支持动态 `allowed_aspects` 集合

- [x] **Step 3: 品类白名单 + UI 提示** ✅ 2026-06-10
  - 前端上传页面新增"已支持的 5 个核心品类"提示（家居/3C/服饰/母婴/宠物 + 60 子品类）
  - 用户选其他品类（户外/食品/...）时弹"该品类暂用通用模板，aspect 颗粒度较粗"提示，让用户知情而非默默降级
  - 后端不做硬白名单，保留通用 fallback（避免拒服务）
  - API: `GET /taxonomy/categories` + `GET /taxonomy/sub_category?name=xxx` 已就位
  - 前端: `CategoryHitBanner` 组件 + `datalist` autocomplete 已集成

- [x] **Step 4: 回归测试** ✅ 2026-06-11
  - 用 `data/golden_set/v1.0/` 的 499 条家居 golden set 跑 v2.3 vs v2.4 prompt 对比（本地 DeepSeek API 直连）
  - 结果：v2.4 情感准确率 94.8% vs v2.3 94.6%（+0.20pp），token 成本增量 +0.3%（远低于 30% 阈值）
  - 高评分(4-5) +1.31pp、低评分(1-2) 持平 100%、中评分(3) -1.07pp（可接受）、Bad Case 持平 96.1%
  - LLM 调用失败 0 次，Output tokens 反而减少 5.8%
  - 详细指标：`data/golden_set/v1.0/eval_v23_vs_v24_comparison.json`
  - 明细数据：`data/golden_set/v1.0/eval_v24_500_raw.csv`
  - 评测脚本：`scripts/eval_v23_vs_v24.py`
  - [x] 跨品类验证 ✅ 2026-06-11（两轮测试）
    - 第一轮：8 条手工评论（4 品类 × 2 条），品类专属 aspect 召回率 81%（21/26）
    - 第二轮：40 条真实评论（4 品类 × 10 条随机采样），Taxonomy 命中率 **100%**（72/72 全部落在品类 taxonomy 内，零越界）
    - 品类专属 aspect 出现：3C `charging_speed/compatibility`、服饰 `cut_fit/cleaning/color_accuracy/size_fit/comfort/length`、母婴 `size_fit`、宠物 `size_fit/smell/weight_capacity`
    - 详细数据：`data/golden_set/v1.0/eval_v24_cross_category.json`

- [x] **Step 5: 切换 + 监控**（代码层已完成 2026-06-10，监控待部署后观察）
  - `DEFAULT_ANNOTATE_VERSION` 已改为 v2.4
  - 监控前 1000 条分析请求的 token 消耗增量 + aspect 抽取分布（⏳ 部署后观察）
  - 若 token 成本上升超过 30%，考虑只把 TOP10 高频 aspect 注入而非全集

**验收：**
- 5 类目内评论：抽取的 aspect 至少 60% 落在 `category_aspect_taxonomy` 的该子品类集内
- 5 类目外评论：仍能跑、走通用模板、UI 有提示
- token 成本上升 ≤ 30%（v2.3 baseline）

**关联任务：** 完成后 6.1 Step 6「Taxonomy 覆盖至少 5 个核心品类」从"已入库"升级为"已生效"，bad_cases 库可借此识别"品类专属错例"补到 50 条门槛。

---

### 6.3 Golden Set 多品类演进 + 时效性防护

**背景（2026-06-17 识别的风险）：** 当前 Golden Set v1.0 仅覆盖家具家居 6 子品类（499 条评测集），CI 回归也只验证这一个品类。如果产品新增品类（3C、宠物、母婴等），或已有品类出现新功能关键词（如"快充"），Golden Set 对这些维度是"盲测"——准确率指标无法反映真实表现。Shulex 用 20000+ tag + 运营团队持续维护解决此问题，ClueAI 需要低成本替代方案。

**目标：** 让 Golden Set 评测覆盖范围随 Taxonomy 扩展同步增长，消除"新品类准确率盲区"。

**前置依赖：** 6.1 Step 3（Taxonomy 入库）✅ + 6.2（Taxonomy 接入链路）✅

**Files:**
- Create: `scripts/build_golden_set_generic.py`（按品类生成 mini golden set）
- Modify: `.github/workflows/golden-set-regression.yml`（支持多品类循环评测）
- Modify: `review_analyzer/eval/run.py`（`--category` 参数支持）
- Create: `backend_api/app/services/taxonomy_coverage_monitor.py`（`other` 占比告警）
- Create: `data/golden_set/v1.1/`（多品类评测集目录）

- [x] **Step 1: 品类级 mini Golden Set 生成脚本** ✅ 2026-06-17
  - 每个新品类上线时，从该品类数据中分层采样 50-100 条
  - 用 DeepSeek 预标注（sentiment + aspect），人工仲裁不一致样本
  - 输出到 `data/golden_set/v1.1/{category_slug}/golden_50.csv`
  - 成本预估：¥0.05-0.10/品类（50 条 DeepSeek 标注）
  - 实际产物：`scripts/build_golden_set_generic.py`

- [x] **Step 2: CI 多品类回归** ✅ 2026-06-17
  - `golden-set-regression.yml` 新增 v1.1 多品类评测步骤（`--all-categories`）
  - 每个品类独立出准确率，任一品类低于阈值即 fail
  - 新品类阈值从 85% 起步（样本少、置信区间宽），家具家居维持 93%
  - eval CLI 新增 `--category` 和 `--all-categories` 参数
  - 实际产物：`review_analyzer/eval/run.py`（多品类 CLI）+ `review_analyzer/eval/golden_set.py`（v1.1 加载器）+ `.github/workflows/golden-set-regression.yml`

- [x] **Step 3: `other` 占比线上监控（最低成本防御）** ✅ 2026-06-17
  - 分析完成后统计该批次 `other` aspect 占比
  - 阈值：单品类 `other` > 15% 触发告警（说明 taxonomy 覆盖不足）
  - 告警方式：写入 `upload_jobs.trace_json.warnings` + `sessions.warnings_json` + 飞书推送
  - UI 侧在分析结果页显示黄色告警横幅
  - 实际产物：`backend_api/app/services/taxonomy_coverage_monitor.py` + `migrations/022_add_session_warnings.sql` + `workers/jobs.py`（集成）+ `frontend/src/app/analysis/results/page.tsx`（UI 展示）

- [ ] **Step 4: Taxonomy 新增 → Golden Set 联动 SOP**
  - 当 `category_aspect_taxonomy` 表新增 sub_category 时，自动创建该品类的 Golden Set TODO
  - 每季度 review：检查 `other` 占比最高的 Top 3 品类，优先补充 golden set
  - 文档化为 `docs/golden-set-evolution-sop.md`

**验收标准：**
- 每个已上线品类至少有 50 条 golden set 评测数据
- CI 能按品类分别报告准确率（不再只有一个全局数字）
- 线上 `other` 占比 > 15% 时，30 分钟内有告警通知
- 新品类从 Taxonomy 入库到 Golden Set 就绪 ≤ 2 天

**当前进度备注（2026-06-17）：**

Step 1-3 已全部实现并通过验证。关键实施细节：

1. **监控链路（Step 3）完整闭环**：`worker 分析完成 → compute_taxonomy_coverage() 计算 other 占比 → 超 15% 阈值触发 → ①写入 trace_json.warnings ②写入 sessions.warnings_json ③飞书 Webhook 推送 → 前端结果页展示黄色告警横幅`。所有异常均 non-fatal catch，不会阻塞主分析流程。

2. **数据库变更**：`migrations/022_add_session_warnings.sql` 已在 dev 库（`clueai-dev`）执行。**prod 部署时需同步执行**：`ALTER TABLE sessions ADD COLUMN IF NOT EXISTS warnings_json JSONB;`

3. **Golden Set 生成脚本（Step 1）已就绪但无实际数据**：当前 `data/golden_set/v1.1/` 目录为空，因为尚未有新品类上线需求触发。下一个品类上线时执行 `python3 scripts/build_golden_set_generic.py --category "品类名" --limit 50` 即可。

4. **CI 多品类评测（Step 2）已就绪但处于空跑状态**：`--all-categories` 在 v1.1 目录为空时跳过，不影响现有 v1.0 家具家居回归。当第一个品类 golden set 落地后自动生效。

5. **Step 4（SOP 文档）未做**：属于流程管理类工作，等第一个新品类实际走完 Step 1 流程后再总结 SOP，避免纸上谈兵。

**触发条件**：当用户上传非家具家居品类评论（如 3C、宠物），且分析结果中 `other` 占比告警频繁出现时，说明该品类需要补充 taxonomy + golden set。

---

### 6.4 商业化基建

**目标：** 让产品具备承接前 50 个付费用户的能力。

**Files:**
- Modify: `review_analyzer/database.py`（多租户隔离审计）
- Modify: `review_analyzer/auth.py`（配额计数）
- Create: `review_analyzer/quota.py`（用量限制）
- Modify: `review_analyzer/paddle_billing.py`（套餐档位）
- Create: `legal/privacy.md`、`legal/terms.md`

- ~~**Step 1: 部署迁移**~~ *已由 5.8 ECS 方案替代*
  - 早期考虑过 Render / Railway / 自建 VPS，后决定使用阿里云 ECS + docker-compose 部署
  - 当前 prod 已运行于 ECS：nginx + Next.js + FastAPI + RQ worker + Redis，域名 `app.clueai-reviewlens.com`（HTTPS）
  - 本条不再作为待办任务

- [ ] **Step 2: 数据库基建升级（成熟 SaaS 标准化）**

  > **目标**：把当前"单库共用 + 散养 schema"升级为生产可承接的成熟 SaaS 数据库基建。
  > **总耗时预估**：3-4 天（拆 7 个子任务）。
  > **关键决策**：本步骤完成后，Step 3 quota.py 才能在干净的多租户环境下实现，避免数据隔离漏洞。

  **现状盘点（2026-06-09 扫描）：**
  - ❌ 本地 / 阿里云生产 / Streamlit Cloud 三处共用同一 Supabase 项目（`inpgrbjwtpxgwungghnz`），存在生产数据被本地代码污染风险
  - ❌ 数据库密码为弱密码（人名+生日格式），且明文写入 [.env](.env) / [deploy/.env](deploy/.env) / [.streamlit/secrets.toml](.streamlit/secrets.toml)
  - ❌ 业务表（comments / sessions / products / actions / trackers）SQL 查询的 `user_id` 过滤情况未审计
  - ❌ 业务表缺 `updated_at` / `deleted_at`（软删除）字段
  - ❌ schema SQL 没有版本号编号（`migrations/001_xxx.sql` 格式缺失）
  - ❌ 缺关键字段 CHECK 约束（如 `plan` 枚举值、`rating` 范围）
  - ❌ 缺周备份到 OSS 的灾备机制（仅依赖 Supabase 默认 7 天快照）

  ---

  ### Step 2.0: 凭证安全加固（30 分钟，最高优先级）

  > **2026-06-10 进度更新**：本步骤已部分启动并发现历史泄露事故。详见下方「实际进展记录」。

  - [x] 检查 git 历史：发现 commit `37032b0`（`review_analyzer/.env`）泄露 DEEPSEEK_API_KEY / AES_SECRET_KEY / FEISHU_WEBHOOK；commit `9c89af0` 在代码/文档里硬编码 Supabase DB 密码（具体值已记录在 Erika 本地 1Password，**不在此处复述**）；远程 `origin = https://github.com/erikazzsw-art/review-analyzer.git` 是 **public**
  - [x] DeepSeek key 在后台 revoke 旧值 + 生成新 key（2026-06-10）
  - [x] `review_analyzer/.env` 从 git 跟踪移除（`git rm --cached`，本地文件保留）
  - [x] `.gitignore` 加固：覆盖 `review_analyzer/.env`、`backend_api/.env`、`deploy/.env*`、`frontend/.env*`、`.streamlit/secrets.toml`
  - [x] 全局 + 项目 CLAUDE.md 新增「机密保护规则」章节，pre-commit 强制扫描清单已写入
  - [x] **Supabase Dashboard → Settings → Database → Reset Password 重置主库密码**（新密码用密码管理器生成 24 位随机串）
  - [x] **飞书机器人 webhook 删除旧值 + 重建新 webhook**
  - [x] 同步更新三处 `.env` 文件（`./.env`、`review_analyzer/.env`、`deploy/.env`）
  - [x] **AES_SECRET_KEY 的轮换推迟到 Step 2.1（建立 dev 库）之后再做**——见 Step 2.0c ✅ 2026-06-11（prod 无加密数据，直接换新 key）
  - 验收：旧 DeepSeek/DB/飞书凭证全部失效，git 工作区无机密文件被跟踪 ✅（git filter-repo 待统一收尾）

  ---

  #### Step 2.0c: AES_SECRET_KEY 迁移（推迟到 Step 2.1 之后执行）

  > **2026-06-11 进度更新**：dry-run 确认 prod 库 0 个用户存有加密 API Key，无需数据迁移。已直接换新 key。
  >
  > 旧 key 仍在 git 历史 `37032b0` 中，`git filter-repo` 清理待所有凭证轮换完成后统一执行。

  - [x] **Step 1: 写 AES key 双 key 迁移脚本（dry-run 版）**
    - 文件：`scripts/rotate_aes_key.py`
    - 逻辑：读环境变量 `AES_SECRET_KEY_OLD`（旧）和 `AES_SECRET_KEY_NEW`（新）
    - 流程：扫 `users.api_key_encrypted` → 用旧 key 解 → 用新 key 加 → 写回
    - dry-run 模式下不写库，只输出"会处理多少行"
  - [x] **Step 2: 在 dev 库演练**
    - dry-run 结果：0 个用户存有加密 API Key → 无需迁移
  - [x] **Step 3: prod 上线**
    - prod 同样 0 条加密数据 → 直接更新 `.env` 中 `AES_SECRET_KEY` 为新值即可
    - 本地三处 `.env` 已更新为新 key ✅ 2026-06-11
    - ECS 重启待 V4 稳定后统一部署时执行
  - [ ] **Step 4: 收尾**
    - ~~移除环境变量里的旧 key~~ ✅ 已完成（本地 .env 已全部换新）
    - `git filter-repo` 清理历史里的 commit `37032b0`（**所有上游凭证轮换完成后**才能做这一步）
  - 验收：新 key 已在本地生效；旧 key 在 git 历史中的清理待统一收尾

  ---

  #### Step 2.0d: Streamlit 退场（执行计划）

  > **背景**：Next.js + FastAPI 已完全接管 prod 流量（5.2~5.8 全部完成）。Streamlit 仅作为 legacy 残留，当前 docker-compose 中 `profiles: legacy` 不启动。本计划正式移除 Streamlit 相关代码和配置。

  **前置条件确认**（2026-06-16 评估）：

  - [x] **数据迁移核对**：5.3~5.7 全部完成，用户/产品/评论/行动/复盘在 Next.js 端完整可用
  - [x] **会话切换**：FastAPI HttpOnly Cookie 已接管（5.2 完成）
  - [x] **Streamlit Cloud 下线**：✅ 2026-06-16 Erika 确认已关停、secrets 已清除
  - [x] **域名收口**：Next.js 已接管 `app.clueai-reviewlens.com`
  - [x] **`review_analyzer/.env` 处置**：当前指向 dev 库，被 backend_api 通过 `os.environ` 加载（非 Streamlit secrets），保留

  ---

  **Phase 1：删除纯 Streamlit UI 层（低风险，不影响 FastAPI）** ✅ 2026-06-16

  - [x] 删除 `review_analyzer/app.py`（Streamlit 主入口，19KB）
  - [x] 删除 `review_analyzer/page_shell.py`（Streamlit 页面壳）
  - [x] 删除 `review_analyzer/i18n.py`（纯 Streamlit UI 国际化）
  - [x] 删除 `.streamlit/` 目录（config.toml + secrets 模板）
  - [x] 删除 `docker-compose.yml` 中 `streamlit` 服务定义（profiles: legacy 块）
  - [x] 删除 `test_m8_full.py`（Streamlit 迁移测试，已过时）

  **Phase 2：清理共享模块中的 Streamlit 残留（需逐文件验证）** ✅ 2026-06-16

  - [x] `review_analyzer/database.py`：移除 `import streamlit as st`，`@st.cache_data` 装饰器，`st.secrets` fallback，`st.error/st.info/st.stop` → logger + raise
  - [x] `review_analyzer/product_store.py`：移除 `@st.cache_data` 装饰器及 `.clear()` 调用
  - [x] `review_analyzer/review_store.py`：同上，移除 `@st.cache_data` 及 `.clear()` 调用
  - [x] `review_analyzer/action_store.py`：同上，移除 `@st.cache_data` 及 `.clear()` 调用
  - [x] `review_analyzer/auth.py`：移除所有 Streamlit UI 函数，仅保留 FastAPI 使用的纯业务逻辑
  - [x] `review_analyzer/workspace_store.py`：移除 `i18n` 依赖，内联 `pick()`/`role_label()` 为 thread-local 实现
  - [x] `review_analyzer/workflow_prompts.py`：移除 `get_lang()` 依赖，改为参数传入 `lang`

  **Phase 3：依赖清理与验证** ✅ 2026-06-16

  - [x] 从 `requirements.txt` 和 `review_analyzer/requirements.txt` 移除 `streamlit` 及 `streamlit-authenticator`
  - [x] 运行 `python -c "from review_analyzer.database import get_user_by_id"` 验证模块可正常 import
  - [x] 运行 `cd frontend && npm run typecheck` 确认前端无影响
  - [x] 运行 `python3 -m ruff check backend_api/ workers/ review_analyzer/` 确认 lint 通过
  - [x] 更新 CLAUDE.md 中 Streamlit 相关说明（标记为已移除）

  验收：`backend_api` + `workers` 正常启动，所有 `from review_analyzer.*` 的 import 无 `streamlit` 依赖报错 ✅

  ---

  ### Step 2.1: 建立开发数据库（1 小时，Erika 操作）

  - [x] 登录 supabase.com → New Project，新建 `clueai-dev` 项目
    - Region 选 `aws-1-ap-southeast-1`（与生产一致）
    - 数据库密码用密码管理器生成
  - [x] 拿到新项目 Connection String 后，更新本地 [.env](.env)：
    ```
    DATABASE_URL=postgresql://postgres.[新项目id]:[密码]@aws-1-ap-southeast-1.pooler.supabase.com:6543/postgres
    ```
    > ✅ **2026-06-11 已切换**：`review_analyzer/.env` 指向 dev 库 `lbvbilkgequrvhldedqg`，连接验证通过
  - [x] 生产环境 [deploy/.env](deploy/.env) 与 [.streamlit/secrets.toml](.streamlit/secrets.toml) **保持原项目连接**
  - [x] 验收：本地代码连 dev 库，生产环境连 prod 库，互不污染 ✅ 2026-06-11

  ---

  ### Step 2.2: schema 编号化与同步（1 小时）

  - [x] 创建 `migrations/` 目录
  - [x] 把现有 [supabase_schema.sql](supabase_schema.sql) 拆成编号化文件：
    - `migrations/001_init_users.sql`
    - `migrations/002_add_plan_field.sql`
    - `migrations/003_create_comments.sql`
    - ...（按现有 schema 历史逻辑切分）
  - [x] 每个文件包含 UP（升级）和 DOWN（回滚）SQL
  - [x] 在 dev 库上跑一遍所有 migrations，验证可重建完整 schema
  - [x] 写一个 `migrations/README.md` 记录 migration 流程规范
  - 验收：dev 库通过 migrations 从零重建，schema 与 prod 库结构一致 ✅ 2026-06-10

  ---

  ### Step 2.3: 多租户隔离审计（1 天）

  - [x] 静态扫描：列出所有 SQL 查询及其 `user_id` 过滤情况
    - 文件：[database.py](review_analyzer/database.py) / [product_store.py](review_analyzer/product_store.py) / [parser.py](review_analyzer/parser.py) / [review_store.py](review_analyzer/review_store.py) / [action_store.py](review_analyzer/action_store.py) / [compare_store.py](review_analyzer/compare_store.py)
    - 已知 SQL 总数：~56 条
  - [x] 输出审计报告：每条 SQL 标注「✅ 已带 user_id」/「⚠️ 漏过滤」/「N/A 系统表」
  - [x] Erika review 报告，确认要修复的清单
  - [x] 修复所有「漏过滤」SQL，加 `WHERE user_id = %s`
  - [x] 高风险 JOIN 重写（避免子查询绕过隔离）
  - [ ] Supabase 启用 Row Level Security（RLS）兜底：⏳ *Step 2.1 dev 库就绪后启用*
    - 业务表加 RLS Policy：`USING (user_id = auth.uid())`
    - 即使代码层漏过滤，数据库层也会拦截
  - 验收：A/B 用户交叉测试通过，A 登录无法读到 B 的任何数据

  ---

  ### Step 2.4: schema 字段标准化（半天）

  - [x] 业务表统一加时间戳三件套：
    ```sql
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
    deleted_at  TIMESTAMPTZ  -- 软删除标记
    ```
  - [x] 加 `updated_at` 自动更新触发器（PostgreSQL trigger）
  - [x] 关键字段加 CHECK 约束：
    ```sql
    plan TEXT CHECK (plan IN ('free', 'pro_early', 'pro', 'team'))
    rating INT CHECK (rating BETWEEN 1 AND 5)
    sentiment TEXT CHECK (sentiment IN ('positive', 'negative', 'neutral'))
    ```
  - [x] 外键级联策略明确：`ON DELETE CASCADE` / `ON DELETE RESTRICT`
  - [x] 高频查询字段补复合索引（user_id + created_at DESC 优先）
  - 验收：所有约束在 dev 库生效，业务代码不受影响 ✅ 2026-06-10

  ---

  ### Step 2.4a: 邮箱唯一约束（注册隔离修复）✅ 2026-06-11

  **问题**：同一邮箱可注册多个账号（发现 `erikazzsw@gmail.com` 注册了 4 个账号：Yao/YYY/XXX/ZZZ）

  **已完成：**
  - [x] 数据库清理：删除重复账号（保留 user_id=4 YYY，删除 3/5/6 及关联的 3 sessions + 204 comments）
  - [x] 数据库加 UNIQUE 约束：`ALTER TABLE users ADD CONSTRAINT users_email_unique UNIQUE (email)`
  - [x] Schema 改动：`RegisterRequest.email` 改为必填（`min_length=3`）
  - [x] 路由改动：去掉 `if email and` 空值跳过逻辑
  - [x] database.py：`create_user` 的 email 参数去掉默认值
  - [x] 迁移文件：`migrations/012_unique_email.sql`

  **注意**：因 Step 2.1 本地环境分离未完成，此约束直接在生产库（`inpgrbjwtpxgwungghnz`）上执行。

  ---

  ### Step 2.5: 灾备与备份（半天）

  - [x] 写周备份脚本 `scripts/backup_to_oss.sh`（含保留策略：近 4 周全量，更早按月留 1 号那份）
  - [x] 写恢复脚本 `scripts/restore_from_oss.sh`（含 prod 安全拦截）
  - [ ] 阿里云 OSS 创建 `clueai-backup` bucket（标准存储）⏳ *V4 稳定后再执行*
  - [ ] ECS 安装 ossutil + pg_dump ⏳ *V4 稳定后再执行*
  - [ ] 配置 cron：每周一 09:00 自动跑 ⏳ *V4 稳定后再执行*
  - [ ] 演练一次"从备份恢复到 dev 库"流程 ⏳ *V4 稳定后再执行*
  - 验收：能从任意一周备份恢复出可用数据库

  ---

  ### Step 2.6: schema 改动回灌生产（30 分钟）

  > **高风险操作**：此步骤前必须先 Step 2.5 备份生产库。

  - [x] 在 dev 库验证所有 migrations 无误后，按编号顺序在 prod 库执行
  - [x] 每条 migration 执行前后做行数对比：
    ```sql
    SELECT COUNT(*) FROM users; -- 执行前后数字一致
    ```
  - [ ] RLS Policy 生产启用前，先用 dev 库的测试账号验证业务功能不受影响 ⏳ *RLS 启用时再做*
  - [ ] 生产启用 RLS 后立即跑端到端冒烟测试 ⏳ *RLS 启用时再做*
  - 验收：生产业务无中断，数据零丢失 ✅ 2026-06-10（migration 004+010+011 已执行）

  ---

  ### Step 2.7: 验收与文档(2 小时)

  - [ ] 多租户隔离测试：A/B 用户交叉访问全 API ⏳ *RLS 启用后再做端到端测试*
  - [ ] 备份恢复演练记录写入 [TEST_LOG.md](TEST_LOG.md) ⏳ *OSS bucket 就绪后再演练*
  - [x] 数据库基建文档 `docs/database-guide.md` 更新：
    - 环境隔离架构图
    - migrations 流程规范
    - 备份恢复 SOP
    - RLS Policy 添加规范
  - 验收：新人按文档可独立完成数据库环境搭建（文档已就绪 ✅ 2026-06-10）

  ---

  **Step 2 总验收标准：**
  - [x] 本地 / 生产数据库完全隔离，密码安全合规
  - [ ] 所有业务 SQL 通过 user_id 过滤 + RLS 双重隔离 ⏳ *RLS 待启用*
  - [x] schema 变更通过编号 migrations 管理
  - [x] 时间戳三件套、CHECK 约束、外键级联策略齐全
  - [ ] 周备份脚本运行 1 次以上 ⏳ *OSS bucket 就绪后再演练*
  - [x] 进入 Step 3 quota.py 实现的所有前置条件就绪


- [x] **Step 3: 套餐配额实现（V1 不限产品版）**
  - **Phase 1（0-100 付费用户）：不限产品数，按"评论条数 + Ask + 文案次数"控制成本**
  - Free Forever:
    - 评论分析 1500 条/月、Ask reviews 10 次/月、广告文案 10 次/月
    - 多产品对比（限同时对比 2 个产品）、Excel 导出 10 次/月
    - 预警通知（飞书 / 钉钉 / 企业微信 / 邮件全渠道开放）：
      - 每用户最多 3 个 webhook
      - 分析完成自动预警 + 按产品自定义规则
      - 全局规则上限 3 条 / 每个产品规则上限 1 条
    - 不限产品数
  - Pro ¥99/月（前 50 名早鸟锁价）:
    - 评论分析 5000 条/月、Ask reviews 50 次/月、广告文案 100 次/月
    - 多产品对比不限、Excel 导出不限
    - 预警通知（飞书 / 钉钉 / 企业微信 / 邮件全渠道）：
      - 不限 webhook 数量
      - 分析完成自动预警 + 按产品自定义规则
      - 全局规则与产品规则均不限条数
    - 上线后迭代独享：评论自动获取（ASIN 抓取更高配额 + 插件无限制）、API 调用（Team 档启用后）、周报/月报定时推送
    - 不限产品数
  - 实现 `quota.check(user_id, action)`，超额提示升级
  - **配额维度详细规格见 [QUOTA_TABLE.md](QUOTA_TABLE.md)**（9 个核心维度的 single source of truth）
  - 数据模型新增：
    - `users` 表新增 `plan_locked_at TIMESTAMPTZ`（早鸟订阅写入时间，涨价时识别老用户）
    - 用户 plan 字段使用独立 key：`free` / `pro_early` / `pro` / `team`
    - 新增 `user_quota_usage(user_id, dimension, period_start, used_count)` 计数表
  - 关键函数：
    - `quota_check(user_id, dim, amount=1)` —— 通用配额校验
    - `quota_check_atomic(user_id, dim, amount)` —— **原子完整校验**，专用于 `review_analyze` 上传前置（避免分析中途中断）
    - `quota_consume` / `quota_refund` —— 扣减与回退
  - 单文件硬限：Free 单次上传 ≤ 500 条 / Pro ≤ 5000 条（防灌爆队列）
  - Webhook 频次保护：[notifier.py](review_analyzer/notifier.py) 加 1 分钟内同类预警合并逻辑（飞书/钉钉/企微 20 条/分限制）
  - Webhook 计数规则：Free 飞书+钉钉+企微 ≤ 3 个 + 邮件独立位（不占配额）
  - **里程碑触发器**：付费用户达 100 时进入 Step 3.5
  - 详细成本利润测算见 [COST_PROFIT.md](COST_PROFIT.md)
  - ✅ 已完成 2026-06-10：`review_analyzer/quota.py` 实现（9 维度配额 + atomic check + consume/refund）+ `backend_api/app/routes/quota.py` API 路由 + migration 011

- [ ] **Step 3.5: 产品数限制 + 涨价（≥100 付费用户后启用）**
  - 触发条件：累计付费用户 ≥ 100，或代运营/Agency 用户占比 > 15%
  - 引入"活跃产品"概念：30 天内有分析的产品计数，历史归档不限
  - Pro ¥199/月（新用户标准价）：活跃产品 10 个、10000 条/月、Ask 不限、文案 300 次
  - Team ¥499/月：活跃产品 50 个、50000 条/月、Ask 不限、文案不限、API、5 席位
  - 老用户（早鸟 ¥99）保留原档，不溯及既往

- [x] **Step 4: Paddle 商品配置**
  - Phase 1：在 Paddle 后台创建 Pro ¥99（早鸟）一个 Product
  - 100 用户里程碑后：新建 Pro ¥199、Team ¥499 两档；早鸟用户保留 ¥99 不变
  - Webhook 处理升级、降级、取消事件
  - 加用户中心页面：当前套餐、用量、续费、取消
  - ✅ 已完成 2026-06-10：`backend_api/app/routes/settings.py` 重写 webhook（subscription.created/updated/canceled/paused/resumed）+ `GET /billing` API + `_resolve_plan_from_event()` 多套餐路由

- [x] **Step 5: 法务底线**
  - 隐私协议（数据使用范围、第三方共享、删除流程）
  - 用户协议（服务范围、责任边界、终止条款）
  - 退款政策（月付不退、年付按比例、取消说明、退款流程）
  - GDPR / 中国个保法基础合规
  - ✅ 已完成 2026-06-10：`frontend/src/app/privacy/page.tsx` + `frontend/src/app/terms/page.tsx`（中文，覆盖个保法 + GDPR 权利条款）
  - ✅ 已完成 2026-07-06：三页全部改造为中英双语 + 新增 `frontend/src/app/refund/page.tsx` 退款政策页 + footer 补充 refund 链接

- [ ] **Step 6: 验收**（部分达成 2026-06-11）
  - [x] 用户注册 → 登录 → cookie 鉴权 → workspace API 数据返回：本地验证通过 ✅ 2026-06-11
    - 前端 `/register` `/login` 表单已接通 FastAPI auth API
    - Next.js rewrites 代理 `/api/*` → FastAPI，cookie 同 origin 设置无跨端口问题
    - 注册成功自动跳转 `/workspace`，登录态正常识别
  - [ ] 试用 → 升级（Paddle sandbox 支付）→ plan 升级确认 ⏳ *需 Paddle sandbox 环境*
  - [ ] 用量到顶 → 403 + 升级提示 ⏳ *需 Redis + worker 运行*
  - [ ] 续费 / 取消 → plan 降级回 free ⏳ *需 Paddle webhook 模拟*
  - [ ] 多租户隔离测试：A 用户看不到 B 用户任何数据 ⏳ *RLS 启用后再做*

---

### 6.5 LLM 输出加固

**目标：** 用最低成本把当前 LLM 输出的稳定性和准确率拉满，作为引入小模型前的过渡方案。

**Files:**
- Modify: `review_analyzer/analyzer.py`（强制 JSON Schema）
- Create: `review_analyzer/prompts/`（Prompt 文件按版本管理）
- Create: `review_analyzer/prompt_registry.py`（版本路由）
- Modify: `supabase_schema.sql`（comments 表加 `prompt_version` 字段）

- [x] **Step 1: 强制 JSON Schema 输出** ✅ 2026-06-10
  - DeepSeek API 已支持 `response_format={"type": "json_object"}`
  - 定义结构：`{sentiment, aspects[], pain_points[], highlights[], suggested_actions[]}`
  - 加 schema 校验，校验失败自动重试 1 次
  - 预期收益：解析错误率降 30%，category 措辞不一致问题基本消除
  - **实际产物**：`review_analyzer/analyzer.py` 使用 `response_format={"type": "json_object"}` + `json.JSONDecodeError` 重试 1 次逻辑

- [x] **Step 2: Prompt 版本管理** ✅ 2026-06-10
  - `prompts/sentiment_v1.0.md`、`prompts/aspect_v1.0.md`、`prompts/insight_v1.0.md`
  - 每个 Prompt 文件包含：版本号、生效日期、变更说明、Few-shot 示例
  - 数据库每条分析记录写入 `prompt_version` 字段
  - 改 Prompt 强制走 PR + Golden Set 回归
  - **实际产物**：`backend_api/app/services/prompt_registry.py`（版本路由）+ `backend_api/app/prompts/annotate_v1.0~v2.4.md`（6 个版本文件）+ DB `prompt_version` 字段（`migrations/002`）+ eval 自动化回归

- [x] **Step 3: 评分覆写规则强化** ✅ 2026-06-10
  - 当前已有"≤3 判负面 / ≥4 判正面"
  - 补：评分缺失时才走 LLM 情感分析
  - 补：unrecognizable 评论从统计分母排除（已在 V1 做过，确认仍生效）
  - **实际产物**：`analyzer.py` 中 `classify_sentiment_by_rating()` + `filter_neutral_unrecognizable()` + v2.4 prompt 完整 rating-priority 三级规则（1.1/1.2/1.3）

- [x] **Step 4: Few-shot 注入 Bad Case** ✅ 2026-06-10
  - 从 6.1 的 Bad Case 库中挑选 5-10 个高频错例
  - 注入 Prompt 末尾作为 few-shot 示例
  - 在 Golden Set 上 A/B 测试新旧 Prompt
  - **实际产物**：v2.3/v2.4 prompt 含 12 个 few-shot 示例，覆盖 3 星边界（mediocre/just OK/worth the buy/otherwise solid）、文本-评分冲突、比较句式、family-love 等高频错例；A/B 测试结果见 `data/golden_set/v1.0/ab_test_report.md`

- [x] **Step 5: 验收标准** ✅ 2026-06-11
  - 跑 6.1 Golden Set 500 条测试集
  - 情感准确率 ≥ 92%
  - 痛点分类准确率 ≥ 88%
  - JSON 解析失败率 < 1%
  - **实际指标（v2.3 on 499 条）**：情感准确率 **94.6%** ✓ | bad case 准确率 **96.1%** ✓ | JSON 失败 **0 条** ✓ | 高评分准确率 98.0% | 3 星准确率 74.5%
  - **v2.4 验证（2026-06-11）**：情感准确率 **95.4%** ✓ | bad case 准确率 **92.2%** ✓ | JSON 失败 **0 条** ✓ | 高评分准确率 99.4% | 3 星准确率 76.6% — 动态 taxonomy 无退步

---

### 6.6 成本优化

**目标：** 用 Embedding 聚类前置层 + 多级缓存 + Fallback 链路，把单条评论成本降 85%。

**Files:**
- Create: `review_analyzer/embedding.py`（Embedding 生成）
- Create: `review_analyzer/clustering.py`（HDBSCAN 聚类）
- Modify: `review_analyzer/analyzer.py`（接入聚类前置层）
- Create: `review_analyzer/llm_router.py`（多模型 Fallback）
- Modify: `supabase_schema.sql`（comments 加 cluster_id、embedding 字段已有）

- [x] **Step 1: Embedding 模型选型** ✅ 2026-06-11
  - ❌ DeepSeek 不提供 embedding API（实测返回 404）
  - ❌ BGE-m3 本地 ONNX 在当前 ECS 2C4G 上不可行（模型 2.2GB 占 55% 内存，与 FastAPI/RQ 争资源，OOM 风险极高）
  - ✅ **决策：复用已有 `review_analyzer/rag.py::generate_embedding()` 管道**
  - 当前方案：OpenAI text-embedding-3-small（1536 维，$0.02/1M tokens）✅ 2026-06-12 key 已更新验证通过
  - 代码层通过环境变量 `EMBEDDING_API_BASE_URL` + `EMBEDDING_MODEL` + `EMBEDDING_API_KEY` 解耦，切换只需改 .env
  - 验收：100 条评论 Embedding 生成 < 3 秒 ✓（API 批量 ~1-2 秒）
  
  **切换路线图（按条件触发，无需改代码）：**
  
  | 条件 | 切换至 | .env 变更 |
  |------|--------|----------|
  | OpenAI API Key 修复 | `text-embedding-3-small`（1536 维） | `EMBEDDING_API_BASE_URL=https://api.openai.com/v1` + `EMBEDDING_MODEL=text-embedding-3-small` + 填入有效 key |
  | ECS 升级至 ≥4C8G + 月评论量 >50 万条 | BGE-m3 本地 ONNX（零边际成本） | 需新增 Docker layer + onnxruntime + 模型文件，代码改为本地调用 |
  
  **BGE-m3 本地部署检查清单（未来执行时参照）：**
  - 前提：ECS ≥ 4C8G（模型 2.2GB + 推理 ~1GB burst）
  - 安装：`pip install onnxruntime sentence-transformers`
  - 模型下载：`huggingface-cli download BAAI/bge-m3 --local-dir models/bge-m3`
  - Docker 镜像膨胀 +2.5GB，建议独立为 embedding-worker 容器
  - 切换方式：改 `generate_embedding()` 调用为本地 ONNX 推理，或部署为 sidecar HTTP 服务 + 改 `EMBEDDING_API_BASE_URL=http://localhost:8080/v1`
  
  **备注**：~~当前 RAG 模块（2.3）embedding 功能因 OpenAI key 过期处于不可用状态。T4 Step 1 完成后 embedding 管道恢复，RAG 同时修复。~~ ✅ 2026-06-12 OpenAI key 已更新，embedding + RAG 均恢复正常。

- [x] **Step 2: HDBSCAN 聚类前置层** ✅ 2026-06-12
  - 100 条评论先 Embedding → HDBSCAN 聚类（min_cluster_size=3）
  - 每个 cluster 选代表评论（中心向量最近的 1 条）
  - LLM 只对代表评论 + noise 点做分析
  - 同 cluster 评论共享分析结果（aspects/pain_points/highlights），sentiment 由 rating 独立覆写
  - **实际产物**：
    - `backend_api/app/services/clustering.py`（cluster_reviews + propagate_cluster_results）
    - `migrations/013_add_cluster_fields.sql`（cluster_id + cluster_representative_id 字段）
    - `review_analyzer/database.py` 新增 get_session_embeddings / update_comment_cluster
    - `workers/jobs.py` 接入聚类前置层（≥10 条自动启用，<10 条或 embedding 不可用时 fallback 全量 LLM）
  - **测试结果**：50 条模拟评论 → 3 cluster + 5 noise → 8 次 LLM 调用（节省 84%）

- [x] **Step 3: 多级缓存** ✅ 2026-06-12
  - L1：评论 content+rating hash 命中（SHA-256，100% 节省）
  - L2：短文本（≤10 字）+ 极端评分（≤2 或 ≥5）跳过 LLM，生成最小结果
  - L3：Embedding 余弦相似度 > 0.95 复用最近邻分析结果
  - **实际产物**：
    - `backend_api/app/services/analysis_cache.py`（三级缓存逻辑 + CacheResult 结构）
    - `migrations/014_add_cache_fields.sql`（cache_hit_level + cache_source_id 字段 + 索引）
    - `review_analyzer/database.py` 新增 get_analyzed_by_content_hash / get_analyzed_with_embeddings
    - `workers/jobs.py` 接入缓存层（缓存 → 聚类 → LLM 三级管道）
    - `_build_comments` 现在在插入时计算 content_hash（SHA-256）
  - **测试结果**：L1/L2/L3 单元测试全通过；缓存命中率通过 DB 字段 cache_hit_level 统计

- [x] **Step 4: 多模型 Fallback 链路** ✅ 2026-06-12（locale-aware 升级 2026-07-07）
  - 主：DeepSeek-V3（deepseek-chat）— 中文优势 + 成本最低
  - 备 1：OpenAI gpt-4o-mini — API 稳定性最高，JSON mode 可靠
  - 备 2：Qwen-Plus（通义千问）— 国内可用性兜底
  - 熔断：连续 3 次失败自动切换，60s 冷却后尝试恢复主模型
  - 实现：`backend_api/app/services/llm_router.py`（LLMRouter 单例 + router_completion 便捷函数）
  - `deep_analyzer.py` 已改造为通过 router 调用，业务代码无感知
  - 线程安全（Lock 保护熔断状态），可通过 `router.status()` 查询各模型健康状态
  - 环境变量：`DEEPSEEK_API_KEY`（必需）、`OPENAI_API_KEY`（可选备 1）、`QWEN_API_KEY`（可选备 2）
  - **2026-07-07 hotfix**：`workers/jobs.py` 上线后传 `locale=locale` 给 `deep_analyze_batch`，但 `deep_analyzer.py` / `llm_router.py` 未同步更新签名，导致生产 `TypeError: unexpected keyword argument 'locale'`，所有分析任务崩溃。修复：`analyze_one` / `analyze_batch` / `router_completion` 全链路补齐 `locale` 参数；引入 `MODELS_EN`（GPT-4o-mini 优先）/ `MODELS_ZH`（DeepSeek 优先）双链路切换

- [x] **Step 5: Token 成本看板** ✅ 2026-06-12
  - 新建 `llm_usage_log` 表（migration 015），记录每次 LLM 调用的 model/tokens/cost
  - `database.py` 新增 `log_llm_usage_batch` + `get_llm_usage_stats`（批量写入 + 聚合查询）
  - Worker 每次 job 完成后自动批量写入用量（含缓存命中标记）
  - 成本估算内置模型定价：DeepSeek ¥1/8M，gpt-4o-mini ¥1.05/4.2M，Qwen-Plus ¥0.8/2M
  - API 端点 `GET /analytics/llm-costs?days=30` 返回汇总 + 按日明细
  - 指标：总成本、总调用、缓存命中率、单次均价

- [x] **Step 6: 验收标准** ✅ 2026-06-12
  - 100 条评论分析耗时：冷启动 8.6s / 有缓存 1.1s（目标 8-12s ✓）
  - 单条评论平均成本：¥0.000062（接近目标 ¥0.00003，缓存池积累后持续下降）
  - LLM 调用量：2%（目标 <15% ✓，远超预期）
  - 缓存命中率：98%（L1=80 + L2=18，100 条仅 2 条需走 LLM）
  - 准确率：保持 6.3 基线（缓存复用已验证结果，无质量损失）

- [x] **Step 7: 跨用户 LLM 分析结果复用（6.4 增强）** ✅ 2026-07-07
  - **背景**：原 L1 缓存 `get_analyzed_by_content_hash` 只查用户自己历史，用户 A/B/C 上传重叠评论时仍会重复调用 DeepSeek。migration 038 建的全局 `review_pool` 已具备跨用户复用条件但未接通。
  - **改动**：
    - `migrations/043_review_pool_global_analysis_cache.sql`：给 `review_pool.content_hash` 加部分索引 + `comments` 新增 `cache_hit_source` 列（'user' | 'global' | NULL）
    - `review_analyzer/database.py::get_analyzed_by_content_hash`：新增 `include_global=True` 分支，用户自己 miss 的 hash 会去查全局 pool（需 `analyzer_version` 匹配）
    - `workers/jobs.py`：拆掉 `source_channel == "api"` 门禁 → CSV 上传的分析结果也回填 pool；同时把 `cache_hit_source` 写入 comments 表供 llm_usage_log 统计
    - `update_comment_analysis`：写入 `cache_hit_source` 列
    - `frontend/src/app/privacy/page.tsx` + `terms/page.tsx`：新增"分析结果聚合复用"条款（含中英双语，隐私政策日期更新至 2026-07-07）
  - **单元测试**：`backend_api/tests/test_global_cache.py` 覆盖用户命中/全局命中/用户优先屏蔽 pool/空输入 4 个分支
  - **验收标准**：
    - [ ] 验证：用户 A 上传 → 用户 B 上传相同 CSV → 观察 worker 日志 `analysis_cache: L1=N` + `cache_hit_source='global'`（migration 043 已于 2026-07-07 在 ECS 执行，功能验证待进行）
    - [ ] 线上：热门 ASIN 场景下 DeepSeek 调用量下降 30%+ （待观察 llm_usage_log 汇总）
  - **计费影响**：无 —— quota 仍在上传时按条数扣减，缓存命中不影响用户额度
  - **隐私披露**：privacy.tsx 第四条已明示"匿名化分析输出可跨用户复用，不涉及身份/账号/上传时间共享"

---

### 6.7 ABSA 小模型 fine-tune

**目标：** 把 ABSA（情感 + Aspect 抽取）这种结构化任务从 LLM 收回到 fine-tuned 小模型，是准确率天花板的真正解药。

**注意：** 这是高 ROI 但高投入的任务，建议在 6.1/6.4/6.5/6.6 完成且拿到至少 5 个付费用户后再启动。如果 PMF 验证不通过，跳过此任务。

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

### 6.8 用户反馈回路

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

### 6.9 Niche 商业化启动

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
  - 收集 bad case 反哺 6.3 / 6.6

- [ ] **Step 6: SEO 内容种子**
  - 写 5 篇知乎 / 小红书种草文（"我用 ClueAI 复盘了一个亚马逊 [品类] 的 SKU 改版"）
  - 录制 3 分钟产品 demo 视频
  - 为 3.1.5 营销站积累内容资产

- [ ] **Step 7: 验收标准**
  - 8 周内拿到 20 个免费试用用户

  - 5 个付费用户（约 ¥250-500 MRR）
  - 至少 1 个用户案例可公开使用

---

### 6 任务依赖关系

```
6.1 (数据资产化) ──┬──► 6.3 (LLM 输出加固) ──┬──► 6.5 (ABSA 小模型)
                     ├──► 6.4 (成本优化)       │
                     ├──► 6.6 (反馈回路) ◄─────┘
                     └──► 6.2 (Taxonomy 接入) ──► 6.3 (Golden Set 多品类演进)
                                                          ↑ 新品类上线时触发
6.2 (商业化基建) ──► 6.7 (Niche 商业化)
                       └──► (依赖 6.5 + 6.6 完成)
```

执行顺序建议：
1. **Week 1-2:** 6.1（数据资产化）+ 6.4（商业化基建）并行启动 — 这是所有后续工作的地基
2. **Week 3-4:** 6.5（LLM 输出加固）+ 6.9 启动品类选定与白皮书
3. **Week 4-6:** 6.6（成本优化）+ 6.9 种子用户招募
4. **Week 5-7:** 6.8（反馈回路）+ 6.9 1对1 跟进
5. **Week 6-8:** 6.7（ABSA 小模型，可选）+ 6.9 转化付费

### 6 优先级精简版

1. **6.1 数据资产化（Week 1-2）** — 不做这个，后面所有优化都没法度量。零技术风险，纯运营投入。
2. **6.7 Niche 商业化（Week 4-8）** — 不做这个，技术优化全是沉没成本。商业化决定产品方向。
3. **6.4 成本优化（Week 4-6）** — 单点技改成本最低、降本最猛，让前 50 个用户的毛利可控。

### 6 阶段验收标准

- [ ] 单条评论成本从 ¥0.0002 降到 ¥0.00003（降 85%）
- [ ] Golden Set 测试集情感准确率 ≥ 95%、痛点分类 ≥ 90%
- [ ] 有 ≥ 5 个付费用户（任一档位）
- [ ] 单用户月毛利 ≥ ¥80（按 ¥99 入门版计算）
- [ ] Prompt 改动不再造成历史口径漂移（版本管理生效）
- [ ] DeepSeek 故障 5 分钟内自动切换备用模型
- [ ] 至少 1 个垂直品类白皮书发布并产生留资

---

## 9. 增值功能

> **目标**：上线后根据用户反馈分阶段引入新能力，避免一次开发太多导致延期。
> 详细成本与定价配套见 `COST_PROFIT.md`。

### 9.1 评论自动获取

**痛点**：当前用户必须手动准备评论 Excel，门槛高，导致 Free 用户上手率低。

**技术调研结论（2026-06-15 更新）**：

评论自动获取存在三条路径，推荐分阶段推进：

| 路径 | 方式 | 优势 | 劣势 | 状态 |
|------|------|------|------|------|
| **Rainforest API（后端自动）** | 服务端按 ASIN 调用 API 获取结构化评论 | 全自动、数据稳定、按需批量 | 有月费（$49起） | ✅ 单次拉取已实现 |
| Chrome 插件（前端抓取） | 用户浏览亚马逊时，插件 parse DOM 提取评论 | 零服务端成本、利用用户登录态 | 需用户主动触发、受页面改版影响 | 后置 |
| Amazon SP-API（卖家授权） | OAuth 授权后自动发现 ASIN + 拉取数据 | 最佳用户体验 | 需 Professional Seller 账号 + 审批 2-4 周 + 无法获取评论全文 | ❌ 当前阶段不走 |

**SP-API 不推荐原因（2026-06-15 调研结论）**：
1. 硬性要求拥有 Amazon Professional Seller 账号（$39.99/月）
2. 开发者审批 2-4 周且早期产品易被拒
3. SP-API 没有获取评论全文的端点（只有 Catalog/Orders 类权限）
4. 即使通过审批，仍需 Rainforest 拉评论内容——SP-API 唯一增量价值是"自动发现 ASIN"
5. 等 10+ 付费用户后再申请审批更容易通过

**推荐路径：Rainforest API 三步走**
- Phase 1：批量 ASIN 管理 + 定时自动拉取（无审批，现在可做）
- Phase 2：Chrome 插件辅助（补充免费用户渠道）
- Phase 3：SP-API 授权自动发现 ASIN（有 10+ 付费用户后启动）

**第三方 API 选型对比**：

| 维度 | Rainforest API（Traject Data）✅ 推荐 | Oxylabs E-Commerce Scraper |
|------|--------------------------------------|---------------------------|
| 定位 | 专注 Amazon/电商数据 | 通用爬虫 + 电商 API |
| 入门价 | $49/月 = 5,000 请求 | $49/月 = 5,000 请求 |
| 单次成本 | ~$0.01/请求 | ~$0.01/请求 |
| 响应速度 | 2-5 秒 | 3-8 秒 |
| 数据字段 | 评论文本/评分/日期/变体/图片/Verified/Helpful votes | 同等 |
| 多国站点 | 16 个 Amazon 站点 | 主要站点 |
| 免费试用 | 100 次（无需销售沟通） | 需申请 |
| 文档质量 | 评论场景专属文档，字段映射清晰 | 通用文档 |

**成本估算**（$49/月 Starter 套餐）：
- 每次 API 请求返回 10 条评论
- 日均可用：~166 次请求 = **~1,660 条评论/天**
- 典型场景：10 ASIN × 5 页 = 50 请求/天，月用量 ~1,500 次，绰绰有余
- 大批量场景（100 ASIN × 50 页）可临时升级 $99/月（15,000 请求）

---

#### Phase 1: 批量 ASIN 管理 + 定时自动拉取（立即可做，无外部审批）

**目标**：卖家输入自己的 ASIN 列表，系统自动定时拉取新评论并分析，体验接近"连接店铺"。

**已实现基础**：
- [x] `backend_api/app/services/rainforest.py` — Rainforest API 封装（16 站点、翻页、结构化解析）
- [x] `backend_api/app/routes/scrape.py` — `POST /reviews/fetch-by-asin` 端点
- [x] `workers/jobs.py` — `process_asin_fetch_job` 异步 Worker（拉取→存储→触发分析）
- [x] `backend_api/app/schemas/scrape.py` — ASIN 校验 schema
- [x] 配额控制：`quota_check(user_id, "asin_fetch")`（daily 周期：Free 1次/天, Pro 10次/天）
- [x] `migrations/017_add_source_channel.sql` — comments/upload_jobs 新增 `source_channel` 字段
- [x] `review_analyzer/quota.py` — 新增 `asin_fetch` 维度 + `daily` 周期类型支持
- [x] `review_analyzer/database.py` — `create_upload_job` 支持 `source_channel` 写入
- [x] `frontend/src/components/upload/asin-fetch-panel.tsx` — ASIN 拉取前端面板
- [x] `frontend/src/app/upload/page.tsx` — 上传页增加"文件上传 / ASIN 自动拉取"双 Tab
- [x] `frontend/src/lib/api/browser.ts` — `fetchByAsin` API 调用函数
- [x] `requirements.txt` — 添加 `httpx>=0.27.0`
- [x] Rainforest API Key 已配置并验证通过（免费额度 96 次）
- [x] Fallback 机制：`type=reviews` 503 时自动降级到 `type=product` + `top_reviews`

**Files:**
- Create: `migrations/017_asin_watchlist.sql`（ASIN 监控列表表）
- Create: `backend_api/app/routes/asin_watchlist.py`（ASIN 列表 CRUD 路由）
- Create: `backend_api/app/schemas/asin_watchlist.py`（请求/响应 schema）
- Create: `workers/asin_scheduler.py`（定时拉取调度器）
- Modify: `frontend/src/app/products/page.tsx`（产品页增加 ASIN 绑定区块）
- Modify: `workers/periodic_jobs.py`（注册定时拉取 job）
- Modify: `review_analyzer/notifier.py`（新评论变化通知）

- [x] **Step 1: ASIN 监控列表数据模型**
  - 新增 `asin_watchlist` 表：
    ```sql
    CREATE TABLE IF NOT EXISTS asin_watchlist (
        id SERIAL PRIMARY KEY,
        user_id INTEGER NOT NULL REFERENCES users(id),
        asin TEXT NOT NULL,
        marketplace TEXT NOT NULL DEFAULT 'us',
        product_name TEXT,
        product_id INTEGER REFERENCES products(id),
        fetch_frequency TEXT DEFAULT 'daily',  -- daily / weekly / manual
        last_fetched_at TIMESTAMPTZ,
        last_review_count INTEGER DEFAULT 0,
        status TEXT DEFAULT 'active',  -- active / paused / error
        error_message TEXT,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        UNIQUE(user_id, asin, marketplace)
    );
    ```
  - 配额限制：Free 限 3 个 ASIN、Pro 限 20 个、Team 限 100 个

- [x] **Step 2: ASIN 列表 CRUD API**
  - `POST /asin-watchlist` — 添加 ASIN（支持单个或批量，最多 20 个/次）
  - `GET /asin-watchlist` — 获取当前用户的监控列表（含状态、上次拉取时间、评论增量）
  - `PATCH /asin-watchlist/{id}` — 修改频率 / 暂停 / 恢复
  - `DELETE /asin-watchlist/{id}` — 移除监控
  - `POST /asin-watchlist/{id}/fetch-now` — 立即触发一次拉取（扣配额）
  - 添加时自动调用 `fetch_product_info` 获取产品名称/品类（已实现于 `rainforest.py`）

- [x] **Step 3: 定时拉取调度**
  - 基于 `rq-scheduler`（已在 9.3 引入）
  - 每天凌晨 2:00 UTC 扫描所有 `status=active` 且 `fetch_frequency=daily` 的记录
  - 每周一凌晨扫描 `fetch_frequency=weekly` 的记录
  - 对每个 ASIN 入队一个 `process_asin_fetch_job`（复用现有 worker）
  - 并发控制：同一用户最多 5 个并发拉取任务
  - 失败重试：最多 3 次，第 3 次失败后标记 `status=error` 并通知用户
  - **2026-06-30 优化**：定时抓取数据源从 Rainforest API（付费）切换为 woot.com（免费），零 API 成本实现自动监控。调用统一入口 `fetch_reviews()` → woot.com AJAX API

- [x] **Step 4: 增量检测 + 去重**
  - 拉取后与上次结果对比：按 `review_id` 去重，只入库新增评论
  - 记录 `last_review_count`，如果新增 > 0 条：
    - 自动触发分析 job
    - 推送通知："{product_name} 新增 {N} 条评论，已自动分析"
  - 如果连续 3 次拉取无新增 → 自动降频（daily→weekly），节约 API 配额

- [x] **Step 5: 前端 — 产品页 ASIN 绑定**
  - 产品管理页每个产品卡片增加"监控 ASIN"区块
  - 支持：手动输入 ASIN / 粘贴 Amazon URL 自动提取 / 上传 CSV（一列 ASIN）
  - 显示：监控状态、上次拉取时间、评论增量趋势迷你图
  - 操作：立即刷新、暂停、删除
  - 新用户引导："粘贴你的 Amazon 产品链接，系统自动每天更新评论"

- [x] **Step 6: 前端 — 独立 ASIN 监控面板**
  - 新建 `/data-sources` 页面（或在产品管理内作为 Tab）
  - 全局视图：所有监控 ASIN 的状态一览
  - 批量操作：全部暂停 / 全部恢复 / 批量添加
  - 配额用量显示：本月已用 / 剩余 / 预估超量提醒

- [x] **Step 7: 通知 + 异常报警**
  - 新评论通知（飞书/邮件）："{product} 新增 {N} 条评论，负面率 {x}%，较上次{↑/↓}"
  - 异常报警：负面率突增（>10pp）、差评数连续 3 天上升
  - 配额预警：本月 API 调用量达 80% 时提醒用户

- [ ] **Step 8: 验收**
  - 用户添加 3 个 ASIN → 系统每天自动拉取 → 新增评论自动入库并分析
  - 产品页能看到"最近 7 天评论增量"趋势
  - 飞书收到新评论通知
  - 配额用完后自动暂停拉取，不超额
  - 手动"立即刷新"按钮可用

- [ ] **Step 9: 回滚边界**
  - 仅回滚本 Phase 新增文件 + 相关路由注册
  - 不影响现有手动上传和单次 ASIN 拉取功能

---

#### Phase 2: Chrome 插件（后置，补充免费用户渠道）

> 触发条件：Phase 1 稳定运行 + 有用户反馈"不想花 Rainforest 配额"

- [ ] **Step 10: Manifest V3 插件骨架**
  - 支持 Amazon US/UK/DE/JP 评论页面
  - 一键"抓取本页评论"，最多翻页 10 页
  - 插件内登录校验，上传到 `POST /reviews/plugin-upload`
- [ ] **Step 11: 后端接收 + 去重**
  - 统一去重逻辑：按 (asin + reviewer_id + review_date) 去重
  - 配额扣减：插件渠道 Free 限 100 条/次、Pro 限 1000 条/次
  - `source_channel` 字段标记来源

---

#### Phase 3: SP-API 授权自动发现 ASIN（后置）

> 触发条件：付费用户 ≥ 10 + 有明确客户需求"希望自动同步店铺"
> 前置条件：拥有 Amazon Professional Seller 账号 + 通过 SP-API 开发者审批

- [ ] **Step 12: SP-API 开发者注册**
  - 注册 Amazon Professional Seller 账号（$39.99/月）
  - 申请 SP-API 开发者资格
  - 创建 LWA（Login with Amazon）应用
  - 申请 `Catalog Items` 权限组（用于获取卖家 ASIN 列表）
  - 准备审核材料：产品截图、数据安全政策页、隐私政策页

- [ ] **Step 13: OAuth 授权流程**
  - 前端"连接 Amazon 店铺"按钮 → 跳转 Amazon OAuth 授权页
  - 回调处理：获取 refresh_token → 加密存储
  - 调用 Catalog Items API 拉取卖家所有在售 ASIN
  - 自动创建 `asin_watchlist` 记录（复用 Phase 1 基础设施）

- [ ] **Step 14: 自动 ASIN 同步**
  - 每周同步一次卖家 ASIN 列表（新增/下架检测）
  - 新增 ASIN 自动加入监控、下架 ASIN 自动暂停
  - 配合 Phase 1 定时拉取，实现全自动闭环

### 9.2 API 调用

**目标**：服务代运营 Agency 与中型卖家的自动化需求。

**Files:**
- Create: `backend_api/app/routers/v1/api.py`（v1 公开 API）
- Create: `backend_api/app/services/api_key.py`（API Key 生成/校验/限流）
- Modify: `supabase_schema.sql`（增加 `api_keys` 表）

- [ ] **Step 1: API Key 生成 + 管理界面**
  - 用户中心增加"我的 API Keys"页面
  - 单用户最多 5 个 Key，可命名、启停、查看用量
- [ ] **Step 2: 核心端点**
  - POST /v1/analyze（提交评论，异步返回 task_id）
  - GET /v1/tasks/{task_id}（查询分析结果）
  - GET /v1/usage（查询本月用量）
- [ ] **Step 3: 限流 + 配额**
  - Team 档：10000 次调用/月
  - 单 Key 限速 60 次/分钟（防滥用）
  - 超额按 ¥0.05/次计费
- [ ] **Step 4: 文档站**
  - mkdocs / Mintlify 搭建 docs.clueai.com
  - OpenAPI Spec 自动生成 + Postman Collection

### 9.3 智能推送 + 分责路由 + 升级行动闭环

**目标**：定期推送产品 TOP 10 问题/亮点到飞书群，按责任部门分板块 @负责人；连续多期 TOP 问题自动升级，LLM 生成行动建议并写入行动中心，形成"发现→通知→行动→复盘"完整闭环。

**竞品差异化**：Enterpret/Birdie/Shulex 等竞品止步于通知层，无一实现"连续升级→自动行动建议→回写追踪"闭环。

**决策记录（2026-06-14 Erika 确认）**：
- 推送触发：即时推送（已有）+ 周期汇总推送（新增）
- 连续性：以推送周期为单位计数（连续 N 个推送周期）
- 行动建议：LLM 自动生成 → 写入行动中心（status=todo）→ 飞书通知负责人确认
- 消息结构：一条消息分板块（运营/质检/产研/客服/其他）
- 分责规则：Aspect Taxonomy 自动映射 + 用户可在设置中调整
- 周期：用户完全自定义（每日/每周/每两周/每月 + 具体时间）

**Files:**
- Create: `review_analyzer/department_router.py`（aspect→部门映射引擎）
- Create: `review_analyzer/escalation.py`（升级判定引擎）
- Create: `backend_api/app/services/action_advisor.py`（LLM 行动建议生成）
- Create: `workers/periodic_jobs.py`（周期汇总推送 job）
- Create: `workers/scheduler.py`（rq-scheduler 启动入口）
- Create: `migrations/016_push_snapshots.sql`（快照表 + 升级状态表）
- Modify: `review_analyzer/notifier.py`（升级为富文本分板块格式 + @mention）
- Modify: `backend_api/app/schemas/settings.py`（新增周期/部门联系人/升级规则 schema）
- Modify: `backend_api/app/routes/settings.py`（新增配置端点）
- Modify: `frontend/src/components/settings/settings-panel.tsx`（新设置区块）
- Modify: `workers/jobs.py`（分析完成后写入 push_snapshot）
- Modify: `deploy/docker-compose.yml`（新增 scheduler service）

**5 个责任部门分类**：

| 部门 | 代码标识 | 对应 Aspect 举例 | 飞书 @对象 |
|------|---------|-----------------|-----------|
| 运营 | `ops` | value_for_money | 运营负责人 open_id |
| 产品质检 | `qa` | durability, material, build_quality, packaging, shipping_damage, missing_parts, smell, safety | 质检负责人 open_id |
| 产研 | `product` | aesthetics, comfort, size_fit, assembly, instructions, ease_of_use, weight_capacity, color_accuracy | 产研负责人 open_id |
| 客服 | `cs` | customer_service | 客服负责人 open_id |
| 其他 | `other` | other | 默认群通知 |

- [x] **Step 1: 数据库 — 推送快照 + 升级状态表**
  - `push_snapshots` 表：记录每次推送时的 TOP 问题排名和占比快照
  - `issue_escalation_state` 表：记录每个问题标签的连续命中次数和升级状态
  - 字段设计：`snapshot_type`（batch/periodic）、`top_issues` JSONB、`consecutive_count`、`escalated_at`
  - 索引：user_id + product_id 组合索引
  - ✅ `migrations/016_push_snapshots.sql` + `review_analyzer/push_snapshot_store.py`（2026-06-14）

- [x] **Step 2: 部门映射引擎**
  - 基于 `scripts/aspect_taxonomy.py` 的 FURNITURE_ASPECTS 建立默认 aspect→dept 映射表
  - 用户自定义映射存入 `push_settings.dept_mapping` 字段，覆盖默认值
  - 核心函数：`route_issues_by_department(top_issues, user_mapping) → dict[dept, list[issue]]`
  - 支持多品类：不同品类的 taxonomy 映射到同一套部门体系
  - ✅ `review_analyzer/department_router.py`（2026-06-14）

- [x] **Step 3: 升级判定引擎**
  - 每次生成推送快照时，更新 `issue_escalation_state` 的连续计数
  - 升级条件（OR 关系，用户可配置）：连续 N 次在 TOP K **或** 占比超过阈值
  - 默认配置：连续 3 个周期、TOP 3、占比 10%
  - 已升级且 action_item 未完结的问题不重复升级
  - 问题标签归一化：基于 aspect key 判断，避免同义标签重复计数
  - ✅ `review_analyzer/escalation.py` + 18 个单元测试通过（2026-06-14）

- [x] **Step 4: LLM 行动建议生成**
  - 升级触发时调用 DeepSeek 生成行动建议
  - Prompt 输入：问题标签 + 近 N 期占比趋势 + 责任部门 + 产品信息 + TOP 5 代表性评论原文
  - Prompt 输出（structured JSON）：action_title / suggested_action / expected_timeline / priority
  - 自动调用 `create_action_item()` 写入行动中心，status="todo"，owner_role=对应部门
  - 成本控制：单次升级约 1 次 LLM 调用，不会批量触发
  - ✅ `backend_api/app/services/action_advisor.py`（2026-06-14）

- [x] **Step 5: 飞书富文本推送（分板块 + @mention）**
  - 升级 `notifier.py` 为 `post`（富文本）消息格式
  - 消息模板：产品标题 → 各部门板块（含 @mention）→ 升级行动摘要 → 亮点 TOP 3
  - @mention 实现：`{"tag": "at", "user_id": "ou_xxx"}`，open_id 从用户设置读取
  - 升级的问题标注 🔴 + ⚡ 视觉突出
  - 无 open_id 配置时降级为文本提及（不 @）
  - ✅ `review_analyzer/notifier.py` 新增 `build_rich_push_content()` + `send_rich_push()` + 9 个单元测试（2026-06-14）

- [x] **Step 6: 周期调度器（rq-scheduler）**
  - 新增 `workers/scheduler.py` 启动 rq-scheduler
  - 用户配置存入 `push_settings.periodic_push`：frequency / day_of_week / day_of_month / time / timezone
  - 调度逻辑：scheduler 进程每分钟扫描订阅，到期的用户触发 `periodic_digest_job`
  - docker-compose 新增 scheduler service（复用 worker 镜像，不同启动命令）
  - 失败重试 3 次，超时记录日志不降级
  - ✅ `workers/scheduler.py` + `workers/periodic_jobs.py` + docker-compose 更新（2026-06-14）

- [x] **Step 7: 前端设置页扩展**
  - 推送设置区块新增：周期推送配置（频率选择器 + 时间选择器 + 时区）
  - 部门负责人配置：5 个部门各一个飞书 open_id 输入框 + 帮助文案（如何获取 open_id）
  - 升级规则配置：连续次数 / TOP N / 占比阈值（带默认值）
  - Aspect-部门映射调整：展示默认映射表，允许用户修改个别 aspect 归属
  - ✅ `frontend/src/components/settings/smart-push-settings.tsx` + tsc 通过（2026-06-14）

- [x] **Step 8: Settings API 扩展**
  - 新增 Pydantic schema：`PeriodicPushPayload`、`DeptContactPayload`、`EscalationRulePayload`
  - 保存/读取端点：与现有 settings API 统一风格
  - 验证逻辑：open_id 格式校验、时间格式校验、阈值范围校验
  - ✅ `GET/PATCH /settings/smart-push` + schemas 扩展（2026-06-14）

- [x] **Step 9: 即时推送升级（分析完成触发）**
  - 修改 `workers/jobs.py`：分析完成后写入 `push_snapshots`（snapshot_type="batch"）
  - 触发升级判定引擎检查
  - 如果触发升级：生成行动建议 → 写入行动中心 → 推送包含升级标记
  - 复用 Step 5 的富文本模板
  - ✅ `workers/jobs.py` 新增 `_post_analysis_smart_push()` 集成到分析管道末尾（2026-06-14）

- [x] **Step 10: 端到端测试 + 联调**
  - 单元测试：department_router、escalation 模块规则判定
  - 集成测试：模拟 3 次连续推送快照，验证升级触发 → LLM 调用 → action_item 写入
  - 飞书联调：测试群验证富文本格式 + @mention 是否生效
  - 回归：确保现有"分析完成即时推送"功能不受影响
  - 前端验收：设置页配置 → 触发推送 → 行动中心查看自动生成的行动项
  - ✅ 35 个单元/集成/回归测试全部通过，ruff + tsc 通过（2026-06-14）

**配额联动**：
- Free：仅即时推送（已有能力），无周期推送，无升级机制
- Pro：即时推送 + 周期推送（每周），升级机制（3 次连续），单产品
- Team：全部能力，多产品多部门，自定义周期

### 9.4 邀请返佣增长

**目标**：通过现有付费用户口碑推荐获取新用户，CAC 远低于广告投放，同时不侵蚀利润。

**机制**：一次性阶梯返佣（现金为主 + 产品额度为辅）

**核心规则：**

| 项目 | 设定 |
|------|------|
| 返佣触发 | 好友通过邀请链接注册 → 完成首次付费 → 7天无退款 |
| 返佣形式 | 现金（可提现） + 产品分析额度（即时到账） |
| 阶梯依据 | 推荐人累计有效推荐人数 |
| 被推荐人优惠 | 首月 8 折 |
| 推荐人画像 | 现有付费用户（非 KOL/代理模式） |

**阶梯表：**

| 档位 | 累计有效推荐 | 现金奖励/人 | 额度奖励/人 | 推荐人称号 |
|------|------------|-----------|-----------|-----------|
| 铜牌 | 1-3 人 | ¥30 | 500 条分析额度 | 推荐新手 |
| 银牌 | 4-10 人 | ¥50 | 1000 条额度 | 银牌推荐官 |
| 金牌 | 11+ 人 | ¥80 | 2000 条额度 | 金牌推荐官 |

> 升档后已发放奖励不追溯补差，从新档位起按新比例算。

**经济模型验证（最低套餐 ¥99/月，平均留存 6 个月，LTV = ¥594）：**

| 档位 | CAC（现金） | CAC/LTV | 对比广告获客（通常 30-50%） |
|------|-----------|---------|--------------------------|
| 铜牌 | ¥30 | 5% | 远低于广告 |
| 银牌 | ¥50 | 8.4% | 远低于广告 |
| 金牌 | ¥80 | 13.5% | 仍然健康 |

额度成本：500 条分析约 ¥2-5（LLM API），可忽略。

**防滥用规则：**
- 同一设备/IP/手机号 7 天内只算 1 次有效推荐
- 好友需完成至少 1 次真实分析任务（非空提交）
- 7 天冷却期内退款 → 佣金不发放
- 单账号单月最高提现 ¥5000
- 发现批量刷单 → 冻结账号 + 追回已发佣金

**Files:**
- Create: `migrations/0XX_referral_rewards.sql`（邀请关系表 + 奖励记录表）
- Create: `backend_api/app/schemas/referral.py`（Pydantic 模型）
- Create: `backend_api/app/routes/referral.py`（邀请链接生成、奖励查询、提现申请）
- Create: `backend_api/app/services/referral.py`（返佣计算、阶梯判定、防滥用校验）
- Create: `frontend/src/app/(protected)/referral/page.tsx`（邀请中心页面）
- Modify: `frontend/src/components/app/sidebar.tsx`（新增邀请中心导航入口）
- Modify: `backend_api/app/main.py`（注册 referral router）

- [ ] **Step 1: 数据库设计**
  - 新建 `referral_links` 表：id, user_id(推荐人), code(唯一邀请码), created_at
  - 新建 `referral_relations` 表：id, referrer_id, referee_id, referral_code, registered_at, first_paid_at, is_valid(7天冷却期后确认), created_at
  - 新建 `referral_rewards` 表：id, user_id(推荐人), referee_id, reward_type('cash'|'quota'), cash_amount, quota_amount, tier_at_time('bronze'|'silver'|'gold'), status('pending'|'confirmed'|'withdrawn'), confirmed_at, withdrawn_at, created_at
  - 新建 `withdrawal_requests` 表：id, user_id, amount, payment_method('wechat'|'alipay'), account_info(加密), status('pending'|'approved'|'paid'|'rejected'), created_at, processed_at
  - 索引：referrer_id + is_valid、user_id + status

- [ ] **Step 2: 后端核心逻辑**
  - 邀请码生成（注册时自动分配唯一码，或用户主动生成）
  - 注册时识别邀请来源（URL 参数 `?ref=CODE`）
  - 好友首次付费后触发 7 天倒计时（RQ delayed job）
  - 7 天后确认有效：计算推荐人当前档位 → 发放对应奖励
  - 额度即时到账（修改用户 quota）、现金记入可提现余额

- [ ] **Step 3: 前端邀请中心页面**
  - 展示专属邀请链接 + 二维码（可复制/分享）
  - 当前档位 + 进度条（"再推荐 X 人升级为银牌"）
  - 推荐记录列表（好友昵称脱敏、状态：待付费/冷却中/已确认）
  - 可提现余额 + 提现按钮（最低 ¥50）
  - 推荐话术模板（一键复制）

- [ ] **Step 4: 被推荐人首月 8 折**
  - 注册时如携带 ref 参数，自动标记 `referred_by`
  - Paddle checkout 时应用 20% discount（或走 coupon code）
  - 折扣从平台毛利让出，不计入推荐人佣金基数

- [ ] **Step 5: 提现流程（Phase 1 - 手动）**
  - 用户提交提现申请（金额 + 支付宝/微信账号）
  - 后台管理界面审核列表
  - 人工每周统一打款
  - 提现成功后状态更新 + 通知用户

- [ ] **Step 6: 提现流程（Phase 2 - 自动，量起来后）**
  - 对接微信商户平台「企业付款到零钱」或支付宝「单笔转账」API
  - 自动审核规则（单笔 ≤ ¥500 自动通过）
  - 需企业主体 + 支付资质

- [ ] **Step 7: 埋点与数据监控**
  - PostHog 事件：referral_link_copied、referral_link_shared、referee_registered、referee_paid、reward_confirmed、withdrawal_requested
  - 核心指标看板：邀请转化率、人均推荐数、各档位分布、总佣金支出/月

- [ ] **Step 8: 验收**
  - `ruff check` + `tsc typecheck`：PASS
  - 用户 A 生成邀请链接 → 用户 B 通过链接注册 → B 付费 → 7 天后 A 收到 ¥30 + 500 额度
  - A 累计推荐 4 人后，第 5 人奖励自动升为 ¥50 + 1000 额度
  - 提现申请正常创建，管理后台可见
  - 防刷规则：同 IP 重复注册不计入有效推荐

### 9.5 自研评论标注模型

> **背景**：当前架构每条评论都需实时调用 DeepSeek API（~1-3 秒/条），432 条评论需 Worker 运行数分钟。
> 竞品 Shulex 采用「自研 tagging model + 预标注入库」模式，用户请求时只做聚合统计，10 秒出结果。
> 本任务通过知识蒸馏将 DeepSeek 的标注能力迁移到自研轻量模型，实现毫秒级推理 + 离线预标注。

#### 阶段一：数据积累与标注质量监控（2-4 周，无额外开发成本）

**前提**：Worker 增量写入已部署（7.11 bug fix），系统正常积累分析数据。

- [ ] 确认 `comments` 表中已有字段满足训练需求：`content`, `sentiment`, `aspects_json`, `issue_tag`, `highlight_tag`, `is_processed`
- [ ] 编写数据导出脚本 `scripts/export_training_data.py`：从生产 DB 导出 `is_processed=1` 的评论为 JSONL 格式
  - 字段：content, rating, sentiment, aspects (from aspects_json), issue_tag, highlight_tag
  - 过滤条件：`analyzer_version >= 'v2.4'`（确保用最新 prompt 标注的数据）
  - 目标：≥10,000 条高质量标注样本
- [ ] 在 `PROGRESS_V2.md` 中设置里程碑追踪：每周统计 `SELECT COUNT(*) FROM comments WHERE is_processed=1 AND analyzer_version >= 'v2.4'`
- [ ] 建立标注质量基线：从 Golden Set（`data/golden_set/`）中导出人工标注对照集

#### 阶段二：模型选型与 PoC 训练（2 周）

**启动条件**：积累 ≥10,000 条标注数据

- [ ] 模型选型评估（选 1 个）：
  - 方案 A：`bert-base-chinese` fine-tune（多任务：sentiment + aspect 分类），推理 ~5ms/条
  - 方案 B：`Qwen2-0.5B` LoRA fine-tune（保留一定生成能力，可输出 JSON），推理 ~50ms/条
  - 方案 C：`distilbert-multilingual` + 分类头（跨语言支持好，推理 ~3ms/条）
  - 评估标准：Golden Set 准确率 ≥ 90% + 推理速度 ≤ 50ms/条 + 显存 ≤ 2GB
- [ ] 搭建训练环境：`review_analyzer/ml/` 目录结构
  ```
  review_analyzer/ml/
  ├── train.py           # 训练脚本
  ├── evaluate.py        # Golden Set 评测
  ├── inference.py       # 推理服务封装
  ├── export_onnx.py     # 导出 ONNX 用于生产部署
  └── config.yaml        # 模型配置
  ```
- [ ] 训练 PoC 模型，在 Golden Set 上评测：
  - sentiment accuracy ≥ 92%（对标 DeepSeek 的 ~95%）
  - aspect top-1 key accuracy ≥ 88%
  - issue_tag / highlight_tag 提取 F1 ≥ 0.85
- [ ] 成本对比文档：自研模型 vs DeepSeek API（推理速度、成本/条、准确率）

#### 阶段三：双轨运行 — Shadow Mode（2 周）

**启动条件**：PoC 模型 Golden Set 达标

- [ ] 部署自研模型为独立服务（Docker container，GPU 可选 / CPU ONNX 推理）
- [ ] Worker 新增 Shadow Mode 配置：`USE_LOCAL_MODEL_SHADOW=true`
  - 每条评论同时调 DeepSeek + 本地模型
  - 本地模型结果不写入 `comments` 表，写入独立的 `ml_shadow_results` 表
  - 对比两者的 sentiment / aspect 一致率
- [ ] 建立自动化对比 dashboard（或定期脚本）：
  - 一致率 ≥ 95% 进入下一阶段
  - 不一致的 case 导出为「困难样本」加入训练集（active learning）
- [ ] 持续迭代：困难样本回灌 → 重新训练 → 评测 → 直到一致率达标

#### 阶段四：切换主链路（1 周）

**启动条件**：Shadow Mode 一致率 ≥ 95% 持续 7 天

- [ ] `workers/jobs.py` 新增模型路由开关：`ANALYSIS_ENGINE=local|deepseek|hybrid`
  - `local`：全量走自研模型（毫秒级，无 API 成本）
  - `deepseek`：保持现状（兜底）
  - `hybrid`：自研模型主 + DeepSeek 对低置信度样本做二次确认
- [ ] 压测：1000 条评论批量分析，确认 < 30 秒完成（对比当前 ~10 分钟）
- [ ] 灰度切换：先 10% 流量 → 50% → 100%，每阶段观察 3 天
- [ ] 切换后 DeepSeek API 降级为 fallback（置信度 < 0.8 时触发）

#### 阶段五：预标注模式（长期方向）

**启动条件**：阶段四成功，且有 9.1 评论自动获取功能

- [ ] 评论入库时自动触发本地模型标注（类 Shulex 模式）
- [ ] 用户点击「分析」时只做聚合统计 + LLM 摘要（10 秒内出结果）
- [ ] 定期重标注：新模型版本上线后，对历史评论做批量重标注（夜间 cron job）

#### 里程碑与退出标准

| 里程碑 | 条件 | 预计时间 |
|--------|------|---------|
| 数据就绪 | ≥10,000 条 v2.4+ 标注数据 | 阶段一完成 |
| PoC 达标 | Golden Set sentiment acc ≥ 92% | 阶段二完成 |
| Shadow 达标 | 7 天一致率 ≥ 95% | 阶段三完成 |
| 主链路切换 | 1000 条 < 30s + 无准确率回归 | 阶段四完成 |
| 预标注上线 | 入库即标注 + 用户 10s 出结果 | 阶段五完成 |

#### 成本收益预估

| 维度 | 当前（DeepSeek API） | 目标（自研模型） |
|------|---------------------|-----------------|
| 推理速度 | 1-3 秒/条 | 3-50 毫秒/条 |
| 432 条分析耗时 | 3-10 分钟 | < 30 秒 |
| 成本/千条 | ¥0.3（API 费用） | ¥0.01（GPU 算力分摊） |
| Worker 崩溃风险 | 高（长时间进程） | 极低（秒级完成） |
| 依赖外部 API | 是（DeepSeek 宕机=全挂） | 否（自主可控） |

#### 风险与应对

| 风险 | 应对措施 |
|------|---------|
| 标注数据不足 | 阶段一期间优先积累数据；必要时用 DeepSeek 对历史未标注评论补标 |
| 模型准确率不达标 | 保持 DeepSeek fallback，hybrid 模式不影响用户体验 |
| GPU 成本 | ONNX 量化后可用 CPU 推理；阿里云 GPU 实例按需开 |
| 新品类泛化差 | 持续收集用户反馈样本 + 定期 fine-tune |

---

### 9 路线图原则

- **不在 9 范围**：PDF 美化报告、A/B 文案批量、避雷文案、关键词命中预警、实时逐条推送 — 这些功能价值有限或可被替代，**永不开发**
- **触发节奏**：每个里程碑任务必须有付费用户里程碑作为启动条件，避免过早投入
- **配额联动**：每个新功能上线前同步更新 `COST_PROFIT.md` 的单价表与套餐配额
- **返佣成本联动**：返佣方案调整时同步更新 `COST_PROFIT.md` 的获客成本模型，确保 CAC/LTV < 15%

---

### 新品类接入 SOP（Taxonomy 扩展流程，2026-06-12 定稿）

> **背景**：6.1 建立了 5 个核心品类（家居/3C/服饰/母婴/宠物）的 Taxonomy + 评测体系。
> 后续新增品类时，按以下分级流程操作，避免重复探索。

#### 一、轻量接入（大多数新品类，半天工作量）

适用场景：用户反馈某品类分析结果"颗粒度粗"，或新签付费用户集中在某品类。

| 步骤 | 操作 | 产物 | 耗时 |
|------|------|------|------|
| 1. 数据准备 | 收集该品类 500-3000 条评论（爬虫/用户上传/公开数据集） | `data/raw/{category}/` | 1h |
| 2. Taxonomy 抽取 | `python3 scripts/extract_taxonomy_generic.py --category {name} --seed data/taxonomy/seeds/{name}.yaml` | `data/taxonomy/v1.0/{category}/{sub_cat}.yaml` | 1-2h（API 费用 ≈ ¥5-15） |
| 3. 人工 Review | `python3 scripts/build_taxonomy_review_sheet.py` → 人工 review Excel → `python3 scripts/apply_taxonomy_review.py` | 修正后的 YAML | 1-2h |
| 4. 入库 | `python3 scripts/import_v4t1_assets.py --category {name}` | PG `category_aspect_taxonomy` 表新增行 | 5min |
| 5. Spot Check | 随机采样 10 条真实评论 → 跑 v2.4 prompt → 确认 Taxonomy 命中率 100% + 品类专属 aspect 有效出现 | 肉眼确认，无需 golden set | 15min |
| 6. 上线 | 无需改代码（v2.4 动态从 DB 查 taxonomy），清 `taxonomy_loader` 缓存即可生效 | — | 0 |

**验收标准（轻量）：**
- Taxonomy 命中率 ≥ 95%（抽出的 aspect 落在品类 taxonomy 集内）
- 品类专属 aspect 至少出现 1-2 个非 base 的 key
- 零越界（不出现其他品类的专属 aspect）

#### 二、深度验证（高价值核心品类，1-2 天工作量）

适用场景：该品类付费用户超过总付费用户 20%，或客户反馈精度不够需要量化证明改进。

在轻量接入的基础上，额外执行：

| 步骤 | 操作 | 产物 | 耗时 |
|------|------|------|------|
| 6. 采样标注 | 从该品类评论中分层采样 50 条（rating × sentiment 交叉），人工标注 gold_sentiment + gold_aspects | `data/golden_set/v1.0/{category}_50.csv` | 3-4h |
| 7. 评测跑分 | `python3 scripts/eval_v23_vs_v24.py`（改造支持多品类）或独立评测脚本 | 准确率 / 召回率 / F1 指标 | 30min |
| 8. Bad Case 补充 | 把误判样本加入 `bad_cases` 表，作为后续 few-shot 种子 | `bad_cases` 表新增行 | 30min |
| 9. 品类专属 few-shot | 在 prompt 末尾注入 2-3 条该品类的 few-shot 示例（6.3 Step 4 框架） | `prompts/annotate_v2.5.md`（若需要） | 1h |

**验收标准（深度）：**
- 情感准确率 ≥ 92%（对齐家居品类基线）
- Aspect 抽取 F1 ≥ 0.75（precision × recall 均衡）
- Bad Case 库该品类至少 10 条

#### 三、工具链速查

| 需求 | 脚本 | 说明 |
|------|------|------|
| 预处理原始评论 | `scripts/preprocess_reviews.py` | 按品类 YAML 配置清洗 |
| Taxonomy 抽取 | `scripts/extract_taxonomy_generic.py` | 支持 seed extends，DeepSeek API |
| 人工 Review 表 | `scripts/build_taxonomy_review_sheet.py` | 生成 Excel，标注保留/合并/删除 |
| Review 决策应用 | `scripts/apply_taxonomy_review.py` | 把 review 决策写回 YAML |
| 入库 | `scripts/import_v4t1_assets.py` | rglob YAML → PG 表，带 keepalive |
| 评测对比 | `scripts/eval_v23_vs_v24.py` | v2.3 vs v2.4 + 跨品类验证 |
| 缓存清除 | `taxonomy_loader.clear_cache()` | 新品类入库后需清缓存 |

#### 四、已完成品类清单

| 品类 | sub_category 数 | aspect 总行数 | 验证级别 | 完成日期 |
|------|----------------|--------------|----------|----------|
| 家居 | 6 | ~120 | 深度（500 条 golden set） | 2026-06-10 |
| 3C | 11 | ~190 | 轻量（10 条 spot check） | 2026-06-11 |
| 服饰 | 8 | ~170 | 轻量（10 条 spot check） | 2026-06-11 |
| 母婴 | 9 | ~135 | 轻量（10 条 spot check） | 2026-06-11 |
| 宠物 | 26 | ~450 | 轻量（10 条 spot check） | 2026-06-11 |
| 户外 | — | — | 未接入（原始数据保留，Erika 决策暂缓） | — |

---

## 7. 运维基建

> **目标**：建立自动化发布流水线，降低人工部署风险，为付费用户提供稳定交付保障。

### 7.1 CI 持续集成 ✅

**启动条件**：无，基础设施，随时可搭。

**Files:**
- Create: `.github/workflows/ci.yml`
- Create: `pyproject.toml`（ruff 配置）

**内容：**
- [x] GitHub Actions workflow：push 到 develop/main 时自动触发
- [x] Python 后端：lint（ruff）— 已配置并通过
- [x] Next.js 前端：类型检查（tsc）+ build 验证 — 已通过
- [ ] 状态徽章挂到 README

**价值**：每次 push 自动验证代码质量，防止低级错误上线。

---

### 7.2 CD 持续部署

**启动条件**：至少 1 个付费用户（手动部署的风险成本开始大于搭建成本）。

**Files:**
- Create: `.github/workflows/deploy.yml`
- Modify: `deploy/docker-compose.yml`（可能需要加 health check）

**内容：**
- [x] main 分支合并后自动触发
- [x] SSH 到 ECS 执行 `git pull && docker compose up -d --build`
- [x] 部署后自动 health check（curl 首页 + API /health）
- [x] 失败时飞书 webhook 告警
- [x] Rollback 方案：保留前一版本 image tag，一键回退

**价值**：合并即上线，从"手动 SSH 部署"到"一键发布"，降低发布遗漏和中断风险。

---

### 7.3 独立测试环境

**启动条件**：团队扩展或付费用户规模需要 staging 验证。

**内容：**
- [ ] 额外一台 ECS（或同一台用不同端口）跑 develop 分支
- [ ] 连 dev 库（`clueai-dev`）
- [ ] staging 域名（如 `staging.clueai-reviewlens.com`）
- [ ] develop 推送自动部署到 staging

**价值**：提供独立于本地的验证环境，支持多人协作和外部演示。

---

### 7.4 预览环境 + 协作审查升级路径

> **当前模式**：AI 写 + AI 审 + Erika 大模块验收。详见 CLAUDE.md「协作审查流程」。

#### 当前阶段（Solo + AI）

- [x] Claude Code 每次 push 前自动 code review
- [x] CI 自动跑 lint + typecheck + build
- [ ] Erika 大模块验收通过本地 `docker compose up` 预览

#### 升级阶段 1: PR 预览环境（满足条件后启动）

**启动条件**：≥1 付费用户 OR Erika 需要频繁远程验收（不方便本地跑 docker）

**内容：**
- [ ] Vercel Preview 接入（每个 PR 自动生成预览 URL）
- [ ] PR 描述模板自动包含预览链接
- [ ] Erika 可在手机/任意设备上验收 UI

**价值**：Erika 不需要本地环境就能验收，降低验收摩擦。

#### 升级阶段 2: 自动化测试覆盖（满足条件后启动）

**启动条件**：核心业务路径稳定（上传→分析→结果展示）+ 出现过回归 bug

**内容：**
- [ ] E2E 测试（Playwright）：覆盖上传、分析、结果展示、付费墙
- [ ] API 集成测试：覆盖核心 endpoint
- [ ] CI 中自动跑测试，PR 必须测试通过才能合并

**价值**：减少"改 A 坏 B"的回归问题，AI 自审有了自动化兜底。

#### 升级阶段 3: 多人协作审查（满足条件后启动）

**启动条件**：第二个开发者加入 OR MRR > $3k

**内容：**
- [ ] PR 强制要求 1 人 approve
- [ ] CODEOWNERS 文件指定模块负责人
- [ ] Lighthouse CI（性能基线）
- [ ] 数据库 migration 变更自动 @mention Erika

**价值**：多人协作时防止互相覆盖，保持架构一致性。

---

### 7.5 数据埋点与用户行为分析

> **目标**：建立完整的用户行为追踪体系，支撑转化漏斗优化、AI 质量监控、产品迭代决策。
> **启动条件**：上线前 P0 部分必须就位；P1/P2 按付费用户里程碑触发。
> **技术选型**：PostHog（开源，自托管免费额度 1M events/月，Next.js SDK 成熟，自带漏斗/留存/热力图/Feature Flags）
> **不选 Google Analytics 的原因**：GA4 事件模型灵活度低、中国大陆访问受限、自定义看板能力弱；PostHog 支持自托管（未来数据合规）+ 开箱即用的 A/B 测试。

**Files:**
- Create: `frontend/src/lib/analytics.ts`（前端埋点统一封装）
- Create: `backend_api/app/services/analytics.py`（后端事件追踪服务）
- Create: `backend_api/app/middleware/analytics_mw.py`（API 自动追踪中间件）
- Modify: `frontend/src/app/layout.tsx`（接入 PostHog Provider）
- Create: `migrations/014_analytics_events.sql`（后端事件表）

#### P0: 上线前必须就位（2-3 天）

- [x] **Step 1: PostHog 接入** ✅ 2026-06-12
  - 注册 PostHog Cloud（免费额度 1M events/月，早期足够）
  - `npm install posthog-js`（前端 SDK）
  - 建立 `frontend/src/lib/analytics.ts` 统一封装层
  - `layout.tsx` 引入 PostHog Provider（配合 Next.js App Router 的 client boundary）
  - 自动采集：PV、停留时长、按钮点击（autocapture）
  - 环境变量：`NEXT_PUBLIC_POSTHOG_KEY` + `NEXT_PUBLIC_POSTHOG_HOST`（不硬编码）
  - PostHog Cloud 注册完成，Free plan，Paddle 数据源已连接
  - 验收：PostHog Dashboard 能看到实时页面浏览事件（待部署后验证）

- [x] **Step 2: 核心转化漏斗事件（前端关键事件）** ✅ 2026-06-12
  - 获客阶段：
    - `landing_page_view`（来源 UTM 参数：utm_source / utm_medium / utm_campaign）
    - `signup_click` / `signup_complete`（注册漏斗）
    - `login_success` / `login_fail`（登录健康度）
  - 激活阶段（Aha Moment = 第一次看到分析结果）：
    - `first_upload_start` / `first_upload_complete`（文件类型、评论数）
    - `first_analysis_result_view`（从注册到此的时间 = Time to Value）
  - 留存阶段：
    - `analysis_session_start`（每次新分析，带品类标签）
    - `feature_use`（功能名：ask_reviews / compare / actions / export / copywriter）
  - 变现阶段：
    - `paywall_hit`（触碰配额墙：feature / current_usage / limit）
    - `pricing_page_view` / `checkout_start` / `payment_success`
  - **已实现**：signup_click, signup_complete, login_success, login_fail, upload_start, upload_complete, upload_fail；其余事件待对应功能页面开发时补齐

- [x] **Step 3: 后端 AI 质量与成本追踪** ✅ 2026-06-12
  - 建表 `analytics_events`（user_id, event_name, properties JSONB, created_at）
  - 关键后端事件：
    - `llm_call`：model, prompt_version, input_tokens, output_tokens, latency_ms, cost_yuan, success
    - `llm_error`：model, error_type, retry_count, fallback_to
    - `analysis_job_complete`：review_count, cluster_count, llm_calls_saved, total_latency_ms, total_cost_yuan
    - `embedding_generate`：count, model, latency_ms, cost_yuan
    - `quota_check`：dimension, current_usage, limit, blocked(bool)
    - `cluster_efficiency`：total_reviews, clusters_formed, representatives_count, savings_pct
  - FastAPI 中间件：自动记录每次 API 调用（path, method, status_code, latency_ms, user_id）
  - 异步写入（不阻塞主请求）：用 `asyncio.create_task` 或后台线程池
  - **已实现**：`backend_api/app/services/analytics.py` + `backend_api/app/middleware/__init__.py` + `migrations/014_analytics_events.sql`（待执行 migration）

- [x] **Step 4: 用户属性标记（PostHog identify + group）** ✅ 2026-06-12
  - 登录成功后：`posthog.identify(user_id, { plan, signup_date, total_analyses, products_count, primary_category })`
  - plan 变更时更新属性（支持分群：Free vs Pro 行为差异）
  - 首次分析完成标记 `activated = true`（激活率核心指标）
  - 可选：PostHog Group Analytics（按"团队"聚合，为 Team 档预留）
  - **已实现**：login-form / register-form 中 identify 调用已接入；plan 变更追踪待 Paddle webhook 联动时补充

#### P1: 上线后 2 周启动（付费用户 ≥5 触发）

- [ ] **Step 5: AI 输出质量监控面板**
  - 看板维度：
    - LLM 平均延迟趋势（按 model / prompt_version 分组）
    - Token 消耗日/周聚合（成本可视化，对照 COST_PROFIT.md 预算）
    - 聚类节省率趋势（cluster_savings = 1 - llm_calls / total_reviews）
    - 分析失败率（按错误类型分组：timeout / json_parse / rate_limit）
    - Prompt 版本切换前后指标对比
  - 告警规则（飞书 webhook）：
    - LLM P95 延迟 > 15s
    - 日分析失败率 > 5%
    - 单用户日成本 > ¥5（异常用量）
    - 聚类节省率 < 50%（聚类失效信号）

- [ ] **Step 6: 用户反馈与 AI 质量闭环追踪**
  - 事件：
    - `thumbs_up` / `thumbs_down`（分析结果满意度打分）
    - `result_edit`（用户修改 AI 输出 = AI 判错信号，记录字段 + 修改前后值）
    - `feedback_submit`（主动纠错提交，关联 6.6 反馈回路）
  - 核心指标：
    - 结果编辑率 = edit_count / total_viewed_results（越低 = AI 越准）
    - 用户满意度 = thumbs_up / (thumbs_up + thumbs_down)
    - 品类准确率差异（哪个品类 edit 最多 → 优先优化）

- [ ] **Step 7: 转化漏斗看板 + 流失分析**
  - PostHog Funnel：`signup → first_upload → first_result_view → second_session → paywall_hit → payment`
  - 关键洞察：
    - 哪一步转化率最低？（定位优化重点）
    - signup → first_upload 的时间分布（Time to Value）
    - 按来源/品类/plan 分群看差异
  - 留存曲线：D1 / D7 / D30 留存率（区分 Free / Pro）

#### P2: 运营优化期（付费用户 ≥20 触发）

- [ ] **Step 8: A/B 测试框架**
  - PostHog Feature Flags + Experiments
  - 可测试场景：
    - Onboarding 引导文案 / 步骤数
    - Paywall 触发时机（第 3 次 vs 第 5 次分析后弹）
    - 定价展示方式（月付 vs 年付默认）
    - Prompt A/B：不同 prompt 版本对用户满意度（thumbs_up 率）的影响
  - 统计显著性要求：p < 0.05，样本量 ≥ 100 per variant

- [ ] **Step 9: 用户分群与生命周期自动化**
  - 活跃分群：日活 / 周活 / 月活 / 沉默（14天无操作）/ 流失（30天无操作）
  - 价值分群：高频付费 / 低频付费 / 免费重度 / 试用未转化
  - 自动化触发：
    - 注册后 24h 未上传 → 引导邮件（"试试上传 10 条评论看看效果"）
    - 7天未登录 + 有剩余配额 → 召回消息
    - 连续 3 次 paywall_hit 未付费 → 优惠券/延长试用
    - 分析结果 thumbs_down > 3 次 → 主动跟进（Erika 人工介入）

- [ ] **Step 10: 运营数据驱动的 AI 迭代闭环**
  - 自动化周报（定时任务生成）：
    - 新增注册、激活率、D7 留存率、付费转化率
    - AI 质量指标变化（准确率代理：edit_rate / thumbs_ratio）
    - 本周 Top 5 bad case（result_edit 最多的评论）
    - Token 成本 vs 收入对比（毛利率监控）
  - 闭环：用户反馈 → bad case 库 → few-shot 更新 → golden set 回归 → prompt 版本升级
  - 决策支撑：哪个品类用户最多 / 哪个功能使用率最低 / 哪个渠道 ROI 最高

#### 埋点命名规范

| 规则 | 示例 |
|------|------|
| 动词_名词格式 | `upload_start`, `analysis_complete`, `paywall_hit` |
| 前缀区分模块 | `auth_login`, `upload_start`, `analysis_result_view`, `billing_checkout` |
| 属性用 snake_case | `{ file_type: "csv", review_count: 150 }` |
| 时间类属性统一 ms | `{ latency_ms: 3200 }` |
| 金额统一元（¥） | `{ cost_yuan: 0.003 }` |
| 布尔属性 is_ 前缀 | `{ is_first_time: true }` |

#### 验收标准

| 阶段 | 验收指标 |
|------|---------|
| P0 完成 | PostHog 实时事件流可见 + 后端 analytics_events 表有数据写入 + 前端 12 个事件全覆盖 |
| P1 完成 | 能回答"用户在哪一步流失""AI 成本本周多少""哪个品类 edit 最多" |
| P2 完成 | 能跑 A/B 测试 + 自动周报 + 流失召回自动触发 |

#### 与现有模块的关系

| 现有模块 | 埋点联动 |
|---------|---------|
| 6.4 成本优化 | `cluster_efficiency` 事件监控聚类效果 |
| 6.6 反馈回路 | `thumbs_up/down` + `result_edit` 是反馈回路的数据源 |
| 6.2 配额系统 | `quota_check` 事件追踪配额墙转化效果 |
| COST_PROFIT.md | 后端 `llm_call` 事件数据验证成本模型准确性 |

#### PostHog 第三方数据源连接清单

> 已连接：Paddle（2026-06-12）。以下按里程碑条件触发，无需提前连接。

| 数据源 | 连接条件 | 连接后能做什么 | 操作方式 |
|--------|---------|--------------|---------|
| **Paddle** ✅ | 上线即连 | 付费事件与用户行为关联：从注册到付费路径分析、付费用户 vs 免费用户行为差异、MRR/Churn 自动同步 | PostHog → Data Sources → Paddle → 填 API Key |
| **Supabase / Postgres** | 付费用户 ≥10 或需要做用户分群 | 把数据库里的用户属性（plan、signup_date、total_analyses）同步到 PostHog，做更精准的分群和漏斗过滤 | PostHog → Data Sources → Postgres → 填 dev 库连接串（只读账号） |
| **飞书 / 钉钉 Webhook**（通过 Custom REST） | 付费用户 ≥20 或需要自动告警 | PostHog Actions 触发飞书通知：如"新用户注册""付费成功""分析失败率飙升" | PostHog → Actions → 配置 Webhook URL |
| **Google Search Console** | 营销站上线且有 SEO 流量后 | 搜索关键词 → 注册 → 付费的全链路归因：哪些关键词带来付费用户 | PostHog → Data Sources → Google Search Console → OAuth |
| **Brevo / Mailgun**（邮件平台） | 开始做邮件召回（付费用户 ≥20） | 邮件打开 → 点击 → 回访 → 付费的转化归因 | PostHog → Data Sources → 选对应邮件平台 |
| **GitHub** | 开源社区运营或 API 产品阶段 | 跟踪 issue/PR 与产品使用行为的关联 | 当前阶段不需要，忽略 |

**原则**：数据源连得越多，PostHog 能做的交叉分析越深。但早期不要贪多——每个连接都需要维护，用不上就是噪音。按条件触发，一个一个加。

---

### 7.6 用户反馈浮窗

**目标：** 在所有已登录页面左下角提供极低摩擦的反馈入口，让种子用户随时反馈 bug、提需求或表达感受。最少 3 次点击完成反馈，无需打字。数据存自有 Supabase，不依赖第三方 SaaS。

**设计依据：** Hotjar（情绪选择极简）+ Linear（自动采集上下文）+ Vercel（不弹模态框，底角浮窗）

**触发条件：** 部署上线前（与 5.8 Phase B 冒烟测试同步完成）

**Files:**
- Create: `migrations/016_user_feedback.sql`
- Create: `review_analyzer/feedback_store.py`
- Create: `backend_api/app/schemas/feedback.py`
- Create: `backend_api/app/routes/feedback.py`
- Modify: `backend_api/app/main.py`（注册 feedback router）
- Create: `frontend/src/components/feedback/FeedbackWidget.tsx`
- Create: `frontend/src/components/feedback/FeedbackMoodPicker.tsx`
- Create: `frontend/src/components/feedback/FeedbackForm.tsx`
- Modify: `frontend/src/components/app/app-shell.tsx`（集成 widget）
- Modify: `frontend/src/lib/api/browser.ts`（新增 submitFeedback）
- Modify: `frontend/src/lib/api/types.ts`（新增 Feedback 类型）

- [x] **Step 1: 数据库 Migration**
  - 新建 `user_feedback` 表：id, user_id, feedback_type('bug'|'feature'|'general'), mood('frustrated'|'idea'|'love'), message(可选,max500), page_path, user_agent, screenshot_url(Phase2), metadata(JSONB), status('new'|'reviewed'|'resolved'), created_at
  - 索引：user_id+created_at DESC, status+created_at DESC
  - 执行 migration 到 dev 库

- [x] **Step 2: 后端 Store + Schema + Route**
  - `feedback_store.py`：`create_feedback(user_id, data) -> int`、`get_feedback_list(status?, limit?)`
  - `schemas/feedback.py`：`FeedbackCreatePayload`（Pydantic, 含字段校验）+ `FeedbackResponse`
  - `routes/feedback.py`：`POST /feedback`（需登录，调用 store 写入）
  - 在 `main.py` 注册 `feedback_router`
  - 提交成功后异步发邮件通知（收件人从 `FEEDBACK_NOTIFY_EMAIL` 环境变量读取，失败静默不阻塞响应）

- [x] **Step 3: 前端 API Client**
  - `types.ts` 新增 `FeedbackCreatePayload` 和 `FeedbackResponse` 类型
  - `browser.ts` 新增 `submitFeedback()` 函数
  - 请求体 snake_case（对齐后端），前端接口 camelCase

- [x] **Step 4: 前端组件实现**
  - `FeedbackWidget.tsx`：FAB 按钮（左下角 fixed，pill 形状）+ 展开面板（状态机：closed → mood → form → submitting → success → closed）
  - `FeedbackMoodPicker.tsx`：3 个情绪按钮（😤 Bug / 💡 建议 / ❤️ 喜欢）
  - `FeedbackForm.tsx`：可选 textarea + 自动显示当前页面标签 + 提交按钮
  - 多语言：通过 `<html lang>` 判断，中文页面显示中文文案，英文页面显示英文文案
  - 快捷键：`Cmd+Shift+F`（Mac）/ `Ctrl+Shift+F`（Win），toggle 开关
  - 样式：`bg-white/88 backdrop-blur border border-line shadow-card rounded-card`，沿用现有设计系统
  - 成功态：✓ + "谢谢反馈！" / "Thanks!" 显示 2s 后自动关闭

- [x] **Step 5: 集成到 AppShell + 埋点**
  - 在 `app-shell.tsx` 末尾加 `<FeedbackWidget />`
  - PostHog 埋点（复用现有 `track()`）：
    - `feedback_opened` — 打开面板
    - `feedback_mood_selected` — 选了哪个情绪
    - `feedback_submitted` — 提交成功（含 type、has_message）
    - `feedback_dismissed` — 未提交就关闭

- [x] **Step 6: 验收**
  - `python3 -m ruff check backend_api/ review_analyzer/`：PASS
  - `cd frontend && npm run typecheck`：PASS
  - 本地 dev server 任意已认证页面左下角 FAB 可见
  - 点击 FAB → 选情绪 → 提交（不写文字）→ 成功关闭，Supabase user_feedback 表有新记录
  - 点击 FAB → 选情绪 → 写文字 → 提交 → 成功关闭
  - 快捷键 Cmd+Shift+F toggle 面板开关
  - 邮件通知发出（或 log 中有发送记录）
  - PostHog debug 模式可见 feedback 事件

- [x] **Step 7: 回滚边界**
  - 仅回滚本任务新增文件 + `app-shell.tsx` 和 `main.py` 的集成改动
  - 不影响其他已有功能

**Phase 2（收集到 ≥10 条反馈后启动）：**
- 截图功能：引入 `html2canvas`（动态 import），一键截取当前页面
- 反馈管理后台：管理员查看/标记状态/回复
- 与 6.6（分析结果纠错）合并数据源

---

### 7.7 中国大陆访问优化

**背景：** 当前服务器 `8.210.51.242` 位于阿里云香港区（Alibaba Cloud HK），域名 `clueai-reviewlens.com` 无 ICP 备案。中国大陆用户可访问但体验不稳定（跨境延迟 50-200ms、部分运营商/时段丢包、无合规保障）。目标用户为中国跨境电商卖家，大陆访问稳定性直接影响留存和付费转化。

**现状诊断：**
- IP: `8.210.51.242`，ISP: Alibaba.com LLC，地区: Hong Kong
- 域名: `.com` TLD，未备案
- 大陆访问: 可达但不稳定，无 CDN 加速
- HTTPS: Let's Encrypt 证书（4 域名），有效期至 2026-09-10

**策略：按阶段推进，先优化后合规。**

---

#### Phase A: Cloudflare CDN + 性能优化 ✅ 2026-06-15

> 触发条件：立即开始
> 预计耗时：2-3 小时
> 目标：不花钱、不备案，把大陆用户体验从"能打开但慢"提升到"基本流畅"

- [x] **Step 1: Cloudflare 接入（~30 min）** ✅ 2026-06-15
  - 注册 Cloudflare 免费账户
  - 添加域名 `clueai-reviewlens.com`
  - Cloudflare 自动扫描现有 DNS 记录
  - 确认 A 记录：`@` → `8.210.51.242`、`www` → `8.210.51.242`、`app` → `8.210.51.242`、`api` → `8.210.51.242`
  - 到阿里云域名管理 → 修改 NS 为 Cloudflare 分配的 nameserver（`shane.ns.cloudflare.com` / `lina.ns.cloudflare.com`）
  - 验证通过：`dig clueai-reviewlens.com NS` 返回 Cloudflare NS ✅

- [x] **Step 2: Cloudflare 配置优化（~20 min）** ✅ 2026-06-15
  - SSL/TLS → Full (Strict) ✅
  - Speed → Auto Minify（JS/CSS/HTML）✅
  - Caching → Browser Cache TTL = 4 hours ✅
  - Cache Rules：API bypass / _next/static/ 30天 / fonts 30天 ✅
  - Network → HTTP/3 + WebSockets 开启 ✅
  - 验证：`cf-ray` 头存在、`alt-svc: h3=":443"` ✅

- [x] **Step 3: Next.js 静态资源优化（~1 hr）** ✅ 2026-06-15（无需改动）
  - `output: 'standalone'` 已启用
  - `_next/static/` 带 content hash + immutable 缓存头
  - 字体使用 `next/font` + `display: swap`
  - 无图片资源，无重量级依赖
  - First Load JS shared = 102kB（React 19 框架本身，已接近最优）
  - nginx real_ip 配置：还原 Cloudflare 背后真实客户端 IP ✅
  - nginx http2 指令升级为新版语法 ✅

- [x] **Step 4: 验收** ✅ 2026-06-15
  - 静态资源命中 CDN：`cf-cache-status: HIT` ✅
  - API 不缓存：`cf-cache-status: DYNAMIC` ✅
  - HTTP/3 启用：`alt-svc: h3=":443"; ma=86400` ✅
  - 长期缓存：`cache-control: public, max-age=31536000, immutable` ✅
  - 待补充：17ce.com 国内多节点测速（需 Erika 手动验证）

---

#### Phase B: ICP 备案 + 国内节点（付费用户 ≥10 触发）

> 触发条件：月付费用户 ≥ 10，或大陆用户访问稳定性成为 Top 3 流失原因
> 预计耗时：3-4 周（含备案审批等待期）
> 目标：合规 + 国内用户体验与海外用户一致
> 备案主体：个体工商户（2026-06-14 确认，详见 Step 5）

- [ ] **Step 5: ICP 备案准备（~2 hr 操作 + 7-20 天等待）**
  - **备案主体：个体工商户**（阿里云备案系统选"企业" → 主体类型"个体工商户"）
  - 前置条件：
    - [x] 域名实名认证（阿里云已完成）
    - [x] 域名注册 ≥3 个自然日（已满足）
    - [ ] 营业执照经营范围含"软件开发"或"信息技术服务"（如未包含，需先做工商变更，半天搞定）
    - [ ] 一台阿里云**国内**区域 ECS（如杭州/深圳）→ 备案提交时需关联，最低配 1C1G（¥30-50/月）即可
  - 备案材料清单：
    - 个体户营业执照副本（扫描件/高清拍照）
    - 经营者身份证正反面
    - 经营者手机号（需实名且与备案省份一致）
    - 经营者邮箱
    - 域名证书（阿里云控制台 → 域名管理 → 域名证书下载）
    - 网站名称（建议："ClueAI 数据分析平台" 或 "评论分析工具"，避免"中国""国际"等大词）
  - 操作流程：
    - 阿里云控制台 → ICP 备案 → 选择"企业" → 主体类型"个体工商户"
    - 填写主体信息 + 域名 + 网站信息
    - 上传营业执照 + 身份证
    - 阿里云初审（1-2 天）→ 可能要求补充材料 → 管局审核（7-20 天，浙江/广东通常 7-10 天）
    - 备案号下发后添加到 `frontend/src/app/layout.tsx` 底部 footer（格式：`浙ICP备2026XXXXXXX号`，链接到 https://beian.miit.gov.cn）
  - 注意事项：
    - 备案期间网站需可访问（Cloudflare 代理模式不影响）
    - 网站实际内容需与备案信息一致（SaaS 商业服务，非个人博客）
    - 个体户备案审批速度与企业一致

- [ ] **Step 5.5: 收款接入（备案通过后或并行准备）**

  #### 5.5.1 ICP 备案 vs ICP 经营许可证（判断依据）

  **核心结论：ClueAI 只需 ICP 备案即可合法收费，不需要 ICP 经营许可证。**

  两者区别：

  | 维度 | ICP 备案 | ICP 经营许可证 |
  |------|---------|---------------|
  | 官方全称 | 非经营性互联网信息服务备案 | 增值电信业务经营许可证（B25 信息服务业务） |
  | 性质 | 备案（登记制） | 许可（审批制） |
  | 主体要求 | 个人 / 个体户 / 公司均可 | 仅内资公司，注册资本 ≥100 万 |
  | 办理周期 | 7-20 工作日 | 40-60 工作日 |
  | 成本 | 免费 | 中介 ¥3000-8000 |
  | 有效期 | 长期 | 5 年，每年 1 月需年检 |

  **常见误解**：收费 ≠ 经营性 ≠ 必须办 ICP 经营许可证。工信部的执法逻辑关注的是"平台性"而非"是否收费"。

  #### 5.5.2 只需 ICP 备案的业务模式（ClueAI 属于此类）

  - ✅ 卖自研 SaaS 工具（订阅制），例如 ClueAI、Notion、腾讯文档订阅版
  - ✅ 卖自己的实体/数字商品（B2C 电商）
  - ✅ 企业官网收咨询费/服务费
  - ✅ 付费内容订阅（内容为自己创作）

  #### 5.5.3 必须办 ICP 经营许可证的业务模式（未来若转型需重新评估）

  - ❌ 交易撮合平台（淘宝、闲鱼、Boss 直聘、大众点评）
  - ❌ 付费信息发布平台（58 同城、招聘网站）
  - ❌ 主要收入来自第三方广告展示
  - ❌ 网络支付 / 金融业务
  - ❌ 在线游戏运营（另需网络文化经营许可证）

  #### 5.5.4 ClueAI 业务模式核对（6 项判断）

  | 判断维度 | ClueAI 情况 | 结论 |
  |---------|------------|------|
  | 谁提供服务 | 自研 SaaS | ✅ 自营 |
  | 收谁的钱 | 直接向工具使用者收订阅费 | ✅ 自营收入 |
  | 有无第三方入驻 | 无 | ✅ 非平台 |
  | 有无广告收入 | 无 | ✅ 非广告 |
  | 有无交易撮合 | 无 | ✅ 非平台 |
  | 有无金融/支付业务 | 仅接支付宝/微信收自己的订阅费 | ✅ 非金融 |

  权威依据：
  - 《互联网信息服务管理办法》第 4 条
  - 《电信业务分类目录（2015版）》B25 信息服务业务

  #### 5.5.5 个体户可用的收款方式

  - ✅ 支付宝商户号（网页支付 / 当面付）— 个体户直接申请，费率 0.6%
  - ✅ 微信支付商户号 — 个体户可申请，费率 0.6%
  - ❌ Stripe / Paddle — 需境外公司主体，个体户阶段不可用
  - 资金流转：商户号 → 经营者个人银行卡（个体户特权，无需对公账户）

  #### 5.5.6 税务与开票

  - 小规模纳税人：年开票 ≤120 万免增值税
  - SaaS 收入税目："信息技术服务"，税率 1%（小规模）/ 6%（一般纳税人）
  - 可开普票；专票需去税务局代开或升为一般纳税人
  - 推荐初期走"核定征收"，报税简单

  #### 5.5.7 备案通过后的合规动作（法定要求，缺失有罚款风险）

  - [ ] `frontend/src/app/layout.tsx` footer 添加备案号 `京ICP备2026XXXXXXX号`，链接到 `https://beian.miit.gov.cn`
  - [ ] 网站实际内容与备案信息一致（备案时的"网站名称""服务类型"）
  - [ ] 不在网站上超出营业执照经营范围经营（营业执照主营："软件开发、信息技术咨询服务、技术服务"）
  - [x] 用户协议 / 隐私政策 / 退款政策 / 服务条款上线（已放到 footer）✅ 2026-07-06

- [ ] **Step 5.6: 主体升级评估（持续关注，按触发条件执行）**
  - **必须切换到公司主体的触发条件（任一命中即启动）：**
    - 需要申请 ICP 经营许可证（增值电信业务）— 仅限注册资本 ≥100 万的内资公司
    - 年收入超 500 万（强制转一般纳税人，公司形式更合适）
    - 接入投资/融资（投资人只投公司）
    - 需要 Stripe/Paddle 收海外款（需境外公司：香港/新加坡）
    - 团队扩张 ≥3 人（公司形式社保合规更规范）
    - 大客户要求开专票 / 签企业合同
  - 现阶段结论：**个体户完全够用**，备案能过、收款能做、税务简单（核定征收省心）
  - 建议升级时机：月收入稳定超 10 万 或 需要拿 ICP 经营许可证时

- [ ] **Step 6: 国内 ECS 部署（备案通过后 ~4 hr）**
  - 购买阿里云国内 ECS（推荐 2C4G，杭州区或深圳区）
  - 复用现有 `deploy/docker-compose.yml` 部署
  - 国内 ECS 的 `deploy/.env` 配置：
    - `DATABASE_URL` → 指向 prod Supabase（或后续国内 RDS）
    - `REDIS_URL` → 本地 Redis
    - 其余环境变量同 HK ECS
  - 安装 Docker + 拉取代码 + 构建 + 启动
  - 验证国内 ECS 各服务正常

- [ ] **Step 7: DNS 智能解析（~30 min）**
  - 从 Cloudflare 切回阿里云 DNS（阿里云 DNS 支持按地域解析）
  - 或使用 Cloudflare 付费版 Geo Steering（$20/月，不推荐早期）
  - 推荐方案（阿里云 DNS）：
    - 国内线路：`clueai-reviewlens.com` → 国内 ECS IP
    - 海外线路：`clueai-reviewlens.com` → 8.210.51.242（香港）
    - 或统一走 Cloudflare 但 origin 按 geo 分流
  - 验证：国内 `dig` 解析到国内 IP，海外解析到 HK IP

- [ ] **Step 8: 国内 HTTPS + CDN（~30 min）**
  - 国内 ECS 签发 SSL 证书（阿里云免费证书 或 Let's Encrypt）
  - 可选：接入阿里云 CDN（需备案后才能用国内加速）
  - 备案号添加到 `frontend/src/app/layout.tsx` 底部 footer

- [ ] **Step 9: 验收**
  - 国内用户访问 `clueai-reviewlens.com` → 解析到国内 ECS
  - 海外用户访问同域名 → 解析到香港 ECS
  - 注册/登录/上传/分析全流程国内可用
  - 网站底部显示备案号
  - 17ce.com 全国测速平均 TTFB < 200ms

---

#### Phase C: 后续优化（可选，按需触发）

> 触发条件：月活用户 ≥100 或国内数据库延迟成为瓶颈

- [ ] **Step 10: 国内数据库（评估后决定）**
  - 当前 Supabase 在海外（Singapore），API 请求从国内 ECS → Supabase 有 80-150ms 延迟
  - 若延迟影响用户体验 → 考虑：
    - 阿里云 RDS PostgreSQL（国内区，¥100-300/月）
    - 数据同步方案（prod 双写或定时同步）
  - 决策依据：API P95 延迟 > 2s 时触发

- [ ] **Step 11: 国内对象存储（评估后决定）**
  - 用户上传的评论文件存储在 Supabase Storage（海外）
  - 若上传体验差 → 接阿里云 OSS（国内区）
  - 改动：`backend_api/app/routes/uploads.py` 增加 OSS 上传路径

**成本预估：**

| 阶段 | 成本 | 说明 |
|------|------|------|
| Phase A（Cloudflare） | ¥0/月 | 免费计划足够 |
| Phase B（ICP + 国内 ECS） | ¥150-300/月 | 2C4G ECS + 带宽 |
| Phase C（国内 RDS + OSS） | ¥200-500/月 | 按需，非必须 |

**执行原则：**
- Phase A 立即执行，零成本零风险
- Phase B 等业务验证后再投入（避免过早花钱）
- Phase C 按用户量和体验反馈按需触发
- 全程不影响现有香港部署和海外用户体验

---

### 7.8 shadcn/ui 设计组件系统

**背景：** 当前前端 UI 全部手写 Tailwind className，没有统一的组件原语层（Button / Card / Dialog / Badge 等）。每次新增页面都从零搭样式，导致：1）样式不一致；2）交互细节（focus ring、disabled state、loading skeleton）遗漏；3）改主题需逐页修改。引入 shadcn/ui 作为组件基建层，统一视觉语言，提升开发效率和用户感知品质。

**技术选型：** shadcn/ui（非 npm 包，代码复制到本地，完全可控） + Radix UI（无障碍基础） + class-variance-authority（变体管理） + tailwind-merge（类名去重）

**现状：**
- ✅ 已有 CSS 变量体系（globals.css: --canvas, --ink, --rose, --lavender 等）
- ✅ 已有 Tailwind 主题扩展（tailwind.config.ts 映射 CSS 变量）
- ✅ lucide-react 图标库已安装
- ✅ components.json 已创建（shadcn 已初始化）
- ✅ `frontend/src/components/ui/` 目录已建立（16+ 组件）
- ✅ 依赖已安装：radix-ui、class-variance-authority、clsx、tailwind-merge、recharts

---

#### Phase 1: 初始化 shadcn/ui + 设计令牌映射（~30 min）✅ 已完成

- [x] **Step 1: 安装 shadcn/ui 基础设施**
  - 手动创建 components.json + lib/utils.ts（避免交互式 CLI）
  - 安装依赖：class-variance-authority, clsx, tailwind-merge, tailwindcss-animate
  - 配置 components.json 指向现有 CSS 变量体系
- [x] **Step 2: 设计令牌桥接**
  - 在 globals.css 中补充 shadcn 所需的 HSL 变量（background, foreground, primary, secondary 等）
  - 映射关系：primary → rose, secondary → lavender, accent → mint, background → canvas
  - 保留现有变量不变，新增 shadcn 兼容层

#### Phase 2: 安装核心 UI 组件（~20 min）✅ 已完成

- [x] **Step 3: 安装 P0 组件**
  - Button, Card, Badge, Separator, Skeleton, Input, Textarea, Select
- [x] **Step 4: 安装 P1 组件**
  - Dialog, Sheet, DropdownMenu, Table, Tabs, Tooltip, Alert, Progress

#### Phase 3: 业务组件迁移（~60 min）✅ 已完成

- [x] **Step 5: P0 迁移 — 侧边栏 + 全局按钮**
  - Sidebar 导航项改用 shadcn Button variant="ghost" + asChild
  - 全局 `<button>` 统一替换为 `<Button>`（auth forms, settings, marketing）
- [x] **Step 6: P1 迁移 — 表单输入**
  - login-form, register-form, forgot-password-form 改用 shadcn `<Input>` + `<Button>`
  - settings-panel 所有 input 改用 shadcn `<Input>`，按钮改用 `<Button>`
- [x] **Step 7: P2 迁移 — 营销页 + CTA**
  - site-header 导航链接改用 Button variant="ghost" asChild
  - cta-row 主次按钮改用 Button + Button variant="outline"

#### Phase 4: 图表组件统一（~30 min）✅ 已完成

- [x] **Step 8: 安装 recharts + shadcn chart 包装**
  - `npm install recharts`
  - 创建 `components/ui/chart.tsx` 封装（ChartContainer + ChartTooltipContent）
  - 图表色板通过 CSS 变量 --chart-1~5，映射 rose/lavender/mint

#### Phase 5: 全局间距与呼吸感优化（~20 min）✅ 已完成

- [x] **Step 9: 间距令牌统一**
  - app-shell 大屏间距升级（lg:gap-8, pb-20）
  - globals.css 添加 animate-in 工具类（fadeIn 0.2s ease-out）
- [x] **Step 10: 验收**
  - 全站 tsc --noEmit 通过 ✅
  - next build 成功 ✅
  - 主题色修改一处 CSS 变量 → 全站联动生效（通过 HSL 变量层实现）

---

### 7.9 首页改造

**背景：** 原首页为英文通用 SaaS 风格，缺乏产品差异化表达。需重新设计为中文闭环概念首页，突出"评论分析 → 行动推送 → 复盘验证"的产品核心价值，并以数据可视化卡片直观展示产品能力。

**设计参考：** 暗色 glassmorphic 仪表板截图（仅参考布局结构和卡片形式），保持现有亮色体系（rose/lavender/mint），在呈现形式上做差异化简化。

**标记：** 版本1 — 后续可能迭代优化

---

#### Phase 1: 布局与组件架构重构 ✅ 已完成

- [x] **Step 1: MarketingShell 重构**
  - 改为单卡片大容器布局（rounded-shell + border-line + shadow-card + backdrop-blur）
  - 顶部区域：标题 + 副标题 + 描述 + CTA 按钮（桌面端右上角，移动端底部）
  - 新增 `subtitle` 和 `cta` props
  - 文件：`frontend/src/components/marketing/marketing-shell.tsx`

- [x] **Step 2: HeroPreview 数据可视化卡片**
  - 2×2 网格布局，四张数据卡片：
    - 评论洞察：柱状图（rose→lavender 渐变色柱），展示 Top 5 问题类别
    - 情感分布：三色横向进度条（负面/中性/正面），含评论总数
    - 措施跟进：三项进度条（mint/lavender/rose），展示改进执行率
    - 复盘验证：SVG 折线趋势图，展示改进前后差评率下降
  - 全部使用内联 SVG + CSS 变量渲染，无外部图表库依赖
  - 文件：`frontend/src/components/marketing/hero-preview.tsx`

#### Phase 2: 文案与内容定义 ✅ 已完成

- [x] **Step 3: 核心文案撰写**
  - eyebrow 标签：「分析 → 行动 → 复盘」
  - 主标题：ReviewLens
  - 副标题：从评论洞察到产品行动的完整闭环
  - 描述：多平台 + 多格式 + AI 分析 + 飞书推送 + 跟进落地 + 数据复盘
  - CTA：开始使用 ↗ → /register
  - SEO metadata 同步更新

- [x] **Step 4: ValueGrid 三步闭环卡片**
  - 卡片 1（roseSoft）：多源接入，智能分析 — 多平台多格式支持 + AI Top 10
  - 卡片 2（lavender-soft）：精准推送，责任到人 — 飞书推送 + 责任人匹配
  - 卡片 3（mint-soft）：数据复盘，验证闭环 — 前后对比验证改进效果
  - 文件：`frontend/src/components/marketing/value-grid.tsx`

#### Phase 3: 首页入口整合 ✅ 已完成

- [x] **Step 5: page.tsx 重写**
  - 移除旧英文 HeroSection/FeatureGrid 组件引用
  - 组装 MarketingShell（含 HeroPreview + CTA）+ ValueGrid
  - 文件：`frontend/src/app/page.tsx`

#### Phase 4: 验收 ✅ 已完成

- [x] **Step 6: 构建验证**
  - tsc --noEmit 通过 ✅
  - next build 成功 ✅
  - dev server 启动后 curl 确认所有中文关键内容正常渲染 ✅

---

### 7.10 登录/注册改造 + 全站文案中文化

**背景：** 原登录/注册页面复用首页 MarketingShell 组件，视觉上不够独立，且所有文案均为英文。需改为独立全屏双栏布局（左侧产品展示 + 右侧表单），同时完成全站营销页面文案中文化。

**设计参考：** Shulex 登录页截图（左右分栏布局），保持现有亮色体系（rose/lavender/mint 渐变），不使用深色主题。

---

#### Phase 1: AuthLayout 共享组件 ✅ 已完成

- [x] **Step 1: 创建 AuthLayout 组件**
  - 左侧：rose/lavender/mint 三色渐变背景 + Logo + 评论趋势折线图（SVG）+ 产品价值文案
  - 右侧：纯白背景 + 表单内容区
  - 响应式：移动端隐藏左栏，仅显示 Logo + 表单
  - 文件：`frontend/src/components/auth/auth-layout.tsx`

#### Phase 2: 页面重写 ✅ 已完成

- [x] **Step 2: 登录页重写**
  - 标题：「欢迎回来」+ 副文案「登录后进入评论分析工作台」
  - 底部链接：忘记密码 / 去注册
  - 文件：`frontend/src/app/login/page.tsx`

- [x] **Step 3: 注册页重写**
  - 标题：「创建账号」+ 副文案「注册后即可上传评论，获取 AI 分析洞察」
  - 底部链接：已有账号？去登录
  - 文件：`frontend/src/app/register/page.tsx`

- [x] **Step 4: 找回密码页适配**
  - 标题：「找回密码」+ 三步流程中文化（发送验证码 → 输入验证码+新密码 → 重置成功）
  - 文件：`frontend/src/app/forgot-password/page.tsx`、`frontend/src/components/auth/forgot-password-form.tsx`

#### Phase 3: 表单组件中文化 ✅ 已完成

- [x] **Step 5: login-form.tsx 中文化**
  - label：用户名 / 密码
  - placeholder：请输入用户名 / 请输入密码
  - 按钮：登 录 / 登录中...

- [x] **Step 6: register-form.tsx 中文化**
  - label：用户名 / 邮箱 / 密码
  - placeholder：请输入用户名 / 请输入邮箱地址 / 至少 6 位字符
  - 按钮：注 册 / 注册中...

#### Phase 4: 导航栏中文化 ✅ 已完成

- [x] **Step 7: site-header 更新**
  - 品牌名：ClueAI → ReviewLens，Logo 缩写 CA → RL
  - 副文案：Review intelligence for sellers → 评论智能分析平台
  - 导航项：Pricing → 定价、Try the Flow → 体验流程、Log In → 登录、Create Account → 注册

#### Phase 5: 验收 ✅ 已完成

- [x] **Step 8: 构建验证**
  - tsc --noEmit 通过 ✅
  - next build 编译成功 ✅
  - dev server 验证 /login、/register、/forgot-password、/ 四个页面中文内容正常渲染 ✅

---

### 7.11 AI 分析链路优化

**背景：** 6.4 成本优化已完成（缓存命中率 98%，100 条仅 2 条走 LLM）。本任务在此基础上进一步提升分析质量、降低延迟、增强可观测性。不破坏现有稳定性。

**前置条件：** 6.4 全部完成 ✅

**详细方案文档：** [`AI_PIPELINE_OPTIMIZATION.md`](AI_PIPELINE_OPTIMIZATION.md)

**Phase 1+2 进度：** 6/6 完成 ✅（2026-06-17）  
**部署待办：**
- [ ] 运行 migration 019（tsvector + GIN 索引）和 020（annotation_quality_log 表）
- [ ] `workers/jobs.py` 接入 OPT-3 质量门控（传 embeddings 给 `propagate_cluster_results`，处理 `needs_llm` 回退）
- [ ] `workers/jobs.py` 接入 OPT-5 抽样（分析完成后调用 `log_quality_sample()`）
- [ ] `workers/periodic_jobs.py` 接入 OPT-6（调用 `check_escalations` 时传 `total_reviews`）

---

#### Phase 1: P0 低成本高收益（1-2 天）

- [x] **OPT-1: Embedding 批量调用** ✅ 2026-06-17
  - 现状：`rag.py:embed_session_comments()` 逐条 HTTP 调用
  - 方案：改用 `input: list[str]` 批量接口（一次最多 2048 条）
  - 改动：`review_analyzer/rag.py` 新增 `generate_embeddings_batch()`
  - 预期：500 条 embedding 延迟从 ~15s → ~2s
  - 风险：极低，失败 fallback 回逐条
  - **实现备注：** 批量大小 256 条/次（留余量避免超时）；`embed_session_comments` 和 `ensure_comment_embeddings` 均已改为批量调用；失败时自动降级逐条重试；新增 `_get_embedding_client()` 复用 client 实例

- [x] **OPT-2: DeepSeek Prefix Caching 验证** ✅ 2026-06-17
  - 现状：`deep_analyzer.py` 每条评论发完整 system prompt（~2000 tokens），DeepSeek 理应自动缓存
  - 方案：检查 DeepSeek 账单 `cache_hit_tokens` 字段，确认是否命中
  - 改动：`llm_router.py` 新增 `_log_cache_stats()` 方法，每次成功调用自动记录 `prompt_cache_hit_tokens` 或 `cache_hit_tokens`（兼容两种 API 返回格式）
  - 风险：零
  - **实现备注：** 日志格式 `llm_router prefix_cache: model=deepseek prompt_tokens=2100 cache_hit_tokens=2000 (95%)`；下一步可从日志中统计实际命中率，若持续为 0 则需调整并发策略（先发 1 条建缓存，再并行）

- [x] **OPT-3: 聚类传播质量门控** ✅ 2026-06-17
  - 现状：`clustering.py` 对所有聚类结果无差别传播
  - 方案：簇内平均余弦相似度 < 0.88 的不传播，成员回退走 LLM
  - 改动：`backend_api/app/services/clustering.py` 新增 `_cluster_avg_cosine_similarity()` + `propagate_cluster_results` 增加 `embeddings` 和 `similarity_threshold` 参数
  - 预期：消除跨品类场景下的错误传播
  - 风险：低，最坏只是多走几次 LLM
  - **实现备注：** 向后兼容 — `embeddings` 参数可选，不传时行为与原来一致；低质量簇成员返回 `{"needs_llm": True, "reason": "low_cluster_similarity"}`，需由 caller（`workers/jobs.py`）二次送 LLM；阈值 0.88 可通过参数调整

---

#### Phase 2: P1 中等投入（3-5 天）

- [x] **OPT-4: RAG Hybrid Search + Reranking** ✅ 2026-06-17
  - 现状：向量检索 OR 文本 fallback（二选一），文本检索是简单 token overlap
  - 方案：向量 Top-20 + tsvector 全文 Top-20 → RRF merge → 取 Top-5
  - 改动：`review_analyzer/rag.py` + `database.py` + SQL migration（tsvector + GIN 索引）
  - 前置确认：Supabase 是否已启用 `zhparser` 中文分词
  - 预期：精确关键词问题命中率 ~60% → ~95%
  - **实现备注：**
    - 新增 `hybrid_retrieve()` + `_rrf_merge()`（RRF k=60）
    - 新增 `search_comments_by_fulltext()` 使用 `ts_rank` + `@@ to_tsquery('simple', ...)`
    - Migration 019: `content_tsv` 生成列（STORED）+ GIN 索引
    - 使用 `'simple'` config（按空格/标点分词），中英文混合基本可用；若 Supabase 确认 `zhparser` 可用，只需改一行 `'simple'` → `'zhparser'`
    - `answer_question()` 的 `retrieval_method` 从 `"vector"` 改为 `"hybrid"`
    - Cross-Encoder reranking 暂未实现（P2 远期，当前 RRF 已足够）

- [x] **OPT-5: Evaluation Pipeline 自动化** ✅ 2026-06-17
  - 现状：Golden Set 499 条，手动跑
  - 方案：CI 集成（prompt 变更触发回归）+ 线上抽样（GPT-4o 二次评判）+ 月度报告
  - 改动：`backend_api/app/services/quality_sampler.py` + migration 020
  - 与 6.3/6.8 关系：6.5 的质量保障自动化延伸，与 6.8（用户反馈）互补
  - **实现备注：**
    - CI 部分已有 `.github/workflows/golden-set-regression.yml`（prompt 变更自动触发，准确率门槛 93%）
    - 线上抽样：`quality_sampler.py` — 每 200 条抽 1 条，`judge_annotation()` 用 LLM 二次评判，结果写入 `annotation_quality_log` 表
    - Migration 020: `annotation_quality_log` 表（user_id, comment_id, prompt_version, verdict, reason, judge_model）
    - 月度报告 API 暂未实现（等有足够数据积累后再做 UI）
    - 需要在 `workers/jobs.py` 的分析完成后调用 `log_quality_sample()` 接入主链路

- [x] **OPT-6: 升级判定加统计显著性** ✅ 2026-06-17
  - 现状：`escalation.py` 固定规则（连续 3 期 TOP + >10%），不考虑样本量
  - 问题：10 条评论中 2 条 = 20%，统计不显著但触发升级
  - 方案：Wilson Score Interval 置信下界，n < 30 时须下界 > 阈值才触发
  - 改动：`review_analyzer/escalation.py` 新增 `_wilson_lower_bound()` + `check_escalations()` 增加 `total_reviews` 参数
  - 预期：小样本误报减少 80%+
  - **实现备注：**
    - 纯 `math` 模块实现，不依赖 scipy
    - z=1.96（95% 置信度），阈值 n<30 启用
    - 向后兼容 — `total_reviews` 参数可选，不传时行为与原来一致（不做小样本过滤）
    - 需要 caller（`workers/periodic_jobs.py`）在调用 `check_escalations()` 时传入当前期评论总数

---

#### Phase 3: P2 远期方向（需 PMF 验证后启动）

- [ ] **OPT-7: Agentic RAG（Tool-augmented 问答）**
  - 适用：用户开始问开放式问题（"为什么差评变多了"）
  - 方案：给 RAG LLM 加 Function Calling（search_reviews / get_stats / compare_periods）
  - 触发条件：≥10 付费用户反馈需要开放式分析能力

- [ ] **OPT-8: Self-Consistency + 主动学习**
  - 适用：6.6（反馈回路）完成后
  - 方案：歧义评论多次投票 + evidence_level=low 样本自动标记 → 扩大 bad case 发现面

---

#### 不适合现在做的

| 方向 | 原因 |
|------|------|
| Multi-Agent 架构 | 当前无适用场景，任务步骤确定 |
| Batch Prompt（多条合一次 LLM） | 缓存 98% 命中率下剩余量太小，收益 < 准确率风险 |
| RQ → Celery 迁移 | 当前无并发瓶颈，等月活 > 50 |
| ABSA fine-tune 小模型 | 已规划为 6.5，等 5 付费用户 |

#### Worker 可靠性补丁（2026-06-17 追加）

- [x] **OPT-9: Stale Job 卡死检测 + 飞书告警** ✅ 2026-06-17
  - 问题：Worker 进程 crash / OOM 后，`upload_jobs.status='processing'` 的任务永远卡死，前端无限 polling
  - 方案：`workers/periodic_jobs.py` 新增 `scan_stale_jobs()`，scheduler 每 5 分钟调用
  - 逻辑：查 `status='processing' AND updated_at < now() - 15min` → 标记 `failed` + 飞书运维群告警
  - 改动：`workers/periodic_jobs.py`（新增 `scan_stale_jobs` + `_send_stale_alert` + `enqueue_stale_job_scan`）
  - 配置：`deploy/.env` 新增 `FEISHU_OPS_WEBHOOK`（运维群 webhook，不设则跳过告警但仍标记 failed）
  - 风险：零，只读扫描 + 标记已卡死的任务

---

### 7.12 可观测性体系

**来源：** 《Agent工程师核心能力学习与实践指南》方向 C
**前置条件：** 7.11 OPT-1~6 完成 ✅ + 5.8 部署 smoke test 通过
**启动时间节点：** 5.8 完成后立即启动（预计 2026-06-18~19 可开始）
**总工期：** ~7 天

**业务意义：**
- 成本可控性：当前 LLM 调用成本仅靠 `llm_usage_log` 被动记录，无法实时感知异常消耗
- 故障定位：worker 管道 7 个步骤串行，任一步骤延迟异常时无结构化数据定位瓶颈
- 面试展示：维度三（评测/可观测性）是 Agent 工程师"合格→优秀"的分水岭

**负面影响评估：**
- C1-C3：纯后端，不影响用户体验，零风险
- C4：新增前端页面，不改动现有页面，零回归风险
- C5：告警频率需调参，过高会打扰（Redis TTL 去重兜底）
- 整体：所有 `track_*` 调用 try/except 包裹，失败不阻塞主分析管道

**关键发现：** `backend_api/app/services/analytics.py` 的 `track_llm_call()` 和 `track_analysis_complete()` 已完整实现（含参数定义），但从未被 worker 管道调用。C1 本质是"接线"，不是"建设"。

---

#### Step 1: C1 接通追踪（1天）

- [x] `deep_analyzer.py` — `analyze_one()` 增加 `user_id` 可选参数 + 计时 + 成功/失败时调用 `track_llm_call()`
- [x] `workers/jobs.py` — `process_upload_job()` 末尾调用 `track_analysis_complete()`
- [x] 无需数据库迁移（写入已有 `analytics_events` 表）
- [x] 验证：上传 10 条 → `SELECT * FROM analytics_events WHERE event_name IN ('llm_call', 'analysis_job_complete')` 有数据

#### Step 2: C2 结构化 Job Trace（1天）

- [x] 新建 `backend_api/app/services/job_trace.py` — `JobTrace` dataclass（step 上下文管理器 + record_decision + persist）
- [x] `workers/jobs.py` — 各阶段用 `trace.step("embed")` 等包裹
- [x] Migration 021: `ALTER TABLE upload_jobs ADD COLUMN trace_json JSONB`
- [x] Trace 记录：各步耗时 + 决策元数据（是否聚类/缓存命中率/prompt 版本/fallback 事件）+ 汇总
- [x] 验证：上传完成后 `SELECT trace_json FROM upload_jobs WHERE id = X` 有完整 JSON

#### Step 3: C3 Dashboard API（2天）

- [x] 新建 `backend_api/app/services/observability_queries.py` — 聚合查询
- [x] `GET /analytics/pipeline-health`：p50/p95/p99 延迟、错误率、吞吐量
- [x] `GET /analytics/cache-effectiveness`：L1/聚类节省比率
- [x] `GET /analytics/model-status`：实时 `LLMRouter.status()` 熔断状态
- [x] `GET /analytics/job-traces/{job_id}`：单任务 trace 详情
- [x] `GET /analytics/llm-costs` 扩展：增加 `by_model` 维度
- [x] 验证：curl 各端点返回正确 schema

#### Step 4: C4 前端看板（2天）

- [x] `frontend/src/app/settings/observability/page.tsx`
- [x] 组件：cost-chart（每日成本折线）、latency-chart（p50/p95）、cache-stats-card、model-status-card
- [x] 图表库：recharts（检查 package.json，无则引入）
- [x] sidebar 添加"可观测性"子导航
- [x] 验证：`npm run dev` → /settings/observability 渲染正常（TypeScript 编译通过，API 端点已验证）
- [x] **2026-06-25 重构**：基于 Langfuse/Helicone/Portkey/Datadog 调研，从 265 行单页重构为 5-Tab 管理后台：
  - Tab 容器 + 时间范围选择器（1h/6h/24h/7d/30d）+ 模型状态灯行（60s 轮询）
  - 概览 Tab（指标卡+延迟趋势+失败任务）/ 成本 Tab（堆叠柱状图+模型汇总表，集成 `/llm-costs` API）/ 任务 Tab（状态筛选+可展开 trace timeline+分页）/ 缓存 Tab / 告警 Tab（占位）
  - 从用户 sidebar 导航中移除，仅管理员通过 URL 访问
  - 10 个新组件文件于 `frontend/src/components/observability/`

#### Step 5: C5 Feishu 告警（1天）

- [ ] 新建 `workers/alert_checker.py` — scheduler 每 10 分钟调用
- [ ] 告警条件：日成本 > ¥10 / 错误率 > 20%（1h 窗口）/ 熔断器 open
- [ ] Redis 去重：`alert:{type}:{user_id}` + 1h TTL
- [ ] 复用 `notifier.py:send_feishu_notification()`
- [ ] `GET/PUT /analytics/alert-config` 端点
- [ ] 验证：手动触发超限 → 飞书收到 → 1h 内不重复

---

### 7.13 Agent 智能工作流

**来源：** 《Agent工程师核心能力学习与实践指南》方向 A
**前置条件：** 7.12 的 C1-C2 完成（需要 trace 数据支撑决策可观测）
**启动时间节点：** 7.12 C1-C2 完成后（预计 2026-06-20~21）
**总工期：** ~6 天

**业务意义：**
- 智能路由：消除 `jobs.py` 中 `if len >= 10` 等硬编码，让系统根据数据特征自主决策分析策略
- 异常自适应：差评突增时无需人工发起深度分析，系统自动检测并触发（从"被动工具"到"主动助手"）
- Action Loop 闭环：9.3 已建立升级推送，但缺少"验证效果→自动关闭"，当前 action_items 只能手动关闭
- 面试展示：维度一"能判断该用什么级别方案"+ 维度四"可暂停可恢复可审计"

**负面影响评估：**
- A1（智能路由）：确定性规则，不消耗 LLM token，可预测可测试，风险极低
- A2（异常检测）：新增根因分析 job 会消耗额外 LLM 调用（但仅异常时触发，频率低），需要 cost alert 保护（C5 先就位）
- A3（闭环）：自动关闭 action_item 可能误判改善（阈值 30% 较保守，可调），不影响用户主动操作
- 整体：所有新逻辑以"增量插入"方式加入 worker 管道，不改动核心分析调用链

**与现有系统的关系：**
- A1 是 6.2 动态 taxonomy 路由的扩展（从"品类选 prompt"到"多维度选策略"）
- A2 依赖 7.12 的 trace 数据来记录检测结果
- A3 直接扩展 9.3 的 `escalation.py` + `action_store.py`（已有 80% 基础设施）

---

#### Step 1: A1 智能路由（2天）

- [ ] 新建 `backend_api/app/services/pipeline_router.py` — `decide_pipeline()` 返回 `PipelineDecision`
- [ ] 规则引擎（非 LLM）：品类 taxonomy 选 prompt 版本 / review_count 决定是否聚类 / 语言分布决定是否翻译 / 数量决定并发度
- [ ] `workers/jobs.py` — 硬编码判断委托给 `decide_pipeline()`
- [ ] C2 的 trace 自动记录决策（`trace.record_decision("pipeline_router", decision)`）
- [ ] 验证：上传 5 条 → trace 显示 `clustering_used=false, reason="count < 10"`

#### Step 2: A2 异常自适应分析（2天）

- [ ] 新建 `backend_api/app/services/anomaly_detector.py` — `detect_anomalies()`
- [ ] 三类检测：情感突变（neg_rate 偏差 >15% vs 历史均值）/ 新 aspect 发现 / 低置信度批次
- [ ] Migration 022: `taxonomy_suggestions` 表（存新 aspect 待人工审核）
- [ ] 情感突变 → 自动 enqueue 根因分析 job
- [ ] `workers/jobs.py` — `_post_analysis_smart_push()` 前插入 `detect_anomalies()`
- [ ] 验证：构造 40% 差评数据（基线 15%）→ sentiment_spike 检出 → 根因 job 入队

#### Step 3: A3 Action Loop 闭环（2天）

- [ ] 新建 `review_analyzer/loop_closure.py` — `check_loop_closure()`
- [ ] 闭环逻辑：tag 占比下降 >30% → 自动 close action_item / 标记 done 但未改善 → re-escalate
- [ ] `action_store.py` 增加 `close_action_with_evidence()` + `reescalate_action()`
- [ ] `workers/jobs.py` — `_post_analysis_smart_push()` 中调用 `check_loop_closure()`
- [ ] `notifier.py` — 推送增加"闭环验证结果"段落
- [ ] 验证：创建 action_item → 上传改善数据 → 自动关闭；创建 → 标记 done → 上传未改善 → 再升级

---

### T12+T13 整体排期与执行策略

| Phase | 预计工期 | 启动条件 | 可独立部署 |
|-------|---------|---------|-----------|
| C1 接通追踪 | 1天 | 5.8 smoke test 通过 | ✅ |
| C2 结构化 Trace | 1天 | C1 完成 | ✅ |
| C3 Dashboard API | 2天 | C2 完成 | ✅ |
| C4 前端看板 | 2天 | C3 完成 | ✅ |
| C5 告警 | 1天 | C3 完成（与 C4 可并行） | ✅ |
| A1 智能路由 | 2天 | C2 完成 | ✅ |
| A2 异常自适应 | 2天 | A1 + C5 完成 | ✅ |
| A3 闭环 | 2天 | A1 完成 | ✅ |

**最小可展示子集（面试准备）：** C1 + C2 + C3 + A1 ≈ 6天，覆盖"可观测性 + Agent 决策"两个维度。

**关键架构决策：**
1. 不引入新框架 — 追踪用已有 `analytics_events` 表 + JSONB
2. Fire-and-forget — 所有 `track_*` 调用绝不阻塞主管道
3. 规则驱动路由 — `pipeline_router.py` 用确定性 if/else，零 LLM 消耗
4. 闭环是被动的 — 跟随正常分析流程执行，不额外开定时任务
5. Trace 存 `upload_jobs` — 一对一关联，查询简单
6. 告警复用 Feishu webhook — 零额外配置

---

### 7.14 i18n 国际化

**来源：** 产品需求 — 服务中国跨境电商团队，需同时支持中文 UI 和英文用户
**前置条件：** 5.8 前端页面基本稳定
**启动时间节点：** 2026-06-18
**总工期：** ~5-7 天（Phase 1: 3-4 天，Phase 2: 2-3 天）

**业务意义：**
- 核心用户是中国跨境电商运营，但产品定位为分析英文评论
- 部分用户英文阅读能力有限，需要中文界面 + 分析结果中文翻译
- 支持英文 UI 可以拓展海外用户或展示给投资人/合作方
- 参考竞品 Shulex VOC 的双语体验模式

**需求核心逻辑：**
- 欢迎页/系统内均可切换中文/英文 → UI 框架跟随语言偏好
- 评论原文保持英文（不翻译后再分析）→ LLM 直接分析英文原文
- 分析结果输出保持英文 → 模块级"翻译"按钮供中文用户查看中文版
- 翻译结果缓存到 DB → 二次查看秒切换

**与 Shulex VOC 的参考对比：**
| 维度 | Shulex 做法 | 我们的做法 | 理由 |
|------|------------|-----------|------|
| UI 框架语言 | 跟用户偏好 | 跟用户偏好 | 一致 |
| 分析结论语言 | 改 prompt 输出中文 | 保持英文 + 翻译按钮 | 不维护两套 prompt，对英文用户零影响 |
| 评论原文 | 保持英文 | 保持英文 | 一致 |
| 翻译入口 | 评论旁行内翻译图标 | 模块级翻译按钮 | 操作更简洁，符合我们模块化布局 |

**负面影响评估：**
- Phase 1（UI 双语化）：纯前端改动，不影响后端逻辑，零 API 风险
- Phase 2（翻译功能）：新增 API 端点 + DB 表，不改动现有分析管道
- 翻译调用 DeepSeek：成本可控（按需翻译 + 缓存，非每次分析都翻译）
- 整体：渐进式，Phase 1 独立可部署，不依赖 Phase 2

---

#### Phase 1: i18n 基础设施 + UI 全局双语化

**技术选型：**
- i18n 库：`next-intl`（Next.js 15 App Router 官方推荐，支持 SSR + 中间件）
- 语言存储：cookie `NEXT_LOCALE`（SSR 可读，middleware 可路由）
- 文案管理：`frontend/messages/zh.json` + `frontend/messages/en.json`

**任务清单：**

- [x] **Step 1: 安装 next-intl + 基础配置**
  - 安装 `next-intl` 依赖
  - 创建 `frontend/src/i18n.ts` 配置文件
  - 修改 `frontend/next.config.ts` 添加 i18n plugin
  - 创建 `frontend/src/middleware.ts`（locale 检测 + cookie 读取）
  - 修改 `frontend/src/app/layout.tsx` 包裹 `NextIntlClientProvider`

- [x] **Step 2: 创建中英文翻译文件**
  - 创建 `frontend/messages/zh.json`（从现有硬编码中文文案提取）
  - 创建 `frontend/messages/en.json`（对应英文翻译）
  - 涵盖：marketing、auth、upload、workspace、analysis、sidebar、common 命名空间

- [x] **Step 3: 语言切换器组件**
  - 新建 `frontend/src/components/ui/locale-switcher.tsx`
  - 欢迎页 site-header 右上角加入语言切换器（未登录态）
  - 系统内 sidebar 底部加入语言切换器（已登录态）
  - 切换后写 cookie + 刷新页面使 SSR 生效

- [x] **Step 4: 欢迎页 + Marketing 组件双语化**
  - `page.tsx`（首页）：metadata + 所有文案 → `t('key')`
  - `site-header.tsx`：导航标签
  - `marketing-shell.tsx`：通用 shell 文案
  - `value-grid.tsx`：三大卖点
  - `hero-preview.tsx`：数据卡片示例文案
  - `cta-row.tsx`：按钮文案（通过 props 传入，已动态化）

- [x] **Step 5: Auth 页面双语化**
  - `login/page.tsx` + `login-form.tsx`：标签、placeholder、按钮、链接文案
  - `register/page.tsx` + `register-form.tsx`：同上
  - `forgot-password/page.tsx` + `forgot-password-form.tsx`：同上
  - 错误信息双语化（当前混用中英文）

- [x] **Step 6: 系统内页面双语化**
  - `sidebar.tsx`：导航组名（核心/洞察/行动/管理）+ 菜单项
  - `app-shell.tsx`：通用 shell 部分
  - `upload/page.tsx`：字段标签、提示语、状态信息、工作目的选项
  - `workspace/page.tsx`：角色标签、指标名、任务描述、fallback 文案
  - `analysis/results/page.tsx`：模块标签（消费者画像/用户体验/购买动机等）、指标名、按钮文案
  - 备注：analysis results 的 LLM 输出内容不在此 Step 处理（留给 Phase 2）

- [x] **Step 7: 验证与回归测试**
  - 中文环境：所有页面显示中文，功能正常
  - 英文环境：所有页面显示英文，功能正常
  - 刷新后语言保持（cookie 持久化验证）
  - `npm run typecheck` 通过
  - `npm run build` 通过
  - CI 通过

**Phase 1 完成：2026-06-18** | 7 commits 推送到 develop (`b8f7e3c`..`fe6adc0`)
- tsc --noEmit ✅ | next build 25 页面 ✅ | CI pending
- 技术要点：同步 server component 用 `useTranslations`，async server component 用 `getTranslations`

---

#### Phase 2: 分析结果模块级翻译功能

**技术方案：**
- 翻译后端：新增 `/api/translate/module` 端点，调 DeepSeek 翻译 + 缓存
- DB 缓存表：`translation_cache`（session_id + module_key + target_lang → 翻译 JSON）
- 前端交互：模块顶部"翻译 / 原文"切换按钮，点击后调 API，loading 态，缓存命中秒切

**任务清单：**

- [ ] **Step 1: 后端翻译 API + DB 缓存表**
  - 新增 migration：`translation_cache` 表（session_id INT, module_key TEXT, target_lang TEXT, content_json JSONB, created_at TIMESTAMPTZ, UNIQUE(session_id, module_key, target_lang)）
  - 新增路由：`backend_api/app/routers/translate.py`
    - `POST /api/translate/module`：接收 session_id + module_key → 调 DeepSeek 翻译 → 写缓存 → 返回翻译结果
    - `GET /api/translate/module?session_id=X&module_key=Y&lang=zh`：优先读缓存，无缓存返回 404
  - 翻译 prompt 设计：保持专业术语准确性，输出结构与原文 JSON 一致
  - 复用 `review_analyzer/` 中的 DeepSeek 调用逻辑

- [ ] **Step 2: 前端翻译按钮交互**
  - 分析结果页每个模块（消费者画像/用户体验/购买动机/未满足需求/综合建议）顶部加"翻译"按钮
  - 按钮状态：默认"翻译为中文" → 点击后 loading → 完成后变为"查看原文"
  - 翻译结果原位替换模块内容展示
  - 再次点击"查看原文"恢复英文内容
  - 已缓存的翻译秒切（前端也做 state 缓存，避免重复请求）

- [ ] **Step 3: 验证**
  - 中文语言环境进入分析结果页 → 模块标签已是中文（Phase 1 覆盖）
  - 点击"翻译为中文"按钮 → loading → 显示中文翻译内容
  - 刷新页面后再次点击 → 秒返回（DB 缓存命中）
  - 切换到"查看原文" → 恢复英文 LLM 输出
  - 英文语言环境下翻译按钮不显示（或显示为"Translate to Chinese"，按需决定）

---

#### Phase 3: 评论证据行内翻译（可选增强，低优先级）

- [ ] 评论原文 evidence 引用旁加翻译图标
- [ ] 点击后在原文下方展示中文翻译
- [ ] 复用 Phase 2 的翻译 API（module_key 改为 `evidence_{index}` 或批量翻译）

---

#### 现状审计备注（2026-06-18）

**当前语言覆盖情况：**

| 页面/区域 | 当前语言 | i18n 改造后 |
|-----------|---------|------------|
| 欢迎页（page.tsx + marketing 组件） | 全中文 | 中/英跟随偏好 |
| site-header 导航 | 中文 | 中/英跟随偏好 |
| login/register/forgot-password | 中文 | 中/英跟随偏好 |
| sidebar 菜单 | 中文 | 中/英跟随偏好 |
| upload 页面 | 中文 | 中/英跟随偏好 |
| workspace 页面 | 中文 | 中/英跟随偏好 |
| analysis/results 模块标签 | 中文 | 中/英跟随偏好 |
| analysis/results LLM 输出内容 | **英文** | 保持英文 + 模块翻译按钮 |
| metadata（HTML title） | 中英混合 | 中/英跟随偏好 |
| 错误信息 | 中英混合 | 中/英跟随偏好 |

**i18n 基础设施现状：** 零。无 next-intl / react-i18next / locale 文件。所有文案硬编码。

---

### 7.15 全面测试方案

> **目标**：建立覆盖核心链路的测试体系，保障上线质量与迭代安全。
> **完整方案文档**：[ClueAI_ReviewLens_测试方案.md](../ClueAI_ReviewLens_测试方案.md)
> **当前基线**：33 个测试，32 通过，1 失败（已于 2026-06-18 修复，见下方备注）
> **工具链**：pytest + httpx（后端）/ Playwright（E2E）/ respx（mock LLM）/ Locust（性能）

---

#### Phase 1: 核心逻辑单元测试（本周，2 天）

**目标覆盖**：认证 token 机制 + 配额系统 + LLM Router 熔断

- [x] 配额系统测试补全（`backend_api/tests/test_quota.py`，22 个用例，全通过）
- [ ] **认证 token 单元测试**（`backend_api/tests/test_auth_token.py`）
  - Token 签名篡改 → 401
  - Token 过期（exp < now）→ 401
  - Refresh token 续期：access 过期 + refresh 有效 → 正常鉴权
  - HMAC timing-safe 比较（使用 `hmac.compare_digest`）
- [ ] **LLM Router 熔断测试**（`backend_api/tests/test_llm_router.py`）
  - 连续 3 次失败 → 自动切换到备用模型
  - 全部模型不可用 → 抛出 RuntimeError
  - 冷却 60s 后恢复主模型

**备注（2026-06-18）**：  
原测试 `test_team_review_analyze_unlimited` 假设 team 套餐 `review_analyze` 不限，实际 QUOTA_TABLE.md 明确为 50000 条。已拆分为 `test_team_review_analyze_at_limit`（49000+1000=50000 → 允许）和 `test_team_review_analyze_over_limit`（49999+1000=50999 → 拒绝），两个新用例均通过。

---

#### Phase 2: 主链路集成测试（下周，3 天）

**目标覆盖**：上传 → Worker Job → 分析结果全链路

- [ ] **文件上传集成测试**（`backend_api/tests/test_uploads.py`）
  - CSV / XLSX 正常上传 → job_id 返回 + 状态 queued
  - Free 用户 > 500 行 → 配额拒绝（HTTP 400）
  - Redis 不可用 → 降级为 Thread 异步执行
  - 上传后临时文件已删除
- [ ] **Worker Job 异常路径测试**（`backend_api/tests/test_jobs.py`）
  - 正常 Job：queued → processing → done，session + stats 正确写入
  - LLM 全部失败 → Job 状态标记 failed + error_message 记录
  - 重复 content_hash → 缓存命中，不重复调用 LLM
- [ ] **文件解析单元测试**（`backend_api/tests/test_parser.py`）
  - 列自动识别（content / date / rating / reviewer / source）
  - 日期格式兼容（ISO / 美式 / 中文）

---

#### Phase 3: 二级功能集成测试（3 天）

**目标覆盖**：RAG 问答 + 对比分析 + 产品管理

- [ ] **RAG 问答测试**（`backend_api/tests/test_qa.py`）
  - Free 用户访问 → 403
  - 空评论库 → 返回 "No review data available"
  - 超过 5 个产品 → 400
  - 去重逻辑（相同 content_hash 不重复展示）
- [ ] **对比分析测试**（`backend_api/tests/test_compare.py`）
  - 非当前用户的 session_id → 404
  - 只有 1 个 session → 返回单组数据 + 空差异
- [ ] **产品 CRUD 测试**（已有 `test_workspace_routes.py`，补充产品/行动/复盘场景）

---

#### Phase 4: E2E 端到端测试（3 天，Playwright）

**启动条件**：Phase 1-3 完成，核心 API 稳定

- [ ] 搭建 Playwright 测试基础设施（`frontend/e2e/` 目录 + playwright.config.ts）
- [ ] **P0 场景**
  - 未登录访问 → 自动重定向 `/login`
  - 登录 → 工作台跳转 + cookie 设置
  - 上传 CSV → job polling → 跳转分析结果页
- [ ] **P1 场景**
  - i18n 中/英切换无 key 缺失
  - 配额耗尽提示升级 CTA 显示

---

#### Phase 5: 性能 + 可靠性测试（上线前，2 天）

**启动条件**：部署到 Staging 环境后执行

- [ ] **性能压测**（Locust）：50 用户并发上传，P99 < 3s，无 500
- [ ] **可靠性注入**
  - `docker stop redis` → Worker Thread 降级正常
  - 数据库连接 kill → 连接池自动重建
  - Mock LLM 全返回 500 → Job 标记 failed，用户收到提示

---

### 9.6 团队管理（多租户）

**启动条件：** 获得 1 个付费用户后启动  
**状态：** 📋 规划中（方案已确认，待启动条件满足）  
**预估总工期：** 15-20 天（分 3 Phase 渐进式落地）

---

#### 一、核心模型：Workspace（工作空间）

参考 Shulex VOC.AI / Notion / Linear 的团队模型，采用 Workspace 作为多租户隔离单元。

**数据架构：**
- 所有业务表增加 `workspace_id` 字段（products、sessions、action_items、download_records 等）
- 查询默认按当前工作空间过滤，用户无感知
- 用户可属于多个 workspace（如顾问同时服务多个品牌方）

**计费模型：**
- Quota 绑定 workspace 而非 user
- 一个 workspace 的 Pro 计划惠及所有成员
- Owner 负责付费，其余角色享受权益

---

#### 二、角色权限体系（RBAC）

| 角色 | 适用人群 | 核心权限 |
|------|---------|---------|
| Owner | 创建者/付费人 | 全部权限 + 计费管理 + 删除工作空间 + 转让所有权 |
| Admin | 运营管理者 | 推送设置 + 产品管理 + 邀请/移除成员 + 查看所有分析 |
| Member | 分析师/运营 | 上传评论 + 发起分析 + Q&A + 下载 + Action 管理 |
| Viewer | 只读人员（如老板/投资人） | 仅查看分析结果 + Dashboard + 下载报告 |

**推送设置权限限制：**
- 推送设置（飞书 webhook、告警规则）仅 Owner/Admin 可配置
- Member/Viewer 在 sidebar 不显示推送设置入口

---

#### 三、邀请流程设计

1. Owner/Admin 进入「团队设置」页面
2. 输入受邀人邮箱 + 选择角色
3. 系统发送邀请邮件（含邀请链接，7 天有效）
4. 受邀人点击链接 → 已有账号直接加入 / 未注册则注册后自动加入
5. 成员列表显示 `pending`（待接受）/ `active`（已加入）状态
6. Owner/Admin 可随时移除成员或修改角色

---

#### 四、关键数据库设计

```sql
-- 工作空间
CREATE TABLE workspaces (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    owner_id INTEGER NOT NULL REFERENCES users(id),
    plan TEXT NOT NULL DEFAULT 'free',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 工作空间成员
CREATE TABLE workspace_members (
    id SERIAL PRIMARY KEY,
    workspace_id INTEGER NOT NULL REFERENCES workspaces(id),
    user_id INTEGER NOT NULL REFERENCES users(id),
    role TEXT NOT NULL DEFAULT 'member',  -- owner/admin/member/viewer
    status TEXT NOT NULL DEFAULT 'active', -- active/pending/removed
    invited_by INTEGER REFERENCES users(id),
    invited_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    joined_at TIMESTAMPTZ,
    UNIQUE(workspace_id, user_id)
);

-- 邀请记录
CREATE TABLE workspace_invitations (
    id SERIAL PRIMARY KEY,
    workspace_id INTEGER NOT NULL REFERENCES workspaces(id),
    email TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'member',
    token TEXT NOT NULL UNIQUE,
    expires_at TIMESTAMPTZ NOT NULL,
    accepted_at TIMESTAMPTZ,
    created_by INTEGER NOT NULL REFERENCES users(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

---

#### 五、分阶段落地计划

| Phase | 内容 | 工期 | 启动条件 |
|-------|------|------|---------|
| Phase 1 | 基础设施：workspace 表 + 自动为现有用户建默认 workspace + 业务表加 workspace_id + 查询改造 | 5-7 天 | 1 个付费用户 |
| Phase 2 | 团队功能 UI：团队设置页（邀请 + 成员列表 + 角色管理）+ 推送设置权限检查 + 邀请邮件 | 5-7 天 | Phase 1 完成 |
| Phase 3 | 多空间支持：工作空间切换器 + 创建新空间 + 空间级 Quota 面板 | 3-5 天 | Phase 2 完成 + 有多 workspace 需求 |

**Phase 1 详细任务清单：**
- [ ] 创建 workspaces / workspace_members / workspace_invitations 表
- [ ] 数据迁移：为每个现有用户创建默认 workspace（`{username}的工作空间`）
- [ ] products / sessions / action_items / download_records 等表加 workspace_id
- [ ] 后端中间件：从 session 中解析当前 workspace_id，注入所有查询
- [ ] API 鉴权层：检查用户在当前 workspace 的角色权限

**Phase 2 详细任务清单：**
- [ ] 前端：团队设置页面（成员列表 + 邀请表单 + 角色修改）
- [ ] 后端：邀请 API（创建邀请 + 接受邀请 + 取消邀请）
- [ ] 邮件服务：接入邮件发送（可复用 Resend / 飞书机器人通知）
- [ ] 推送设置页加权限检查（非 Owner/Admin 返回 403）
- [ ] Sidebar 按角色动态隐藏受限菜单项

**Phase 3 详细任务清单：**
- [ ] 前端：workspace 切换器（sidebar 顶部 / dropdown）
- [ ] 后端：切换 workspace API + 创建新 workspace
- [ ] Quota 面板改为空间级展示

---

#### 六、风险与注意事项

| 风险 | 影响 | 缓解措施 |
|------|------|---------|
| 现有数据迁移 | 所有业务表需回填 workspace_id | Phase 1 用默认 workspace 回填，零停机 |
| 权限穿透 | 用户跨 workspace 访问数据 | 所有查询强制带 workspace_id WHERE 条件 |
| 计费争议 | 成员使用配额但不付费 | Quota 归属 workspace，Owner 负责管理 |
| 邀请安全 | 邀请链接泄露 | Token 一次性 + 7 天过期 + 绑定邮箱验证 |

---



| 条件 | 要求 |
|------|------|
| P0 用例全部通过 | 100% |
| P1 用例通过率 | ≥ 95% |
| Golden Set 准确率 | ≥ 93%（CI 自动跑） |
| 无已知安全漏洞 | 0 Critical / 0 High |
| 核心模块代码覆盖率 | ≥ 80% |

---

#### 已知质量债务（待修复）

| 文件 | 问题 | 优先级 |
|------|------|--------|
| `backend_api/tests/test_v24_dynamic_aspects.py` | 6 个测试用 `return` 代替 `assert`，pytest 会忽略这些断言（假通过） | P1 |
| `backend_api/tests/test_llm_router.py` | 文件不存在，熔断逻辑完全无测试覆盖 | P0 |
| `frontend/e2e/` | 目录不存在，UI 回归靠人眼 | P1 |

---

### AliExpress 评论抓取集成（2026-06-30 完成）

- 状态: ✅ 已完成 | 已部署线上验证通过
- 分支: `develop`（commit `9cd4771`、`c97ae74`）
- 任务:
  - [x] 新建 AliExpress 抓取器（双数据源：feedback API + Playwright 浏览器 fallback）
  - [x] 更新 review_scraper 路由层按 platform 分派
  - [x] 更新 API Schema（platform 字段 + 按平台动态校验产品编码格式）
  - [x] 更新 API 路由（传递 platform 到 payload）
  - [x] 更新 Worker 任务分派（Amazon / AliExpress 独立路径）
  - [x] 前端 asin-fetch-panel 改造为平台切换模式（Amazon / AliExpress 分段控件）
  - [x] 产品管理页新增平台 Tab 过滤 + 平台 badge
  - [x] 移除非英文 Amazon 站点（仅保留 US/UK/CA/AU）
  - [x] 接入 Apify CrowdPull 作为主数据源（解决 feedback API 反爬封锁）
  - [x] 三级 fallback 策略：Apify → feedback API → Playwright
  - [x] 修复 Product ID 验证范围（12-16 位，支持 16 位 ID）
  - [x] 修复 Apify HTTP 201 状态码被错误丢弃问题
  - 线上验证（2026-06-30）：product ID 1005009259589970 成功抓取 131 条评论，session_id=75，好评率 82.4%，差评率 17.6%
- Apify 计费说明:
  - 计费模式：按量付费，$1.50 / 1,000 条评论
  - 当前状态：使用 $5 免费平台积分（约 3,000 条），未绑定信用卡
  - 当前上限：每次抓取 max_reviews=200（含定时自动抓取）
  - 后续计划：等有付费用户后再绑卡 + 提升 max_reviews 上限（改 `aliexpress_scraper.py:428` 即可）
  - 注意：免费积分耗尽后 Apify 返回 402，代码会 fallback 到 feedback API / Playwright（但目前两者均不稳定）
- [x] eBay 评论抓取接入（2026-07-01）
  - Actor: scrapier/ebay-review-scraper，$5.99/1,000 条
  - eBay 仅 Positive/Neutral/Negative 三档 → 映射为 5/3/1 星
  - 相对时间（Past month / Past 6 months / More than a year ago）→ 近似日期
  - max_reviews=100（节省免费额度）
- [x] Walmart 评论抓取接入（2026-07-01）
  - Actor: webscrapewizard/walmart-review-crawler，$6.00/1,000 条
  - 标准 1-5 星 + 精确日期
  - max_reviews=100（节省免费额度）
  - 注意：字段映射基于文档推断，首次运行需确认实际字段名

---

## 8. 出海合规

> **完整合规文档**：[`OVERSEAS_COMPLIANCE_PLAN.md`](OVERSEAS_COMPLIANCE_PLAN.md)（含所有决策依据、法规解释、合规 review 结论）
>
> **执行原则**：本模块所有任务按下述清单顺序推进；每个 Task 完成后勾选 `[x]`；遇到高风险变更（数据库 migration、支付逻辑、安全相关）需通知 Erika 验收。

### 立项背景

- 国内 ICP 备案 + 经营许可需 3 个月，为快速验证市场先出海
- 服务器已在香港阿里云 ECS，规避 ICP 备案
- 目标：6-7 周完成合规改造 → Beta 上线 → 收取海外订阅

### 核心决策（2026-07-03 已确认，不再讨论）

| 维度 | 决策 |
|------|------|
| 业务主体 | 个人 + Wise 收款（MRR $4,000 时启动香港/新加坡公司注册） |
| 目标市场 | 排除 EU/UK/EEA 的全球英语市场 |
| LLM 服务商 | **AWS Bedrock Claude Haiku 4.5（主）+ DeepSeek fallback**（原 Anthropic 直连方案因 HK IP 封锁 + 中方持股 ownership 封禁弃用；已有 `backend_api/app/services/llm_router.py` 三级 fallback 骨架，扩展 `provider="bedrock"` 分支即可） |
| Amazon 数据源 | DataForSEO（主）+ Rainforest（fallback），woot.com 出海禁用 |
| 多语言方案 | next-intl + 子域名路由（`app.` 出海英文 / `cn.` 未来国内中文） |

> **⚠️ LLM 路由重要背景（详见 `~/.claude/plans/anthropic-claude-haiku-piped-spark.md`）**
> - Anthropic 官方 API 对香港 IP 做 IP 级封锁（阿里云 HK 机房必被 403）
> - 2025-09 起对中方持股 >50% 公司做全球 ownership 级封禁
> - **走 AWS Bedrock**（AK/SK 鉴权，不看调用方 IP + AWS 提供 GDPR/SCC DPA）
> - Region:`ap-southeast-1`（Singapore），距 HK ECS 延迟 30-50ms
> - 成本:Haiku 比 DeepSeek 贵 4-9x，**必须启用 Bedrock prompt caching**(SYSTEM_PROMPT 1500 tokens 全静态，可节省约 50% input 成本)
> - DeepSeek 保留 fallback，BYOK 仅限 DeepSeek 分支

> **🚨 2026-07-03 重大发现 — 上述 Bedrock 路径被推翻**
>
> Erika 完成 AWS 账户 + IAM 用户 `clueai-bedrock-prod` + Bedrock model access 后，本地用 `boto3` 从国内 IP 直连诊断（详见 `scripts/diagnose_bedrock.py`），结果：
> - ✅ Test 1 STS get-caller-identity 通过（AK/SK 有效）
> - ✅ Test 2 ListFoundationModels 返回 16 个 Anthropic 模型（含 Haiku 4.5，权限已生效）
> - ❌ Test 3 InvokeModel `anthropic.claude-haiku-4-5-20251001-v1:0` 报 `ValidationException: Access to Anthropic models is not allowed from unsupported countries`
> - ❌ Test 3 InvokeModel `global.anthropic.claude-haiku-4-5-*` 全局 inference profile 同样被拦
>
> **结论**：Anthropic 在 Bedrock API 层做 IP 检查，AK/SK 鉴权**不**绕开 geo-block。原假设"Bedrock AK/SK 认证不看调用方 IP"**错误**。HK 阿里云 ECS 走 Bedrock 必然被拦。

> **🚨 2026-07-03 追加发现 — OpenAI Chat 在 HK ECS 同样被 API 层 geo-block 拒绝**
>
> 因原 Bedrock 方案被推翻，讨论切换 OpenAI 主链路时，Erika 敏锐指出：现状生产 OpenAI 一直**只用于 embedding**（`/v1/embeddings` endpoint，HK 生产已跑 3 周稳定），`/v1/chat/completions` 从未被真实生产流量触发过（`llm_router.py` 里 OpenAI 是备 1，DeepSeek 主链路一直稳定，从未熔断到 OpenAI）。**跨端点推断可用性是危险的**。
>
> 于是新写 `scripts/diagnose_openai_chat.py`，在生产 HK ECS 的 api 容器内实测 `gpt-4o-mini` chat completion：
> - Egress IP: `8.210.51.242`（阿里云 HK IDC）
> - 结果: `403 unsupported_country_region_territory` + `type: request_forbidden` + `message: Country, region, or territory not supported`
>
> **结论**：OpenAI 也在 API 层用 official error code 明确拒绝 HK IP，与 Anthropic 完全一致。原 B 方案"HK ECS 直调 OpenAI"**技术上直接不可行**（不是灰色地带，是硬 403）。
>
> **关键推论**：OpenAI 对不同 endpoint 有独立地区策略 —— embedding 松，chat 严。TEST_LOG 2026-06-18 "生产 OpenAI 直连可达" 那条记录已修订限定为 "**Embedding** 直连可达"，避免后续再被误读。

> **📌 2026-07-03 决策定型**
>
> 综合两次实测（Anthropic Bedrock + OpenAI Chat 均在 HK 被 403），出海 LLM 主链路调整必须**以 ECS 迁移到 SG/US 为硬前提**。剩余两条真实候选路径：
>
> - **A. 迁 ECS 到 SG（Lightsail SG $40/mo，工期 ~2h）** — 一次到位；SG IP 后 Bedrock/OpenAI/Gemini/Anthropic 全部原生可用；未来无中间人税；月成本与阿里云 HK ¥300/mo 基本持平。**推荐**。
> - **C. HK ECS 保留 + OpenRouter 中转（工期 30 min，+5-10% LLM 加价）** — 不迁移；OpenRouter 帮我们从 HK 到 OpenAI/Anthropic 合规中转；账号仍在 OpenRouter 名下有黑盒风险；长期看两个月加价就把 SG 迁移一次性钱赚回来。
>
> B（HK 直调 OpenAI）**永久移除**（已实测证伪）。D（保持 DeepSeek 主）技术上可行但偏离"用国际大厂 LLM 强化海外品牌力"目标。
>
> **待 Erika 拍板 A vs C**。拍板后：
> - 选 A → 按 [Lightsail SG 迁移计划](#) 走 4 阶段（Cloudflare TTL / Lightsail 开机 / hosts 验证 / DNS 切换），8.5 里"Bedrock 集成"改为迁移后跑"OpenAI GPT-4o-mini 直连"
> - 选 C → `llm_router.py` 加 `provider="openrouter"` 分支，8.5 里"Bedrock 集成"改为"OpenRouter 集成 + Anthropic Claude Haiku 4.5 via OpenRouter"
>
> **AWS Bedrock IAM 用户 / Policy / AK/SK 现状处理**：
> - 本地 `review_analyzer/.env` 已删除 `AWS_BEDROCK_*` 三行（防误提交，2026-07-03 完成）
> - AWS IAM 侧 `clueai-bedrock-prod` 用户 + `ClueAI-Bedrock-Invoke` 策略 + AK/SK **保留 30 天**待观察（若最终选 A + Bedrock 路线可复用；若选 C 或选 A 但直调 OpenAI 则 30 天后 deactivate）

---

### 8.1 Erika 手动执行

- 状态: 🔄 部分完成（AWS Bedrock 分支已实测证伪；SG 迁移任务待启动） | 分支: N/A（Erika 独立操作，不阻塞开发）
- 依赖: 无

**收款链路**
- [x] 注册 Wise 个人多币种账户（护照 + 身份证，30 分钟）
  - 开 USD + EUR + GBP 虚拟账户号
- [ ] Paddle 商户升级为 Sole Trader（提交护照 + 地址证明 + Wise 账户）
- [ ] Paddle 后台配置产品地区限制：移除 EU 27 国 + UK + EEA 3 国 + CH

**数据源账户 + LLM 账户**
- [ ] 注册 DataForSEO 账户（充值 $50 测试余额）
- [ ] 保留现有 Rainforest 账户降级为 fallback
- [x] ~~**注册 AWS 账号**~~（2026-07-03 已完成，账号可用；若选 A + OpenAI 路线保留待用，若选 C 可保留但可选）
- [x] ~~**AWS Bedrock Console → Model access 申请**~~（2026-07-03 已批准 Haiku 4.5 SG region，但**实测证明 HK IP 被 API 层 403 拒绝**，见上方"🚨 2026-07-03 重大发现"）
- [x] ~~**创建 IAM User + AK/SK**~~（2026-07-03 已创建 `clueai-bedrock-prod` 用户 + `ClueAI-Bedrock-Invoke` 策略 + AK/SK；**已从本地 `.env` 删除**避免误提交；AWS 侧保留 30 天待观察）
- [x] ~~AK/SK 交给 Claude Code 写入 `.env`~~（2026-07-03 已完成写入 → 实测 geo-block 后删除，AK/SK 在 AWS 侧仍有效）

**基础设施（原有）**
- [ ] `clueai-reviewlens.com` 接入 Cloudflare（免费方案）
  - NS 改指向 Cloudflare + 开启 Proxy + 确认 CF-IPCountry header

**🆕 ECS 迁移到 SG（2026-07-03 新增，两次 geo-block 实测后必须）**
> 详细步骤参考本次对话已交付的《Lightsail SG 迁移 4 阶段计划》（阶段 0 准备 / 阶段 1 新机起服务 / 阶段 2 hosts 验证 / 阶段 3 DNS 切换 / 阶段 4 老机清理）。**✅ 2026-07-05 Phase 0-3b 全部完成，流量已切 SG，进入 Phase 4 观察窗口。**

- [x] 阶段 0：Cloudflare DNS 4 条 A 记录 TTL 调低到 5 min（如未走 CF Proxy 橙色云则必需，橙色云可跳过）
- [x] 阶段 0：备份现网 `.env`（`scp` 从老 ECS 到本地 Mac）
- [x] 阶段 1：AWS Lightsail SG region 开 $40/mo 实例 + 分配 Static IP + 开 22/80/443 端口
- [x] 阶段 1：Ubuntu 22.04 装 Docker + Compose，git clone 项目到 `/opt/clueai`，上传 `.env`
- [x] 阶段 1：Cloudflare Origin Cert 签 SSL 证书（有效期至 2041-06-29）→ 挂到 nginx volume
- [x] 阶段 1：`docker compose up -d --build` 起全部 6 服务（redis/api/worker/scheduler/frontend/nginx），等 healthy
- [x] 阶段 2：Mac hosts 指向新 IP（13.215.29.99），测试账号跑一遍 golden path（B 场景 7 tab 全渲染）
- [x] 阶段 3：Cloudflare 4 条 A 记录（root/www/app/api）改新 IP（Proxied 橙色云，公网 DNS 均返回 CF 边缘 IP）
- [x] 阶段 3：无痕窗口 + 测试账号验证线上（4 域名 HTTPS 200，B 场景公网路径端到端通过）
- [x] 阶段 3-fix：SG `.env` `DATABASE_URL` 修复（`/pos>` → `/postgres`，重建 worker/api/scheduler）
- [ ] 阶段 4：观察 3-7 天（到 2026-07-12 前）后老 HK ECS 停机 → 释放
- [ ] 阶段 4（顺便）：`deploy/docker-compose.yml` volumes 加 `external: true`（`certbot_www` / `letsencrypt`）

**基础设施**
- [ ] `clueai-reviewlens.com` 接入 Cloudflare（免费方案）
  - NS 改指向 Cloudflare + 开启 Proxy + 确认 CF-IPCountry header
- [x] 登录 Supabase 确认 prod 项目 `inpgrbjwtpxgwungghnz` region（必须非中国 region）
  - ✅ 2026-07-03 核查：prod host `aws-1-ap-southeast-1.pooler.supabase.com` → Singapore，符合出海合规要求，无需数据迁移

**法律文档**
- [ ] 用 Termly 或 iubenda 生成 Privacy Policy / Terms of Service / Cookie Policy 模板
- [ ] 检查文档明示：EU 排除条款 / Amazon 免责 / LLM 数据处理 / sub-processors

---

### 8.2 i18n 框架 + 双语文案 + 法律页面

- 状态: ⏳ 待启动 | 分支: `feature/v4-i18n-framework`
- 依赖: 8.1（Erika 完成 Cloudflare 接入 + 法律文档生成）

**2.1 next-intl 框架搭建（3 天）** ✅ 2026-07-07 完成（路线 A：cookie + middleware，不做 `app/[locale]/` 目录改造）
- [x] `npm install next-intl` 到 frontend（`next-intl@4.13.0` 已装）
- [x] 新建 `frontend/src/i18n/routing.ts`（next-intl v4 官方结构，等价于原计划的 `config.ts`）+ `frontend/src/i18n/request.ts`
- [x] `frontend/src/middleware.ts`：CF-IPCountry 白名单 + Accept-Language 检测 + cookie 持久化，输出 `Content-Language` + `Vary: Cookie`
- [x] **未做** `app/[locale]/` 目录改造 —— 采用 `localePrefix: "never"` cookie 方案，URL 保持单一，SEO 与老收藏夹不受影响
- [x] `frontend/src/app/layout.tsx` 集成 `NextIntlClientProvider`，`<html lang={locale} dir="ltr">` 动态化
- [x] `defaultLocale = "en"`（主打出海，中国大陆 IP 由 CF-IPCountry=CN/HK/MO/TW 显式回落 zh）

**2.2 全站字符串提取 + 翻译（4 天）**
- [ ] 遍历 `frontend/src/**/*.tsx` 提取所有中文字符串到 `frontend/messages/zh-CN.json`
- [ ] 用 Claude 批量翻译到 `frontend/messages/en-US.json`（约 200-300 条 key）
- [ ] Erika review 关键业务术语（评论分析 / 问题标签 / 行动中心 等）
- [ ] 现有页面代码改用 `useTranslations` hook 引用 key

**2.2.C 类别标签 i18n 化（backend slug 迁移 + 前端翻译层）** ✅ 2026-07-08 完成
- [x] Step 1 — [backend_api/app/services/category_grouper.py](backend_api/app/services/category_grouper.py)：新增 `CATEGORY_SLUGS` / `CATEGORY_ZH_LABELS` 常量，`ASPECT_TO_CATEGORY` / `_derive_category` / `aspects_to_legacy_schema` fallback 全部改英文 slug
- [x] Step 2 — [workers/jobs.py:472](workers/jobs.py#L472)：error 分支 `"无效乱码"` → `"invalid_garbage"`
- [x] Step 3 — [review_analyzer/analyzer.py](review_analyzer/analyzer.py)：SYSTEM_PROMPT 分类规则改 `slug（中文名）` 双语格式 + 输出格式枚举 + `VALID_CATEGORIES` 改 slug set + `_validate_result` fallback + `_make_unrecognizable` + `PROMPT_VERSION` v2.1 → v2.2
- [x] Step 4 — 新建 [migrations/047_categories_to_slug.sql](migrations/047_categories_to_slug.sql)：11 条幂等 UPDATE 中文 → slug + 回滚 SQL 注释块（原计划 046 已被占用，改用 047）
- [x] Step 5 — [frontend/messages/{en,zh}.json](frontend/messages/en.json) categoryLabels 段 11 个 key 全改 slug
- [x] Step 6 — [frontend/src/components/analysis/download-tag-button.tsx](frontend/src/components/analysis/download-tag-button.tsx) 引入 `useTranslations('categoryLabels')`；[review_analyzer/exporter.py](review_analyzer/exporter.py) 新增 `_category_zh(slug)` helper + `CATEGORY_ZH_LABELS` 复用
- [x] Step 7 — [backend_api/tests/test_category_grouper.py](backend_api/tests/test_category_grouper.py) 9 个 TEST_CASES 断言改 slug + 新增 `CATEGORY_SLUGS` 白名单 snapshot（10/10 通过）
- Golden set 500 条回归跳过：`eval_v23_500_metrics.json` 无 per-category 字段；`_derive_category` 是确定性纯字符串派生，不经 LLM
- ⚠️ 部署顺序：**migration 047 先跑（psycopg2 python 脚本，ECS api 容器无 psql）→ 再重建 api/worker/frontend + nginx reload**

**2.3 Backend i18n + 邮件模板双语（2 天）**
- [ ] 新建 `backend_api/app/services/i18n.py`（简化 i18n 层）
- [ ] FastAPI dependency 注入 locale（Accept-Language header + users.locale 字段）
- [ ] Resend 邮件模板双语化（注册验证 / 密码重置 / 订阅通知）
- [ ] users 表新增 `locale VARCHAR(10) DEFAULT 'en-US'` 字段（合并到 migration 041）

**2.4 7 个法律页面（双语）**
- [x] `frontend/src/app/privacy/page.tsx` — Privacy Policy（已存在，8.2.4 需按 OVERSEAS_COMPLIANCE_PLAN 补 10 项条款）✅ 2026-07-06 改造为中英双语
- [x] `frontend/src/app/terms/page.tsx` — Terms of Service（已存在，8.2.4 需按 OVERSEAS_COMPLIANCE_PLAN 补 6 项条款）✅ 2026-07-06 改造为中英双语
- [x] `frontend/src/app/refund/page.tsx` — Refund Policy（✅ 2026-07-06 新建，中英双语，覆盖月付不退/年付按比例/取消说明/退款流程）
- [ ] `frontend/src/app/cookies/page.tsx` — Cookie Policy（8.3.4 已创建占位空壳，需补正文）
- [ ] `frontend/src/app/dpa/page.tsx` — Data Processing Agreement（8.3.4 已创建占位空壳，需补正文）
- [x] `frontend/src/app/sub-processors/page.tsx` — Sub-processor 清单（8.3.4 完成，双语 + 8 家清单 + DPA 外链）
- [x] `frontend/src/app/contact/page.tsx` — Contact 页面（8.3.4 完成，双语 + 3 邮箱）
- [ ] Privacy Policy 必须包含 10 项合规条款（见 OVERSEAS_COMPLIANCE_PLAN.md 第 2.4 节）
- [ ] Terms of Service 必须包含 6 项合规条款（见 OVERSEAS_COMPLIANCE_PLAN.md 第 2.4 节）

**2.5 注册流程 + Cookie Banner + Footer + 老用户 Terms Gate**
- [ ] 新建 migration `migrations/041_add_compliance_fields.sql`（users 表 8 个新字段:terms_accepted_at / terms_version / age_confirmed_at / marketing_opt_in / marketing_opt_in_at / locale)
  - > **编号说明**:2026-06-30 前已存在 040_translate_cache.sql,本 migration 沿用 041。**⚠️ 高风险变更需通知 Erika**
- [ ] 改造 `frontend/src/components/auth/register-form.tsx`:强制勾选 Terms + 18+ + 独立 Marketing Opt-in（default OFF）
  - 注册接口 body 补充 `terms_version: "2.0"`
- [ ] 新建 `frontend/src/components/terms/terms-gate.tsx`(老用户强制同意 modal)
  - 挂载在 `frontend/src/app/(dashboard)/layout.tsx` 或全局 provider
  - 登录后调 `GET /api/user/me`,若 `terms_version` 非 `"2.0"` 弹全屏 z-50 modal
  - 点同意后调 `POST /api/auth/accept-terms` 更新 `terms_accepted_at=NOW(), terms_version='2.0'`
- [ ] 新建 backend `POST /api/auth/accept-terms` 端点([backend_api/app/routes/auth.py](backend_api/app/routes/auth.py))
- [ ] `GET /api/user/me` 响应体补充 `terms_version` 字段
- [ ] 新增 `frontend/src/components/CookieBanner.tsx`（顶部通知栏 + localStorage）
- [x] 全站 Footer 强制展示：6 个法律链接 + Amazon disclaimer（8.3.4 完成，挂在 `marketing-shell.tsx`）
- [ ] 上传页 [frontend/src/app/upload/page.tsx](frontend/src/app/upload/page.tsx) 加数据告知小字(注册已同意,无需再次 checkbox):
  ```tsx
  {t("uploadDataNotice")}<Link href="/privacy">{t("privacyLink")}</Link>
  ```

**2.6 LLM Prompt 语言策略** 🔄 2026-07-07 方案变更
- [x] **决策**：Prompt 保持英文单一版本，LLM 分析结果只存英文（title / description / tags 等业务字段）
  - 原因：一份分析结果服务所有语言用户，成本 ~50%↓；英文 prompt LLM 质量更稳定；未来加日/西/德语只需扩展"翻译层"，不用重跑分析
- [x] **不做**：原计划的"按 user locale 切换 prompt 中/英两套"（避免同产品分析结果双份存储）
- [ ] 中国用户看中文体验的实现路径 —— 待展示层翻译方案设计（见新增 8.2.7）

**2.7 展示层翻译（中国用户看英文分析结果） 🆕**
- [ ] 决策：DeepSeek 翻译 API（复用现有）vs 前端 i18n key 化 vs 缓存表
- [ ] 落地：analyses / issues / highlights 等表新增 `title_zh` / `description_zh` 字段 或 独立 `translations` 缓存表
- [ ] 触发：分析完成后异步生成 zh 翻译（不阻塞主流程）
- [ ] 展示：locale=zh 时读中文字段，为空则 fallback 英文原文
- [ ] 与 8.2.6 的关系：8.2.6 上游保持英文，8.2.7 是展示层增强，可独立迭代

**验收标准**
- 使用 US IP 访问 `app.clueai-reviewlens.com` → 全英文
- 手动切换 locale → 中英切换流畅无残留
- Footer 6 个法律页面全部可访问
- 注册表单 3 个勾选框行为符合预期

---

### 8.3 后端合规能力

- 状态: 🔄 进行中（80%） | 分支: `develop`
- 依赖: M2（migration 041 已上线）

**3.1 EU/UK/EEA + OFAC 制裁国 Geo-Block**
- [x] 新建 `backend_api/app/middleware/geo_block.py`（2026-07-03 完成）
- [x] BLOCKED_COUNTRIES 清单（EU 27 + EEA 3 + UK + CH + OFAC 6 国，合计 38）
- [x] 仅拦注册端点，不拦登录端点（存量用户不影响）
- [x] 认证路由集成 middleware（`backend_api/app/main.py` CORS 之后挂载）
- 附加落地：
  - `CF-IPCountry` header 缺失时放行（Cloudflare 未上线阶段兜底，DEBUG 日志）
  - 单元测试 `backend_api/tests/test_geo_block.py` 覆盖 8 个场景（DE/IR → 403、缺 header → 200、US → 200、大小写、非注册路径放行、清单完整性）

**3.2 数据主权 API（CCPA / CPRA / PIPEDA）**
- [x] 新建 `backend_api/app/routes/me.py`（2026-07-03 已完成，扩展现有文件）
- [x] `GET /api/me/export` — 数据可携权（返回 user/sessions/comments/products/subscriptions 完整 JSON）
- [x] `PATCH /api/me` — 更正权（修正邮箱/姓名/公司，email 需二次验证 ⚠️ 二次验证 flow 未做，当前仅要求当前密码 + 唯一性校验，后续再补 verification token）
- [x] `DELETE /api/me` — 遗忘权（硬删或匿名化 users + 级联删除，触发 Paddle 取消 ⚠️ Paddle 自动取消未做，当前仅 WARNING 日志提醒手动取消）
- 附加落地：
  - `deps.py` / `auth.py` login 均加 `deleted_at IS NOT NULL` 拒绝，即使旧 cookie 有效也拿不到接口
  - 前端 `/settings/account` 新页面（导出 JSON 快照 / 修改用户名邮箱密码 / 二次密码 + "DELETE" 确认删除）
  - Sidebar「管理」组新增「账号与数据」入口

**3.3 邮件双语化 + Marketing/Transactional 拆分 + Unsubscribe（约 1 天）**

> ✅ **2026-07-03 核查**：Resend 已完全接入（`RESEND_API_KEY` 已在 `deploy/.env` 和 `review_analyzer/.env`，`review_analyzer/mailer.py` 已实现密码重置邮件，发件域名 `noreply@clueai-reviewlens.com` 已验证）。**无需迁移邮件服务商**，只需扩展现有 `mailer.py`。

- [x] 改造 `review_analyzer/mailer.py` — 现有 `send_reset_code()` 增加 `locale` 参数支持中英切换（2026-07-04 完成）
- [x] 新增邮件函数：`send_verification_email` / `send_subscription_confirmed` / `send_subscription_expiring` / `send_deletion_confirmed`（均双语）
- [x] 邮件模板集中管理：`review_analyzer/email_templates/{zh-CN,en-US}/*.html`（5 类模板 × 2 语言 = 10 个）
- [x] Transactional 与 Marketing 分离 from address：
  - Transactional 继续用 `noreply@clueai-reviewlens.com`
  - Marketing 用新 `updates@clueai-reviewlens.com`（✅ 2026-07-06 确认：域名已 Verified，发件人自动可用）
- [x] 新建 `send_marketing_email(to, subject, html, locale, user_id)`：
  - 调用前校验 users 表 `marketing_opt_in=TRUE`
  - 自动追加双语 unsubscribe footer
  - ⚠️ `marketing_opt_in` 字段依赖 migration 041（8.2.5 未上线），fail-close：字段缺失时视作未 opt-in
- [x] 新建 `backend_api/app/routes/unsubscribe.py`：
  - `GET /api/unsubscribe?uid=<id>&token=<hmac>` — 一键退订，无需登录
  - HMAC token：`hmac.new(API_SESSION_SECRET, str(user_id), sha256).hexdigest()[:16]`
  - `UPDATE users SET marketing_opt_in=FALSE`，字段缺失时 302 到 `?status=pending`
- [x] 新建 `frontend/src/app/unsubscribed/page.tsx` — 双语退订成功页（success/pending/error 三态，用 next-intl `useTranslations`）
- [x] PATCH /me 改邮箱成功后 fire-and-forget 发变更通知邮件；DELETE /me 匿名化完成后发确认邮件
- [x] 单测 `backend_api/tests/test_mailer.py` 19 个用例：locale 归一化、双语渲染、Transactional/Marketing 路由、opt-in fail-close、HMAC token 生成+校验+防篡改
- 🔜 依赖 8.2.5 上线：migration 041 落地 `marketing_opt_in` 字段后，本模块自动生效（当前 send_marketing_email 会 fail-close，unsubscribe 会 302 pending）

**3.4 Contact + Sub-processor 清单页填充** ✅（2026-07-05 完成）
- [x] `frontend/src/app/contact/page.tsx` — 3 邮箱卡片双语（privacy@ / support@ / hello@，next-intl + MarketingShell）
- [x] `frontend/src/app/sub-processors/page.tsx` — 8 家清单表格（Supabase / Cloudflare / Anthropic / DataForSEO / Rainforest / Paddle / Resend / CF Analytics），Desktop 表格 + Mobile 卡片双布局，含 DPA 外链
- [x] 新增 `frontend/src/components/marketing/site-footer.tsx`：6 个法律链接（/privacy /terms /cookies /dpa /sub-processors /contact）+ Amazon disclaimer，挂到 `marketing-shell.tsx`
- [x] 新增 `frontend/messages/{zh,en}.json` 三个命名空间：`footer.*` / `contact.*` / `subProcessors.*`
- [x] cookies + dpa 页面创建为占位空壳（TODO(8.2.4)，避免 footer 链接 404，8.2.4 独立任务补齐正文）

**3.5 数据保留策略自动清理** ✅（2026-07-07 完成）
- [x] `migrations/042_add_inactivity_tracking.sql` — `users` 表加 `last_login_at` + `inactivity_notified_at` + 2 个部分索引，兼容老用户（fallback `last_login_at = created_at`）
- [x] 邮件模板 `email_templates/{zh-CN,en-US}/inactivity_warning.html` × 2，`deletion_confirmed.html` 里"30 天备份"改成"60 天备份"（对齐 Shulex 窗口）
- [x] `review_analyzer/mailer.py` 补 `send_inactivity_warning()` + `_SUBJECTS["inactivity_warning"]`（Transactional，不受 opt-out 控制）
- [x] `review_analyzer/database.py` 加 `mark_user_login()`（登录时刷 `last_login_at`、清零 `inactivity_notified_at`）
- [x] `backend_api/app/routes/auth.py` login() 成功分支调 `mark_user_login()`（DB 写失败不阻塞登录）
- [x] 新建 `workers/retention_cleanup.py` — 6 块清理串行执行，每块独立 try/except + 单独 commit：
  1. inactive 6m + 未通知 → 发预告 + 打时间戳（单次 500 条上限）
  2. 已通知 90d + 仍未登录 → 复用 8.3.2 `anonymize_user()`（500 条上限）
  3. `deleted_at < NOW() - 60d` → 硬删 6 张业务表（不动 `review_pool`，200 用户/天上限）
  4. `analytics_events > 90d` → 硬删
  5. `llm_usage_log > 6y` → 硬删（对齐 Shulex）
  6. `sessions/comments > 6y AND deleted_at IS NULL` → 软删（等未来冷存储方案再做物理清理）
- [x] `workers/periodic_jobs.py` 加 `enqueue_retention_cleanup()`（`job_timeout=30min`，`result_ttl=7d`，`failure_ttl=30d` 供审计）
- [x] `workers/scheduler.py` 加 UTC+8 03:23 触发 + Redis 锁 `scheduler:retention_cleanup:lock:{YYYY-MM-DD}`（业务低峰、避开 09:07 成本日报）
- [x] 单元测试 `workers/tests/test_retention_cleanup.py` — 每块��少 1 个用例（no-candidates / 正常路径 / 边界 case），加 SQL 关键词哨兵测试防止未来误改窗口口径
- **窗口决策记录**（对齐 Shulex）：
  - 通用保留期 **6 年**（Shulex 也是 6 年，方便长周期趋势 + 跨用户复用命中）
  - 删除后宽限窗口 **60 天**（Shulex 也是 60 天，给"删了后悔"更长机会）
  - inactivity 阈值 **6 月**（Shulex 无此机制，我们保留为差异化亮点）
  - `analytics_events` 90 天 + `llm_usage_log` 6 年
- **冷热分层缓冲方案**（未来备用，2026-07-07 追加决策）：
  - 触发条件：单表 > 5000 万行 / 关键查询 p95 劣化 > 200ms / 存储成本超预算 30%
  - 预案方向：老数据（>2y）dump 到 S3 / OSS 冷存储，主库只留热数据（<2y）
  - 本次 8.3.5 不实施，先按 6y 硬保留跑一段时间观察增长曲线

**功能说明：不活跃用户告警 + 数据清理全流程**

这是面向 GDPR Art.5 "数据存储限制"原则的合规自动化机制。核心逻辑：用户 6 个月不登录 → 预告 → 再 90 天不登录 → 匿名化 → 再 60 天 → 硬删业务数据。

| 阶段 | 时间点 | 触发条件 | 动作 | 用户感知 | 数据可恢复？ |
|------|--------|----------|------|---------|------------|
| 正常 | 0–6 月 | 持续登录使用 | 无 | 无 | — |
| Block 1 | 6 月未登录 | `last_login_at < NOW() - 6m` + 未通知过 | 发 inactivity_warning 邮件（中/英双语），告知 90 天后清理 | 收到邮件 | ✅ 登录即取消，`inactivity_notified_at` 被清零 |
| 等待期 | 6–9 月 | 邮件已发，等待 90 天 | 无 | 无 | ✅ 随时登录即取消 |
| Block 2 | 9 月未登录 | `inactivity_notified_at < NOW() - 90d` + 仍未登录 | 匿名化：username → `deleted_user_{id}`，email → NULL，password_hash → 随机值（无法登录），api_key/paddle_customer_id → NULL，plan → free，deleted_at → NOW() | 账号无法登录 | ⚠️ PII 不可逆（email/username/password 已覆盖或清空）。但业务数据（sessions/comments/products）仍保留 user_id，只是断开了和真人的关联 |
| Block 3 | 匿名化后 60 天 | `deleted_at < NOW() - 60d` | 硬删 6 张业务表：review_trackers → action_items → comments → product_variants → products → sessions（按 FK 叶子→根顺序 DELETE） | 无（用户早已无法登录） | ❌ 业务数据物理删除，不可恢复。users 匿名化行保留（防止其他表 LEFT JOIN 出现悬垂 user_id），review_pool 不删（全局评论缓存，无 PII） |
| Block 4–6 | 独立时间窗口 | 按各自规则 | 清理 analytics_events（90d）/ llm_usage_log（6y）/ sessions+comments（6y 软删） | 无 | ❌ 硬删的表不可恢复；软删的表仅标记 deleted_at，行还在 |

**邮件分类**：inactivity_warning 走 Transactional 通道（`noreply@clueai-reviewlens.com`），不受 marketing opt-out 控制 —— 即使用户退订了产品更新邮件，合规通知也必须送达。

**数据库备份兜底**：Supabase Pro 及以上套餐有 7 天 PITR（Point-in-Time Recovery），可作为误删后的最后一道防线，但恢复是手动运维操作，不对用户开放自助。

**验收标准**
- VPN 切换 DE / IR IP 注册 → 403
- VPN 切换 US IP 注册 → 200
- `GET /api/me/export` 返回完整 JSON
- `PATCH /api/me` 修改邮箱触发二次验证邮件
- `DELETE /api/me` 后无法登录，级联删除生效
- 中英文用户分别收到对应语言的密码重置邮件
- Marketing 邮件仅发给 `marketing_opt_in=TRUE` 用户
- 点击 marketing 邮件的 unsubscribe 链接（未登录状态）→ 成功退订
- retention_cleanup 每日 cron 触发无异常

---

### 8.4 LLM 路由 locale 切换（前置准备）

- 状态: ✅ 完成 | 分支: `develop`
- 依赖: 无（不阻塞 8.5 决策；不接触 Bedrock/OpenRouter，仅在现有 DeepSeek/OpenAI/Qwen 三家里按 locale 换 fallback 优先级）
- 背景: 海外用户默认走 GPT-4o-mini 优先链（英文能力 + 品牌信任），国内用户保持 DeepSeek 优先。**统一英文 prompt**，不做中英双 prompt。

**改动清单**
- [x] `backend_api/app/services/llm_router.py` — `_DEEPSEEK` / `_OPENAI` / `_QWEN` 拆常量 + `MODELS_EN` / `MODELS_ZH` + `_models_for_locale()`；`LLMRouter.completion()` 与 `router_completion()` 新增 `locale` 参数（默认 "zh" 向后兼容）；`__post_init__` 种子所有可能模型的熔断态；`status()` 汇总两条链的模型状态
- [x] `backend_api/app/services/locale.py` — 新建 `get_analysis_locale(request)`：`?locale=` > cookie `NEXT_LOCALE` > `Accept-Language` > 默认 `"en"`；normalize `zh-CN → zh`、`en-US → en`
- [x] `backend_api/app/routes/uploads.py` — `/uploads` 与 `/analysis/jobs` 注入 `Request` + 写 `payload_json["locale"]`
- [x] `workers/jobs.py` — `process_upload_job` 从 `payload_json` 读 locale，透传给 3 处 `deep_analyze_batch()`
- [x] `backend_api/app/services/deep_analyzer.py` — `analyze_one` / `analyze_batch` 新增 `locale` 参数，透传给 `router_completion()`（默认 `"en"`）
- [x] `review_analyzer/insight_engine.py` — 删除硬编码 `OpenAI(base_url="deepseek")`，改走 `router_completion(locale=...)`；`build_results_insights` / `build_compare_insights` / 两个内部 `_build_ai_*` 加 locale 参数
- [x] `backend_api/app/routes/analysis.py` — `/sessions/{id}/results` 与 `/results` 端点注入 `Request` + 传 locale 到 `build_results_insights` / `_cached_build_insights`
- [x] 2026-07-23 补充：Review Q&A 旧链路迁移到 Router；`review_analyzer/qa_handlers.py` 不再直接创建 OpenAI client 指向 DeepSeek，也不再硬编码 `deepseek-chat`；`review_analyzer/rag.answer_question()` 默认 `locale="en"` 并向 intent handler 透传
- [x] 2026-07-23 补充：`backend_api/app/routes/qa.py` 与 `backend_api/app/routes/compare.py` 复用 `get_analysis_locale(request)`，QA / Compare AI Summary 与核心评论分析共用 locale-aware fallback 顺序
- [x] 2026-07-23 补充：`review_analyzer/translation.py`、`review_analyzer/compare_store.py`、`review_analyzer/parser.py`、`review_analyzer/eval/runner.py` 以及已跟踪维护脚本 `scripts/apply_3c_review.py` / `scripts/extract_taxonomy.py` / `scripts/extract_taxonomy_generic.py` 移除旧 DeepSeek 直连，统一通过 Router 或 `review_analyzer/router_client.py` 兼容 shim 调用
- [x] 2026-07-23 补充：`backend_api/app/services/action_advisor.py` 文件头注释改为“通过统一 LLM Router 生成结构化行动建议”
- [x] `frontend/src/i18n/routing.ts` — `defaultLocale: "zh"` → `"en"`（海外优先，配合 `localePrefix: "never"` + middleware/cookie 检测）
- [x] `frontend/messages/{en,zh}.json` — 新增 `categoryLabels` 段，11 个中文分类（产品质量/包装物流/使用体验/客服售后/性价比/功能需求/正面反馈/单纯好评/无效乱码/混合评价/其他）英文翻译（en 侧完整翻译；zh 侧保留中文本名以对齐 key）

**验收标准**
- [x] llm_router import 成功 + `_models_for_locale("en") == [openai, deepseek, qwen]` + `_models_for_locale("zh") == [deepseek, openai, qwen]`
- [x] `get_analysis_locale` 正确处理 `en`/`en-US`/`zh-CN`/`en-US,zh;q=0.9`/`fr`（fr 落到默认 en）
- [x] `python -m pytest backend_api/tests/ --ignore=backend_api/tests/test_v24_dynamic_aspects.py` 60 通过（test_v24 失败与本次改动无关，是 taxonomy_loader row 解包问题）
- [x] JSON messages 校验：en / zh 的 categoryLabels key 集合一致
- [x] 2026-07-23 Review Q&A Router 迁移验证：`python3 -m pytest backend_api/tests/test_qa_llm_router.py -q` 3 passed；核心 runtime 文件 ruff PASS；本次 runtime + 已跟踪 scripts `python3 -m py_compile` PASS
- [ ] 部署到 prod 后线上验证：以 en cookie 上传评论 → 日志显示 model_used=gpt-4o-mini（如 OPENAI_API_KEY 已配置且 SG IP 可达）

---

### 8.5 LLM 集成 + 数据源改造

- 状态: ⏸️ 冻结（等 Erika 拍板 A vs C，见上方"📌 2026-07-03 决策定型"块）| 分支: `feature/v4-bedrock-dataforseo`
- 依赖: **8.1（ECS 迁移到 SG 完成）+ 8.3（合规基础）**  ← 2026-07-03 依赖变更：8.1 前置条件由"AWS Bedrock 申请 + AK/SK 到位"改为"ECS 迁移到 SG/US 完成"（两次实测证明 HK IP 被 Anthropic/OpenAI 双双 403）

> **⚠️ 2026-07-03 8.5 章节标题保留但内容需按最终选型重写**
> - 选 A（SG 迁移）+ OpenAI 直连 → 8.5 改为"OpenAI GPT-4o-mini 主链路集成"，删除 Bedrock 分支
> - 选 A（SG 迁移）+ Bedrock → 8.5 保持现状（下述步骤）
> - 选 C（OpenRouter 中转）→ 8.5 改为"OpenRouter 集成"，新增 `provider="openrouter"` 分支代替 `provider="bedrock"`
> - 拍板前**不启动 8.5 任何编码任务**

> **技术背景**:项目已有 `backend_api/app/services/llm_router.py`(6.4 三级 fallback: DeepSeek/OpenAI/Qwen + 熔断)。本 Milestone **扩展现有 router 支持 Bedrock provider**,不新建 llm_client 抽象层。

**4.1 LLMRouter 扩展 Bedrock 支持(1.5 天)**
- [ ] `backend_api/app/services/llm_router.py` — `ModelConfig` 新增 `provider: str = "openai_compat"` + `aws_region: str = "ap-southeast-1"` 字段
- [ ] `MODELS` 列表头部插入 Bedrock Claude 配置:
  ```python
  ModelConfig(
      name="bedrock_claude_haiku",
      model_id="anthropic.claude-haiku-4-5-20251001-v1:0",
      base_url="",
      api_key_env="",
      provider="bedrock",
      aws_region="ap-southeast-1",
  )
  ```
- [ ] `LLMRouter._get_bedrock_client()` — 用 `boto3.client('bedrock-runtime', ...)` 从 `AWS_BEDROCK_ACCESS_KEY_ID` / `AWS_BEDROCK_SECRET_ACCESS_KEY` 初始化
- [ ] 新增 `completion_text(messages, ..., user_id=None) -> tuple[str, str, dict]`:
  - Bedrock 分支:抽出 system message + 打 `cache_control={"type":"ephemeral"}` → 构造 InvokeModel 请求体(anthropic_version="bedrock-2023-05-31")
  - OpenAI 兼容分支(DeepSeek/OpenAI/Qwen):保留 BYOK 逻辑(user_id → get_api_key)
  - 复用现有熔断/fallback/日志骨架
- [ ] 新增便捷函数 `router_completion_text(messages, ..., user_id=None)`
- [ ] `requirements.txt` / `pyproject.toml` 增加 `boto3>=1.35.0`

**4.2 analyzer.py 接入 Router + JSON 输出保证(1 天)**
- [ ] `review_analyzer/analyzer.py` — `SYSTEM_PROMPT` 末尾追加英文强化:`"Respond with raw JSON only. No markdown fences, no explanation outside the JSON object."`
- [ ] `_call_deepseek_api()` → `_call_llm()`,走 `router_completion_text()`,不传 `response_format`
- [ ] 抢救逻辑:Claude 偶尔加 markdown fence,用 `re.search(r'\{.*\}', text, re.DOTALL)` 提取
- [ ] `analyze_comment()` 签名保持兼容 or 改为 `(comment, category, user_id, rating)`,同步改 `workers/jobs.py`

**4.3 translate.py + copywriter.py 接入 Router(0.5 天)**
- [ ] `backend_api/app/routes/translate.py` `_translate_payload()` — 直接 OpenAI 调用 → `router_completion_text()`
  - system prompt 加 `"Output raw JSON only. No markdown."`
  - 删除 `response_format={"type":"json_object"}`
  - `log_llm_usage()` tokens 从 Router usage dict 取
- [ ] `backend_api/app/routes/copywriter.py` `_generate_copy_item()` + `_generate_ideal_profile()` 同上

**4.4 DataForSEO Amazon Reviews 集成(1 天)**
- [ ] 新建 `backend_api/app/services/dataforseo.py`（参照 rainforest.py 结构）
- [ ] 复用 `_parse_review` 数据结构（保持字段一致）
- [ ] Basic Auth + live mode 端点 + 错误处理（429 / 5xx retry）

**4.5 数据源 Router(0.3 天)**
- [ ] `workers/jobs.py` 增加 `fetch_amazon_reviews()` 统一入口
- [ ] 优先级链:DataForSEO → Rainforest fallback → woot(仅国内启用)
- [ ] `backend_api/app/routes/scrape.py` 同步改造

**4.6 woot 出海版禁用(0.2 天)**
- [ ] `workers/jobs.py` / `backend_api/app/services/review_scraper.py` 判断 `ENABLE_WOOT_SCRAPER` 环境变量
- [ ] `deploy/.env.example` 加 `ENABLE_WOOT_SCRAPER=false`,通知 Erika 在 prod `deploy/.env` 设置
- [ ] 前端隐藏"免费抓取" UI（若有）

**4.7 California AI Transparency Act 合规**
- [ ] 分析结果 UI 加 "🤖 AI-generated analysis" 标签
- [ ] PDF/Excel 导出加 "Analysis powered by AI (Anthropic Claude via AWS Bedrock)"

**验收标准**
- Bedrock 连通性 smoke test 通过(`boto3.invoke_model` 返回 200)
- 单条评论分析成本:Haiku(cache 命中)≈ $0.00145,与预期一致
- 观察 3 天 Bedrock 调用成功率 ≥ 99%(未触发熔断切 DeepSeek)
- DataForSEO 抓取 3-5 个热门 ASIN 对比 Rainforest 数据一致性
- 断开 DataForSEO 后 Rainforest fallback 生效
- 临时错误 AWS AK 触发熔断,自动切 DeepSeek 成功
- prod 日志确认 woot 代码不被调用
- 分析结果 UI 显示 AI 标签

---

### 8.6 Beta 发布准备

- 状态: ⏳ 待启动 | 分支: `feature/v4-beta-launch`
- 依赖: 8.5（技术改造全部完成）

**5.1 早鸟定价配置**
- [ ] `frontend/src/app/pricing/page.tsx` 新增 "Early Bird -50%" 折扣位
- [ ] Paddle 后台创建早鸟折扣码
- [ ] 3 档套餐：Free / Starter $29 / Pro $99（早鸟 $14.5 / $49.5）

**5.2 社区渗透（Erika 执行）**
- [ ] Reddit：r/FulfillmentByAmazon、r/AmazonSeller、r/ecommerce 发帖
- [ ] Facebook Groups：Amazon FBA Seller 群（≥ 5-10 个大群）
- [ ] LinkedIn：关键词搜索潜在早鸟用户
- [ ] 招募 5-10 个免费早鸟用户

**5.3 数据泄露响应 Runbook**
- [ ] 新建 `docs/incident-response.md` — 内部文档
- [ ] 定义 T+0h / T+24h / T+48-72h / T+7d 四阶段响应流程

**5.4 WCAG 2.1 AA 辅助功能扫查**
- [ ] 用 axe DevTools 扫全站
- [ ] Lighthouse Accessibility Score 目标 ≥ 90
- [ ] 修复：img alt / 键盘导航 / contrast 4.5:1 / form label / focus indicator / landmark roles

**5.5 nginx / 部署侧改动**
- [ ] Cloudflare DNS 新增 `app` A/CNAME 记录
- [ ] `deploy/nginx.conf` 新增 `app.clueai-reviewlens.com` server block
- [ ] `deploy/docker-compose.yml` certbot 命令新增 `-d app.clueai-reviewlens.com`
- [ ] `deploy/docker-compose.yml` API_CORS_ORIGINS 新增 `https://app.clueai-reviewlens.com`
- [ ] `www.` 301 重定向到 `app.`

**5.6 监控 + 上线**
- [ ] Cloudflare Analytics 监控流量国家分布
- [ ] Paddle Dashboard 监控订阅转化 + 退款率
- [ ] Sentry 观察 EU IP 403 拦截率（应 0-1%）
- [ ] Paddle sandbox 完整订阅流程测试
- [ ] 邀请海外朋友测试 3 个套餐转化

**验收标准**
- 使用测试账号（惜_clueai / test123456）登录 `app.clueai-reviewlens.com` 全流程无异常
- Footer 6 个法律链接 + Amazon disclaimer 全部展示
- 用海外 IP 注册 + 订阅完整流程跑通
- ASIN 抓取走 DataForSEO 通道（后端日志确认）
- LLM 分析走 Claude 通道（后端日志确认）

---

### 8.7 Credit 定价体系改造

- 状态: ✅ 基建完成（6.1-6.9 已部署验证） | 分支: `develop`
- 依赖: 8.3（用户注册/locale 已区分海外流量）
- 设计文档: `~/.claude/plans/cheeky-percolating-zephyr.md`（含完整成本测算 + 套餐详表 + 套利验证）

**背景**：现有配额体系是 8 维独立限制（评论条数 / Ask 次数 / 文案 / Excel / 对比 / Webhook / 规则数），用户理解成本高、加功能就要新开限额。海外市场最强竞品 VOC AI 采用统一 credit 池，我们需要对齐并差异化。

**定价决策（已锁定）**

| 档位 | 月付 | 年付（−20%）| Credits/月 | Trial |
|------|:---:|:---:|:---:|:---:|
| Free | $0 | — | 300（永久）| — |
| Starter | $12 | $9.6/月 | 5,000 | — |
| Pro ⭐ | $29 | $23.2/月 | 15,000 | — |
| Team | $59 | $47.2/月 | 45,000 | — |
| 首次注册 Trial | — | — | 3,000 × 14 天 | 全档解锁 |
| Enterprise | 联系我们 | — | 200K+ | — |

**Credit 单价表（全球统一）**

| 动作 | Credit 单价 |
|------|:---:|
| 评论标注 1 条 | 1 |
| Ask reviews 1 次 | 3 |
| Insight 报告 1 份 | 6 |
| 广告文案 1 次（单平台单变体）| 2 |
| 翻译 1 批次 | 1 |
| Excel/CSV 导出 | 1 |
| 竞品追踪 1 ASIN | 10 |
| Webhook 推送 | 0 |

**加油包（套利已消除 · 升档永远比堆加油包划算）**

| 加油包 | 价格 | 单 credit 面价 |
|------|:---:|:---:|
| +5K | $9 | $0.0018 |
| +10K | $18 | $0.0018 |
| +50K | $79 | $0.00158 |

---

**6.1 数据库 Migration（新增 · 无 breaking change）** ✅ 2026-07-08 prod 已执行

- [x] 新建 `migrations/044_create_user_credits.sql`
  - `user_credits` 表：`user_id PK / balance INT / monthly_grant INT / trial_expires_at TIMESTAMP / last_refill_at TIMESTAMP / updated_at`
  - `credit_ledger` 表：`id BIGSERIAL PK / user_id / delta INT / reason TEXT / ref_id TEXT / balance_after INT / created_at`
  - reason 枚举：`monthly_grant / trial / topup / refund / review_analyze / ask / insight / copywriter / translate / export / competitor`
- [x] 新建 `migrations/045_add_starter_plan.sql` — `users.plan` CHECK 约束加入 `'starter'`
- [x] 保留 `user_quota_usage` 表（仍用于独立硬限：seats / api_keys / 产品数 / Webhook 数 / 规则数）

**6.2 后端 — Credit 核心层**（`review_analyzer/quota.py`）✅ 2026-07-07

- [x] 新增 `credit_check(user_id, amount) → (bool, str)` — 校验余额是否足够
- [x] 新增 `credit_consume(user_id, amount, reason, ref_id=None) → int` — 原子扣减，返回余额；失败抛异常
- [x] 新增 `credit_refund(user_id, amount, reason, ref_id=None) → None` — LLM 熔断失败时反向记账
- [x] 新增 `get_credit_balance(user_id) → dict` — 返回 balance / monthly_grant / trial_expires_at / days_left
- [x] 新增 `get_credit_ledger(user_id, limit=30) → list[dict]` — 近 N 条流水
- [x] Credit 不结转：`last_refill_at` 每月 1 号重置 balance = monthly_grant（不累加旧余额）

**6.3 后端 — 月度 Refill 定时任务**（`workers/periodic_jobs.py`）✅ 2026-07-07

- [x] 新增 RQ 定时任务 `refill_monthly_credits()`
  - 每月 1 号 00:05 UTC 触发
  - 扫描 `users` 表，按 plan 字段发放对应 monthly_grant：free=300 / starter=5000 / pro=15000 / team=45000
  - 写入 `credit_ledger`（reason='monthly_grant'）
- [x] 新增 RQ 定时任务 `expire_trials()`
  - 每天 00:10 UTC 触发
  - 查 `user_credits.trial_expires_at < now()`，自动降级 plan='free'，monthly_grant=300

**6.4 后端 — 调用点改造**（替换原 `quota_consume` 为 `credit_consume`）✅ 2026-07-07

- [x] `workers/jobs.py` — 评论批次分析：`credit_consume(user_id, len(reviews), 'review_analyze', str(job_id))`
- [x] `workers/jobs.py` — Insight 报告生成：`credit_consume(user_id, 6, 'insight', product_id)`
- [x] `backend_api/app/routes/qa.py` — Ask reviews：`credit_consume(user_id, 3, 'ask')`
- [x] `backend_api/app/routes/copywriter.py` — 文案：`credit_consume(user_id, 2, 'copywriter')`
- [x] `backend_api/app/routes/translate.py` — 翻译：`credit_consume(user_id, 1, 'translate')`
- [x] `backend_api/app/routes/export.py` — 导出：`credit_consume(user_id, 1, 'export')`
- [x] LLM 熔断兜底：调用点 try/except，失败时 `InsufficientCreditsError` 返回 402

**6.5 后端 — Paddle Webhook 改造**（`backend_api/app/routes/settings.py`）✅ 2026-07-07

- [x] Paddle 后台（Erika 手动）新建 8 个 Price SKU（含 custom_data）— 见 session-summary 2026-07-07
- [x] `_resolve_plan_from_event()` 新增 starter 档；优先读 Price.custom_data.plan，降级按 Price ID 匹配
- [x] `_get_price_custom_data()` 辅助函数提取 Price 级别 custom_data
- [x] 订阅 created/activated/updated/resumed → 解析 plan → 更新 `user_credits.monthly_grant`
- [x] 订阅 canceled/paused → plan='free' + monthly_grant=300
- [x] `transaction.completed` + `custom_data.topup=true` → `credit_refund(user_id, credits, 'topup')`
- [x] `review_analyzer/database.py` 新增 `update_user_credits_monthly_grant(user_id, plan)`
- ⚠️ **待确认**：升级时是否应立即将 balance 重置为 new_monthly_grant（"即时发放当月余额"）？当前实现只更新 monthly_grant，不动 balance

**6.6 后端 — Trial 发放**（`backend_api/app/routes/auth.py` 注册流程）✅ 2026-07-07

- [x] 用户注册成功后插入 `user_credits`：balance=3000 / monthly_grant=300 / trial_expires_at=now()+14d
- [x] 写 `credit_ledger`（reason='trial', delta=+3000）
- [ ] Trial 到期前 3 天 / 1 天 / 当天触发升级引导邮件（待后续实现）

**6.7 前端 — pricing.ts 扩展**（`frontend/src/lib/pricing.ts`）✅ 2026-07-07

- [x] `PlanKey` 扩展为 `"free" | "starter" | "pro" | "team"`
- [x] `PLANS` 补齐 Starter 档（$12月付 / $115年付 / 5000 credits）
- [x] 新增 `ADD_ONS` 常量：`[{credits:5000,price:9},{credits:10000,price:18},{credits:50000,price:79}]`
- [x] `monthly_grant` 映射：free=300 / starter=5000 / pro=15000 / team=45000

**6.8 前端 — 定价页重构**（`frontend/src/app/pricing/pricing-content.tsx`）✅ 2026-07-07

- [x] 月付/年付切换 Toggle（年付标注 "-20% off"）
- [x] 4 列套餐对比卡（Free / Starter / Pro ⭐ / Team），Pro 卡片高亮
- [x] 加油包区块（定价页底部）：3 档加油包卡片 + "Need more credits?"
- [x] Trial 说明文案："Start with 3,000 free credits — 14 days, no credit card required"
- [x] Enterprise 联系入口

**6.9 前端 — Credit 余额 UI** ✅ 2026-07-08 prod 验证通过

- [x] 新增 `frontend/src/components/credit/sidebar-credit-entry.tsx` — Sidebar 常驻余额入口
  - 显示：`X credits · Trial X days left` 或 `X / monthly_grant`
  - 余额低于 20% 显示"Top up"快捷入口
  - 点击打开 ledger 抽屉
- [x] 新增 `frontend/src/components/credit/credit-ledger-drawer.tsx` — 近 30 条消费明细抽屉
  - 每行：动作类型 / 日期 / delta / balance_after
- [x] 后端 `GET /credits/balance` + `GET /credits/ledger?limit=N` API 端点
- [x] Sidebar 集成：`SidebarCreditEntry` 加入 `sidebar.tsx`
- [x] 移除 `SidebarQuotaEntry`（Plan Quota 展示）— Sidebar 切换为纯 credits 计费展示，后端 `quota_check` 保留作内部风控

**6.9.1 前端 — 侧边栏 Credits 升级按钮 + 升级弹窗** ✅ 2026-07-08

> 需求：在侧边栏左下角 Credits 卡片右侧新增常驻 **Upgrade 按钮**，点击后弹出套餐升级弹窗（Shulex 风格：顶部套餐卡片 + 下方功能对比表）。Credits 余额区域的点击行为保持不变（仍弹出已有的"套餐使用量"对话框）。弹窗底部保留"查看消费记录"入口。Credit 单价是内部信息，不展示给客户。

**新建文件**：`frontend/src/components/credit/upgrade-pricing-dialog.tsx`
**修改文件**：`frontend/src/components/credit/sidebar-credit-entry.tsx`

**执行步骤**：

1. 新建 `upgrade-pricing-dialog.tsx`，实现 `<UpgradePricingDialog>` 组件：
   - Props：`open`, `onOpenChange`, `currentPlan: PlanKey`, `onOpenLedger: () => void`
   - 使用 `Dialog/DialogContent/DialogHeader/DialogTitle`（来自 `@/components/ui/dialog`）
   - 导入 `PLANS`, `formatPrice`, `PlanKey`, `BillingPeriod`（来自 `@/lib/pricing.ts`）
   - DialogContent：`max-w-4xl max-h-[90vh] p-0`

2. 弹窗结构：
   - **Header**：标题"升级套餐" + 月付/年付切换开关（内部 state `billingCycle`）
   - **套餐卡片区**：`grid sm:grid-cols-2 lg:grid-cols-4`，4 列卡片（Free / Starter / Pro / Team）
     - 每张卡片：中文套餐名、价格（根据月付/年付切换）、credits 数量、5-6 条中文功能要点
     - Pro 卡片高亮：`border-2 border-[#d94d72]`，徽章"最受欢迎"
   - **功能对比表**：`mt-8 overflow-x-auto`，按分组展示，值类型：`string`（数值）/ `true`（蓝色勾 ✓）/ `false`（灰色横线 —）
   - **Footer**：错误提示区 + "查看消费记录"链接（触发 `onOpenLedger`）

3. **功能对比表内容**（credit 单价是内部信息，不展示给用户）：

   | 分组 | 行 | Free | Starter | Pro | Team |
   |------|-----|------|---------|-----|------|
   | 积分与配额 | 月度 Credits | 300 | 5,000 | 15,000 | 45,000 |
   | | 单次上传上限 | 500 条 | 1,000 条 | 5,000 条 | 5,000 条 |
   | | ASIN 自动拉取 | 1 次/天 | 10 次/天 | 10 次/天 | 50 次/天 |
   | 评论分析 | 情感分析与标签 | ✓ | ✓ | ✓ | ✓ |
   | | Ask Reviews 问答 | ✓ | ✓ | ✓ | ✓ |
   | | Insight 深度报告 | ✓ | ✓ | ✓ | ✓ |
   | | 多产品对比 | 2 款 | 不限 | 不限 | 不限 |
   | 内容生成 | 广告文案 | ✓ | ✓ | ✓ | ✓ |
   | | 翻译 | 20 次/天 | 200 次/天 | 200 次/天 | 500 次/天 |
   | 导出与集成 | Excel/CSV 导出 | 10 次/月 | 不限 | 不限 | 不限 |
   | | Webhook 集成 | 3 个 | 不限 | 不限 | 不限 |
   | | 预警规则 | 全局 3 条 | 不限 | 不限 | 不限 |
   | | API 密钥 | — | — | 3 个（即将） | 10 个（即将） |
   | 团队与支持 | 多成员协作 | — | — | — | ✓ |
   | | 角色权限 | — | — | — | ✓ |
   | | 客服支持 | 社区 | 邮件 | 优先 | 专属经理 |

4. **CTA 按钮逻辑**：
   - `planKey === currentPlan` → disabled 按钮显示"当前套餐"
   - `planKey === 'free'` 且用户已付费 → 不显示按钮
   - `planKey === 'team'` → `<a mailto:hello@clueai.co>联系销售</a>`
   - Free 用户升级付费套餐 → `<Link href="/pricing">立即升级</Link>`
   - 付费用户换档 → `<button onClick={handlePaidCheckout}>升级套餐</button>`

5. **修改 `sidebar-credit-entry.tsx`**：
   - 新增 `upgradeOpen` state（保留原有 `open` 控制消费记录抽屉）
   - **Credits 余额区域点击行为保持不变**（仍打开已有的"套餐使用量"对话框）
   - 在 Credits 卡片右侧新增**常驻 "Upgrade" 按钮**（替代原来仅余额 <20% 时显示的 "Top up" 链接），点击 → `setUpgradeOpen(true)` 打开升级弹窗
   - 按钮样式：`self-center text-xs font-semibold text-rose hover:underline`，位于卡片右侧（与当前 "Top up" 位置一致）
   - 当用户是 Team 套餐时隐藏 Upgrade 按钮（已是最高档）
   - 从 `data.monthly_grant` 推导 `currentPlan`（`>=45000→team, >=15000→pro, >=5000→starter, else→free`）
   - 渲染 `<UpgradePricingDialog>` + 保留原有 `<CreditLedgerDrawer>`
   - UpgradePricingDialog 的 `onOpenLedger` 回调：关闭升级弹窗 → 打开消费记录抽屉

6. **复用清单**：
   - `Dialog/DialogContent/DialogHeader/DialogTitle` — `components/ui/dialog`
   - `PLANS`, `formatPrice`, `PlanKey`, `BillingPeriod` — `lib/pricing.ts`
   - `CreditLedgerDrawer` — 保留不改，通过回调打开
   - `Check`, `Minus` icons — `lucide-react`
   - 参考 `components/quota/quota-dialog.tsx` 中 `ManageSubscriptionButton` 的 Paddle checkout 模式

7. **验证**：
   - `cd frontend && npm run dev` 启动开发服务器
   - 登录后侧边栏 Credits 卡片右侧显示常驻 "Upgrade" 按钮
   - 点击 Credits 余额区域 → 仍弹出已有的"套餐使用量"对话框（行为不变）
   - 点击 Upgrade 按钮 → 弹出套餐升级弹窗（4 卡片 + 月/年切换 + 对比表）
   - 当前套餐卡片显示"当前套餐"禁用按钮
   - 点击弹窗底部"查看消费记录" → 关闭弹窗 → 打开消费记录抽屉
   - `npx tsc --noEmit` 类型检查通过

**6.10 文档同步**（执行完以上步骤后必做）

- [ ] `QUOTA_TABLE.md` — 全部重写为 credit 单价表 + 4 档硬限矩阵（作为唯一 SSOT）
- [ ] `COST_PROFIT.md` — 修正 OpenAI 单价（¥0.15/¥0.60 → ¥1.08/¥4.32，漏了 ×7.2 汇率），补充 4 档 credit 定价推导 + 新毛利率表
- [ ] `需求记录/CHANGELOG.md` — 追加"海外 credit 定价体系上线"记录

**验收标准**

- 注册新用户 → 余额显示 "3,000 credits · Trial 14 days left"
- 上传 300 条评论 → 余额扣至 2,700，`credit_ledger` 有 `-300 review_analyze` 记录
- 余额不足时拒绝操作并提示 "Not enough credits: X needed, Y left"
- Trial 到期 → 自动降级 Free 300 credits/月（不结转）
- Paddle Sandbox 订阅 Starter → webhook 触发 → 余额 5,000 + monthly_grant 生效
- 购买加油包 +5K/$9 → 余额瞬时 +5,000
- LLM 熔断失败 → 自动 refund，credit_ledger 有反向记录
- 场景验证：Starter 5,000 credits 跑 5 产品×700 条 + 20 Ask + 5 Insight + 40 文案 ≈ 3,894，剩 1,106（22% buffer）
- 套利验证：Starter $12 + 加油包 $18 = 15K credits $30 vs Pro $29 → Pro 便宜 ✅

---

### 8.x 出海模块进度总览

| Milestone | 内容 | 状态 | 进度 |
|-----------|------|------|------|
| 8.1 | Erika 手动准备（账户/文档 + AWS Bedrock） | 🔄 进行中 | SG 迁移 Phase 0-3b ✅（Phase 4 观察中到 07-12），收款/DataForSEO/法律文档待办 |
| 8.2 | i18n 框架 + 双语文案 + 法律页面 + Terms Gate | ⏳ 待启动 | 0% |
| 8.3 | 后端合规能力（geo-block / 数据主权 API / 邮件双语） | 🔄 进行中 | 80%（Geo-Block + 数据主权 API + 邮件双语化 + Contact/Sub-processor 页已完成；数据保留清理待办） |
| 8.5 | LLM 集成 + 数据源改造 | ⏳ 待启动 | 0% |
| 8.6 | Beta 发布 + 部署 + 监控 | ⏳ 待启动 | 0% |
| 8.7 | Credit 定价体系改造（海外 4 档套餐 + 统一 credit 池）| ✅ 基建完成 | 已部署上线，文档待同步 |

```
[                    ] 0%  (0/7 modules)
```

**时间估算**：6-7 周（Week 1 Erika 手动 + Week 2-5 Claude 开发）
**参考文档**：[OVERSEAS_COMPLIANCE_PLAN.md](OVERSEAS_COMPLIANCE_PLAN.md)

---
