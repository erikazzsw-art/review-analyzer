# ClueAI 测试记录

> 版本：v1.0
> 创建日期：2026-05-07

---

## 修复记录

| 日期 | 问题描述 | 解决方案 |
|------|---------|---------|
| 2026-06-25 | 设置页面（推送/API密钥/计费）标题字体过大（text-2xl/xl）、模块间距过宽（space-y-8, p-6）、与导航栏距离远，与其他页面风格不统一 | 统一所有 section heading 为 `text-base font-bold`，section padding 从 `p-6` 收紧到 `p-5`，模块间距从 `space-y-8` 降为 `space-y-5`，layout 垂直 padding 从 `p-6` 改为 `py-4`。涉及 `push-settings-panel.tsx`、`api-keys-panel.tsx`、`billing-panel.tsx`、`settings/layout.tsx` 四个文件。typecheck 通过 |
| 2026-06-25 | 点击 sidebar"系统设置"入口页面闪退（白屏后跳转） | 根因：`/settings/page.tsx` 使用服务端 `redirect("/settings/push")` 导致客户端导航时触发全页刷新。修复：改为 `"use client"` + `useRouter().replace()` 客户端软跳转，layout 正常渲染不闪白。typecheck 通过 |
| 2026-06-25 | 修复上述 commit 02b221c 后设置页仍闪退（点击侧栏"系统设置"白屏崩溃） | 根因：子页面（push/api-keys/billing）各自包裹 `AppShell`（含 fixed Sidebar），而 `settings/layout.tsx` 是薄壳无 Sidebar，导致双重嵌套布局 + 服务端 `getSettings()` 未 catch 的异常直接崩溃整页。修复：1) `settings/layout.tsx` 重写为完整 shell（含 Sidebar + header + tab 导航）；2) 三个子页面从 server component 转为 client component，使用 `fetchSettings()` 客户端获取数据，统一处理 401/error/loading 三态，不再嵌套 AppShell。typecheck + next build 通过，Playwright 验证页面结构正确 |
| 2026-06-25 | 可观测性页面信息杂乱：单页 265 行塞进 Pipeline Health/Cache/Model Status/Job Traces 四块，无时间选择器、无 Tab 分层、无 trace 展开、无成本独立视图 | 重构为 5-Tab 管理后台结构：`page.tsx` 改为容器（PageTabs + TimeRangeSelect + ModelStatusRow），拆分为 `overview-tab`（概览）/ `cost-tab`（成本：堆叠柱状图+模型汇总表）/ `jobs-tab`（任务：状态筛选+可展开 trace timeline+分页）/ `cache-tab`（缓存效果）/ `alerts-tab`（告警占位）5 个独立组件。新增时间范围选择器（1h/6h/24h/7d/30d）、模型状态灯行（60s 轮询）、集成之前未使用的 `/llm-costs` API。各 Tab 独立 loading/error 状态。从用户 sidebar 导航中移除，仅管理员通过 URL 访问。typecheck + build 通过 |
| 2026-06-25 | 反馈按钮（💬）固定在页面右下角浮动，与 sidebar 底部的语言切换地球图标分离，位置不统一 | 将反馈触发按钮从 FeedbackWidget 的 fixed 浮动布局移除，新增 `FeedbackTrigger` 组件放入 sidebar 底部与 `LocaleSwitcher` 同行并排（`flex items-center gap-1`）。FeedbackWidget 通过监听自定义事件 `open-feedback` 打开面板，FeedbackTrigger 点击时 dispatch 该事件。快捷键 `Cmd+Shift+F` 保持可用。typecheck 通过 |
| 2026-06-25 | 分析结果页"原文下载"按钮始终匹配不到评论。根因：`category_grouper.py` 把 taxonomy key 转为中文存入 DB（违反 L2 英文设计），然后 `insight_engine.py` 的二次 AI 调用又把中文改写为不一致的英文（如"稳固性"→"Sturdiness"），前端无法匹配回评论字段 | 三层修复：(1) `category_grouper.py` 新增 `aspect_to_en()`，`issue_tag`/`highlight_tag` 改存英文 canonical label（如 "Durability"）；(2) `insight_engine.py` AI merge 跳过 tag 数组覆盖，只增强 summary 文本，删除 `_inject_original_tags`；(3) 前端下载匹配简化为精确匹配（tag 名 = 评论字段值）。旧 session 中文 tag 仍可精确匹配（heuristic 统计自评论字段，一致性天然保证）。commit `8054b48` | `/analysis/compare` 三个体验问题：1) 时间环比模式渲染两行重复的「产品 / 版本 / 时间」筛选，用户得挑两次产品两段时间；2) 输出只有 KPI + 差异表 + 风险机会卡，缺少结果页那种"购买动机 / 未被满足需求 / 产品体验(正/负)"按维度横向铺开的双窗口对照；3) AI 总结要先填报告标题/关键词、按按钮才生成，且每次点都重新调 LLM 且落 `comparison_reports` 一条新记录 | **后端**：1) `review_analyzer/compare_store.py` 新增 `compute_compare_fingerprint(user, type, groups)`（sha256，对 versions 排序、归一化日期）+ `load_compare_cache` / `save_compare_cache`（新表 `comparison_summary_cache` 永不过期）+ `build_group_insights(user, group, comments)` 复用 `insight_engine.build_results_insights` 拿单产品 7 维度结构化结果。`get_comparison_dataset` 顶层多挂内部字段 `_group_comments` 给上层调用 insights。2) `_build_recommended_actions` 上限从 4 改 10，扩展规则：好评率涨/跌 ≥5pt 的环比建议、每个 group 的"TOP 问题根因复盘"+"TOP 亮点放大"、差评率 ≥30% 的"先解药再扬长"，dedupe 后取 ≤10 条。3) `backend_api/app/routes/compare.py` 的 `POST /compare/dataset` 重构：算完 dataset 后查 fingerprint 缓存命中则直接挂 cached `group_insights` + `ai_summary`，未命中则 per-group 调一次 LLM + 一次 AI 总结 LLM，结果写缓存。新建 migration `migrations/025_compare_summary_cache.sql`。schema 新增 `AnalysisCompareGroupPayload.insights` + `AnalysisComparePayload.ai_summary`。**前端**：1) `compare-filter-bar.tsx` 拆 `same_product_time` 走单行 `TimeWindowEditor`：产品 + 版本（默认全部版本）+ 环比口径（7/14/30/60/自定义）下拉，preset 自动算"前 N 天 vs 上一个 N 天"两段窗口并在筛选条下方用浅灰小字回显；多产品 / 版本对比保持原渲染。从 `MODE_LABELS` 删 `custom` Tab；`/analysis/compare/page.tsx` 同步从 `ALLOWED_MODES` 删 `custom`。2) `compare-dashboard.tsx` 在 KPI 之下新加"维度对照"网格：4 个维度（购买动机 / 未被满足需求 / 产品体验正向 / 产品体验负向）每行内并列展示各窗口 TOP5 标签 + 横向 bar + 占比，配色 positive 绿 / negative 粉 / neutral 蓝；问题/亮点 TOP 变化表保持原表格但隐藏空数据；推荐动作没数据时不显示空字提示。3) 删 `compare-ai-summary-panel.tsx`，新建 `compare-ai-summary.tsx`（无输入框、无按钮，直接展示 `dataset.ai_summary`）。`compare-workspace.tsx` 去掉 `sessionIds` 推导 + AI panel 改用新组件。`lib/api/types.ts` 新增 `CompareAiSummary` + `AnalysisCompareGroup.insights` + `AnalysisCompareResponse.ai_summary`。**验证**：`ruff check backend_api/ workers/ review_analyzer/` 全过；`npm run typecheck` 全过；本地 dev DB 跑 migration 025 成功；Python smoke test 验证 fingerprint 对 versions 排序后命中相同 + 推荐动作产出 10 条 + 缓存读写 roundtrip OK |
| 2026-06-23 | 生产 502 第 N 次（继 6/22 后又一次）。push 完 commit 1a0fb77 + b8918fd 后 Erika 在 ECS 跑了 `docker compose up -d --build api worker frontend`，api / worker / frontend 全部重建（34 min 前），但 nginx 容器是 3 小时前启动的 — nginx 的 upstream DNS 缓存仍指向已死的旧 api 容器 IP，所有 `/api/*` 请求转发到死 IP 后超时返回 502。`docker compose ps` 显示 api 是 healthy + `docker compose logs api` 显示 `/health` 200 OK 但都是 127.0.0.1 内部探测，nginx 转发的请求根本没到 api 容器。frontend 也 unhealthy 报 "Failed to find Server Action"（next.js 的 server action 哈希在新旧 deployment 间不匹配，但这条不阻塞登录） | **立即修复**：`docker compose exec nginx nginx -s reload` 刷新 upstream DNS 缓存，`api.clueai-reviewlens.com/health` 和 `www.clueai-reviewlens.com/api/health` 立刻恢复 200。**根治**：`deploy/post-deploy-check.sh` 在每次 `docker compose up -d --build` 后必须自动跑 `nginx -s reload`；同时强烈建议把 nginx 也写进 build 链或在容器 build 后强制 reload，避免再忘。**教训**：1) `docker compose ps` 显示 "healthy" 只能证明容器本地探测通，不能证明 nginx 路径通；2) 每次 `--build` api 之后,nginx **必须** reload（即使 ps 全绿）；3) 排障时第一时间用 `curl https://api.<domain>/health` 测端到端,而不是只看 container ps |
| 2026-06-23 | 对比分析页（`/analysis/compare`）只能从历史页带 `session_id` 进来，主入口是「AI Report」卡片：用户没法直接选「产品 A vs 产品 B、过去 30 天」或「产品 A 环比」，看板用 `Object.entries` 通用键值对渲染，没有下载入口。整页更像 AI 报告生成器，不是对比工作台 | **后端**：1) `review_analyzer/compare_store.py` 新增 `build_compare_specs_from_filters(user_id, compare_type, filter_groups)`，接受 `{product_id, versions[], date_start, date_end, label, description}` 列表，按 product+versions 匹配 sessions 并把评论日期窗口写入 spec；下游 `_filter_comments` 已支持 `date_start/date_end` 按评论 `date` 列过滤。2) 同文件新增 `dataset_to_xlsx_payload(dataset, ai_summary)` 把对比 dataset 适配成 `export_compare_page_to_xlsx` 需要的 `{columns, objects}` 结构（① 总览指标 ② 问题差异 ③ 亮点差异 ④ 风险对象 ⑤ 机会对象 ⑥ 推荐动作 ⑦ 可选 AI 总结）。3) `backend_api/app/routes/compare.py` 新增 `POST /compare/dataset` 和 `POST /compare/export`：前者返回 `AnalysisComparePayload`，后者用 xlsxwriter 流式回 `.xlsx` + `Content-Disposition: attachment`；`backend_api/app/schemas/analysis.py` 新增 `CompareFilterGroupPayload / CompareDatasetRequest / CompareExportRequest`。**前端**：1) 新建 `frontend/src/components/analysis/compare-filter-bar.tsx`，提供「时间环比 / 版本对比 / 多产品对比 / 自定义」四模式 + 产品下拉 + 版本下拉 + 评论时间窗预设（7/14/30/60/180/全部/自定义日期段），切模式自动重排行（环比 2 个窗口、版本对比 2 个版本、多产品最多 5 行）。2) 新建 `compare-dashboard.tsx`，含 4 个 KPI 列（评论数 / 好评率 / 差评率 / 平均评分，相对基准带 ↑↓ 变化徽章 + 绿/红配色）、问题 TOP 变化表、亮点 TOP 变化表（每列相对第一组算 delta）、风险 / 机会对象卡和推荐动作列表。3) 新建 `compare-ai-summary-panel.tsx` 把原 `compare-report-panel` 的 AI 报告功能降级为看板下方「可选 · AI 总结」按钮，复用现有 `/compare/reports` 接口。4) 新建 `compare-workspace.tsx` 客户端容器，串筛选 → 看板 → 下载 → AI 总结一条链路；旧 `compare-page-tabs.tsx`、`compare-report-panel.tsx` 删除。5) `frontend/src/lib/api/types.ts` 新增 `CompareFilterGroup / CompareDatasetRequest / CompareExportRequest`，`browser.ts` 新增 `fetchCompareDataset(request)` 和 `downloadCompareExport(request)`（后者用 Blob + `<a download>` 触发 XLSX 下载）。6) `frontend/src/app/analysis/compare/page.tsx` 改为 server component 拉 `getProducts()` 喂给 `CompareWorkspace`，URL 仍兼容 `product_id` / `compare_type`，但筛选器全部在客户端组件里。**验证**：`ruff check backend_api/ review_analyzer/` 全过，`npx tsc --noEmit` 无报错 |
| 2026-06-23 | 分析结果页交互三大短板：1) 5 个独立 Tab 强制用户手动切换才能看到不同模块；2) 时间维度被锁死在 session 的 `date_range_start/end`，没法回头看"该产品最近 30 天"；3) 产品切换必须返回 `/analysis/history` 重新点击，结果页顶部没有产品搜索入口 | **后端**：1) `review_analyzer/database.py` 的 `get_comments` 新增 `date_start` / `date_end` 参数，按 ISO 字符串字典序过滤 `comments.date`；2) `backend_api/app/routes/analysis.py` 新增 `GET /analysis/results?product_id=&range=&start=&end=&session_id=` 聚合接口：跨 session 合并评论 → 调用 `build_results_insights` → 返回与 `AnalysisSessionResultsPayload` 同形 payload，30 分钟进程内缓存（key 含 comment_ids hash）；`_resolve_range` 支持 `default/7d/14d/30d/90d/all/custom`，`default` 优先用 session.date_range，缺失则取产品最近一个 session；3) `backend_api/app/routes/products.py` 新增 `GET /products/search?q=&limit=`，按 `parent_product_id`/`name` 模糊匹配，前缀命中优先 → 评论数降序。**前端**：1) 旧 `analysis-results-tabs.tsx` 删除，新建 `analysis-results-sections.tsx`（同名 props 形状），5 个 `<section id>` 长滚动 + 章节标题 + `scroll-mt-32` 偏移；2) 新建 `section-anchor-nav.tsx`（sticky top-68 + IntersectionObserver `rootMargin: -30% 0 -55% 0` 自动高亮）；3) 新建 `results-filter-bar.tsx`（sticky top-0，左产品 Combobox 右时间 Select，自定义范围用浮层 Popover + 两个 `<input type="date">`）；4) 新建 `product-search-combobox.tsx`（200ms debounce + 浮层下拉，纯手搓不引入 cmdk）；5) `results/page.tsx` 改造为 `?product_id=&range=&start=&end=&session_id=` URL 模型，老链接 `?session_id=N` 自动 redirect；6) `lib/api/server.ts` + `browser.ts` + `types.ts` 同步新增 `getAnalysisResults` / `searchProducts` / `AnalysisResultsResponse` / `ProductSearchResponse`。**验证**：`ruff check backend_api/ workers/ review_analyzer/` 通过；`npm run typecheck` 通过 |

