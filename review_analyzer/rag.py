"""评论问答 RAG 流程：检索相关评论，生成带引用的回答。"""

from __future__ import annotations

import logging
import math
import os
import re
from collections import Counter
from difflib import SequenceMatcher
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

from review_analyzer.analyzer import get_api_key
from review_analyzer.database import (
    get_comments_missing_embeddings,
    get_setting,
    search_comments_by_embedding,
    search_comments_by_fulltext,
    update_comment_embedding,
)

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

logger = logging.getLogger(__name__)

TOKEN_RE = re.compile(r"[\w\u4e00-\u9fff]+", re.UNICODE)
MAX_CONTEXT_CHARS = 3600
DEFAULT_TOP_K = 5
EMBEDDING_BASE_URL = os.getenv("EMBEDDING_API_BASE_URL", "https://api.openai.com/v1")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
EMBEDDING_API_KEY = os.getenv("EMBEDDING_API_KEY", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
STOP_WORDS = {
    "a", "an", "and", "are", "do", "does", "for", "in", "is", "it", "of",
    "on", "or", "the", "to", "what", "which", "with", "customers", "mention",
}


def _get_embedding_api_key(user_id: int | None = None) -> str:
    if EMBEDDING_API_KEY:
        return EMBEDDING_API_KEY
    if OPENAI_API_KEY:
        return OPENAI_API_KEY
    if user_id is not None:
        try:
            user_key = get_setting(user_id, "embedding_api_key")
            if user_key:
                return user_key
        except Exception:
            pass
    return get_api_key(user_id)


def _get_embedding_client(user_id: int | None = None) -> OpenAI:
    api_key = _get_embedding_api_key(user_id)
    return OpenAI(api_key=api_key, base_url=EMBEDDING_BASE_URL, timeout=60.0)


def generate_embedding(text: str, user_id: int | None = None) -> list[float]:
    """调用 OpenAI-compatible embedding API 生成向量。"""
    client = _get_embedding_client(user_id)
    response = client.embeddings.create(
        model=EMBEDDING_MODEL,
        input=text[:8000],
    )
    return [float(value) for value in response.data[0].embedding]


EMBEDDING_BATCH_SIZE = 256


def generate_embeddings_batch(
    texts: list[str], user_id: int | None = None
) -> list[list[float]]:
    """批量生成 embedding（一次 HTTP 最多 EMBEDDING_BATCH_SIZE 条）。

    失败时 fallback 到逐条调用。
    """
    if not texts:
        return []

    client = _get_embedding_client(user_id)
    all_embeddings: list[list[float]] = []

    for i in range(0, len(texts), EMBEDDING_BATCH_SIZE):
        batch = [t[:8000] for t in texts[i : i + EMBEDDING_BATCH_SIZE]]
        try:
            response = client.embeddings.create(model=EMBEDDING_MODEL, input=batch)
            sorted_data = sorted(response.data, key=lambda d: d.index)
            all_embeddings.extend(
                [float(v) for v in item.embedding] for item in sorted_data
            )
        except Exception:
            logger.warning(
                "generate_embeddings_batch failed for chunk %d-%d, falling back to single",
                i, i + len(batch),
            )
            for text in batch:
                try:
                    emb = generate_embedding(text, user_id)
                    all_embeddings.append(emb)
                except Exception:
                    all_embeddings.append([])

    return all_embeddings


def embed_session_comments(user_id: int, session_id: int) -> dict:
    """为一个上传批次中缺失向量的评论生成 embedding 并入库。"""
    comments = get_comments_missing_embeddings(user_id, session_id)
    if not comments:
        return {"ok": True, "embedded": 0, "total": 0, "error": ""}

    texts: list[str] = []
    valid_comments: list[dict] = []
    for comment in comments:
        content = str(comment.get("content", "")).strip()
        if content:
            texts.append(content)
            valid_comments.append(comment)

    if not texts:
        return {"ok": True, "embedded": 0, "total": len(comments), "error": ""}

    embeddings = generate_embeddings_batch(texts, user_id)
    embedded = 0
    for comment, embedding in zip(valid_comments, embeddings):
        if embedding:
            update_comment_embedding(user_id, int(comment["id"]), embedding)
            embedded += 1

    return {"ok": True, "embedded": embedded, "total": len(comments), "error": ""}


def ensure_comment_embeddings(user_id: int, comments: list[dict]) -> int:
    """为当前问答范围内缺失 embedding 的评论按需补齐向量。"""
    texts: list[str] = []
    targets: list[dict] = []
    for comment in comments:
        if comment.get("embedding") is not None:
            continue
        content = str(comment.get("content", "")).strip()
        comment_id = comment.get("id")
        if not content or not comment_id:
            continue
        texts.append(content)
        targets.append(comment)

    if not texts:
        return 0

    embeddings = generate_embeddings_batch(texts, user_id)
    embedded = 0
    for comment, embedding in zip(targets, embeddings):
        if embedding:
            update_comment_embedding(user_id, int(comment["id"]), embedding)
            embedded += 1
    return embedded


def _tokenize(text: str) -> list[str]:
    tokens = []
    for token in TOKEN_RE.findall(text):
        normalized = token.lower().strip()
        if not normalized or normalized in STOP_WORDS:
            continue
        if normalized.isascii() and len(normalized) < 3:
            continue
        tokens.append(normalized)
    return tokens


def _score_comment(query_tokens: Counter[str], comment: dict) -> float:
    content = str(comment.get("content", ""))
    if not content:
        return 0.0

    comment_tokens = Counter(_tokenize(content))
    if not comment_tokens:
        return 0.0

    overlap = sum(min(count, comment_tokens[token]) for token, count in query_tokens.items())
    for query_token in query_tokens:
        if query_token in comment_tokens:
            continue
        if any(
            query_token in comment_token
            or comment_token in query_token
            or (
                len(query_token) >= 5
                and len(comment_token) >= 5
                and SequenceMatcher(None, query_token, comment_token).ratio() >= 0.72
            )
            for comment_token in comment_tokens
        ):
            overlap += 0.5
    if overlap == 0:
        return 0.0

    rating = comment.get("rating")
    rating_boost = 0.08 if rating else 0
    length_penalty = math.log(len(comment_tokens) + 2)
    return overlap / length_penalty + rating_boost


def retrieve_relevant_comments(question: str, comments: list[dict], top_k: int = 5) -> list[dict]:
    """用轻量文本检索返回最相关评论，作为向量检索不可用时的稳定 fallback。"""
    query_tokens = Counter(_tokenize(question))
    if not query_tokens:
        return []

    scored: list[tuple[float, dict]] = []
    for comment in comments:
        score = _score_comment(query_tokens, comment)
        if score > 0:
            scored.append((score, comment))

    scored.sort(key=lambda item: item[0], reverse=True)
    return [comment for _, comment in scored[:top_k]]


RRF_K = 60


def _rrf_merge(
    vector_results: list[dict], fulltext_results: list[dict], top_k: int = 5
) -> list[dict]:
    """Reciprocal Rank Fusion 合并两路检索结果。"""
    scores: dict[int, float] = {}
    id_to_doc: dict[int, dict] = {}

    for rank, doc in enumerate(vector_results, 1):
        doc_id = int(doc["id"])
        scores[doc_id] = scores.get(doc_id, 0) + 1.0 / (RRF_K + rank)
        id_to_doc[doc_id] = doc

    for rank, doc in enumerate(fulltext_results, 1):
        doc_id = int(doc["id"])
        scores[doc_id] = scores.get(doc_id, 0) + 1.0 / (RRF_K + rank)
        if doc_id not in id_to_doc:
            id_to_doc[doc_id] = doc

    sorted_ids = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)
    return [id_to_doc[doc_id] for doc_id in sorted_ids[:top_k]]


