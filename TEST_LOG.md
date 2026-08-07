# ClueAI 测试记录

> 版本：v1.0
> 创建日期：2026-05-07

---

## 修复记录

| 日期 | 问题描述 | 解决方案 |
|------|---------|---------|
| 2026-08-07 | **`other` 占比告警泄漏给客户（5.9.6-C1）**。`taxonomy_coverage_monitor` 把「品类 X 的 aspect 覆盖不足：'other' 占比 23.4%（阈值 15%）」写入 `sessions.warnings_json`，结果页 `results/page.tsx:547` 无条件把 `warnings_json` 全量渲染成黄色横幅。该告警是我方 taxonomy 资产债务，客户看到等于自曝分类覆盖不足，且无法据此行动。此横幅由 Step 3 监控链路引入，早于 5.9.6-C，一直在线。 | `taxonomy_coverage_monitor.py` 新增 `WARNING_TYPE_TAXONOMY_COVERAGE_LOW` 常量 + `INTERNAL_ONLY_WARNING_TYPES` frozenset + `filter_customer_visible_warnings()`（fail-closed：非 dict / 缺 `type` / `type` 为空的条目一律按内部丢弃，防止未来新增内部告警类型时忘记登记就默认泄漏）；`analysis.py` 的 `_session_payload()` 统一过滤。选单点过滤而非改前端渲染：前端改法只挡页面，导出和其他 payload 消费方仍会泄漏。**内部信号未减弱** —— DB `warnings_json` 写入、`trace.record_warning`、飞书推送三条链路保持原样。新增 `test_taxonomy_coverage_customer_visibility.py` 6 测试全绿；`test_analysis_results_llm_fallback` + `test_taxonomy_routes` 3 测试回归通过；ruff clean。 |
| 2026-08-06 | **线上登录无法提交：表单 `type="email"` HTML5 约束验证阻止非邮箱用户名登录**。用户填入用户名 `惜_clueai` + 密码后点击"登录"，浏览器因 `<input type="email">` 值不含 `@` 触发约束验证失败 → 阻止 `submit` 事件 → `handleSubmit` 从未调用 → `fetch("/api/auth/login")` 从未执行 → 无 POST 请求、无错误提示、无重定向。Playwright 线上复现确认 `form.checkValidity()=false`，换用 `test@example.com` 后 POST 正常发出。 | 修改 `frontend/src/components/auth/login-form.tsx`：`type="email"` → `type="text"`（API 同时支持邮箱和用户名登录，前端不应做 email 格式校验）；同步更新 `frontend/messages/zh.json` 和 `frontend/messages/en.json` 的 `loginEmailPlaceholder` 为 "请输入邮箱或用户名" / "Enter email or username"。 |
| 2026-08-06 | **5.9.6-D 工作包 4/5 完成：Resolver fail-closed + 9 标签重标**。WP4：新增 `ResolutionRejectReason` enum（5 值，固定 gate 顺序）+ `LabelResolutionResult` dataclass，删除 `_scope_matches()`，`resolve_formal_label*` 改为 keyword-only 必传 `category_key`/`sub_category_key`，所有实验模块调用方已更新。WP5：16 个 taxonomy YAML 新增 `size_chart` aspect，`confusing_size_chart` 的 `aspect_keys` 从 `size_fit` 改为 `size_chart`（scope: 63→16），`category_keys`/`sub_category_keys` 从 YAML+dataclass+validator 三处删除，`registry_version` 升至 `5.9.6-D.1`，`aspect_taxonomy.py` 新增 `size_chart`，cosequin→Cosequin 大小写修复。 | 更新 `review_fragment_label_catalog.py`（+~120 行 resolver 改造）、`review_fragment_candidate_multimodule.py`（8 个 call site 更新）、16 个 taxonomy YAML（size_chart）、3 个 seed YAML、`review_fragment_label_registry.yaml`（9 label 删 category_keys/sub_category_keys、confusing_size_chart aspect_keys 改 size_chart）、`aspect_taxonomy.py`（size_chart）、`validate_label_scope.py`（hasattr 替换 `"*"` in list 检查）。新增 14 个 WP4 测试 + 1 个 WP5 size_chart 测试。validator 0 failure/0 warning。45 catalog + 14 cache + 9 sync = 68 tests PASS。ruff clean。 |Scope Governance DoD (`notes/scope-governance-dod.md`) 定义交易层/产品层二分、三档 scope_policy、封闭枚举护栏；Registry schema 升级：新增 `data/taxonomy/shared/transaction_aspects.yaml`（3 个交易层维度），扩展 `FormalLabelDefinition` 8 个新字段（scope_policy / required_transaction_dimension / scope_reason / positive_examples / negative_examples / review_status / blocked_contexts / owner_note），实现 effective scope 计算（内存+lru_cache，防水→5 子类目，accessory_storage→1）；scope 校验脚本 `scripts/validate_label_scope.py`（6 项校验，--dry-run/--print-matrix）；31 个单元测试（含 25 个新增：schema fail-closed ×6、transaction 枚举 ×2、effective scope ×7、负例 ×3、scope_policy 分布 ×2、数据模型 ×5）。解析层 fail-closed：缺 scope_policy/review_status、transaction_universal 缺 dim/scope_reason、非封闭集维度均 raise ValueError 不进 registry。registry_version 保持 5.9.6-A.1 不 bump。 | 新增 `data/taxonomy/shared/transaction_aspects.yaml`、`scripts/validate_label_scope.py`、`notes/scope-governance-dod.md`；更新 `review_fragment_label_registry.yaml`（9 label 各补 8 字段）、`review_fragment_label_catalog.py`（+200 行：TransactionDimension/PositiveExample/NegativeExample dataclass、YAML 解析、effective scope 计算）、`test_review_fragment_label_catalog.py`（6→31 测试）。ruff check PASS，6 旧测试回归 PASS，9 sync_taxonomy 回归 PASS，静态确认 active 路径未 import 新函数。 |
| 2026-07-31 | **5.9.9 Step 7.6→Step 8 final gates PASS**。完成 production config / kill switch / observability、gray-run runbook / rollback drill、go/no-go acceptance pack、vector bad case memory lite 后执行最终本地门禁；生产 feature flag 未开启，未执行 production upload / reanalysis / DB write / credit / LLM。 | 验证：Step 6/7/7.5/7.6/7.7/7.8/8 focused `44 passed in 0.58s`；waders/customer-label 目标回归 `125 passed in 8.48s`；`python3 scripts/customer_label_v2_waders_shadow_replay.py` PASS，P0=`0`；六个重点标签 FP/FN=0；`python3 -m ruff check ...` PASS；`git diff --check` PASS；未触碰前端，未运行 frontend typecheck。未 push。 |
| 2026-07-31 | **5.9.9 Step 8 Vector bad case memory lite PASS**。新增 lightweight/local sparse token vector memory，将 audited bad case、gold regression、candidate pool reviewed result 转成本地可检索 memory；仅辅助相似历史错例检索、candidate 聚类、审核排序、audit/debug report，不接生产写库，不参与 frontstage display 决策。 | 新增 `backend_api/app/services/customer_label_v2_bad_case_memory.py`、`backend_api/tests/test_customer_label_v2_bad_case_memory.py`、报告 `docs/5.9.9-step8-vector-bad-case-memory-lite.md`，更新 `scripts/customer_label_v2_waders_shadow_replay.py` 输出 artifact `tmp/5.9.9-step8-vector-bad-case-memory-lite/vector-bad-case-memory-lite.json`。验证：focused Step 8 `5 passed`；Step 8 + shadow/frontstage focused `32 passed`；`python3 scripts/customer_label_v2_waders_shadow_replay.py` PASS，P0=0，memory item count `81`、source counts audited bad case `32` / candidate pool reviewed `14` / gold regression `35`，no evidence display count `0`，context blocked display count `0`，`vector_result_decides_display=false`；未 production upload / reanalysis / DB write / credit / LLM，未开启生产 feature flag，未 push。 |
| 2026-07-31 | **5.9.9 Step 7.8 v2 frontstage go/no-go acceptance pack PASS**。新增灰度前 acceptance pack，汇总 Step 6/7/7.5/7.6/7.7 的九项门禁：feature flag 默认 off、readiness dry-run PASS、kill switch PASS、rollback drill PASS、stored shadow availability 明确、L3-only gate 明确、unknown/candidate/audit 不进 frontstage、replay P0=0、六个重点标签 FP/FN=0。 | 新增 `backend_api/app/services/customer_label_v2_frontstage_acceptance.py`、`backend_api/tests/test_customer_label_v2_frontstage_acceptance.py`、报告 `docs/5.9.9-step7.8-frontstage-go-no-go-acceptance-pack.md`，更新 `scripts/customer_label_v2_waders_shadow_replay.py` 输出 artifact `tmp/5.9.9-step7.8-frontstage-go-no-go-acceptance-pack/go-no-go-acceptance-pack.json`。验证：focused Step 7.8 `3 passed`；acceptance/runbook/config focused `12 passed`；`python3 scripts/customer_label_v2_waders_shadow_replay.py` PASS，P0=0，acceptance pack `status=PASS`、`go_no_go=GO_READY_FOR_ERIKA_AUTHORIZED_GRAY_RUN_ONLY`、`no_go_items=[]`、9 项 checklist 全 PASS；未 production upload / reanalysis / DB write / credit / LLM，未开启生产 feature flag，未 push。 |
| 2026-07-31 | **5.9.9 Step 7.7 v2 frontstage gray-run runbook / rollback drill PASS**。新增只读灰度 runbook，定义 0% baseline、stored shadow audit、scoped session、scoped sub_category、scoped category observation；新增本地 rollback drill，覆盖 baseline v2 selected、global rollback、scoped rollback、global kill switch、scoped kill switch、flag off。生产操作必须由 Erika 单独授权，本轮未执行生产灰度、未开启生产 feature flag。 | 新增 `backend_api/app/services/customer_label_v2_frontstage_runbook.py`、`backend_api/tests/test_customer_label_v2_frontstage_runbook.py`、报告 `docs/5.9.9-step7.7-frontstage-gray-run-rollback-drill.md`，更新 `scripts/customer_label_v2_waders_shadow_replay.py` 输出 artifact `tmp/5.9.9-step7.7-frontstage-gray-run-rollback-drill/gray-run-rollback-drill.json`。验证：focused Step 7.7 `3 passed`；相邻 config/readiness/runbook `19 passed`；`python3 scripts/customer_label_v2_waders_shadow_replay.py` PASS，P0=0，rollback drill case count `6`、selected read paths `v1_current=5` / `v2_shadow=1`、rollback selected `2`、kill switch selected `2`、violations `[]`；未 production upload / reanalysis / DB write / credit / LLM，未开启生产 feature flag，未 push。 |
| 2026-07-31 | **5.9.9 Step 7.6 v2 frontstage production config / kill switch / observability contract PASS**。在 Step 7.5 readiness 基础上新增 production-safe config resolution：env/config 解析集中化，支持 enabled、session/category/sub_category/category-sub_category scope、fixture gate、enabled maturity、rollback、global/scoped kill switch；默认全部 off，runtime shadow env 默认 false；invalid config fail closed 到 `v1_current` 并记录 validation errors。 | 更新 `backend_api/app/services/customer_label_v2_frontstage.py`、`scripts/customer_label_v2_waders_shadow_replay.py`，新增 `backend_api/tests/test_customer_label_v2_frontstage_config.py`、报告 `docs/5.9.9-step7.6-frontstage-config-kill-switch-observability.md` 与 artifact `tmp/5.9.9-step7.6-frontstage-config-kill-switch-observability/frontstage-config-kill-switch-observability.json`。验证：focused Step 7.6 `6 passed`；Step 6/7/7.5/7.6 focused `33 passed`；`python3 scripts/customer_label_v2_waders_shadow_replay.py` PASS，P0=0，Step 7.6 artifact case count `8`、selected read paths `v1_current=7` / `v2_shadow=1`、kill switch selected `2`、rollback selected `2`、config validation error count `2`、case expectation violations `[]`；未 production upload / reanalysis / DB write / credit / LLM，未开启生产 feature flag，未 push。 |
| 2026-07-31 | **5.9.9 Step 7.5 v2 frontstage read-path production readiness / dry-run pack PASS**。在 Step 7 actual consumer integration 基础上新增只读 readiness dry-run 能力：输入本地 review payload + feature flag/env config，输出 selected read path preview，检查 flag/scope/fixture gate/maturity/stored shadow/rollback；dry-run 强制 `allow_runtime_shadow=False`，no stored shadow 不进入 v2，unknown/new label 不进入 frontstage。 | 更新 `backend_api/app/services/customer_label_v2_frontstage.py`、`scripts/customer_label_v2_waders_shadow_replay.py`，新增 `backend_api/tests/test_customer_label_v2_frontstage_readiness.py`、报告 `docs/5.9.9-step7.5-frontstage-readiness-dry-run.md` 与 artifact `tmp/5.9.9-step7.5-frontstage-readiness-dry-run/frontstage-readiness-dry-run.json`。验证：focused Step 7.5 `10 passed`；Step 6/7/7.5 focused `27 passed`；相关后端回归 `69 passed`；waders/customer-label 目标回归 `125 passed`；`npm run typecheck` PASS；`python3 scripts/customer_label_v2_waders_shadow_replay.py` PASS，P0=0，Step 7.5 artifact case count `10`、selected read paths `v1_current=8` / `v2_shadow=2`、case expectation violations `[]`；六个重点标签 FP/FN=0；`python3 -m ruff check ...` PASS；`git diff --check` PASS；未 production upload / reanalysis / DB write / credit / LLM，未开启生产 feature flag，未 push。 |
| 2026-07-30 | **5.9.9 Step 7 v2 frontstage read-path actual consumer integration PASS**。把 Step 6 selected read model 接入实际 frontstage 读路径：Results page Top10、single review detail、raw review export、single-tag download；默认仍为 v1/current，v2 仅在显式 flag + scope 命中 + shadow fixture gate PASS + `L3_sub_category` + verified v2 display 时生效；L0/L1/L2、unknown/new label、audit/candidate pool 不进入前台，rollback 回 v1/current。 | 更新 `backend_api/app/services/customer_label_v2_frontstage.py`、`backend_api/app/services/specific_issue.py`、`backend_api/app/routes/analysis.py`、`backend_api/app/routes/export.py`、`review_analyzer/exporter.py`、`frontend/src/lib/customer-labels.ts`、`scripts/customer_label_v2_waders_shadow_replay.py`，新增 `backend_api/tests/test_customer_label_v2_frontstage_integration.py` 与报告 `docs/5.9.9-step7-v2-frontstage-read-path-integration.md`。验证：focused integration `8 passed`；Step 6+7 focused `17 passed`；相关后端回归 `69 passed`；waders/customer-label 目标回归 `125 passed`；`npm run typecheck` PASS；`python3 scripts/customer_label_v2_waders_shadow_replay.py` PASS，artifact `tmp/5.9.9-step7-v2-frontstage-read-path-integration/waders-shadow-summary.json`，P0=0，`frontstage-consumer-integration.json` case count `5`、violations `0`，`frontstage-read-path-contract.json` case count `8`、violations `0`；六个重点标签 FP/FN=0；`python3 -m ruff check ...` PASS；`git diff --check` PASS；未 production upload / reanalysis / DB write / credit / LLM，未开启生产 feature flag，未 push。 |
| 2026-07-30 | **5.9.9 Step 6 v2 frontstage feature flag / read-path contract PASS**。新增本地 read-path helper，定义 v2 shadow 到 frontstage 的默认关闭 feature flag、per-session / per-category / per-sub_category / category-sub_category scope、shadow fixture gate、默认 L3-only eligibility 与 rollback 回 v1/current。当前 live frontstage 未替换，四条消费路径仅在 contract 中绑定 selected display occurrences：Results page Top10、single review detail、raw review export、single-tag download。 | 新增 `backend_api/app/services/customer_label_v2_frontstage.py`、`backend_api/tests/test_customer_label_v2_frontstage.py`、报告 `docs/5.9.9-step6-v2-frontstage-feature-flag-read-path.md`，更新 `scripts/customer_label_v2_waders_shadow_replay.py` 输出 Step 6 artifact。验证：focused tests `python3 -m pytest backend_api/tests/test_customer_label_v2_frontstage.py -q` PASS（9 passed）；v2/read-path/maturity/candidate pool `51 passed in 0.59s`；目标回归 `139 passed in 8.71s`；`python3 scripts/customer_label_v2_waders_shadow_replay.py` PASS，artifact `tmp/5.9.9-step6-v2-frontstage-feature-flag-read-path/waders-shadow-summary.json`，P0=0，六个重点标签 FP/FN=0；read-path artifact `frontstage-read-path-contract.json` case count `8`、violations `0`；`python3 -m ruff check ...` PASS；`git diff --check` PASS；未 production upload / reanalysis / DB write / credit / LLM，未开启生产 feature flag，frontstage 未替换。 |
| 2026-07-30 | **5.9.9 Step 5 Category Maturity + 10 大类 L1/L2 灰度 PASS**。实现 Customer Label v2 category/sub_category maturity gate：`L0_unknown` 默认 audit/candidate pool；`L1_generic` 只允许 generic-safe highlights；`L2_category` 只允许高置信、强 evidence、低风险 category-safe 基础标签；`L3_sub_category` 保留 waders 成熟 catalog + verifier display。10 大类灰度复用 `backend_api/app/data/sub_category_categories.json`，不新增后台 UI、不写 DB。 | 新增 `backend_api/app/services/customer_label_v2_maturity.py`、`backend_api/tests/fixtures/customer_label_v2_maturity_rollout.json`、`backend_api/tests/test_customer_label_v2_maturity.py`、报告 `docs/5.9.9-step5-category-maturity-l1-l2-rollout.md`，更新 `backend_api/app/services/customer_label_v2_shadow.py` 与 `scripts/customer_label_v2_waders_shadow_replay.py`。验证：focused tests `python3 -m pytest backend_api/tests/test_customer_label_v2_maturity.py -q` PASS（8 passed）；v2/candidate pool/maturity `42 passed in 0.74s`；目标回归 `130 passed in 10.80s`；`python3 scripts/customer_label_v2_waders_shadow_replay.py` PASS，artifact `tmp/5.9.9-step5-category-maturity-l1-l2-rollout/waders-shadow-summary.json`，P0=0，六个重点标签 FP/FN=0；candidate pool raw/deduped `14/14`、reviewed `14`、invalid `0`；`python3 -m ruff check ...` PASS；`git diff --check` PASS；未 production upload / reanalysis / DB write / credit / LLM，frontstage 未替换。 |
| 2026-07-30 | **5.9.9 Step 4.6 waders 351-400 human gold assimilation PASS**。将 Erika 人工标注 Excel 转为 `backend_api/tests/fixtures/customer_label_waders_351_400_human_gold.json`，校验 50 条样本的 expected issue/highlight、locatable evidence spans、blocked labels 与 needs_new_label candidates；5 条人工标签因无可定位 evidence 显式进入 fixture validation errors。 | 更新 `backend_api/app/services/specific_issue.py`、`scripts/customer_label_v2_waders_shadow_replay.py`，新增 `backend_api/tests/test_customer_label_waders_351_400_human_gold.py` 与报告 `docs/5.9.9-step4.6-waders-351-400-human-gold-assimilation.md`。验证：focused tests `python3 -m pytest backend_api/tests/test_customer_label_waders_351_400_human_gold.py -q` PASS（6 passed）；waders old regression PASS（16 passed）；目标回归 `python3 -m pytest backend_api/tests/test_customer_label_waders_351_400_human_gold.py backend_api/tests/test_customer_label_v2_candidate_pool.py backend_api/tests/test_customer_label_v2_shadow.py backend_api/tests/test_customer_label_waders_session121_blind_regression.py backend_api/tests/test_customer_label_waders_session120_human_gold.py backend_api/tests/test_customer_label_waders_step4_gold.py backend_api/tests/test_customer_label_waders_step2_gating.py backend_api/tests/test_specific_issue.py backend_api/tests/test_customer_label_phase6_validation.py backend_api/tests/test_export_customer_label_phase5.py backend_api/tests/test_customer_label_50u_readiness.py backend_api/tests/test_outdoor_waders_taxonomy.py -q` PASS（122 passed in 7.88s）；`python3 scripts/customer_label_v2_waders_shadow_replay.py` PASS，artifact `tmp/5.9.9-step4.6-waders-351-400-human-gold-assimilation/waders-shadow-summary.json`，P0=0，六个重点标签 FP/FN=0；`python3 -m ruff check ...` PASS；`git diff --check` PASS；未 production upload / reanalysis / DB write / credit / LLM，frontstage 未替换。 |
| 2026-07-30 | **5.9.9 Step 4.5 Candidate Pool lightweight review entry MVP PASS**。在 Step 4 candidate pool MVP 基础上补齐本地 review action apply flow：输入 candidate pool artifact/items + review actions，复用 `accept`、`reject`、`correct_label`、`correct_evidence`、`needs_new_label`、`ignore`；invalid action 不改变 source item，只进入 `validation_errors` / `action_audit`；reviewed artifact 保留 `source_candidate_item`、action、validation errors、review_status、deterministic `reviewed_at`。 | 更新 `backend_api/app/services/customer_label_v2_candidate_pool.py`、`backend_api/tests/test_customer_label_v2_candidate_pool.py`、`scripts/customer_label_v2_waders_shadow_replay.py`，新增报告 `docs/5.9.9-step4.5-candidate-pool-review-entry-mvp.md`。验证：`python3 -m pytest backend_api/tests/test_customer_label_v2_candidate_pool.py -q` PASS（16 passed）；`python3 -m pytest backend_api/tests/test_customer_label_v2_candidate_pool.py backend_api/tests/test_customer_label_v2_shadow.py -q` PASS（34 passed）；目标回归 `python3 -m pytest backend_api/tests/test_customer_label_v2_candidate_pool.py backend_api/tests/test_customer_label_v2_shadow.py backend_api/tests/test_customer_label_waders_session121_blind_regression.py backend_api/tests/test_customer_label_waders_session120_human_gold.py backend_api/tests/test_customer_label_waders_step4_gold.py backend_api/tests/test_customer_label_waders_step2_gating.py backend_api/tests/test_specific_issue.py backend_api/tests/test_customer_label_phase6_validation.py backend_api/tests/test_export_customer_label_phase5.py backend_api/tests/test_customer_label_50u_readiness.py backend_api/tests/test_outdoor_waders_taxonomy.py -q` PASS（116 passed in 6.56s）；`python3 scripts/customer_label_v2_waders_shadow_replay.py` PASS，artifact `tmp/5.9.9-step4.5-candidate-pool-review-entry-mvp/waders-shadow-summary.json`，reviewed JSON/CSV 输出完成，waders P0=0，六个重点标签 FP/FN=0；`python3 -m ruff check ...` PASS；`git diff --check` PASS；未 production upload / reanalysis / DB write / credit / LLM，frontstage 未替换。 |
| 2026-07-30 | **5.9.9 Step 4 Candidate Pool MVP + audit export PASS**。实现本地 candidate pool collector/helper，从 `run_customer_label_v2_shadow` result 收集 `candidate_pool_items`，按 `canonical_label_key` / `raw_label` / `sub_category` / `downgrade_reasons` 去重，按 downgrade reason priority、review count、impact score、confidence 排序；新增稳定 JSON artifact、最小 CSV export 与本地 review action validation contract。 | 新增 `backend_api/app/services/customer_label_v2_candidate_pool.py`、`backend_api/tests/test_customer_label_v2_candidate_pool.py`、`docs/5.9.9-step4-candidate-pool-mvp.md`，更新 `scripts/customer_label_v2_waders_shadow_replay.py`。验证：`python3 -m pytest backend_api/tests/test_customer_label_v2_candidate_pool.py -q` PASS（8 passed）；`python3 -m pytest backend_api/tests/test_customer_label_v2_shadow.py -q` PASS（18 passed）；目标回归 `python3 -m pytest backend_api/tests/test_customer_label_v2_candidate_pool.py backend_api/tests/test_customer_label_v2_shadow.py backend_api/tests/test_customer_label_waders_session121_blind_regression.py backend_api/tests/test_customer_label_waders_session120_human_gold.py backend_api/tests/test_customer_label_waders_step4_gold.py backend_api/tests/test_customer_label_waders_step2_gating.py backend_api/tests/test_specific_issue.py backend_api/tests/test_customer_label_phase6_validation.py backend_api/tests/test_export_customer_label_phase5.py backend_api/tests/test_customer_label_50u_readiness.py backend_api/tests/test_outdoor_waders_taxonomy.py -q` PASS（108 passed in 6.63s）；`python3 scripts/customer_label_v2_waders_shadow_replay.py` PASS，artifact `tmp/5.9.9-step4-candidate-pool-mvp/waders-shadow-summary.json`，candidate pool JSON/CSV 输出完成，waders P0=0，六个重点标签 FP/FN=0；未 production upload / reanalysis / DB write / credit / LLM。 |
| 2026-07-30 | **5.9.9 Step 3 Verifier safety gate + candidate pool MVP PASS**。固化 v2 deterministic verifier：拆出 verifier context/outcome、display gate、downgrade reason 聚合与 candidate pool minimum item schema；继续复用 5.9.8 verified occurrence projection/gating，不替换前台展示。 | 更新 `backend_api/app/services/customer_label_v2_shadow.py`、`backend_api/tests/test_customer_label_v2_shadow.py`、`scripts/customer_label_v2_waders_shadow_replay.py`，新增报告 `docs/5.9.9-step3-verifier-safety-gate.md`。验证：`python3 -m pytest backend_api/tests/test_customer_label_v2_shadow.py -q` PASS（18 passed）；目标回归 `python3 -m pytest backend_api/tests/test_customer_label_v2_shadow.py backend_api/tests/test_customer_label_waders_session121_blind_regression.py backend_api/tests/test_customer_label_waders_session120_human_gold.py backend_api/tests/test_customer_label_waders_step4_gold.py backend_api/tests/test_customer_label_waders_step2_gating.py backend_api/tests/test_specific_issue.py backend_api/tests/test_customer_label_phase6_validation.py backend_api/tests/test_export_customer_label_phase5.py backend_api/tests/test_customer_label_50u_readiness.py backend_api/tests/test_outdoor_waders_taxonomy.py -q` PASS（100 passed in 6.51s）；`python3 scripts/customer_label_v2_waders_shadow_replay.py` PASS，artifact `tmp/5.9.9-step3-verifier-safety-gate/waders-shadow-summary.json`，waders P0=0，六个重点标签 FP/FN=0；未 production upload / reanalysis / DB write / credit / LLM。 |
| 2026-07-30 | **5.9.9 Step 2 LLM evidence-first shadow run PASS**。新增本地 v2 shadow runner、deterministic verifier 雏形、focused tests 与 waders replay artifact；默认 `mock-v1-display-replay`，未调用真实 LLM。 | 新增 `backend_api/app/services/customer_label_v2_shadow.py`、`backend_api/tests/test_customer_label_v2_shadow.py`、`scripts/customer_label_v2_waders_shadow_replay.py`、`docs/5.9.9-step2-llm-evidence-first-shadow-run.md`。验证：`python3 -m pytest backend_api/tests/test_customer_label_v2_shadow.py -q` PASS（10 passed）；目标回归 `python3 -m pytest backend_api/tests/test_customer_label_v2_shadow.py backend_api/tests/test_customer_label_waders_session121_blind_regression.py backend_api/tests/test_customer_label_waders_session120_human_gold.py backend_api/tests/test_customer_label_waders_step4_gold.py backend_api/tests/test_customer_label_waders_step2_gating.py backend_api/tests/test_specific_issue.py backend_api/tests/test_customer_label_phase6_validation.py backend_api/tests/test_export_customer_label_phase5.py backend_api/tests/test_customer_label_50u_readiness.py backend_api/tests/test_outdoor_waders_taxonomy.py -q` PASS（92 passed in 6.20s）；`python3 scripts/customer_label_v2_waders_shadow_replay.py` PASS，artifact `tmp/5.9.9-step2-customer-label-v2-shadow-run/waders-shadow-summary.json`，waders P0=0；`git diff --check` PASS；未 production upload / reanalysis / DB write / credit / LLM。 |
| 2026-07-30 | **5.9.8 Step 4 session122 postdeploy PASS**。session122 生产完整验收先发现 `water_leaks_through` P0=2：旧/他牌 `other neoprene waders ... leak` 污染当前产品漏水、`They do not keep you dry.` 漏召回。窄修复 commit `c38e7ff` push `origin/develop` 后触发生产部署，Erika 确认 GitHub Actions/生产查看全绿；Codex 追加生产 health check 与 production DB 只读 replay，确认 Top10、单条评论明细、raw review download、single-tag download 四条路径 P0=0，frontstage 无 evidence false、cluster propagated、旧产品/他牌/配件漏水污染。 | Step 4 已在 `PROGRESS_V2.md` 改为 PASS，并进入 `5.9.9 Customer Label System v2 Step 1`。部署后 artifact：`tmp/5.9.8-step4-tidewe-waders-prod-20260729/session122-readonly/session122-postdeploy-readonly-acceptance-audit.json`；报告：`docs/5.9.8-step4-tidewe-waders-session122-blind-acceptance-report.md`；Step 1 契约文档：`docs/5.9.9-customer-label-v2-contract.md`。 |
| 2026-07-28 | **50U-T1 production write-path smoke STOP after worker `done`**。生产写路径 smoke 在 worker 完成后触发停止条件：存在已处理但未形成完整结构化分析的评论，且 usage 记录模型名口径不符合预期。 | 本地修复已准备但未部署/未 push：exhausted LLM fallback 改写结构化非缓存分析错误，不回填全局缓存；content-hash cache 读取排除该类 fallback；LLM usage 改记录真实模型 ID。精确 job/session/cost/counter 保留在私有本地记录。新的生产写路径验证需 Erika 另行授权。 |
| 2026-07-28 | **50U-T1 production upload 500 before job creation**。production write-path smoke 在 preflight 通过后，上传入口返回 500，且未创建 upload job；事后只读对账确认业务写入、credit、LLM、analytics 与全局缓存均无变化。 | 根因定位为生产 API DB session 处于 read-only 状态；已通过容器环境配置修复并复核。未自动重试上传，需 Erika 重新 GO 才能继续 50U-T1；精确 trace、计数和环境细节保留在私有本地记录。 |
| 2026-07-08 | **Credit History drawer 被 Workspace 页面盖住 bug**（sidebar 点 Upgrade → 升级套餐弹窗 → 点底部「查看消费记录」→ Credit History drawer 出现在 Workspace 主内容之下，无法交互）。根因：[frontend/src/components/credit/credit-ledger-drawer.tsx](frontend/src/components/credit/credit-ledger-drawer.tsx) 是 inline 渲染（不走 portal），挂载在 `Sidebar` 的 `<aside class="fixed left-0 top-0">` 内。`position:fixed` 会创建独立的 stacking context，导致 drawer 的 `z-50` 只在 sidebar 内部生效，无法压过后面 DOM sibling 里带 `backdrop-blur` 的 workspace 主内容（`backdrop-filter` 也会创建 stacking context）。参考 `UpgradePricingDialog` 走 Radix `DialogPortal` 就没此问题。 | Portal 到 `document.body`：新增 `import { createPortal } from "react-dom"`，`return (...)` 改为 `return createPortal(..., document.body)`；加 SSR 守卫 `if (typeof document === "undefined") return null`（避免 Next.js SSR 阶段 `document` 未定义）；backdrop `z-40` → `z-[100]`、drawer `z-50` → `z-[110]`（抬升 z 数值兜底确保盖过任何 `z-50` 元素）。**已本地 tsc 通过**；**Prod 验证通过**（commit `66b8254`，2026-07-08 Playwright MCP session 92 复测）：① 视觉——drawer 完整覆盖 Workspace 主内容，backdrop 半透明遮罩正常，无穿透（截图 `credit-drawer-verification.png`）。② 结构——DOM 挂载在 `document.body` 下（`drawerParentTag=BODY`），drawer `z-index=110`、backdrop `z-index=100`，portal 生效。③ 交互——点击 backdrop 关闭（`drawerStillOpen=false`）；列表加载 Insight/Export/Top-up/Monthly grant 等条目。 |
| 2026-07-08 | **[export/full] Content-Disposition latin-1 编码 500 bug**（M2-2.2.C 验收过程暴露的 pre-existing bug，跟本次 slug 改造无关）。`GET /analysis/sessions/{id}/export/full` 返回 500 Internal Server Error。api 容器 traceback 关键行：`File "starlette/responses.py", line 61, in init_headers ... UnicodeEncodeError: 'latin-1' codec can't encode characters in position 31-32`。根因：[backend_api/app/routes/export.py:75](backend_api/app/routes/export.py#L75) 把 `exporter._build_filename()` 生成的中文文件名（`产品编号-版本-全部-分析结果-20260708.xlsx`，含"分析结果"四个中文）直接塞进 `Content-Disposition: attachment; filename="..."` header value，starlette 用 latin-1 编码 header 时炸。filename 生成逻辑早期就是这样，此前没暴露可能是英文用户从没点过这个原始评论导出按钮。 | RFC 5987 encoding：新增 `from urllib.parse import quote` import，`Content-Disposition` 中的 `filename="{filename}"` 改为 `filename*=UTF-8''{quote(filename)}`，Chrome / Firefox / Safari / Edge 全支持 UTF-8 编码文件名。只改 `/export/full` line 75（`/export` line 48 的 filename 是 pure ASCII `analysis_{id}_{module}.xlsx`，本次不动，避免范围蔓延）。**部署后待验证**：EN + ZH 两种 locale 各点一次原始评论下载按钮，均需 200 OK 且下载文件名可正确显示。 |
| 2026-07-08 | **V4-M2-2.2.C 类别标签 i18n 化**（非 bug，出海化 feature）。`comments.category` 字段一直存 11 个中文分类名，导致英文用户导出的 Excel「Category」列全是中文，分析结果对英文用户不可用。同时 M4-pre 阶段已建的 `messages/{zh,en}.json` `categoryLabels` 命名空间是死代码（key 都是中文）。 | 7 处改动 + 1 migration all-in-one：① [backend_api/app/services/category_grouper.py](backend_api/app/services/category_grouper.py) 顶部新增 `CATEGORY_SLUGS`(11 tuple) + `CATEGORY_ZH_LABELS`(slug→中文 map)，`ASPECT_TO_CATEGORY` / `_derive_category` / `aspects_to_legacy_schema` fallback 全部改英文 slug。② [workers/jobs.py:472](workers/jobs.py#L472) error 分支 `"无效乱码"` → `"invalid_garbage"`。③ [review_analyzer/analyzer.py](review_analyzer/analyzer.py) SYSTEM_PROMPT 分类规则改 `slug（中文名）` 双语格式 + 输出格式 JSON 枚举改 slug 列表 + `VALID_CATEGORIES` 改 slug set + `_validate_result` fallback + `_make_unrecognizable` + `PROMPT_VERSION` v2.1→v2.2。④ 新建 [migrations/047_categories_to_slug.sql](migrations/047_categories_to_slug.sql) 11 条幂等 UPDATE（原计划 046 已被占用改用 047）。⑤ [frontend/messages/{en,zh}.json](frontend/messages/en.json) `categoryLabels` 段 11 个 key 全改 slug。⑥ [frontend/src/components/analysis/download-tag-button.tsx](frontend/src/components/analysis/download-tag-button.tsx) 引入 `useTranslations('categoryLabels')`；[review_analyzer/exporter.py](review_analyzer/exporter.py) 新增 `_category_zh(slug)` helper。⑦ [backend_api/tests/test_category_grouper.py](backend_api/tests/test_category_grouper.py) 9 case 断言全改 slug + 新增 `CATEGORY_SLUGS` 白名单 snapshot（**10/10 通过**）。**验证**：本地 `python3 backend_api/tests/test_category_grouper.py` 10/10 ✅、`npx tsc --noEmit` 通过 ✅。**部署顺序**：先跑 migration 047（psycopg2 python 脚本，ECS api 容器无 psql）→ 再重建 api/worker/frontend + nginx reload。 |
| 2026-07-07 | **V4-出海-M4-pre LLM 路由 locale 切换**（非 bug，海外化 feature）。原 `llm_router.py` 只有一条固定 MODELS 链（DeepSeek → OpenAI → Qwen），海外用户拿到的分析结果也是 DeepSeek 主，海外化后需要按用户 locale 换主链路：en 用户 GPT-4o-mini 主（英文能力 + 品牌信任），zh 用户仍 DeepSeek 主。同时 `review_analyzer/insight_engine.py` 硬编码 `OpenAI(base_url="deepseek.com")` 直调 DeepSeek，绕过了整个 router 熔断/fallback / user_id BYOK 逻辑；前端 `defaultLocale` 也还是 `"zh"`，不利于海外获客。**统一英文 prompt**（评论源就是英文，英文 prompt 分析效果最好，跟用什么模型无关），前端展示层再翻译，避免维护双 prompt | 8 处改动 all-in-one 落地：① `llm_router.py` `LLMRouter.completion()` + `router_completion()` 加 `locale` 参数，`_models_for_locale()` 按 locale 返回不同链；`__post_init__` 种子所有可能模型的 `_CircuitState` 避免运行时 KeyError；`status()` 汇总 EN+ZH 两条链状态。② 新建 `backend_api/app/services/locale.py::get_analysis_locale(request)`：`?locale=` > cookie `NEXT_LOCALE` > `Accept-Language` > 默认 `"en"`，`_normalize()` 处理 `en-US`/`zh-CN`/`en-US,zh;q=0.9` 各种形态。③ `backend_api/app/routes/uploads.py` `/uploads` + `/analysis/jobs` 注入 `Request` 参数，写入 `payload_json["locale"]`。④ `workers/jobs.py::process_upload_job` 从 `payload_json` 取 locale（默认 `"en"`），透传给 3 处 `deep_analyze_batch()`。⑤ `backend_api/app/services/deep_analyzer.py` `analyze_one` / `analyze_batch` 加 `locale` 参数（默认 `"en"`）传给 `router_completion()`。⑥ `review_analyzer/insight_engine.py` 删掉硬编码 OpenAI 直连，改走 `router_completion(locale=...)`；两个内部函数 + 两个公共函数（`build_results_insights` / `build_compare_insights`）签名加 `locale` 参数。⑦ `frontend/src/i18n/routing.ts` `defaultLocale: "zh"` → `"en"`（海外优先，配合 middleware/cookie 检测）。⑧ `frontend/messages/{en,zh}.json` 新增 `categoryLabels` 段，11 个中文分类的英文翻译（产品质量→Product Quality / 包装物流→Packaging & Logistics / 使用体验→Usage Experience / 客服售后→Customer Service / 性价比→Value for Money / 功能需求→Feature Request / 正面反馈→Positive Feedback / 单纯好评→Praise Only / 无效乱码→Invalid Content / 混合评价→Mixed Review / 其他→Other）。**向后兼容**：所有新参数都有默认值（llm_router 保 `"zh"`、其它保 `"en"`），旧调用点不改也能跑。**验证**：`_models_for_locale("en") == [openai, deepseek, qwen]`、`_models_for_locale("zh") == [deepseek, openai, qwen]` ✅；`get_analysis_locale` 单测 5 case（en/en-US/zh-CN/多 tag/未知→默认）✅；`pytest backend_api/tests/ --ignore=test_v24_dynamic_aspects.py` 60 通过 ✅；en/zh categoryLabels key 集合一致 ✅。**待线上验证**：以 en cookie 上传评论 → prod 日志 `model_used=gpt-4o-mini` |
| 2026-07-07 | **V4-T4 Step 7 跨用户 LLM 分析结果复用**（非 bug，成本优化 feature）。原 L1 缓存 `get_analyzed_by_content_hash` 只查用户自己历史 comments，用户 A、B、C 上传相同 ASIN 或相同评论文本时仍会重复调用 DeepSeek，浪费 API 成本。基建其实早已就绪：`review_pool` 全局表（migration 038）无 user_id + 已有 `aspects_json` + `analyzer_version` 字段，`pool_backfill_analysis()` 函数已实现，但接线被两处门禁堵住：① L1 lookup 只查 comments 不查 pool；② pool 回填被 `source_channel == "api"` 挡住，CSV 上传不入池。**未处理会持续冒 API 冤枉钱**：热门 ASIN 场景（多卖家竞品共同关注）100% 评论重叠仍会全额扣 DeepSeek 调用 | migration 043 加两项：`review_pool.content_hash` 部分索引（analyzed_at IS NOT NULL 才索引，大幅缩小体积）+ `comments.cache_hit_source VARCHAR(20)`（'user' \| 'global' \| NULL 区分命中来源，供 llm_usage_log 统计"跨用户节约成本"指标）。`review_analyzer/database.py::get_analyzed_by_content_hash` 新增 `include_global=True` + `analyzer_version` 参数：先查用户自己历史，未命中的 hash 再查全局 pool（用 `analyzer_version = %s` 兜底防止老版本结果污染当前分析）；`update_comment_analysis` 写入 `cache_hit_source` 列。`workers/jobs.py` 三处改：① L1 lookup 传 `include_global=True, analyzer_version=ANALYZER_VERSION`；② `cache_hit_source` 透传写入 comments；③ 拆掉 `source_channel == "api"` 门禁，改判 `product_id` 非空即回填（CSV 上传也参与池贡献）。隐私条款 `frontend/src/app/privacy/page.tsx` 新增第四条"分析结果聚合复用"（中英双语），服务条款 `terms/page.tsx` 第四条追加对应说明并指向隐私协议第四条。计费影响：无（quota 仍在上传时按条数扣，缓存命中不影响用户额度，符合"用户付的是分析输出，不是每次 DeepSeek 调用"的产品定义）。单元测试 `backend_api/tests/test_global_cache.py`：用户命中/全局命中/user 屏蔽 pool/空输入/`include_global=False` 关闭全局路径/content_hash 稳定性 6 个用例。py_compile 全绿。**已知限制**：无 product_id 的自由 CSV 不回填（避免跨产品污染池）。**待验证**：Erika 部署 develop 后用两个测试账号上传同一 CSV，观察 worker 日志 `analysis_cache: L1=N` + `cache_hit_source='global'` |
| 2026-07-07 | **V4-T4 Step 7 跨用户缓存 pool_backfill_analysis 回填失败 bug**。migration 043 + 全局缓存逻辑已部署，但线上验证发现第二个账号上传相同 CSV 时 `cache_hit_source` 全为 NULL。诊断：第一次上传的 content_hash 在 review_pool 中匹配数为 0，第一次分析结果根本未写入 pool。根因：`workers/jobs.py:656`（修复前）调用 `pool_backfill_analysis` 时传入的是 `unprocessed`（从 DB 查出的原始评论，`sentiment=NULL`、`aspects_json=NULL`），导致 `review_pool.py:200` 的检查 `if not sentiment and not aspects_json: continue` 跳过所有行，pool 始终为空，全局缓存永远无法命中 | 修复 `workers/jobs.py:659-670`：调用前将 `unprocessed`（有 `content_hash`）和 `results`（有分析结果）合并成 `backfill_data`，每项含 `{content_hash, sentiment, aspects_json}`，再传给 `pool_backfill_analysis`。commit `2b552c0`。**待验证**：两个不同账号先后上传完全相同的 CSV，第二次评论 `cache_hit_source = 'global'` + worker 日志显示 L1 全局命中 |
| 2026-07-07 | **V4-出海-M3.5 数据保留策略自动清理落地**（非 bug，M3 收官 feature）。之前只有 M3.2 的"用户主动删账号 → anonymize_user"，没有"长期 inactive 用户自动清理" + "删除账号 60 天后硬删关联业务数据" + "老数据软删/硬删按类型分级"的自动化。**未处理会踩合规红线**：CCPA/CPRA/GDPR 明确���求"不能无限期保留",Shulex 已按 6y 通用 + 60d 删除窗口在做,ClueAI 需对齐 | 6 块清理串行 job，UTC+8 03:23 由 scheduler 触发（业务低峰、避开 09:07 成本日报）+ Redis 锁 `scheduler:retention_cleanup:lock:{YYYY-MM-DD}` 保证同一日历日只入队 1 次。清理顺序：Block1 inactive 6m + 未通知 → 发预告 + 打时间戳（单次 500 条上限、send-first-mark-after）；Block2 已通知 90d 未登录 → 复用 M3.2 `anonymize_user()`（500 条上限）；Block3 `deleted_at > 60d` → 硬删 6 张业务表（review_trackers → action_items → comments → product_variants → products → sessions 按 FK 叶子→根顺序，不动 `review_pool`，200 用户/天上限）；Block4 `analytics_events > 90d` 硬删；Block5 `llm_usage_log > 6y` 硬删；Block6 `sessions/comments > 6y AND deleted_at IS NULL` 软删（等未来冷存储再做物理清理）。窗口对齐 Shulex：通用 6y + 删除后 60d + `analytics_events` 90d + `llm_usage_log` 6y；差异化亮点：inactivity 6m + 90d（Shulex 无）。每块独立 try/except + 单独 commit，一块炸不影响其他；返回 `{ok, blocks, errors, started_at, finished_at}` 结构化统计供飞书运维日报。auth.py login 加 `mark_user_login()`（DB 写失败不阻塞登录）。落地文件：`migrations/042_add_inactivity_tracking.sql` + `workers/retention_cleanup.py`（新建）+ `workers/periodic_jobs.py` `enqueue_retention_cleanup()`（`job_timeout=30min`、`result_ttl=7d`、`failure_ttl=30d`）+ `workers/scheduler.py` 03:23 触发 + `workers/tests/test_retention_cleanup.py` 每块至少 1 用例 + SQL 关键词哨兵防误改窗口。**冷热分层缓冲方案**记录为未来备用：单表 >5000 万行 / p95 >200ms / 存储超预算 30% 任一命中时启动，老数据 dump S3/OSS，本次不实施 |
| 2026-07-05 | **SG 服务器 `deploy/.env` 中 `DATABASE_URL` 末尾写成 `/pos>` 导致 `scan_stale_jobs` 定时任务每 5 分钟报 `DatabaseConnectionUnavailable`**。`urlparse` 解析 db path 为 `/pos>`，比正确值 `/postgres` 少 4 字符（`tgres` 被 `>` 替换），推测是初次配置 `.env` 时 shell 重定向符 `>` 误入字符串。主分析链路（B 场景）未受影响，因 Supabase transaction pooler (6543) 对非法 db 名在 session 层容忍路由；而 `scan_stale_jobs` 走 `psycopg2.pool.ThreadedConnectionPool` 初始化 startup packet，触发严格 db 校验。两端（api + worker 容器）均读到同一坏 URL，`dig` + `docker compose exec` 诊断确认。HK 老服务器不受影响（DATABASE_URL 已在 HK 修复过） | `cp .env .env.bak.20260704 && sed -i 's\|:6543/pos>\|:6543/postgres\|' .env`，用 `:6543` 做锚点精准替换，自动备份。然后 `docker compose up -d --force-recreate worker api scheduler && docker compose exec nginx nginx -s reload` 重建 3 容器（不重建镜像）。验证：90 秒观察窗口 worker 日志无 stale 报错；`psycopg2.connect` 直连返回 `SUCCESS: ('postgres', 'postgres')`；B 场景 7 tab 全渲染 |
| 2026-07-05 | **服务器迁移 HK（阿里云 8.210.51.242）→ SG（AWS Lightsail 13.215.29.99）**。Anthropic Bedrock + OpenAI Chat Completions 从 HK ECS 出口被 API 层 geo-block 拒绝（2026-07-03 实测，出口 IP `8.210.51.242` 触发 `403 unsupported_country_region_territory`）；SG 无此问题，且出海合规更完整。迁移 4 阶段：Phase 2a 服务器初始化、2b SSL + .env 部署、2c 全容器起活、3 hosts 验证（B 场景端到端通过）、3b Cloudflare DNS 切换（4 条 A 记录 root/www/app/api 全指 13.215.29.99，Proxied 模式）。过程中发现并修复 `.env` `DATABASE_URL` 末尾 `/pos>` bug（见上条记录）。**顺带发现 2 个 pre-existing bug**（HK 时代就有，跟迁移无关，已记录待修）：① `generate_embeddings_batch` 在 SG 也偶发失败跳过（非 fatal）；② `push_snapshots` 表未建，导致 `_post_analysis_smart_push` 报 `UndefinedTable` | Phase 0-3b 全部完成：4 域名公网 HTTPS 200，B 场景真实公网路径（Cloudflare → SG）端到端验证通过，worker stale scan 稳定运行 3.5+ 小时无报错。进入 Phase 4 观察窗口（3-7 天，到 2026-07-12 前），HK ECS 保留在线但不接流量 |
| 2026-07-03 | **【实测结论】OpenAI Chat Completions 在生产 HK ECS 被 API 层 geo-block 拒绝**。运行 `scripts/diagnose_openai_chat.py`（等价的 heredoc 版）在生产 HK ECS 的 api 容器内直调 `gpt-4o-mini`，出口 IP 为阿里云 HK IDC `8.210.51.242`，OpenAI 返回官方错误码 `403 unsupported_country_region_territory` + `type: request_forbidden` + `message: Country, region, or territory not supported`。这不是账号/配额/网络问题 —— 是 OpenAI 在 API 层用 official error code 明确拒绝 HK IP。**关键推论**：OpenAI 对不同 endpoint 有独立地区策略 —— `/v1/embeddings` 在 HK 生产已跑 3 周稳定（`review_analyzer/rag.py`），但 `/v1/chat/completions` 直接 403。因 llm_router 里 DeepSeek 主链路一直稳定从未熔断到 OpenAI，这个 fallback 分支实际是死代码，之前无从发现。**同日 Anthropic Claude Haiku 4.5 via AWS Bedrock 也确认 API 层 geo-block（`unsupported countries` ValidationException）**。→ 结论：**V4-出海模块 LLM 主链路调整（OpenAI/Anthropic 任一 provider）必须以 ECS 迁移到 SG/US IP 为硬前提**。DeepSeek/Qwen 走国内 IDC 不受影响，现状可维持 | ① 修订 line 51（原 line 49，2026-06-18）"OpenAI 直连可达" 加限定词 "**Embedding** 直连可达（Chat Completions endpoint 尚未在生产实测，仅 embedding 端点验证过）"；② 补充"验证过程 + 关键教训"—— 跨端点推断可用性是危险的（embedding 通 ≠ chat 通），涉及主链路 provider 切换必须实测，不接受 "网络层可达" 的间接证据；③ 新建 `scripts/diagnose_openai_chat.py` 一次性诊断脚本（打印出口 IP + 完整错误码 + 自动识别 4 类失败模式），未来若切 SG/US 后可重跑复验；④ 从本地 `review_analyzer/.env` 删除 AWS_BEDROCK_* 三行（避免误提交，AWS IAM 侧 AK 保留 30 天待观察）；⑤ 更新 `PROGRESS_V2.md` V4-出海模块，把"OpenAI/Anthropic 集成"的前置条件明确改为"ECS 迁移到 SG/US 完成后"；⑥ 待 Erika 拍板 SG 迁移方案（Lightsail SG $40/mo vs OpenRouter 中转 +5-10% 加价）|
| 2026-07-03 | V4-出海模块讨论 LLM 路由主备顺序调整时，参考了原 line 49（2026-06-18）的记录 "生产环境（香港 ECS）不设此变量，OpenAI 直连可达"，据此推断"OpenAI Chat 在生产 HK 稳定跑 3 周"，进而险些直接调换 `llm_router.py` 里 DeepSeek/OpenAI 主备顺序。Erika 及时指出：生产 OpenAI 一直**只用于 embedding**，Chat Completions endpoint 从未被真实生产流量触发（llm_router 里 OpenAI 是备 1，DeepSeek 主链路一直稳定，未熔断过）| 澄清：① 修订原记录，把 "OpenAI 直连可达" 加限定词 "**Embedding** 直连可达（Chat Completions endpoint 尚未在生产实测，仅 embedding 端点验证过）"；② 新建 `scripts/diagnose_openai_chat.py`（一次性诊断），从生产 HK ECS 上跑一次 `gpt-4o-mini` chat completion，出口 IP + latency + 错误码全打印，专门识别 403 unsupported country / 429 geo-block 关键词。**教训**：跨端点推断可用性（embedding 通 ≠ chat 通）是危险的，不同 endpoint 可能有独立 policy 判断，涉及主链路切换的决策必须实测，不接受 "网络层可达" 的间接证据。**后续更新**：见上一条 2026-07-03 记录，实测已确认 geo-block 属实 |
| 2026-07-03 | 测试账号（[REDACTED_PROD_USERNAME]）上传 `data.xlsx`（产品编号 `BG015-PN-US-01`，一级"户外运动"/二级"户外背包"）触发 `POST /uploads` 500，前端仅显示 `Request failed with status 500.`。DB 中 `upload_jobs` 无对应记录。ECS api 日志 traceback：`psycopg2.errors.UndefinedColumn: column "source_channel" of relation "upload_jobs" does not exist` at `review_analyzer/database.py:368` create_upload_job INSERT。两次报错时间 `02/Jul/2026 08:46:10 / 09:28:55 UTC` | 根因：生产库 `upload_jobs` 表缺 `source_channel` 列，migration `017_add_source_channel.sql` 从未在生产执行；代码 `create_upload_job` 的 try/UndefinedColumn fallback 未生效（推测 ECS 镜像里的 database.py 早于 06-17 提交 `2a5dc58` 加入 fallback 的时间点）。修复：ECS api 容器内补跑 migration 017 —— `ALTER TABLE upload_jobs / comments ADD COLUMN IF NOT EXISTS source_channel TEXT NOT NULL DEFAULT 'manual'` + `CREATE INDEX IF NOT EXISTS idx_comments_source_channel`。幂等 DDL，历史 45 条 upload_jobs 自动补 default `manual`。验证：`information_schema.columns` 查询确认 `source_channel` 已存在。无需 nginx reload、无需重建镜像 |
| 2026-07-03 | 服务条款 `terms/page.tsx:24` 承诺"预警通知（飞书/钉钉/企业微信 Webhook）"，但代码仅实装飞书，构成虚假宣传合规风险 | **B2 方案（补实装）**：1) `review_analyzer/notifier.py` 重构为 platform 分发架构：新增 `send_text_notification(platform, url, text, secret)` 统一入口 + 飞书/钉钉/企业微信各自 body 构造 + 三家签名机制（飞书 body 加签、钉钉 URL query 加签、企业微信免签）；富文本 `send_rich_push` 新增 `platform` 参数，飞书走 post 富文本、钉钉/企业微信共用一份 markdown 渲染器（`_build_markdown_rich`）。旧 `send_feishu_notification` / `send_notification` 保留兼容。2) 用户面 schema `backend_api/app/schemas/settings.py` + `routes/settings.py` 新增 `webhook_platform` 字段（feishu/dingtalk/wechat，默认 feishu，历史数据自动落 feishu），`test-webhook` 路由读取并透传 platform；`PATCH /settings` 改为 merge 更新（不再整包覆写 push_settings 里的 periodic_push/dept_contacts）。3) 运维告警：`backend_api/app/services/budget_guard.py` 的 `_send_feishu_alert` 重命名 `_send_ops_alert`，`workers/periodic_jobs.py` 的 stale 告警和 daily cost digest 全部走 `send_text_notification`；新增可选环境变量 `OPS_WEBHOOK_PLATFORM`（默认 feishu）+ `OPS_WEBHOOK_SECRET`，`FEISHU_OPS_WEBHOOK` 变量名保留但语义升级为通用运维 URL；`taxonomy_coverage_monitor.format_feishu_alert` 重命名 `format_ops_alert`，`workers/jobs.py` 的 taxonomy 告警读取用户 `webhook_platform` 字段。4) 前端 `lib/api/types.ts` 新增 `WebhookPlatform` 类型 + `SettingsResponse.webhook_platform` + `SettingsUpdatePayload.webhookPlatform`；`lib/api/browser.ts` 的 `saveSettings` / `testWebhook` 透传 platform；`components/settings/push-settings-panel.tsx` 新增平台下拉 + 按平台动态切换 section 标题/URL placeholder/secret 提示/联系人 hint（企业微信隐藏 secret 输入框；钉钉/企业微信 disable 部门 open_id 输入）；`components/settings/settings-panel.tsx` 兼容修复类型。**限制说明**：钉钉/企业微信群机器人只支持文本级 @all，不能精准 @ 联系人（Open ID 是飞书专属），前端 UI 已 disable 对应输入。**验证**：ruff check 通过、npm run typecheck 通过、py_compile 全绿 |
| 2026-07-02 | 问评论页面 4 个示例问题（差评原因/质量最好/最常提到的优点/共同质量问题）在真实数据上全部返回"没有在当前评论中找到足够相关的内容"。根因：`review_analyzer/rag.py:answer_question` 是纯检索型 RAG，只取 Top-K 5 条评论喂给 LLM，而这些示例问题都是"最常/共同"类聚合统计问题，5 条评论根本给不出统计结论；system prompt 又强制"证据不足要明确说明"，退回到 fallback | **P0 重构：意图路由 + 结构化聚合**。1) 新建 `review_analyzer/aggregations.py` 提取 `top_tags`/`pick_representative_reviews`/`pick_citations_by_tags` 公共原语（含 TypedDict），`compare_store.py` 复用同一模块避免重复。2) 新建 `review_analyzer/qa_intent.py` 规则版意图分类器：7 个 intent（aggregate_feedback/product_compare/rating_breakdown/consumer_insight/trend_and_emerging/specific_retrieval/unanswerable），4 个示例问题分别命中 aggregate_feedback×2 + product_compare×2，未命中默认 specific_retrieval（等同旧流程，永不阻塞）。3) 新建 `review_analyzer/qa_handlers.py` 3 个 P0 handler：`aggregate_feedback_handler`（top_tags 骨架 + 代表评论 → LLM 强制列 Top 3-5 项 + 占比 + 引用）、`product_compare_handler`（按 product_id 分组聚合 → 表格式对比）、`retrieval_handler`（封装现有 hybrid 检索作 fallback）。4) 重构 `rag.py:answer_question` 只做意图路由，返回体新增 `intent`/`aggregation_snapshot` 字段。5) `backend_api/app/routes/qa.py` 传 `products_meta=selected_rows` 给 answer_question，把 intent/snapshot 塞进响应并存入 `qa_messages`。6) migration `039_qa_intent_columns.sql` 加 `intent TEXT` + `aggregation_snapshot JSONB` 两列。7) 前端 `qa-chat-area.tsx` 新增意图徽章（聚合分析/跨产品对比/检索证据/…）+ retrieval_method 中文化。**Smoke 验证**：4 条示例问题全部产出结构化答案（Top-N 标签 + 占比 + [n] 引用 + 可行动建议），retrieval_method 分别显示 `aggregation`/`compare`。ruff + tsc 通过 |
| 2026-07-01 | 分析结果页翻译后"下载原文"和"加入行动"按钮消失；"加入行动"按钮需 hover 才显示 | 根因：ModuleCard 翻译模式用 TranslatedView 完全替换 children，导致 TagTable 中的 DownloadTagButton / InlineActionButton 丢失；按钮设有 `opacity-0 group-hover:opacity-100`。修复：① TranslatedView 接收 comments/sessionId/showAction/locale 并在每行渲染对应按钮；② 提取 DownloadTagButton 为独立文件避免循环依赖；③ 移除 InlineActionButton 的 hover 隐藏样式改为常显。commit `4477aee` |
| 2026-06-30 | AliExpress 评论抓取全部返回 0 条（三次修复迭代）：1) feedback API 被反爬封锁；2) Apify 接入后产品 ID 被 maxLength=15 截断（16位ID被截为15位）；3) Apify run-sync 端点返回 HTTP 201，代码只接受 200 导致数据被丢弃 | 1) 接入 Apify CrowdPull 作为主数据源（commit `c97ae74`）；2) 前端 maxLength 从 15 改为 16、后端正则 `\d{12,15}` 改为 `\d{12,16}`（commit `9b1bc0a`）；3) `_fetch_via_apify` 状态码检查改为 `in (200, 201)`（commit `5f4b5e6`）。线上验证：product ID 1005009259589970 成功抓取 131 条评论，完整分析结果正常渲染（session_id=75，好评率82.4%，差评率17.6%） |
| 2026-06-30 | AliExpress 产品编码抓取后分析结果页显示空白卡片，刷新后也无分析结果。用户体验：无进度条、无错误提示、无法判断任务状态 | 根因双 bug：1) 后端设 status="fetching" 但前端 UploadJob.status 类型缺少 "fetching"，polling panel 条件分支全部不匹配渲染为空；2) 0 条评论时 status="done" + session_id=null，前端 `done && session_id` 条件不满足也不停轮询导致无限循环。修复：types.ts 补 "fetching" 状态 + 重写 polling panel 新增四步横向进度条（排队→拉取→分析→完成）、"未找到评论"空结果提示（含原因说明+操作按钮）、60s 超时提醒、网络中断自动重试。commit `88ca2d5` |
| 2026-06-30 | ASIN 监控页面线上 500 错误 + 定时抓取依赖付费 Rainforest API | 1) 500 错误根因：生产数据库缺少 `asin_watchlist` 表（migration 018 未执行），在 ECS api 容器内执行建表 SQL 修复；2) 定时调度器 `workers/asin_scheduler.py` 从 Rainforest API (`fetch_reviews_by_asin`) 切换为 woot.com 免费源 (`fetch_reviews`)，零 API 成本实现自动监控。线上验证：监控页面正常加载，显示空列表+配额信息 |
| 2026-06-30 | ASIN 评论抓取数量不足（Rainforest API 免费版仅返回 ~13 条 top_reviews，`type=reviews` 返回 503）。ScrapingDog lite plan `/amazon/reviews` 端点返回 400（Amazon auth wall），不可用 | 用 woot.com 免费 AJAX API 替代 Rainforest 的评论抓取：新建 `woot_scraper.py`（遍历 5 星级×2 排序=10 组合，每组合最多 5 页，`(content[:80], reviewer)` 去重，2 年截断）+ `review_scraper.py` 统一入口 + `workers/jobs.py` 替换调用。保留 Rainforest 的产品信息/变体功能。线上验证：ASIN B0DB4GRPYZ 从 ~13 条提升到 45 条，session_id=74 分析结果完整渲染（好评率 44.4%，差评率 55.6%，评分 3.1/5，用户画像+标签表正常） |
| 2026-06-30 | 产品管理页删除按钮无效：点击确认删除后产品仍存在。根因：`product_store.py` 的 `delete_product()` 在清理 FK 关联时执行 `UPDATE push_snapshots SET product_id = NULL`，但 `push_snapshots` 表未建（migration 016 未应用），`psycopg2.errors.UndefinedTable` 异常导致整个事务回滚，FastAPI 返回 500 Internal Server Error，前端 catch 块静默吞错无用户反馈 | 新增 `_safe_execute()` 辅助函数：用 PostgreSQL SAVEPOINT 包裹每条 FK 清理 SQL，`UndefinedTable` 异常时 ROLLBACK TO SAVEPOINT 跳过该表，不影响后续语句和最终 DELETE。同样处理 `issue_escalation_state`（也未建表）。前端 catch 块补充 `console.error` 便于调试。线上验证：DELETE /api/products/11 返回 204，产品列表已移除 |
| 2026-06-30 | 产品详情页 `/products/[id]` 线上 500 报错（Digest: 1582326665）。根因：PostgreSQL NUMERIC 类型字段 `rating` 序列化为字符串 `"4.5"`，前端 Server Component 中 `rating.toFixed(1)` 对字符串调用失败（String.prototype 无 toFixed 方法），导致 SSR 渲染崩溃 | 将 `product.rating as number \| null` 改为 `product.rating != null ? Number(product.rating) : null`，显式转为数字后再调用 `.toFixed()`。commit `43993fc` |
| 2026-06-29 | 产品管理列表页 `/products` 线上 500 报错（Digest: 4292725916）。根因：`ProductCard` 组件（Server Component）中外层 `<Link>` 嵌套内层 `<Link>`（"查看分析"按钮），HTML 规范不允许 `<a>` 嵌套 `<a>`，Next.js 15 SSR 渲染时抛出异常。本地 build 不报错（静态分析不执行渲染），但运行时 SSR 必崩 | 移除嵌套 Link，改为静态 `<span>` badge 标识"有分析"。用户点击整张卡片进入详情页后再跳转分析结果。commit `09d466e` |
| 2026-06-29 | ASIN 抓取评论后分析结果页全部为空（0 条评论、0% 好评/差评、无用户画像）。根因：Rainforest API 返回日期为 `{"raw": "Reviewed in ... on March 5, 2023", "utc": "2023-03-05T00:00:00.000Z"}`，之前 `_parse_review` 直接存 raw 文本，SQL `date <= '2026-06-29'` 对文本做字典序比较全部排除；加上 session 没有 date_range，`_resolve_range` 兜底到 30 天窗口进一步导致零结果 | 三处修复：1) `rainforest.py` 新增 `_extract_iso_date()` 优先取 utc 字段转 ISO 日期；2) `analysis.py /results` 传 session_id 给 get_comments 精确匹配；3) `_resolve_range` 当 session 存在但日期无法解析时返回不过滤（靠 session_id 兜底）。commit `cf9ed06` |
| 2026-06-29 | 分析结果页 Aesthetics 标签代表性评论不准（含聚类传播的无关评论）。三次迭代：1) 首版只检查 cluster_propagated 标志 → 对旧数据无效；2) 增加 evidence_span ∈ content 验证 → Pass 1 因大小写不匹配（Title Case vs snake_case）永远为空；3) 归一化 tagKey 为 lowercase+underscore 后修复 | 前端 `hasAspectEvidence()` + 后端 `_has_aspect_evidence()` 两处同步修复：normalize(`tagKey.toLowerCase().replace(/[\s_]+/g, "_")`) 与 `aspects[].key` 比较 + 验证 evidence_span 在正文中存在 + 排除 cluster_propagated 评论。commit `00b83b9` → `04f0d5a` → `65709ff`。验证结论：session 69 无聚类传播评论（0/193），显示结果不变是正常的；修复对未来有传播的 session 生效 |
| 2026-06-29 | 测试账号套餐额度始终显示 0/10000 不变化。根因：1) commit e122eba 前 worker 从未调用 quota_consume；2) 修复后未执行新分析故 used 仍为 0；3) qa/copywriter/export 三个路由完全缺失 quota_check + quota_consume | 1) quota_consume 加 amount<=0 防御性早返回；2) qa.py 的 ask_reviews + send_message 接入 quota_check/consume(ask_review)；3) copywriter.py generate 接入 quota_check/consume(ad_copy)；4) export.py 两个导出端点接入 quota_check/consume(excel_export)；5) 提供回填 SQL 按月汇总 sessions.total_reviews 写入 user_quota_usage |
| 2026-06-29 | 聚合视图（range=all）下模块 XLSX 下载按钮点击无反应。根因：聚合视图 URL 没有 session_id，前端 sessionId=0，请求 `/api/analysis/sessions/0/export` 返回 404，catch 块静默吞错 | ModuleCard 新增 `comments` prop；sessionId>0 走后端 API 下载，sessionId=0 时用已加载的 comments 数据在客户端通过 xlsx 库直接生成 TOP10 XLSX（逻辑与后端一致）。commit `258c943` |
| 2026-06-29 | 设置页面 4 项优化：1) API 密钥管理对用户无意义（后台已配置）；2) 系统设置作为 sidebar 导航项占位不合理；3) 缺少下载中心页面记录用户导出历史；4) 缺少团队管理方案规划 | 1) 删除 api-keys-panel.tsx + settings/api-keys/page.tsx；2) 系统设置改为 Dialog 弹窗（从用户下拉菜单触发），sidebar groupManage 不再包含系统设置入口；3) 新增下载中心全栈实现：后端 migration 030 + GET/POST /downloads API + 前端 /downloads 页面（表格+空状态+状态 badge）+ 现有导出自动记录；4) 团队管理可行性方案（Workspace 模型 + 4 角色 RBAC + 3 Phase 落地）写入 PROGRESS_V2.md |
| 2026-06-29 | 用户画像模块三大问题：1) Review Distribution 与上方汇总好评率/差评率重复；2) Core Audience Focus 中同一标签出现两次；3) Key Insight 模板句式逻辑自相矛盾；且整体内容与「消费动机」「未满足的需求」模块职责重叠 | 重构 consumer_profile 为纯人物画像（参考 Facebook Ads 核心受众模型）：三行改为 Demographics / Interests & Context / Purchase Behavior，只描述买家身份、使用场景和购买行为模式，不再包含产品好坏评价。新增三个 heuristic 函数从评论文本中提取关键词（身份角色、兴趣场景、行为模式），AI prompt 同步更新强制输出人物维度。前端无需改动（通用 label/detail 渲染），compare-dashboard fallback 兼容。ruff + typecheck 通过 |
| 2026-06-29 | 推送设置页面标题错误显示"系统设置"；产品级规则输入框为纯文本无法搜索；订阅计费和 API 密钥不应放在推送设置里；系统设置页缺乏实际内容 | 拆分 settings/layout.tsx 为纯结构壳 + 新建 push/layout.tsx（标题"推送设置"）；产品规则 Input 替换为 ProductSearchCombobox；新建系统设置页（/settings）含账户信息 + API 密钥 + 数据导出占位；订阅计费移入 QuotaDialog（Pro 用户显示"管理订阅"按钮）；侧边栏新增"系统设置"入口。typecheck + build 通过 |
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
| 2026-06-18 | 本地开发环境 embedding 代理方案优化：之前为解决代理导致全局请求卡死，一刀切清除了所有代理变量，导致 OpenAI embedding 在国内直连不通、batch失败后跳过、聚类优化失效、432条评论全部逐条走 LLM（本可优化为~150次） | 修复：`review_analyzer/rag.py` 的 `_get_embedding_client` 改为通过 `httpx.Client(proxy=...)` **单独**给 OpenAI embedding 客户端配代理（读取 `.env` 中的 `EMBEDDING_PROXY=http://127.0.0.1:7890`），不再依赖全局环境变量。DeepSeek LLM 和 Supabase DB 继续直连不受影响。生产环境（香港 ECS）不设此变量，OpenAI **Embedding** 直连可达（Chat Completions endpoint 尚未在生产实测，仅 embedding 端点验证过） |
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
| DB-2 | 数据库密码为弱密码（具体值已脱敏），且明文存于 [.env](.env)、[deploy/.env](deploy/.env)、[.streamlit/secrets.toml](.streamlit/secrets.toml) 三个文件 | 🔴 高 | 立即重置密码为 24 位随机串；检查 git 历史是否泄露过；同步更新三处文件（Step 2.0） |
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

