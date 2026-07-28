from __future__ import annotations

from datetime import date

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
        self.rowcount = -1

    def __enter__(self) -> _FakeCursor:
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        return None

    def execute(self, query: str, params: list[object] | tuple[object, ...] = ()) -> None:
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
        self.commits = 0
        self.rollbacks = 0

    def cursor(self, **_kwargs) -> _FakeCursor:
        return _FakeCursor(
            self._queries,
            fetchall_rows=self._fetchall_rows,
            fetchone_row=self._fetchone_row,
            execute_error=self._execute_error,
        )

    def close(self) -> None:
        self.closed = True

    def commit(self) -> None:
        self.commits += 1

    def rollback(self) -> None:
        self.rollbacks += 1


class _PoolCursor:
    def __init__(self, conn: _PoolConnection) -> None:
        self._conn = conn

    def __enter__(self) -> _PoolCursor:
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        return None

    def execute(self, query: str, params: tuple[object, ...] = ()) -> None:
        self._conn.queries.append((query, params))
        if self._conn.execute_error:
            raise self._conn.execute_error


class _PoolConnection:
    def __init__(self, *, execute_error: Exception | None = None) -> None:
        self.closed = False
        self.autocommit = False
        self.execute_error = execute_error
        self.queries: list[tuple[str, tuple[object, ...]]] = []
        self.rollbacks = 0
        self.set_session_calls: list[dict[str, object]] = []

    def cursor(self) -> _PoolCursor:
        return _PoolCursor(self)

    def rollback(self) -> None:
        self.rollbacks += 1

    def set_session(self, **kwargs: object) -> None:
        self.set_session_calls.append(kwargs)
        if "autocommit" in kwargs:
            self.autocommit = bool(kwargs["autocommit"])


class _Pool:
    def __init__(self, conns: list[_PoolConnection]) -> None:
        self.conns = conns
        self.put_calls: list[tuple[_PoolConnection, bool]] = []

    def getconn(self) -> _PoolConnection:
        return self.conns.pop(0)

    def putconn(self, conn: _PoolConnection, close: bool = False) -> None:
        self.put_calls.append((conn, close))


def _selected_columns(query: str) -> str:
    return query.split(" FROM comments", 1)[0]


def test_get_connection_forces_read_write_session(monkeypatch) -> None:
    raw_conn = _PoolConnection()
    pool = _Pool([raw_conn])
    monkeypatch.setattr(database, "_get_database_url", lambda: "postgresql://example")
    monkeypatch.setattr(database, "_get_connection_pool", lambda: pool)

    conn = database.get_connection()

    assert conn._conn is raw_conn
    assert raw_conn.rollbacks == 1
    assert raw_conn.set_session_calls == [{"readonly": False, "autocommit": True}]
    assert raw_conn.autocommit is False
    assert raw_conn.queries == [("SELECT 1", ())]


def test_get_connection_reprepares_replacement_connection(monkeypatch) -> None:
    bad_conn = _PoolConnection(execute_error=psycopg2.InterfaceError("closed"))
    good_conn = _PoolConnection()
    pool = _Pool([bad_conn, good_conn])
    monkeypatch.setattr(database, "_get_database_url", lambda: "postgresql://example")
    monkeypatch.setattr(database, "_get_connection_pool", lambda: pool)

    conn = database.get_connection()

    assert conn._conn is good_conn
    assert pool.put_calls == [(bad_conn, True)]
    assert bad_conn.set_session_calls == [{"readonly": False, "autocommit": True}]
    assert good_conn.set_session_calls == [{"readonly": False, "autocommit": True}]
    assert good_conn.autocommit is False
    assert good_conn.queries == [("SELECT 1", ())]


def test_comment_values_normalizes_review_date_from_date_iso() -> None:
    values = database._comment_values(
        7,
        {
            "product_id": "Parent",
            "content": "ok",
            "date": "Reviewed in the United States on July 1, 2026",
            "date_iso": "2026-07-02",
        },
    )

    review_date_index = database._COMMENT_INSERT_FIELDS.index("review_date")
    assert values[review_date_index] == date(2026, 7, 2)


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
    assert "review_date" in _selected_columns(query)
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


def test_get_comments_date_range_uses_normalized_review_date(monkeypatch) -> None:
    queries: list[tuple[str, list[object] | tuple[object, ...]]] = []
    monkeypatch.setattr(
        database,
        "get_connection",
        lambda: _FakeConnection(queries, fetchall_rows=[]),
    )

    database.get_comments(7, product_id="Parent", date_start="2025-01-01", date_end="2025-01-31")

    query, params = queries[0]
    assert "review_date >= %s::date" in query
    assert "review_date <= %s::date" in query
    assert " AND date >= %s" not in query
    assert " AND date <= %s" not in query
    assert params == [7, "Parent", "2025-01-01", "2025-01-31"]


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
    assert "MIN(review_date)::text" in query
    assert "MAX(review_date)::text" in query
    assert "review_date IS NOT NULL" in query
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


