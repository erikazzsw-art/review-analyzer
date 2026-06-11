from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends

from backend_api.app.deps import get_current_user
from backend_api.app.schemas.products import ProductsResponsePayload
from review_analyzer.product_store import get_product_overview_rows

router = APIRouter(prefix="/products", tags=["products"])


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
