"""Golden Set API — 标杆数据管理端点."""
from __future__ import annotations

import csv
import io
import logging
from typing import Any

from fastapi import APIRouter, Depends, File, Query, UploadFile

from backend_api.app.deps import get_current_user
from backend_api.app.schemas.golden_set import (
    AccuracyStat,
    GoldenSetOut,
    GoldenSetUpload,
)
from review_analyzer.golden_set_store import (
    get_accuracy_stats,
    get_golden_entries,
    get_total_count,
    save_golden_batch,
    toggle_fewshot,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/golden-set", tags=["golden-set"])


@router.post("/upload", response_model=dict)
def upload_golden_set(
    body: GoldenSetUpload,
    user: dict[str, Any] = Depends(get_current_user),
) -> dict:
    """JSON 方式批量上传标注数据."""
    batch_id = save_golden_batch(
        user_id=user["id"],
        items=[item.model_dump() for item in body.items],
        sub_category=body.sub_category,
    )
    return {"batch_id": batch_id, "count": len(body.items)}


@router.post("/upload-csv", response_model=dict)
async def upload_golden_csv(
    file: UploadFile = File(...),
    sub_category: str = Query(default="家具家居"),
    user: dict[str, Any] = Depends(get_current_user),
) -> dict:
    """CSV 文件上传标注数据.

    期望表头: 序号, 英文原文, 原标签, 标签正确？, 原因
    或英文: index, comment_text, aspect_key, is_correct, reason
    """
    content = await file.read()
    text = content.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))

    column_map = {
        "序号": "index",
        "英文原文": "comment_text",
        "原标签": "aspect_key",
        "标签正确？": "is_correct",
        "原因": "reason",
        "comment_text": "comment_text",
        "aspect_key": "aspect_key",
        "is_correct": "is_correct",
        "reason": "reason",
    }

    items: list[dict] = []
    for row in reader:
        mapped: dict[str, Any] = {}
        for orig_key, value in row.items():
            norm_key = column_map.get(orig_key.strip(), orig_key.strip())
            mapped[norm_key] = value

        comment_text = mapped.get("comment_text", "").strip()
        if not comment_text:
            continue

        is_correct_raw = mapped.get("is_correct", "").strip().lower()
        is_correct = is_correct_raw in ("true", "1", "yes", "是", "✅", "正确")

        items.append({
            "comment_text": comment_text,
            "aspect_key": mapped.get("aspect_key", "other").strip(),
            "is_correct": is_correct,
            "reason": mapped.get("reason", "").strip() or None,
            "correct_tag": mapped.get("correct_tag", "").strip() or None,
            "source": "manual",
        })

    if not items:
        return {"batch_id": None, "count": 0, "error": "No valid rows found"}

    batch_id = save_golden_batch(
        user_id=user["id"],
        items=items,
        sub_category=sub_category,
    )
    return {"batch_id": batch_id, "count": len(items)}


@router.get("/entries", response_model=list[GoldenSetOut])
def list_entries(
    sub_category: str | None = Query(default=None),
    aspect_key: str | None = Query(default=None),
    limit: int = Query(default=100, le=500),
    offset: int = Query(default=0),
    user: dict[str, Any] = Depends(get_current_user),
) -> list[dict]:
    """获取 golden_set 条目列表."""
    return get_golden_entries(sub_category, aspect_key, limit=limit, offset=offset)


@router.get("/stats", response_model=list[AccuracyStat])
def accuracy_stats(
    sub_category: str | None = Query(default=None),
    user: dict[str, Any] = Depends(get_current_user),
) -> list[dict]:
    """按标签统计准确率."""
    return get_accuracy_stats(sub_category)


@router.get("/summary", response_model=dict)
def summary(
    sub_category: str | None = Query(default=None),
    user: dict[str, Any] = Depends(get_current_user),
) -> dict:
    """总览：总条目数 + 整体准确率."""
    total = get_total_count(sub_category)
    stats = get_accuracy_stats(sub_category)
    if stats:
        overall_correct = sum(s["correct_count"] for s in stats)
        overall_total = sum(s["total"] for s in stats)
        overall_pct = round(overall_correct / overall_total * 100, 1) if overall_total else None
    else:
        overall_correct = 0
        overall_total = 0
        overall_pct = None
    return {
        "total_entries": total,
        "total_correct": overall_correct,
        "overall_accuracy_pct": overall_pct,
        "aspect_count": len(stats),
    }


@router.patch("/{entry_id}/fewshot", response_model=dict)
def set_fewshot(
    entry_id: int,
    use_as_fewshot: bool = Query(...),
    user: dict[str, Any] = Depends(get_current_user),
) -> dict:
    """切换某条记录的 few-shot 标记."""
    ok = toggle_fewshot(entry_id, use_as_fewshot=use_as_fewshot)
    return {"ok": ok}
