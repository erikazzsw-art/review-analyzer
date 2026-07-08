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

---

## 2026-07-08

### V4-M6-6.9.1：侧边栏 Credits 升级按钮 + 套餐升级弹窗

- **工作量**: S（2 文件，0.5 人天）
- **状态**: ✅ 已实现 + 类型检查 + dev preview 验证；待 push + Erika 部署 + prod 验证

**需求描述**：
在侧边栏 Credits 卡片右侧新增常驻 **Upgrade** 按钮，点击后弹出中文套餐升级弹窗（Shulex 风格：顶部 4 卡片 + 下方功能对比表）。Credits 余额区域点击改为打开原有的"套餐使用量"对话框（QuotaDialog）。Credit 单价是内部信息，不展示给用户。弹窗底部保留"查看消费记录"入口，关闭弹窗后打开 CreditLedgerDrawer。

**实现内容**：
- 新建 `frontend/src/components/credit/upgrade-pricing-dialog.tsx`：
  - 月付/年付切换 Toggle（年付 -20%）
  - 4 列卡片：免费版 / 入门版 / 专业版 ⭐"最受欢迎" / 团队版
  - 5 组功能对比表（积分/评论分析/内容生成/导出集成/团队支持），共 16 行；勾/横线/中文数值三类单元格
  - CTA 分支：当前套餐 disabled；team → mailto 联系销售；free 用户 → `/register?plan=X` 立即升级；付费换档 → Paddle checkout
  - Footer："查看消费记录"链接触发 `onOpenLedger`
- 修改 `frontend/src/components/credit/sidebar-credit-entry.tsx`：
  - 并行 fetch `/api/credits/balance` + `/api/quota`
  - Credits 数字点击 → 打开 QuotaDialog（原有"套餐使用量"）
  - 右侧常驻 "Upgrade" 按钮（team 用户隐藏），点击 → UpgradePricingDialog
  - 从 `monthly_grant` 派生 currentPlan：`>=45000→team, >=15000→pro, >=5000→starter, else→free`
  - 集成三个弹层：QuotaDialog / UpgradePricingDialog / CreditLedgerDrawer

**涉及岗位及工时**：
- 前端开发（0.5 人天）：新建升级弹窗 + Sidebar 集成 + dev preview 验证

**验证方式**：
- `npx tsc --noEmit` 通过
- 本地 dev preview 页面截图确认弹窗 4 卡片 + 对比表 + 月/年切换 + Pro 高亮均符合预期
- 待 Erika 部署到 prod 后用测试账号验证：登录 → 侧边栏 Credits 卡片 → 点击 Upgrade → 弹窗正常 → 底部"查看消费记录" → 消费记录抽屉

---

### Bug fix: quota.py PLAN_LIMITS 缺失 starter key（M6 收尾）

- **工作量**: S（1 个 dict 补 11 个 key + 2 个回归测试，0.3 人天）
- **状态**: ✅ 已修复，单测 24 通过；待 push + Erika 部署 + prod 验证

**需求描述**：
M6 引入 Starter 档时，`review_analyzer/quota.py::PLAN_LIMITS` 每个维度的 `limits` 字典遗漏了 `starter` key，只保留 `free/pro_early/pro/team`。`_get_limit()` 找不到套餐时 fallback 到 free 值，导致所有付费 Starter 用户实际拿到的是 Free 硬限（review_analyze 1500 而非 5000、ask_review 10 而非 50、upload_rows_per_file 500 而非 1000 等），付费但未获等价配额，存在退款风险。

**修复内容**：
- 补齐 11 个维度（review_analyze / ask_review / ad_copy / excel_export / compare_products / webhook_count / global_rules / product_rules / upload_rows_per_file / asin_fetch / translate）的 `starter` 限额，值与 [frontend/src/app/pricing/pricing-content.tsx](frontend/src/app/pricing/pricing-content.tsx) `PLAN_FEATURES.starter` 一致
- 新增回归测试 `test_get_limit_starter_not_fallback_to_free` + `test_starter_all_dimensions_have_key`，锁定 starter 不再回退到 free
- QUOTA_TABLE.md（SSoT）当前仍是 Free / pro_early / Pro / Team 四列结构，缺 Starter 列，本次未同步（涉及多张表列结构改造，建议后续单独任务处理）

**涉及岗位及工时**：
- 后端开发（0.3 人天）：定位 bug + 补 dict key + 回归测试

**风险与验证**：
- 直接影响所有已订阅 Starter 的付费用户，部署后 Erika 用 Starter 测试账号验证：
  - upload 1000 行 CSV 不再被拦（旧行为：500 条上限提示）
  - review_analyze 累计 1500 条后仍能继续（旧行为：1500 用完触发升级弹窗）

---



- **工作量**: L（2 migration + 后端核心层 6 函数 + Webhook 改造 + Trial 发放 + 月度 Refill 定时任务 + 6 调用点改造 + 前端定价页重构 + Credit 余额 UI 2 组件 + 2 API 端点，约 4 人天）
- **状态**: ✅ 6.1-6.9 已部署上线、prod 验证通过；6.10 文档待同步

**需求描述**：
现有配额体系是 8 维独立限制（评论条数 / Ask 次数 / 文案 / Excel / 对比 / Webhook / 规则数），用户理解成本高、加功能就要新开限额。海外市场竞品（VOC AI）采用统一 credit 池，ClueAI 需对齐并差异化。定价 4 档：Free($0/300) / Starter($12/5K) / Pro($29/15K) / Team($59/45K)，首注册送 3000 credits × 14 天 Trial。

**涉及岗位及工时**：
- 后端开发：2.5 人天（credit 核心层 6 函数 + Webhook 改造 + Trial 发放 + 月度 Refill + 6 调用点改造 + 2 API 端点）
- 前端开发：1 人天（定价页重构 pricing-content.tsx + Credit 余额 UI sidebar-credit-entry.tsx + credit-ledger-drawer.tsx + pricing.ts 扩展）
- DBA：0.3 人天（migration 044 + 045 + backfill）
- 文档：0.2 人天（PROGRESS_V2 + TEST_LOG + CHANGELOG）

**变更清单**：
- `migrations/044_create_user_credits.sql`：创建 `user_credits`（credit 钱包）+ `credit_ledger`（流水账）+ 索引 + updated_at 触发器 + 全量 backfill
- `migrations/045_add_starter_plan.sql`：`users.plan` CHECK 约束加入 `'starter'`
- `review_analyzer/quota.py`：新增 `credit_check` / `credit_consume`（SELECT FOR UPDATE 防并发）/ `credit_refund` / `get_credit_balance` / `get_credit_ledger` + `InsufficientCreditsError` 异常类
- `backend_api/app/routes/quota.py`：新增 `GET /credits/balance` + `GET /credits/ledger` API 端点
- `backend_api/app/routes/settings.py`：Paddle Webhook 改造 — `_resolve_plan_from_event()` 新增 starter 档 + `_get_price_custom_data()` + subscription.*/transaction.completed → 更新 monthly_grant
- `backend_api/app/routes/auth.py`：注册时插入 user_credits（Trial: balance=3000, trial_expires_at=now()+14d）
- `review_analyzer/database.py`：新增 `update_user_credits_monthly_grant(user_id, plan)`
- `workers/periodic_jobs.py`：新增 `refill_monthly_credits()`（每月 1 号）+ `expire_trials()`（每日）
- `workers/jobs.py` + `backend_api/app/routes/{qa,copywriter,translate,export}.py`：6 处调用点 `quota_consume` → `credit_consume` + `InsufficientCreditsError` → 402
- `frontend/src/lib/pricing.ts`：PlanKey 扩展 + PLANS 补 Starter 档 + ADD_ONS 常量
- `frontend/src/app/pricing/pricing-content.tsx`（新建）：月付/年付 Toggle + 4 档对比卡 + 加油包区块 + Trial 文案
- `frontend/src/components/credit/sidebar-credit-entry.tsx`（新建）：Sidebar 常驻余额入口
- `frontend/src/components/credit/credit-ledger-drawer.tsx`（新建）：近 30 条消费明细抽屉
- `frontend/src/components/app/sidebar.tsx`：集成 SidebarCreditEntry

