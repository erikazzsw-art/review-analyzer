from __future__ import annotations

import ssl
from typing import Optional

import streamlit as st
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine


def _get_engine() -> Engine:
    """获取 SQLAlchemy 引擎（带连接池）"""
    if "db_engine" not in st.session_state:
        db_url = st.secrets["database"]["url"]
        # 统一为 SQLAlchemy 格式，使用 pg8000 驱动
        if db_url.startswith("postgres://"):
            db_url = db_url.replace("postgres://", "postgresql+pg8000://", 1)
        elif db_url.startswith("postgresql://") and "+pg8000" not in db_url:
            db_url = db_url.replace("postgresql://", "postgresql+pg8000://", 1)
        # Supabase 要求 SSL 连接
        ssl_ctx = ssl.create_default_context()
        ssl_ctx.check_hostname = False
        ssl_ctx.verify_mode = ssl.CERT_NONE
        st.session_state["db_engine"] = create_engine(
            db_url,
            pool_pre_ping=True,
            connect_args={"ssl_context": ssl_ctx},
        )
    return st.session_state["db_engine"]


def get_connection():
    """获取数据库连接（供外部兼容调用）"""
    return _get_engine().connect()


def init_db() -> None:
    """在 Supabase 上表已通过 SQL 脚本创建，此函数仅做兼容保留。"""
    pass


# ============================================================
# Users CRUD
# ============================================================

def create_user(username: str, password_hash: str) -> int:
    with _get_engine().connect() as conn:
        result = conn.execute(
            text("INSERT INTO users (username, password_hash) VALUES (:u, :p) RETURNING id"),
            {"u": username, "p": password_hash},
        )
        conn.commit()
        return result.fetchone()[0]


def get_user_by_username(username: str) -> Optional[dict]:
    with _get_engine().connect() as conn:
        result = conn.execute(
            text("SELECT * FROM users WHERE username = :u"),
            {"u": username},
        )
        row = result.mappings().fetchone()
        return dict(row) if row else None


def get_user_by_id(user_id: int) -> Optional[dict]:
    with _get_engine().connect() as conn:
        result = conn.execute(
            text("SELECT * FROM users WHERE id = :id"),
            {"id": user_id},
        )
        row = result.mappings().fetchone()
        return dict(row) if row else None


def update_user_api_key(user_id: int, api_key_encrypted: str) -> None:
    with _get_engine().connect() as conn:
        conn.execute(
            text("UPDATE users SET api_key_encrypted = :key WHERE id = :id"),
            {"key": api_key_encrypted, "id": user_id},
        )
        conn.commit()


def delete_user(user_id: int) -> None:
    with _get_engine().connect() as conn:
        conn.execute(text("DELETE FROM settings WHERE user_id = :id"), {"id": user_id})
        conn.execute(text("DELETE FROM comments WHERE user_id = :id"), {"id": user_id})
        conn.execute(text("DELETE FROM sessions WHERE user_id = :id"), {"id": user_id})
        conn.execute(text("DELETE FROM users WHERE id = :id"), {"id": user_id})
        conn.commit()


# ============================================================
# Comments CRUD
# ============================================================

def _comment_params(user_id: int, comment: dict) -> dict:
    return {
        "user_id": user_id,
        "product_id": comment.get("product_id"),
        "version": comment.get("version", "V1"),
        "content": comment.get("content"),
        "rating": comment.get("rating"),
        "date": comment.get("date"),
        "reviewer": comment.get("reviewer"),
        "source": comment.get("source"),
        "content_hash": comment.get("content_hash"),
        "sentiment": comment.get("sentiment"),
        "category": comment.get("category"),
        "priority": comment.get("priority"),
        "reason": comment.get("reason"),
        "improvement": comment.get("improvement"),
        "issue_tag": comment.get("issue_tag", ""),
        "highlight_tag": comment.get("highlight_tag", ""),
        "is_processed": comment.get("is_processed", 0),
        "session_id": comment.get("session_id"),
    }


