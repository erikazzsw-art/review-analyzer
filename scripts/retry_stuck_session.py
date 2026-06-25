"""一次性脚本：重跑所有 stuck 状态的 upload job（断点续跑模式）。

用法：
    python scripts/retry_stuck_session.py

逻辑：
1. 查询 status='processing' 且超过 15 分钟未更新的 job
2. 对每个 job：直接调用 process_upload_job（增量写入模式下会自动跳过已处理的评论）
3. 输出结果统计
"""
from __future__ import annotations

import logging
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def main() -> None:
    import psycopg2
    import psycopg2.extras

    from review_analyzer.database import get_connection

    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """SELECT id, user_id, session_id, status, processed_rows, total_rows,
                          created_at, updated_at
                   FROM upload_jobs
                   WHERE status IN ('processing', 'queued')
                     AND updated_at < NOW() - INTERVAL '15 minutes'
                   ORDER BY id"""
            )
            stuck_jobs = [dict(row) for row in cur.fetchall()]
    finally:
        conn.close()

    if not stuck_jobs:
        logger.info("No stuck jobs found.")
        return

    logger.info("Found %d stuck jobs:", len(stuck_jobs))
    for job in stuck_jobs:
        logger.info(
            "  job_id=%d user_id=%d session_id=%s status=%s progress=%s/%s",
            job["id"], job["user_id"], job.get("session_id"),
            job["status"], job.get("processed_rows"), job.get("total_rows"),
        )

    from workers.jobs import process_upload_job

    success = 0
    failed = 0
    for job in stuck_jobs:
        logger.info("--- Retrying job %d (user %d) ---", job["id"], job["user_id"])
        try:
            process_upload_job(job["user_id"], job["id"])
            success += 1
            logger.info("Job %d completed successfully.", job["id"])
        except Exception:
            failed += 1
            logger.exception("Job %d failed:")

    logger.info("Done. success=%d failed=%d total=%d", success, failed, len(stuck_jobs))


if __name__ == "__main__":
    main()
