"""analysis results route variant-scope regressions."""

from __future__ import annotations

from fastapi.testclient import TestClient

from backend_api.app.deps import get_current_user
from backend_api.app.main import app


def test_analysis_results_filters_by_variant_asin(monkeypatch):
    captured: list[dict[str, object]] = []

    def fake_get_comments(user_id: int, **kwargs):
        captured.append(kwargs)
        return [
            {
                "id": 1,
                "product_id": kwargs.get("product_id"),
                "source_variant_asin": kwargs.get("source_variant_asin"),
                "content": "Works well",
                "sentiment": "positive",
                "date": "2026-01-01",
            }
        ]

    monkeypatch.setattr("backend_api.app.routes.analysis.get_comments", fake_get_comments)
    monkeypatch.setattr("backend_api.app.routes.analysis.get_sessions", lambda *args, **kwargs: [])
    monkeypatch.setattr(
        "backend_api.app.routes.analysis._cached_build_insights",
        lambda *args, **kwargs: {"consumer_profile": {"summary": "ok"}},
    )
    monkeypatch.setattr("backend_api.app.routes.analysis.credit_consume", lambda *args, **kwargs: None)
    app.dependency_overrides[get_current_user] = lambda: {"id": 7, "username": "alice"}

    try:
        client = TestClient(app)
        response = client.get(
            "/analysis/results",
            params={
                "product_id": "Parent A",
                "variant_asin": "B0ASINMATCH",
                "range": "all",
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert captured[-1]["product_id"] == "Parent A"
    assert captured[-1]["source_variant_asin"] == "B0ASINMATCH"
    body = response.json()
    assert body["context"]["variant_asin"] == "B0ASINMATCH"
    assert body["context"]["scope_label"] == "B0ASINMATCH"
    assert body["session"]["product_id"] == "Parent A"
    assert body["session"]["total_reviews"] == 1