**部署修复记录**（3 个 hotfix）：
1. `locale.py` 未 git add → api 容器 ModuleNotFoundError（commit `443f982`）
2. `get_quota_status` 函数定义被误删 → api 容器 ImportError（commit `9a38777`）
3. `pricing-content.tsx` 未 git add → frontend build Module not found（commit `3e9c41a`）
4. Migration 044 原始 SQL 的 user_id 类型 UUID 与 users.id INT 不匹配 + backfill 引用不存在的 is_active 列 — 修正后 Erika 在 Supabase 重新执行成功

**线上验证结果**（2026-07-08 测试账号 惜_clueai）：
- SidebarCreditEntry 显示 `Credits 300 / 300` ✅
- CreditLedgerDrawer 点击弹出，显示 `Monthly grant +300` ✅
- API `/credits/balance` 返回 `{"balance":300,"monthly_grant":300}` ✅
- 套餐额度组件 + workspace 页面正常 ✅

**待确认**：升级时是否应立即将 balance 重置为 new_monthly_grant（"即时发放当月余额"）？当前实现只更新 monthly_grant，不动 balance。

---

## 2026-07-07

### V4-出海-M4-pre：LLM 路由 locale 切换（海外优先 GPT-4o-mini 主链路）

- **工作量**: M（1 新建 util + 8 处 wire-up + 1 前端 config + 2 处 messages 补词表，约 0.8 人天）
- **状态**: 本地完成，pytest 60 通过（1 pre-existing 无关失败已排除），import smoke test 通过；不改动 requirements��无 migration；待 Erika 部署后线上以 en cookie 验证 `model_used=gpt-4o-mini`

**需求描述**：
承接海外市场调研结论（`docs/overseas-market-research-2026-07.md`）——海外用户对国际大厂 LLM（GPT-4o-mini）品牌信任更高，且英文 aspect 抽取质量与 DeepSeek 相当或更好，国内用户仍走 DeepSeek 保成本。核心决策（Erika 拍板）：**统一英文 prompt**，不搞中英双 prompt；locale 只影响模型链优先级，不影响 prompt 内容；国内用户看到的分析结果由前端展示层翻译；`review_analyzer/insight_engine.py` 顺手把硬编码 OpenAI 直调 DeepSeek 的老代码收编进 router。

**涉及岗位及工时**：
- 后端开发：0.5 人天（llm_router locale 切换 + locale util + uploads/analysis 路由注入 Request + workers 透传 + deep_analyzer 参数 + insight_engine 收编到 router，约 6 个文件）
- 前端开发：0.2 人天（`routing.ts` defaultLocale + `en.json` / `zh.json` categoryLabels 段）
- 文档：0.1 人天（PROGRESS_V2 + TEST_LOG + CHANGELOG）

**变更清单**：
- `backend_api/app/services/llm_router.py`：`_DEEPSEEK` / `_OPENAI` / `_QWEN` 拆常量 + `MODELS_EN` / `MODELS_ZH` + `_models_for_locale()`；`LLMRouter.completion()` 与 `router_completion()` 新增 `locale` 参数（默认 `"zh"` 向后兼容）；`__post_init__` 种子所有可能模型的熔断态；`status()` 汇总两条链
- `backend_api/app/services/locale.py`（新建）：`get_analysis_locale(request)` = `?locale=` > cookie `NEXT_LOCALE` > `Accept-Language` > 默认 `"en"`；`_normalize()` 处理 `zh-CN`/`en-US`/`en-US,zh;q=0.9`/未知语言（→ 默认）
- `backend_api/app/routes/uploads.py`：`/uploads` + `/analysis/jobs` 端点注入 `Request`，写 `payload_json["locale"]`
- `workers/jobs.py`：`process_upload_job` 从 `payload_json` 读 locale（默认 `"en"`），透传给 3 处 `deep_analyze_batch()`
- `backend_api/app/services/deep_analyzer.py`：`analyze_one` / `analyze_batch` 加 `locale` 参数（默认 `"en"`）→ `router_completion(locale=...)`
- `review_analyzer/insight_engine.py`：删除硬编码 `OpenAI(base_url="deepseek.com")` 直调 + `get_api_key(user_id)` 依赖，改走 `router_completion(locale=...)`；两个公共 API + 两个内部 helper 都加 locale 参数
- `backend_api/app/routes/analysis.py`：`/sessions/{id}/results` + `/results` 端点注入 `Request`，传 locale 到 `build_results_insights` / `_cached_build_insights`
- `frontend/src/i18n/routing.ts`：`defaultLocale: "zh"` → `"en"`
- `frontend/messages/en.json` / `zh.json`：新增 `categoryLabels` 段，11 个中文分类的翻译（产品质量→Product Quality / 包装物流→Packaging & Logistics / 使用体验→Usage Experience / 客服售后→Customer Service / 性价比→Value for Money / 功能需求→Feature Request / 正面反馈→Positive Feedback / 单纯好评→Praise Only / 无效乱码→Invalid Content / 混合评价→Mixed Review / 其他→Other；zh 侧同 key 保留中文本名，便于前端 `useTranslations` 统一按 key 取值）

**关键决策记录**：
1. **统一英文 prompt**：评论源就是英文，英文 prompt 分析效果最好，跟用什么模型无关。中英双 prompt 需要维护两套版本、双套 golden set，产研收益负数（Erika 决策）
2. **locale 向后兼容**：`router_completion` 默认 `locale="zh"`（保原生产链路），`deep_analyzer` / `insight_engine` 默认 `locale="en"`（新入口默认海外优先），旧调用点不改也能跑
3. **不阻塞 M4 Bedrock/OpenRouter 决策**：本 pre-milestone 不接触 Bedrock/OpenRouter，仅在现有 DeepSeek/OpenAI/Qwen 三家里切主链路优先级；M4 决策拍板后再叠加 `provider="bedrock"` 或 `"openrouter"` 分支
4. **insight_engine 顺手收编**：老代码硬编码 OpenAI 直调 DeepSeek 已存在很久，绕过 router 熔断 + BYOK，本次一并收编到 `router_completion`，未来 `.env` 换 key 全站生效
5. **前端 defaultLocale 改 en**：因为 `localePrefix: "never"` 靠 cookie 驱动，defaultLocale 决定"没 cookie 的新访客"进什么语言。海外优先则默认 en，国内用户由 middleware 检测 `Accept-Language: zh-*` 或手动切换
6. **catgoryLabels 只做前端翻译**：不改 backend `_derive_category` 返回的中文枚举，避免破坏 DB 已存的 category 字段和现有 dashboard 逻辑

