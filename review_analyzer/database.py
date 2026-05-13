from __future__ import annotations

import psycopg2
import psycopg2.extras
import streamlit as st
from typing import Optional


def get_connection():
    """获取 Supabase PostgreSQL 连接"""
    db_url = st.secrets["database"]["url"]
    conn = psycopg2.connect(db_url)
    conn.autocommit = False
    return conn


def init_db() -> None:
    """在 Supabase 上表已通过 SQL 脚本创建，此函数仅做兼容保留。"""
    pass


# ============================================================
# Users CRUD
# ============================================================

def create_user(username: str, password_hash: str) -> int:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO users (username, password_hash) VALUES (%s, %s) RETURNING id",
                (username, password_hash),
            )
            user_id = cur.fetchone()[0]
            conn.commit()
            return user_id


def get_user_by_username(username: str) -> Optional[dict]:
    with get_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT * FROM users WHERE username = %s", (username,))
            row = cur.fetchone()
            return dict(row) if row else None


def get_user_by_id(user_id: int) -> Optional[dict]:
    with get_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT * FROM users WHERE id = %s", (user_id,))
            row = cur.fetchone()
            return dict(row) if row else None


def update_user_api_key(user_id: int, api_key_encrypted: str) -> None:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE users SET api_key_encrypted = %s WHERE id = %s",
                (api_key_encrypted, user_id),
            )
            conn.commit()


def delete_user(user_id: int) -> None:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM settings WHERE user_id = %s", (user_id,))
            cur.execute("DELETE FROM comments WHERE user_id = %s", (user_id,))
            cur.execute("DELETE FROM sessions WHERE user_id = %s", (user_id,))
            cur.execute("DELETE FROM users WHERE id = %s", (user_id,))
            conn.commit()


# ============================================================
# Comments CRUD
# ============================================================

_COMMENT_FIELDS = (
    "user_id, product_id, version, content, rating, date, "
    "reviewer, source, content_hash, sentiment, category, "
    "priority, reason, improvement, issue_tag, highlight_tag, "
    "is_processed, session_id"
)
_COMMENT_PLACEHOLDERS = ", ".join(["%s"] * 18)


def _comment_values(user_id: int, comment: dict) -> list:
    return [
        user_id,
        comment.get("product_id"),
        comment.get("version", "V1"),
        comment.get("content"),
        comment.get("rating"),
        comment.get("date"),
        comment.get("reviewer"),
        comment.get("source"),
        comment.get("content_hash"),
        comment.get("sentiment"),
        comment.get("category"),
        comment.get("priority"),
        comment.get("reason"),
        comment.get("improvement"),
        comment.get("issue_tag", ""),
        comment.get("highlight_tag", ""),
        comment.get("is_processed", 0),
        comment.get("session_id"),
    ]


def add_comment(user_id: int, comment: dict) -> int:
    values = _comment_values(user_id, comment)
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"INSERT INTO comments ({_COMMENT_FIELDS}) VALUES ({_COMMENT_PLACEHOLDERS}) RETURNING id",
                values,
            )
            comment_id = cur.fetchone()[0]
            conn.commit()
            return comment_id


def add_comments_batch(user_id: int, comments: list[dict]) -> int:
    rows = [_comment_values(user_id, c) for c in comments]
    with get_connection() as conn:
        with conn.cursor() as cur:
            psycopg2.extras.execute_batch(
                cur,
                f"INSERT INTO comments ({_COMMENT_FIELDS}) VALUES ({_COMMENT_PLACEHOLDERS})",
                rows,
            )
            conn.commit()
            return len(rows)


