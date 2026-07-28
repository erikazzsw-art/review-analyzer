from __future__ import annotations

import json
import logging
import os
import time as _time
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import psycopg2
import psycopg2.extras
import psycopg2.pool
from dotenv import load_dotenv

from review_analyzer.review_dates import review_date_for_comment

logger = logging.getLogger(__name__)

load_dotenv(Path(__file__).resolve().parent / ".env")


class DatabaseConnectionUnavailable(RuntimeError):
    """Raised when the database connection pool cannot be created."""


def _get_database_url() -> str:
    """从环境变量获取数据库连接串。"""
    env_url = os.getenv("DATABASE_URL") or os.getenv("SUPABASE_DB_URL")
    return env_url.strip() if env_url else ""


def _get_database_host(db_url: str) -> str:
    parsed = urlparse(db_url)
    return parsed.hostname or ""


def _render_connection_error(error: psycopg2.OperationalError, db_url: str) -> None:
    error_text = str(error).strip()
    host = _get_database_host(db_url)
    logger.error("Database connection failed: %s (host=%s)", error_text, host)


_connection_pool = None
_pool_creation_failed = False
_pool_last_attempt = 0.0
_POOL_RETRY_INTERVAL = 10.0  # 连接池创建失败后 10 秒才允许重试

_COMMENT_READ_COLUMNS = (
    "id",
    "user_id",
    "product_id",
    "version",
    "content",
    "rating",
    "date",
    "review_date",
    "reviewer",
    "source",
    "content_hash",
    "sentiment",
    "content_sentiment",
    "category",
    "priority",
    "reason",
    "improvement",
    "issue_tag",
    "highlight_tag",
    "is_processed",
    "session_id",
    "analyzer_version",
    "created_at",
    "updated_at",
    "deleted_at",
    "cache_hit_level",
    "cache_source_id",
    "cache_hit_source",
    "source_variant_asin",
    "source_channel",
    "cluster_id",
    "cluster_representative_id",
)
_COMMENT_READ_COLUMNS_LEGACY = tuple(
    column for column in _COMMENT_READ_COLUMNS if column != "review_date"
)
_COMMENT_EMBEDDING_COLUMN = "embedding"
_COMMENT_READ_RETRY_ERRORS = (psycopg2.OperationalError, psycopg2.InterfaceError)

_COMPACT_ASPECTS_JSON_SQL = """
CASE
    WHEN aspects_json IS NULL THEN NULL
    WHEN aspects_json->>'customer_label_occurrence_schema_version' = '1.0'
         THEN jsonb_strip_nulls(jsonb_build_object(
             'customer_label_occurrence_schema_version', aspects_json->'customer_label_occurrence_schema_version',
             'customer_label_occurrence_ruleset_version', aspects_json->'customer_label_occurrence_ruleset_version',
             'specific_issue_schema_version', aspects_json->'specific_issue_schema_version',
             'customer_label_schema_version', aspects_json->'customer_label_schema_version',
             'issue_ruleset_version', aspects_json->'issue_ruleset_version',
             'highlight_ruleset_version', aspects_json->'highlight_ruleset_version',
             'sub_category', aspects_json->'sub_category',
             'cluster_propagated', aspects_json->'cluster_propagated',
             'customer_label_occurrences', aspects_json->'customer_label_occurrences'
         ))
    ELSE aspects_json
END AS aspects_json
""".strip()


def _clear_cache(func) -> None:
    """Safely clear a cache-like function if it supports `.clear()`."""
    clear = getattr(func, "clear", None)
    if callable(clear):
        clear()


def _clear_comment_analysis_caches() -> None:
    _clear_cache(get_comments)
    _clear_cache(get_comments_deduped)
    _clear_cache(get_product_stats_deduped)


def _get_connection_pool():
    """全局共享的 PostgreSQL 连接池，创建失败后定期重试。"""
    global _connection_pool, _pool_creation_failed, _pool_last_attempt
    if _connection_pool is not None:
        return _connection_pool

    import time
    now = time.time()
    if _pool_creation_failed and (now - _pool_last_attempt) < _POOL_RETRY_INTERVAL:
        return None

    db_url = _get_database_url()
    if not db_url:
        return None
    try:
        _pool_last_attempt = now
        _connection_pool = psycopg2.pool.ThreadedConnectionPool(
            minconn=2,
            maxconn=50,
            dsn=db_url,
            connect_timeout=10,
            sslmode="require",
            keepalives=1,
            keepalives_idle=30,
            keepalives_interval=5,
            keepalives_count=3,
        )
        _pool_creation_failed = False
        return _connection_pool
    except psycopg2.OperationalError as e:
        _pool_creation_failed = True
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
    """从连接池借一条连接，调用方 conn.close() 时会自动归还到池。

    当连接池暂时耗尽时，最多重试 3 次（指数退避 0.5s / 1s / 2s）。
    """
    db_url = _get_database_url()
    if not db_url:
        raise DatabaseConnectionUnavailable("Database URL is missing.")

    pool = _get_connection_pool()
    if pool is None:
        raise DatabaseConnectionUnavailable("Database connection pool is unavailable.")

    max_retries = 3
    for attempt in range(max_retries + 1):
        try:
            conn = pool.getconn()
            break
        except psycopg2.pool.PoolError as e:
            if attempt == max_retries:
                raise DatabaseConnectionUnavailable(
                    "Connection pool exhausted after retries."
                ) from e
            _time.sleep(0.5 * (2 ** attempt))
        except psycopg2.OperationalError as e:
            _render_connection_error(e, db_url)
            raise DatabaseConnectionUnavailable("Database connection failed.") from e

    if conn.closed:
        pool.putconn(conn, close=True)
        conn = pool.getconn()

    try:
        with conn.cursor() as cur:
            cur.execute("SELECT 1")
    except Exception:
        pool.putconn(conn, close=True)
        try:
            conn = pool.getconn()
        except (psycopg2.OperationalError, psycopg2.pool.PoolError) as e:
            raise DatabaseConnectionUnavailable("Database connection failed.") from e

    return _PooledConnection(conn, pool)


def init_db() -> None:
    """在 Supabase 上表已通过 SQL 脚本创建，此函数仅做兼容保留。"""
    pass


