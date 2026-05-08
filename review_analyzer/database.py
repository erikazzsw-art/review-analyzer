import os
import sqlite3
from typing import Optional

DB_PATH = os.path.join(os.path.dirname(__file__), "data", "review_analyzer.db")


def _ensure_db_dir() -> None:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)


def get_connection() -> sqlite3.Connection:
    _ensure_db_dir()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db() -> None:
    with get_connection() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                api_key_encrypted TEXT,
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS comments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                product_id TEXT NOT NULL,
                version TEXT NOT NULL DEFAULT 'V1',
                content TEXT NOT NULL,
                rating INTEGER,
                date TEXT,
                reviewer TEXT,
                source TEXT,
                content_hash TEXT,
                sentiment TEXT,
                category TEXT,
                priority TEXT,
                reason TEXT,
                improvement TEXT,
                issue_tag TEXT DEFAULT '',
                highlight_tag TEXT DEFAULT '',
                is_processed INTEGER NOT NULL DEFAULT 0,
                session_id INTEGER,
                FOREIGN KEY (user_id) REFERENCES users(id),
                FOREIGN KEY (session_id) REFERENCES sessions(id)
            );

            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                product_id TEXT NOT NULL,
                version TEXT NOT NULL DEFAULT 'V1',
                auto_title TEXT,
                custom_title TEXT,
                date_range_start TEXT,
                date_range_end TEXT,
                total_reviews INTEGER DEFAULT 0,
                positive_count INTEGER DEFAULT 0,
                negative_count INTEGER DEFAULT 0,
                category TEXT,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                FOREIGN KEY (user_id) REFERENCES users(id)
            );

            CREATE TABLE IF NOT EXISTS settings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                key TEXT NOT NULL,
                value TEXT,
                FOREIGN KEY (user_id) REFERENCES users(id),
                UNIQUE(user_id, key)
            );

            CREATE INDEX IF NOT EXISTS idx_comments_user_id ON comments(user_id);
            CREATE INDEX IF NOT EXISTS idx_comments_product_id ON comments(user_id, product_id);
            CREATE INDEX IF NOT EXISTS idx_comments_session_id ON comments(session_id);
            CREATE INDEX IF NOT EXISTS idx_comments_hash ON comments(user_id, content_hash);
            CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON sessions(user_id);
            CREATE INDEX IF NOT EXISTS idx_settings_user_key ON settings(user_id, key);
        """)


# ============================================================
# Users CRUD
# ============================================================

def create_user(username: str, password_hash: str) -> int:
    with get_connection() as conn:
        cursor = conn.execute(
            "INSERT INTO users (username, password_hash) VALUES (?, ?)",
            (username, password_hash),
        )
        conn.commit()
        return cursor.lastrowid


def get_user_by_username(username: str) -> Optional[dict]:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM users WHERE username = ?",
            (username,),
        ).fetchone()
        return dict(row) if row else None


def get_user_by_id(user_id: int) -> Optional[dict]:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM users WHERE id = ?",
            (user_id,),
        ).fetchone()
        return dict(row) if row else None


def update_user_api_key(user_id: int, api_key_encrypted: str) -> None:
    with get_connection() as conn:
        conn.execute(
            "UPDATE users SET api_key_encrypted = ? WHERE id = ?",
            (api_key_encrypted, user_id),
        )
        conn.commit()


def delete_user(user_id: int) -> None:
    with get_connection() as conn:
        conn.execute("DELETE FROM settings WHERE user_id = ?", (user_id,))
        conn.execute("DELETE FROM comments WHERE user_id = ?", (user_id,))
        conn.execute("DELETE FROM sessions WHERE user_id = ?", (user_id,))
        conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
        conn.commit()


# ============================================================
# Comments CRUD
# ============================================================

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


_COMMENT_FIELDS = (
    "user_id, product_id, version, content, rating, date, "
    "reviewer, source, content_hash, sentiment, category, "
    "priority, reason, improvement, issue_tag, highlight_tag, "
    "is_processed, session_id"
)
_COMMENT_PLACEHOLDERS = ", ".join(["?"] * 18)


def add_comment(user_id: int, comment: dict) -> int:
    values = _comment_values(user_id, comment)
    with get_connection() as conn:
        cursor = conn.execute(
            f"INSERT INTO comments ({_COMMENT_FIELDS}) VALUES ({_COMMENT_PLACEHOLDERS})",
            values,
        )
        conn.commit()
        return cursor.lastrowid


def add_comments_batch(user_id: int, comments: list[dict]) -> int:
    rows = [_comment_values(user_id, c) for c in comments]
    with get_connection() as conn:
        conn.executemany(
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
    query = "SELECT * FROM comments WHERE user_id = ?"
    params: list = [user_id]
    if product_id is not None:
        query += " AND product_id = ?"
        params.append(product_id)
    if session_id is not None:
        query += " AND session_id = ?"
        params.append(session_id)
    if version is not None:
        query += " AND version = ?"
        params.append(version)
    query += " ORDER BY id DESC"
    with get_connection() as conn:
        rows = conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]


def get_comment_by_id(user_id: int, comment_id: int) -> Optional[dict]:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM comments WHERE id = ? AND user_id = ?",
            (comment_id, user_id),
        ).fetchone()
        return dict(row) if row else None


def update_comment_analysis(user_id: int, comment_id: int, analysis: dict) -> None:
    with get_connection() as conn:
        conn.execute(
            """UPDATE comments
               SET sentiment = ?, category = ?, priority = ?, reason = ?,
                   improvement = ?, issue_tag = ?, highlight_tag = ?, is_processed = 1
               WHERE id = ? AND user_id = ?""",
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
        conn.execute(
            "DELETE FROM comments WHERE id = ? AND user_id = ?",
            (comment_id, user_id),
        )
        conn.commit()


def delete_comments_by_session(user_id: int, session_id: int) -> None:
    with get_connection() as conn:
        conn.execute(
            "DELETE FROM comments WHERE session_id = ? AND user_id = ?",
            (session_id, user_id),
        )
        conn.commit()


def get_existing_hashes(user_id: int, product_id: str) -> set[str]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT content_hash FROM comments WHERE user_id = ? AND product_id = ? AND content_hash IS NOT NULL",
            (user_id, product_id),
        ).fetchall()
        return {r["content_hash"] for r in rows}


def get_product_stats_deduped(user_id: int, product_id: str) -> dict:
    """按 content_hash 去重后统计产品级指标。"""
    sql = """
        SELECT
            COUNT(*) AS total_reviews,
            SUM(CASE WHEN sentiment = 'positive' THEN 1 ELSE 0 END) AS positive_count,
            SUM(CASE WHEN sentiment = 'negative' THEN 1 ELSE 0 END) AS negative_count
        FROM (
            SELECT sentiment,
                   ROW_NUMBER() OVER (PARTITION BY content_hash ORDER BY id DESC) AS rn
            FROM comments
            WHERE user_id = ? AND product_id = ? AND content_hash IS NOT NULL
        )
        WHERE rn = 1
    """
    with get_connection() as conn:
        row = conn.execute(sql, (user_id, product_id)).fetchone()
        return dict(row) if row else {"total_reviews": 0, "positive_count": 0, "negative_count": 0}


def get_comments_deduped(user_id: int, product_id: str) -> list[dict]:
    """按 content_hash 去重，保留最新一条记录。"""
    sql = """
        SELECT * FROM (
            SELECT *,
                   ROW_NUMBER() OVER (PARTITION BY content_hash ORDER BY id DESC) AS rn
            FROM comments
            WHERE user_id = ? AND product_id = ? AND content_hash IS NOT NULL
        )
        WHERE rn = 1
        ORDER BY id DESC
    """
    with get_connection() as conn:
        rows = conn.execute(sql, (user_id, product_id)).fetchall()
        return [dict(r) for r in rows]


def get_unprocessed_comments(user_id: int, session_id: int) -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM comments WHERE user_id = ? AND session_id = ? AND is_processed = 0",
            (user_id, session_id),
        ).fetchall()
        return [dict(r) for r in rows]


# ============================================================
# Sessions CRUD
# ============================================================

def create_session(user_id: int, session_data: dict) -> int:
    with get_connection() as conn:
        cursor = conn.execute(
            """INSERT INTO sessions
               (user_id, product_id, version, auto_title, custom_title,
                date_range_start, date_range_end, total_reviews,
                positive_count, negative_count, category)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
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
        conn.commit()
        return cursor.lastrowid


