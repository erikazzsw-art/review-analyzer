"""Tests for label_review routes — admin-only access control."""

from __future__ import annotations

import sys
from pathlib import Path

from fastapi import HTTPException, Request, status
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backend_api.app.deps import get_admin_user
from backend_api.app.main import app


def _fake_non_admin(request: Request):
    """Dependency override simulating a non-admin user hitting get_admin_user."""
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Admin access required.",
    )


def test_label_review_proposals_rejects_non_admin():
    """GET /proposals with a non-admin user should return 403."""
    client = TestClient(app)

    app.dependency_overrides[get_admin_user] = _fake_non_admin
    try:
        resp = client.get("/settings/label-review/proposals?status=pending")
        assert resp.status_code == 403
        assert "Admin access required" in resp.json()["detail"]
    finally:
        app.dependency_overrides.clear()


def test_label_review_review_rejects_non_admin():
    """POST /review with a non-admin user should return 403."""
    client = TestClient(app)

    app.dependency_overrides[get_admin_user] = _fake_non_admin
    try:
        resp = client.post(
            "/settings/label-review/review",
            json={"proposal_id": 1, "action": "approve"},
        )
        assert resp.status_code == 403
        assert "Admin access required" in resp.json()["detail"]
    finally:
        app.dependency_overrides.clear()