# ============================================================
# Users CRUD
# ============================================================

def create_user(
    username: str,
    password_hash: str,
    email: str,
    *,
    locale: str = "en-US",
    terms_version: str | None = None,
    age_confirmed: bool = False,
    marketing_opt_in: bool = False,
) -> int:
    """创建用户，支持 V4-出海合规字段。

    Args:
        age_confirmed: 后端二次校验；若为 False，调用方应在调用前拒绝。
    """
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc)
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO users (
                    username, password_hash, email,
                    locale,
                    terms_accepted_at, terms_version,
                    age_confirmed_at,
                    marketing_opt_in, marketing_opt_in_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
                """,
                (
                    username,
                    password_hash,
                    email,
                    locale,
                    now,
                    terms_version,
                    now if age_confirmed else None,
                    marketing_opt_in,
                    now if marketing_opt_in else None,
                ),
            )
            user_id = cur.fetchone()[0]
            conn.commit()
            return user_id
    finally:
        conn.close()


def get_user_by_username(username: str) -> dict | None:
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT * FROM users WHERE username = %s", (username,))
            row = cur.fetchone()
            return dict(row) if row else None
    finally:
        conn.close()


def get_user_by_id(user_id: int) -> dict | None:
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


def get_paddle_customer_id(user_id: int) -> str | None:
    """获取用户的 Paddle customer ID，用于 Paddle Retain (pwCustomer)。"""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT paddle_customer_id FROM users WHERE id = %s", (user_id,))
            row = cur.fetchone()
            return str(row[0]) if row and row[0] else None
    except psycopg2.errors.UndefinedColumn:
        conn.rollback()
        return None
    finally:
        conn.close()


def update_user_plan(user_id: int, plan: str, paddle_customer_id: str | None = None) -> None:
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


_PLAN_MONTHLY_GRANT: dict[str, int] = {
    "free": 300,
    "starter": 5000,
    "pro_early": 15000,
    "pro": 15000,
    "team": 45000,
}


def update_user_credits_monthly_grant(user_id: int, plan: str) -> None:
    """套餐变更后同步更新 user_credits.monthly_grant（不重置 balance）。"""
    grant = _PLAN_MONTHLY_GRANT.get(plan, 300)
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE user_credits SET monthly_grant = %s, updated_at = NOW() WHERE user_id = %s",
                (grant, user_id),
            )
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

_COMMENT_INSERT_FIELDS = (
    "user_id",
    "product_id",
    "version",
    "content",
    "rating",
    "date",
    "review_date",
    "reviewer",
    "source",
    "source_channel",
    "source_variant_asin",
    "content_hash",
    "sentiment",
    "content_sentiment",
    "category",
    "priority",
    "reason",
    "improvement",
    "issue_tag",
    "highlight_tag",
    "is_processed",
    "session_id",
)
_COMMENT_INSERT_FIELDS_LEGACY = tuple(
    field for field in _COMMENT_INSERT_FIELDS if field != "review_date"
)


def _comment_insert_sql(fields: tuple[str, ...]) -> str:
    placeholders = ", ".join(["%s"] * len(fields))
    return f"INSERT INTO comments ({', '.join(fields)}) VALUES ({placeholders})"


def _comment_values(user_id: int, comment: dict, fields: tuple[str, ...] = _COMMENT_INSERT_FIELDS) -> list:
    values = {
        "user_id": user_id,
        "product_id": comment.get("product_id"),
        "version": comment.get("version", "V1"),
        "content": comment.get("content"),
        "rating": comment.get("rating"),
        "date": comment.get("date"),
        "review_date": review_date_for_comment(comment),
        "reviewer": comment.get("reviewer"),
        "source": comment.get("source"),
        "source_channel": comment.get("source_channel") or "manual",
        "source_variant_asin": comment.get("source_variant_asin"),
        "content_hash": comment.get("content_hash"),
        "sentiment": comment.get("sentiment"),
        "content_sentiment": comment.get("content_sentiment", comment.get("sentiment")),
        "category": comment.get("category"),
        "priority": comment.get("priority"),
        "reason": comment.get("reason"),
        "improvement": comment.get("improvement"),
        "issue_tag": comment.get("issue_tag", ""),
        "highlight_tag": comment.get("highlight_tag", ""),
        "is_processed": comment.get("is_processed", 0),
        "session_id": comment.get("session_id"),
    }
    return [values[field] for field in fields]


def add_comment(user_id: int, comment: dict) -> int:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            try:
                cur.execute(
                    f"{_comment_insert_sql(_COMMENT_INSERT_FIELDS)} RETURNING id",
                    _comment_values(user_id, comment),
                )
            except psycopg2.errors.UndefinedColumn:
                conn.rollback()
                logger.warning("comments.review_date column unavailable; inserting comment without normalized date")
                cur.execute(
                    f"{_comment_insert_sql(_COMMENT_INSERT_FIELDS_LEGACY)} RETURNING id",
                    _comment_values(user_id, comment, _COMMENT_INSERT_FIELDS_LEGACY),
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
            try:
                psycopg2.extras.execute_batch(
                    cur,
                    _comment_insert_sql(_COMMENT_INSERT_FIELDS),
                    rows,
                )
            except psycopg2.errors.UndefinedColumn:
                conn.rollback()
                logger.warning("comments.review_date column unavailable; inserting batch without normalized dates")
                legacy_rows = [
                    _comment_values(user_id, c, _COMMENT_INSERT_FIELDS_LEGACY)
                    for c in comments
                ]
                psycopg2.extras.execute_batch(
                    cur,
                    _comment_insert_sql(_COMMENT_INSERT_FIELDS_LEGACY),
                    legacy_rows,
                )
            conn.commit()
            _clear_cache(get_comments)
            _clear_cache(get_existing_hashes)
            _clear_cache(get_comments_deduped)
            _clear_cache(get_product_stats_deduped)
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
            try:
                cur.execute(
                    """INSERT INTO upload_jobs
                       (user_id, status, source_filename, product_id, version, workflow_purpose,
                        product_ref_id, variant_ref_id, total_rows, processed_rows,
                        positive_count, negative_count, session_id, error_message, payload_json,
                        source_channel)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
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
                        job_data.get("source_channel", "manual"),
                    ),
                )
            except psycopg2.errors.UndefinedColumn:
                conn.rollback()
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
            _clear_cache(get_upload_job)
            return job_id
    finally:
        conn.close()