_INSERT_COMMENT = text("""
    INSERT INTO comments
    (user_id, product_id, version, content, rating, date,
     reviewer, source, content_hash, sentiment, category,
     priority, reason, improvement, issue_tag, highlight_tag,
     is_processed, session_id)
    VALUES
    (:user_id, :product_id, :version, :content, :rating, :date,
     :reviewer, :source, :content_hash, :sentiment, :category,
     :priority, :reason, :improvement, :issue_tag, :highlight_tag,
     :is_processed, :session_id)
    RETURNING id
""")

_INSERT_COMMENT_NO_RETURN = text("""
    INSERT INTO comments
    (user_id, product_id, version, content, rating, date,
     reviewer, source, content_hash, sentiment, category,
     priority, reason, improvement, issue_tag, highlight_tag,
     is_processed, session_id)
    VALUES
    (:user_id, :product_id, :version, :content, :rating, :date,
     :reviewer, :source, :content_hash, :sentiment, :category,
     :priority, :reason, :improvement, :issue_tag, :highlight_tag,
     :is_processed, :session_id)
""")


def add_comment(user_id: int, comment: dict) -> int:
    params = _comment_params(user_id, comment)
    with _get_engine().connect() as conn:
        result = conn.execute(_INSERT_COMMENT, params)
        conn.commit()
        return result.fetchone()[0]


def add_comments_batch(user_id: int, comments: list[dict]) -> int:
    rows = [_comment_params(user_id, c) for c in comments]
    with _get_engine().connect() as conn:
        conn.execute(_INSERT_COMMENT_NO_RETURN, rows)
        conn.commit()
        return len(rows)


def get_comments(
    user_id: int,
    product_id: Optional[str] = None,
    session_id: Optional[int] = None,
    version: Optional[str] = None,
) -> list[dict]:
    query = "SELECT * FROM comments WHERE user_id = :user_id"
    params: dict = {"user_id": user_id}
    if product_id is not None:
        query += " AND product_id = :product_id"
        params["product_id"] = product_id
    if session_id is not None:
        query += " AND session_id = :session_id"
        params["session_id"] = session_id
    if version is not None:
        query += " AND version = :version"
        params["version"] = version
    query += " ORDER BY id DESC"
    with _get_engine().connect() as conn:
        result = conn.execute(text(query), params)
        return [dict(r) for r in result.mappings().fetchall()]


def get_comment_by_id(user_id: int, comment_id: int) -> Optional[dict]:
    with _get_engine().connect() as conn:
        result = conn.execute(
            text("SELECT * FROM comments WHERE id = :id AND user_id = :uid"),
            {"id": comment_id, "uid": user_id},
        )
        row = result.mappings().fetchone()
        return dict(row) if row else None


def update_comment_analysis(user_id: int, comment_id: int, analysis: dict) -> None:
    with _get_engine().connect() as conn:
        conn.execute(
            text("""UPDATE comments
                   SET sentiment = :sentiment, category = :category,
                       priority = :priority, reason = :reason,
                       improvement = :improvement, issue_tag = :issue_tag,
                       highlight_tag = :highlight_tag, is_processed = 1
                   WHERE id = :id AND user_id = :uid"""),
            {
                "sentiment": analysis.get("sentiment"),
                "category": analysis.get("category"),
                "priority": analysis.get("priority"),
                "reason": analysis.get("reason"),
                "improvement": analysis.get("improvement"),
                "issue_tag": analysis.get("issue_tag", ""),
                "highlight_tag": analysis.get("highlight_tag", ""),
                "id": comment_id,
                "uid": user_id,
            },
        )
        conn.commit()


def delete_comment(user_id: int, comment_id: int) -> None:
    with _get_engine().connect() as conn:
        conn.execute(
            text("DELETE FROM comments WHERE id = :id AND user_id = :uid"),
            {"id": comment_id, "uid": user_id},
        )
        conn.commit()


def delete_comments_by_session(user_id: int, session_id: int) -> None:
    with _get_engine().connect() as conn:
        conn.execute(
            text("DELETE FROM comments WHERE session_id = :sid AND user_id = :uid"),
            {"sid": session_id, "uid": user_id},
        )
        conn.commit()


