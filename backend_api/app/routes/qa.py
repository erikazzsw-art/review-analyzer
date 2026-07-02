from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException, status

from backend_api.app.deps import get_current_user
from backend_api.app.schemas.analysis import (
    QaAskRequest,
    QaAskResponse,
    QaCitationPayload,
    QaConversationCreate,
    QaConversationResponse,
    QaMessageCreate,
    QaMessageResponse,
    QaProductPayload,
)
from review_analyzer.database import get_comments, get_connection
from review_analyzer.paddle_billing import is_pro_user
from review_analyzer.product_store import get_product_overview_rows
from review_analyzer.quota import quota_check, quota_consume
from review_analyzer.rag import answer_question

router = APIRouter(prefix="/qa", tags=["qa"])

MAX_QA_PRODUCTS = 5
MAX_HISTORY_TURNS = 10


@router.get("/products", response_model=list[QaProductPayload])
def list_qa_products(current_user: dict = Depends(get_current_user)) -> list[QaProductPayload]:
    user_id = int(current_user["id"])
    if not is_pro_user(user_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Review Q&A is a Pro feature.")

    rows = get_product_overview_rows(user_id)
    return [
        QaProductPayload(
            id=int(row["id"]) if row.get("id") is not None else None,
            parent_product_id=str(row["parent_product_id"]),
            name=row.get("name"),
            review_count=int(row.get("review_count") or 0),
            negative_rate=float(row.get("negative_rate") or 0.0),
            latest_session_label=row.get("latest_session_label"),
        )
        for row in rows
        if row.get("parent_product_id")
    ]


@router.post("/ask", response_model=QaAskResponse)
@router.post("/questions", response_model=QaAskResponse)
def ask_reviews(
    payload: QaAskRequest,
    current_user: dict = Depends(get_current_user),
) -> QaAskResponse:
    user_id = int(current_user["id"])
    if not is_pro_user(user_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Review Q&A is a Pro feature.")

    product_ids = [value.strip() for value in payload.product_ids if value and value.strip()]
    if not product_ids:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Please select at least one product.")
    if len(product_ids) > MAX_QA_PRODUCTS:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="You can ask about at most 5 products.")
    if not payload.question.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Please enter a question.")

    product_rows = get_product_overview_rows(user_id)
    product_map = {str(row["parent_product_id"]): row for row in product_rows if row.get("parent_product_id")}
    selected_rows = [product_map[product_id] for product_id in product_ids if product_id in product_map]
    selected_comments = []
    for product_id in product_ids:
        selected_comments.extend(get_comments(user_id, product_id=product_id))

    if not selected_comments:
        return QaAskResponse(answer="No review data is available for the selected products.", retrieval_method="text")

    selected_comments = _dedupe_comments(selected_comments)

    allowed, msg = quota_check(user_id, "ask_review")
    if not allowed:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=msg)

    result = answer_question(
        user_id,
        payload.question.strip(),
        selected_comments,
        top_k=payload.top_k,
        products_meta=selected_rows,
    )
    quota_consume(user_id, "ask_review")

    citations = [
        QaCitationPayload(
            id=int(comment["id"]) if comment.get("id") is not None else None,
            product_id=str(comment.get("product_id") or "") or None,
            version=str(comment.get("version") or "") or None,
            session_id=int(comment["session_id"]) if comment.get("session_id") is not None else None,
            date=str(comment.get("date") or "") or None,
            rating=int(comment["rating"]) if comment.get("rating") is not None else None,
            content=str(comment.get("content") or "") or None,
            issue_tag=str(comment.get("issue_tag") or "") or None,
            highlight_tag=str(comment.get("highlight_tag") or "") or None,
            sentiment=str(comment.get("sentiment") or "") or None,
        )
        for comment in result.get("citations", [])
    ]
    return QaAskResponse(
        answer=str(result.get("answer") or ""),
        retrieval_method=str(result.get("retrieval_method") or "text"),
        intent=result.get("intent"),
        aggregation_snapshot=result.get("aggregation_snapshot"),
        selected_products=[
            QaProductPayload(
                id=int(row["id"]) if row.get("id") is not None else None,
                parent_product_id=str(row["parent_product_id"]),
                name=row.get("name"),
                review_count=int(row.get("review_count") or 0),
                negative_rate=float(row.get("negative_rate") or 0.0),
                latest_session_label=row.get("latest_session_label"),
            )
            for row in selected_rows
        ],
        citations=citations,
    )


