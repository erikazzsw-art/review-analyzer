# 需求记录

> 所有需求开发完成并推送后，在此文档追加一条记录，同时在对话中输出需求明细供 Erika 核实。

---

## 工作量判断标准（行业惯例）

| 级别 | 判断标准 | 典型工时 | 示例 |
|------|---------|---------|------|
| S | 单文件或 2-3 文件改动；逻辑简单；无新接口/表结构；不影响其他模块 | 0.5-2 人天 | 修复样式 bug、调整文案、增加一个已有 API 的参数 |
| M | 跨 3-8 文件；新增 API 端点或组件；需前后端联调；可能涉及数据库变更 | 2-5 人天 | 新增一个列表页+筛选功能、增加导出功能、新增缓存机制 |
| L | 跨模块架构变更；新增完整功能模块；涉及多个子系统联动；需要 migration | 5-15 人天 | 新增完整对比分析模块、重构认证系统、接入第三方支付 |
| XL | 系统级重构；技术栈迁移；全新业务线；需多个角色协作数周 | 15+ 人天 | 从 Streamlit 迁移到 Next.js、多租户架构改造、国际化 |

## 岗位分类

| 岗位 | 职责范围 |
|------|---------|
| 前端开发 | 页面 UI、组件、交互逻辑、状态管理、类型定义 |
| 后端开发 | API 端点、业务逻辑、数据库操作、缓存、队列 |
| 算法工程师 | LLM prompt 设计、分析链路、数据处理管线、模型调优 |
| DevOps | 部署配置、CI/CD、nginx、Docker、监控 |
| 产品经理 | 需求定义、验收标准、优先级排序 |

---

## 2026-07-02

### 问评论页面能力升级 · P0（意图路由 + 结构化聚合）

- **工作量**: M
- **状态**: 已完成（P0），P1/P2 待排期

**需求描述**：
问评论页面的 4 个内置示例问题（差评原因/质量最好/最常提到的优点/共同质量问题）在真实数据上全部返回"没有找到"。用户反馈：页面上"看似能问的问题"都不能问，不清楚具体能问什么。对齐竞品 Shulex VOC 的问评论能力（消费者洞察/产品反馈/竞品对比/市场趋势 4 大类），把系统从"单一检索型 RAG"重构为"意图路由 + 结构化聚合 + 检索证据"。

**实现要点**：
1. 新增聚合原语层 `review_analyzer/aggregations.py`（top_tags / pick_representative_reviews / pick_citations_by_tags 含 TypedDict），`compare_store.py` 复用同一模块，消除重复实现
2. 规则版意图分类 `review_analyzer/qa_intent.py`（7 类 intent + `_RULE_PATTERNS` 20+ 正则），4 个示例问题全部命中期望 intent（0ms 开销）；LLM 兜底 P1 再接入
3. P0 三个 handler `review_analyzer/qa_handlers.py`：aggregate_feedback（Top-N 骨架 + 代表评论 → LLM 强制列 Top 3-5 + 占比 + 引用 + 可行动建议）、product_compare（按产品分组表格对比）、retrieval（封装现有 hybrid 检索作 fallback）
4. `rag.py:answer_question` 重构为纯意图路由，返回体新增 `intent` + `aggregation_snapshot` 字段；handler 内部 LLM 失败自动降级到骨架文案（永不返回"没有找到"）
5. `backend_api/app/routes/qa.py` 单轮/多轮两处入口都传 `products_meta` 支持跨产品对比；qa_messages 表 INSERT 存 intent 和 snapshot 便于历史回放
6. migration `039_qa_intent_columns.sql` 加两列，schema `QaAskResponse`/`QaMessageResponse` 加两字段
7. 前端 `qa-chat-area.tsx` 加意图徽章（聚合分析/跨产品对比/检索证据/…），retrieval_method 中文化
8. Smoke test 验证：4 条示例问题全部产出结构化答案，retrieval_method 分别显示 `aggregation`/`compare`；ruff + tsc 通过

**涉及岗位及工时**：
- 算法工程师 · 0.75 天（意图分类规则设计、handler prompt 编写、聚合原语提取）
- 后端开发 · 0.5 天（路由层适配、schema/migration、qa_messages 存 intent）
- 前端开发 · 0.25 天（类型同步、意图徽章）

