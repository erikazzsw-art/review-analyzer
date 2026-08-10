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

## 2026-07-15

### Bug 修复：GitHub Actions CD 自动部署管道打通（3 个根因串联）

- **工作量**: S（1 个 workflow 文件改动 + secret 配置 + 3 轮触发验证，约 0.5 人天）
- **状态**: ✅ CD 全绿，自动部署链路（Validate Secrets → SSH → Deploy → Health Check）端到端打通

**需求描述**：
GitHub Actions CD 管道（push develop / workflow_dispatch 触发自动部署到阿里云 ECS）连环报错无法完成一次成功部署，修复后打通自动化部署。

修复内容：
- **根因 1（Missing secrets）**：workflow 引用 4 个独立 secret（`ECS_HOST`/`ECS_USER`/`ECS_SSH_KEY`/`ECS_DEPLOY_PATH`），此前只配了一个 `Clueai_CD` → Erika 补齐 4 个 Repository secret。
- **根因 2（Permission denied publickey，exit 255）**：`ECS_SSH_KEY` secret 粘贴时 PEM 换行/尾行被破坏 → Configure SSH 步骤写 key 由 `echo` 改为 `printf '%s\n'` 保证尾部换行（commit `4add680`）+ Erika 重新粘贴 secret。
- **根因 3（health check 5 次全败 + 误回滚，exit 1）**：健康检查用 `curl`/`wget`，但 api 是精简 Python 镜像、frontend 是 node 镜像，容器内无这两个工具 → 改用容器原生运行时：API 用 `python urllib`、frontend 用 `node http`（commit `4a20370`）。

**涉及岗位及工时**：
- DevOps：0.5 人天（诊断 3 个根因 + workflow 修复 + secret 配置指导 + 3 轮触发验证）

**安全事件**：排查中私钥曾被误粘贴到终端（zsh 逐行执行 PEM 行），泄露仅限本地 scrollback + `~/.zsh_history`，未进 git/远程，Erika 已清除。

### 新功能：Chrome 扩展 Step 16 — 多市场（UK/CA）+ UI 双语 + 登录校验 + Web Store 上架材料

- **工作量**: M（扩展前端 5 文件改动 + 后端复用 + 新增打包脚本/测试/上架材料，约 2 人天）
- **状态**: ✅ 代码全部完成 + 本地测试通过（人工上架步骤待 Erika 执行）

**需求描述**：
Chrome 扩展（ClueAI ReviewLens）出海阻塞项 Step 16，让扩展支持英国/加拿大站点、界面中英双语、扩展内识别 ClueAI 登录状态，并准备好 Chrome Web Store 上架所需的全套材料。

实现内容：
- **多市场（UK/CA）**：核实 `chrome-extension/manifest.json`（host_permissions / content_scripts / web_accessible_resources）及 `content.js` MARKETPLACE_MAP、`background.js` MARKETPLACE_TLD_MAP 均已覆盖 co.uk/.ca；UK/CA 英文日期由 `parseDateToISO` 正确解析。新增 `chrome-extension/tests/multimarket.test.js`（7 项：结构覆盖 + 日期/marketplace 解析，全绿）
- **i18n 双语 UI**：新增 `chrome-extension/i18n.js`（zh-CN/en-US 消息字典 + `{param}` 插值 + locale 持久化）；`popup.html` 加 `data-i18n` 标签、语言切换按钮、登录状态区；`popup.js` 全量改用 `I18N.t()`，切换语言实时重渲染，首次按浏览器语言自动选择
- **登录校验（Cookie 透传）**：实际系统为 httponly session cookie（非 OAuth），扩展 `credentials:'include'` 自动带 cookie；`background.js` 新增 `CHECK_LOGIN` handler（`GET /me`）+ 抽出 `getApiBaseUrl()` 复用；popup 三态登录指示灯（绿/橙/灰）
- **Web Store 上架**：`scripts/build_extension_zip.sh`（allowlist 打包，产出 36K zip）；`docs/chrome-web-store-submission.md`（中英文案 / 隐私政策 / 权限说明 / 数据用途 / 检查清单 / 拒审预案）；manifest 0.2.0→0.3.0，description 改双语

**修改/新增文件**：
- 新增：`chrome-extension/i18n.js`、`chrome-extension/tests/multimarket.test.js`、`scripts/build_extension_zip.sh`、`docs/chrome-web-store-submission.md`
- 修改：`chrome-extension/popup.js`、`popup.html`、`popup.css`、`background.js`、`manifest.json`、`.gitignore`

**本地测试**：`multimarket.test.js` 7 项全绿；既有 E2E `e2e-full-pipeline.spec.js` 11 项全绿；4 个扩展 JS `node --check` 通过。

**Push + code-review**：推送前走 `/code-review`（high effort），发现并修复语言切换 bug —— popup 语言切换回调无条件调用 `updateActionUI()`，会在抓取中/限流倒计时状态下把抓取按钮重新启用、清掉反爬提示（详见 TEST_LOG 同日条目）。修复后合入本批推送。代码已 push develop（commit `6889a70`，仅 9 个代码文件，文档按策略留本地）；扩展不经 docker，无需 ECS 部署。

**待 Erika 手动**：Chrome Web Store 开发者注册（$5）+ 上传 zip + 填表 + 提交审核（材料见 `docs/chrome-web-store-submission.md`）。

**涉及岗位及工时**：

| 岗位 | 工时 | 具体工作 |
|------|------|---------|
| 前端开发 | 8h | i18n 模块 + popup 全量国际化 + 语言切换 + 登录指示灯 UI |
| 后端开发 | 1.5h | CHECK_LOGIN handler + getApiBaseUrl 复用（复用现有 /me + cookie 链路）|
| DevOps | 2h | 打包脚本 + .gitignore + 本地冒烟流程 |
| 产品经理 | 4.5h | Web Store 全套上架材料（文案/隐私政策/权限说明/检查清单）|

### 新功能：woot 出海版禁用 — ENABLE_WOOT_SCRAPER 环境变量门控

- **工作量**: S（2 文件改动 + 1 新建 + 占位符模板，约 0.2 人天）
- **状态**: ✅ 代码完成 + push develop（CB `cb29f78`），prod `deploy/.env` 已加 `ENABLE_WOOT_SCRAPER=false`

**需求描述**：
woot.com 评论抓取仅限国内环境（US marketplace only，~50 条/ASIN），出海 prod 默认禁用，防止海外用户误触 woot 返回空评论。用户应使用 Chrome 扩展上传替代。

实现内容：
- `backend_api/app/services/review_scraper.py` 新增 `_woot_enabled()` 门控函数，读取 `ENABLE_WOOT_SCRAPER`（默认 `false`），Amazon 路径调用 woot 前先判断，禁用时返回空列表 + 日志提示用 Chrome 扩展上传
- `deploy/.env.example` 新建 — 全部部署环境变量的占位符模板，包含 `ENABLE_WOOT_SCRAPER=false`
- `.gitignore` 加 `!deploy/.env.example` 白名单
- 前端确认无"免费抓取"UI 需要隐藏

**涉及岗位及工时**：

| 岗位 | 工时 | 具体工作 |
|------|------|---------|
| 后端开发 | 1h | `_woot_enabled()` 门控 + review_scraper.py Amazon 分支改造 |
| DevOps | 0.6h | `deploy/.env.example` 模板 + `.gitignore` 白名单 + prod `.env` 同步 |

---

### Bug 修复：Chrome 扩展 Step 16 code-review 3 个遗留边界项

- **工作量**: S（扩展背景脚本 3 项修复 + popup/CSS/i18n 配套，约 0.3 人天）
- **状态**: ✅ push develop + CD 全绿

**需求描述**：
Step 16 `storage.session` 迁移引入的 3 个 code-review 边界项逐一修复：① saveTabReviews 配额错误静默丢失 → 回传 `storage_error` 到 popup 显示可见警告（i18n 中英双语 + CSS 琥珀色样式）；② load→mutate→save 异步链缺串行化 → 新增 `withTabLock()` per-tab Promise 锁包裹 `START_SCRAPING` 和 `STORE_REVIEWS` handler 的读写循环；③ tabLastScrapeTime/tabConsecutiveZeros 内存 Map 未持久化 → 新增 `loadTabMeta/saveTabMeta/deleteTabMeta` storage.session helper，6 个读写点全部迁移，SW 重启后 throttle 和 consecutive-zero 防护不再失效。

**涉及岗位及工时**：

| 岗位 | 工时 | 具体工作 |
|------|------|---------|
| 前端开发 | 1.2h | background.js 3 项修复（+~85 行 helper + handler 重构）+ popup.js storage_error 检测 + i18n.js 双 key + popup.css 样式 |
| 测试 | 0.3h | node --check 三文件 + multimarket.test.js 7/7 + pre-commit 机密扫描 |

---

## 2026-07-14

### 新功能：支付成功页面 + 支付后套餐自动激活

- **工作量**: S（前端 1 新页面 + 前后端各 1 文件改 redirect URL，约 0.5 人天）
- **状态**: ✅ 全部完成 + push develop + 部署 + 线上验证通过

**需求描述**：
用户通过 Paddle 支付后，原流程重定向到 `/settings?billing=success` → `/settings/billing` → `/settings` → `/settings/push`，无任何成功反馈，且套餐需等待 webhook 异步更新。本次新增专用支付成功页面，支付后直接展示套餐详情并轮询等待激活。

实现内容：
- 新建 `frontend/src/app/payment/success/page.tsx`：三态 UI（pending 琥珀脉冲动画 / activated 绿色 Sparkles 图标 / error 联系客服提示）；每 2s 轮询 `GET /api/billing` 检测 `plan === planKey`，最多 40s；展示套餐名、月 credits、价格；提供"Go to workspace"和"Configure push notifications"跳转
- 修改 `frontend/src/lib/api/browser.ts`：success_url 从 `/settings?billing=success` 改为 `/payment/success?plan=${opts.planKey}`
- 修改 `backend_api/app/routes/settings.py`：后端默认 success_url 同步更新为 `/payment/success?plan={plan_key}`
- Paddle Dashboard webhook URL 已确认配置为 `https://api.clueai-reviewlens.com/api/billing/webhook`

**线上验证**（2026-07-14 惜_clueai/test123456）：
- 支付成功页 `/payment/success?plan=starter` 正常渲染 ✅
- 套餐从 free 更新为 starter ✅

**涉及岗位及工时**：

| 岗位 | 工时 | 具体工作 |
|------|------|---------|
| 前端开发 | 2h | payment/success 页面开发（三态 UI + 轮询逻辑 + PlanPricing/MONTHLY_GRANT 数据展示）|
| 后端开发 | 0.5h | settings.py success_url 默认值修复 + Paddle webhook 配置确认 |

---

## 2026-07-13

### 新功能：V4-出海 M4 4.1 analyzer.py 接入 LLM Router + JSON 输出硬化

- **工作量**: S（单模块 1 文件 + 轻量重构，约 0.3 人天）
- **状态**: ✅ 全部完成 + 26/26 测试通过 + push develop + 部署

**需求描述**：
V4 出海 M4 最后一个直连 DeepSeek 的模块（`review_analyzer/analyzer.py`）接入 LLM Router。此前 M4-pre 已完成 `llm_router.py` 双 locale 链路（MODELS_EN: GPT-4o-mini→DeepSeek→Qwen; MODELS_ZH: DeepSeek→GPT-4o-mini→Qwen）并集成了 `deep_analyzer.py` 和 `insight_engine.py`。本次是收尾任务，确保遗留的 Streamlit 分析路径也走 Router。

实现内容：
- 移除 `from openai import OpenAI`，仅保留 `AuthenticationError`
- 新增 `_call_llm()` 函数：内部 `import router_completion`（懒加载避免循环引用），`locale="en"` 走 GPT-4o-mini 优先链，`"zh"` 走 DeepSeek 优先链
- JSON 输出硬化：SYSTEM_PROMPT 末尾追加 "Respond with raw JSON only. No markdown fences, no explanation outside the JSON object." + markdown fence 正则抢救（`re.search(r'\{.*\}', content, re.DOTALL)`）
- 所有分析入口（`analyze_comment` / `_analyze_one` / `analyze_batch`）新增 `locale` 参数透传，默认 "en"（海外优先）
- `api_key` 参数保留向后兼容（Streamlit 仍传），实际调用走 llm_router（从环境变量读取 Key）
- 错误提示更新："DeepSeek API Key" → "LLM API Key"
- 移除 `response_format={"type": "json_object"}`（DeepSeek 支持不完整，改用文本 + 正则提取）

**涉及岗位及工时**：

| 岗位 | 工时 | 具体工作 |
|------|------|---------|
| 后端开发 | 1.5h | `_call_llm()` 实现、SYSTEM_PROMPT 硬化、locale 参数透传、markdown fence 抢救、测试验证 |
| 算法工程师 | 0.5h | JSON 输出保证策略（强化指令 + fence rescue）、rescue 4 模式验证 |

---

### 新功能：V4-出海 M2.7 展示层翻译（分析结果中文自动翻译）

- **工作量**: S（跨前后端 2 文件 + hook + ModuleCard 改造，约 0.5 人天）
- **状态**: ✅ 全部完成 + tsc/next build 通过 + 本地验证

