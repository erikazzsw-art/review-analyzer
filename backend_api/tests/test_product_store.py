"""Product store deletion behavior tests."""

from __future__ import annotations

from typing import Any

from review_analyzer import product_store


class FakeCursor:
    def __init__(
        self,
        variant_ids: list[int] | None = None,
        session_ids: list[int] | None = None,
        parent_product_id: str | None = "Wader",
        product_deleted: bool = True,
    ) -> None:
        self.variant_ids = variant_ids or []
        self.session_ids = session_ids or []
        self.parent_product_id = parent_product_id
        self.product_deleted = product_deleted
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

    def fetchall(self) -> list[tuple[int]]:
        if self.last_sql.startswith("SELECT id FROM product_variants"):
            return [(variant_id,) for variant_id in self.variant_ids]
        if self.last_sql.startswith("SELECT id FROM sessions"):
            return [(session_id,) for session_id in self.session_ids]
        return []

    def fetchone(self) -> tuple[int] | None:
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

    def cursor(self) -> FakeCursor:
        return self._cursor

    def commit(self) -> None:
        self.committed = True

    def close(self) -> None:
        self.closed = True


def test_delete_product_hard_deletes_user_review_data_without_touching_global_pool(monkeypatch):
    cursor = FakeCursor(variant_ids=[31, 32], session_ids=[101, 102])
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
        "DELETE FROM comments WHERE user_id = %s AND product_id = %s",
        (7, "Wader"),
    ) in cursor.queries
    assert (
        "DELETE FROM upload_jobs WHERE user_id = %s AND product_id = %s",
        (7, "Wader"),
    ) in cursor.queries
    assert (
        "DELETE FROM upload_jobs WHERE user_id = %s AND product_ref_id = %s",
        (7, 12),
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
