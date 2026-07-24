#!/usr/bin/env python
from __future__ import annotations

import argparse
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

import psycopg2
import psycopg2.extras
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parents[1]


def _preload_env_files() -> str | None:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--env-file", default=None)
    args, _unknown = parser.parse_known_args()
    load_dotenv(ROOT_DIR / ".env")
    load_dotenv(ROOT_DIR / "review_analyzer" / ".env", override=False)
    if args.env_file:
        load_dotenv(Path(args.env_file), override=True)
    return args.env_file


_PRELOADED_ENV_FILE = _preload_env_files()

from review_analyzer.database import get_connection


def _safe_execute(cur: Any, sql: str, params: tuple[Any, ...]) -> None:
    cur.execute("SAVEPOINT merge_optional")
    try:
        cur.execute(sql, params)
        cur.execute("RELEASE SAVEPOINT merge_optional")
    except (psycopg2.errors.UndefinedTable, psycopg2.errors.UndefinedColumn):
        cur.execute("ROLLBACK TO SAVEPOINT merge_optional")
        cur.execute("RELEASE SAVEPOINT merge_optional")


def _fetch_products(
    cur: Any,
    user_id: int | None,
    name: str | None,
) -> list[dict[str, Any]]:
    filters = ["NULLIF(BTRIM(COALESCE(NULLIF(p.name, ''), p.parent_product_id)), '') IS NOT NULL"]
    params: list[Any] = []
    if user_id is not None:
        filters.append("p.user_id = %s")
        params.append(user_id)
    if name:
        filters.append("LOWER(BTRIM(COALESCE(NULLIF(p.name, ''), p.parent_product_id))) = LOWER(BTRIM(%s))")
        params.append(name)

    cur.execute(
        f"""SELECT
               p.id,
               p.user_id,
               p.parent_product_id,
               p.name,
               COALESCE(NULLIF(BTRIM(p.name), ''), p.parent_product_id) AS display_name,
               p.platform,
               p.created_at,
               COALESCE(v.variant_count, 0) AS variant_count,
               COALESCE(s.session_count, 0) AS session_count,
               COALESCE(c.comment_count, 0) AS comment_count,
               CASE WHEN pl.product_id IS NULL THEN 0 ELSE 1 END AS listing_count
           FROM products p
           LEFT JOIN (
               SELECT user_id, product_id, COUNT(*) AS variant_count
               FROM product_variants
               GROUP BY user_id, product_id
           ) v ON v.user_id = p.user_id AND v.product_id = p.id
           LEFT JOIN (
               SELECT user_id, product_id, COUNT(*) AS session_count
               FROM sessions
               GROUP BY user_id, product_id
           ) s ON s.user_id = p.user_id AND s.product_id = p.parent_product_id
           LEFT JOIN (
               SELECT user_id, product_id, COUNT(*) AS comment_count
               FROM comments
               GROUP BY user_id, product_id
           ) c ON c.user_id = p.user_id AND c.product_id = p.parent_product_id
           LEFT JOIN product_listings pl ON pl.product_id = p.id
           WHERE {' AND '.join(filters)}
           ORDER BY p.user_id, LOWER(BTRIM(p.name)), p.id""",
        tuple(params),
    )
    return [dict(row) for row in cur.fetchall()]


