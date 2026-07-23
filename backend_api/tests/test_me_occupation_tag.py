"""职业标签资料端点回归测试."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backend_api.app.routes.me import update_me_occupation_tag
from backend_api.app.schemas.me import OccupationTagUpdateRequest


def test_update_me_occupation_tag_saves_selection(monkeypatch):
    updates: list[dict[str, object]] = []
    events: list[dict[str, object]] = []

    monkeypatch.setattr(
        "backend_api.app.routes.me.update_user_occupation_tag",
        lambda user_id, **kwargs: updates.append({"user_id": user_id, **kwargs}),
    )
    monkeypatch.setattr(
        "backend_api.app.routes.me.track_event",
        lambda user_id, event_name, properties=None: events.append(
            {"user_id": user_id, "event_name": event_name, "properties": properties or {}}
        ),
    )
    monkeypatch.setattr("backend_api.app.routes.me.get_user_plan", lambda user_id: "free")
    monkeypatch.setattr("backend_api.app.routes.me._check_admin", lambda user_id: False)
    monkeypatch.setattr(
        "backend_api.app.routes.me.get_user_by_id",
        lambda user_id: {
            "id": user_id,
            "username": "alice",
            "email": "alice@example.com",
            "plan": "free",
            "occupation_tag": "operations",
            "occupation_tag_status": "completed",
        },
    )

    result = update_me_occupation_tag(
        OccupationTagUpdateRequest(occupation_tag="operations", source="onboarding"),
        current_user={"id": 7, "username": "alice", "email": "alice@example.com"},
    )

    assert result.occupation_tag == "operations"
    assert result.occupation_tag_status == "completed"
    assert updates == [
        {"user_id": 7, "occupation_tag": "operations", "status": "completed"}
    ]
    assert events == [
        {
            "user_id": 7,
            "event_name": "occupation_tag_saved",
            "properties": {"source": "onboarding", "occupation_tag": "operations"},
        }
    ]


def test_update_me_occupation_tag_skips(monkeypatch):
    updates: list[dict[str, object]] = []
    events: list[dict[str, object]] = []

    monkeypatch.setattr(
        "backend_api.app.routes.me.update_user_occupation_tag",
        lambda user_id, **kwargs: updates.append({"user_id": user_id, **kwargs}),
    )
    monkeypatch.setattr(
        "backend_api.app.routes.me.track_event",
        lambda user_id, event_name, properties=None: events.append(
            {"user_id": user_id, "event_name": event_name, "properties": properties or {}}
        ),
    )
    monkeypatch.setattr("backend_api.app.routes.me.get_user_plan", lambda user_id: "free")
    monkeypatch.setattr("backend_api.app.routes.me._check_admin", lambda user_id: False)
    monkeypatch.setattr(
        "backend_api.app.routes.me.get_user_by_id",
        lambda user_id: {
            "id": user_id,
            "username": "alice",
            "email": "alice@example.com",
            "plan": "free",
            "occupation_tag": None,
            "occupation_tag_status": "skipped",
        },
    )

    result = update_me_occupation_tag(
        OccupationTagUpdateRequest(skip=True, source="onboarding"),
        current_user={"id": 7, "username": "alice", "email": "alice@example.com"},
    )

    assert result.occupation_tag is None
    assert result.occupation_tag_status == "skipped"
    assert updates == [
        {"user_id": 7, "occupation_tag": None, "status": "skipped"}
    ]
    assert events == [
        {
            "user_id": 7,
            "event_name": "occupation_tag_skipped",
            "properties": {"source": "onboarding"},
        }
    ]
