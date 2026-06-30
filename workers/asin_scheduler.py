"""V5-T1 Phase 1 Step 3: ASIN 定时拉取调度器

每分钟扫描 asin_watchlist 表，将到期的 active 监控项入队拉取。
同时暴露 enqueue_single_asin_fetch() 供手动「立即拉取」调用。

启动方式：python -m workers.asin_scheduler
"""
from __future__ import annotations

import logging
import time
from datetime import datetime, timezone

from workers.queue import get_queue, get_redis_connection

logger = logging.getLogger(__name__)

SCAN_INTERVAL_SECONDS = 60
LOCK_PREFIX = "asin_scheduler:lock:"
LOCK_TTL_SECONDS = 600


def enqueue_single_asin_fetch(user_id: int, item_id: int) -> str:
    """入队单条 ASIN 拉取任务（手动触发 / 调度器触发）。"""
    queue = get_queue()
    job = queue.enqueue(
        "workers.asin_scheduler.process_watchlist_fetch",
        user_id,
        item_id,
        job_id=f"asin-watch-{item_id}-{int(time.time())}",
        description=f"ASIN watchlist fetch (item {item_id})",
        result_ttl=0,
        failure_ttl=7 * 24 * 3600,
    )
    return job.id


def process_watchlist_fetch(user_id: int, item_id: int) -> None:
    """Worker 任务：拉取单条监控项的评论，增量检测，触发分析。"""
    import asyncio

    from backend_api.app.services.asin_watchlist_store import (
        get_watchlist_item_by_id,
        mark_fetch_error,
        mark_fetch_result,
    )
    from backend_api.app.services.review_scraper import ReviewScraperError, fetch_reviews

    try:
        item = get_watchlist_item_by_id(item_id)
        if not item or item["user_id"] != user_id:
            logger.warning("watchlist item %d not found or user mismatch", item_id)
            return

        asin = item["asin"]
        marketplace = item["marketplace"]

        loop = asyncio.new_event_loop()
        try:
            reviews = loop.run_until_complete(
                fetch_reviews(asin, platform="amazon", marketplace=marketplace)
            )
        finally:
            loop.close()

        new_reviews = _deduplicate_reviews(user_id, item, reviews)
        new_count = len(new_reviews)
        total_count = len(reviews)

        consecutive_empty = item.get("consecutive_empty", 0)
        if new_count == 0:
            consecutive_empty += 1
        else:
            consecutive_empty = 0

        auto_downgrade = (
            consecutive_empty >= 3 and item["fetch_frequency"] == "daily"
        )

        mark_fetch_result(
            item_id,
            new_count=new_count,
            total_count=total_count,
            consecutive_empty=consecutive_empty,
            auto_downgrade=auto_downgrade,
        )

        if new_reviews:
            _trigger_analysis(user_id, item, new_reviews)

        logger.info(
            "watchlist fetch done: item=%d asin=%s new=%d total=%d",
            item_id, asin, new_count, total_count,
        )

    except ReviewScraperError as exc:
        mark_fetch_error(item_id, f"Scraper error: {exc}")
        _notify_fetch_error(user_id, item, str(exc))
        logger.error("watchlist fetch failed: item=%d err=%s", item_id, exc)
    except Exception as exc:
        mark_fetch_error(item_id, str(exc)[:500])
        _notify_fetch_error(user_id, item, str(exc)[:200])
        logger.exception("watchlist fetch error: item=%d", item_id)
        raise


def _deduplicate_reviews(
    user_id: int, item: dict, reviews: list[dict]
) -> list[dict]:
    """基于内容 hash 去重：返回数据库中尚不存在的评论。"""
    if not reviews:
        return []

    from review_analyzer.database import get_connection

    conn = get_connection()
    try:
        product_id = item.get("product_id")
        if not product_id:
            return reviews

        contents = [r.get("content", "") for r in reviews]
        import hashlib
        hashes = [
            hashlib.md5(c.encode("utf-8")).hexdigest() for c in contents
        ]

        with conn.cursor() as cur:
            cur.execute(
                """SELECT content_hash FROM comments
                   WHERE session_id IN (
                       SELECT id FROM analysis_sessions WHERE product_id = %s
                   ) AND content_hash = ANY(%s)""",
                (product_id, hashes),
            )
            existing = {row[0] for row in cur.fetchall()}

        return [
            r for r, h in zip(reviews, hashes) if h not in existing
        ]
    except Exception:
        logger.warning("dedup failed, returning all reviews", exc_info=True)
        return reviews
    finally:
        conn.close()


