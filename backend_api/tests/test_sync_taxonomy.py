from __future__ import annotations

import io
import json
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest
import yaml

from scripts import sync_taxonomy


def _identity(sub_category: str, aspect_key: str, version: str = "v1.0") -> tuple[str, str, str]:
    return (sub_category, aspect_key, version)


def _aspect(
    key: str,
    label_zh: str,
    *,
    total: int = 10,
    positive_count: int = 7,
    negative_count: int = 2,
    neutral_count: int = 1,
    negative_rate: str = "20.0%",
    boundary_note: str | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "key": key,
        "label_zh": label_zh,
        "total": total,
        "positive_count": positive_count,
        "negative_count": negative_count,
        "neutral_count": neutral_count,
        "negative_rate": negative_rate,
        "top_phrases": [{"phrase": "easy", "count": 2}],
        "sample_reviews": ["R-1"],
    }
    if boundary_note is not None:
        payload["boundary_note"] = boundary_note
    return payload


def _write_taxonomy(
    root: Path,
    category: str,
    filename: str,
    sub_category: str,
    aspects: list[dict[str, Any]],
    *,
    version: str | None = None,
) -> Path:
    category_dir = root / category
    category_dir.mkdir(parents=True, exist_ok=True)
    payload: dict[str, Any] = {
        "sub_category": sub_category,
        "aspect_count": len(aspects),
        "aspects": aspects,
    }
    if version is not None:
        payload["version"] = version
    path = category_dir / filename
    path.write_text(yaml.safe_dump(payload, allow_unicode=True, sort_keys=False), encoding="utf-8")
    return path


def _db_row(
    sub_category: str,
    aspect_key: str,
    *,
    label_zh: str = "旧标签",
    total_count: int = 10,
    positive_count: int = 7,
    negative_count: int = 2,
    neutral_count: int = 1,
    negative_rate: Decimal = Decimal("20.00"),
    boundary_note: str | None = None,
    top_phrases: list[dict[str, Any]] | None = None,
    sample_review_ids: list[str] | None = None,
    version: str = "v1.0",
) -> dict[str, Any]:
    return {
        "sub_category": sub_category,
        "aspect_key": aspect_key,
        "label_zh": label_zh,
        "boundary_note": boundary_note,
        "total_count": total_count,
        "positive_count": positive_count,
        "negative_count": negative_count,
        "neutral_count": neutral_count,
        "negative_rate": negative_rate,
        "top_phrases": top_phrases if top_phrases is not None else [{"phrase": "easy", "count": 2}],
        "sample_review_ids": sample_review_ids if sample_review_ids is not None else ["R-1"],
        "taxonomy_version": version,
    }


class FakeCursor:
    def __init__(self, conn: FakeConnection) -> None:
        self.conn = conn
        self._results: list[dict[str, Any]] = []

    def __enter__(self) -> FakeCursor:
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        return None

    def execute(self, sql: str, params: Any = None) -> None:
        self.conn.executed.append(sql)
        normalized = " ".join(sql.strip().upper().split())
        if normalized.startswith("SELECT"):
            versions = set(params[0]) if params else {"v1.0"}
            self._results = [
                dict(row)
                for row in self.conn.rows.values()
                if row.get("taxonomy_version") in versions
            ]
            return
        if normalized.startswith("INSERT"):
            key = _identity(params["sub_category"], params["aspect_key"], params["taxonomy_version"])
            self.conn.rows[key] = {
                "sub_category": params["sub_category"],
                "aspect_key": params["aspect_key"],
                "label_zh": params["label_zh"],
                "boundary_note": params["boundary_note"],
                "total_count": params["total_count"],
                "positive_count": params["positive_count"],
                "negative_count": params["negative_count"],
                "neutral_count": params["neutral_count"],
                "negative_rate": params["negative_rate"],
                "top_phrases": json.loads(params["top_phrases"]),
                "sample_review_ids": json.loads(params["sample_review_ids"]),
                "taxonomy_version": params["taxonomy_version"],
            }
            self.conn.mutations.append(("upsert", key))
            return
        if normalized.startswith("DELETE"):
            key = _identity(params["sub_category"], params["aspect_key"], params["taxonomy_version"])
            self.conn.rows.pop(key, None)
            self.conn.mutations.append(("delete", key))
            return
        raise AssertionError(f"unexpected SQL: {sql}")

    def fetchall(self) -> list[dict[str, Any]]:
        return self._results


