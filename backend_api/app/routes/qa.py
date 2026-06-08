from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from backend_api.app.deps import get_current_user
from backend_api.app.schemas.analysis import QaAskRequest, QaAskResponse, QaCitationPayload, QaProductPayload
from review_analyzer.database import get_comments
from review_analyzer.paddle_billing import is_pro_user
from review_analyzer.product_store import get_product_overview_rows
from review_analyzer.rag import answer_question


router = APIRouter(prefix="/qa", tags=["qa"])

MAX_QA_PRODUCTS = 5


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
    result = answer_question(user_id, payload.question.strip(), selected_comments, top_k=payload.top_k)
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
