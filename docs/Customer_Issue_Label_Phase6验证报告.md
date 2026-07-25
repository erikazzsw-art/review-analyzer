# Customer Issue / Customer Label Phase 6 验证报告

验证日期：2026-07-25

## 1. 验证结论

Phase 6 固定验证集、后端聚合、后端导出、前端下载字段、页面主数据源和真实 Foxelli session 114 干净 raw replay 均已通过本地 / clueai-dev 回归。

本轮发现并修复 1 个 Phase 6 验证问题：后端 TOP 问题 / TOP 亮点 XLSX sheet 已有 `Evidence Verified`，但缺少 `Cluster Propagated` 审计列；完整导出的源评论明细也缺少 issue occurrence 的 cluster 标记。已补齐，并新增自动化测试覆盖。

真实 raw replay 继续发现并修复 2 个问题：

- 旧 cluster propagated payload 会掩盖当前产品真实漏水 evidence，导致 `Water Leaks Through` under-count；已增加保守的当前产品漏水原文规则，只召回当前产品 waders / boots / seams / material 等明确漏水 span，并过滤 `no leaks / kept dry / didn't experience leaking`、旧产品 / 其他品牌漏水、口袋 / 手机袋进水等上下文。
- occurrence 自己的 `cluster_propagated=false` 曾被顶层 `aspects_json.cluster_propagated=true` 覆盖，导致代表证据被错误排除；已改为 occurrence 级字段优先，缺失时才继承顶层 cluster 标记。

完整 XLSX 真实下载还发现 `AI Notice / AI 标注` sheet 名包含 Excel 非法字符 `/`，导致完整导出 500；已最小改为合法 sheet 名 `AI Notice` 并补测试。

真实 Foxelli session 114 干净 raw replay 结论：旧风险 `Water Leaks Through = 9/9` 未复现；最终 `Water Leaks Through` 为 5 mentions / 5 reviews，全部来自当前产品真实漏水原文 span，`Evidence Verified=true`，`Cluster Propagated=false`。

仍需补跑：

- `Comfortable_to_Wear_reviews_57.xlsx`

## 2. 验证样本

固定验证集位置：

- `backend_api/tests/fixtures/customer_label_phase6_validation.json`

真实样本：

- `scratch/session114_comments.xlsx`：prod 只读导出的 Foxelli session 114，92 条评论；仅作为原始来源检查，不上传，因包含旧 `aspects_json` / 标签污染字段
- `scratch/session114_raw_replay.xlsx`：干净 replay 文件，仅保留 `id/content/rating/date/reviewer/source` raw columns，共 92 条，已上传 clueai-dev

覆盖样本：

- Foxelli session 114 风险复刻：`no leaks`、`remained dry`、`kept dry` 不触发 `Water Leaks Through`
- Foxelli session 114 正向触发：`water leaking in`、`Water came in` 进入 `Water Leaks Through`
- `Comfortable_to_Wear_reviews_57.xlsx` 风险复刻：`Comfortable To Wear` occurrence 的 evidence 不在原文
- Mixed review：`The phone protector and hanger was missing... The waders seem to be decent...`
- `cluster_propagated=true` 审计样本：计入统计，不进入代表证据
- 床架类目：`Missing Parts` 与 `Sturdy Construction`
- 睫毛膏类目：`Mascara Clumps` 与 `Does Not Smudge`
- legacy old session / old aspects_json：旧 `issue_tag/highlight_tag` 保守 fallback
- negative overall review 中的 highlight occurrence
- Internal Aspect 过滤：`Waterproof` 不作为主 Customer Label 展示

本地真实数据可用性检查：

- `review_analyzer/data/review_analyzer.db` 中 `sessions` 和 `comments` 为空
- 本地未找到 `Comfortable_to_Wear_reviews_57.xlsx`
- 已通过 prod 只读导出补充 Foxelli session 114，并读取 `scratch/session114_comments.xlsx`
- 已生成并上传干净 replay 文件 `scratch/session114_raw_replay.xlsx`，未上传带旧标签污染字段的 `scratch/session114_comments.xlsx`

真实 Foxelli session 114 raw replay 结果：

