"""Calibration Injector — 从 golden_set 构建 few-shot prompt 注入片段.

方案B：精选正/负例作为 few-shot 示例注入 aspects_block，取代旧版抽象否定规则。
"""
from __future__ import annotations

import logging

from review_analyzer.golden_set_store import get_fewshot_examples

logger = logging.getLogger(__name__)


def build_calibration_block(sub_category: str) -> str:
    """加载 golden_set 中标记为 few-shot 的示例，构建 prompt 片段.

    返回空字符串表示无校准数据（调用方无需注入）。
    格式：正例展示"这条评论属于X标签"，负例展示"这条评论不属于X标签，应为Y"。
    """
    examples = get_fewshot_examples(sub_category, limit=30)
    if not examples:
        return ""

    lines: list[str] = [
        "[标签校准参考 — 以下为人工验证的标注示例，请参考判断标签归属]"
    ]

    for ex in examples:
        text_preview = ex["comment_text"][:80]
        aspect = ex["aspect_key"]
        if ex["is_correct"]:
            lines.append(f'- "{text_preview}..." → 正确标签: {aspect}')
        else:
            correct = ex.get("correct_tag")
            reason = ex.get("reason", "")
            if correct:
                lines.append(
                    f'- "{text_preview}..." → 不属于 {aspect}，应为 {correct}'
                )
            elif reason:
                lines.append(
                    f'- "{text_preview}..." → 不属于 {aspect}（{reason}）'
                )
            else:
                lines.append(f'- "{text_preview}..." → 不属于 {aspect}')

    return "\n".join(lines)
