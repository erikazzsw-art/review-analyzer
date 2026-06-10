from __future__ import annotations

from fastapi import APIRouter, Depends

from backend_api.app.deps import get_current_user
from review_analyzer.quota import get_all_quota_status, get_quota_status

router = APIRouter(tags=["quota"])


@router.get("/quota")
def list_quota(current_user: dict = Depends(get_current_user)) -> list[dict]:
    user_id = int(current_user["id"])
    return get_all_quota_status(user_id)


@router.get("/quota/{dimension}")
def get_dimension_quota(
    dimension: str,
    current_user: dict = Depends(get_current_user),
) -> dict:
    user_id = int(current_user["id"])
    return get_quota_status(user_id, dimension)