**关联文档**：
- PROGRESS_V2.md 新增 V4-出海-M4-pre 章节（`✅ 完成`）
- TEST_LOG.md 追加 2026-07-07 记录（M4-pre）
- session-summary.md：本次任务的源计划（session 加载后落地）
- 后续 M4 决策仍冻结，等待 Erika 拍板 A（SG + OpenAI 直连）vs C（OpenRouter 中转）

---

## 2026-07-07

### V4-T4 Step 7：跨用户 LLM 分析结果复用（成本节约方案）

- **工作量**: M（1 migration + 1 核心函数扩展 + 3 处 wire-up + 1 单测文件 + 2 处隐私/服务条款，约 0.5 人天）
- **状态**: ✅ 已部署，migration 043 已在 ECS 执行（2026-07-07）；线上上传验证待 Erika 用两账号上传同一 CSV 观察 `cache_hit_source='global'` 日志

**需求描述**：
Erika 提出——原 L1 缓存 `get_analyzed_by_content_hash` 只查用户自己历史 comments，用户 A、B、C 上传相同 ASIN 或相同评论文本时仍会重复调用 DeepSeek，浪费 API 成本。热门 ASIN 场景（多卖家竞品共同关注）100% 评论重叠仍全额扣费。基建其实早已就绪：`review_pool` 全局表（migration 038）无 user_id + 已有 `aspects_json` + `analyzer_version` 字段，`pool_backfill_analysis()` 函数已实现，但接线被两处门禁堵住：① L1 lookup 只查 comments 不查 pool；② pool 回填被 `source_channel == "api"` 挡住，CSV 上传结果不入池。**核心决策（Erika 拍板）**：作用域全局共享，缓存命中仍扣用户额度（quota 上传时消费不受影响），存储扩展现有 `review_pool` 表（不新建）。

**涉及岗位及工时**：
- 后端开发：0.3 人天（`get_analyzed_by_content_hash` 扩展 + `workers/jobs.py` 三处 wire-up + `update_comment_analysis` 支持 cache_hit_source 列 0.2 / 单元测试 0.1）
- 前端开发：0.05 人天（隐私政策 + 服务条款文案追加，中英双语）
- 合规审阅：0.05 人天（跨用户数据复用合规披露的措辞把关）
- 文档：0.1 人天（PROGRESS_V2 + TEST_LOG + CHANGELOG + plan 文件更新）

**变更清单**：
- `migrations/043_review_pool_global_analysis_cache.sql`（新建）：`review_pool.content_hash` 部分索引（analyzed_at IS NOT NULL 才索引，大幅缩小体积）+ `comments.cache_hit_source VARCHAR(20)`（'user' | 'global' | NULL 区分命中来源）
- `review_analyzer/database.py::get_analyzed_by_content_hash`：新增 `include_global=True` + `analyzer_version` 参数——先查用户自己历史，未命中的 hash 再查全局 pool（analyzer_version 匹配才复用，防止老版本结果污染当前分析）；返回值新增 `cache_hit_source` 字段
- `review_analyzer/database.py::update_comment_analysis`：写入 `cache_hit_source` 列，异常回退到原 base_sql
- `workers/jobs.py` 三处改：
  1. L1 lookup 传 `include_global=True, analyzer_version=ANALYZER_VERSION`
  2. `cache_hit_source` 从 `hit.result` 透传写入 `id_to_v4[cid]`
  3. 拆掉 `source_channel == "api"` 门禁，改判 `product_id` 非空即回填（CSV 上传也参与池贡献）；同时新增 `pool_write()` 调用，确保 CSV 数据先入池再回填分析结果
- `frontend/src/app/privacy/page.tsx`：新增第四条"分析结果聚合复用"章节（中英双语），原第 4-10 章顺移为 5-11 章，"最后更新"日期改为 2026-07-07
- `frontend/src/app/terms/page.tsx`：第四条"数据所有权"追加聚合复用说明（中英双语），指向隐私协议第四条；日期同步更新
- `backend_api/tests/test_global_cache.py`（新建）：6 个用例覆盖用户命中/全局命中/user 屏蔽 pool/空输入/`include_global=False` 关闭全局路径/content_hash 稳定性

**关键决策记录**：
1. **计费不变**：quota 在上传时按条数扣，缓存命中不返还额度。用户付的是"分析输出"，不是"每次 DeepSeek 调用"（Erika 决策）
2. **作用域全局**：不限制同 ASIN 或同 category（虽然 prompt 里 category 会影响 aspects taxonomy，但同 content_hash 通常语义一致；如未来发现问题可通过 `analyzer_version` 显式 bump 来强制刷新）
3. **CSV 也回填**：拆掉 `source_channel == "api"` 门禁的前提是 `product_id` 非空，避免自由 CSV 污染池
4. **隐私披露前置**：privacy.tsx 第四条明示"匿名化分析输出可跨用户复用，不涉及身份/账号/上传时间共享"，避免 GDPR/个保法风险
5. **cache_source_id 保持 INT**：既存列是 INTEGER，改类型会破坏迁移；用新增 `cache_hit_source` VARCHAR 区分归属表（'user' → comments.id / 'global' → review_pool.id）
6. **feature flag 预留**：`include_global` 默认 True 但可通过参数关闭，未来若需灰度可包一层 env var

**关联文档**：
- PROGRESS_V2.md 变更日志追加一行 2026-07-07（V4-T4 Step 7）+ V4-T4 章节末尾追加 Step 7 详情
- TEST_LOG.md 追加 2026-07-07 记录
- plan 文件 `~/.claude/plans/llm-a-b-c-velvety-journal.md` 保留供后续追溯

---

## 2026-07-07

### V4-出海-M3.5：数据保留策略自动清理（对齐 Shulex 6y+60d，M3 合规模块收官）

- **工作量**: M（1 migration + 1 核心 worker + 4 处 wire-up + 1 单测文件 + 4 处邮件模板/mailer + auth.py 补钩子，约 1 人天）
- **状态**: ✅ 已部署，线上验证通过（2026-07-07）；migration 042 已在 ECS 执行（`Migration 042 OK`）

**需求描述**：
V4-出海模块 M3 合规能力收官任务。此前 M3.2 只做了"用户主动删账号 → anonymize_user"，没有：① 长期 inactive 用户自动清理（CCPA/CPRA 要求"不能无限期保留",Shulex 已做）；② 删除账号 60 天宽限后硬删关联业务数据（Shulex 也是 60d 窗口）；③ 老数据按类型分级软删/硬删的自动化。Erika 追问"保留期 2 年 vs 6 年在成本/实现上有何区别"时牵出跨用户数据复用问题（review_pool 已实现抓取层去重、评论 + LLM 分析结果按 user_id 隔离没复用），并确认按 Shulex 6 年通用保留期落地，跨用户复用作为独立话题移交新对话。

**涉及岗位及工时**：
- 后端开发：0.7 人天（`workers/retention_cleanup.py` 6 块清理主逻辑 0.4 / mailer + template + auth.py 补钩子 0.15 / scheduler + periodic_jobs 集成 0.05 / 单元测试 0.1）
- 合规审阅：0.1 人天（对齐 Shulex 保留期决策 + 冷存储缓冲方案讨论）
- 文档：0.2 人天（PROGRESS_V2 + TEST_LOG + CHANGELOG + plan 更新，含"冷热分层缓冲方案"备用记录）