def _dedupe_comments(comments: list[dict]) -> list[dict]:
    seen: set[str] = set()
    deduped: list[dict] = []
    for comment in comments:
        key = str(comment.get("content_hash") or comment.get("id") or "")
        if key and key in seen:
            continue
        if key:
            seen.add(key)
        deduped.append(comment)
    return deduped


# ──────────────────────────────────────────────────────────────
# Conversation endpoints (multi-turn)
# ──────────────────────────────────────────────────────────────


@router.post("/conversations", response_model=QaConversationResponse)
def create_conversation(
    payload: QaConversationCreate,
    current_user: dict = Depends(get_current_user),
) -> QaConversationResponse:
    user_id = int(current_user["id"])
    if not is_pro_user(user_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Review Q&A is a Pro feature.")

    product_ids = [v.strip() for v in payload.product_ids if v and v.strip()]
    if not product_ids:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Please select at least one product.")
    if len(product_ids) > MAX_QA_PRODUCTS:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="You can select at most 5 products.")

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO qa_conversations (user_id, product_ids) VALUES (%s, %s) RETURNING id, created_at, updated_at",
                (user_id, product_ids),
            )
            row = cur.fetchone()
            conn.commit()
    finally:
        conn.close()

    return QaConversationResponse(
        id=row[0],
        product_ids=product_ids,
        title=None,
        created_at=row[1].isoformat(),
        updated_at=row[2].isoformat(),
    )


@router.get("/conversations", response_model=list[QaConversationResponse])
def list_conversations(
    current_user: dict = Depends(get_current_user),
) -> list[QaConversationResponse]:
    user_id = int(current_user["id"])
    if not is_pro_user(user_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Review Q&A is a Pro feature.")

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, product_ids, title, created_at, updated_at FROM qa_conversations WHERE user_id = %s ORDER BY updated_at DESC LIMIT 50",
                (user_id,),
            )
            rows = cur.fetchall()
    finally:
        conn.close()

    return [
        QaConversationResponse(
            id=r[0],
            product_ids=r[1] or [],
            title=r[2],
            created_at=r[3].isoformat(),
            updated_at=r[4].isoformat(),
        )
        for r in rows
    ]


@router.get("/conversations/{conversation_id}/messages", response_model=list[QaMessageResponse])
def get_conversation_messages(
    conversation_id: int,
    current_user: dict = Depends(get_current_user),
) -> list[QaMessageResponse]:
    user_id = int(current_user["id"])
    _verify_conversation_owner(conversation_id, user_id)

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, conversation_id, role, content, citations, retrieval_method, intent, aggregation_snapshot, created_at FROM qa_messages WHERE conversation_id = %s ORDER BY created_at ASC",
                (conversation_id,),
            )
            rows = cur.fetchall()
    finally:
        conn.close()

    return [
        QaMessageResponse(
            id=r[0],
            conversation_id=r[1],
            role=r[2],
            content=r[3],
            citations=_parse_citations_json(r[4]),
            retrieval_method=r[5],
            intent=r[6],
            aggregation_snapshot=_parse_snapshot_json(r[7]),
            created_at=r[8].isoformat(),
        )
        for r in rows
    ]