---

### 2026-07-28 5.9.8 Step 2 TIDEWE waders Customer Issue / Customer Label display gating

| 日期 | 范围 | 命令 | 结果 | 结论 |
|------|------|------|------|------|
| 2026-07-28 | 后端 focused + 相关回归 | `python3 -m pytest backend_api/tests/test_customer_label_waders_step2_gating.py backend_api/tests/test_specific_issue.py backend_api/tests/test_customer_label_phase6_validation.py backend_api/tests/test_export_customer_label_phase5.py backend_api/tests/test_customer_label_50u_readiness.py -q` | PASS，65 passed in 1.58s | verified source-review gating 生效：无 evidence / cluster propagated / legacy fallback 不进入单条明细标签和 Top occurrence；no leaks / leak proof 不触发 `water_leaks_through`；phone case/pocket 漏水不归整体 waterproof；raw/full export 与 Top export 审计列一致。 |
| 2026-07-28 | 前端类型检查 | `npm run typecheck`（cwd=`frontend`） | PASS，`tsc --noEmit` | 前端 Customer Label parser、raw review XLSX、单标签下载、客户端 Top 聚合类型通过。 |
| 2026-07-28 | 安全边界 | 本地 pytest / typecheck only | PASS | 未调用生产业务 API，未上传生产数据，未触发生产重分析、credit 消耗或 LLM 成本。 |