**后续计划（P1）**：
补齐 rating_breakdown/consumer_insight/trend_and_emerging/unanswerable 4 个 handler + LLM few-shot 兜底意图分类 + 前端建议问题重做为 4 分组 12-16 条 + Golden Set 10 条完整验收。

---

## 2026-07-01

### eBay + Walmart 评论抓取接入

- **工作量**: M
- **状态**: 已完成

**需求描述**：
新增 eBay 和 Walmart 平台评论抓取能力，通过 Apify 按量付费 Actor 实现，与 AliExpress 共用同一个 APIFY_API_TOKEN。先用 $5 免费积分跑通流程，后期有付费用户后再充值。

**实现要点**：
1. eBay: Apify `scrapier/ebay-review-scraper`（$5.99/1k条），无 1-5 星评分（Positive/Neutral/Negative → 5/3/1），无精确日期（相对时间 → 近似日期：Past month → -15天，Past 6 months → -90天）
2. Walmart: Apify `webscrapewizard/walmart-review-crawler`（$6.00/1k条），标准 1-5 星 + 精确日期
3. 各平台 max_reviews=100（节省免费额度）
4. 前端平台选择器扩展（产品编码抓取 + 定时抓取面板均支持 4 平台）
5. Worker 分派逻辑、Schema 校验、TypeScript 类型同步扩展

**涉及岗位及工时**：

| 岗位 | 工作内容 | 预估工时 |
|------|---------|---------|
| 后端开发 | ebay_scraper.py + walmart_scraper.py + review_scraper 分派 + schemas + jobs.py | 3h |
| 前端开发 | asin-fetch-panel + asin-watchlist-panel + types.ts 扩展 | 1h |

**合计：约 0.5 人天**

**修改文件**：

| 文件 | 变更 |
|------|------|
| `backend_api/app/services/ebay_scraper.py` | 新建，eBay Apify 抓取 + 评分映射 + 日期近似化 |
| `backend_api/app/services/walmart_scraper.py` | 新建，Walmart Apify 抓取 + 多字段名兼容 |
| `backend_api/app/services/review_scraper.py` | 添加 ebay/walmart 分派分支 |
| `backend_api/app/schemas/scrape.py` | platform Literal 扩展 + 校验规则 |
| `backend_api/app/schemas/asin_watchlist.py` | platform Literal 扩展 + 校验规则 |
| `workers/jobs.py` | 新增 _fetch_ebay_path / _fetch_walmart_path + 分派 + source_label |
| `frontend/src/components/upload/asin-fetch-panel.tsx` | 平台选项 + 校验规则扩展 |
| `frontend/src/components/upload/asin-watchlist-panel.tsx` | 平台选择器 + 校验 + placeholder |
| `frontend/src/lib/api/types.ts` | platform union 扩展 |

**部署注意**：无数据库变更。需重建 api + worker 容器。

---

### 分析结果页翻译后按钮消失 + 行动按钮常显

- **工作量**: S
- **状态**: 已完成

**需求描述**：
1. 分析结果页（用户体验等模块）点击"翻译"按钮后，每行的"下载原文"（Reviews N）和"加入行动"按钮消失
2. "加入行动"按钮需要鼠标 hover 到该行才会出现，希望始终可见

**解决方案**：
1. 根因：`ModuleCard` 翻译模式用 `TranslatedView` 完全替换 `children`，`TagTable` 中的 `DownloadTagButton` / `InlineActionButton` 随之丢失
2. `TranslatedView` 新增 `comments`、`sessionId`、`session`、`showAction`、`locale` props，在每个翻译后的 tag 行末尾渲染对应按钮
3. 提取 `DownloadTagButton` 为独立文件 `download-tag-button.tsx`，避免循环依赖
4. 移除 `InlineActionButton` 的 `opacity-0 group-hover:opacity-100` 样式，改为始终可见

**涉及岗位及工时**：

| 岗位 | 工作内容 | 预估工时 |
|------|---------|---------|
| 前端开发 | TranslatedView 按钮集成 + DownloadTagButton 提取 + hover 样式移除 | 1h |