**需求描述**：
V4 出海 M2.6 已决策分析结果只存英文，M2.7 在前端展示层实现按 locale 自动翻译——中文用户看到中文分析结果，英文用户看到原文。翻译调用后端已有 `POST /api/translate/module` 端点（DeepSeek, temperature=0.1），后端 `translate_cache` 表按内容 SHA256 去重，相同内容不重复消耗 credit。

前端实现：
- 新建 `frontend/src/hooks/useTranslatedContent.ts` — 翻译 hook，检测 locale=zh 自动调用翻译 API，翻译失败时静默 fallback 英文原文，不白屏
- 改造 `frontend/src/components/analysis/module-card.tsx` — 接入 hook，英文用户无变化；中文用户自动翻译展示，右上角出现 原文/翻译 切换按钮

不改动：
- translate.py 端点（已可用）
- translate_cache 表结构
- LLM 分析链路（仍只写英文）

**涉及岗位及工时**：

| 岗位 | 工时 | 具体工作 |
|------|------|---------|
| 前端开发 | 2h | useTranslatedContent hook、ModuleCard 改造、tsc/build 验证 |
| 后端开发 | 0h | 复用已有 translate.py + translate_cache（M2.6 已就绪） |
| 产品经理 | 0.5h | 验收标准确认（中英切换 / 翻译失败 fallback / 缓存不重复消耗 credit） |

---

### 新功能：V4-出海 M2.5-B accept-terms 端点 + M2.5-C Terms Gate 老用户合规拦截

- **工作量**: M（跨前后端 12 文件 + 2 commit + 线上验证，约 1.2 人天）
- **状态**: ✅ 全部完成 + ruff/tsc 通过 + push develop + 部署 + 线上 Playwright 端到端验证通过

**需求描述**：
V4 出海合规闭环 — 确保所有用户（新+老）都接受过更新后的 Terms of Service 和 Privacy Policy（版本 2.0，包含 GDPR/CCPA/PIPL 合规条款）。

M2.5-B 后端：
- `POST /auth/accept-terms` 端点：接收 `terms_version`，写入 `users.terms_accepted_at` + `terms_version`，幂等（同版本重复调用返回 already_accepted）
- `GET /me` 响应扩展：新增 `terms_accepted_at`、`terms_version`、`locale` 三个字段
- `CURRENT_TERMS_VERSION = "2.0"` 常量统一管理
- `AcceptTermsRequest` Pydantic schema
- `UserPayload` 扩展 3 个字段

M2.5-C 前端：
- 新建 `frontend/src/components/terms/terms-gate.tsx` — 全屏不可关闭 modal（z-[9999]），含两个必选勾选框（18+ 确认 + 同意协议）、i18n 双语支持（`t.rich` 渲染 Terms/Privacy 链接）、调用 `acceptTerms("2.0")` 成功后关闭
- 新建 `frontend/src/lib/api/browser.ts` 中 `acceptTerms()` 函数
- 改造 `frontend/src/components/app/sidebar.tsx` — `useMe()` hook 扩展返回 `showTermsGate` 布尔值（`terms_version !== "2.0"` 且 `me !== null`），JSX 挂载 `<TermsGate open={showTermsGate} />`
- i18n：`auth` 段新增 5 个 key（termsGateTitle / termsGateSubtitle / termsGateDescription / termsGateSubmit / termsGateSubmitting），en + zh 双语言

Bug 修复（部署后）：
- 遗漏 `backend_api/app/services/i18n.py` 导致 API 全部 502，补提交后恢复正常

**涉及岗位及工时**：

| 岗位 | 工时 | 具体工作 |
|------|------|---------|
| 前端开发 | 4h | TermsGate 组件、Sidebar useMe 改造、acceptTerms API、i18n key 定义、en/zh 文案 |
| 后端开发 | 3h | accept-terms 端点、GET /me 扩展、UserPayload/AcceptTermsRequest schema、i18n.py 服务层 |
| 产品经理 | 0.5h | 需求验收标准定义 |

---

### 新功能：V4-出海 M2.5-D CookieBanner + 上传页数据告知 + M2.4-A Privacy 合规条款 + M2.4-B Terms 合规条款

- **工作量**: M（新组件 2 + i18n 文案双侧 + 4 页面改动 + inline parser 提取，约 0.8 人天）
- **状态**: ✅ 全部完成 + tsc 通过 + 本地 Playwright E2E 验收通过 + 待 push develop

**需求描述**：
V4 出海合规三项收尾任务：
- **M2.5-D**：首次访问 Cookie 同意横幅（底部固定栏 + localStorage 持久化，Accept 后刷新不再出现）+ 上传页数据匿名化告知小字
- **M2.4-A**：Privacy Policy 补全 6 项合规条款（EU/EEA Exclusion、Amazon Disclaimer、AI Training Data、Governing Law、Dispute Resolution、Age 18+ & AI Transparency），从 11 sections → 17 sections
- **M2.4-B**：Terms of Service 补全 4 项合规条款（Age Restriction 18+、Prohibited Use Cases、Governing Law & Arbitration、Amazon Trademark Disclaimer），从 10 sections → 14 sections

**实现内容**（8 文件）：
1. 新建 `frontend/src/components/CookieBanner.tsx` — 底部固定横幅（`fixed bottom-0`），首次访问 `localStorage` 检查后显示，Accept 写入 `cookie_consent=true` 并消失，i18n 双语支持
2. 新建 `frontend/src/lib/render-inline.tsx` — 从 `legal-article.tsx` 提取出的共享内联富文本解析器（支持 `<b>` / `<mail>` / `<link href>` / `<ext href>` 标签）
3. 改造 `frontend/src/app/layout.tsx` — `<NextIntlClientProvider>` 内挂载 `<CookieBanner />`
4. 改造 `frontend/src/components/upload/upload-form.tsx` — 上传区域下方添加数据告知小字："您上传的评论将在分析前进行匿名化处理。我们不存储个人身份信息。详见我们的 [隐私政策]"
5. 更新 `frontend/messages/en.json` — +cookieBanner（text + accept）+ upload.uploadNotice + legal.privacy 6 新 sections + legal.terms 4 新 sections
6. 更新 `frontend/messages/zh.json` — 同上中文翻译
7. 更新 `PROGRESS_V2.md` — M2 进度 65%→~80%（2.4 合规条款✅ / 2.5 全部✅）

**技术细节**：
- `next-intl`（use-intl）内置消息解析器拒绝自定义 XML 标签（如 `<link href="...">`），导致 `t("text")` 抛出 `INVALID_TAG` 错误并回退显示 key 名
- 解决方案：使用 `useMessages()` 获取原始 JSON 字符串绕过 use-intl 解析器，再传递给 `renderInline()` 处理富文本标签
- 该模式与 `LegalArticle` 组件一致（直接读取 messages 而非通过 useTranslations）

**验收结果**（本地 Playwright E2E，2026-07-13）：
- CookieBanner 首次显示 ✅ | Accept 消失 ✅ | 刷新后不出现 ✅
- /privacy：17 sections ✅（十二~十七为新增合规条款）
- /terms：14 sections ✅（十一~十四为新增合规条款）
- 上传页数据告知小字 + 隐私政策链接 ✅
- 零控制台错误 ✅

**涉及岗位及工时**：

| 岗位 | 工时 | 具体工作 |
|------|------|---------|
| 前端开发 | 3h | CookieBanner 组件、render-inline 提取、layout 挂载、upload-form 数据告知、i18n key 定义 |
| 产品经理 | 0.5h | 合规文案审阅（Privacy 6 + Terms 4 sections 双语） |
| QA | 0.5h | Playwright E2E 本地验收（4 项全部通过） |

---

## 2026-07-09

### Bug 修复：Paddle 支付 6 项根因系统性修复（含 PADDLE_CLIENT_TOKEN 命名兼容）

- **工作量**: M（11 文件跨前后端 + 4 commit 分阶段落地 + 2 轮部署验证，约 1.2 人天）
- **状态**: ✅ 全部修复 + tsc/ruff 通过 + 4 commit push develop + Erika 部署 + Prod Playwright MCP 端到端验证 Paddle overlay 正常拉起

**需求描述**：
生产环境 Paddle 支付链路存在 6 个根因导致用户无法完成升级付费：
- R1：前端部署过旧导致升级弹窗显示裸 i18n key
- R2：后端 `createBillingCheckout` 硬编码 tier，所有套餐按钮都拉起 Pro Monthly
- R3：`billing.ts` 未检查 `configured` 字段就注入 HTML，未配置时静默失败
- R4：5 个 CTA catch 处理器不一致，部分静默吞错无用户反馈
- R5：env var 命名不匹配 — ECS 使用 `NEXT_PUBLIC_PADDLE_CLIENT_TOKEN`，后端读的是 `PADDLE_CLIENT_TOKEN`
- R6：`quota-dialog.tsx` 手写 fetch 绕过 billing helper，与其他入口行为不一致

**实现内容**（11 文件，4 commit）：
1. `e749a05`（R1）：修复 products 页面标题双重 ClueAI 和升级弹窗翻译 key 不匹配
2. `690413e` / `48f08de` / `deb763c`（R2-R4 + R6）：
   - `review_analyzer/paddle_billing.py`：新增 6 个 price_id 常量 + `_resolve_price_id(plan_key, period)` 映射 + `get_checkout_html()` 接受 plan_key/period 参数
   - `backend_api/app/schemas/settings.py` + `routes/settings.py`：BillingCheckoutPayload 新增 plan_key/period 字段
   - `frontend/src/lib/billing.ts`：`openBillingCheckout` 检查 `configured` → false 返回 `{ok:false}` → true 但无 html 返回 `{hasHtml:false}`
   - `frontend/src/lib/api/browser.ts`：`createBillingCheckout` 接受并转发 plan_key/period
   - 6 个入口统一走 `openBillingCheckout`：pricing-content.tsx / pro-cta-button.tsx / billing-panel.tsx / upgrade-pricing-dialog.tsx / quota-dialog.tsx（从手写 fetch 迁移）/ register-form.tsx（解析 ?period= 参数）
3. `1611000`（R5）：`paddle_billing.py` 新增 `os.environ.get("PADDLE_CLIENT_TOKEN") or os.environ.get("NEXT_PUBLIC_PADDLE_CLIENT_TOKEN") or ""` fallback（同时对 `PADDLE_ENVIRONMENT`/`NEXT_PUBLIC_PADDLE_ENV` 做同样兼容）

**涉及岗位及工时**：
- 后端开发（0.4 人天）：paddle_billing.py 重构 + settings schema/route 扩展 + env var 兼容
- 前端开发（0.6 人天）：billing helper 重构 + 6 入口统一 + register 闭环 + pricing 错误状态
- QA（0.2 人天）：2 轮 Playwright MCP 端到端验证（configured 检查 + Paddle overlay 拉起 + price_id 正确性）

**验证结果**（Prod，2026-07-09 部署后 Playwright MCP + 惜_clueai/test123456）：
- `POST /api/billing/checkout` → `configured: true` ✅
- `checkout_html` 含有效 `Paddle.Initialize({ token: "live_..." })` ✅
- Starter Monthly → price_id `pri_01kwxwtav7n1vy5vc906v0ywnr` 正确解析 ✅
- Paddle overlay iframe 完整弹出：订单概览 / US$12.00 / 邮箱预填 / 国家选择 / 继续按钮 ✅
- 无 console 错误 ✅

---

### V4-出海-M2.2 全站 i18n Commit 4/4：auth + edge cases

- **工作量**: S（3 page + 1 component 重构 + messages 双侧 +13 key，约 0.3 人天）
- **状态**: ✅ 已实现 + 本地 tsc 通过 + push develop（commit `e5a1d42`）+ Erika 部署上线 + Prod Playwright MCP 双 locale 验证通过

**需求描述**：
V4 出海 beta 全站 i18n 第 4 批（最后一批）。auth-layout.tsx 是 auth 模块共用的左半区品牌展示组件，左侧包含 SVG 图（3 个中文注释保留）+ 趋势标签 + 底部价值主张文案，共 7 个硬编码中文字符串；login / register / forgot-password 三个页面的 metadata（`<title>` / `<meta name="description">`）原本是静态 `export const metadata`，无法随 locale 切换。

**实现内容**：
1. [auth-layout.tsx](frontend/src/components/auth/auth-layout.tsx)：`AuthShowcase()` 内联组件 5 个字符串（`showcaseTitle` / `showcaseLive` / `showcasePositive` / `showcaseNegative` / `showcaseActions`）+ `AuthLayout()` 2 个字符串（`showcaseHeading` / `showcaseBody`）→ `t()`；3 个 SVG 注释保留中文
2. [login/page.tsx](frontend/src/app/login/page.tsx) / [register/page.tsx](frontend/src/app/register/page.tsx) / [forgot-password/page.tsx](frontend/src/app/forgot-password/page.tsx)：`export const metadata = buildNoIndexMetadata({title: "登录"})` → `export async function generateMetadata()` + `await getTranslations("auth")`
3. [frontend/messages/{en,zh}.json](frontend/messages/en.json)：auth namespace 各新增 13 个 key（showcase* × 7 + *MetaTitle × 3 + *MetaDescription × 3），双侧 54 key 完全对齐
4. Edge case sweep：`grep -rn` 扫 `components/auth/` + `app/{login,register,forgot-password}/`，零中文遗漏

