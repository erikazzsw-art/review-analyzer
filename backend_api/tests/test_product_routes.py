"""products 路由回归测试."""

from __future__ import annotations

from fastapi.testclient import TestClient

from backend_api.app.deps import get_current_user
from backend_api.app.main import app
from review_analyzer.product_store import ProductParentNameConflictError


def test_update_product_accepts_parent_product_id(monkeypatch):
    captured: dict[str, object] = {}

    monkeypatch.setattr(
        "backend_api.app.routes.products.get_product_by_id",
        lambda user_id, product_id: {"id": product_id, "parent_product_id": "Old Parent"},
    )

    def fake_update_product(user_id: int, product_id: int, data: dict):
        captured["user_id"] = user_id
        captured["product_id"] = product_id
        captured["data"] = data
        return True

    monkeypatch.setattr("backend_api.app.routes.products.update_product", fake_update_product)
    app.dependency_overrides[get_current_user] = lambda: {"id": 7, "username": "alice"}

    try:
        client = TestClient(app)
        response = client.patch(
            "/products/12",
            json={"parent_product_id": "  New Parent  ", "name": "Display Name"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {"updated": True}
    assert captured["user_id"] == 7
    assert captured["product_id"] == 12
    assert captured["data"] == {
        "parent_product_id": "New Parent",
        "name": "Display Name",
    }


def test_update_product_reports_parent_name_conflict(monkeypatch):
    monkeypatch.setattr(
        "backend_api.app.routes.products.get_product_by_id",
        lambda user_id, product_id: {"id": product_id, "parent_product_id": "Old Parent"},
    )

    def fake_update_product(user_id: int, product_id: int, data: dict):
        raise ProductParentNameConflictError("父体名称已存在，请换一个名称。")

    monkeypatch.setattr("backend_api.app.routes.products.update_product", fake_update_product)
    app.dependency_overrides[get_current_user] = lambda: {"id": 7, "username": "alice"}

    try:
        client = TestClient(app)
        response = client.patch("/products/12", json={"parent_product_id": "Existing Parent"})
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 409
    assert response.json()["detail"] == "父体名称已存在，请换一个名称。"
