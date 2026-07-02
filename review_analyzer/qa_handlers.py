"""问评论 handler：每个 intent 对应一个 handler，统一签名。

P0 只实现 3 个：aggregate_feedback / product_compare / retrieval。
其他 intent 一律降级到 retrieval_handler。
"""

from __future__ import annotations

import logging
import os
from collections.abc import Callable
from pathlib import Path
from typing import Any, TypedDict

from dotenv import load_dotenv
from openai import OpenAI

from review_analyzer.aggregations import (
    TagStat,
    pick_citations_by_tags,
    top_tags,
)
from review_analyzer.analyzer import get_api_key

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

logger = logging.getLogger(__name__)

MAX_CONTEXT_CHARS = 3600
MIN_TAGS_FOR_AGGREGATION = 3  # 少于此数量降级到 retrieval
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")


class HandlerResult(TypedDict):
    answer: str
    citations: list[dict[str, Any]]
    retrieval_method: str  # "aggregation" | "compare" | "hybrid" | "fallback"
    aggregation_snapshot: dict[str, Any] | None


Fallback = Callable[
    [int, str, list[dict[str, Any]], int, list[dict] | None, dict[str, Any]],
    HandlerResult,
]


def _get_llm_client(api_key: str) -> OpenAI:
    return OpenAI(api_key=api_key, base_url=DEEPSEEK_BASE_URL, timeout=30.0)


def _resolve_api_key(user_id: int, api_key: str | None) -> str:
    return api_key or get_api_key(user_id)


def _format_citations_context(citations: list[dict[str, Any]]) -> str:
    """把 citations 拼成 [1] [2] 编号的上下文，保留评分/日期/情感/产品。"""
    chunks: list[str] = []
    used = 0
    for idx, comment in enumerate(citations, 1):
        content = str(comment.get("content") or "").strip()
        if not content:
            continue
        if used + len(content) > MAX_CONTEXT_CHARS:
            content = content[: max(0, MAX_CONTEXT_CHARS - used)]
        used += len(content)
        parts = [
            f"[{idx}]",
            f"产品：{comment.get('product_id') or '未知'}",
            f"评分：{comment.get('rating') if comment.get('rating') is not None else '无'}",
            f"日期：{comment.get('date') or '无'}",
            f"情感：{comment.get('sentiment') or '未分析'}",
        ]
        chunks.append(" ｜ ".join(parts) + f"\n{content}")
        if used >= MAX_CONTEXT_CHARS:
            break
    return "\n\n".join(chunks)


def _format_tags_skeleton(tags: list[TagStat]) -> str:
    return "\n".join(
        f"- {tag['tag']}：出现 {tag['count']} 次，占比 {tag['pct']}%"
        for tag in tags
        if tag.get("tag")
    )


# ── aggregate_feedback ────────────────────────────────────────────────
def aggregate_feedback_handler(
    user_id: int,
    question: str,
    comments: list[dict[str, Any]],
    top_k: int,  # noqa: ARG001
    history: list[dict] | None,
    intent_result: dict[str, Any],
    fallback: Fallback | None = None,
) -> HandlerResult:
    """聚合 highlight_tag / issue_tag Top-N，回捞代表评论，让 LLM 基于骨架总结。"""
    polarity = intent_result.get("slots", {}).get("polarity") or "negative"
    tag_field = "highlight_tag" if polarity == "positive" else "issue_tag"

    tags = top_tags(comments, tag_field, top_n=8)
    non_empty = [t for t in tags if t.get("tag")]
    if len(non_empty) < MIN_TAGS_FOR_AGGREGATION:
        # 标签稀疏，降级到 retrieval
        if fallback:
            return fallback(user_id, question, comments, top_k, history, intent_result)
        return _empty_result(
            "当前评论的结构化标签太稀疏，无法给出可靠的聚合结论。可以试试更具体的问题。",
        )

    citations = pick_citations_by_tags(
        comments, tag_field, non_empty, per_tag=2, max_total=10
    )
    if not citations:
        citations = comments[:5]

    skeleton = _format_tags_skeleton(non_empty)
    context = _format_citations_context(citations)
    dimension = "买家最常提到的优点" if polarity == "positive" else "买家最常抱怨的问题"

    system_prompt = (
        "你是跨境电商评论洞察分析师。请基于给定的【聚合骨架】和【代表性评论】用中文回答用户问题。\n"
        "必须遵守：\n"
        "1. 用编号列表列出 Top 3-5 项，每项明确标注出现次数和占比\n"
        "2. 每一项配 1-2 条代表评论，用 [1] [2] 格式引用\n"
        "3. 不要说'没有找到'——聚合骨架已经给出了统计结果\n"
        "4. 结尾用一句话给出可行动的建议（如需改进的方向）"
    )
    user_prompt = (
        f"用户问题：{question}\n\n"
        f"【聚合骨架 — {dimension}】\n{skeleton}\n\n"
        f"【代表性评论】\n{context}"
    )

    try:
        api_key = _resolve_api_key(user_id, None)
        client = _get_llm_client(api_key)
        messages: list[dict] = [{"role": "system", "content": system_prompt}]
        if history:
            messages.extend(history)
        messages.append({"role": "user", "content": user_prompt})
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=messages,
            temperature=0.2,
            max_tokens=800,
        )
        answer = response.choices[0].message.content.strip()
    except Exception:
        logger.exception("aggregate_feedback LLM 调用失败，回退到骨架文本")
        answer = _skeleton_fallback_text(dimension, non_empty)

    return {
        "answer": answer,
        "citations": citations,
        "retrieval_method": "aggregation",
        "aggregation_snapshot": {
            "type": "top_tags",
            "polarity": polarity,
            "tag_field": tag_field,
            "tags": non_empty,
        },
    }


