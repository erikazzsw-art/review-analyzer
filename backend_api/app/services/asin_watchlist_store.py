"""定时自动抓取评论 — 数据存储层。"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from review_analyzer.database import get_connection

logger = logging.getLogger(__name__)


def count_watchlist(user_id: int) -> int:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT COUNT(*) FROM asin_watchlist WHERE user_id = %s",
                (user_id,),
            )
            return cur.fetchone()[0]
    finally:
        conn.close()


def add_watchlist_items(
    user_id: int,
    product_ids: list[str],
    platform: str,
    marketplace: str,
    fetch_frequency: str,
) -> list[dict[str, Any]]:
    conn = get_connection()
    results = []
    try:
        with conn.cursor() as cur:
            for pid in product_ids:
                cur.execute(
                    """INSERT INTO asin_watchlist
                           (user_id, asin, platform, marketplace, fetch_frequency)
                       VALUES (%s, %s, %s, %s, %s)
                       ON CONFLICT (user_id, platform, asin, marketplace) DO UPDATE
                         SET status = 'active', fetch_frequency = EXCLUDED.fetch_frequency,
                             retry_count = 0, updated_at = NOW()
                       RETURNING id, asin, platform, marketplace, product_name, product_id,
                                 fetch_frequency, last_fetched_at, last_review_count,
                                 new_review_count, status, error_message, retry_count,
                                 consecutive_empty, created_at""",
                    (user_id, pid, platform, marketplace, fetch_frequency),
                )
                row = cur.fetchone()
                results.append(_row_to_dict(row, cur.description))
        conn.commit()
    finally:
        conn.close()

    if platform == "amazon":
        _async_fetch_product_names(user_id, results, marketplace)
    return results


def get_watchlist(user_id: int) -> list[dict[str, Any]]:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT id, asin, platform, marketplace, product_name, product_id,
                          fetch_frequency, last_fetched_at, last_review_count,
                          new_review_count, status, error_message, retry_count,
                          consecutive_empty, created_at
                   FROM asin_watchlist
                   WHERE user_id = %s
                   ORDER BY created_at DESC""",
                (user_id,),
            )
            return [_row_to_dict(row, cur.description) for row in cur.fetchall()]
    finally:
        conn.close()


def get_watchlist_item(user_id: int, item_id: int) -> dict[str, Any] | None:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT id, asin, platform, marketplace, product_name, product_id,
                          fetch_frequency, last_fetched_at, last_review_count,
                          new_review_count, status, error_message, retry_count,
                          consecutive_empty, created_at
                   FROM asin_watchlist
                   WHERE id = %s AND user_id = %s""",
                (item_id, user_id),
            )
            row = cur.fetchone()
            return _row_to_dict(row, cur.description) if row else None
    finally:
        conn.close()


def get_watchlist_item_by_id(item_id: int) -> dict[str, Any] | None:
    """按 ID 获取监控项（调度器内部用，含 user_id 字段）。"""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT id, user_id, asin, platform, marketplace, product_name,
                          product_id, fetch_frequency, last_fetched_at,
                          last_review_count, new_review_count, status, error_message,
                          retry_count, consecutive_empty, created_at
                   FROM asin_watchlist
                   WHERE id = %s""",
                (item_id,),
            )
            row = cur.fetchone()
            return _row_to_dict(row, cur.description) if row else None
    finally:
        conn.close()


def update_watchlist_item(
    user_id: int, item_id: int, updates: dict[str, Any]
) -> dict[str, Any]:
    updates["updated_at"] = datetime.now(timezone.utc)
    set_clauses = ", ".join(f"{k} = %s" for k in updates)
    values = list(updates.values())

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                f"""UPDATE asin_watchlist SET {set_clauses}
                    WHERE id = %s AND user_id = %s
                    RETURNING id, asin, platform, marketplace, product_name, product_id,
                              fetch_frequency, last_fetched_at, last_review_count,
                              new_review_count, status, error_message, retry_count,
                              consecutive_empty, created_at""",
                values + [item_id, user_id],
            )
            row = cur.fetchone()
        conn.commit()
        return _row_to_dict(row, cur.description)
    finally:
        conn.close()


