from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

import psycopg2
import psycopg2.extras
import psycopg2.pool
import streamlit as st
from dotenv import load_dotenv


load_dotenv(Path(__file__).resolve().parent.parent / ".env")


class DatabaseConnectionUnavailable(RuntimeError):
    """Raised when the database connection pool cannot be created."""


def _get_database_url() -> str:
    """优先使用本地环境变量，便于本地开发覆盖 Streamlit secrets。"""
    env_url = os.getenv("DATABASE_URL") or os.getenv("SUPABASE_DB_URL")
    if env_url:
        return env_url.strip()

    try:
        return str(st.secrets["database"]["url"]).strip()
    except Exception:
        return ""


def _get_database_host(db_url: str) -> str:
    parsed = urlparse(db_url)
    return parsed.hostname or ""


def _render_connection_error(error: psycopg2.OperationalError, db_url: str) -> None:
    error_text = str(error).strip()
    host = _get_database_host(db_url)

    if "could not translate host name" in error_text:
        st.error(
            "⚠️ 数据库连接失败：当前 Supabase 主机名无法在本机解析。"
        )
        st.info(
            "请检查 3 件事：\n"
            f"1. 当前连接主机是否正确：`{host or '未识别'}`\n"
            "2. 到 Supabase 后台复制最新的 Connection Pooling 连接串，覆盖 `.streamlit/secrets.toml`\n"
            "3. 本地开发时可直接在 `.env` 增加 `DATABASE_URL=...`，它会优先覆盖 Streamlit secrets"
        )
        return

    if "connection refused" in error_text or "timeout expired" in error_text:
        st.error("⚠️ 数据库连接失败：数据库主机可识别，但当前网络无法连通 Supabase。")
        st.info(
            "请优先确认：\n"
            f"1. 当前连接主机：`{host or '未识别'}`\n"
            "2. 本机网络是否可访问外网\n"
            "3. Supabase 项目是否仍在运行，连接串是否为 Pooling 地址（通常是 6543 端口）"
        )
        return

    st.error(f"⚠️ 数据库连接失败：{error_text}")


@st.cache_resource
def _get_connection_pool():
    """全局共享的 PostgreSQL 连接池，避免每次查询都重新建立 TCP+SSL 握手。"""
    db_url = _get_database_url()
    if not db_url:
        return None
    try:
        return psycopg2.pool.ThreadedConnectionPool(
            minconn=1,
            maxconn=10,
            dsn=db_url,
            connect_timeout=10,
            sslmode="require",
        )
    except psycopg2.OperationalError as e:
        _render_connection_error(e, db_url)
        return None


class _PooledConnection:
    """轻量包装：将 close() 改为归还到连接池，其他属性透传给真实连接。"""

    __slots__ = ("_conn", "_pool", "_closed")

    def __init__(self, conn, pool):
        object.__setattr__(self, "_conn", conn)
        object.__setattr__(self, "_pool", pool)
        object.__setattr__(self, "_closed", False)

    def close(self):
        if self._closed:
            return
        object.__setattr__(self, "_closed", True)
        try:
            if self._conn.closed:
                self._pool.putconn(self._conn, close=True)
            else:
                self._conn.rollback()
                self._pool.putconn(self._conn)
        except Exception:
            try:
                self._conn.close()
            except Exception:
                pass

    def __getattr__(self, name):
        return getattr(self._conn, name)

    def __setattr__(self, name, value):
        setattr(self._conn, name, value)

    def __enter__(self):
        return self._conn.__enter__()

    def __exit__(self, exc_type, exc_val, exc_tb):
        return self._conn.__exit__(exc_type, exc_val, exc_tb)


def get_connection():
    """从连接池借一条连接，调用方 conn.close() 时会自动归还到池。"""
    db_url = _get_database_url()
    if not db_url:
        st.error("⚠️ 数据库连接失败：未找到数据库连接串。")
        st.info(
            "请在本地配置以下任一位置后重试：\n"
            "1. `.env` 中增加 `DATABASE_URL=...`\n"
            "2. `.streamlit/secrets.toml` 中配置 `[database] url = \"...\"`"
        )
        st.stop()
        raise DatabaseConnectionUnavailable("Database URL is missing.")

    pool = _get_connection_pool()
    if pool is None:
        st.stop()
        raise DatabaseConnectionUnavailable("Database connection pool is unavailable.")

    try:
        conn = pool.getconn()
    except psycopg2.OperationalError as e:
        _render_connection_error(e, db_url)
        st.stop()
        raise DatabaseConnectionUnavailable("Database connection failed.") from e

    if conn.closed:
        pool.putconn(conn, close=True)
        conn = pool.getconn()

    return _PooledConnection(conn, pool)


