"""V4-T1.6 Step 3: Taxonomy 覆盖率监控.

分析完成后统计 `other` aspect 占比，超过阈值时生成告警。
告警写入 trace_json + 飞书推送，帮助发现 taxonomy 覆盖盲区。
"""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

OTHER_RATIO_THRESHOLD = 0.15


def compute_taxonomy_coverage(
    results: list[dict[str, Any]],
    sub_category: str | None = None,
) -> dict[str, Any]:
    """统计本批次分析结果中 `other` aspect 占比.

    Args:
        results: ordered_v4_results 列表，每项含 aspects 字段
        sub_category: 当前分析的子品类

    Returns:
        {
            "total_aspects": int,
            "other_count": int,
            "other_ratio": float,
            "threshold": float,
            "exceeded": bool,
            "sub_category": str | None,
        }
    """
    total_aspects = 0
    other_count = 0

    for r in results:
        if r.get("error"):
            continue
        aspects = r.get("aspects", [])
        for aspect in aspects:
            key = aspect.get("key", "") if isinstance(aspect, dict) else ""
            total_aspects += 1
            if key == "other":
                other_count += 1

    ratio = other_count / total_aspects if total_aspects > 0 else 0.0

    return {
        "total_aspects": total_aspects,
        "other_count": other_count,
        "other_ratio": round(ratio, 4),
        "threshold": OTHER_RATIO_THRESHOLD,
        "exceeded": ratio > OTHER_RATIO_THRESHOLD,
        "sub_category": sub_category,
    }


def build_coverage_warning(coverage: dict[str, Any]) -> dict[str, Any] | None:
    """如果 other 占比超阈值，生成结构化告警信息."""
    if not coverage["exceeded"]:
        return None

    pct = round(coverage["other_ratio"] * 100, 1)
    sub_cat = coverage["sub_category"] or "未知品类"

    return {
        "type": "taxonomy_coverage_low",
        "severity": "warning",
        "message": (
            f"品类「{sub_cat}」的 aspect 维度覆盖不足："
            f"'other' 占比 {pct}%（阈值 {int(coverage['threshold'] * 100)}%）。"
            f"建议扩展该品类的 taxonomy 定义。"
        ),
        "data": coverage,
    }


def format_ops_alert(warning: dict[str, Any], session_id: int, user_id: int) -> str:
    """格式化运维告警文本（三平台通用）."""
    data = warning["data"]
    pct = round(data["other_ratio"] * 100, 1)
    return (
        f"⚠️ Taxonomy 覆盖告警\n"
        f"品类：{data['sub_category'] or '未知'}\n"
        f"'other' 占比：{pct}%（阈值 {int(data['threshold'] * 100)}%）\n"
        f"总 aspect 数：{data['total_aspects']}，其中 other：{data['other_count']}\n"
        f"Session: {session_id} | User: {user_id}\n"
        f"建议：检查 category_aspect_taxonomy 表是否覆盖该品类"
    )
