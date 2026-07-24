"""Product store deletion behavior tests."""

from __future__ import annotations

from datetime import datetime
from typing import Any

import psycopg2

from review_analyzer import product_store


class FakeCursor:
    def __init__(
        self,
        variant_ids: list[int] | None = None,
        variant_rows: list[tuple[int, str | None, str | None]] | None = None,
        session_ids: list[int] | None = None,
        action_item_ids: list[int] | None = None,
        parent_product_id: str | None = "Wader",
        product_deleted: bool = True,
        resolve_rows: list[dict[str, Any]] | None = None,
    ) -> None:
        self.variant_ids = variant_ids or []
        self.variant_rows = variant_rows or [
            (variant_id, f"B0VAR{variant_id}", f"SKU-{variant_id}")
            for variant_id in self.variant_ids
        ]
        self.session_ids = session_ids or []
        self.action_item_ids = action_item_ids or []
        self.parent_product_id = parent_product_id
        self.product_deleted = product_deleted
        self.resolve_rows = resolve_rows or []
        self.queries: list[tuple[str, tuple[Any, ...] | None]] = []
        self.last_sql = ""
        self.rowcount = 0

    def __enter__(self) -> FakeCursor:
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        return None

    def execute(self, sql: str, params: tuple[Any, ...] | None = None) -> None:
        self.last_sql = " ".join(sql.split())
        self.queries.append((self.last_sql, params))
        if self.last_sql.startswith("DELETE FROM products"):
            self.rowcount = 1 if self.product_deleted else 0
        elif self.last_sql.startswith("DELETE FROM product_variants"):
            self.rowcount = 1
        else:
            self.rowcount = 0

    def fetchall(self) -> list[tuple[Any, ...]]:
        if self.last_sql.startswith("SELECT p.id, p.parent_product_id"):
            return self.resolve_rows
        if self.last_sql.startswith("SELECT id, child_asin, variant_sku FROM product_variants"):
            return self.variant_rows
        if self.last_sql.startswith("SELECT id FROM sessions"):
            return [(session_id,) for session_id in self.session_ids]
        if self.last_sql.startswith("SELECT id FROM action_items"):
            return [(action_item_id,) for action_item_id in self.action_item_ids]
        return []

    def fetchone(self) -> tuple[Any, ...] | None:
        if self.last_sql.startswith("SELECT parent_product_id FROM products"):
            return (self.parent_product_id,) if self.parent_product_id is not None else None
        if self.last_sql.startswith("SELECT id FROM product_variants"):
            return (self.variant_ids[0],) if self.variant_ids else None
        return None


class FakeConnection:
    def __init__(self, cursor: FakeCursor) -> None:
        self._cursor = cursor
        self.committed = False
        self.closed = False

    def cursor(self, *args: Any, **kwargs: Any) -> FakeCursor:
        return self._cursor

    def commit(self) -> None:
        self.committed = True

    def close(self) -> None:
        self.closed = True


def test_delete_product_hard_deletes_user_review_data_without_touching_global_pool(monkeypatch):
    cursor = FakeCursor(
        variant_rows=[
            (31, "B0779PQHM5", "WADER-BLACK"),
            (32, "B0OTHERASIN", "WADER-GREEN"),
        ],
        session_ids=[101, 102],
        action_item_ids=[201],
    )
    conn = FakeConnection(cursor)
    monkeypatch.setattr(product_store, "get_connection", lambda: conn)

    deleted = product_store.delete_product(user_id=7, product_id=12)

    assert deleted is True
    assert conn.committed is True
    assert (
        "DELETE FROM comments WHERE user_id = %s AND session_id = ANY(%s)",
        (7, [101, 102]),
    ) in cursor.queries
    assert (
        "DELETE FROM sessions WHERE user_id = %s AND id = ANY(%s)",
        (7, [101, 102]),
    ) in cursor.queries
    assert (
        "DELETE FROM comments WHERE user_id = %s AND product_id = ANY(%s)",
        (7, ["Wader", "B0779PQHM5", "B0OTHERASIN", "WADER-BLACK", "WADER-GREEN"]),
    ) in cursor.queries
    assert (
        "DELETE FROM upload_jobs WHERE user_id = %s AND product_id = ANY(%s)",
        (7, ["Wader", "B0779PQHM5", "B0OTHERASIN", "WADER-BLACK", "WADER-GREEN"]),
    ) in cursor.queries
    assert (
        "DELETE FROM upload_jobs WHERE user_id = %s AND product_ref_id = %s",
        (7, 12),
    ) in cursor.queries
    assert (
        "DELETE FROM asin_watchlist WHERE user_id = %s AND asin = ANY(%s)",
        (7, ["Wader", "B0779PQHM5", "B0OTHERASIN", "WADER-BLACK", "WADER-GREEN"]),
    ) in cursor.queries
    assert (
        "DELETE FROM asin_watchlist WHERE user_id = %s AND product_id = %s",
        (7, 12),
    ) in cursor.queries
    assert (
        "DELETE FROM action_items WHERE user_id = %s AND id = ANY(%s)",
        (7, [201]),
    ) in cursor.queries
    assert not any("review_pool" in sql for sql, _params in cursor.queries)


