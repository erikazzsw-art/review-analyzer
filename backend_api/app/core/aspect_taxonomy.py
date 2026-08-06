"""家具家居 Aspect Taxonomy（V1.0）.

业界依据：
- SemEval ABSA 闭合 taxonomy 标准
- Shulex / Helium 10 预定义 + 用户自定义双轨设计
- 详见 docs/competitor-research-2026-06-05.md

设计原则：
- 闭合 20 类 + other 兜底（V1.1 新增 safety；5.9.6-D 新增 size_chart）
- 英文 canonical key（全系统底层一致）
- 中文 label 仅用于 UI 显示（i18n 由前端处理）
"""
from __future__ import annotations

FURNITURE_ASPECTS: dict[str, str] = {
    # 物理质量类（家具核心，5 类）
    "assembly": "组装难度",
    "durability": "耐用性",
    "stability": "稳固性",
    "material": "材质用料",
    "build_quality": "做工",
    # 使用体验类（4 类）
    "comfort": "舒适度",
    "size_fit": "尺寸匹配",
    "size_chart": "尺码表",
    "weight_capacity": "承重",
    "ease_of_use": "易用性",
    # 外观类（2 类）
    "aesthetics": "外观设计",
    "color_accuracy": "颜色还原度",
    # 物流类（家具特别重要，3 类）
    "packaging": "包装",
    "shipping_damage": "运输损坏",
    "missing_parts": "缺件",
    # 售后类（2 类）
    "instructions": "说明书",
    "customer_service": "客服",
    # 经济与体感类（2 类）
    "value_for_money": "性价比",
    "smell": "异味",
    # 安全类（V1.1 新增，来自 Golden Set bad case）
    "safety": "安全性",
    # 兜底
    "other": "其他",
}

ASPECT_KEYS: list[str] = list(FURNITURE_ASPECTS.keys())

SENTIMENT_VALUES: list[str] = ["positive", "negative", "neutral"]
POLARITY_VALUES: list[str] = ["positive", "negative", "neutral"]
EVIDENCE_LEVELS: list[str] = ["certain", "probable", "uncertain"]


def get_aspect_label_zh(key: str) -> str:
    """根据英文 key 返回中文 label（UI 显示用）."""
    return FURNITURE_ASPECTS.get(key, key)


def is_valid_aspect(key: str) -> bool:
    """校验 aspect key 是否在闭合列表中."""
    return key in FURNITURE_ASPECTS