def _skeleton_fallback_text(dimension: str, tags: list[TagStat]) -> str:
    lines = [f"根据评论标签聚合，{dimension} Top 5："]
    for idx, tag in enumerate(tags[:5], 1):
        lines.append(f"{idx}. {tag['tag']}（出现 {tag['count']} 次，占比 {tag['pct']}%）")
    lines.append("\n以上为结构化聚合结果；如需进一步分析请查看下方引用的原始评论。")
    return "\n".join(lines)


# ── product_compare ──────────────────────────────────────────────────
def product_compare_handler(
    user_id: int,
    question: str,
    comments: list[dict[str, Any]],
    top_k: int,  # noqa: ARG001
    history: list[dict] | None,
    intent_result: dict[str, Any],  # noqa: ARG001
    fallback: Fallback | None = None,
    products_meta: list[dict] | None = None,
) -> HandlerResult:
    """按 product_id 分组聚合 Top-5 issue + Top-5 highlight，让 LLM 输出对比结论。"""
    # 按 product_id 分组
    groups: dict[str, list[dict[str, Any]]] = {}
    for c in comments:
        pid = str(c.get("product_id") or "").strip()
        if not pid:
            continue
        groups.setdefault(pid, []).append(c)

    if len(groups) < 2:
        # 只有一个产品，无法对比 → 降级
        if fallback:
            return fallback(user_id, question, comments, top_k, history, intent_result)
        return _empty_result("只选了一个产品，无法做对比。请选择至少 2 个产品后再问。")

    product_name_map: dict[str, str] = {}
    if products_meta:
        for row in products_meta:
            pid = str(row.get("parent_product_id") or "").strip()
            if pid:
                product_name_map[pid] = row.get("name") or pid

    per_product_snapshot: list[dict[str, Any]] = []
    citations: list[dict[str, Any]] = []
    skeleton_lines: list[str] = []

    for pid, group_comments in groups.items():
        issues = [t for t in top_tags(group_comments, "issue_tag", top_n=5) if t.get("tag")]
        highs = [t for t in top_tags(group_comments, "highlight_tag", top_n=5) if t.get("tag")]
        name = product_name_map.get(pid) or pid

        # 每个产品取 2 条引用
        product_citations = pick_citations_by_tags(
            group_comments, "issue_tag", issues, per_tag=1, max_total=2
        )
        product_citations += pick_citations_by_tags(
            group_comments, "highlight_tag", highs, per_tag=1, max_total=2
        )
        citations.extend(product_citations[:2])

        per_product_snapshot.append(
            {
                "product_id": pid,
                "product_name": name,
                "review_count": len(group_comments),
                "top_issues": issues,
                "top_highlights": highs,
            }
        )

        skeleton_lines.append(f"\n### {name}（{len(group_comments)} 条评论）")
        if issues:
            skeleton_lines.append("差评标签：" + "；".join(
                f"{t['tag']}({t['count']}次/{t['pct']}%)" for t in issues
            ))
        if highs:
            skeleton_lines.append("好评标签：" + "；".join(
                f"{t['tag']}({t['count']}次/{t['pct']}%)" for t in highs
            ))

    # 去重 citations 并截断
    seen: set[int] = set()
    dedup_citations: list[dict[str, Any]] = []
    for c in citations:
        cid = c.get("id")
        if cid is None or cid in seen:
            continue
        seen.add(int(cid))
        dedup_citations.append(c)
        if len(dedup_citations) >= 10:
            break

    total_valid = sum(1 for snap in per_product_snapshot if snap["top_issues"] or snap["top_highlights"])
    if total_valid < 2:
        if fallback:
            return fallback(user_id, question, comments, top_k, history, intent_result)

    skeleton = "\n".join(skeleton_lines)
    context = _format_citations_context(dedup_citations)

    system_prompt = (
        "你是跨境电商产品对比分析师。请基于每个产品的【标签聚合骨架】和【代表评论】用中文回答用户问题。\n"
        "必须遵守：\n"
        "1. 明确说出产品名称，用表格或列表对比\n"
        "2. 关键结论用数字支撑（占比、出现次数）\n"
        "3. 每个结论至少引用 1 条评论 [1] [2]\n"
        "4. 不要说'没有找到'"
    )
    user_prompt = (
        f"用户问题：{question}\n\n"
        f"【各产品聚合骨架】{skeleton}\n\n"
        f"【代表评论】\n{context}"
    )

    try:
        api_key = _resolve_api_key(user_id, None)
        client = _get_llm_client(api_key)
        messages: list[dict] = [{"role": "system", "content": system_prompt}]
        if history:
            messages.extend(history)
        messages.append({"role": "user", "content": user_prompt})
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=messages,
            temperature=0.2,
            max_tokens=900,
        )
        answer = response.choices[0].message.content.strip()
    except Exception:
        logger.exception("product_compare LLM 调用失败，回退到骨架文本")
        answer = _compare_skeleton_fallback(per_product_snapshot)

    return {
        "answer": answer,
        "citations": dedup_citations,
        "retrieval_method": "compare",
        "aggregation_snapshot": {
            "type": "product_compare",
            "products": per_product_snapshot,
        },
    }