| 2026-06-23 | Sidebar 底部"语言切换 + 用户信息"两行高曝光位被浪费，用户无法在业务页面感知套餐剩余额度；现有 `QuotaPanel` 藏在 `/settings` 深处，超额拒绝时才被动得知限制 | 新增 `frontend/src/components/quota/` 三个文件：`quota-groups.ts`（4 个业务分组 + 9 个 dimension 映射 + 共享 label/period/plan 常量 + nextResetDate 工具）、`quota-dialog.tsx`（Radix Dialog，复用 `ui/dialog` + `ui/tooltip`，按 monthly/daily/forever/concurrent/per_request 分别决定是否显示进度条和 used/limit）、`sidebar-quota-entry.tsx`（client component，fetch `/api/quota` 后渲染入口按钮 + 副文 `Free · 0/1500`，Free 用户右侧露出"升级套餐"链接到 `/pricing`）。`sidebar.tsx` 在 User info 区块上方插入入口；顺手把 `notLoggedIn / tagline / openMenu / closeMenu` 中文硬编码迁出到 i18n。`quota-panel.tsx` 改为 client component 并复用 `quota-groups.ts` 常量，文案接 next-intl。`messages/zh.json` 和 `en.json` 同步新增 `sidebar.quotaEntry/upgradeLink/tagline/notLoggedIn/openMenu/closeMenu`、`quotaPanel.*`、`quotaDialog.*` 命名空间（含 4 个分组 + 10 个 dimension label/hint）。**验证**：`npm run typecheck` 通过；Playwright 用临时账号 `quota_test_2026` 登录后访问 `/workspace`，确认 sidebar 入口副文显示 `Free · 0/1500`，点击打开弹窗后 4 个分组 9 个维度全部正确渲染（`upload_rows_per_file` 显示 "500" 无进度条、`compare_products` 显示 "0/2"），Tooltip hover 正常，`/settings` 页 QuotaPanel 9 张卡片重构后保持完整 |
| 2026-06-23 | `/upload` 页面右侧两个面板（STEP 2「任务状态」+「这次上传会做什么」）信息密度低且 STEP 2 在 `handleSubmit` 完成时已 `router.push` 跳转结果页，用户实际看不到运行中状态，仅展示永久空态文案；同时右栏挤占了 STEP 1 表单的横向空间 | 改 `frontend/src/components/upload/upload-form.tsx`：1) 外层 `<section>` 从 `grid xl:grid-cols-[1.05fr_0.95fr]` 改为 `space-y-6`，让 STEP 1 卡片单栏铺满；2) 删除右栏 `<div className="space-y-6">` 容器及内含的两个 `<section>` 面板；3) 删除仅在 STEP 2 面板里使用的 `statusTone()` 辅助函数；保留 `job`/`setJob`/`jobInProgress` 状态（提交按钮 disabled 和跳转逻辑仍依赖）；i18n 键（statusTitle/whatHappens* 等）保留不动避免影响其它页面。typecheck 通过 |
| 2026-06-23 | ECS 部署 `docker compose up -d --build` 失败：`next build` 报 `next/headers only works in Server Component`。根因：`upload/page.tsx` 标了 `"use client"` 但直接 import `AppShell`（async server component），`AppShell` 间接引入 `@/lib/api/server`（含 `import { cookies } from "next/headers"`），客户端组件不允许此引入链 | 拆分 `upload/page.tsx` 为 server component（只包裹 `AppShell`）+ `components/upload/upload-form.tsx`（`"use client"`，所有表单交互逻辑）。`npm run build` 本地验证通过 |
| 2026-06-22 | 生产站点 502 Bad Gateway（第二次）。推送 4 个新 commit（含新增 `export.py`、`translate.py` 路由 + 前端结果页重构 + `insight_engine.py` 修改）到 develop 后，ECS 容器未重建。根因与上次相同模式：代码 push 后 ECS 只 `git pull` 未执行 `docker compose up -d --build`，容器内代码与 `main.py` import 不一致导致 api 崩溃或 frontend 过期，nginx upstream 无响应返回 502。附带问题：Next.js standalone 模式 HOSTNAME 绑定容器 ID 而非 `0.0.0.0`，导致 healthcheck `wget localhost:3000` 不稳定 | **立即修复**：ECS 执行 `git pull origin develop && cd deploy && docker compose up -d --build api worker frontend && docker compose exec nginx nginx -s reload`。**根治措施**：1) `frontend/Dockerfile` 添加 `ENV HOSTNAME=0.0.0.0` 解决 standalone 绑定问题；2) `deploy/docker-compose.yml` frontend healthcheck 增加 retries=5 + timeout=10s + start_period=45s；3) 新增 `deploy/post-deploy-check.sh` 部署后自动验证所有容器健康状态 + 端点可达性；4) `.github/workflows/ci.yml` 新增 `backend-import-check` job，push 时自动验证 `from backend_api.app.main import app` 和 `from workers.jobs import process_upload_job` 能加载成功，彻底防止"文件未 git add"导致生产崩溃。**教训**：每次 push 到 develop 后必须在 ECS 执行完整的 `--build` 流程；CI 层面必须有 import 级别的 smoke test 作为硬防线 |
| 2026-06-22 | 分析结果页数据不稳定 + 页面过于简陋：1) LLM (DeepSeek) 返回 JSON 字段不完整时 `merged.update()` 整体覆盖 heuristic 有效值导致模块显示为空；2) heuristic fallback 数据太模板化无信息量；3) 页面没有图表、icon、色彩区分，不像成品 SaaS；4) 缺少翻译、下载、inline 行动创建等交互功能 | **后端加固**：`insight_engine.py` merge 逻辑改为字段级覆盖（空值不覆盖 heuristic）+ 新增 `_validate_ai_payload` 校验 AI 输出结构 + `_normalize_tag_row` 统一字段名 + heuristic 改善为含 pos_rate/neg_rate 统计的信息性 summary + TOP 10 限制。**前端重写**：`results/page.tsx` 全面重构为 Shulex 风格表格布局（TagRow 组件含排名 + 标签名 + PctBadge + progress bar + 证据引用），5 个模块各有独立色系 + Lucide icon，TOP issue/highlight 用 CalloutCard 高亮。**交互功能**：新增 `ModuleCard` 客户端组件（每个模块含翻译 + XLSX 下载按钮），新增 `InlineActionButton` 组件（负向标签旁 Dialog 弹窗创建行动）。**新后端路由**：`POST /translate/module`（DeepSeek 翻译）、`GET /analysis/sessions/{id}/export?module=xxx`（openpyxl 生成 XLSX）。tsc + build 全通过 |
| 2026-06-22 | 生产上传评论后分析进度永远卡在 0%（第三次出现）。**根因1（架构缺陷）**：浏览器发 `POST /api/uploads`，Next.js standalone 的 rewrite 把请求转到外网 `https://api.clueai-reviewlens.com/uploads`，绕回 nginx 再到后端——大文件上传在这条链路上不稳定，随机返回 404（HTML 错误页而非 JSON）。**根因2（Worker 数据库连接永久失败）**：Worker 容器 6 天前构建时镜像还包含 streamlit 依赖，`database.py` 的 `get_upload_job()` 触发 `NoSessionContext`；更核心的是连接池 `_get_connection_pool()` 首次创建失败后 `_connection_pool = None` 永不重试，后续每个 job 进来都立即抛 `DatabaseConnectionUnavailable` 且无法写入失败状态，job 永远卡在 `queued` | **修复1（架构级）**：在 `deploy/nginx.conf` 的前端 server 块新增 `location /api/` 直接 proxy 到 `clueai_api`，绕过 Next.js rewrite 层——浏览器 `/api/uploads` 请求不再经过 Node.js 进程，一步到位到 FastAPI。**修复2（连接池韧性）**：`review_analyzer/database.py` 的 `_get_connection_pool()` 新增重试机制——创建失败后记录时间戳，10 秒后允许再次尝试，不再"一次失败终身报废"。**部署**：`git pull && docker compose up -d --build worker && docker compose restart nginx`。**教训**：1) Next.js standalone rewrite 不适合代理大文件 POST，nginx 层应直接路由所有 API 请求；2) Worker 镜像必须随代码变更一起重建，不能只 recreate api/frontend；3) 连接池初始化必须有重试，单点失败不能永久锁死进程 |
| 2026-06-22 | 生产登录页报 "Authentication service unavailable"（503）。根因：API 容器内 `get_user_by_username()` → `get_connection()` 连接 Supabase 失败。`db.inpgrbjwtpxgwungghnz.supabase.co` 只解析出 IPv6 地址（`2406:da18:...`），ECS Docker 网络无 IPv6 路由，连接报 "Network is unreachable"。`/health` 端点不检查数据库因此 healthcheck 通过掩盖了真实故障。排障过程中 `docker compose restart` 多次未生效，因为 restart 不重读 `.env` 文件。另外镜像内 `review_analyzer/.env`（被 `load_dotenv()` 加载）也曾包含旧的 direct connection 地址 | 修复：将 `deploy/.env` 的 `DATABASE_URL` 从 direct connection（`db.*.supabase.co:5432`）改为 Supabase pooler 端点（`aws-1-ap-southeast-1.pooler.supabase.com:6543`，有 IPv4），然后 `docker compose up -d --force-recreate api` 重建容器使新环境变量生效。教训：1) 排查 503 应第一时间看 api 容器日志而非 nginx；2) 改 `.env` 后必须 `up --force-recreate` 而非 `restart`；3) 生产 DATABASE_URL 应统一使用 pooler 端点避免 IPv6-only 问题 |
| 2026-06-22 | 生产站点 502 Bad Gateway（复合故障，两阶段）。**阶段1**：api 容器反复崩溃重启。根因：`workers/jobs.py` 新增了对 `backend_api.app.services.taxonomy_coverage_monitor` 的 import 并提交，但该文件本身从未 `git add`，ECS 拉取后 api 容器启动即报 `ModuleNotFoundError` 崩溃循环。**阶段2**：api 修复后 502 仍持续。根因：frontend 容器已 3 天处于 `unhealthy` 状态（镜像过期，git pull 拉取了 125 个前端文件变更但未重建镜像）；nginx upstream 指向 frontend:3000，frontend 不响应则 502。附带发现：Next.js standalone 模式绑定容器 HOSTNAME（容器ID）而非 `0.0.0.0`，导致 `wget localhost:3000` 健康检查始终失败，但 Docker 内部 DNS 解析到容器实际 IP 后可达。另外 SSH 连接 ECS 超时（`KEXINIT sent` 后挂起），通过阿里云 VNC 远程连接绕过 | **阶段1修复**：本地 `git add backend_api/app/services/taxonomy_coverage_monitor.py` + commit `6f96695` + push develop，ECS `git pull && docker compose up -d --build api`，api 41 秒后 healthy。**阶段2修复**：ECS 执行 `docker compose up -d --build frontend`，重建镜像后 frontend 恢复；`docker compose exec nginx nginx -s reload` 刷新 upstream DNS；`docker compose restart nginx` 完成全链路恢复 |
| 2026-06-22 | SSH 连接 ECS 超时：`ssh -v` 显示 `SSH2_MSG_KEXINIT sent` 后挂起，但 `ping` 通且 `nc -zv port 22` 成功。服务器资源正常（CPU 3%、内存 780M/3.4G、磁盘 52%）。安全组 22 端口对 0.0.0.0/0 开放 | 原因未完全确认（可能是 sshd 负载或网络中间设备干扰）。临时绕过：使用阿里云控制台 VNC/Workbench 远程连接完成所有操作。建议后续排查 `/var/log/auth.log` 和 sshd 配置 |
| 2026-06-18 | 本地开发环境 embedding 代理方案优化：之前为解决代理导致全局请求卡死，一刀切清除了所有代理变量，导致 OpenAI embedding 在国内直连不通、batch失败后跳过、聚类优化失效、432条评论全部逐条走 LLM（本可优化为~150次） | 修复：`review_analyzer/rag.py` 的 `_get_embedding_client` 改为通过 `httpx.Client(proxy=...)` **单独**给 OpenAI embedding 客户端配代理（读取 `.env` 中的 `EMBEDDING_PROXY=http://127.0.0.1:7890`），不再依赖全局环境变量。DeepSeek LLM 和 Supabase DB 继续直连不受影响。生产环境（香港 ECS）不设此变量，OpenAI 直连可达 |
| 2026-06-18 | 上传432条评论后进度条一直卡在0/432不动，持续10+分钟 | 根因：`review_analyzer/rag.py` 的 `generate_embeddings_batch` batch请求失败时回退到逐条单独调用（432条×5s超时=36分钟）。OpenAI在无代理环境下不可达，2个batch各失败后触发432次单条超时调用，embedding阶段无限期阻塞。修复：删除单条回退逻辑，batch失败直接跳过整批（填空vector），embedding是可选优化，不影响LLM分析主流程 |
| 2026-06-18 | 分析432条评论进度卡住（`processed_rows`从28停止不动，总耗时20+分钟），根本原因是OpenAI Python SDK默认`max_retries=2`：每个LLM调用失败时SDK自动重试2次，每次最多30s，3个fallback模型（DeepSeek→OpenAI→Qwen）叠加后单条评论最坏耗时270s（30s×3次×3模型）；在代理关闭环境下DeepSeek/OpenAI各超时90s后才切Qwen，导致整体分析速度极慢并最终卡死 | 修复：在`backend_api/app/services/llm_router.py`和`review_analyzer/rag.py`的OpenAI客户端构造中加`max_retries=0`——我们自己的fallback链已经处理重试，不需要SDK层再重试，失败立即切下一个模型 |
| 2026-06-18 | 开启 Clash（127.0.0.1:7890）时，本地前端 webpack 模式下所有页面报 `Cannot read properties of undefined (reading 'call')`，指向 `app-shell.tsx:32` 的 `<Sidebar />` 渲染 | 根因：macOS 系统代理将浏览器对 `localhost` 的 webpack chunk 请求路由到 Clash，webpack HMR 模块解析被干扰。修复：将 `frontend/package.json` 的 `dev` 脚本恢复为 `next dev --turbopack --hostname 127.0.0.1`（Turbopack 不受此影响）。注：之前 6-17 改回普通 webpack 的决策有误，Turbopack 才是 VPN 环境下的正确选择 |
| 2026-06-18 | 点击登录按钮后页面无反应，按钮几秒后恢复原状，用户需反复点击。Network 显示 login → 200，workspace RSC → 200（耗时 16s），但页面始终停在登录表单 | 根因：`router.push(“/workspace”)` 使用 Next.js 软导航，需先下载目标页 RSC payload 才跳转；workspace SSR 调后端数据慢（16s），期间用户看不到任何导航反馈，`finally { setLoading(false) }` 又会让按钮恢复。修复：将 `login-form.tsx` 的跳转从 `router.push` 改为 `window.location.href = “/workspace”`（硬跳转，浏览器立即导航），并移除成功路径的 `setLoading(false)` 保持按钮为”登录中...”直到页面卸载 |
| 2026-06-18 | 登录后 workspace 首次加载 16 秒，上传评论时报 `500: Database connection pool is unavailable`，分析 job 卡在 `processing` / `processed_rows=0` 永不完成 | 根因：后端 uvicorn 进程启动时继承了 shell 的 `http_proxy` / `https_proxy` 环境变量（指向 Clash 127.0.0.1:7890）。OpenAI embedding 客户端（`api.openai.com`）的 socket connect 被代理黑洞 — Python 3.14/macOS 上 `timeout=60.0` 无法正确限制 connect 阶段，导致 3 个分析守护线程全部永久挂死在 `sock_connect`。修复：1) 重启后端时显式清除所有代理变量；2) 在 `review_analyzer/rag.py` 和 `backend_api/app/services/llm_router.py` 中将 OpenAI 客户端 timeout 改为 `httpx.Timeout(60.0, connect=5.0)`，确保网络不通时 5 秒快速失败。已将 3 个卡住的 job 标记为 failed |
| 2026-06-18 | 端到端测试报错 `UndefinedColumn: column "title" does not exist` — `review_analyzer/database.py` 的 `get_session_embeddings` 查询引用了 comments 表不存在的 title 列 | 修复：从 `get_session_embeddings` 的 SELECT 语句中移除 `title` 字段，只查询 `id, content, rating, embedding::text` |
| 2026-06-18 | 端到端测试报错 `UndefinedColumn: column "cache_hit_level" of relation "comments" does not exist` — migration 014 未在 dev 数据库执行成功（Supabase statement_timeout 限制无法 ALTER TABLE） | 修复：将 `review_analyzer/database.py` 的 `update_comment_analysis` 改为优雅降级 — 有 cache_hit_level 数据时尝试写入含缓存字段的 SQL，若列不存在则自动回退到不含缓存字段的基础 SQL |
| 2026-06-18 | `http://127.0.0.1:3000/upload` 无限 307 重定向循环，页面无法打开 | 根因：`next-intl` middleware（v4.13）在 `localePrefix: "never"` 配置下既做了内部 rewrite（→ `/zh/upload`）又发了外部 redirect（→ `/upload`），形成死循环。页面路由结构（`src/app/upload/page.tsx`）没有 `[locale]` 动态段，rewrite 目标无法匹配。修复：将 `frontend/src/middleware.ts` 从 `next-intl createMiddleware` 替换为简单的 NextResponse.next() + NEXT_LOCALE cookie 设置，去掉 locale 路由重写。需重启 dev server 才生效（Turbopack 不热更新 middleware） |
| 2026-06-18 | 登录进入系统后几秒报 Runtime Error：`Module lucide-react/dist/esm/icons/layout-dashboard.js was instantiated because it was required from sidebar.tsx, but the module factory is not available` | 根因：`sidebar.tsx` 之前使用过 `LayoutDashboard` 图标（已在历史修改中移除），但浏览器 HTTP 缓存仍持有旧的 Turbopack 模块图 chunk，新旧模块引用冲突。修复：`Cmd+Shift+R` 硬刷新清除浏览器缓存（非代码问题） |
| 2026-06-17 | 本地链路频繁报错，用户希望有一个真正的”一键重建”入口，避免再靠手动清进程、删缓存、猜端口来排障 | 新增 [`scripts/rebuild_frontend_local.sh`](/Users/zhangxi/Desktop/Claude%20Code/评论分析_Web_系统/scripts/rebuild_frontend_local.sh)，会先检查 `3000` 监听、读取 `frontend/.env.local`、探测 `8000` 健康状态，再清空 `.next`、关闭当前工作区旧前端实例并重启 `next dev`；同时在 [`frontend/package.json`](/Users/zhangxi/Desktop/Claude%20Code/评论分析_Web_系统/frontend/package.json) 暴露 `npm run rebuild:local`，并把用法补进 [`前端启动停止操作规范.md`](/Users/zhangxi/Desktop/Claude%20Code/评论分析_Web_系统/前端启动停止操作规范.md) |
| 2026-06-17 | 前端环境虽然已重装，但登录页点击后仍然报 hydration mismatch，DevTools 里还能看到 `page.js` 从 disk cache 命中，说明浏览器仍在拿旧 bundle | 将 [`frontend/next.config.ts`](/Users/zhangxi/Desktop/Claude%20Code/评论分析_Web_系统/frontend/next.config.ts) 的开发环境静态资源策略从“无 headers”升级为 `no-store, no-cache, must-revalidate, proxy-revalidate`，并同步设置 `Pragma: no-cache` / `Expires: 0`；目标是让 `/_next/static` 和字体资源在 dev 模式下彻底不走缓存，避免旧 `page.js` 继续和新服务端渲染打架 |
| 2026-06-17 | 登录页在浏览器里一直出现服务端/客户端文本不一致，截图中 `Username` 和 `用户名` 交替出现，导致无法稳定进入系统，且历史上还反复出现过类似的旧 bundle / 旧进程问题 | 本轮确认真正的根因不是登录表单文本本身，而是前端开发环境把 `/_next/static` 资源设置成了长缓存，导致浏览器持续拿到旧的客户端 bundle；先在 [`frontend/next.config.ts`](/Users/zhangxi/Desktop/Claude%20Code/评论分析_Web_系统/frontend/next.config.ts) 中将该缓存策略限制到 production 环境，开发环境返回空 headers，避免旧 JS 继续覆盖最新代码；同时新增 [`scripts/rollback_frontend_hydration_fix.sh`](/Users/zhangxi/Desktop/Claude%20Code/评论分析_Web_系统/scripts/rollback_frontend_hydration_fix.sh)，可一键把本次前端修复相关文件回滚到 `HEAD`，作为这次大修的安全回滚点 |
| 2026-06-17 | 用户登录后进入 `/workspace` 仍然报 `Cannot read properties of undefined (reading 'call')`，刷新首页也无法稳定恢复，说明问题还没有真正收口 | 本轮先做了前端运行时排查和减法式定位：确认 `frontend/` 下的 dev server 仍在 `3000` 监听，重启后类型检查通过，但浏览器里的 runtime error 依旧指向 [`frontend/src/components/app/app-shell.tsx`](/Users/zhangxi/Desktop/Claude%20Code/评论分析_Web_系统/frontend/src/components/app/app-shell.tsx) 第 32 行的 `<Sidebar currentPath={currentPath} />`；因此我临时把 [`frontend/src/components/app/sidebar.tsx`](/Users/zhangxi/Desktop/Claude%20Code/评论分析_Web_系统/frontend/src/components/app/sidebar.tsx) 里的 `Button asChild`、图标依赖和 `Separator` 全部拆平成原生元素，尝试排除客户端包装层 / HMR 状态问题，但页面报错依旧存在，说明根因大概率还在 `AppShell` 这条渲染链的其他客户端子树或 dev server 缓存状态 |
| 2026-06-17 | 仅有单点接口测试还不够，`/auth/login` 和 `/workspace/summary` 串起来以后还要确认登录态 cookie 真能把用户带进工作台 | 新增 [`backend_api/tests/test_login_workspace_chain.py`](/Users/zhangxi/Desktop/Claude%20Code/评论分析_Web_系统/backend_api/tests/test_login_workspace_chain.py)，真实走一次登录接口后再访问 `/workspace/summary`，验证认证 cookie、`get_current_user()` 和工作台兜底层可以连续工作，防止“各自通过、串起来失败”的回归 |
| 2026-06-17 | “Login failed (500)” 表象已经收口，但为了彻底避免以后再复发，需要把真正的脆弱点收紧到后端接口层，而不是只靠前端降级兜底 | 在 [`backend_api/app/routes/workspace.py`](/Users/zhangxi/Desktop/Claude%20Code/评论分析_Web_系统/backend_api/app/routes/workspace.py) 为 `/workspace/summary` 增加统一规范化层，对 `intro`、`metrics`、`today_tasks`、`risk_products`、`pending_trackers`、`role_action_summary`、`recent_sessions` 的缺失或脏字段全部补默认值；新增 [`backend_api/tests/test_workspace_routes.py`](/Users/zhangxi/Desktop/Claude%20Code/评论分析_Web_系统/backend_api/tests/test_workspace_routes.py) 回归测试，验证上游返回 `None`、错误类型或字符串数字时接口仍能稳定返回 200，避免登录后首屏再次因脏数据崩溃 |
| 2026-06-17 | 上传评论后分析进度一直停在 0，点击分析结果页又容易直接报错 | 上传链路补上逐步进度回写：`backend_api/app/services/deep_analyzer.py` 新增 `progress_callback`，`workers/jobs.py` 按缓存命中 + LLM 实际完成数持续更新 `processed_rows`；结果页则在 [`frontend/src/app/analysis/results/page.tsx`](/Users/zhangxi/Desktop/Claude%20Code/评论分析_Web_系统/frontend/src/app/analysis/results/page.tsx) 增加模块归一化和候选项过滤，避免脏数据把整页渲染拖垮 |
| 2026-06-17 | 登录接口本身已经恢复，但用户登录后进入 `/workspace` 时前端运行时崩溃，浏览器报 `Cannot read properties of undefined (reading 'call')`，导致看起来像“登录失败” | 先修后端登录链路的脆弱点：`backend_api/app/routes/auth.py` 为 `bcrypt.checkpw()` 增加异常兜底，旧/脏 `password_hash` 统一按 401 处理，并把数据库不可用显式转成 503；随后为了保证用户能先登录进系统，临时把 [`frontend/src/app/workspace/page.tsx`](/Users/zhangxi/Desktop/Claude%20Code/评论分析_Web_系统/frontend/src/app/workspace/page.tsx) 降级成稳定落地页，避免工作台复杂渲染链再次把登录后的跳转页炸掉；同时对 [`frontend/src/components/app/sidebar.tsx`](/Users/zhangxi/Desktop/Claude%20Code/评论分析_Web_系统/frontend/src/components/app/sidebar.tsx) 做了更稳的 `Link` 渲染收口，并补充了登录路由回归测试，最终让用户能够稳定登录进入系统 |
| 2026-06-17 | 网站已经恢复正常访问，需要把这次补充加固和修改痕迹补进测试记录，避免后续只看到“能打开”却看不到具体改了什么 | 本次补充修改集中在启动与缓存层：[`frontend/package.json`](/Users/zhangxi/Desktop/Claude%20Code/评论分析_Web_系统/frontend/package.json) 的 `dev` 脚本绑定 `127.0.0.1`，[`frontend/src/app/layout.tsx`](/Users/zhangxi/Desktop/Claude%20Code/评论分析_Web_系统/frontend/src/app/layout.tsx) 增加 `no-store` / `no-cache` / `Expires: 0` 头，[`scripts/check_frontend_port.sh`](/Users/zhangxi/Desktop/Claude%20Code/评论分析_Web_系统/scripts/check_frontend_port.sh) 增强旧进程提示；复测后网站可正常打开 |
| 2026-06-17 | 需要把前端启动/停止的正确操作单独沉淀成可见文档，避免以后再次因为旧实例残留或误关窗口而重复踩坑 | 新增根目录文档 [`前端启动停止操作规范.md`](/Users/zhangxi/Desktop/Claude%20Code/评论分析_Web_系统/前端启动停止操作规范.md)，把启动前检查、正确启动/停止方式、常见误操作和这次问题结论整理成可直接照做的步骤 |
| 2026-06-17 | 启动前端时增加端口守卫后，脚本成功识别到当前 `3000` 监听进程并确认其 cwd 为本仓库 `frontend/`，证明残留的不是别的项目而是当前工作区的前端实例 | [`scripts/check_frontend_port.sh`](/Users/zhangxi/Desktop/Claude%20Code/评论分析_Web_系统/scripts/check_frontend_port.sh) 已可用：若 `3000` 端口被占用，会输出 PID/cwd/exec 并阻止再次启动；结合 `~/.zsh_history` 中的 `cd frontend` + `npm run dev`，可以把根因稳定归因为“手动启动后的会话未结束” |
| 2026-06-17 | 本地前端 `npm run dev` 反复遇到旧实例残留时缺少启动前告警，容易直接撞上 `3000` 端口的后台 `next dev` | 新增 [`scripts/check_frontend_port.sh`](/Users/zhangxi/Desktop/Claude%20Code/评论分析_Web_系统/scripts/check_frontend_port.sh)，并接入 [`frontend/package.json`](/Users/zhangxi/Desktop/Claude%20Code/评论分析_Web_系统/frontend/package.json) 的 `predev`：启动前检测 `3000` 是否已有监听进程，若已有则输出 PID/cwd 并阻止再次启动；结合 shell 历史与当前进程确认，残留实例更像是之前手动启动后的会话未结束，而不是项目自启动 |
| 2026-06-17 | 本地 `http://localhost:3000/` 页面持续返回 `Internal Server Error`，上传评论后也曾出现 `Request failed with status 500` / `Failed to fetch`；排查后确认上传链路与首页 SSR 是两个独立问题 | 本次只做排查和代码记录，不继续推进新修复；期间已经加入上传任务兼容回退、前端 dev 启动参数调整、AnalyticsProvider 容错等修改，详见下方“本次排查记录” |
| 2026-06-17 | 补充确认：`http://localhost:3000/` 在重新用当前工作区启动 `npm run dev` 后已恢复正常访问；此前 500 的直接触发条件更像是浏览器命中的前端实例处在旧进程/旧构建状态，首页 SSR 的 metadata URL 链路又缺少兜底，导致该状态一旦异常就直接暴露为 500 | 在 [`frontend/src/lib/seo.ts`](/Users/zhangxi/Desktop/Claude%20Code/评论分析_Web_系统/frontend/src/lib/seo.ts) 新增 `getMetadataBaseUrl()` 和 `absoluteUrl()` 回退；在 [`frontend/src/app/layout.tsx`](/Users/zhangxi/Desktop/Claude%20Code/评论分析_Web_系统/frontend/src/app/layout.tsx) 用安全 `metadataBase` 替代顶层 `new URL(siteUrl)`；随后重启前端服务并复测首页返回 200 |
| 2026-06-16 | 端口检查脚本第一次运行时报 `grep` 将 `--port` 识别成参数，导致自检脚本误报失败 | 在 `scripts/check_port_migration.sh` 的 `grep` 调用中增加 `--`，让模式字符串按普通正则处理；随后脚本复测通过 |
| 2026-06-16 | 端口迁移后缺少可重复执行的自动检查入口，容易只改配置不验证最终运行态 | 新增 `scripts/check_port_migration.sh`，只检查运行时相关文件中的 `8000` / `3000` 是否一致；并把脚本写入 [`docs/PORT_MIGRATION_CHECKLIST.md`](/Users/zhangxi/Desktop/Claude%20Code/评论分析_Web_系统/docs/PORT_MIGRATION_CHECKLIST.md)、[`CLAUDE.md`](/Users/zhangxi/Desktop/Claude%20Code/评论分析_Web_系统/CLAUDE.md) 和 [`CODEX.md`](/Users/zhangxi/Desktop/Claude%20Code/评论分析_Web_系统/CODEX.md) 作为强提醒 |
| 2026-06-16 | 端口迁移和部署配置容易再次混淆，修改时缺少统一检查入口，容易遗漏 `8100` / `8000` / `3000` 的运行时差异 | 新增 [`docs/PORT_MIGRATION_CHECKLIST.md`](/Users/zhangxi/Desktop/Claude%20Code/评论分析_Web_系统/docs/PORT_MIGRATION_CHECKLIST.md)；并在 [`CLAUDE.md`](/Users/zhangxi/Desktop/Claude%20Code/评论分析_Web_系统/CLAUDE.md) 中加入修改端口/环境变量/部署链路前必须先读清单的强提醒 |
| 2026-06-16 | 后端本地开发、Docker Compose、Nginx 与前端默认 API 地址存在 `8100` / `8000` 混用，导致本地 `3000 -> 8000`、容器内 `frontend -> api`、以及健康检查链路容易错位 | 统一后端默认端口为 `8000`：更新 `backend_api/Dockerfile`、`deploy/docker-compose.yml`、`deploy/nginx.conf`、`frontend/src/lib/api/server.ts`、`frontend/src/lib/api/browser.ts`，并在部署文档中注明后端 `8000` / 前端 `3000` 的固定分工 |
| 2026-06-16 | 本地前端 `/api/*` 重写与本地实际后端端口不一致，登录请求会打到错误地址，表现为点击后没反应或长时间无反馈 | 将 `frontend/next.config.ts` 和 `frontend/src/lib/api/server.ts` 的默认 API 地址统一为 `http://127.0.0.1:8000`，与本地后端实际监听端口一致。注：`.env.local` 无需设置 `NEXT_PUBLIC_API_BASE_URL`，代码默认值已正确 |
| 2026-06-16 | 登录页与注册页在请求进行中缺少重复提交保护，用户可能在网络慢或首个请求未返回时连续点击，造成“点多次才成功”的误感知 | 在 `frontend/src/components/auth/login-form.tsx` 和 `frontend/src/components/auth/register-form.tsx` 的提交入口加入 `loading` 保护，避免重复提交 |
| 2026-06-16 | 登录/注册成功后前端还要额外请求一次 `/api/me` 才跳转，导致成功反馈延迟，放大“要点几次才进去”的体感 | 登录/注册表单直接使用 `/api/auth/*` 返回的 `user` 数据完成 `identify` 和跳转，移除额外的 `/api/me` 往返 |
| 2026-06-16 | 审查阶段新增根目录审查计划文档，明确先审查后修复、每次修改必须记录 bug / 修复 / 测试结果 | 新增 [`CODE_REVIEW_PLAN.md`](/Users/zhangxi/Desktop/Claude%20Code/评论分析_Web_系统/CODE_REVIEW_PLAN.md) 作为标准审查流程说明 |
| 2026-05-07 | Streamlit Cloud 启动报错 `ModuleNotFoundError: No module named 'review_analyzer'` | app.py 顶部加入 `sys.path.insert(0, parent_dir)` 将仓库根目录加入路径 |
| 2026-05-07 | 上传 xlsx 文件报错 `parse_file() missing 1 required positional argument: 'file_type'` | upload.py 改为先写临时文件、提取扩展名，再调用 `parse_file(tmp_path, file_type)` |
| 2026-05-07 | 上传 xlsx 后 `review_id` 被误识别为评论内容，真正的 `review_text` 被塞入 raw_data | parser.py 列名匹配改为优先精确匹配，子串匹配时排除 `_id` 结尾的列 |
| 2026-05-07 | 点击分析评论报错 `analyze_batch() missing required argument: 'api_key'` | upload.py 补充 `api_key=get_api_key(user_id)` 参数传入 |
| 2026-05-07 | 分析完成后导出结果情感/分类/优先级等字段全部为空 | upload.py 传给 `analyze_batch` 的 comments 从字符串列表改为 dict 列表 `[{"content": ..., "rating": ...}]` |
| 2026-05-08 | 重复上传同一文件后仪表盘数据累加（未去重） | 仪表盘改为按 `content_hash` 去重统计，新增 `get_product_stats_deduped` 和 `get_comments_deduped` 查询 |
| 2026-05-08 | 修复代码推送到 develop 但 Streamlit Cloud 连接的是 main 分支，导致修复未生效 | 将 develop 合并到 main 并推送，触发 Streamlit Cloud 重新部署 |
| 2026-05-08 | 上传重复数据时提示"没有可分析的数据"，语义不清 | 区分全部重复/部分重复两种情况，提示改为"上传数据重复" |
| 2026-05-08 | 行动建议用 HTML 标签+符号展示，普通运营看不懂 | 分析结果页和仪表盘的行动建议全部改为自然语言输出 |
| 2026-05-08 | 宣传文案页平台按钮点击后颜色闪回，无法确认选中状态 | 选中平台使用 `type="primary"` 按钮，未选中使用 `type="secondary"` |
| 2026-05-08 | 宣传文案页只输出占位文本，未实际生成广告文案 | 接入 DeepSeek API 实际生成广告文案和理想产品描述 |
| 2026-05-08 | 小标题旁有无用的锚点链接按钮 | 全局 CSS 隐藏 `.stMarkdown h1~h6 a` 和 `stHeaderActionElements` |
| 2026-05-09 | 欢迎页只有"免费试用"和"登录"两个按钮，新用户找不到注册入口 | 欢迎页改为三按钮布局：「立即免费试用」「注册账号」「已有账号，登录」；注册按钮跳转登录页并默认选中注册 Tab |
| 2026-05-09 | 负面率计算不准确（25.9% vs 预期 21.93%），有评分的评论未按评分覆写情感 | 有评分：≤3 负面、≥4 正面（覆写 AI 分析结果）；无评分：使用 AI 情感分析 |
| 2026-05-09 | unrecognizable（无效评论）被计入正面率/负面率分母，导致比例失真 | 统计时排除 unrecognizable，页面显示「无效评论 X 条（不参与统计）」；仪表盘同步修改 |
| 2026-05-09 | 重复检测仅用 content 字段 hash，同内容不同评分/日期的评论被误判为重复 | hash 改为 content+rating+date+reviewer 四字段组合；空内容有评分不算重复；完全空行直接跳过 |
| 2026-05-09 | 历史记录作为独立页面，用户需在侧边栏切换，查看分析结果时无法直接访问历史 | 历史记录整合到分析结果页底部 expander，移除侧边栏「历史记录」导航和独立路由 |
| 2026-05-09 | 分析结果页无时间筛选功能，无法按时间段查看子集数据 | 新增时间筛选栏（全部/7天/14天/30天/90天/自定义），所有选项均弹出日期选择器供精确调整，以数据最新日期为基准推算默认值 |
| 2026-05-09 | 时间环比只有占位文字，无实际对比数据 | 实现自动时间环比：根据数据跨度提供周/双周/月环比选项，自动划分当期 vs 上期，展示正面率/负面率变化和 TOP 问题环比 |
| 2026-05-09 | 历史记录中产品多时查找困难，无搜索功能 | 历史记录区域顶部新增产品搜索框，输入 SKU 关键词即时筛选 |
| 2026-05-11 | Streamlit Cloud 部署环境为 Python 3.9，不支持 `X \| Y` 联合类型语法 | 所有模块顶部添加 `from __future__ import annotations` 兼容 Python 3.9 |
| 2026-05-11 | `requirements.txt` 在子目录下，Streamlit Cloud 无法自动识别依赖 | 将 `requirements.txt` 复制到仓库根目录供 Streamlit Cloud 识别 |
| 2026-05-11 | 评分覆写逻辑遇到浮点格式评分（如 `'3.0'`）时 `int()` 报错 | 评分转换改为 `int(float(rating))` 兼容浮点格式 |
| 2026-05-11 | 情感分布饼图未排除 unrecognizable，导致比例失真 | 饼图排除 unrecognizable，使用 `valid_total` 作为计算基数 |
| 2026-05-11 | 重复检测 hash 仅含 content+rating+date+reviewer，缺少 source 和其他字段 | hash 加入 source + raw_data，所有字段完全一致才判定为重复 |
| 2026-05-11 | 历史记录在 expander 中折叠，产品搜索框不可见，交互体验差 | 历史记录去掉 expander 直接展示，产品搜索框直接可见 |
| 2026-05-11 | 时间筛选只查当前 session 数据，选 90 天时无法覆盖历史 session | 时间筛选支持跨 session 合并，自动拉取同产品同版本的历史数据 |
| 2026-05-11 | 环比功能仅支持固定周期，无法选择时间粒度和版本维度 | 环比功能重做：支持时间粒度（周/双周/月）+ 版本筛选（同版本/跨版本）+ 跨 session 数据合并 |
| 2026-05-25 | 评分2星但评论内容正面时，issue_tag 被强制置空导致差评池中该条评论无标签贡献 | SYSTEM_PROMPT 新增矛盾处理规则：sentiment 按评分，highlight_tag/issue_tag 按内容实际提取 |
| 2026-05-25 | 混合评论（既有亮点又有问题）的 issue_tag 和 highlight_tag 互斥，丢失一半信息 | 输出格式改为 issue_tags/highlight_tags 数组，允许同时填写；新增"混合评价"分类 |
| 2026-05-25 | 同一评论多个同义抱怨被重复计入标签统计（如 "包装破损" 出现两次计2次） | extract_tags_from_comments、_get_top_tags、exporter、notifier 均加入单条评论内去重逻辑 |
| 2026-05-25 | 正负率只有评分版，无法反映评论内容的真实口碑 | 新增 content_sentiment 字段（基于文字内容判断），results.py 新增双版本正负率对比展示（仅在同时有评分和文字内容时出现）|
| 2026-05-25 | 修改 Prompt 后历史数据口径失控，无法追踪哪批数据用的哪个版本 | analyzer.py 新增 PROMPT_VERSION 常量（当前 v2.1）；sessions 表新增 prompt_version 列；结果页标题展示版本号；环比时若两批数据 Prompt 版本不一致自动显示警告 |
| 2026-05-25 | SYSTEM_PROMPT 输出格式分隔符不规范（`/` 而非 `|`），字段说明缺失导致 LLM 理解不稳定 | SYSTEM_PROMPT 升级至 v2.1：规范分隔符为 JSON Schema 标准风格（`|`），新增 4 条字段说明，category 选择规则独立段落 |
| 2026-05-11 | 欢迎页注册按钮指向 prototype.html 而非 Streamlit 应用 | 修正欢迎页注册入口，三按钮布局：「免费注册」「先试用」「已有账号，登录」 |
| 2026-05-13 | 全站 UI 风格不统一，紫色主题与各页面配色不协调 | 全站切换为 Ventriloc 风格：白底灰卡、Inter+Montserrat 字体、#ff682c 橙色点缀、扁平无阴影、统一标题层级（L1 编号徽章 + L2 彩色圆点） |
| 2026-05-13 | Landing 页使用渐变背景和大量 emoji，视觉噪音大 | 移除渐变/阴影/emoji，改为纯色扁平 + 序号标记 + ghost 按钮 |
| 2026-05-13 | 推送设置页规则区域排版凌乱，标题层级不清晰 | 规则行改为单行紧凑布局，标题分级为 L1 编号徽章 + L2 彩色圆点分类（问题红/环比蓝/亮点绿/其他灰） |
| 2026-05-13 | 分析结果页 emoji 图标和紫色配色与新风格不匹配 | 指标卡图标改为几何符号，图表配色统一为绿/红/橙，标题改为编号徽章风格 |
| 2026-05-13 | 数据库迁移：SQLite → Supabase PostgreSQL（详见下方专项记录） | 最终方案：psycopg2-binary + packages.txt(libpq-dev) + 同步 review_analyzer/ 目录下的依赖文件 |
| 2026-05-25 | 邮箱验证码找回密码功能始终失败（详见下方专项记录） | 最终方案：Resend SDK + 验证自有域名 clueai-reviewlens.com，修复 login.py 发送失败静默跳转 bug |
| 2026-05-25 | AI 返回的 issue_tag / highlight_tag 存在同义词变体（如"packaging damage"和"包装损坏"被算作两个不同标签），导致 TOP10 统计被稀释 | config.py 新增 TAG_NORMALIZE_MAP（标准词→变体映射表，覆盖 8 个类目中英文同义词），analyzer.py 新增 _normalize_tag / _normalize_tag_field，在 _validate_result 写库前将所有 tag 变体统一映射到标准词；找不到映射的新词原样保留，不丢失新问题信号 |
| 2026-05-25 | 分析结果页点击"开始分析"报错 `TypeError: 'NoneType' object is not subscriptable`，原因是 `created_at` 字段为 None 时对其做 `[:16]` 切片 | results.py 第228行改为 `(s.get("created_at") or "")[:16]`，防御 None 值 |
| 2026-05-25 | 上传一次但结果页显示同样评论源数据 4 条 | 根因：Streamlit 在分析期间 WebSocket 心跳重新执行脚本，Step 3 的 create_session + add_comments_batch 被重复调用；修复：用 `analyzing_session_id` 在 session_state 中保护，只在首次执行时创建 session 和插入评论，脚本重跑时复用同一 session_id |
| 2026-05-25 | Settings 页面已有环比规则配置 UI（负面率环比、问题占比环比、亮点环比），但 notifier.py 的 check_global_rules() 完全未实现这些逻辑，导致用户配置后永远不触发 | 新增 _get_prev_neg_rate() / _get_prev_top_issues() 辅助函数查询历史批次；check_global_rules() 补全三条环比规则：负面率环比突增、问题占比环比突增、亮点环比变化；should_notify() 签名同步增加 user_id / session_id 参数，透传给规则引擎 |
| 2026-06-03 | V2 RAG/付费代码检查发现 Ask your reviews 未接入结果页、`get_user_plan()` 缺失、users 表缺少付费字段、Paddle webhook 字段不一致 | 新增 rag.py 评论问答模块并接入结果页；补齐 get_user_plan/update_user_plan/get_user_product_count；schema 增加 plan/paddle_customer_id/embedding；修复 webhook custom_data 和 paddle_customer_id 字段 |
| 2026-06-03 | Ask your reviews 仅为文本检索版，未真正生成 embedding 或使用 pgvector 余弦检索 | 新增 embedding 生成、评论向量入库、上传后批量向量化、历史评论按需补齐、`embedding <=> query_embedding` Top-K 检索；文本检索保留为 fallback |
| 2026-06-03 | 上传评论时报错 `psycopg2.errors.UndefinedColumn: column "workflow_purpose" of relation "sessions" does not exist` | `create_session()` 增加数据库兼容降级：若 `sessions` 尚未迁移出 `workflow_purpose/product_ref_id/variant_ref_id`，自动回退到旧字段插入，避免本地上传被 schema 阻塞 |
| 2026-06-04 | 评论分析页上传文件后，用户不容易在首屏找到“开始分析”，完成分析后也缺少“这就是刚生成结果”的承接提示 | 上传页在文件解析成功后前置“开始分析并查看结果”按钮；分析完成后写入跳转标记，结果页显示“本次评论已分析完成，结果页已自动打开”提示 |
| 2026-06-04 | 评论工作流重构后存在旧导航残留、上传完成未稳定进入新结果容器、对比页导出结构与页面矩阵不一致 | 统一一级导航与 `评论分析` 子页路由；上传完成固定跳到 `评论分析 > 分析结果`；结果/对比页补齐翻译缓存隔离；对比页 XLSX 导出兼容矩阵结构；问评论补充产品范围与引用来源展示 |
| 2026-06-04 | 本地登录时报错 `could not translate host name ...pooler.supabase.com`，用户无法判断是 DNS、配置还是网络问题 | `database.py` 新增本地 `DATABASE_URL/SUPABASE_DB_URL` 覆盖逻辑，并按“主机名解析失败 / 网络不通 / 连接串缺失”三类输出明确排查提示；文档补充 `.env` 本地覆盖说明 |
| 2026-06-05 | 打开 `http://localhost:8502/` 未登录时仍显示旧欢迎页，看不到新版本地预览效果 | `app.py` 的未登录默认分支改为直接渲染新版欢迎页 `render_landing_page(variant="refresh")`；旧版仍保留在“预览当前欢迎页”入口中 |
| 2026-06-05 | 切换未登录默认新版欢迎页后报错 `TypeError: render_landing_page() got an unexpected keyword argument 'variant'` | 将欢迎页版本切换改为通过 `st.session_state["landing_preview_variant"]` 控制，`render_landing_page()` 恢复为无参函数，避免 Streamlit 热更新残留旧函数签名时崩溃 |
| 2026-06-05 | 同一浏览器会话里访问过旧版预览后，重新打开 `http://localhost:8502/` 仍会被 `force_public_preview` 状态带回旧版 | 调整 `app.py` 路由顺序：未登录访问时优先清除 `force_public_preview` 并固定渲染新版欢迎页，避免旧预览状态覆盖默认首页 |
| 2026-06-05 | 本地 `8502` 端口确认运行的是 `review_analyzer/app.py`，但欢迎页仍可能因内部默认分支回落到旧版 | 收紧 `landing.py` 的版本决策：默认一律渲染新版，只有显式处于 `force_public_preview` 且选择了 `current` 时才展示旧版欢迎页 |
| 2026-06-05 | 新版欢迎页的大段 HTML 被当作普通文本显示，页面出现 `<div class="refresh-hero">` 等源码内容 | `landing.py` 新增统一 HTML 渲染助手，对多行 HTML 先 `dedent().strip()` 再传给 `st.markdown(..., unsafe_allow_html=True)`，避免缩进触发 Markdown 代码块渲染 |
| 2026-06-08 | ECS 基础环境后续部署文档未明确宿主机 `nginx` 与 compose 内置 `nginx` 的 80 端口冲突，容易导致 `docker compose up` 启动失败 | 在 `docs/deployment-nextjs-fastapi-aliyun.md` 中补充：若采用 `deploy/docker-compose.yml` 的内置 `nginx`，需先停用宿主机 `nginx`，避免 80 端口冲突 |
| 2026-06-08 | ECS 上从 GitHub 拉取的仓库缺少 `webhook/` 目录，导致 `backend_api/Dockerfile` / `workers/Dockerfile` 构建时 `COPY webhook` 失败 | 删除两个 Dockerfile 中对 `webhook/` 的无必要复制，保持 API / Worker 构建不依赖未纳入远端仓库的目录 |
| 2026-06-15 | `/analysis/history`、`/analysis/compare`、`/copywriter` 三个页面未登录访问时返回 500 | history 和 compare 页面补充 try/catch + 401 → EmptyAuthState 降级；copywriter 的 500 根因是 router 未挂载导致后端返回 404，在 `main.py` 中 `include_router(copywriter_router)` 修复 |
| 2026-06-15 | 本地 dev server 开 VPN 后所有页面报 "Cannot read properties of undefined (reading 'call')" | webpack chunk 加载被 VPN 干扰，dev 脚本切换为 `next dev --turbopack`；生产构建不受影响 |
| 2026-06-15 | FeedbackWidget hydration mismatch：服务端渲染 "反馈"、客户端渲染 "Feedback" | `layout.tsx` 的 `<html lang>` 从 `"en"` 改为 `"zh"`，与 `getLocale()` 服务端默认值一致 |
| 2026-06-15 | Turbopack 模式启动报 "Cannot find module 'tailwindcss-animate'" | `npm install tailwindcss-animate` 补装缺失依赖 |
| 2026-06-16 | 本地登录报 500，`psycopg2.ProgrammingError: invalid dsn: invalid connection option "DATABASE_URL"` | 根因：(1) `database.py` 的 `load_dotenv` 路径指向了根目录 `.env` 而非 `review_analyzer/.env`，已修正路径；(2) `.env` 文件中 DATABASE_URL 值前多了一个 `DATABASE_URL=` 前缀导致 DSN 格式错误，由 Erika 手动删除多余前缀后修复 |
| 2026-06-24 | 宣传文案页面用批次卡片列表选择数据源，与"按产品出文案"工作流不匹配且占大量首屏空间 | 改造为搜索框 + 版本/时间过滤 + 平台 tabs + 风格 chips（右上角，按平台兼容性灰显）+ 结果分块（单条生成 + 再生成追加）+ 理想画像缓存（按用户/产品/版本持久化到 `ideal_profiles` 表，评论增量失效）。后端 `PLATFORM_DATA` 扩 TikTok、Amazon 禁用词按 2026-06 调研收紧，新增 `STYLE_INCOMPATIBLE` 矩阵与服务端二次校验（字符/禁用词/ALL-CAPS）。新增 `docs/copywriter-platform-rules.md` 与 `migrations/026_add_ideal_profiles.sql` |

