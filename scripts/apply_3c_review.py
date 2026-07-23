"""Step 9: Apply Erika's reviewer_notes corrections to 3C golden set.

Parses reviewer_notes in the CSV, applies corrections (修正/可补/可删),
re-translates affected Chinese JSON fields, and saves the corrected CSV.

Usage:
    python3 scripts/apply_3c_review.py
"""
from __future__ import annotations

import csv
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Any

from review_analyzer.router_client import OpenAI

ROOT = Path(__file__).resolve().parent.parent
INPUT_CSV = ROOT / "data" / "golden_set" / "v1.1" / "3c" / "ai_annotated_50.csv"
OUTPUT_CSV = ROOT / "data" / "golden_set" / "v1.1" / "3c" / "ai_annotated_50_reviewed.csv"
TAXONOMY_FILE = ROOT / "data" / "taxonomy" / "v1.0" / "3c" / "iphone_charger.yaml"
MODEL = "router"
BASE_URL = "router"


def load_key_zh_map() -> dict[str, str]:
    """Load taxonomy key->label_zh mapping."""
    import yaml
    data = yaml.safe_load(TAXONOMY_FILE.read_text(encoding="utf-8"))
    return {a["key"]: a["label_zh"] for a in data["aspects"]}


def parse_operations(notes: str) -> list[dict[str, Any]]:
    """Parse reviewer_notes into a list of structured operations."""
    ops: list[dict[str, Any]] = []

    # 修正 {key: "X"} → {key: "Y", polarity: "Z", evidence_span: "...", evidence_level: "W"}
    fix_pattern = (
        r'修正\s*\{key:\s*"([^"]+)"\}\s*→\s*'
        r'\{key:\s*"([^"]+)",\s*polarity:\s*"([^"]+)",\s*'
        r'evidence_span:\s*"([^"]+)",\s*evidence_level:\s*"([^"]+)"\}'
    )
    for m in re.finditer(fix_pattern, notes):
        ops.append({
            "type": "fix",
            "old_key": m.group(1),
            "key": m.group(2),
            "polarity": m.group(3),
            "evidence_span": m.group(4),
            "evidence_level": m.group(5),
        })

    # 可补 {key: "X", polarity: "Y", evidence_span: "...", evidence_level: "W"}
    add_pattern = (
        r'可补\s*\{key:\s*"([^"]+)",\s*polarity:\s*"([^"]+)",\s*'
        r'evidence_span:\s*"([^"]+)",\s*evidence_level:\s*"([^"]+)"\}'
    )
    for m in re.finditer(add_pattern, notes):
        ops.append({
            "type": "add",
            "key": m.group(1),
            "polarity": m.group(2),
            "evidence_span": m.group(3),
            "evidence_level": m.group(4),
        })

    # 可删 {key: "X"}
    del_pattern = r'可删\s*\{key:\s*"([^"]+)"\}'
    for m in re.finditer(del_pattern, notes):
        ops.append({
            "type": "delete",
            "key": m.group(1),
        })

    return ops


def translate_text(client: OpenAI, text: str) -> str:
    """Translate English text to Chinese using the unified LLM Router."""
    if not text or not text.strip():
        return ""
    try:
        resp = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": "You are a translator. Translate the following English to Simplified Chinese. Output ONLY the translation, no explanation."},
                {"role": "user", "content": text[:2000]},
            ],
            temperature=0.1,
            max_tokens=600,
        )
        return (resp.choices[0].message.content or "").strip()
    except Exception as e:
        print(f"  ⚠️ Translation failed: {e}")
        return ""


