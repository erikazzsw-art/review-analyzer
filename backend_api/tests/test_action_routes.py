"""actions 路由回归测试."""

from __future__ import annotations

from fastapi.testclient import TestClient

from backend_api.app.deps import get_current_user
from backend_api.app.main import app


def _action_row(action_id: int = 12) -> dict:
    return {
        "id": action_id,
        "user_id": 7,
        "product_id": 3,
        "variant_id": None,
        "session_id": 21,
        "source_product_id": "PARENT-1",
        "source_version": "V1",
        "source_batch_label": "2026-07",
        "title": "Improve the waterproofing.",
        "tag_name": "waterproofing",
        "tag_type": "issue",
        "aspect_key": "waterproof_performance",
        "canonical_issue_key": "water_leaks_through",
        "specific_issue": "Water Leaks Through",
        "current_pct": 18.2,
        "owner_role": "产研",
        "suggested_action": "Improve seam sealing.",
        "ai_suggestions_json": ["Improve seam sealing."],
        "expected_effect_batch": None,
        "expected_review_at": None,
        "status": "pending_review",
        "sort_order": 0,
        "removed_at": None,
        "created_at": None,
        "parent_product_id": "PARENT-1",
        "product_name": "Rain Jacket",
        "variant_sku": None,
        "child_asin": None,
        "source_reviews_json": [{"id": 101, "content": "Water leaked in after a storm."}],
        "product_group_key": "product:3",
        "product_group_name": "Rain Jacket",
        "product_note": None,
        "product_sort_order": None,
    }


def _tracker_row(action_id: int = 12) -> dict:
    return {
        "id": 33,
        "user_id": 7,
        "action_item_id": action_id,
        "product_id": 3,
        "variant_id": None,
        "tracker_title": "waterproofing 复盘",
        "tag_name": "waterproofing",
        "aspect_key": "waterproof_performance",
        "canonical_issue_key": "water_leaks_through",
        "specific_issue": "Water Leaks Through",
        "baseline_pct": 18.2,
        "improvement_action": "Improve seam sealing.",
        "effective_batch": None,
        "review_scope": None,
        "current_pct": None,
        "result_status": "pending",
        "conclusion": None,
        "closed_at": None,
        "created_at": None,
        "action_title": None,
        "source_product_id": None,
        "source_version": None,
        "expected_review_at": None,
        "parent_product_id": None,
        "product_name": None,
        "variant_sku": None,
        "child_asin": None,
    }