**合计：约 0.125 人天**

**修改文件**：
- `frontend/src/components/analysis/module-card.tsx`
- `frontend/src/components/analysis/analysis-results-sections.tsx`
- `frontend/src/components/analysis/inline-action-button.tsx`
- `frontend/src/components/analysis/download-tag-button.tsx`（新建）

---

## 2026-06-30

### 产品管理删除功能 + rating 类型修复

- **工作量**: S
- **状态**: 已完成

**需求描述**：
产品管理页面需要支持删除操作，同时修复线上发现的渲染崩溃 bug：
1. 产品列表页（`/products`）每张卡片增加删除按钮，支持删除整个产品（级联删除变体和关联评论）
2. 产品详情页（`/products/[id]`）变体表格每行增加删除按钮，支持单独删除变体
3. 删除操作需内联确认（避免误触）：初始态→"确认？"确认态→执行删除
4. 产品详情页 rating 渲染崩溃（500 错误）：PostgreSQL NUMERIC 类型经 JSON 序列化后变成字符串 `"4.5"`，前端 TypeScript 类型断言 `as number` 未实际转换，导致 `.toFixed(1)` 对字符串调用报 TypeError

**解决方案**：
1. 后端新增两个 DELETE 端点：`DELETE /products/{id}`（级联删除 variants + 关联 upload_jobs）、`DELETE /products/{product_id}/variants/{variant_id}`
2. 前端新建两个 Client Component：`DeleteProductButton`（产品卡片级别）、`DeleteVariantButton`（变体表格行级别），均采用三态交互模式（idle → confirming → deleting）
3. Rating 修复：`const rating = product.rating != null ? Number(product.rating) : null` — 显式调用 `Number()` 转换，而非依赖类型断言

**涉及岗位及工时**：

| 岗位 | 工作内容 | 预估工时 |
|------|---------|---------|
| 前端开发 | DeleteProductButton + DeleteVariantButton 组件 + API 函数 + 页面集成 + rating 类型修复 | 2h |
| 后端开发 | 两个 DELETE 端点（含 FK 级联处理） | 1h |

**合计：约 0.5 人天**

**修改文件**：

| 文件 | 变更 |
|------|------|
| `frontend/src/components/products/delete-product-button.tsx` | 新建，产品卡片删除按钮（内联确认） |
| `frontend/src/components/products/delete-variant-button.tsx` | 新建，变体行删除按钮（内联确认） |
| `frontend/src/app/products/page.tsx` | 集成 DeleteProductButton 到卡片 |
| `frontend/src/app/products/[id]/page.tsx` | 集成 DeleteVariantButton + 修复 rating 类型转换 |
| `frontend/src/lib/api/browser.ts` | 新增 `deleteProduct()` + `deleteVariant()` 函数 |
| `backend_api/app/routes/products.py` | 新增 DELETE /products/{id} + DELETE /products/{pid}/variants/{vid} |

**部署注意**：无数据库变更，前后端同时部署即可

---

### Golden Set 标签校准系统 + 管理员权限控制

- **工作量**: L
- **状态**: 已完成

**需求描述**：
建立 Golden Set 管理系统，用于通过人工标注样例提升 LLM 标签准确率：
1. 数据库表 `golden_set`：存储人工标注的正确/错误标签判断 + 原因 + few-shot 标记
2. 数据库表 `category_aspect_taxonomy` 新增 `boundary_note` 字段：零 token 成本的标签边界描述
3. 后端 API：CSV 上传（中英文表头兼容）、条目查询、准确率统计、few-shot 切换
4. 前端 `/settings/golden-set` 管理页：4 张摘要卡片 + 准确率表格 + 标注记录表 + CSV 上传
5. Prompt 注入：few-shot 示例自动注入分析 prompt（正例 "→ 正确标签: X"，反例 "→ 不属于 X，应为 Y"）
6. Taxonomy 渲染：`render_aspects_block` 输出边界描述（`（边界: ...）`）
7. 管理员权限：`users.is_admin` 字段 + `/me` 返回 is_admin + sidebar 过滤 adminOnly 页面 + 页面级权限守卫

