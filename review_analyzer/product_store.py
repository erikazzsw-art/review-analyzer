from __future__ import annotations

from collections import Counter
from datetime import datetime
from typing import Any

import psycopg2
import psycopg2.extras

from review_analyzer.database import get_connection, get_sessions

LIFECYCLE_OPTIONS = ["research", "launch", "growth", "mature", "decline"]
VARIANT_STATUS_OPTIONS = ["active", "paused", "clearance", "retired"]
TRACKER_ACTIVE_STATUSES = ("pending", "todo", "in_progress", "follow_up")


def create_product(user_id: int, data: dict[str, Any]) -> int:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO products
                   (user_id, parent_product_id, name, platform, category, lifecycle_stage,
                    current_version, core_selling_points, main_competitors, owner_role, production_cycle_days)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                   RETURNING id""",
                (
                    user_id,
                    data.get("parent_product_id"),
                    data.get("name"),
                    data.get("platform"),
                    data.get("category"),
                    data.get("lifecycle_stage", "growth"),
                    data.get("current_version", "V1"),
                    data.get("core_selling_points"),
                    data.get("main_competitors"),
                    data.get("owner_role"),
                    data.get("production_cycle_days"),
                ),
            )
            product_id = int(cur.fetchone()[0])
            conn.commit()
            return product_id
    finally:
        conn.close()



def get_products(user_id: int) -> list[dict[str, Any]]:
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                "SELECT * FROM products WHERE user_id = %s ORDER BY created_at DESC, id DESC",
                (user_id,),
            )
            return [dict(row) for row in cur.fetchall()]
    except psycopg2.errors.UndefinedTable:
        conn.rollback()
        return []
    finally:
        conn.close()



def get_product_by_id(user_id: int, product_id: int) -> dict[str, Any] | None:
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                "SELECT * FROM products WHERE user_id = %s AND id = %s",
                (user_id, product_id),
            )
            row = cur.fetchone()
            return dict(row) if row else None
    except psycopg2.errors.UndefinedTable:
        conn.rollback()
        return None
    finally:
        conn.close()



def get_product_by_parent_id(user_id: int, parent_product_id: str) -> dict[str, Any] | None:
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                "SELECT * FROM products WHERE user_id = %s AND parent_product_id = %s",
                (user_id, parent_product_id),
            )
            row = cur.fetchone()
            return dict(row) if row else None
    except psycopg2.errors.UndefinedTable:
        conn.rollback()
        return None
    finally:
        conn.close()


def create_variant(user_id: int, product_id: int, data: dict[str, Any]) -> int:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT 1 FROM products WHERE id = %s AND user_id = %s",
                (product_id, user_id),
            )
            if cur.fetchone() is None:
                raise ValueError("产品档案不存在，无法创建变体。")

            cur.execute(
                """INSERT INTO product_variants
                   (user_id, product_id, variant_sku, child_asin, color, size, style, material, status, launched_at)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                   RETURNING id""",
                (
                    user_id,
                    product_id,
                    data.get("variant_sku"),
                    data.get("child_asin"),
                    data.get("color"),
                    data.get("size"),
                    data.get("style"),
                    data.get("material"),
                    data.get("status", "active"),
                    data.get("launched_at"),
                ),
            )
            variant_id = int(cur.fetchone()[0])
            conn.commit()
            return variant_id
    finally:
        conn.close()



def get_variants(user_id: int, product_id: int) -> list[dict[str, Any]]:
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """SELECT *
                   FROM product_variants
                   WHERE user_id = %s AND product_id = %s
                   ORDER BY created_at DESC, id DESC""",
                (user_id, product_id),
            )
            return [dict(row) for row in cur.fetchall()]
    except psycopg2.errors.UndefinedTable:
        conn.rollback()
        return []
    finally:
        conn.close()



def get_product_versions(user_id: int, product_id: int) -> list[dict[str, Any]]:
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """SELECT *
                   FROM product_versions
                   WHERE user_id = %s AND product_id = %s
                   ORDER BY created_at DESC, id DESC""",
                (user_id, product_id),
            )
            return [dict(row) for row in cur.fetchall()]
    except psycopg2.errors.UndefinedTable:
        conn.rollback()
        return []
    finally:
        conn.close()


def create_product_version(user_id: int, product_id: int, data: dict[str, Any]) -> int:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT 1 FROM products WHERE id = %s AND user_id = %s",
                (product_id, user_id),
            )
            if cur.fetchone() is None:
                raise ValueError("产品档案不存在，无法创建版本。")

            cur.execute(
                """INSERT INTO product_versions
                   (user_id, product_id, variant_id, version_name, version_notes,
                    change_summary, launched_at, is_current)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                   RETURNING id""",
                (
                    user_id,
                    product_id,
                    data.get("variant_id"),
                    data.get("version_name"),
                    data.get("version_notes"),
                    data.get("change_summary"),
                    data.get("launched_at"),
                    data.get("is_current", False),
                ),
            )
            version_id = int(cur.fetchone()[0])
            conn.commit()
            return version_id
    finally:
        conn.close()


def _fetch_all_variants_grouped(user_id: int) -> dict[int, list[dict[str, Any]]]:
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """SELECT *
                   FROM product_variants
                   WHERE user_id = %s
                   ORDER BY created_at DESC, id DESC""",
                (user_id,),
            )
            grouped: dict[int, list[dict[str, Any]]] = {}
            for row in cur.fetchall():
                pid = int(row["product_id"])
                grouped.setdefault(pid, []).append(dict(row))
            return grouped
    except psycopg2.errors.UndefinedTable:
        conn.rollback()
        return {}
    finally:
        conn.close()


def _fetch_all_versions_grouped(user_id: int) -> dict[int, list[dict[str, Any]]]:
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """SELECT *
                   FROM product_versions
                   WHERE user_id = %s
                   ORDER BY created_at DESC, id DESC""",
                (user_id,),
            )
            grouped: dict[int, list[dict[str, Any]]] = {}
            for row in cur.fetchall():
                pid = int(row["product_id"])
                grouped.setdefault(pid, []).append(dict(row))
            return grouped
    except psycopg2.errors.UndefinedTable:
        conn.rollback()
        return {}
    finally:
        conn.close()


def _fetch_all_comments_deduped_grouped(user_id: int) -> dict[str, list[dict[str, Any]]]:
    sql = """
        SELECT * FROM (
            SELECT *,
                   ROW_NUMBER() OVER (PARTITION BY content_hash ORDER BY id DESC) AS rn
            FROM comments
            WHERE user_id = %s AND content_hash IS NOT NULL
        ) sub
        WHERE rn = 1
        ORDER BY id DESC
    """
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, (user_id,))
            grouped: dict[str, list[dict[str, Any]]] = {}
            for row in cur.fetchall():
                pid = str(row.get("product_id") or "")
                if not pid:
                    continue
                grouped.setdefault(pid, []).append(dict(row))
            return grouped
    finally:
        conn.close()


def _fetch_all_pending_review_counts(user_id: int) -> dict[int, int]:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT product_id, COUNT(*)
                   FROM review_trackers
                   WHERE user_id = %s AND result_status = ANY(%s)
                   GROUP BY product_id""",
                (user_id, list(TRACKER_ACTIVE_STATUSES)),
            )
            return {int(pid): int(cnt) for pid, cnt in cur.fetchall() if pid is not None}
    except psycopg2.errors.UndefinedTable:
        conn.rollback()
        return {}
    finally:
        conn.close()



