"""ASIN 监控列表 CRUD 路由。"""
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


@router.post("", response_model=list[AsinWatchlistItem], status_code=status.HTTP_201_CREATED)
def add_asins(
    req: AsinWatchlistCreate,
    current_user: dict = Depends(get_current_user),
) -> list[AsinWatchlistItem]:
    """添加 ASIN 到监控列表（支持批量，最多 20 个/次）。"""
    user_id = int(current_user["id"])
    store = _get_watchlist_db()

    current_count = store.count_watchlist(user_id)
    plan = current_user.get("plan", "free")
    limit = WATCHLIST_LIMITS.get(plan, 3)

    if current_count + len(req.asins) > limit:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"ASIN 监控上限 {limit} 个（当前 {current_count}），升级套餐解锁更多",
        )

    items = store.add_watchlist_items(
        user_id=user_id,
        asins=req.asins,
        marketplace=req.marketplace,
        fetch_frequency=req.fetch_frequency,
    )
    return items


@router.get("", response_model=AsinWatchlistResponse)
def get_watchlist(
    current_user: dict = Depends(get_current_user),
) -> AsinWatchlistResponse:
    """获取当前用户的 ASIN 监控列表。"""
    user_id = int(current_user["id"])
    store = _get_watchlist_db()
    plan = current_user.get("plan", "free")
    limit = WATCHLIST_LIMITS.get(plan, 3)

    items = store.get_watchlist(user_id)
    return AsinWatchlistResponse(
        items=items,
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
        return AsinWatchlistItem(**item)

    updated = store.update_watchlist_item(user_id, item_id, updates)
    return AsinWatchlistItem(**updated)


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
