"""V4-出海-M3.5 数据保留策略清理 job

每天 UTC+8 03:23 由 scheduler 触发一次,顺序执行 6 块清理:

    Block 1: inactive >6m + 未通知 → 发预告邮件 + 打时间戳
    Block 2: 已通知 >90d + 仍未登录 → 匿名化 (复用 M3.2 anonymize_user)
    Block 3: deleted_at >60d → 硬删关联业务数据 (不动 review_pool)
    Block 4: review_pool >2y → 硬删全局评论池旧缓存
    Block 5: analytics_events >90d → 硬删
    Block 6: llm_usage_log >6y → 硬删
    Block 7: sessions/comments >6y AND 行 deleted_at IS NULL → 软删

设计要点:
- 每块独立 try/except,一块失败不影响其他
- 每块单独 commit,避免长事务锁热表
- 每块 log 处理条数,便于审计
- 幂等: 靠 inactivity_notified_at 字段状态机 + 只处理未到最终态的行
- 每块 SELECT 都带 LIMIT,单日处理量上限保护;下一天继续
- 单块内部 try/except: rollback 后继续下一 user,不整块中断

用户级硬删不清理 review_pool；review_pool 由独立 2 年窗口按评论日期清理。
不清理: users 表本身 (M3.2 已经把 PII 匿名化)。
"""
from __future__ import annotations

import logging
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

logger = logging.getLogger(__name__)

# 各块单次处理上限,防止某块爆量把整个 job 拖垮。到量后下一天继续。
_NOTIFY_BATCH_LIMIT = 500
_ANONYMIZE_BATCH_LIMIT = 500
_HARD_DELETE_BATCH_LIMIT = 200

# 各块的时间窗口。集中在这里,方便未来改口径不用翻代码。
_INACTIVE_THRESHOLD_MONTHS = 6
_NOTIFY_TO_ANONYMIZE_DAYS = 90
_DELETION_GRACE_DAYS = 60
_ANALYTICS_EVENTS_RETENTION_DAYS = 90
_LLM_USAGE_RETENTION_YEARS = 6
_REVIEW_POOL_RETENTION_YEARS = 2
_SESSIONS_COMMENTS_RETENTION_YEARS = 6

# Block 3 硬删的业务表,按 FK 依赖顺序: 叶子先删。review_pool 不在此列 —— 全局缓存独立保留。
_HARD_DELETE_TABLES: tuple[str, ...] = (
    "review_trackers",
    "action_items",
    "comments",
    "product_variants",
    "products",
    "sessions",
)


def _scrambled_password_hash() -> str:
    """匿名化用户用的不可用 bcrypt hash(random bytes,无法登录)。"""
    import bcrypt

    return bcrypt.hashpw(secrets.token_bytes(32), bcrypt.gensalt()).decode("utf-8")


def retention_cleanup_job() -> dict[str, Any]:
    """M3.5 清理 job 入口,由 scheduler 每天 UTC+8 03:23 触发一次。

    每块独立 try/except,一块炸不影响其他;返回结构化统计供飞书运维日报/审计使用。
    """
    started_at = datetime.now(timezone.utc)
    logger.info("retention_cleanup: starting at %s UTC", started_at.isoformat())

    results: dict[str, Any] = {
        "started_at": started_at.isoformat(),
        "blocks": {},
        "errors": [],
    }

    for name, fn in (
        ("notify_inactive", _block1_notify_inactive),
        ("anonymize_notified", _block2_anonymize_notified),
        ("hard_delete_after_grace", _block3_hard_delete_after_grace),
        ("purge_review_pool", _block4_purge_review_pool),
        ("purge_analytics_events", _block4_purge_analytics_events),
        ("purge_llm_usage_log", _block5_purge_llm_usage_log),
        ("soft_delete_stale_sessions_comments", _block6_soft_delete_stale_business_data),
    ):
        try:
            block_result = fn()
            results["blocks"][name] = block_result
            logger.info("retention_cleanup: block=%s result=%s", name, block_result)
        except Exception as exc:  # noqa: BLE001
            logger.exception("retention_cleanup: block %s crashed", name)
            results["blocks"][name] = {"ok": False, "error": str(exc)}
            results["errors"].append({"block": name, "error": str(exc)})

    results["finished_at"] = datetime.now(timezone.utc).isoformat()
    results["ok"] = len(results["errors"]) == 0
    logger.info("retention_cleanup: done, ok=%s errors=%d", results["ok"], len(results["errors"]))
    return results