---

## 本次排查记录：前端首页 500 与上传链路兼容处理（2026-06-17）

### 问题背景

用户反馈 `http://localhost:3000/` 无法正常打开，浏览器直接显示 `Internal Server Error`。此前上传评论文件时，还出现过 `Request failed with status 500` 和 `Failed to fetch`。本轮目标是先追查问题根因并保留操作记录，不再继续扩大修复范围。

### 已做修改

| 文件 | 改动内容 | 目的 |
|------|---------|------|
| `frontend/package.json` | 将 `dev` 脚本从 `next dev --turbopack` 改为普通 `next dev`，同时继续清空 `http_proxy/https_proxy/HTTP_PROXY/HTTPS_PROXY` | ~~降低 Turbopack 相关运行时不稳定因素，避免本地代理环境干扰 dev server~~ **[2026-06-18 修正]** 此决策有误——真正被代理干扰的是 webpack 而非 Turbopack。已在 6-18 恢复为 `next dev --turbopack`，详见上方修复记录 |
| `frontend/src/components/app/AnalyticsProvider.tsx` | 给 `usePathname()`、`initAnalytics()`、`trackPageView()` 增加容错包裹；任一埋点失败都不再阻断页面渲染 | 避免全局 Analytics 组件在 SSR / hydration 阶段把首页拖成 500 |
| `backend_api/app/routes/uploads.py` | 上传解析失败时将 `ValueError` 映射为 HTTP 400；入队失败时若是 `RuntimeError`，改为用后台线程直接执行 `process_upload_job()` | 防止上传接口在解析或队列不可用时直接 500/503 |
| `backend_api/app/routes/scrape.py` | ASIN 拉取入口同样增加 `RuntimeError` 回退，队列不可用时直接执行 `process_asin_fetch_job()` | 让两个上传/拉取入口在本地无 `rq` 环境下保持一致行为 |
| `review_analyzer/database.py` | 增加 `_clear_cache()` 安全兜底，替代多处直接调用 `.clear()` 的写法 | 修复上传 job 落库后调用 `get_upload_job.clear()` 导致的 `AttributeError`，这是本轮复现到的上传 500 根因 |

