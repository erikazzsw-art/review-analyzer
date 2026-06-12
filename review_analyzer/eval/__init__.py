"""ClueAI 评测模块.

提供：
- runner.evaluate(prompt_version, golden_set_version) → EvalResult
- CLI: python3 -m review_analyzer.eval.run --prompt-version v2.1 --golden-set v1.0

业界依据：SemEval ABSA 评测设计（accuracy / precision / recall / F1）
设计参考：scripts/ab_test_prompts.py
"""
from __future__ import annotations

from .runner import EvalResult, evaluate

__all__ = ["EvalResult", "evaluate"]
