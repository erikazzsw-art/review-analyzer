"""products 路由回归测试."""

from __future__ import annotations

from fastapi.testclient import TestClient

from backend_api.app.deps import get_current_user
from backend_api.app.main import app
from review_analyzer.product_store import ProductParentNameConflictError


def _overview_row(
    *,
    product_id: int | None,
    parent_product_id: str,
    name: str | None = None,
    is_archived_from_sessions: bool = False,
) -> dict:
    return {
        "id": product_id,
        "parent_product_id": parent_product_id,
        "name": name,
        "platform": "amazon",
        "category": None,
        "lifecycle_stage": "growth",
        "current_version": "V1",
        "core_selling_points": None,
        "main_competitors": None,
        "owner_role": None,
        "production_cycle_days": None,
        "is_archived_from_sessions": is_archived_from_sessions,
        "review_count": 0,
        "positive_rate": 0.0,
        "negative_rate": 0.0,
        "top_issue": None,
        "top_highlight": None,
        "variant_count": 0,
        "variants": [],
        "versions": [],
        "session_versions": [],
        "version_date_ranges": {},
        "session_count": 0,
        "pending_review_count": 0,
        "latest_session_label": None,
        "latest_updated_at": None,
        "latest_review_date": None,
        "earliest_review_date": None,
        "image_url": None,
        "brand": None,
        "rating": None,
        "ratings_total": None,
        "reviews_total": None,
    }


def test_get_products_excludes_archived_session_rows(monkeypatch):
    monkeypatch.setattr(
        "backend_api.app.routes.products.get_product_overview_rows",
        lambda user_id: [
            _overview_row(product_id=12, parent_product_id="Parent A", name="Desk Lamp"),
            _overview_row(
                product_id=None,
                parent_product_id="Wader",
                is_archived_from_sessions=True,
            ),
        ],
    )
    app.dependency_overrides[get_current_user] = lambda: {"id": 7, "username": "alice"}

    try:
        client = TestClient(app)
        response = client.get("/products")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["total"] == 1
    assert [item["parent_product_id"] for item in response.json()["items"]] == ["Parent A"]


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


def test_update_product_accepts_name_without_rewriting_parent_product_id(monkeypatch):
    captured: dict[str, object] = {}

    monkeypatch.setattr(
        "backend_api.app.routes.products.get_product_by_id",
        lambda user_id, product_id: {"id": product_id, "parent_product_id": "B0PLUGIN01"},
    )

    def fake_update_product(user_id: int, product_id: int, data: dict):
        captured["data"] = data
        return True

    monkeypatch.setattr("backend_api.app.routes.products.update_product", fake_update_product)
    app.dependency_overrides[get_current_user] = lambda: {"id": 7, "username": "alice"}

    try:
        client = TestClient(app)
        response = client.patch("/products/12", json={"name": "TIDEWE-下水服-WD001"})
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert captured["data"] == {"name": "TIDEWE-下水服-WD001"}


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


def test_get_product_detail_includes_listing_metadata(monkeypatch):
    monkeypatch.setattr(
        "backend_api.app.routes.products.get_product_by_id",
        lambda user_id, product_id: {
            "id": product_id,
            "user_id": user_id,
            "parent_product_id": "TIDEWE-下水服-WD001",
            "name": "TIDEWE-下水服-WD001",
            "platform": "amazon",
        },
    )
    monkeypatch.setattr(
        "backend_api.app.routes.products.get_variants_with_review_counts",
        lambda user_id, product_id: [],
    )
    monkeypatch.setattr(
        "backend_api.app.routes.products.get_product_listing_by_product_id",
        lambda user_id, product_id: {
            "parent_asin": "B0B14JY8S8",
            "marketplace": "us",
            "title": "TIDEWE Bootfoot Chest Wader",
            "scraped_at": None,
        },
    )
    app.dependency_overrides[get_current_user] = lambda: {"id": 7, "username": "alice"}

    try:
        client = TestClient(app)
        response = client.get("/products/12/detail")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["listing"] == {
        "parent_asin": "B0B14JY8S8",
        "marketplace": "us",
        "title": "TIDEWE Bootfoot Chest Wader",
        "scraped_at": None,
    }