class FakeConnection:
    def __init__(self, rows: list[dict[str, Any]] | None = None) -> None:
        self.rows = {
            _identity(row["sub_category"], row["aspect_key"], row["taxonomy_version"]): dict(row)
            for row in (rows or [])
        }
        self.executed: list[str] = []
        self.mutations: list[tuple[str, tuple[str, str, str]]] = []
        self.commit_count = 0
        self.rollback_count = 0

    def cursor(self, **_kwargs: Any) -> FakeCursor:
        return FakeCursor(self)

    def commit(self) -> None:
        self.commit_count += 1

    def rollback(self) -> None:
        self.rollback_count += 1


def _run_sync(
    root: Path,
    conn: FakeConnection,
    *,
    category: str | None = None,
    dry_run: bool = False,
    allow_delete: bool = False,
    category_mapping: dict[str, str] | None = None,
    cache_calls: list[str] | None = None,
) -> sync_taxonomy.TaxonomySyncResult:
    output = io.StringIO()
    return sync_taxonomy.sync_taxonomy(
        conn=conn,
        taxonomy_root=root,
        category=category,
        dry_run=dry_run,
        allow_delete=allow_delete,
        category_mapping=category_mapping or {},
        cache_refresh=lambda: cache_calls.append("clear") if cache_calls is not None else None,
        stdout=output,
    )


def test_dry_run_reports_diff_without_writing_db(tmp_path: Path) -> None:
    _write_taxonomy(tmp_path, "home", "bed.yaml", "Bed", [_aspect("assembly", "组装")])
    conn = FakeConnection()
    cache_calls: list[str] = []

    result = _run_sync(
        tmp_path,
        conn,
        dry_run=True,
        category_mapping={"Bed": "home"},
        cache_calls=cache_calls,
    )

    assert len(result.diff.added) == 1
    assert conn.rows == {}
    assert conn.mutations == []
    assert conn.commit_count == 0
    assert cache_calls == []


def test_sync_adds_new_taxonomy_row_and_refreshes_cache(tmp_path: Path) -> None:
    _write_taxonomy(
        tmp_path,
        "home",
        "bed.yaml",
        "Bed",
        [_aspect("assembly", "组装", boundary_note="Only assembly comments.")],
    )
    conn = FakeConnection()
    cache_calls: list[str] = []

    result = _run_sync(
        tmp_path,
        conn,
        category_mapping={"Bed": "home"},
        cache_calls=cache_calls,
    )

    row = conn.rows[_identity("Bed", "assembly")]
    assert result.applied.added == 1
    assert row["label_zh"] == "组装"
    assert row["boundary_note"] == "Only assembly comments."
    assert conn.commit_count == 1
    assert cache_calls == ["clear"]
    assert result.applied.cache_refreshed is True


def test_sync_updates_modified_taxonomy_row(tmp_path: Path) -> None:
    _write_taxonomy(
        tmp_path,
        "home",
        "bed.yaml",
        "Bed",
        [_aspect("assembly", "组装新版", total=12, positive_count=6, negative_count=3, neutral_count=3)],
    )
    conn = FakeConnection([_db_row("Bed", "assembly", label_zh="组装旧版")])
    cache_calls: list[str] = []

    result = _run_sync(
        tmp_path,
        conn,
        category_mapping={"Bed": "home"},
        cache_calls=cache_calls,
    )

    assert len(result.diff.modified) == 1
    assert "label_zh" in result.diff.modified[0].changed_fields
    assert conn.rows[_identity("Bed", "assembly")]["label_zh"] == "组装新版"
    assert conn.rows[_identity("Bed", "assembly")]["total_count"] == 12
    assert result.applied.modified == 1
    assert cache_calls == ["clear"]


