"""V4-T4 Step 2: HDBSCAN 聚类前置层.

将同一批次评论按 embedding 相似度聚类，只对每簇代表评论调用 LLM，
同簇成员复用代表的结构化分析结果（aspects/pain_points/highlights）。

设计要点：
- batch < MIN_BATCH_FOR_CLUSTERING 时跳过聚类，全量走 LLM
- noise 点（HDBSCAN label=-1）单独走 LLM
- 代表选取：cluster centroid 最近邻
- 聚类本身为纯 CPU numpy 运算，100 条耗时 < 200ms
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

import numpy as np
from sklearn.cluster import HDBSCAN

logger = logging.getLogger(__name__)

MIN_BATCH_FOR_CLUSTERING = 10
DEFAULT_MIN_CLUSTER_SIZE = 3


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


def propagate_cluster_results(
    cluster_result: ClusterResult,
    llm_comments: list[dict[str, Any]],
    llm_results: list[dict[str, Any]],
    all_comments: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """将 LLM 分析结果从代表评论传播到同簇成员.

    代表和噪声点使用 LLM 原始结果；同簇成员继承代表的
    aspects/pain_points/highlights/evidence_level_overall，
    但 sentiment 独立由 rating 决定（在 caller 侧覆写）。

    Args:
        cluster_result: 聚类结果
        llm_comments: 送入 LLM 的评论列表（代表 + 噪声）
        llm_results: LLM 返回结果列表（与 llm_comments 一一对应）
        all_comments: 全部评论列表（含未送入 LLM 的成员）

    Returns:
        与 all_comments 一一对应的结果列表
    """
    id_to_result: dict[int, dict[str, Any]] = {}
    for comment, result in zip(llm_comments, llm_results):
        id_to_result[int(comment["id"])] = result

    if cluster_result.skipped:
        return llm_results

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
                rep_id = cluster_to_rep.get(cluster_label)
                if rep_id and rep_id in id_to_result:
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
