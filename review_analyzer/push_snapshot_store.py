"""推送快照 + 升级状态 数据访问层"""
from __future__ import annotations

import json
from typing import Any

import psycopg2.extras

from review_analyzer.database import get_connection


def create_push_snapshot(user_id: int, data: dict[str, Any]) -> int:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO push_snapshots
                   (user_id, product_id, snapshot_type, period_start, period_end,
                    top_issues, top_highlights, summary_stats)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                   RETURNING id""",
                (
                    user_id,
                    data.get("product_id"),
                    data.get("snapshot_type", "batch"),
                    data.get("period_start"),
                    data.get("period_end"),
                    json.dumps(data.get("top_issues", []), ensure_ascii=False),
                    json.dumps(data.get("top_highlights", []), ensure_ascii=False),
                    json.dumps(data.get("summary_stats", {}), ensure_ascii=False),
                ),
            )
            snapshot_id = int(cur.fetchone()[0])
            conn.commit()
            return snapshot_id
    finally:
        conn.close()


def get_recent_snapshots(
    user_id: int,
    product_id: int | None,
    limit: int = 3,
) -> list[dict[str, Any]]:
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            if product_id is not None:
                cur.execute(
                    """SELECT * FROM push_snapshots
                       WHERE user_id = %s AND product_id = %s
                       ORDER BY created_at DESC LIMIT %s""",
                    (user_id, product_id, limit),
                )
            else:
                cur.execute(
                    """SELECT * FROM push_snapshots
                       WHERE user_id = %s AND product_id IS NULL
                       ORDER BY created_at DESC LIMIT %s""",
                    (user_id, limit),
                )
            return [dict(row) for row in cur.fetchall()]
    finally:
        conn.close()


def get_escalation_states(
    user_id: int,
    product_id: int | None,
) -> list[dict[str, Any]]:
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            if product_id is not None:
                cur.execute(
                    """SELECT * FROM issue_escalation_state
                       WHERE user_id = %s AND product_id = %s""",
                    (user_id, product_id),
                )
            else:
                cur.execute(
                    """SELECT * FROM issue_escalation_state
                       WHERE user_id = %s AND product_id IS NULL""",
                    (user_id,),
                )
            return [dict(row) for row in cur.fetchall()]
    finally:
        conn.close()


def upsert_escalation_state(
    user_id: int,
    product_id: int | None,
    tag_name: str,
    dept: str,
    consecutive_count: int,
    snapshot_id: int,
) -> None:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO issue_escalation_state
                   (user_id, product_id, tag_name, dept, consecutive_count,
                    last_snapshot_id, updated_at)
                   VALUES (%s, %s, %s, %s, %s, %s, NOW())
                   ON CONFLICT (user_id, product_id, tag_name)
                   DO UPDATE SET
                       dept = EXCLUDED.dept,
                       consecutive_count = EXCLUDED.consecutive_count,
                       last_snapshot_id = EXCLUDED.last_snapshot_id,
                       updated_at = NOW()""",
                (user_id, product_id, tag_name, dept, consecutive_count, snapshot_id),
            )
            conn.commit()
    finally:
        conn.close()


def reset_escalation_count(
    user_id: int,
    product_id: int | None,
    tag_name: str,
) -> None:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            if product_id is not None:
                cur.execute(
                    """UPDATE issue_escalation_state
                       SET consecutive_count = 0, updated_at = NOW()
                       WHERE user_id = %s AND product_id = %s AND tag_name = %s""",
                    (user_id, product_id, tag_name),
                )
            else:
                cur.execute(
                    """UPDATE issue_escalation_state
                       SET consecutive_count = 0, updated_at = NOW()
                       WHERE user_id = %s AND product_id IS NULL AND tag_name = %s""",
                    (user_id, tag_name),
                )
            conn.commit()
    finally:
        conn.close()


def mark_escalated(
    user_id: int,
    product_id: int | None,
    tag_name: str,
    action_item_id: int,
) -> None:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            if product_id is not None:
                cur.execute(
                    """UPDATE issue_escalation_state
                       SET escalated_at = NOW(), action_item_id = %s, updated_at = NOW()
                       WHERE user_id = %s AND product_id = %s AND tag_name = %s""",
                    (action_item_id, user_id, product_id, tag_name),
                )
            else:
                cur.execute(
                    """UPDATE issue_escalation_state
                       SET escalated_at = NOW(), action_item_id = %s, updated_at = NOW()
                       WHERE user_id = %s AND product_id IS NULL AND tag_name = %s""",
                    (action_item_id, user_id, tag_name),
                )
            conn.commit()
    finally:
        conn.close()