def init_db() -> None:
    """在 Supabase 上表已通过 SQL 脚本创建，此函数仅做兼容保留。"""
    pass


# ============================================================
# Users CRUD
# ============================================================

def create_user(username: str, password_hash: str, email: str = "") -> int:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO users (username, password_hash, email) VALUES (%s, %s, %s) RETURNING id",
                (username, password_hash, email or None),
            )
            user_id = cur.fetchone()[0]
            conn.commit()
            return user_id
    finally:
        conn.close()


def get_user_by_username(username: str) -> Optional[dict]:
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT * FROM users WHERE username = %s", (username,))
            row = cur.fetchone()
            return dict(row) if row else None
    finally:
        conn.close()


def get_user_by_id(user_id: int) -> Optional[dict]:
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT * FROM users WHERE id = %s", (user_id,))
            row = cur.fetchone()
            return dict(row) if row else None
    finally:
        conn.close()


def get_user_plan(user_id: int) -> str:
    """获取用户订阅计划；旧数据库未迁移时默认 free。"""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT plan FROM users WHERE id = %s", (user_id,))
            row = cur.fetchone()
            return str(row[0] or "free") if row else "free"
    except psycopg2.errors.UndefinedColumn:
        conn.rollback()
        return "free"
    finally:
        conn.close()


def update_user_plan(user_id: int, plan: str, paddle_customer_id: Optional[str] = None) -> None:
    """更新用户订阅计划。"""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            if paddle_customer_id:
                cur.execute(
                    "UPDATE users SET plan = %s, paddle_customer_id = %s WHERE id = %s",
                    (plan, paddle_customer_id, user_id),
                )
            else:
                cur.execute("UPDATE users SET plan = %s WHERE id = %s", (plan, user_id))
            conn.commit()
    finally:
        conn.close()


def get_user_product_count(user_id: int) -> int:
    """统计用户已有产品数，用于 Free 版计费墙。"""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(DISTINCT product_id) FROM sessions WHERE user_id = %s", (user_id,))
            row = cur.fetchone()
            return int(row[0] or 0) if row else 0
    finally:
        conn.close()


def update_user_api_key(user_id: int, api_key_encrypted: str | None) -> None:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("UPDATE users SET api_key_encrypted = %s WHERE id = %s", (api_key_encrypted, user_id))
            conn.commit()
    finally:
        conn.close()


def delete_user(user_id: int) -> None:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM settings WHERE user_id = %s", (user_id,))
            cur.execute("DELETE FROM comments WHERE user_id = %s", (user_id,))
            cur.execute("DELETE FROM sessions WHERE user_id = %s", (user_id,))
            cur.execute("DELETE FROM users WHERE id = %s", (user_id,))
            conn.commit()
    finally:
        conn.close()


# ============================================================
# Comments CRUD
# ============================================================

_COMMENT_FIELDS = (
    "user_id, product_id, version, content, rating, date, "
    "reviewer, source, content_hash, sentiment, content_sentiment, category, "
    "priority, reason, improvement, issue_tag, highlight_tag, "
    "is_processed, session_id"
)
_COMMENT_PLACEHOLDERS = ", ".join(["%s"] * 19)


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
        comment.get("content_sentiment", comment.get("sentiment")),
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
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                f"INSERT INTO comments ({_COMMENT_FIELDS}) VALUES ({_COMMENT_PLACEHOLDERS}) RETURNING id",
                values,
            )
            comment_id = cur.fetchone()[0]
            conn.commit()
            return comment_id
    finally:
        conn.close()


def add_comments_batch(user_id: int, comments: list[dict]) -> int:
    rows = [_comment_values(user_id, c) for c in comments]
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            psycopg2.extras.execute_batch(
                cur,
                f"INSERT INTO comments ({_COMMENT_FIELDS}) VALUES ({_COMMENT_PLACEHOLDERS})",
                rows,
            )
            conn.commit()
            get_comments.clear()
            get_existing_hashes.clear()
            get_comments_deduped.clear()
            get_product_stats_deduped.clear()
            return len(rows)
    finally:
        conn.close()


# ============================================================
# Upload Jobs CRUD
# ============================================================