**涉及岗位及工时**：
- 前端开发（0.3 人天）：1 component + 3 page metadata 动态化 + messages 补齐 + edge sweep

**验证结果**（Prod Playwright MCP，惜_clueai/test123456）：
- EN locale（cookie `NEXT_LOCALE=en`）：
  - Login page title: `Log In | ClueAI` ✅ | Showcase: `Review Trend Analysis / Live / Positive trending up / Negative trending down / Improvements` ✅ | Heading: `Review insights drive product iteration` ✅
  - Register page title: `Sign Up | ClueAI` ✅
  - Forgot password page title: `Reset Password | ClueAI` ✅
- ZH locale（cookie `NEXT_LOCALE=zh`）：
  - Login page title: `登录 | ClueAI` ✅ | Showcase: `评论趋势分析 / 实时更新 / 好评上升 / 差评下降 / 改进措施` ✅ | Heading: `评论洞察驱动产品迭代` ✅
  - Forgot password page: `找回密码 | ClueAI` ✅ | Content: `重置密码 / 输入注册邮箱，我们将发送重置链接` ✅
- 三页 showcase 组件共用 auth-layout，EN/ZH 切换全部字符串正确 ✅

---

## 2026-07-08

### V4-出海-M2.2 全站 i18n Commit 1/4：analysis 模块

- **工作量**: M（23 文件重构 + 2 messages 双侧新增 ~258 key，约 0.8 人天）
- **状态**: ✅ 已实现 + 本地 tsc 通过 + push develop（commit `ee940b4` + fix `6cd4263`）+ Erika 部署上线 + Prod Playwright MCP 双 locale 验证通过

**需求描述**：
V4 出海 beta 全站硬编码中文提取到 `useTranslations()` 的第一步。全量分 4 个 commit 落地（analysis / settings + upload / marketing + credit / auth + edge），本次是第 1 批 —— 分析结果页 / 对比页 / 历史页 / 行动项面板等 23 个文件。核心难点是 `create-action-panel.tsx` + `inline-action-button.tsx` 的 `owner_role` 字段：后端 `workers/jobs.py` 默认存中文 `"运营"`，`action_advisor.get_dept_label` 也返回中文，前端如果直接把 value 改成英文 slug 会破坏混合语言环境下的聚合/查询逻辑（完整迁移到 slug 是独立任务，等 backend migration 后跟 M2.3 一起做）。

**实现内容**：
1. [frontend/messages/{zh,en}.json](frontend/messages/en.json)：双侧各新增 ~258 行 key（`analysis.polling` / `compare` / `action` / `session` / `qa` / `filterBar` / `productSearch` / `history` 命名空间 + `common.*` 扩展）
2. `frontend/src/app/analysis/{compare,history,results}/page.tsx`：3 个 page 全部接入 `useTranslations`
3. `frontend/src/components/analysis/*.tsx`：17 个组件重构（polling / results-sections / compare-* / action / session / qa-* / module-card / product-search / filter-bar）
4. **API 契约保留模式**（关键）：[create-action-panel.tsx](frontend/src/components/analysis/create-action-panel.tsx) + [inline-action-button.tsx](frontend/src/components/analysis/inline-action-button.tsx) 的 `OWNER_ROLES` 常量改造为 `{ value: "运营", labelKey: "ownerOps" }` 格式：
   - state 存中文 value（`useState<string>(OWNER_ROLES[0].value)`）
   - 提交时 payload `ownerRole: ownerRole`（仍是中文，后端契约不变）
   - UI 渲染 `<option>{t(item.labelKey)}</option>` / `variant={ownerRole === role.value ? "default" : "outline"}`（i18n key 走 `ownerOps` / `ownerProduct` / `ownerQA` / `ownerReview`）
5. 分两次 commit：`ee940b4` 主体重构 + `6cd4263` owner_role 契约修复补丁

**涉及岗位及工时**：
- 前端开发（0.6 人天）：23 文件 tsx 重构 + messages 双侧 key 补齐 + owner_role API 契约保留改造
- 翻译校对（0.1 人天）：258 key 的英文文案对齐
- QA（0.1 人天）：Playwright MCP 双 locale E2E（`/analysis/history` + `/analysis/results?session_id=92`）

**风险与验证**：
- **零后端/DB/环境变量变更** — 纯前端 + i18n messages 文件，无 migration
- **验证方式**（Prod，2026-07-08 部署后 Playwright MCP + 惜_clueai/test123456 登录 https://www.clueai-reviewlens.com）：
  - `/analysis/history` — 中→英切换后头部（`分析历史`→`Analysis history`）、表头（`批次标题/版本/时间/评论/操作`→`Batch title/Version/Time/Reviews/Actions`）、操作按钮（`看结果/对比/删除`→`View results/Compare/Delete`）全部 i18n ✅
  - `/analysis/results?session_id=92` — 7 个 tab（User Profile / User Experience / Buying Motives / Unmet Needs / Recommendations / Create Action / Raw Reviews）+ 5 个 stat 卡（Total Reviews / Positive Rate / Negative Rate / Rating / Purpose）+ 6 个 section header + Create Action 面板（Choose issue / Action title / Owner role / Expected review date / Expected effect batch / Suggested action / Create action）+ Translate/XLSX buttons 全部 i18n ✅
  - Owner role 下拉打开菜单显示 `Ops / PM/R&D / QA / Review`（英文标签），但内部 state 保留中文 value ✅
- **已知遗留**：
  - 表格数据里残余的 `日常评论分析 | N条` 是 backend session_label（后端存储字段），在 M2.3 独立任务范围内
  - Commit 2 (settings + upload) / Commit 3 (marketing + credit) / Commit 4 (auth + edge) 仍在做，分别在新会话续做（stash@{0} 里有 Commit 2 半成品，`push-settings-panel.tsx` / `smart-push-settings.tsx` / `golden-set/page.tsx` 三处仍有残余中文需补齐）
  - 3 个法律页 metadata（terms/privacy/refund）的 `export const metadata` 无法用 `useTranslations`（Next.js metadata 静态限制），随 M2.3 独立任务处理；11 个 `categoryLabels` 已在 2.2.C 迁移完成

---

### Bug 修复：Credit History drawer 被 Workspace 页面盖住

- **工作量**: XS（单文件 4 行改动，0.2 人时）
- **状态**: ✅ 已实现 + 本地 tsc 通过 + push develop（commit `66b8254`）+ Erika 部署上线 + Prod Playwright MCP 验证通过

**需求描述**：
Sidebar → Upgrade 按钮打开升级套餐弹窗（`UpgradePricingDialog`，Radix `DialogPortal`）后，点击弹窗底部「查看消费记录」按钮，`CreditLedgerDrawer` 应从右侧滑入并覆盖整个 Workspace。实际观察到 drawer 出现在 Workspace 主内容之下：drawer 面板被 Workspace 的模块卡片遮挡，右侧看到的仍是 Workspace 的 "Today's Workspace" 及 SKU 卡片，drawer 内容不可点击。

**根因**：
`CreditLedgerDrawer` 是 inline 渲染（`return <>...</>` 直接返回），挂载在 `SidebarCreditEntry` → `Sidebar` 的 `<aside class="fixed left-0 top-0">` 内。`position: fixed` 会创建独立的 stacking context，导致 drawer 的 `z-50` 只在 sidebar 这个 context 内部生效，无法压过后面 DOM sibling（AppShell 里的 main）中带 `backdrop-blur` 的 workspace 模块卡片（`backdrop-filter` 也会创建 stacking context）。参考 `UpgradePricingDialog` 走 Radix `DialogPortal`，portal 到 `document.body` 后就可以逃出 sidebar 的 stacking context，因此升级套餐弹窗本身能正常压过 Workspace。

**实现内容**：
1. [frontend/src/components/credit/credit-ledger-drawer.tsx](frontend/src/components/credit/credit-ledger-drawer.tsx)：新增 `import { createPortal } from "react-dom"`
2. `return (...)` 改为 `return createPortal(..., document.body)`
3. 加 SSR 守卫 `if (typeof document === "undefined") return null`（避免 Next.js SSR 阶段 `document` 未定义）
4. Backdrop `z-40` → `z-[100]`、drawer `z-50` → `z-[110]`（抬升 z 数值兜底，确保盖过任何 `z-50` 元素）

**验证方式**：
- 本地 `npx tsc --noEmit` 通过 ✅
- **Prod Playwright MCP 验证**（2026-07-08 部署 commit `66b8254` 后，测试账号 `惜_clueai` 登录 https://www.clueai-reviewlens.com/workspace）：
  - 视觉 ✅ — sidebar 点 Upgrade → 升级套餐弹窗 → 底部「查看消费记录 →」→ Credit History drawer 完整覆盖 Workspace 主内容，backdrop 半透明遮罩生效，无穿透（截图 `credit-drawer-verification.png`）
  - 结构 ✅ — `browser_evaluate` 查询 DOM：`drawerParentTag=BODY`、`drawerParentIsBody=true`、`drawerZ=110`、`backdropParentIsBody=true`、`backdropZ=100`（portal 到 body 生效，z-index 层级正确）
  - 交互 ✅ — 点击 backdrop 关闭 drawer（`drawerStillOpen=false`）；列表正常加载 Insight/Export/Top-up/Monthly grant 等 ledger 条目

**涉及岗位及工时**：
- 前端开发：0.2 人时（诊断 stacking context + 单文件 portal 改造）
- QA：0.1 人时（Prod Playwright MCP 三维度验证）

---

### V4-出海-M2.2.L：法律五页 locale 完全切换 + cookies/dpa 补正文

- **工作量**: M（10 文件改造 + 2 页正文新增，约 1.2 人天）
- **状态**: ✅ 已实现 + 本地 tsc + build 通过 + Playwright MCP 双 locale E2E；已 push develop（commit `2b488f2`）+ Erika 部署上线 + prod 验证通过

**需求描述**：
V4 出海 beta 上线前，法律页面呈现方式与 Shulex 对标：voc.ai/privacy 纯英文 vs voc.ai/cn/privacy 中文。之前 privacy/terms/refund 页是并排中英双列（左中右英），阅读密度大且不符合海外用户习惯；cookies/dpa 是 M3.4 时期为避免 footer 链接 404 建的占位空壳。本次改造：五页统一走 next-intl locale 单语切换（中国 IP → zh，其余 → en，与站点 middleware 一致），并把 cookies/dpa 补齐完整合规正文（GDPR Art. 28 DPA + SCC 2021/914 Module 2 + UK IDTA + GDPR/CCPA/PIPL cookies 合规）。

**实现内容**：
- [frontend/messages/{zh,en}.json](frontend/messages/en.json)：新增 `legal.*` 命名空间，5 页结构化文案：`legal.terms` / `legal.privacy` / `legal.refund` / `legal.cookies` / `legal.dpa`；每页含 `pageTitle` + `pageSubtitle` + `sections[]`，段落块三种类型：`paragraph` / `bullets` / `ordered`；文案内嵌 4-tag rich-text marker：`<b>` 加粗、`<mail>` mailto、`<link>` 站内链接、`<ext>` 外链
- 新建 [frontend/src/components/legal/legal-article.tsx](frontend/src/components/legal/legal-article.tsx)：server component，127 行，用 `getMessages()` 读 locale 消息 + 内联 4-tag marker 解析器（白名单模式，未识别 tag 直接透传原文）
- [frontend/src/app/{terms,privacy,refund,cookies,dpa}/page.tsx](frontend/src/app/privacy/page.tsx)：5 页统一改造为 `async` component，`getTranslations("legal.<page>")` 拿 `pageTitle` / `pageSubtitle`，`generateMetadata` async pattern 让 SEO title/description 也 locale-aware
- cookies 页正文新增 6 段：Cookies 用途 / 三方 cookie 清单（Cloudflare Analytics、Paddle checkout、Sub-processors DPA）/ 保留期 / 用户控制路径 / GDPR/CCPA/PIPL 合规分析 / 更新条款
- dpa 页正文新增 12 段：GDPR Art. 28 processor 义务、SCC 2021/914 Module 2 国际传输、UK IDTA、Sub-processors 变更通知期、数据主体权利支持、breach notification 72h、数据返还/删除、审计权、DPO 联系方式等

**涉及岗位及工时**：
- 前端开发（0.6 人天）：legal-article server component + 5 页 page.tsx 改造 + messages 命名空间接线
- 内容/合规（0.4 人天）：cookies 6 段 + dpa 12 段的合规文案撰写（GDPR/CCPA/PIPL/SCC/UK IDTA 参考条款）
- QA（0.2 人天）：Playwright MCP 双 locale E2E（5 页 × 2 locale = 10 次渲染），语言切换器菜单、CJK 污染检查

**风险与验证**：
- **零后端/DB/环境变量变更** — 纯前端 + i18n 消息文件，无 migration
- **验证方式**：
  - 本地 `npx tsc --noEmit` + `npm run build` 通过 ✅
  - Playwright MCP 五页 × 两 locale 各渲染一次：全部通过，5 en 页均无 CJK 污染，zh 页文案排版符合预期 ✅
  - 线上（https://www.clueai-reviewlens.com）Erika 部署后二次验证通过 ✅
