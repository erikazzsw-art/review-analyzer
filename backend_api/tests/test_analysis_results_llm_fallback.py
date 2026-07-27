from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi.testclient import TestClient

from backend_api.app.deps import get_current_user
from backend_api.app.main import app
from backend_api.app.services.specific_issue import (
    CUSTOMER_LABEL_OCCURRENCE_RULESET_VERSION,
    CUSTOMER_LABEL_OCCURRENCE_SCHEMA_VERSION,
)
from review_analyzer import insight_engine
from review_analyzer.insight_engine import build_results_insights


def _occurrence(
    *,
    label_type: str,
    canonical: str,
    display: str,
    aspect_key: str,
    evidence: str,
    comment_id: int,
) -> dict[str, object]:
    return {
        "comment_id": comment_id,
        "type": label_type,
        "raw_label": display,
        "canonical_label_key": canonical,
        "display_label_en": display,
        "display_label_zh": display,
        "aspect_key": aspect_key,
        "evidence_span": evidence,
        "evidence_start": -1,
        "evidence_end": -1,
        "confidence": "high",
        "source": "human",
        "source_detail": "phase65_unit_fixture",
        "evidence_verified": True,
        "cluster_propagated": False,
        "schema_version": CUSTOMER_LABEL_OCCURRENCE_SCHEMA_VERSION,
        "ruleset_version": CUSTOMER_LABEL_OCCURRENCE_RULESET_VERSION,
        "display_allowed": True,
    }


def _route_comments() -> list[dict[str, Any]]:
    return [
        {
            "id": 1,
            "product_id": "Foxelli Waders - Session114 Phase6 Replay",
            "rating": 1,
            "date": "2026-07-01",
            "reviewer": "A",
            "source": "amazon",
            "sentiment": "negative",
            "content": "Both feet are leaking around where the boot connects to the wader.",
            "aspects_json": {
                "customer_label_occurrence_schema_version": CUSTOMER_LABEL_OCCURRENCE_SCHEMA_VERSION,
                "sub_category": "outdoor",
                "customer_label_occurrences": [
                    _occurrence(
                        label_type="issue",
                        canonical="water_leaks_through",
                        display="Water Leaks Through",
                        aspect_key="waterproof",
                        evidence="Both feet are leaking around where the boot connects to the wader",
                        comment_id=1,
                    )
                ],
            },
        },
        {
            "id": 2,
            "product_id": "Foxelli Waders - Session114 Phase6 Replay",
            "rating": 2,
            "date": "2026-07-02",
            "reviewer": "B",
            "source": "amazon",
            "sentiment": "negative",
            "content": "After one trip I had water leaking in through the seams.",
            "aspects_json": {
                "customer_label_occurrence_schema_version": CUSTOMER_LABEL_OCCURRENCE_SCHEMA_VERSION,
                "sub_category": "outdoor",
                "customer_label_occurrences": [
                    _occurrence(
                        label_type="issue",
                        canonical="water_leaks_through",
                        display="Water Leaks Through",
                        aspect_key="waterproof",
                        evidence="water leaking in",
                        comment_id=2,
                    )
                ],
            },
        },
        {
            "id": 3,
            "product_id": "Foxelli Waders - Session114 Phase6 Replay",
            "rating": 5,
            "date": "2026-07-03",
            "reviewer": "C",
            "source": "amazon",
            "sentiment": "positive",
            "content": "They kept me dry all morning in the creek.",
            "aspects_json": {
                "customer_label_occurrence_schema_version": CUSTOMER_LABEL_OCCURRENCE_SCHEMA_VERSION,
                "sub_category": "outdoor",
                "customer_label_occurrences": [
                    _occurrence(
                        label_type="highlight",
                        canonical="keeps_water_out",
                        display="Keeps Water Out",
                        aspect_key="waterproof",
                        evidence="kept me dry",
                        comment_id=3,
                    )
                ],
            },
        },
    ]


