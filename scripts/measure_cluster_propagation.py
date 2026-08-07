#!/usr/bin/env python3
"""只读统计脚本：量出 cluster 传播在生产数据中的占比。

背景：clustering.py 的 propagate_cluster_results() 会把簇代表的 aspects/pain_points/
highlights 整份传给同簇成员，并标记 cluster_propagated=True。而 _is_frontstage_countable_occurrence
会把所有 cluster_propagated 的 occurrence 从 TOP10 剔除。如果传播占比过高，TOP10 会被掏空。

严格只读 —— 只 SELECT，不 INSERT/UPDATE/DELETE，不调 LLM，不写文件。
输出纯文本表格到 stdout。

用法:
  cd /opt/clueai/deploy
  docker compose exec api python scripts/measure_cluster_propagation.py
"""

import os
import sys
from pathlib import Path

# ── Bootstrap ──────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "backend_api"))

# 加载 .env（本地用项目根 .env；ECS 容器内 DATABASE_URL 已在环境中）
try:
    from dotenv import load_dotenv

    env_path = PROJECT_ROOT / ".env"
    if env_path.exists():
        load_dotenv(env_path)
except ImportError:
    pass  # ECS 容器可能没有 dotenv，直接用 os.environ

import psycopg2
from psycopg2.extras import RealDictCursor

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    print("ERROR: DATABASE_URL not set in environment")
    sys.exit(1)

# ── 主逻辑 ──────────────────────────────────────────────────────────────────


