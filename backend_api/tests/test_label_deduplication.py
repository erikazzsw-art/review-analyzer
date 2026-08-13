"""阶段 A Task A-3 单元测试：证据级去重 + D1 语义守卫.

测试覆盖：
1. 纯辅助函数（aspect 兼容 / 置信度比较 / 证据重叠 / 来源权威性）
2. 去重机制边缘情况（空列表 / 单项 / 无关系时 no-op）
3. not_breathable 环境高温 guard
4. 明确产品透气性否定 → guard 不否决

注意（2026-08-13 A-5）：size 域粗细标签已统一为 size_fit_problem，
COARSE_TO_FINE_LABELS 暂时清空，原 size_fit_problem → {runs_too_small, runs_too_large}
关系作废。因此去重机制当前是 no-op，相关"粗细去重"场景测试已移除，
待未来出现经真实标注验证的新粗细关系时再补充。
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from backend_api.app.services.label_deduplication import (  # noqa: E402
    COARSE_TO_FINE_LABELS,
    DEDUP_RULESET_VERSION,
    SEMANTIC_GUARD_RULESET_VERSION,
    _aspect_keys_compatible,
    _confidence_not_lower,
    _evidence_overlaps,
    _not_breathable_env_heat_guard,
    _source_priority,
    apply_label_postprocessing,
    deduplicate_coarse_occurrences,
)

# ===================================================================
# Helpers
# ===================================================================

def _make_occ(**overrides):
    """Create a minimal occurrence dict for testing."""
    base = {
        "type": "issue",
        "canonical_label_key": "size_fit_problem",
        "canonical_issue_key": "size_fit_problem",
        "aspect_key": "size_fit",
        "evidence_span": "runs too small",
        "evidence_start": 0,
        "evidence_end": 13,
        "confidence": "high",
        "source_detail": "waders_content_rule",
        "source_review_allowed": True,
    }
    base.update(overrides)
    return base


# ===================================================================
# COARSE_TO_FINE_LABELS
# ===================================================================

def test_coarse_to_fine_labels_version():
    """关系映射版本号应为 A-3 日期."""
    assert DEDUP_RULESET_VERSION == "2026-08-12-a3-coarse-fine-dedup"
    assert SEMANTIC_GUARD_RULESET_VERSION == "2026-08-12-a3-d1-not-breathable-guard"


def test_coarse_to_fine_labels_empty_after_size_unification():
    """A-5：size 域统一为 size_fit_problem，粗细关系暂时清空."""
    # runs_too_small / runs_too_large 已退役，原 size_fit_problem → {runs_too_small, runs_too_large}
    # 关系作废。未来若其它域出现经真实标注验证的粗细关系再追加。
    assert COARSE_TO_FINE_LABELS == {}


# ===================================================================
# _aspect_keys_compatible
# ===================================================================

def test_aspect_keys_compatible_same():
    """相同 aspect_key 应兼容."""
    assert _aspect_keys_compatible("size_fit_problem", "size_fit", "size_fit")


def test_aspect_keys_compatible_family():
    """同一兼容家族内的不同 aspect_key 应兼容."""
    # size_fit vs boot_fit, both in size_fit_problem compatible set
    assert _aspect_keys_compatible("size_fit_problem", "boot_fit", "size_fit")
    assert _aspect_keys_compatible("size_fit_problem", "size_fit", "boot_fit")


def test_aspect_keys_compatible_empty():
    """任一方空 aspect_key 应放行."""
    assert _aspect_keys_compatible("size_fit_problem", "", "size_fit")
    assert _aspect_keys_compatible("size_fit_problem", "size_fit", "")
    assert _aspect_keys_compatible("size_fit_problem", "", "")


def test_aspect_keys_compatible_unknown_coarse():
    """不在兼容家族 lookup 中的粗标签，只允许相同或空."""
    assert _aspect_keys_compatible("quality_problem", "build_quality", "build_quality")
    assert not _aspect_keys_compatible("quality_problem", "build_quality", "durability")


# ===================================================================
# _confidence_not_lower
# ===================================================================

def test_confidence_not_lower():
    """置信度比较."""
    assert _confidence_not_lower("high", "medium")
    assert _confidence_not_lower("high", "high")
    assert not _confidence_not_lower("medium", "high")
    assert _confidence_not_lower("medium", "low")


# ===================================================================
# _evidence_overlaps
# ===================================================================

def test_evidence_overlap_interval():
    """区间重叠."""
    assert _evidence_overlaps(
        "boots run small", "run small",
        0, 16, 6, 15,
    )


def test_evidence_overlap_containment():
    """文本包含."""
    assert _evidence_overlaps(
        "boots run small purchase larger size", "run small",
        None, None, None, None,
    )


def test_evidence_overlap_exact():
    """完全相同的 evidence."""
    assert _evidence_overlaps(
        "runs too small", "runs too small",
        None, None, None, None,
    )


def test_evidence_no_overlap():
    """不重叠."""
    assert not _evidence_overlaps(
        "wish it got a female body a little more snug",
        "size up",
        None, None, None, None,
    )


def test_evidence_empty():
    """空 evidence 不应判定为重叠."""
    assert not _evidence_overlaps("", "run small", None, None, None, None)
    assert not _evidence_overlaps("run small", "", None, None, None, None)


# ===================================================================
# deduplicate_coarse_occurrences
# ===================================================================

def test_dedup_empty_list():
    """空列表."""
    display, audit = deduplicate_coarse_occurrences([], "")
    assert display == []
    assert audit == []


def test_dedup_single_item():
    """单项列表."""
    occ = [_make_occ()]
    display, audit = deduplicate_coarse_occurrences(occ, "")
    assert len(display) == 1
    assert len(audit) == 0


def test_dedup_noop_when_no_relationship():
    """A-5：COARSE_TO_FINE_LABELS 为空时，去重是 no-op，所有 occurrence 原样保留."""
    occ = [
        _make_occ(
            canonical_label_key="size_fit_problem",
            evidence_span="runs too small",
            source_detail="llm_canonical_hint",
        ),
        _make_occ(
            canonical_label_key="size_fit_problem",
            evidence_span="runs too small",
            source_detail="waders_content_rule",
        ),
    ]
    display, audit = deduplicate_coarse_occurrences(occ, "test")
    assert len(display) == 2
    assert len(audit) == 0
    assert [o["canonical_label_key"] for o in display] == ["size_fit_problem", "size_fit_problem"]


# ===================================================================
# _not_breathable_env_heat_guard
# ===================================================================

ROW_378_CONTENT = (
    "threw it on in my kitchen while I was cooking and had oven on "
    "so it was pretty warm in my kitchen already and I was only wear "
    "shorts and was already starting to break a sweat"
)


def test_guard_not_not_breathable():
    """非 not_breathable 标签 → 不否决."""
    occ = {"canonical_label_key": "size_fit_problem", "evidence_span": "too big"}
    assert not _not_breathable_env_heat_guard(occ, ROW_378_CONTENT)


def test_guard_no_sweat_evidence():
    """证据不含出汗词 → 不否决."""
    occ = {
        "canonical_label_key": "not_breathable",
        "evidence_span": "don't breathe at all",
    }
    assert not _not_breathable_env_heat_guard(occ, ROW_378_CONTENT)


def test_guard_env_heat_veto():
    """出汗词 + 环境高温 + 无产品透气性否定 → 否决."""
    occ = {
        "canonical_label_key": "not_breathable",
        "evidence_span": "starting to break a sweat",
    }
    assert _not_breathable_env_heat_guard(occ, ROW_378_CONTENT)


def test_guard_explicit_breathability_negation_no_veto():
    """有明确产品透气性否定 → 不否决."""
    occ = {
        "canonical_label_key": "not_breathable",
        "evidence_span": "I sweat so much",
    }
    content = "these waders do not breathe at all, I sweat so much in my kitchen"
    assert not _not_breathable_env_heat_guard(occ, content)


def test_guard_no_env_heat():
    """有出汗词但无环境高温 → 不否决."""
    occ = {
        "canonical_label_key": "not_breathable",
        "evidence_span": "made me sweat a lot",
    }
    content = "I wore these waders fishing and they made me sweat a lot, not breathable at all"
    # 无 kitchen/oven/cooking 上下文 → guard 不应否决
    assert not _not_breathable_env_heat_guard(occ, content)


def test_guard_empty_evidence():
    """空证据 → 不否决."""
    occ = {"canonical_label_key": "not_breathable", "evidence_span": ""}
    assert not _not_breathable_env_heat_guard(occ, ROW_378_CONTENT)


def test_guard_oven_context():
    """oven 上下文 + sweat → 否决."""
    occ = {
        "canonical_label_key": "not_breathable",
        "evidence_span": "got sweaty",
    }
    content = "had the oven on and got sweaty trying them on"
    assert _not_breathable_env_heat_guard(occ, content)


# ===================================================================
# apply_label_postprocessing (统一入口)
# ===================================================================

def test_postprocessing_applies_guard_only():
    """A-5：粗细关系清空后，apply_label_postprocessing 只做 D1 语义守卫，不再去重."""
    occ = [
        _make_occ(
            canonical_label_key="size_fit_problem",
            evidence_span="runs too small",
            source_detail="llm_canonical_hint",
        ),
        {
            "type": "issue",
            "canonical_label_key": "not_breathable",
            "canonical_issue_key": "not_breathable",
            "aspect_key": "breathability",
            "evidence_span": "break a sweat",
            "confidence": "high",
            "source_detail": "waders_content_rule",
            "source_review_allowed": True,
        },
    ]
    content = "kitchen was hot from cooking and I started to break a sweat"
    display, audit = apply_label_postprocessing(occ, content)
    # not_breathable 被 D1 guard 否决；size_fit_problem 原样保留（无粗细关系去重）
    assert len(display) == 1
    assert display[0]["canonical_label_key"] == "size_fit_problem"
    assert audit == []


# ===================================================================
# 回归：row-378
# ===================================================================

def test_row378_scenario():
    """row-378：not_breathable 被 D1 环境高温 guard 否决."""
    occ = {
        "canonical_label_key": "not_breathable",
        "evidence_span": "break a sweat",
    }
    content = (
        "threw it on in my kitchen while I was cooking and had oven on "
        "so it was pretty warm and I was starting to break a sweat"
    )
    assert _not_breathable_env_heat_guard(occ, content)


def test_row378_size_fit_problem_not_affected():
    """row-378 的 size_fit_problem 不被 guard 影响（guard 只管 not_breathable）."""
    occ = {
        "canonical_label_key": "size_fit_problem",
        "evidence_span": "got size 9",
    }
    assert not _not_breathable_env_heat_guard(occ, ROW_378_CONTENT)


# ===================================================================
# _source_priority
# ===================================================================

def test_source_priority_llm_highest():
    """LLM 来源权威性最高."""
    assert _source_priority("llm_canonical_hint") == 3
    assert _source_priority("regex_alias_rule") == 2
    assert _source_priority("waders_content_rule") == 1
    assert _source_priority("sentiment_recovery_rule") == 1
    assert _source_priority("unknown") == 0
    assert _source_priority("") == 0