def get_product_overview_rows(user_id: int) -> list[dict[str, Any]]:
    stored_products = get_products(user_id)
    sessions = get_sessions(user_id)
    session_map = _build_session_map(sessions)

    stored_by_parent = {
        str(product["parent_product_id"]): product
        for product in stored_products
        if product.get("parent_product_id")
    }

    all_parent_ids = list(dict.fromkeys([*stored_by_parent.keys(), *session_map.keys()]))

    variants_by_product = _fetch_all_variants_grouped(user_id)
    versions_by_product = _fetch_all_versions_grouped(user_id)
    comments_by_parent = _fetch_all_comments_deduped_grouped(user_id)
    pending_by_product = _fetch_all_pending_review_counts(user_id)

    rows: list[dict[str, Any]] = []

    for parent_id in all_parent_ids:
        product_row = stored_by_parent.get(parent_id)
        related_sessions = session_map.get(parent_id, [])
        latest_session = related_sessions[0] if related_sessions else None
        comments = comments_by_parent.get(parent_id, []) if parent_id else []
        product_pid = int(product_row["id"]) if product_row else None
        variants = variants_by_product.get(product_pid, []) if product_pid is not None else []
        versions = versions_by_product.get(product_pid, []) if product_pid is not None else []
        stats = _build_comment_stats(comments)

        current_version = (
            str(product_row.get("current_version"))
            if product_row and product_row.get("current_version")
            else str(latest_session.get("version"))
            if latest_session and latest_session.get("version")
            else "V1"
        )

        created_at = _pick_created_at(product_row, latest_session)
        rows.append(
            {
                "id": product_row.get("id") if product_row else None,
                "parent_product_id": parent_id,
                "name": product_row.get("name") if product_row else None,
                "platform": (
                    product_row.get("platform")
                    if product_row and product_row.get("platform")
                    else latest_session.get("platform")
                    if latest_session
                    else None
                ),
                "category": (
                    product_row.get("category")
                    if product_row and product_row.get("category")
                    else latest_session.get("category")
                    if latest_session
                    else None
                ),
                "lifecycle_stage": (
                    product_row.get("lifecycle_stage")
                    if product_row and product_row.get("lifecycle_stage")
                    else "growth"
                ),
                "current_version": current_version,
                "core_selling_points": product_row.get("core_selling_points") if product_row else None,
                "main_competitors": product_row.get("main_competitors") if product_row else None,
                "owner_role": product_row.get("owner_role") if product_row else None,
                "production_cycle_days": product_row.get("production_cycle_days") if product_row else None,
                "is_archived_from_sessions": product_row is None,
                "review_count": stats["review_count"],
                "positive_rate": stats["positive_rate"],
                "negative_rate": stats["negative_rate"],
                "top_issue": stats["top_issue"],
                "top_highlight": stats["top_highlight"],
                "variant_count": len(variants),
                "variants": variants,
                "versions": versions,
                "session_count": len(related_sessions),
                "pending_review_count": pending_by_product.get(product_pid, 0) if product_pid is not None else 0,
                "latest_session_label": _build_session_label(latest_session),
                "latest_updated_at": created_at,
            }
        )

    rows.sort(
        key=lambda row: (
            row["latest_updated_at"] or datetime.min,
            row["review_count"],
        ),
        reverse=True,
    )
    return rows