**解决方案**：
- Plan A（零成本）：taxonomy 表 boundary_note 字段 → 渲染到 prompt 中帮 LLM 区分易混标签
- Plan B（few-shot）：golden_set 中 `use_as_fewshot=true` 的条目注入 prompt，替代抽象校准规则
- 管理员控制：migration 035 加 is_admin 列并授权测试账号 `惜_clueai`

**涉及岗位及工时**：

| 岗位 | 工作内容 | 预估工时 |
|------|---------|---------|
| 后端开发 | golden_set_store + API 路由 + calibration_injector + taxonomy_loader 改造 | 4h |
| 前端开发 | golden-set 管理页 + sidebar admin 过滤 + 权限守卫 | 3h |
| 算法工程师 | few-shot prompt 注入设计 + boundary_note 渲染逻辑 | 1h |
| DevOps | 3 个 migration (033/034/035) | 0.5h |

**合计：约 1.5 人天**

**修改文件**：

| 文件 | 变更 |
|------|------|
| `migrations/033_golden_set.sql` | 新建 golden_set 表 + 3 个索引 |
| `migrations/034_taxonomy_boundary_note.sql` | taxonomy 表加 boundary_note 列 |
| `migrations/035_add_is_admin.sql` | users 表加 is_admin + 授权惜_clueai |
| `review_analyzer/golden_set_store.py` | 新建，golden_set CRUD |
| `backend_api/app/schemas/golden_set.py` | 新建，Pydantic models |
| `backend_api/app/routes/golden_set.py` | 新建，/golden-set API 路由 |
| `backend_api/app/services/calibration_injector.py` | 重构，从 golden_set 加载 few-shot |
| `backend_api/app/services/taxonomy_loader.py` | 改造，支持 boundary_note 渲染 |
| `backend_api/app/schemas/auth.py` | UserPayload 加 is_admin |
| `backend_api/app/routes/me.py` | 新增 _check_admin + 返回 is_admin |
| `backend_api/app/main.py` | 注册 golden_set_router |
| `frontend/src/app/settings/golden-set/page.tsx` | 新建，管理页（含权限守卫） |
| `frontend/src/components/app/sidebar.tsx` | adminOnly 过滤逻辑 |
| `frontend/messages/zh.json` | 新增 goldenSet 翻译 |
| `frontend/messages/en.json` | 新增 goldenSet 翻译 |

**部署注意**：需执行 migration 033 + 034 + 035

---

### 产品删除按钮失效修复

- **工作量**: S
- **状态**: 已完成

**需求描述**：
产品管理页面点击删除按钮→确认删除后，产品仍然存在，未被删除。

**根因**：
`product_store.py` 的 `delete_product()` 在清理外键关联时执行 `UPDATE push_snapshots SET product_id = NULL`，但 `push_snapshots` 表未建（migration 016 未应用到生产），`psycopg2.errors.UndefinedTable` 异常导致整个事务回滚。FastAPI 返回 500 Internal Server Error，前端 catch 块静默吞错无用户反馈。同样问题影响 `issue_escalation_state` 表。

**解决方案**：
新增 `_safe_execute()` 辅助函数：用 PostgreSQL SAVEPOINT 包裹每条 FK 清理 SQL，`UndefinedTable` 异常时 ROLLBACK TO SAVEPOINT 跳过该表，不影响后续语句和最终 DELETE。前端 catch 块补充 `console.error` 便于调试。

**涉及岗位及工时**：

| 岗位 | 工作内容 | 预估工时 |
|------|---------|---------|
| 后端开发 | `_safe_execute()` 函数 + SAVEPOINT 防御逻辑 | 0.5h |
| 前端开发 | catch 块补 console.error | 0.1h |

**合计：约 0.1 人天**

**修改文件**：

| 文件 | 变更 |
|------|------|
| `review_analyzer/product_store.py` | 新增 `_safe_execute()` + 6 处 FK 清理改用 SAVEPOINT |
| `frontend/src/components/products/delete-product-button.tsx` | catch 块补 console.error |
| `frontend/src/components/products/delete-variant-button.tsx` | catch 块补 console.error |

