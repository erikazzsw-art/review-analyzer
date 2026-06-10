# 服装 评论数据画像报告

> 生成时间: 2026-06-09 15:35:53
> 数据来源: /Users/zhangxi/Desktop/评论分析项目/服装
> 总条数 (清洗后): **19191**
> 总条数 (原始): 22814

---

## 1. 子品类 (产品类型) 分布

| 子品类 | 条数 | 占比 |
|--------|------|------|
| Bras for Women | 3000 | 15.6% |
| Men's Crew T-Shirts | 3000 | 15.6% |
| mens Underwear | 3000 | 15.6% |
| Water Shoes | 2531 | 13.2% |
| Women's Underwear | 2371 | 12.4% |
| 连衣裙 | 2282 | 11.9% |
| 手提包 | 1710 | 8.9% |
| 上衣 | 1297 | 6.8% |

## 2. 评分分布

| 评分 | 条数 | 占比 |
|------|------|------|
| 5 星 | 10657 | 55.5% |
| 4 星 | 2556 | 13.3% |
| 3 星 | 1927 | 10.0% |
| 2 星 | 1593 | 8.3% |
| 1 星 | 2458 | 12.8% |

**负面率 (≤3 星): 31.2%**
**正面率 (≥4 星): 68.8%**

## 3. 子品类 × 评分交叉

| 子品类 | 1星 | 2星 | 3星 | 4星 | 5星 | 负面率 |
|--------|-----|-----|-----|-----|-----|--------|
| Bras for Women | 344 | 222 | 297 | 329 | 1808 | 28.8% |
| Men's Crew T-Shirts | 389 | 257 | 295 | 365 | 1694 | 31.4% |
| Water Shoes | 425 | 174 | 188 | 301 | 1443 | 31.1% |
| Women's Underwear | 489 | 309 | 274 | 229 | 1070 | 45.2% |
| mens Underwear | 560 | 314 | 264 | 286 | 1576 | 37.9% |
| 上衣 | 47 | 66 | 147 | 274 | 763 | 20.0% |
| 手提包 | 132 | 117 | 164 | 250 | 1047 | 24.2% |
| 连衣裙 | 72 | 134 | 298 | 522 | 1256 | 22.1% |

## 4. TOP 20 ASIN 分布

| ASIN | 子品类 | 条数 | 命中规则 |
|------|--------|------|----------|
| B09Q3MYDQH | Water Shoes | 517 | title/file 兜底 |
| B0CP815WGH | 手提包 | 310 | title/file 兜底 |
| B09Q3NN37M | Water Shoes | 273 | title/file 兜底 |
| B09Q3LV1TQ | Water Shoes | 255 | title/file 兜底 |
| B086L4BXZC | mens Underwear | 239 | title/file 兜底 |
| B09Q4C5MJL | Water Shoes | 225 | title/file 兜底 |
| B09Q3MMT2C | Water Shoes | 225 | title/file 兜底 |
| B086KSDTQ4 | mens Underwear | 210 | title/file 兜底 |
| B0F6VKZ4FB | Bras for Women | 200 | title/file 兜底 |
| B0787P86ZZ | Men's Crew T-Shirts | 197 | title/file 兜底 |
| B0F6V8RDYM | Bras for Women | 186 | title/file 兜底 |
| B0F6V6RW6D | Bras for Women | 185 | title/file 兜底 |
| B0CZLPHTT2 | 手提包 | 180 | title/file 兜底 |
| B0CP816215 | 手提包 | 179 | title/file 兜底 |
| B086LDXW63 | mens Underwear | 175 | title/file 兜底 |
| B0CP7ZYPQ8 | 手提包 | 171 | title/file 兜底 |
| B077ZKDQLV | Men's Crew T-Shirts | 161 | title/file 兜底 |
| B0F6TWKDFK | Bras for Women | 161 | title/file 兜底 |
| B0F6V6WNTS | Bras for Women | 157 | title/file 兜底 |
| B086KYKR6Q | mens Underwear | 151 | title/file 兜底 |

## 5. 未命中 ASIN 映射表的 TOP 30 ASIN (供补 asin_product_type)

> 这些 ASIN 数量大但 `asin_product_type` 表里没有, 当前靠 title 关键词兜底归类.
> 建议: 看 Amazon listing 后在 yaml 配置里补 `asin_product_type: {ASIN: 产品类型}`, 重跑预处理.

| ASIN | 当前归类 | 条数 | TOP1 评论标题样例 |
|------|----------|------|-------------------|
| B09Q3MYDQH | Water Shoes | 517 | Thin soled but a solid shoe otherwise. |
| B0CP815WGH | 手提包 | 310 | Church Clerk |
| B09Q3NN37M | Water Shoes | 273 | Good purchase |
| B09Q3LV1TQ | Water Shoes | 255 | Great deal |
| B086L4BXZC | mens Underwear | 239 | Not for thick thighs! |
| B09Q4C5MJL | Water Shoes | 225 | Great shoes! |
| B09Q3MMT2C | Water Shoes | 225 | Great! |
| B086KSDTQ4 | mens Underwear | 210 | OK purchase but  not great |
| B0F6VKZ4FB | Bras for Women | 200 | So soft and seamless |
| B0787P86ZZ | Men's Crew T-Shirts | 197 | Good quality |
| B0F6V8RDYM | Bras for Women | 186 | Let's Joli bras |
| B0F6V6RW6D | Bras for Women | 185 | Fit |
| B0CZLPHTT2 | 手提包 | 180 | Beautiful |
| B0CP816215 | 手提包 | 179 | Perfect bag, right size, good price, works well! |
| B086LDXW63 | mens Underwear | 175 | Uncomfortable material/Cuts into thighs |
| B0CP7ZYPQ8 | 手提包 | 171 | Nice |
| B077ZKDQLV | Men's Crew T-Shirts | 161 | Great quality |
| B0F6TWKDFK | Bras for Women | 161 | Wear all day & comfortable |
| B0F6V6WNTS | Bras for Women | 157 | Straps will not stay up |
| B086KYKR6Q | mens Underwear | 151 | Suggest briefs |
| B0B57JC9R6 | mens Underwear | 151 | Fit and Comfortable. |
| B07JDFPQTC | Men's Crew T-Shirts | 150 | Quality product at a reasonable price. |
| B077ZJXCTS | Men's Crew T-Shirts | 147 | Not like store bought one's I buy |
| B07JCS8NRC | Men's Crew T-Shirts | 147 | They don't shrink 🙂 |
| B077ZMKWVM | Men's Crew T-Shirts | 144 | I buy these all the time, great go-to Tshirt. |
| B086L79Q6X | mens Underwear | 139 | The serve the purpose, but wouldn’t buy again |
| B077ZL5935 | Men's Crew T-Shirts | 139 | Holes in shirts |
| B0CZLX9YFZ | 手提包 | 137 | For Less Wet Weather... |
| B0F6V6WNTW | Bras for Women | 133 | I can throw away all the others!!! |
| B09G4T3V2P | mens Underwear | 132 | Too thin |

## 6. 语言分布

| 语言 | 条数 | 占比 |
|------|------|------|
| en | 19191 | 100.0% |

## 7. Schema 分布

| Schema | 条数 |
|--------|------|
| shulex_standard | 15612 |
| public_dataset | 3579 |