from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from backend_api.app.deps import get_current_user
from backend_api.app.schemas.products import ProductsResponsePayload
from review_analyzer.product_store import (
    create_product,
    delete_product,
    get_product_by_id,
    get_product_overview_rows,
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