- **⚠️ 遗留待办**：五页（含 pricing）`<title>` 出现 `X | ClueAI | ClueAI` 重复 —— root `layout.tsx` template `"%s | ClueAI"` + 各 `page.tsx` `buildMarketingMetadata({ title })` 手写 " | ClueAI" 叠加。属项目历史约定不一致，非本次引入的回归。Erika 决定新开会话独立修复

---



- **工作量**: M（7 文件改造 + 1 migration + 1 单测 + 3 文档，约 0.8 人天）
- **状态**: ✅ 已实现 + 本地 tsc + 单测 10/10 通过；待 push + Erika 部署（含 migration 047）+ prod 验证

**需求描述**：
V4 出海 beta 上线前最后一处硬编码中文。`comments.category` 字段一直存 11 个中文分类名（产品质量/包装物流/使用体验/客服售后/性价比/功能需求/正面反馈/单纯好评/无效乱码/混合评价/其他），前端下载 Excel 与后端导出直接裸展示，英文用户导出的 Excel「Category」列全是中文，分析结果对英文用户不可用。改造为：backend 输出稳定英文 slug（业务标识符）→ i18n 层按 locale 映射中/英标签 → 前端 `t()` 消费；同时打通 M4-pre 阶段建的死代码 `messages/{zh,en}.json` `categoryLabels` 命名空间。

