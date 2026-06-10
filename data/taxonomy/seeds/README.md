# 品类 Taxonomy 数据上传规范

> 用途：V4-T1 Taxonomy 扩到 5 个核心品类
> 范围：3C 配件 / 母婴用品 / 宠物用品 / 服装（家具家居已完成）

## 上传流程

### 1. CSV 文件命名

`data/processed/{category_slug}_v1.0.csv`

| 品类 | category_slug | sub_category 示例 |
|------|---------------|--------------------|
| 3C 配件 | 3c | 耳机 / 充电器 / 数据线 / 键鼠 |
| 母婴用品 | baby | 咳嗽机 / 奶瓶 / 安全座椅 / 童车 |
| 宠物用品 | pet | 狗粮 / 猫砂 / 背带 / 狗床 |
| 服装 | apparel | T恤 / 运动鞋 / 背包 / 运动服 |

### 2. CSV 必须包含的字段

| 字段 | 必需 | 说明 |
|------|------|------|
| review_id | ✅ | 全局唯一 ID（建议格式：`{prefix}-NNNNNN`，如 `3C-000001`）|
| category | ✅ | 大类中文名（如「3C 配件」）|
| sub_category | ✅ | 子品类中文名（如「耳机」）|
| asin | ⚪ | Amazon ASIN，用于跨产品关联 |
| title | ⚪ | 评论标题（可空）|
| content | ✅ | 评论正文（≥ 10 字符）|
| rating | ✅ | 1-5 整数 |
| date | ⚪ | 评论日期 ISO 格式 |
| nation | ⚪ | 用户所在地（us / de / uk 等）|
| language | ⚪ | 评论语言（en / es / de 等）|

每品类建议 **5000+ 条**，分布要求：

- 5 个评分（1-5 星）每档至少 500 条
- 至少 4-6 个子品类，每子品类至少 500 条
- 内容长度 20-2000 字符（短的语义不足，长的成本高）

### 3. 上传后告诉我 CSV 路径

我会跑：

```bash
python3 scripts/extract_taxonomy_generic.py \
    --input data/processed/3c_v1.0.csv \
    --category 3C \
    --seed-yaml data/taxonomy/seeds/3c.yaml
```

预估时间：5000 条 ≈ 17 分钟（8 并发）
预估成本：5000 条 ≈ ¥4

输出：

```
data/taxonomy/v1.0/3c/
├── 耳机.yaml
├── 充电器.yaml
├── 数据线.yaml
├── 键鼠.yaml
├── aspect_extraction_raw.jsonl
└── extraction_summary.md
```

### 4. 你 review YAML 文件

抽取完后逐个 yaml 文件 review：

- 检查 `top_phrases` 是否有同义词（如 "easy to use" / "user friendly" 应合并）
- 检查 aspect 命名是否符合你的运营经验
- 删除频次过低（< 5）或不属于该品类的 aspect

review 完后我把 yaml 写进 PG `category_aspect_taxonomy` 表（重跑 `scripts/import_v4t1_assets.py --taxonomy-only`）。

---

## 数据收集建议

如果原始数据从 Shulex 导出：

1. 在 Shulex 后台筛 4 个品类各自 TOP10 ASIN
2. 每 ASIN 导出最近 1000 条评论
3. 合并去重后导出 CSV（`content_hash` 字段做唯一键）

如果从 Helium10 / SellerSprite 导出：

1. 选定 4 个品类的 BSR Top100
2. 拉取近 90 天评论
3. 合并字段映射到上方表格

---

## 已完成的品类

| 品类 | 状态 | 输出 |
|------|------|------|
| 家具家居 | ✅ v1.0（24032 条 → 6 子品类 × 20 aspects）| `data/taxonomy/v1.0/home/床*.yaml` |
| 3C 配件 | ✅ v1.0（21719 条 → 11 子品类 × 16-18 aspects）| `data/taxonomy/v1.0/3c/*.yaml` |
| 母婴用品 | ✅ v1.0（6588 条 → 9 子品类 × 13-19 aspects）| `data/taxonomy/v1.0/baby/*.yaml` |
| 宠物用品 | ✅ v1.0（41536 条 → 26 子品类 × 15-18 aspects）| `data/taxonomy/v1.0/pet/*.yaml` |
| 服装 | ✅ v1.0（18695 条 → 8 子品类 × 21 aspects）| `data/taxonomy/v1.0/apparel/*.yaml` |
| 户外 | ⏸️ 本轮剔除（Erika 2026-06-10 决策）| 原始数据 `/Users/zhangxi/Desktop/评论分析项目/户外/` 保留待下一轮 |

**入库结果**：PostgreSQL `category_aspect_taxonomy` 表共 1060 行（60 sub_category × 平均 17.7 aspect），入库时间 2026-06-10。

**总投入**：DeepSeek API 抽取成本 ¥55.99（4 品类新增），评论合计 112570 条。