**变更清单**：
- `migrations/042_add_inactivity_tracking.sql`：`users` 表加 `last_login_at` + `inactivity_notified_at` 两列 + 两个部分索引（`WHERE deleted_at IS NULL`），老用户 fallback `last_login_at = created_at` 避免全部误判 inactive
- 邮件模板：`email_templates/{zh-CN,en-US}/inactivity_warning.html`（新建）+ `deletion_confirmed.html` 里"30 天备份保留期" → "60 天备份保留期"（对齐 Shulex）
- `review_analyzer/mailer.py`：`_SUBJECTS["inactivity_warning"]` + `send_inactivity_warning(to_email, username, deletion_date, locale)`，归类 Transactional（合规通知，不受 marketing opt-out 控制）
- `review_analyzer/database.py`：加 `mark_user_login(user_id)` helper（登录时刷 `last_login_at` + 清零 `inactivity_notified_at`）
- `backend_api/app/routes/auth.py`：`login()` 成功分支调 `mark_user_login()`，DB 写失败降级为 warning 日志不阻塞登录
- `workers/retention_cleanup.py`（核心新文件）：6 块清理串行执行，每块独立 try/except + 单独 commit + 单次处理上限（Block1/2 500 条、Block3 200 用户），返回 `{ok, blocks, errors, started_at, finished_at}` 结构化统计
  - Block 1: inactive 6m + 未通知 → 发预告 + send-first-mark-after 打时间戳
  - Block 2: 已通知 90d + 仍未登录 → 复用 M3.2 `anonymize_user()`
  - Block 3: `deleted_at > 60d` → 按 FK 叶子→根顺序硬删 6 张表（review_trackers → action_items → comments → product_variants → products → sessions），**不动 review_pool**（无 PII、纯抓取缓存），users 表本身保留（M3.2 已匿名化，保留主键防悬垂）
  - Block 4: `analytics_events > 90d` → 硬删
  - Block 5: `llm_usage_log > 6y` → 硬删（对齐 Shulex）
  - Block 6: `sessions/comments > 6y AND deleted_at IS NULL` → 软删（`UPDATE ... SET deleted_at = NOW()`，等未来冷存储方案再做物理清理）
- `workers/periodic_jobs.py`：加 `enqueue_retention_cleanup()`（`job_timeout=30min`、`result_ttl=7d` 供审计、`failure_ttl=30d` 供定位）
- `workers/scheduler.py`：加 `RETENTION_CLEANUP_HOUR=3` + `RETENTION_CLEANUP_MINUTE=23`（业务低峰、避开 09:07 成本日报）+ Redis 锁 `scheduler:retention_cleanup:lock:{YYYY-MM-DD}` 保证同一日历日只入队 1 次
- `workers/tests/test_retention_cleanup.py`：每块至少 1 个用例（no-candidates / 正常路径 / 边界失败），加 SQL 关键词哨兵测试（"90 days" / "6 years" / "UPDATE ... deleted_at = NOW()"）防未来误改窗口口径，顶层 job 测试确认 6 块串行 + 一块炸不影响其他

**关键决策记录**：
- **通用保留期 6 年**（对齐 Shulex，兼顾未来跨用户 embedding 复用命中率）
- **删除后宽限窗口 60 天**（对齐 Shulex，给"删了后悔"更长机会）
- **inactivity 阈值 6 月**（所有用户一视同仁，Shulex 无此机制，我们保留为差异化亮点）
- **运行时间 UTC+8 03:23**（业务低峰，避开 09:07 daily_cost_digest）
- **review_pool 不清理**（无 PII、纯抓取缓存，删了直接翻倍抓取成本）
- **users 表本身不删**（M3.2 已匿名化，保留主键防止业务侧 LEFT JOIN 出现悬垂 user_id 展示成 "unknown"）
- **冷热分层缓冲方案（未来备用，本次不实施）**：如果 6 年保留导致 Postgres 主库压力（单表 >5000 万行 / p95 劣化 >200ms / 存储超预算 30% 任一命中），启动老数据（>2y）dump 到 S3/OSS 冷存储、主库只留热数据（<2y）的方案。先按 6y 硬保留跑一段观察增长曲线，触发条件命中再启动

**上线部署**（待 Erika 手动执行）：
```bash
cd /opt/clueai/deploy && git pull origin develop && docker compose exec -T api python -c "import psycopg2, os; conn = psycopg2.connect(os.environ['DATABASE_URL']); cur = conn.cursor(); cur.execute(open('/opt/clueai/migrations/042_add_inactivity_tracking.sql').read()); conn.commit(); print('migration 042 ok')" && docker compose up -d --build api worker scheduler && docker compose exec nginx nginx -s reload
```

**验证方式**（Erika 部署后）：
- migration 042 执行后 `SELECT column_name FROM information_schema.columns WHERE table_name='users' AND column_name IN ('last_login_at','inactivity_notified_at')` 返回 2 行
- 测试账号登录后 `SELECT last_login_at FROM users WHERE username='惜_clueai'` 应为最近时间
- 第 2 天 03:23 后 `docker compose logs scheduler | grep "retention cleanup"` 应看到 `enqueued retention cleanup`
- 若线上有老 inactive 账号，`SELECT COUNT(*) FROM users WHERE inactivity_notified_at IS NOT NULL` 应 > 0
- 测试账号收到 inactivity_warning 邮件（如触发）时检查双语模板渲染

---



### Bug 修复：P2 级 pre-existing 分析链路 6 连修（rag 日志 + push_snapshots 表 + embedding batch + scripts 缺失 + embedding provider 回退 + except pass 显形）

- **工作量**: M+（6 个独立 pre-existing bug 连锁排查 + 修复 + 迁移 + 线上验证，约 1.2 人天）
- **状态**: ✅ 已线上验证通过 — 新分析 embedded/total = **30/30**，网页问评论走 **混合检索（vector + fulltext RRF）**，`retrieval_method=hybrid` 稳定返回

**需求描述**：
2026-07-05 服务器迁移 SG 后，Erika 拉 worker 日志暴露出 4 个长期被静默 exception handler 吞掉的 pre-existing bug，与迁移无关，全部为分析链路 P2 级。分三个会话逐层剥离：① P2-A/B 修 rag 异常日志详细化 + push_snapshots 表建立；② P2-C/D 借 P2-A 的日志锁定 DashScope embedding batch 超限和 workers scripts 模块缺失；③ 本轮验证阶段发现 pgvector 仍 0/7740 覆盖，进一步顺出 P2-E（embedding provider 维度不匹配 pgvector 列 + 合规风险）和 P2-F（`workers/jobs.py` 里另有两处 `except: pass` 继续吞掉 pgvector `DataException`），全部修完后线上验证通过。

**涉及岗位及工时**：
- 后端开发：1.2 人天（P2-A rag 日志 0.2 / P2-B migration 0.2 / P2-C batch 常量定位 0.2 / P2-D 5 处 import 迁移 + Dockerfile 归因 0.4 / P2-E 合规审阅 + provider 回退 0.1 / P2-F except pass 显形 + 线上验证 0.1）

