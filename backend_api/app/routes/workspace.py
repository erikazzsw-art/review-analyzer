from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, Query

from backend_api.app.deps import get_current_user
from backend_api.app.schemas.workspace import WorkspaceSummaryPayload
from review_analyzer.workspace_store import ROLES, get_workspace_summary


router = APIRouter(prefix="/workspace", tags=["workspace"])


@router.get("/summary", response_model=WorkspaceSummaryPayload)
def get_workspace_summary_route(
    role: str = Query(default="运营"),
    lang: str = Query(default="zh"),
    current_user: dict = Depends(get_current_user),
) -> WorkspaceSummaryPayload:
    selected_role = role if role in ROLES else ROLES[0]
    selected_lang = lang if lang in {"zh", "en"} else "zh"
    summary = get_workspace_summary(
        int(current_user["id"]),
        selected_role,
        selected_lang,
    )
    return WorkspaceSummaryPayload(
        **summary,
        generated_at=datetime.utcnow(),
    )