**部署注意**：仅代码变更，无数据库迁移。需重建 api + worker 容器。

---

## 2026-06-29

### 用户画像模块重构（Facebook Ads 受众模型）

- **工作量**: S
- **状态**: 已完成

**需求描述**：
用户画像模块存在三大问题：
1. Review Distribution（好评率/差评率）与上方汇总模块信息重复
2. Core Audience Focus 中同一标签出现两次（positive_tags 和 negative_tags 拼接时标签重叠）
3. Key Insight 模板句式 "values X but is sensitive to problems around X" 逻辑自相矛盾
4. 整体内容与「消费动机」「未满足的需求」模块职责重叠，不应在画像中评价产品

**解决方案**：
参考 Facebook Ads 核心受众定向模型，将用户画像重构为纯人物描述（只画人，不评价产品）：
- 三行从 Review Distribution / Core Audience Focus / Key Insight → Demographics / Interests & Context / Purchase Behavior
- 新增三个 heuristic 函数，从评论文本中提取身份角色（parent/gift buyer/student 等）、兴趣场景（home decor/space-saving 等）、行为模式（self-assembly/price comparison 等）
- AI prompt 同步更新，明确禁止输出产品好坏标签
- 前端无需改动（通用 label/detail 循环渲染兼容新 label）

**涉及岗位及工时**：

| 岗位 | 工作内容 | 预估工时 |
|------|---------|---------|
| 算法工程师 | insight_engine.py heuristic 重写 + AI prompt schema 更新 | 2h |
| 产品经理 | 竞品调研 + 维度定义 + 验收 | 1h |

---

### 设置页面拆分重构 + 订阅计费迁移

- **工作量**: M
- **状态**: 已完成

**需求描述**：
1. 推送设置页面标题修复：从 sidebar 点击"推送设置"进入后，页面标题应显示"推送设置"而非"系统设置"
2. 产品级专项规则的产品输入框改为搜索式下拉选择（与上传页统一，placeholder 为"产品编码"）
3. 新建独立的"系统设置"页（/settings），包含账户信息 + API 密钥管理 + 数据导出占位
4. 订阅计费从推送设置中移除，移入套餐额度弹窗（Free 用户→升级套餐链接；Pro 用户→管理订阅按钮拉起 Paddle）

---

### 设置页优化 + 下载中心

- **工作量**: M
- **状态**: 已完成

**需求描述**：
1. 删除 API 密钥管理：用户无需配置（后台已预设），从系统设置中移除
2. 系统设置改弹窗：从 sidebar 导航移除，改为用户下拉菜单（点 chevron-up）触发 Dialog 弹窗展示账户信息
3. 新增下载中心页面 `/downloads`：用户菜单入口 + 表格列表（名称/来源/操作时间/状态/操作）+ 后端 download_records 表 + API
4. 团队管理方案：输出 Workspace 模型 + 4 角色 RBAC + 3 Phase 落地计划，写入 PROGRESS_V2（启动条件：1 个付费用户）

**解决方案**：
1. 删除 `api-keys-panel.tsx` + `settings/api-keys/page.tsx`
2. 新建 `system-settings-dialog.tsx`（Radix Dialog），`sidebar-user-menu.tsx` 增加 state 控制弹窗；sidebar.tsx groupManage 移除系统设置入口
3. 后端：migration 030 建表 `download_records` + `backend_api/app/routes/downloads.py`（GET/POST）；前端：`/downloads` 页面 + `fetchDownloads()` / `recordDownload()` API 函数 + 现有 `downloadCompareExport` 自动记录
4. PROGRESS_V2 新增 V5-T1 团队管理方案（Workspace、Owner/Admin/Member/Viewer、邀请流程、DB 设计、分阶段落地）

**涉及岗位及工时**：

| 岗位 | 工作内容 | 预估工时 |
|------|---------|---------|
| 前端开发 | Dialog 组件 + 用户菜单改造 + 下载中心页面 + API 函数 + 导出记录集成 | 4h |
| 后端开发 | migration + downloads route（GET/POST）+ main.py 注册 | 1.5h |
| 产品经理 | 团队管理方案调研 + 文档撰写 | 2h |

**合计：约 1 人天**

