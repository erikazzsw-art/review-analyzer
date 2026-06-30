"""定时自动抓取评论 — CRUD 路由。"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from backend_api.app.deps import get_current_user
from backend_api.app.schemas.asin_watchlist import (
    AsinWatchlistCreate,
    AsinWatchlistItem,
    AsinWatchlistResponse,
    AsinWatchlistUpdate,
)
from review_analyzer.quota import quota_check

router = APIRouter(prefix="/asin-watchlist", tags=["asin-watchlist"])

WATCHLIST_LIMITS = {"free": 3, "pro_early": 20, "pro": 20, "team": 100}


def _get_watchlist_db():
    """懒加载避免循环导入。"""
    from backend_api.app.services import asin_watchlist_store
    return asin_watchlist_store


def _compute_hint(item: dict) -> str | None:
    """根据内部状态生成用户可见的优化提示。"""
    consecutive_empty = item.get("consecutive_empty", 0)
    retry_count = item.get("retry_count", 0)

    if consecutive_empty >= 3 and item.get("fetch_frequency") == "weekly":
        return "连续多次无新评论，已自动降频为每周"
    if retry_count >= 3:
        return "抓取暂时受阻，系统将自动重试"
    if retry_count >= 1:
        return "上次抓取未成功，系统将自动重试"
    if item.get("new_review_count", 0) == 0 and item.get("last_fetched_at"):
        if consecutive_empty >= 1:
            return "上次拉取未获取到新评论"
    return None


def _item_to_response(item: dict) -> AsinWatchlistItem:
    """将 DB 行转为对外响应，隐藏 error 状态。"""
    display_status = item.get("status", "active")
    if display_status == "error":
        display_status = "active"

    return AsinWatchlistItem(
        id=item["id"],
        platform=item.get("platform", "amazon"),
        asin=item["asin"],
        marketplace=item["marketplace"],
        product_name=item.get("product_name"),
        product_id=item.get("product_id"),
        fetch_frequency=item["fetch_frequency"],
        last_fetched_at=item.get("last_fetched_at"),
        last_review_count=item.get("last_review_count", 0),
        new_review_count=item.get("new_review_count", 0),
        status=display_status,
        hint_message=_compute_hint(item),
        created_at=item["created_at"],
    )


@router.post("", response_model=list[AsinWatchlistItem], status_code=status.HTTP_201_CREATED)
def add_asins(
    req: AsinWatchlistCreate,
    current_user: dict = Depends(get_current_user),
) -> list[AsinWatchlistItem]:
    """添加产品编码到定时抓取（支持批量，最多 20 个/次）。"""
    user_id = int(current_user["id"])
    store = _get_watchlist_db()

    current_count = store.count_watchlist(user_id)
    plan = current_user.get("plan", "free")
    limit = WATCHLIST_LIMITS.get(plan, 3)

    if current_count + len(req.product_ids) > limit:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"定时抓取上限 {limit} 个（当前 {current_count}），升级套餐解锁更多",
        )

    items = store.add_watchlist_items(
        user_id=user_id,
        product_ids=req.product_ids,
        platform=req.platform,
        marketplace=req.marketplace,
        fetch_frequency=req.fetch_frequency,
    )
    return [_item_to_response(item) for item in items]


@router.get("", response_model=AsinWatchlistResponse)
def get_watchlist(
    current_user: dict = Depends(get_current_user),
) -> AsinWatchlistResponse:
    """获取当前用户的定时抓取列表。"""
    user_id = int(current_user["id"])
    store = _get_watchlist_db()
    plan = current_user.get("plan", "free")
    limit = WATCHLIST_LIMITS.get(plan, 3)

    items = store.get_watchlist(user_id)
    return AsinWatchlistResponse(
        items=[_item_to_response(item) for item in items],
        total=len(items),
        quota_used=len(items),
        quota_limit=limit,
    )


@router.patch("/{item_id}", response_model=AsinWatchlistItem)
def update_watchlist_item(
    item_id: int,
    req: AsinWatchlistUpdate,
    current_user: dict = Depends(get_current_user),
) -> AsinWatchlistItem:
    """修改监控项（频率/状态）。"""
    user_id = int(current_user["id"])
    store = _get_watchlist_db()

    item = store.get_watchlist_item(user_id, item_id)
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="监控项不存在")

    updates = req.model_dump(exclude_none=True)
    if not updates:
        return _item_to_response(item)

    updated = store.update_watchlist_item(user_id, item_id, updates)
    return _item_to_response(updated)


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_watchlist_item(
    item_id: int,
    current_user: dict = Depends(get_current_user),
) -> None:
    """移除监控项。"""
    user_id = int(current_user["id"])
    store = _get_watchlist_db()

    item = store.get_watchlist_item(user_id, item_id)
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="监控项不存在")

    store.delete_watchlist_item(user_id, item_id)


@router.post("/{item_id}/fetch-now", response_model=dict)
def fetch_now(
    item_id: int,
    current_user: dict = Depends(get_current_user),
) -> dict:
    """立即触发一次拉取（扣配额）。"""
    user_id = int(current_user["id"])
    store = _get_watchlist_db()

    item = store.get_watchlist_item(user_id, item_id)
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="监控项不存在")

    allowed, msg = quota_check(user_id, "asin_fetch")
    if not allowed:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=msg)

    from workers.asin_scheduler import enqueue_single_asin_fetch
    job_id = enqueue_single_asin_fetch(user_id, item_id)
    return {"job_id": job_id, "message": f"已触发 {item['asin']} 拉取任务"}