**变更清单**：
- **P2-A**：`review_analyzer/rag.py` `generate_embeddings_batch` 捕获异常时打印完整异常 + `base_url` / `model` / `key_source`（原来只打 "skipping chunk"）；模块加载时校验 `EMBEDDING_API_KEY` / `OPENAI_API_KEY` 至少一个非空，均缺则打 WARNING
- **P2-B**：新建 `migrations/041_push_snapshots.sql`，`push_snapshots` + `issue_escalation_state` 两表；用 `UNIQUE NULLS NOT DISTINCT` 保证 `product_id=NULL` 时 upsert 语义正确
- **P2-C**：`review_analyzer/rag.py:90` `EMBEDDING_BATCH_SIZE 256 → 10`（DashScope `text-embedding-v3` 官方硬上限 10，OpenAI 是 2048 之前能跑，切 DashScope 后一直 400 静默失败），常量注释注明来源
- **P2-D**：迁移 `scripts/aspect_taxonomy.py → review_analyzer/aspect_taxonomy.py`（属于共享分析业务字典，归属更合理），同步修 5 处 import：`workers/jobs.py:779`、`workers/jobs.py:823`、`workers/periodic_jobs.py:164`、`workers/periodic_jobs.py:174`、`backend_api/app/services/action_advisor.py:75`；`scripts/` 恢复"一次性运维脚本"定位，不进 prod 镜像
- **P2-E**：embedding provider 从 DashScope（`text-embedding-v3`，1024 维，中国境内）回退到 OpenAI（`text-embedding-3-small`，1536 维，与 `comments.embedding vector(1536)` 列匹配）。合规动机：目标市场为排除 EU/UK/EEA 的全球英语市场，DashScope 在中国境内不满足 GDPR/CCPA 子处理商披露要求；技术动机：pgvector 列维度在建表时固化，写入 1024 维会抛 `DataException`，与列一致的选择只有 1536 维。改动仅 `.env` 三个变量 `EMBEDDING_API_BASE_URL/EMBEDDING_MODEL/EMBEDDING_API_KEY`，零 migration
- **P2-F**：`workers/jobs.py:206`（分析主链路调 `embed_session_comments`）和 `workers/jobs.py:384`（聚类结果写 `update_comment_cluster`）另有两处 `except Exception: pass`，即使 P2-A 让 `rag.generate_embeddings_batch` 内部日志详细了，一旦异常上冒到这两处仍会被静默吞掉。改为 `logger.exception(...)` 输出完整堆栈 + user_id / session_id / comment_id 上下文；`review_analyzer/rag.py:90` 注释同步更新为 OpenAI 上限来源

**根因深度**：
- 6 个 bug 长期存在但都被多层 `except Exception: pass/log("skipping")` 遮蔽，属于**"先修日志再修 bug"的正向连锁**：P2-A → 让 batch 内部错误显形 → 定位 P2-C；P2-F → 让 batch 上游错误显形 → 定位 P2-E
- P2-E 是最深层根因：即使 P2-C 让 batch size 从 256 降到 10，pgvector 列维度与 provider 输出维度不匹配的问题依然存在。ECS 上一次修 P2-C 时切换了 provider 到 DashScope，无意中把长期潜藏的维度依赖从 1536 → 1024，直接被 pgvector 拒绝入库
- 生产 pgvector `comments.embedding` 从 2026-06-03 迁移建表至今一直为空（7740 条评论 0 覆盖），本次修复只让新分析写入，历史 embedding 是否补数仍待与 Erika 讨论
- **合规副产物**：借这次事件把 DashScope 从主 embedding 链路移除，规避海外用户数据经中国 IDC 的 GDPR/CCPA 灰色地带；`llm_router.py:57` Qwen chat fallback 属于死代码，触发率极低，另行清理

**上线部署**：
- P2-A / P2-B 已随 commit `e7613cb` 上线
- P2-C / P2-D 已随第二轮 commit 上线，Erika 完成 `docker compose up -d --build worker api && docker compose exec nginx nginx -s reload`
- P2-E / P2-F 本次 commit `b06e4da` push develop，Erika 完成 `.env` 三变量替换 + `docker compose up -d --build worker api && docker compose exec nginx nginx -s reload`
- **线上验证结果**：① worker 日志无 `batch size is invalid` / `ModuleNotFoundError` / `UndefinedTable` / `DataException`；② 新分析 embedded/total = 30/30；③ 网页问评论 "What do customers say about waterproof?" 返回 5 条引用，检索标签为 **混合检索**（`retrieval_method=hybrid`），vector 检索确认激活

---

## 2026-07-05

### DevOps：服务器迁移 HK ECS → AWS Lightsail SG

- **工作量**: L（基础设施迁移 + 多轮诊断修复 + 全链路验证，约 2 人天）
- **状态**: Phase 0-3b 完成，线上流量已切 SG，进入 Phase 4 观察窗口（到 2026-07-12）

**需求描述**：
Anthropic Bedrock + OpenAI Chat Completions 从香港 ECS（`8.210.51.242`）出口被 API 层地理封锁（`403 unsupported_country_region_territory`），V4-出海 LLM 主链路必须以 ECS 迁 SG/US 为硬前提。选 AWS Lightsail SG（新加坡）$40/mo 静态 IP `13.215.29.99`，SG 无地理封锁，出海合规更完整。

**涉及岗位及工时**：
- DevOps：2 人天（服务器初始化 / Docker + Compose / SSL 证书 / `.env` 部署 / 容器起活 / `DATABASE_URL` bug 修复 / Cloudflare DNS 切换 / 全链路验证）

**变更清单**：
- AWS Lightsail SG 实例（Ubuntu 24.04，$40/mo，静态 IP `13.215.29.99`），开 22/80/443 端口
- Cloudflare Origin Cert（有效期至 2041-06-29）挂入 nginx volume
- 全部 6 个容器（redis / api / worker / scheduler / frontend / nginx）起活并 healthy
- `deploy/.env` `DATABASE_URL` 修复：末尾 `/pos>` → `/postgres`（shell 重定向符误入 bug）
- Cloudflare DNS 4 条 A 记录（root / www / app / api）从 HK 切到 `13.215.29.99`（Proxied 模式）
- Mac `/etc/hosts` 临时行清理 + DNS 缓存刷新

**验证结果**：
- B 场景（上传 CSV → worker 分析 → 结果页 7 tab）两次端到端通过（hosts 指 SG + 真实公网 Cloudflare 路径）
- worker `scan_stale_jobs` 修复后连续 3.5+ 小时稳定运行，无 `DatabaseConnectionUnavailable`
- 4 域名公网 HTTPS 全部 200

**待完成（Phase 4）**：
- 观察 SG 稳定性至 2026-07-12，届时撤 HK ECS
- `deploy/docker-compose.yml` volumes 加 `external: true`（`certbot_www` / `letsencrypt`）
- 修复 2 个 pre-existing bug（embedding batch 偶发失败 + `push_snapshots` 表缺失）

---

## 2026-07-03

### V4-出海-M3.1：EU/UK/EEA + OFAC 制裁国 Geo-Block 中间件

- **工作量**: S（1 文件新增 + 1 文件挂载 + 1 单测，约 0.5 人天）
- **状态**: 本地完成，未部署（M1 Erika 手动 Cloudflare 未上线，本次上线不影响功能，等 Cloudflare 前置后自动生效）

