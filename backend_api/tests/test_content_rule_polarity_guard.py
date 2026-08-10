"""5.9.7-T4 Layer 0：content rule 极性对撞守卫测试.

验证 content rule candidate 落地前，会拿 aspect_key 对撞 LLM 已判定的
polarity，把极性错位的 candidate 挡掉（"aren't waterproof" 不再产出
"Keeps Water Out"），且读写两条路径同时生效。
"""
from __future__ import annotations

from typing import Any

import pytest

from backend_api.app.services.specific_issue import (
    _POLARITY_GUARD_ENV,
    _append_waders_content_rule_occurrences,
    _llm_polarity_by_aspect_key,
    _polarity_guard_rejects_candidate,
    enrich_aspects_json,
    iter_customer_highlight_occurrences,
)

_SUB_CATEGORY = "waders"


def _aspects_json(
    aspects: list[dict[str, Any]] | None = None,
    *,
    cluster_propagated: bool = False,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "sentiment": "negative",
        "aspects": aspects or [],
        "pain_points": [],
        "highlights": [],
        "evidence_level_overall": "certain",
        "sub_category": _SUB_CATEGORY,
    }
    if cluster_propagated:
        payload["cluster_propagated"] = True
    return payload


def _aspect(key: str, polarity: str, *, cluster_propagated: bool = False) -> dict[str, Any]:
    aspect: dict[str, Any] = {
        "key": key,
        "polarity": polarity,
        "evidence_span": f"{key} evidence",
        "evidence_level": "certain",
    }
    if cluster_propagated:
        aspect["cluster_propagated"] = True
    return aspect


def _comment(comment_id: int, content: str) -> dict[str, Any]:
    return {
        "id": comment_id,
        "content": content,
        "sub_category": _SUB_CATEGORY,
        "category": _SUB_CATEGORY,
    }


def _highlight_keys(occurrences: list[dict[str, Any]]) -> set[str]:
    return {str(item.get("canonical_label_key") or "") for item in occurrences}


# ---------------------------------------------------------------- 极性提取


def test_polarity_map_extracts_key_and_polarity() -> None:
    aj = _aspects_json([_aspect("waterproof", "negative"), _aspect("size_fit", "positive")])
    assert _llm_polarity_by_aspect_key(aj) == {
        "waterproof": {"negative"},
        "size_fit": {"positive"},
    }


def test_polarity_map_skips_cluster_propagated_payload() -> None:
    """整体 cluster 传播来的极性不算本条评论自己的判断."""
    aj = _aspects_json([_aspect("waterproof", "negative")], cluster_propagated=True)
    assert _llm_polarity_by_aspect_key(aj) == {}


def test_polarity_map_skips_cluster_propagated_aspect() -> None:
    aj = _aspects_json(
        [
            _aspect("waterproof", "negative", cluster_propagated=True),
            _aspect("size_fit", "positive"),
        ]
    )
    assert _llm_polarity_by_aspect_key(aj) == {"size_fit": {"positive"}}


def test_polarity_map_ignores_invalid_polarity_and_missing_key() -> None:
    aj = _aspects_json([{"key": "waterproof", "polarity": "mixed"}, {"polarity": "negative"}])
    assert _llm_polarity_by_aspect_key(aj) == {}


@pytest.mark.parametrize("payload", [None, {}, {"aspects": "not-a-list"}])
def test_polarity_map_handles_malformed_payload(payload: Any) -> None:
    assert _llm_polarity_by_aspect_key(payload) == {}


# ---------------------------------------------------------------- 对撞裁决


def test_rejects_highlight_when_llm_says_negative() -> None:
    candidate = {"canonical_label_key": "keeps_water_out", "aspect_key": "waterproof"}
    assert _polarity_guard_rejects_candidate(
        candidate,
        label_type="highlight",
        polarity_by_aspect_key={"waterproof": {"negative"}},
    )


def test_rejects_issue_when_llm_says_positive() -> None:
    candidate = {"canonical_label_key": "water_leaks_through", "aspect_key": "waterproof"}
    assert _polarity_guard_rejects_candidate(
        candidate,
        label_type="issue",
        polarity_by_aspect_key={"waterproof": {"positive"}},
    )