def get_upload_job(user_id: int, job_id: int) -> dict | None:
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


def get_upload_jobs_by_session(user_id: int, session_id: int) -> list[dict]:
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                "SELECT * FROM upload_jobs WHERE user_id = %s AND session_id = %s ORDER BY id DESC",
                (user_id, session_id),
            )
            return [dict(r) for r in cur.fetchall()]
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
        "trace_json",
        "total_rows",
    }
    fields = [key for key in updates if key in allowed_fields]
    if not fields:
        return

    assignments = []
    values: list = []
    for field in fields:
        if field in ("payload_json", "trace_json") and updates.get(field) is not None:
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
            _clear_cache(get_upload_job)
    finally:
        conn.close()


def _vector_to_sql(vector: list[float]) -> str:
    return "[" + ",".join(str(float(value)) for value in vector) + "]"


def _execute_values_attempted_count(rows: list[tuple]) -> int:
    return len(rows)


def update_comment_embedding(user_id: int, comment_id: int, embedding: list[float]) -> None:
    """写入单条评论 embedding。"""
    update_comment_embeddings_batch(user_id, [{"comment_id": comment_id, "embedding": embedding}])


def update_comment_embeddings_batch(user_id: int, embeddings: list[dict]) -> int:
    """批量写入评论 embedding，共用一个连接和事务。"""
    rows = [
        (user_id, int(item["comment_id"]), _vector_to_sql(item["embedding"]))
        for item in embeddings
        if item.get("embedding")
    ]
    if not rows:
        return 0

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            psycopg2.extras.execute_values(
                cur,
                """UPDATE comments AS c
                   SET embedding = v.embedding::vector
                   FROM (VALUES %s) AS v(user_id, comment_id, embedding)
                   WHERE c.id = v.comment_id AND c.user_id = v.user_id""",
                rows,
                page_size=100,
            )
            updated = _execute_values_attempted_count(rows)
            conn.commit()
            _clear_cache(get_comments)
            _clear_cache(get_comments_deduped)
            return updated
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
    comment_ids: list[int] | None = None,
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


def search_comments_by_fulltext(
    user_id: int,
    query_text: str,
    comment_ids: list[int] | None = None,
    top_k: int = 20,
) -> list[dict]:
    """使用 PostgreSQL tsvector 全文检索评论（OPT-4 hybrid search 组件）。"""
    if not query_text.strip():
        return []
    if comment_ids is not None and not comment_ids:
        return []

    tsquery = " | ".join(query_text.strip().split())

    sql = (
        "SELECT *, ts_rank(content_tsv, to_tsquery('simple', %s)) AS ft_rank "
        "FROM comments WHERE user_id = %s AND content_tsv @@ to_tsquery('simple', %s)"
    )
    params: list = [tsquery, user_id, tsquery]
    if comment_ids is not None:
        sql += " AND id = ANY(%s)"
        params.append(comment_ids)
    sql += " ORDER BY ft_rank DESC LIMIT %s"
    params.append(top_k)

    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, params)
            return [dict(r) for r in cur.fetchall()]
    except (psycopg2.errors.UndefinedColumn, psycopg2.errors.UndefinedFunction):
        conn.rollback()
        return []
    finally:
        conn.close()


def get_comments(
    user_id: int,
    product_id: str | None = None,
    session_id: int | None = None,
    version: str | None = None,
    date_start: str | None = None,
    date_end: str | None = None,
    source_variant_asin: str | None = None,
    *,
    include_embedding: bool = False,
    compact_aspects_json: bool = True,
) -> list[dict]:
    try:
        query, params = _build_get_comments_query(
            user_id,
            product_id=product_id,
            session_id=session_id,
            version=version,
            date_start=date_start,
            date_end=date_end,
            source_variant_asin=source_variant_asin,
            include_embedding=include_embedding,
            compact_aspects_json=compact_aspects_json,
            use_review_date=True,
        )
        return _execute_comment_read_query(
            query,
            params,
            user_id=user_id,
            session_id=session_id,
            product_id=product_id,
            include_embedding=include_embedding,
        )
    except psycopg2.errors.UndefinedColumn:
        logger.warning("comments.review_date column unavailable; falling back to legacy date text reads")
        query, params = _build_get_comments_query(
            user_id,
            product_id=product_id,
            session_id=session_id,
            version=version,
            date_start=date_start,
            date_end=date_end,
            source_variant_asin=source_variant_asin,
            include_embedding=include_embedding,
            compact_aspects_json=compact_aspects_json,
            use_review_date=False,
        )
        return _execute_comment_read_query(
            query,
            params,
            user_id=user_id,
            session_id=session_id,
            product_id=product_id,
            include_embedding=include_embedding,
        )


def _build_get_comments_query(
    user_id: int,
    *,
    product_id: str | None = None,
    session_id: int | None = None,
    version: str | None = None,
    date_start: str | None = None,
    date_end: str | None = None,
    source_variant_asin: str | None = None,
    include_embedding: bool = False,
    compact_aspects_json: bool = True,
    use_review_date: bool = True,
) -> tuple[str, list[Any]]:
    columns = list(_COMMENT_READ_COLUMNS if use_review_date else _COMMENT_READ_COLUMNS_LEGACY)
    if compact_aspects_json:
        columns.append(_COMPACT_ASPECTS_JSON_SQL)
    else:
        columns.append("aspects_json")
    if include_embedding:
        columns.append(_COMMENT_EMBEDDING_COLUMN)
    where, params = _build_comments_where_clause(
        user_id,
        product_id=product_id,
        session_id=session_id,
        version=version,
        date_start=date_start,
        date_end=date_end,
        source_variant_asin=source_variant_asin,
        use_review_date=use_review_date,
    )
    query = f"SELECT {', '.join(columns)} FROM comments WHERE {where} ORDER BY id DESC"
    return query, params