def test_missing_yaml_is_delete_candidate_but_not_deleted_by_default(tmp_path: Path) -> None:
    (tmp_path / "home").mkdir()
    conn = FakeConnection([_db_row("Removed Bed", "assembly")])
    cache_calls: list[str] = []

    result = _run_sync(
        tmp_path,
        conn,
        category="home",
        allow_delete=False,
        category_mapping={"Removed Bed": "home"},
        cache_calls=cache_calls,
    )

    assert len(result.diff.delete_candidates) == 1
    assert _identity("Removed Bed", "assembly") in conn.rows
    assert conn.mutations == []
    assert result.applied.deleted == 0
    assert cache_calls == []


def test_allow_delete_removes_delete_candidates(tmp_path: Path) -> None:
    (tmp_path / "home").mkdir()
    conn = FakeConnection([_db_row("Removed Bed", "assembly")])
    cache_calls: list[str] = []

    result = _run_sync(
        tmp_path,
        conn,
        category="home",
        allow_delete=True,
        category_mapping={"Removed Bed": "home"},
        cache_calls=cache_calls,
    )

    assert len(result.diff.delete_candidates) == 1
    assert _identity("Removed Bed", "assembly") not in conn.rows
    assert result.applied.deleted == 1
    assert cache_calls == ["clear"]


def test_category_filter_only_syncs_selected_category(tmp_path: Path) -> None:
    _write_taxonomy(tmp_path, "home", "bed.yaml", "Bed", [_aspect("assembly", "组装")])
    _write_taxonomy(tmp_path, "pet", "toy.yaml", "Dog Toy", [_aspect("durability", "耐用性新版")])
    pet_before = _db_row("Dog Toy", "durability", label_zh="耐用性旧版")
    conn = FakeConnection(
        [
            pet_before,
            _db_row("Removed Bed", "stale_aspect"),
        ]
    )

    result = _run_sync(
        tmp_path,
        conn,
        category="home",
        allow_delete=True,
        category_mapping={
            "Bed": "home",
            "Removed Bed": "home",
            "Dog Toy": "pet",
        },
    )

    assert [row.identity for row in result.diff.added] == [
        sync_taxonomy.TaxonomyIdentity("Bed", "assembly", "v1.0")
    ]
    assert [row.identity for row in result.diff.delete_candidates] == [
        sync_taxonomy.TaxonomyIdentity("Removed Bed", "stale_aspect", "v1.0")
    ]
    assert conn.rows[_identity("Dog Toy", "durability")]["label_zh"] == "耐用性旧版"
    assert _identity("Removed Bed", "stale_aspect") not in conn.rows


@pytest.mark.parametrize(
    "payload",
    [
        "sub_category: Broken\naspects: [\n",
        yaml.safe_dump(
            {
                "sub_category": "Broken",
                "aspect_count": 1,
                "aspects": [{"label_zh": "缺少 key"}],
            },
            allow_unicode=True,
            sort_keys=False,
        ),
        yaml.safe_dump(
            {
                "sub_category": "Broken",
                "aspect_count": 2,
                "aspects": [
                    _aspect("duplicate_key", "重复 1"),
                    _aspect("duplicate_key", "重复 2"),
                ],
            },
            allow_unicode=True,
            sort_keys=False,
        ),
    ],
)
def test_invalid_yaml_fails_closed_without_db_writes(tmp_path: Path, payload: str) -> None:
    category_dir = tmp_path / "home"
    category_dir.mkdir()
    (category_dir / "broken.yaml").write_text(payload, encoding="utf-8")
    conn = FakeConnection()
    cache_calls: list[str] = []

    with pytest.raises(sync_taxonomy.TaxonomyValidationError):
        _run_sync(
            tmp_path,
            conn,
            category_mapping={"Broken": "home"},
            cache_calls=cache_calls,
        )

    assert conn.executed == []
    assert conn.mutations == []
    assert conn.commit_count == 0
    assert cache_calls == []