def _compare_skeleton_fallback(snapshot: list[dict[str, Any]]) -> str:
    lines = ["各产品标签聚合对比："]
    for snap in snapshot:
        lines.append(f"\n【{snap['product_name']}】共 {snap['review_count']} 条评论")
        if snap["top_issues"]:
            lines.append("  差评 Top: " + "、".join(
                f"{t['tag']}({t['pct']}%)" for t in snap["top_issues"][:3]
            ))
        if snap["top_highlights"]:
            lines.append("  好评 Top: " + "、".join(
                f"{t['tag']}({t['pct']}%)" for t in snap["top_highlights"][:3]
            ))
    lines.append("\n以上为结构化聚合结果。")
    return "\n".join(lines)


# ── retrieval（复用 rag.hybrid_retrieve） ────────────────────────────
def retrieval_handler(
    user_id: int,
    question: str,
    comments: list[dict[str, Any]],
    top_k: int,
    history: list[dict] | None,
    intent_result: dict[str, Any],  # noqa: ARG001
    fallback: Fallback | None = None,  # noqa: ARG001
) -> HandlerResult:
    """现有检索型 RAG 流程原样封装。"""
    # 延迟导入避免循环依赖
    from review_analyzer.rag import (  # noqa: PLC0415
        _fallback_answer,
        _format_context,
        ensure_comment_embeddings,
        generate_embedding,
        hybrid_retrieve,
        retrieve_relevant_comments,
    )

    citations: list[dict[str, Any]] = []
    retrieval_method = "text"
    try:
        ensure_comment_embeddings(user_id, comments)
        question_embedding = generate_embedding(question, user_id)
        comment_ids = [int(c["id"]) for c in comments if c.get("id")]
        citations = hybrid_retrieve(
            user_id, question, question_embedding, comment_ids, top_k=top_k
        )
        if citations:
            retrieval_method = "hybrid"
    except Exception:
        logger.exception("retrieval_handler 混合检索失败，回退到文本检索")
        citations = []

    if not citations:
        citations = retrieve_relevant_comments(question, comments, top_k=top_k)

    if not citations:
        return {
            "answer": _fallback_answer(question, citations),
            "citations": [],
            "retrieval_method": retrieval_method,
            "aggregation_snapshot": None,
        }

    try:
        api_key = _resolve_api_key(user_id, None)
        client = _get_llm_client(api_key)
        context = _format_context(citations)
        messages: list[dict] = [
            {
                "role": "system",
                "content": (
                    "你是跨境电商评论分析助手。只能基于给定评论回答问题；"
                    "如果证据不足，要明确说明。回答要简洁，并用 [1] [2] 这样的编号引用评论。"
                ),
            },
        ]
        if history:
            messages.extend(history)
        messages.append(
            {
                "role": "user",
                "content": f"用户问题：{question}\n\n相关评论：\n{context}",
            },
        )
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=messages,
            temperature=0.2,
            max_tokens=700,
        )
        answer = response.choices[0].message.content.strip()
    except Exception:
        logger.exception("retrieval_handler LLM 调用失败，回退到 fallback 文案")
        answer = _fallback_answer(question, citations)

    return {
        "answer": answer,
        "citations": citations,
        "retrieval_method": retrieval_method,
        "aggregation_snapshot": None,
    }


def _empty_result(message: str) -> HandlerResult:
    return {
        "answer": message,
        "citations": [],
        "retrieval_method": "fallback",
        "aggregation_snapshot": None,
    }


# ── 意图路由表 ────────────────────────────────────────────────────────
# 未实现的意图（P1 会补齐）：consumer_insight / rating_breakdown / trend_and_emerging / unanswerable
# P0 阶段这些 intent 全部降级到 retrieval_handler。

INTENT_HANDLERS: dict[str, Callable[..., HandlerResult]] = {
    "aggregate_feedback": aggregate_feedback_handler,
    "product_compare": product_compare_handler,
    "specific_retrieval": retrieval_handler,
    # P0 未实现的一律走 retrieval
    "rating_breakdown": retrieval_handler,
    "consumer_insight": retrieval_handler,
    "trend_and_emerging": retrieval_handler,
    "unanswerable": retrieval_handler,
}