---

### 2026-07-29 5.9.8 Step 3 TIDEWE waders 人工参与上传验证预检

| 日期 | 范围 | 命令 | 结果 | 结论 |
|------|------|------|------|------|
| 2026-07-29 | 只读预检 | `python3` + `openpyxl` 只读加载 `/Users/zhangxi/Desktop/TIDEWE-下水服-WD001-人工纠正标签.xlsx`；读取 `docs/5.9.8-step1-tidewe-waders-baseline.md`、Step 2 fixture/test | PASS；Excel `评论原文` 为 100 条评论、24 列；Step 1 29 条重点验收行已抽取 | 未调用生产业务 API，未上传生产数据，未触发生产重分析、credit 消耗或 LLM 成本。 |
| 2026-07-29 | 人工验收矩阵 | 文档整理 | PASS；生成 `docs/5.9.8-step3-tidewe-waders-human-acceptance-matrix.md` | 矩阵覆盖四件套扩散、无 evidence、cluster propagated、no leaks/leak proof/kept dry/stayed dry、phone case/pocket、未实际使用、泛泛好评、mixed review、aspect 冲突；当前等待 Erika 确认 `GO`。 |
| 2026-07-29 | 生产上传门禁 | 待 GO | PENDING | 若进入真实生产上传，执行前必须再次提醒会触发真实分析并消耗 credit/LLM，且等待 Erika 明确授权；上传后再补充截图/导出路径、异常样例和结论。 |
| 2026-07-29 | 生产上传 preflight | 生产 API/DB preflight；不带 execute | STOP；健康检查通过，本地上传样本已生成，但生产账号登录失败 | 未执行上传；未创建 job/session；未触发分析 credit、LLM 或 export credit。账号与原始 preflight 细节保留在私有本地记录。 |
| 2026-07-29 | 结果页验收 | 生产 DB 只读 + 本地等价导出；不调用上传/重分析/API export | `REVIEW_NEEDED`；重点验收行可定位；无 evidence/cluster propagated 展示门禁通过 | Step 2 展示 gating 硬门禁 PASS，但语义验收未通过：phone case、旧产品、no leaks 正向语境仍污染 `water_leaks_through`；`pocket_not_waterproof` 未正确召回；产出 `docs/5.9.8-step3-tidewe-waders-acceptance-report.md`。 |
| 2026-07-29 | 缓存风险复核 | 同上结果 + DB grouped usage | 证据确认存在缓存复用 | 因 content hash = `content + rating + category` 且不含 ASIN，同批评论换 ASIN 仍可能命中旧分析；本轮结果只能验当前线上展示/导出口径，不能作为干净新分析验收。 |
| 2026-07-29 | 删除后只读清理审计 | Erika 已手动删除本次产品及评论；Codex 做生产 DB 只读审计 | 用户侧 L1 已清干净；全局缓存仍存在复用风险 | 干净复测前需要 Erika 明确授权是否清理同批 content_hash 对应的全局已分析缓存。 |
| 2026-07-29 | review_pool 授权清缓存 | 生产 DB 限定范围清缓存；仅置空同批全局分析缓存字段，不删除评论源 | `CLEARED`；未上传、未调用生产分析 API、未触发 credit/LLM | 清理范围限定在 TIDEWE WD001 人工样本对应 content_hash；精确行数、ID 和审计 JSON 留在私有本地记录。 |
| 2026-07-29 | 清缓存后只读复核 | 生产 DB 只读复核 | 当前已满足干净重传前置条件 | 下一步必须由 Erika 手动在前端重传同一人工样本，并提供新结果页；该上传会真实消耗分析 credit 与 LLM 成本，Codex 不执行生产上传。 |
| 2026-07-29 | session 119 干净重传只读验收 | `python3 tmp/production_tidewe_waders_step3_runner.py --validate-session 119 --artifact-dir tmp/5.9.8-step3-tidewe-waders-prod-20260729/session119-readonly`；读取 Erika 提供的 `/Users/zhangxi/Desktop/TIDEWE-下水服-WD001-AGGREGATED-raw-reviews -0729.xlsx` | `REVIEW_NEEDED`；100/100 processed+analyzed；`comments.cache_hit_level/cache_hit_source/cache_source_id` 全空；`review_analyze=-100`；`review_pool` 仅回填同批 49 hash；Top/单标签无 propagated/unverified | 干净 L1 复测通过，但语义与导出一致性未过：`water_leaks_through` 仍包含 row 46 phone case、row 52 旧产品历史漏水、row 62 no-leaks 正向语境；`pocket_not_waterproof` 单标签 0 行；实际 raw 下载审计列有 issue propagated 9 行 / issue evidence false 10 行 / highlight propagated 44 行 / highlight evidence false 44 行，四件套 propagated/unverified 42 行。报告：`docs/5.9.8-step3-tidewe-waders-session119-acceptance-report.md`。 |

