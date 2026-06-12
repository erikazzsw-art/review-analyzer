"""V4-T4 Step 5: LLM 成本看板 API."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from backend_api.app.deps import get_current_user
from review_analyzer.database import get_llm_usage_stats

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/llm-costs")
def get_llm_costs(
    days: int = Query(default=30, ge=1, le=365),
    user: dict = Depends(get_current_user),
) -> dict:
    rows = get_llm_usage_stats(user_id=user["id"], days=days)
    total_cost = sum(float(r.get("total_cost_yuan") or 0) for r in rows)
    total_calls = sum(int(r.get("call_count") or 0) for r in rows)
    cache_hits = sum(int(r.get("cache_hits") or 0) for r in rows)

    return {
        "summary": {
            "total_cost_yuan": round(total_cost, 4),
            "total_calls": total_calls,
            "cache_hits": cache_hits,
            "cache_rate": round(cache_hits / total_calls * 100, 1) if total_calls else 0,
            "avg_cost_per_call": round(total_cost / (total_calls - cache_hits), 6) if (total_calls - cache_hits) > 0 else 0,
        },
        "daily": [
            {
                "date": str(r["date"]),
                "model": r["model_name"],
                "calls": r["call_count"],
                "tokens_in": r["total_tokens_in"],
                "tokens_out": r["total_tokens_out"],
                "cost_yuan": float(r["total_cost_yuan"] or 0),
                "cache_hits": r["cache_hits"],
            }
            for r in rows
        ],
    }