def get_sessions(user_id: int, product_id: Optional[str] = None) -> list[dict]:
    query = "SELECT * FROM sessions WHERE user_id = ?"
    params: list = [user_id]
    if product_id is not None:
        query += " AND product_id = ?"
        params.append(product_id)
    query += " ORDER BY created_at DESC"
    with get_connection() as conn:
        rows = conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]


def get_session_by_id(user_id: int, session_id: int) -> Optional[dict]:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM sessions WHERE id = ? AND user_id = ?",
            (session_id, user_id),
        ).fetchone()
        return dict(row) if row else None


def update_session_title(user_id: int, session_id: int, custom_title: str) -> None:
    with get_connection() as conn:
        conn.execute(
            "UPDATE sessions SET custom_title = ? WHERE id = ? AND user_id = ?",
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
        conn.execute(
            """UPDATE sessions
               SET total_reviews = ?, positive_count = ?, negative_count = ?
               WHERE id = ? AND user_id = ?""",
            (total_reviews, positive_count, negative_count, session_id, user_id),
        )
        conn.commit()


def delete_session(user_id: int, session_id: int) -> None:
    with get_connection() as conn:
        conn.execute(
            "DELETE FROM comments WHERE session_id = ? AND user_id = ?",
            (session_id, user_id),
        )
        conn.execute(
            "DELETE FROM sessions WHERE id = ? AND user_id = ?",
            (session_id, user_id),
        )
        conn.commit()


def delete_product(user_id: int, product_id: str) -> None:
    with get_connection() as conn:
        session_ids = [
            row[0] for row in conn.execute(
                "SELECT id FROM sessions WHERE user_id = ? AND product_id = ?",
                (user_id, product_id),
            ).fetchall()
        ]
        if session_ids:
            placeholders = ",".join("?" * len(session_ids))
            conn.execute(
                f"DELETE FROM comments WHERE user_id = ? AND session_id IN ({placeholders})",
                [user_id] + session_ids,
            )
            conn.execute(
                f"DELETE FROM sessions WHERE user_id = ? AND id IN ({placeholders})",
                [user_id] + session_ids,
            )
        conn.commit()


# ============================================================
# Settings CRUD
# ============================================================

def get_setting(user_id: int, key: str) -> Optional[str]:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT value FROM settings WHERE user_id = ? AND key = ?",
            (user_id, key),
        ).fetchone()
        return row["value"] if row else None


def set_setting(user_id: int, key: str, value: str) -> None:
    with get_connection() as conn:
        conn.execute(
            """INSERT INTO settings (user_id, key, value) VALUES (?, ?, ?)
               ON CONFLICT(user_id, key) DO UPDATE SET value = excluded.value""",
            (user_id, key, value),
        )
        conn.commit()


def get_all_settings(user_id: int) -> dict[str, str]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT key, value FROM settings WHERE user_id = ?",
            (user_id,),
        ).fetchall()
        return {r["key"]: r["value"] for r in rows}


def delete_setting(user_id: int, key: str) -> None:
    with get_connection() as conn:
        conn.execute(
            "DELETE FROM settings WHERE user_id = ? AND key = ?",
            (user_id, key),
        )
        conn.commit()
