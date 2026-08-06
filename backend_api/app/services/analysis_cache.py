"""V4-T4 Step 3: 多级缓存.

两层缓存减少 LLM 调用：
- L1: content_hash 精确命中（+ 语义版本校验）— 同一条评论内容已有分析结果，直接复用
- L3: embedding 余弦相似度 > 0.95 — 复用最近邻的分析结果

L2（短文本默认结果）已在 5.9.6-B.1 删除：该分支对 ≤10 字 + 极端评分评论
跳过 LLM 直接给默认结果，与 5.9.3 证据门冲突。

返回 CacheResult 列表，标记每条评论是否命中缓存及命中层级。
未命中的评论继续走 LLM 管道。
"""
from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass, field
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)

L3_SIMILARITY_THRESHOLD = 0.95


@dataclass
class CacheHit:
    comment_id: int
    level: str  # "L1" | "L3"
    result: dict[str, Any]
    source_comment_id: int | None = None


@dataclass
class CacheResult:
    hits: dict[int, CacheHit] = field(default_factory=dict)
    misses: list[int] = field(default_factory=list)

    @property
    def hit_count(self) -> int:
        return len(self.hits)

    @property
    def miss_count(self) -> int:
        return len(self.misses)

    def stats(self) -> dict[str, int]:
        levels = {"L1": 0, "L3": 0}
        for hit in self.hits.values():
            levels[hit.level] += 1
        return {**levels, "miss": self.miss_count, "total": self.hit_count + self.miss_count}


def compute_content_hash(content: str, rating: Any = None, category: str | None = None) -> str:
    """计算评论内容 hash（content + rating + category）."""
    normalized = content.strip().lower()
    key = f"{normalized}|{rating}" if rating is not None else normalized
    if category:
        key = f"{key}|{category.strip().lower()}"
    return hashlib.sha256(key.encode("utf-8")).hexdigest()


def compute_batch_hash(comments: list[dict[str, Any]], category: str | None = None) -> str:
    """计算整批评论的指纹，用于批次去重。

    排序所有 content_hash 后拼接再 SHA256，保证行顺序无关。
    """
    hashes = sorted(
        compute_content_hash(
            str(c.get("content") or ""),
            c.get("rating"),
            category,
        )
        for c in comments
    )
    combined = "|".join(hashes)
    return hashlib.sha256(combined.encode("utf-8")).hexdigest()


def _check_l1(
    comments: list[dict[str, Any]],
    existing_analyses: dict[str, dict[str, Any]],
) -> tuple[list[CacheHit], list[dict[str, Any]]]:
    """L1: content_hash 精确命中已有分析结果."""
    hits: list[CacheHit] = []
    remaining: list[dict[str, Any]] = []

    for c in comments:
        content_hash = c.get("content_hash") or compute_content_hash(
            c.get("content", ""),
            c.get("rating"),
            c.get("category"),
        )
        cached = existing_analyses.get(content_hash)
        if cached and cached.get("aspects_json"):
            hits.append(CacheHit(
                comment_id=c["id"],
                level="L1",
                result=cached,
                source_comment_id=cached.get("source_id"),
            ))
        else:
            remaining.append(c)

    return hits, remaining


def _check_l3(
    comments: list[dict[str, Any]],
    reference_embeddings: list[list[float]],
    reference_ids: list[int],
    reference_results: dict[int, dict[str, Any]],
    threshold: float = L3_SIMILARITY_THRESHOLD,
) -> tuple[list[CacheHit], list[dict[str, Any]]]:
    """L3: embedding 余弦相似度 > threshold，复用最近邻分析."""
    if not reference_embeddings or not comments:
        return [], comments

    ref_matrix = np.array(reference_embeddings, dtype=np.float32)
    ref_norms = np.linalg.norm(ref_matrix, axis=1, keepdims=True)
    ref_norms[ref_norms == 0] = 1.0
    ref_normalized = ref_matrix / ref_norms

    hits: list[CacheHit] = []
    remaining: list[dict[str, Any]] = []

    for c in comments:
        emb = c.get("embedding")
        if emb is None:
            remaining.append(c)
            continue

        vec = np.array(emb, dtype=np.float32)
        norm = np.linalg.norm(vec)
        if norm == 0:
            remaining.append(c)
            continue

        vec_normalized = vec / norm
        similarities = ref_normalized @ vec_normalized
        best_idx = int(np.argmax(similarities))
        best_sim = float(similarities[best_idx])

        if best_sim >= threshold:
            ref_id = reference_ids[best_idx]
            ref_result = reference_results.get(ref_id)
            if ref_result and ref_result.get("aspects_json"):
                hits.append(CacheHit(
                    comment_id=c["id"],
                    level="L3",
                    result={
                        **ref_result,
                        "cache_similarity": round(best_sim, 4),
                    },
                    source_comment_id=ref_id,
                ))
            else:
                remaining.append(c)
        else:
            remaining.append(c)

    return hits, remaining


def apply_cache(
    comments: list[dict[str, Any]],
    existing_analyses: dict[str, dict[str, Any]],
    reference_embeddings: list[list[float]] | None = None,
    reference_ids: list[int] | None = None,
    reference_results: dict[int, dict[str, Any]] | None = None,
) -> CacheResult:
    """依次执行 L1→L3 缓存检查.

    L2（短文本默认结果）已在 5.9.6-B.1 删除。

    Args:
        comments: 待分析评论列表，每条需含 id, content, rating, embedding(可选)
        existing_analyses: content_hash → 已有分析结果的映射（L1 用）
        reference_embeddings: 已有分析结果的 embedding 列表（L3 用）
        reference_ids: 与 reference_embeddings 对应的 comment_id
        reference_results: comment_id → 分析结果映射（L3 用）

    Returns:
        CacheResult 包含命中和未命中列表
    """
    result = CacheResult()

    l1_hits, after_l1 = _check_l1(comments, existing_analyses)
    for hit in l1_hits:
        result.hits[hit.comment_id] = hit

    if reference_embeddings and reference_ids and reference_results:
        l3_hits, after_l3 = _check_l3(
            after_l1,
            reference_embeddings,
            reference_ids,
            reference_results,
        )
        for hit in l3_hits:
            result.hits[hit.comment_id] = hit
        remaining = after_l3
    else:
        remaining = after_l1

    result.misses = [c["id"] for c in remaining]

    stats = result.stats()
    logger.info(
        "analysis_cache: L1=%d L3=%d miss=%d total=%d (hit_rate=%.1f%%)",
        stats["L1"], stats["L3"], stats["miss"], stats["total"],
        (result.hit_count / stats["total"] * 100) if stats["total"] > 0 else 0,
    )

    return result