def test_search_products_matches_variant_asin(monkeypatch):
    monkeypatch.setattr(
        "backend_api.app.routes.products.get_product_overview_rows",
        lambda user_id: [
            {
                "id": 12,
                "parent_product_id": "Parent A",
                "name": "Desk Lamp",
                "review_count": 20,
                "session_count": 1,
                "variants": [
                    {"child_asin": "B0ASINMATCH", "variant_sku": "B0ASINMATCH", "name": "Black"},
                ],
            },
            {
                "id": 13,
                "parent_product_id": "Parent B",
                "name": "Other Lamp",
                "review_count": 50,
                "session_count": 0,
                "variants": [],
            },
        ],
    )
    app.dependency_overrides[get_current_user] = lambda: {"id": 7, "username": "alice"}

    try:
        client = TestClient(app)
        response = client.get("/products/search", params={"q": "b0asinmatch"})
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["items"] == [
        {
            "id": 12,
            "parent_product_id": "Parent A",
            "name": "Desk Lamp",
            "variant_asins": ["B0ASINMATCH"],
            "variants": [{"child_asin": "B0ASINMATCH", "name": "Black"}],
            "review_count": 20,
            "session_count": 1,
            "latest_session_id": None,
        }
    ]


def test_search_products_includes_product_management_items_without_sessions(monkeypatch):
    monkeypatch.setattr(
        "backend_api.app.routes.products.get_product_overview_rows",
        lambda user_id: [
            {
                "id": 12,
                "parent_product_id": "Parent A",
                "name": "Desk Lamp",
                "review_count": 0,
                "session_count": 0,
                "variants": [],
            },
        ],
    )
    app.dependency_overrides[get_current_user] = lambda: {"id": 7, "username": "alice"}

    try:
        client = TestClient(app)
        response = client.get("/products/search", params={"q": "desk"})
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["items"][0]["parent_product_id"] == "Parent A"


def test_search_products_matches_variant_product_name(monkeypatch):
    monkeypatch.setattr(
        "backend_api.app.routes.products.get_product_overview_rows",
        lambda user_id: [
            {
                "id": 12,
                "parent_product_id": "Parent A",
                "name": "Parent Group Name",
                "review_count": 20,
                "session_count": 1,
                "variants": [
                    {"child_asin": "B0ASINMATCH", "variant_sku": "B0ASINMATCH", "name": "Desk Lamp Black"},
                ],
            },
        ],
    )
    app.dependency_overrides[get_current_user] = lambda: {"id": 7, "username": "alice"}

    try:
        client = TestClient(app)
        response = client.get("/products/search", params={"q": "desk lamp black"})
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["items"][0]["parent_product_id"] == "Parent A"
    assert response.json()["items"][0]["variants"] == [
        {"child_asin": "B0ASINMATCH", "name": "Desk Lamp Black"}
    ]


def test_search_products_matches_normalized_similar_parent_name(monkeypatch):
    monkeypatch.setattr(
        "backend_api.app.routes.products.get_product_overview_rows",
        lambda user_id: [
            {
                "id": 12,
                "parent_product_id": "TIDEWE-下水服-WD001",
                "name": "TIDEWE-下水服-WD001",
                "review_count": 100,
                "session_count": 1,
                "variants": [],
            },
        ],
    )
    app.dependency_overrides[get_current_user] = lambda: {"id": 7, "username": "alice"}

    try:
        client = TestClient(app)
        response = client.get("/products/search", params={"q": "tidewe 下水服 wd001"})
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["items"][0]["parent_product_id"] == "TIDEWE-下水服-WD001"


def test_search_products_excludes_archived_session_rows(monkeypatch):
    monkeypatch.setattr(
        "backend_api.app.routes.products.get_product_overview_rows",
        lambda user_id: [
            {
                "id": None,
                "parent_product_id": "Wader",
                "name": None,
                "is_archived_from_sessions": True,
                "review_count": 340,
                "session_count": 1,
                "variants": [],
            },
        ],
    )
    app.dependency_overrides[get_current_user] = lambda: {"id": 7, "username": "alice"}

    try:
        client = TestClient(app)
        response = client.get("/products/search", params={"q": "wader"})
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["items"] == []
    assert response.json()["total"] == 0
