# V4-T3 集成方案演进文档

> 创建时间：2026-06-06
> 文档作者：Erika + Claude（V4-T3 阶段共同决策）
> 目的：记录 V4-T3 v2.1 集成方案的完整思考过程，避免未来忘记决策依据

---

## 1. 背景与起点

### 1.1 V4-T3 阶段的产出

V4-T3 阶段产出了一个新的 prompt 体系：
- **文件**：`prompts/annotate_v2.1.md`
- **核心改进**：19 类英文 aspects + 7 条 few-shot 示例 + rating-priority 规则 + 比较级隐含批评识别 + family-love 信号识别
- **评测结果**：38 条 Golden Set 上 **92.1% 准确率**
- **对比基线**：
  - v1.0（无 few-shot）：76.3%
  - v2.0（rating-priority + 5 few-shot）：86.8%
  - v2.1（+ neutral 兜底 + family-love）：**92.1%** ⭐
- **成本**：单条 ¥0.00394（比 v1.0 翻倍，但绝对值仍极低）

### 1.2 集成阻力（关键发现）

调研生产代码 `review_analyzer/analyzer.py` 后发现：
1. **生产用的是另一套 schema**：中文 11 类 category + 中文 issue_tags/highlight_tags + priority + reason + improvement
2. **`PROMPT_VERSION = "v2.1"` 是巧合命名**，与 `prompts/annotate_v2.1.md` 不是同一个东西
3. **生产 prompt 没做过 Golden Set 评测**，准确率未知
4. **V4-T3 v2.1 输出 schema 与生产完全不兼容**：19 类英文 aspects vs 11 类中文 category

### 1.3 同时进行的架构迁移

**关键背景：项目正在从 Streamlit 迁移到 Next.js + FastAPI**

- NX-M1 至 NX-M8 **全部已完成**（截至 2026-06-06）
- Next.js 前端、FastAPI 后端、Workers 异步任务、部署配置全部就绪
- Streamlit 已具备下线条件，等待整体切换
- 真正调用 `analyzer.py` 的是 `workers/jobs.py`（RQ worker），不是 backend_api 路由

---

## 2. 决策演进过程

### 2.1 第一版方案（错误）：直接替换

**思路**：用 V4-T3 v2.1 替换生产 v2.1，前端跟着改。

**为什么错**：
- 破坏 9+ 处下游消费者（results.py / compare.py / dashboard.py / exporter.py / insight_engine.py / 飞书推送 / 历史数据聚合）
- 推翻 Erika 6 年运营经验沉淀的 11 类业务大类
- 改动成本 2-3 周

**否决原因**：反向投资，破坏现有商业化资产。

### 2.2 第二版方案（部分对）：双轨架构

**思路**：L1（生产 analyzer.py）保持不动，L2（V4-T3 v2.1）独立通道，分别服务不同场景。

**为什么部分对**：
- 保护了现有 11 类商业化资产 ✅
- 但忽略了用户感知层面的准确率提升 ❌
- 用户在 UI 上看到的负面率仍由 L1 输出，准确率不变

**核心问题**：双轨架构默认不会让用户感知到准确率提升，需要明确决策才会。

### 2.3 第三版方案（路径分支）：3 选 1

提出三条路径供 Erika 选择：

| 路径 | UI 准确率提升 | 工时 | 风险 |
|------|--------------|------|------|
| 路径 1: L2 反哺 L1（中文 prompt 加 few-shot）| +10pp 估算 | 30 分钟 | 低 |
| 路径 2: L2 替代 L1（重写 9+ 文件）| → 92.1% 实测 | 2-3 周 | 高 |
| 路径 3: 仅 L2 通道（UI 不变）| 不变 | 1.5 天 | 低 |

**Erika 反问**：成熟竞品（如 Shulex）是怎么处理的？

### 2.4 第四版方案（业界对齐）：基于 Shulex 调研

**Shulex / VOC AI 调研核心发现**：

1. **Shulex 是市场份额最大的评论分析 SaaS**，采用三层架构（不是单层 / 双轨）
2. **Tier 2 业务大类**（Quality / Logistics / Service）= ClueAI 11 类的同位概念
3. **Tier 3 细分 aspect**（20000+ 标签，最深 6 层）= ClueAI 19 类英文 aspects
4. **业务模块视图**（Pros / Cons / Customer Profile）= 用户首屏看到的聚合层
5. **多语言通过 i18n 字典查表**（不是 LLM 输出双套，不是二次翻译 API）

**对比其他竞品**：

| 竞品 | 架构 | 评价 |
|------|------|------|
| Shulex / VOC AI | 三层架构 ⭐ | 业界最优，市场领导者 |
| Bazaarvoice | 单层 flat best/worst | 退化方案 |
| Yotpo | 单层 topics | 退化方案 |
| Helium 10 | 不做 aspect | 不属于评论分析专业工具 |