---

### 2026-07-29 5.9.8 Step 4 TIDEWE waders 标签漏标/错标主修复

| 日期 | 范围 | 命令 | 结果 | 结论 |
|------|------|------|------|------|
| 2026-07-29 | 人工标注 vs session119 下载对照 | `python3` + `openpyxl` 只读加载 `/Users/zhangxi/Desktop/TIDEWE-下水服-WD001-人工纠正标签.xlsx` 与 `/Users/zhangxi/Desktop/TIDEWE-下水服-WD001-AGGREGATED-raw-reviews -0729.xlsx` | PASS；人工标签列与 session119 当前输出可比对 | 前台最高频 FP：Issue `water_leaks_through` 6；前台最高频 FN：Issue `breaks_easily` 9、`inaccurate_size_chart` 7、Highlight `fits_as_expected` 20、`good_value_for_the_price` 18、`keeps_water_out` 16；audit 最高频 FP 为四件套 propagated/unverified。 |
| 2026-07-29 | 后端 Step 4 focused gold | `python3 -m pytest backend_api/tests/test_customer_label_waders_step4_gold.py -q` | PASS，3 passed in 0.89s | focused gold fixture 精确覆盖 phone case/pocket 漏水、旧产品历史漏水、no leaks 正向、真实小漏水召回、未实际使用、泛泛负评、cluster propagated/raw display 分离。 |
| 2026-07-29 | 后端 Step 2 + 相关回归 | `python3 -m pytest backend_api/tests/test_customer_label_waders_step4_gold.py backend_api/tests/test_customer_label_waders_step2_gating.py backend_api/tests/test_specific_issue.py backend_api/tests/test_customer_label_phase6_validation.py backend_api/tests/test_export_customer_label_phase5.py backend_api/tests/test_customer_label_50u_readiness.py backend_api/tests/test_outdoor_waders_taxonomy.py -q` | PASS，73 passed in 3.07s | Step 4 生成层修复未破坏 Step 2 展示 gating、通用 specific issue、Phase 5/6 export、50U readiness 与 outdoor/waders taxonomy 测试。 |
| 2026-07-29 | 前端 raw XLSX / parser 类型检查 | `npm run typecheck`（cwd=`frontend`） | PASS，`tsc --noEmit` | 前端 raw review XLSX display/audit 分列、Customer Label parser、下载口径类型通过。 |
| 2026-07-29 | diff whitespace 检查 | `git diff --check` | PASS | 本轮代码/文档 diff 无 whitespace error。 |
| 2026-07-29 | 安全边界 | 本地文件读取、pytest、typecheck only | PASS | 未执行生产上传，未删除生产数据，未清理 production review_pool，未触发 production LLM、credit 或 reanalysis。 |
| 2026-07-29 | session120 50 条盲测只读验收 | `python3 tmp/production_tidewe_waders_session120_readonly.py`；读取 Erika 下载 `/Users/zhangxi/Desktop/TIDEWE-下水服-WD001-session_id=120.xlsx` | `REVIEW_NEEDED`；生产 DB 50/50 processed+analyzed，47 无缓存、2 L1 global、1 L2；真实下载文件无 `Audit ...` 分列，issue evidence false 90 / issue cluster true 90 / highlight evidence false 24 / highlight cluster true 24 | 生产当前结果不能 PASS；本地追加修复 row 3/27/28/31 后重新只读回放 `validation.status=PASS`，但整体仍因 session120 cache 与线上下载旧口径保持 REVIEW_NEEDED。报告：`docs/5.9.8-step4-tidewe-waders-session120-acceptance-report.md`。 |
| 2026-07-29 | session120 追加 hard cases 回归 | `python3 -m pytest backend_api/tests/test_customer_label_waders_step4_gold.py backend_api/tests/test_customer_label_waders_step2_gating.py backend_api/tests/test_specific_issue.py backend_api/tests/test_customer_label_phase6_validation.py backend_api/tests/test_export_customer_label_phase5.py backend_api/tests/test_customer_label_50u_readiness.py backend_api/tests/test_outdoor_waders_taxonomy.py -q` | PASS，73 passed in 3.16s | 覆盖 `not yet tested...leakproof` 不触发 `keeps_water_out`、`boots got filled with water` 召回 `water_leaks_through`、`can't say whether or not they leak` 不触发 `water_leaks_through`、`Cheap and durable` 不触发 `feels_thin_and_flimsy`。 |
| 2026-07-29 | session120 人工 gold 效果对比 | 只读加载 Erika 已追加人工标注的 `/Users/zhangxi/Desktop/TIDEWE-下水服-WD001-session_id=120.xlsx`；对比 `download_raw_all`、`download_verified_only`、`local_latest_replay` 三组口径 | `REVIEW_NEEDED`；下载 raw 全量 both exact `1/50`，verified-only `3/50`，本地最新 replay `10/50`；本地 issue exact `37/50`、highlight exact `18/50`；`water_leaks_through` 人工 3 / 命中 3 / FP 0 | 本次修复对 P0 水漏边界有效，但整体仍未达到人工可用 PASS；下一轮应基于 session120 人工 gold 继续修 size/fit、气味、耐用、泛泛满意、性价比、外观、适用场景和储物亮点召回。报告：`docs/5.9.8-step4-tidewe-waders-session120-human-label-comparison.md`。 |
| 2026-07-29 | session120 Step 4.1 human gold fixture | `python3 -m pytest backend_api/tests/test_customer_label_waders_session120_human_gold.py -q` | PASS，7 passed in 3.87s | 新增 `backend_api/tests/fixtures/customer_label_waders_session120_human_gold.json`，覆盖 50 条人工 issue/highlight gold、本地当前输出、FP/FN、wrong aspect/evidence、证据定位、hard negative、cluster audit-only、raw/frontstage/Top/single-tag 口径一致。 |
| 2026-07-29 | session120 Step 4.1 后端目标回归 | `python3 -m pytest backend_api/tests/test_customer_label_waders_session120_human_gold.py backend_api/tests/test_customer_label_waders_step4_gold.py backend_api/tests/test_customer_label_waders_step2_gating.py backend_api/tests/test_specific_issue.py backend_api/tests/test_customer_label_phase6_validation.py backend_api/tests/test_export_customer_label_phase5.py backend_api/tests/test_customer_label_50u_readiness.py backend_api/tests/test_outdoor_waders_taxonomy.py -q` | PASS，80 passed in 11.52s | session120 human gold both exact set `50/50`、issue exact `50/50`、highlight exact `50/50`，issue TP/FP/FN `22/0/0`，highlight TP/FP/FN `49/0/0`；旧 Step2/Step4、通用 specific issue、Phase5/6、50U readiness、waders taxonomy 回归通过。 |
| 2026-07-29 | session120 Step 4.1 前端与 diff 验证 | `npm run typecheck`（cwd=`frontend`）；`git diff --check` | PASS，`tsc --noEmit`；PASS | 前端 Customer Label occurrence/parser context guard 类型通过；代码/fixture/文档 diff 无 whitespace error。 |