def get_comments(
    user_id: int,
    product_id: Optional[str] = None,
    session_id: Optional[int] = None,
    version: Optional[str] = None,
) -> list[dict]:
    query = "SELECT * FROM comments WHERE user_id = %s"
    params: list = [user_id]
    if product_id is not None:
        query += " AND product_id = %s"
        params.append(product_id)
    if session_id is not None:
        query += " AND session_id = %s"
        params.append(session_id)
    if version is not None:
        query += " AND version = %s"
        params.append(version)
    query += " ORDER BY id DESC"
    with get_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(query, params)
            return [dict(r) for r in cur.fetchall()]


def get_comment_by_id(user_id: int, comment_id: int) -> Optional[dict]:
    with get_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                "SELECT * FROM comments WHERE id = %s AND user_id = %s",
                (comment_id, user_id),
            )
            row = cur.fetchone()
            return dict(row) if row else None


def update_comment_analysis(user_id: int, comment_id: int, analysis: dict) -> None:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """UPDATE comments
                   SET sentiment = %s, category = %s, priority = %s, reason = %s,
                       improvement = %s, issue_tag = %s, highlight_tag = %s, is_processed = 1
                   WHERE id = %s AND user_id = %s""",
                (
                    analysis.get("sentiment"),
                    analysis.get("category"),
                    analysis.get("priority"),
                    analysis.get("reason"),
                    analysis.get("improvement"),
                    analysis.get("issue_tag", ""),
                    analysis.get("highlight_tag", ""),
                    comment_id,
                    user_id,
                ),
            )
            conn.commit()


def delete_comment(user_id: int, comment_id: int) -> None:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM comments WHERE id = %s AND user_id = %s",
                (comment_id, user_id),
            )
            conn.commit()


def delete_comments_by_session(user_id: int, session_id: int) -> None:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM comments WHERE session_id = %s AND user_id = %s",
                (session_id, user_id),
            )
            conn.commit()


def get_existing_hashes(user_id: int, product_id: str) -> set[str]:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT content_hash FROM comments WHERE user_id = %s AND product_id = %s AND content_hash IS NOT NULL",
                (user_id, product_id),
            )
            return {r[0] for r in cur.fetchall()}


def get_product_stats_deduped(user_id: int, product_id: str) -> dict:
    """按 content_hash 去重后统计产品级指标。"""
    sql = """
        SELECT
            COUNT(*) AS total_reviews,
            SUM(CASE WHEN sentiment = 'positive' THEN 1 ELSE 0 END) AS positive_count,
            SUM(CASE WHEN sentiment = 'negative' THEN 1 ELSE 0 END) AS negative_count,
            SUM(CASE WHEN sentiment = 'unrecognizable' THEN 1 ELSE 0 END) AS unrecognizable_count
        FROM (
            SELECT sentiment,
                   ROW_NUMBER() OVER (PARTITION BY content_hash ORDER BY id DESC) AS rn
            FROM comments
            WHERE user_id = %s AND product_id = %s AND content_hash IS NOT NULL
        ) sub
        WHERE rn = 1
    """
    with get_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, (user_id, product_id))
            row = cur.fetchone()
            return dict(row) if row else {"total_reviews": 0, "positive_count": 0, "negative_count": 0, "unrecognizable_count": 0}


def get_comments_deduped(user_id: int, product_id: str) -> list[dict]:
    """按 content_hash 去重，保留最新一条记录。"""
    sql = """
        SELECT * FROM (
            SELECT *,
                   ROW_NUMBER() OVER (PARTITION BY content_hash ORDER BY id DESC) AS rn
            FROM comments
            WHERE user_id = %s AND product_id = %s AND content_hash IS NOT NULL
        ) sub
        WHERE rn = 1
        ORDER BY id DESC
    """
    with get_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, (user_id, product_id))
            return [dict(r) for r in cur.fetchall()]


def get_unprocessed_comments(user_id: int, session_id: int) -> list[dict]:
    with get_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                "SELECT * FROM comments WHERE user_id = %s AND session_id = %s AND is_processed = 0",
                (user_id, session_id),
            )
            return [dict(r) for r in cur.fetchall()]


# ============================================================
# Sessions CRUD
# ============================================================