### 复现与排查结果

1. 先在浏览器里复现了首页 `Internal Server Error`。
2. 用本地脚本直接调用上传路由，复现到 `500`。
3. 进一步调用同一路由源码，定位到 `review_analyzer/database.py:create_upload_job()` 里对普通函数执行 `get_upload_job.clear()`，触发 `AttributeError: 'function' object has no attribute 'clear'`。
4. 修完后再次复测，发现当前环境缺少 `rq`，上传任务会退回到 `503 Worker queue is unavailable.`，因此又补了线程级同步回退。
5. 随后又把前端首页 SSR 侧的 analytics 全局组件加了保护，但浏览器截图显示首页仍然报 `Internal Server Error`，说明前端还有别的运行时问题未解决。

### 复测结论

- 上传链路的一个明确 500 根因已经确认：`get_upload_job.clear()` 的错误调用。
- `rq` 缺失会导致任务队列不可用，因此又加了同步回退，避免本地开发环境直接 503。
- 首页 `Internal Server Error` 仍未彻底解决，当前只能确认它不再是上面那个上传 500 同一个问题。
- 本次按用户要求先停止继续修复，保留记录，方便后续从这里继续。

### 本次登录 500 的根因与防复发

1. `login` 请求本身并不是最终根因，真正阻断用户进入系统的是 `/workspace` 页面在客户端渲染时崩溃，错误表现为 `Cannot read properties of undefined (reading 'call')`。
2. 后端登录链路本身也存在脆弱点：如果数据库里出现非 bcrypt 格式的旧 `password_hash`，原来的 `bcrypt.checkpw()` 会直接抛异常；我已把它改成统一返回 401，避免坏数据把接口炸成 500。
3. 为了保证“先能登录进系统”，我把工作台页面临时降级成稳定落地页，并收紧了 `Sidebar` 的链接渲染方式，先把登录后的跳转链路稳定住。
4. 防复发建议：
   - 遇到“登录失败”时，先区分是认证接口失败还是登录后页面崩溃，不要把两者混为一谈。
   - 任何会渲染在登录后首屏的客户端组件，都要优先保持最小可用，并对 `undefined` 数据做兜底。
   - 密码校验、数据库连接、路由跳转三处都要有明确错误边界，坏数据应返回 401/503，而不是 500。
   - 新增或恢复工作台复杂内容时，建议分块恢复并为每一块保留回归测试，避免单个子组件再次拖垮整个登录后的落地页。

