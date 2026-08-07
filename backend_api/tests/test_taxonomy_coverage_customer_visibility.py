"""5.9.6-C1: `other` 占比告警不得出现在客户前台读路径。

内部信号（DB / trace / 飞书）必须保持不变，只有客户读路径过滤。
"""
from __future__ import annotations

from backend_api.app.services.taxonomy_coverage_monitor import (
    INTERNAL_ONLY_WARNING_TYPES,
    WARNING_TYPE_TAXONOMY_COVERAGE_LOW,
    build_coverage_warning,
    compute_taxonomy_coverage,
    filter_customer_visible_warnings,
)


def _coverage_warning() -> dict:
    results = [{"aspects": [{"key": "other"}] * 3 + [{"key": "waterproof"}]}]
    warning = build_coverage_warning(compute_taxonomy_coverage(results, sub_category="waders"))
    assert warning is not None, "75% other 应该越过 15% 阈值"
    return warning


def test_coverage_warning_type_is_internal_only() -> None:
    assert _coverage_warning()["type"] == WARNING_TYPE_TAXONOMY_COVERAGE_LOW
    assert WARNING_TYPE_TAXONOMY_COVERAGE_LOW in INTERNAL_ONLY_WARNING_TYPES


def test_coverage_warning_filtered_from_customer_payload() -> None:
    assert filter_customer_visible_warnings([_coverage_warning()]) is None


def test_customer_facing_warning_survives() -> None:
    keep = {"type": "quota_exceeded", "severity": "warning", "message": "配额不足"}
    assert filter_customer_visible_warnings([_coverage_warning(), keep]) == [keep]


def test_empty_and_none_inputs() -> None:
    assert filter_customer_visible_warnings(None) is None
    assert filter_customer_visible_warnings([]) is None


def test_untyped_entries_dropped_fail_closed() -> None:
    """无法判定 type 的条目按内部处理丢弃，避免新增内部类型时默认泄漏。"""
    assert filter_customer_visible_warnings([{"message": "no type"}]) is None
    assert filter_customer_visible_warnings([{"type": "", "message": "empty"}]) is None
    assert filter_customer_visible_warnings(["not a dict"]) is None  # type: ignore[list-item]


def test_internal_signal_path_unchanged() -> None:
    """过滤只发生在读路径：build_coverage_warning 仍产出完整 data。"""
    warning = _coverage_warning()
    assert warning["data"]["other_count"] == 3
    assert warning["data"]["exceeded"] is True
    assert "占比" in warning["message"]