# ---------------------------------------------------------------------------
# Block 1: inactive 6m + 未通知 → 发预告 + 打时间戳
# ---------------------------------------------------------------------------


def _block1_notify_inactive() -> dict[str, Any]:
    """6 个月未登录、未通知过、还没被软删的用户 → 发 inactivity_warning 邮件。

    - 发信成功 → 立即写 inactivity_notified_at = NOW() (send-first-mark-after,
      避免"标记了但邮件其实没发出去")。发信成功但写库失败的极少数情况会导致下一
      天再发一封,可接受。
    - 发信失败 → 不写时间戳,下一天再试。
    - 无 email 的用户跳过 (registered without email 的历史遗留)。
    """
    import psycopg2.extras

    from review_analyzer.database import get_connection
    from review_analyzer.mailer import send_inactivity_warning

    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                f"""
                SELECT id, username, email
                FROM users
                WHERE deleted_at IS NULL
                  AND last_login_at IS NOT NULL
                  AND last_login_at < NOW() - INTERVAL '{_INACTIVE_THRESHOLD_MONTHS} months'
                  AND inactivity_notified_at IS NULL
                  AND email IS NOT NULL
                ORDER BY last_login_at ASC
                LIMIT %s
                """,
                (_NOTIFY_BATCH_LIMIT,),
            )
            candidates = list(cur.fetchall())
    finally:
        conn.close()

    if not candidates:
        return {"ok": True, "candidates": 0, "sent": 0, "failed": 0}

    deletion_date = (datetime.now(timezone.utc) + timedelta(days=_NOTIFY_TO_ANONYMIZE_DAYS)).strftime("%Y-%m-%d")

    sent, failed = 0, 0
    for user in candidates:
        user_id = int(user["id"])
        try:
            ok, msg = send_inactivity_warning(
                to_email=str(user["email"]),
                username=str(user["username"]),
                deletion_date=deletion_date,
            )
            if not ok:
                logger.warning("block1: send_inactivity_warning failed user_id=%s msg=%s", user_id, msg)
                failed += 1
                continue

            # 邮件已发,立刻打时间戳。
            mark_conn = get_connection()
            try:
                with mark_conn.cursor() as mark_cur:
                    mark_cur.execute(
                        "UPDATE users SET inactivity_notified_at = NOW() WHERE id = %s",
                        (user_id,),
                    )
                    mark_conn.commit()
                sent += 1
            finally:
                mark_conn.close()
        except Exception:  # noqa: BLE001
            logger.exception("block1: unexpected error for user_id=%s", user_id)
            failed += 1

    return {"ok": True, "candidates": len(candidates), "sent": sent, "failed": failed}


# ---------------------------------------------------------------------------
# Block 2: 已通知 90 天 + 仍未登录 → 匿名化
# ---------------------------------------------------------------------------