**需求描述**：
V4-出海模块 M3.1 后端合规能力第一环。在用户注册入口拦截来自 EU / UK / EEA / 瑞士 / OFAC 全面制裁 6 国的请求,防止在合规配套（Cookie Banner、Terms Gate、GDPR 通知）就绪前就把这些高监管地区用户圈进系统。只拦注册,不拦登录,存量用户完全不受影响。

**涉及岗位及工时**：
- 后端开发：0.5 人天（`backend_api/app/middleware/geo_block.py` 新建、`backend_api/app/main.py` 挂载、`backend_api/tests/test_geo_block.py` 8 个单测）

**变更清单**：
- `BLOCKED_COUNTRIES = 38 国` — EU 27（AT/BE/BG/HR/CY/CZ/DK/EE/FI/FR/DE/GR/HU/IE/IT/LV/LT/LU/MT/NL/PL/PT/RO/SK/SI/ES/SE）+ EEA 3（IS/LI/NO）+ UK/CH + OFAC 6（IR/KP/SY/CU/RU/BY）
- 拦截范围严格限定 `(POST, /auth/register)`；登录、其他 API、GET 请求全部放行
- `CF-IPCountry` header 缺失时放行 + DEBUG 日志（Cloudflare 未上线阶段的兜底策略,避免上线前把所有注册都误拦）
- 命中受限国家返回 403 JSON：`{"detail": "Registration is not available in your region...", "country": "DE", "reason": "geo_blocked"}`
- middleware 挂载顺序：CORS → GeoBlock → Analytics（在 CORS 之后追加,与其他中间件解耦）
- 大小写兼容：`de` 也能被识别为 `DE`

**验收 & lint**：
- `pytest backend_api/tests/test_geo_block.py`：8 passed
- `ruff check`：PASS
- 单测覆盖：DE → 403、IR（OFAC）→ 403、缺 header → 200、US → 200、小写 → 403、`/auth/login` DE → 200（不拦）、`/health` IR → 200（不拦）、清单完整性校验（38 国 + 未拦国抽样）

**PROGRESS_V2.md M3.1 全部勾选**，M3 进度 20% → 40%。

**上线依赖**：
- Cloudflare 未接入前,`CF-IPCountry` 全部为空,middleware 相当于空操作,安全上线不影响任何用户
- Erika 完成 M1 Cloudflare 配置后（域名接入 + Proxy 开启）,`CF-IPCountry` 自动出现在请求 header,geo-block 立即生效

---

### V4-出海-M3.2：数据主权 API（GDPR / CCPA / PIPEDA）

- **工作量**: M（后端 3 端点 + 前端 1 页面 + sidebar 入口，约 2 人天）
- **状态**: 本地完成，未部署（M1 Erika 手动任务完成后再统一部署）

**需求描述**：
V4-出海模块推进「M1 Erika 手动执行」期间，同步落地不阻塞的代码任务。M3.2 是海外合规最基础的三个用户端点，无外部依赖、无 migration，纯附加式代码，适合先行。

**涉及岗位及工时**：
- 后端开发：1.5 人天（`backend_api/app/routes/me.py` 新增 3 端点、`backend_api/app/schemas/me.py` 新建、`review_analyzer/database.py` 新增 5 个辅助函数、`deps.py` / `auth.py` 加软删拦截）
- 前端开发：0.5 人天（`frontend/src/app/settings/account/page.tsx` 新建、`lib/api/browser.ts` + `lib/api/types.ts` 新增 3 个封装、sidebar 新增入口、中英文 i18n label）

**变更清单**：
- `GET /me/export` — 导出 JSON 快照（user / subscription / sessions / products / product_variants / actions / trackers / settings / asin_watchlist + comments 计数）
- `PATCH /me` — 更正用户名 / 邮箱 / 密码，强制当前密码校验，唯一性冲突返回 409
- `DELETE /me` — 匿名化 users 主表（username 置 `deleted_user_{id}`、email/paddle_customer_id/api_key 清空、password_hash 随机化、`deleted_at=NOW()`），业务数据 user_id 保留但已无法识别真人；有 Paddle 订阅时打 WARNING 日志，提醒手动去 Paddle 后台取消（自动取消 API 未接）
- 认证层：`deps.get_current_user` + `/auth/login` 加 `deleted_at IS NOT NULL` 拒绝，防止旧 cookie / 猜密码绕过
- 前端 `/settings/account` 新页面：JSON 快照下载 / 三合一修改表单 / 二次密码 + "DELETE" 双重确认删除

**验收 & lint**：
- `ruff check backend_api/ workers/ review_analyzer/`：PASS
- `npm run typecheck`：PASS
- `python3 -c "from backend_api.app.main import app"` 挂载 4 个 `/me*` 路由

**PROGRESS_V2.md M3.2 全部勾选**，M3 进度 0% → 20%。

**未完成延后项**：
- PATCH /me 的邮箱二次验证 flow（send code + confirm）— 依赖邮件模板双语化（M3.3），待 M3.3 完成后统一补
- DELETE /me 的 Paddle 自动取消 API — 依赖 Paddle SDK 集成，Erika 在 M1 完成 Paddle 商户配置后再接

---

## 2026-07-04

### V4-出海-M3.3：邮件双语化 + Marketing/Transactional 拆分 + Unsubscribe

- **工作量**: M（review_analyzer + backend_api + frontend + 单测共 15 个文件，约 1 人天）
- **状态**: 本地完成，代码已 push develop，等 Erika 部署

**需求描述**：
V4-出海模块 M3.3 后端合规能力第三环。给 Resend 邮件通道加中英双语能力，同时严格分离 Transactional（noreply@）和 Marketing（updates@）两条发件通道，Marketing 邮件强制走 opt-in 并自带一键退订链接，满足 GDPR / CCPA 对营销邮件的合规要求。所有邮件模板从代码硬编码搬到 `review_analyzer/email_templates/{zh-CN,en-US}/*.html`，后续文案迭代不用改 Python。

**涉及岗位及工时**：
- 后端开发：0.7 人天（`review_analyzer/mailer.py` 完整重构、10 个 HTML 模板、`backend_api/app/routes/unsubscribe.py` 新建、`backend_api/app/routes/me.py` 接入邮件通知、19 个单测）
- 前端开发：0.2 人天（`frontend/src/app/unsubscribed/page.tsx` 双语退订成功页 + zh/en messages 新增 8 条文案）
- DevOps 待办：Erika 在 Resend 后台加 `updates@clueai-reviewlens.com` 发件人验证（3 分钟），否则 send_marketing_email 走不通

