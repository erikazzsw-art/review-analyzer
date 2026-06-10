# 母婴用品 评论数据画像报告

> 生成时间: 2026-06-09 16:03:42
> 数据来源: /Users/zhangxi/Desktop/评论分析项目/母婴
> 总条数 (清洗后): **6736**
> 总条数 (原始): 10320

---

## 1. 子品类 (产品类型) 分布

| 子品类 | 条数 | 占比 |
|--------|------|------|
| Baby Gate | 3000 | 44.5% |
| baby footed pajamas | 904 | 13.4% |
| Baby Bibs | 598 | 8.9% |
| Muslin Burp Cloths | 588 | 8.7% |
| Baby Non Slip Socks | 518 | 7.7% |
| Baby Sun Hat | 476 | 7.1% |
| Unisex-Baby | 322 | 4.8% |
| Swim Diapers | 203 | 3.0% |
| Onesies Bodysuits | 127 | 1.9% |

## 2. 评分分布

| 评分 | 条数 | 占比 |
|------|------|------|
| 5 星 | 4524 | 67.2% |
| 4 星 | 578 | 8.6% |
| 3 星 | 432 | 6.4% |
| 2 星 | 399 | 5.9% |
| 1 星 | 803 | 11.9% |

**负面率 (≤3 星): 24.3%**
**正面率 (≥4 星): 75.7%**

## 3. 子品类 × 评分交叉

| 子品类 | 1星 | 2星 | 3星 | 4星 | 5星 | 负面率 |
|--------|-----|-----|-----|-----|-----|--------|
| Baby Bibs | 19 | 9 | 15 | 39 | 516 | 7.2% |
| Baby Gate | 601 | 232 | 220 | 288 | 1659 | 35.1% |
| Baby Non Slip Socks | 17 | 20 | 21 | 30 | 430 | 11.2% |
| Baby Sun Hat | 20 | 19 | 19 | 29 | 389 | 12.2% |
| Muslin Burp Cloths | 28 | 21 | 25 | 40 | 474 | 12.6% |
| Onesies Bodysuits | 3 | 1 | 7 | 13 | 103 | 8.7% |
| Swim Diapers | 16 | 13 | 21 | 19 | 134 | 24.6% |
| Unisex-Baby | 12 | 5 | 11 | 25 | 269 | 8.7% |
| baby footed pajamas | 87 | 79 | 93 | 95 | 550 | 28.7% |

## 4. TOP 20 ASIN 分布

| ASIN | 子品类 | 条数 | 命中规则 |
|------|--------|------|----------|
| B08GFCX964 | Baby Bibs | 513 | title/file 兜底 |
| B001OC5UMQ | Baby Gate | 427 | title/file 兜底 |
| B0CLPGQWNB | Muslin Burp Cloths | 215 | title/file 兜底 |
| B01HG7E5R8 | Baby Gate | 208 | title/file 兜底 |
| B0CH1C55L5 | Baby Gate | 153 | title/file 兜底 |
| B0CJXC7YTC | Baby Gate | 131 | title/file 兜底 |
| B01EMK5JQI | Baby Gate | 131 | title/file 兜底 |
| B07MLFKP1G | Baby Gate | 128 | title/file 兜底 |
| B095XD61JX | Baby Gate | 128 | title/file 兜底 |
| B0BKPDT7TS | Baby Gate | 127 | title/file 兜底 |
| B001OC5UNA | Baby Gate | 118 | title/file 兜底 |
| B0BYMYSH4Y | Baby Gate | 114 | title/file 兜底 |
| B001OE1PC8 | Baby Gate | 114 | title/file 兜底 |
| B003VNKLIY | Baby Gate | 103 | title/file 兜底 |
| B07PSNVYFZ | Baby Non Slip Socks | 98 | title/file 兜底 |
| B001OC5UN0 | Baby Gate | 96 | title/file 兜底 |
| B07WFZSW72 | Baby Gate | 88 | title/file 兜底 |
| B08CBJ2SSQ | Muslin Burp Cloths | 87 | title/file 兜底 |
| B07GFPVS2M | Unisex-Baby | 82 | title/file 兜底 |
| B01JCO56OO | Swim Diapers | 80 | title/file 兜底 |

## 5. 未命中 ASIN 映射表的 TOP 30 ASIN (供补 asin_product_type)

> 这些 ASIN 数量大但 `asin_product_type` 表里没有, 当前靠 title 关键词兜底归类.
> 建议: 看 Amazon listing 后在 yaml 配置里补 `asin_product_type: {ASIN: 产品类型}`, 重跑预处理.

| ASIN | 当前归类 | 条数 | TOP1 评论标题样例 |
|------|----------|------|-------------------|
| B08GFCX964 | Baby Bibs | 513 | Great |
| B001OC5UMQ | Baby Gate | 427 | Rickety as heck |
| B0CLPGQWNB | Muslin Burp Cloths | 215 | Baby Cloths |
| B01HG7E5R8 | Baby Gate | 208 | Baby Gate |
| B0CH1C55L5 | Baby Gate | 153 | Pet gate |
| B0CJXC7YTC | Baby Gate | 131 | Great gate! |
| B01EMK5JQI | Baby Gate | 131 | As Advertised |
| B07MLFKP1G | Baby Gate | 128 | My preferred gate |
| B095XD61JX | Baby Gate | 128 | Very Good |
| B0BKPDT7TS | Baby Gate | 127 | Must have gate. |
| B001OC5UNA | Baby Gate | 118 | OK GATE |
| B0BYMYSH4Y | Baby Gate | 114 | Good gate |
| B001OE1PC8 | Baby Gate | 114 | Best pet/kid gate |
| B003VNKLIY | Baby Gate | 103 | I’m satisfied |
| B07PSNVYFZ | Baby Non Slip Socks | 98 | Very good grip |
| B001OC5UN0 | Baby Gate | 96 | Works well |
| B07WFZSW72 | Baby Gate | 88 | Solid gate |
| B08CBJ2SSQ | Muslin Burp Cloths | 87 | Does the job |
| B07GFPVS2M | Unisex-Baby | 82 | Soft |
| B01JCO56OO | Swim Diapers | 80 | These are great! |
| B0C6KHVS4D | Baby Bibs | 73 | Allergic Reaction |
| B0746RGRL3 | Baby Gate | 71 | More trouble than having the dogs all over |
| B0D4B466R6 | Baby Gate | 68 | Did use a drill but it’s Perfect! |
| B0BS8VSFBC | Baby Sun Hat | 60 | Baby loves ! |
| B0BS8WT7HL | Baby Sun Hat | 60 | Product failed |
| B0DR55SVHB | Muslin Burp Cloths | 56 | Must have for your newborn |
| B08H1R7SRF | Baby Gate | 50 | Great gate |
| B003VNKLHA | Baby Gate | 50 | Great gate and easy to open and close |
| B07JL9291Y | Baby Gate | 44 | Gate door |
| B09XJH99C3 | Muslin Burp Cloths | 43 | Softness, washability, and ease of use |

## 6. 语言分布

| 语言 | 条数 | 占比 |
|------|------|------|
| en | 6736 | 100.0% |

## 7. Schema 分布

| Schema | 条数 |
|--------|------|
| shulex_standard | 6736 |