def _group_duplicates(rows: list[dict[str, Any]]) -> list[list[dict[str, Any]]]:
    grouped: dict[tuple[int, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        key = (int(row["user_id"]), str(row["display_name"]).strip().casefold())
        grouped[key].append(row)
    return [items for items in grouped.values() if len(items) > 1]


def _keep_score(row: dict[str, Any]) -> tuple[int, int, int, int, datetime, int]:
    created_at = row.get("created_at")
    if not isinstance(created_at, datetime):
        created_at = datetime.min
    return (
        int(row.get("listing_count") or 0),
        int(row.get("variant_count") or 0),
        int(row.get("comment_count") or 0),
        int(row.get("session_count") or 0),
        created_at,
        int(row["id"]),
    )


def _update_variant_references(
    cur: Any,
    user_id: int,
    source_variant_id: int,
    target_variant_id: int,
) -> None:
    _safe_execute(
        cur,
        "UPDATE upload_jobs SET variant_ref_id = %s WHERE user_id = %s AND variant_ref_id = %s",
        (target_variant_id, user_id, source_variant_id),
    )
    _safe_execute(
        cur,
        "UPDATE sessions SET variant_ref_id = %s WHERE user_id = %s AND variant_ref_id = %s",
        (target_variant_id, user_id, source_variant_id),
    )
    _safe_execute(
        cur,
        "UPDATE action_items SET variant_id = %s WHERE user_id = %s AND variant_id = %s",
        (target_variant_id, user_id, source_variant_id),
    )
    _safe_execute(
        cur,
        "UPDATE review_trackers SET variant_id = %s WHERE user_id = %s AND variant_id = %s",
        (target_variant_id, user_id, source_variant_id),
    )
    _safe_execute(
        cur,
        "UPDATE product_versions SET variant_id = %s WHERE user_id = %s AND variant_id = %s",
        (target_variant_id, user_id, source_variant_id),
    )


def _merge_variants(
    cur: Any,
    user_id: int,
    source_product_id: int,
    target_product_id: int,
) -> None:
    cur.execute(
        """SELECT id, child_asin, variant_sku
           FROM product_variants
           WHERE user_id = %s AND product_id = %s""",
        (user_id, source_product_id),
    )
    for variant in cur.fetchall():
        source_variant_id = int(variant["id"])
        child_asin = str(variant.get("child_asin") or "").strip()
        variant_sku = str(variant.get("variant_sku") or "").strip()
        cur.execute(
            """SELECT id
               FROM product_variants
               WHERE user_id = %s
                 AND product_id = %s
                 AND id <> %s
                 AND (
                      (NULLIF(%s, '') IS NOT NULL AND child_asin = %s)
                   OR (NULLIF(%s, '') IS NOT NULL AND variant_sku = %s)
                 )
               LIMIT 1""",
            (
                user_id,
                target_product_id,
                source_variant_id,
                child_asin,
                child_asin,
                variant_sku,
                variant_sku,
            ),
        )
        existing = cur.fetchone()
        if existing:
            target_variant_id = int(existing["id"])
            _update_variant_references(cur, user_id, source_variant_id, target_variant_id)
            cur.execute(
                "DELETE FROM product_variants WHERE user_id = %s AND id = %s",
                (user_id, source_variant_id),
            )
        else:
            cur.execute(
                "UPDATE product_variants SET product_id = %s WHERE user_id = %s AND id = %s",
                (target_product_id, user_id, source_variant_id),
            )


def _merge_one(cur: Any, target: dict[str, Any], source: dict[str, Any]) -> None:
    user_id = int(target["user_id"])
    target_id = int(target["id"])
    source_id = int(source["id"])
    target_parent = str(target["parent_product_id"])
    source_parent = str(source["parent_product_id"])

    _merge_variants(cur, user_id, source_id, target_id)

    _safe_execute(
        cur,
        """DELETE FROM product_versions pv
           WHERE pv.user_id = %s AND pv.product_id = %s
             AND EXISTS (
                 SELECT 1 FROM product_versions target
                 WHERE target.user_id = pv.user_id
                   AND target.product_id = %s
                   AND target.version_name = pv.version_name
             )""",
        (user_id, source_id, target_id),
    )
    _safe_execute(
        cur,
        "UPDATE product_versions SET product_id = %s WHERE user_id = %s AND product_id = %s",
        (target_id, user_id, source_id),
    )

    _safe_execute(
        cur,
        "UPDATE sessions SET product_id = %s, product_ref_id = %s WHERE user_id = %s AND (product_id = %s OR product_ref_id = %s)",
        (target_parent, target_id, user_id, source_parent, source_id),
    )
    _safe_execute(
        cur,
        "UPDATE upload_jobs SET product_id = %s, product_ref_id = %s WHERE user_id = %s AND (product_id = %s OR product_ref_id = %s)",
        (target_parent, target_id, user_id, source_parent, source_id),
    )
    _safe_execute(
        cur,
        "UPDATE comments SET product_id = %s WHERE user_id = %s AND product_id = %s",
        (target_parent, user_id, source_parent),
    )

    _safe_execute(
        cur,
        "UPDATE action_items SET product_id = %s WHERE user_id = %s AND product_id = %s",
        (target_id, user_id, source_id),
    )
    _safe_execute(
        cur,
        "UPDATE action_items SET source_product_id = %s WHERE user_id = %s AND source_product_id = %s",
        (target_parent, user_id, source_parent),
    )
    _safe_execute(
        cur,
        "UPDATE review_trackers SET product_id = %s WHERE user_id = %s AND product_id = %s",
        (target_id, user_id, source_id),
    )
    _safe_execute(
        cur,
        "UPDATE push_snapshots SET product_id = %s WHERE user_id = %s AND product_id = %s",
        (target_id, user_id, source_id),
    )
    _safe_execute(
        cur,
        "UPDATE issue_escalation_state SET product_id = %s WHERE user_id = %s AND product_id = %s",
        (target_id, user_id, source_id),
    )
    _safe_execute(
        cur,
        "UPDATE asin_watchlist SET product_id = %s WHERE user_id = %s AND product_id = %s",
        (target_id, user_id, source_id),
    )

    _safe_execute(
        cur,
        """DELETE FROM ideal_profiles old
           WHERE old.user_id = %s AND old.product_id = %s
             AND EXISTS (
                 SELECT 1 FROM ideal_profiles target
                 WHERE target.user_id = old.user_id
                   AND target.product_id = %s
                   AND target.version = old.version
             )""",
        (user_id, source_parent, target_parent),
    )
    _safe_execute(
        cur,
        "UPDATE ideal_profiles SET product_id = %s WHERE user_id = %s AND product_id = %s",
        (target_parent, user_id, source_parent),
    )

    cur.execute("SELECT 1 FROM product_listings WHERE product_id = %s", (target_id,))
    target_has_listing = cur.fetchone() is not None
    cur.execute("SELECT 1 FROM product_listings WHERE product_id = %s", (source_id,))
    source_has_listing = cur.fetchone() is not None
    if source_has_listing and target_has_listing:
        cur.execute("DELETE FROM product_listings WHERE product_id = %s", (source_id,))
    elif source_has_listing:
        cur.execute("UPDATE product_listings SET product_id = %s WHERE product_id = %s", (target_id, source_id))

    cur.execute("DELETE FROM products WHERE user_id = %s AND id = %s", (user_id, source_id))


def main() -> int:
    parser = argparse.ArgumentParser(description="Merge duplicate product records sharing the same display name.")
    parser.add_argument("--env-file", default=_PRELOADED_ENV_FILE, help="Optional .env file to load with override.")
    parser.add_argument("--user-id", type=int, default=None, help="Limit merge scan to one user id.")
    parser.add_argument("--name", default=None, help="Limit merge scan to one exact products.name.")
    parser.add_argument("--show", action="store_true", help="Print matching product rows before duplicate detection.")
    parser.add_argument("--apply", action="store_true", help="Apply changes. Without this flag the script only previews.")
    args = parser.parse_args()

    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            rows = _fetch_products(cur, args.user_id, args.name)
            if args.show and rows:
                print("MATCHING PRODUCT ROWS:")
                for row in rows:
                    print(
                        "  user={user} id={id} parent={parent!r} display={display!r} "
                        "variants={variants} comments={comments} sessions={sessions} listing={listing}".format(
                            user=row["user_id"],
                            id=row["id"],
                            parent=row["parent_product_id"],
                            display=row["display_name"],
                            variants=row["variant_count"],
                            comments=row["comment_count"],
                            sessions=row["session_count"],
                            listing=row["listing_count"],
                        )
                    )
            groups = _group_duplicates(rows)
            if not groups:
                print("No duplicate product display-name groups found.")
                conn.rollback()
                return 0

            for group in groups:
                ordered = sorted(group, key=_keep_score, reverse=True)
                target = ordered[0]
                sources = ordered[1:]
                print(
                    "KEEP user={user} id={id} parent={parent!r} name={name!r} "
                    "variants={variants} comments={comments} listing={listing}".format(
                        user=target["user_id"],
                        id=target["id"],
                        parent=target["parent_product_id"],
                        name=target["name"],
                        variants=target["variant_count"],
                        comments=target["comment_count"],
                        listing=target["listing_count"],
                    )
                )
                for source in sources:
                    print(
                        "  MERGE id={id} parent={parent!r} variants={variants} comments={comments} listing={listing}".format(
                            id=source["id"],
                            parent=source["parent_product_id"],
                            variants=source["variant_count"],
                            comments=source["comment_count"],
                            listing=source["listing_count"],
                        )
                    )
                    if args.apply:
                        _merge_one(cur, target, source)

            if args.apply:
                conn.commit()
                print("Merge applied.")
            else:
                conn.rollback()
                print("Dry run only. Re-run with --apply to update the database.")
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