- 上传文件：`scratch/session114_raw_replay.xlsx`
- 上传 job：`job_id=2`
- 新 session：`session_id=3`
- 产品名称：`Foxelli Waders - Session114 Phase6 Replay`
- 版本：`phase6-session114-replay-20260725`
- 评论数：92
- clueai-dev SQL：`id=3, total_reviews=92, created_at=2026-07-25 05:45:21.831682+00:00`
- 页面主数据源 `/analysis/results?product_id=...&range=default&session_id=3` 返回 200；3001 results 页面 HTML 返回 200，并包含 `Water Leaks Through`、`Mention Share`、`Impact Reviews`、`Representative Evidence` 与真实 evidence 文案

Top Issue：

- `Water Leaks Through`：5 mentions，Mention Share 62.5%，Review Count 5，Impact Review Share 5.4%，`Evidence Verified=true`，`Cluster Propagated=false`
- Representative Evidence：`Both feet are leaking around where the boot connects to the wader`、`leak at the seams`、`water leaking in`、`not 100% waterproof material`、`were leaking a little bit`
- `Not Breathable`：2 mentions，Mention Share 25.0%，Review Count 2，Impact Review Share 2.2%，`Evidence Verified=false`，`Cluster Propagated=true`
- `Uncomfortable Fit`：1 mention，Mention Share 12.5%，Review Count 1，Impact Review Share 1.1%，`Evidence Verified=false`，`Cluster Propagated=true`

False positive 排除：

- `no leaks`
- `kept dry / remained dry / kept him dry`
- `didn't experience any leaking`
- `no leakage`
- `not a leak yet`
- 旧产品 / 其他品牌 / Magellan 漏水上下文
- 手暖口袋 / storage pocket / 手机袋进水上下文

## 3. 验证项与结果

| 验证项 | 结果 | 说明 |
| --- | --- | --- |
| Mention Share 分母 | 通过 | `mention_count / 同类 label mention_count 总数` |
| Impact Review Share | 通过 | `review_count / 当前筛选范围总评论数` |
| `count / pct` 兼容字段 | 通过 | `count=mention_count`，`pct=mention_share` |
| review_count distinct | 通过 | 同一评论同一 canonical 多 occurrence 只计 1 条 review |
| mixed review 双贡献 | 通过 | 同一评论同时贡献 `Missing Accessories` 和亮点 |
| positive 整体评论里的 issue | 通过 | `water leaking in` 可进入 Top Issue |
| negative 整体评论里的 highlight | 通过 | `feels well made` 可进入 Top Label |
| `no leaks / remained dry / kept dry` | 通过 | 不触发 `Water Leaks Through` |
| 真实漏水表达 | 通过 | `water leaking in / Water came in` 触发 `Water Leaks Through` |
| 真实 Foxelli session 114 raw replay | 通过 | 干净 raw replay 上传 clueai-dev，`Water Leaks Through=5`，全部来自当前产品真实漏水原文 span，无 9/9 过计数 |
| evidence 真实原文校验 | 通过 | evidence 不在原文时 `evidence_verified=false` |
| 代表证据过滤 | 通过 | missing evidence 与 cluster propagated 不进入代表证据 |
| 页面主数据源 | 通过 | `/analysis/results?product_id=...&session_id=3` 与 3001 results HTML 均包含正确 Top Issue / Top Label 字段 |
| Internal Aspect 主展示过滤 | 通过 | broad/internal label 不进入 Top Customer Label |
| legacy old session | 通过 | 旧 `issue_tag/highlight_tag` 保守展示，不崩 |
| 后端模块 XLSX | 通过 | TOP sheet 包含 Phase 6 要求字段 |
| 完整 XLSX 导出 | 通过 | TOP sheet 与源评论明细补齐审计字段，`AI Notice` sheet 名合法，真实下载 200 |
| 前端下载字段 | 通过 | occurrence 级下载包含 `Evidence Verified` 与 `Cluster Propagated` |
| 前端表头与 tooltip | 通过 | 表头和 tooltip 文案符合 Phase 5/6 口径 |

## 4. 自动化测试覆盖

新增测试文件：

- `backend_api/tests/test_customer_label_phase6_validation.py`

新增覆盖：

- 固定验证集加载与 Top Issue / Top Label 聚合
- Foxelli 114 风险复刻
- Comfortable evidence 失配
- mixed review issue/highlight 双贡献
- occurrence 聚合 denominator
- review_count distinct
- impact_review_share
- evidence verification
- cluster propagated audit only
- legacy fallback
- export payload 字段

