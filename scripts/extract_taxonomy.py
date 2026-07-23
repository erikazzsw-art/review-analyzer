"""家具家居 Taxonomy 全量抽取脚本（统一 LLM Router）.

用法:
- 对 24032 条全量数据做 Aspect 抽取（与 annotate_golden_set.py 用同一 prompt）
- 按子品类聚合 phrases，统计频次和情感倾向
- 输出 YAML 格式的子品类 Aspect 词典

输出:
    data/taxonomy/v1.0/{sub_category}.yaml  (6 个子品类各一份)
    data/taxonomy/v1.0/aspect_extraction_raw.csv  (原始抽取结果)
    data/taxonomy/v1.0/extraction_summary.md  (汇总报告)

成本预估（按当前 Router 可用模型计费）:
    24032 条 × ~150 input + ~80 output tokens
    ≈ 3.6M input + 1.92M output
    ≈ ¥3.6 + ¥15.4 = ¥19

时间预估: ~80 分钟 (5 条/秒, 8 并发)

用法:
    python3 scripts/extract_taxonomy.py            # 全量
    python3 scripts/extract_taxonomy.py --limit 100  # 测试用
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

from review_analyzer.router_client import OpenAI

sys.path.insert(0, str(Path(__file__).parent))
from aspect_taxonomy import ASPECT_KEYS, FURNITURE_ASPECTS, POLARITY_VALUES

INPUT_PATH = Path(__file__).parent.parent / "data" / "processed" / "furniture_v1.0.parquet"
OUTPUT_DIR = Path(__file__).parent.parent / "data" / "taxonomy" / "v1.0"

MODEL = "router"
BASE_URL = "router"
MAX_WORKERS = 8
PROMPT_VERSION = "taxonomy_v1.0"

ASPECT_DESC = "\n".join(f"- {k}: {v}" for k, v in FURNITURE_ASPECTS.items())

SYSTEM_PROMPT = f"""You are an Aspect extraction expert for cross-border e-commerce furniture/home reviews.

Your task: For each review, extract all mentioned aspects with their key phrases and sentiment polarity.

ASPECT TAXONOMY (closed list of {len(ASPECT_KEYS)} keys, use English keys ONLY):
{ASPECT_DESC}

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
2. Each phrase should be a CONCISE expression (e.g. "easy to assemble", "stained pillows", "creaks when moved")
3. Use exact wording from review when possible (preserve common phrases for clustering)
4. polarity describes sentiment about THIS aspect (not overall review sentiment)

Output ONLY the JSON object."""


def _build_prompt(row: pd.Series) -> str:
    return (
        f"Sub-category: {row['sub_category']}\n"
        f"Rating: {int(row['rating'])} stars\n"
        f"Title: {row.get('title', '')}\n"
        f"Content: {row['content']}\n\n"
        f"Output JSON:"
    )


def extract_one(client: OpenAI, row: pd.Series) -> dict[str, Any]:
    """对单条评论做 Aspect 抽取."""
    try:
        resp = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
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
            if key not in ASPECT_KEYS:
                continue
            polarity = a.get("polarity", "neutral")
            if polarity not in POLARITY_VALUES:
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
    """按子品类聚合 aspects."""
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


def write_yaml(sub: str, aspects: dict, output_dir: Path) -> Path:
    """为单个子品类写 YAML（不依赖 PyYAML，手写格式）."""
    safe_sub = sub.replace("/", "_")
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
        lines.append(f"    label_zh: {FURNITURE_ASPECTS[key]}")
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


def write_summary(agg: dict, total_reviews: int, total_cost: float, output_dir: Path) -> Path:
    """写汇总报告."""
    lines = [
        "# Taxonomy Extraction Summary v1.0",
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
    for _sub, aspects in agg.items():
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


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=0, help="0 = 全量")
    parser.add_argument("--workers", type=int, default=MAX_WORKERS)
    parser.add_argument("--resume", action="store_true", help="跳过已完成的 review_id")
    args = parser.parse_args()

    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        env_path = Path(__file__).parent.parent / ".env"
        if env_path.exists():
            for line in env_path.read_text().splitlines():
                if line.startswith("DEEPSEEK_API_KEY="):
                    api_key = line.split("=", 1)[1].strip().strip('"').strip("'")
                    break
    if not api_key:
        print("错误: 未找到 DEEPSEEK_API_KEY", file=sys.stderr)
        sys.exit(1)

    client = OpenAI(api_key=api_key, base_url=BASE_URL)

    df = pd.read_parquet(INPUT_PATH)
    df = df[df["rating"].notna() & (df["content"].str.len() >= 10)].copy()
    df["rating"] = df["rating"].astype(int)
    if args.limit:
        df = df.head(args.limit)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    raw_path = OUTPUT_DIR / "aspect_extraction_raw.jsonl"

    # 断点续跑：从已有 jsonl 读取所有完成的 review_id 和已有结果
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
        print(f"断点续跑: 已跳过 {len(completed_ids)} 条已完成样本")
        df = df[~df["review_id"].isin(completed_ids)]

    print(f"待抽取 {len(df)} 条数据 (并发 {args.workers})")
    print(f"模型: {MODEL} | Prompt 版本: {PROMPT_VERSION}\n")

    results: list[dict] = list(existing_results)  # 包含历史结果
    failures: list[dict] = []
    total_in = 0
    total_out = 0
    start = time.time()

    raw_file = open(raw_path, "a" if args.resume else "w", encoding="utf-8")  # noqa: SIM115

    try:
        with ThreadPoolExecutor(max_workers=args.workers) as executor:
            futures = {executor.submit(extract_one, client, row): row for _, row in df.iterrows()}
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
    print(f"\n抽取完成，用时 {elapsed/60:.1f}min")
    print(f"成功 {len(results)} | 失败 {len(failures)}")
    print(f"Token: input {total_in:,} | output {total_out:,}")
    print(f"总成本: ¥{cost:.2f}")
    print(f"\n[OUT] 原始抽取: {raw_path}")

    print("\n开始按子品类聚合...")
    agg = aggregate_by_subcategory(results)

    yaml_paths = []
    for sub in agg:
        yaml_path = write_yaml(sub, agg[sub], OUTPUT_DIR)
        yaml_paths.append(yaml_path)
        print(f"[OUT] {yaml_path.name}")

    summary_path = write_summary(agg, len(results), cost, OUTPUT_DIR)
    print(f"[OUT] 汇总报告: {summary_path}")

    print("\n" + "=" * 60)
    print("Taxonomy 抽取完成")
    print("=" * 60)


if __name__ == "__main__":
    main()