def _execute_comment_read_query(
    query: str,
    params: list[Any],
    *,
    user_id: int,
    session_id: int | None,
    product_id: str | None,
    include_embedding: bool,
) -> list[dict]:
    last_error: Exception | None = None
    for attempt in range(2):
        conn = get_connection()
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(query, params)
                return [dict(r) for r in cur.fetchall()]
        except _COMMENT_READ_RETRY_ERRORS as exc:
            last_error = exc
            if attempt == 1:
                raise
            logger.warning(
                "get_comments read connection failed; retrying once "
                "(user_id=%s session_id=%s product_id=%s include_embedding=%s): %s",
                user_id,
                session_id,
                product_id,
                include_embedding,
                exc,
            )
        finally:
            conn.close()
    if last_error:
        raise last_error
    return []


def _build_comments_where_clause(
    user_id: int,
    *,
    product_id: str | None = None,
    session_id: int | None = None,
    version: str | None = None,
    date_start: str | None = None,
    date_end: str | None = None,
    source_variant_asin: str | None = None,
    use_review_date: bool = True,
) -> tuple[str, list[Any]]:
    clauses = ["user_id = %s"]
    params: list[Any] = [user_id]
    if product_id is not None:
        clauses.append("product_id = %s")
        params.append(product_id)
    if session_id is not None:
        clauses.append("session_id = %s")
        params.append(session_id)
    if version is not None:
        clauses.append("version = %s")
        params.append(version)
    if date_start is not None:
        clauses.append("review_date >= %s::date" if use_review_date else "date >= %s")
        params.append(date_start)
    if date_end is not None:
        clauses.append("review_date <= %s::date" if use_review_date else "date <= %s")
        params.append(date_end)
    if source_variant_asin is not None:
        clauses.append("LOWER(source_variant_asin) = LOWER(%s)")
        params.append(source_variant_asin)
    return " AND ".join(clauses), params


def get_comments_date_span(
    user_id: int,
    product_id: str | None = None,
    session_id: int | None = None,
    source_variant_asin: str | None = None,
) -> tuple[str, str]:
    """Return min/max ISO-like review dates without loading comment payloads."""
    try:
        query, params = _build_comments_date_span_query(
            user_id,
            product_id=product_id,
            session_id=session_id,
            source_variant_asin=source_variant_asin,
            use_review_date=True,
        )
        return _execute_comments_date_span_query(query, params)
    except psycopg2.errors.UndefinedColumn:
        logger.warning("comments.review_date column unavailable; falling back to legacy date span")
        query, params = _build_comments_date_span_query(
            user_id,
            product_id=product_id,
            session_id=session_id,
            source_variant_asin=source_variant_asin,
            use_review_date=False,
        )
        return _execute_comments_date_span_query(query, params)


def _build_comments_date_span_query(
    user_id: int,
    *,
    product_id: str | None = None,
    session_id: int | None = None,
    source_variant_asin: str | None = None,
    use_review_date: bool = True,
) -> tuple[str, list[Any]]:
    where, params = _build_comments_where_clause(
        user_id,
        product_id=product_id,
        session_id=session_id,
        source_variant_asin=source_variant_asin,
        use_review_date=use_review_date,
    )
    if use_review_date:
        query = f"""
            SELECT
                MIN(review_date)::text AS min_date,
                MAX(review_date)::text AS max_date
            FROM comments
            WHERE {where}
              AND review_date IS NOT NULL
        """
    else:
        query = f"""
            SELECT
                MIN(SUBSTRING(date FROM 1 FOR 10)) AS min_date,
                MAX(SUBSTRING(date FROM 1 FOR 10)) AS max_date
            FROM comments
            WHERE {where}
              AND date ~ '^[0-9]{{4}}'
        """
    return query, params


def _execute_comments_date_span_query(query: str, params: list[Any]) -> tuple[str, str]:
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(query, params)
            row = cur.fetchone()
            if not row:
                return "", ""
            return str(row.get("min_date") or ""), str(row.get("max_date") or "")
    finally:
        conn.close()


def get_comment_by_id(user_id: int, comment_id: int) -> dict | None:
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


def _comment_analysis_update_row(
    user_id: int,
    comment_id: int,
    analysis: dict,
    *,
    include_cache_fields: bool,
) -> tuple:
    base = (
        user_id,
        int(comment_id),
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
    )
    if not include_cache_fields:
        return base
    return base + (
        analysis.get("cache_hit_level"),
        analysis.get("cache_source_id"),
        analysis.get("cache_hit_source"),
    )


def _execute_comment_analysis_values(cur, rows: list[tuple], *, include_cache_fields: bool) -> int:
    if include_cache_fields:
        psycopg2.extras.execute_values(
            cur,
            """UPDATE comments AS c
               SET sentiment = v.sentiment,
                   content_sentiment = v.content_sentiment,
                   category = v.category,
                   priority = v.priority,
                   reason = v.reason,
                   improvement = v.improvement,
                   issue_tag = v.issue_tag,
                   highlight_tag = v.highlight_tag,
                   aspects_json = v.aspects_json::jsonb,
                   analyzer_version = v.analyzer_version,
                   cache_hit_level = v.cache_hit_level,
                   cache_source_id = v.cache_source_id,
                   cache_hit_source = v.cache_hit_source,
                   is_processed = 1
               FROM (VALUES %s) AS v(user_id, comment_id, sentiment, content_sentiment, category, priority,
                                      reason, improvement, issue_tag, highlight_tag, aspects_json, analyzer_version,
                                      cache_hit_level, cache_source_id, cache_hit_source)
               WHERE c.id = v.comment_id AND c.user_id = v.user_id""",
            rows,
            page_size=100,
        )
    else:
        psycopg2.extras.execute_values(
            cur,
            """UPDATE comments AS c
               SET sentiment = v.sentiment,
                   content_sentiment = v.content_sentiment,
                   category = v.category,
                   priority = v.priority,
                   reason = v.reason,
                   improvement = v.improvement,
                   issue_tag = v.issue_tag,
                   highlight_tag = v.highlight_tag,
                   aspects_json = v.aspects_json::jsonb,
                   analyzer_version = v.analyzer_version,
                   is_processed = 1
               FROM (VALUES %s) AS v(user_id, comment_id, sentiment, content_sentiment, category, priority,
                                      reason, improvement, issue_tag, highlight_tag, aspects_json, analyzer_version)
               WHERE c.id = v.comment_id AND c.user_id = v.user_id""",
            rows,
            page_size=100,
        )
    return _execute_values_attempted_count(rows)