### 补充复盘：首页恢复打开后的根因确认

1. 重新使用当前工作区执行 `cd frontend && npm run dev` 后，`http://localhost:3000/` 已恢复为 200 并正常渲染首页。
2. 这说明之前的 500 并不是首页静态代码缺失或构建失败，而是浏览器命中的前端服务状态不对，更接近旧进程/旧构建产物在提供响应。
3. 为降低同类问题再次出现的概率，我把首页 metadata 链路做了防御性加固：
   - `frontend/src/app/layout.tsx` 不再直接在顶层执行 `new URL(siteUrl)`
   - `frontend/src/lib/seo.ts` 在 `metadataBase` 和绝对 URL 生成时都增加了兜底回退
4. 从现象和代码改动一起看，最稳妥的结论是：旧前端实例是最初 `Internal Server Error` 的直接暴露面，而 metadata 链路的脆弱性放大了这个问题；重启到最新代码后页面恢复正常。

### 本次补充加固

这次为了降低同类问题再次出现的概率，我没有去改业务页面内容，而是把前端启动和缓存相关的地方做了最小化加固：

1. `frontend/package.json`
   - 将 `dev` 改为 `next dev --hostname 127.0.0.1`
   - 目的：让本地开发服务明确绑定到回环地址，减少外部网络环境或异常绑定带来的干扰