### 2026-07-30 5.9.8 Step 4 session121 CI/CD 勘误与 session122 生产下载纠正

| 日期 | 变更类型 | 描述 | 验证结果 |
|------|---------|------|---------|
| 2026-07-30 | 勘误 | session121 对应构建后续确认未成功通过 CI/CD 部署，因此先前基于 session121 的 production download 结论作废；真正的部署后生产下载改以 session122 `/Users/zhangxi/Desktop/TIDEWE-下水服-WD001-AGGREGATED-301-350.xlsx` 为准 | 下载结构 `download-file-audit.json` status=PASS，Raw Reviews 50 行 / 15 列、Label Audit 50 行 / 30 列；但完整验收 `session122-full-acceptance-audit.json` 为 `REVIEW_NEEDED`，生产 raw 前台 `water_leaks_through` P0=2：row 9 旧/他牌漏水污染，row 38 当前产品漏水漏召回。 |
| 2026-07-30 | session122 P0 窄修复回归 | `python3 -m pytest backend_api/tests/test_customer_label_waders_session121_blind_regression.py -q`；`python3 -m pytest backend_api/tests/test_customer_label_waders_step4_gold.py -q`；waders 目标回归 9 文件；`npm run typecheck`；`git diff --check` | PASS，`2 passed in 0.50s`；PASS，`3 passed in 1.65s`；PASS，`82 passed in 6.10s`；frontend typecheck PASS；diff check PASS。本地 post-fix session122 只读回放 `validation.status=PASS`，six single-tag equivalent exports PASS；仍需部署后重新生产下载验收。 |

