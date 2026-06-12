"""Prompt 版本管理中心（生产版，移自 scripts/prompt_registry.py）.

设计原则:
- 单一来源：所有 prompt 写在 backend_api/app/prompts/*.md
- 版本不可变：发布后的 prompt 版本文件不允许修改，新版本 = 新文件
- 调用追踪：每次 LLM 调用记录 prompt_version 字段
- DEFAULT 版本：当前生产使用的版本，由本模块常量定义

prompts/ 目录约定：
    annotate_v{major}.{minor}.md   标注任务（情感 + Aspect + 痛点 + 亮点）
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import NamedTuple

PROMPTS_DIR = Path(__file__).parent.parent / "prompts"

# 当前生产默认版本
# v2.4 (2026-06-10): 动态 taxonomy 注入（{{ASPECTS_BLOCK}} 占位符）
# 品类专属 aspect 替代硬编码 19 个家具 aspect；情感规则与 v2.3 完全一致
# v2.3 (2026-06-08): 在 499 条 Golden Set 上 94.6% 准确率（v2.1 基线 92.2%）
DEFAULT_ANNOTATE_VERSION = "v2.4"


class PromptDef(NamedTuple):
    """单个 prompt 版本的元信息."""
    name: str
    version: str
    system_prompt: str
    raw_md: str
    file_path: Path


def _extract_system_prompt(md_text: str) -> str:
    """从 markdown 中提取 ## System Prompt 下的代码块内容."""
    pattern = r"##\s+System Prompt\s*\n\s*```(?:\w+)?\n(.*?)\n```"
    match = re.search(pattern, md_text, re.DOTALL)
    if not match:
        raise ValueError("未在 markdown 中找到 ## System Prompt 代码块")
    return match.group(1).strip()


def load_prompt(task: str, version: str | None = None) -> PromptDef:
    """加载指定 prompt 版本.

    Args:
        task: 任务名 (annotate)
        version: 版本号 (v2.1)。None 时使用 DEFAULT_*_VERSION

    Returns:
        PromptDef 包含 system_prompt 和元信息
    """
    if version is None:
        if task == "annotate":
            version = DEFAULT_ANNOTATE_VERSION
        else:
            raise ValueError(f"未知任务名: {task}")

    file_name = f"{task}_{version}.md"
    file_path = PROMPTS_DIR / file_name
    if not file_path.exists():
        raise FileNotFoundError(f"找不到 prompt 文件: {file_path}")

    raw_md = file_path.read_text(encoding="utf-8")
    system_prompt = _extract_system_prompt(raw_md)
    return PromptDef(
        name=task,
        version=version,
        system_prompt=system_prompt,
        raw_md=raw_md,
        file_path=file_path,
    )


def list_versions(task: str) -> list[str]:
    """列出某任务的所有可用版本."""
    pattern = re.compile(rf"^{re.escape(task)}_v(\d+)\.(\d+)\.md$")
    versions = []
    for p in PROMPTS_DIR.glob(f"{task}_v*.md"):
        m = pattern.match(p.name)
        if m:
            versions.append(f"v{m.group(1)}.{m.group(2)}")
    return sorted(versions, key=lambda v: tuple(int(x) for x in v[1:].split(".")))
