# 文案平台规则调研（2026-06-24）

本文件汇总宣传文案功能涉及的 6 个广告平台的字符限制、禁用词与风格偏好，作为 [`backend_api/app/routes/copywriter.py`](../backend_api/app/routes/copywriter.py) 中 `PLATFORM_DATA` 与 `STYLE_INCOMPATIBLE` 的依据，便于后续规则刷新时只改文档与常量，不动业务代码。

> 取数日期：2026-06-24
> 维护者：Erika
> 来源说明：以下规则综合自各平台官方文档与多份 2026 年第三方汇总；Walmart Connect 的官方文案位规格暂未对外公开，所列数值标注为 internal_estimate，发布前请二次核对。

## 1. Amazon Ads

### 1.1 广告类型与字符位（系统真正允许自定义的部分）

| Ad Type | 字段 | 字符上限 | 备注 |
|---|---|---|---|
| Sponsored Products (SP) | — | — | SP 不允许自定义广告文案；创意完全由 listing（Title / Bullet / Image）决定。本系统**不**为 SP 生成文案。 |
| Sponsored Brands (SB) | Headline | 50 | 单行标题；不允许 ALL-CAPS 段落与多个感叹号 |
| Sponsored Display (SD) | Headline | 50 | 自定义头条 |
| Sponsored Display (SD) | Body / Lifestyle Copy | 100 | 副文案 |

### 1.2 禁用词与表达

- 紧迫语：`today only`, `last chance`, `limited time`, `act now`, `don't miss out`
- 价格/折扣：`$X off`, `% off`, `save $X`, `lowest price`, `cheapest`, `discount`, `free`
- 最高级 / 排名：`best`, `#1`, `top`, `greatest`
- CTA 类：`buy now`（应改为 `Shop now` / `Learn more` / `See details`）
- 标点：单条文案中 `!` 视为高风险；`ALL CAPS` 连续 ≥ 3 个单词视为风险
- 健康/索赔类：`guaranteed`, `100% safe`, `cure`

### 1.3 风格偏好

简洁专业 / 数据驱动 / 情感共鸣 友好；幽默风趣可接受但需克制；**紧迫促单禁止**。

### 1.4 来源

- Amazon Ads — Creative acceptance: advertising copy https://advertising.amazon.com/resources/ad-policy/creative-acceptance/advertising-copy
- Amazon Ads — Sponsored Brands and display ads moderation https://advertising.amazon.com/library/guides/sponsored-brands-display-ads-moderation
- Amazon Ads — Quick reference https://advertising.amazon.com/resources/ad-policy/quick-reference

---

## 2. Facebook (Meta) Ads

### 2.1 广告类型与字符位

| 字段 | 推荐上限 | 备注 |
|---|---|---|
| Primary Text | 125 | 移动端约 125 字符后被 "See More" 折叠，首句即广告 |
| Headline | 40 | Reels Overlay 仅 10 字符可视 |
| Description | 30 | 多数版位隐藏，CTA / 关键卖点不能放这里 |

### 2.2 禁用词与表达

- 针对个人属性：`you are`, `your body`, `your weight`
- 身体羞辱 / 健康声明：`weight loss`, `before and after`, `cure`, `guaranteed results`
- 情感操纵：`Are you tired of...?` 这类"问句逼迫"
- 误导承诺：`guaranteed`, `100%`, `risk-free`

### 2.3 风格偏好

简洁专业 / 幽默风趣 / 情感共鸣 / 数据驱动 / 紧迫促单 均可。

### 2.4 来源

- Meta Business Help — Creative best practices for text in ads https://www.facebook.com/business/help/223409425500940
- Ad copy specs 2026 汇总 https://adsuploader.com/blog/meta-ad-copy-specs

---

## 3. TikTok Ads

### 3.1 广告类型与字符位

| Ad Type | 字段 | 字符上限 | 备注 |
|---|---|---|---|
| In-Feed Ad | Caption | 100 | 含 hashtag；前 4 行约 100 字符可见后折叠 |
| Spark Ad | Headline | 40 | 副标题；Spark 主文案沿用原帖（最长 2200，重点落在前 100） |
| 所有 | Brand / App Name | 4–40 | 拉丁字符；中日韩字符按 2 计 |

### 3.2 禁用词与表达

- `click link in bio`, `link in bio`（TikTok 付费广告不支持）
- 紧迫语：`limited time`, `today only`
- 索赔：`100% guaranteed`, `cure`
- 健康/医疗夸大表达

### 3.3 风格偏好

幽默风趣 / 情感共鸣 / 紧迫促单 友好；简洁专业 / 数据驱动可用但 TikTok 算法更偏向口语化"vibe"，纯数据风格效果较弱（标 △，可选但前端 Tooltip 提示）。

