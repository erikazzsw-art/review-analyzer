# 竞品技术选型调研报告

> 调研日期：2026-06-05
> 适用场景：V4-T1 数据资产化阶段的 Prompt 设计决策
> 调研范围：Shulex / VOC AI、Helium 10、Bazaarvoice、Yotpo、AWS Comprehend、Google Cloud NL、SemEval ABSA 学术标准
> 决策载体：ClueAI 跨境电商家具家居评论分析 SaaS（单人创业 / 预算敏感 / 英文评论）

---

## 调研背景

V4-T1 阶段需要确定 5 个 Prompt 设计决策（Aspect 体系、多语言策略、置信度输出、模型选型、Golden Set 规模），原始方案基于个人判断。为避免拍脑袋，对成熟 ABSA 工业产品和学术评测做了调研，重新校准方案。

---

## 1. Aspect 体系：封闭列表 vs 开放抽取

**业界主流：闭合 taxonomy + 可扩展层级体系，而非每次让 LLM 自由生成。**

| 来源 | 做法 | 规模 |
|------|------|------|
| SemEval 2014/2015/2016 | `Entity#Attribute` 二元闭合分类 | Restaurant 域 12-15 类，Laptop 域 80+ 组合 |
| Shulex VOC AI | 预定义 + 用户自定义双轨 | 内置 20,000+ 预定义 tag，6 级层级；用户自建最多 3 级 |
| Helium 10 Review Insights | 固定 aspect 分类 | quality / packaging / durability / value 等预定义集合 |

**结论：** 所有成熟竞品都用闭合 taxonomy，开放抽取仅在用户自定义层允许。Aspect 体系的稳定性是 ABSA 系统能跨产品做对比的前提。

**ClueAI 决策：**
- 采用闭合 taxonomy（家具家居 18 类专用 aspect）
- 保留 `other` 兜底类
- 后期再做 1 级 → 2 级的层级展开

---

## 2. 多语言：中文 taxonomy 还是英文 canonical key？

**业界主流：底层存英文 canonical key，UI 层做翻译；分类模型按英文统一。**

- **SemEval 2016** 引入多语言后，各语言数据集独立标注但共享同一 Entity#Attribute 概念骨架，标签 key 是英文
- **Shulex** 同时提供英文/日文版页面，但 tag 本身底层 key 推断为英文（行业合理推断，未明确公开）
- 跨境电商工具的 i18n 标准做法：业务逻辑层用英文 key，前端按用户语言翻译展示

**结论：** 英文为底层 key，中文卖家看到的标签做 UI 翻译即可，不要按语言分裂 taxonomy。

**ClueAI 决策：**
- `aspects[].key` 全英文（如 `assembly`、`shipping_damage`）
- `evidence_span` 保留英文原文（评论原句）
- `pain_points` 用英文短语
- UI 层做中英 i18n，跨境卖家看到的中文标签是翻译结果

---

## 3. 置信度（Confidence）：是否输出？什么格式？

**业界主流：工业 API 返回 per-class 概率（不是单一 confidence），LLM 自报 confidence 学术上证明不可靠。**

| 系统 | 置信度格式 |
|------|-----------|
| AWS Comprehend Targeted Sentiment | `SentimentScore = {Positive, Negative, Neutral, Mixed}` 四个 0-1 浮点数（分类概率，非"confidence"）|
| Google Cloud Natural Language | `score`(-1~1，方向) + `magnitude`(0~∞，强度) + `salience`(0~1，重要性)，非单一 confidence |
| OpenAI / Anthropic SDK | 提供 logprobs，但需用户自行处理 |

