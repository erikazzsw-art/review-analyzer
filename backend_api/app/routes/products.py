from __future__ import annotations

import re
import unicodedata
from datetime import datetime
from difflib import SequenceMatcher

import psycopg2.extras
from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from pydantic import BaseModel

from backend_api.app.deps import get_current_user
from backend_api.app.schemas.products import (
    PluginListingUploadRequest,
    ProductSearchItem,
    ProductSearchResponse,
    ProductSearchVariantItem,
    ProductsResponsePayload,
    ProductVersionItem,
    ProductVersionsResponse,
)
from review_analyzer.database import get_connection
from review_analyzer.product_store import (
    ProductParentNameConflictError,
    create_product,
    delete_product,
    delete_variant,
    get_parent_variant_analysis,
    get_product_by_id,
    get_product_by_parent_id,
    get_product_listing_by_product_id,
    get_product_overview_rows,
    get_variants_with_review_counts,
    move_variant_to_parent,
    plugin_upload_listing,
    update_product,
    upsert_manual_variant,
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
    parent_product_id: str | None = None
    name: str | None = None
    platform: str | None = None
    category: str | None = None
    lifecycle_stage: str | None = None
    current_version: str | None = None
    core_selling_points: str | None = None
    main_competitors: str | None = None
    owner_role: str | None = None
    production_cycle_days: int | None = None


class ProductImportRow(BaseModel):
    row_number: int | None = None
    product_name: str | None = None
    platform: str | None = None
    category: str | None = None
    lifecycle_stage: str | None = None
    current_version: str | None = None
    core_selling_points: str | None = None
    main_competitors: str | None = None
    owner_role: str | None = None
    production_cycle_days: int | None = None
    child_asin: str | None = None
    variant_sku: str | None = None
    variant_name: str | None = None
    color: str | None = None
    size: str | None = None
    style: str | None = None
    material: str | None = None
    status: str | None = None
    launched_at: str | None = None
    image_url: str | None = None
    brand: str | None = None
    price: float | None = None
    price_currency: str | None = None
    sales_volume: int | None = None
    sales_revenue: float | None = None
    is_fba: bool | None = None
    listing_date: str | None = None


class ProductImportRequest(BaseModel):
    rows: list[ProductImportRow]


def _visible_product_rows(rows: list[dict]) -> list[dict]:
    return [
        row
        for row in rows
        if row.get("id") is not None and not row.get("is_archived_from_sessions")
    ]


def _normalize_product_lookup(value: object) -> str:
    text = unicodedata.normalize("NFKC", str(value or "")).casefold()
    return re.sub(r"[\W_]+", "", text, flags=re.UNICODE)


def _product_similarity(query: str, value: str) -> float:
    q_norm = _normalize_product_lookup(query)
    value_norm = _normalize_product_lookup(value)
    if not q_norm or not value_norm:
        return 0.0
    if q_norm == value_norm:
        return 1.0
    if q_norm in value_norm or value_norm in q_norm:
        return 0.92 * min(len(q_norm), len(value_norm)) / max(len(q_norm), len(value_norm))
    return SequenceMatcher(None, q_norm, value_norm).ratio()


def _clean_text(value: object) -> str | None:
    text = str(value or "").strip()
    return text or None


def _product_import_data(row: ProductImportRow) -> dict:
    product_name = _clean_text(row.product_name)
    data = {
        "parent_product_id": product_name,
        "name": product_name,
        "platform": _clean_text(row.platform) or "Amazon",
        "category": _clean_text(row.category),
        "lifecycle_stage": _clean_text(row.lifecycle_stage) or "growth",
        "current_version": _clean_text(row.current_version) or "V1",
        "core_selling_points": _clean_text(row.core_selling_points),
        "main_competitors": _clean_text(row.main_competitors),
        "owner_role": _clean_text(row.owner_role),
        "production_cycle_days": row.production_cycle_days,
    }
    return {key: value for key, value in data.items() if value is not None}


def _variant_import_data(row: ProductImportRow, platform: str | None) -> dict:
    data = {
        "child_asin": _clean_text(row.child_asin),
        "variant_sku": _clean_text(row.variant_sku) or _clean_text(row.child_asin),
        "name": _clean_text(row.variant_name),
        "platform": _clean_text(row.platform) or platform,
        "color": _clean_text(row.color),
        "size": _clean_text(row.size),
        "style": _clean_text(row.style),
        "material": _clean_text(row.material),
        "status": _clean_text(row.status) or "active",
        "launched_at": _clean_text(row.launched_at),
        "image_url": _clean_text(row.image_url),
        "brand": _clean_text(row.brand),
        "price": row.price,
        "price_currency": _clean_text(row.price_currency),
        "sales_volume": row.sales_volume,
        "sales_revenue": row.sales_revenue,
        "is_fba": row.is_fba,
        "listing_date": _clean_text(row.listing_date),
    }
    return {key: value for key, value in data.items() if value is not None}


@router.get("", response_model=ProductsResponsePayload)
def get_products_route(
    current_user: dict = Depends(get_current_user),
) -> ProductsResponsePayload:
    items = _visible_product_rows(get_product_overview_rows(int(current_user["id"])))
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
    """按父体名称 / 子变体 ASIN / 子变体产品名称模糊匹配,用于产品切换搜索框。

    排序:精确命中优先 → 前缀命中优先 → 评论数降序 → 字母序。
    """
    user_id = int(current_user["id"])
    rows = _visible_product_rows(get_product_overview_rows(user_id))
    q_raw = q.strip()
    q_lower = q_raw.lower()
    q_norm = _normalize_product_lookup(q_raw)

    def _variant_values(row: dict) -> list[str]:
        values: list[str] = []
        seen: set[str] = set()
        for variant in row.get("variants") or []:
            if not isinstance(variant, dict):
                continue
            for key in ("child_asin", "variant_sku", "name"):
                value = str(variant.get(key) or "").strip()
                if value and value.lower() not in seen:
                    seen.add(value.lower())
                    values.append(value)
        return values

    def _search_values(row: dict) -> list[str]:
        return [
            str(row.get("parent_product_id") or "").strip(),
            str(row.get("name") or "").strip(),
            *_variant_values(row),
        ]

    def _variant_asins(row: dict) -> list[str]:
        asins: list[str] = []
        seen: set[str] = set()
        for variant in row.get("variants") or []:
            if not isinstance(variant, dict):
                continue
            asin = str(variant.get("child_asin") or "").strip()
            if asin and asin.lower() not in seen:
                seen.add(asin.lower())
                asins.append(asin)
        return asins

    def _variant_items(row: dict) -> list[ProductSearchVariantItem]:
        items: list[ProductSearchVariantItem] = []
        seen: set[str] = set()
        for variant in row.get("variants") or []:
            if not isinstance(variant, dict):
                continue
            asin = str(variant.get("child_asin") or "").strip()
            if not asin or asin.lower() in seen:
                continue
            seen.add(asin.lower())
            items.append(
                ProductSearchVariantItem(
                    child_asin=asin,
                    name=(str(variant.get("name") or variant.get("variant_sku") or "") or None),
                )
            )
        return items

    def _match(row: dict) -> bool:
        if not q_raw:
            return True
        for value in _search_values(row):
            if q_lower in value.lower():
                return True
            if len(q_norm) >= 4 and _product_similarity(q_raw, value) >= 0.82:
                return True
        return False

    matched = [r for r in rows if _match(r)]

    def _sort_key(row: dict) -> tuple:
        values = [value for value in _search_values(row) if value]
        lower_values = [value.lower() for value in values]
        norm_values = [_normalize_product_lookup(value) for value in values]
        exact_hit = 0 if (q_lower and any(value == q_lower for value in lower_values)) else 1
        normalized_hit = 0 if (q_norm and any(value == q_norm for value in norm_values)) else 1
        prefix_hit = 0 if (q_lower and any(value.startswith(q_lower) for value in lower_values)) else 1
        normalized_prefix_hit = 0 if (q_norm and any(value.startswith(q_norm) for value in norm_values)) else 1
        best_similarity = max((_product_similarity(q_raw, value) for value in values), default=0.0)
        pid = str(row.get("parent_product_id") or "").lower()
        return (
            exact_hit,
            normalized_hit,
            prefix_hit,
            normalized_prefix_hit,
            -best_similarity,
            -int(row.get("review_count") or 0),
            pid,
        )

    matched.sort(key=_sort_key)

    items = [
        ProductSearchItem(
            id=r.get("id"),
            parent_product_id=str(r.get("parent_product_id") or ""),
            name=(str(r.get("name") or "") or None),
            variant_asins=_variant_asins(r),
            variants=_variant_items(r),
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
    data = body.model_dump(exclude_none=True)
    parent_product_id = str(data.get("parent_product_id") or "").strip()
    if not parent_product_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="产品名称不能为空。",
        )
    data["parent_product_id"] = parent_product_id
    data["name"] = parent_product_id
    product_id = create_product(user_id, data)
    return {"id": product_id}


@router.post("/import", status_code=status.HTTP_200_OK)
def import_products_route(
    body: ProductImportRequest,
    current_user: dict = Depends(get_current_user),
) -> dict:
    """批量导入产品和子 ASIN 变体。"""
    user_id = int(current_user["id"])
    if not body.rows:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="导入表格为空。",
        )

    product_ids: dict[str, int] = {}
    products_created = 0
    products_updated = 0
    variants_created = 0
    variants_updated = 0
    variants_skipped = 0
    errors: list[dict[str, object]] = []

    for index, row in enumerate(body.rows, start=1):
        row_number = row.row_number or index + 1
        product_name = _clean_text(row.product_name)
        if not product_name:
            errors.append({"row": row_number, "detail": "产品名称不能为空。"})
            continue

        try:
            product_data = _product_import_data(row)
            if product_name in product_ids:
                product_id = product_ids[product_name]
            else:
                existing = get_product_by_parent_id(user_id, product_name)
                if existing:
                    product_id = int(existing["id"])
                    update_payload = {
                        key: value
                        for key, value in product_data.items()
                        if key not in {"parent_product_id", "name"}
                    }
                    if update_payload and update_product(user_id, product_id, update_payload):
                        products_updated += 1
                else:
                    product_id = create_product(user_id, product_data)
                    products_created += 1
                product_ids[product_name] = product_id

            if not _clean_text(row.child_asin):
                variants_skipped += 1
                continue

            variant_result = upsert_manual_variant(
                user_id,
                product_id,
                _variant_import_data(row, _clean_text(row.platform) or product_data.get("platform")),
            )
            if variant_result.get("action") == "created":
                variants_created += 1
            else:
                variants_updated += 1
        except (ProductParentNameConflictError, ValueError) as exc:
            errors.append({"row": row_number, "detail": str(exc)})

    return {
        "ok": len(errors) == 0,
        "total_rows": len(body.rows),
        "products_created": products_created,
        "products_updated": products_updated,
        "variants_created": variants_created,
        "variants_updated": variants_updated,
        "variants_skipped": variants_skipped,
        "errors": errors,
    }


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
    if "parent_product_id" in data:
        parent_product_id = str(data["parent_product_id"]).strip()
        if not parent_product_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="产品名称不能为空。",
            )
        data["parent_product_id"] = parent_product_id
        if "name" in data:
            data["name"] = str(data["name"] or "").strip() or parent_product_id
        else:
            data["name"] = parent_product_id
    elif "name" in data:
        name = str(data["name"] or "").strip()
        if not name:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="产品名称不能为空。",
            )
        data["name"] = name
    if not data:
        return {"updated": False}
    try:
        updated = update_product(user_id, product_id, data)
    except ProductParentNameConflictError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
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
    analysis = get_parent_variant_analysis(user_id, product_id)
    product = dict(product)
    product["review_count"] = int(analysis.get("total_reviews") or 0)
    variants = get_variants_with_review_counts(user_id, product_id)
    listing = get_product_listing_by_product_id(user_id, product_id)
    return {
        "product": product,
        "variants": variants,
        "listing": listing,
    }