### 3.4 来源

- TikTok For Business — In-feed reservation ad specs https://ads.tiktok.com/help/article/tiktok-reservation-in-feed-ads-reach-frequency
- TikTok ad copy character limit guide 2026 https://tlinky.com/tiktok-ad-copy-character-limit/

---

## 4. Walmart Connect

> ⚠️ **internal_estimate**：Walmart Connect Sponsored Search 对站内"广告文案"字段（非商品 listing）公开规格有限，下列上限为本系统的保守估计，发布前请二次核对最新 Walmart Connect 创意规范。

### 4.1 广告类型与字符位

| Ad Type | 字段 | 字符上限 | 备注 |
|---|---|---|---|
| Sponsored Products | Product Title | 75 | 实际由 listing 决定；本系统提供优化建议 |
| Sponsored Brands | Product Description | 150 | 简短描述 |
| Sponsored Brands | Ad Slogan / Tagline | 80 | 标语 |

### 4.2 禁用词与表达

- 最高级 / 排名：`best`, `#1`, `top`
- 价格 / 折扣：`lowest price`, `cheap`, `discount`, `free`, `$X off`
- 紧迫语：`limited time`, `act now`
- 索赔：`guaranteed`, `100%`

### 4.3 风格偏好

与 Amazon 接近：简洁专业 / 情感共鸣 / 数据驱动 / 幽默风趣 可用；**紧迫促单禁止**。

### 4.4 来源

- Walmart Connect — Sponsored Search advertising https://marketplacelearn.walmart.com/guides/Advertising/Walmart%20Connect/Advertise-with-Walmart-Connect-sponsored-search
- Walmart Connect Ads guide 2026 https://selltru.com/blog/walmart-connect-ads-guide

---

## 5. Google Ads

### 5.1 广告类型与字符位

| 字段 | 字符上限 | 备注 |
|---|---|---|
| Headline | 30 | 至少 3 条，建议 15 条 |
| Description | 90 | 至少 2 条 |
| Extra Detail / Sitelink | 25 | 站点链接补充信息 |

### 5.2 禁用词与表达

- 误导：`click here`, `you won't believe`
- 索赔：`guaranteed`, `100%`, `risk-free`
- 价格诱导：`free`, `lowest price`
- 排名 / 最高级：`#1`, `best`
- 标点：标题禁多重 `!`、ALL CAPS

### 5.3 风格偏好

简洁专业 / 数据驱动 友好；情感共鸣可用但 Google 文字广告本身偏理性，标 △。

### 5.4 来源

- Google Ads Help — About expanded text ads https://support.google.com/google-ads/answer/7056544

---

## 6. Instagram (Meta) Ads

### 6.1 广告类型与字符位

| 字段 | 字符上限 | 备注 |
|---|---|---|
| Post Copy | 2200 | 前 125 字符以内为可见摘要 |
| Story Copy | 125 | 单屏可见 |
| Reels Title / Caption | 100 | 与 In-Feed 一致 |

### 6.2 禁用词与表达

- 与 Facebook 一致（Meta 共用政策）
- 付费广告中**不得**使用 `swipe up`, `link in bio` 这类引导

### 6.3 风格偏好

与 Facebook 一致。

### 6.4 来源

- Meta Business Help — Creative best practices https://www.facebook.com/business/help/223409425500940

---

## 7. 风格 × 平台兼容性矩阵

| 风格 | Amazon | Facebook | TikTok | Walmart | Google | Instagram |
|---|---|---|---|---|---|---|
| 简洁专业 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| 幽默风趣 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| 情感共鸣 | ✓ | ✓ | ✓ | ✓ | △ | ✓ |
| 数据驱动 | ✓ | ✓ | △ | ✓ | ✓ | ✓ |
| 紧迫促单 | ✗ | ✓ | ✓ | ✗ | ✗ | ✓ |

- ✗：前端 chip 灰显禁选；服务端二次校验拒绝该组合
- △：可选，前端 Tooltip 提示"该平台对此风格效果较弱"

矩阵在代码中对应 `backend_api/app/routes/copywriter.py` 的 `STYLE_INCOMPATIBLE: dict[str, list[str]]`，字段值为不兼容的平台 id 列表。

---

## 8. 维护方式

- 平台规则变化时，先更新本文件对应小节并标注新的取数日期
- 再同步修改 `PLATFORM_DATA` / `STYLE_INCOMPATIBLE` 常量，保持两边一致
- 不要在业务代码里写"为什么禁这个词"的长注释，原因留在本文件即可