**变更清单**：
- `review_analyzer/mailer.py` — 从 35 行扩到 280 行：新增 5 个邮件函数（reset_code / verification / subscription_confirmed / subscription_expiring / deletion_confirmed），全部支持 `locale="zh-CN"|"en-US"` 参数
- `_normalize_locale()` — 前端 next-intl 的 `zh` / `en` → `zh-CN` / `en-US`；兼容 `zh-Hans` / `zh_TW` / `en-GB` 等变体；未知 locale fallback 到 `en-US`
- 常量 `FROM_TRANSACTIONAL="ClueAI <noreply@...>"` 与 `FROM_MARKETING="ClueAI <updates@...>"` 严格分离，代码路径不可混用
- `send_marketing_email(to, subject, html, locale, user_id)`：发送前 `SELECT marketing_opt_in FROM users` 校验，fail-close（字段缺失 / 值为 FALSE / DB 异常 → 一律不发）；自动追加双语 unsubscribe footer
- HMAC 退订 token：`hmac.new(API_SESSION_SECRET, str(user_id).encode(), sha256).hexdigest()[:16]`，`hmac.compare_digest` 常数时间比对
- `backend_api/app/routes/unsubscribe.py` — `GET /api/unsubscribe?uid=X&token=Y`，无需登录，三态 302 → 前端 `/unsubscribed?status={success|pending|error}`；DB 字段缺失路径归为 `pending`（等 041 上线自动生效）而非 `error`
- `backend_api/app/routes/me.py` — PATCH /me 改邮箱成功后 fire-and-forget 发变更通知到新邮箱；DELETE /me 匿名化完成后发确认邮件到原邮箱；线程池后台发送，邮件失败不阻断主响应
- `frontend/src/app/unsubscribed/page.tsx` — Suspense 包 useSearchParams（Next 15 静态渲染要求），`MarketingShell` + `useTranslations` 双语呈现三态
- `frontend/messages/{zh,en}.json` — 新增 `unsubscribed.*` 命名空间（8 条文案）
- **单元测试** `backend_api/tests/test_mailer.py`（19 个用例）：locale 归一化 4 组变体、双语模板渲染 4 类、Transactional/Marketing 通道分离、opt-in fail-close 兜底、HMAC token 生成/校验/防篡改 5 个断言

**验收 & lint**：
- `pytest backend_api/tests/test_mailer.py` — 19 passed
- `pytest backend_api/tests/test_geo_block.py` — 8 passed（回归确认 M3.1 未破坏）
- `ruff check backend_api/ review_analyzer/mailer.py` — All checks passed
- `npm run typecheck`（frontend）— 通过

**依赖门槛 & 已知限制**：
- ⚠️ `send_marketing_email` 依赖 users.marketing_opt_in 字段，该字段属 migration 041（M2.5 未上线）。041 前 send_marketing_email 会 fail-close（不误发），unsubscribe 端点会 302 到 `?status=pending` 提示用户。041 上线后**代码零改动自动生效**
- ⚠️ `updates@clueai-reviewlens.com` 发件人需 Erika 在 Resend 后台加验证，未验证前 send_marketing_email 即使 opt-in 通过也会被 Resend 拒
- ⚠️ PATCH /me 改邮箱的**真实二次验证 flow**（code 存 DB + confirm 端点）仍未做，当前只发通知邮件带占位 code；追加 verification token 表 + `/me/verify-email` 端点是下一步
- ⚠️ 订阅相关邮件（confirmed / expiring）已具备双语模板和函数入口，实际触发点等 Paddle webhook 集成（M1 依赖）落地后再调用

**M3 进度更新**：40% → 60%（M3.1 / M3.2 / M3.3 完成，剩 M3.4 Contact 页面 + M3.5 数据保留自动清理）

---

### V4-出海-M3.4：Contact 页 + Sub-processor 清单页 + 全站法律 Footer

- **工作量**: S（前端 6 文件新增 + 1 shell 挂载 + 2 messages 命名空间，约 0.5 人天）
- **状态**: 本地完成，typecheck 通过，等 Erika 部署 + 线上验收

**需求描述**：
V4-出海模块 M3 收尾第一块。用户在合规相关 flow（GDPR/CCPA 数据请求、账号支持、一般咨询）需要一个明确的联系入口；SaaS 合规惯例还要求把所有代表用户处理个人数据的第三方 sub-processor 公开列表，以便审计和季度更新。同时 M2.5 遗留的"全站 Footer 6 个法律链接 + Amazon disclaimer"因 M3.4 属先落地范畴，本次一并做到 marketing-shell 层，让所有营销页面立刻带上 footer。

**涉及岗位及工时**：
- 前端开发：0.5 人天（Contact 页 / Sub-processor 表格双布局 / SiteFooter 组件 / marketing-shell 集成 / cookies + dpa 占位 shell / 双语命名空间）

**变更清单**：
- 新建 `frontend/src/app/contact/page.tsx` — 3 邮箱卡片（privacy@ / support@ / hello@），`use client` + `useTranslations`，参考 `/unsubscribed` 风格；每张卡片：分类标签 + mailto 链接 + 场景描述；底部 1–2 工作日回复时长
- 新建 `frontend/src/app/sub-processors/page.tsx` — 8 家 sub-processor 清单：Supabase / Cloudflare / Anthropic / DataForSEO / Rainforest API / Paddle / Resend / Cloudflare Web Analytics；Desktop 表格 + Mobile 卡片双布局；每家外链其 DPA / Privacy 页；标注 "Last updated: July 2026" + 季度审查声明
- 新建 `frontend/src/components/marketing/site-footer.tsx` — 6 个法律链接（/privacy /terms /cookies /dpa /sub-processors /contact）+ Amazon disclaimer 小字 + `© year ClueAI` 版权
- 修改 `frontend/src/components/marketing/marketing-shell.tsx` — import + 在 `</main>` 之后挂 `<SiteFooter />`（所有营销页 privacy/terms/pricing/trial/unsubscribed/contact/sub-processors 立刻带上 footer）
- 新建 `frontend/src/app/cookies/page.tsx` + `frontend/src/app/dpa/page.tsx` — M2.4 独立任务前的占位空壳，避免 footer 链接 404；含 `TODO(M2.4)` 注释 + 引导到 privacy@ 邮箱兜底
- `frontend/messages/en.json` + `frontend/messages/zh.json` 各新增 3 个命名空间：`footer.*`（7 条：6 法律链接标题 + Amazon disclaimer）/ `contact.*`（3 个 channel 结构化对象 + title/description/responseTime）/ `subProcessors.*`（title/description/lastUpdated/表头 4 列 + quarterly + learnMore）

**依赖门槛 & 已知限制**：
- cookies + dpa 页面本体属 M2.4，本次只做占位 shell 避免 footer 404；M2.4 独立任务时替换正文
- Cookie Banner（EU 首次访问弹窗）+ 老用户 Terms Gate 属 M2.5，migration 041 上线后另做，本次不动
- footer 目前只挂在 `marketing-shell` 层（营销侧全部覆盖）；dashboard 侧（`/dashboard`、`/upload`、`/history` 等）用独立 layout，需要时再单独挂

**M3 进度更新**：60% → 80%（M3.1 / M3.2 / M3.3 / M3.4 完成，剩 M3.5 数据保留清理）

---

## 2026-07-03

### Bug 修复：文件上传 500（生产库缺 source_channel 列）

- **工作量**: S
- **状态**: 已修复（Erika 已执行 migration，无需重启服务）

**需求描述**：
测试账号在上传页选 `data.xlsx`（产品编号 `BG015-PN-US-01`，一级"户外运动"/二级"户外背包"）点"上传并开始分析"后，前端弹出 `Request failed with status 500.`，且 `upload_jobs` 表内没有对应记录（请求根本没落库）。

**根因**：
生产 Supabase 库缺少 `upload_jobs.source_channel` 列，migration `017_add_source_channel.sql` 从未在生产执行。`review_analyzer/database.py:368` 的 `create_upload_job` INSERT 语句包含该列，`psycopg2.errors.UndefinedColumn` 冒到 FastAPI 顶层默认变 500。代码里其实写了 try/except fallback 走无 source_channel 的 INSERT，但从 traceback 看未生效（推测 ECS 镜像里的 database.py 版本早于 06-17 加入 fallback 的提交 `2a5dc58`）。同一测试账号 45 条历史 upload_jobs 也都是无 source_channel 的老结构。

