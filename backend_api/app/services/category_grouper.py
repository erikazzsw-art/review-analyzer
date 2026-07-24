"""19 类英文 aspects → 11 类 category slug 聚合 + 派生规则.

业界依据：
- Shulex Tier 2 业务大类聚合（Quality / Logistics / Service）
- ClueAI 11 类是 Erika 6 年运营经验沉淀的同位概念
- 详见 docs/v4-t3-integration-plan-2026-06-06.md

输出 schema 与 review_analyzer.analyzer 一致：
- sentiment, content_sentiment, category, priority, reason, improvement,
  issue_tag, highlight_tag

category 字段自 V4-M2-2.2.C 起改为英文 slug（product_quality / packaging_logistics ...），
展示层通过 messages/{zh,en}.json 的 categoryLabels 翻译；Streamlit 老路径直接查
CATEGORY_ZH_LABELS 拿到中文。
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from backend_api.app.services.specific_issue import customer_highlight_tags_from_aspects

# 11 类 category slug（对外稳定业务标识；供 migration / tests / exporter 复用）
CATEGORY_SLUGS: tuple[str, ...] = (
    "product_quality",
    "packaging_logistics",
    "user_experience",
    "customer_service",
    "value_for_money",
    "feature_request",
    "positive_feedback",
    "simple_praise",
    "invalid_garbage",
    "mixed",
    "other",
)

# slug → 中文人类可读标签（供 Streamlit / exporter.py 后端导出复用）
CATEGORY_ZH_LABELS: dict[str, str] = {
    "product_quality": "产品质量",
    "packaging_logistics": "包装物流",
    "user_experience": "使用体验",
    "customer_service": "客服售后",
    "value_for_money": "性价比",
    "feature_request": "功能需求",
    "positive_feedback": "正面反馈",
    "simple_praise": "单纯好评",
    "invalid_garbage": "无效乱码",
    "mixed": "混合评价",
    "other": "其他",
}

# 19 类 aspect → category slug 直接映射（不含派生类）
ASPECT_TO_CATEGORY: dict[str, str] = {
    "durability": "product_quality",
    "stability": "product_quality",
    "material": "product_quality",
    "build_quality": "product_quality",
    "size_fit": "product_quality",
    "weight_capacity": "product_quality",
    "color_accuracy": "product_quality",
    "smell": "product_quality",
    "safety": "product_quality",
    "packaging": "packaging_logistics",
    "shipping_damage": "packaging_logistics",
    "missing_parts": "packaging_logistics",
    "assembly": "user_experience",
    "comfort": "user_experience",
    "ease_of_use": "user_experience",
    "instructions": "user_experience",
    "customer_service": "customer_service",
    "value_for_money": "value_for_money",
    # beauty / personal care dynamic taxonomy keys
    "efficacy": "product_quality",
    "cleansing_efficacy": "product_quality",
    "cleaning_efficacy": "product_quality",
    "spf_efficacy": "product_quality",
    "ingredients": "product_quality",
    "lengthening_effect": "product_quality",
    "volumizing_effect": "product_quality",
    "curl_hold": "product_quality",
    "separation_definition": "product_quality",
    "clumping": "product_quality",
    "smudge_resistance": "product_quality",
    "waterproof_performance": "product_quality",
    "flaking": "product_quality",
    "longevity": "product_quality",
    "color_payoff": "product_quality",
    "skin_compatibility": "user_experience",
    "scalp_compatibility": "user_experience",
    "eye_sensitivity": "user_experience",
    "texture": "user_experience",
    "formula_texture": "user_experience",
    "scent": "user_experience",
    "absorption": "user_experience",
    "moisturizing": "user_experience",
    "moisturizing_after_wash": "user_experience",
    "hair_feel_after": "user_experience",
    "foam": "user_experience",
    "residue": "user_experience",
    "noise": "user_experience",
    "vibration_strength": "user_experience",
    "battery_life": "user_experience",
    "charging": "user_experience",
    "brush_head_quality": "user_experience",
    "removal_ease": "user_experience",
    "brush_applicator": "user_experience",
    # outdoor dynamic taxonomy keys
    "waterproof": "product_quality",
    "seam_integrity": "product_quality",
    "wind_resistance": "product_quality",
    "temperature_rating": "product_quality",
    "grip": "product_quality",
    "ankle_support": "product_quality",
    "zipper_quality": "product_quality",
    "sensitivity": "product_quality",
    "strength": "product_quality",
    "corrosion_resistance": "product_quality",
    "action": "product_quality",
    "boot_fit": "product_quality",
    "capacity": "product_quality",
    "breathability": "user_experience",
    "portability": "user_experience",
    "ventilation": "user_experience",
    "organization": "user_experience",
    "break_in": "user_experience",
    "weight": "user_experience",
    "mobility": "user_experience",
    "grip_comfort": "user_experience",
    "accessory_storage": "user_experience",
    "other": "other",
}

VALID_CATEGORIES: set[str] = set(CATEGORY_SLUGS)

FUNCTIONAL_REQUEST_KEYWORDS = [
    "should add", "wish it had", "would like", "would love",
    "could add", "needs a", "would benefit from", "missing feature",
]

_LABELS_CACHE: dict[str, Any] | None = None


def _load_labels() -> dict[str, Any]:
    global _LABELS_CACHE
    if _LABELS_CACHE is None:
        path = Path(__file__).parent.parent / "i18n" / "aspect_labels.json"
        _LABELS_CACHE = json.loads(path.read_text(encoding="utf-8"))
    return _LABELS_CACHE


def aspect_to_zh(key: str) -> str:
    labels = _load_labels()
    return labels.get(key, {}).get("zh", key)


def aspect_to_en(key: str) -> str:
    labels = _load_labels()
    return labels.get(key, {}).get("en", key)


def _derive_category(
    aspects: list[dict[str, Any]],
    sentiment: str,
    content: str,
    highlights: list[str],
) -> str:
    """根据 sentiment + aspects + content 派生 category slug."""
    if not content or len(content.strip()) < 5:
        return "invalid_garbage"

    has_pos_aspect = any(a.get("polarity") == "positive" for a in aspects)
    has_neg_aspect = any(a.get("polarity") == "negative" for a in aspects)

    if has_pos_aspect and has_neg_aspect:
        return "mixed"

    content_lower = content.lower()
    if any(k in content_lower for k in FUNCTIONAL_REQUEST_KEYWORDS):
        return "feature_request"

    if not aspects:
        if sentiment == "positive":
            return "simple_praise"
        return "other"

    primary_aspect = aspects[0]
    aspect_key = primary_aspect.get("key", "other")
    polarity = primary_aspect.get("polarity", "neutral")

    # aesthetics 边界规则：positive → positive_feedback, negative → product_quality
    if aspect_key == "aesthetics":
        if polarity == "positive":
            return "positive_feedback"
        return "product_quality"

    if sentiment == "positive" and not has_neg_aspect:
        return "positive_feedback"

    return ASPECT_TO_CATEGORY.get(aspect_key, "other")


def _derive_priority(aspects: list[dict[str, Any]], sentiment: str) -> str:
    """根据 aspects 数量、polarity、evidence_level 派生优先级."""
    neg_aspects = [a for a in aspects if a.get("polarity") == "negative"]
    if not neg_aspects:
        return "无"
    high_risk_keys = {"safety", "skin_compatibility", "scalp_compatibility", "eye_sensitivity"}
    has_safety = any(a.get("key") in high_risk_keys for a in neg_aspects)
    if has_safety:
        return "高"
    has_certain = any(a.get("evidence_level") == "certain" for a in neg_aspects)
    if len(neg_aspects) >= 2 or has_certain:
        return "高"
    return "中"


def _derive_reason(aspects: list[dict[str, Any]], pain_points: list[str]) -> str:
    """生成一句话原因（≤30 字中文）."""
    if pain_points:
        return f"问题: {pain_points[0]}"[:30]
    if aspects:
        primary = aspects[0]
        zh = aspect_to_zh(primary.get("key", "other"))
        polarity = primary.get("polarity", "neutral")
        polarity_zh = {"positive": "好评", "negative": "差评", "neutral": "中性"}.get(polarity, "")
        return f"{zh}{polarity_zh}"
    return ""


def _derive_improvement(pain_points: list[str], aspects: list[dict[str, Any]]) -> str:
    """根据 pain_points 拼接改进建议."""
    if not pain_points:
        return ""
    neg_aspects_en = [
        aspect_to_en(a.get("key", ""))
        for a in aspects
        if a.get("polarity") == "negative"
    ]
    if neg_aspects_en:
        return f"Improve {','.join(neg_aspects_en[:2])}: {'; '.join(pain_points[:2])}"
    return "; ".join(pain_points[:2])


def _aspects_to_issue_tag(aspects: list[dict[str, Any]]) -> str:
    """提取负面 aspects 的英文标签，逗号分隔（最多 3 个）."""
    neg_en: list[str] = []
    seen: set[str] = set()
    for a in aspects:
        if a.get("polarity") == "negative":
            en = aspect_to_en(a.get("key", ""))
            if en and en not in seen:
                seen.add(en)
                neg_en.append(en)
                if len(neg_en) >= 3:
                    break
    return ",".join(neg_en)


def _aspects_to_highlight_tag(aspects: list[dict[str, Any]]) -> str:
    """提取正面 aspects 的英文标签，逗号分隔（最多 3 个）."""
    pos_en: list[str] = []
    seen: set[str] = set()
    for a in aspects:
        if a.get("polarity") == "positive":
            en = aspect_to_en(a.get("key", ""))
            if en and en not in seen:
                seen.add(en)
                pos_en.append(en)
                if len(pos_en) >= 3:
                    break
    return ",".join(pos_en)


def aspects_to_legacy_schema(
    aspects: list[dict[str, Any]],
    sentiment: str,
    content: str,
    pain_points: list[str] | None = None,
    highlights: list[str] | None = None,
    locale: str = "en",
) -> dict[str, Any]:
    """V4-T3 输出 → 生产 8 字段（向后兼容 Streamlit + Next.js 旧 UI）."""
    pain_points = pain_points or []
    highlights = highlights or []
    aspects = aspects or []

    if not content or len(content.strip()) < 5:
        return {
            "sentiment": "unrecognizable",
            "content_sentiment": "unrecognizable",
            "category": "invalid_garbage",
            "priority": "无",
            "reason": "",
            "improvement": "",
            "issue_tag": "",
            "highlight_tag": "",
        }

    content_sentiment = sentiment
    category = _derive_category(aspects, sentiment, content, highlights)
    priority = _derive_priority(aspects, sentiment)
    reason = _derive_reason(aspects, pain_points)
    improvement = _derive_improvement(pain_points, aspects)
    issue_tag = _aspects_to_issue_tag(aspects)
    highlight_tag = customer_highlight_tags_from_aspects(
        aspects,
        content=content,
        locale=locale,
    ) or _aspects_to_highlight_tag(aspects)

    return {
        "sentiment": sentiment,
        "content_sentiment": content_sentiment,
        "category": category if category in VALID_CATEGORIES else "other",
        "priority": priority,
        "reason": reason,
        "improvement": improvement,
        "issue_tag": issue_tag,
        "highlight_tag": highlight_tag,
    }