def create_session(user_id: int, session_data: dict) -> int:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO sessions
                   (user_id, product_id, version, auto_title, custom_title,
                    date_range_start, date_range_end, total_reviews,
                    positive_count, negative_count, category)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id""",
                (
                    user_id,
                    session_data.get("product_id"),
                    session_data.get("version", "V1"),
                    session_data.get("auto_title"),
                    session_data.get("custom_title"),
                    session_data.get("date_range_start"),
                    session_data.get("date_range_end"),
                    session_data.get("total_reviews", 0),
                    session_data.get("positive_count", 0),
                    session_data.get("negative_count", 0),
                    session_data.get("category"),
                ),
            )
            session_id = cur.fetchone()[0]
            conn.commit()
            return session_id


def get_sessions(user_id: int, product_id: Optional[str] = None) -> list[dict]:
    query = "SELECT * FROM sessions WHERE user_id = %s"
    params: list = [user_id]
    if product_id is not None:
        query += " AND product_id = %s"
        params.append(product_id)
    query += " ORDER BY created_at DESC"
    with get_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(query, params)
            return [dict(r) for r in cur.fetchall()]


def get_session_by_id(user_id: int, session_id: int) -> Optional[dict]:
    with get_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                "SELECT * FROM sessions WHERE id = %s AND user_id = %s",
                (session_id, user_id),
            )
            row = cur.fetchone()
            return dict(row) if row else None


def update_session_title(user_id: int, session_id: int, custom_title: str) -> None:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE sessions SET custom_title = %s WHERE id = %s AND user_id = %s",
                (custom_title, session_id, user_id),
            )
            conn.commit()


def update_session_stats(
    user_id: int,
    session_id: int,
    total_reviews: int,
    positive_count: int,
    negative_count: int,
) -> None:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """UPDATE sessions
                   SET total_reviews = %s, positive_count = %s, negative_count = %s
                   WHERE id = %s AND user_id = %s""",
                (total_reviews, positive_count, negative_count, session_id, user_id),
            )
            conn.commit()


def delete_session(user_id: int, session_id: int) -> None:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM comments WHERE session_id = %s AND user_id = %s",
                (session_id, user_id),
            )
            cur.execute(
                "DELETE FROM sessions WHERE id = %s AND user_id = %s",
                (session_id, user_id),
            )
            conn.commit()


def delete_product(user_id: int, product_id: str) -> None:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id FROM sessions WHERE user_id = %s AND product_id = %s",
                (user_id, product_id),
            )
            session_ids = [row[0] for row in cur.fetchall()]
            if session_ids:
                cur.execute(
                    "DELETE FROM comments WHERE user_id = %s AND session_id = ANY(%s)",
                    (user_id, session_ids),
                )
                cur.execute(
                    "DELETE FROM sessions WHERE user_id = %s AND id = ANY(%s)",
                    (user_id, session_ids),
                )
            conn.commit()


# ============================================================
# Settings CRUD
# ============================================================

def get_setting(user_id: int, key: str) -> Optional[str]:
    with get_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                "SELECT value FROM settings WHERE user_id = %s AND key = %s",
                (user_id, key),
            )
            row = cur.fetchone()
            return row["value"] if row else None


def set_setting(user_id: int, key: str, value: str) -> None:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO settings (user_id, key, value) VALUES (%s, %s, %s)
                   ON CONFLICT(user_id, key) DO UPDATE SET value = EXCLUDED.value""",
                (user_id, key, value),
            )
            conn.commit()


def get_all_settings(user_id: int) -> dict[str, str]:
    with get_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                "SELECT key, value FROM settings WHERE user_id = %s",
                (user_id,),
            )
            return {r["key"]: r["value"] for r in cur.fetchall()}


def delete_setting(user_id: int, key: str) -> None:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM settings WHERE user_id = %s AND key = %s",
                (user_id, key),
            )
            conn.commit()
