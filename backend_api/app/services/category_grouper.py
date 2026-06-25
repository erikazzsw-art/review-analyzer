"""19 类英文 aspects → 11 类中文 category 聚合 + 派生规则.

业界依据：
- Shulex Tier 2 业务大类聚合（Quality / Logistics / Service）
- ClueAI 11 类是 Erika 6 年运营经验沉淀的同位概念
- 详见 docs/v4-t3-integration-plan-2026-06-06.md

输出 schema 与 review_analyzer.analyzer 一致：
- sentiment, content_sentiment, category, priority, reason, improvement,
  issue_tag, highlight_tag

确保 Streamlit 旧 UI 与 Next.js 新 UI 都能消费（API 中间层翻译用）.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

# 19 类 aspect → 11 类 L0 category 直接映射（不含派生类）
ASPECT_TO_CATEGORY: dict[str, str] = {
    "durability": "产品质量",
    "stability": "产品质量",
    "material": "产品质量",
    "build_quality": "产品质量",
    "size_fit": "产品质量",
    "weight_capacity": "产品质量",
    "color_accuracy": "产品质量",
    "smell": "产品质量",
    "safety": "产品质量",
    "packaging": "包装物流",
    "shipping_damage": "包装物流",
    "missing_parts": "包装物流",
    "assembly": "使用体验",
    "comfort": "使用体验",
    "ease_of_use": "使用体验",
    "instructions": "使用体验",
    "customer_service": "客服售后",
    "value_for_money": "性价比",
    "other": "其他",
}

VALID_CATEGORIES = {
    "产品质量", "包装物流", "使用体验", "客服售后", "性价比",
    "功能需求", "正面反馈", "单纯好评", "无效乱码", "混合评价", "其他",
}

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
    """根据 sentiment + aspects + content 派生 11 类 category."""
    if not content or len(content.strip()) < 5:
        return "无效乱码"

    has_pos_aspect = any(a.get("polarity") == "positive" for a in aspects)
    has_neg_aspect = any(a.get("polarity") == "negative" for a in aspects)

    if has_pos_aspect and has_neg_aspect:
        return "混合评价"

    content_lower = content.lower()
    if any(k in content_lower for k in FUNCTIONAL_REQUEST_KEYWORDS):
        return "功能需求"

    if not aspects:
        if sentiment == "positive":
            return "单纯好评"
        return "其他"

    primary_aspect = aspects[0]
    aspect_key = primary_aspect.get("key", "other")
    polarity = primary_aspect.get("polarity", "neutral")

    # aesthetics 边界规则：positive→正面反馈, negative→产品质量
    if aspect_key == "aesthetics":
        if polarity == "positive":
            return "正面反馈"
        return "产品质量"

    if sentiment == "positive" and not has_neg_aspect:
        return "正面反馈"

    return ASPECT_TO_CATEGORY.get(aspect_key, "其他")


def _derive_priority(aspects: list[dict[str, Any]], sentiment: str) -> str:
    """根据 aspects 数量、polarity、evidence_level 派生优先级."""
    neg_aspects = [a for a in aspects if a.get("polarity") == "negative"]
    if not neg_aspects:
        return "无"
    has_safety = any(a.get("key") == "safety" for a in neg_aspects)
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
) -> dict[str, Any]:
    """V4-T3 输出 → 生产 8 字段（向后兼容 Streamlit + Next.js 旧 UI）."""
    pain_points = pain_points or []
    highlights = highlights or []
    aspects = aspects or []

    if not content or len(content.strip()) < 5:
        return {
            "sentiment": "unrecognizable",
            "content_sentiment": "unrecognizable",
            "category": "无效乱码",
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
    highlight_tag = _aspects_to_highlight_tag(aspects)

    return {
        "sentiment": sentiment,
        "content_sentiment": content_sentiment,
        "category": category if category in VALID_CATEGORIES else "其他",
        "priority": priority,
        "reason": reason,
        "improvement": improvement,
        "issue_tag": issue_tag,
        "highlight_tag": highlight_tag,
    }