def _block2_anonymize_notified() -> dict[str, Any]:
    """已发过预告、又过了 90 天还没回来登录 → 复用 M3.2 anonymize_user()。

    重新登录会把 inactivity_notified_at 清零(见 database.mark_user_login),
    所以这里不会误伤刚回归的用户。
    """
    import psycopg2.extras

    from review_analyzer.database import anonymize_user, get_connection

    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                f"""
                SELECT id FROM users
                WHERE deleted_at IS NULL
                  AND inactivity_notified_at IS NOT NULL
                  AND inactivity_notified_at < NOW() - INTERVAL '{_NOTIFY_TO_ANONYMIZE_DAYS} days'
                ORDER BY inactivity_notified_at ASC
                LIMIT %s
                """,
                (_ANONYMIZE_BATCH_LIMIT,),
            )
            candidates = [int(r["id"]) for r in cur.fetchall()]
    finally:
        conn.close()

    if not candidates:
        return {"ok": True, "candidates": 0, "anonymized": 0, "failed": 0}

    anonymized, failed = 0, 0
    for user_id in candidates:
        try:
            anonymize_user(user_id, _scrambled_password_hash())
            anonymized += 1
        except Exception:  # noqa: BLE001
            logger.exception("block2: anonymize_user failed for user_id=%s", user_id)
            failed += 1

    return {"ok": True, "candidates": len(candidates), "anonymized": anonymized, "failed": failed}


# ---------------------------------------------------------------------------
# Block 3: deleted_at 超过 60 天宽限期 → 硬删关联业务数据
# ---------------------------------------------------------------------------


def _block3_hard_delete_after_grace() -> dict[str, Any]:
    """删除 60 天窗口过后,清空该 user_id 的业务数据。

    - 表清单见 _HARD_DELETE_TABLES,按 FK 叶子→根顺序删,避免 FK 冲突
    - review_pool 不删(无 PII、纯抓取缓存,还能给其他用户复用)
    - users 表本身不删(M3.2 已经把 PII 匿名化,保留主键防止业务侧
      LEFT JOIN 出现悬垂 user_id 展示成 "unknown")
    """
    import psycopg2.extras

    from review_analyzer.database import get_connection

    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                f"""
                SELECT id FROM users
                WHERE deleted_at IS NOT NULL
                  AND deleted_at < NOW() - INTERVAL '{_DELETION_GRACE_DAYS} days'
                ORDER BY deleted_at ASC
                LIMIT %s
                """,
                (_HARD_DELETE_BATCH_LIMIT,),
            )
            candidates = [int(r["id"]) for r in cur.fetchall()]
    finally:
        conn.close()

    if not candidates:
        return {"ok": True, "candidates": 0, "users_purged": 0, "rows_deleted": 0}

    total_rows_deleted = 0
    users_purged = 0
    users_failed = 0

    for user_id in candidates:
        conn = get_connection()
        try:
            with conn.cursor() as cur:
                rows_for_user = 0
                for table in _HARD_DELETE_TABLES:
                    # 表名来自模块常量,不含用户输入,直接拼接安全。
                    cur.execute(f"DELETE FROM {table} WHERE user_id = %s", (user_id,))  # noqa: S608
                    rows_for_user += cur.rowcount
                conn.commit()
                total_rows_deleted += rows_for_user
                users_purged += 1
                logger.info("block3: hard-deleted user_id=%s rows=%d", user_id, rows_for_user)
        except Exception:  # noqa: BLE001
            logger.exception("block3: hard delete failed for user_id=%s", user_id)
            try:
                conn.rollback()
            except Exception:  # noqa: BLE001
                pass
            users_failed += 1
        finally:
            conn.close()

    return {
        "ok": True,
        "candidates": len(candidates),
        "users_purged": users_purged,
        "users_failed": users_failed,
        "rows_deleted": total_rows_deleted,
    }


# ---------------------------------------------------------------------------
# Block 4: review_pool > 2 年 → 硬删全局评论池旧缓存
# ---------------------------------------------------------------------------


def _review_pool_recent_date_sql() -> str:
    return "substring(review_date from '^[0-9]{4}-[0-9]{2}-[0-9]{2}')::date >= CURRENT_DATE - INTERVAL '2 years'"


def _review_pool_stale_date_sql() -> str:
    return (
        "substring(review_date from '^[0-9]{4}-[0-9]{2}-[0-9]{2}') IS NULL "
        "OR substring(review_date from '^[0-9]{4}-[0-9]{2}-[0-9]{2}')::date < CURRENT_DATE - INTERVAL '2 years'"
    )


