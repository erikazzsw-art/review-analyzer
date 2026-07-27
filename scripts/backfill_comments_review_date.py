from __future__ import annotations

import argparse
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import psycopg2
import psycopg2.extras
from dotenv import load_dotenv

from review_analyzer.review_dates import normalize_comment_review_date


@dataclass
class BackfillStats:
    total_seen: int = 0
    already_normalized: int = 0
    blank_raw_date: int = 0
    parsed_pending: int = 0
    unparsed_pending: int = 0
    updated: int = 0
    unparsed_samples: list[dict[str, Any]] = field(default_factory=list)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Dry-run or backfill comments.review_date from raw comments.date."
    )
    parser.add_argument(
        "--database-url-env",
        default="DEV_DATABASE_URL",
        help="Environment variable containing the target DB URL. Defaults to DEV_DATABASE_URL.",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Write parsed review_date values. Without this flag the script only prints stats.",
    )
    parser.add_argument(
        "--allow-prod",
        action="store_true",
        help="Required when --database-url-env is DATABASE_URL or PROD_DATABASE_URL.",
    )
    parser.add_argument("--batch-size", type=int, default=500)
    parser.add_argument("--limit", type=int, default=0, help="Optional row limit for dev sampling.")
    return parser.parse_args()


def _database_url(env_name: str, allow_prod: bool) -> str:
    load_dotenv(Path(__file__).resolve().parents[1] / ".env")
    if env_name in {"DATABASE_URL", "PROD_DATABASE_URL"} and not allow_prod:
        raise SystemExit(
            f"{env_name} looks production-like; pass --allow-prod only after backup/window approval."
        )
    url = os.getenv(env_name, "").strip()
    if not url:
        raise SystemExit(f"{env_name} is not set.")
    return url


def _print_stats(stats: BackfillStats, *, apply: bool) -> None:
    mode = "apply" if apply else "dry_run"
    print(f"mode={mode}")
    print(f"total_seen={stats.total_seen}")
    print(f"already_normalized={stats.already_normalized}")
    print(f"blank_raw_date={stats.blank_raw_date}")
    print(f"parsed_pending={stats.parsed_pending}")
    print(f"unparsed_pending={stats.unparsed_pending}")
    print(f"updated={stats.updated}")
    if stats.unparsed_samples:
        print("unparsed_samples:")
        for sample in stats.unparsed_samples:
            print(f"  id={sample['id']} date={sample['date']!r}")


def _iter_comments(cur, *, limit: int):
    sql = """
        SELECT id, date, review_date
        FROM comments
        ORDER BY id ASC
    """
    params: tuple[Any, ...] = ()
    if limit > 0:
        sql += " LIMIT %s"
        params = (limit,)
    cur.execute(sql, params)
    yield from cur.fetchall()


def _flush_updates(cur, rows: list[tuple[int, str]]) -> int:
    if not rows:
        return 0
    psycopg2.extras.execute_values(
        cur,
        """
        UPDATE comments AS c
        SET review_date = v.review_date::date
        FROM (VALUES %s) AS v(id, review_date)
        WHERE c.id = v.id
          AND c.review_date IS NULL
        """,
        rows,
        page_size=500,
    )
    return len(rows)


def main() -> None:
    args = _parse_args()
    dsn = _database_url(args.database_url_env, args.allow_prod)
    stats = BackfillStats()
    pending_updates: list[tuple[int, str]] = []

    conn = psycopg2.connect(dsn, connect_timeout=10, sslmode="require")
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            for row in _iter_comments(cur, limit=args.limit):
                stats.total_seen += 1
                if row.get("review_date") is not None:
                    stats.already_normalized += 1
                    continue

                raw_date = row.get("date")
                if not str(raw_date or "").strip():
                    stats.blank_raw_date += 1
                    continue

                normalized = normalize_comment_review_date(raw_date)
                if normalized:
                    stats.parsed_pending += 1
                    if args.apply:
                        pending_updates.append((int(row["id"]), normalized))
                        if len(pending_updates) >= args.batch_size:
                            stats.updated += _flush_updates(cur, pending_updates)
                            pending_updates.clear()
                    continue

                stats.unparsed_pending += 1
                if len(stats.unparsed_samples) < 10:
                    stats.unparsed_samples.append({"id": row["id"], "date": raw_date})

            if args.apply and pending_updates:
                stats.updated += _flush_updates(cur, pending_updates)
                pending_updates.clear()

        if args.apply:
            conn.commit()
        else:
            conn.rollback()
    finally:
        conn.close()

    _print_stats(stats, apply=args.apply)


if __name__ == "__main__":
    main()
