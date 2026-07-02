# 配额维度表（Single Source of Truth）

> **用途**：所有套餐配额规则的唯一权威来源。代码（[quota.py](review_analyzer/)）、UI 提示、营销页都从这里取数。
> **修改原则**：调整任何配额前必须先改本表，再改代码——避免代码与文档脱节。
> **配套文档**：成本利润核算见 [COST_PROFIT.md](COST_PROFIT.md)，开发路线见 [PROGRESS_V2.md](PROGRESS_V2.md) V4-T2。

---

## 一、维度分类

| 类别 | 包含维度 | 限制目的 |
|------|------|------|
| LLM 成本类 | 评论分析、Ask reviews、广告文案 | **控成本**（每次调用都烧钱） |
| 资源软限类 | Excel 导出、多产品对比、Webhook 数 | **商业升级钩子**（无 LLM 成本） |
| 规则配置类 | 全局预警规则、产品预警规则 | **商业升级钩子**（防代运营薅羊毛） |
| 安全硬限类 | 单文件上传条数、API 调用频率 | **技术保护**（防灌爆队列） |
| V5 预留类 | 谷歌插件抓取、API 调用 | **未来增值** |

---

## 二、配额维度总表

> 数值约定：`-1` 表示不限；`null` 表示该维度对该套餐不开放（功能锁）。
> 周期约定：`monthly` 自然月重置；`concurrent` 同时持有；`per_request` 单次请求；`forever` 累计永久。

### 2.1 LLM 成本类

