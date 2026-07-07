"""V5-T3 Step 6: 周期推送调度器

轻量实现：每分钟扫描一次用户的周期推送配置，
到期的用户触发 periodic_digest_job 入队。

启动方式：python -m workers.scheduler
"""
from __future__ import annotations

import logging
import time
from datetime import datetime

from workers.periodic_jobs import (
    enqueue_daily_cost_digest,
    enqueue_expire_trials,
    enqueue_periodic_digest,
    enqueue_refill_monthly_credits,
    enqueue_retention_cleanup,
    enqueue_stale_job_scan,
)
from workers.queue import get_redis_connection

logger = logging.getLogger(__name__)

SCAN_INTERVAL_SECONDS = 60
STALE_SCAN_INTERVAL_SECONDS = 300
DAILY_DIGEST_HOUR = 9
DAILY_DIGEST_MINUTE = 7
# V4-出海-M3.5: 数据保留清理,业务低峰(UTC+8 03:23),避开 09:07 成本日报
RETENTION_CLEANUP_HOUR = 3
RETENTION_CLEANUP_MINUTE = 23
LOCK_PREFIX = "scheduler:periodic_push:lock:"
DAILY_DIGEST_LOCK_PREFIX = "scheduler:daily_cost_digest:lock:"
RETENTION_CLEANUP_LOCK_PREFIX = "scheduler:retention_cleanup:lock:"
CREDIT_REFILL_LOCK_PREFIX = "scheduler:credit_refill:lock:"
EXPIRE_TRIALS_LOCK_PREFIX = "scheduler:expire_trials:lock:"
LOCK_TTL_SECONDS = 300

# Credit 月度发放：每月 1 号 00:05 UTC
CREDIT_REFILL_HOUR = 0
CREDIT_REFILL_MINUTE = 5
# Trial 到期检查：每天 00:10 UTC
EXPIRE_TRIALS_HOUR = 0
EXPIRE_TRIALS_MINUTE = 10