### 2.5 最终方案：三层架构（业界对齐 + 资产保留）

```
┌──────────────────────────────────────────────────┐
│  L0 业务大类（11 类中文 category）                 │
│  - 仪表盘默认聚合视图                              │
│  - 月度复盘抓重点用                                │
│  - 例: "产品质量 32% / 包装物流 18%"               │
└──────────────────┬───────────────────────────────┘
                   │ N:1 聚合派生（静态映射表）
                   ▼
┌──────────────────────────────────────────────────┐
│  L1 细分 Aspect 中文标签                          │
│  - drill-down 后看到的细分                        │
│  - 例: "耐用性 / 稳固性 / 做工"                    │
└──────────────────┬───────────────────────────────┘
                   │ 1:1 i18n 字典查表
                   ▼
┌──────────────────────────────────────────────────┐
│  L2 数据层（19 英文 canonical key）               │
│  - LLM 输出 / 数据库存储 / RAG 索引 / 跨产品对比   │
│  - 例: "durability / stability / build_quality"   │
└──────────────────────────────────────────────────┘

派生流向：
  L2（LLM 输出）→ L1（i18n 字典）→ L0（聚合规则）
  L0 / L1 都不让 LLM 直接输出。
```

**关键设计原则**：

| 原则 | 业界依据 | 在 ClueAI 的体现 |
|------|---------|-----------------|
| LLM 只输出 L2 英文 canonical | Shulex 推断做法 + 学术 ABSA 标准 | DeepSeek 输出 19 类英文 aspects |
| L1 中文标签用 i18n 字典查表 | Bazaarvoice Sentiments API（en/fr/de/es 4 种语言）| `aspect_labels.json` |
| L0 业务大类是 N:1 聚合，不是 1:1 翻译 | Shulex Tier 2（Quality / Logistics / Service）| 19→11 静态映射表 |
| 5 种业务大类是派生（不映射 aspect）| 业界共识：分类不应被 LLM 决定 | 正面反馈/单纯好评/无效乱码/混合评价/功能需求 |

---

## 3. 19 类 → 11 类聚合映射表

### 3.1 直接映射（来自 aspect 抽取）

| 11 类 L0 Category | 包含的 L2 aspects |
|------------------|------------------|
| 产品质量 | durability, stability, material, build_quality, size_fit, weight_capacity, color_accuracy, smell, safety |
| 包装物流 | packaging, shipping_damage, missing_parts |
| 使用体验 | assembly, comfort, ease_of_use, instructions |
| 客服售后 | customer_service |
| 性价比 | value_for_money |
| 其他 | other |

### 3.2 派生分类（不直接映射 aspect）

| 11 类 L0 Category | 派生规则 |
|------------------|---------|
| 正面反馈 | sentiment=positive 且所有 aspects polarity=positive |
| 单纯好评 | sentiment=positive 且 aspects 为空 |
| 无效乱码 | content 为空或长度 < 5 字符 |
| 混合评价 | aspects 中同时含 positive 和 negative |
| 功能需求 | highlights 中含 "should add" / "wish" / "would like" 等改进诉求 |

### 3.3 边界规则

**aesthetics 特殊处理**（同一个 aspect 在不同 polarity 下归不同 category）：
- aesthetics + polarity=positive → "正面反馈"
- aesthetics + polarity=negative → "产品质量"

**理由**：颜色丑/外观粗糙是质量问题，符合运营直觉。

---

## 4. NX-M8 完成后的方案调整

### 4.1 关键事实变更

之前我以为 NX-M7/M8 还在进行中，需要担心"V4-T3 集成会不会冲突 Next.js 迁移"。

**实际情况**：NX-M1-M8 全部完成，Streamlit 已具备下线条件。

### 4.2 调整的方案要点

| 之前的方案 | 调整后 |
|----------|--------|
| 改 `workers/jobs.py`（旧 worker）| 不变，仍是真正的执行入口 |
| 担心 Streamlit 旧路径回归测试 | **不必担心** — Streamlit 已具备下线条件 |
| 计划"双写 schema 兼容旧 UI" | **保留双写**，但优先级降低（仅给历史数据留 fallback）|
| 工时 2.5 天 | **保持 2.5 天**，风险降低 |
| 后续 V5.0 才下线 Streamlit | **可提前**，V4-T3 完成后 Streamlit 即可进入"维护状态" |

### 4.3 集成时机判断

**V4-T3 v2.1 集成是历史最佳窗口期**：
- Next.js 用户首次见到的就是 92.1% 准确率版本
- 不需要等 MRR > $3k 才升级
- 不需要做"L1 准确率反哺"的小改动（路径 1）

---

## 5. 实施方案概要（详见 plan 文件）

### 5.1 核心改动文件