@router.post("/conversations/{conversation_id}/messages", response_model=QaMessageResponse)
def send_message(
    conversation_id: int,
    payload: QaMessageCreate,
    current_user: dict = Depends(get_current_user),
) -> QaMessageResponse:
    user_id = int(current_user["id"])
    if not is_pro_user(user_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Review Q&A is a Pro feature.")

    conv = _verify_conversation_owner(conversation_id, user_id)
    product_ids = conv["product_ids"]
    question = payload.question.strip()
    if not question:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Please enter a question.")

    history = _get_history_messages(conversation_id)

    selected_comments: list[dict] = []
    for pid in product_ids:
        selected_comments.extend(get_comments(user_id, product_id=pid))
    if not selected_comments:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No review data available for selected products.")
    selected_comments = _dedupe_comments(selected_comments)

    allowed, msg = quota_check(user_id, "ask_review")
    if not allowed:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=msg)

    product_rows = get_product_overview_rows(user_id)
    product_map = {str(row["parent_product_id"]): row for row in product_rows if row.get("parent_product_id")}
    selected_rows_for_conv = [product_map[pid] for pid in product_ids if pid in product_map]

    result = answer_question(
        user_id,
        question,
        selected_comments,
        top_k=payload.top_k,
        history=history,
        products_meta=selected_rows_for_conv,
    )
    quota_consume(user_id, "ask_review")
    answer = str(result.get("answer") or "")
    citations_raw = result.get("citations", [])
    retrieval_method = str(result.get("retrieval_method") or "text")
    intent = result.get("intent")
    aggregation_snapshot = result.get("aggregation_snapshot")

    citations_payload = [
        QaCitationPayload(
            id=int(c["id"]) if c.get("id") is not None else None,
            product_id=str(c.get("product_id") or "") or None,
            version=str(c.get("version") or "") or None,
            session_id=int(c["session_id"]) if c.get("session_id") is not None else None,
            date=str(c.get("date") or "") or None,
            rating=int(c["rating"]) if c.get("rating") is not None else None,
            content=str(c.get("content") or "") or None,
            issue_tag=str(c.get("issue_tag") or "") or None,
            highlight_tag=str(c.get("highlight_tag") or "") or None,
            sentiment=str(c.get("sentiment") or "") or None,
        )
        for c in citations_raw
    ]

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO qa_messages (conversation_id, role, content) VALUES (%s, 'user', %s)",
                (conversation_id, question),
            )
            cur.execute(
                "INSERT INTO qa_messages (conversation_id, role, content, citations, retrieval_method, intent, aggregation_snapshot) VALUES (%s, 'assistant', %s, %s, %s, %s, %s) RETURNING id, created_at",
                (
                    conversation_id,
                    answer,
                    json.dumps([c.model_dump() for c in citations_payload]),
                    retrieval_method,
                    intent,
                    json.dumps(aggregation_snapshot, ensure_ascii=False) if aggregation_snapshot else None,
                ),
            )
            row = cur.fetchone()
            title_update = ""
            if not conv.get("title") and question:
                title_update = question[:50]
                cur.execute(
                    "UPDATE qa_conversations SET title = %s, updated_at = NOW() WHERE id = %s",
                    (title_update, conversation_id),
                )
            else:
                cur.execute(
                    "UPDATE qa_conversations SET updated_at = NOW() WHERE id = %s",
                    (conversation_id,),
                )
            conn.commit()
    finally:
        conn.close()

    return QaMessageResponse(
        id=row[0],
        conversation_id=conversation_id,
        role="assistant",
        content=answer,
        citations=citations_payload,
        retrieval_method=retrieval_method,
        intent=intent,
        aggregation_snapshot=aggregation_snapshot,
        created_at=row[1].isoformat(),
    )


def _verify_conversation_owner(conversation_id: int, user_id: int) -> dict:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, user_id, product_ids, title FROM qa_conversations WHERE id = %s",
                (conversation_id,),
            )
            row = cur.fetchone()
    finally:
        conn.close()

    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found.")
    if row[1] != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")
    return {"id": row[0], "user_id": row[1], "product_ids": row[2] or [], "title": row[3]}


def _get_history_messages(conversation_id: int) -> list[dict]:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT role, content FROM qa_messages WHERE conversation_id = %s ORDER BY created_at ASC",
                (conversation_id,),
            )
            rows = cur.fetchall()
    finally:
        conn.close()

    messages = [{"role": r[0], "content": r[1]} for r in rows]
    if len(messages) > MAX_HISTORY_TURNS * 2:
        messages = messages[-(MAX_HISTORY_TURNS * 2):]
    return messages


def _parse_citations_json(raw) -> list[QaCitationPayload]:
    if not raw:
        return []
    if isinstance(raw, str):
        raw = json.loads(raw)
    return [QaCitationPayload(**item) for item in raw]


def _parse_snapshot_json(raw) -> dict | None:
    if not raw:
        return None
    if isinstance(raw, str):
        return json.loads(raw)
    if isinstance(raw, dict):
        return raw
    return None