def update_comment_analysis(user_id: int, comment_id: int, analysis: dict) -> None:
    update_comment_analysis_batch(user_id, [(comment_id, analysis)])


def update_comment_analysis_batch(
    user_id: int,
    analyses: list[tuple[int, dict]] | list[dict],
) -> int:
    """批量写入评论分析结果，共用一个连接和事务。"""
    normalized: list[tuple[int, dict]] = []
    for item in analyses:
        if isinstance(item, dict):
            normalized.append((int(item["comment_id"]), item["analysis"]))
        else:
            comment_id, analysis = item
            normalized.append((int(comment_id), analysis))
    if not normalized:
        return 0

    include_cache_fields = any(analysis.get("cache_hit_level") is not None for _, analysis in normalized)
    rows = [
        _comment_analysis_update_row(user_id, comment_id, analysis, include_cache_fields=include_cache_fields)
        for comment_id, analysis in normalized
    ]

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            if include_cache_fields:
                try:
                    updated = _execute_comment_analysis_values(cur, rows, include_cache_fields=True)
                except Exception:
                    conn.rollback()
                    fallback_rows = [
                        _comment_analysis_update_row(user_id, comment_id, analysis, include_cache_fields=False)
                        for comment_id, analysis in normalized
                    ]
                    updated = _execute_comment_analysis_values(cur, fallback_rows, include_cache_fields=False)
            else:
                updated = _execute_comment_analysis_values(cur, rows, include_cache_fields=False)
            conn.commit()
            _clear_comment_analysis_caches()
            return updated
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


def get_existing_plugin_review_keys(user_id: int, asin: str) -> set[str]:
    """返回用户对指定 ASIN 已有的 (reviewer, date) 去重键集合。

    用于 Chrome 扩展插件上传时的去重（Step 15）。
    去重键格式："{reviewer}|{date}"，与插件上传请求中的 reviewer + date 对应。
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT reviewer, date FROM comments WHERE user_id = %s AND product_id = %s",
                (user_id, asin),
            )
            return {f"{r[0] or ''}|{r[1] or ''}" for r in cur.fetchall()}
    finally:
        conn.close()


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


def reset_session_analysis(user_id: int, session_id: int) -> int:
    """重置 session 内所有评论的分析状态，返回受影响行数。"""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """UPDATE comments
                   SET is_processed = 0,
                       sentiment = NULL,
                       issue_tag = '',
                       highlight_tag = '',
                       aspects_json = NULL
                   WHERE user_id = %s AND session_id = %s""",
                (user_id, session_id),
            )
            conn.commit()
            return cur.rowcount
    finally:
        conn.close()


def get_session_embeddings(user_id: int, session_id: int) -> list[dict]:
    """获取 session 内所有带 embedding 的评论（聚类用）."""
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """SELECT id, content, rating, embedding::text
                   FROM comments
                   WHERE user_id = %s AND session_id = %s
                     AND embedding IS NOT NULL
                   ORDER BY id ASC""",
                (user_id, session_id),
            )
            rows = []
            for r in cur.fetchall():
                row = dict(r)
                emb_str = row.pop("embedding", None)
                if emb_str:
                    row["embedding"] = [float(x) for x in emb_str.strip("[]").split(",")]
                else:
                    row["embedding"] = None
                rows.append(row)
            return rows
    finally:
        conn.close()


def update_comment_cluster(
    user_id: int, comment_id: int, cluster_id: int, representative_id: int
) -> None:
    """写入单条评论的聚类结果."""
    update_comment_clusters_batch(
        user_id,
        [
            {
                "comment_id": comment_id,
                "cluster_id": cluster_id,
                "cluster_representative_id": representative_id,
            }
        ],
    )


def update_comment_clusters_batch(user_id: int, clusters: list[dict]) -> int:
    """批量写入评论聚类元数据，共用一个连接和事务。"""
    rows = [
        (
            user_id,
            int(item["comment_id"]),
            item.get("cluster_id"),
            item.get("cluster_representative_id"),
        )
        for item in clusters
    ]
    if not rows:
        return 0

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            psycopg2.extras.execute_values(
                cur,
                """UPDATE comments AS c
                   SET cluster_id = v.cluster_id,
                       cluster_representative_id = v.cluster_representative_id
                   FROM (VALUES %s) AS v(user_id, comment_id, cluster_id, cluster_representative_id)
                   WHERE c.id = v.comment_id AND c.user_id = v.user_id""",
                rows,
                page_size=100,
            )
            updated = _execute_values_attempted_count(rows)
            conn.commit()
            return updated
    finally:
        conn.close()


# ============================================================
# Cache lookup (V4-T4 Step 3)
# ============================================================


def get_analyzed_by_content_hash(
    user_id: int,
    content_hashes: list[str],
    include_global: bool = True,
    analyzer_version: str | None = None,
) -> dict[str, dict]:
    """批量按 content_hash 查找已有分析结果（L1 缓存用）.

    查询顺序：
    1) 先查用户自己的历史 comments（cache_hit_source='user'）
    2) 未命中的 content_hash 再查全局 review_pool（cache_hit_source='global'）
       —— 支持跨用户 A/B/C 上传重叠评论时复用（migration 043）

    Args:
        user_id: 当前用户 ID
        content_hashes: 待查 hash 列表
        include_global: 是否查全局 review_pool（默认 True，可关灰度）
        analyzer_version: 全局池查询时校验的分析器版本，None 不校验

    Returns:
        content_hash → {aspects_json, sentiment, source_id, cache_hit_source} 映射
        - source_id: int
          · cache_hit_source='user' → 对应 comments.id
          · cache_hit_source='global' → 对应 review_pool.id
          （用 cache_hit_source 区分来自哪张表，两个 ID 空间不重叠。）
        - cache_hit_source: 'user' | 'global'
    """
    if not content_hashes:
        return {}
    conn = get_connection()
    result: dict[str, dict] = {}
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            # ── 第一步：查用户自己历史（沿用原逻辑） ──
            cur.execute(
                """SELECT id, content_hash, sentiment, aspects_json
                   FROM comments
                   WHERE user_id = %s
                     AND content_hash = ANY(%s)
                     AND is_processed = 1
                     AND aspects_json IS NOT NULL
                     AND NOT (aspects_json ? 'analysis_error')
                   ORDER BY id DESC""",
                (user_id, content_hashes),
            )
            for row in cur.fetchall():
                h = row["content_hash"]
                if h not in result:
                    aspects_json = row["aspects_json"]
                    if isinstance(aspects_json, str):
                        aspects_json = json.loads(aspects_json)
                    result[h] = {
                        "aspects_json": aspects_json,
                        "sentiment": row["sentiment"],
                        "source_id": row["id"],
                        "cache_hit_source": "user",
                    }

            # ── 第二步：未命中的 hash 查全局 review_pool ──
            if include_global:
                missing = [h for h in content_hashes if h not in result]
                if missing:
                    if analyzer_version:
                        cur.execute(
                            """SELECT id, content_hash, sentiment, aspects_json
                               FROM review_pool
                               WHERE content_hash = ANY(%s)
                                 AND analyzed_at IS NOT NULL
                                 AND aspects_json IS NOT NULL
                                 AND NOT (aspects_json ? 'analysis_error')
                                 AND analyzer_version = %s
                               ORDER BY analyzed_at DESC""",
                            (missing, analyzer_version),
                        )
                    else:
                        cur.execute(
                            """SELECT id, content_hash, sentiment, aspects_json
                               FROM review_pool
                               WHERE content_hash = ANY(%s)
                                 AND analyzed_at IS NOT NULL
                                 AND aspects_json IS NOT NULL
                                 AND NOT (aspects_json ? 'analysis_error')
                               ORDER BY analyzed_at DESC""",
                            (missing,),
                        )
                    for row in cur.fetchall():
                        h = row["content_hash"]
                        if h not in result:
                            aspects_json = row["aspects_json"]
                            if isinstance(aspects_json, str):
                                aspects_json = json.loads(aspects_json)
                            result[h] = {
                                "aspects_json": aspects_json,
                                "sentiment": row["sentiment"],
                                "source_id": row["id"],
                                "cache_hit_source": "global",
                            }
            return result
    finally:
        conn.close()


def get_analyzed_with_embeddings(
    user_id: int, product_id: str, limit: int = 500
) -> list[dict]:
    """查询同产品下已分析且有 embedding 的评论（L3 缓存用）.

    Returns:
        list of {id, embedding, aspects_json, sentiment}
    """
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """SELECT id, embedding::text, aspects_json, sentiment
                   FROM comments
                   WHERE user_id = %s AND product_id = %s
                     AND is_processed = 1
                     AND aspects_json IS NOT NULL
                     AND embedding IS NOT NULL
                   ORDER BY id DESC
                   LIMIT %s""",
                (user_id, product_id, limit),
            )
            rows = []
            for r in cur.fetchall():
                row = dict(r)
                emb_str = row.pop("embedding", None)
                if emb_str:
                    row["embedding"] = [
                        float(x) for x in emb_str.strip("[]").split(",")
                    ]
                else:
                    row["embedding"] = None
                aspects_json = row.get("aspects_json")
                if isinstance(aspects_json, str):
                    row["aspects_json"] = json.loads(aspects_json)
                rows.append(row)
            return rows
    finally:
        conn.close()


# ============================================================
# Sessions CRUD
# ============================================================

def find_session_by_batch_hash(
    user_id: int, product_id: str, batch_hash: str
) -> dict | None:
    """查询是否已有相同 batch_hash 的 session（批次去重）。"""
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """SELECT id, product_id, auto_title, custom_title, created_at, total_reviews
                   FROM sessions
                   WHERE user_id = %s AND product_id = %s AND batch_hash = %s
                   ORDER BY created_at DESC LIMIT 1""",
                (user_id, product_id, batch_hash),
            )
            row = cur.fetchone()
            return dict(row) if row else None
    finally:
        conn.close()


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
                        workflow_purpose, product_ref_id, variant_ref_id, batch_hash)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id""",
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
                        session_data.get("batch_hash"),
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
            _clear_cache(get_sessions)
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


