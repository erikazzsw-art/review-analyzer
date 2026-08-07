"""V4-T4 Step 2: HDBSCAN 聚类前置层.

将同一批次评论按 embedding 相似度聚类，只对每簇代表评论调用 LLM，
同簇成员复用代表的结构化分析结果（aspects/pain_points/highlights）。

设计要点：
- batch < MIN_BATCH_FOR_CLUSTERING 时跳过聚类，全量走 LLM
- noise 点（HDBSCAN label=-1）单独走 LLM
- 代表选取：cluster centroid 最近邻
- 聚类本身为纯 CPU numpy 运算，100 条耗时 < 200ms
- 5.9.7 新增 rating guard：代表与成员评分差距 ≥ RATING_GUARD_THRESHOLD 时不传播
  标签+证据，防止好评代表的标签误传播到差评成员（cluster 传播污染）
"""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from typing import Any

import numpy as np
from sklearn.cluster import HDBSCAN

logger = logging.getLogger(__name__)

MIN_BATCH_FOR_CLUSTERING = 10
DEFAULT_MIN_CLUSTER_SIZE = 3
PROPAGATION_SIMILARITY_THRESHOLD = 0.88

# 评分守卫：代表与成员评分绝对差值 >= 此阈值时，拒绝传播标签+证据
# 5 星制下：|5-3|=2 为边界（好评 vs 中性），|5-2|=3 / |5-1|=4 为明显冲突
# 阈值=2.0 表示差 ≥2 星的评论不共享标签+证据
# 可通过环境变量 CLUSTER_RATING_GUARD_THRESHOLD 覆盖
# 设 CLUSTER_RATING_GUARD_ENABLED=false 可完全关闭守卫（紧急回退）
RATING_GUARD_THRESHOLD = 2.0


@dataclass
class ClusterResult:
    """聚类结果."""

    clusters: dict[int, list[int]] = field(default_factory=dict)
    representatives: list[int] = field(default_factory=list)
    noise_ids: list[int] = field(default_factory=list)
    skipped: bool = False

    @property
    def llm_target_ids(self) -> list[int]:
        """需要发送给 LLM 的 comment_id 列表."""
        return self.representatives + self.noise_ids

    @property
    def n_clusters(self) -> int:
        return len(self.clusters)

    @property
    def total_llm_calls(self) -> int:
        return len(self.llm_target_ids)


def cluster_reviews(
    comment_ids: list[int],
    embeddings: list[list[float]],
    min_cluster_size: int = DEFAULT_MIN_CLUSTER_SIZE,
    min_batch_for_clustering: int = MIN_BATCH_FOR_CLUSTERING,
) -> ClusterResult:
    """对一批评论的 embedding 做 HDBSCAN 聚类.

    Args:
        comment_ids: 评论 ID 列表（与 embeddings 一一对应）
        embeddings: 1536 维向量列表
        min_cluster_size: HDBSCAN 最小聚类大小
        min_batch_for_clustering: 低于此数量跳过聚类

    Returns:
        ClusterResult 包含聚类结果、代表 ID、噪声 ID
    """
    n = len(comment_ids)
    if n < min_batch_for_clustering:
        return ClusterResult(
            representatives=list(comment_ids),
            skipped=True,
        )

    X = np.array(embeddings, dtype=np.float32)

    hdb = HDBSCAN(
        min_cluster_size=min_cluster_size,
        metric="euclidean",
        n_jobs=1,
    )
    labels = hdb.fit_predict(X)

    clusters: dict[int, list[int]] = {}
    noise_ids: list[int] = []
    representatives: list[int] = []

    for idx, label in enumerate(labels):
        cid = comment_ids[idx]
        if label == -1:
            noise_ids.append(cid)
        else:
            clusters.setdefault(int(label), []).append(cid)

    for label, _member_ids in clusters.items():
        member_indices = [i for i, lbl in enumerate(labels) if lbl == label]
        member_vecs = X[member_indices]
        centroid = member_vecs.mean(axis=0)
        distances = np.linalg.norm(member_vecs - centroid, axis=1)
        best_local_idx = int(np.argmin(distances))
        rep_id = comment_ids[member_indices[best_local_idx]]
        representatives.append(rep_id)

    logger.info(
        "cluster_reviews: n=%d clusters=%d representatives=%d noise=%d total_llm=%d (saved %d calls)",
        n,
        len(clusters),
        len(representatives),
        len(noise_ids),
        len(representatives) + len(noise_ids),
        n - len(representatives) - len(noise_ids),
    )

    return ClusterResult(
        clusters=clusters,
        representatives=representatives,
        noise_ids=noise_ids,
    )


