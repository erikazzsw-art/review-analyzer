"""阶段 A Task A-3：证据感知的粗细标签去重 + D1 语义守卫.

职责：
1. 粗/细标签去重 —— 同一条 evidence 上同时存在粗细两个标签时，只保留细标签
2. D1 通用语义守卫 —— 否决规则产生的误标（如环境高温导致的 sweat → not_breathable）

设计原则：
- 纯函数、幂等、确定性、无副作用
- 只否决、不创造标签（遵循"AI 负责理解，规则只负责刹车"）
- 被删的粗标签保留到 audit record，带 deduplication_applied / deduped_by_label / evidence_overlap
- 第一版只启用已被 A-2 真实样本证明的关系，不加入未经验证的推测关系
"""

from __future__ import annotations

import logging
import os
import re
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 版本与开关
# ---------------------------------------------------------------------------

DEDUP_RULESET_VERSION = "2026-08-12-a3-coarse-fine-dedup"
SEMANTIC_GUARD_RULESET_VERSION = "2026-08-12-a3-d1-not-breathable-guard"

_DEDUP_KILL_SWITCH_ENV = "COARSE_FINE_DEDUP_ENABLED"
_SEMANTIC_GUARD_KILL_SWITCH_ENV = "SEMANTIC_GUARD_ENABLED"


def _is_dedup_enabled() -> bool:
    """粗细去重总开关（默认开，设 env=false 紧急关闭）."""
    return os.getenv(_DEDUP_KILL_SWITCH_ENV, "true").strip().lower() != "false"


def _is_semantic_guard_enabled() -> bool:
    """D1 语义守卫总开关（默认开，设 env=false 紧急关闭）."""
    return os.getenv(_SEMANTIC_GUARD_KILL_SWITCH_ENV, "true").strip().lower() != "false"


# ---------------------------------------------------------------------------
# 父子标签关系（第一版只启用 A-2 已验证的关系）
# ---------------------------------------------------------------------------

COARSE_TO_FINE_LABELS: dict[str, frozenset[str]] = {
    # 2026-08-13 A-5：size 域粗细标签已统一为 size_fit_problem（runs_too_small / runs_too_large 退役），
    # 原 size_fit_problem → {runs_too_small, runs_too_large} 关系作废。
    # 未来若其它域出现经真实标注验证的粗细关系，在此追加（遵循"只启用已验证关系"原则）。
}

# 暂不启用的推测关系（待真实标注验证后加入）：
# "size_fit_problem" → inaccurate_size_chart / pants_too_long / not_petite_friendly
# "quality_problem" → arrived_damaged / quality_control_storage_issue
# "breaks_easily" → 其他耐用性细标签


# ---------------------------------------------------------------------------
# 兼容 aspect_key 集合（用于粗细去重时的 aspect_key 兼容性判定）
# LLM 可能用 mobility/boot_fit/comfort 等维度表达 size_fit 问题，
# 而 content-rule 固定使用 size_fit。只要双方都属于同一粗标签家族的
# 兼容维度，就不应因 aspect_key 不同而阻止去重。
# ---------------------------------------------------------------------------

_COMPATIBLE_ASPECT_KEYS_BY_COARSE: dict[str, set[str]] = {
    "size_fit_problem": {"size_fit", "boot_fit", "mobility", "comfort"},
}


def _aspect_keys_compatible(
    coarse_canonical: str,
    coarse_aspect: str,
    fine_aspect: str,
) -> bool:
    """判断粗/细标签的 aspect_key 是否兼容."""
    if not coarse_aspect or not fine_aspect:
        return True  # 任一方为空 → 无法判定不兼容，放行
    if coarse_aspect == fine_aspect:
        return True
    compatible = _COMPATIBLE_ASPECT_KEYS_BY_COARSE.get(coarse_canonical, set())
    return bool(compatible and coarse_aspect in compatible and fine_aspect in compatible)


# ---------------------------------------------------------------------------
# 置信度排序
# ---------------------------------------------------------------------------

_CONFIDENCE_ORDER: dict[str, int] = {"low": 0, "medium": 1, "high": 2}


def _confidence_not_lower(a: str, b: str) -> bool:
    """a 的置信度不低于 b."""
    return _CONFIDENCE_ORDER.get(a, 0) >= _CONFIDENCE_ORDER.get(b, 0)


# ---------------------------------------------------------------------------
# 来源权威性排序（用于判定细标签是否比粗标签更权威）
# ---------------------------------------------------------------------------

_SOURCE_PRIORITY: dict[str, int] = {
    "llm_canonical_hint": 3,
    "regex_alias_rule": 2,
    "sentiment_recovery_rule": 1,
    "waders_content_rule": 1,
}


def _source_priority(source_detail: str) -> int:
    """返回来源的权威性分数，未知来源默认 0."""
    if not source_detail:
        return 0
    return _SOURCE_PRIORITY.get(source_detail, 0)


# ---------------------------------------------------------------------------
# 证据重叠判定
# ---------------------------------------------------------------------------

