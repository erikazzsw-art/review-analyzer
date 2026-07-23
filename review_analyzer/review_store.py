from __future__ import annotations

from typing import Any

import psycopg2
import psycopg2.extras

from review_analyzer.database import get_connection

REVIEW_TRACKER_STATUSES = ["pending", "improved", "not_improved", "follow_up", "done"]
REVIEW_TRACKER_STATUS_LABELS = {
    "pending": "待复盘",
    "improved": "已改善",
    "not_improved": "未改善",
    "follow_up": "继续跟进",
    "done": "已完结",
}

ACTIVE_TRACKER_STATUSES = ("pending", "follow_up")


def create_review_tracker(user_id: int, data: dict[str, Any]) -> int:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO review_trackers
                   (user_id, action_item_id, product_id, variant_id, tracker_title, tag_name,
                    aspect_key, canonical_issue_key, specific_issue, baseline_pct,
                    improvement_action, effective_batch, review_scope, current_pct,
                    result_status, conclusion)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                   RETURNING id""",
                (
                    user_id,
                    data.get("action_item_id"),
                    data.get("product_id"),
                    data.get("variant_id"),
                    data.get("tracker_title"),
                    data.get("tag_name"),
                    data.get("aspect_key"),
                    data.get("canonical_issue_key"),
                    data.get("specific_issue") or data.get("tag_name"),
                    data.get("baseline_pct"),
                    data.get("improvement_action"),
                    data.get("effective_batch"),
                    data.get("review_scope"),
                    data.get("current_pct"),
                    data.get("result_status", "pending"),
                    data.get("conclusion"),
                ),
            )
            tracker_id = int(cur.fetchone()[0])
            conn.commit()
            return tracker_id
    finally:
        conn.close()



def get_review_trackers(
    user_id: int,
    status: str | None = None,
    product_id: int | None = None,
) -> list[dict[str, Any]]:
    query = """
        SELECT
            rt.*,
            ai.title AS action_title,
            ai.source_product_id,
            ai.source_version,
            ai.expected_review_at,
            p.parent_product_id,
            p.name AS product_name,
            pv.variant_sku,
            pv.child_asin
        FROM review_trackers rt
        LEFT JOIN action_items ai ON rt.action_item_id = ai.id
        LEFT JOIN products p ON rt.product_id = p.id
        LEFT JOIN product_variants pv ON rt.variant_id = pv.id
        WHERE rt.user_id = %s
    """
    params: list[Any] = [user_id]
    if status:
        query += " AND rt.result_status = %s"
        params.append(status)
    if product_id:
        query += " AND rt.product_id = %s"
        params.append(product_id)
    query += " ORDER BY rt.created_at DESC, rt.id DESC"

    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(query, params)
            return [dict(row) for row in cur.fetchall()]
    except psycopg2.errors.UndefinedTable:
        conn.rollback()
        return []
    finally:
        conn.close()


def update_review_tracker_result(user_id: int, tracker_id: int, data: dict[str, Any]) -> None:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            result_status = data.get("result_status")
            closed_at_sql = "NOW()" if result_status == "done" else "NULL"
            cur.execute(
                f"""UPDATE review_trackers
                    SET review_scope = %s,
                        current_pct = %s,
                        result_status = %s,
                        conclusion = %s,
                        closed_at = {closed_at_sql}
                    WHERE id = %s AND user_id = %s""",
                (
                    data.get("review_scope"),
                    data.get("current_pct"),
                    result_status,
                    data.get("conclusion"),
                    tracker_id,
                    user_id,
                ),
            )
            conn.commit()
    finally:
        conn.close()


def get_review_tracker_by_action_id(user_id: int, action_item_id: int) -> dict[str, Any] | None:
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                "SELECT * FROM review_trackers WHERE user_id = %s AND action_item_id = %s ORDER BY id DESC LIMIT 1",
                (user_id, action_item_id),
            )
            row = cur.fetchone()
            return dict(row) if row else None
    except psycopg2.errors.UndefinedTable:
        conn.rollback()
        return None
    finally:
        conn.close()


def get_matching_review_trackers(
    user_id: int,
    product_id: int | None,
    tag_names: list[str],
) -> list[dict[str, Any]]:
    if not product_id or not tag_names:
        return []

    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """SELECT *
                   FROM review_trackers
                   WHERE user_id = %s
                     AND product_id = %s
                     AND tag_name = ANY(%s)
                     AND result_status = ANY(%s)
                   ORDER BY created_at DESC, id DESC""",
                (user_id, product_id, tag_names, list(ACTIVE_TRACKER_STATUSES)),
            )
            return [dict(row) for row in cur.fetchall()]
    except psycopg2.errors.UndefinedTable:
        conn.rollback()
        return []
    finally:
        conn.close()
