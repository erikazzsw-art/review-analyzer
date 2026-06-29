from __future__ import annotations

from datetime import datetime

import psycopg2.extras
from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from pydantic import BaseModel

from backend_api.app.deps import get_current_user
from backend_api.app.schemas.products import (
    ProductSearchItem,
    ProductSearchResponse,
    ProductsResponsePayload,
    ProductVersionItem,
    ProductVersionsResponse,
)
from review_analyzer.database import get_connection
from review_analyzer.product_store import (
    create_product,
    delete_product,
    delete_variant,
    get_product_by_id,
    get_product_overview_rows,
    get_variants,
    update_product,
)

router = APIRouter(prefix="/products", tags=["products"])


class ProductCreateRequest(BaseModel):
    parent_product_id: str
    name: str | None = None
    platform: str | None = None
    category: str | None = None
    lifecycle_stage: str = "growth"
    current_version: str = "V1"
    core_selling_points: str | None = None
    main_competitors: str | None = None
    owner_role: str | None = None
    production_cycle_days: int | None = None


class ProductUpdateRequest(BaseModel):
    name: str | None = None
    platform: str | None = None
    category: str | None = None
    lifecycle_stage: str | None = None
    current_version: str | None = None
    core_selling_points: str | None = None
    main_competitors: str | None = None
    owner_role: str | None = None
    production_cycle_days: int | None = None


@router.get("", response_model=ProductsResponsePayload)
def get_products_route(
    current_user: dict = Depends(get_current_user),
) -> ProductsResponsePayload:
    items = get_product_overview_rows(int(current_user["id"]))
    return ProductsResponsePayload(
        items=items,
        total=len(items),
        generated_at=datetime.utcnow(),
    )


@router.get("/search", response_model=ProductSearchResponse)
def search_products_route(
    q: str = Query(default="", max_length=64),
    limit: int = Query(default=20, ge=1, le=50),
    current_user: dict = Depends(get_current_user),
) -> ProductSearchResponse:
    """按 parent_product_id / name 模糊匹配,用于结果页产品切换下拉框。

    排序:前缀命中优先 → 评论数降序 → 字母序。
    """
    user_id = int(current_user["id"])
    rows = get_product_overview_rows(user_id)
    q_norm = q.strip().lower()

    def _match(row: dict) -> bool:
        if not q_norm:
            return True
        pid = str(row.get("parent_product_id") or "").lower()
        name = str(row.get("name") or "").lower()
        return q_norm in pid or q_norm in name

    matched = [
        r for r in rows
        if _match(r) and int(r.get("session_count") or 0) > 0
    ]

    def _sort_key(row: dict) -> tuple:
        pid = str(row.get("parent_product_id") or "").lower()
        prefix_hit = 0 if (q_norm and pid.startswith(q_norm)) else 1
        return (
            prefix_hit,
            -int(row.get("review_count") or 0),
            pid,
        )

    matched.sort(key=_sort_key)

    items = [
        ProductSearchItem(
            parent_product_id=str(r.get("parent_product_id") or ""),
            name=(str(r.get("name") or "") or None),
            review_count=int(r.get("review_count") or 0),
            session_count=int(r.get("session_count") or 0),
            latest_session_id=None,  # latest_session_label 是字符串,不含 id;前端通过 /analysis/history 拿
        )
        for r in matched[:limit]
        if r.get("parent_product_id")
    ]
    return ProductSearchResponse(items=items, total=len(items), query=q)


@router.get("/{product_id}/versions", response_model=ProductVersionsResponse)
def list_product_versions(
    product_id: str = Path(..., min_length=1, max_length=128),
    current_user: dict = Depends(get_current_user),
) -> ProductVersionsResponse:
    """列出该产品已有的版本与各版本评论数 / 最近分析时间。

    供宣传文案、对比分析等"按版本聚合"场景使用。
    """
    user_id = int(current_user["id"])
    pid = product_id.strip()
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """
                SELECT
                    s.version AS version,
                    COALESCE(SUM(s.total_reviews), 0) AS review_count,
                    MAX(s.created_at) AS last_analyzed_at
                FROM sessions s
                WHERE s.user_id = %s AND s.product_id = %s
                GROUP BY s.version
                ORDER BY s.version ASC
                """,
                (user_id, pid),
            )
            rows = cur.fetchall()
    finally:
        conn.close()

    items = [
        ProductVersionItem(
            version=str(r["version"] or "V1"),
            review_count=int(r.get("review_count") or 0),
            last_analyzed_at=r.get("last_analyzed_at"),
        )
        for r in rows
    ]
    return ProductVersionsResponse(items=items, total=len(items), product_id=pid)


@router.post("", status_code=status.HTTP_201_CREATED)
def create_product_route(
    body: ProductCreateRequest,
    current_user: dict = Depends(get_current_user),
) -> dict:
    user_id = int(current_user["id"])
    product_id = create_product(user_id, body.model_dump(exclude_none=True))
    return {"id": product_id}


@router.patch("/{product_id}")
def update_product_route(
    product_id: int,
    body: ProductUpdateRequest,
    current_user: dict = Depends(get_current_user),
) -> dict:
    user_id = int(current_user["id"])
    existing = get_product_by_id(user_id, product_id)
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found.",
        )
    data = body.model_dump(exclude_none=True)
    if not data:
        return {"updated": False}
    updated = update_product(user_id, product_id, data)
    return {"updated": updated}


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_product_route(
    product_id: int,
    current_user: dict = Depends(get_current_user),
) -> None:
    user_id = int(current_user["id"])
    existing = get_product_by_id(user_id, product_id)
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found.",
        )
    delete_product(user_id, product_id)


@router.delete("/{product_id}/variants/{variant_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_variant_route(
    product_id: int,
    variant_id: int,
    current_user: dict = Depends(get_current_user),
) -> None:
    user_id = int(current_user["id"])
    existing = get_product_by_id(user_id, product_id)
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found.",
        )
    deleted = delete_variant(user_id, product_id, variant_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Variant not found.",
        )


@router.get("/{product_id}/detail")
def get_product_detail(
    product_id: int,
    current_user: dict = Depends(get_current_user),
) -> dict:
    """产品详情 — 返回产品完整信息 + 变体列表（含新增字段）。"""
    user_id = int(current_user["id"])
    product = get_product_by_id(user_id, product_id)
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found.",
        )
    variants = get_variants(user_id, product_id)
    return {
        "product": product,
        "variants": variants,
    }