def get_sessions(user_id: int, product_id: str | None = None) -> list[dict]:
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


def get_session_by_id(user_id: int, session_id: int) -> dict | None:
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
            _clear_cache(get_sessions)
            _clear_cache(get_session_by_id)
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
            _clear_cache(get_sessions)
            _clear_cache(get_session_by_id)
    finally:
        conn.close()


def update_session_warnings(user_id: int, session_id: int, warnings: list[dict]) -> None:
    """写入分析告警到 sessions.warnings_json（V4-T1.6 Step 3）."""
    if not warnings:
        return
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """UPDATE sessions
                   SET warnings_json = %s
                   WHERE id = %s AND user_id = %s""",
                (psycopg2.extras.Json(warnings), session_id, user_id),
            )
            conn.commit()
            _clear_cache(get_sessions)
            _clear_cache(get_session_by_id)
    finally:
        conn.close()


def delete_session(user_id: int, session_id: int) -> None:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE upload_jobs SET session_id = NULL WHERE session_id = %s AND user_id = %s",
                (session_id, user_id),
            )
            cur.execute(
                "UPDATE action_items SET session_id = NULL WHERE session_id = %s AND user_id = %s",
                (session_id, user_id),
            )
            cur.execute(
                "DELETE FROM comments WHERE session_id = %s AND user_id = %s",
                (session_id, user_id),
            )
            cur.execute(
                "DELETE FROM sessions WHERE id = %s AND user_id = %s",
                (session_id, user_id),
            )
            conn.commit()
            _clear_cache(get_sessions)
            _clear_cache(get_session_by_id)
            _clear_cache(get_comments)
            _clear_cache(get_comments_deduped)
            _clear_cache(get_product_stats_deduped)
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
            _clear_cache(get_sessions)
            _clear_cache(get_session_by_id)
            _clear_cache(get_comments)
            _clear_cache(get_comments_deduped)
            _clear_cache(get_product_stats_deduped)
            _clear_cache(get_existing_hashes)
    finally:
        conn.close()


# ============================================================
# Settings CRUD
# ============================================================