---

### 2026-06-26 对比分析版本下拉框 + 产品列表同步修复

| 日期 | 变更类型 | 描述 | 验证结果 |
|------|---------|------|---------|
| 2026-06-26 | fix | 版本对比模式下版本下拉框只显示"全部版本"，无法选择 V1/V2；原因是读取 product_versions 目录表而非 sessions 实际版本。改为从 sessions.version 聚合 | tsc PASS, ruff PASS |
| 2026-06-26 | fix | 历史记录删除分析记录后对比分析页产品列表未同步；改为 compare-workspace 挂载时 client-side 重新获取产品列表 | tsc PASS, ruff PASS |

---

### 2026-06-29 分析结果页下载与显示优化

| 日期 | 变更类型 | 描述 | 验证结果 |
|------|---------|------|---------|
| 2026-06-29 | feat | 标签代表性评论下载扩展为 13 列完整分析格式（序号/评论内容/评分/日期/评论者/来源/情感/分类/优先级/分析理由/改进建议/问题标签/亮点标签） | tsc PASS, ruff PASS |
| 2026-06-29 | feat | 综合建议模块去掉 "Recommendation N" 标题，只保留序号圆圈 + 建议正文 | tsc PASS |
| 2026-06-29 | feat | 模块右上角下载按钮（用户体验/消费动机/未满足的需求/用户画像）输出改为 TOP10 格式（排名/标签/出现次数/提及占比/代表性评论前20条摘要） | tsc PASS, ruff PASS |
| 2026-06-29 | feat | 所有下载 Excel 表头支持 i18n（中文系统输出中文表头，英文系统输出英文表头） | tsc PASS, ruff PASS |
| 2026-06-29 | fix | ?session_id=N 直接访问分析结果页报错，需带 product_id 才能加载。根因：redirect() 在 try-catch 中被吞掉。修复：catch 中加 isRedirectError 判断重新抛出 | tsc PASS, 线上验证 PASS |

