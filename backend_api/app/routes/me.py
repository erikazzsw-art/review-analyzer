from __future__ import annotations

from fastapi import APIRouter, Depends

from backend_api.app.deps import get_current_user
from backend_api.app.schemas.auth import UserPayload
from review_analyzer.database import get_user_plan


router = APIRouter(tags=["me"])


@router.get("/me", response_model=UserPayload)
def get_me(current_user: dict = Depends(get_current_user)) -> UserPayload:
    user_id = int(current_user["id"])
    return UserPayload(
        id=user_id,
        username=str(current_user["username"]),
        email=str(current_user.get("email") or ""),
        plan=get_user_plan(user_id),
    )
