#!/usr/bin/env python3
"""
apply_pet_golden_review.py — 宠物品类 Golden Set 人工仲裁批处理

读取 data/golden_set/v1.1/pet/ai_annotated_50.csv，
将 reviewer_notes 中的仲裁意见结构化到 reviewed_sentiment / reviewed_aspects 列，
并更新 annotation_status 为 reviewed。
"""

import csv
import json
import re
import sys
from pathlib import Path


def parse_aspects_from_notes(notes: str) -> list[dict] | None:
    """从 reviewer_notes 中提取结构化的 AI Aspects 修正块。

    支持两种格式：
      - AI Aspects: [{key: "xxx", polarity: "yyy", ...}, ...]
      - ai_aspects: [{"key": "xxx", "polarity": "yyy", ...}, ...]
    """
    if not notes or not notes.strip():
        return None

    # 匹配单个 aspect 对象：{key: "name", polarity: "pos/neg/neutral", ...}
    # 兼容 key 有/无引号
    aspect_re = re.compile(
        r'\{(?:["\']?key["\']?\s*:\s*["\']([^"\']+)["\'])\s*,'
        r'\s*(?:["\']?polarity["\']?\s*:\s*["\']([^"\']+)["\'])'
        r'(?:[^}]*)\}',
        re.IGNORECASE,
    )

    matches = aspect_re.findall(notes)
    if not matches:
        return None

    aspects = []
    seen = set()  # 去重：同 key+polarity 只保留一条
    for key, polarity in matches:
        key = key.strip()
        polarity = polarity.strip().lower()
        if polarity not in ("positive", "negative", "neutral"):
            polarity = "neutral"
        dedup = f"{key}|{polarity}"
        if dedup in seen:
            continue
        seen.add(dedup)
        aspects.append({
            "key": key,
            "polarity": polarity,
            "evidence_span": "",
            "evidence_level": "certain",
        })

    return aspects if aspects else None


def parse_sentiment_from_notes(notes: str) -> str | None:
    """从 reviewer_notes 中提取情感修正。"""
    if not notes or not notes.strip():
        return None

    m = re.search(
        r'(?:AI\s*)?Sentiment\s*:\s*(positive|negative|neutral)',
        notes, re.IGNORECASE,
    )
    return m.group(1).lower() if m else None


# ---- 特殊行手动映射（无法通过正则自动解析的 free-text 仲裁） ----
SPECIAL_OVERRIDES: dict[str, dict] = {
    # pet_003: 门垫 - 吸水力差 + 难清洁
    # 对应 taxonomy key: material(吸水力), cleaning(清洁难度)
    "pet_003": {
        "reviewed_aspects": json.dumps([
            {"key": "material", "polarity": "negative",
             "evidence_span": "still find myself having to clean the dogs feet",
             "evidence_level": "certain"},
            {"key": "cleaning", "polarity": "negative",
             "evidence_span": "I would not purchase again",
             "evidence_level": "probable"},
        ], ensure_ascii=False),
    },
    # pet_037: 过敏免疫零食 - reviewer_notes 标注 AI Sentiment: negative
    # 原 AI 标注为 neutral，情感需修正；aspects 保持 AI 原值
    "pet_037": {
        "reviewed_sentiment": "negative",
    },
}


def process_row(row: dict) -> dict:
    """对单行执行仲裁，返回更新后的行。"""
    notes = (row.get("reviewer_notes") or "").strip()
    review_id = row.get("review_id", "")

    # 默认值：沿用 AI 标注
    reviewed_sentiment = row.get("ai_sentiment", "").strip()
    reviewed_aspects = row.get("ai_aspects", "").strip()

    # 应用特殊覆盖
    override = SPECIAL_OVERRIDES.get(review_id, {})
    if "reviewed_sentiment" in override:
        reviewed_sentiment = override["reviewed_sentiment"]
    if "reviewed_aspects" in override:
        reviewed_aspects = override["reviewed_aspects"]

    if notes:
        # 情感修正（正则提取，优先级低于特殊覆盖）
        if "reviewed_sentiment" not in override:
            corrected = parse_sentiment_from_notes(notes)
            if corrected:
                reviewed_sentiment = corrected

        # Aspect 修正（正则提取，优先级低于特殊覆盖）
        if "reviewed_aspects" not in override:
            corrected_aspects = parse_aspects_from_notes(notes)
            if corrected_aspects:
                reviewed_aspects = json.dumps(corrected_aspects, ensure_ascii=False)

    row["reviewed_sentiment"] = reviewed_sentiment
    row["reviewed_aspects"] = reviewed_aspects
    row["annotation_status"] = "reviewed"
    return row


def main():
    root = Path(__file__).resolve().parent.parent
    csv_path = root / "data" / "golden_set" / "v1.1" / "pet" / "ai_annotated_50.csv"

    if not csv_path.exists():
        print(f"❌ 文件不存在: {csv_path}")
        sys.exit(1)

    # 读取
    rows = []
    with open(csv_path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        for row in reader:
            rows.append(process_row(row))

    # 回写
    with open(csv_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    # 统计
    sentiment_changed = sum(
        1 for r in rows
        if r["reviewed_sentiment"] != r["ai_sentiment"]
    )
    aspects_changed = sum(
        1 for r in rows
        if r["reviewed_aspects"] != r["ai_aspects"]
    )
    has_notes = sum(1 for r in rows if (r.get("reviewer_notes") or "").strip())

    print(f"✅ 处理完成: {len(rows)} 条")
    print(f"   annotation_status → reviewed: {len(rows)} 条")
    print(f"   情感修正: {sentiment_changed} 条")
    print(f"   Aspect 修正: {aspects_changed} 条")
    print(f"   含 reviewer_notes: {has_notes} 条")
    print(f"   输出: {csv_path}")


if __name__ == "__main__":
    main()
