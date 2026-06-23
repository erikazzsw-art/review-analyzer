"""通用品类评论数据预处理脚本.

V4-T1 Step 3 扩展: 把家具家居预处理流程通用化, 通过 yaml 配置驱动支持任意品类.

设计:
- 复用 preprocess_furniture_data.py 的核心函数 (schema 检测、normalize_*、去重、画像)
- 子品类识别改为 3 级匹配:
  1) 文件名关键词 (file_to_sub)
  2) ASIN 映射表 (asin_product_type)  ← 大杂烩文件按产品类型细分
  3) Title/Model 关键词兜底 (title_keywords)
- 输出 data/processed/{slug}_v1.0.{parquet,csv} + data/profile_reports/{slug}_profile_v1.0.md

用法:
    python3 scripts/preprocess_reviews.py --config data/preprocess_configs/3c.yaml
    python3 scripts/preprocess_reviews.py --config data/preprocess_configs/outdoor.yaml --limit 1000

配置 yaml schema 详见 data/preprocess_configs/README.md (本任务一并产出).
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Any, Optional

import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# 复用家具预处理脚本中的纯函数 (无副作用)
from scripts.preprocess_furniture_data import (  # type: ignore[import-not-found]
    UNIFIED_COLUMNS,
    _coalesce,
    detect_language,
    detect_schema,
    extract_asin,
    normalize_rating,
)


def _read_excel_or_csv(path: Path) -> pd.DataFrame | None:
    fname = path.name
    try:
        if path.suffix.lower() in (".xlsx", ".xls"):
            return pd.read_excel(path, engine="openpyxl")
        if path.suffix.lower() == ".csv":
            return pd.read_csv(path, low_memory=False)
    except Exception as e:
        print(f"  [SKIP] {fname}: 读取失败 - {type(e).__name__}: {e}")
    return None


def _match_keywords(text: str, keywords: list[str]) -> bool:
    fl = text.lower()
    return any(k.lower() in fl for k in keywords)


# 源 Excel 中可能的"产品类型"列名 (Erika 手工分类后加的列)
PRODUCT_TYPE_COLUMNS = ("product_type", "产品类型", "Product Type", "ProductType")


def detect_sub_category(
    fname: str,
    asin: str,
    title: str,
    model: str,
    rules: dict,
) -> str:
    """3 级匹配判断子品类 (产品类型). 仅在源 Excel 没有 product_type 列时启用.

    Args:
        fname: 文件名
        asin: ASIN 字符串 (可空)
        title: 评论标题 (可空)
        model: Model 字段 (颜色/尺寸描述, 可空)
        rules: 配置 yaml 中加载的规则 dict, 含 file_to_sub / asin_product_type / title_keywords / default_*
    """
    # 1) 文件名关键词
    for rule in rules.get("file_to_sub", []):
        if _match_keywords(fname, rule.get("match", [])):
            sub = rule.get("sub", "")
            if not sub.startswith("_split_by_asin"):
                return sub
            # 命中拆分标记, 进入下一级
            break

    # 2) ASIN 映射表
    asin_map = rules.get("asin_product_type", {}) or {}
    if asin and asin in asin_map:
        return asin_map[asin]

    # 3) Title/Model 关键词兜底
    fallback_text = f"{title} {model}".strip()
    for rule in rules.get("title_keywords", []):
        if _match_keywords(fallback_text, rule.get("match", [])):
            return rule.get("sub", "")

    # 兜底
    return rules.get("default_split") or rules.get("default_sub", "其他")


def _resolve_product_type_column(df: pd.DataFrame) -> str | None:
    """如果 df 里有用户手工加的产品类型列, 返回列名; 否则 None."""
    for col in PRODUCT_TYPE_COLUMNS:
        if col in df.columns:
            return col
    return None


def normalize_shulex(
    df: pd.DataFrame, fname: str, schema: str, category_label: str, rules: dict,
) -> pd.DataFrame:
    """归一化 Shulex 导出格式. sub_category 优先读源 Excel 的 product_type 列, 否则走 3 级匹配."""
    out = pd.DataFrame(index=df.index)
    out["category"] = category_label
    asin_series = df.get("Asin", pd.Series([extract_asin(fname)] * len(df))).fillna("").astype(str)
    out["asin"] = asin_series
    title_en = df.get("English Title", pd.Series([""] * len(df)))
    title_orig = df.get("Title", pd.Series([""] * len(df)))
    out["title"] = _coalesce(title_orig, title_en).fillna("").astype(str)
    content_en = df.get("English Content", pd.Series([""] * len(df)))
    content_orig = df.get("Content", pd.Series([""] * len(df)))
    out["content"] = _coalesce(content_orig, content_en).fillna("").astype(str)
    out["rating"] = df.get("Rating", pd.Series([None] * len(df))).apply(normalize_rating)
    out["date"] = df.get("Date", pd.Series([""] * len(df))).fillna("").astype(str)
    out["reviewer"] = df.get("Author", pd.Series([""] * len(df))).fillna("").astype(str)
    out["verified"] = df.get("Verified Purchase", pd.Series([""] * len(df))).fillna("").astype(str)
    out["nation"] = df.get("Nation", pd.Series([""] * len(df))).fillna("").astype(str)
    model_series = df.get("Model", pd.Series([""] * len(df))).fillna("").astype(str)

    pt_col = _resolve_product_type_column(df)
    if pt_col is not None:
        out["sub_category"] = (
            df[pt_col].fillna("").astype(str).str.strip()
            .replace("", rules.get("default_sub", "其他"))
        )
    else:
        out["sub_category"] = [
            detect_sub_category(fname, a, t, m, rules)
            for a, t, m in zip(asin_series, out["title"], model_series)
        ]

    out["source_file"] = fname
    out["source_schema"] = schema
    return out


def normalize_self_owned(df: pd.DataFrame, fname: str, category_label: str, rules: dict) -> pd.DataFrame:
    out = pd.DataFrame(index=df.index)
    out["category"] = category_label
    asin = extract_asin(fname) or ""
    out["asin"] = asin
    out["title"] = df.get("title", pd.Series([""] * len(df))).fillna("").astype(str)
    out["content"] = df.get("content", pd.Series([""] * len(df))).fillna("").astype(str)
    out["rating"] = df.get("rating", pd.Series([None] * len(df))).apply(normalize_rating)
    out["date"] = df.get("date", pd.Series([""] * len(df))).fillna("").astype(str)
    out["reviewer"] = df.get("reviewer", pd.Series([""] * len(df))).fillna("").astype(str)
    out["verified"] = df.get("verified", pd.Series([""] * len(df))).fillna("").astype(str)
    out["nation"] = ""
    pt_col = _resolve_product_type_column(df)
    if pt_col is not None:
        out["sub_category"] = (
            df[pt_col].fillna("").astype(str).str.strip()
            .replace("", rules.get("default_sub", "其他"))
        )
    else:
        out["sub_category"] = [
            detect_sub_category(fname, asin, t, "", rules) for t in out["title"]
        ]
    out["source_file"] = fname
    out["source_schema"] = "self_owned"
    return out


def normalize_public(df: pd.DataFrame, fname: str, category_label: str, rules: dict) -> pd.DataFrame:
    """Kaggle Women's E-Commerce Reviews 公开数据集格式 (Tops/Dresses 文件)."""
    out = pd.DataFrame(index=df.index)
    out["category"] = category_label
    out["asin"] = ""
    out["title"] = df.get("Title", pd.Series([""] * len(df))).fillna("").astype(str)
    out["content"] = df.get("Review Text", pd.Series([""] * len(df))).fillna("").astype(str)
    out["rating"] = df.get("Rating", pd.Series([None] * len(df))).apply(normalize_rating)
    out["date"] = ""
    out["reviewer"] = ""
    out["verified"] = ""
    out["nation"] = ""
    pt_col = _resolve_product_type_column(df)
    if pt_col is not None:
        out["sub_category"] = (
            df[pt_col].fillna("").astype(str).str.strip()
            .replace("", rules.get("default_sub", "其他"))
        )
    else:
        # 公开数据集 ASIN 为空, 仅靠文件名 + title 关键词判断
        out["sub_category"] = [
            detect_sub_category(fname, "", t, "", rules) for t in out["title"]
        ]
    out["source_file"] = fname
    out["source_schema"] = "public_dataset"
    return out


