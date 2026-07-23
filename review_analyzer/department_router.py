"""部门映射引擎 — Aspect → 问题归属/责任部门路由"""
from __future__ import annotations

from typing import Any

DEPT_LABELS: dict[str, str] = {
    "qa": "质检",
    "product": "产研",
    "ops": "运营",
    "cs": "客服",
    "other": "其他",
}

DEPT_ICONS: dict[str, str] = {
    "qa": "📦",
    "product": "🎨",
    "ops": "🛒",
    "cs": "📞",
    "other": "📋",
}

DEFAULT_ASPECT_DEPT_MAP: dict[str, str] = {
    # 质检（产品本身质量/包装/物流）
    "quality": "qa",
    "product_quality": "qa",
    "defective": "qa",
    "damage": "qa",
    "broken": "qa",
    "breakage": "qa",
    "broken_on_arrival": "qa",
    "durability": "qa",
    "stability": "qa",
    "material": "qa",
    "materials": "qa",
    "build_quality": "qa",
    "packaging": "qa",
    "packaging_damage": "qa",
    "shipping_damage": "qa",
    "missing_parts": "qa",
    "smell": "qa",
    "safety": "qa",
    "ingredients": "qa",
    "leak_proof": "qa",
    # 产研（尺寸、设计、结构、易用性、说明书）
    "design": "product",
    "structure": "product",
    "structural_design": "product",
    "aesthetics": "product",
    "color_accuracy": "product",
    "comfort": "product",
    "size_fit": "product",
    "weight_capacity": "product",
    "ease_of_use": "product",
    "usability": "product",
    "assembly": "product",
    "installation": "product",
    "instructions": "product",
    "compatibility": "product",
    # 客服（售后、服务态度、退换货体验）
    "customer_service": "cs",
    "after_sales": "cs",
    "service_attitude": "cs",
    "returns": "cs",
    "return_exchange": "cs",
    "returns_refunds": "cs",
    "refund_experience": "cs",
    # 运营（价格、Listing、卖点表达、竞品机会）
    "value_for_money": "ops",
    "price": "ops",
    "pricing": "ops",
    "listing": "ops",
    "listing_accuracy": "ops",
    "listing_content": "ops",
    "description": "ops",
    "description_mismatch": "ops",
    "selling_points": "ops",
    "selling_point_expression": "ops",
    "copywriting": "ops",
    "bullet_points": "ops",
    "main_image": "ops",
    "image_accuracy": "ops",
    "competitor_opportunity": "ops",
    "competitive_opportunity": "ops",
    "competitor_research": "ops",
    "market_opportunity": "ops",
    # 兜底
    "other": "other",
}


def normalize_dept_mapping(user_mapping: Any) -> dict[str, str] | None:
    """将 API 保存的映射整理成 aspect -> dept，兼容列表和字典两种旧格式。"""
    if isinstance(user_mapping, dict):
        return {
            str(aspect): str(dept)
            for aspect, dept in user_mapping.items()
            if str(dept) in DEPT_LABELS
        }
    if isinstance(user_mapping, list):
        normalized: dict[str, str] = {}
        for item in user_mapping:
            if not isinstance(item, dict):
                continue
            aspect = str(item.get("aspect") or "").strip()
            dept = str(item.get("dept") or "").strip()
            if aspect and dept in DEPT_LABELS:
                normalized[aspect] = dept
        return normalized or None
    return None


def get_issue_dept(tag: str, user_mapping: Any = None) -> str:
    """单个 tag -> 责任部门映射。用户自定义映射优先于默认映射。"""
    normalized_mapping = normalize_dept_mapping(user_mapping)
    if normalized_mapping and tag in normalized_mapping:
        return normalized_mapping[tag]
    return DEFAULT_ASPECT_DEPT_MAP.get(tag, "other")


def route_issues_by_department(
    top_issues: list[dict],
    user_mapping: Any = None,
) -> dict[str, list[dict]]:
    """
    将 issues 按责任部门分组。

    参数:
        top_issues: [{"tag": "packaging", "pct": 15.2, "count": 10, ...}, ...]
        user_mapping: 用户自定义 aspect -> dept 覆盖映射

    返回:
        {"qa": [issue1, issue2], "product": [issue3], ...}
        每个 issue 会被注入 "dept" 字段
    """
    grouped: dict[str, list[dict]] = {dept: [] for dept in DEPT_LABELS}
    normalized_mapping = normalize_dept_mapping(user_mapping)

    for issue in top_issues:
        tag = issue.get("tag", "other")
        dept = get_issue_dept(tag, normalized_mapping)
        enriched = {**issue, "dept": dept}
        grouped[dept].append(enriched)

    return grouped


def get_dept_label(dept: str) -> str:
    """获取部门中文名称"""
    return DEPT_LABELS.get(dept, "其他")


def get_dept_icon(dept: str) -> str:
    """获取部门图标"""
    return DEPT_ICONS.get(dept, "📋")