已运行：

```bash
python3 -m pytest backend_api/tests/test_specific_issue.py backend_api/tests/test_customer_label_catalog.py backend_api/tests/test_customer_label_phase6_validation.py backend_api/tests/test_export_customer_label_phase5.py
```

结果：45 passed

```bash
python3 -m ruff check backend_api/app/services/specific_issue.py backend_api/app/routes/export.py review_analyzer/exporter.py review_analyzer/insight_engine.py backend_api/tests/test_specific_issue.py backend_api/tests/test_customer_label_phase6_validation.py backend_api/tests/test_export_customer_label_phase5.py
```

结果：All checks passed

```bash
npm run typecheck --prefix frontend
```

结果：通过

```bash
git diff --check
```

结果：通过

## 5. 手动验证记录

前端展示代码检查：

- 高频痛点表头：`Customer Issue | Mention Share | Impact Reviews | Representative Evidence | Actions`
- 产品亮点表头：`Customer Label | Mention Share | Impact Reviews | Representative Evidence | Download`
- `Mention Share` tooltip：解释为同类标签出现次数占比
- `Impact Reviews` tooltip：解释为命中评论数 / 当前筛选范围总评论数
- Representative Evidence 仅来自 `evidence_spans/representative_evidence`
- 无 verified evidence 时展示 `No verified representative evidence`
- 旧 session 通过 `legacy_fallback` 显示 legacy 说明或保守口径
- Internal Aspect 仅作为下载或审计 metadata，不作为主标签

下载和导出代码检查：

- `DownloadTagButton` occurrence 级下载包含评论、evidence、`Evidence Verified`、`Cluster Propagated`
- `backend_api/app/routes/export.py` 模块导出 TOP sheet 包含 Phase 6 字段
- `review_analyzer/exporter.py` 完整导出 TOP sheet 包含 Phase 6 字段
- 源评论明细补齐 issue occurrence 的 `Cluster Propagated`

真实 session 114 手动验证：

- `scratch/session114_comments.xlsx` 是 prod 只读导出源文件，包含旧 `aspects_json` / 标签污染字段，仅用于核对，不上传。
- `scratch/session114_raw_replay.xlsx` 只保留 `id/content/rating/date/reviewer/source`，共 92 条，已上传 clueai-dev。
- 上传使用临时验证账号 `phase6_replay_20260725_0545@example.com`，生成 `job_id=2`、`session_id=3`。
- 用户指定 SQL 返回：`id=3 | product_id=Foxelli Waders - Session114 Phase6 Replay | version=phase6-session114-replay-20260725 | total_reviews=92 | created_at=2026-07-25 05:45:21.831682+00:00`。
- 页面主数据源 `/analysis/results?product_id=Foxelli%20Waders%20-%20Session114%20Phase6%20Replay&range=default&session_id=3` 返回 200；3001 results 页面 HTML 在 dev server 热身后返回 200。
- 页面 / API Top Issue 中 `Water Leaks Through` 为 5 mentions / 5 reviews，Representative Evidence 均为原文 span，`Evidence Verified=true`，`Cluster Propagated=false`。
- 抽查 `no leaks / kept dry / didn't experience leaking / no leakage / not a leak yet` 评论均无 `water_leaks_through` occurrence。

真实下载 / 导出验证：

- 模块导出：`/analysis/sessions/3/export?module=user_experience&locale=en` 返回 200，`Positive Feedback TOP10` 和 `Negative Feedback TOP10` 均包含 `Mention Count`、`Mention Share`、`Review Count`、`Impact Review Share`、`Representative Evidence`、`Evidence Verified`、`Cluster Propagated`。
- 模块导出 `Water Leaks Through` 行：Mention Count 5，Mention Share 62.5%，Review Count 5，Impact Review Share 5.4%，Representative Evidence 为 5 条真实原文 span，`Evidence Verified=true`，`Cluster Propagated=false`。
- 完整导出：`/analysis/sessions/3/export/full` 返回 200，sheet 包含 `总览摘要`、`源评论分析明细`、`TOP10 核心问题点`、`TOP10 产品亮点`、`AI Notice`。
- 完整导出 TOP sheet 字段与模块导出一致；源评论明细包含 occurrence 级 `Evidence Span`、`Evidence Verified`、`Cluster Propagated`，水漏 occurrence 均为 `true / false`。