def delete_watchlist_item(user_id: int, item_id: int) -> None:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM asin_watchlist WHERE id = %s AND user_id = %s",
                (item_id, user_id),
            )
        conn.commit()
    finally:
        conn.close()


def get_active_items_for_schedule(frequency: str) -> list[dict[str, Any]]:
    """获取所有需要定时拉取的活跃监控项（调度器用）。"""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT w.id, w.user_id, w.asin, w.platform, w.marketplace,
                          w.product_name, w.product_id, w.last_fetched_at,
                          w.last_review_count, w.consecutive_empty, w.fetch_frequency
                   FROM asin_watchlist w
                   JOIN users u ON u.id = w.user_id AND u.is_active = true
                   WHERE w.status = 'active' AND w.fetch_frequency = %s
                   ORDER BY w.last_fetched_at ASC NULLS FIRST""",
                (frequency,),
            )
            return [_row_to_dict(row, cur.description) for row in cur.fetchall()]
    finally:
        conn.close()


def mark_fetch_result(
    item_id: int,
    new_count: int,
    total_count: int,
    consecutive_empty: int,
    auto_downgrade: bool = False,
) -> None:
    """拉取完成后更新监控项状态。"""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            updates = {
                "last_fetched_at": datetime.now(timezone.utc),
                "last_review_count": total_count,
                "new_review_count": new_count,
                "consecutive_empty": consecutive_empty,
                "retry_count": 0,
                "status": "active",
                "error_message": None,
                "updated_at": datetime.now(timezone.utc),
            }
            if auto_downgrade:
                updates["fetch_frequency"] = "weekly"

            set_clauses = ", ".join(f"{k} = %s" for k in updates)
            cur.execute(
                f"UPDATE asin_watchlist SET {set_clauses} WHERE id = %s",
                list(updates.values()) + [item_id],
            )
        conn.commit()
    finally:
        conn.close()


def mark_fetch_retry(item_id: int, error_msg: str) -> None:
    """抓取失败时静默重试：不改 status，只增加 retry_count。"""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """UPDATE asin_watchlist
                   SET retry_count = retry_count + 1,
                       error_message = %s,
                       updated_at = NOW()
                   WHERE id = %s""",
                (error_msg, item_id),
            )
        conn.commit()
    finally:
        conn.close()


def update_product_name(item_id: int, product_name: str) -> None:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE asin_watchlist SET product_name = %s, updated_at = NOW() WHERE id = %s",
                (product_name, item_id),
            )
        conn.commit()
    finally:
        conn.close()


def _row_to_dict(row: tuple, description) -> dict[str, Any]:
    return {col.name: val for col, val in zip(description, row)}


def _async_fetch_product_names(
    user_id: int, items: list[dict], marketplace: str
) -> None:
    """后台获取产品名（非阻塞，失败不影响主流程）。"""
    try:
        from workers.queue import get_queue
        queue = get_queue()
        for item in items:
            if not item.get("product_name"):
                queue.enqueue(
                    _fetch_and_update_product_name,
                    item["id"],
                    item["asin"],
                    marketplace,
                    job_id=f"product-name-{item['id']}",
                    result_ttl=0,
                    failure_ttl=3600,
                )
    except Exception:
        logger.warning("Failed to enqueue product name fetch", exc_info=True)


def _fetch_and_update_product_name(item_id: int, asin: str, marketplace: str) -> None:
    """Worker job: 获取产品名并更新。"""
    import asyncio

    from backend_api.app.services.rainforest import fetch_product_info

    loop = asyncio.new_event_loop()
    try:
        info = loop.run_until_complete(fetch_product_info(asin, marketplace=marketplace))
        title = info.get("title", "")
        if title:
            update_product_name(item_id, title)
    except Exception:
        logger.warning("Failed to fetch product name for ASIN %s", asin, exc_info=True)
    finally:
        loop.close()