def test_create_tracker_from_action_reuses_existing_tracker(monkeypatch):
    captured: dict[str, object] = {}

    monkeypatch.setattr("backend_api.app.routes.actions.get_action_item_by_id", lambda user_id, action_id: _action_row(action_id))
    monkeypatch.setattr(
        "backend_api.app.routes.actions.get_review_tracker_by_action_id",
        lambda user_id, action_id: _tracker_row(action_id),
    )

    def fake_update_action_status(user_id: int, action_id: int, status: str) -> None:
        captured["status"] = status

    monkeypatch.setattr("backend_api.app.routes.actions.update_action_status", fake_update_action_status)
    monkeypatch.setattr(
        "backend_api.app.routes.actions.create_review_tracker",
        lambda user_id, data: (_ for _ in ()).throw(AssertionError("should not create duplicate tracker")),
    )
    app.dependency_overrides[get_current_user] = lambda: {"id": 7, "username": "alice"}

    try:
        client = TestClient(app)
        response = client.post(
            "/actions/12/tracker",
            json={
                "tracker_title": "waterproofing 复盘",
                "tag_name": "waterproofing",
                "result_status": "pending",
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert captured["status"] == "pending_review"
    assert response.json()["action"]["status"] == "pending_review"
    assert response.json()["tracker"]["id"] == 33
    assert response.json()["tracker"]["aspect_key"] == "waterproof_performance"
    assert response.json()["tracker"]["canonical_issue_key"] == "water_leaks_through"
    assert response.json()["tracker"]["specific_issue"] == "Water Leaks Through"


def test_create_action_accepts_specific_issue_metadata(monkeypatch):
    captured: dict[str, object] = {}

    def fake_create_action_item(user_id: int, data: dict) -> int:
        captured["user_id"] = user_id
        captured["data"] = data
        return 12

    monkeypatch.setattr("backend_api.app.routes.actions.create_action_item", fake_create_action_item)
    monkeypatch.setattr("backend_api.app.routes.actions.get_action_item_by_id", lambda user_id, action_id: _action_row(action_id))
    app.dependency_overrides[get_current_user] = lambda: {"id": 7, "username": "alice"}

    try:
        client = TestClient(app)
        response = client.post(
            "/actions",
            json={
                "product_id": 3,
                "session_id": 21,
                "source_product_id": "PARENT-1",
                "source_version": "V1",
                "title": "Fix leaking issue",
                "tag_name": "Water Leaks Through",
                "tag_type": "issue",
                "aspect_key": "waterproof_performance",
                "canonical_issue_key": "water_leaks_through",
                "specific_issue": "Water Leaks Through",
                "current_pct": 18.2,
                "recommended_action_key": "improve_waterproofing",
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    data = captured["data"]
    assert isinstance(data, dict)
    assert captured["user_id"] == 7
    assert data["aspect_key"] == "waterproof_performance"
    assert data["canonical_issue_key"] == "water_leaks_through"
    assert data["specific_issue"] == "Water Leaks Through"
    assert "recommended_action_key" not in data
    assert response.json()["aspect_key"] == "waterproof_performance"
    assert response.json()["canonical_issue_key"] == "water_leaks_through"
    assert response.json()["specific_issue"] == "Water Leaks Through"
    assert "recommended_action_key" not in response.json()


def test_create_tracker_from_action_inherits_specific_issue_metadata(monkeypatch):
    captured: dict[str, object] = {}
    created = {"value": False}

    monkeypatch.setattr("backend_api.app.routes.actions.get_action_item_by_id", lambda user_id, action_id: _action_row(action_id))

    def fake_get_review_tracker_by_action_id(user_id: int, action_id: int):
        return _tracker_row(action_id) if created["value"] else None

    def fake_create_review_tracker(user_id: int, data: dict) -> int:
        captured["user_id"] = user_id
        captured["data"] = data
        created["value"] = True
        return 33

    monkeypatch.setattr("backend_api.app.routes.actions.get_review_tracker_by_action_id", fake_get_review_tracker_by_action_id)
    monkeypatch.setattr("backend_api.app.routes.actions.create_review_tracker", fake_create_review_tracker)
    monkeypatch.setattr("backend_api.app.routes.actions.update_action_status", lambda user_id, action_id, status: None)
    app.dependency_overrides[get_current_user] = lambda: {"id": 7, "username": "alice"}

    try:
        client = TestClient(app)
        response = client.post(
            "/actions/12/tracker",
            json={
                "tracker_title": "Water leak validation",
                "result_status": "pending",
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    data = captured["data"]
    assert isinstance(data, dict)
    assert captured["user_id"] == 7
    assert data["aspect_key"] == "waterproof_performance"
    assert data["canonical_issue_key"] == "water_leaks_through"
    assert data["specific_issue"] == "Water Leaks Through"
    assert response.json()["tracker"]["aspect_key"] == "waterproof_performance"


def test_remove_product_group_returns_removed_count(monkeypatch):
    monkeypatch.setattr("backend_api.app.routes.actions.remove_product_group_actions", lambda user_id, key: 4)
    app.dependency_overrides[get_current_user] = lambda: {"id": 7, "username": "alice"}

    try:
        client = TestClient(app)
        response = client.post("/actions/product-groups/remove", json={"product_group_key": "product:3"})
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {"removed": 4}


def test_remove_product_group_reports_empty_group(monkeypatch):
    monkeypatch.setattr("backend_api.app.routes.actions.remove_product_group_actions", lambda user_id, key: 0)
    app.dependency_overrides[get_current_user] = lambda: {"id": 7, "username": "alice"}

    try:
        client = TestClient(app)
        response = client.post("/actions/product-groups/remove", json={"product_group_key": "product:missing"})
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404


def test_reorder_actions_rejects_invalid_group(monkeypatch):
    monkeypatch.setattr("backend_api.app.routes.actions.reorder_actions", lambda user_id, key, action_ids: False)
    app.dependency_overrides[get_current_user] = lambda: {"id": 7, "username": "alice"}

    try:
        client = TestClient(app)
        response = client.patch(
            "/actions/reorder",
            json={"product_group_key": "product:3", "action_ids": [1, 2]},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 400
