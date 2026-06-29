"""Taxonomy API routes (V4-T1.5 Step 3).

提供给前端：
- GET /taxonomy/categories: 返回已入库的 sub_category 清单（按 5 核心品类分组）+ unknown 桶
- GET /taxonomy/sub_category?name=床架: 探测某 sub_category 是否命中 taxonomy

数据源：
- DB: category_aspect_taxonomy 表的 DISTINCT sub_category（single source of truth）
- 静态 JSON: backend_api/app/data/sub_category_categories.json（sub_category → category 归类映射，
  由 scripts/import_v4t1_assets 上游产物推导，Dockerfile COPY backend_api 时打入容器）
"""
from __future__ import annotations

import json
import logging
from functools import lru_cache
from pathlib import Path

from fastapi import APIRouter, Depends, Query

from backend_api.app.deps import get_current_user
from backend_api.app.schemas.taxonomy import (
    CategoryGroup,
    SubCategoryProbeResponse,
    TaxonomyCategoriesResponse,
)
from backend_api.app.services.taxonomy_loader import resolve_aspects

logger = logging.getLogger(__name__)

router = APIRouter(tags=["taxonomy"])

_MAPPING_PATH = Path(__file__).parent.parent / "data" / "sub_category_categories.json"


@lru_cache(maxsize=1)
def _load_static_mapping() -> dict:
    """加载 sub_category → category 静态映射 JSON.

    返回结构 dict 包含：category_labels / sub_category_to_category / taxonomy_version
    JSON 文件缺失时回退最小默认结构（仅 home 品类，避免 API 完全坏掉）.
    """
    if not _MAPPING_PATH.exists():
        logger.warning("taxonomy: mapping file missing at %s; using minimal default", _MAPPING_PATH)
        return {
            "taxonomy_version": "v1.0",
            "category_labels": {"home": "家居家具"},
            "sub_category_to_category": {},
            "total_sub_categories": 0,
        }
    return json.loads(_MAPPING_PATH.read_text(encoding="utf-8"))


def _load_db_sub_categories() -> list[str]:
    """从 category_aspect_taxonomy 表查所有 DISTINCT sub_category.

    DB 异常时返回空列表，让 API 回退到只用静态映射（不阻断响应）.
    """
    try:
        import psycopg2.extras

        from review_analyzer.database import get_connection
    except Exception as exc:
        logger.warning("taxonomy: cannot import db deps: %s", exc)
        return []
    try:
        conn = get_connection()
    except Exception as exc:
        logger.warning("taxonomy: get_connection failed: %s", exc)
        return []
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                "SELECT DISTINCT sub_category FROM category_aspect_taxonomy "
                "ORDER BY sub_category"
            )
            rows = cur.fetchall()
    except Exception as exc:
        logger.warning("taxonomy: query distinct sub_category failed: %s", exc)
        try:
            conn.rollback()
        except Exception:
            pass
        return []
    finally:
        try:
            conn.close()
        except Exception:
            pass
    return [str(r["sub_category"]) for r in rows]


@router.get("/taxonomy/categories", response_model=TaxonomyCategoriesResponse)
def get_categories(
    _: dict = Depends(get_current_user),
) -> TaxonomyCategoriesResponse:
    """返回当前已入库的 sub_category 清单（按 5 核心品类分组）.

    DB 是 single source of truth。若 DB 不可用，回退到只用静态映射键集，
    保证上传页仍能展示"已支持品类"提示.
    """
    mapping = _load_static_mapping()
    sc_to_cat: dict[str, str] = mapping.get("sub_category_to_category", {})
    cat_labels: dict[str, str] = mapping.get("category_labels", {})

    db_subs = _load_db_sub_categories()
    if not db_subs:
        db_subs = sorted(sc_to_cat.keys())
        notice = "taxonomy DB 暂时不可用，已退回静态映射；分析链路 fallback 通用模板仍可工作"
    else:
        notice = None

    grouped: dict[str, list[str]] = {key: [] for key in cat_labels}
    unknown: list[str] = []
    for sub in db_subs:
        cat = sc_to_cat.get(sub)
        if cat and cat in grouped:
            grouped[cat].append(sub)
        else:
            unknown.append(sub)

    groups = [
        CategoryGroup(
            category_key=key,
            category_label=cat_labels[key],
            sub_categories=sorted(subs),
        )
        for key, subs in grouped.items()
        if subs
    ]
    groups.sort(key=lambda g: (-len(g.sub_categories), g.category_key))

    return TaxonomyCategoriesResponse(
        supported_categories=groups,
        unknown_sub_categories=sorted(unknown),
        total_sub_categories=len(db_subs),
        taxonomy_version=str(mapping.get("taxonomy_version") or "v1.0"),
        notice=notice,
    )


@router.get("/taxonomy/sub_category", response_model=SubCategoryProbeResponse)
def probe_sub_category(
    name: str = Query(..., min_length=1, description="待探测的 sub_category 名称"),
    _: dict = Depends(get_current_user),
) -> SubCategoryProbeResponse:
    """探测给定 sub_category 是否命中 taxonomy，返回归类与 aspect 数.

    前端上传页用户实时输入 / 选择 category 时调用，决定显示绿色"已识别"或橙色"通用模板"提示.
    """
    mapping = _load_static_mapping()
    sc_to_cat: dict[str, str] = mapping.get("sub_category_to_category", {})
    cat_labels: dict[str, str] = mapping.get("category_labels", {})

    aspects, hit = resolve_aspects(name)
    cat_key = sc_to_cat.get(name)
    return SubCategoryProbeResponse(
        sub_category=name,
        is_taxonomy_hit=hit,
        category_key=cat_key,
        category_label=cat_labels.get(cat_key) if cat_key else None,
        aspects_count=len(aspects) if hit else 0,
    )


@router.get("/taxonomy/aspects")
def get_aspects(
    _: dict = Depends(get_current_user),
) -> list[dict[str, str]]:
    """返回完整 aspect 列表（key + 中文 label），供校准下拉选择."""
    from backend_api.app.core.aspect_taxonomy import FURNITURE_ASPECTS

    return [{"key": k, "label": v} for k, v in FURNITURE_ASPECTS.items()]