def _session(total_reviews: int = 3) -> dict[str, Any]:
    return {
        "id": 3,
        "user_id": 7,
        "product_id": "Foxelli Waders - Session114 Phase6 Replay",
        "version": "phase6-session114-replay-20260725",
        "auto_title": None,
        "custom_title": None,
        "date_range_start": None,
        "date_range_end": None,
        "total_reviews": total_reviews,
        "positive_count": 1,
        "negative_count": 2,
        "category": "outdoor",
        "prompt_version": None,
        "version_notes": None,
        "workflow_purpose": "",
        "product_ref_id": None,
        "variant_ref_id": None,
        "warnings_json": None,
        "created_at": datetime(2026, 7, 25, 5, 45, 21),
    }


def _enable_failing_results_ai(monkeypatch: Any) -> None:
    insight_engine._clear_results_ai_cache()
    monkeypatch.setenv("RESULTS_AI_ENHANCEMENT_ENABLED", "true")
    monkeypatch.setenv("RESULTS_AI_ENHANCEMENT_TIMEOUT_SECONDS", "0.5")
    monkeypatch.setenv("RESULTS_AI_PROVIDER_TIMEOUT_SECONDS", "0.5")
    monkeypatch.setenv("RESULTS_AI_MAX_MODEL_ATTEMPTS", "1")
    monkeypatch.setenv("RESULTS_AI_DISABLED_PROVIDERS", "deepseek")

    def failing_router_completion(**_kwargs: Any) -> tuple[Any, str]:
        raise RuntimeError("provider unavailable")

    monkeypatch.setattr(
        "backend_api.app.services.llm_router.router_completion",
        failing_router_completion,
    )


def _water_row(payload: dict[str, Any]) -> dict[str, Any]:
    return next(
        row
        for row in payload["modules"]["user_experience"]["negative"]
        if row.get("canonical_issue_key") == "water_leaks_through"
    )


def test_build_results_insights_keeps_top_rows_when_results_ai_fails(monkeypatch: Any) -> None:
    _enable_failing_results_ai(monkeypatch)

    insights = build_results_insights(
        7,
        _route_comments(),
        {"product_id": "Foxelli Waders - Session114 Phase6 Replay"},
        locale="en",
    )

    water = next(
        row for row in insights["user_experience"]["negative"] if row["canonical_issue_key"] == "water_leaks_through"
    )
    highlight = next(
        row for row in insights["user_experience"]["positive"] if row["canonical_highlight_key"] == "keeps_water_out"
    )

    assert water["specific_issue"] == "Water Leaks Through"
    assert water["mention_count"] == 2
    assert water["review_count"] == 2
    assert water["evidence_spans"] == [
        "Both feet are leaking around where the boot connects to the wader",
        "water leaking in",
    ]
    assert highlight["customer_highlight"] == "Keeps Water Out"
    assert highlight["mention_count"] == 1


def test_results_routes_return_200_when_results_ai_router_fails(monkeypatch: Any) -> None:
    from backend_api.app.routes import analysis

    comments = [{**comment, "embedding": [0.1, 0.2]} for comment in _route_comments()]
    session = _session(len(comments))

    _enable_failing_results_ai(monkeypatch)
    analysis._INSIGHTS_CACHE.clear()
    monkeypatch.setattr(analysis, "get_session_by_id", lambda user_id, session_id: session)
    monkeypatch.setattr(analysis, "get_comments", lambda user_id, **kwargs: comments)
    monkeypatch.setattr(analysis, "get_sessions", lambda user_id, product_id=None: [session])
    monkeypatch.setattr(analysis, "credit_consume", lambda *args, **kwargs: None)
    app.dependency_overrides[get_current_user] = lambda: {"id": 7, "username": "alice"}

    try:
        client = TestClient(app)
        session_response = client.get("/analysis/sessions/3/results")
        aggregate_response = client.get(
            "/analysis/results",
            params={
                "product_id": "Foxelli Waders - Session114 Phase6 Replay",
                "range": "all",
                "session_id": 3,
            },
        )
    finally:
        app.dependency_overrides.clear()
        analysis._INSIGHTS_CACHE.clear()

    assert session_response.status_code == 200
    assert aggregate_response.status_code == 200

    for response in (session_response, aggregate_response):
        body = response.json()
        assert all("embedding" not in comment for comment in body["comments"])
        water = _water_row(body)
        assert water["tag"] == "Water Leaks Through"
        assert water["mention_count"] == 2
        assert water["review_count"] == 2
        assert body["modules"]["user_experience"]["summary"]
