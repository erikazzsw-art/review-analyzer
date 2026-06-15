"""V5-T3 Step 6: 周期推送调度器

轻量实现：每分钟扫描一次用户的周期推送配置，
到期的用户触发 periodic_digest_job 入队。

启动方式：python -m workers.scheduler
"""
from __future__ import annotations

import logging
import time
from datetime import datetime

from workers.periodic_jobs import enqueue_periodic_digest
from workers.queue import get_redis_connection

logger = logging.getLogger(__name__)

SCAN_INTERVAL_SECONDS = 60
LOCK_PREFIX = "scheduler:periodic_push:lock:"
LOCK_TTL_SECONDS = 300


def _get_due_users() -> list[dict]:
    """查询所有启用了周期推送且当前时间到期的用户配置"""
    import json

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
    """主循环：每分钟扫描一次到期用户，入队推送任务"""
    logger.info("scheduler: started, scan interval=%ds", SCAN_INTERVAL_SECONDS)
    redis_conn = get_redis_connection()

    while True:
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
            logger.exception("scheduler: scan cycle error")

        time.sleep(SCAN_INTERVAL_SECONDS)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
    run_scheduler()


if __name__ == "__main__":
    main()