---

### 2026-06-29 产品管理删除 + 搜索下拉框修复

| 日期 | 变更类型 | 描述 | 验证结果 |
|------|---------|------|---------|
| 2026-06-29 | fix | 产品管理页删除产品无效。根因：delete_product() 中使用了不存在的表名 `actions`（正确为 `action_items`），导致 SQL 报错事务回滚；同时补充删除 variants 前清空 action_items/review_trackers 的 variant_id 外键引用 | ruff PASS |
| 2026-06-29 | fix | 分析结果页产品搜索下拉框显示已删除历史记录的产品（session_count=0）。修复：search 接口过滤掉 session_count=0 的产品 | ruff PASS |

---

### 2026-06-30 Golden Set 标签校准系统 + 管理员权限控制

| 日期 | 变更类型 | 描述 | 验证结果 |
|------|---------|------|---------|
| 2026-06-30 | feat | Golden Set 管理页 `/settings/golden-set`：4 张摘要卡片 + 准确率表格 + 标注记录表 + CSV 上传 + few-shot 切换 | tsc PASS, 线上验证 PASS |
| 2026-06-30 | feat | 管理员权限控制：users.is_admin 字段 + /me API 返回 is_admin + sidebar adminOnly 过滤 + 页面级权限守卫（非管理员 redirect 到 /workspace） | tsc PASS, 线上验证 PASS |
| 2026-06-30 | feat | golden_set 后端：CSV 上传（中英文表头兼容）+ 条目查询 + 准确率统计 + few-shot 切换 API | ruff PASS |
| 2026-06-30 | feat | Prompt 注入：few-shot 示例从 golden_set 自动注入分析 prompt + taxonomy boundary_note 渲染 | ruff PASS |
| 2026-06-30 | feat | AliExpress 评论抓取集成：双数据源（feedback API + Playwright 浏览器 fallback）、平台切换 UI（Amazon/AliExpress 分段控件）、产品管理页平台 Tab 过滤 + badge、移除非英文 Amazon 站点 | ruff PASS, tsc PASS, 线上验证 PASS |

---

### 2026-06-30 全品类 Taxonomy 批量扩展

| 日期 | 变更类型 | 描述 | 验证结果 |
|------|---------|------|---------|
| 2026-06-30 | feat | 新增 5 品类 27 子品类 taxonomy YAML：outdoor(冲锋衣/帐篷/登山鞋/睡袋/户外背包/钓鱼竿)、beauty(面霜/洗面奶/防晒霜/口红/洗发水/电动牙刷)、kitchen(不粘锅/刀具套装/保温杯/空气炸锅/收纳盒)、automotive(车载充电器/行车记录仪/座椅套/遮阳挡/车载吸尘器)、office(办公椅/显示器支架/桌面收纳/打印机墨盒/鼠标垫) | HIT 验证全部通过 |
| 2026-06-30 | feat | category_aspect_taxonomy 表结构重建（migration 037）：旧schema(category/aspect/level) → 新schema(sub_category/aspect_key/label_zh/boundary_note/统计字段)；1501 条全部入库 | import OK |
| 2026-06-30 | feat | sub_category_categories.json 扩展至 87 子品类；docs/类目标签覆盖表.md 产出 | - |

---

### 2026-07-01 跨用户评论源数据缓存池（review_pool）

| 日期 | 变更类型 | 描述 | 验证结果 |
|------|---------|------|---------|
| 2026-07-01 | feat | review_pool + review_pool_meta 表：全局共享抓取结果缓存，(platform, product_key, marketplace, content_hash) 唯一约束去重 | migration 038 执行 OK |
| 2026-07-01 | feat | review_pool.py 服务模块：pool_lookup/pool_write/pool_backfill_analysis，抓取前查缓存命中则跳过第三方 API | ruff PASS, import OK |
| 2026-07-01 | feat | process_asin_fetch_job 池拦截：缓存命中跳过 scraper，miss 后写入池；分析完成回填 sentiment/aspects_json | ruff PASS |
| 2026-07-01 | feat | max_reviews=100 免费额度限制 + force_refresh 强制刷新参数透传 | schema 验证 OK |

---

### 2026-07-01 eBay 评论抓取修复

| 日期 | 变更类型 | 描述 | 验证结果 |
|------|---------|------|---------|
| 2026-07-01 | fix | shopee_scraper.py 未提交导致线上 ModuleNotFoundError — 所有平台抓取全部失败 | 部署后恢复 |
| 2026-07-01 | fix | eBay Apify Actor ebayProductUrls 传参格式错误：纯字符串→对象 {"url": ...}，旧格式返回 400 静默空结果；同时添加 proxyConfiguration + sortReviewsBy=RELEVANCE | 本地测试成功获取 10 条评论 |

---

### 2026-07-06 P2 级预存 Bug 修复

| 日期 | 变更类型 | 描述 | 验证结果 |
|------|---------|------|---------|
| 2026-07-06 | fix | P2-A: generate_embeddings_batch 捕获异常时仅打 "skipping" 无根因信息，改为打印完整异常 + base_url/model/key_source，方便排查 SG 服务器缺 key 或网络不通 | ruff PASS |
| 2026-07-06 | fix | P2-A: rag.py 模块加载时检查 EMBEDDING_API_KEY/OPENAI_API_KEY 均为空则打 WARNING，提示管理员配置 | ruff PASS |
| 2026-07-06 | fix | P2-B: push_snapshots + issue_escalation_state 表缺 migration 导致 _post_analysis_smart_push 抛 UndefinedTable — 新建 migrations/041_push_snapshots.sql；UNIQUE NULLS NOT DISTINCT 保证 product_id=NULL 时 upsert 正常 | migration 语法验证 OK |
| 2026-07-06 | fix | P2-C: DashScope `text-embedding-v3` 官方 batch 上限 10，`review_analyzer/rag.py:90` 常量 `EMBEDDING_BATCH_SIZE=256` 一直触发 `400 InvalidParameter batch size is invalid`。之前用 OpenAI（上限 2048）时能跑，切 DashScope 后被 P2-A 之前的静默 exception handler 吞掉，导致生产 pgvector `product_embeddings/review_embeddings` 长期未生效。改为 `EMBEDDING_BATCH_SIZE=10`，注释标注官方硬上限来源 | 本地 grep 定位单点，改动仅一行常量 |
| 2026-07-06 | fix | P2-D: `workers/Dockerfile` 未 COPY `scripts/`，`workers/jobs.py:779,823`、`workers/periodic_jobs.py:164,174`、`backend_api/app/services/action_advisor.py:75` 5 处 `from scripts.aspect_taxonomy import get_aspect_label_zh` 在容器内 `ModuleNotFoundError`。方案 C：迁移 `scripts/aspect_taxonomy.py` → `review_analyzer/aspect_taxonomy.py`（属于共享分析业务字典，归属更合理），同步改 5 处 import；`scripts/` 保留纯运维脚本目录，不进 prod 镜像 | 本地 grep `scripts.aspect_taxonomy` 5 处引用全部改完，运行时目录（workers/backend_api/review_analyzer）无残留 |
| 2026-07-06 | fix | P2-E: embedding provider 从 DashScope（`text-embedding-v3` 1024 维）回退到 OpenAI（`text-embedding-3-small` 1536 维），与 `comments.embedding vector(1536)` 列一致。合规动机：目标市场为排除 EU/UK/EEA 的全球英语市场，DashScope 中国境内不满足 GDPR/CCPA 子处理商披露要求；技术动机：pgvector 列维度固化，1024 维写入抛 `DataException`。改动仅 `.env` 三变量 `EMBEDDING_API_BASE_URL/EMBEDDING_MODEL/EMBEDDING_API_KEY`，零 migration | 线上验证：新分析 embedded/total = 30/30，pgvector 列写入成功 |
| 2026-07-06 | fix | P2-F: `workers/jobs.py:206`（embed_session_comments 调用点）和 `workers/jobs.py:384`（update_comment_cluster 调用点）两处 `except Exception: pass` 继续吞掉上冒的 pgvector `DataException`，让 P2-A 详化的 rag 日志功亏一篑。改为 `logger.exception(...)` 输出完整堆栈 + user_id / session_id / comment_id 上下文；`review_analyzer/rag.py:90` 常量注释同步更新为 OpenAI 上限来源 | 线上验证：worker 日志无 `DataException` 静默吞噬，无新增 exception traceback |
| 2026-07-06 | verify | 【线上验证】P2-A/B/C/D/E/F 6 连修全部通过：① Step 6 worker 日志无 `embed/error/dimension/InvalidParameter/ModuleNot` 相关错误；② Step 7 数据库 `SELECT COUNT(*) FILTER (WHERE embedding IS NOT NULL), COUNT(*) FROM comments WHERE session_id=<new>` 结果 = (30, 30)；③ Step 8 网页 `问评论` 提问 "What do customers say about waterproof?"，返回 5 条引用 + 检索标签为 **混合检索**（`retrieval_method=hybrid`），vector 检索确认激活 | ✅ 3 项全通过 |

---

### 2026-07-07 analyze_batch locale 参数缺失修复

| 日期 | 变更类型 | 描述 | 验证结果 |
|------|---------|------|---------|
| 2026-07-07 | fix | `workers/jobs.py` 已上线并向 `deep_analyze_batch()` 传递 `locale=locale`，但 `deep_analyzer.py` / `llm_router.py` 未同步更新函数签名，导致生产所有分析任务抛 `TypeError: analyze_batch() got an unexpected keyword argument 'locale'`。修复：`analyze_one` / `analyze_batch` 新增 `locale` 参数并透传给 `router_completion`；`llm_router.router_completion` / `LLMRouter.completion` 同步新增 `locale`，并引入 `MODELS_EN`（GPT-4o-mini 优先）/ `MODELS_ZH`（DeepSeek 优先）双链路 | 待部署后线上验证 |

### 2026-07-08 V4-出海-M2.2.L 法律五页 locale 完全切换

| 日期 | 变更类型 | 描述 | 验证结果 |
|------|---------|------|---------|
| 2026-07-08 | feat | 参考 Shulex 方案，五个法律页（terms/privacy/refund/cookies/dpa）从并排中英双列改为 next-intl locale 单语切换。文案抽到 `messages/{zh,en}.json` `legal.*` 命名空间（`paragraph`/`bullets`/`ordered` 三段类型 + 4-tag 富文本 marker `<b>` / `<mail>` / `<link>` / `<ext>`）。新建 `frontend/src/components/legal/legal-article.tsx` server component + 五个 `page.tsx` 统一 `async` + `getTranslations` + `generateMetadata`。cookies 补 6 段 GDPR/CCPA/PIPL 合规分析，dpa 补 12 段 GDPR Art. 28 + SCC 2021/914 Module 2 + UK IDTA 全文 | ✅ 本地 tsc + build 通过；Playwright MCP 双 locale E2E：/privacy /terms /refund /cookies /dpa 五页 zh/en 各验证一次，语言切换器 `aria-label="切换语言"` 菜单 中文/English 切换正常，5 en 页均无 CJK 污染 |
| 2026-07-08 | bug-发现 | 所有 marketing 页（法律五页 + pricing）`<title>` 出现 `X \| ClueAI \| ClueAI` 重复：`app/layout.tsx` 定义 `title.template: "%s \| ClueAI"` 会自动追加 " \| ClueAI"，但各 `page.tsx` 的 `buildMarketingMetadata({ title })` 已经手写了 " \| ClueAI"，两处叠加。属项目历史约定不一致，非本次任务引入的回归。Erika 决定新开会话独立修复，本任务不改 | 记录待办 |