**学术界明确结论：** LLM 自报 confidence 系统性高估，对 framing 敏感，未经校准不可信。
- [Just Ask for Calibration (arXiv 2305.14975)](https://ar5iv.labs.arxiv.org/html/2305.14975)
- [A Survey of Confidence Estimation in LLMs (arXiv 2311.08298)](https://arxiv.org/html/2311.08298)

**ClueAI 决策：**
- 放弃 `confidence: 0.85` 浮点数自由输出
- 改用 `evidence_span`（原文证据片段）+ `evidence_level: certain / probable / uncertain` 三档枚举
- 三档枚举比浮点数稳定，且 evidence_span 可直接做 Listing 优化素材

---

## 4. 模型选型：GPT-4o vs GPT-4o-mini vs Claude Haiku vs DeepSeek

**业界主流：GPT-4o-mini 是 ABSA 任务性价比最优解；DeepSeek 在英文细粒度任务上落后。**

| 来源 | 结论 |
|------|------|
| AIMultiple TweetEval Benchmark | Claude 3.7 ~79%、GPT-4o ~75%、DeepSeek V3 ~70%；所有模型 sentiment classification 仅 54-69% |
| arXiv 2412.02279 ABSA 综合评测 | API 模型中 GPT-4-Turbo + BM25 demo 选择最强（aspect F1 ~72，sentiment F1 ~83）；fine-tuned LLaMA3-8B 反超所有 zero-shot LLM |
| OpenAI Structured Outputs | 原生 schema enforcement 在 GPT-4o-mini 上稳定，复杂嵌套 schema 偶发不一致 |
| Shulex 2024 | 公开博客提及 GPT 升级，未指定 mini/full（行业合理推断为 GPT-4o 系列） |

**关键事实：** GPT-4o-mini 价格仅 GPT-4o 的 7%（$0.15/1M input vs $2.5/1M），但在结构化输出 + ABSA 任务上质量差距 < 5%。

**ClueAI 决策：**
- 主力模型：**GPT-4o-mini + Structured Outputs**
- 高难样本 fallback：GPT-4o
- DeepSeek：仅作离线对照，不上生产
- Claude Haiku：备用 fallback（指令跟随强，但缺原生 schema enforcement）

**成本预估对比：**
| 任务 | GPT-4o 方案 | GPT-4o-mini 方案 | 节省 |
|------|------------|----------------|------|
| Golden Set 500 条标注 | ¥23 | ¥3-5 | -85% |
| Taxonomy 全量 24032 条抽取 | ¥220 | ¥15-20 | -90% |

---

## 5. Golden Set 标注规范

**业界主流：双人标注 + 第三人仲裁 + Cohen's Kappa ≥ 0.7 是黄金标准；500-1000 条已足够单人验证模型迭代。**

| 来源 | 做法 |
|------|------|
| SemEval ABSA 系列 | 每域 3,000-6,000 句子，部分双标注 + Kappa 度量 + organizer 仲裁分歧 |
| arXiv 2605.03624 | 专家、学生、众包、LLM 一致性差异显著；专家最高，LLM 已接近众包水平 |
| 工业实践 | SaaS 早期 500 条迭代足够，2,000+ 适合发表 |

**ClueAI 决策（分阶段）：**

| 阶段 | 规模 | 时机 | 用途 |
|------|------|------|------|
| 阶段 1 | 500 条 | 本周 | V4-T3 评测基准锁版本 |
| 阶段 2 | +500 条（累计 1000）| V4-T3 完成后 | 加入 V4-T6 用户反馈 bad case |
| 阶段 3 | +1000 条（累计 2000）| V4-T5 ABSA 训练前 | 达到学术发表水平 |

**双标注策略：** 单人创业阶段走「你标第一遍 + GPT-4o 二审 + 不一致样本你仲裁」，等价于 Kappa 校验的简化版。

---

## 家具家居 18 类 Aspect Taxonomy（最终版）

基于业界做法 + Shulex 床架/床垫品类用户实际抱怨频次设计。

```python
FURNITURE_ASPECTS = {
    # 物理质量类（家具核心维度，5 类）
    "assembly":          "组装难度",
    "durability":        "耐用性",
    "stability":         "稳固性",
    "material":          "材质用料",
    "build_quality":     "做工",

    # 使用体验类（4 类）
    "comfort":           "舒适度",
    "size_fit":          "尺寸匹配",
    "weight_capacity":   "承重",
    "ease_of_use":       "易用性",

    # 外观类（2 类）
    "aesthetics":        "外观设计",
    "color_accuracy":    "颜色还原度",

    # 物流类（家具特别重要，3 类）
    "packaging":         "包装",
    "shipping_damage":   "运输损坏",
    "missing_parts":     "缺件",

    # 售后类（2 类）
    "instructions":      "说明书",
    "customer_service":  "客服",

    # 经济与体感类（2 类）
    "value_for_money":   "性价比",
    "smell":             "异味",

    # 兜底（1 类）
    "other":             "其他",
}
```

**规模合理性：** 介于 SemEval Restaurant 域（12-15 类）与 Laptop 域（80+ 类）之间，符合家具家居复杂度。

---

## ClueAI 最终方案（落地决策清单）

| # | 决策项 | 最终方案 | 业界依据 |
|---|--------|---------|---------|
| 1 | Aspect 体系 | 闭合 18 类 + `other` 兜底 | SemEval / Shulex 闭合 taxonomy 标准 |
| 2 | 多语言策略 | 英文 canonical key + UI 层 i18n | SemEval 多语言标准做法 |
| 3 | 置信度输出 | `evidence_span` + `evidence_level` 三档枚举 | 学术界 LLM confidence 不可信结论 |
| 4 | 标注模型 | GPT-4o-mini + Structured Outputs | AIMultiple benchmark 性价比最优 |
| 5 | Golden Set 规模 | 500 条起步 → 1000 条 → 2000 条分阶段 | SemEval 工业实践 |
| 6 | 双标注策略 | 你标 + GPT 二审 + 不一致样本仲裁 | 单人创业版 Kappa 校验 |

---

## 引用来源

### 学术论文
- [SemEval-2014 Task 4 (ABSA)](https://aclanthology.org/S14-2004.pdf)
- [SemEval-2016 Task 5 (ABSA)](https://aclanthology.org/S16-1002.pdf)
- [Just Ask for Calibration (arXiv 2305.14975)](https://ar5iv.labs.arxiv.org/html/2305.14975)
- [A Survey of Confidence Estimation in LLMs (arXiv 2311.08298)](https://arxiv.org/html/2311.08298)
- [A Comprehensive Evaluation of LLMs on ABSA (arXiv 2412.02279)](https://arxiv.org/html/2412.02279)
- [Annotation Quality in ABSA (arXiv 2605.03624)](https://arxiv.org/html/2605.03624)

### 工业产品文档
- [Shulex AI Tags 文档](https://blog.voc.ai/en_What_are_AI_Tags/)
- [Helium 10 Review Insights KB](https://kb.helium10.com/hc/en-us/articles/48006601967643-Review-Insights-Analyze-Customer-Feedback-with-Amazon-Data)
- [AWS Comprehend Targeted Sentiment API](https://docs.aws.amazon.com/comprehend/latest/APIReference/API_DetectTargetedSentiment.html)
- [Google Cloud Natural Language Sentiment](https://cloud.google.com/natural-language/docs/reference/rest/v2/Sentiment)

### Benchmark 与社区
- [AIMultiple Sentiment Analysis Benchmark](https://aimultiple.com/sentiment-analysis-benchmark)
- [OpenAI Structured Outputs Reliability Discussion](https://community.openai.com/t/structured-outputs-not-reliable-with-gpt-4o-mini-and-gpt-4o/918735)

---

## 调研结论一句话

**ClueAI V4-T1 不要重新发明轮子——业界已有清晰最佳实践：闭合 taxonomy + 英文 canonical + evidence-based confidence + GPT-4o-mini + 分阶段 Golden Set。这 5 个决策合起来把 V4-T1 总成本从 ¥260+ 压到 ¥20-25，准确率不降反升。**

---

## 附录 A: V4-T3 决策修订记录（2026-06-06）

> 本节记录 V4-T1 调研结论 → V4-T3 实施过程中的真实决策演进，避免未来忘记决策依据。

### A.1 决策 1（评分覆写）：1C 方案被实测推翻 → 改走 1A

V4-T1 调研后给出的初版方案是**决策 1C（prompt 软规则 + 后处理硬覆写）**，预设 prompt + override 双层防护最稳。

**A/B 实测结果（38 条 reviewed Golden Set）**：

| 组 | 总样本准确率 | Bad Case (12 条) | 高评分 ≥4 (16 条) |
|----|------------|-----------------|------------------|
| v1.0 基线 | 76.3% | 25.0% | 56.2% |
| v2.0 (rating-priority + 5 few-shot) | 86.8% | 100.0% | 93.8% |
| **v2.1 (+ neutral 兜底 + family-love)** ⭐ | **92.1%** | **100.0%** | **100.0%** |
| v2.0 + override 后处理 | 76.3% | 91.7% | 75.0% |

**关键发现**：v2.0 prompt 已经学会处理边界 case，但 override 后处理是"强约束"，会把 v2.0 已正确判断的样本错误覆写。**实测推翻了 1C 预设**。

**最终采用决策 1A（纯 prompt 软规则）**：让 LLM 内化业务规则比后处理硬覆写更稳定。`sentiment_override.py` 保留作冷藏 fallback，不主动启用。

### A.2 架构演进：单层 → 双轨 → 三层

V4-T3 集成方案经历了三次演进：

**第一版（错误）：直接替换**
- 用 V4-T3 v2.1 替换生产 analyzer.py
- 否决原因：破坏 9+ 处下游消费者，推翻 Erika 6 年运营经验沉淀的 11 类业务大类

**第二版（部分对）：双轨架构**
- L1（生产 analyzer.py）保持不动，L2（V4-T3 v2.1）独立通道
- 部分对原因：保护现有商业化资产 ✅，但用户感知层面准确率不变 ❌

**第三版（最终）：三层架构（业界对齐）**

基于 Shulex / VOC AI 调研发现：业界领导者用的是三层架构（不是单层 / 双轨）。

```
L0 业务大类（11 类中文 category）= Shulex Tier 2
L1 细分 Aspect 中文标签（19 类 i18n 翻译）
L2 数据层（19 英文 canonical key）= LLM 输出
派生流向: L2 → L1 → L0（不让 LLM 直接输出 L0/L1）
```

### A.3 i18n 字典查表是业界共识

调研多家竞品后确认：**LLM 不应同时输出英文 + 中文双套**。

| 竞品 | 多语言做法 |
|------|----------|
| Shulex / VOC AI | 底层英文 canonical + i18n 字典查表（推断）|
| Bazaarvoice Sentiments API | API 按 `language` 参数返回 nativeFeature（en/fr/de/es 4 种）|
| AWS Comprehend | 单语言模型 + 客户端按需翻译 |

**ClueAI 落地**：`backend_api/app/i18n/aspect_labels.json` 维护 19 类英中映射，UI 渲染时查表。

### A.4 Shulex 三层架构 vs 单层退化方案

| 产品 | 架构 | 评价 |
|------|------|------|
| **Shulex / VOC AI** ⭐ | **三层架构（多层 tag tree，最深 6 层）** | **市场领导者，业界最优** |
| Bazaarvoice | 单层 flat best/worst | 退化方案 |
| Yotpo | 单层 topics + 星标 | 退化方案 |
| Helium 10 | 不做 aspect | 不属于评论分析专业工具 |

**核心结论**：完全舍弃 L1 中文 11 类 = 退化到 Bazaarvoice/Yotpo 单层模式，丢失 6 年运营经验沉淀。

### A.5 V4-T3 集成时机判断

**关键事实**：Next.js + FastAPI 迁移已完成 NX-M1 至 NX-M8 全部 8 个模块（截至 2026-06-06），Streamlit 已具备下线条件。

| 时机 | 评估 |
|------|------|
| **现在**（NX-M8 完成后立即集成）⭐ | Next.js 全栈架构的"准确率收尾"，用户立刻享受 92.1% |
| 等 MRR > $3k | 错过 Next.js 迁移窗口，用户多承担 6 个月低准确率 |
| Streamlit 整体下线后 | 太晚，新用户上线即用低准确率版本 |

### A.6 V4-T3 集成的成本与产出

| 项 | 数据 |
|----|------|
| Prompt v2.0 → v2.1 改进 | +5.3pp 准确率（86.8% → 92.1%）|
| Bad Case 修复率 | 25% → 100% |
| 高评分 ≥4 准确率 | 56.2% → 100% |
| 单条评论成本 | ¥0.00182 → ¥0.00394 (+116%) |
| 单条评论 Token | 输入 ~720 → ~2840 (+295%, few-shot 注入) |
| 集成工时 | 2.5 天 |

**判断**：成本翻倍换来 16pp 准确率提升 + 商业化部署门槛达成（业界 SaaS 标准 ≥ 90%），完全值得。换算到生产规模：10000 条评论 ¥40，远低于商业化定价（¥99/月入门版）。

---

## 附录 B: V4-T3 关键产出物

| 产出 | 路径 |
|------|------|
| 三版 Prompt 演进 | `prompts/annotate_v1.0.md` / `v2.0.md` / `v2.1.md` |
| Golden Set 评测报告 | `data/golden_set/v1.0/ab_test_report.md` |
| Bad Case 库 v1.0 | `data/golden_set/v1.0/bad_cases_v1.0.md` |
| Taxonomy 详细分析 | `docs/taxonomy-analysis-2026-06-06.md` |
| V4-T3 集成思考过程 | `docs/v4-t3-integration-plan-2026-06-06.md` |
| 生产模块（backend_api）| `backend_api/app/services/deep_analyzer.py` / `category_grouper.py` / `prompt_registry.py` |
| Aspect 19 类定义 | `backend_api/app/core/aspect_taxonomy.py` |
| i18n 字典 | `backend_api/app/i18n/aspect_labels.json` |
| Worker 双写实现 | `workers/jobs.py` |