**修改文件**：

| 文件 | 变更 |
|------|------|
| `frontend/src/components/settings/api-keys-panel.tsx` | 删除 |
| `frontend/src/app/settings/api-keys/page.tsx` | 删除 |
| `frontend/src/app/settings/page.tsx` | 改为 redirect 到 /settings/push |
| `frontend/src/components/app/system-settings-dialog.tsx` | 新建，Dialog 展示账户信息 |
| `frontend/src/components/app/sidebar-user-menu.tsx` | 重写，增加下载中心入口 + 系统设置触发弹窗 |
| `frontend/src/components/app/sidebar.tsx` | groupManage 移除系统设置 |
| `frontend/src/app/downloads/layout.tsx` | 新建，Sidebar 布局壳 |
| `frontend/src/app/downloads/page.tsx` | 新建，下载中心表格页 |
| `frontend/src/lib/api/browser.ts` | 新增 fetchDownloads + recordDownload + 导出自动记录 |
| `frontend/src/lib/api/types.ts` | 新增 DownloadRecord 类型 |
| `frontend/messages/zh.json` | 新增 downloadCenter 翻译 |
| `frontend/messages/en.json` | 新增 downloadCenter 翻译 |
| `backend_api/app/routes/downloads.py` | 新建，GET/POST /downloads |
| `backend_api/app/main.py` | 注册 downloads_router |
| `migrations/030_create_download_records.sql` | 新建表 + 索引 |
| `PROGRESS_V2.md` | 新增 V5-T1 团队管理方案 |

**部署注意**：需执行 migration 030（`CREATE TABLE IF NOT EXISTS download_records`）

**解决方案**：
1. `settings/layout.tsx` 精简为纯结构壳（Sidebar + FeedbackWidget），新建 `settings/push/layout.tsx` 承载推送设置专属标题
2. 产品规则区域的 Input 替换为已有的 `ProductSearchCombobox` 组件（debounce + API 搜索 + 下拉选择）
3. `settings/page.tsx` 从 redirect 改为完整系统设置页，内嵌 ApiKeysPanel + 账户信息 + 数据导出占位
4. `quota-dialog.tsx` 新增 `ManageSubscriptionButton`（复用 `createBillingCheckout` 逻辑）
5. 侧边栏 groupManage 新增"系统设置"入口指向 `/settings`，推送设置指向 `/settings/push`
6. 旧 billing/api-keys 独立页改为 redirect

**涉及岗位及工时**：

| 岗位 | 工作内容 | 预估工时 |
|------|---------|---------|
| 前端开发 | layout 拆分 + 新页面 + 组件替换 + QuotaDialog 增强 + sidebar 导航 + 路由清理 | 3h |
| 产品经理 | 需求定义 + 系统设置内容规划 | 0.5h |

**合计：约 0.5 人天**

**修改文件**：

| 文件 | 变更 |
|------|------|
| `frontend/src/app/settings/layout.tsx` | 精简为纯结构壳，currentPath 改用 pathname |
| `frontend/src/app/settings/push/layout.tsx` | 新建，推送设置专属标题布局 |
| `frontend/src/app/settings/page.tsx` | 改写为系统设置页（账户信息 + API 密钥 + 数据导出） |
| `frontend/src/app/settings/billing/page.tsx` | 改为 redirect 到 /settings |
| `frontend/src/app/settings/api-keys/page.tsx` | 改为 redirect 到 /settings |
| `frontend/src/components/settings/push-settings-panel.tsx` | 产品 Input 替换为 ProductSearchCombobox |
| `frontend/src/components/quota/quota-dialog.tsx` | 新增 ManageSubscriptionButton（Pro 用户管理订阅） |
| `frontend/src/components/app/sidebar.tsx` | 导航项拆分：推送设置 + 系统设置 |

---

## 2026-06-26

### 对比分析：版本下拉框修复 + 产品列表同步

- **工作量**: S
- **状态**: 已完成

**需求描述**：
1. 对比分析页面"版本对比"模式下，选择产品后版本下拉框只显示"全部版本"，无法选择 V1/V2
2. 历史记录页面删除分析记录后，对比分析页面的产品列表未同步更新

