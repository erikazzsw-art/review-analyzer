"""5.9.7: 聚类评分守卫测试.

验证 propagate_cluster_results() 在代表与成员评分差距过大时
拒绝传播标签+证据，防止 cluster 传播污染。
"""
from __future__ import annotations

from typing import Any

from backend_api.app.services.clustering import (
    RATING_GUARD_THRESHOLD,
    ClusterResult,
    propagate_cluster_results,
)


def _make_llm_result(
    *,
    sentiment: str = "positive",
    aspects: list[dict[str, Any]] | None = None,
    pain_points: list[dict[str, Any]] | None = None,
    highlights: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """构造一条 LLM 分析结果."""
    return {
        "sentiment": sentiment,
        "aspects": aspects or [],
        "pain_points": pain_points or [],
        "highlights": highlights or [],
        "evidence_level_overall": "high",
        "prompt_version": "v5.9.7-test",
    }


def _make_comment(comment_id: int, rating: float | None = 5) -> dict[str, Any]:
    """构造一条评论数据（含 rating）."""
    return {
        "id": comment_id,
        "content": f"test review content {comment_id}",
        "rating": rating,
    }


def _make_cluster(
    label: int, member_ids: list[int], rep_id: int
) -> ClusterResult:
    """构造一个单簇的 ClusterResult."""
    return ClusterResult(
        clusters={label: member_ids},
        representatives=[rep_id],
        noise_ids=[],
    )


class TestRatingGuard:
    """评分守卫：阻挡好评代表 → 差评成员的标签传播."""

    def test_positive_rep_negative_member_blocked(self) -> None:
        """好评代表(5★) + 差评成员(1★) → 不传播，标记 needs_llm."""
        rep_id = 100
        member_id = 101
        cluster = _make_cluster(0, [rep_id, member_id], rep_id)

        llm_comments = [_make_comment(rep_id, rating=5)]
        llm_results = [
            _make_llm_result(
                aspects=[{"label": "good_quality", "evidence_span": "works great"}],
                highlights=[{"label": "comfortable", "evidence_span": "very comfy"}],
            )
        ]
        all_comments = [
            _make_comment(rep_id, rating=5),
            _make_comment(member_id, rating=1),
        ]

        results = propagate_cluster_results(
            cluster, llm_comments, llm_results, all_comments,
            rating_guard_threshold=RATING_GUARD_THRESHOLD,
        )

        assert len(results) == 2
        # rep 保留 LLM 原始结果
        assert results[0]["sentiment"] == "positive"
        assert results[0]["aspects"][0]["label"] == "good_quality"
        # 成员被评分守卫拦截
        assert results[1]["needs_llm"] is True
        assert results[1]["reason"] == "rating_mismatch"

    def test_same_rating_normal_propagation(self) -> None:
        """同档评分(5★+5★) → 正常传播标签+证据."""
        rep_id = 200
        member_id = 201
        cluster = _make_cluster(0, [rep_id, member_id], rep_id)

        llm_comments = [_make_comment(rep_id, rating=5)]
        llm_results = [
            _make_llm_result(
                aspects=[{"label": "good_quality", "evidence_span": "works great"}],
            )
        ]
        all_comments = [
            _make_comment(rep_id, rating=5),
            _make_comment(member_id, rating=5),
        ]

        results = propagate_cluster_results(
            cluster, llm_comments, llm_results, all_comments,
            rating_guard_threshold=RATING_GUARD_THRESHOLD,
        )

        assert len(results) == 2
        # rep 保留 LLM 原始结果
        assert results[0]["sentiment"] == "positive"
        # 成员收到传播
        assert results[1]["cluster_propagated"] is True
        assert results[1]["cluster_representative_id"] == rep_id
        assert results[1]["aspects"][0]["label"] == "good_quality"

    def test_adjacent_rating_still_propagates(self) -> None:
        """相邻评分(5★+4★, diff=1) → 正常传播（未达到阈值）."""
        rep_id = 300
        member_id = 301
        cluster = _make_cluster(0, [rep_id, member_id], rep_id)

        llm_comments = [_make_comment(rep_id, rating=5)]
        llm_results = [
            _make_llm_result(
                aspects=[{"label": "good_quality", "evidence_span": "works great"}],
            )
        ]
        all_comments = [
            _make_comment(rep_id, rating=5),
            _make_comment(member_id, rating=4),
        ]

        results = propagate_cluster_results(
            cluster, llm_comments, llm_results, all_comments,
            rating_guard_threshold=RATING_GUARD_THRESHOLD,
        )

        assert len(results) == 2
        assert results[0]["sentiment"] == "positive"
        # diff=1 < 2.0，正常传播
        assert results[1]["cluster_propagated"] is True
        assert results[1]["aspects"][0]["label"] == "good_quality"

    def test_threshold_boundary_diff_equals_threshold_blocked(self) -> None:
        """边界 case: diff=2.0（刚好等于默认阈值）→ 不传播."""
        rep_id = 400
        member_id = 401
        cluster = _make_cluster(0, [rep_id, member_id], rep_id)

        llm_comments = [_make_comment(rep_id, rating=5)]
        llm_results = [_make_llm_result()]
        all_comments = [
            _make_comment(rep_id, rating=5),
            _make_comment(member_id, rating=3),  # diff=2, >= 2.0
        ]

        results = propagate_cluster_results(
            cluster, llm_comments, llm_results, all_comments,
            rating_guard_threshold=RATING_GUARD_THRESHOLD,
        )

        assert results[1]["needs_llm"] is True
        assert results[1]["reason"] == "rating_mismatch"

    def test_threshold_boundary_diff_just_below_propagates(self) -> None:
        """边界 case: diff=0.9 使用 threshold=1.0 → 正常传播."""
        rep_id = 500
        member_id = 501
        cluster = _make_cluster(0, [rep_id, member_id], rep_id)

        llm_comments = [_make_comment(rep_id, rating=4.0)]
        llm_results = [_make_llm_result()]
        all_comments = [
            _make_comment(rep_id, rating=4.0),
            _make_comment(member_id, rating=3.1),  # diff=0.9 < 1.0
        ]

        results = propagate_cluster_results(
            cluster, llm_comments, llm_results, all_comments,
            rating_guard_threshold=1.0,
        )

        assert results[1]["cluster_propagated"] is True

    def test_rep_missing_from_llm_results(self) -> None:
        """代表不在 LLM 结果中 → error: cluster_rep_missing."""
        rep_id = 600
        member_id = 601
        cluster = _make_cluster(0, [rep_id, member_id], rep_id)

        # LLM 结果中不包含 rep_id
        llm_comments = [_make_comment(999, rating=5)]  # unrelated comment
        llm_results = [_make_llm_result()]
        all_comments = [
            _make_comment(rep_id, rating=5),
            _make_comment(member_id, rating=1),
        ]

        results = propagate_cluster_results(
            cluster, llm_comments, llm_results, all_comments,
            rating_guard_threshold=RATING_GUARD_THRESHOLD,
        )

        # 成员因为 rep 缺失而报错
        member_result = results[1]  # member is all_comments[1]
        assert member_result.get("error") == "cluster_rep_missing"

    def test_guard_disabled_via_threshold_none(self) -> None:
        """rating_guard_threshold=None → 守卫关闭，正常传播."""
        rep_id = 700
        member_id = 701
        cluster = _make_cluster(0, [rep_id, member_id], rep_id)

        llm_comments = [_make_comment(rep_id, rating=5)]
        llm_results = [_make_llm_result(
            aspects=[{"label": "test_label", "evidence_span": "test evidence"}],
        )]
        all_comments = [
            _make_comment(rep_id, rating=5),
            _make_comment(member_id, rating=1),  # 本来会被拦截
        ]

        results = propagate_cluster_results(
            cluster, llm_comments, llm_results, all_comments,
            rating_guard_threshold=None,
        )

        # 守卫关闭，即使 diff=4 也正常传播
        assert results[1]["cluster_propagated"] is True
        assert results[1]["aspects"][0]["label"] == "test_label"

    def test_missing_rating_falls_through_to_propagation(self) -> None:
        """成员 rating 缺失 → 不做评分检查，正常传播（相似度守卫仍在）."""
        rep_id = 800
        member_id = 801
        cluster = _make_cluster(0, [rep_id, member_id], rep_id)

        llm_comments = [_make_comment(rep_id, rating=5)]
        llm_results = [_make_llm_result(
            aspects=[{"label": "test_label", "evidence_span": "test evidence"}],
        )]
        all_comments = [
            _make_comment(rep_id, rating=5),
            _make_comment(member_id, rating=None),  # 无 rating
        ]

        results = propagate_cluster_results(
            cluster, llm_comments, llm_results, all_comments,
            rating_guard_threshold=RATING_GUARD_THRESHOLD,
        )

        # rating 缺失不触发守卫，正常传播
        assert results[1]["cluster_propagated"] is True

    def test_rep_missing_rating_falls_through_to_propagation(self) -> None:
        """代表 rating 缺失 → 不做评分检查，正常传播."""
        rep_id = 900
        member_id = 901
        cluster = _make_cluster(0, [rep_id, member_id], rep_id)

        llm_comments = [_make_comment(rep_id, rating=None)]
        llm_results = [_make_llm_result(
            aspects=[{"label": "test_label", "evidence_span": "test evidence"}],
        )]
        all_comments = [
            _make_comment(rep_id, rating=None),
            _make_comment(member_id, rating=1),
        ]

        results = propagate_cluster_results(
            cluster, llm_comments, llm_results, all_comments,
            rating_guard_threshold=RATING_GUARD_THRESHOLD,
        )

        # rep rating 缺失不触发守卫，正常传播
        assert results[1]["cluster_propagated"] is True

    def test_custom_threshold_respected(self) -> None:
        """自定义阈值 threshold=3.0 → diff=2 不拦截."""
        rep_id = 1000
        member_id = 1001
        cluster = _make_cluster(0, [rep_id, member_id], rep_id)

        llm_comments = [_make_comment(rep_id, rating=5)]
        llm_results = [_make_llm_result()]
        all_comments = [
            _make_comment(rep_id, rating=5),
            _make_comment(member_id, rating=2),  # diff=3
        ]

        # threshold=3.0: diff=3 >= 3 → 拦截
        results_strict = propagate_cluster_results(
            cluster, llm_comments, llm_results, all_comments,
            rating_guard_threshold=3.0,
        )
        assert results_strict[1]["needs_llm"] is True

        # threshold=4.0: diff=3 < 4 → 不拦截
        results_loose = propagate_cluster_results(
            cluster, llm_comments, llm_results, all_comments,
            rating_guard_threshold=4.0,
        )
        assert results_loose[1]["cluster_propagated"] is True

    def test_multi_cluster_independent_guarding(self) -> None:
        """多簇场景：每个簇独立评估评分守卫."""
        # Cluster 0: rep=5★, member=2★ → 应被拦截
        # Cluster 1: rep=4★, member=4★ → 应正常传播
        rep0, member0 = 1100, 1101
        rep1, member1 = 1110, 1111

        cluster = ClusterResult(
            clusters={0: [rep0, member0], 1: [rep1, member1]},
            representatives=[rep0, rep1],
            noise_ids=[],
        )

        llm_comments = [
            _make_comment(rep0, rating=5),
            _make_comment(rep1, rating=4),
        ]
        llm_results = [
            _make_llm_result(aspects=[{"label": "cluster0_label", "evidence_span": "e0"}]),
            _make_llm_result(aspects=[{"label": "cluster1_label", "evidence_span": "e1"}]),
        ]
        all_comments = [
            _make_comment(rep0, rating=5),
            _make_comment(member0, rating=2),  # diff=3 → 拦截
            _make_comment(rep1, rating=4),
            _make_comment(member1, rating=4),  # diff=0 → 传播
        ]

        results = propagate_cluster_results(
            cluster, llm_comments, llm_results, all_comments,
            rating_guard_threshold=RATING_GUARD_THRESHOLD,
        )

        assert len(results) == 4
        # rep0: LLM 原始结果
        assert results[0]["sentiment"] == "positive"
        # member0: 被评分守卫拦截
        assert results[1]["needs_llm"] is True
        assert results[1]["reason"] == "rating_mismatch"
        # rep1: LLM 原始结果
        assert results[2]["sentiment"] == "positive"
        # member1: 正常传播
        assert results[3]["cluster_propagated"] is True
        assert results[3]["aspects"][0]["label"] == "cluster1_label"

    def test_noise_points_unaffected_by_rating_guard(self) -> None:
        """噪声点直接走 LLM，不被评分守卫影响."""
        noise_id = 1200
        cluster = ClusterResult(
            clusters={},
            representatives=[],
            noise_ids=[noise_id],
        )

        llm_comments = [_make_comment(noise_id, rating=1)]
        llm_results = [_make_llm_result(
            aspects=[{"label": "noise_label", "evidence_span": "noise evidence"}],
        )]
        all_comments = [_make_comment(noise_id, rating=1)]

        results = propagate_cluster_results(
            cluster, llm_comments, llm_results, all_comments,
            rating_guard_threshold=RATING_GUARD_THRESHOLD,
        )

        # 噪声点保留 LLM 原始结果
        assert len(results) == 1
        assert results[0]["sentiment"] == "positive"
        assert results[0]["aspects"][0]["label"] == "noise_label"


class TestRatingGuardIntegration:
    """评分守卫与现有质量门控的交互."""

    def test_similarity_gate_takes_precedence_over_rating_guard(self) -> None:
        """低相似度簇优先被 similarity gate 拦截，reason 为 low_cluster_similarity."""
        rep_id = 1300
        member_id = 1301
        cluster = _make_cluster(0, [rep_id, member_id], rep_id)

        llm_comments = [_make_comment(rep_id, rating=5)]
        llm_results = [_make_llm_result()]
        all_comments = [
            _make_comment(rep_id, rating=5),
            _make_comment(member_id, rating=1),  # 评分也冲突
        ]

        # 提供正交向量使相似度远低于阈值
        embeddings = [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]]
        results = propagate_cluster_results(
            cluster, llm_comments, llm_results, all_comments,
            embeddings=embeddings, similarity_threshold=0.9,
            rating_guard_threshold=RATING_GUARD_THRESHOLD,
        )

        # similarity gate 先触发，reason 应为 low_cluster_similarity
        assert results[1]["needs_llm"] is True
        assert results[1]["reason"] == "low_cluster_similarity"

    def test_rating_guard_applies_when_similarity_passes(self) -> None:
        """相似度通过但评分冲突 → reason 为 rating_mismatch."""
        rep_id = 1400
        member_id = 1401
        cluster = _make_cluster(0, [rep_id, member_id], rep_id)

        llm_comments = [_make_comment(rep_id, rating=5)]
        llm_results = [_make_llm_result()]
        all_comments = [
            _make_comment(rep_id, rating=5),
            _make_comment(member_id, rating=1),
        ]

        # 提供相同向量使相似度=1.0（通过 similarity gate）
        embeddings = [[1.0, 0.0, 0.0], [1.0, 0.0, 0.0]]
        results = propagate_cluster_results(
            cluster, llm_comments, llm_results, all_comments,
            embeddings=embeddings, similarity_threshold=0.9,
            rating_guard_threshold=RATING_GUARD_THRESHOLD,
        )

        # similarity gate 通过，但 rating guard 拦截
        assert results[1]["needs_llm"] is True
        assert results[1]["reason"] == "rating_mismatch"
