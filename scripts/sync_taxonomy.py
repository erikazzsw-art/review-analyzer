#!/usr/bin/env python3
"""Safely sync taxonomy YAML assets into category_aspect_taxonomy.

The legacy importers only performed one-way upserts. This tool builds a full
YAML-to-DB diff first, keeps delete candidates blocked by default, and clears
the taxonomy loader cache after successful writes.

Use this for taxonomy DB sync instead of scripts/import_v4t1_assets.py
--taxonomy-only or data/taxonomy/import_taxonomy_to_db.py.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from pathlib import Path
from typing import Any, TextIO

import yaml

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DEFAULT_TAXONOMY_ROOT = ROOT / "data" / "taxonomy" / "v1.0"
DEFAULT_CATEGORY_MAPPING_PATH = ROOT / "backend_api" / "app" / "data" / "sub_category_categories.json"
DEFAULT_TAXONOMY_VERSION = "v1.0"
DECIMAL_2 = Decimal("0.01")
SYNC_FIELD_NAMES = (
    "label_zh",
    "boundary_note",
    "total_count",
    "positive_count",
    "negative_count",
    "neutral_count",
    "negative_rate",
    "top_phrases",
    "sample_review_ids",
)


class TaxonomySyncError(RuntimeError):
    """Base error for fail-closed taxonomy sync failures."""


class TaxonomyValidationError(TaxonomySyncError):
    """Raised when a YAML taxonomy asset is missing required valid fields."""


@dataclass(frozen=True, order=True)
class TaxonomyIdentity:
    sub_category: str
    aspect_key: str
    taxonomy_version: str

    def params(self) -> dict[str, str]:
        return {
            "sub_category": self.sub_category,
            "aspect_key": self.aspect_key,
            "taxonomy_version": self.taxonomy_version,
        }


@dataclass(frozen=True)
class TaxonomyRow:
    category_key: str
    sub_category: str
    aspect_key: str
    label_zh: str
    boundary_note: str | None
    total_count: int
    positive_count: int
    negative_count: int
    neutral_count: int
    negative_rate: Decimal
    top_phrases: Any
    sample_review_ids: Any
    taxonomy_version: str
    source_path: str = ""

    @property
    def identity(self) -> TaxonomyIdentity:
        return TaxonomyIdentity(
            sub_category=self.sub_category,
            aspect_key=self.aspect_key,
            taxonomy_version=self.taxonomy_version,
        )

    def comparable_values(self) -> dict[str, Any]:
        return {
            "label_zh": self.label_zh,
            "boundary_note": self.boundary_note or "",
            "total_count": self.total_count,
            "positive_count": self.positive_count,
            "negative_count": self.negative_count,
            "neutral_count": self.neutral_count,
            "negative_rate": _format_decimal(self.negative_rate),
            "top_phrases": _canonical_json_text(self.top_phrases),
            "sample_review_ids": _canonical_json_text(self.sample_review_ids),
        }

    def db_params(self) -> dict[str, Any]:
        return {
            "sub_category": self.sub_category,
            "aspect_key": self.aspect_key,
            "label_zh": self.label_zh,
            "boundary_note": self.boundary_note,
            "total_count": self.total_count,
            "positive_count": self.positive_count,
            "negative_count": self.negative_count,
            "neutral_count": self.neutral_count,
            "negative_rate": self.negative_rate,
            "top_phrases": json.dumps(self.top_phrases, ensure_ascii=False),
            "sample_review_ids": json.dumps(self.sample_review_ids, ensure_ascii=False),
            "taxonomy_version": self.taxonomy_version,
        }


@dataclass(frozen=True)
class TaxonomyChange:
    before: TaxonomyRow
    after: TaxonomyRow
    changed_fields: tuple[str, ...]


@dataclass(frozen=True)
class TaxonomyAssetBundle:
    rows: tuple[TaxonomyRow, ...]
    yaml_files: tuple[Path, ...]
    category: str | None
    taxonomy_root: Path

    @property
    def sub_categories(self) -> frozenset[str]:
        return frozenset(row.sub_category for row in self.rows)

    @property
    def versions(self) -> frozenset[str]:
        return frozenset(row.taxonomy_version for row in self.rows)


@dataclass(frozen=True)
class TaxonomyDiff:
    added: tuple[TaxonomyRow, ...]
    modified: tuple[TaxonomyChange, ...]
    delete_candidates: tuple[TaxonomyRow, ...]
    unchanged: tuple[TaxonomyRow, ...]
    asset_count: int
    db_count: int

    @property
    def upsert_count(self) -> int:
        return len(self.added) + len(self.modified)


@dataclass(frozen=True)
class AppliedStats:
    added: int = 0
    modified: int = 0
    deleted: int = 0
    cache_refreshed: bool = False

    @property
    def total_writes(self) -> int:
        return self.added + self.modified + self.deleted


@dataclass(frozen=True)
class TaxonomySyncResult:
    bundle: TaxonomyAssetBundle
    diff: TaxonomyDiff
    applied: AppliedStats
    dry_run: bool
    allow_delete: bool
    category: str | None


UPSERT_SQL = """
INSERT INTO category_aspect_taxonomy
    (sub_category, aspect_key, label_zh, boundary_note,
     total_count, positive_count, negative_count, neutral_count, negative_rate,
     top_phrases, sample_review_ids, taxonomy_version, updated_at)
