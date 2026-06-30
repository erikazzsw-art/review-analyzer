from __future__ import annotations

from fastapi import APIRouter, Depends

from backend_api.app.deps import get_current_user
from backend_api.app.schemas.auth import UserPayload
from review_analyzer.database import get_connection, get_user_plan

router = APIRouter(tags=["me"])


@router.get("/me", response_model=UserPayload)
def get_me(current_user: dict = Depends(get_current_user)) -> UserPayload:
    user_id = int(current_user["id"])
    is_admin = _check_admin(user_id)
    return UserPayload(
        id=user_id,
        username=str(current_user["username"]),
        email=str(current_user.get("email") or ""),
        plan=get_user_plan(user_id),
        is_admin=is_admin,
    )


def _check_admin(user_id: int) -> bool:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT is_admin FROM users WHERE id = %s", (user_id,))
            row = cur.fetchone()
            return bool(row and row[0])
    except Exception:
        return False
    finally:
        conn.close()
