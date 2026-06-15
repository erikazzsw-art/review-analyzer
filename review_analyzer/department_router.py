"""部门映射引擎 — Aspect → 责任部门路由"""
from __future__ import annotations

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
    "durability": "qa",
    "stability": "qa",
    "material": "qa",
    "build_quality": "qa",
    "packaging": "qa",
    "shipping_damage": "qa",
    "missing_parts": "qa",
    "smell": "qa",
    "safety": "qa",
    # 产研（设计相关）
    "aesthetics": "product",
    "color_accuracy": "product",
    "comfort": "product",
    "size_fit": "product",
    "weight_capacity": "product",
    "ease_of_use": "product",
    "assembly": "product",
    "instructions": "product",
    # 客服
    "customer_service": "cs",
    # 运营
    "value_for_money": "ops",
    # 兜底
    "other": "other",
}


def get_issue_dept(tag: str, user_mapping: dict[str, str] | None = None) -> str:
    """单个 tag → dept 映射。用户自定义映射优先于默认映射。"""
    if user_mapping and tag in user_mapping:
        return user_mapping[tag]
    return DEFAULT_ASPECT_DEPT_MAP.get(tag, "other")


def route_issues_by_department(
    top_issues: list[dict],
    user_mapping: dict[str, str] | None = None,
) -> dict[str, list[dict]]:
    """
    将 issues 按部门分组。

    参数:
        top_issues: [{"tag": "packaging", "pct": 15.2, "count": 10, ...}, ...]
        user_mapping: 用户自定义 aspect→dept 覆盖映射

    返回:
        {"qa": [issue1, issue2], "product": [issue3], ...}
        每个 issue 会被注入 "dept" 字段
    """
    grouped: dict[str, list[dict]] = {dept: [] for dept in DEPT_LABELS}

    for issue in top_issues:
        tag = issue.get("tag", "other")
        dept = get_issue_dept(tag, user_mapping)
        enriched = {**issue, "dept": dept}
        grouped[dept].append(enriched)

    return grouped


def get_dept_label(dept: str) -> str:
    """获取部门中文名称"""
    return DEPT_LABELS.get(dept, "其他")


def get_dept_icon(dept: str) -> str:
    """获取部门图标"""
    return DEPT_ICONS.get(dept, "📋")