def _get_due_users() -> list[dict]:
    """查询所有启用了周期推送且当前时间到期的用户配置"""
    import json

    import psycopg2

    from review_analyzer.database import get_connection

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT u.id AS user_id, s.value AS settings_json
                   FROM users u
                   JOIN user_settings s ON s.user_id = u.id AND s.key = 'push_settings'
                   WHERE u.is_active = true"""
            )
            rows = cur.fetchall()
    except psycopg2.errors.UndefinedTable:
        logger.warning("_get_due_users: user_settings table missing, skipping periodic push scan")
        return []
    except Exception:
        logger.exception("_get_due_users: query failed")
        return []
    finally:
        conn.close()

    due_users = []
    now = datetime.now()

    for row in rows:
        user_id = row[0]
        try:
            settings = json.loads(row[1]) if isinstance(row[1], str) else row[1]
        except (json.JSONDecodeError, TypeError):
            continue

        periodic = settings.get("periodic_push", {})
        if not periodic.get("enabled"):
            continue

        if _is_due(periodic, now):
            due_users.append({"user_id": user_id, "settings": settings})

    return due_users


def _is_due(periodic_config: dict, now: datetime) -> bool:
    """判断当前时间是否匹配用户的推送周期配置"""
    frequency = periodic_config.get("frequency", "weekly")
    push_time = periodic_config.get("time", "09:00")

    try:
        hour, minute = map(int, push_time.split(":"))
    except (ValueError, AttributeError):
        hour, minute = 9, 0

    if now.hour != hour or now.minute != minute:
        return False

    if frequency == "daily":
        return True
    elif frequency == "weekly":
        day_of_week = periodic_config.get("day_of_week", "monday")
        weekday_map = {
            "monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3,
            "friday": 4, "saturday": 5, "sunday": 6,
        }
        return now.weekday() == weekday_map.get(day_of_week, 0)
    elif frequency == "biweekly":
        day_of_week = periodic_config.get("day_of_week", "monday")
        weekday_map = {
            "monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3,
            "friday": 4, "saturday": 5, "sunday": 6,
        }
        if now.weekday() != weekday_map.get(day_of_week, 0):
            return False
        week_num = now.isocalendar()[1]
        return week_num % 2 == 0
    elif frequency == "monthly":
        day_of_month = periodic_config.get("day_of_month", 1)
        return now.day == day_of_month

    return False


def _acquire_lock(redis_conn, user_id: int) -> bool:
    """分布式锁防止重复推送（同一周期内只推一次）"""
    lock_key = f"{LOCK_PREFIX}{user_id}:{datetime.now().strftime('%Y%m%d%H%M')}"
    return bool(redis_conn.set(lock_key, "1", nx=True, ex=LOCK_TTL_SECONDS))


def run_scheduler() -> None:
    """主循环：每分钟扫描一次到期用户，入队推送任务；每 5 分钟扫描卡死任务；每天 09:07 UTC+8 推送成本日报。

    每个调度点独立 try/except，一个失败不影响其他。
    """
    logger.info("scheduler: started, scan interval=%ds, stale scan interval=%ds", SCAN_INTERVAL_SECONDS, STALE_SCAN_INTERVAL_SECONDS)
    redis_conn = get_redis_connection()
    last_stale_scan = 0.0

    while True:
        # --- 周期推送扫描 ---
        try:
            due_users = _get_due_users()
            if due_users:
                logger.info("scheduler: found %d due users", len(due_users))
            for user_config in due_users:
                user_id = user_config["user_id"]
                if not _acquire_lock(redis_conn, user_id):
                    continue
                try:
                    enqueue_periodic_digest(user_id)
                    logger.info("scheduler: enqueued periodic digest for user %d", user_id)
                except Exception:
                    logger.exception("scheduler: failed to enqueue for user %d", user_id)
        except Exception:
            logger.exception("scheduler: periodic push scan failed")

        # --- 卡死任务扫描 ---
        try:
            import time as _time
            now = _time.time()
            if now - last_stale_scan >= STALE_SCAN_INTERVAL_SECONDS:
                enqueue_stale_job_scan()
                logger.info("scheduler: enqueued stale job scan")
                last_stale_scan = now
        except Exception:
            logger.exception("scheduler: failed to enqueue stale job scan")

        # --- 每日成本日报（09:07 UTC+8，redis lock 去重）---
        try:
            now_dt = datetime.now()
            if now_dt.hour == DAILY_DIGEST_HOUR and now_dt.minute == DAILY_DIGEST_MINUTE:
                lock_key = f"{DAILY_DIGEST_LOCK_PREFIX}{now_dt.strftime('%Y%m%d')}"
                if redis_conn.set(lock_key, "1", nx=True, ex=86400):
                    enqueue_daily_cost_digest()
                    logger.info("scheduler: enqueued daily cost digest")
        except Exception:
            logger.exception("scheduler: failed to enqueue daily cost digest")

        # --- 数据保留清理（03:23 UTC+8，redis lock 去重, M3.5）---
        try:
            now_dt = datetime.now()
            if now_dt.hour == RETENTION_CLEANUP_HOUR and now_dt.minute == RETENTION_CLEANUP_MINUTE:
                lock_key = f"{RETENTION_CLEANUP_LOCK_PREFIX}{now_dt.strftime('%Y%m%d')}"
                # TTL=86400 保证同一日历日只入队一次;跨天自然过期。
                if redis_conn.set(lock_key, "1", nx=True, ex=86400):
                    enqueue_retention_cleanup()
                    logger.info("scheduler: enqueued retention cleanup")
        except Exception:
            logger.exception("scheduler: failed to enqueue retention cleanup")

        # --- Credit 月度发放（每月 1 号 00:05 UTC，redis lock 去重, M6）---
        try:
            now_dt = datetime.now()
            if (
                now_dt.day == 1
                and now_dt.hour == CREDIT_REFILL_HOUR
                and now_dt.minute == CREDIT_REFILL_MINUTE
            ):
                lock_key = f"{CREDIT_REFILL_LOCK_PREFIX}{now_dt.strftime('%Y%m')}"
                if redis_conn.set(lock_key, "1", nx=True, ex=32 * 86400):
                    enqueue_refill_monthly_credits()
                    logger.info("scheduler: enqueued monthly credit refill")
        except Exception:
            logger.exception("scheduler: failed to enqueue monthly credit refill")

        # --- Trial 到期检查（每天 00:10 UTC，redis lock 去重, M6）---
        try:
            now_dt = datetime.now()
            if now_dt.hour == EXPIRE_TRIALS_HOUR and now_dt.minute == EXPIRE_TRIALS_MINUTE:
                lock_key = f"{EXPIRE_TRIALS_LOCK_PREFIX}{now_dt.strftime('%Y%m%d')}"
                if redis_conn.set(lock_key, "1", nx=True, ex=86400):
                    enqueue_expire_trials()
                    logger.info("scheduler: enqueued trial expiry check")
        except Exception:
            logger.exception("scheduler: failed to enqueue trial expiry check")

        time.sleep(SCAN_INTERVAL_SECONDS)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
    run_scheduler()


if __name__ == "__main__":
    main()