def hybrid_retrieve(
    user_id: int,
    question: str,
    question_embedding: list[float],
    comment_ids: list[int],
    top_k: int = DEFAULT_TOP_K,
) -> list[dict]:
    """混合检索：向量 Top-20 + 全文 Top-20 → RRF merge → Top-K."""
    vector_results = search_comments_by_embedding(
        user_id, question_embedding, comment_ids=comment_ids, top_k=20
    )
    fulltext_results = search_comments_by_fulltext(
        user_id, question, comment_ids=comment_ids, top_k=20
    )
    if not fulltext_results:
        return vector_results[:top_k]
    return _rrf_merge(vector_results, fulltext_results, top_k=top_k)


def _format_context(citations: list[dict]) -> str:
    chunks = []
    used_chars = 0
    for index, comment in enumerate(citations, 1):
        content = str(comment.get("content", "")).strip()
        if not content:
            continue
        if used_chars + len(content) > MAX_CONTEXT_CHARS:
            content = content[: max(0, MAX_CONTEXT_CHARS - used_chars)]
        used_chars += len(content)
        rating = comment.get("rating") or "无评分"
        date = comment.get("date") or "无日期"
        sentiment = comment.get("sentiment") or "未分析"
        chunks.append(f"[{index}] 评分：{rating}；日期：{date}；情感：{sentiment}\n{content}")
        if used_chars >= MAX_CONTEXT_CHARS:
            break
    return "\n\n".join(chunks)


