"""Calibration Injector — 从 label_calibration 表构建 prompt 注入片段."""
from __future__ import annotations

import logging

from review_analyzer.calibration_store import get_calibrations

logger = logging.getLogger(__name__)


def build_calibration_block(sub_category: str) -> str:
    """加载 active 校准样例，构建可追加到 aspects_block 的 prompt 片段.

    返回空字符串表示无校准数据（调用方无需注入）。
    """
    calibrations = get_calibrations(sub_category, limit=20)
    if not calibrations:
        return ""

    lines: list[str] = ["[标签校准参考 — 以下为人工标注的纠错样例，请避免重复相同错误]"]
    for cal in calibrations:
        original = cal["original_tag"]
        correct = cal.get("correct_tag")
        note = cal.get("note")

        if correct:
            lines.append(f"- 不要将类似内容标记为 {original}，正确标签应为 {correct}")
        elif note:
            lines.append(f"- 不要将类似内容标记为 {original}（备注: {note}）")
        else:
            lines.append(f"- 不要将类似内容标记为 {original}")

    return "\n".join(lines)