def get_setting(user_id: int, key: str) -> str | None:
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
            _clear_cache(get_setting)
            _clear_cache(get_all_settings)
    finally:
        conn.close()


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

def get_user_by_email(email: str) -> dict | None:
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


def get_valid_reset_token(email: str, token: str) -> dict | None:
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


# ============================================================
# V4-出海-M3.2 数据主权 API 支持函数
# ============================================================

def is_user_deleted(user_id: int) -> bool:
    """检查用户是否已软删；deleted_at 列缺失时视为未删除。"""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT deleted_at FROM users WHERE id = %s", (user_id,))
            row = cur.fetchone()
            if not row:
                return True
            return row[0] is not None
    except psycopg2.errors.UndefinedColumn:
        conn.rollback()
        return False
    finally:
        conn.close()


def update_user_profile(
    user_id: int,
    *,
    username: str | None = None,
    email: str | None = None,
) -> None:
    """局部更新用户名/邮箱；至少传一个字段。"""
    if username is None and email is None:
        return
    fields: list[str] = []
    values: list[object] = []
    if username is not None:
        fields.append("username = %s")
        values.append(username)
    if email is not None:
        fields.append("email = %s")
        values.append(email)
    values.append(user_id)
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                f"UPDATE users SET {', '.join(fields)} WHERE id = %s",
                values,
            )
            conn.commit()
    finally:
        conn.close()


def update_user_occupation_tag(
    user_id: int,
    *,
    occupation_tag: str | None = None,
    status: str,
) -> None:
    """更新用户职业标签采集状态。

    该字段仅用于后续行为路径分析，不参与权限、页面内容或推送分责。
    """
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc)
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            if status == "completed":
                cur.execute(
                    """
                    UPDATE users
                    SET occupation_tag = %s,
                        occupation_tag_status = 'completed',
                        occupation_tag_collected_at = COALESCE(occupation_tag_collected_at, %s),
                        occupation_tag_updated_at = %s
                    WHERE id = %s
                    """,
                    (occupation_tag, now, now, user_id),
                )
            elif status == "skipped":
                cur.execute(
                    """
                    UPDATE users
                    SET occupation_tag = NULL,
                        occupation_tag_status = 'skipped',
                        occupation_tag_skipped_at = %s,
                        occupation_tag_updated_at = %s
                    WHERE id = %s
                    """,
                    (now, now, user_id),
                )
            else:
                raise ValueError(f"Unsupported occupation tag status: {status}")
            conn.commit()
    finally:
        conn.close()


def mark_user_login(user_id: int) -> None:
    """V4-出海-M3.5: 每次成功登录时刷新 last_login_at,并清零 inactivity_notified_at。

    - last_login_at → NOW(): retention_cleanup 靠它判定 6 个月 inactive。
    - inactivity_notified_at → NULL: 用户回归时把"已发预告"状态清零,避免下次运行
      直接把回归用户匿名化。
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE users SET last_login_at = NOW(), inactivity_notified_at = NULL WHERE id = %s",
                (user_id,),
            )
            conn.commit()
    finally:
        conn.close()


def anonymize_user(user_id: int, scrambled_password_hash: str) -> None:
    """匿名化用户主表 (GDPR/CCPA 遗忘权)。

    - username → deleted_user_{id}
    - email → NULL (释放邮箱唯一约束, 允许原邮箱再注册)
    - password_hash → 随机 bcrypt hash (无法登录)
    - api_key_encrypted / paddle_customer_id → NULL
    - plan → 'free'
    - deleted_at → NOW()

    业务数据 (sessions / comments / products) 保留 user_id, 但已无法识别真人。
    """
    anon_username = f"deleted_user_{user_id}"
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE users
                SET username = %s,
                    email = NULL,
                    password_hash = %s,
                    api_key_encrypted = NULL,
                    paddle_customer_id = NULL,
                    plan = 'free',
                    occupation_tag = NULL,
                    occupation_tag_status = 'not_required',
                    occupation_tag_collected_at = NULL,
                    occupation_tag_skipped_at = NULL,
                    occupation_tag_updated_at = NOW(),
                    deleted_at = NOW()
                WHERE id = %s
                """,
                (anon_username, scrambled_password_hash, user_id),
            )
            conn.commit()
    finally:
        conn.close()


def collect_user_data_for_export(user_id: int) -> dict:
    """聚合导出用户全部数据 (数据可携权 / GDPR Article 20 / CCPA)。

    返回结构直接对应 MeExportPayload schema。评论只返回统计计数 (可能上万条,
    单次响应会过大); 如需导出全部评论明细, 走 /downloads 或 /export 接口。
    """
    data: dict = {
        "subscription": None,
        "sessions": [],
        "products": [],
        "product_variants": [],
        "comments_count": 0,
        "actions": [],
        "trackers": [],
        "settings": [],
        "asin_watchlist": [],
    }
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            # sessions (评论批次)
            _fetch_optional(cur, data, "sessions", """
                SELECT id, product_id, version, workflow_purpose,
                       product_ref_id, variant_ref_id, created_at
                FROM sessions
                WHERE user_id = %s AND (deleted_at IS NULL)
                ORDER BY id ASC
            """, (user_id,))

            # comments 只返回计数
            try:
                cur.execute(
                    "SELECT COUNT(*) AS c FROM comments WHERE user_id = %s AND (deleted_at IS NULL)",
                    (user_id,),
                )
                row = cur.fetchone()
                data["comments_count"] = int(row["c"] or 0) if row else 0
            except (psycopg2.errors.UndefinedTable, psycopg2.errors.UndefinedColumn):
                conn.rollback()
                data["comments_count"] = 0

            # products & variants
            _fetch_optional(cur, data, "products", """
                SELECT id, parent_product_id, name, platform, category,
                       lifecycle_stage, current_version, created_at
                FROM products
                WHERE user_id = %s AND (deleted_at IS NULL)
                ORDER BY id ASC
            """, (user_id,))
            _fetch_optional(cur, data, "product_variants", """
                SELECT id, product_id, variant_sku, child_asin, color, size,
                       style, material, status, created_at
                FROM product_variants
                WHERE user_id = %s AND (deleted_at IS NULL)
                ORDER BY id ASC
            """, (user_id,))

            # actions & trackers
            _fetch_optional(cur, data, "actions", """
                SELECT id, product_id, session_id, source_tag, issue_summary,
                       owner_role, status, created_at
                FROM action_items
                WHERE user_id = %s AND (deleted_at IS NULL)
                ORDER BY id ASC
            """, (user_id,))
            _fetch_optional(cur, data, "trackers", """
                SELECT id, product_id, initial_issue, improvement_action,
                       status, created_at
                FROM review_trackers
                WHERE user_id = %s AND (deleted_at IS NULL)
                ORDER BY id ASC
            """, (user_id,))

            # settings (推送/通知配置)
            _fetch_optional(cur, data, "settings", """
                SELECT key, value, updated_at
                FROM settings
                WHERE user_id = %s
                ORDER BY key ASC
            """, (user_id,))

            # asin_watchlist
            _fetch_optional(cur, data, "asin_watchlist", """
                SELECT id, asin, marketplace, product_name, fetch_frequency,
                       last_fetched_at, status, created_at
                FROM asin_watchlist
                WHERE user_id = %s
                ORDER BY id ASC
            """, (user_id,))

            # subscription 视图 (从 users 表提取)
            cur.execute(
                "SELECT plan, paddle_customer_id, plan_locked_at FROM users WHERE id = %s",
                (user_id,),
            )
            row = cur.fetchone()
            if row:
                data["subscription"] = {
                    "plan": row.get("plan"),
                    "paddle_customer_id": row.get("paddle_customer_id"),
                    "plan_locked_at": _iso_or_none(row.get("plan_locked_at")),
                }
    finally:
        conn.close()

    # 反序列化 datetime → ISO 字符串, 便于 JSON 导出
    for key in ("sessions", "products", "product_variants", "actions", "trackers", "settings", "asin_watchlist"):
        data[key] = [_row_to_jsonable(r) for r in data[key]]
    return data


