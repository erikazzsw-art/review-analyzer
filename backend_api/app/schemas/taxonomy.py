"""Taxonomy API schemas (V4-T1.5 Step 3)."""
from __future__ import annotations

from pydantic import BaseModel, Field


class CategoryGroup(BaseModel):
    """单个核心品类下的 sub_category 清单."""
    category_key: str = Field(..., description="品类 key，如 home / 3c / apparel / baby / pet")
    category_label: str = Field(..., description="按请求 locale 本地化后的品类展示名")
    sub_categories: list[str] = Field(default_factory=list, description="该品类下入库的 sub_category 列表（原始 key，用于提交）")
    sub_category_labels: dict[str, str] = Field(
        default_factory=dict,
        description="该组内 sub_category → 本地化显示名 的映射，前端用此字段渲染下拉选项文本",
    )


class TaxonomyCategoriesResponse(BaseModel):
    """GET /taxonomy/categories 返回结构.

    前端用途：
    - supported_categories：用于上传页类目选择的 autocomplete + 已支持品类提示
    - unknown_sub_categories：DB 表里有但映射文件没归类的 sub_category（fallback 通用模板范围内）
    - total_sub_categories：合计入库的 sub_category 数（命中提示文案用）
    """
    supported_categories: list[CategoryGroup]
    unknown_sub_categories: list[str] = Field(default_factory=list)
    total_sub_categories: int
    taxonomy_version: str
    notice: str | None = Field(
        default=None,
        description="给前端的提示语，例如未识别 category 时的引导文案",
    )


class SubCategoryProbeResponse(BaseModel):
    """GET /taxonomy/sub_category?name=床架 返回结构.

    用于前端实时显示某个 sub_category 是否命中 taxonomy（决定提示样式）.
    """
    sub_category: str
    is_taxonomy_hit: bool
    category_key: str | None = None
    category_label: str | None = None
    aspects_count: int = 0
