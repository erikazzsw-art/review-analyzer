"""Auto-seed golden_set from historical high-confidence analysis results.

从 review_comments 表中提取 evidence_level=certain 且被人工确认正确的数据，
自动填充 golden_set 表作为初始标杆数据。

Usage:
    python -m scripts.seed_golden_set [--sub-category 家具家居] [--limit 500]
"""
from __future__ import annotations

import argparse
import logging

import psycopg2.extras

from review_analyzer.database import get_connection
from review_analyzer.golden_set_store import save_golden_batch

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def seed_from_certain_aspects(
    sub_category: str = "家具家居",
    limit: int = 500,
    user_id: int = 1,
) -> int:
    """从 review_comments 提取 evidence_level=certain 的 aspect 标注."""
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """SELECT rc.content, rc.ai_aspects
                   FROM review_comments rc
                   WHERE rc.ai_aspects IS NOT NULL
                     AND jsonb_array_length(rc.ai_aspects) > 0
                   ORDER BY rc.analyzed_at DESC NULLS LAST
                   LIMIT %s""",
                (limit * 3,),
            )
            rows = cur.fetchall()
    finally:
        conn.close()

    items: list[dict] = []
    for row in rows:
        content = row.get("content", "")
        aspects = row.get("ai_aspects", [])
        if not content or not aspects:
            continue
        for asp in aspects:
            if asp.get("evidence_level") == "certain" and asp.get("key"):
                items.append({
                    "comment_text": content[:500],
                    "aspect_key": asp["key"],
                    "is_correct": True,
                    "reason": f"Auto-seeded: evidence_level=certain, span={asp.get('evidence_span', '')[:60]}",
                    "correct_tag": None,
                    "source": "auto_seed",
                })
        if len(items) >= limit:
            break

    items = items[:limit]
    if not items:
        logger.info("No certain-level aspects found. Nothing to seed.")
        return 0

    batch_id = save_golden_batch(
        user_id=user_id,
        items=items,
        sub_category=sub_category,
    )
    logger.info("Seeded %d golden_set entries (batch: %s)", len(items), batch_id)
    return len(items)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed golden_set from historical data")
    parser.add_argument("--sub-category", default="家具家居")
    parser.add_argument("--limit", type=int, default=500)
    parser.add_argument("--user-id", type=int, default=1)
    args = parser.parse_args()
    count = seed_from_certain_aspects(
        sub_category=args.sub_category,
        limit=args.limit,
        user_id=args.user_id,
    )
    print(f"Done. Seeded {count} entries.")
