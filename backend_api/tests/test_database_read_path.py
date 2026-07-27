from __future__ import annotations

import psycopg2

from review_analyzer import database


class _FakeCursor:
    def __init__(
        self,
        queries: list[tuple[str, list[object] | tuple[object, ...]]],
        *,
        fetchall_rows: list[dict] | None = None,
        fetchone_row: dict | None = None,
        execute_error: Exception | None = None,
    ) -> None:
        self._queries = queries
        self._fetchall_rows = fetchall_rows or []
        self._fetchone_row = fetchone_row
        self._execute_error = execute_error

    def __enter__(self) -> _FakeCursor:
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        return None

    def execute(self, query: str, params: list[object] | tuple[object, ...]) -> None:
        self._queries.append((query, params))
        if self._execute_error:
            raise self._execute_error

    def fetchall(self) -> list[dict]:
        return self._fetchall_rows

    def fetchone(self) -> dict | None:
        return self._fetchone_row


class _FakeConnection:
    def __init__(
        self,
        queries: list[tuple[str, list[object] | tuple[object, ...]]],
        *,
        fetchall_rows: list[dict] | None = None,
        fetchone_row: dict | None = None,
        execute_error: Exception | None = None,
    ) -> None:
        self.closed = False
        self._queries = queries
        self._fetchall_rows = fetchall_rows
        self._fetchone_row = fetchone_row
        self._execute_error = execute_error

    def cursor(self, **_kwargs) -> _FakeCursor:
        return _FakeCursor(
            self._queries,
            fetchall_rows=self._fetchall_rows,
            fetchone_row=self._fetchone_row,
            execute_error=self._execute_error,
        )

    def close(self) -> None:
        self.closed = True


def _selected_columns(query: str) -> str:
    return query.split(" FROM comments", 1)[0]


def test_get_comments_uses_slim_columns_by_default(monkeypatch) -> None:
    queries: list[tuple[str, list[object] | tuple[object, ...]]] = []
    conn = _FakeConnection(queries, fetchall_rows=[{"id": 1, "content": "ok"}])
    monkeypatch.setattr(database, "get_connection", lambda: conn)

    rows = database.get_comments(7, session_id=3)

    assert rows == [{"id": 1, "content": "ok"}]
    query, params = queries[0]
    assert "SELECT *" not in query
    assert "embedding" not in _selected_columns(query)
    assert "jsonb_build_object" in _selected_columns(query)
    assert "customer_label_occurrences" in _selected_columns(query)
    assert "WHERE user_id = %s AND session_id = %s ORDER BY id DESC" in query
    assert params == [7, 3]
    assert conn.closed is True


def test_get_comments_can_explicitly_include_embedding(monkeypatch) -> None:
    queries: list[tuple[str, list[object] | tuple[object, ...]]] = []
    monkeypatch.setattr(
        database,
        "get_connection",
        lambda: _FakeConnection(queries, fetchall_rows=[{"id": 1, "embedding": "[1,2]"}]),
    )

    database.get_comments(7, product_id="Parent", include_embedding=True)

    query, params = queries[0]
    assert "embedding" in _selected_columns(query)
    assert "product_id = %s" in query
    assert params == [7, "Parent"]


def test_get_comments_can_disable_compact_aspects_json(monkeypatch) -> None:
    queries: list[tuple[str, list[object] | tuple[object, ...]]] = []
    monkeypatch.setattr(
        database,
        "get_connection",
        lambda: _FakeConnection(queries, fetchall_rows=[{"id": 1, "aspects_json": {}}]),
    )

    database.get_comments(7, session_id=3, compact_aspects_json=False)

    selected = _selected_columns(queries[0][0])
    assert "jsonb_build_object" not in selected
    assert "aspects_json" in selected


def test_get_comments_date_span_uses_sql_aggregation(monkeypatch) -> None:
    queries: list[tuple[str, list[object] | tuple[object, ...]]] = []
    monkeypatch.setattr(
        database,
        "get_connection",
        lambda: _FakeConnection(
            queries,
            fetchone_row={"min_date": "2025-04-27", "max_date": "2026-05-25"},
        ),
    )

    span = database.get_comments_date_span(4, session_id=5, source_variant_asin="B0ASIN")

    query, params = queries[0]
    assert span == ("2025-04-27", "2026-05-25")
    assert "MIN(SUBSTRING(date FROM 1 FOR 10))" in query
    assert "MAX(SUBSTRING(date FROM 1 FOR 10))" in query
    assert "date ~ '^[0-9]{4}'" in query
    assert "LOWER(source_variant_asin) = LOWER(%s)" in query
    assert params == [4, 5, "B0ASIN"]


def test_get_comments_retries_once_on_read_connection_error(monkeypatch) -> None:
    queries: list[tuple[str, list[object] | tuple[object, ...]]] = []
    conns = [
        _FakeConnection(queries, execute_error=psycopg2.InterfaceError("connection closed")),
        _FakeConnection(queries, fetchall_rows=[{"id": 2, "content": "after retry"}]),
    ]
    monkeypatch.setattr(database, "get_connection", lambda: conns.pop(0))

    rows = database.get_comments(7, session_id=3)

    assert rows == [{"id": 2, "content": "after retry"}]
    assert len(queries) == 2
