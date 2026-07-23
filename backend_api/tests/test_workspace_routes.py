"""workspace 路由回归测试."""

from __future__ import annotations

from fastapi.testclient import TestClient

from backend_api.app.deps import get_current_user
from backend_api.app.main import app


def test_workspace_summary_normalizes_invalid_upstream_data(monkeypatch):
    def fake_get_workspace_summary(user_id: int, lang: str):
        return {
            "intro": {
                "headline": None,
                "focus": "",
            },
            "metrics": {
                "product_count": "12",
                "risk_product_count": None,
                "open_action_count": 3,
                "open_tracker_count": 2,
                "recent_upload_count": 1,
            },
            "today_tasks": [
                {
                    "category": None,
                    "title": "",
                    "description": None,
                    "cta_label": None,
                    "page": None,
                    "session_updates": ["broken"],
                }
            ],
            "risk_products": [
                {
                    "product_id": 123,
                    "product_name": None,
                    "negative_rate": "42.5",
                    "top_issue": None,
                    "pending_review_count": "7",
                    "review_count": None,
                    "latest_session_label": None,
                }
            ],
            "pending_trackers": [
                {
                    "title": None,
                    "product_name": None,
                    "tag_name": None,
                    "status": None,
                    "baseline_pct": "8.5",
                    "current_pct": None,
                    "review_scope": None,
                }
            ],
            "role_action_summary": [
                {
                    "role": None,
                    "count": "9",
                }
            ],
            "recent_sessions": [
                {
                    "session_id": "6",
                    "title": None,
                    "product_id": None,
                    "workflow_purpose": None,
                    "created_at": None,
                    "total_reviews": "18",
                }
            ],
    }

    monkeypatch.setattr("backend_api.app.routes.workspace.get_workspace_summary", fake_get_workspace_summary)
    app.dependency_overrides[get_current_user] = lambda: {"id": 1, "username": "alice"}

    try:
        client = TestClient(app)
        response = client.get("/workspace/summary")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert "role" not in payload
    assert payload["intro"]["headline"] == "欢迎回来"
    assert payload["intro"]["focus"] == "工作台数据正在加载。"
    assert payload["metrics"]["product_count"] == 0
    assert payload["today_tasks"][0]["page"] == "/workspace"
    assert payload["risk_products"][0]["product_name"] == "未命名产品"
    assert payload["risk_products"][0]["product_id"] is None
    assert payload["recent_sessions"][0]["session_id"] == 0