2. `frontend/src/app/layout.tsx`
   - 在 `<head>` 中加入 `Cache-Control: no-store, no-cache, must-revalidate, proxy-revalidate`
   - 同时补充 `Pragma: no-cache` 和 `Expires: 0`
   - 目的：降低浏览器或代理缓存到旧前端状态的概率
3. `scripts/check_frontend_port.sh`
   - 增强了端口占用时的提示，除了 PID 之外，还会显示 `cwd` 和 `exec`
   - 如果发现监听进程就是当前仓库的 `frontend/`，会明确提醒先停掉旧实例再启动新服务

这几项改动已经和前面的排查结论一起写入 `TEST_LOG.md`，方便后面回看时能一眼看出“改了什么”和“为什么这么改”。

### 根因判断

1. 现场现象说明问题不是“页面本身无法编译”，因为 `npm run dev` 重新用当前工作区启动后，`http://localhost:3000/` 立即恢复 200。
2. 端口 `3000` 上当时确实存在一个 `node` 进程在监听，且它的工作目录是当前 `frontend/`，说明问题更接近“前端开发实例状态异常”而不是“访问了别的项目”。
3. 首页 metadata 代码原先依赖顶层 `new URL(siteUrl)` 和 `absoluteUrl()` 的默认行为，虽然默认配置正常时可用，但缺少显式兜底，容易把运行时状态问题放大成整页 500。
4. 因此，这次真正起作用的修复分两层：
   - 启动层：用当前工作区重新拉起前端，确保浏览器访问的是最新实例
   - 代码层：给 metadataBase / absoluteUrl 增加回退，降低同类状态异常再次把首页拖成 500 的概率