def process_file(path: Path, category_label: str, rules: dict) -> pd.DataFrame | None:
    fname = path.name
    df = _read_excel_or_csv(path)
    if df is None or df.empty:
        return None
    schema = detect_schema(df.columns.tolist())
    if schema in ("shulex_standard", "shulex_dirty"):
        return normalize_shulex(df, fname, schema, category_label, rules)
    if schema == "self_owned":
        return normalize_self_owned(df, fname, category_label, rules)
    if schema == "public_dataset":
        return normalize_public(df, fname, category_label, rules)
    print(f"  [SKIP] {fname}: 未识别 schema, 列名样例={df.columns.tolist()[:5]}")
    return None


def add_metadata(df: pd.DataFrame, prefix: str) -> pd.DataFrame:
    df = df.reset_index(drop=True)
    df["review_id"] = df.index.map(lambda i: f"{prefix}-{i+1:06d}")
    df["language"] = df["content"].apply(detect_language)
    return df[UNIFIED_COLUMNS]


def filter_invalid(df: pd.DataFrame) -> pd.DataFrame:
    before = len(df)
    df = df[df["content"].notna() & (df["content"].str.len() >= 5)].copy()
    print(f"过滤无效: {before} -> {len(df)} (移除 {before - len(df)} 条)")
    return df