def _cluster_avg_cosine_similarity(
    member_indices: list[int], X: np.ndarray
) -> float:
    """计算簇内成员两两余弦相似度的均值。"""
    vecs = X[member_indices]
    norms = np.linalg.norm(vecs, axis=1, keepdims=True)
    norms = np.where(norms == 0, 1, norms)
    normed = vecs / norms
    sim_matrix = normed @ normed.T
    n = len(member_indices)
    if n < 2:
        return 1.0
    triu_sum = (sim_matrix.sum() - n) / 2
    pairs = n * (n - 1) / 2
    return float(triu_sum / pairs)


def propagate_cluster_results(
    cluster_result: ClusterResult,
    llm_comments: list[dict[str, Any]],
    llm_results: list[dict[str, Any]],
    all_comments: list[dict[str, Any]],
    embeddings: list[list[float]] | None = None,
    similarity_threshold: float = PROPAGATION_SIMILARITY_THRESHOLD,
    rating_guard_threshold: float | None = RATING_GUARD_THRESHOLD,
) -> list[dict[str, Any]]:
    """将 LLM 分析结果从代表评论传播到同簇成员.

    代表和噪声点使用 LLM 原始结果；同簇成员继承代表的
    aspects/pain_points/highlights/evidence_level_overall，
    但 sentiment 独立由 rating 决定（在 caller 侧覆写）。

    质量门控：
    - 余弦相似度门控：若提供 embeddings 且簇内平均余弦相似度 < threshold，
      该簇成员不传播，标记为 needs_llm
    - 评分守卫（5.9.7）：若成员与代表的 rating 绝对差值 >= rating_guard_threshold，
      该成员不传播，标记为 needs_llm（防止好评代表标签+证据误传播到差评成员）

    可通过环境变量关闭评分守卫（紧急回退）：
      CLUSTER_RATING_GUARD_ENABLED=false
    或调整阈值：
      CLUSTER_RATING_GUARD_THRESHOLD=1.5

    Args:
        cluster_result: 聚类结果
        llm_comments: 送入 LLM 的评论列表（代表 + 噪声）
        llm_results: LLM 返回结果列表（与 llm_comments 一一对应）
        all_comments: 全部评论列表（含未送入 LLM 的成员），每条需含 rating 字段
        embeddings: 与 all_comments 一一对应的向量（用于质量门控）
        similarity_threshold: 簇内传播的最低余弦相似度阈值
        rating_guard_threshold: 评分守卫阈值（None 关闭评分守卫）

    Returns:
        与 all_comments 一一对应的结果列表
    """
    id_to_result: dict[int, dict[str, Any]] = {}
    for comment, result in zip(llm_comments, llm_results):
        id_to_result[int(comment["id"])] = result

    if cluster_result.skipped:
        return llm_results

    # 评分守卫：可通过环境变量全局关闭（紧急回退），或调整阈值
    if rating_guard_threshold is not None:
        _enabled = os.getenv("CLUSTER_RATING_GUARD_ENABLED", "true").lower() != "false"
        if not _enabled:
            rating_guard_threshold = None
            logger.info("cluster rating guard: disabled via CLUSTER_RATING_GUARD_ENABLED=false")
        else:
            _env_threshold = os.getenv("CLUSTER_RATING_GUARD_THRESHOLD")
            if _env_threshold is not None:
                try:
                    rating_guard_threshold = float(_env_threshold)
                    logger.info(
                        "cluster rating guard: threshold overridden via env to %.1f",
                        rating_guard_threshold,
                    )
                except ValueError:
                    logger.warning(
                        "cluster rating guard: invalid CLUSTER_RATING_GUARD_THRESHOLD=%s, "
                        "using default %.1f",
                        _env_threshold,
                        RATING_GUARD_THRESHOLD,
                    )

    # 构建 comment_id → rating 映射（用于评分守卫）
    id_to_rating: dict[int, float | None] = {}
    for comment in all_comments:
        cid = int(comment["id"])
        rating_raw = comment.get("rating")
        if rating_raw is not None:
            try:
                id_to_rating[cid] = float(rating_raw)
            except (TypeError, ValueError):
                id_to_rating[cid] = None
        else:
            id_to_rating[cid] = None

    # 构建 comment_id → index 映射（用于质量门控）
    id_to_idx: dict[int, int] = {}
    for idx, comment in enumerate(all_comments):
        id_to_idx[int(comment["id"])] = idx

    # 质量门控：标记低质量簇
    low_quality_clusters: set[int] = set()
    if embeddings:
        X = np.array(embeddings, dtype=np.float32)
        for label, member_ids in cluster_result.clusters.items():
            member_indices = [id_to_idx[mid] for mid in member_ids if mid in id_to_idx]
            if len(member_indices) < 2:
                continue
            avg_sim = _cluster_avg_cosine_similarity(member_indices, X)
            if avg_sim < similarity_threshold:
                low_quality_clusters.add(label)
                logger.info(
                    "cluster quality gate: cluster %d (size=%d) avg_sim=%.3f < %.2f, skipping propagation",
                    label, len(member_indices), avg_sim, similarity_threshold,
                )

    rep_to_cluster: dict[int, int] = {}
    for label, member_ids in cluster_result.clusters.items():
        for rep_id in cluster_result.representatives:
            if rep_id in member_ids:
                rep_to_cluster[rep_id] = label
                break

    cluster_to_rep: dict[int, int] = {v: k for k, v in rep_to_cluster.items()}

    member_to_cluster: dict[int, int] = {}
    for label, member_ids in cluster_result.clusters.items():
        for mid in member_ids:
            member_to_cluster[mid] = label

    final_results: list[dict[str, Any]] = []
    for comment in all_comments:
        cid = int(comment["id"])
        if cid in id_to_result:
            final_results.append(id_to_result[cid])
        else:
            cluster_label = member_to_cluster.get(cid)
            if cluster_label is not None:
                if cluster_label in low_quality_clusters:
                    final_results.append({"needs_llm": True, "reason": "low_cluster_similarity"})
                else:
                    rep_id = cluster_to_rep.get(cluster_label)
                    if rep_id and rep_id in id_to_result:
                        # 评分守卫：成员与代表评分差距过大时不传播标签+证据
                        rating_mismatch = False
                        if rating_guard_threshold is not None:
                            member_rating = id_to_rating.get(cid)
                            rep_rating = id_to_rating.get(rep_id)
                            if member_rating is not None and rep_rating is not None:
                                diff = abs(member_rating - rep_rating)
                                if diff >= rating_guard_threshold:
                                    rating_mismatch = True
                                    logger.info(
                                        "cluster rating guard: member %d (rating=%.0f) vs "
                                        "rep %d (rating=%.0f) diff=%.0f >= %.1f, "
                                        "skipping propagation",
                                        cid, member_rating, rep_id, rep_rating,
                                        diff, rating_guard_threshold,
                                    )
                        if rating_mismatch:
                            final_results.append(
                                {"needs_llm": True, "reason": "rating_mismatch"}
                            )
                        else:
                            rep_result = id_to_result[rep_id]
                            propagated = {
                                "sentiment": rep_result.get("sentiment"),
                                "aspects": rep_result.get("aspects", []),
                                "pain_points": rep_result.get("pain_points", []),
                                "highlights": rep_result.get("highlights", []),
                                "evidence_level_overall": rep_result.get("evidence_level_overall"),
                                "prompt_version": rep_result.get("prompt_version"),
                                "cluster_propagated": True,
                                "cluster_representative_id": rep_id,
                            }
                            final_results.append(propagated)
                    else:
                        final_results.append({"error": "cluster_rep_missing"})
            else:
                final_results.append({"error": "orphan_comment"})

    return final_results