| 文件 | 操作 |
|------|------|
| `backend_api/app/services/deep_analyzer.py` | 新建：V4-T3 v2.1 核心服务 |
| `backend_api/app/services/prompt_registry.py` | 新建（移自 scripts/）|
| `backend_api/app/services/category_grouper.py` | 新建：19→11 聚合 + 派生规则 |
| `backend_api/app/core/aspect_taxonomy.py` | 新建（移自 scripts/）|
| `backend_api/app/prompts/annotate_v2.1.md` | 新建（复制）|
| `backend_api/app/i18n/aspect_labels.json` | 新建：19 类英中映射 |
| `workers/jobs.py` | 修改：切到 deep_analyzer + 双写 schema |
| `supabase_schema.sql` | 修改：加 aspects_json + analyzer_version 字段 |
| `docs/competitor-research-2026-06-05.md` | 修改：决策回顾 + 三层架构记录 |
| `review_analyzer/analyzer.py` | **不动**（Streamlit 旧路径继续可用，等下线）|

### 5.2 工时估算

| Step | 工时 |
|------|------|
| Step 1: deep_analyzer + prompt_registry 移植 | 0.5 天 |
| Step 2: i18n 字典 + category_grouper | 0.5 天 |
| Step 3: DB schema 改造 + 部署 | 0.2 天 |
| Step 4: workers/jobs.py 改造 | 0.5 天 |
| Step 5: 文档更新 | 0.3 天 |
| 端到端测试 + Bug fix | 0.5 天 |
| **总计** | **2.5 天** |

---

## 6. 关键决策记录

### 6.1 已确认的决策

| 决策 | 选项 | 状态 |
|------|------|------|
| 主攻品类 | 家具家居（Erika 6 年运营经验最深的品类）| ✅ 已确认 |
| Aspect 体系 | 闭合 19 类 + safety（V4-T1 验证 80.8% 负面率确认必加）+ other 兜底 | ✅ 已确认 |
| Confidence 输出 | evidence_span + evidence_level 三档枚举（不用浮点）| ✅ 已确认 |
| Prompt 模型 | DeepSeek-V4-flash（性价比最优）| ✅ 已确认 |
| Golden Set 规模 | 500 条起步 + 38 条 reviewed（business as usual）| ✅ 已确认 |
| 决策 1（评分覆写）| 1A 纯 v2.1 prompt 软规则（实测 1C 反而更差）| ✅ A/B 实测后确认 |
| 决策 2（A/B 评测）| 38 条 reviewed 样本（有 ground truth 可比）| ✅ 已确认 |
| 架构方向 | A 三层架构（业界对齐）| ✅ 已确认 |

### 6.2 留待方案审批后再确认的决策

| 决策 | 默认推荐 |
|------|---------|
| 执行节奏 | V4-T3 集成与 Next.js 后续优化完全并行 |
| 前端策略 | API 中间层翻译（4 小时）|
| 中文标签产生 | 预定义 i18n 字典查表（业界共识）|
| aesthetics 边界 | positive→正面反馈, negative→产品质量 |

---

## 7. 引用来源

### 学术与业界标准
- [SemEval-2014 Task 4 (ABSA)](https://aclanthology.org/S14-2004.pdf)
- [SemEval-2016 Task 5 (ABSA)](https://aclanthology.org/S16-1002.pdf)
- [A Comprehensive Evaluation of LLMs on ABSA (arXiv 2412.02279)](https://arxiv.org/html/2412.02279)

### 工业产品调研
- [What are AI Tags - Shulex VOC Blog](https://blog.voc.ai/en_What_are_AI_Tags/)
- [Voice of Customer Analysis - VOC AI](https://insight.shulex.com/product/voice-of-customer-analysis)
- [Shulex VOC User Manual](https://www.voc.ai/support/shulex-voc-user-manual-2023)
- [Bazaarvoice Sentiments API](https://developers.bazaarvoice.com/v1.0-SentimentsAPI/docs/get-summarised-features)
- [Yotpo Insights - Topics](https://support.yotpo.com/docs/insights-topics)
- [Helium 10 Insights Dashboard](https://www.helium10.com/tools/insights-dashboard/)

### 项目内文档
- `docs/competitor-research-2026-06-05.md` — 5 个核心 prompt 设计决策
- `docs/taxonomy-analysis-2026-06-06.md` — 家具家居 Taxonomy 详细分析
- `data/golden_set/v1.0/ab_test_report.md` — V4-T3 A/B 评测结果
- `prompts/annotate_v1.0.md` / `prompts/annotate_v2.0.md` / `prompts/annotate_v2.1.md` — 三版 prompt 演进

---

## 8. 待确认事项

本文档完成后，需要 Erika 审批以下：

1. **三层架构方向是否确认**（之前回复"A"，再次确认）
2. **plan 文件 `~/.claude/plans/joyful-frolicking-whisper.md` 中的实施方案是否需要调整**（基于 NX-M8 已完成的事实）
3. **执行节奏 / 前端策略 / aesthetics 边界 4 个决策**是否按默认推荐