---

## 专项记录：SQLite → Supabase 数据库迁移（2026-05-13）

### 问题背景
每次 git push 部署或 Streamlit Cloud 重启时，本地 SQLite 文件被清空，用户数据全部丢失。需要迁移到云端持久化数据库。

### 方案选择
选择 Supabase（PostgreSQL）：免费 500MB、自动备份、支持多用户并发、有管理面板。

### 迁移过程中遇到的报错

#### 报错 1：`ModuleNotFoundError: No module named 'psycopg2'`
- **现象**：推送代码后 Streamlit Cloud 启动报错
- **原因分析**：`psycopg2-binary` 需要系统级 C 库 `libpq-dev` 才能安装
- **尝试方案 1**：pin 版本号 `psycopg2-binary==2.9.9` 触发重建 → 失败
- **尝试方案 2**：改用 SQLAlchemy + pg8000（纯 Python 驱动）→ 失败（SQLAlchemy 也报 ModuleNotFoundError）
- **尝试方案 3**：添加 `packages.txt`（内容 `libpq-dev`）+ psycopg2-binary → 失败
- **根本原因**：Streamlit Cloud 入口文件为 `review_analyzer/app.py`，它优先读取 `review_analyzer/requirements.txt`，而该文件一直没有 `psycopg2-binary`。根目录的 requirements.txt 被忽略了。
- **最终解决**：同步更新 `review_analyzer/requirements.txt` 添加 `psycopg2-binary>=2.9.9`，并在 `review_analyzer/` 下也放置 `packages.txt`

#### 报错 2：`ModuleNotFoundError: No module named 'sqlalchemy'`
- **现象**：尝试用 SQLAlchemy 替代 psycopg2 时仍然报错
- **原因分析**：同上，`review_analyzer/requirements.txt` 没有 sqlalchemy，虽然 Streamlit 自带 SQLAlchemy 作为依赖，但可能因为 pip 安装整体失败导致环境不完整
- **结论**：放弃 SQLAlchemy 方案，回归 psycopg2-binary + 正确的 requirements 路径

### 关键教训
> Streamlit Cloud 的依赖文件查找规则：以 app 入口文件所在目录为基准，优先读取该目录下的 `requirements.txt` 和 `packages.txt`。如果 app 入口不在仓库根目录，根目录的依赖文件会被忽略。

---

## 专项记录：psycopg2.OperationalError 数据库连接失败（2026-05-14）

### 问题现象
打开 https://clueai-reviewlens.streamlit.app/ 登录时报错：
```
psycopg2.OperationalError
File "database.py", line 13, in get_connection
    conn = psycopg2.connect(db_url)
```

### 排查过程

#### 排查 1：Supabase 项目是否暂停？
- 检查结果：项目正常运行，排除此原因

#### 排查 2：Python 版本兼容性
- 发现错误日志中 Python 版本为 **3.14**（`/home/adminuser/venv/lib/python3.14/`）
- Python 3.14 是 pre-release 版本，psycopg2-binary 可能未完全适配
- 修复：创建 `runtime.txt` 固定 `python-3.11.0`
- 结果：部署成功但仍连接失败

#### 排查 3：连接字符串配置错误（根本原因）
- Streamlit Cloud Secrets 中配置的是**直连地址**（端口 5432）：
  ```
  postgresql://postgres:Zhangxi%405764047@db.xxx.supabase.co:5432/postgres
  ```
- Supabase 直连地址对外部 IP 有限制，Streamlit Cloud 的 IP 不在允许范围内
- 需要改用 **Connection Pooling 地址**（端口 6543）：
  ```
  postgresql://postgres.inpgrbjwtpxgwungghnz:Zhangxi%405764047@aws-1-ap-southeast-1.pooler.supabase.com:6543/postgres
  ```

### 最终解决方案

1. **Streamlit Cloud Secrets 改为 Pooler 连接字符串**：
   ```toml
   [database]
   url = "postgresql://postgres.inpgrbjwtpxgwungghnz:Zhangxi%405764047@aws-1-ap-southeast-1.pooler.supabase.com:6543/postgres"
   ```
2. **添加 `runtime.txt`**：固定 Python 3.11，避免 3.14 兼容性问题
3. **`database.py` 改进**：添加 `connect_timeout=10`、`sslmode="require"`、具体错误信息显示

### 关键知识点

| 项目 | 直连（Direct） | 连接池（Pooler） |
|------|---------------|-----------------|
| 端口 | 5432 | 6543 |
| 用户名 | `postgres` | `postgres.[project-ref]` |
| 主机 | `db.[ref].supabase.co` | `aws-[region].pooler.supabase.com` |
| 外部访问 | 受 IP 限制 | 无限制，推荐用于云部署 |
| 密码中有 `@` | 必须编码为 `%40` | 必须编码为 `%40` |

### 关键教训
> 1. Supabase 直连地址（5432）对外部 IP 有网络限制，云平台部署（Streamlit Cloud、Vercel 等）必须使用 Pooler 连接字符串（6543）
> 2. 数据库密码中的特殊字符（`@`、`#`、`%` 等）必须进行 URL 编码
> 3. `runtime.txt` 可以固定 Streamlit Cloud 的 Python 版本，避免自动升级到不稳定版本

---

## 专项记录：邮箱验证码找回密码功能修复（2026-05-25）

### 问题背景
找回密码功能上线后，用户始终无法收到验证码。输入邮箱点击"发送验证码"后页面跳转到验证码输入界面，但验证码从未实际送达，导致重置密码永远失败。

### 排查过程

#### 排查 1：发现 login.py 静默吞错 bug（代码层面）
- **现象**：发送验证码无论成功失败，页面都跳转到验证码输入界面，用户无任何错误提示
- **根本原因**：`login.py` 第 43-47 行完全忽略了 `request_password_reset()` 的 `ok` 返回值，直接无条件设置 `reset_step = "input_code"` 并 `st.rerun()`
- **修复**：改为先判断 `ok`，只有发送成功才跳转；失败时用 `st.error(msg)` 显示具体错误

#### 排查 2：Gmail SMTP 被云平台 IP 封锁（根本原因）
- **现象**：修复静默 bug 后，错误信息暴露为 `source IP address not allowed`
- **原因**：上一版本（commit `8fe55d2`）将发件方式从 Resend 改成了 Gmail SMTP，但 Gmail 对云服务器 IP 段有封锁，Streamlit Cloud 的出站 IP 不被允许
- **排查 Resend 当初为何放弃**：git 历史显示当时用的是 `onboarding@resend.dev`（Resend 测试地址），该地址只能向已在 Resend 后台验证的邮箱发送，所以普通用户收不到
- **结论**：Resend 本身没问题，问题是发件域名未验证

#### 排查 3：Resend 域名验证失败（DNS 配置问题）
- **现象**：Resend 后台域名 `clueai-reviewlens.com` 状态为 Failed
- **错误**：`Invalid DKIM: The record value is incorrect`
- **原因**：阿里云 DNS 中已有 `resend._domainkey` 的 TXT 记录，但填写的值不正确
- **修复**：在阿里云 DNS 控制台更新该 TXT 记录为 Resend 提供的正确值；SPF 和 MX 记录此前已验证通过
- **结果**：DKIM 验证通过，域名状态变为 Active

### 最终解决方案

1. **mailer.py 切回 Resend SDK**，发件人改为 `noreply@clueai-reviewlens.com`
2. **login.py 修复静默 bug**：发送失败时展示 `st.error(msg)`，不跳转
3. **Resend 后台验证域名**：修正阿里云 DNS 中 DKIM TXT 记录值，点击 Restart 重新验证
4. **Streamlit Cloud Secrets** 已有 `[resend]` api_key，无需修改