def _build_session_map(sessions: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    session_map: dict[str, list[dict[str, Any]]] = {}
    for session in sessions:
        product_id = str(session.get("product_id") or "").strip()
        if not product_id:
            continue
        session_map.setdefault(product_id, []).append(session)
    return session_map


def _build_comment_stats(comments: list[dict[str, Any]]) -> dict[str, Any]:
    review_count = len(comments)
    unrecognizable_count = sum(1 for comment in comments if comment.get("sentiment") == "unrecognizable")
    valid_count = review_count - unrecognizable_count
    positive_count = sum(1 for comment in comments if comment.get("sentiment") == "positive")
    negative_count = sum(1 for comment in comments if comment.get("sentiment") == "negative")
    top_issue = _get_top_tag(comments, "issue_tag")
    top_highlight = _get_top_tag(comments, "highlight_tag")
    return {
        "review_count": review_count,
        "positive_rate": round((positive_count / valid_count) * 100, 1) if valid_count > 0 else 0.0,
        "negative_rate": round((negative_count / valid_count) * 100, 1) if valid_count > 0 else 0.0,
        "top_issue": top_issue,
        "top_highlight": top_highlight,
    }


def _get_top_tag(comments: list[dict[str, Any]], field_name: str) -> str | None:
    counter: Counter[str] = Counter()
    for comment in comments:
        tags = str(comment.get(field_name) or "")
        seen_tags: set[str] = set()
        for tag in tags.split(","):
            cleaned = tag.strip()
            if cleaned and cleaned not in seen_tags:
                seen_tags.add(cleaned)
                counter[cleaned] += 1
    if not counter:
        return None
    return counter.most_common(1)[0][0]


def _pick_created_at(product_row: dict[str, Any] | None, latest_session: dict[str, Any] | None) -> datetime | None:
    if product_row and isinstance(product_row.get("created_at"), datetime):
        return product_row["created_at"]
    if latest_session and isinstance(latest_session.get("created_at"), datetime):
        return latest_session["created_at"]
    return None


def _build_session_label(latest_session: dict[str, Any] | None) -> str | None:
    if not latest_session:
        return None
    title = latest_session.get("custom_title") or latest_session.get("auto_title") or latest_session.get("version")
    if not title:
        return None
    return str(title)


def _get_pending_review_count(user_id: int, product_id: int | None) -> int:
    if product_id is None:
        return 0

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT COUNT(*)
                   FROM review_trackers
                   WHERE user_id = %s AND product_id = %s AND result_status = ANY(%s)""",
                (user_id, product_id, list(TRACKER_ACTIVE_STATUSES)),
            )
            row = cur.fetchone()
            return int(row[0] or 0) if row else 0
    except psycopg2.errors.UndefinedTable:
        conn.rollback()
        return 0
    finally:
        conn.close()