本轮未做 Playwright 交互式点击走查；当前项目未配置前端组件测试框架，本轮不引入新框架，按约束使用 API / HTML / XLSX 读取 + typecheck + 代码检查记录。

## 6. 修复项

Phase 6 验证发现并修复：

- `backend_api/app/services/specific_issue.py`
  - 聚合 row 增加 `evidence_verified`
  - 聚合 row 增加 `cluster_propagated`
  - 增加保守的当前产品水漏原文规则，召回当前产品真实 `Water Leaks Through` evidence，同时过滤否定、正向 dry、旧产品 / 其他品牌、附件口袋进水上下文
  - occurrence 级 `cluster_propagated` 字段优先，缺失时才继承顶层 `aspects_json.cluster_propagated`
- `backend_api/app/routes/export.py`
  - TOP 问题 / TOP 亮点 sheet 增加 `Cluster Propagated`
  - `Evidence Verified` 改读聚合 row 显式字段
- `review_analyzer/exporter.py`
  - 完整导出 TOP 问题 / TOP 亮点 sheet 增加 `Cluster Propagated`
  - 源评论明细增加 issue occurrence `Cluster Propagated`
  - `AI Notice / AI 标注` 改为合法 Excel sheet 名 `AI Notice`
- `frontend/src/components/analysis/analysis-results-sections.tsx`
  - 前端原始评论下载增加 issue occurrence `Cluster Propagated`
- `frontend/src/components/analysis/module-card.tsx`
  - 本地聚合 XLSX fallback 增加 `Evidence Verified` 与 `Cluster Propagated`

## 7. 残留风险

- `Comfortable_to_Wear_reviews_57.xlsx` 原始数据仍未放入本地工作区，只能用固定 fixture 复刻风险。
- `scratch/session114_comments.xlsx` 仍包含旧 persisted occurrence payload 污染，不应上传；真实 replay 必须继续使用 `scratch/session114_raw_replay.xlsx` 或重新导出的 raw-only 文件。
- 本轮未做浏览器人工点击下载验证，已用 API / HTML / XLSX 读取、typecheck 和代码检查覆盖前端路径。
- TOP sheet 的 `Cluster Propagated` 是 row 级布尔值，含义为该 Top 标签至少包含一个 cluster propagated occurrence；逐条追溯仍以 occurrence 级下载为准。
- legacy old session 缺少 verified evidence 时不会展示代表证据，这是保守口径，可能导致旧数据页面 evidence 较少。
- 本地后端使用 `.env` LLM key 时，results 首次请求可能被 OpenAI connection error 与 DeepSeek `deepseek-chat` 模型不支持拖慢；Direct backend 最终 fallback 返回 200，3001 页面 dev server 热身后返回 200，但建议后续单独修正 DeepSeek model 配置或为 results 文本增强加非阻塞 / 缓存策略。
- clueai-dev 与当前代码存在 schema drift，真实上传验证期间已最小补齐 `comments.source_channel`、`comments.cluster_id`、`comments.cluster_representative_id`、`upload_jobs.source_channel`、`upload_jobs.trace_json`、`sessions.warnings_json`，并执行 `058_customer_label_catalog_alias_candidates.sql`；应纳入正式 migration 检查。

## 8. Phase 7 灰度建议

- 将 `scratch/session114_raw_replay.xlsx` 对应的 session 3 作为 Foxelli Water Leak 灰度金样本，持续确认 `Water Leaks Through` 只包含当前产品真实漏水 evidence。
- 导入或重放 `Comfortable_to_Wear_reviews_57.xlsx`，确认 missing evidence 不进入 Representative Evidence，下载中标记 `Evidence Verified=false`。
- 对灰度 session 记录 label stats：issue/highlight total_mentions、top label share、impact share、evidence_verified_ratio、cluster_propagated_ratio。
- 加告警：单一标签突然 100%、verified evidence 比例过低、broad/internal label 进入 Top、cluster propagated 占比异常升高。
- 保留新旧聚合并行对比一段时间，确认页面、下载、后端导出、Action Center、Review Tracking 口径一致。
- 单独修正 LLM router 的 DeepSeek model 配置或将 results AI 文本增强改成非阻塞，避免页面首开被外部模型失败拖慢。
