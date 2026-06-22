from __future__ import annotations

import io
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse

from backend_api.app.deps import get_current_user
from review_analyzer.database import get_comments, get_session_by_id
from review_analyzer.insight_engine import build_results_insights

router = APIRouter(prefix="/analysis", tags=["export"])


@router.get("/sessions/{session_id}/export")
def export_module_xlsx(
    session_id: int,
    module: str = Query(default="user_experience"),
    current_user: dict = Depends(get_current_user),
) -> StreamingResponse:
    user_id = int(current_user["id"])
    session = get_session_by_id(user_id, session_id)
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found.")

    comments = get_comments(user_id, session_id=session_id)
    for c in comments:
        c.pop("embedding", None)
    context = _build_context(session)
    modules = build_results_insights(user_id, comments, context)

    module_data = modules.get(module)
    if not module_data or not isinstance(module_data, dict):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Module '{module}' not found.")

    output = _build_xlsx(module, module_data)
    filename = f"analysis_{session_id}_{module}.xlsx"
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def _build_context(session: dict[str, Any]) -> dict[str, Any]:
    start = str(session.get("date_range_start") or "")
    end = str(session.get("date_range_end") or "")
    time_label = f"{start} ~ {end}" if start and end else "All Time"
    return {
        "product_id": str(session.get("product_id") or ""),
        "version": str(session.get("version") or "V1"),
        "time_label": time_label,
        "workflow_purpose": str(session.get("workflow_purpose") or ""),
    }


def _build_xlsx(module_key: str, data: dict[str, Any]) -> io.BytesIO:
    import openpyxl

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = module_key

    summary = str(data.get("summary") or "")
    ws.append(["Summary", summary])
    ws.append([])

    if module_key == "user_experience":
        ws.append(["=== Positive Feedback ==="])
        ws.append(["Rank", "Tag", "Percentage", "Evidence"])
        for i, row in enumerate(data.get("positive") or [], start=1):
            ws.append([i, str(row.get("tag", "")), float(row.get("pct", 0)), str(row.get("reason", ""))])
        ws.append([])
        ws.append(["=== Negative Feedback ==="])
        ws.append(["Rank", "Tag", "Percentage", "Evidence"])
        for i, row in enumerate(data.get("negative") or [], start=1):
            ws.append([i, str(row.get("tag", "")), float(row.get("pct", 0)), str(row.get("reason", ""))])

    elif module_key in ("purchase_motives", "unmet_needs"):
        ws.append(["Rank", "Tag", "Percentage", "Evidence"])
        for i, row in enumerate(data.get("rows") or [], start=1):
            ws.append([i, str(row.get("tag", "")), float(row.get("pct", 0)), str(row.get("reason", ""))])

    elif module_key == "consumer_profile":
        ws.append(["Label", "Detail"])
        for row in data.get("rows") or []:
            ws.append([str(row.get("label", "")), str(row.get("detail", ""))])
        ws.append([])
        ws.append(["Evidence Quotes"])
        for quote in data.get("evidence") or []:
            ws.append([str(quote)])

    elif module_key == "recommendations":
        ws.append(["#", "Label", "Detail"])
        for i, row in enumerate(data.get("rows") or [], start=1):
            ws.append([i, str(row.get("label", "")), str(row.get("detail", ""))])

    else:
        ws.append(["Key", "Value"])
        for k, v in data.items():
            if k == "summary":
                continue
            ws.append([str(k), str(v)[:500]])

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    return output