def create_upload_job(user_id: int, job_data: dict) -> int:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO upload_jobs
                   (user_id, status, source_filename, product_id, version, workflow_purpose,
                    product_ref_id, variant_ref_id, total_rows, processed_rows,
                    positive_count, negative_count, session_id, error_message, payload_json)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                   RETURNING id""",
                (
                    user_id,
                    job_data.get("status", "queued"),
                    job_data.get("source_filename"),
                    job_data.get("product_id"),
                    job_data.get("version", "V1"),
                    job_data.get("workflow_purpose"),
                    job_data.get("product_ref_id"),
                    job_data.get("variant_ref_id"),
                    job_data.get("total_rows", 0),
                    job_data.get("processed_rows", 0),
                    job_data.get("positive_count", 0),
                    job_data.get("negative_count", 0),
                    job_data.get("session_id"),
                    job_data.get("error_message"),
                    psycopg2.extras.Json(job_data.get("payload_json"))
                    if job_data.get("payload_json") is not None
                    else None,
                ),
            )
            job_id = int(cur.fetchone()[0])
            conn.commit()
            get_upload_job.clear()
            return job_id
    finally:
        conn.close()


@st.cache_data(ttl=15)
def get_upload_job(user_id: int, job_id: int) -> Optional[dict]:
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                "SELECT * FROM upload_jobs WHERE user_id = %s AND id = %s",
                (user_id, job_id),
            )
            row = cur.fetchone()
            return dict(row) if row else None
    finally:
        conn.close()


def update_upload_job(
    user_id: int,
    job_id: int,
    updates: dict,
) -> None:
    allowed_fields = {
        "status",
        "processed_rows",
        "positive_count",
        "negative_count",
        "session_id",
        "error_message",
        "payload_json",
        "total_rows",
    }
    fields = [key for key in updates.keys() if key in allowed_fields]
    if not fields:
        return

    assignments = []
    values: list = []
    for field in fields:
        if field == "payload_json" and updates.get(field) is not None:
            assignments.append(f"{field} = %s")
            values.append(psycopg2.extras.Json(updates[field]))
        else:
            assignments.append(f"{field} = %s")
            values.append(updates.get(field))
    assignments.append("updated_at = NOW()")
    if updates.get("status") in {"done", "failed"}:
        assignments.append("completed_at = NOW()")

    values.extend([job_id, user_id])

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                f"UPDATE upload_jobs SET {', '.join(assignments)} WHERE id = %s AND user_id = %s",
                values,
            )
            conn.commit()
            get_upload_job.clear()
    finally:
        conn.close()


def _vector_to_sql(vector: list[float]) -> str:
    return "[" + ",".join(str(float(value)) for value in vector) + "]"


def update_comment_embedding(user_id: int, comment_id: int, embedding: list[float]) -> None:
    """写入单条评论 embedding。"""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE comments SET embedding = %s::vector WHERE id = %s AND user_id = %s",
                (_vector_to_sql(embedding), comment_id, user_id),
            )
            conn.commit()
            get_comments.clear()
            get_comments_deduped.clear()
    finally:
        conn.close()


def get_comments_missing_embeddings(user_id: int, session_id: int) -> list[dict]:
    """获取当前批次中尚未生成 embedding 的评论。"""
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """SELECT id, content
                   FROM comments
                   WHERE user_id = %s AND session_id = %s
                     AND embedding IS NULL AND COALESCE(content, '') <> ''
                   ORDER BY id ASC""",
                (user_id, session_id),
            )
            return [dict(r) for r in cur.fetchall()]
    except psycopg2.errors.UndefinedColumn:
        conn.rollback()
        return []
    finally:
        conn.close()


def search_comments_by_embedding(
    user_id: int,
    embedding: list[float],
    comment_ids: Optional[list[int]] = None,
    top_k: int = 5,
) -> list[dict]:
    """使用 pgvector 余弦距离检索最相关评论。"""
    if comment_ids is not None and not comment_ids:
        return []

    query = "SELECT * FROM comments WHERE user_id = %s AND embedding IS NOT NULL"
    params: list = [user_id]
    if comment_ids is not None:
        query += " AND id = ANY(%s)"
        params.append(comment_ids)
    query += " ORDER BY embedding <=> %s::vector LIMIT %s"
    params.extend([_vector_to_sql(embedding), top_k])

    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(query, params)
            return [dict(r) for r in cur.fetchall()]
    except psycopg2.errors.UndefinedColumn:
        conn.rollback()
        return []
    finally:
        conn.close()


@st.cache_data(ttl=30)
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
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(query, params)
            return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()


def get_comment_by_id(user_id: int, comment_id: int) -> Optional[dict]:
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                "SELECT * FROM comments WHERE id = %s AND user_id = %s",
                (comment_id, user_id),
            )
            row = cur.fetchone()
            return dict(row) if row else None
    finally:
        conn.close()


def update_comment_analysis(user_id: int, comment_id: int, analysis: dict) -> None:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """UPDATE comments
                   SET sentiment = %s, content_sentiment = %s, category = %s, priority = %s, reason = %s,
                       improvement = %s, issue_tag = %s, highlight_tag = %s,
                       aspects_json = %s, analyzer_version = %s,
                       is_processed = 1
                   WHERE id = %s AND user_id = %s""",
                (
                    analysis.get("sentiment"),
                    analysis.get("content_sentiment", analysis.get("sentiment")),
                    analysis.get("category"),
                    analysis.get("priority"),
                    analysis.get("reason"),
                    analysis.get("improvement"),
                    analysis.get("issue_tag", ""),
                    analysis.get("highlight_tag", ""),
                    json.dumps(analysis["aspects_json"], ensure_ascii=False) if analysis.get("aspects_json") else None,
                    analysis.get("analyzer_version", "legacy"),
                    comment_id,
                    user_id,
                ),
            )
            conn.commit()
            get_comments.clear()
            get_comments_deduped.clear()
            get_product_stats_deduped.clear()
    finally:
        conn.close()


def delete_comment(user_id: int, comment_id: int) -> None:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM comments WHERE id = %s AND user_id = %s",
                (comment_id, user_id),
            )
            conn.commit()
    finally:
        conn.close()


def delete_comments_by_session(user_id: int, session_id: int) -> None:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM comments WHERE session_id = %s AND user_id = %s",
                (session_id, user_id),
            )
            conn.commit()
    finally:
        conn.close()


@st.cache_data(ttl=30)
def get_existing_hashes(user_id: int, product_id: str) -> set[str]:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT content_hash FROM comments WHERE user_id = %s AND product_id = %s AND content_hash IS NOT NULL",
                (user_id, product_id),
            )
            return {r[0] for r in cur.fetchall()}
    finally:
        conn.close()


@st.cache_data(ttl=30)
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
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, (user_id, product_id))
            row = cur.fetchone()
            return dict(row) if row else {"total_reviews": 0, "positive_count": 0, "negative_count": 0, "unrecognizable_count": 0}
    finally:
        conn.close()


@st.cache_data(ttl=30)
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
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, (user_id, product_id))
            return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()


def get_unprocessed_comments(user_id: int, session_id: int) -> list[dict]:
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                "SELECT * FROM comments WHERE user_id = %s AND session_id = %s AND is_processed = 0",
                (user_id, session_id),
            )
            return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()


# ============================================================
# Sessions CRUD
# ============================================================

def create_session(user_id: int, session_data: dict) -> int:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            try:
                cur.execute(
                    """INSERT INTO sessions
                       (user_id, product_id, version, auto_title, custom_title,
                        date_range_start, date_range_end, total_reviews,
                        positive_count, negative_count, category, prompt_version, version_notes,
                        workflow_purpose, product_ref_id, variant_ref_id)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id""",
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
                        session_data.get("prompt_version"),
                        session_data.get("version_notes"),
                        session_data.get("workflow_purpose"),
                        session_data.get("product_ref_id"),
                        session_data.get("variant_ref_id"),
                    ),
                )
            except psycopg2.errors.UndefinedColumn:
                conn.rollback()
                cur.execute(
                    """INSERT INTO sessions
                       (user_id, product_id, version, auto_title, custom_title,
                        date_range_start, date_range_end, total_reviews,
                        positive_count, negative_count, category, prompt_version, version_notes)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id""",
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
                        session_data.get("prompt_version"),
                        session_data.get("version_notes"),
                    ),
                )
            session_id = cur.fetchone()[0]
            conn.commit()
            get_sessions.clear()
            return session_id
    finally:
        conn.close()


def update_session_notes(user_id: int, session_id: int, version_notes: str) -> None:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE sessions SET version_notes = %s WHERE id = %s AND user_id = %s",
                (version_notes, session_id, user_id),
            )
            conn.commit()
    finally:
        conn.close()


@st.cache_data(ttl=30)
def get_sessions(user_id: int, product_id: Optional[str] = None) -> list[dict]:
    query = "SELECT * FROM sessions WHERE user_id = %s"
    params: list = [user_id]
    if product_id is not None:
        query += " AND product_id = %s"
        params.append(product_id)
    query += " ORDER BY created_at DESC"
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(query, params)
            return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()


@st.cache_data(ttl=30)
def get_session_by_id(user_id: int, session_id: int) -> Optional[dict]:
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                "SELECT * FROM sessions WHERE id = %s AND user_id = %s",
                (session_id, user_id),
            )
            row = cur.fetchone()
            return dict(row) if row else None
    finally:
        conn.close()


def update_session_title(user_id: int, session_id: int, custom_title: str) -> None:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE sessions SET custom_title = %s WHERE id = %s AND user_id = %s",
                (custom_title, session_id, user_id),
            )
            conn.commit()
            get_sessions.clear()
            get_session_by_id.clear()
    finally:
        conn.close()


def update_session_stats(
    user_id: int,
    session_id: int,
    total_reviews: int,
    positive_count: int,
    negative_count: int,
) -> None:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """UPDATE sessions
                   SET total_reviews = %s, positive_count = %s, negative_count = %s
                   WHERE id = %s AND user_id = %s""",
                (total_reviews, positive_count, negative_count, session_id, user_id),
            )
            conn.commit()
            get_sessions.clear()
            get_session_by_id.clear()
    finally:
        conn.close()


def delete_session(user_id: int, session_id: int) -> None:
    conn = get_connection()
    try:
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
            get_sessions.clear()
            get_session_by_id.clear()
            get_comments.clear()
            get_comments_deduped.clear()
            get_product_stats_deduped.clear()
    finally:
        conn.close()


def delete_product(user_id: int, product_id: str) -> None:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id FROM sessions WHERE user_id = %s AND product_id = %s",
                (user_id, product_id),
            )
            session_ids = [row[0] for row in cur.fetchall()]
            for sid in session_ids:
                cur.execute(
                    "DELETE FROM comments WHERE user_id = %s AND session_id = %s",
                    (user_id, sid),
                )
                cur.execute(
                    "DELETE FROM sessions WHERE user_id = %s AND id = %s",
                    (user_id, sid),
                )
            conn.commit()
            get_sessions.clear()
            get_session_by_id.clear()
            get_comments.clear()
            get_comments_deduped.clear()
            get_product_stats_deduped.clear()
            get_existing_hashes.clear()
    finally:
        conn.close()


# ============================================================
# Settings CRUD
# ============================================================

@st.cache_data(ttl=30)
def get_setting(user_id: int, key: str) -> Optional[str]:
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                "SELECT value FROM settings WHERE user_id = %s AND key = %s",
                (user_id, key),
            )
            row = cur.fetchone()
            return row["value"] if row else None
    finally:
        conn.close()


def set_setting(user_id: int, key: str, value: str) -> None:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO settings (user_id, key, value) VALUES (%s, %s, %s)
                   ON CONFLICT(user_id, key) DO UPDATE SET value = EXCLUDED.value""",
                (user_id, key, value),
            )
            conn.commit()
            get_setting.clear()
            get_all_settings.clear()
    finally:
        conn.close()