def _normalize_evidence(text: str) -> str:
    """规范化 evidence 文本用于比较."""
    return re.sub(r"\s+", " ", text).strip().lower()


def _evidence_overlaps(
    coarse_evidence: str,
    fine_evidence: str,
    coarse_start: Any,
    coarse_end: Any,
    fine_start: Any,
    fine_end: Any,
) -> bool:
    """判断两条 evidence 是否描述同一段原文.

    满足以下任一条件即视为重叠：
    1. evidence_start/evidence_end 区间重叠
    2. 一个 evidence 文本规范化后包含另一个
    3. 规范化文本完全相同
    """
    # 条件 1：区间重叠（如果有区间信息）
    if (
        coarse_start is not None and coarse_end is not None
        and fine_start is not None and fine_end is not None
    ):
        try:
            cs, ce = int(coarse_start), int(coarse_end)
            fs, fe = int(fine_start), int(fine_end)
            if cs <= fe and fs <= ce:
                return True
        except (ValueError, TypeError):
            pass

    # 条件 2/3：文本包含或相同
    if not coarse_evidence or not fine_evidence:
        return False
    coarse_norm = _normalize_evidence(coarse_evidence)
    fine_norm = _normalize_evidence(fine_evidence)
    if not coarse_norm or not fine_norm:
        return False
    if coarse_norm == fine_norm:
        return True
    return coarse_norm in fine_norm or fine_norm in coarse_norm


def _describe_overlap(coarse_evidence: str, fine_evidence: str) -> str:
    """描述重叠关系（用于 audit record）."""
    coarse_norm = _normalize_evidence(coarse_evidence)
    fine_norm = _normalize_evidence(fine_evidence)
    if coarse_norm == fine_norm:
        return "identical"
    if coarse_norm in fine_norm:
        return "coarse_contained_in_fine"
    if fine_norm in coarse_norm:
        return "fine_contained_in_coarse"
    return "interval_overlap"


# ---------------------------------------------------------------------------
# 粗细去重核心函数
# ---------------------------------------------------------------------------