def deduplicate(df: pd.DataFrame) -> pd.DataFrame:
    before = len(df)
    df = df.drop_duplicates(
        subset=["content", "rating", "asin", "reviewer"], keep="first"
    ).copy()
    print(f"去重: {before} -> {len(df)} (移除 {before - len(df)} 条)")
    return df


def sample_per_sub(df: pd.DataFrame, sample_per_sub_limit: int, seed: int = 42) -> pd.DataFrame:
    """每子品类等比抽样, 控制后续 GPT 抽取成本."""
    if not sample_per_sub_limit:
        return df
    pieces = []
    for _sub, group in df.groupby("sub_category"):
        n = min(len(group), sample_per_sub_limit)
        pieces.append(group.sample(n=n, random_state=seed))
    sampled = pd.concat(pieces, ignore_index=True)
    print(f"抽样 (每子品类 ≤ {sample_per_sub_limit}): {len(df)} -> {len(sampled)}")
    return sampled


def generate_profile_report(
    df: pd.DataFrame, raw_df: pd.DataFrame, category_label: str, source_dirs: list[str], rules: dict,
) -> str:
    """生成画像报告. 关键: 列出未命中 ASIN 清单, 供 Erika 补 asin_product_type 表."""
    lines: list[str] = [
        f"# {category_label} 评论数据画像报告",
        "",
        f"> 生成时间: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"> 数据来源: {' / '.join(source_dirs)}",
        f"> 总条数 (清洗后): **{len(df)}**",
        f"> 总条数 (原始): {len(raw_df)}",
        "",
        "---",
        "",
        "## 1. 子品类 (产品类型) 分布",
        "",
        "| 子品类 | 条数 | 占比 |",
        "|--------|------|------|",
    ]
    for sub, count in df["sub_category"].value_counts().items():
        lines.append(f"| {sub} | {count} | {count/len(df)*100:.1f}% |")

    lines += [
        "",
        "## 2. 评分分布",
        "",
        "| 评分 | 条数 | 占比 |",
        "|------|------|------|",
    ]
    for rating, count in df["rating"].value_counts().sort_index(ascending=False).items():
        if pd.notna(rating):
            lines.append(f"| {int(rating)} 星 | {count} | {count/len(df)*100:.1f}% |")
    null_rating = df["rating"].isna().sum()
    if null_rating:
        lines.append(f"| 缺失 | {null_rating} | {null_rating/len(df)*100:.1f}% |")
    neg = len(df[df["rating"].notna() & (df["rating"] <= 3)])
    pos = len(df[df["rating"].notna() & (df["rating"] >= 4)])
    lines += [
        "",
        f"**负面率 (≤3 星): {neg/len(df)*100:.1f}%**",
        f"**正面率 (≥4 星): {pos/len(df)*100:.1f}%**",
    ]

    # 子品类 × 评分交叉
    lines += [
        "",
        "## 3. 子品类 × 评分交叉",
        "",
        "| 子品类 | 1星 | 2星 | 3星 | 4星 | 5星 | 负面率 |",
        "|--------|-----|-----|-----|-----|-----|--------|",
    ]
    for sub in df["sub_category"].unique():
        sub_df = df[df["sub_category"] == sub]
        rc = sub_df["rating"].value_counts()
        r1, r2, r3, r4, r5 = (rc.get(i, 0) for i in (1, 2, 3, 4, 5))
        total_rated = r1 + r2 + r3 + r4 + r5
        nr = (r1 + r2 + r3) / total_rated * 100 if total_rated else 0
        lines.append(f"| {sub} | {r1} | {r2} | {r3} | {r4} | {r5} | {nr:.1f}% |")

    # ASIN 维度: TOP 20 + 未命中清单
    lines += [
        "",
        "## 4. TOP 20 ASIN 分布",
        "",
        "| ASIN | 子品类 | 条数 | 命中规则 |",
        "|------|--------|------|----------|",
    ]
    asin_map_rules = rules.get("asin_product_type", {}) or {}
    asin_dist = df.groupby(["asin", "sub_category"]).size().reset_index(name="count")
    asin_dist = asin_dist[asin_dist["asin"] != ""].sort_values("count", ascending=False).head(20)
    for _, row in asin_dist.iterrows():
        hit = "ASIN表" if row["asin"] in asin_map_rules else "title/file 兜底"
        lines.append(f"| {row['asin']} | {row['sub_category']} | {row['count']} | {hit} |")

    # 未命中 ASIN 清单 (重点: 给 Erika 补映射用)
    lines += [
        "",
        "## 5. 未命中 ASIN 映射表的 TOP 30 ASIN (供补 asin_product_type)",
        "",
        "> 这些 ASIN 数量大但 `asin_product_type` 表里没有, 当前靠 title 关键词兜底归类.",
        "> 建议: 看 Amazon listing 后在 yaml 配置里补 `asin_product_type: {ASIN: 产品类型}`, 重跑预处理.",
        "",
        "| ASIN | 当前归类 | 条数 | TOP1 评论标题样例 |",
        "|------|----------|------|-------------------|",
    ]
    unmapped = (
        df[(df["asin"] != "") & (~df["asin"].isin(asin_map_rules.keys()))]
        .groupby(["asin", "sub_category"])
        .size()
        .reset_index(name="count")
        .sort_values("count", ascending=False)
        .head(30)
    )
    for _, row in unmapped.iterrows():
        sample_title = (
            df[df["asin"] == row["asin"]]["title"].dropna().astype(str)
            .map(lambda x: x[:80]).iloc[0]
            if (df["asin"] == row["asin"]).any() else ""
        )
        lines.append(f"| {row['asin']} | {row['sub_category']} | {row['count']} | {sample_title} |")

    # 语言/Schema/字段空值
    lines += [
        "",
        "## 6. 语言分布",
        "",
        "| 语言 | 条数 | 占比 |",
        "|------|------|------|",
    ]
    for lang, count in df["language"].value_counts().items():
        lines.append(f"| {lang} | {count} | {count/len(df)*100:.1f}% |")

    lines += [
        "",
        "## 7. Schema 分布",
        "",
        "| Schema | 条数 |",
        "|--------|------|",
    ]
    for s, count in df["source_schema"].value_counts().items():
        lines.append(f"| {s} | {count} |")

    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="通用品类评论预处理")
    parser.add_argument("--config", required=True, help="品类配置 yaml 路径")
    parser.add_argument("--limit", type=int, default=0, help="0=全量,>0=每个文件只读前 N 行用于调试")
    parser.add_argument("--no-sample", action="store_true", help="跳过子品类等比抽样")
    args = parser.parse_args()

    config_path = Path(args.config)
    if not config_path.exists():
        print(f"错误: 配置不存在 {config_path}", file=sys.stderr)
        return 1

    with config_path.open("r", encoding="utf-8") as f:
        cfg: dict[str, Any] = yaml.safe_load(f)

    category_label = cfg["category_label"]
    category_slug = cfg["category_slug"]
    review_id_prefix = cfg.get("review_id_prefix", category_slug.upper())
    source_dirs = [Path(d) for d in cfg.get("source_dirs") or []]
    sample_limit = int(cfg.get("sample_per_sub", 0))

    output_dir = ROOT / "data" / "processed"
    report_dir = ROOT / "data" / "profile_reports"
    output_dir.mkdir(parents=True, exist_ok=True)
    report_dir.mkdir(parents=True, exist_ok=True)

    # 收集源文件
    files: list[Path] = []
    for d in source_dirs:
        if not d.exists():
            print(f"[WARN] 源目录不存在: {d}")
            continue
        for f in sorted(d.iterdir()):
            if f.name.startswith(".") or f.name.startswith("~"):
                continue
            if f.suffix.lower() in (".xlsx", ".xls", ".csv"):
                files.append(f)

    if not files:
        print(f"错误: 在 source_dirs 下没找到任何 xlsx/csv 文件: {source_dirs}", file=sys.stderr)
        return 1

    print(f"\n[{category_label}] 扫描到 {len(files)} 个文件\n")
    all_dfs: list[pd.DataFrame] = []
    for path in files:
        print(f"  [READ] {path.name}")
        df = process_file(path, category_label, cfg)
        if df is None or len(df) == 0:
            continue
        if args.limit:
            df = df.head(args.limit)
        all_dfs.append(df)
        sub_dist = df["sub_category"].value_counts().to_dict()
        print(f"         -> {len(df)} 条, 子品类分布: {sub_dist}")

    if not all_dfs:
        print("错误: 没有可处理的数据", file=sys.stderr)
        return 1

    raw = pd.concat(all_dfs, ignore_index=True)
    print(f"\n合并: 总计 {len(raw)} 条")

    cleaned = filter_invalid(raw)
    cleaned = deduplicate(cleaned)
    cleaned = add_metadata(cleaned, review_id_prefix)
    if not args.no_sample:
        cleaned = sample_per_sub(cleaned, sample_limit)
    cleaned = cleaned.reset_index(drop=True)

    # 输出
    csv_path = output_dir / f"{category_slug}_v1.0.csv"
    parquet_path = output_dir / f"{category_slug}_v1.0.parquet"
    cleaned.to_csv(csv_path, index=False)
    cleaned.to_parquet(parquet_path, index=False)
    print(f"\n[OUT] CSV:     {csv_path}  ({len(cleaned)} 条)")
    print(f"[OUT] Parquet: {parquet_path}")

    report = generate_profile_report(cleaned, raw, category_label, [str(d) for d in source_dirs], cfg)
    report_path = report_dir / f"{category_slug}_profile_v1.0.md"
    report_path.write_text(report, encoding="utf-8")
    print(f"[OUT] 画像:    {report_path}")

    print("\n" + "=" * 60)
    print(f"处理完成 [{category_label}]")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