def rebuild_zh_json(aspects: list[dict], key_zh_map: dict[str, str], client: OpenAI | None = None) -> str:
    """Rebuild Chinese JSON for aspects list with translations.

    Tries API translation first; falls back to English evidence_span if API unavailable.
    """
    result = []
    pol_map = {"positive": "正面", "negative": "负面", "neutral": "中性"}
    lvl_map = {"certain": "确定", "probable": "很可能", "uncertain": "不确定"}

    for a in aspects:
        span_en = a.get("evidence_span", "")
        span_zh = ""
        if client and span_en:
            span_zh = translate_text(client, span_en)
        if not span_zh:
            span_zh = span_en  # fallback: keep English

        entry = {
            "key": a["key"],
            "polarity": a.get("polarity", ""),
            "evidence_span": span_en,
            "evidence_level": a.get("evidence_level", ""),
            "label_zh": key_zh_map.get(a["key"], a["key"]),
            "evidence_span_zh": span_zh,
            "polarity_zh": pol_map.get(a.get("polarity", ""), ""),
            "evidence_level_zh": lvl_map.get(a.get("evidence_level", ""), ""),
        }
        result.append(entry)

    return json.dumps(result, ensure_ascii=False)


def main():
    api_key = os.environ.get("DEEPSEEK_API_KEY")
    client = None
    if api_key:
        try:
            client = OpenAI(api_key=api_key, base_url=BASE_URL)
        except Exception:
            pass

    if client is None:
        print("⚠️ 未检测到可用的 LLM API Key，中文翻译将回退到英文原文")

    key_zh_map = load_key_zh_map()
    print(f"Loaded taxonomy: {len(key_zh_map)} aspects")

    # Read CSV
    rows: list[dict[str, str]] = []
    with open(INPUT_CSV, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)

    print(f"Loaded {len(rows)} rows from CSV")

    # Apply corrections
    reviewed_count = 0
    total_ops = 0
    for i, row in enumerate(rows):
        notes = row.get("reviewer_notes", "").strip()
        if not notes:
            continue

        aspects = json.loads(row["ai_aspects_json"]) if row.get("ai_aspects_json") else []
        ops = parse_operations(notes)

        if not ops:
            print(f"  ⚠️ Row {i}: reviewer_notes present but no ops parsed")
            continue

        print(f"\nRow {i}: {row['content'][:60]}...")
        for op in ops:
            if op["type"] == "fix":
                found = False
                for a in aspects:
                    if a["key"] == op["old_key"]:
                        print(f"  修正: {a['key']} → {op['key']}")
                        a["key"] = op["key"]
                        a["polarity"] = op["polarity"]
                        a["evidence_span"] = op["evidence_span"]
                        a["evidence_level"] = op["evidence_level"]
                        found = True
                        total_ops += 1
                        break
                if not found:
                    print(f"  ⚠️ 修正 target '{op['old_key']}' not found in aspects")

            elif op["type"] == "add":
                new_a = {
                    "key": op["key"],
                    "polarity": op["polarity"],
                    "evidence_span": op["evidence_span"],
                    "evidence_level": op["evidence_level"],
                }
                aspects.append(new_a)
                print(f"  可补: +{op['key']}")
                total_ops += 1

            elif op["type"] == "delete":
                before = len(aspects)
                aspects = [a for a in aspects if a["key"] != op["key"]]
                if len(aspects) < before:
                    print(f"  可删: -{op['key']}")
                    total_ops += 1
                else:
                    print(f"  ⚠️ 可删 target '{op['key']}' not found in aspects")

        # Update row
        row["ai_aspects_json"] = json.dumps(aspects, ensure_ascii=False)
        row["annotation_status"] = "reviewed"

        # Rebuild Chinese JSON for corrected row
        print(f"  Rebuilding zh JSON for {len(aspects)} aspects...")
        row["ai_aspects_json_zh"] = rebuild_zh_json(aspects, key_zh_map, client)

        reviewed_count += 1

    print(f"\n{'='*50}")
    print(f"Applied {total_ops} operations across {reviewed_count} rows")

    # Write corrected CSV
    fieldnames = list(rows[0].keys())
    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    print(f"Corrected CSV saved: {OUTPUT_CSV}")


if __name__ == "__main__":
    main()