def deduplicate_coarse_occurrences(
    occurrences: list[dict[str, Any]],
    content: str = "",
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """对 occurrence 列表做证据感知的粗细标签去重.

    只有以下条件**全部**满足时才删除粗标签：
    1. label_type 相同（不能跨 issue/highlight 去重）
    2. 粗标签和细标签属于 COARSE_TO_FINE_LABELS 关系
    3. aspect_key 相同或至少一方为空
    4. 两条 evidence 可定位且满足重叠条件
    5. 细标签置信度不低于粗标签

    Args:
        occurrences: 已投影的 occurrence 列表
        content: 原始评论文本（用于证据定位）

    Returns:
        (display_occurrences, dedup_audit_records)
        - display_occurrences: 去重后的 occurrence 列表
        - dedup_audit_records: 被删除的粗标签副本，带 dedup 元信息
    """
    if not _is_dedup_enabled():
        return list(occurrences), []

    n = len(occurrences)
    if n < 2:
        return list(occurrences), []

    # Pass 1：识别要删除的粗标签索引
    to_remove: set[int] = set()
    audit_records: list[dict[str, Any]] = []

    for i in range(n):
        coarse = occurrences[i]
        coarse_canonical = str(coarse.get("canonical_label_key") or "").strip()
        fine_keys = COARSE_TO_FINE_LABELS.get(coarse_canonical)
        if not fine_keys:
            continue

        coarse_type = str(coarse.get("type") or "").strip()
        coarse_aspect = str(coarse.get("aspect_key") or "").strip()
        coarse_evidence = str(coarse.get("evidence_span") or "").strip()
        coarse_start = coarse.get("evidence_start")
        coarse_end = coarse.get("evidence_end")
        coarse_confidence = str(coarse.get("confidence") or "medium").strip()

        for j in range(n):
            if i == j:
                continue
            fine = occurrences[j]
            fine_canonical = str(fine.get("canonical_label_key") or "").strip()
            if fine_canonical not in fine_keys:
                continue

            # 条件 1：同 label_type
            fine_type = str(fine.get("type") or "").strip()
            if fine_type != coarse_type:
                continue

            # 条件 2：aspect_key 相同或兼容
            fine_aspect = str(fine.get("aspect_key") or "").strip()
            if not _aspect_keys_compatible(coarse_canonical, coarse_aspect, fine_aspect):
                continue

            # 条件 3：证据重叠
            fine_evidence = str(fine.get("evidence_span") or "").strip()
            fine_start = fine.get("evidence_start")
            fine_end = fine.get("evidence_end")

            if not _evidence_overlaps(
                coarse_evidence, fine_evidence,
                coarse_start, coarse_end,
                fine_start, fine_end,
            ):
                continue

            # 条件 4：细标签置信度不低于粗标签
            fine_confidence = str(fine.get("confidence") or "medium").strip()
            if not _confidence_not_lower(fine_confidence, coarse_confidence):
                continue

            # 条件 5：细标签来源权威性不低于粗标签，或置信度严格更高
            # 防止同源同置信度时误删 gold 期望的粗标签（如 #395 size_fit_problem）
            coarse_source = str(coarse.get("source_detail") or "").strip()
            fine_source = str(fine.get("source_detail") or "").strip()
            same_source = coarse_source == fine_source
            fine_strictly_higher_conf = _CONFIDENCE_ORDER.get(fine_confidence, 0) > _CONFIDENCE_ORDER.get(coarse_confidence, 0)
            if same_source and not fine_strictly_higher_conf:
                # 同源同置信度 → 不去重，避免把 gold 认可的粗标签错误删除
                continue

            # 全部条件满足 → 删除粗标签
            to_remove.add(i)
            audit_records.append({
                **coarse,
                "deduplication_applied": True,
                "deduplication_reason": "coarse_label_replaced_by_fine_label",
                "deduped_by_label": fine_canonical,
                "evidence_overlap": _describe_overlap(coarse_evidence, fine_evidence),
                "dedup_ruleset_version": DEDUP_RULESET_VERSION,
            })
            logger.debug(
                "label_deduplication: removed %s (replaced by %s), overlap=%s",
                coarse_canonical, fine_canonical,
                _describe_overlap(coarse_evidence, fine_evidence),
            )
            break  # 该粗标签已匹配，跳出内层循环

    display = [occ for idx, occ in enumerate(occurrences) if idx not in to_remove]
    return display, audit_records


# ---------------------------------------------------------------------------
# D1 语义守卫：not_breathable 环境高温否决
# ---------------------------------------------------------------------------

# 出汗相关词（仅由这些词触发的 not_breathable 需要审查环境上下文）
_SWEAT_WORDS_PATTERN = re.compile(
    r"\b(?:sweat|sweaty|sweating|break\s+a\s+sweat)\b",
    re.IGNORECASE,
)

# 环境高温 / 热源上下文（出汗来自环境而非产品透气性差）
_ENV_HEAT_PATTERN = re.compile(
    r"\b(?:oven|kitchen|cooking|already\s+(?:warm|hot)|hot\s+room|"
    r"it\s+was\s+(?:pretty\s+)?warm\s+in)\b",
    re.IGNORECASE,
)

# 明确的产品透气性否定证据（有此证据时 guard 不否决）
_EXPLICIT_BREATHABILITY_NEGATION = re.compile(
    r"\b(?:not\s+breathable|doesn['’]t\s+breathe|do\s+not\s+breathe|"
    r"no\s+ventilation|poor\s+breathability)\b",
    re.IGNORECASE,
)


def _not_breathable_env_heat_guard(occurrence: dict[str, Any], content: str) -> bool:
    """否决因环境高温出汗而误标的 not_breathable.

    通用条件（不做 row id / fixture 文本硬编码）：
    1. 候选标签是 not_breathable
    2. 证据仅由出汗词触发
    3. 邻近上下文有环境高温/热源语义
    4. 没有明确的产品透气性否定证据

    Returns:
        True 表示应否决该标签，False 表示保留。
    """
    canonical = str(occurrence.get("canonical_label_key") or "").strip()
    if canonical != "not_breathable":
        return False

    evidence = str(occurrence.get("evidence_span") or "").strip()
    if not evidence:
        return False

    # 条件 1：证据仅由出汗词触发
    if not _SWEAT_WORDS_PATTERN.search(evidence):
        return False

    # 条件 2：邻近上下文有环境高温语义
    if not _ENV_HEAT_PATTERN.search(content):
        return False

    # 条件 3：没有明确的产品透气性否定证据（有此证据时不否决）
    if _EXPLICIT_BREATHABILITY_NEGATION.search(content):
        return False

    logger.debug(
        "semantic_guard: vetoed not_breathable — sweat evidence in env heat context, "
        "no explicit breathability negation. evidence=%r",
        evidence[:120],
    )
    return True


# ---------------------------------------------------------------------------
# 统一入口：去重 + 语义守卫
# ---------------------------------------------------------------------------

def apply_label_postprocessing(
    occurrences: list[dict[str, Any]],
    content: str = "",
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """对 occurrence 列表统一应用去重和语义守卫.

    这是 iter_*_occurrences 应该调用的统一入口。
    调用顺序：先语义守卫（否决误标），再去重（删粗细重复）。

    Args:
        occurrences: 已投影的 occurrence 列表
        content: 原始评论文本

    Returns:
        (final_occurrences, audit_records)
    """
    if not occurrences:
        return [], []

    # Step 1：D1 语义守卫（只否决）
    if _is_semantic_guard_enabled():
        guarded: list[dict[str, Any]] = []
        for occ in occurrences:
            if _not_breathable_env_heat_guard(occ, content):
                continue  # 否决
            guarded.append(occ)
    else:
        guarded = list(occurrences)

    # Step 2：粗细去重
    deduped, audit = deduplicate_coarse_occurrences(guarded, content)

    return deduped, audit
