"""uploads route parent product and variant attribution regressions."""

from __future__ import annotations

from datetime import datetime

import pandas as pd
import psycopg2
import pytest
from fastapi.testclient import TestClient

from backend_api.app.deps import get_current_user
from backend_api.app.main import app
from backend_api.app.schemas.uploads import UploadJobPayload, UploadJobResponse


def test_file_upload_uses_product_name_as_parent_and_reads_asins_from_raw_data(monkeypatch):
    captured: dict[str, object] = {}

    parsed = pd.DataFrame(
        [
            {
                "content": "Great waders",
                "date": "2026-01-01",
                "rating": 5,
                "raw_data": '{"ASIN": "b0779pqhm5"}',
            },
            {
                "content": "Sizing runs large",
                "date": "2026-01-02",
                "rating": 3,
                "raw_data": '{"ASIN": "B07J4N9TM5"}',
            },
        ],
    )

    monkeypatch.setattr("backend_api.app.routes.uploads.parse_file", lambda *_args: parsed)
    monkeypatch.setattr("backend_api.app.routes.uploads.compute_batch_hash", lambda *_args: "batch-1")

    def fake_batch_upsert(user_id, platform, identifiers, parent_name, category=None):
        captured["variant_args"] = {
            "user_id": user_id,
            "platform": platform,
            "identifiers": identifiers,
            "parent_name": parent_name,
            "category": category,
        }
        return [
            {"child_asin": asin, "action": "new", "parent_name": parent_name}
            for asin in identifiers
        ]

    def fake_enqueue(user_id, payload):
        captured["user_id"] = user_id
        captured["payload"] = payload
        now = datetime.utcnow()
        return UploadJobResponse(
            job=UploadJobPayload(
                id=99,
                user_id=user_id,
                status="queued",
                source_filename=payload["source_filename"],
                product_id=payload["product_id"],
                version=payload["version"],
                workflow_purpose=payload["workflow_purpose"],
                product_ref_id=payload.get("product_ref_id"),
                variant_ref_id=payload.get("variant_ref_id"),
                total_rows=len(payload["comments"]),
                processed_rows=0,
                positive_count=0,
                negative_count=0,
                session_id=None,
                error_message=None,
                payload_json=payload,
                created_at=now,
                updated_at=now,
                completed_at=None,
            ),
            message="ok",
        )

    monkeypatch.setattr("backend_api.app.routes.uploads.batch_upsert_variants_for_upload", fake_batch_upsert)
    monkeypatch.setattr("backend_api.app.routes.uploads._enqueue_upload_job", fake_enqueue)
    app.dependency_overrides[get_current_user] = lambda: {"id": 7, "username": "alice"}

    try:
        client = TestClient(app)
        response = client.post(
            "/uploads",
            data={
                "product_id": "B0779PQHM5",
                "product_name": "TIDEWE-下水服-WD001",
                "platform": "Amazon",
                "category": "waders",
                "version": "V1",
                "workflow_purpose": "Daily analysis",
                "representative_asin": "B0779PQHM5",
            },
            files={
                "source_file": (
                    "reviews.xlsx",
                    b"placeholder",
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                ),
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = captured["payload"]
    assert payload["product_id"] == "TIDEWE-下水服-WD001"
    assert payload["product_name"] == "TIDEWE-下水服-WD001"
    assert [row["source_variant_asin"] for row in payload["comments"]] == [
        "B0779PQHM5",
        "B07J4N9TM5",
    ]
    assert captured["variant_args"] == {
        "user_id": 7,
        "platform": "Amazon",
        "identifiers": ["B0779PQHM5", "B07J4N9TM5"],
        "parent_name": "TIDEWE-下水服-WD001",
        "category": "waders",
    }


@pytest.mark.parametrize(
    "merge_error",
    [
        psycopg2.errors.UndefinedColumn("column product_variants.platform does not exist"),
        psycopg2.errors.UniqueViolation(
            'duplicate key value violates unique constraint "product_variants_user_id_variant_sku_key"'
        ),
    ],
)
def test_file_upload_skips_variant_merge_when_product_catalog_fails(monkeypatch, merge_error):
    captured: dict[str, object] = {}

    parsed = pd.DataFrame(
        [
            {
                "content": "Great waders",
                "date": "2026-01-01",
                "rating": 5,
                "raw_data": '{"Asin": "B0779PQHM5"}',
            },
        ],
    )

    monkeypatch.setattr("backend_api.app.routes.uploads.parse_file", lambda *_args: parsed)
    monkeypatch.setattr("backend_api.app.routes.uploads.compute_batch_hash", lambda *_args: "batch-1")

    def fake_batch_upsert(*_args, **_kwargs):
        raise merge_error

    def fake_enqueue(user_id, payload):
        captured["user_id"] = user_id
        captured["payload"] = payload
        now = datetime.utcnow()
        return UploadJobResponse(
            job=UploadJobPayload(
                id=100,
                user_id=user_id,
                status="queued",
                source_filename=payload["source_filename"],
                product_id=payload["product_id"],
                version=payload["version"],
                workflow_purpose=payload["workflow_purpose"],
                product_ref_id=payload.get("product_ref_id"),
                variant_ref_id=payload.get("variant_ref_id"),
                total_rows=len(payload["comments"]),
                processed_rows=0,
                positive_count=0,
                negative_count=0,
                session_id=None,
                error_message=None,
                payload_json=payload,
                created_at=now,
                updated_at=now,
                completed_at=None,
            ),
            message="ok",
        )

    monkeypatch.setattr("backend_api.app.routes.uploads.batch_upsert_variants_for_upload", fake_batch_upsert)
    monkeypatch.setattr("backend_api.app.routes.uploads._enqueue_upload_job", fake_enqueue)
    app.dependency_overrides[get_current_user] = lambda: {"id": 7, "username": "alice"}

    try:
        client = TestClient(app)
        response = client.post(
            "/uploads",
            data={
                "product_id": "B0779PQHM5",
                "product_name": "TIDEWE-下水服-WD001",
                "platform": "Amazon",
                "category": "waders",
                "version": "V1",
                "workflow_purpose": "Daily analysis",
                "representative_asin": "B0779PQHM5",
            },
            files={
                "source_file": (
                    "reviews.xlsx",
                    b"placeholder",
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                ),
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = captured["payload"]
    assert payload["product_id"] == "TIDEWE-下水服-WD001"
    assert payload["comments"][0]["source_variant_asin"] == "B0779PQHM5"
    assert "variant_merge" not in response.json()
