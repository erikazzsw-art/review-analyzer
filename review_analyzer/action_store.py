from __future__ import annotations

import re
from typing import Any

import psycopg2
import psycopg2.extras

from review_analyzer.database import get_connection

ACTION_STATUSES = ["todo", "in_progress", "pending_review", "done"]
ACTION_STATUS_LABELS = {
    "todo": "处理中",
    "in_progress": "处理中",
    "pending_review": "复盘中",
    "done": "已完结",
}

_ACTION_GROUP_KEY_SQL = """
    COALESCE(
        CASE WHEN ai.product_id IS NOT NULL THEN 'product:' || ai.product_id::text END,
        CASE WHEN NULLIF(ai.source_product_id, '') IS NOT NULL THEN 'source:' || ai.source_product_id END,
        CASE WHEN ai.session_id IS NOT NULL THEN 'session:' || ai.session_id::text END,
        'unbound'
    )
"""

_ACTION_SELECT_SQL = f"""
    SELECT
        ai.*,
        p.parent_product_id,
        p.name AS product_name,
        pv.variant_sku,
        pv.child_asin,
        (
            SELECT COALESCE(jsonb_agg(to_jsonb(source_review) ORDER BY source_review.id DESC), '[]'::jsonb)
            FROM (
                SELECT c.id, c.content, c.rating, c.date, c.issue_tag, c.highlight_tag
                FROM comments c
                WHERE c.user_id = ai.user_id
                  AND (ai.session_id IS NULL OR c.session_id = ai.session_id)
                  AND (NULLIF(ai.source_product_id, '') IS NULL OR c.product_id = ai.source_product_id)
                  AND (
                      NULLIF(ai.tag_name, '') IS NULL
                      OR POSITION(
                          LOWER(ai.tag_name)
                          IN LOWER(COALESCE(c.issue_tag, '') || ' ' || COALESCE(c.highlight_tag, ''))
                      ) > 0
                  )
                ORDER BY c.id DESC
                LIMIT 3
            ) source_review
        ) AS source_reviews_json,
        {_ACTION_GROUP_KEY_SQL} AS product_group_key,
        COALESCE(
            NULLIF(p.name, ''),
            NULLIF(p.parent_product_id, ''),
            NULLIF(ai.source_product_id, ''),
            CASE WHEN ai.session_id IS NOT NULL THEN 'Session #' || ai.session_id::text END,
            '未绑定产品'
        ) AS product_group_name,
        acpg.note AS product_note,
        acpg.sort_order AS product_sort_order
    FROM action_items ai
    LEFT JOIN products p ON ai.product_id = p.id
    LEFT JOIN product_variants pv ON ai.variant_id = pv.id
    LEFT JOIN action_center_product_groups acpg
        ON acpg.user_id = ai.user_id
       AND acpg.product_group_key = {_ACTION_GROUP_KEY_SQL}
"""


def normalize_action_status(status: str | None) -> str:
    if not status or status == "todo":
        return "in_progress"
    return status


def create_action_item(user_id: int, data: dict[str, Any]) -> int:
    suggestions = _coerce_suggestions(data.get("ai_suggestions") or data.get("ai_suggestions_json"))
    if not suggestions:
        suggestions = _split_suggestions(data.get("suggested_action"))

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO action_items
                   (user_id, product_id, variant_id, session_id, source_product_id, source_version,
                    source_batch_label, title, tag_name, tag_type, current_pct, owner_role,
                    suggested_action, expected_effect_batch, expected_review_at, status,
                    sort_order, ai_suggestions_json)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
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
                    normalize_action_status(data.get("status")),
                    data.get("sort_order"),
                    psycopg2.extras.Json(suggestions),
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
    query = _ACTION_SELECT_SQL + """
        WHERE ai.user_id = %s
          AND ai.removed_at IS NULL
    """
    params: list[Any] = [user_id]
    if status:
        query += " AND ai.status = %s"
        params.append(normalize_action_status(status))
    if owner_role:
        query += " AND ai.owner_role = %s"
        params.append(owner_role)
    query += """
        ORDER BY
            COALESCE(acpg.sort_order, 2147483647) ASC,
            product_group_name ASC,
            COALESCE(ai.sort_order, 2147483647) ASC,
            ai.created_at DESC,
            ai.id DESC
    """

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
                """UPDATE action_items
                   SET status = %s
                   WHERE id = %s AND user_id = %s AND removed_at IS NULL""",
                (normalize_action_status(status), action_id, user_id),
            )
            conn.commit()
    finally:
        conn.close()


def get_action_item_by_id(user_id: int, action_id: int) -> dict[str, Any] | None:
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                _ACTION_SELECT_SQL + """
                WHERE ai.id = %s
                  AND ai.user_id = %s
                  AND ai.removed_at IS NULL
                """,
                (action_id, user_id),
            )
            row = cur.fetchone()
            return dict(row) if row else None
    except psycopg2.errors.UndefinedTable:
        conn.rollback()
        return None
    finally:
        conn.close()