def test_update_comment_analysis_batch_uses_one_values_update(monkeypatch) -> None:
    queries: list[tuple[str, list[object] | tuple[object, ...]]] = []
    conn = _FakeConnection(queries)
    calls: list[tuple[str, list[tuple], int]] = []

    def fake_execute_values(cur, query, rows, page_size=100):
        rows = list(rows)
        calls.append((query, rows, page_size))
        cur.rowcount = len(rows)

    monkeypatch.setattr(database, "get_connection", lambda: conn)
    monkeypatch.setattr(database.psycopg2.extras, "execute_values", fake_execute_values)

    updated = database.update_comment_analysis_batch(
        7,
        [
            (
                11,
                {
                    "sentiment": "positive",
                    "category": "quality",
                    "aspects_json": {"aspects": [{"key": "fit"}]},
                    "analyzer_version": "v4_deep",
                },
            ),
            (
                12,
                {
                    "sentiment": "negative",
                    "content_sentiment": "negative",
                    "category": "risk",
                    "priority": "high",
                    "aspects_json": {"aspects": [{"key": "leak"}]},
                    "analyzer_version": "v4_deep",
                    "cache_hit_level": "L1",
                    "cache_source_id": 99,
                    "cache_hit_source": "user",
                },
            ),
        ],
    )

    assert updated == 2
    assert len(calls) == 1
    query, rows, page_size = calls[0]
    assert "UPDATE comments AS c" in query
    assert "cache_hit_level = v.cache_hit_level" in query
    assert "FROM (VALUES %s)" in query
    assert rows[0][0:2] == (7, 11)
    assert rows[1][0:2] == (7, 12)
    assert rows[1][-3:] == ("L1", 99, "user")
    assert page_size == 100
    assert conn.commits == 1
    assert conn.rollbacks == 0
    assert conn.closed is True


def test_update_comment_analysis_batch_falls_back_without_cache_columns(monkeypatch) -> None:
    queries: list[tuple[str, list[object] | tuple[object, ...]]] = []
    conn = _FakeConnection(queries)
    calls: list[tuple[str, list[tuple]]] = []

    def fake_execute_values(cur, query, rows, page_size=100):
        rows = list(rows)
        calls.append((query, rows))
        if len(calls) == 1:
            raise RuntimeError("cache_hit_source column missing")
        cur.rowcount = len(rows)

    monkeypatch.setattr(database, "get_connection", lambda: conn)
    monkeypatch.setattr(database.psycopg2.extras, "execute_values", fake_execute_values)

    updated = database.update_comment_analysis_batch(
        7,
        [
            (
                11,
                {
                    "sentiment": "positive",
                    "aspects_json": {"aspects": []},
                    "cache_hit_level": "L1",
                    "cache_source_id": 99,
                    "cache_hit_source": "global",
                },
            )
        ],
    )

    assert updated == 1
    assert len(calls) == 2
    assert "cache_hit_source = v.cache_hit_source" in calls[0][0]
    assert "cache_hit_source" not in calls[1][0]
    assert calls[1][1][0][0:2] == (7, 11)
    assert conn.rollbacks == 1
    assert conn.commits == 1
    assert conn.closed is True


def test_update_comment_embeddings_batch_uses_one_values_update(monkeypatch) -> None:
    queries: list[tuple[str, list[object] | tuple[object, ...]]] = []
    conn = _FakeConnection(queries)
    calls: list[tuple[str, list[tuple]]] = []

    def fake_execute_values(cur, query, rows, page_size=100):
        rows = list(rows)
        calls.append((query, rows))
        cur.rowcount = len(rows)

    monkeypatch.setattr(database, "get_connection", lambda: conn)
    monkeypatch.setattr(database.psycopg2.extras, "execute_values", fake_execute_values)

    updated = database.update_comment_embeddings_batch(
        7,
        [
            {"comment_id": 11, "embedding": [1, 2]},
            {"comment_id": 12, "embedding": [3.5, 4]},
        ],
    )

    assert updated == 2
    assert len(calls) == 1
    query, rows = calls[0]
    assert "SET embedding = v.embedding::vector" in query
    assert rows == [(7, 11, "[1.0,2.0]"), (7, 12, "[3.5,4.0]")]
    assert conn.commits == 1
    assert conn.closed is True


def test_content_hash_cache_excludes_error_fallback_aspects(monkeypatch) -> None:
    queries: list[tuple[str, list[object] | tuple[object, ...]]] = []
    conn = _FakeConnection(queries, fetchall_rows=[])
    monkeypatch.setattr(database, "get_connection", lambda: conn)

    database.get_analyzed_by_content_hash(
        7,
        ["hash-1"],
        include_global=True,
        analyzer_version="v4_deep",
    )

    combined = "\n".join(query for query, _params in queries)
    assert "NOT (aspects_json ? 'analysis_error')" in combined
    assert combined.count("NOT (aspects_json ? 'analysis_error')") == 2
    assert conn.closed is True


def test_update_comment_clusters_batch_uses_one_values_update(monkeypatch) -> None:
    queries: list[tuple[str, list[object] | tuple[object, ...]]] = []
    conn = _FakeConnection(queries)
    calls: list[tuple[str, list[tuple]]] = []

    def fake_execute_values(cur, query, rows, page_size=100):
        rows = list(rows)
        calls.append((query, rows))
        cur.rowcount = len(rows)

    monkeypatch.setattr(database, "get_connection", lambda: conn)
    monkeypatch.setattr(database.psycopg2.extras, "execute_values", fake_execute_values)

    updated = database.update_comment_clusters_batch(
        7,
        [
            {"comment_id": 11, "cluster_id": 2, "cluster_representative_id": 11},
            {"comment_id": 12, "cluster_id": -1, "cluster_representative_id": 12},
        ],
    )

    assert updated == 2
    assert len(calls) == 1
    query, rows = calls[0]
    assert "cluster_id = v.cluster_id" in query
    assert rows == [(7, 11, 2, 11), (7, 12, -1, 12)]
    assert conn.commits == 1
    assert conn.closed is True