def _trigger_analysis(user_id: int, item: dict, new_reviews: list[dict]) -> None:
    """将新评论入库并触发分析流水线。"""
    from review_analyzer.database import create_upload_job
    from workers.jobs import process_upload_job

    asin = item["asin"]
    marketplace = item["marketplace"]
    product_name = item.get("product_name") or f"ASIN: {asin}"

    comments_payload = [
        {
            "content": r["content"],
            "rating": r.get("rating"),
            "date": r.get("date", ""),
            "reviewer": r.get("reviewer", ""),
            "source": f"Amazon {marketplace.upper()}",
        }
        for r in new_reviews
    ]

    job_id = create_upload_job(
        user_id=user_id,
        job_data={
            "source_filename": f"auto-fetch-{asin}-{int(time.time())}",
            "status": "queued",
            "total_rows": len(comments_payload),
            "product_id": item.get("product_id"),
            "source_channel": "auto_fetch",
            "payload_json": {
                "asin": asin,
                "marketplace": marketplace,
                "comments": comments_payload,
                "product_name": product_name,
                "platform": f"Amazon {marketplace.upper()}",
                "source_channel": "auto_fetch",
                "product_id": item.get("product_id"),
            },
        },
    )
    process_upload_job(user_id, job_id)


def _notify_fetch_error(user_id: int, item: dict, error_msg: str) -> None:
    """通过用户已配置的 webhook 发送拉取异常通知（静默失败）。"""
    try:
        import json

        from review_analyzer.database import get_connection

        conn = get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT value FROM user_settings WHERE user_id = %s AND key = 'push_settings'",
                    (user_id,),
                )
                row = cur.fetchone()
        finally:
            conn.close()

        if not row:
            return
        settings = json.loads(row[0]) if isinstance(row[0], str) else row[0]
        webhook_url = settings.get("webhook_url", "")
        if not webhook_url:
            return

        asin = item.get("asin", "")
        product_name = item.get("product_name") or asin
        text = f"⚠️ ASIN 监控拉取异常\n产品：{product_name}\nASIN：{asin}\n错误：{error_msg[:100]}"

        import requests
        body = {"msg_type": "text", "content": {"text": text}}
        requests.post(webhook_url, json=body, timeout=5)
    except Exception:
        logger.debug("notify_fetch_error failed silently", exc_info=True)


def _is_fetch_due(item: dict) -> bool:
    """判断该监控项是否到了需要拉取的时间。"""
    last_fetched = item.get("last_fetched_at")
    if last_fetched is None:
        return True

    if isinstance(last_fetched, str):
        last_fetched = datetime.fromisoformat(last_fetched)
    if last_fetched.tzinfo is None:
        last_fetched = last_fetched.replace(tzinfo=timezone.utc)

    now = datetime.now(timezone.utc)
    freq = item.get("fetch_frequency", "daily")

    if freq == "daily":
        return (now - last_fetched).total_seconds() >= 23 * 3600
    elif freq == "weekly":
        return (now - last_fetched).total_seconds() >= 6.5 * 24 * 3600
    return False


def _run_schedule_scan() -> None:
    """单次扫描：获取所有到期项并入队。"""
    from backend_api.app.services.asin_watchlist_store import get_active_items_for_schedule

    redis_conn = get_redis_connection()
    enqueued = 0

    for freq in ("daily", "weekly"):
        items = get_active_items_for_schedule(freq)
        for item in items:
            if not _is_fetch_due(item):
                continue

            lock_key = f"{LOCK_PREFIX}{item['id']}"
            if not redis_conn.set(lock_key, "1", nx=True, ex=LOCK_TTL_SECONDS):
                continue

            try:
                enqueue_single_asin_fetch(item["user_id"], item["id"])
                enqueued += 1
            except Exception:
                logger.exception("failed to enqueue item %d", item["id"])

    if enqueued:
        logger.info("asin_scheduler: enqueued %d fetch jobs", enqueued)


def run_scheduler() -> None:
    """主循环：每分钟扫描一次。"""
    logger.info("asin_scheduler: started, interval=%ds", SCAN_INTERVAL_SECONDS)

    while True:
        try:
            _run_schedule_scan()
        except Exception:
            logger.exception("asin_scheduler: scan cycle error")
        time.sleep(SCAN_INTERVAL_SECONDS)


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
    )
    run_scheduler()


if __name__ == "__main__":
    main()