**根因**：
1. 版本下拉：前端从 `product_versions`（产品目录手动管理表）读取版本，但实际 V1/V2 存储在 `sessions.version` 字段
2. 产品列表同步：对比页面使用 SSR 初始数据，跨页面操作后不会自动刷新

**解决方案**：
1. 后端 `product_store.py` 新增 `_fetch_session_versions_grouped()` 从 sessions 表聚合实际版本，注入到产品列表返回数据的 `session_versions` 字段
2. 前端 compare-workspace 组件挂载时 client-side 重新获取产品列表

**涉及岗位及工时**：

| 岗位 | 工作内容 | 预估工时 |
|------|---------|---------|
| 后端开发 | 新增聚合查询函数 + schema 加字段 | 0.5 人天 |
| 前端开发 | types 加字段 + filter-bar 改数据源 + workspace 加 useEffect 刷新 + browser.ts 加 fetchProductList | 0.5 人天 |

**合计：约 1 人天**

**修改文件**：

| 文件 | 变更 |
|------|------|
| `review_analyzer/product_store.py` | 新增 `_fetch_session_versions_grouped`，`get_product_overview_rows` 注入 `session_versions` |
| `backend_api/app/schemas/products.py` | `ProductOverviewPayload` 加 `session_versions: list[str]` |
| `frontend/src/lib/api/types.ts` | `ProductOverview` 加 `session_versions` |
| `frontend/src/components/analysis/compare-filter-bar.tsx` | 版本选项改用 `session_versions` |
| `frontend/src/components/analysis/compare-workspace.tsx` | 挂载时 client-side 刷新产品列表 |
| `frontend/src/lib/api/browser.ts` | 新增 `fetchProductList()` |

---

## 2026-06-25

### 推送设置页重构 + 推送内容增强

- **工作量**: L
- **状态**: 已完成

**需求描述**：

Part A: 设置页面重构
1. 设置页改为 sidebar 导航，分 3 个子页面（push / api-keys / billing）
2. 推送设置页改为全宽单列布局，移除右侧栏
3. 产品级规则支持添加/编辑/删除
4. 环比窗口锁定 14 天

Part B: 推送内容增强
- B1: 问题/亮点输出条数 + 占比
- B2: 附加 AI 总结和建议
- B3: 附加可点击链接（分析详情 + 行动中心）
- B4: 升级行动增加引导文案 + 行动中心链接
- B5: 环比推送增强（对比周期、上期→本期、TOP3 变化含条数）
- B6: TOP 问题复盘进度

**涉及岗位及工时**：

| 岗位 | 预估工时 |
|------|---------|
| 前端开发 | 4h（路由重构 + 面板合并 + 子页面拆分） |
| 后端开发 | 6h（notifier 6 项增强 + workers 集成 + 环境变量） |
| 测试验证 | 1h |

---

### 问评论页面对话式 UI 重构 + 多轮对话支持

- **工作量**: L
- **状态**: 已完成

**需求描述**：
将"问评论"页面从传统表单布局改为现代 AI 对话框形式，后端增加多轮对话支持。

**主要变更**：
1. 前端 UI 重构：对话式布局 + Popover 产品选择 + 预设问题卡片 + 引用折叠
2. 后端多轮对话：新增 qa_conversations / qa_messages 表 + 对话管理 API + RAG history 参数

**涉及岗位及工时**：

| 岗位 | 工时 |
|------|------|
| 前端开发 | 6h |
| 后端开发 | 3h |
| 测试验证 | 1h |

**部署注意**：需执行 migration 027

---

### 对比分析：自动加载最近结果 + 历史记录面板

- **工作量**: L
- **状态**: 已完成

**需求描述**：
1. 打开对比页面时自动展示最近一次对比结果
2. 页面底部增加历史记录面板（列表/搜索/加载/删除）

**涉及岗位及工时**：

| 岗位 | 工作内容 | 预估工时 |
|------|---------|---------|
| 后端开发 | 4 个 API 端点 + compare_store 函数 + schema | 2 人天 |
| 前端开发 | CompareHistory 组件 + page 改造 + API 调用函数 | 2.5 人天 |
| 产品经理 | 需求定义、交互确认 | 0.5 人天 |

