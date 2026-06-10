# 3C 配件 评论数据画像报告

> 生成时间: 2026-06-09 15:00:39
> 数据来源: /Users/zhangxi/Desktop/评论分析项目/3C
> 总条数 (清洗后): **22411**
> 总条数 (原始): 46532

---

## 1. 子品类 (产品类型) 分布

| 子品类 | 条数 | 占比 |
|--------|------|------|
| Screen Protector Compatible with Apple Watch | 3000 | 13.4% |
| Screen Protector for iPhone | 3000 | 13.4% |
| iPhone Charger | 3000 | 13.4% |
| Power Strip | 2933 | 13.1% |
| Wall Charger | 2519 | 11.2% |
| USB C to USB C Cable | 2159 | 9.6% |
| USB C Charger Block | 1443 | 6.4% |
| 便携话筒 | 1301 | 5.8% |
| USB A to USB C Cable | 1294 | 5.8% |
| Fast Charging Portable Charger | 934 | 4.2% |
| Ink Cartridges | 828 | 3.7% |

## 2. 评分分布

| 评分 | 条数 | 占比 |
|------|------|------|
| 5 星 | 13262 | 59.2% |
| 4 星 | 1910 | 8.5% |
| 3 星 | 1381 | 6.2% |
| 2 星 | 1540 | 6.9% |
| 1 星 | 4318 | 19.3% |

**负面率 (≤3 星): 32.3%**
**正面率 (≥4 星): 67.7%**

## 3. 子品类 × 评分交叉

| 子品类 | 1星 | 2星 | 3星 | 4星 | 5星 | 负面率 |
|--------|-----|-----|-----|-----|-----|--------|
| Fast Charging Portable Charger | 141 | 35 | 39 | 95 | 624 | 23.0% |
| Ink Cartridges | 277 | 55 | 36 | 52 | 408 | 44.4% |
| Power Strip | 630 | 182 | 165 | 191 | 1765 | 33.3% |
| Screen Protector Compatible with Apple Watch | 523 | 292 | 304 | 341 | 1540 | 37.3% |
| Screen Protector for iPhone | 543 | 245 | 237 | 282 | 1693 | 34.2% |
| USB A to USB C Cable | 143 | 51 | 60 | 93 | 947 | 19.6% |
| USB C Charger Block | 341 | 93 | 81 | 115 | 813 | 35.7% |
| USB C to USB C Cable | 192 | 81 | 61 | 96 | 1729 | 15.5% |
| Wall Charger | 407 | 142 | 136 | 311 | 1523 | 27.2% |
| iPhone Charger | 894 | 281 | 182 | 201 | 1442 | 45.2% |
| 便携话筒 | 227 | 83 | 80 | 133 | 778 | 30.0% |

## 4. TOP 20 ASIN 分布

| ASIN | 子品类 | 条数 | 命中规则 |
|------|--------|------|----------|
| B09PDLBFKY | Power Strip | 2750 | title/file 兜底 |
| B08R6S1M1K | Wall Charger | 2268 | title/file 兜底 |
| B0B283QP2N | iPhone Charger | 1649 | title/file 兜底 |
| B0CPSBD68W | USB C Charger Block | 1308 | title/file 兜底 |
| B088NRLMPV | USB C to USB C Cable | 1229 | title/file 兜底 |
| B0CMJTSVRW | 便携话筒 | 1019 | title/file 兜底 |
| B0CB1FW5FC | Fast Charging Portable Charger | 752 | title/file 兜底 |
| B07DD5YHMH | USB A to USB C Cable | 576 | title/file 兜底 |
| B07DC5PPFV | USB A to USB C Cable | 519 | title/file 兜底 |
| B09KR8P3L5 | iPhone Charger | 472 | title/file 兜底 |
| B08412HXK9 | Ink Cartridges | 470 | title/file 兜底 |
| B09JWDZ64S | Screen Protector Compatible with Apple Watch | 308 | title/file 兜底 |
| B07WRBDXZ8 | Screen Protector Compatible with Apple Watch | 261 | title/file 兜底 |
| B0CQXDFHL3 | iPhone Charger | 227 | title/file 兜底 |
| B0DFVB13XF | Screen Protector Compatible with Apple Watch | 215 | title/file 兜底 |
| B088NMR44C | USB C to USB C Cable | 204 | title/file 兜底 |
| B07WR8KCLM | Screen Protector Compatible with Apple Watch | 179 | title/file 兜底 |
| B09CSSP9C1 | Screen Protector for iPhone | 179 | title/file 兜底 |
| B0CQQXLKQQ | iPhone Charger | 178 | title/file 兜底 |
| B084131T6G | Ink Cartridges | 177 | title/file 兜底 |