def _block4_purge_review_pool() -> dict[str, Any]:
    """全局评论池只保留最近 2 年、日期可解析的评论缓存。"""
    from review_analyzer.database import get_connection

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(f"DELETE FROM review_pool WHERE {_review_pool_stale_date_sql()}")
            deleted = cur.rowcount
            cur.execute(
                f"""UPDATE review_pool_meta m
                    SET total_reviews = COALESCE(r.total_reviews, 0),
                        last_scraped_at = COALESCE(r.last_scraped_at, m.last_scraped_at)
                    FROM (
                        SELECT platform, product_key, marketplace,
                               COUNT(*) AS total_reviews,
                               MAX(scraped_at) AS last_scraped_at
                        FROM review_pool
                        WHERE {_review_pool_recent_date_sql()}
                        GROUP BY platform, product_key, marketplace
                    ) r
                    WHERE m.platform = r.platform
                      AND m.product_key = r.product_key
                      AND m.marketplace = r.marketplace"""
            )
            cur.execute(
                """UPDATE review_pool_meta m
                   SET total_reviews = 0
                   WHERE NOT EXISTS (
                       SELECT 1
                       FROM review_pool p
                       WHERE p.platform = m.platform
                         AND p.product_key = m.product_key
                         AND p.marketplace = m.marketplace
                   )"""
            )
            conn.commit()
    finally:
        conn.close()
    return {"ok": True, "deleted": deleted}


# ---------------------------------------------------------------------------
# Block 5: analytics_events > 90 天 → 硬删
# ---------------------------------------------------------------------------


def _block4_purge_analytics_events() -> dict[str, Any]:
    """埋点事件只保留 90 天,超过就 DELETE。表无 deleted_at,只能硬删。"""
    from review_analyzer.database import get_connection

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                f"DELETE FROM analytics_events WHERE created_at < NOW() - INTERVAL '{_ANALYTICS_EVENTS_RETENTION_DAYS} days'"
            )
            deleted = cur.rowcount
            conn.commit()
    finally:
        conn.close()
    return {"ok": True, "deleted": deleted}


# ---------------------------------------------------------------------------
# Block 5: llm_usage_log > 6 年 → 硬删
# ---------------------------------------------------------------------------


def _block5_purge_llm_usage_log() -> dict[str, Any]:
    """LLM 调用日志保留 6 年(对齐 Shulex),超过就 DELETE。"""
    from review_analyzer.database import get_connection

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                f"DELETE FROM llm_usage_log WHERE created_at < NOW() - INTERVAL '{_LLM_USAGE_RETENTION_YEARS} years'"
            )
            deleted = cur.rowcount
            conn.commit()
    finally:
        conn.close()
    return {"ok": True, "deleted": deleted}


# ---------------------------------------------------------------------------
# Block 6: sessions/comments > 6 年 + 行 deleted_at IS NULL → 软删
# ---------------------------------------------------------------------------


def _block6_soft_delete_stale_business_data() -> dict[str, Any]:
    """老化的 sessions/comments 只软删,不清物理行。

    - 只处理 deleted_at IS NULL 的活行,避免重复标记
    - 软删而非硬删的原因: 用户账号还活着,老数据可能对未来 embedding 复用/审计
      有用;实际物理清理等冷存储方案(见 plan 里"冷热分层缓冲方案")上线再做
    - Block 3 走用户级 60 天硬删链路,这里的软删和那条链路不重叠
    """
    from review_analyzer.database import get_connection

    results = {}
    for table in ("sessions", "comments"):
        conn = get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    # 表名来自代码常量,无 SQL 注入风险
                    f"""
                    UPDATE {table}
                    SET deleted_at = NOW()
                    WHERE deleted_at IS NULL
                      AND created_at < NOW() - INTERVAL '{_SESSIONS_COMMENTS_RETENTION_YEARS} years'
                    """  # noqa: S608
                )
                results[table] = cur.rowcount
                conn.commit()
        finally:
            conn.close()
    return {"ok": True, **results}