---

### 2026-08-06 5.9.6-B.1 缓存语义版本化与 L2 下线

| 日期 | 变更类型 | 描述 | 验证结果 |
|------|---------|------|---------|
| 2026-08-06 | fix | Bug 1（PROGRESS 补充项 1）：L1 缓存命中校验仅检查静态 `ANALYZER_VERSION="v4_deep"`，从不随 prompt/taxonomy/registry/model 变更而失效。修复：`database.py` `get_analyzed_by_content_hash()` 新增 `prompt_version` / `taxonomy_version` / `registry_version` / `model_name` 四个参数，通过 `aspects_json->>'字段'` JSONB 操作符在 SQL 层过滤；`workers/jobs.py` 写入方面 `aspects_json` 同步补全三个新字段（`prompt_version` 已存在）；`taxonomy_loader.py` 新增 `get_taxonomy_version()` 函数按 sub_category 查 `category_aspect_taxonomy.taxonomy_version`。改动范围：`analysis_cache.py` + `database.py` + `workers/jobs.py` + `taxonomy_loader.py`。无需 migration（复用已有 JSONB 列） | ruff PASS；55 现有测试 + 14 新测试全绿 |
| 2026-08-06 | fix | Bug 2（PROGRESS 补充项 2）：删除 L2 短文本默认结果分支。`analysis_cache._check_l2()` 对 ≤10 字 + 评分 1-2/5 的评论跳过 LLM 直接给空 aspect + 默认 sentiment 结果，与 5.9.3 证据门冲突（如 `"Leaks."` 6 字 1 星含明确产品问题信号但系统未读原文即产出标签）。修复：删除 `_check_l2()` 函数 + `L2_MAX_CONTENT_LENGTH` 常量 + `apply_cache` 中 L2 调用 + `CacheResult.stats()` L2 计数 + `_cache_observability_summary()` 中 `short_text_rating_rule` 来源。`apply_cache` 链路从 L1→L2→L3 简化为 L1→L3 | ruff PASS；14 新测试覆盖 L2 不存在 + short text 应进 miss |
| 2026-08-06 | verify | 【测试】`test_cache_semantic_versioning.py`（14 tests）：SQL 版本过滤构造验证 × 5（四版本全传含 ->> / 不传不含 / 单参数单过滤 / pool 查询也含过滤 / 向后兼容）、L2 已删除验证 × 4（函数/常量不存在 / Leaks miss / stats 无 L2 / 链 L1→L3）、observability × 2（无 short_text_rating_rule / miss reason）、taxonomy 解析 × 2（fallback / empty）、向后兼容 × 1。全部 PASS | ✅ 14/14 |
| 2026-08-06 | verify | 【回归】`test_global_cache.py`（10 tests）+ `test_observability_p3_metrics.py`（3 tests）+ `test_v5t3_e2e.py`（8 tests）+ `test_v5t3_phase1.py`（20 tests）= 41 个现有测试全绿 | ✅ 41/41 |

---

### 2026-08-06 CI 修复（commit ca9042c 后 ci-gate 失败）

| 日期 | 变更类型 | 描述 | 验证结果 |
|------|---------|------|---------|
| 2026-08-06 | fix | `ci-gate / backend-lint` 失败（ruff 3 errors）：① `test_cache_semantic_versioning.py` F401 `unittest.mock.ANY` 导入未使用 + I001 import 块未排序；② `workers/jobs.py:1339` I001 函数内延迟导入顺序错误，`backend_api.app.services.action_advisor` 排在 `backend_api.app.core.aspect_taxonomy` 之前。修复：删除未用的 `ANY`；将 `core.aspect_taxonomy` 提到 `services.action_advisor` 之前 | `ruff check backend_api/ workers/ review_analyzer/ scripts/` → All checks passed! |
| 2026-08-06 | fix | `ci-gate / backend-import-check` 失败（`ModuleNotFoundError: No module named 'yaml'`）：`review_fragment_label_catalog.py:23` 引入 `yaml`，但 `requirements.txt` 未声明该依赖，CI 走 `pip install -r requirements.txt` 装不到。修复：`requirements.txt` 补 `PyYAML>=6.0.0`。影响范围：仅依赖声明，无代码逻辑变更 | `from backend_api.app.main import app` → OK；`from workers.jobs import process_upload_job` → OK |
| 2026-08-06 | verify | 【回归】`test_cache_semantic_versioning.py` 14 tests 全绿（确认删除 `ANY` 未破坏断言） | ✅ 14/14 |

---

### 2026-08-07 Label Registry Review 并入 Label Calibration + 权限收紧

| 日期 | 变更类型 | 描述 | 验证结果 |
|------|---------|------|---------|
| 2026-08-07 | feat | `/settings/label-review` 收进 `/settings/golden-set` 做 tab 排版（Tab 1: Golden Set + Tab 2: Registry Review）；旧 URL 改 server redirect | frontend tsc PASS; next build PASS |
| 2026-08-07 | security | `backend_api/app/routes/label_review.py` 两个 endpoint 权限从 `get_current_user` 收紧为 `get_admin_user`（仅 admin 可调） | ruff PASS; pytest 2 new 403 tests PASS |
| 2026-08-07 | verify | 【回归】全量 backend test suite：459 passed, 11 pre-existing failures（无关联） | ✅ 459/470 |
| 2026-08-07 | verify | 【回归】frontend next build PASS，无新增 error/warning | ✅ |
| 2026-08-07 | verify | 【线上-admin】`erikazz@foxmail.com`（`is_admin: true`）验证 8 项：侧边栏「标签校准」可见 → `/settings/golden-set`；H1 + 两 tab 中文 i18n 正确；Tab 1 数据 24 条/15 标签/15 行准确率表/24 行标注记录；Tab 2 四状态筛选 + Reviewer Note 渲染；筛选 `pending`→`applied` 重新拉取无报错；旧 URL `/settings/label-review` redirect 到 golden-set；4 接口全 200（proposals/summary/stats/entries）；console 0 error | ✅ 8/8 |
| 2026-08-07 | verify | 【线上-非 admin】`erikazzsw@gmail.com`（`/api/me` 实测 `is_admin: false`，pro plan）验证 5 项，走真实 `get_admin_user` DB 查询而非 mock：`GET /proposals` → 403 `Admin access required.`；`POST /review` → 403 同上；侧边栏「标签校准」+「可观测性」两个 adminOnly 项均不可见；直访 `/settings/golden-set` → 前端守卫 redirect `/workspace`；旧 URL `/settings/label-review` → golden-set → 守卫 → `/workspace` 两跳链完整。补齐本地 2 个 mock 测试未覆盖的真实 DB 权限路径 | ✅ 5/5 |
| 2026-08-07 | verify | 【线上】migration 060 两张表存在性：Erika 报告已在 clueai-dev + prod 执行；`/proposals` 返回 `200 {"proposals":[],"total":0}` 与「表存在且为空」一致（注：`query_proposals` 用 `except Exception: return []` 兜异常，空数组本身不能单独证明表存在，故以 Erika 的执行报告为准） | ✅ |

---

### 2026-08-07 5.9.6-D WP9 验收裁决返修（4 batch · 7 bugs + P0 gate + reflux 修复 · 10 文档修正）

| 日期 | 变更类型 | 描述 | 验证结果 |
|------|---------|------|---------|
| 2026-08-07 | fix | Bug 1 (P0): 空 taxonomy 索引时 Gate 3 静默放行 — 新增 `SCOPE_UNAVAILABLE` 枚举，Gate 3 拆为 3a/3b，空索引拒绝全部 9 个 label | 56 tests PASS; validate_label_scope.py --dry-run 0 failures |
| 2026-08-07 | fix | Bug 0-3: taxonomy 启动自检 — `assert_taxonomy_index_healthy()` + /health 暴露索引状态 | ruff PASS; test_taxonomy_index_count_assertion PASS |
| 2026-08-07 | fix | Bug 3: proposal 查询只用 limit=1 → `get_proposal_by_id()` 精确查询 | ruff PASS; label_review route 路径验证 |
| 2026-08-07 | fix | Bug 4: merge 禁用返回 501 (决策 q: registry 变更走 PR workflow) | ruff PASS |
| 2026-08-07 | fix | Bug 5/6: ContextVar 替代 module-level list 解决并发 shadow diff 混合问题 | ruff PASS; 无并发测试但语义正确 |
| 2026-08-07 | fix | Bug 5b: reflux pipeline — `generate_label_proposals.py` 从 audit events 聚合候选 proposal | script 语法 OK; --help 输出正确 |
| 2026-08-07 | verify | 【回归】全量 catalog tests：56 passed | ✅ 56/56 |
| 2026-08-07 | verify | validate_label_scope.py --dry-run：0 failures, scope matrix unchanged 89/89/89/89/5/5/16/1/1 | ✅ |
| 2026-08-07 | verify | ruff check 全量修改文件：All checks passed! | ✅ |
| 2026-08-07 | verify | 【线上】部署后 7 项验证（测试账号 `erikazz@foxmail.com`）：① `/api/health` → `{"taxonomy_index":"healthy","taxonomy_index_detail":"89 sub_categories"}` — 启动自检生效且可观测（部署前该字段不存在）；② `GET /proposals?status=all` → 200 `{"proposals":[],"total":0}`；③ `POST /review` `{proposal_id:1, action:"merge"}` → 404 `Proposal 1 not found.` — 先查存在性再判 action，`get_proposal_by_id()` 精确查询已生效（Bug 3 修复已验证）；④ `/settings/golden-set` 两 Tab 正常渲染（Golden Set 24 条/15 标签 + 标签注册表审核）；⑤ Registry Review tab 四状态筛选按钮 + Reviewer Note textarea + `No pending proposals found.` 空态；⑥ 旧 URL `/settings/label-review` → `/settings/golden-set` redirect；⑦ console 0 error / 0 warning | ✅ 7/7 |

### 2026-08-07 5.9.7 小样本验收（45 条评论 · 离线 resolver 验证）

| 日期 | 变更类型 | 描述 | 验证结果 |
|------|---------|------|---------|
| 2026-08-07 | verify | Scope gating: 45 条评论 × 9 标签 = 405 次 resolve，360 次 in-scope/out-of-scope 判定全部与 taxonomy aspect 匹配 | ✅ 0 scope 级别错标 |
| 2026-08-07 | verify | scope_unavailable=0：离线验收中 0 次触发 scope_unavailable，确认 Bug 1 修复效果 | ✅ |
| 2026-08-07 | verify | 跨类目负例：上衣/床架 两个不同 taxonomy profile（30 条）确认 capability_derived 标签正确拒绝 | ✅ 165 out_of_scope 全部正确 |
| 2026-08-07 | verify | Alias 解析：16/16 别名正确解析到 canonical key，含跨 scope 拒绝验证 | ✅ |
| 2026-08-07 | verify | Metadata：registry_version=5.9.6-D.1、review_status=pending、formal_module 路由正确、boundary_note 一致 | ✅ |
| 2026-08-07 | verify | Waders 配件标签：accessory_leak/missing_accessory scope=1（仅 waders），生效正确；15 条评论覆盖，不降级 | ✅ |
| 2026-08-07 | finding | **⚠️ 原"证据门禁缺失"P0 已撤回（2026-08-07 修正）**：离线脚本无条件调全部 label key 造成假象；生产 TOP10 门禁已通过 `_is_frontstage_countable_occurrence` 校验 evidence + cluster_propagated + evidence_span，无证据标签不进 TOP10。**真实发现：cluster 传播污染** — waders 96% occurrence 的 evidence_span 不出现在对应评论原文中（来自 cluster 0 代表 id=479 传播），TOP10 被掏空（漏标）。案例 id=508（真实漏水投诉）拿到反向证据、漏标 `water_leaks_through`。 | ⚠️ 阻塞 5.9.7 剩余出口条件，需关传播重新分析 |
| 2026-08-07 | verify | 离线脚本硬约束遵守：① 5 个 capability_derived 标签 effective_scope 启动断言 ✅；② 同一 resolver 入口 + approved_only=True ✅；③ 无 shadow 依赖 ✅ | ✅ |
| 2026-08-07 | doc | 产出 `docs/5.9.7-small-sample-acceptance-report.md`（45 条逐条判定 + scope/证据/alias/metadata/waders 5 维分析） | ✅ |
| 2026-08-07 | fix | **5.9.7-T2: cluster 传播污染修复 — 评分守卫**。`propagate_cluster_results()` 新增 rating guard：成员与代表评分绝对差值 ≥ 2.0 时不传播 aspects/pain_points/highlights，退回 needs_llm。模块级常量 `RATING_GUARD_THRESHOLD=2.0`，可通过 `CLUSTER_RATING_GUARD_ENABLED=false` 全局关闭或 `CLUSTER_RATING_GUARD_THRESHOLD` 调整阈值。新增 14 个 focused tests（`test_clustering_rating_guard.py`）覆盖：好评代表+差评成员不传播、同档评分正常传播、代表缺失、阈值边界、守卫关闭、多簇独立、与 similarity gate 交互。回归：481 passed / 0 新增失败；ruff 通过。 | ✅ |
| 2026-08-07 | estimate | 成本影响估算（clueai-dev waders cluster 0: 78 成员，rep=479 rating=5）：阈值 2.0 下 9/78（11.5%）被评分守卫拦截退回 needs_llm，69/78 仍通过传播节省 LLM。全局影响：生产全库传播 20.2%，传播证据污染率 99.3%，修复后 LLM 调用预估增加 ~10-15%（约 20% 的传播成员 x ~50% 聚合类目受影响）。**修复只对新分析生效，DB 已有脏数据不变**。 | ✅ |