VALUES
    (%(sub_category)s, %(aspect_key)s, %(label_zh)s, %(boundary_note)s,
     %(total_count)s, %(positive_count)s, %(negative_count)s, %(neutral_count)s, %(negative_rate)s,
     %(top_phrases)s::jsonb, %(sample_review_ids)s::jsonb, %(taxonomy_version)s, NOW())
ON CONFLICT (sub_category, aspect_key, taxonomy_version)
DO UPDATE SET
    label_zh = EXCLUDED.label_zh,
    boundary_note = EXCLUDED.boundary_note,
    total_count = EXCLUDED.total_count,
    positive_count = EXCLUDED.positive_count,
    negative_count = EXCLUDED.negative_count,
    neutral_count = EXCLUDED.neutral_count,
    negative_rate = EXCLUDED.negative_rate,
    top_phrases = EXCLUDED.top_phrases,
    sample_review_ids = EXCLUDED.sample_review_ids,
    updated_at = NOW()
"""

DELETE_SQL = """
DELETE FROM category_aspect_taxonomy
WHERE sub_category = %(sub_category)s
  AND aspect_key = %(aspect_key)s
  AND taxonomy_version = %(taxonomy_version)s
"""


def _clean(value: Any) -> str:
    return str(value or "").strip()


def _display_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return str(path)


def _format_decimal(value: Decimal) -> str:
    return str(value.quantize(DECIMAL_2, rounding=ROUND_HALF_UP))


def _canonical_json_value(value: Any) -> Any:
    if value is None:
        return []
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return []
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return text
    if isinstance(value, tuple):
        return [_canonical_json_value(item) for item in value]
    if isinstance(value, list):
        return [_canonical_json_value(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _canonical_json_value(item) for key, item in value.items()}
    return value


def _canonical_json_text(value: Any) -> str:
    return json.dumps(
        _canonical_json_value(value),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def _parse_int(value: Any, *, field_name: str, path: Path, default: int = 0) -> int:
    if value is None or value == "":
        return default
    if isinstance(value, bool):
        raise TaxonomyValidationError(f"{_display_path(path)}: {field_name} must be an integer")
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise TaxonomyValidationError(f"{_display_path(path)}: {field_name} must be an integer") from exc
    if parsed < 0:
        raise TaxonomyValidationError(f"{_display_path(path)}: {field_name} cannot be negative")
    return parsed


def _parse_negative_rate(
    value: Any,
    *,
    total_count: int,
    negative_count: int,
    field_name: str,
    path: Path,
) -> Decimal:
    if value is None or value == "":
        parsed = Decimal("0") if total_count == 0 else (Decimal(negative_count) / Decimal(total_count) * Decimal("100"))
    else:
        text = str(value).strip()
        if text.endswith("%"):
            text = text[:-1].strip()
        try:
            parsed = Decimal(text)
        except (InvalidOperation, ValueError) as exc:
            raise TaxonomyValidationError(f"{_display_path(path)}: {field_name} must be a percent number") from exc
    if parsed < 0 or parsed > 100:
        raise TaxonomyValidationError(f"{_display_path(path)}: {field_name} must be between 0 and 100")
    return parsed.quantize(DECIMAL_2, rounding=ROUND_HALF_UP)


def _parse_json_array(value: Any, *, field_name: str, path: Path) -> list[Any]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise TaxonomyValidationError(f"{_display_path(path)}: {field_name} must be a list")
    try:
        json.dumps(value, ensure_ascii=False)
    except (TypeError, ValueError) as exc:
        raise TaxonomyValidationError(f"{_display_path(path)}: {field_name} must be JSON serializable") from exc
    return value


def discover_taxonomy_yaml_paths(
    taxonomy_root: Path = DEFAULT_TAXONOMY_ROOT,
    *,
    category: str | None = None,
) -> tuple[Path, ...]:
    taxonomy_root = taxonomy_root.resolve()
    if not taxonomy_root.exists():
        raise TaxonomyValidationError(f"taxonomy root does not exist: {taxonomy_root}")
    if not taxonomy_root.is_dir():
        raise TaxonomyValidationError(f"taxonomy root is not a directory: {taxonomy_root}")
    if category:
        category_dir = taxonomy_root / category
        if not category_dir.exists():
            raise TaxonomyValidationError(f"category taxonomy directory does not exist: {_display_path(category_dir)}")

    paths: list[Path] = []
    for path in taxonomy_root.rglob("*.yaml"):
        relative = path.relative_to(taxonomy_root)
        if any(part.startswith("backup-") or part == "seeds" for part in relative.parts):
            continue
        if category and (not relative.parts or relative.parts[0] != category):
            continue
        paths.append(path)
    return tuple(sorted(paths))


def _category_from_path(path: Path, taxonomy_root: Path, data: Mapping[str, Any]) -> str:
    relative = path.relative_to(taxonomy_root)
    category_from_file = _clean(data.get("category_key") or data.get("category"))
    category_from_path = relative.parts[0] if len(relative.parts) > 1 else ""
    if category_from_file and category_from_path and category_from_file != category_from_path:
        raise TaxonomyValidationError(
            f"{_display_path(path)}: category field {category_from_file!r} "
            f"does not match path category {category_from_path!r}"
        )
    category_key = category_from_file or category_from_path
    if not category_key:
        raise TaxonomyValidationError(f"{_display_path(path)}: category is missing")
    return category_key


def _parse_taxonomy_yaml_file(path: Path, taxonomy_root: Path) -> tuple[TaxonomyRow, ...]:
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise TaxonomyValidationError(f"{_display_path(path)}: YAML parse failed: {exc}") from exc
    if not isinstance(raw, Mapping):
        raise TaxonomyValidationError(f"{_display_path(path)}: taxonomy YAML must be a mapping")

    category_key = _category_from_path(path, taxonomy_root, raw)
    sub_category = _clean(raw.get("sub_category"))
    if not sub_category:
        raise TaxonomyValidationError(f"{_display_path(path)}: sub_category is required")
    taxonomy_version = _clean(raw.get("taxonomy_version") or raw.get("version")) or DEFAULT_TAXONOMY_VERSION
    aspects = raw.get("aspects")
    if not isinstance(aspects, list):
        raise TaxonomyValidationError(f"{_display_path(path)}: aspects must be a list")
    if not aspects:
        raise TaxonomyValidationError(f"{_display_path(path)}: aspects cannot be empty")

    declared_count = raw.get("aspect_count")
    if declared_count is not None:
        parsed_count = _parse_int(declared_count, field_name="aspect_count", path=path)
        if parsed_count != len(aspects):
            raise TaxonomyValidationError(
                f"{_display_path(path)}: aspect_count={parsed_count} does not match aspects length={len(aspects)}"
            )

    rows: list[TaxonomyRow] = []
    seen_keys: set[str] = set()
    for index, aspect in enumerate(aspects, start=1):
        if not isinstance(aspect, Mapping):
            raise TaxonomyValidationError(f"{_display_path(path)}: aspect #{index} must be a mapping")
        aspect_key = _clean(aspect.get("key") or aspect.get("aspect_key"))
        if not aspect_key:
            raise TaxonomyValidationError(f"{_display_path(path)}: aspect #{index} key is required")
        if aspect_key in seen_keys:
            raise TaxonomyValidationError(f"{_display_path(path)}: duplicate aspect key {aspect_key!r}")
        seen_keys.add(aspect_key)

        label_zh = _clean(aspect.get("label_zh"))
        if not label_zh:
            raise TaxonomyValidationError(f"{_display_path(path)}: aspect {aspect_key!r} label_zh is required")

        total_count = _parse_int(
            aspect.get("total_count", aspect.get("total")),
            field_name=f"{aspect_key}.total",
            path=path,
        )
        positive_count = _parse_int(
            aspect.get("positive_count"),
            field_name=f"{aspect_key}.positive_count",
            path=path,
        )
        negative_count = _parse_int(
            aspect.get("negative_count"),
            field_name=f"{aspect_key}.negative_count",
            path=path,
        )
        neutral_count = _parse_int(
            aspect.get("neutral_count"),
            field_name=f"{aspect_key}.neutral_count",
            path=path,
        )
        negative_rate = _parse_negative_rate(
            aspect.get("negative_rate"),
            total_count=total_count,
            negative_count=negative_count,
            field_name=f"{aspect_key}.negative_rate",
            path=path,
        )
        top_phrases = _parse_json_array(
            aspect.get("top_phrases"),
            field_name=f"{aspect_key}.top_phrases",
            path=path,
        )
        sample_review_ids = _parse_json_array(
            aspect.get("sample_review_ids", aspect.get("sample_reviews")),
            field_name=f"{aspect_key}.sample_reviews",
            path=path,
        )
        boundary_note = _clean(aspect.get("boundary_note")) or None
        rows.append(
            TaxonomyRow(
                category_key=category_key,
                sub_category=sub_category,
                aspect_key=aspect_key,
                label_zh=label_zh,
                boundary_note=boundary_note,
                total_count=total_count,
                positive_count=positive_count,
                negative_count=negative_count,
                neutral_count=neutral_count,
                negative_rate=negative_rate,
                top_phrases=top_phrases,
                sample_review_ids=sample_review_ids,
                taxonomy_version=taxonomy_version,
                source_path=_display_path(path),
            )
        )
    return tuple(rows)


def load_taxonomy_assets(
    taxonomy_root: Path = DEFAULT_TAXONOMY_ROOT,
    *,
    category: str | None = None,
) -> TaxonomyAssetBundle:
    taxonomy_root = taxonomy_root.resolve()
    paths = discover_taxonomy_yaml_paths(taxonomy_root, category=category)
    rows: list[TaxonomyRow] = []
    identities: set[TaxonomyIdentity] = set()
    for path in paths:
        parsed_rows = _parse_taxonomy_yaml_file(path, taxonomy_root)
        for row in parsed_rows:
            if row.identity in identities:
                raise TaxonomyValidationError(
                    f"{row.source_path}: duplicate taxonomy identity "
                    f"{row.sub_category}/{row.aspect_key}/{row.taxonomy_version}"
                )
            identities.add(row.identity)
            rows.append(row)
    return TaxonomyAssetBundle(
        rows=tuple(sorted(rows, key=lambda row: row.identity)),
        yaml_files=paths,
        category=category,
        taxonomy_root=taxonomy_root,
    )


def _parse_db_row(raw: Mapping[str, Any]) -> TaxonomyRow:
    path = Path("<db>")
    total_count = _parse_int(raw.get("total_count"), field_name="db.total_count", path=path)
    negative_count = _parse_int(raw.get("negative_count"), field_name="db.negative_count", path=path)
    return TaxonomyRow(
        category_key="",
        sub_category=_clean(raw.get("sub_category")),
        aspect_key=_clean(raw.get("aspect_key")),
        label_zh=_clean(raw.get("label_zh")),
        boundary_note=_clean(raw.get("boundary_note")) or None,
        total_count=total_count,
        positive_count=_parse_int(raw.get("positive_count"), field_name="db.positive_count", path=path),
        negative_count=negative_count,
        neutral_count=_parse_int(raw.get("neutral_count"), field_name="db.neutral_count", path=path),
        negative_rate=_parse_negative_rate(
            raw.get("negative_rate"),
            total_count=total_count,
            negative_count=negative_count,
            field_name="db.negative_rate",
            path=path,
        ),
        top_phrases=_canonical_json_value(raw.get("top_phrases")),
        sample_review_ids=_canonical_json_value(raw.get("sample_review_ids")),
        taxonomy_version=_clean(raw.get("taxonomy_version")) or DEFAULT_TAXONOMY_VERSION,
        source_path="category_aspect_taxonomy",
    )


def fetch_taxonomy_rows_from_db(conn: Any, *, taxonomy_versions: Sequence[str]) -> tuple[TaxonomyRow, ...]:
    try:
        import psycopg2.extras

        cursor_kwargs: dict[str, Any] = {"cursor_factory": psycopg2.extras.RealDictCursor}
    except Exception:
        cursor_kwargs = {}

    versions = tuple(taxonomy_versions) or (DEFAULT_TAXONOMY_VERSION,)
    with conn.cursor(**cursor_kwargs) as cur:
        cur.execute(
            """SELECT sub_category, aspect_key, label_zh, boundary_note,
                      total_count, positive_count, negative_count, neutral_count, negative_rate,
                      top_phrases, sample_review_ids, taxonomy_version
               FROM category_aspect_taxonomy
               WHERE taxonomy_version = ANY(%s)
               ORDER BY sub_category, aspect_key, taxonomy_version""",
            (list(versions),),
        )
        rows = cur.fetchall()
    return tuple(sorted((_parse_db_row(dict(row)) for row in rows), key=lambda row: row.identity))


def load_category_mapping(
    mapping_path: Path = DEFAULT_CATEGORY_MAPPING_PATH,
) -> dict[str, str]:
    if not mapping_path.exists():
        return {}
    try:
        raw = json.loads(mapping_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise TaxonomyValidationError(f"cannot load category mapping: {_display_path(mapping_path)}") from exc
    mapping = raw.get("sub_category_to_category")
    if not isinstance(mapping, Mapping):
        return {}
    return {_clean(sub_category): _clean(category) for sub_category, category in mapping.items() if _clean(sub_category)}


def _scope_db_rows(
    db_rows: Sequence[TaxonomyRow],
    *,
    category: str | None,
    yaml_sub_categories: frozenset[str],
    category_mapping: Mapping[str, str],
) -> tuple[TaxonomyRow, ...]:
    if not category:
        return tuple(db_rows)
    scoped_sub_categories = {
        sub_category
        for sub_category, mapped_category in category_mapping.items()
        if mapped_category == category
    } | set(yaml_sub_categories)
    return tuple(row for row in db_rows if row.sub_category in scoped_sub_categories)


def build_taxonomy_diff(
    yaml_rows: Sequence[TaxonomyRow],
    db_rows: Sequence[TaxonomyRow],
) -> TaxonomyDiff:
    yaml_by_id = {row.identity: row for row in yaml_rows}
    db_by_id = {row.identity: row for row in db_rows}
    if len(yaml_by_id) != len(yaml_rows):
        raise TaxonomyValidationError("duplicate taxonomy identity in YAML rows")
    if len(db_by_id) != len(db_rows):
        raise TaxonomySyncError("duplicate taxonomy identity returned by DB")

    added = tuple(yaml_by_id[key] for key in sorted(yaml_by_id.keys() - db_by_id.keys()))
    delete_candidates = tuple(db_by_id[key] for key in sorted(db_by_id.keys() - yaml_by_id.keys()))

    modified: list[TaxonomyChange] = []
    unchanged: list[TaxonomyRow] = []
    for key in sorted(yaml_by_id.keys() & db_by_id.keys()):
        yaml_row = yaml_by_id[key]
        db_row = db_by_id[key]
        yaml_values = yaml_row.comparable_values()
        db_values = db_row.comparable_values()
        changed_fields = tuple(field for field in SYNC_FIELD_NAMES if yaml_values[field] != db_values[field])
        if changed_fields:
            modified.append(TaxonomyChange(before=db_row, after=yaml_row, changed_fields=changed_fields))
        else:
            unchanged.append(yaml_row)

    return TaxonomyDiff(
        added=added,
        modified=tuple(modified),
        delete_candidates=delete_candidates,
        unchanged=tuple(unchanged),
        asset_count=len(yaml_rows),
        db_count=len(db_rows),
    )


def apply_taxonomy_diff_to_db(
    conn: Any,
    diff: TaxonomyDiff,
    *,
    allow_delete: bool,
) -> AppliedStats:
    with conn.cursor() as cur:
        for row in diff.added:
            cur.execute(UPSERT_SQL, row.db_params())
        for change in diff.modified:
            cur.execute(UPSERT_SQL, change.after.db_params())

        deleted = 0
        if allow_delete and diff.delete_candidates:
            for row in diff.delete_candidates:
                cur.execute(DELETE_SQL, row.identity.params())
            deleted = len(diff.delete_candidates)

    return AppliedStats(
        added=len(diff.added),
        modified=len(diff.modified),
        deleted=deleted,
    )


def refresh_taxonomy_cache() -> None:
    from backend_api.app.services import taxonomy_loader

    taxonomy_loader.clear_cache()


def _print_row_preview(title: str, rows: Sequence[TaxonomyRow], *, stdout: TextIO, limit: int) -> None:
    if not rows:
        return
    print(f"{title}:", file=stdout)
    for row in rows[:limit]:
        print(
            f"  - {row.sub_category}/{row.aspect_key}/{row.taxonomy_version}"
            f" label_zh={row.label_zh!r}",
            file=stdout,
        )
    if len(rows) > limit:
        print(f"  ... {len(rows) - limit} more", file=stdout)


def print_taxonomy_diff_summary(
    bundle: TaxonomyAssetBundle,
    diff: TaxonomyDiff,
    *,
    dry_run: bool,
    allow_delete: bool,
    stdout: TextIO = sys.stdout,
    preview_limit: int = 10,
) -> None:
    mode = "dry-run" if dry_run else "write"
    print("=" * 80, file=stdout)
    print("Taxonomy sync summary", file=stdout)
    print("=" * 80, file=stdout)
    print(f"mode={mode}", file=stdout)
    print(f"taxonomy_root={bundle.taxonomy_root}", file=stdout)
    print(f"category={bundle.category or '*'}", file=stdout)
    print(f"yaml_files={len(bundle.yaml_files)} yaml_rows={diff.asset_count} db_rows_in_scope={diff.db_count}", file=stdout)
    print(
        "diff: "
        f"added={len(diff.added)} "
        f"modified={len(diff.modified)} "
        f"delete_candidates={len(diff.delete_candidates)} "
        f"unchanged={len(diff.unchanged)}",
        file=stdout,
    )
    planned_deletes = len(diff.delete_candidates) if allow_delete else 0
    print(f"planned_writes: upserts={diff.upsert_count} deletes={planned_deletes}", file=stdout)
    if dry_run:
        print("DRY-RUN: no DB writes will be made.", file=stdout)
    elif diff.delete_candidates and not allow_delete:
        print("Delete candidates are blocked. Pass --allow-delete to delete them.", file=stdout)
    elif diff.delete_candidates and allow_delete:
        print("Delete execution enabled by --allow-delete.", file=stdout)

    _print_row_preview("added", diff.added, stdout=stdout, limit=preview_limit)
    if diff.modified:
        print("modified:", file=stdout)
        for change in diff.modified[:preview_limit]:
            print(
                f"  - {change.after.sub_category}/{change.after.aspect_key}/{change.after.taxonomy_version} "
                f"fields={','.join(change.changed_fields)}",
                file=stdout,
            )
        if len(diff.modified) > preview_limit:
            print(f"  ... {len(diff.modified) - preview_limit} more", file=stdout)
    _print_row_preview("delete_candidates", diff.delete_candidates, stdout=stdout, limit=preview_limit)


def sync_taxonomy_bundle(
    bundle: TaxonomyAssetBundle,
    *,
    conn: Any,
    dry_run: bool,
    allow_delete: bool,
    category_mapping: Mapping[str, str] | None = None,
    cache_refresh: Callable[[], None] = refresh_taxonomy_cache,
    stdout: TextIO = sys.stdout,
    preview_limit: int = 10,
) -> TaxonomySyncResult:
    mapping = category_mapping if category_mapping is not None else load_category_mapping()
    versions = tuple(sorted(bundle.versions)) or (DEFAULT_TAXONOMY_VERSION,)
    db_rows = fetch_taxonomy_rows_from_db(conn, taxonomy_versions=versions)
    scoped_db_rows = _scope_db_rows(
        db_rows,
        category=bundle.category,
        yaml_sub_categories=bundle.sub_categories,
        category_mapping=mapping,
    )
    diff = build_taxonomy_diff(bundle.rows, scoped_db_rows)
    print_taxonomy_diff_summary(
        bundle,
        diff,
        dry_run=dry_run,
        allow_delete=allow_delete,
        stdout=stdout,
        preview_limit=preview_limit,
    )

    if dry_run:
        _rollback_quietly(conn)
        return TaxonomySyncResult(
            bundle=bundle,
            diff=diff,
            applied=AppliedStats(),
            dry_run=True,
            allow_delete=allow_delete,
            category=bundle.category,
        )

    try:
        applied = apply_taxonomy_diff_to_db(conn, diff, allow_delete=allow_delete)
        if applied.total_writes:
            conn.commit()
            cache_refresh()
            applied = AppliedStats(
                added=applied.added,
                modified=applied.modified,
                deleted=applied.deleted,
                cache_refreshed=True,
            )
        else:
            _rollback_quietly(conn)
    except Exception:
        _rollback_quietly(conn)
        raise

    print(
        "Applied: "
        f"added={applied.added} modified={applied.modified} "
        f"deleted={applied.deleted} cache_refreshed={applied.cache_refreshed}",
        file=stdout,
    )
    return TaxonomySyncResult(
        bundle=bundle,
        diff=diff,
        applied=applied,
        dry_run=False,
        allow_delete=allow_delete,
        category=bundle.category,
    )


def sync_taxonomy(
    *,
    conn: Any,
    taxonomy_root: Path = DEFAULT_TAXONOMY_ROOT,
    category: str | None = None,
    dry_run: bool,
    allow_delete: bool,
    category_mapping: Mapping[str, str] | None = None,
    cache_refresh: Callable[[], None] = refresh_taxonomy_cache,
    stdout: TextIO = sys.stdout,
    preview_limit: int = 10,
) -> TaxonomySyncResult:
    bundle = load_taxonomy_assets(taxonomy_root, category=category)
    return sync_taxonomy_bundle(
        bundle,
        conn=conn,
        dry_run=dry_run,
        allow_delete=allow_delete,
        category_mapping=category_mapping,
        cache_refresh=cache_refresh,
        stdout=stdout,
        preview_limit=preview_limit,
    )


def _rollback_quietly(conn: Any) -> None:
    rollback = getattr(conn, "rollback", None)
    if callable(rollback):
        try:
            rollback()
        except Exception:
            pass


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Safely sync data/taxonomy/v1.0/**/*.yaml into category_aspect_taxonomy."
    )
    parser.add_argument(
        "--taxonomy-root",
        type=Path,
        default=DEFAULT_TAXONOMY_ROOT,
        help="Taxonomy asset root. Defaults to data/taxonomy/v1.0.",
    )
    parser.add_argument("--category", help="Only sync one category directory, for example outdoor or pet.")
    parser.add_argument("--dry-run", action="store_true", help="Print the diff without writing DB changes.")
    parser.add_argument(
        "--allow-delete",
        action="store_true",
        help="Allow deleting DB taxonomy rows that no longer exist in YAML.",
    )
    parser.add_argument("--preview-limit", type=int, default=10, help="Max rows to preview per diff section.")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    conn = None
    try:
        bundle = load_taxonomy_assets(args.taxonomy_root, category=args.category)
        from review_analyzer.database import get_connection

        conn = get_connection()
        sync_taxonomy_bundle(
            bundle,
            conn=conn,
            dry_run=args.dry_run,
            allow_delete=args.allow_delete,
            preview_limit=args.preview_limit,
        )
    except TaxonomySyncError as exc:
        print(f"FAIL-CLOSED: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"FAILED: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    finally:
        if conn is not None:
            try:
                conn.close()
            except Exception:
                pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