def get_existing_hashes(user_id: int, product_id: str) -> set[str]:
    with _get_engine().connect() as conn:
        result = conn.execute(
            text("SELECT content_hash FROM comments WHERE user_id = :uid AND product_id = :pid AND content_hash IS NOT NULL"),
            {"uid": user_id, "pid": product_id},
        )
        return {r[0] for r in result.fetchall()}


def get_product_stats_deduped(user_id: int, product_id: str) -> dict:
    """按 content_hash 去重后统计产品级指标。"""
    sql = text("""
        SELECT
            COUNT(*) AS total_reviews,
            SUM(CASE WHEN sentiment = 'positive' THEN 1 ELSE 0 END) AS positive_count,
            SUM(CASE WHEN sentiment = 'negative' THEN 1 ELSE 0 END) AS negative_count,
            SUM(CASE WHEN sentiment = 'unrecognizable' THEN 1 ELSE 0 END) AS unrecognizable_count
        FROM (
            SELECT sentiment,
                   ROW_NUMBER() OVER (PARTITION BY content_hash ORDER BY id DESC) AS rn
            FROM comments
            WHERE user_id = :uid AND product_id = :pid AND content_hash IS NOT NULL
        ) sub
        WHERE rn = 1
    """)
    with _get_engine().connect() as conn:
        result = conn.execute(sql, {"uid": user_id, "pid": product_id})
        row = result.mappings().fetchone()
        return dict(row) if row else {"total_reviews": 0, "positive_count": 0, "negative_count": 0, "unrecognizable_count": 0}


def get_comments_deduped(user_id: int, product_id: str) -> list[dict]:
    """按 content_hash 去重，保留最新一条记录。"""
    sql = text("""
        SELECT * FROM (
            SELECT *,
                   ROW_NUMBER() OVER (PARTITION BY content_hash ORDER BY id DESC) AS rn
            FROM comments
            WHERE user_id = :uid AND product_id = :pid AND content_hash IS NOT NULL
        ) sub
        WHERE rn = 1
        ORDER BY id DESC
    """)
    with _get_engine().connect() as conn:
        result = conn.execute(sql, {"uid": user_id, "pid": product_id})
        return [dict(r) for r in result.mappings().fetchall()]


def get_unprocessed_comments(user_id: int, session_id: int) -> list[dict]:
    with _get_engine().connect() as conn:
        result = conn.execute(
            text("SELECT * FROM comments WHERE user_id = :uid AND session_id = :sid AND is_processed = 0"),
            {"uid": user_id, "sid": session_id},
        )
        return [dict(r) for r in result.mappings().fetchall()]


# ============================================================
# Sessions CRUD
# ============================================================

def create_session(user_id: int, session_data: dict) -> int:
    with _get_engine().connect() as conn:
        result = conn.execute(
            text("""INSERT INTO sessions
                   (user_id, product_id, version, auto_title, custom_title,
                    date_range_start, date_range_end, total_reviews,
                    positive_count, negative_count, category)
                   VALUES (:user_id, :product_id, :version, :auto_title, :custom_title,
                           :date_range_start, :date_range_end, :total_reviews,
                           :positive_count, :negative_count, :category)
                   RETURNING id"""),
            {
                "user_id": user_id,
                "product_id": session_data.get("product_id"),
                "version": session_data.get("version", "V1"),
                "auto_title": session_data.get("auto_title"),
                "custom_title": session_data.get("custom_title"),
                "date_range_start": session_data.get("date_range_start"),
                "date_range_end": session_data.get("date_range_end"),
                "total_reviews": session_data.get("total_reviews", 0),
                "positive_count": session_data.get("positive_count", 0),
                "negative_count": session_data.get("negative_count", 0),
                "category": session_data.get("category"),
            },
        )
        conn.commit()
        return result.fetchone()[0]


