"""V4-T1 数据资产入库脚本 — bad_cases CSV + taxonomy YAML → PostgreSQL.

用法:
    python3 scripts/import_v4t1_assets.py
    python3 scripts/import_v4t1_assets.py --bad-cases-only
    python3 scripts/import_v4t1_assets.py --taxonomy-only
    python3 scripts/import_v4t1_assets.py --dry-run

依赖：
- DATABASE_URL 环境变量 / .env / .streamlit/secrets.toml 中任一处提供
- Supabase 已执行 supabase_schema.sql 中 V4-T1 段（bad_cases / category_aspect_taxonomy 两表）
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from pathlib import Path
from typing import Any

import psycopg2
import yaml
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

load_dotenv(ROOT / ".env")

BAD_CASES_CSV = ROOT / "data" / "golden_set" / "v1.0" / "bad_cases_v1.0.csv"
TAXONOMY_DIR = ROOT / "data" / "taxonomy" / "v1.0"


def _get_database_url() -> str:
    url = os.getenv("DATABASE_URL") or os.getenv("SUPABASE_DB_URL")
    if url:
        return url
    secrets_path = ROOT / ".streamlit" / "secrets.toml"
    if secrets_path.exists():
        try:
            import toml
            secrets = toml.load(secrets_path)
            if isinstance(secrets, dict):
                # 优先嵌套 [database].url（Streamlit 标准），其次顶层 DATABASE_URL
                db_section = secrets.get("database")
                if isinstance(db_section, dict) and db_section.get("url"):
                    return str(db_section["url"]).strip()
                url = secrets.get("DATABASE_URL") or secrets.get("SUPABASE_DB_URL")
                if url:
                    return str(url).strip()
        except Exception:
            pass
    raise RuntimeError(
        "找不到 DATABASE_URL（检查 env / .env / .streamlit/secrets.toml [database].url）"
    )


def _parse_json_field(raw: str | None) -> Any:
    if raw is None or raw == "":
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return None


def import_bad_cases(conn, dry_run: bool = False) -> tuple[int, int]:
    if not BAD_CASES_CSV.exists():
        print(f"  [SKIP] 未找到 {BAD_CASES_CSV}")
        return 0, 0

    rows: list[dict[str, Any]] = []
    with BAD_CASES_CSV.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                rating = int(row["rating"]) if row.get("rating") else None
            except (TypeError, ValueError):
                rating = None
            rows.append({
                "case_id": row["case_id"],
                "review_id": row.get("review_id") or None,
                "sub_category": row["sub_category"],
                "rating": rating,
                "content": row["content"],
                "ai_sentiment": row.get("ai_sentiment") or None,
                "ai_aspects": _parse_json_field(row.get("ai_aspects")),
                "correct_sentiment": None,
                "correct_aspects": None,
                "correction_note": row.get("correction_note") or None,
                "error_category": row.get("error_category") or "unknown",
                "severity": row.get("severity") or "medium",
                "use_for_few_shot": (row.get("use_for_few_shot") or "True").strip().lower()
                in ("true", "1", "yes", "y"),
                "source": "v4t1_csv_import",
                "prompt_version": None,
            })

    print(f"  解析到 {len(rows)} 条 bad_case")

    if dry_run:
        print("  [DRY-RUN] 跳过写库")
        return len(rows), 0

    inserted = 0
    skipped = 0
    with conn.cursor() as cur:
        for row in rows:
            cur.execute(
                """INSERT INTO bad_cases
                   (case_id, review_id, sub_category, rating, content,
                    ai_sentiment, ai_aspects, correct_sentiment, correct_aspects,
                    correction_note, error_category, severity, use_for_few_shot,
                    source, prompt_version)
                   VALUES (%s, %s, %s, %s, %s,
                           %s, %s, %s, %s,
                           %s, %s, %s, %s,
                           %s, %s)
                   ON CONFLICT (case_id) DO NOTHING""",
                (
                    row["case_id"], row["review_id"], row["sub_category"], row["rating"], row["content"],
                    row["ai_sentiment"],
                    json.dumps(row["ai_aspects"], ensure_ascii=False) if row["ai_aspects"] is not None else None,
                    row["correct_sentiment"],
                    json.dumps(row["correct_aspects"], ensure_ascii=False) if row["correct_aspects"] is not None else None,
                    row["correction_note"], row["error_category"], row["severity"], row["use_for_few_shot"],
                    row["source"], row["prompt_version"],
                ),
            )
            if cur.rowcount > 0:
                inserted += 1
            else:
                skipped += 1
    conn.commit()
    print(f"  写入 {inserted} 条新记录 / 跳过 {skipped} 条已存在")
    return inserted, skipped


def import_taxonomy(conn, dry_run: bool = False) -> tuple[int, int]:
    if not TAXONOMY_DIR.exists():
        print(f"  [SKIP] 未找到 {TAXONOMY_DIR}")
        return 0, 0

    # 递归扫描 v1.0/ 及其子目录 (home / 3c / apparel / baby / pet 等),
    # 排除 backup 目录和 seeds 目录 (seeds 是输入,不是产物)
    yaml_files = sorted(
        f for f in TAXONOMY_DIR.rglob("*.yaml")
        if not any(part.startswith("backup-") or part == "seeds" for part in f.parts)
    )
    print(f"  找到 {len(yaml_files)} 个 taxonomy yaml")

    rows: list[dict[str, Any]] = []
    for yf in yaml_files:
        with yf.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        sub_category = data.get("sub_category", yf.stem)
        for aspect in data.get("aspects", []):
            total = int(aspect.get("total", 0))
            negative = int(aspect.get("negative_count", 0))
            negative_rate = (negative / total * 100) if total > 0 else 0
            rows.append({
                "sub_category": sub_category,
                "aspect_key": aspect["key"],
                "label_zh": aspect.get("label_zh", aspect["key"]),
                "total_count": total,
                "positive_count": int(aspect.get("positive_count", 0)),
                "negative_count": negative,
                "neutral_count": int(aspect.get("neutral_count", 0)),
                "negative_rate": round(negative_rate, 2),
                "top_phrases": aspect.get("top_phrases") or [],
                "sample_review_ids": aspect.get("sample_reviews") or [],
                "taxonomy_version": data.get("version") or "v1.0",
            })

    print(f"  解析到 {len(rows)} 条 taxonomy 行")

    if dry_run:
        print("  [DRY-RUN] 跳过写库")
        return len(rows), 0

    inserted = 0
    updated = 0
    BATCH = 50
    with conn.cursor() as cur:
        for i, row in enumerate(rows, 1):
            cur.execute(
                """INSERT INTO category_aspect_taxonomy
                   (sub_category, aspect_key, label_zh, total_count,
                    positive_count, negative_count, neutral_count, negative_rate,
                    top_phrases, sample_review_ids, taxonomy_version)
                   VALUES (%s, %s, %s, %s,
                           %s, %s, %s, %s,
                           %s, %s, %s)
                   ON CONFLICT (sub_category, aspect_key, taxonomy_version)
                   DO UPDATE SET
                       label_zh = EXCLUDED.label_zh,
                       total_count = EXCLUDED.total_count,
                       positive_count = EXCLUDED.positive_count,
                       negative_count = EXCLUDED.negative_count,
                       neutral_count = EXCLUDED.neutral_count,
                       negative_rate = EXCLUDED.negative_rate,
                       top_phrases = EXCLUDED.top_phrases,
                       sample_review_ids = EXCLUDED.sample_review_ids
                   RETURNING (xmax = 0) AS inserted""",
                (
                    row["sub_category"], row["aspect_key"], row["label_zh"], row["total_count"],
                    row["positive_count"], row["negative_count"], row["neutral_count"], row["negative_rate"],
                    json.dumps(row["top_phrases"], ensure_ascii=False),
                    json.dumps(row["sample_review_ids"], ensure_ascii=False),
                    row["taxonomy_version"],
                ),
            )
            result = cur.fetchone()
            if result and result[0]:
                inserted += 1
            else:
                updated += 1
            if i % BATCH == 0:
                conn.commit()
                print(f"  ... {i}/{len(rows)} (新增 {inserted} / 更新 {updated})")
    conn.commit()
    print(f"  新增 {inserted} 条 / 更新 {updated} 条")
    return inserted, updated


def main() -> int:
    parser = argparse.ArgumentParser(description="V4-T1 数据资产入库")
    parser.add_argument("--bad-cases-only", action="store_true", help="只导 bad_cases")
    parser.add_argument("--taxonomy-only", action="store_true", help="只导 taxonomy")
    parser.add_argument("--dry-run", action="store_true", help="解析但不写库")
    args = parser.parse_args()

    print("=" * 80)
    print(f"V4-T1 数据资产入库 (dry_run={args.dry_run})")
    print("=" * 80)

    db_url = _get_database_url() if not args.dry_run else ""
    if db_url:
        print(f"\n数据库: {db_url.split('@')[-1] if '@' in db_url else '(unknown)'}")
    else:
        print("\n[DRY-RUN] 跳过 DB 连接")
    conn = psycopg2.connect(
        db_url,
        connect_timeout=10,
        keepalives=1,
        keepalives_idle=30,
        keepalives_interval=10,
        keepalives_count=5,
    ) if not args.dry_run else None

    try:
        if not args.taxonomy_only:
            print("\n[1/2] 导入 bad_cases...")
            import_bad_cases(conn, dry_run=args.dry_run)

        if not args.bad_cases_only:
            print("\n[2/2] 导入 category_aspect_taxonomy...")
            import_taxonomy(conn, dry_run=args.dry_run)
    finally:
        if conn is not None:
            conn.close()

    print("\n" + "=" * 80)
    print("✅ 完成")
    return 0


if __name__ == "__main__":
    sys.exit(main())
