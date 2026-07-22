"""taxonomy route localization regression tests."""

from __future__ import annotations

from fastapi.testclient import TestClient

from backend_api.app.deps import get_current_user
from backend_api.app.main import app
from backend_api.app.routes import taxonomy as taxonomy_routes


def test_taxonomy_categories_localizes_labels_to_english(monkeypatch):
    monkeypatch.setattr(
        taxonomy_routes,
        "_load_db_sub_categories",
        lambda: ["冲锋衣", "Baby Bibs"],
    )
    app.dependency_overrides[get_current_user] = lambda: {"id": 7, "username": "alice"}

    try:
        client = TestClient(app)
        response = client.get("/taxonomy/categories", params={"locale": "en"})
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    groups = {group["category_key"]: group for group in response.json()["supported_categories"]}
    assert groups["outdoor"]["category_label"] == "Outdoor Sports"
    assert groups["outdoor"]["sub_category_labels"]["冲锋衣"] == "Hardshell Jacket"
    assert groups["baby"]["category_label"] == "Baby Products"
    assert groups["baby"]["sub_category_labels"]["Baby Bibs"] == "Baby Bibs"
