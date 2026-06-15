from __future__ import annotations

from typing import Any

import psycopg2.extras

from review_analyzer.database import get_connection

FEEDBACK_TYPES = ["bug", "feature", "general"]
FEEDBACK_MOODS = ["frustrated", "idea", "love"]
FEEDBACK_STATUSES = ["new", "reviewed", "resolved"]


def create_feedback(user_id: int, data: dict[str, Any]) -> int:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO user_feedback
                   (user_id, feedback_type, mood, message, page_path,
                    user_agent, metadata, status)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, 'new')
                   RETURNING id""",
                (
                    user_id,
                    data["feedback_type"],
                    data["mood"],
                    data.get("message"),
                    data["page_path"],
                    data.get("user_agent"),
                    psycopg2.extras.Json(data.get("metadata") or {}),
                ),
            )
            feedback_id = int(cur.fetchone()[0])
            conn.commit()
            return feedback_id
    finally:
        conn.close()


def get_feedback_list(
    user_id: int | None = None,
    status: str | None = None,
    limit: int = 50,
) -> list[dict[str, Any]]:
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            conditions = []
            params: list[Any] = []
            if user_id is not None:
                conditions.append("user_id = %s")
                params.append(user_id)
            if status is not None:
                conditions.append("status = %s")
                params.append(status)
            where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
            cur.execute(
                f"SELECT * FROM user_feedback {where} ORDER BY created_at DESC LIMIT %s",
                [*params, limit],
            )
            return [dict(row) for row in cur.fetchall()]
    finally:
        conn.close()