def update_action_suggestions(user_id: int, action_id: int, suggestions: list[str]) -> None:
    cleaned = _coerce_suggestions(suggestions)
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """UPDATE action_items
                   SET ai_suggestions_json = %s,
                       suggested_action = %s
                   WHERE id = %s AND user_id = %s AND removed_at IS NULL""",
                (
                    psycopg2.extras.Json(cleaned),
                    "\n".join(cleaned) if cleaned else None,
                    action_id,
                    user_id,
                ),
            )
            conn.commit()
    finally:
        conn.close()


def remove_action_item(user_id: int, action_id: int) -> bool:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """UPDATE action_items
                   SET removed_at = NOW()
                   WHERE id = %s AND user_id = %s AND removed_at IS NULL""",
                (action_id, user_id),
            )
            removed = cur.rowcount > 0
            conn.commit()
            return removed
    finally:
        conn.close()


def remove_product_group_actions(user_id: int, product_group_key: str) -> int:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                f"""UPDATE action_items ai
                    SET removed_at = NOW()
                    WHERE ai.user_id = %s
                      AND ai.removed_at IS NULL
                      AND {_ACTION_GROUP_KEY_SQL} = %s""",
                (user_id, product_group_key),
            )
            removed = cur.rowcount
            cur.execute(
                """DELETE FROM action_center_product_groups
                   WHERE user_id = %s AND product_group_key = %s""",
                (user_id, product_group_key),
            )
            conn.commit()
            return int(removed)
    finally:
        conn.close()


def update_product_group_note(user_id: int, product_group_key: str, note: str | None) -> dict[str, Any]:
    cleaned_note = note.strip() if note else None
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """INSERT INTO action_center_product_groups
                   (user_id, product_group_key, note)
                   VALUES (%s, %s, %s)
                   ON CONFLICT (user_id, product_group_key)
                   DO UPDATE SET note = EXCLUDED.note, updated_at = NOW()
                   RETURNING product_group_key, note, sort_order""",
                (user_id, product_group_key, cleaned_note),
            )
            row = cur.fetchone()
            conn.commit()
            return dict(row)
    finally:
        conn.close()


def reorder_product_groups(user_id: int, product_group_keys: list[str]) -> int:
    unique_keys = list(dict.fromkeys(key for key in product_group_keys if key))
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            for sort_order, product_group_key in enumerate(unique_keys):
                cur.execute(
                    """INSERT INTO action_center_product_groups
                       (user_id, product_group_key, sort_order)
                       VALUES (%s, %s, %s)
                       ON CONFLICT (user_id, product_group_key)
                       DO UPDATE SET sort_order = EXCLUDED.sort_order, updated_at = NOW()""",
                    (user_id, product_group_key, sort_order),
                )
            conn.commit()
            return len(unique_keys)
    finally:
        conn.close()


def reorder_actions(user_id: int, product_group_key: str, action_ids: list[int]) -> bool:
    unique_ids = list(dict.fromkeys(int(action_id) for action_id in action_ids if action_id))
    if len(unique_ids) != len(action_ids):
        return False

    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                f"""SELECT ai.id, {_ACTION_GROUP_KEY_SQL} AS product_group_key
                    FROM action_items ai
                    WHERE ai.user_id = %s
                      AND ai.removed_at IS NULL
                      AND ai.id = ANY(%s)""",
                (user_id, unique_ids),
            )
            rows = [dict(row) for row in cur.fetchall()]
            if len(rows) != len(unique_ids):
                conn.rollback()
                return False
            if any(row.get("product_group_key") != product_group_key for row in rows):
                conn.rollback()
                return False

            for sort_order, action_id in enumerate(unique_ids):
                cur.execute(
                    """UPDATE action_items
                       SET sort_order = %s
                       WHERE id = %s AND user_id = %s AND removed_at IS NULL""",
                    (sort_order, action_id, user_id),
                )
            conn.commit()
            return True
    finally:
        conn.close()


def _coerce_suggestions(value: Any) -> list[str]:
    if not value:
        return []
    if not isinstance(value, list):
        return _split_suggestions(value)
    return [_clean_suggestion(item) for item in value if _clean_suggestion(item)]


def _split_suggestions(value: Any) -> list[str]:
    raw = str(value or "").strip()
    if not raw:
        return []

    lines = [_clean_suggestion(line) for line in raw.replace("\r", "\n").split("\n")]
    lines = [line for line in lines if line]
    if len(lines) > 1:
        return lines

    numbered_parts = [_clean_suggestion(part) for part in re.split(r"(?=\d+[、.]\s*)", raw)]
    numbered_parts = [part for part in numbered_parts if part]
    if len(numbered_parts) > 1:
        return numbered_parts
    return [_clean_suggestion(raw)]


def _clean_suggestion(value: Any) -> str:
    text = str(value or "").strip()
    return re.sub(r"^\d+[、.]\s*", "", text).strip()