### 关键知识点

| 发件方案 | 限制 |
|---------|------|
| Gmail SMTP | 云服务器 IP 被封，无法在 Streamlit Cloud 使用 |
| Resend（测试地址 onboarding@resend.dev） | 只能发给已在 Resend 后台验证的邮箱 |
| Resend（验证自有域名） | 无限制，可发任意收件人，推荐方案 |

### 关键教训
> 1. 云平台部署的邮件发送必须使用事务性邮件服务（Resend、SendGrid 等），不能用 Gmail SMTP——云服务器 IP 会被 Google 封锁
> 2. Resend 免费版需验证发件域名（自有域名），才能向任意收件人发送；使用测试地址 `onboarding@resend.dev` 只能发给已验证邮箱
> 3. 邮件发送结果必须检查返回值，发送失败应明确告知用户，不能静默跳转

---

## 数据库基建审查（2026-06-09）

> 在规划 V4-T2 套餐配额（quota.py）实现前，对数据库环境与 schema 进行了一次完整审查，发现 7 项 SaaS 上线前必须修复的问题。整改方案已写入 [PROGRESS_V2.md](PROGRESS_V2.md) Step 2 子任务 2.0-2.7。

### 已踩坑记录

| 编号 | 问题描述 | 风险等级 | 解决方案（Step 2 对应） |
|------|---------|---------|---------|
| DB-1 | 本地开发 / 阿里云生产 / Streamlit Cloud 三处共用同一个 Supabase 项目（`inpgrbjwtpxgwungghnz`），本地代码可直接污染生产数据 | 🔴 高 | 新建 `clueai-dev` 独立开发项目；本地 `.env` 切换到 dev 库（Step 2.1） |
| DB-2 | 数据库密码为弱密码（人名+生日格式 `Zhangxi@5764047`），且明文存于 [.env](.env)、[deploy/.env](deploy/.env)、[.streamlit/secrets.toml](.streamlit/secrets.toml) 三个文件 | 🔴 高 | 立即重置密码为 24 位随机串；检查 git 历史是否泄露过；同步更新三处文件（Step 2.0） |
| DB-3 | 业务表（comments / sessions / products / actions / trackers）共 ~56 条 SQL 查询的 `user_id` 过滤情况未审计，可能存在跨用户数据泄露 | 🔴 高 | 静态扫描 + 修复漏过滤 SQL；Supabase 启用 RLS Policy 双重隔离（Step 2.3） |
| DB-4 | 业务表缺 `updated_at` / `deleted_at` 字段，无法追踪修改时间和支持软删除（GDPR 数据恢复） | 🟡 中 | 业务表统一加时间戳三件套 + 自动更新触发器（Step 2.4） |
| DB-5 | schema SQL 没有版本号编号，`supabase_schema.sql` 单文件累积所有 ALTER 语句，无法回滚 | 🟡 中 | 建立 `migrations/001_xxx.sql` 编号化 schema 管理（Step 2.2） |
| DB-6 | 缺关键字段 CHECK 约束（如 `plan` 枚举值、`rating` 范围、`sentiment` 枚举），数据合法性仅靠应用层校验 | 🟡 中 | 关键字段加 CHECK 约束 + 外键级联策略明确（Step 2.4） |
| DB-7 | 仅依赖 Supabase 默认 7 天快照，无异地周备份（OSS），单点风险高 | 🟡 中 | 写 `scripts/backup_to_oss.sh` 周备份脚本，配置 cron 每周一 09:00 自动跑（Step 2.5） |

### 关键教训

> 1. **环境隔离是 SaaS 红线**：本地 / 测试 / 生产必须使用不同数据库实例。即使没用户也要分——一次本地 `DROP TABLE` 误操作就能搞垮生产。Supabase 免费档每账号可建 2 个项目，零成本即可分离
> 2. **凭证安全要在代码上线第一天就做对**：弱密码 + 明文 `.env` + 不查 git 历史 = 上线即被脱库。任何密钥的存储与轮换流程必须在第一次 commit 之前定好，而不是上线前补救
> 3. **多租户隔离不能只靠应用层**：代码层 `WHERE user_id = %s` 总会有人漏写。必须用 Supabase RLS Policy 在数据库层兜底，做到「即使代码漏了也不会泄露」。RLS 是 SaaS 数据合规的必备，不是 nice-to-have
> 4. **schema 变更必须可回滚**：每个 schema 改动写编号 migration 文件（含 UP/DOWN），单文件累积 ALTER 不是 schema 管理，是 schema 灾难。严禁在 Supabase 后台 SQL Editor 直接改生产 schema
> 5. **CHECK 约束在数据库层而非应用层**：`plan IN ('free','pro_early','pro','team')` 这种规则必须 DB 兜底——多语言 / 多服务接入同一个库时，应用层校验会绕过
> 6. **备份策略不是有就行，要演练能恢复**：每周一次 `pg_dump` 到阿里云 OSS（标准存储 ¥0.12/GB/月几乎免费），关键是定期演练"从备份恢复出可用数据库"——没演练过的备份不算备份
> 7. **Phase 1 初创阶段恰恰是建立基建的最佳窗口期**：用户少、数据量小、改动成本低。等用户多了再补基建是 10 倍工作量 + 业务中断风险

### 整改优先级

> 整改顺序按风险等级和耗时综合排序，详见 [PROGRESS_V2.md](PROGRESS_V2.md) V4-T2 Step 2 完整执行计划：
> - **立即（30 分钟）**：DB-2 凭证安全（Step 2.0）
> - **当天（1 小时 + 1 天）**：DB-1 环境隔离（Step 2.1）+ DB-3 多租户审计（Step 2.3）
> - **本周内（1 天）**：DB-4/5/6 schema 标准化 + DB-7 备份脚本（Step 2.2/2.4/2.5）
> - **回灌生产（30 分钟）**：所有 dev 库验证通过后再操作生产库（Step 2.6）

---

## 部署（2026-06-18）

### 环境信息

| 项目 | 值 |
|------|---|
| ECS 服务器 | 阿里云 `8.210.51.242`（香港） |
| 登录用户 | `ecs-user` |
| SSH 密钥 | `~/.ssh/clueai-reviewlens` |
| 仓库路径 | `/opt/clueai/` |
| 部署编排 | `deploy/docker-compose.yml` |
| 测试域名 | `https://clueai-reviewlens.com` |
| 分支 | `develop`（ECS 跟踪 develop） |

### 容器组成

通过 `deploy/docker-compose.yml` 编排，共 5 个容器：

| 容器 | 镜像/基础 | 作用 |
|------|----------|------|
| nginx | nginx:alpine | 反向代理，80/443 入口 |
| frontend | node:20-alpine（多阶段构建） | Next.js 15 standalone 产物 |
| api | python:3.11-slim | FastAPI 后端 |
| worker | python:3.11-slim | RQ 异步任务消费 |
| redis | redis:7-alpine | 任务队列 broker |

### 部署工作流

```
本地代码修改 → git push origin develop → SSH 到 ECS → cd ~/评论分析_Web_系统 → git pull origin develop → cd deploy → docker compose up -d --build → 浏览器访问 https://clueai-reviewlens.com 验证
```

> 选择 ECS 作为测试环境的原因：本地 Mac（8GB RAM）资源不足以同时跑 Docker Compose 全套容器，ECS 作为真实环境可直接验证部署链路。

### 首次部署遇到的问题

| 问题 | 现象 | 解决方案 |
|------|------|---------|
| BuildKit gRPC 报错 | `docker compose build` 输出乱码 non-printable characters | 使用 `DOCKER_BUILDKIT=0 docker compose build` 禁用 BuildKit |
| npm ci 缺失 @swc/helpers | frontend 构建阶段报 `Could not resolve @swc/helpers` | Dockerfile 多阶段构建中确保 `package-lock.json` 完整，`npm ci` 正常拉取依赖后解决 |
| next build Module not found | `Can't resolve '@/components/auth/auth-layout'` | 该文件本地存在但未被 git 跟踪，`git add` + `git commit` + `git push` 后 ECS 重新拉取即解决（commit `116f6ee`） |
| 仓库路径混淆 | 误以为 ECS 仓库在 `/root/review-analyzer`，多克隆了一份 | 确认实际路径为 `/opt/clueai/`，删除多余克隆 `rm -rf ~/review-analyzer` |

### 最终状态

所有 5 个容器启动成功（`docker compose ps` 均为 running），网站可通过 `https://clueai-reviewlens.com` 正常访问。

### 关键教训

> 1. **本地有但 git 没跟踪的文件**会在 ECS 上缺失导致构建失败——每次新增组件后及时 `git status` 检查是否有遗漏的 untracked 文件。**已发生两次（auth-layout / taxonomy_coverage_monitor）**，建议在 CI 加 `python -c "from backend_api.app.main import app"` smoke test 作为硬防线
> 2. **ECS 上只有一份仓库**（`/opt/clueai/`），不要因为找不到路径就重新 clone，避免多仓库造成混乱
> 3. **BuildKit 兼容性**：阿里云 ECS 的 Docker 版本若遇到 gRPC 乱码，用 `DOCKER_BUILDKIT=0` 回退到传统构建器
> 4. **SSH 连接限制**：ECS 安全组仅允许 IPv4 访问 22 端口，本地若走 IPv6 网络需确认连通性

---

### 2026-06-25 Worker 批量分析崩溃 — 增量写入修复

| 问题 | 现象 | 根因 | 解决方案 |
|------|------|------|---------|
| Session 58（432条评论）好评率/差评率均为 0%，全部显示"未分析" | upload_job status=processing 卡住，processed_rows=67，33秒后进程死亡 | Worker 的 batch-write-at-end 模式：所有评论分析完才一次性写入 DB；进程崩溃后零数据保存。同时 Scheduler 未启用 stale job scan，卡死任务无人检测 | 4 层修复：(1) 增量写入 — 每条分析完立即 `update_comment_analysis()` 写入 DB；(2) 断点续跑 — job 重启后只处理 `is_processed=0` 的剩余评论；(3) Scheduler 启用每 5 分钟 stale scan + 自动重试（≤2次）；(4) Docker worker 加 memory limit 1024M + healthcheck |

---

### 2026-06-25 问评论页面对话式 UI 重构

| 日期 | 变更类型 | 描述 | 验证结果 |
|------|---------|------|---------|
| 2026-06-25 | feat | 问评论页面从表单布局改为 AI 对话框形式；后端新增多轮对话支持（qa_conversations + qa_messages 表 + 对话管理 API + RAG history 参数） | tsc PASS, ruff PASS, next build PASS |

---

### 2026-06-25 推送设置页重构 + 推送内容增强

| 日期 | 变更类型 | 描述 | 验证结果 |
|------|---------|------|---------|
| 2026-06-25 | feat(Part A) | 设置页改为 sidebar 导航 + 3 子页（/settings/push, /settings/api-keys, /settings/billing）；推送页合并全局规则+产品规则+周期推送+升级规则为单页全宽 | tsc PASS, ruff PASS, next build PASS |
| 2026-06-25 | feat(Part B) | 推送内容增强：B1 条数+占比、B2 AI 总结建议（insight_engine）、B3 可点击链接、B4 行动中心引导文案、B5 环比推送增强（对比周期+上下期+TOP3变化）、B6 TOP 问题复盘进度 | ruff PASS |
| 2026-06-25 | fix(UI) | 设置页面卡片移除 max-w-2xl/3xl + mx-auto 约束，平铺撑满内容区，与其他页面风格一致 | tsc PASS |