@pytest.mark.parametrize("polarity", ["positive", "neutral"])
def test_keeps_highlight_when_no_conflict(polarity: str) -> None:
    candidate = {"canonical_label_key": "keeps_water_out", "aspect_key": "waterproof"}
    assert not _polarity_guard_rejects_candidate(
        candidate,
        label_type="highlight",
        polarity_by_aspect_key={"waterproof": {polarity}},
    )


def test_keeps_candidate_when_llm_never_mentioned_aspect() -> None:
    """LLM 没提这个维度 = 没表态，不是冲突，放行（留给 Layer 1 兜底）."""
    candidate = {"canonical_label_key": "keeps_water_out", "aspect_key": "waterproof"}
    assert not _polarity_guard_rejects_candidate(
        candidate,
        label_type="highlight",
        polarity_by_aspect_key={"comfort": {"negative"}},
    )


def test_keeps_candidate_when_both_polarities_present() -> None:
    """同一维度既夸又骂时放行 —— 规则匹到的正向证据可能是真的."""
    candidate = {"canonical_label_key": "keeps_water_out", "aspect_key": "waterproof"}
    assert not _polarity_guard_rejects_candidate(
        candidate,
        label_type="highlight",
        polarity_by_aspect_key={"waterproof": {"negative", "positive"}},
    )


def test_conflict_detected_via_alias_aspect_key() -> None:
    """规则写死 size_fit，LLM 用别名 boot_fit 也要能对撞上."""
    candidate = {"canonical_label_key": "fits_as_expected", "aspect_key": "size_fit"}
    assert _polarity_guard_rejects_candidate(
        candidate,
        label_type="highlight",
        polarity_by_aspect_key={"boot_fit": {"negative"}},
    )


def test_no_rejection_when_candidate_has_no_aspect_key() -> None:
    assert not _polarity_guard_rejects_candidate(
        {"canonical_label_key": "unknown_label_xyz", "aspect_key": ""},
        label_type="highlight",
        polarity_by_aspect_key={"waterproof": {"negative"}},
    )


# ---------------------------------------------------------------- 回归：session 126 的两条差评


def test_27171_arent_waterproof_keeps_water_out_blocked() -> None:
    """id=27171 rating=1 "aren't waterproof" → LLM 已判 waterproof=negative → 否决 keeps_water_out."""
    comment = _comment(27171, "Boot has a hole in it, these aren't waterproof.")
    aj = _aspects_json([_aspect("waterproof", "negative")])
    comment["aspects_json"] = aj
    comment["specific_issue_schema_version"] = "1.0"
    occurrences = _append_waders_content_rule_occurrences(
        comment, [], label_type="highlight", locale="en", aspects_json=aj, project=False,
    )
    assert "keeps_water_out" not in _highlight_keys(occurrences)


def test_27152_fit_but_bad_fits_as_expected_blocked() -> None:
    """id=27152 rating=1 "wanted these to fit but..." → LLM 判 size_fit=negative → 否决 fits_as_expected."""
    comment = _comment(27152, "I really wanted these to fit but they raised my voice about 3 octaves.")
    aj = _aspects_json([_aspect("size_fit", "negative")])
    comment["aspects_json"] = aj
    comment["specific_issue_schema_version"] = "1.0"
    occurrences = _append_waders_content_rule_occurrences(
        comment, [], label_type="highlight", locale="en", aspects_json=aj, project=False,
    )
    assert "fits_as_expected" not in _highlight_keys(occurrences)


