"""通用品类 Aspect Taxonomy 抽取脚本.

V4-T1 Step 3 扩展：从家具家居 1 个品类扩到 5 个核心品类。

设计：
- 接受任意品类的输入 CSV 和 seed yaml
- 复用 scripts/extract_taxonomy.py 的核心逻辑（GPT-4o 抽取 + 频次聚合）
- 输出到 data/taxonomy/v1.0/{category_slug}/{sub_category}.yaml

用法:
    python3 scripts/extract_taxonomy_generic.py \
        --input data/processed/3c_v1.0.csv \
        --category 3C \
        --seed-yaml data/taxonomy/seeds/3c.yaml

    python3 scripts/extract_taxonomy_generic.py \
        --input data/processed/baby_v1.0.csv \
        --category baby \
        --seed-yaml data/taxonomy/seeds/baby.yaml \
        --limit 100   # 测试用

输入 CSV 字段要求详见 data/taxonomy/seeds/README.md。

成本预估（DeepSeek-V4-flash, ¥1/M input + ¥8/M output）:
    5000 条 ≈ ¥4
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

import pandas as pd
import yaml
from openai import OpenAI

ROOT = Path(__file__).resolve().parent.parent

MODEL = "deepseek-chat"
BASE_URL = "https://api.deepseek.com"
MAX_WORKERS = 8
PROMPT_VERSION = "taxonomy_v1.0_generic"


def _build_system_prompt(aspects_dict: dict[str, str], category_label: str) -> str:
    """从外部 aspect 列表构造 system prompt."""
    aspect_desc = "\n".join(f"- {k}: {v}" for k, v in aspects_dict.items())
    return f"""You are an Aspect extraction expert for cross-border e-commerce {category_label} reviews.

Your task: For each review, extract all mentioned aspects with their key phrases and sentiment polarity.

ASPECT TAXONOMY (closed list of {len(aspects_dict)} keys, use English keys ONLY):
{aspect_desc}

OUTPUT JSON SCHEMA:
{{
  "aspects": [
    {{
      "key": "<one of taxonomy keys>",
      "phrase": "<short key phrase from review, max 60 chars, original language>",
      "polarity": "positive" | "negative" | "neutral"
    }}
  ]
}}

RULES:
1. Extract 0-5 aspects. Use empty array if review is too vague.
2. Each phrase should be a CONCISE expression (e.g. "easy to use", "fits perfectly", "battery dies fast")
3. Use exact wording from review when possible (preserve common phrases for clustering)
4. polarity describes sentiment about THIS aspect (not overall review sentiment)