def test_delete_variant_clears_version_and_session_refs(monkeypatch):
    cursor = FakeCursor(variant_ids=[31])
    conn = FakeConnection(cursor)
    monkeypatch.setattr(product_store, "get_connection", lambda: conn)

    deleted = product_store.delete_variant(user_id=7, product_id=12, variant_id=31)

    assert deleted is True
    assert conn.committed is True
    assert (
        "UPDATE product_versions SET variant_id = NULL WHERE user_id = %s AND variant_id = %s",
        (7, 31),
    ) in cursor.queries
    assert (
        "UPDATE sessions SET variant_ref_id = NULL WHERE user_id = %s AND variant_ref_id = %s",
        (7, 31),
    ) in cursor.queries


def test_upload_variant_reuses_legacy_variant_sku_record(monkeypatch):
    cursor = FakeCursor()
    conn = FakeConnection(cursor)
    monkeypatch.setattr(product_store, "get_connection", lambda: conn)
    monkeypatch.setattr(
        product_store,
        "_find_existing_variant_for_identifier",
        lambda user_id, child_asin, platform: {
            "id": 55,
            "product_id": 12,
            "platform": None,
            "child_asin": child_asin,
            "variant_sku": child_asin,
        },
    )
    monkeypatch.setattr(product_store, "_get_parent_product_name", lambda user_id, product_id: "TIDEWE")

    result = product_store.upsert_product_variant_for_upload(
        user_id=7,
        platform="Amazon",
        child_asin="B0779NTMYD",
        parent_name="TIDEWE",
        category="waders",
    )

    assert result["action"] == "existing"
    assert result["variant_id"] == 55
    assert (
        "UPDATE product_variants SET platform = COALESCE(platform, %s), child_asin = COALESCE(child_asin, %s), variant_sku = COALESCE(NULLIF(variant_sku, ''), %s) WHERE user_id = %s AND id = %s",
        ("Amazon", "B0779NTMYD", "B0779NTMYD", 7, 55),
    ) in cursor.queries
    assert conn.committed is True


def test_upload_variant_merges_to_existing_parent_for_legacy_variant_sku(monkeypatch):
    monkeypatch.setattr(
        product_store,
        "_find_existing_variant_for_identifier",
        lambda user_id, child_asin, platform: {
            "id": 56,
            "product_id": 13,
            "platform": None,
            "child_asin": child_asin,
            "variant_sku": child_asin,
        },
    )
    monkeypatch.setattr(product_store, "_get_parent_product_name", lambda user_id, product_id: "Existing Parent")

    result = product_store.upsert_product_variant_for_upload(
        user_id=7,
        platform="Amazon",
        child_asin="B0779NTMYD",
        parent_name="TIDEWE",
        category="waders",
    )

    assert result["action"] == "merged_to_other"
    assert result["parent_name"] == "Existing Parent"
    assert result["variant_id"] == 56


def test_resolve_upload_reference_prefers_variant_match_over_exact_name_parent(monkeypatch):
    cursor = FakeCursor(
        resolve_rows=[
            {
                "id": 21,
                "parent_product_id": "TIDEWE-下水服-WD001",
                "name": "TIDEWE-下水服-WD001",
                "platform": "Amazon",
                "created_at": datetime(2026, 1, 1),
                "variant_count": 0,
                "variant_match_count": 0,
                "variant_id": None,
            },
            {
                "id": 12,
                "parent_product_id": "B0PLUGIN01",
                "name": "TIDEWE-下水服-WD001",
                "platform": "amazon",
                "created_at": datetime(2026, 1, 2),
                "variant_count": 28,
                "variant_match_count": 1,
                "variant_id": 55,
            },
        ],
    )
    conn = FakeConnection(cursor)
    monkeypatch.setattr(product_store, "get_connection", lambda: conn)

    result = product_store.resolve_product_reference_for_upload(
        user_id=7,
        parent_name="TIDEWE-下水服-WD001",
        platform="Amazon",
        identifiers=["B0779PQHM5"],
    )

    assert result == {
        "id": 12,
        "parent_product_id": "B0PLUGIN01",
        "name": "TIDEWE-下水服-WD001",
        "platform": "amazon",
        "variant_id": 55,
    }


