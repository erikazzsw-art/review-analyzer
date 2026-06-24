"""Ideal Profile 缓存：内存 LRU + DB 持久化。

按 (user_id, product_id, version) 缓存一次理想画像生成结果。
失效条件：该范围内 latest_comment_id 变化（用户上传了新评论并完成分析）
       或调用方显式传 force=True。

调用方负责：
- 把待用评论集合先聚合好（已按 product+version+range 过滤完）
- 传入一个 `generate_fn(review_summary) -> dict`，画像缺失时 fallback 调用 LLM
"""

from __future__ import annotations

import json
import logging
import time
from collections.abc import Callable
from typing import Any

import psycopg2.extras

from review_analyzer.database import get_connection

_LOGGER = logging.getLogger(__name__)

# 进程内热缓存（重启失效可接受）
_MEMO: dict[str, tuple[float, dict[str, Any]]] = {}
_MEMO_TTL = 60 * 30
_MEMO_MAX = 128

_VERSION_ALL = "ALL"


def _normalize_version(version: str | None) -> str:
    v = (version or "").strip()
    return v or _VERSION_ALL


def _memo_key(user_id: int, product_id: str, version: str) -> str:
    return f"{user_id}|{product_id}|{version}"


def _memo_get(key: str) -> dict[str, Any] | None:
    entry = _MEMO.get(key)
    if not entry:
        return None
    if time.time() - entry[0] >= _MEMO_TTL:
        _MEMO.pop(key, None)
        return None
    return entry[1]


def _memo_put(key: str, payload: dict[str, Any]) -> None:
    if len(_MEMO) >= _MEMO_MAX:
        oldest = min(_MEMO.items(), key=lambda kv: kv[1][0])[0]
        _MEMO.pop(oldest, None)
    _MEMO[key] = (time.time(), payload)


def get_or_generate_ideal_profile(
    *,
    user_id: int,
    product_id: str,
    version: str | None,
    comments: list[dict[str, Any]],
    generate_fn: Callable[[], dict[str, Any]],
    force: bool = False,
) -> tuple[dict[str, Any], bool]:
    """返回 (payload, cached_flag)。cached_flag=True 表示命中缓存（内存或 DB）。

    generate_fn 不接受参数；上层闭包应捕获自己的 review_summary / user_id 等。
    """
    version_key = _normalize_version(version)
    comment_ids = [int(c.get("id") or 0) for c in comments if c.get("id") is not None]
    latest_comment_id = max(comment_ids) if comment_ids else 0
    comment_count = len(comments)

    memo_key = _memo_key(user_id, product_id, version_key)
    if not force:
        memo_hit = _memo_get(memo_key)
        if memo_hit and int(memo_hit.get("latest_comment_id_at_generation") or 0) == latest_comment_id:
            _LOGGER.info("ideal_profile HIT memory user=%s product=%s version=%s", user_id, product_id, version_key)
            return memo_hit, True

        db_row = _db_get(user_id, product_id, version_key)
        if db_row and int(db_row.get("latest_comment_id_at_generation") or 0) == latest_comment_id:
            payload = dict(db_row["payload"])
            payload["latest_comment_id_at_generation"] = db_row["latest_comment_id_at_generation"]
            payload["comment_count_at_generation"] = db_row["comment_count_at_generation"]
            payload["generated_at"] = db_row.get("updated_at") or db_row.get("created_at")
            _memo_put(memo_key, payload)
            _LOGGER.info("ideal_profile HIT db user=%s product=%s version=%s", user_id, product_id, version_key)
            return payload, True

    _LOGGER.info(
        "ideal_profile MISS user=%s product=%s version=%s force=%s latest=%s",
        user_id, product_id, version_key, force, latest_comment_id,
    )
    raw = generate_fn() or {}
    payload = dict(raw)
    payload["latest_comment_id_at_generation"] = latest_comment_id
    payload["comment_count_at_generation"] = comment_count

    saved_at = _db_upsert(
        user_id=user_id,
        product_id=product_id,
        version=version_key,
        comment_count=comment_count,
        latest_comment_id=latest_comment_id,
        payload=raw,
    )
    payload["generated_at"] = saved_at
    _memo_put(memo_key, payload)
    return payload, False


def _db_get(user_id: int, product_id: str, version: str) -> dict[str, Any] | None:
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """
                SELECT payload, comment_count_at_generation,
                       latest_comment_id_at_generation, created_at, updated_at
                FROM ideal_profiles
                WHERE user_id = %s AND product_id = %s AND version = %s
                """,
                (user_id, product_id, version),
            )
            row = cur.fetchone()
            return dict(row) if row else None
    finally:
        conn.close()


def _db_upsert(
    *,
    user_id: int,
    product_id: str,
    version: str,
    comment_count: int,
    latest_comment_id: int,
    payload: dict[str, Any],
) -> Any:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO ideal_profiles
                    (user_id, product_id, version, comment_count_at_generation,
                     latest_comment_id_at_generation, payload, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s::jsonb, NOW())
                ON CONFLICT (user_id, product_id, version)
                DO UPDATE SET
                    comment_count_at_generation = EXCLUDED.comment_count_at_generation,
                    latest_comment_id_at_generation = EXCLUDED.latest_comment_id_at_generation,
                    payload = EXCLUDED.payload,
                    updated_at = NOW()
                RETURNING updated_at
                """,
                (
                    user_id,
                    product_id,
                    version,
                    comment_count,
                    latest_comment_id,
                    json.dumps(payload, ensure_ascii=False),
                ),
            )
            row = cur.fetchone()
            conn.commit()
            return row[0] if row else None
    finally:
        conn.close()