## 5. 未命中 ASIN 映射表的 TOP 30 ASIN (供补 asin_product_type)

> 这些 ASIN 数量大但 `asin_product_type` 表里没有, 当前靠 title 关键词兜底归类.
> 建议: 看 Amazon listing 后在 yaml 配置里补 `asin_product_type: {ASIN: 产品类型}`, 重跑预处理.

| ASIN | 当前归类 | 条数 | TOP1 评论标题样例 |
|------|----------|------|-------------------|
| B09PDLBFKY | Power Strip | 2750 | great |
| B08R6S1M1K | Wall Charger | 2268 | DID NOT CHARGE MY IPHONES |
| B0B283QP2N | iPhone Charger | 1649 | Improper fit |
| B0CPSBD68W | USB C Charger Block | 1308 | NOT FAST CHARGING |
| B088NRLMPV | USB C to USB C Cable | 1229 | Rugged and Reliable |
| B0CMJTSVRW | 便携话筒 | 1019 | Excelente compra |
| B0CB1FW5FC | Fast Charging Portable Charger | 752 | I love this little powerhouse |
| B07DD5YHMH | USB A to USB C Cable | 576 | Braided |
| B07DC5PPFV | USB A to USB C Cable | 519 | Good quality |
| B09KR8P3L5 | iPhone Charger | 472 | They work ! |
| B08412HXK9 | Ink Cartridges | 470 | Excelente calidad |
| B09JWDZ64S | Screen Protector Compatible with Apple Watch | 308 | Work’s wonderful |
| B07WRBDXZ8 | Screen Protector Compatible with Apple Watch | 261 | Fits great |
| B0CQXDFHL3 | iPhone Charger | 227 | No sirven |
| B0DFVB13XF | Screen Protector Compatible with Apple Watch | 215 | Excellent fit and finish |
| B088NMR44C | USB C to USB C Cable | 204 | Charges quickly |
| B07WR8KCLM | Screen Protector Compatible with Apple Watch | 179 | I’ve had better |
| B09CSSP9C1 | Screen Protector for iPhone | 179 | Protects but texting is hard |
| B0CQQXLKQQ | iPhone Charger | 178 | Purple charger<white charger |
| B084131T6G | Ink Cartridges | 177 | Good price |
| B0CQC97GKT | iPhone Charger | 166 | Charger |
| B0CFZNZN25 | USB C to USB C Cable | 161 | It just works. |
| B09K6C8S9Q | Screen Protector Compatible with Apple Watch | 156 | easy to use |
| B0C7VYFXD8 | Screen Protector Compatible with Apple Watch | 155 | Good screen protector! |
| B0CFZDHRPP | USB C to USB C Cable | 154 | Good product |
| B0CCYM3F1V | Screen Protector for iPhone | 149 | Too small in width for iPhone 16 |
| B0BGXD2DQ7 | Screen Protector Compatible with Apple Watch | 148 | Perfect Fit |
| B0CQQW59NF | iPhone Charger | 142 | Cheaper version of a more expensive name brand |
| B0D9LJPKF5 | Screen Protector for iPhone | 141 | Satisfied |
| B09K6BQPYZ | Screen Protector Compatible with Apple Watch | 134 | Apple Watch cover |

## 6. 语言分布

| 语言 | 条数 | 占比 |
|------|------|------|
| en | 22411 | 100.0% |

## 7. Schema 分布

| Schema | 条数 |
|--------|------|
| shulex_standard | 22411 |