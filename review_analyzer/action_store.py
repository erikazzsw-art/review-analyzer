from __future__ import annotations

from typing import Any

import psycopg2
import psycopg2.extras

from review_analyzer.database import get_connection

ACTION_STATUSES = ["todo", "in_progress", "pending_review", "done"]
ACTION_STATUS_LABELS = {
    "todo": "待处理",
    "in_progress": "处理中",
    "pending_review": "待复盘",
    "done": "已完结",
}


def create_action_item(user_id: int, data: dict[str, Any]) -> int:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO action_items
                   (user_id, product_id, variant_id, session_id, source_product_id, source_version,
                    source_batch_label, title, tag_name, tag_type, current_pct, owner_role,
                    suggested_action, expected_effect_batch, expected_review_at, status)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                   RETURNING id""",
                (
                    user_id,
                    data.get("product_id"),
                    data.get("variant_id"),
                    data.get("session_id"),
                    data.get("source_product_id"),
                    data.get("source_version"),
                    data.get("source_batch_label"),
                    data.get("title"),
                    data.get("tag_name"),
                    data.get("tag_type", "issue"),
                    data.get("current_pct"),
                    data.get("owner_role"),
                    data.get("suggested_action"),
                    data.get("expected_effect_batch"),
                    data.get("expected_review_at"),
                    data.get("status", "todo"),
                ),
            )
            action_id = int(cur.fetchone()[0])
            conn.commit()
            return action_id
    finally:
        conn.close()



def get_action_items(
    user_id: int,
    status: str | None = None,
    owner_role: str | None = None,
) -> list[dict[str, Any]]:
    query = """
        SELECT
            ai.*,
            p.parent_product_id,
            p.name AS product_name,
            pv.variant_sku,
            pv.child_asin
        FROM action_items ai
        LEFT JOIN products p ON ai.product_id = p.id
        LEFT JOIN product_variants pv ON ai.variant_id = pv.id
        WHERE ai.user_id = %s
    """
    params: list[Any] = [user_id]
    if status:
        query += " AND ai.status = %s"
        params.append(status)
    if owner_role:
        query += " AND ai.owner_role = %s"
        params.append(owner_role)
    query += " ORDER BY ai.created_at DESC, ai.id DESC"

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


def update_action_status(user_id: int, action_id: int, status: str) -> None:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE action_items SET status = %s WHERE id = %s AND user_id = %s",
                (status, action_id, user_id),
            )
            conn.commit()
    finally:
        conn.close()


def get_action_item_by_id(user_id: int, action_id: int) -> dict[str, Any] | None:
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                "SELECT * FROM action_items WHERE id = %s AND user_id = %s",
                (action_id, user_id),
            )
            row = cur.fetchone()
            return dict(row) if row else None
    except psycopg2.errors.UndefinedTable:
        conn.rollback()
        return None
    finally:
        conn.close()