**修复动作**：
ECS api 容器内一次性补跑 migration 017：
- `ALTER TABLE upload_jobs ADD COLUMN IF NOT EXISTS source_channel TEXT NOT NULL DEFAULT 'manual'`
- `ALTER TABLE comments ADD COLUMN IF NOT EXISTS source_channel TEXT NOT NULL DEFAULT 'manual'`
- `CREATE INDEX IF NOT EXISTS idx_comments_source_channel ON comments(user_id, source_channel)`

幂等 DDL，历史行自动补 default `manual`（与代码兜底一致）。`information_schema.columns` 已确认列存在。无需 nginx reload、无需重建镜像。

**验证**：
- Erika 执行 migration 命令后返回 `migration 017 done` + `verify: [('source_channel',)]`
- 待用测试账号线上重跑一次 `data.xlsx` 上传确认 500 消失

**涉及岗位及工时**：
- 后端开发 / DevOps: 1h（排查 + migration 执行）

---

### 推送渠道扩展：钉钉 / 企业微信 · B2 方案

- **工作量**: M
- **状态**: 已完成（待 Erika 部署 + 线上验收）

**需求描述**：
服务条款 `terms/page.tsx:24` 明写"预警通知（飞书/钉钉/企业微信 Webhook）"，但代码只实装飞书，构成虚假宣传合规风险。方案 B2（补实装）：用户面 + 运维告警双通道全部支持三平台；单选下拉；原生富文本格式（飞书 post，钉钉/企业微信 markdown）。

**实现要点**：
1. `review_analyzer/notifier.py` 抽象 platform 分发层：`send_text_notification(platform, url, text, secret)` 统一入口 + 三家 body 构造 + 三家签名（飞书 body、钉钉 URL query、企业微信免签）；富文本 `send_rich_push` 新增 `platform` 参数，飞书用 post 保留 @人 能力，钉钉/企业微信共用一份 markdown 渲染
2. Schema `backend_api/app/schemas/settings.py` + `routes/settings.py` 新增 `webhook_platform` 字段（feishu/dingtalk/wechat，默认 feishu）；`test-webhook` 路由透传 platform；PATCH 改为 merge 更新避免误清 periodic_push/dept_contacts
3. 运维告警：`budget_guard._send_ops_alert`（原 `_send_feishu_alert` 重命名）+ `workers/periodic_jobs` 的 stale 告警和 daily cost digest 全部走 `send_text_notification`；新增环境变量 `OPS_WEBHOOK_PLATFORM`（默认 feishu）+ `OPS_WEBHOOK_SECRET`；`FEISHU_OPS_WEBHOOK` 变量名保留（语义升级为通用运维 URL）
4. `taxonomy_coverage_monitor.format_ops_alert`（原 `format_feishu_alert` 重命名）+ `workers/jobs.py` 的 taxonomy 告警读用户 `webhook_platform` 字段
5. 前端：`lib/api/types.ts` 新增 `WebhookPlatform` + `SettingsResponse.webhook_platform` + `SettingsUpdatePayload.webhookPlatform`；`browser.ts` 的 `saveSettings` / `testWebhook` 透传 platform；`push-settings-panel.tsx` 新增平台下拉 + 按平台动态切换 section 标题/URL placeholder/secret 提示/联系人 hint（企业微信隐藏 secret 输入框；钉钉/企业微信 disable 部门 open_id 输入）；`settings-panel.tsx` 兼容修复

**限制说明**：钉钉/企业微信群机器人不支持精准 @ 联系人（Open ID 是飞书专属），前端 UI 已 disable 对应输入。

**验证**：ruff check、npm run typecheck、py_compile 全过。

**涉及岗位及工时**：
- 后端开发（含 worker）: 4h
- 前端开发: 2h
- 合计: ~1 人天

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

---

## 2026-07-07

### V4-出海-M6: Credit 定价体系改造（海外 4 档套餐 · 统一 credit 池）

- **工作量**: XL
- **状态**: 代码完成，待部署验收

**需求描述**：
海外 SaaS 定价体系全面改造：用统一 credit 池替代原有8维独立限额，降低用户认知成本。新增 Free / Starter / Pro / Team 四档套餐（月付/年付），配套加油包机制。通过 Paddle 计费平台完成订阅管理和加油包充值。

**实现要点**：
1. **DB Migration**：新建 `user_credits`（credit 钱包）+ `credit_ledger`（流水账）两张表；`045_add_starter_plan.sql` 扩展 CHECK 约束支持 starter 档
2. **Credit 核心层**（`quota.py`）：`credit_check` / `credit_consume` / `credit_refund` / `get_credit_balance` / `get_credit_ledger` 五个函数，SELECT FOR UPDATE 防并发超扣
3. **月度 Refill**（`periodic_jobs.py`）：每月 1 号 00:05 UTC 发放 monthly_grant；每天 00:10 UTC 扫描 trial 到期，自动降级 free
4. **调用点改造**：review_analyze / ask / insight / copywriter / translate / export 全部接入 `credit_consume`，失败时 `InsufficientCreditsError` 返回 402
5. **Trial 发放**（`auth.py`）：注册即发 3000 credits + 14 天有效期，写 credit_ledger
6. **Paddle Webhook 改造**（`settings.py`）：`_resolve_plan_from_event` 优先读 Price.custom_data.plan；subscription 事件更新 `user_credits.monthly_grant`；`transaction.completed` + topup=true 触发加油包充值
7. **前端定价页**（`pricing-content.tsx`）：月付/年付 Toggle + 4 列套餐卡（Free/Starter/Pro⭐/Team）+ 加油包区块 + Enterprise 联系入口
8. **Credit 余额 UI**（`sidebar-credit-entry.tsx` + `credit-ledger-drawer.tsx`）：Sidebar 常驻余额入口 + 近 30 条流水抽屉；后端对应 `GET /credits/balance` + `GET /credits/ledger` 端点

**待确认**：
- 用户升级时是否应立即将 balance 重置为新套餐的 monthly_grant（当前仅更新 monthly_grant 字段）

**涉及岗位及工时**：

| 岗位 | 工时 |
|------|------|
| 产品设计 | 8h（Paddle SKU 手动配置 + 定价策略） |
| 后端开发 | 12h |
| 前端开发 | 6h |
| 数据库 | 2h |

---

## 2026-07-08

### V4-出海-M6: 移除 Plan Quota UI 展示，Sidebar 切换为纯 Credits 计费

- **工作量**: XS
- **状态**: 完成

**需求描述**：
删除侧边栏 Plan Quota 展示条目（SidebarQuotaEntry），用户侧只保留 Credits 余额入口。后端 quota_check 逻辑保留不动，作为内部风控使用。

**实现要点**：
1. 从 `sidebar.tsx` 移除 `SidebarQuotaEntry` import 和 JSX 渲染
2. 后端 `quota_check` / `quota_consume` / `PLAN_LIMITS` 全部保留，不影响业务逻辑

**涉及岗位及工时**：

| 岗位 | 工时 |
|------|------|
| 前端开发 | 0.1h |