# ── 5.8.2: 父变体 & 子 ASIN 管理 ──


class AddVariantRequest(BaseModel):
    child_asin: str
    variant_sku: str | None = None
    name: str | None = None
    platform: str | None = None
    color: str | None = None
    size: str | None = None
    style: str | None = None
    material: str | None = None
    brand: str | None = None
    price: float | None = None
    price_currency: str | None = None
    sales_volume: int | None = None
    sales_revenue: float | None = None
    is_fba: bool | None = None
    listing_date: str | None = None
    launched_at: str | None = None
    status: str | None = None
    image_url: str | None = None


class MoveVariantRequest(BaseModel):
    target_product_id: int


@router.post("/{product_id}/variants", status_code=status.HTTP_201_CREATED)
def add_variant_route(
    product_id: int,
    body: AddVariantRequest,
    current_user: dict = Depends(get_current_user),
) -> dict:
    """手动添加子 ASIN 变体到父产品。"""
    user_id = int(current_user["id"])
    existing = get_product_by_id(user_id, product_id)
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found.",
        )
    data = body.model_dump(exclude_none=True)
    data["variant_sku"] = data.get("variant_sku") or body.child_asin
    data["platform"] = data.get("platform") or existing.get("platform")
    try:
        result = upsert_manual_variant(user_id, product_id, data)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    return result


