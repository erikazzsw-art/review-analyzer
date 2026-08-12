"""阶段 A Task A-3 单元测试：证据级去重 + D1 语义守卫.

测试覆盖：
1. 同 evidence 粗细去重
2. 同 review 不同 evidence → 不去重
3. 不同 label_type → 不去重
4. aspect_key 兼容但不同源 → 去重
5. 同源同置信度 → 不去重（防 FN 回归）
6. evidence 无法定位 → 不去重
7. 去重函数幂等
8. not_breathable 环境高温 guard
9. 明确产品透气性否定 → guard 不否决
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


def test_coarse_to_fine_only_validated():
    """第一版只启用 A-2 已验证的关系."""
    assert "size_fit_problem" in COARSE_TO_FINE_LABELS
    assert "runs_too_small" in COARSE_TO_FINE_LABELS["size_fit_problem"]
    assert "runs_too_large" in COARSE_TO_FINE_LABELS["size_fit_problem"]
    # 推测关系不应存在
    assert "quality_problem" not in COARSE_TO_FINE_LABELS
    assert "breaks_easily" not in COARSE_TO_FINE_LABELS


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

def test_dedup_same_evidence():
    """同 evidence 同 aspect → 去重."""
    occ = [
        _make_occ(
            canonical_label_key="size_fit_problem",
            evidence_span="runs too small",
            source_detail="llm_canonical_hint",  # different source!
        ),
        _make_occ(
            canonical_label_key="runs_too_small",
            evidence_span="runs too small",
            source_detail="waders_content_rule",
        ),
    ]
    display, audit = deduplicate_coarse_occurrences(occ, "test")
    assert len(display) == 1, f"Expected 1 kept, got {len(display)}"
    assert display[0]["canonical_label_key"] == "runs_too_small"
    assert len(audit) == 1
    assert audit[0]["deduplication_applied"] is True
    assert audit[0]["deduped_by_label"] == "runs_too_small"


def test_dedup_runs_too_large():
    """runs_too_large 也能去重 size_fit_problem."""
    occ = [
        _make_occ(
            canonical_label_key="size_fit_problem",
            evidence_span="way too big",
            source_detail="llm_canonical_hint",
        ),
        _make_occ(
            canonical_label_key="runs_too_large",
            evidence_span="way too big",
            source_detail="waders_content_rule",
        ),
    ]
    display, audit = deduplicate_coarse_occurrences(occ, "test")
    assert len(display) == 1
    assert display[0]["canonical_label_key"] == "runs_too_large"


def test_dedup_different_evidence_same_review():
    """同 review 不同 evidence → 不去重."""
    occ = [
        _make_occ(
            canonical_label_key="size_fit_problem",
            evidence_span="belt loops are too high",
            evidence_start=0, evidence_end=22,
            source_detail="llm_canonical_hint",
        ),
        _make_occ(
            canonical_label_key="runs_too_small",
            evidence_span="size up",
            evidence_start=50, evidence_end=57,
            source_detail="waders_content_rule",
        ),
    ]
    display, audit = deduplicate_coarse_occurrences(occ, "test")
    assert len(display) == 2, "Different evidence should both be kept"
    assert len(audit) == 0


def test_dedup_different_label_type():
    """不同 label_type → 不去重."""
    occ = [
        _make_occ(
            canonical_label_key="size_fit_problem",
            evidence_span="runs too small",
        ),
        _make_occ(
            type="highlight",
            canonical_label_key="runs_too_small",
            evidence_span="runs too small",
        ),
    ]
    display, audit = deduplicate_coarse_occurrences(occ, "test")
    assert len(display) == 2


def test_dedup_same_source_same_confidence():
    """同源同置信度 → 不去重（防 #395 FN 回归）."""
    occ = [
        _make_occ(
            canonical_label_key="size_fit_problem",
            evidence_span="too small",
            source_detail="waders_content_rule",
            confidence="high",
        ),
        _make_occ(
            canonical_label_key="runs_too_small",
            evidence_span="too small",
            source_detail="waders_content_rule",
            confidence="high",
        ),
    ]
    display, audit = deduplicate_coarse_occurrences(occ, "test")
    assert len(display) == 2, "Same source + same confidence → keep both"
    assert len(audit) == 0


def test_dedup_same_source_higher_fine_confidence():
    """同源但细标签置信度更高 → 去重."""
    occ = [
        _make_occ(
            canonical_label_key="size_fit_problem",
            evidence_span="too small",
            source_detail="waders_content_rule",
            confidence="medium",
        ),
        _make_occ(
            canonical_label_key="runs_too_small",
            evidence_span="too small",
            source_detail="waders_content_rule",
            confidence="high",
        ),
    ]
    display, audit = deduplicate_coarse_occurrences(occ, "test")
    assert len(display) == 1
    assert display[0]["canonical_label_key"] == "runs_too_small"