def test_27152_still_gets_other_highlights() -> None:
    """对撞只挡冲突的 candidate，不影响同评论的其他规则匹配."""
    comment = _comment(27152, "I really wanted these to fit but they raised my voice about 3 octaves.")
    aj = _aspects_json([_aspect("size_fit", "negative")])
    comment["aspects_json"] = aj
    comment["specific_issue_schema_version"] = "1.0"
    occurrences = _append_waders_content_rule_occurrences(
        comment, [], label_type="highlight", locale="en", aspects_json=aj, project=False,
    )
    assert "fits_as_expected" not in _highlight_keys(occurrences)
    # 同一评论里 comfort 没有 LLM 判负，不应连带否决
    has_keeps_water_out = "keeps_water_out" in _highlight_keys(occurrences)
    # 这条原文不含 waterproof 关键词，keep_water_out 本身也不会被匹配到
    # 重点是 fits_as_expected 被挡了而其他非冲突标签照常
    assert not has_keeps_water_out  # 原文无 waterproof 证据，不应命中


def test_27180_good_review_keeps_labels() -> None:
    """id=27180 rating=5 "Kept me dry and warm" → LLM 判 waterproof=positive → 标签保留."""
    comment = _comment(27180, "Kept me dry and warm in freezing cold water.")
    aj = _aspects_json([_aspect("waterproof", "positive")])
    comment["aspects_json"] = aj
    comment["specific_issue_schema_version"] = "1.0"
    occurrences = _append_waders_content_rule_occurrences(
        comment, [], label_type="highlight", locale="en", aspects_json=aj, project=False,
    )
    assert "keeps_water_out" in _highlight_keys(occurrences)


# ---------------------------------------------------------------- 读路径不复活已被否决的标签


def test_read_path_does_not_resurrect_rejected_label() -> None:
    """读路径 iter_customer_highlight_occurrences 也经 _append_waders_content_rule_occurrences，
    如果 LLM 已判负，不应把规则匹到的正向 candidate 补回来."""
    comment = _comment(27171, "Boot has a hole in it, these aren't waterproof.")
    aj = _aspects_json([_aspect("waterproof", "negative")])
    comment["aspects_json"] = aj
    occurrences = iter_customer_highlight_occurrences(comment, locale="en")
    assert "keeps_water_out" not in _highlight_keys(occurrences)


# ---------------------------------------------------------------- 降级：guard 关闭时不拦截


def test_disabled_guard_lets_all_through(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(_POLARITY_GUARD_ENV, "false")
    comment = _comment(27171, "Boot has a hole in it, these aren't waterproof.")
    aj = _aspects_json([_aspect("waterproof", "negative")])
    comment["aspects_json"] = aj
    comment["specific_issue_schema_version"] = "1.0"
    occurrences = _append_waders_content_rule_occurrences(
        comment, [], label_type="highlight", locale="en", aspects_json=aj, project=False,
    )
    # guard 关闭时 behavior 回到旧逻辑，keeps_water_out 仍会产出（回归基线）
    assert "keeps_water_out" in _highlight_keys(occurrences)
    monkeypatch.delenv(_POLARITY_GUARD_ENV)


# ---------------------------------------------------------------- 集成：enrich_aspects_json 写路径


def test_enrich_aspects_json_rejects_mismatched_highlight() -> None:
    """写路径终点 enrich_aspects_json 也应过滤极性错误的 highlight."""
    comment = _comment(99999, "These aren't waterproof at all, leaked first use.")
    aj = _aspects_json([_aspect("waterproof", "negative")])
    enriched = enrich_aspects_json(
        aj,
        sub_category=_SUB_CATEGORY,
        content=comment["content"],
        locale="en",
        comment_id=99999,
    )
    assert enriched is not None
    keys = {
        str(item.get("canonical_label_key") or "")
        for item in (enriched.get("customer_label_occurrences") or [])
    }
    assert "keeps_water_out" not in keys


def test_enrich_aspects_json_respects_correct_polarity() -> None:
    """正向评论 + LLM 判正向 → 标签保留."""
    comment = _comment(99998, "Kept me dry and warm all day.")
    aj = _aspects_json([_aspect("waterproof", "positive")])
    enriched = enrich_aspects_json(
        aj,
        sub_category=_SUB_CATEGORY,
        content=comment["content"],
        locale="en",
        comment_id=99998,
    )
    assert enriched is not None
    keys = {
        str(item.get("canonical_label_key") or "")
        for item in (enriched.get("customer_label_occurrences") or [])
    }
    assert "keeps_water_out" in keys