@router.patch("/{product_id}/variants/{variant_id}/move")
def move_variant_route(
    product_id: int,
    variant_id: int,
    body: MoveVariantRequest,
    current_user: dict = Depends(get_current_user),
) -> dict:
    """将变体移动到另一个父产品下。"""
    user_id = int(current_user["id"])
    result = move_variant_to_parent(user_id, variant_id, body.target_product_id)
    if not result.get("success"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.get("message", "移动失败"),
        )
    return result


@router.get("/{product_id}/parent-analysis")
def get_parent_analysis_route(
    product_id: int,
    current_user: dict = Depends(get_current_user),
) -> dict:
    """父变体整体分析 — 聚合当前用户所有子 ASIN 的分析数据。"""
    user_id = int(current_user["id"])
    existing = get_product_by_id(user_id, product_id)
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found.",
        )
    analysis = get_parent_variant_analysis(user_id, product_id)
    return {
        "product": existing,
        "analysis": analysis,
    }


# ── Step 11.5: Chrome 插件 Listing 上传 ──


@router.post("/plugin-upload", status_code=status.HTTP_200_OK)
def plugin_upload_listing_route(
    body: PluginListingUploadRequest,
    current_user: dict = Depends(get_current_user),
) -> dict:
    """Chrome 插件上传 Amazon 产品 listing 数据。

    接收扩展抓取的产品 listing 信息 + 变体 ASIN，自动创建/更新产品档案。
    产品使用用户手动填写的 name，parent_product_id 使用 Amazon ASIN。
    """
    user_id = int(current_user["id"])

    try:
        result = plugin_upload_listing(
            user_id=user_id,
            parent_asin=body.parent_asin,
            name=body.name,
            platform=body.platform,
            marketplace=body.marketplace,
            listing=body.listing.model_dump(exclude_none=True) if body.listing else None,
            variants=[v.model_dump(exclude_none=True) for v in body.variants] if body.variants else [],
        )
        return result
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