**实现内容**：
- [backend_api/app/services/category_grouper.py](backend_api/app/services/category_grouper.py)：新增 `CATEGORY_SLUGS`（11 slug tuple）+ `CATEGORY_ZH_LABELS`（slug → 中文标签 map），`ASPECT_TO_CATEGORY` 值全改 slug，`_derive_category` 所有 return 改 slug，`aspects_to_legacy_schema` fallback `"其他"` → `"other"` / `"无效乱码"` → `"invalid_garbage"`
- [workers/jobs.py:472](workers/jobs.py#L472)：error 分支 `"无效乱码"` → `"invalid_garbage"`
- [review_analyzer/analyzer.py](review_analyzer/analyzer.py)：SYSTEM_PROMPT 分类规则改 `slug（中文名）` 双语格式（LLM 仍能理解中文语义描述） + 输出格式 JSON 枚举改 slug + `VALID_CATEGORIES` 改 slug set + `_validate_result` fallback 改 `"other"` + `_make_unrecognizable` 改 `"invalid_garbage"` + `PROMPT_VERSION` v2.1 → v2.2
- [migrations/047_categories_to_slug.sql](migrations/047_categories_to_slug.sql)：11 条幂等 UPDATE 中文 → slug + 回滚 SQL 注释块（原计划 046 已被 `046_add_scraped_title.sql` 占用，改用 047）
- [frontend/messages/{en,zh}.json](frontend/messages/en.json) `categoryLabels` 段 11 个 key 全改 slug（value 保持原英/中文标签）
- [frontend/src/components/analysis/download-tag-button.tsx](frontend/src/components/analysis/download-tag-button.tsx)：引入 `useTranslations('categoryLabels')`，导出 Excel 时把 slug 翻译成对应 locale 的可读标签
- [review_analyzer/exporter.py](review_analyzer/exporter.py)：新建 `_category_zh(slug)` helper，从 category_grouper 引入 `CATEGORY_ZH_LABELS`，Streamlit 老路径继续显示中文
- [backend_api/tests/test_category_grouper.py](backend_api/tests/test_category_grouper.py)：9 个 TEST_CASES 全改 slug 断言 + 新增 `CATEGORY_SLUGS` 白名单 snapshot 测试（10/10 通过）

**涉及岗位及工时**：
- 后端开发（0.4 人天）：category_grouper / analyzer / worker / exporter / migration / 单测
- 前端开发（0.2 人天）：messages i18n key 改造 + download-tag-button useTranslations 接入
- QA（0.2 人天）：本地上传验证 slug 写入 + en/zh 两语言导出 Excel 分类列人工核对（待部署后跑）

**风险与验证**：
- **⚠️ 高风险 — 数据库 migration**：一次性 UPDATE 所有历史 comments 的 category 字段。已通过 Explore 全库确认无 SQL 查询按中文字面量过滤 `comments.category`，仅写入 + 读取回渲染，就地 UPDATE 安全，无需 dual-read 兼容层。
- **部署顺序**：**先跑 migration 047（psycopg2 python 脚本，ECS api 容器无 psql），再重建 api/worker/frontend + nginx reload**。migration 与部署之间的空窗期即使有分析任务完成也写的是新 slug，历史数据由 UPDATE 一次性收敛。
- **Golden Set 500 条回归跳过**：`eval_v23_500_metrics.json` 无 per-category 字段；`_derive_category` 是 aspects → slug 的确定性纯字符串派生，不经 LLM，中→slug 只改字面量。
- **验证方式**：
  - 本地 `python3 backend_api/tests/test_category_grouper.py` 10/10 通过 ✅
  - 本地 `npx tsc --noEmit` 通过 ✅
  - 待 Erika 部署后用测试账号 `惜_clueai / test123456` 登录 https://www.clueai-reviewlens.com ，用 en cookie + zh cookie 各跑一次上传 + 导出 Excel，验证「Category」/「分类」列分别显示英/中文人类可读标签

---



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

### Bug 修复：Paddle checkout 点 "Get Pro" 错误跳 `/register?plan=pro`（M6 收尾付费路径 hotfix）

- **工作量**: S（新建 1 helper + 4 入口 refactor + 注册闭环，约 0.5 人天）
- **状态**: ✅ 已修复 + 本地 tsc 通过 + push develop（分支 `fix/paddle-checkout-401-redirect`，4 commit：`690413e` + `48f08de` + `deb763c` + C4）+ Erika 合入 develop 并部署上线 + Prod 登录场景验证通过

**需求描述**：
所有用户（**包括已登录的 free 用户**）点 Pro 套餐 "升级" / "Get Pro" 按钮时被直接跳到 `/register?plan=pro`，无法原地拉起 Paddle checkout overlay。付费主路径断裂，登录 free 用户从 Sidebar / Pricing / 落地页 / Settings 任一入口都无法完成升级。期望行为：
- **已登录用户**（含 free）→ 原地拉起 Paddle overlay
- **未登录用户** → 跳 `/register?plan=pro` → 注册成功后自动拉起 Paddle

**根因**：
`upgrade-pricing-dialog.tsx` / `pricing-content.tsx` / `pro-cta-button.tsx` / `billing-panel.tsx` 4 个 Pro 入口的 free 分支硬编码 `<Link href="/register?plan=pro">`，跳过了 "先尝试拉起 Paddle → 401 才 fallback register" 的顺序判断；注册页也没有从 `?plan=xxx` 恢复购买意图的能力。

**实现内容**（4 commit）：
1. `690413e` — 新建 [frontend/src/lib/billing.ts](frontend/src/lib/billing.ts)（+69 行）：
   - `openBillingCheckout(host?)` → 返回 `{ok, configured, hasHtml}`，封装 `createBillingCheckout` API → 注入 `checkout_html` → 遍历 `<script>` 用 `replaceWith` 触发 Paddle inline script 执行
   - `isUnauthenticatedCheckoutError(err)` → 检查 `err.status === 401`
2. `48f08de` — 核心修复（+65 / -53）：[upgrade-pricing-dialog.tsx](frontend/src/components/credit/upgrade-pricing-dialog.tsx) + [pricing-content.tsx](frontend/src/app/pricing/pricing-content.tsx)：
   - 移除 "free 用户跳 `<Link href="/register">`" 分支
   - 合并为统一 `handlePaidCheckout(planKey)`：先调 `openBillingCheckout` → 401 才 fallback 到 `/register?plan=xxx`
   - 加 `<div ref={checkoutRef} className="hidden" aria-hidden="true" />` 挂 Paddle script
3. `deb763c` — 注册闭环（+30 / -4）：
   - [register/page.tsx](frontend/src/app/register/page.tsx) 包 `<Suspense fallback={null}>`（Next.js 15 `useSearchParams` 硬约束）
   - [register-form.tsx](frontend/src/components/auth/register-form.tsx) `PAID_PLAN_KEYS = new Set(["starter", "pro"])` + 读 `searchParams.get("plan")` 记为 `intendedPlan`
   - 注册成功后 `if (intendedPlan)` → `openBillingCheckout(null)` 自动拉起 Paddle
   - 埋点：新增 `signup_checkout_intent` 事件；`signup_click` / `signup_complete` 附 `intended_plan`
4. C4 — 落地页 + 设置页 refactor：[pro-cta-button.tsx](frontend/src/components/marketing/pro-cta-button.tsx) + [billing-panel.tsx](frontend/src/components/settings/billing-panel.tsx) 统一改走 `openBillingCheckout` helper，401 fallback 到 `/register?plan=pro`

**涉及岗位及工时**：
- 前端开发（0.4 人天）：billing helper 抽取 + 4 入口 refactor + register 闭环 + Suspense 兼容
- QA（0.1 人天）：Playwright MCP 登录状态验证 + 网络面板核对 checkout 请求

**风险与验证**：
- **零后端/DB 变更** — 纯前端 helper 抽取 + 入口 refactor；无 migration；`/api/billing/checkout` 端点未动
- **Prod 验证结果**（2026-07-08 惜_clueai / test123456 登录 https://www.clueai-reviewlens.com）：
  - ✅ Pricing 页 Pro 卡片渲染为 `<button "Get Pro">`（旧代码是 `<Link>`），证明 develop 已合入并部署成功
  - ✅ 点 Get Pro 不再跳 `/register?plan=pro`
  - ✅ `POST /api/billing/checkout` 返回 200，`checkout_html` 下发
  - ✅ billing helper 成功注入 script 并触发 Paddle inline JS 执行
- **独立发现问题**（非本次 PR 范围，pre-existing 配置缺失）：
  - Paddle SDK 控制台报 `Uncaught Error: [PADDLE BILLING] You must specify your Paddle Seller ID or token within the Paddle.Initialize() method.`
  - 后端返回体 `checkout_html` 里 `Paddle.Initialize({ token: "" })`，同时 `"configured": false`
  - 根因：prod 环境 `NEXT_PUBLIC_PADDLE_CLIENT_TOKEN`（或后端对应变量）为空，`deploy/.env` 需补配置
  - 该问题独立开任务处理，本次不修改 `deploy/.env`
- **待补验证**：
  - ⏸ workspace 顶栏 Upgrade 按钮预期行为（打开 dialog 还是跳 `/pricing`）—— 待 Erika 确认后补
  - ⏸ 未登录场景闭环：清 cookie → `/pricing` 点 Get Pro → 应跳 `/register?plan=pro` → 注册成功应自动拉起 Paddle（受 token 配置阻塞，只能观察到 "尝试拉起 → SDK 报 seller ID 错误" 行为）

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

---

### Bug 修复：/analysis/sessions/{id}/export/full Content-Disposition latin-1 编码 500

- **工作量**: XS
- **状态**: 代码完成，待部署验收

**需求描述**：
M2-2.2.C 类别标签 i18n 化上线后跑 prod 验收，点击「原始评论 XLSX 下载」按钮返回 HTTP 500。api 容器 traceback 定位为 pre-existing bug，跟 M2-2.2.C 无关：`exporter._build_filename()` 生成的中文文件名（`产品编号-版本-全部-分析结果-20260708.xlsx`）直接塞进 `Content-Disposition` header，starlette 用 latin-1 编码时抛 `UnicodeEncodeError: 'latin-1' codec can't encode characters in position 31-32`。此前应该没英文用户点过这个按钮才没暴露。

**实现要点**：
1. `backend_api/app/routes/export.py` 顶部新增 `from urllib.parse import quote`
2. `/export/full` 路由 `Content-Disposition` 从 `attachment; filename="{filename}"` 改为 RFC 5987 编码 `attachment; filename*=UTF-8''{quote(filename)}`，Chrome / Firefox / Safari / Edge 全支持 UTF-8 编码文件名
3. `/export` 路由 filename 是纯 ASCII（`analysis_{id}_{module}.xlsx`），本次不改，避免范围蔓延

**待验证**：Erika 部署后 EN + ZH 两种 locale 各点一次原始评论下载按钮，均需 200 OK 且文件名可正确显示。

**涉及岗位及工时**：

| 岗位 | 工时 |
|------|------|
| 后端开发 | 0.2h |

---

## 2026-07-09

### V4-出海-M2.2 Commit 2/4: settings + upload 模块 i18n 重构

- **工作量**: L
- **状态**: 完成

**需求描述**：
全站 i18n 第 2/4 批次：settings 模块（7 个子命名空间：billing/account/push/goldenSet/observability/layout/common）+ upload 模块（3 个子命名空间：page/asinFetch/asinWatchlist）全量接入 next-intl `useTranslations`/`getTranslations`。messages zh/en 各 +598 行，zh/en 100% key 对齐。

**实现要点**：
1. 11 个 tsx 文件接入：billing-panel/push-settings-panel/account/golden-set/observability/push/push-layout/asin-fetch-panel/asin-watchlist-panel/upload-page
2. push-settings-panel.tsx 移除硬编码 DEPT_LABELS/FREQUENCY_OPTIONS/DAY_OPTIONS/PLATFORM_OPTIONS/PLATFORM_META，改为静态 key 数组 + runtime `t()` 查找
3. asin-fetch-panel.tsx VALIDATION 表 hint/placeholder 改 i18n key 引用
4. asin-watchlist-panel.tsx relativeTime() 重写为 ICU message format
5. 删除 2 个死代码文件（settings-panel.tsx + smart-push-settings.tsx，合计 -622 行）
6. billing-panel.tsx rebase 冲突解决（origin/develop 已将 createBillingCheckout 重构为 openBillingCheckout）

**涉及岗位及工时**：

| 岗位 | 工时 |
|------|------|
| 前端开发 | 4h |
| 代码审查 | 0.5h |

---

### V4-出海-M2.2 Commit 3/4: marketing + products + credit 模块 i18n 重构

- **工作量**: L
- **状态**: ✅ 已实现 + 本地 tsc/build 通过 + push develop（commit `d30cc0d`）+ Erika 部署上线 + Prod Playwright MCP 双 locale 验证通过

**需求描述**：
全站 i18n 第 3/4 批次：marketing 模块（pricing-faq/trust-signal/pro-cta-button 3 组件）+ credit 模块（credit-ledger-drawer/sidebar-credit-entry/upgrade-pricing-dialog 3 组件）+ products 模块（page/[id]/grid/create/edit/delete/deleteVariant 9 文件）全量接入 next-intl `useTranslations`/`getTranslations`。messages zh/en 各 +220 行（~250 key），zh/en 100% key 对齐。

**实现要点**：
1. **Marketing**：pricing-faq.tsx 6 组 Q&A 全部 i18n；trust-signal.tsx "已支持主流跨境电商平台" → `t("label")`；pro-cta-button.tsx "升级到 Pro"/"处理中..." → `t("defaultLabel")`/`t("loading")`
2. **Credit**：credit-ledger-drawer.tsx 移除 `REASON_LABEL` 常量 map，动态 `t("reasonLabel.${reason}")`；sidebar-credit-entry.tsx Credits/试用天数/Upgrade 全双语；upgrade-pricing-dialog.tsx **大重构**：移除所有硬编码中文（`PLAN_NAME_CN`/`PLAN_HIGHLIGHTS`/`COMPARISON_GROUPS`），改为 key-based 结构 + `resolveComparisonValue()` helper（boolean→icons/numeric→as-is/string→`t("comparisonValue.${value}")`），plan highlights 数组 flatten 为独立 key（next-intl v4 不支持数组）
3. **Products**：server component `generateMetadata()` + page body 走 `await getTranslations()`；client component grid 传 `t` prop（含 ICU interpolation 类型适配）；create/edit/delete/deleteVariant 全部 i18n；lifecycle options 走 `lifecycleKeys` mapping；platform "其他" 用 `t("platformOther")` value="其他" 保持向后兼容

**涉及岗位及工时**：

| 岗位 | 工时 |
|------|------|
| 前端开发 | 5h |
| 翻译校对 | 0.3h |
| QA（Playwright MCP 双 locale E2E） | 0.5h |

**验证结论**（2026-07-09 Prod Playwright MCP + 惜_clueai/test123456）：
- ✅ EN locale：Products list/detail/delete 全英文；Pricing FAQ 6 Q&A 英文；Upgrade dialog plan 名/对比表/功能行全英文
- ✅ ZH locale：全部切换中文正确（产品管理/新建产品/积分/升级套餐/功能对比/月付/年付/最受欢迎）
- ✅ 双 locale cookie 持久化正常；EN→ZH→EN 切换无 key 缺失

**已知遗留**：
- Pricing 页主体（pricing-content.tsx）不在 Commit 3 范围，仍为英文
- Page title 双重 `| ClueAI | ClueAI` pre-existing bug
- Upgrade dialog close 按钮未走 i18n（Radix 默认 aria-label）
- Commit 4/4（auth + edge cases）待做

---

## 2026-07-09

### 付费转化 bug 深度修复（Paddle tier × CTA 错误处理统一）

- **工作量**：~3.5h（含深度根因分析 + 后端 tier 解析 + 前端 5 CTA 统一 + 线上 Playwright 验证）
- **需求描述**：
  - 修复 6 项根因（R1~R6），覆盖 Paddle 升级弹窗裸 i18n key、tier 硬编码导致全部拉起 Pro Monthly、5 处 CTA 点击无反应等线上付费转化阻断问题
  - 后端新增 plan_key/period 入参 + 6 路 price_id 解析；前端 billing.ts 新增 configured 前置检查 + 5 CTA 统一错误处理
  - 关联 Jul 8 的 bcfa655/deb763c/48f08de/690413e 四个 commit（CTA 统一 + i18n，但未部署导致 prod bug）
  - Step 0 前置：Erika 手动补齐 5 个 price_id 到 deploy/.env 和本地 .env
- **涉及岗位及工时**：
  | 岗位 | 工时 |
  |------|------|
  | 后端开发（Python/FastAPI） | 0.8h |
  | 前端开发（Next.js/React） | 1.5h |
  | QA（Playwright MCP 线上 E2E） | 0.7h |
  | 文档更新 | 0.5h |

**验证结论**（2026-07-09 Prod Playwright MCP）：
- ✅ plan_key/period 正确透传（Starter Monthly / Pro Annual / Pro Monthly 三组验证通过）
- ✅ 后端 6 路 price_id 解析正确（每种 tier×period 返回不同 priceId）
- ✅ !configured 错误信息 "Payment not enabled yet." 正常显示（不再沉默无反应）
- ✅ 零 JavaScript console 错误
- ⚠️ 生产 deploy/.env 缺少 PADDLE_CLIENT_TOKEN，所有 tier 的 Paddle overlay 无法拉起（需 Erika 补齐此 env var）

**变更文件（11 个）**：
- 后端：`settings.py`（route+schema）、`paddle_billing.py`
- 前端 lib：`billing.ts`、`browser.ts`
- 前端组件：`pro-cta-button.tsx`、`pricing-content.tsx`、`billing-panel.tsx`、`upgrade-pricing-dialog.tsx`、`quota-dialog.tsx`、`register-form.tsx`

## 2026-07-13

### V4-出海-M2.5-A：注册表单合规改造（3 勾选框 + 后端写入）

- **工作量**：~2h（前端 register-form.tsx + i18n 双语文案 + 后端 schema/route/database 4 文件）
- **需求描述**：
  - 注册表单 password 字段下方新增 3 个 checkbox："我已年满 18 周岁"（必选）、"我同意服务条款和隐私政策"（必选+内联 Link，`t.rich` 渲染）、"向我发送产品更新"（可选）
  - 后端 `RegisterRequest` 新增 `terms_version` / `age_confirmed` / `marketing_opt_in` 三字段
  - `create_user()` 扩展签名支持合规字段 INSERT（locale=默认 en-US, terms_accepted_at=now, age_confirmed_at=now, marketing_opt_in 按需）
  - `register()` 增加 age_confirmed 后端二次校验（False → 400）
  - 不涉及 terms-gate / CookieBanner / 法律页面内容（后续 M2.5-B/C/D）
- **涉及岗位及工时**：
  | 岗位 | 工时 |
  |------|------|
  | 后端开发（Python/FastAPI） | 0.5h |
  | 前端开发（Next.js/React/next-intl） | 1.0h |
  | i18n 翻译 | 0.3h |
  | 文档更新 | 0.2h |

**变更文件（7 个）**：
- 后端：`backend_api/app/schemas/auth.py`、`backend_api/app/routes/auth.py`、`review_analyzer/database.py`
- 前端：`frontend/src/components/auth/register-form.tsx`、`frontend/messages/en.json`、`frontend/messages/zh.json`
- 进度追踪：`PROGRESS_V2.md`（M2.5 节勾选完成项）

## 2026-07-14

### Chrome 插件 Step 12：MutationObserver 分页处理

- **工作量**：~1.5h（inject.js 分页监听 + content.js 消息桥接 + background.js handler）
- **需求描述**：
  - `inject.js` 新增 `allReviews[]` 和 `seenIds Set` 实现跨页累积去重；MutationObserver 监听 `#cm_cr-review_list`（`childList + subtree`），防抖 500ms 后触发提取，通过 `window.postMessage({ type: 'REVIEWLENS_NEW_REVIEWS', count, total })` 通知 content.js；页面加载后 1s 自动启动初始提取 + Observer
  - `content.js` 新增 `window.addEventListener('message')` 监听 `REVIEWLENS_NEW_REVIEWS`，收到后转发 `EXTRACT_REVIEWS_RESULT` 到 background.js
  - `background.js` 新增 `EXTRACT_REVIEWS_RESULT` handler，记录每个 tab 的 `reviewCount` + `lastExtraction`
  - 数据流：Amazon AJAX 翻页 → MutationObserver(MAIN world) → postMessage → content.js(ISOLATED world) → chrome.runtime.sendMessage → background.js
- **涉及岗位及工时**：
  | 岗位 | 工时 |
  |------|------|
  | 前端/插件开发（JS） | 1.2h |
  | 文档更新 | 0.3h |

**变更文件（3 个）**：
- `chrome-extension/inject.js`（+71 行：allReviews/seenIds/MutationObserver/handleNewDOM/startObserver）
- `chrome-extension/content.js`（+36 行：REVIEWLENS_NEW_REVIEWS 监听 + 转发）
- `chrome-extension/background.js`（+22 行：EXTRACT_REVIEWS_RESULT handler）

### Chrome 插件 Step 14-2：反爬限流 + CAPTCHA 检测 + 连续零结果追踪

- **工作量**：~2.0h（background.js 限流 + content.js CAPTCHA 检测 + popup 三种反爬 UI + CSS）
- **需求描述**：
  - `background.js`: 新增 `MIN_SCRAPE_INTERVAL_MS=3000` 频率限流（同 tab 间隔 < 3s 返回 `throttled`），抓取前先 `DETECT_CAPTCHA` 预检，记录 `tabLastScrapeTime`/`tabConsecutiveZeros`（连续 3 次 0 条触发警告）
  - `content.js`: 新增 `detectCaptcha()` 检测 7 项 DOM 指标（title/form/img/body text），≥2 匹配即判定 CAPTCHA 页面；`extractReviews()` 优先检查 CAPTCHA；新增 `DETECT_CAPTCHA` 消息处理器
  - `popup.js`: 三种反爬 UI 提示（🛑 CAPTCHA 红色禁用/⏳ 频率限制黄色倒计时/⚠️ 连续零结果黄色警告）；`skipUIRestore` 标志位防止 finally 块覆盖倒计时状态
  - `popup.html + popup.css`: 新增 `#antiCrawlSection` 区块及三种样式
- **涉及岗位及工时**：
  | 岗位 | 工时 |
  |------|------|
  | 插件开发（JS/CSS/HTML） | 1.8h |
  | 文档更新 | 0.2h |

**变更文件（5 个）**：
- `chrome-extension/background.js`（+98 行：MIN_SCRAPE_INTERVAL_MS/限流/CAPTCHA 预检/zeros 追踪/GET_SCRAPE_STATUS 扩展/cleanup 扩展）
- `chrome-extension/content.js`（+55 行：detectCaptcha/DETECT_CAPTCHA handler/extractReviews CAPTCHA 优先检查）
- `chrome-extension/popup.js`（+108 行：showAntiCrawlUI/hideAntiCrawlUI/startThrottleCountdown/GET_SCRAPE_STATUS 处理/初始化限流检测）
- `chrome-extension/popup.html`（+10 行：#antiCrawlSection 区块）
- `chrome-extension/popup.css`（+68 行：.anticrawl-* 全套样式）

### Step 14-4: Woot/Amazon 数据一致性验证 + Parser 修复

- **工作量**：~1.0h（Woot API 交叉验证 + helpful_count 缺失修复 + 文档）
- **需求描述**：
  - 对 Woot API (`/review/Reviews/{asin}`) 和 Chrome Extension Amazon DOM 解析器进行跨平台字段交叉验证
  - 验证标的：ASIN B08BX7FV5L（Amazon Fire HD 10 2021），Woot API 返回 10 条评论
  - 交叉验证 4 个核心字段：
    | 字段 | Woot API | 扩展 (Amazon DOM) | 一致性 |
    |------|---------|-------------------|--------|
    | Rating | `OverallRating` int (1-5) | 文本解析 "X.X out of 5 stars" → float | ✅ 一致 |
    | Date (ISO) | `OriginDescription` → strptime | 同一格式 → `new Date()`+regex | ✅ 一致 |
    | Helpful Count | `HelpfulVotes` int | DOM 文本解析 "X people found..." | ❌ **Woot 后端未映射** |
    | Verified | `IsVerifiedPurchase` bool | DOM 元素检测 | ✅ 一致 |
  - 额外发现：`SubmissionDate` 始终为 `/Date(0)/`（不可用）、`Id` 始终为 null、`MediaUrls` 始终为空数组
  - 对 B09BG5L7WW / B0CRY8L7HZ 测试返回 404，确认 Woot API 仅覆盖部分 ASIN
  - 修复：`woot_scraper.py:_parse_woot_review` 新增 `helpful_count`（从 `HelpfulVotes`）和 `image_urls`（从 `ImageUrls`）映射
  - 补充模块 docstring 数据质量说明
- **涉及岗位及工时**：
  | 岗位 | 工时 |
  |------|------|
  | 后端开发（Python） | 0.3h |
  | 数据验证（Playwright MCP + WebFetch） | 0.5h |
  | 文档更新（TEST_LOG + CHANGELOG） | 0.2h |

**变更文件（2 个）**：
- `backend_api/app/services/woot_scraper.py`（+22 行：helpful_count/image_urls 映射 + docstring 数据质量说明）
- `TEST_LOG.md`（+1 行修复记录）

---

## 2026-08-06

### 5.9.6-D 工作包 1/2/3：Scope Governance DoD + Registry Schema 升级 + Scope 校验脚本

- **标题**：正式标签 scope 治理基础设施（零 active 行为变更）
- **工作量**：2.5 天
- **需求描述**：
  - 工作包 1（Scope Governance DoD）：定义交易层/产品层二分模型，三档 scope_policy（transaction_universal / capability_derived / explicit）判定标准，transaction_universal 封闭枚举护栏，capability_derived any-of 语义，负例两种形状及政策最低要求，9 个现有 label 的 scope_policy 落位判断（4 个 transaction_universal + 5 个 capability_derived，0 个 explicit），新增品类/标签零 registry 改动保证机制。产出 `notes/scope-governance-dod.md`（稳定后 git mv 到 docs/）。
  - 工作包 2（Registry schema 升级）：新建 `data/taxonomy/shared/transaction_aspects.yaml`（3 个交易层维度：logistics_issue / customer_service / packaging）+ 解析与校验；扩展 `review_fragment_label_registry.yaml` schema（9 label 各补 scope_policy / required_transaction_dimension / scope_reason / positive_examples / negative_examples / review_status / blocked_contexts / owner_note，review_status 一律 pending）；扩展 `FormalLabelDefinition` dataclass 与 `_load_label()` 解析（fail-closed：缺必填字段 → ValueError 不进 registry）；实现 effective scope 计算（`compute_effective_scope()` + `compute_effective_scope_matrix()`，基于 89 个 taxonomy YAML 构建 sub_category→aspects 索引，lru_cache 缓存，transaction_universal → 89 子类目，capability_derived → any-of 语义，explicit → 空集）。registry_version 保持 5.9.6-A.1 不 bump（决策 f：bump 会使全量 L1 缓存失效，而 active 路径尚未消费 resolver）。
  - 工作包 3（scope 校验脚本）：`scripts/validate_label_scope.py`，6 项校验：禁止 wildcard `*`（硬失败）、transaction_universal 维度枚举校验、capability_derived 命中 taxonomy（永不生效标签→失败）、正例最低要求、负例政策最低 + out_of_scope 反查矩阵验证、explicit 子类目存在性。支持 `--dry-run`（失败非零退出码）和 `--print-matrix`（人验收材料）。解析/输出风格对齐 `scripts/sync_taxonomy.py`。
  - 零 active 行为变更：不改 `resolve_formal_label()` / `_scope_matches()`（工作包 4）、不改 9 个 label 的 `category_keys`/`sub_category_keys` 实际值（工作包 5）、不改 `taxonomy_loader.resolve_aspects()`（工作包 4/6）、不碰 active 路径。
- **涉及岗位及工时**：
  | 岗位 | 工时 |
  |------|------|
  | 后端开发（Python） | 12.0h |
  | 测试（单元测试，25 新增 + 6 回归 + 9 sync_taxonomy 回归） | 4.0h |
  | 文档（DoD + PROGRESS + TEST_LOG + CHANGELOG） | 4.0h |

**变更文件（8 个）**：
- `notes/scope-governance-dod.md`（新增：Scope Governance DoD 规范文档）
- `data/taxonomy/shared/transaction_aspects.yaml`（新增：3 个交易层维度定义）
- `data/taxonomy/registry/review_fragment_label_registry.yaml`（扩展：9 label × 8 新字段）
- `backend_api/app/services/review_fragment_label_catalog.py`（+200 行：TransactionDimension/PositiveExample/NegativeExample dataclass、transaction_aspects.yaml 解析、effective scope 计算）
- `scripts/validate_label_scope.py`（新增：6 项校验 + --print-matrix）
- `backend_api/tests/test_review_fragment_label_catalog.py`（6→31 测试：+25 新增）
- `PROGRESS_V2.md`（工作包 1/2/3 状态更新）
- `TEST_LOG.md`（+1 修复记录）

### 5.9.6-D 工作包 4/5：Resolver fail-closed + 9 标签重标与回归

- **标题**：正式标签 resolver 改为 fail-closed + 现有标签 scope 收窄 + size_chart 维度新增
- **工作量**：3.5 天
- **需求描述**：
  - 工作包 4（Resolver fail-closed）：`resolutionRejectReason` enum（5 值，固定 gate 顺序：unknown_key → not_approved → out_of_scope → blocked_context → insufficient_evidence）；`LabelResolutionResult` dataclass 包装 `label | None + reject_reason | None + is_resolved`；删除 `_scope_matches()` 占位方法；`resolve_formal_label()` 改为 keyword-only 必传 `category_key`/`sub_category_key`，缺失任一 → TypeError；`resolve_formal_label_aspect()` / `resolve_highlight_for_aspect()` 同样必传品类信息；所有实验模块调用方（`_approved_label` / `_approved_formal_label_for_fragment` / `_approved_aspect_key` / `_approved_highlight_label_for_aspect` / `_display_label_for_key` / `_formal_row` / `_route_fragment` / `validate_review_fragment_candidate_artifact_row`）均已更新传递 category/sub_category。新增 14 个 WP4 测试（TypeError/各 reject reason/gate 顺序/empty category/is_resolved/transaction_universal in scope）。evidence gate 推迟到 WP6。
  - 工作包 5（9 标签重标）：16 个 taxonomy YAML（7 apparel + 6 baby + 3 outdoor）新增 `size_chart` aspect（总/正/负/中=0，top_phrases/sample_reviews 空，boundary_note 明确离散码数 + 尺码表定义）；seed 文件 `delta_aspects` 新增 `{key: size_chart, label_zh: 尺码表}`；`confusing_size_chart` 标签 `aspect_keys` 从 `[size_fit]` 改为 `[size_chart]`，boundary_note/scope_reason/negative_examples/owner_note 同步更新，effective scope 从 63 子类目收窄到 16；`category_keys`/`sub_category_keys` 从 registry YAML（9 label）、`FormalLabelDefinition` dataclass、`_load_label()` 构造函数三处删除；validator `_check_no_wildcard_in_scope` 从 `"*" in label.category_keys` 改为 `hasattr(label, "category_keys")`（字段必须不存在）；`registry_version` 升至 `5.9.6-D.1`（decision j，预期 L1 缓存全量失效，旧缓存通过 5.9.6-B.1 语义版本过滤自动 miss）；`backend_api/app/core/aspect_taxonomy.py` FURNITURE_ASPECTS 新增 `size_chart: 尺码表`；修复 confusing_size_chart 负例 sub_category `cosequin for dogs` → `Cosequin for Dogs`（大小写匹配 taxonomy key）。
- **涉及岗位及工时**：
  | 岗位 | 工时 |
  |------|------|
  | 后端开发（Python） | 20.0h |
  | 测试（单元测试，14 新增 WP4 + 1 新增 WP5 + 44 回归 + 14 cache 回归 + 9 sync 回归） | 6.0h |
  | 文档（PROGRESS + TEST_LOG + CHANGELOG + acceptance package） | 4.0h |

**变更文件（13 个）**：
- `backend_api/app/services/review_fragment_label_catalog.py`（+~120 行：enum/dataclass/resolver fail-closed/category_keys 删除）
- `backend_api/app/services/review_fragment_candidate_multimodule.py`（8 个 call site 更新）
- `backend_api/app/core/aspect_taxonomy.py`（+size_chart，闭合 19→20 类）
- `data/taxonomy/registry/review_fragment_label_registry.yaml`（9 label 删 category_keys/sub_category_keys、confusing_size_chart 改 aspect_keys、registry_version bump、cosequin→Cosequin）
- `data/taxonomy/categories/*/` 16 个 YAML（+size_chart aspect）
- `data/taxonomy/seeds/apparel.yaml`、`baby.yaml`、`outdoor.yaml`（+size_chart delta_aspects）
- `scripts/validate_label_scope.py`（hasattr 替换 list 检查）
- `backend_api/tests/test_review_fragment_label_catalog.py`（+15 测试，45 total）
- `PROGRESS_V2.md`、`TEST_LOG.md`、`需求记录/CHANGELOG.md`（文档更新）

### 5.9.6-B.1 缓存语义版本化与 L2 下线

- **标题**：L1 缓存命中校验纳入语义版本 + 删除 L2 短文本默认结果分支
- **工作量**：0.5 天
- **需求描述**：
  - Bug 修复：L1 缓存 key 仅校验静态 `ANALYZER_VERSION="v4_deep"`，prompt/taxonomy/registry/model 变更后旧缓存仍命中，导致 5.9.6-D scope 治理成果在 5.9.7 验收时不可见。修复：`get_analyzed_by_content_hash()` 增加 `prompt_version` / `taxonomy_version` / `registry_version` / `model_name` 四个参数，通过 PostgreSQL JSONB `->>` 操作符做 SQL 层版本过滤；写入侧 `aspects_json` 同步补全三个新字段（`prompt_version` 已存在）；无需 migration（复用已有 JSONB 列）。
  - Bug 修复：删除 L2 短文本默认结果分支（`_check_l2` + `L2_MAX_CONTENT_LENGTH`）。L2 对 ≤10 字 + 评分 1-2/5 的评论跳过 LLM 直接给空结果，与 5.9.3 证据门冲突。例如 `"Leaks."` 6 字 1 星含明确产品问题信号，但系统未读原文即产出标签。`apply_cache` 链路从 L1→L2→L3 简化为 L1→L3。
  - 新增 `taxonomy_loader.get_taxonomy_version()` 函数，按 sub_category 查 `category_aspect_taxonomy.taxonomy_version`
  - 新增 14 个单元测试（SQL 版本过滤构造 + L2 已删除 + observability + taxonomy 解析）
- **涉及岗位及工时**：
  | 岗位 | 工时 |
  |------|------|
  | 后端开发（Python） | 3.5h |
  | 测试（单元测试） | 1.0h |
  | 文档更新（PROGRESS + TEST_LOG + CHANGELOG） | 0.5h |

**变更文件（6 个）**：
- `backend_api/app/services/analysis_cache.py`（-55 行：删除 L2 分支/常量/stats，L1→L3 直连）
- `backend_api/app/services/taxonomy_loader.py`（+45 行：新增 `get_taxonomy_version()`）
- `review_analyzer/database.py`（+50 行：`get_analyzed_by_content_hash` 增加 4 个版本参数 + JSONB 过滤）
- `workers/jobs.py`（+30 行：导入 registry/taxonomy version，L1 查询传入四版本，write 侧写入三新字段）
- `backend_api/tests/test_cache_semantic_versioning.py`（新增 14 个测试）
- `TEST_LOG.md`（追加修复记录）

### 5.9.6-D 工作包 6/7/8：Active 入口 resolver shadow 接线 + 审核回流 + CI 门禁 + 审核页

- **标题**：完成 5.9.6-D 全部工作包（零 active 行为变更 + 基础设施就位）
- **工作量**：5.5 天
- **需求描述**：
  - **决策 l（删除 Gate 5）**：删除 `_resolve_formal_label_impl()` 的 `evidence_span`/`review_text` 参数和 Gate 5 代码块，docstring 写入「调用方先过 5.9.3 证据门再调 resolver」契约。保留 `INSUFFICIENT_EVIDENCE` 枚举（调用方产出）。3 个新测试断言传 evidence 参数 → TypeError。
  - **决策 m（三态 Feature Flag）**：新建 `label_registry_frontstage.py`，三态 off（默认）/shadow（旧路径决定展示、resolver 并行记录差异）/enforce（5.9.7 交付）。遵循现有 flag 惯例（frozen dataclass + `_from_env()` + `cache_key()`），fail-closed 校验。`LABEL_REGISTRY_FRONTSTAGE_MODE` 环境变量控制，默认 off。
  - **WP6（Active 入口 shadow 接线）**：`specific_issue.py` 的 `decorate_comment_customer_labels()` 新增 `label_registry_flag` 参数 + `_run_label_registry_shadow_pass()` 后处理（遍历 canonical issue/highlight key 调 resolver、记录 `ResolverShadowDiff`、跳过 UNKNOWN_KEY 拒绝）；`analysis.py` session + aggregated results 两处 handler 创建 flag 传入 decorator + 缓存 key 纳入 flag；`export.py` module export handler 同样接入。flag off 时为零开销 no-op。
  - **WP7（审核回流）**：新建 `label_registry_audit.py`（`AuditEvent` dataclass，3 种 event_type：resolver_reject/shadow_diff/human_flag，DB 读写 + 批量写入，fail-open）；新建 `label_registry_proposal.py`（`RegistryProposal` dataclass，4 种封闭 action_type：scope_adjust/alias_merge/blocked_rule/negative_example，DB 读写 + 状态更新 + 4 个生成助手）；新建 migration SQL `060_label_registry_audit_and_proposal.sql`（两张表：`label_registry_audit_events` + `label_registry_proposals`，待 Erika 批准执行）。
  - **WP8（CI 门禁 + 审核页）**：`ci.yml` 新增 `label-scope-validate` + `resolver-gate-tests` 两个 job（scope 校验 dry-run、wildcard 禁止、resolver TypeError、各 reject reason 触发、effective scope 数量断言、evidence 参数拒绝）；新建 `/settings/label-review` 后端 API（GET proposals 列表 + POST review approve/reject/merge，merge 时写回 YAML → 验证 → 失败回滚 → 生成负例回归测试）+ `main.py` 注册 router；新建前端页面（状态筛选 tabs、approve/reject/merge 三按钮、proposal_data JSON 展示、reviewer note）；输出验收包文档 `docs/5.9.6-D-wp6-8-acceptance-package.md`（变更清单、权限约束、部署检查清单、预期行为、已知限制、验收步骤）。
- **涉及岗位及工时**：
  | 岗位 | 工时 |
  |------|------|
  | 后端开发（Python） | 28.0h |
  | 前端开发（Next.js） | 4.0h |
  | DevOps（CI） | 2.0h |
  | 测试（单元测试，48 resolver tests all pass） | 4.0h |
  | 文档（PROGRESS + CHANGELOG + 验收包） | 4.0h |

**变更文件（14 个）**：
- `backend_api/app/services/review_fragment_label_catalog.py`（删除 Gate 5 + docstring 契约）
- `backend_api/app/services/label_registry_frontstage.py`（新增：三态 flag + ResolverShadowDiff + 日志 flush）
- `backend_api/app/services/specific_issue.py`（decorator 接入 shadow pass + _run_label_registry_shadow_pass）
- `backend_api/app/routes/analysis.py`（session + aggregated handler 创建 flag + 缓存 key 纳入）
- `backend_api/app/routes/export.py`（module export handler 创建 flag）
- `backend_api/app/services/label_registry_audit.py`（新增：AuditEvent + DB 读写 + 批量）
- `backend_api/app/services/label_registry_proposal.py`（新增：RegistryProposal + 4 种 action_type + 生成助手）
- `migrations/060_label_registry_audit_and_proposal.sql`（新增：2 张表，待执行）
- `.github/workflows/ci.yml`（+2 job：label-scope-validate + resolver-gate-tests）
- `backend_api/app/routes/label_review.py`（新增：审核页 API + YAML write-back + rollback）
- `backend_api/app/main.py`（注册 label_review_router）
- `frontend/src/app/settings/label-review/page.tsx`（新增：审核页前端）
- `backend_api/tests/test_review_fragment_label_catalog.py`（+3 测试，48 total）
- `docs/5.9.6-D-wp6-8-acceptance-package.md`（新增：验收包）

### 2026-08-07 Label Registry Review 并入 Label Calibration + 权限收紧为 admin-only

**变更摘要**：将独立的 `/settings/label-review` 审核页并入 `/settings/golden-set` 做成 tab 排版（Tab 1: Label Calibration Golden Set + Tab 2: Label Registry Review），后端两个审核 endpoint 从 `get_current_user` 收紧为 `get_admin_user`，旧 URL 保留 redirect。

- **前端**：
  - 新建 `frontend/src/components/label-calibration/golden-set-tab.tsx`（从 golden-set page 抽出 body，~260 行）
  - 新建 `frontend/src/components/label-calibration/registry-review-tab.tsx`（从 label-review page 抽出 body，~220 行，逻辑不变）
  - 重写 `frontend/src/app/settings/golden-set/page.tsx` 为 admin-gated 外壳（~50 行）：admin 校验 + h1 + `PageTabs` 两个 tab
  - 替换 `frontend/src/app/settings/label-review/page.tsx` 为 server component `redirect("/settings/golden-set")`
  - i18n `messages/{en,zh}.json` `settings.goldenSet` 下新增 2 键：`pageTitle`、`tabRegistryReview`

- **后端**：
  - `backend_api/app/routes/label_review.py`：import `get_admin_user` 替换 `get_current_user`，两个 endpoint 的 `Depends` 改为 `Depends(get_admin_user)`
  - 新增 `backend_api/tests/test_label_review_admin_only.py`：2 个 403 测试（GET proposals + POST review 以非 admin 身份请求均返回 403）

- **影响范围**：侧边栏入口不变（本就是 `adminOnly: true`）；review tab 保持英文硬编码（admin-only 内部页，本批次不做双语）；旧 URL 自动 redirect 不破坏书签/文档引用

- **验证**：
  - ruff check PASS（2 文件）
  - pytest 459 passed（含新 2 tests），11 pre-existing failures（无关联）
  - frontend tsc typecheck PASS
  - frontend next build PASS

### 2026-08-07 5.9.6-D WP9 验收裁决返修（4 批次 · 7 bugs + P0 gate + reflux pipeline + 10 文档修正）

**变更摘要**：根据 WP9 验收裁决中的工程侧独立核验结果，执行 4 批次返修，修复 7 个实现 bug（Bug 1-6 + Bug 5b）、修复 P0 门禁静默失效、恢复中断的回流链路、修正验收包 10 项文档问题。4 个独立 commit（`c5bf769` `c09f751` `8f9b849` `54602c3`），不包含批次 2 和 registry_version 升版。

**需求描述**：
- 批次 0（P0 门禁，commit `c5bf769`）：新增 `SCOPE_UNAVAILABLE` 枚举值 + Gate 3a/3b 拆分 + `assert_taxonomy_index_healthy()` 启动自检 + CI Check 7（exact 89 sub_category）+ 8 个新测试（48→56）
- 批次 1a（route + 校验层，commit `c09f751`）：`get_proposal_by_id()` 精确查询 + merge 返回 501 禁用 + `alias_merge` 跨 `label_type` 硬阻断 + 路径 `parents[4]→parents[3]` 修复
- 批次 1b（shadow 落库，commit `8f9b849`）：`_shadow_diffs` ContextVar 隔离（Bug 6）+ audit persist 中间件 + `generate_label_proposals.py`（Bug 5b）+ `LABEL_REGISTRY_AUDIT_PERSIST` 独立开关
- 批次 3（文档修正，commit `54602c3`）：验收包 10 项修正（URL/tab 路径、测试数、migration 状态、摘要注解、fiction 声明、CI lock、7+2 修正、formal_module 定义、checklist 裁决）

**涉及岗位及工时**：

| 岗位 | 工作内容 | 工时 |
|------|---------|------|
| 后端（catalog resolver） | Bug 1 P0 gate + Bug 0-3 启动自检 + new tests (8) | 3.0h |
| 后端（label review route） | Bug 3/4 + proposal CRUD + alias_merge guard | 2.0h |
| 后端（frontstage middleware） | Bug 5/6 ContextVar + audit persist + proposal generator | 3.0h |
| DevOps（CI + validate） | CI Check 7 + validate_label_scope.py 扩展 | 0.5h |
| 文档（验收包修正） | 10 项文档修正 | 0.5h |
| 测试（回归验证） | 56 tests + ruff + validate --dry-run + repro | 1.5h |
| 文档（TEST_LOG + PROGRESS + CHANGELOG） | 3 文档更新 | 1.5h |

**变更文件（10 个）**：
- `backend_api/app/services/review_fragment_label_catalog.py`（SCOPE_UNAVAILABLE + Gate 3a/3b + assert_taxonomy_index_healthy + EXPECTED_TAXONOMY_SUB_CATEGORY_COUNT）
- `backend_api/app/main.py`（startup health check + /health 暴露 + shadow middleware 注册）
- `scripts/validate_label_scope.py`（Check 7: exact 89 sub_category 断言）
- `.github/workflows/ci.yml`（scope_unavailable 覆盖率条目）
- `backend_api/tests/test_review_fragment_label_catalog.py`（8 new tests, 48→56, 删除 unused import）
- `backend_api/app/routes/label_review.py`（get_proposal_by_id + merge 501 + parents fix）
- `backend_api/app/services/label_registry_proposal.py`（新增 get_proposal_by_id + alias_merge 跨类型阻断）
- `backend_api/app/services/label_registry_frontstage.py`（ContextVar 隔离 + audit persist + shadow middleware）
- `scripts/generate_label_proposals.py`（新增：audit → proposal 聚合脚本）
- `docs/5.9.6-D-wp9-erika-acceptance-package.md`（新增：10 项修正后的验收包）

**验证结果**：
- 56 tests PASS, ruff clean, validate_label_scope.py --dry-run 0 failures
- scope matrix unchanged: 89/89/89/89/5/5/16/1/1
- Bug 1 repro: 空 taxonomy → all 9 labels return SCOPE_UNAVAILABLE (was: OUT_OF_SCOPE)

---

## 2026-08-07 5.9.7 小样本验收（离线 resolver · 45 条真实评论）【2026-08-07 修正：撤回错 P0】

**工作量**：2-3 小时（脚本编写 + 执行 + 深度分析 + 报告撰写 + 修正）

**需求描述**：
执行 5.9.7 小样本验收任务：从 clueai-dev 取 45 条真实评论（waders 15 + 上衣 15 + 床架 15），走离线 resolver 验证 9 个正式标签的 scope gating、跨类目负例、alias 解析、元数据一致性、waders 配件标签治理，以及行动中心 handoff 预检。

**验收结果**：
- Scope gating ✅：全部 5 个 capability_derived 标签在非适用类目正确拒绝（165 out_of_scope，0 scope_unavailable）
- 跨类目负例 ✅：上衣/床架 两个 taxonomy profile 确认防水/配件/尺码表标签正确 out_of_scope
- Alias 解析 ✅：16/16 正确解析
- Metadata ✅：registry_version=5.9.6-D.1、review_status=pending、formal_module 路由正确
- Waders 配件标签 ✅：保持 approved，不降级
- **原"证据门禁缺失"P0 已撤回**（2026-08-07 修正）：离线脚本无条件调全部 label key 造成假象，生产 TOP10 门禁已有 evidence 校验
- **真实发现 ⚠️**：cluster 传播污染 — waders 96% occurrence 的 evidence_span 来自 cluster 代表而非自身原文（案例 id=508 真实漏水投诉拿到反向证据、漏标），TOP10 被掏空

**涉及岗位及工时**：
- 后端/验收：2-3 小时

**产出物**：
- `docs/5.9.7-small-sample-acceptance-report.md`（验收报告）
- `scripts/5.9.7_offline_resolver_acceptance.py`（离线验收脚本）
- `scratch/5.9.7_acceptance_verdicts.csv`（逐条判定表）
- 更新 `PROGRESS_V2.md` / `TEST_LOG.md` / `需求记录/CHANGELOG.md`

---

## 2026-08-07 5.9.7-T1 生产 cluster 传播占比统计

**工作量**：0.5 天（脚本编写 + 本地验证 + 生产执行 + 数据分析 + 定级建议）

**需求描述**：
5.9.7 小样本验收发现 waders 96% occurrence 的 evidence_span 来自 cluster 传播而非自身原文（cluster 传播污染），需在生产数据上量出真实传播占比以决定问题定级（P0/P1/P2）。编写纯只读统计脚本 `scripts/measure_cluster_propagation.py`，在 dev 和生产分别执行，统计全库 cluster_propagated 占比、按 sub_category 分组传播占比、evidence_span 交叉验证。

**生产结果**：
- 全库传播占比：20.2%（542/2,680），远低于 dev 的 84.1%
- 传播证据污染率：99.3%（2,071/2,086 条 evidence_span 不在目标评论原文中）
- 直接 LLM 证据不匹配率：仅 3.7%（157/4,249），正常误差
- waders 传播占比 52.5%（受灾最重），USB C Charger Block 和 家具家居 均为 0%
- **定级：P1**。不构成 P0（全局仅 20.2%、门禁正确拦截污染数据），不降 P2（waders 52.5% 传播导致 TOP10 代表性不足）

**修复方向**：收紧 `PROPAGATION_SIMILARITY_THRESHOLD`（0.88→0.92/0.95）或对传播结果加 evidence 回退校验（evidence_span 不在原文中则降级为 needs_llm）

**涉及岗位及工时**：
- 后端/数据分析：0.5 天

**产出物**：
- `scripts/measure_cluster_propagation.py`（只读统计脚本，commit `44a889e`）
- 更新 `PROGRESS_V2.md`

## 2026-08-07 5.9.7-T2 cluster 传播污染修复 — 评分守卫

**工作量**：S（0.5 天 · 单一服务三个文件 · 逻辑简单 · 无新接口/表结构）

**需求描述**：
5.9.7 验收发现 waders 96% occurrence 的 evidence_span 来自 cluster 0 代表 id=479（好评）传播，导致 id=508（真实漏水投诉）拿到反向证据「stayed warm, dry and comfortable」、漏标 `water_leaks_through`。根因：`propagate_cluster_results()` 只检查簇内余弦相似度 ≥ 0.88，无评分/情感一致性检查，好评差评混入同一簇后标签+证据被无条件传播。

**修复方案**：
1. `clustering.py` 新增模块级常量 `RATING_GUARD_THRESHOLD = 2.0`（5 星制，|5-3|=2 为边界），可通过 `CLUSTER_RATING_GUARD_ENABLED=false` 全局关闭紧急回退
2. `propagate_cluster_results()` 新增 `rating_guard_threshold` 参数（默认 2.0，None 关闭）
3. 传播前比较成员与代表 rating：绝对差值 ≥ 阈值时不传播 aspects/pain_points/highlights，退回 needs_llm（复用现有 low_cluster_similarity 机制）
4. 新增 `test_clustering_rating_guard.py`（14 个 focused tests）

**成本影响**（clueai-dev waders cluster 0 数据）：
- 阈值 2.0：9/78（11.5%）成员被拦截退回 needs_llm，69/78 仍通过传播节省 LLM
- 生产全局预估：LLM 调用增加 ~10-15%（全库传播 20.2% × 约 50% 含评分冲突）
- 修复只对新分析生效，数据库已有脏数据不变

**涉及岗位及工时**：
- 后端开发/算法工程师：0.5 天

**产出物**：
- `backend_api/app/services/clustering.py`（新增 RATING_GUARD_THRESHOLD + id_to_rating 映射 + 评分守卫逻辑 + 环境变量开关）
- `backend_api/tests/test_clustering_rating_guard.py`（14 个 focused tests）
- 更新 `TEST_LOG.md` + `PROGRESS_V2.md`

---

## 2026-08-07 5.9.6-C 受众拆分 + `other` 占比告警下架

### Bug 修复：taxonomy 覆盖率告警泄漏给客户 + 5.9.6-C 按受众拆为 C1/C2

- **工作量**: S（2 个后端文件 + 1 个新测试文件 + 3 个文档，约 0.5 人天）
- **状态**: ✅ 内部告警已下架，9 测试通过；C2 内部校准链路已排期未开始

**需求描述**：
Erika 质疑 5.9.6-C 任务描述「展示原文证据、低置信提醒和 `other` 占比」——认为 `other` 和置信度不该给客户看，应该通过 label calibration 页给她审批后回流成正确标签。复核确认该读法正确，原描述把三个受众不同的信息混为一句话。

**定性**：
- **原文证据** → 客户价值。客户看到标签下挂真实评论才信这个标签，该展示。
- **低置信提醒** → 模型内部状态。客户只会读成「你们的产品不准」，无法据此行动，不该展示。
- **`other` 占比** → 我方 taxonomy 资产债务。客户看到等于自曝分类覆盖不足，不该展示。

**发现的线上问题**：
`other` 占比此前已对客户可见——`taxonomy_coverage_monitor` 把「品类 X 的 aspect 覆盖不足：'other' 占比 23.4%（阈值 15%）」写入 `sessions.warnings_json`，结果页无条件把 `warnings_json` 全量渲染成黄色横幅。该横幅由 Step 3 监控链路引入，早于 5.9.6-C，一直在线。

**修复方案**：
1. `taxonomy_coverage_monitor.py` 新增 `WARNING_TYPE_TAXONOMY_COVERAGE_LOW` 常量 + `INTERNAL_ONLY_WARNING_TYPES` frozenset + `filter_customer_visible_warnings()`
2. fail-closed 设计：非 dict / 缺 `type` / `type` 为空的条目一律按内部丢弃，防止未来新增内部告警类型时忘记登记就默认泄漏
3. `analysis.py` 的 `_session_payload()` 单点过滤。**选后端单点而非改前端渲染**：前端改法只挡住页面，导出和其他 payload 消费方仍会泄漏
4. **内部信号未减弱**：DB `warnings_json` 写入、`trace.record_warning`、飞书推送三条链路全部保持原样，只有客户读路径隐藏

**核实结论**：置信度本来就未出现在客户 UI，只在导出文件的 audit sheet 列（`Audit Issue Confidence` / `Audit Highlight Confidence`），这一半无需改动。

**任务拆分与排期**：
- **5.9.6-C1 客户前台证据展示**（留在 5.9.7-T3 第三块，0.5 天）：只做原文证据，TOP10 每行可展开代表性评论。本次已完成其中「内部告警下架」部分。
- **5.9.6-C2 内部校准信号接入**（单独排，1.5-2 天）：不并入 T3，因需新增 `new_aspect` 提案动作，并入会让 enforce 灰度被校准页开发阻塞。

**C2 的实际工作量来源（本次发现的实现缺口）**：
WP7/WP8 的回流链路只覆盖 scope 治理那一半——`generate_label_proposals.py` 只读 `resolver_reject` / `shadow_diff`；`human_flag` 事件类型已定义但**全仓库零个生产者**；`other` 占比走完全独立的 `taxonomy_coverage_monitor` → `sessions.warnings_json` + 飞书链路，从未进 audit / proposal 表。即「other → Erika 审批 → 回流成正确标签」这条路在 C2 之前是断的。现有 4 种提案动作（scope_adjust / alias_merge / blocked_rule / negative_example）都只治已有标签的 scope，没有「新建 aspect」这条路径，而 `other` 高占比恰恰指向「这个品类缺维度」。

**验证结果**：
- 新增 `test_taxonomy_coverage_customer_visibility.py` 6 测试全绿
- 回归 `test_analysis_results_llm_fallback` + `test_taxonomy_routes` 3 测试通过
- ruff check clean，`git diff --check` 通过

**涉及岗位及工时**：
- 后端开发：0.3 天（告警过滤 + 测试）
- 产品经理：0.2 天（受众拆分定性 + 排期决策）

**产出物**：
- `backend_api/app/services/taxonomy_coverage_monitor.py`（内部告警类型登记 + fail-closed 过滤函数）
- `backend_api/app/routes/analysis.py`（`_session_payload()` 单点过滤）
- `backend_api/tests/test_taxonomy_coverage_customer_visibility.py`（6 个 focused tests）
- 更新 `PROGRESS_V2.md`（C1/C2 任务行拆分 + 受众拆分决策段 + 验收表两行）+ `TEST_LOG.md`

---

## 2026-08-07 海外合规模型链路改造（DeepSeek/Qwen 下架 → Gemini）

### 需求：LLM fallback 链去中国厂商化 + 附带修复 L1 缓存 model 门

- **工作量**: S（7 个后端文件 + 2 个测试文件改动，无 migration，约 0.5 人天）
- **状态**: ✅ 代码完成，回归 0 新增失败；⚠️ Gemini 付费未开通，兜底链暂不可用

**需求描述**：
Erika 提出替换 DeepSeek 与删除 Qwen，改为两层模型链。原因是这两家（深度求索 / 阿里云）都是中国厂商，海外用户的评论数据流向中国不满足合规要求 —— 8.4 当时只在这三家里换 locale 优先级，实际的 provider 地理分散只有 OpenAI 一家。

**选型结论**：Gemini 2.0 Flash 作为唯一兜底

| 维度 | 值 |
|------|-----|
| 定价 | $0.10/M input + $0.40/M output（比 DeepSeek ¥1/¥8 与 GPT-4o-mini $0.15/$0.60 都便宜） |
| 接入成本 | 零代码改动 —— Google 提供 OpenAI 兼容端点 `generativelanguage.googleapis.com/v1beta/openai/`，只需新增一个 `ModelConfig` |
| JSON 模式 | 原生支持 `response_format: {"type": "json_object"}`，满足 annotate v2.4 的结构化输出要求 |
| 合规 | Google 基础设施，与 OpenAI 互为独立云，构成真正的双 provider 容灾 |

未选 Claude Haiku 4.5：JSON 可靠性最好但 Anthropic API 非 OpenAI 兼容，需引入 OpenRouter 中间层，增加依赖与延迟。

**改动内容**：
1. `llm_router.py` — 新增 `_GEMINI`（threshold=3 / cooldown=60s），删除 `_QWEN` 与 `_DEEPSEEK`，`MODELS_EN` = `MODELS_ZH` = `[_OPENAI, _GEMINI]`
2. 费率表两处（`deep_analyzer._estimate_cost` + `database.MODEL_COST_PER_MILLION`）追加 gemini 条目；**保留 deepseek/qwen 费率**供历史 `llm_usage` 行的成本查询不失真
3. `database._provider_from_model_name()` 新增 gemini 分支
4. `insight_engine` 默认 `RESULTS_AI_DISABLED_PROVIDERS` 从 `deepseek` 改 `gemini`（结果页 AI 增强默认只用主模型，语义等价迁移）
5. `analyzer.get_api_key()` 兜底 env 从 `DEEPSEEK_API_KEY` 改 `OPENAI_API_KEY`

**附带修复的真 bug（L1 缓存 model 门永不命中）**：
排查 `CACHE_MODEL_NAME` 时发现写入侧与读取侧不同构 —— 写入侧 `jobs.py:995` 存的是 `router_completion()` 返回的 **model_id**（`llm_router.py:390` `return resp, model.model_id` → `"gpt-4o-mini"`），读取侧 `database.py:1571` 却用 provider 名 `"deepseek"` 做 `aspects_json->>'model_name' = %s` 等值比较，结果恒为假。该门自 5.9.6-B.1 上线起一直把 L1 缓存判死，另 3 个版本门（prompt / taxonomy / registry）正常工作。改为 `CACHE_MODEL_NAME = "gpt-4o-mini"` 后 L1 缓存真正生效。Gemini 兜底期间产出的结果按语义判 miss（不跨模型复用分析结果），符合预期。

**验证结果**：
- Gemini API key 连通性：认证通过，返回 429 `limit: 0` → key 有效但**免费层输入配额为 0（未开付费）**
- `backend_api/tests/` 487 passed / 11 failed；11 项失败经 HEAD 干净 worktree 基线比对确认为改动前既有失败（waders taxonomy aspect_count 22≠21 + review_fragment_candidate 10 项），与本次无关
- 受影响的 focused tests：`test_cache_semantic_versioning` + `test_analysis_results_llm_fallback` + `test_global_cache` 共 23 passed
- ruff check 全部改动文件 clean

**遗留阻塞**：
Gemini 需在 Google AI Studio 绑卡开通付费，否则 fallback 链实际退化为 OpenAI 单模型，容灾能力弱于改造前的三模型链。

**涉及岗位及工时**：
- 算法工程师：0.2 天（模型选型对比 + 费率核算 + API 连通性验证）
- 后端开发：0.25 天（router 改造 + 缓存门 bug 排查修复 + 测试适配）
- DevOps：0.05 天（`deploy/.env` 注入 `Gemini_API_KEY`，确认 docker-compose `env_file` 已覆盖 api/worker 两个容器）

**产出物**：
- `backend_api/app/services/llm_router.py`（`_GEMINI` 新增 + `_QWEN`/`_DEEPSEEK` 删除 + 双模型链）
- `backend_api/app/services/deep_analyzer.py`、`review_analyzer/database.py`（费率 + provider 识别）
- `review_analyzer/insight_engine.py`、`review_analyzer/analyzer.py`、`review_analyzer/rag.py`（默认值与文案迁移）
- `workers/jobs.py`（`CACHE_MODEL_NAME` 同构修复）
- `backend_api/tests/test_cache_semantic_versioning.py`、`test_analysis_results_llm_fallback.py`（断言同步）

---

## 2026-08-10 Gemini 模型 ID 更新（gemini-2.0-flash → gemini-flash-latest）

### 需求：Google 下线旧模型后更新模型 ID + 重新验证 API key

- **工作量**: S（3 个文件改动，无 migration，约 0.1 人天）
- **状态**: ✅ 完成待部署

**需求描述**：
2026-08 测试 Gemini API key 时发现 `gemini-2.0-flash` 在 OpenAI 兼容端点返回 404 "no longer available"，`gemini-2.5-flash` / `gemini-2.5-pro` 同样 404，仅 `gemini-flash-latest`（Google 的 latest 别名）可用。同时候 Erika 重新提供了已开通付费的 API key。

**改动内容**：
1. `llm_router.py` — `_GEMINI.model_id` 从 `gemini-2.0-flash` 改为 `gemini-flash-latest`
2. `deep_analyzer._estimate_cost()` + `database.MODEL_COST_PER_MILLION` — key 同步更新

**为什么使用 `gemini-flash-latest`（别名而非固定版本）**：
Google 的 OpenAI 兼容端点模型生命周期较短，固定版本（如 `gemini-2.0-flash`）可能随时被下线。`-latest` 别名始终解析为最新稳定 Flash 模型，避免未来再次出现 404。作为 fallback 模型，行为微小变化可接受。

**验证结果**：
- Gemini API 连通性：认证通过，JSON 模式/中文/结构化输出均正常
- `backend_api/tests/` focused tests：23 passed（test_cache_semantic_versioning + test_analysis_results_llm_fallback + test_global_cache）
- ruff check 全部改动文件 clean

**涉及岗位及工时**：
- 后端开发：0.1 天（模型 ID 更新 + 测试适配 + API 验证）

**产出物**：
- `backend_api/app/services/llm_router.py`（model_id）
- `backend_api/app/services/deep_analyzer.py`（费率 key）
- `review_analyzer/database.py`（费率 key）