@st.cache_data(ttl=30)
def get_all_settings(user_id: int) -> dict[str, str]:
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                "SELECT key, value FROM settings WHERE user_id = %s",
                (user_id,),
            )
            return {r["key"]: r["value"] for r in cur.fetchall()}
    finally:
        conn.close()


def delete_setting(user_id: int, key: str) -> None:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM settings WHERE user_id = %s AND key = %s",
                (user_id, key),
            )
            conn.commit()
    finally:
        conn.close()


# ============================================================
# Password Reset
# ============================================================

def get_user_by_email(email: str) -> Optional[dict]:
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT * FROM users WHERE email = %s", (email,))
            row = cur.fetchone()
            return dict(row) if row else None
    finally:
        conn.close()


def create_reset_token(email: str, token: str, expires_at: str) -> None:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO password_reset_tokens (email, token, expires_at) VALUES (%s, %s, %s)",
                (email, token, expires_at),
            )
            conn.commit()
    finally:
        conn.close()


def get_valid_reset_token(email: str, token: str) -> Optional[dict]:
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """SELECT * FROM password_reset_tokens
                   WHERE email = %s AND token = %s AND used = FALSE AND expires_at > NOW()
                   ORDER BY id DESC LIMIT 1""",
                (email, token),
            )
            row = cur.fetchone()
            return dict(row) if row else None
    finally:
        conn.close()


def mark_token_used(token_id: int) -> None:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("UPDATE password_reset_tokens SET used = TRUE WHERE id = %s", (token_id,))
            conn.commit()
    finally:
        conn.close()


def update_user_password(user_id: int, password_hash: str) -> None:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("UPDATE users SET password_hash = %s WHERE id = %s", (password_hash, user_id))
            conn.commit()
    finally:
        conn.close()