def _fetch_optional(cur, data: dict, key: str, sql: str, params: tuple) -> None:
    """执行查询, 缺表/缺列时安静降级为空列表 (老库兼容)。"""
    try:
        cur.execute(sql, params)
        data[key] = [dict(r) for r in cur.fetchall()]
    except (psycopg2.errors.UndefinedTable, psycopg2.errors.UndefinedColumn):
        cur.connection.rollback()
        data[key] = []


def _iso_or_none(value) -> str | None:
    if value is None:
        return None
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


def _row_to_jsonable(row: dict) -> dict:
    result: dict = {}
    for k, v in row.items():
        if hasattr(v, "isoformat"):
            result[k] = v.isoformat()
        else:
            result[k] = v
    return result


# ---------- V4-T4 Step 5: LLM 用量日志 ----------

MODEL_COST_PER_MILLION: dict[str, tuple[float, float]] = {
    "deepseek-chat": (1.0, 8.0),
    "gpt-4o-mini": (1.05, 4.2),
    "qwen-plus": (0.8, 2.0),
}


def _provider_from_model_name(model_name: str) -> str:
    """从 model_name 反推 provider 名称."""
    if not model_name:
        return "unknown"
    name = model_name.lower()
    if "deepseek" in name:
        return "deepseek"
    if "gpt" in name or "openai" in name:
        return "openai"
    if "qwen" in name:
        return "qwen"
    return name


def _estimate_cost_yuan(model_name: str, tokens_in: int, tokens_out: int) -> float:
    costs = MODEL_COST_PER_MILLION.get(model_name, (1.0, 8.0))
    return (tokens_in * costs[0] + tokens_out * costs[1]) / 1_000_000


def log_llm_usage(
    user_id: int,
    model_name: str,
    tokens_in: int,
    tokens_out: int,
    session_id: int | None = None,
    comment_id: int | None = None,
    sub_category: str | None = None,
    cache_hit: bool = False,
    provider: str | None = None,
) -> None:
    cost = _estimate_cost_yuan(model_name, tokens_in, tokens_out) if not cache_hit else 0.0
    if provider is None:
        provider = _provider_from_model_name(model_name)
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO llm_usage_log
                   (user_id, session_id, comment_id, model_name, tokens_in, tokens_out,
                    cost_yuan, sub_category, cache_hit, provider)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                (user_id, session_id, comment_id, model_name, tokens_in, tokens_out,
                 cost, sub_category, cache_hit, provider),
            )
            conn.commit()
    finally:
        conn.close()


def log_llm_usage_batch(
    rows: list[dict],
) -> None:
    """批量写入 LLM 用量日志（减少 DB 连接次数）."""
    if not rows:
        return
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            psycopg2.extras.execute_values(
                cur,
                """INSERT INTO llm_usage_log
                   (user_id, session_id, comment_id, model_name, tokens_in, tokens_out,
                    cost_yuan, sub_category, cache_hit, provider)
                   VALUES %s""",
                [
                    (
                        r["user_id"], r.get("session_id"), r.get("comment_id"),
                        r["model_name"], r.get("tokens_in", 0), r.get("tokens_out", 0),
                        r.get("cost_yuan", 0), r.get("sub_category"), r.get("cache_hit", False),
                        r.get("provider") or _provider_from_model_name(r.get("model_name", "")),
                    )
                    for r in rows
                ],
            )
            conn.commit()
    finally:
        conn.close()


def get_llm_usage_stats(
    user_id: int | None = None,
    days: int = 30,
) -> list[dict]:
    """聚合 LLM 用量统计（按用户 + 模型 + 日期）."""
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            where = "WHERE created_at >= NOW() - INTERVAL '%s days'"
            params: list = [days]
            if user_id is not None:
                where += " AND user_id = %s"
                params.append(user_id)
            cur.execute(
                f"""SELECT user_id, model_name, DATE(created_at) as date,
                           COUNT(*) as call_count,
                           SUM(tokens_in) as total_tokens_in,
                           SUM(tokens_out) as total_tokens_out,
                           SUM(cost_yuan) as total_cost_yuan,
                           SUM(CASE WHEN cache_hit THEN 1 ELSE 0 END) as cache_hits
                    FROM llm_usage_log
                    {where}
                    GROUP BY user_id, model_name, DATE(created_at)
                    ORDER BY date DESC, total_cost_yuan DESC""",
                params,
            )
            return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()
