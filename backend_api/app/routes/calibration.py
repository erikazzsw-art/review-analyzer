"""Calibration API — 标签校准反馈端点."""
from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, Query

from backend_api.app.deps import get_current_user
from backend_api.app.schemas.calibration import CalibrationCreate, CalibrationOut
from review_analyzer.calibration_store import get_calibrations, save_calibration

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/calibration", tags=["calibration"])


@router.post("", response_model=dict)
def create_calibration(
    body: CalibrationCreate,
    user: dict[str, Any] = Depends(get_current_user),
) -> dict:
    """提交一条标签校准反馈."""
    cal_id = save_calibration(
        user_id=user["id"],
        comment_id=body.comment_id,
        session_id=body.session_id,
        original_tag=body.original_tag,
        correct_tag=body.correct_tag,
        note=body.note,
        sub_category=body.sub_category,
    )
    return {"id": cal_id, "status": "created"}


@router.get("", response_model=list[CalibrationOut])
def list_calibrations(
    sub_category: str = Query(default="家具家居"),
    user: dict[str, Any] = Depends(get_current_user),
) -> list[dict]:
    """获取指定品类的校准列表."""
    return get_calibrations(sub_category)