| key | 中文名 | 单位 | 周期 | Free | Pro ¥99 早鸟 | Pro ¥199 | Team ¥499 | 限制类型 | LLM 成本 | 触发位置 |
|------|------|------|------|------|------|------|------|------|------|------|
| `review_analyze` | 评论分析 | 条 | monthly | 1500 | 5000 | 10000 | 50000 | 硬限 | ¥0.0037/条 | [analyzer.py:284](review_analyzer/analyzer.py#L284) |
| `ask_review` | Ask reviews | 次 | monthly | 10 | 50 | -1 | -1 | 硬限 | ¥0.0107/次 | [rag.py:241](review_analyzer/rag.py#L241) |
| `ad_copy` | 广告文案生成 | 次 | monthly | 10 | 100 | 300 | -1 | 硬限 | ¥0.0053/次 | [copywriter.py:357](review_analyzer/pages/copywriter.py#L357) |
| `translate` | 分析结果翻译 | 次 | daily | 20 | 200 | 200 | 500 | 硬限 | ¥0.002~0.02/次 | [translate.py](backend_api/app/routes/translate.py) |

> "1 次广告文案 = 1 个平台 × 1 种广告类型 × 1 个变体"，多平台/多变体批量生成按实际调用次数累计。

### 2.2 资源软限类

| key | 中文名 | 单位 | 周期 | Free | Pro ¥99 早鸟 | Pro ¥199 | Team ¥499 | 限制类型 | LLM 成本 | 触发位置 |
|------|------|------|------|------|------|------|------|------|------|------|
| `excel_export` | Excel 导出 | 次 | monthly | 10 | -1 | -1 | -1 | 软限 | ¥0 | [analysis_export.py](review_analyzer/analysis_export.py) |
| `compare_products` | 多产品对比 | 个 | concurrent | 2 | -1 | -1 | -1 | 软限 | ¥0 | [compare.py:48](review_analyzer/pages/compare.py#L48) |
| `webhook_count` | Webhook 数 | 个 | forever | 3 | -1 | -1 | -1 | 软限 | ¥0 | [settings.py:109](review_analyzer/pages/settings.py#L109) |
| `product_count` | 产品数 | 个 | forever | -1 | -1 | -1 | -1 | 不限（Phase 1） | ¥0 | [upload.py:419](review_analyzer/pages/upload.py#L419) |

> Phase 2（≥ 100 付费用户）启用 `active_product_count`（30 天活跃产品）：Pro ¥199 → 10、Team ¥499 → 50。

### 2.3 规则配置类

| key | 中文名 | 单位 | 周期 | Free | Pro ¥99 早鸟 | Pro ¥199 | Team ¥499 | 限制类型 | LLM 成本 | 触发位置 |
|------|------|------|------|------|------|------|------|------|------|------|
| `global_rules` | 全局预警规则 | 条 | forever | 3 | -1 | -1 | -1 | 软限 | ¥0 | [notifier.py:212](review_analyzer/notifier.py#L212) |
| `product_rules` | 每产品预警规则 | 条 | forever | 1 | -1 | -1 | -1 | 软限 | ¥0 | [notifier.py:317](review_analyzer/notifier.py#L317) |

### 2.4 安全硬限类（不分套餐，全局生效）

| key | 中文名 | 单位 | 周期 | Free | Pro 全档 | 限制类型 | 触发位置 | 备注 |
|------|------|------|------|------|------|------|------|------|
| `upload_rows_per_file` | 单文件上传条数 | 条 | per_request | 500 | 5000 | 硬限 | [upload.py](review_analyzer/pages/upload.py) | 防灌爆队列 |
| `webhook_rate_limit` | 同类预警合并窗口 | 秒 | per_request | 60 | 60 | 硬限 | [notifier.py](review_analyzer/notifier.py) | 飞书/钉钉/企微 20 条/分限制 |

### 2.5 V5 预留类（功能未上线，配额预定义）

| key | 中文名 | 单位 | 周期 | Free | Pro ¥99 早鸟 | Pro ¥199 | Team ¥499 | 启动条件 |
|------|------|------|------|------|------|------|------|------|
| `extension_scrape_per_request` | 谷歌插件单次抓取 | 条 | per_request | 100 | 1000 | 1000 | 1000 | V5-T1（付费 ≥ 30）|
| `api_calls` | API 调用 | 次 | monthly | null | null | null | 10000 | V5-T2（Team 档启用）|
| `digest_subscribe_products` | 周报/月报订阅产品 | 个 | concurrent | 1 | -1 | -1 | -1 | V5-T3（付费 ≥ 50）|
| `digest_frequency` | 周报/月报频率 | — | — | weekly | weekly+monthly | weekly+monthly | weekly+monthly | V5-T3 |

---

## 三、限制类型语义约定

| 类型 | 行为 | 用户体验 |
|------|------|------|
| **硬限** | 触发后直接 403，必须升级或等下月 | "本月 Ask reviews 已用完（10/10），升级 Pro 解锁" |
| **软限** | 触发后降级处理或提示，不立即拦截 | "Free 仅支持 2 个产品同时对比，升级解锁更多" |
| **不限** | 无限制，但代码侧仍要做合理性兜底（如单次 ≤ 1000） | — |

**LLM 成本类必须硬限**（直接烧钱）；**资源类一律软限**（让用户尽量用得舒服）。

---

## 四、计数与重置规则

### 4.1 monthly 周期
- 重置时间：每月 1 号 00:00 UTC+8
- 计数表：`user_quota_usage(user_id, dimension, period_start, used_count)`
- 跨月零点不结转、不退还

### 4.2 concurrent 周期
- 实时计算：`SELECT COUNT(*) FROM ... WHERE user_id = %s AND status = 'active'`
- 不需独立计数表

### 4.3 per_request 周期
- 单次请求内一次性校验，无累计
- 失败立即返回，不写入计数表

### 4.4 forever 周期
- 累计创建数，删除后释放（`DELETE` 触发计数器 -1）
- 适用于"创建即占用"的资源（webhook、规则）

---

## 五、超额行为规范

| 维度 | 超额时行为 | UI 文案 |
|------|------|------|
| `review_analyze` | 拒绝本次分析任务，进度条暂停 | "本月评论分析配额已用完（{used}/{limit} 条），升级 Pro 解锁 5000 条" |
| `ask_review` | 输入框置灰 + Toast | "Ask reviews 本月已用完（10/10），升级 Pro 解锁 50 次" |
| `ad_copy` | 生成按钮置灰 | "广告文案本月已用完（10/10），升级 Pro 解锁 100 次" |
| `excel_export` | 导出按钮置灰 + 提示 | "Excel 导出本月已用完（10/10），升级 Pro 解锁不限" |
| `compare_products` | 第 3 个产品勾选时阻止 | "Free 仅支持同时对比 2 个产品，升级 Pro 解锁不限" |
| `webhook_count` | 添加按钮置灰 | "Free 最多 3 个 webhook，升级 Pro 解锁不限" |
| `global_rules` / `product_rules` | 新建按钮置灰 | "Free 最多 {limit} 条规则，升级 Pro 解锁不限" |
| `upload_rows_per_file` | 上传时前置校验 + 阻止 | "Free 单文件最多 500 条，请拆分上传或升级 Pro" |

**统一升级 CTA 落点**：`/billing` 页面，URL 带 `?from={dimension}` 用于追踪转化漏斗。

---

## 六、数据模型建议（quota.py 实现时参考）

```python
# Schema (Supabase)
CREATE TABLE user_quota_usage (
  user_id      INT NOT NULL,
  dimension    TEXT NOT NULL,
  period_start DATE NOT NULL,        -- monthly 周期的当月 1 号
  used_count   INT NOT NULL DEFAULT 0,
  updated_at   TIMESTAMPTZ DEFAULT NOW(),
  PRIMARY KEY (user_id, dimension, period_start)
);
CREATE INDEX idx_quota_user ON user_quota_usage(user_id, period_start);

# 配额定义（Python 常量，不入库，发版时跟随代码）
QUOTA_DIMENSIONS = {
    # key: (unit, period, plan_limits, billing_type, has_llm_cost)
    "review_analyze": {
        "unit": "条", "period": "monthly",
        "limits": {"free": 1500, "pro_early": 5000, "pro": 10000, "team": 50000},
        "type": "hard", "llm_cost": True,
    },
    "ask_review": {
        "unit": "次", "period": "monthly",
        "limits": {"free": 10, "pro_early": 50, "pro": -1, "team": -1},
        "type": "hard", "llm_cost": True,
    },
    "ad_copy": {
        "unit": "次", "period": "monthly",
        "limits": {"free": 10, "pro_early": 100, "pro": 300, "team": -1},
        "type": "hard", "llm_cost": True,
    },
    "excel_export": {
        "unit": "次", "period": "monthly",
        "limits": {"free": 10, "pro_early": -1, "pro": -1, "team": -1},
        "type": "soft", "llm_cost": False,
    },
    "compare_products": {
        "unit": "个", "period": "concurrent",
        "limits": {"free": 2, "pro_early": -1, "pro": -1, "team": -1},
        "type": "soft", "llm_cost": False,
    },
    "webhook_count": {
        "unit": "个", "period": "forever",
        "limits": {"free": 3, "pro_early": -1, "pro": -1, "team": -1},
        "type": "soft", "llm_cost": False,
    },
    "global_rules": {
        "unit": "条", "period": "forever",
        "limits": {"free": 3, "pro_early": -1, "pro": -1, "team": -1},
        "type": "soft", "llm_cost": False,
    },
    "product_rules": {
        "unit": "条", "period": "forever",
        "limits": {"free": 1, "pro_early": -1, "pro": -1, "team": -1},
        "type": "soft", "llm_cost": False,
        "scope": "per_product",
    },
    "upload_rows_per_file": {
        "unit": "条", "period": "per_request",
        "limits": {"free": 500, "pro_early": 5000, "pro": 5000, "team": 5000},
        "type": "hard", "llm_cost": False,
    },
}

# 核心 API
def quota_check(user_id: int, dimension: str, amount: int = 1) -> tuple[bool, str]:
    """
    返回 (allowed, message)
    allowed=False 时 message 即为 UI 展示文案。
    """

def quota_check_atomic(user_id: int, dimension: str, amount: int) -> tuple[bool, str]:
    """
    原子完整校验：amount 必须一次性全部允许，否则整体拒绝。
    专用于 review_analyze 的批量上传场景，避免分析中途中断。
    返回 (allowed, message)
    """

def quota_consume(user_id: int, dimension: str, amount: int = 1) -> None:
    """成功调用后扣减，失败可手动 quota_refund"""

def quota_refund(user_id: int, dimension: str, amount: int = 1) -> None:
    """LLM 调用失败时回退已扣配额"""
```

---

## 八、决策记录（2026-06-09 已落定）

### 决策 1：`compare_products` 同时语义 — **方案 A：勾选数 ≤ 2**

- 计算口径：用户在对比页同时勾选的产品数 ≤ Free 2 / Pro 不限
- 历史对比报告不计入配额（属 sessions 副产物）
- 实现位置：[compare.py](review_analyzer/pages/compare.py) 多选组件加 `max_selections={2 | None}`

### 决策 2：`webhook_count` 计数规则 — **方案 B：混合计数 + 邮件独立位**

- Free：飞书 / 钉钉 / 企业微信 任意组合 ≤ 3 个 + 邮件 1 个独立位（不占配额）
- Pro：所有渠道不限 webhook 数量
- 邮件作为永久免费兜底通道，不计入 `webhook_count`
- 实现位置：[settings.py](review_analyzer/pages/settings.py) 校验 `len(webhooks_excluding_email) <= limit`

### 决策 3：早鸟锁价数据模型 — **方案 A：`plan_locked_at` 字段（精简版）**

- `users` 表新增字段：`plan_locked_at TIMESTAMPTZ`（早鸟订阅成功时写入）
- 用户的 plan 字段使用独立 key 区分：`free` / `pro_early` / `pro` / `team`
- 涨价逻辑：当系统计划价格变化时，对比 `plan_locked_at` 与涨价生效时间，早于涨价的用户保留 `pro_early` 配额
- 不引入 `user_plan_history` 表（Phase 1 简化，Phase 2 财务对账需求出现时再补）

### 决策 4：超额行为 — **方案 A 硬拒 + `review_analyze` 上传前置校验例外**

**通用规则（Ask reviews / 广告文案 / Excel 导出 / 其他）**：
- 配额耗尽后直接拒绝，UI 按第五节超额文案表提示升级
- 不做"借用下月配额"、不做按次计费

**`review_analyze` 例外（"原子完整"原则）**：
```
上传文件时前置校验剩余配额：
  - 已用 4500 / 5000 → 上传 500 条 → 允许（恰好用完）
  - 已用 4500 / 5000 → 上传 800 条 → 拒绝并提示"本次会超额（800 > 剩余 500），请拆分上传或升级 Pro"
  - 已用 5000 / 5000 → 上传任何条数 → 直接拒绝
```

- 校验时机：上传文件解析行数后，分析任务入队前
- 校验位置：[upload.py](review_analyzer/pages/upload.py) 上传按钮点击 → 解析条数 → `quota_check_atomic("review_analyze", rows)`
- 底线：**绝不允许"分析到一半因配额不足中断"**，避免用户已投入数据但拿不到结果

---

## 九、变更日志

| 日期 | 变更内容 | 触发原因 |
|------|------|------|
| 2026-06-09 | 初版建立，9 个核心维度 + 4 个 V5 预留维度 | V4-T2 Step 3 实现前的 SoT 准备 |
| 2026-06-09 | 4 个待确认问题决策落定（compare 勾选 ≤ 2、webhook 混合 3+邮件独立、`plan_locked_at` 字段、`review_analyze` 上传前置校验） | Erika 确认 |
| 2026-07-02 | 新增 `translate` 维度（Free 20 次/日、Pro 200 次/日）+ 全局/单用户成本熔断（BUDGET_* 环境变量）+ `/compare/export` `/compare/reports` 走 fingerprint 缓存复用 | 种子用户放出前的成本兜底 |

---

## 十、全局预算熔断（2026-07-02 新增）

### 10.1 环境变量

在 `deploy/.env` 中配置：

```bash
# 全站预算
BUDGET_DAILY_TOTAL_YUAN=100        # 全站每日预算，触达则全站 429 暂停到次日 0 点
BUDGET_MONTHLY_TOTAL_YUAN=1500     # 全站每月预算，触达则全站 429 暂停到下月 1 日

# 单用户预算
BUDGET_USER_DAILY_YUAN=20          # 单用户每日预算，触达则该用户当日冻结
BUDGET_USER_MONTHLY_YUAN=200       # 单用户每月预算，触达则该用户当月冻结
```

**未设置任一变量视为不启用**（放行）。种子阶段建议全部启用。

### 10.2 熔断触发行为

- 全站阈值触达 → 所有 LLM 接口返回 429 `"系统繁忙，请稍后再试"`（不暴露内部预算）
- 单用户阈值触达 → 该用户 LLM 接口返回 429 `"您今日/本月的 AI 使用额度已达上限"`
- 触发时同步推送飞书告警到 `FEISHU_OPS_WEBHOOK`，同周期去重（每天/每月只告一次）

### 10.3 覆盖范围

所有走 DeepSeek 的接口都要调 `assert_budget(user_id)`：
- ✅ `/translate/module` — 已接入
- ✅ `/compare/dataset` `/compare/export` `/compare/reports` — 已接入
- ⚠️ `/upload` / `/ask` / `/copywriter` — 依赖既有的 `quota_check` 硬限做成本兜底，未接入 `assert_budget`（后续按需补齐）

### 10.4 每日成本日报

每天 UTC+8 09:07 自动发飞书运维群（`FEISHU_OPS_WEBHOOK`），内容：
- 昨日总花费 / 调用次数
- 日预算用量百分比
- 月预算用量百分比
- Top 10 用户花费

由 `workers/scheduler.py` 触发 `daily_cost_digest_job`。

### 10.5 管理员查询接口

需 `users.is_admin = true`：
- `GET /admin/spend-report?days=7&top_n=10` — 花费概况 + top 用户 + 预算状态
- `GET /admin/budget-status` — 快速查询当前预算使用情况