Output ONLY the JSON object."""


def _build_prompt(row: pd.Series) -> str:
    return (
        f"Sub-category: {row['sub_category']}\n"
        f"Rating: {int(row['rating'])} stars\n"
        f"Title: {row.get('title', '') or ''}\n"
        f"Content: {row['content']}\n\n"
        f"Output JSON:"
    )


def extract_one(client: OpenAI, system_prompt: str, valid_keys: set[str],
                polarities: set[str], row: pd.Series) -> dict[str, Any]:
    try:
        resp = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": _build_prompt(row)},
            ],
            response_format={"type": "json_object"},
            temperature=0,
            max_tokens=400,
        )
        raw = resp.choices[0].message.content
        try:
            obj = json.loads(raw)
        except json.JSONDecodeError:
            return {"review_id": row["review_id"], "ok": False, "error": "json_decode"}

        aspects = obj.get("aspects", [])
        if not isinstance(aspects, list):
            return {"review_id": row["review_id"], "ok": False, "error": "aspects_not_list"}

        valid_aspects = []
        for a in aspects:
            if not isinstance(a, dict):
                continue
            key = a.get("key")
            if key not in valid_keys:
                continue
            polarity = a.get("polarity", "neutral")
            if polarity not in polarities:
                polarity = "neutral"
            phrase = str(a.get("phrase", "")).strip()[:80]
            if phrase:
                valid_aspects.append({"key": key, "phrase": phrase, "polarity": polarity})

        return {
            "review_id": row["review_id"],
            "sub_category": row["sub_category"],
            "rating": int(row["rating"]),
            "asin": row.get("asin", ""),
            "ok": True,
            "aspects": valid_aspects,
            "tokens_in": resp.usage.prompt_tokens,
            "tokens_out": resp.usage.completion_tokens,
        }
    except Exception as e:
        return {"review_id": row["review_id"], "ok": False, "error": str(e)[:200]}


def aggregate_by_subcategory(results: list[dict]) -> dict[str, dict]:
    agg: dict[str, dict] = defaultdict(lambda: defaultdict(lambda: {
        "phrases": Counter(),
        "positive_count": 0,
        "negative_count": 0,
        "neutral_count": 0,
        "review_ids": [],
    }))

    for r in results:
        if not r.get("ok"):
            continue
        sub = r["sub_category"]
        for a in r["aspects"]:
            key = a["key"]
            slot = agg[sub][key]
            slot["phrases"][a["phrase"]] += 1
            slot[f"{a['polarity']}_count"] += 1
            if len(slot["review_ids"]) < 5:
                slot["review_ids"].append(r["review_id"])
    return agg


def _slugify(text: str) -> str:
    """sub_category → ASCII 文件名 slug.

    保留 ASCII 字母数字, 其余字符 (空格 / 中文 / 西语 / 标点) 全部转下划线; 多个连续下划线压成 1 个.
    例: 'Almohadillas para orinar' → 'almohadillas_para_orinar'
        'Wild Alaskan' → 'wild_alaskan'
        '充电配件' → '_' (全中文会回退到原 sub 替换 / 后的版本, 见调用方)
    """
    import re as _re
    s = _re.sub(r"[^A-Za-z0-9]+", "_", text).strip("_").lower()
    return s


def write_yaml(sub: str, aspects: dict, label_map: dict[str, str], output_dir: Path) -> Path:
    slug = _slugify(sub)
    # 全非 ASCII 时(纯中文 sub_category) slug 会为空, 回退到原 sub 替换 /
    safe_sub = slug if slug else sub.replace("/", "_")
    path = output_dir / f"{safe_sub}.yaml"
    lines = [
        f"# {sub} Aspect Taxonomy v1.0",
        f"# 生成时间: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"sub_category: {sub}",
        f"aspect_count: {len(aspects)}",
        "aspects:",
    ]

    sorted_aspects = sorted(
        aspects.items(),
        key=lambda x: x[1]["positive_count"] + x[1]["negative_count"] + x[1]["neutral_count"],
        reverse=True,
    )
    for key, data in sorted_aspects:
        total = data["positive_count"] + data["negative_count"] + data["neutral_count"]
        neg_pct = data["negative_count"] / total * 100 if total else 0
        lines.append(f"  - key: {key}")
        lines.append(f"    label_zh: {label_map.get(key, key)}")
        lines.append(f"    total: {total}")
        lines.append(f"    positive_count: {data['positive_count']}")
        lines.append(f"    negative_count: {data['negative_count']}")
        lines.append(f"    neutral_count: {data['neutral_count']}")
        lines.append(f"    negative_rate: {neg_pct:.1f}%")
        top_phrases = data["phrases"].most_common(10)
        lines.append("    top_phrases:")
        for phrase, count in top_phrases:
            phrase_safe = phrase.replace('"', "'").replace("\n", " ")
            lines.append(f'      - {{phrase: "{phrase_safe}", count: {count}}}')
        lines.append(f"    sample_reviews: {data['review_ids']}")
        lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def write_summary(agg: dict, total_reviews: int, total_cost: float,
                  category_label: str, output_dir: Path) -> Path:
    lines = [
        f"# {category_label} Taxonomy Extraction Summary v1.0",
        "",
        f"> 生成时间: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"> 总评论数: {total_reviews}",
        f"> 总成本: ¥{total_cost:.2f}",
        "",
        "## 子品类 Aspect 覆盖",
        "",
        "| 子品类 | Aspect 数 | TOP 1 (按频次) | TOP 1 负面率 |",
        "|--------|-----------|----------------|--------------|",
    ]
    for sub, aspects in sorted(agg.items()):
        if not aspects:
            continue
        sorted_aspects = sorted(
            aspects.items(),
            key=lambda x: x[1]["positive_count"] + x[1]["negative_count"] + x[1]["neutral_count"],
            reverse=True,
        )
        top_key, top_data = sorted_aspects[0]
        top_total = top_data["positive_count"] + top_data["negative_count"] + top_data["neutral_count"]
        top_neg = top_data["negative_count"] / top_total * 100 if top_total else 0
        lines.append(f"| {sub} | {len(aspects)} | {top_key} ({top_total}) | {top_neg:.1f}% |")

    lines += [
        "",
        "## 跨子品类 Aspect 分布（合并）",
        "",
        "| Aspect | 总频次 | 总负面数 | 负面率 |",
        "|--------|--------|----------|--------|",
    ]

    overall: dict[str, dict] = defaultdict(lambda: {"total": 0, "negative": 0})
    for sub, aspects in agg.items():
        for key, data in aspects.items():
            total = data["positive_count"] + data["negative_count"] + data["neutral_count"]
            overall[key]["total"] += total
            overall[key]["negative"] += data["negative_count"]

    for key in sorted(overall, key=lambda k: overall[k]["total"], reverse=True):
        d = overall[key]
        neg_pct = d["negative"] / d["total"] * 100 if d["total"] else 0
        lines.append(f"| {key} | {d['total']} | {d['negative']} | {neg_pct:.1f}% |")

    path = output_dir / "extraction_summary.md"
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def _load_seed_yaml(path: Path) -> tuple[dict[str, str], str]:
    """加载 seed yaml,返回 (aspect_key → label_zh map, category_slug).

    支持两种 schema:
    1) 平铺(向后兼容): 顶层 `aspects: [...]`,直接读取
    2) base + delta(v1.0+): 顶层 `extends: base.yaml` + `delta_aspects: [...]`,
       脚本加载同目录下 base.yaml 的 `aspects`,与 delta_aspects 合并(base 优先,
       去重保留顺序),并确保 `other` 始终为最后一项
    """
    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    aspects: dict[str, str] = {}

    extends = data.get("extends")
    if extends:
        base_path = (path.parent / extends).resolve()
        if not base_path.exists():
            raise ValueError(f"seed yaml {path} 声明 extends={extends} 但找不到 {base_path}")
        with base_path.open("r", encoding="utf-8") as f:
            base_data = yaml.safe_load(f)
        for a in base_data.get("aspects", []):
            aspects[a["key"]] = a["label_zh"]
        for a in data.get("delta_aspects", []):
            aspects.setdefault(a["key"], a["label_zh"])
        # `other` 兜底强制移到最后一项
        if "other" in aspects:
            other_label = aspects.pop("other")
            aspects["other"] = other_label
    else:
        for a in data.get("aspects", []):
            aspects[a["key"]] = a["label_zh"]

    if not aspects:
        raise ValueError(f"seed yaml {path} 解析不到 aspects 字段")
    return aspects, data.get("category", path.stem)


def _get_api_key() -> str:
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if api_key:
        return api_key
    env_path = ROOT / ".env"
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            if line.startswith("DEEPSEEK_API_KEY="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    raise RuntimeError("DEEPSEEK_API_KEY 未配置")


def main() -> int:
    parser = argparse.ArgumentParser(description="通用品类 Taxonomy 抽取")
    parser.add_argument("--input", required=True, help="评论 CSV 路径")
    parser.add_argument("--category", required=True,
                        help="品类标识（用于输出目录命名，如 3c / baby / pet / apparel）")
    parser.add_argument("--seed-yaml", required=True, help="seed aspect yaml 路径")
    parser.add_argument("--limit", type=int, default=0, help="0 = 全量")
    parser.add_argument("--workers", type=int, default=MAX_WORKERS)
    parser.add_argument("--resume", action="store_true", help="跳过已完成的 review_id")
    parser.add_argument("--output-dir", default=None,
                        help="输出目录（默认 data/taxonomy/v1.0/{category}）")
    args = parser.parse_args()

    seed_path = Path(args.seed_yaml)
    if not seed_path.exists():
        print(f"错误: seed yaml 不存在 {seed_path}", file=sys.stderr)
        return 1
    aspects_dict, category_label = _load_seed_yaml(seed_path)
    valid_keys = set(aspects_dict.keys())
    print(f"[seed] {seed_path.name} → {len(aspects_dict)} 个 aspects (category={category_label})")

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"错误: 输入 CSV 不存在 {input_path}", file=sys.stderr)
        return 1

    output_dir = Path(args.output_dir) if args.output_dir else (
        ROOT / "data" / "taxonomy" / "v1.0" / args.category
    )
    output_dir.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(input_path)
    required_cols = {"review_id", "sub_category", "rating", "content"}
    missing = required_cols - set(df.columns)
    if missing:
        print(f"错误: CSV 缺少必需字段 {missing}", file=sys.stderr)
        print(f"  当前列: {list(df.columns)}", file=sys.stderr)
        return 1

    df = df[df["rating"].notna() & (df["content"].astype(str).str.len() >= 10)].copy()
    df["rating"] = df["rating"].astype(int)
    if args.limit:
        df = df.head(args.limit)
    print(f"[input] 读取 {len(df)} 条评论")

    raw_path = output_dir / "aspect_extraction_raw.jsonl"

    completed_ids: set[str] = set()
    existing_results: list[dict] = []
    if args.resume and raw_path.exists():
        with open(raw_path, encoding="utf-8") as f:
            for line in f:
                try:
                    obj = json.loads(line)
                    completed_ids.add(obj["review_id"])
                    existing_results.append({
                        "review_id": obj["review_id"],
                        "sub_category": obj["sub_category"],
                        "rating": obj["rating"],
                        "asin": obj.get("asin", ""),
                        "ok": True,
                        "aspects": obj["aspects"],
                    })
                except (json.JSONDecodeError, KeyError):
                    continue
        print(f"[resume] 已跳过 {len(completed_ids)} 条已完成样本")
        df = df[~df["review_id"].isin(completed_ids)]

    print(f"[run] 待抽取 {len(df)} 条 (并发 {args.workers})")
    print(f"[run] 模型 {MODEL} | prompt 版本 {PROMPT_VERSION}\n")

    if len(df) == 0:
        print("没有需要抽取的样本，直接生成 yaml...")
    else:
        client = OpenAI(api_key=_get_api_key(), base_url=BASE_URL)
        system_prompt = _build_system_prompt(aspects_dict, category_label)
        polarities = {"positive", "negative", "neutral"}

    results: list[dict] = list(existing_results)
    failures: list[dict] = []
    total_in = 0
    total_out = 0
    start = time.time()

    raw_file = open(raw_path, "a" if args.resume else "w", encoding="utf-8")

    try:
        if len(df) > 0:
            with ThreadPoolExecutor(max_workers=args.workers) as executor:
                futures = {
                    executor.submit(extract_one, client, system_prompt, valid_keys, polarities, row): row
                    for _, row in df.iterrows()
                }
                done = 0
                for future in as_completed(futures):
                    done += 1
                    res = future.result()
                    if res["ok"]:
                        results.append(res)
                        total_in += res["tokens_in"]
                        total_out += res["tokens_out"]
                        raw_file.write(json.dumps({
                            "review_id": res["review_id"],
                            "sub_category": res["sub_category"],
                            "rating": res["rating"],
                            "asin": res["asin"],
                            "aspects": res["aspects"],
                        }, ensure_ascii=False) + "\n")
                        raw_file.flush()
                    else:
                        failures.append(res)
                    if done % 200 == 0 or done == len(df):
                        elapsed = time.time() - start
                        rate = done / elapsed if elapsed else 0
                        eta = (len(df) - done) / rate if rate else 0
                        cost_so_far = total_in / 1e6 + total_out * 8 / 1e6
                        print(f"  {done}/{len(df)} | 失败 {len(failures)} | 用时 {elapsed:.0f}s | "
                              f"速度 {rate:.1f}/s | ETA {eta/60:.1f}min | 成本 ¥{cost_so_far:.2f}")
    finally:
        raw_file.close()

    elapsed = time.time() - start
    cost = total_in / 1e6 + total_out * 8 / 1e6
    print(f"\n[done] 抽取完成，用时 {elapsed/60:.1f}min")
    print(f"[done] 成功 {len(results)} | 失败 {len(failures)}")
    print(f"[done] Token: input {total_in:,} | output {total_out:,}")
    print(f"[done] 总成本: ¥{cost:.2f}")
    print(f"[done] 原始抽取: {raw_path}")

    print("\n[agg] 按子品类聚合...")
    agg = aggregate_by_subcategory(results)

    yaml_paths = []
    for sub in agg:
        yaml_path = write_yaml(sub, agg[sub], aspects_dict, output_dir)
        yaml_paths.append(yaml_path)
        print(f"[out] {yaml_path.name}")

    summary_path = write_summary(agg, len(results), cost, category_label, output_dir)
    print(f"[out] 汇总报告: {summary_path}")

    print("\n" + "=" * 60)
    print(f"{category_label} Taxonomy 抽取完成")
    print("=" * 60)
    print(f"\n下一步:")
    print(f"  1. Erika review {output_dir} 下的 yaml 文件，合并同义词、删除低频 aspect")
    print(f"  2. review 完成后运行: python3 scripts/import_v4t1_assets.py --taxonomy-only")
    return 0


if __name__ == "__main__":
    sys.exit(main())
