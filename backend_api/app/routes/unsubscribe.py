"""V4-出海-M3.3 一键退订端点。

设计原则:
- GET 而非 POST — 邮件客户端点链接就是 GET,不能要求用户先登录再 POST。
- 参数 `uid` + `token`(HMAC-SHA256(API_SESSION_SECRET, str(user_id))[:16]) 常数时间比对。
- 无效 token / 未知 user / DB 字段缺失 都 302 到前端 /unsubscribed?status=error,
  不返回 4xx —— 邮件客户端有时会预取链接做安全扫描,404/400 会污染 email server 的
  bounce 率。
- 有效 token 时 `UPDATE users SET marketing_opt_in=FALSE`。⚠️ 该字段依赖 migration 041(M2.5),
  041 前 UPDATE 会 UndefinedColumn → 记 WARNING 日志 + 302 到 status=pending,
  告诉用户"我们收到了你的退订请求,但退订机制还在部署中"。
"""

from __future__ import annotations

import logging
import os

from fastapi import APIRouter, Query
from fastapi.responses import RedirectResponse

from review_analyzer.database import get_connection
from review_analyzer.mailer import verify_unsubscribe_token

logger = logging.getLogger(__name__)

router = APIRouter(tags=["unsubscribe"])


def _frontend_base() -> str:
    """前端域名。dev 走 localhost:3000,prod 走 www.clueai-reviewlens.com。"""
    return os.environ.get("FRONTEND_BASE_URL", "https://www.clueai-reviewlens.com").rstrip("/")


def _redirect(status: str) -> RedirectResponse:
    """统一收口 302 到前端退订成功页,通过 query 传状态。"""
    return RedirectResponse(url=f"{_frontend_base()}/unsubscribed?status={status}", status_code=302)


@router.get("/unsubscribe")
def unsubscribe(
    uid: int = Query(..., description="user id, signed by token"),
    token: str = Query(..., min_length=16, max_length=16, description="HMAC token"),
) -> RedirectResponse:
    if not verify_unsubscribe_token(uid, token):
        logger.info("unsubscribe: token mismatch uid=%s", uid)
        return _redirect("error")

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE users SET marketing_opt_in = FALSE WHERE id = %s",
                (uid,),
            )
            if cur.rowcount == 0:
                logger.info("unsubscribe: user not found uid=%s", uid)
                return _redirect("error")
        conn.commit()
    except Exception as exc:  # noqa: BLE001 — UndefinedColumn 是预期路径(041 前)
        conn.rollback()
        # marketing_opt_in 字段不存在 → migration 041 尚未上线,退回 pending 而非 error,
        # 让用户知道"请求已收到,但机制还未完全上线"。
        logger.warning("unsubscribe: DB update failed uid=%s err=%s", uid, exc)
        return _redirect("pending")
    finally:
        conn.close()

    logger.info("unsubscribe: success uid=%s", uid)
    return _redirect("success")