def main() -> None:
    conn = psycopg2.connect(DATABASE_URL)
    conn.set_session(readonly=True)

    print()
    print("=" * 92)
    print("  Cluster 传播污染统计")
    print("  目标数据库: {}".format(DATABASE_URL.split("@")[-1] if "@" in DATABASE_URL else "(已隐藏)"))
    print("=" * 92)

    # ── 维度 1: 全库传播占比 ──────────────────────────────────────────────
    print("\n## 维度 1: 全库 cluster_propagated 占比\n")

    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("""
        SELECT
            COUNT(*) AS total_with_aspects,
            COUNT(*) FILTER (
                WHERE aspects_json->>'cluster_propagated' = 'true'
            ) AS propagated,
            COUNT(*) FILTER (
                WHERE aspects_json->>'cluster_propagated' = 'false'
                   OR aspects_json->>'cluster_propagated' IS NULL
            ) AS direct_llm
        FROM comments
        WHERE aspects_json IS NOT NULL
    """)
    row = cur.fetchone()
    total = row["total_with_aspects"]
    prop = row["propagated"]
    direct = row["direct_llm"]
    pct = round(100 * prop / total, 1) if total else 0
    cur.close()

    print(f"  总评论数（含 aspects_json）:        {total:>10,}")
    print(f"  其中 cluster_propagated = true:      {prop:>10,}  ({pct}%)")
    print(f"  其中 直接 LLM 分析（非传播）:          {direct:>10,}  ({round(100 * direct / total, 1) if total else 0}%)")

    if pct >= 50:
        print(f"\n  ⚠️  传播占比 {pct}% — 超过半数评论的前台计数会被门禁剔除，TOP10 有掏空风险。")
    elif pct >= 30:
        print(f"\n  ⚠️  传播占比 {pct}% — 接近三分之一评论受影响，特定类目可能更严重。")
    else:
        print(f"\n  传播占比 {pct}% — 在可接受范围内。")

    # ── 维度 2: 按 sub_category 分组 TOP 15 ────────────────────────────────
    print("\n## 维度 2: 按 sub_category 分组传播占比（按占比降序 TOP 15）\n")

    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("""
        SELECT
            aspects_json->>'sub_category' AS sub_category,
            COUNT(*) AS total,
            COUNT(*) FILTER (
                WHERE aspects_json->>'cluster_propagated' = 'true'
            ) AS propagated,
            ROUND(
                100.0 * COUNT(*) FILTER (
                    WHERE aspects_json->>'cluster_propagated' = 'true'
                ) / NULLIF(COUNT(*), 0), 1
            ) AS propagated_pct
        FROM comments
        WHERE aspects_json IS NOT NULL
        GROUP BY aspects_json->>'sub_category'
        ORDER BY propagated_pct DESC
        LIMIT 15
    """)
    rows = cur.fetchall()
    cur.close()

    if rows:
        print(f"  {'sub_category':<38s} {'total':>8s} {'propagated':>12s} {'占比':>8s}")
        print(f"  {'-' * 38} {'-' * 8} {'-' * 12} {'-' * 8}")
        for r in rows:
            sc = r["sub_category"] or "(null)"
            t = r["total"]
            pp = r["propagated"]
            ppct = r["propagated_pct"]
            # 样本量不足时标注
            flag = " ⚠️ 样本<30" if t < 30 else ""
            print(f"  {sc:<38s} {t:>8,} {pp:>12,} {ppct:>7.1f}%{flag}")
    else:
        print("  (无数据)")

    # ── 维度 3: evidence_span 交叉验证 ─────────────────────────────────────
    print("\n## 维度 3: evidence_span 交叉验证（传播污染实证度量）\n")
    print("  展开 aspects_json.aspects[] 数组，检查每条 evidence_span 是否出现在")
    print("  该评论自己的 content 文本中。匹配规则与 _locate_evidence_span() 一致：")
    print("  先大小写敏感匹配，再大小写不敏感匹配。\n")

    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("""
        WITH expanded AS (
            SELECT
                c.id,
                c.content,
                c.aspects_json->>'cluster_propagated' AS is_propagated,
                a->>'evidence_span' AS evidence_span,
                a->>'key' AS aspect_key
            FROM comments c
            CROSS JOIN LATERAL jsonb_array_elements(
                CASE
                    WHEN jsonb_typeof(c.aspects_json->'aspects') = 'array'
                    THEN c.aspects_json->'aspects'
                    ELSE '[]'::jsonb
                END
            ) AS a
            WHERE c.aspects_json IS NOT NULL
              AND c.content IS NOT NULL
              AND a->>'evidence_span' IS NOT NULL
              AND length(trim(a->>'evidence_span')) > 0
        )
        SELECT
            is_propagated,
            COUNT(*) AS total_spans,
            COUNT(*) FILTER (
                WHERE position(evidence_span IN content) > 0
                   OR position(lower(evidence_span) IN lower(content)) > 0
            ) AS found_in_content,
            COUNT(*) FILTER (
                WHERE position(evidence_span IN content) = 0
                  AND position(lower(evidence_span) IN lower(content)) = 0
            ) AS not_found_in_content
        FROM expanded
        GROUP BY is_propagated
        ORDER BY is_propagated DESC NULLS LAST
    """)
    rows = cur.fetchall()
    cur.close()

    if rows:
        print(f"  {'cluster_propagated':<20s} {'total_spans':>12s} {'found_in_content':>18s} {'NOT_found':>12s} {'污染率':>8s}")
        print(f"  {'-' * 20} {'-' * 12} {'-' * 18} {'-' * 12} {'-' * 8}")
        for r in rows:
            is_prop = str(r["is_propagated"])
            ts = r["total_spans"]
            found = r["found_in_content"]
            not_found = r["not_found_in_content"]
            poll = round(100 * not_found / ts, 1) if ts else 0
            print(f"  {is_prop:<20s} {ts:>12,} {found:>18,} {not_found:>12,} {poll:>7.1f}%")
    else:
        print("  (无数据)")

    # ── 维度 4: 按 sub_category 分的传播 + 污染 ────────────────────────────
    print("\n## 维度 4: 按 sub_category 分的 evidence_span 污染率（按污染率降序 TOP 15）\n")

    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("""
        WITH expanded AS (
            SELECT
                c.id,
                c.content,
                c.aspects_json->>'sub_category' AS sub_category,
                c.aspects_json->>'cluster_propagated' AS is_propagated,
                a->>'evidence_span' AS evidence_span
            FROM comments c
            CROSS JOIN LATERAL jsonb_array_elements(
                CASE
                    WHEN jsonb_typeof(c.aspects_json->'aspects') = 'array'
                    THEN c.aspects_json->'aspects'
                    ELSE '[]'::jsonb
                END
            ) AS a
            WHERE c.aspects_json IS NOT NULL
              AND c.content IS NOT NULL
              AND a->>'evidence_span' IS NOT NULL
              AND length(trim(a->>'evidence_span')) > 0
        )
        SELECT
            sub_category,
            COUNT(*) AS total_spans,
            COUNT(*) FILTER (WHERE is_propagated = 'true') AS propagated_spans,
            COUNT(*) FILTER (
                WHERE position(evidence_span IN content) = 0
                  AND position(lower(evidence_span) IN lower(content)) = 0
            ) AS pollution_spans,
            ROUND(
                100.0 * COUNT(*) FILTER (
                    WHERE position(evidence_span IN content) = 0
                      AND position(lower(evidence_span) IN lower(content)) = 0
                ) / NULLIF(COUNT(*), 0), 1
            ) AS pollution_pct
        FROM expanded
        WHERE sub_category IS NOT NULL
        GROUP BY sub_category
        ORDER BY pollution_pct DESC
        LIMIT 15
    """)
    rows = cur.fetchall()
    cur.close()

    if rows:
        print(f"  {'sub_category':<38s} {'total_spans':>12s} {'propagated':>12s} {'pollution':>10s} {'污染率':>8s}")
        print(f"  {'-' * 38} {'-' * 12} {'-' * 12} {'-' * 10} {'-' * 8}")
        for r in rows:
            sc = r["sub_category"] or "(null)"
            ts = r["total_spans"]
            ps = r["propagated_spans"]
            pos = r["pollution_spans"]
            pop = r["pollution_pct"]
            flag = " ⚠️ 样本<30" if ts < 30 else ""
            print(f"  {sc:<38s} {ts:>12,} {ps:>12,} {pos:>10,} {pop:>7.1f}%{flag}")
    else:
        print("  (无数据)")

    # ── 收尾 ───────────────────────────────────────────────────────────────
    conn.close()
    print()
    print("=" * 92)
    print("  统计完成。（只读，未修改任何数据）")
    print("=" * 92)
    print()


if __name__ == "__main__":
    main()