def test_dedup_no_evidence_overlap():
    """evidence 不重叠 → 不去重."""
    occ = [
        _make_occ(
            canonical_label_key="size_fit_problem",
            evidence_span="belt loops too high",
            evidence_start=0, evidence_end=22,
            source_detail="llm_canonical_hint",
        ),
        _make_occ(
            canonical_label_key="runs_too_small",
            evidence_span="boots run small",
            evidence_start=50, evidence_end=65,
            source_detail="waders_content_rule",
        ),
    ]
    display, audit = deduplicate_coarse_occurrences(occ, "test")
    assert len(display) == 2
    assert len(audit) == 0


def test_dedup_idempotent():
    """去重应幂等."""
    occ = [
        _make_occ(
            canonical_label_key="size_fit_problem",
            source_detail="llm_canonical_hint",
        ),
        _make_occ(
            canonical_label_key="runs_too_small",
            source_detail="waders_content_rule",
        ),
    ]
    display1, _ = deduplicate_coarse_occurrences(occ, "test")
    display2, _ = deduplicate_coarse_occurrences(display1, "test")
    assert len(display1) == len(display2)
    assert [d["canonical_label_key"] for d in display1] == [d["canonical_label_key"] for d in display2]


def test_dedup_different_aspect_keys():
    """不同 aspect_key 家族 → 不去重."""
    occ = [
        _make_occ(
            canonical_label_key="size_fit_problem",
            aspect_key="waterproof",
            source_detail="llm_canonical_hint",
        ),
        _make_occ(
            canonical_label_key="runs_too_small",
            aspect_key="size_fit",
            source_detail="waders_content_rule",
        ),
    ]
    display, audit = deduplicate_coarse_occurrences(occ, "test")
    # waterproof is NOT in compatible set for size_fit_problem → should not dedup
    assert len(display) == 2
    assert len(audit) == 0


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
    occ = {"canonical_label_key": "runs_too_large", "evidence_span": "too big"}
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

def test_postprocessing_combined():
    """去重 + 守卫组合."""
    occ = [
        _make_occ(
            canonical_label_key="size_fit_problem",
            evidence_span="runs too small",
            source_detail="llm_canonical_hint",
        ),
        _make_occ(
            canonical_label_key="runs_too_small",
            evidence_span="runs too small",
            source_detail="waders_content_rule",
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
    # size_fit_problem 被 runs_too_small 去重
    # not_breathable 被 D1 guard 否决
    assert len(display) == 1
    assert display[0]["canonical_label_key"] == "runs_too_small"
    assert len(audit) == 1  # one dedup audit record


# ===================================================================
# 回归：row-366 / row-386 / row-378
# ===================================================================

def test_row366_scenario():
    """row-366：粗标签 size_fit_problem (LLM) + 细标签 runs_too_small (rule) → 去重."""
    occ = [
        _make_occ(
            canonical_label_key="size_fit_problem",
            aspect_key="boot_fit",
            evidence_span="I should have got one more size up for shoes",
            source_detail="llm_canonical_hint",
        ),
        _make_occ(
            canonical_label_key="runs_too_small",
            aspect_key="size_fit",
            evidence_span="size up",
            source_detail="waders_content_rule",
        ),
    ]
    display, audit = deduplicate_coarse_occurrences(occ, "test")
    # boot_fit size_fit_problem overlaps with runs_too_small → removed
    assert len(display) == 1
    assert display[0]["canonical_label_key"] == "runs_too_small"


def test_row386_scenario():
    """row-386：boot_fit size_fit_problem + runs_too_small → 去重."""
    occ = [
        _make_occ(
            canonical_label_key="size_fit_problem",
            aspect_key="boot_fit",
            evidence_span="BOOTS RUN SMALL. PURCHASE A LARGER SIZE.",
            source_detail="llm_canonical_hint",
        ),
        _make_occ(
            canonical_label_key="runs_too_small",
            aspect_key="size_fit",
            evidence_span="RUN SMALL",
            source_detail="waders_content_rule",
        ),
    ]
    display, audit = deduplicate_coarse_occurrences(occ, "test")
    assert len(display) == 1
    assert display[0]["canonical_label_key"] == "runs_too_small"


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


def test_row378_runs_too_large_not_affected():
    """row-378 的 runs_too_large 不被 guard 影响（guard 只管 not_breathable）."""
    occ = {
        "canonical_label_key": "runs_too_large",
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