def _fallback_answer(question: str, citations: list[dict]) -> str:
    if not citations:
        return "没有在当前评论中找到足够相关的内容。可以换一个更具体的问题，例如询问包装、质量、尺寸、物流或某个关键词。"

    issue_tags = Counter()
    highlight_tags = Counter()
    for comment in citations:
        for field, counter in (("issue_tag", issue_tags), ("highlight_tag", highlight_tags)):
            raw_tags = str(comment.get(field, ""))
            for tag in raw_tags.split(","):
                tag = tag.strip()
                if tag:
                    counter[tag] += 1

    parts = [f"我找到了 {len(citations)} 条相关评论。"]
    if issue_tags:
        parts.append("主要问题：" + "、".join(tag for tag, _ in issue_tags.most_common(5)) + "。")
    if highlight_tags:
        parts.append("主要亮点：" + "、".join(tag for tag, _ in highlight_tags.most_common(5)) + "。")
    parts.append("引用可查看下方评论原文。")
    return "\n\n".join(parts)


def answer_question(
    user_id: int,
    question: str,
    comments: list[dict],
    api_key: str | None = None,
    top_k: int = DEFAULT_TOP_K,
) -> dict:
    """检索评论并生成回答，返回 answer + citations。"""
    retrieval_method = "text"
    citations: list[dict] = []
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
        citations = []

    if not citations:
        citations = retrieve_relevant_comments(question, comments, top_k=top_k)

    if not citations:
        return {"answer": _fallback_answer(question, citations), "citations": [], "retrieval_method": retrieval_method}

    try:
        resolved_api_key = api_key or get_api_key(user_id)
        client = OpenAI(
            api_key=resolved_api_key,
            base_url="https://api.deepseek.com/v1",
            timeout=30.0,
        )
        context = _format_context(citations)
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "你是跨境电商评论分析助手。只能基于给定评论回答问题；"
                        "如果证据不足，要明确说明。回答要简洁，并用 [1] [2] 这样的编号引用评论。"
                    ),
                },
                {
                    "role": "user",
                    "content": f"用户问题：{question}\n\n相关评论：\n{context}",
                },
            ],
            temperature=0.2,
            max_tokens=700,
        )
        answer = response.choices[0].message.content.strip()
    except Exception:
        answer = _fallback_answer(question, citations)

    return {"answer": answer, "citations": citations, "retrieval_method": retrieval_method}
