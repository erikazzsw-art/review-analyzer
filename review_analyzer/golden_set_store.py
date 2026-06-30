"""Golden Set Store — 标杆数据的持久化层."""
from __future__ import annotations

import logging
import uuid

import psycopg2.extras

from review_analyzer.database import get_connection

logger = logging.getLogger(__name__)


def save_golden_batch(
    *,
    user_id: int,
    items: list[dict],
    sub_category: str = "家具家居",
) -> str:
    """批量写入 golden_set 记录，返回 batch_id."""
    batch_id = f"batch_{uuid.uuid4().hex[:12]}"
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            psycopg2.extras.execute_values(
                cur,
                """INSERT INTO golden_set
                   (user_id, comment_text, aspect_key, is_correct, reason, correct_tag, sub_category, source, batch_id)
                   VALUES %s""",
                [
                    (
                        user_id,
                        item["comment_text"],
                        item["aspect_key"],
                        item["is_correct"],
                        item.get("reason"),
                        item.get("correct_tag"),
                        sub_category,
                        item.get("source", "manual"),
                        batch_id,
                    )
                    for item in items
                ],
                template="(%s, %s, %s, %s, %s, %s, %s, %s, %s)",
            )
            conn.commit()
        return batch_id
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def get_golden_entries(
    sub_category: str | None = None,
    aspect_key: str | None = None,
    *,
    limit: int = 200,
    offset: int = 0,
) -> list[dict]:
    """获取 golden_set 记录列表."""
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            conditions = []
            params: list = []
            if sub_category:
                conditions.append("sub_category = %s")
                params.append(sub_category)
            if aspect_key:
                conditions.append("aspect_key = %s")
                params.append(aspect_key)
            where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
            cur.execute(
                f"""SELECT id, comment_text, aspect_key, is_correct, reason,
                           correct_tag, sub_category, source, use_as_fewshot,
                           batch_id, created_at
                   FROM golden_set {where}
                   ORDER BY created_at DESC
                   LIMIT %s OFFSET %s""",
                params + [limit, offset],
            )
            return [dict(row) for row in cur.fetchall()]
    finally:
        conn.close()


def get_accuracy_stats(sub_category: str | None = None) -> list[dict]:
    """按 aspect_key 统计准确率."""
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            condition = "WHERE sub_category = %s" if sub_category else ""
            params = [sub_category] if sub_category else []
            cur.execute(
                f"""SELECT
                       aspect_key,
                       COUNT(*) AS total,
                       COUNT(*) FILTER (WHERE is_correct) AS correct_count,
                       COUNT(*) FILTER (WHERE NOT is_correct) AS incorrect_count,
                       ROUND(
                           COUNT(*) FILTER (WHERE is_correct)::numeric / NULLIF(COUNT(*), 0) * 100,
                           1
                       ) AS accuracy_pct
                   FROM golden_set {condition}
                   GROUP BY aspect_key
                   ORDER BY accuracy_pct ASC NULLS LAST""",
                params,
            )
            return [dict(row) for row in cur.fetchall()]
    finally:
        conn.close()


def get_fewshot_examples(sub_category: str, *, limit: int = 40) -> list[dict]:
    """获取标记为 few-shot 的典型示例."""
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """SELECT aspect_key, comment_text, is_correct, correct_tag, reason
                   FROM golden_set
                   WHERE sub_category = %s AND use_as_fewshot = TRUE
                   ORDER BY aspect_key, is_correct DESC
                   LIMIT %s""",
                (sub_category, limit),
            )
            return [dict(row) for row in cur.fetchall()]
    finally:
        conn.close()


def toggle_fewshot(entry_id: int, *, use_as_fewshot: bool) -> bool:
    """切换某条记录的 few-shot 状态."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE golden_set SET use_as_fewshot = %s WHERE id = %s",
                (use_as_fewshot, entry_id),
            )
            conn.commit()
            return cur.rowcount > 0
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def get_total_count(sub_category: str | None = None) -> int:
    """获取 golden_set 总条目数."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            if sub_category:
                cur.execute(
                    "SELECT COUNT(*) FROM golden_set WHERE sub_category = %s",
                    (sub_category,),
                )
            else:
                cur.execute("SELECT COUNT(*) FROM golden_set")
            return cur.fetchone()[0]
    finally:
        conn.close()