class PluginUploadCursor:
    def __init__(
        self,
        *,
        resolved_product_id: int | None = None,
        parent_asin_product_id: int | None = None,
        inserted_product_id: int = 31,
        existing_variant_id: int | None = None,
        fail_variant_insert: bool = False,
    ) -> None:
        self.resolved_product_id = resolved_product_id
        self.parent_asin_product_id = parent_asin_product_id
        self.inserted_product_id = inserted_product_id
        self.existing_variant_id = existing_variant_id
        self.fail_variant_insert = fail_variant_insert
        self.queries: list[tuple[str, tuple[Any, ...] | None]] = []
        self._next_fetchone: tuple[Any, ...] | None = None

    def __enter__(self) -> PluginUploadCursor:
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        return None

    def execute(self, sql: str, params: tuple[Any, ...] | None = None) -> None:
        normalized = " ".join(sql.split())
        self.queries.append((normalized, params))
        self._next_fetchone = None

        if normalized == "SELECT id FROM products WHERE user_id = %s AND id = %s":
            if self.resolved_product_id is not None and params == (7, self.resolved_product_id):
                self._next_fetchone = (self.resolved_product_id,)
        elif normalized == "SELECT id FROM products WHERE user_id = %s AND parent_product_id = %s":
            if self.parent_asin_product_id is not None:
                self._next_fetchone = (self.parent_asin_product_id,)
        elif normalized.startswith("INSERT INTO products"):
            self._next_fetchone = (self.inserted_product_id,)
        elif normalized.startswith("SELECT id FROM product_variants"):
            if self.existing_variant_id is not None:
                self._next_fetchone = (self.existing_variant_id,)
        elif normalized.startswith("INSERT INTO product_variants") and self.fail_variant_insert:
            raise psycopg2.errors.UniqueViolation()

    def fetchone(self) -> tuple[Any, ...] | None:
        return self._next_fetchone


class PluginUploadConnection:
    def __init__(self, cursor: PluginUploadCursor) -> None:
        self._cursor = cursor
        self.committed = False
        self.closed = False
        self.rollback_count = 0

    def cursor(self, *args: Any, **kwargs: Any) -> PluginUploadCursor:
        return self._cursor

    def commit(self) -> None:
        self.committed = True

    def rollback(self) -> None:
        self.rollback_count += 1

    def close(self) -> None:
        self.closed = True


def test_plugin_upload_listing_completes_existing_product_by_name(monkeypatch):
    captured: dict[str, Any] = {}

    def fake_resolve_product_reference_for_upload(
        user_id: int,
        parent_name: str,
        platform: str | None = None,
        identifiers: list[str] | None = None,
    ) -> dict[str, Any]:
        captured["user_id"] = user_id
        captured["parent_name"] = parent_name
        captured["platform"] = platform
        captured["identifiers"] = identifiers
        return {
            "id": 12,
            "parent_product_id": "FISHINGSIR-下水服-XSY01",
            "name": "FISHINGSIR-下水服-XSY01",
            "platform": "Amazon",
            "variant_id": 55,
        }

    cursor = PluginUploadCursor(resolved_product_id=12, existing_variant_id=55)
    conn = PluginUploadConnection(cursor)
    monkeypatch.setattr(product_store, "resolve_product_reference_for_upload", fake_resolve_product_reference_for_upload)
    monkeypatch.setattr(product_store, "get_connection", lambda: conn)

    result = product_store.plugin_upload_listing(
        user_id=7,
        parent_asin="B07VFCWCNC",
        name="FISHINGSIR-下水服-XSY01",
        platform="amazon",
        marketplace="us",
        listing={
            "title": "Waders for Women",
            "brand": "FISHINGSIR",
            "rating": 4.4,
            "ratings_total": 200,
        },
        variants=[{"asin": "B07VFCWCNC", "color": "Camo"}],
    )

    assert result == {
        "product_id": 12,
        "variant_count": 1,
        "listing_updated": True,
        "message": "产品信息已更新",
    }
    assert captured["identifiers"] == ["B07VFCWCNC"]
    assert not any(params and 200 in params for _sql, params in cursor.queries)
    assert not any(sql.startswith("INSERT INTO products") for sql, _params in cursor.queries)
    assert any(
        sql.startswith("UPDATE products SET name = %s")
        and params == ("FISHINGSIR-下水服-XSY01", "amazon", 7, 12)
        for sql, params in cursor.queries
    )
    assert any(
        sql.startswith("UPDATE product_variants SET product_id = %s")
        and params is not None
        and params[0] == 12
        and params[-1] == 55
        for sql, params in cursor.queries
    )
    assert conn.committed is True
    assert conn.rollback_count == 0


def test_plugin_upload_listing_variant_conflict_does_not_rollback_product(monkeypatch):
    cursor = PluginUploadCursor(inserted_product_id=31, fail_variant_insert=True)
    conn = PluginUploadConnection(cursor)
    monkeypatch.setattr(product_store, "resolve_product_reference_for_upload", lambda **_kwargs: None)
    monkeypatch.setattr(product_store, "get_connection", lambda: conn)

    result = product_store.plugin_upload_listing(
        user_id=7,
        parent_asin="B07VFCWCNC",
        name="FISHINGSIR-下水服-XSY01",
        platform="amazon",
        marketplace="us",
        listing={"title": "Waders for Women"},
        variants=[{"asin": "B07VFCWCNC"}],
    )

    assert result == {
        "product_id": 31,
        "variant_count": 0,
        "listing_updated": True,
        "message": "产品已创建并上传成功",
    }
    assert any(sql.startswith("INSERT INTO products") for sql, _params in cursor.queries)
    assert ("ROLLBACK TO SAVEPOINT _plugin_variant_upsert", None) in cursor.queries
    assert conn.committed is True
    assert conn.rollback_count == 0