**合计：约 5 人天**

---

### 可观测性页面重构

- **工作量**: M
- **状态**: 已完成

**需求描述**：
将 `/settings/observability` 从 265 行单页重构为 5-Tab 管理后台结构（概览/成本/任务/缓存/告警）。

**涉及岗位及工时**：

| 岗位 | 工时 |
|------|------|
| 前端开发 | 3h |

---

### 标签数据层回归英文 canonical key

- **工作量**: S
- **状态**: 已完成

**需求描述**：
将 `issue_tag` / `highlight_tag` 存储从中文标签回归为英文 canonical label，修复前端下载按钮无法匹配评论原文的问题。

**涉及岗位及工时**：
- 后端开发 0.5h + 前端开发 0.5h

---

### 反馈按钮移至 Sidebar

- **工作量**: S
- **状态**: 已完成

**需求描述**：
将反馈按钮（💬）从页面右下角浮动位置移到 sidebar 底部语言切换图标旁。

**涉及岗位及工时**：

| 岗位 | 工时 |
|------|------|
| 前端开发 | 0.5h |

---

### 系统设置闪退修复

- **工作量**: S
- **状态**: 已完成

**需求描述**：
点击 sidebar "系统设置"入口时页面闪白/闪退。

**根因**：`/settings/page.tsx` 使用服务端 `redirect()` 在客户端 SPA 导航时触发全页刷新。

**解决方案**：改为 `"use client"` 组件 + `useRouter().replace()` 客户端软跳转。

**涉及岗位及工时**：

| 岗位 | 工时 |
|------|------|
| 前端开发 | 0.1h |

---

## 2026-06-30

### AliExpress 评论抓取集成

- **工作量**: L
- **状态**: 已完成

**需求描述**：
新增 AliExpress 平台评论抓取能力，与 Amazon 统一入口管理。用户可在"产品编码抓取"面板选择平台（Amazon / AliExpress），输入对应产品编码后拉取评论进入分析流程。

**实现要点**：
1. 新建 AliExpress 抓取器（双数据源：feedback API 主数据源 + Playwright 无头浏览器 fallback）
2. 前端平台切换分段控件 + 动态校验 + 动态 placeholder
3. 产品管理页新增平台 Tab 过滤（全部/Amazon/AliExpress）+ 平台 badge
4. Worker 按 platform 分派到对应抓取路径
5. 移除非英文 Amazon 站点（仅保留 US/UK/CA/AU）

**涉及岗位及工时**：

| 岗位 | 工时 |
|------|------|
| 后端开发 | 3h |
| 前端开发 | 2h |
| 产品设计 | 0.5h |

---

### AliExpress 评论抓取 — Apify CrowdPull 数据源接入 + 三处 bug 修复

- **工作量**: M
- **状态**: 已完成

**需求描述**：
AliExpress feedback API 被反爬封锁（返回 antiCrawlerContent），Playwright 浏览器也被验证码拦截，导致所有 AliExpress 产品抓取返回 0 条评论。接入 Apify CrowdPull 作为主数据源（付费，~$1.50/1000 条），同时修复调试过程中发现的两个前端/后端 bug。

**实现要点**：
1. 新增 `_fetch_via_apify()` 函数（Apify CrowdPull Actor，付费稳定数据源）
2. `fetch_aliexpress_reviews()` 改为三级 fallback：Apify → feedback API → Playwright
3. 修复前端输入 maxLength 15→16（AliExpress 部分产品 ID 为 16 位）
4. 修复后端 Pydantic 校验正则 `\d{12,15}` → `\d{12,16}`
5. 修复 Apify run-sync 接口返回 HTTP 201 被误判为错误（应接受 200 和 201）
6. APIFY_API_TOKEN 通过环境变量注入，不硬编码

**线上验证结果**：product ID 1005009259589970 成功抓取 131 条评论，session_id=75，好评率 82.4%，差评率 17.6%，完整分析模块正常渲染。

**涉及岗位及工时**：

| 岗位 | 工时 |
|------|------|
| 后端开发 | 2h |
| 前端开发 | 0.5h |
| DevOps | 0.5h |
