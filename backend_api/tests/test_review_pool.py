"""review_pool retention and dedupe tests."""

from __future__ import annotations

from typing import Any

from backend_api.app.services import review_pool


class FakeCursor:
    def __init__(self) -> None:
        self.queries: list[tuple[str, tuple[Any, ...] | None]] = []
        self._last_fetch: list[tuple[int]] = []
        self.rowcount = 0

    def __enter__(self) -> FakeCursor:
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        return None

    def execute(self, sql: str, params: tuple[Any, ...] | None = None) -> None:
        normalized = " ".join(sql.split())
        self.queries.append((normalized, params))
        if normalized.startswith("SELECT id FROM review_pool"):
            self._last_fetch = []
            self.rowcount = 0
            return
        if normalized.startswith("INSERT INTO review_pool "):
            self._last_fetch = []
            self.rowcount = 1
            return
        self._last_fetch = []
        self.rowcount = 0

    def fetchone(self) -> tuple[int] | None:
        return self._last_fetch[0] if self._last_fetch else None


class FakeConnection:
    def __init__(self, cursor: FakeCursor) -> None:
        self._cursor = cursor
        self.committed = False
        self.rolled_back = False
        self.closed = False

    def cursor(self) -> FakeCursor:
        return self._cursor

    def commit(self) -> None:
        self.committed = True

    def rollback(self) -> None:
        self.rolled_back = True

    def close(self) -> None:
        self.closed = True


def test_pool_write_keeps_recent_reviews_and_dedupes_by_review_id(monkeypatch):
    cursor = FakeCursor()
    conn = FakeConnection(cursor)
    monkeypatch.setattr(review_pool, "get_connection", lambda: conn)

    inserted = review_pool.pool_write(
        "amazon",
        "B0TESTASIN",
        "us",
        [
            {
                "review_id": "R1",
                "content": "Great product",
                "rating": 5,
                "date": "2999-01-02",
                "reviewer": "Alice",
            },
            {
                "review_id": "R1",
                "content": "Great product edited",
                "rating": 5,
                "date": "2999-01-03",
                "reviewer": "Alice",
            },
            {
                "review_id": "R2",
                "content": "Too old",
                "rating": 1,
                "date": "2000-01-02",
                "reviewer": "Bob",
            },
            {
                "review_id": "R3",
                "content": "No date",
                "rating": 4,
                "reviewer": "Cara",
            },
        ],
        scraper_source="unit-test",
    )

    assert inserted == 1
    assert conn.committed is True
    inserts = [
        params
        for sql, params in cursor.queries
        if sql.startswith("INSERT INTO review_pool ")
    ]
    assert len(inserts) == 1
    assert inserts[0][8] == "R1"
    assert inserts[0][5] == "2999-01-02"
