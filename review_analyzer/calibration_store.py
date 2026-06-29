"""Label Calibration Store — 校准反馈的持久化层."""
from __future__ import annotations

import logging

import psycopg2.extras

from review_analyzer.database import get_connection

logger = logging.getLogger(__name__)


def save_calibration(
    *,
    user_id: str,
    comment_id: int | None,
    session_id: str | None,
    original_tag: str,
    correct_tag: str | None,
    note: str | None,
    sub_category: str = "家具家居",
) -> int:
    """存储一条校准记录，返回新记录 id."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO label_calibration
                   (user_id, comment_id, session_id, original_tag, correct_tag, note, sub_category)
                   VALUES (%s, %s, %s, %s, %s, %s, %s)
                   RETURNING id""",
                (user_id, comment_id, session_id, original_tag, correct_tag, note, sub_category),
            )
            row = cur.fetchone()
            conn.commit()
            return row[0]
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def get_calibrations(
    sub_category: str,
    *,
    status: str = "active",
    limit: int = 20,
) -> list[dict]:
    """获取指定 sub_category 的校准记录列表."""
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """SELECT id, original_tag, correct_tag, note, comment_id, session_id, created_at
                   FROM label_calibration
                   WHERE sub_category = %s AND status = %s
                   ORDER BY created_at DESC
                   LIMIT %s""",
                (sub_category, status, limit),
            )
            return [dict(row) for row in cur.fetchall()]
    finally:
        conn.close()


def revoke_calibration(calibration_id: int) -> bool:
    """撤销一条校准记录."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE label_calibration SET status = 'revoked' WHERE id = %s",
                (calibration_id,),
            )
            conn.commit()
            return cur.rowcount > 0
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