def get_sessions(user_id: int, product_id: Optional[str] = None) -> list[dict]:
    query = "SELECT * FROM sessions WHERE user_id = :user_id"
    params: dict = {"user_id": user_id}
    if product_id is not None:
        query += " AND product_id = :product_id"
        params["product_id"] = product_id
    query += " ORDER BY created_at DESC"
    with _get_engine().connect() as conn:
        result = conn.execute(text(query), params)
        return [dict(r) for r in result.mappings().fetchall()]


def get_session_by_id(user_id: int, session_id: int) -> Optional[dict]:
    with _get_engine().connect() as conn:
        result = conn.execute(
            text("SELECT * FROM sessions WHERE id = :id AND user_id = :uid"),
            {"id": session_id, "uid": user_id},
        )
        row = result.mappings().fetchone()
        return dict(row) if row else None


def update_session_title(user_id: int, session_id: int, custom_title: str) -> None:
    with _get_engine().connect() as conn:
        conn.execute(
            text("UPDATE sessions SET custom_title = :title WHERE id = :id AND user_id = :uid"),
            {"title": custom_title, "id": session_id, "uid": user_id},
        )
        conn.commit()


def update_session_stats(
    user_id: int,
    session_id: int,
    total_reviews: int,
    positive_count: int,
    negative_count: int,
) -> None:
    with _get_engine().connect() as conn:
        conn.execute(
            text("""UPDATE sessions
                   SET total_reviews = :total, positive_count = :pos, negative_count = :neg
                   WHERE id = :id AND user_id = :uid"""),
            {"total": total_reviews, "pos": positive_count, "neg": negative_count,
             "id": session_id, "uid": user_id},
        )
        conn.commit()


def delete_session(user_id: int, session_id: int) -> None:
    with _get_engine().connect() as conn:
        conn.execute(
            text("DELETE FROM comments WHERE session_id = :sid AND user_id = :uid"),
            {"sid": session_id, "uid": user_id},
        )
        conn.execute(
            text("DELETE FROM sessions WHERE id = :id AND user_id = :uid"),
            {"id": session_id, "uid": user_id},
        )
        conn.commit()


def delete_product(user_id: int, product_id: str) -> None:
    with _get_engine().connect() as conn:
        result = conn.execute(
            text("SELECT id FROM sessions WHERE user_id = :uid AND product_id = :pid"),
            {"uid": user_id, "pid": product_id},
        )
        session_ids = [row[0] for row in result.fetchall()]
        if session_ids:
            for sid in session_ids:
                conn.execute(
                    text("DELETE FROM comments WHERE user_id = :uid AND session_id = :sid"),
                    {"uid": user_id, "sid": sid},
                )
                conn.execute(
                    text("DELETE FROM sessions WHERE user_id = :uid AND id = :sid"),
                    {"uid": user_id, "sid": sid},
                )
        conn.commit()


# ============================================================
# Settings CRUD
# ============================================================

def get_setting(user_id: int, key: str) -> Optional[str]:
    with _get_engine().connect() as conn:
        result = conn.execute(
            text("SELECT value FROM settings WHERE user_id = :uid AND key = :key"),
            {"uid": user_id, "key": key},
        )
        row = result.mappings().fetchone()
        return row["value"] if row else None


def set_setting(user_id: int, key: str, value: str) -> None:
    with _get_engine().connect() as conn:
        conn.execute(
            text("""INSERT INTO settings (user_id, key, value) VALUES (:uid, :key, :val)
                   ON CONFLICT(user_id, key) DO UPDATE SET value = EXCLUDED.value"""),
            {"uid": user_id, "key": key, "val": value},
        )
        conn.commit()


def get_all_settings(user_id: int) -> dict[str, str]:
    with _get_engine().connect() as conn:
        result = conn.execute(
            text("SELECT key, value FROM settings WHERE user_id = :uid"),
            {"uid": user_id},
        )
        return {r["key"]: r["value"] for r in result.mappings().fetchall()}


def delete_setting(user_id: int, key: str) -> None:
    with _get_engine().connect() as conn:
        conn.execute(
            text("DELETE FROM settings WHERE user_id = :uid AND key = :key"),
            {"uid": user_id, "key": key},
        )
        conn.commit()
