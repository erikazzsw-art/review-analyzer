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
    update_comment_embeddings_batch,
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
if not EMBEDDING_API_KEY and not OPENAI_API_KEY:
    logger.warning(
        "No embedding API key found (EMBEDDING_API_KEY / OPENAI_API_KEY both empty). "
        "Embedding calls will fall back to per-user key or DeepSeek key — "
        "RAG/Q&A may be unavailable if those are also absent."
    )

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
    import httpx
    local_proxy = os.environ.get("EMBEDDING_PROXY") or None
    http_client = httpx.Client(
        timeout=httpx.Timeout(60.0, connect=5.0),
        proxy=local_proxy,
    )
    return OpenAI(
        api_key=api_key,
        base_url=EMBEDDING_BASE_URL,
        http_client=http_client,
        max_retries=0,
    )


def generate_embedding(text: str, user_id: int | None = None) -> list[float]:
    """调用 OpenAI-compatible embedding API 生成向量。"""
    client = _get_embedding_client(user_id)
    response = client.embeddings.create(
        model=EMBEDDING_MODEL,
        input=text[:8000],
    )
    return [float(value) for value in response.data[0].embedding]


EMBEDDING_BATCH_SIZE = 10  # OpenAI text-embedding-3-small 支持到 2048，先保守限 10


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
        except Exception as exc:
            logger.warning(
                "generate_embeddings_batch failed for chunk %d-%d: %s. "
                "base_url=%s model=%s key_source=%s",
                i,
                i + len(batch),
                exc,
                EMBEDDING_BASE_URL,
                EMBEDDING_MODEL,
                "EMBEDDING_API_KEY" if EMBEDDING_API_KEY else (
                    "OPENAI_API_KEY" if OPENAI_API_KEY else "fallback/user"
                ),
            )
            all_embeddings.extend([] for _ in batch)

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
    embedding_updates = []
    for comment, embedding in zip(valid_comments, embeddings):
        if embedding:
            embedding_updates.append({"comment_id": int(comment["id"]), "embedding": embedding})
    embedded = update_comment_embeddings_batch(user_id, embedding_updates)

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
    embedding_updates = []
    for comment, embedding in zip(targets, embeddings):
        if embedding:
            embedding_updates.append({"comment_id": int(comment["id"]), "embedding": embedding})
    return update_comment_embeddings_batch(user_id, embedding_updates)


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
    history: list[dict] | None = None,
    products_meta: list[dict] | None = None,
    locale: str = "en",
) -> dict:
    """路由到对应 handler 生成回答，返回 {answer, citations, retrieval_method, intent, aggregation_snapshot}."""
    # 延迟导入避免循环依赖（qa_handlers 会 import rag 里的原语）
    from review_analyzer.qa_handlers import INTENT_HANDLERS, retrieval_handler  # noqa: PLC0415
    from review_analyzer.qa_intent import classify_intent  # noqa: PLC0415

    intent_result = classify_intent(question, products_meta, history)
    intent = intent_result["intent"]
    handler = INTENT_HANDLERS.get(intent, retrieval_handler)

    kwargs: dict = {"fallback": retrieval_handler, "locale": locale}
    if intent == "product_compare":
        kwargs["products_meta"] = products_meta

    result = handler(
        user_id,
        question,
        comments,
        top_k,
        history,
        intent_result,
        **kwargs,
    )

    return {
        "answer": result["answer"],
        "citations": result["citations"],
        "retrieval_method": result["retrieval_method"],
        "intent": intent,
        "aggregation_snapshot": result.get("aggregation_snapshot"),
    }
