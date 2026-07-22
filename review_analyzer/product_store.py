from __future__ import annotations

from collections import Counter
from datetime import datetime
from typing import Any

import psycopg2
import psycopg2.extras

from review_analyzer.database import (
    get_comments,
    get_comments_deduped,
    get_connection,
    get_existing_hashes,
    get_product_stats_deduped,
    get_session_by_id,
    get_sessions,
)

LIFECYCLE_OPTIONS = ["research", "launch", "growth", "mature", "decline"]
VARIANT_STATUS_OPTIONS = ["active", "paused", "clearance", "retired"]
TRACKER_ACTIVE_STATUSES = ("pending", "todo", "in_progress", "follow_up")


class ProductParentNameConflictError(ValueError):
    """Raised when a parent product name is already used by this user."""


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

def update_product(user_id: int, product_id: int, data: dict[str, Any]) -> bool:
    conn = get_connection()
    try:
        allowed = {
            "parent_product_id", "name", "platform", "category", "lifecycle_stage",
            "current_version", "core_selling_points", "main_competitors",
            "owner_role", "production_cycle_days",
        }
        fields = {k: v for k, v in data.items() if k in allowed}
        if not fields:
            return False
        if "parent_product_id" in fields:
            fields["parent_product_id"] = str(fields["parent_product_id"]).strip()
            if not fields["parent_product_id"]:
                raise ValueError("父体名称不能为空。")
        set_clause = ", ".join(f"{k} = %s" for k in fields)
        with conn.cursor() as cur:
            cur.execute(
                "SELECT parent_product_id FROM products WHERE user_id = %s AND id = %s FOR UPDATE",
                (user_id, product_id),
            )
            row = cur.fetchone()
            if row is None:
                return False

            old_parent_product_id = str(row[0] or "").strip()
            new_parent_product_id = str(fields.get("parent_product_id") or old_parent_product_id).strip()
            parent_name_changed = (
                "parent_product_id" in fields
                and new_parent_product_id != old_parent_product_id
            )
            if parent_name_changed:
                _ensure_parent_name_available(cur, user_id, product_id, new_parent_product_id)

            values = list(fields.values()) + [user_id, product_id]
            cur.execute(
                f"UPDATE products SET {set_clause} WHERE user_id = %s AND id = %s",
                values,
            )
            updated = cur.rowcount > 0
            if updated and parent_name_changed:
                _update_parent_product_references(
                    cur,
                    user_id,
                    old_parent_product_id,
                    new_parent_product_id,
                )
        conn.commit()
        if updated and parent_name_changed:
            _clear_product_reference_caches()
        return updated
    except (ProductParentNameConflictError, ValueError):
        conn.rollback()
        raise
    except psycopg2.errors.UniqueViolation as exc:
        conn.rollback()
        raise ProductParentNameConflictError("父体名称已存在，请换一个名称。") from exc
    finally:
        conn.close()


def _ensure_parent_name_available(
    cur: Any,
    user_id: int,
    product_id: int,
    parent_product_id: str,
) -> None:
    cur.execute(
        """SELECT 1 FROM products
           WHERE user_id = %s AND parent_product_id = %s AND id <> %s
           LIMIT 1""",
        (user_id, parent_product_id, product_id),
    )
    if cur.fetchone():
        raise ProductParentNameConflictError("父体名称已存在，请换一个名称。")

    for table in ("sessions", "comments", "upload_jobs"):
        cur.execute(
            f"SELECT 1 FROM {table} WHERE user_id = %s AND product_id = %s LIMIT 1",
            (user_id, parent_product_id),
        )
        if cur.fetchone():
            raise ProductParentNameConflictError("父体名称已存在，请换一个名称。")


def _update_parent_product_references(
    cur: Any,
    user_id: int,
    old_parent_product_id: str,
    new_parent_product_id: str,
) -> None:
    for table in ("sessions", "comments", "upload_jobs"):
        cur.execute(
            f"UPDATE {table} SET product_id = %s WHERE user_id = %s AND product_id = %s",
            (new_parent_product_id, user_id, old_parent_product_id),
        )

    _safe_execute(
        cur,
        """UPDATE action_items
           SET source_product_id = %s
           WHERE user_id = %s AND source_product_id = %s""",
        (new_parent_product_id, user_id, old_parent_product_id),
    )
    _safe_execute(
        cur,
        """DELETE FROM ideal_profiles old
           WHERE old.user_id = %s AND old.product_id = %s
             AND EXISTS (
                 SELECT 1 FROM ideal_profiles existing
                 WHERE existing.user_id = old.user_id
                   AND existing.product_id = %s
                   AND existing.version = old.version
             )""",
        (user_id, old_parent_product_id, new_parent_product_id),
    )
    _safe_execute(
        cur,
        """UPDATE ideal_profiles
           SET product_id = %s
           WHERE user_id = %s AND product_id = %s""",
        (new_parent_product_id, user_id, old_parent_product_id),
    )


def _clear_product_reference_caches() -> None:
    for func in (
        get_comments,
        get_comments_deduped,
        get_existing_hashes,
        get_product_stats_deduped,
        get_session_by_id,
        get_sessions,
    ):
        clear = getattr(func, "clear", None)
        if callable(clear):
            clear()


def _safe_execute(cur: Any, sql: str, params: tuple) -> None:
    """Execute SQL, silently skipping if the target table doesn't exist."""
    cur.execute("SAVEPOINT _safe_exec")
    try:
        cur.execute(sql, params)
        cur.execute("RELEASE SAVEPOINT _safe_exec")
    except psycopg2.errors.UndefinedTable:
        cur.execute("ROLLBACK TO SAVEPOINT _safe_exec")


def delete_product(user_id: int, product_id: int) -> bool:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT parent_product_id FROM products WHERE user_id = %s AND id = %s FOR UPDATE",
                (user_id, product_id),
            )
            product = cur.fetchone()
            if product is None:
                return False
            parent_product_id = str(product[0] or "").strip()

            variant_ids_sql = (
                "SELECT id FROM product_variants WHERE user_id = %s AND product_id = %s"
            )
            cur.execute(variant_ids_sql, (user_id, product_id))
            variant_ids = [r[0] for r in cur.fetchall()]

            if variant_ids:
                cur.execute(
                    """SELECT id FROM sessions
                       WHERE user_id = %s
                         AND (
                             product_ref_id = %s
                             OR product_id = %s
                             OR variant_ref_id = ANY(%s)
                         )""",
                    (user_id, product_id, parent_product_id, variant_ids),
                )
            else:
                cur.execute(
                    """SELECT id FROM sessions
                       WHERE user_id = %s
                         AND (product_ref_id = %s OR product_id = %s)""",
                    (user_id, product_id, parent_product_id),
                )
            session_ids = [r[0] for r in cur.fetchall()]

            if session_ids:
                _safe_execute(
                    cur,
                    "UPDATE action_items SET session_id = NULL WHERE user_id = %s AND session_id = ANY(%s)",
                    (user_id, session_ids),
                )
                _safe_execute(
                    cur,
                    "DELETE FROM upload_jobs WHERE user_id = %s AND session_id = ANY(%s)",
                    (user_id, session_ids),
                )
                _safe_execute(
                    cur,
                    "DELETE FROM comments WHERE user_id = %s AND session_id = ANY(%s)",
                    (user_id, session_ids),
                )
                cur.execute(
                    "DELETE FROM sessions WHERE user_id = %s AND id = ANY(%s)",
                    (user_id, session_ids),
                )

            if parent_product_id:
                _safe_execute(
                    cur,
                    "DELETE FROM upload_jobs WHERE user_id = %s AND product_id = %s",
                    (user_id, parent_product_id),
                )
                cur.execute(
                    "DELETE FROM comments WHERE user_id = %s AND product_id = %s",
                    (user_id, parent_product_id),
                )

            _safe_execute(
                cur,
                "DELETE FROM upload_jobs WHERE user_id = %s AND product_ref_id = %s",
                (user_id, product_id),
            )

            if variant_ids:
                _safe_execute(
                    cur,
                    "DELETE FROM upload_jobs WHERE user_id = %s AND variant_ref_id = ANY(%s)",
                    (user_id, variant_ids),
                )
                _safe_execute(
                    cur,
                    "UPDATE action_items SET variant_id = NULL WHERE variant_id = ANY(%s)",
                    (variant_ids,),
                )
                _safe_execute(
                    cur,
                    "UPDATE review_trackers SET variant_id = NULL WHERE variant_id = ANY(%s)",
                    (variant_ids,),
                )
                _safe_execute(
                    cur,
                    "UPDATE upload_jobs SET variant_ref_id = NULL WHERE variant_ref_id = ANY(%s)",
                    (variant_ids,),
                )
                _safe_execute(
                    cur,
                    "UPDATE sessions SET variant_ref_id = NULL WHERE user_id = %s AND variant_ref_id = ANY(%s)",
                    (user_id, variant_ids),
                )

            _safe_execute(
                cur,
                "DELETE FROM product_versions WHERE user_id = %s AND product_id = %s",
                (user_id, product_id),
            )
            cur.execute(
                "DELETE FROM product_variants WHERE user_id = %s AND product_id = %s",
                (user_id, product_id),
            )
            _safe_execute(
                cur,
                "UPDATE action_items SET product_id = NULL WHERE product_id = %s",
                (product_id,),
            )
            _safe_execute(
                cur,
                "UPDATE review_trackers SET product_id = NULL WHERE product_id = %s",
                (product_id,),
            )
            _safe_execute(
                cur,
                "UPDATE push_snapshots SET product_id = NULL WHERE product_id = %s",
                (product_id,),
            )
            _safe_execute(
                cur,
                "UPDATE issue_escalation_state SET product_id = NULL WHERE product_id = %s",
                (product_id,),
            )
            _safe_execute(
                cur,
                "UPDATE upload_jobs SET product_ref_id = NULL WHERE product_ref_id = %s",
                (product_id,),
            )
            _safe_execute(
                cur,
                "UPDATE sessions SET product_ref_id = NULL WHERE user_id = %s AND product_ref_id = %s",
                (user_id, product_id),
            )
            cur.execute(
                "DELETE FROM products WHERE user_id = %s AND id = %s",
                (user_id, product_id),
            )
            deleted = cur.rowcount > 0
        conn.commit()
        if deleted:
            _clear_product_reference_caches()
        return deleted
    finally:
        conn.close()


def delete_variant(user_id: int, product_id: int, variant_id: int) -> bool:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id FROM product_variants WHERE id = %s AND user_id = %s AND product_id = %s",
                (variant_id, user_id, product_id),
            )
            if not cur.fetchone():
                return False

            cur.execute(
                "UPDATE action_items SET variant_id = NULL WHERE variant_id = %s",
                (variant_id,),
            )
            cur.execute(
                "UPDATE review_trackers SET variant_id = NULL WHERE variant_id = %s",
                (variant_id,),
            )
            cur.execute(
                "UPDATE upload_jobs SET variant_ref_id = NULL WHERE variant_ref_id = %s",
                (variant_id,),
            )
            _safe_execute(
                cur,
                "UPDATE product_versions SET variant_id = NULL WHERE user_id = %s AND variant_id = %s",
                (user_id, variant_id),
            )
            _safe_execute(
                cur,
                "UPDATE sessions SET variant_ref_id = NULL WHERE user_id = %s AND variant_ref_id = %s",
                (user_id, variant_id),
            )
            cur.execute(
                "DELETE FROM product_variants WHERE id = %s AND user_id = %s AND product_id = %s",
                (variant_id, user_id, product_id),
            )
            deleted = cur.rowcount > 0
        conn.commit()
        return deleted
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
                   (user_id, product_id, variant_sku, child_asin, platform,
                    color, size, style, material, status, launched_at)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                   RETURNING id""",
                (
                    user_id,
                    product_id,
                    data.get("variant_sku"),
                    data.get("child_asin"),
                    data.get("platform"),
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


def get_variants_with_review_counts(user_id: int, product_id: int) -> list[dict[str, Any]]:
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """SELECT
                       v.*,
                       COALESCE(vc.review_count, 0) AS review_count,
                       vc.latest_review_date
                   FROM product_variants v
                   LEFT JOIN products p
                     ON p.id = v.product_id AND p.user_id = v.user_id
                   LEFT JOIN (
                       SELECT source_variant_asin,
                              COUNT(*) AS review_count,
                              MAX(date) AS latest_review_date
                       FROM comments
                       WHERE user_id = %s
                         AND product_id = (
                             SELECT parent_product_id
                             FROM products
                             WHERE user_id = %s AND id = %s
                         )
                         AND source_variant_asin IS NOT NULL
                       GROUP BY source_variant_asin
                   ) vc ON vc.source_variant_asin = v.child_asin
                   WHERE v.user_id = %s AND v.product_id = %s
                   ORDER BY v.created_at DESC, v.id DESC""",
                (user_id, user_id, product_id, user_id, product_id),
            )
            return [dict(row) for row in cur.fetchall()]
    except psycopg2.errors.UndefinedTable:
        conn.rollback()
        return []
    finally:
        conn.close()



def upsert_product_from_api(user_id: int, data: dict[str, Any]) -> int:
    """从 Rainforest API 数据 upsert 产品记录，返回 product_id。"""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO products
                   (user_id, parent_product_id, name, scraped_title, platform, category, brand,
                    image_url, rating, ratings_total, reviews_total, current_version)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                   ON CONFLICT (user_id, parent_product_id) DO UPDATE SET
                       name = COALESCE(EXCLUDED.name, products.name),
                       scraped_title = COALESCE(EXCLUDED.scraped_title, products.scraped_title),
                       brand = COALESCE(EXCLUDED.brand, products.brand),
                       image_url = COALESCE(EXCLUDED.image_url, products.image_url),
                       rating = COALESCE(EXCLUDED.rating, products.rating),
                       ratings_total = COALESCE(EXCLUDED.ratings_total, products.ratings_total),
                       reviews_total = COALESCE(EXCLUDED.reviews_total, products.reviews_total),
                       category = COALESCE(EXCLUDED.category, products.category)
                   RETURNING id""",
                (
                    user_id,
                    data["parent_product_id"],
                    data.get("name"),
                    data.get("scraped_title"),
                    data.get("platform", "amazon"),
                    data.get("category"),
                    data.get("brand"),
                    data.get("image_url"),
                    data.get("rating"),
                    data.get("ratings_total"),
                    data.get("reviews_total"),
                    data.get("current_version", "V1"),
                ),
            )
            product_id = int(cur.fetchone()[0])
            conn.commit()
            return product_id
    finally:
        conn.close()


def upsert_variant_from_api(user_id: int, product_id: int, data: dict[str, Any]) -> int:
    """从 Rainforest API 数据 upsert 变体记录，返回 variant_id。

    使用 (user_id, platform, child_asin) 联合唯一索引（050 migration），
    支持同一 ASIN 在不同平台下独立存在。
    """
    platform = data.get("platform", "amazon")
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO product_variants
                   (user_id, product_id, child_asin, variant_sku, platform, name, brand,
                    image_url, price, price_currency, status)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                   ON CONFLICT (user_id, platform, child_asin) WHERE platform IS NOT NULL AND child_asin IS NOT NULL DO UPDATE SET
                       name = COALESCE(EXCLUDED.name, product_variants.name),
                       brand = COALESCE(EXCLUDED.brand, product_variants.brand),
                       image_url = COALESCE(EXCLUDED.image_url, product_variants.image_url),
                       price = COALESCE(EXCLUDED.price, product_variants.price),
                       price_currency = COALESCE(EXCLUDED.price_currency, product_variants.price_currency)
                   RETURNING id""",
                (
                    user_id,
                    product_id,
                    data.get("child_asin"),
                    data.get("child_asin"),
                    platform,
                    data.get("name"),
                    data.get("brand"),
                    data.get("image_url"),
                    data.get("price"),
                    data.get("price_currency", "USD"),
                    data.get("status", "active"),
                ),
            )
            variant_id = int(cur.fetchone()[0])
            conn.commit()
            return variant_id
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


def _fetch_session_versions_grouped(user_id: int) -> dict[str, list[str]]:
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """SELECT product_id, version
                   FROM sessions
                   WHERE user_id = %s AND product_id IS NOT NULL
                   GROUP BY product_id, version
                   ORDER BY product_id, version""",
                (user_id,),
            )
            grouped: dict[str, list[str]] = {}
            for row in cur.fetchall():
                pid = str(row["product_id"]).strip()
                ver = str(row["version"] or "V1")
                if pid:
                    grouped.setdefault(pid, []).append(ver)
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
    session_versions_by_parent = _fetch_session_versions_grouped(user_id)
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
        version_date_ranges = _build_version_date_ranges(comments)

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
                "latest_review_date": stats["latest_review_date"],
                "earliest_review_date": stats["earliest_review_date"],
                "variant_count": len(variants),
                "variants": variants,
                "versions": versions,
                "session_versions": session_versions_by_parent.get(parent_id, []),
                "version_date_ranges": version_date_ranges,
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


def _build_version_date_ranges(comments: list[dict[str, Any]]) -> dict[str, dict[str, str | None]]:
    version_dates: dict[str, list[str]] = {}
    for comment in comments:
        version = str(comment.get("version") or "").strip()
        if not version:
            continue
        date_str = str(comment.get("date") or "").strip()
        if date_str:
            version_dates.setdefault(version, []).append(date_str)
    result: dict[str, dict[str, str | None]] = {}
    for version, dates in version_dates.items():
        result[version] = {
            "earliest": min(dates) if dates else None,
            "latest": max(dates) if dates else None,
        }
    return result


def _build_comment_stats(comments: list[dict[str, Any]]) -> dict[str, Any]:
    review_count = len(comments)
    unrecognizable_count = sum(1 for comment in comments if comment.get("sentiment") == "unrecognizable")
    valid_count = review_count - unrecognizable_count
    positive_count = sum(1 for comment in comments if comment.get("sentiment") == "positive")
    negative_count = sum(1 for comment in comments if comment.get("sentiment") == "negative")
    top_issue = _get_top_tag(comments, "issue_tag")
    top_highlight = _get_top_tag(comments, "highlight_tag")
    valid_dates = [str(comment.get("date") or "") for comment in comments if comment.get("date")]
    latest_date = max(valid_dates, default="") or None
    earliest_date = min(valid_dates, default="") or None
    return {
        "review_count": review_count,
        "positive_rate": round((positive_count / valid_count) * 100, 1) if valid_count > 0 else 0.0,
        "negative_rate": round((negative_count / valid_count) * 100, 1) if valid_count > 0 else 0.0,
        "top_issue": top_issue,
        "top_highlight": top_highlight,
        "latest_review_date": latest_date,
        "earliest_review_date": earliest_date,
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


# ──────────────────────────────────────────────────────
# 5.8 产品管理功能增强 — 上传归并 + 变体管理
# ──────────────────────────────────────────────────────


def _detect_identifier_column(
    columns: list[str], sample_values: list[list[Any]], platform: str
) -> str | None:
    """在 CSV 列中自动检测标识码列名。

    Args:
        columns: CSV 列名列表（已标准化为小写）
        sample_values: 每列的前 N 个样本值
        platform: 平台 (amazon / aliexpress / ebay / shopee / walmart)

    Returns:
        检测到的最佳匹配列名，未找到返回 None
    """
    import re

    # 1. 按列名关键词匹配
    _COLUMN_KEYWORDS: dict[str, list[str]] = {
        "amazon": ["asin", "child_asin", "product_id", "item_id"],
        "aliexpress": ["product_id", "item_id", "productid", "itemid"],
        "ebay": ["product_id", "item_id", "epid"],
        "shopee": ["product_id", "item_id", "shopid"],
        "walmart": ["product_id", "item_id", "wpid", "sku"],
    }
    keywords = _COLUMN_KEYWORDS.get(platform.lower(), ["product_id", "item_id"])

    for kw in keywords:
        for col in columns:
            col_clean = col.strip().lower().replace(" ", "_").replace("-", "_")
            if col_clean == kw or kw in col_clean:
                return col

    # 2. ASIN 正则兜底（仅 Amazon）：^B[A-Z0-9]{9}$
    if platform.lower() == "amazon":
        asin_re = re.compile(r"^B[A-Z0-9]{9}$")
        for col in columns:
            col_idx = columns.index(col)
            vals = [str(v).strip().upper() for v in sample_values[col_idx] if v is not None]
            if vals and all(asin_re.match(v) for v in vals[:5] if v):
                return col

    # 3. AliExpress 纯数字长串兜底（8-16位数字）
    if platform.lower() == "aliexpress":
        num_re = re.compile(r"^\d{8,16}$")
        for col in columns:
            col_idx = columns.index(col)
            vals = [str(v).strip() for v in sample_values[col_idx] if v is not None]
            if vals and all(num_re.match(v) for v in vals[:5] if v):
                return col

    return None


def _extract_unique_identifiers(
    rows: list[dict[str, Any]], id_column: str, platform: str
) -> list[str]:
    """从 CSV 行数据中提取唯一标识码列表。"""
    import re

    seen: set[str] = set()
    result: list[str] = []

    for row in rows:
        raw = str(row.get(id_column, "")).strip()
        if not raw:
            continue

        if platform.lower() == "amazon":
            # 标准化 ASIN 为大写
            val = raw.upper()
            if re.match(r"^B[A-Z0-9]{9}$", val):
                if val not in seen:
                    seen.add(val)
                    result.append(val)
        elif platform.lower() == "aliexpress":
            val = raw
            if re.match(r"^\d{8,16}$", val):
                if val not in seen:
                    seen.add(val)
                    result.append(val)
        else:
            # 其他平台：接受非空值
            val = raw
            if val not in seen:
                seen.add(val)
                result.append(val)

    return result


def find_or_create_parent_product(
    user_id: int, parent_name: str, platform: str, category: str | None = None
) -> int:
    """按名称 + 平台查找或创建父产品，返回 product_id (DB PK)。

    查找逻辑：先按 parent_product_id（=parent_name）匹配，无则创建。
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            # 查找已有产品
            cur.execute(
                "SELECT id FROM products WHERE user_id = %s AND parent_product_id = %s",
                (user_id, parent_name),
            )
            row = cur.fetchone()
            if row:
                product_id = int(row[0])
                # 如果已有产品但 platform 为空，补充 platform
                cur.execute(
                    "UPDATE products SET platform = COALESCE(platform, %s) WHERE id = %s",
                    (platform, product_id),
                )
                conn.commit()
                return product_id

            # 不存在则创建
            cur.execute(
                """INSERT INTO products
                   (user_id, parent_product_id, name, platform, category, lifecycle_stage, current_version)
                   VALUES (%s, %s, %s, %s, %s, %s, %s)
                   RETURNING id""",
                (
                    user_id,
                    parent_name,
                    parent_name,
                    platform,
                    category,
                    "growth",
                    "V1",
                ),
            )
            product_id = int(cur.fetchone()[0])
            conn.commit()
            return product_id
    finally:
        conn.close()


def _find_existing_variant_parent(
    user_id: int, child_asin: str, platform: str
) -> int | None:
    """查找指定 ASIN 在当前用户+平台下是否已有归属父产品。

    Returns:
        已有父产品的 product_id (DB PK)，无则返回 None
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT product_id FROM product_variants
                   WHERE user_id = %s AND platform = %s AND child_asin = %s
                   LIMIT 1""",
                (user_id, platform, child_asin),
            )
            row = cur.fetchone()
            return int(row[0]) if row else None
    finally:
        conn.close()


def _get_parent_product_name(user_id: int, product_id: int) -> str:
    """获取产品的 parent_product_id（显示名）。"""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT parent_product_id FROM products WHERE user_id = %s AND id = %s",
                (user_id, product_id),
            )
            row = cur.fetchone()
            return str(row[0]) if row else "未知产品"
    finally:
        conn.close()


def upsert_product_variant_for_upload(
    user_id: int,
    platform: str,
    child_asin: str,
    parent_name: str,
    category: str | None = None,
) -> dict[str, Any]:
    """上传时 upsert 单个子 ASIN 变体，自动处理归并冲突。

    归并规则：
    - ASIN 重叠 > 名称匹配：若 child_asin 已属于其他父产品 → 不创建新变体，标记为"已归入 [原父产品]"
    - 无冲突：在 parent_name 对应的产品下创建/更新变体

    Returns:
        {
            "child_asin": str,
            "action": "new" | "existing" | "merged_to_other",
            "parent_name": str,
            "variant_id": int | None,
            "message": str,
        }
    """
    # 1. 检查 ASIN 是否已有归属（ASIN 重叠检查）
    existing_parent_id = _find_existing_variant_parent(user_id, child_asin, platform)
    if existing_parent_id is not None:
        existing_parent_name = _get_parent_product_name(user_id, existing_parent_id)
        # ASIN 已存在 → 不创建新记录，返回现有归属
        if existing_parent_name == parent_name:
            return {
                "child_asin": child_asin,
                "action": "existing",
                "parent_name": parent_name,
                "variant_id": None,
                "message": f"ASIN {child_asin} 已存在于父产品 [{parent_name}] 下",
            }
        else:
            # ASIN 属于其他父产品 → 按"ASIN 重叠 > 名称匹配"，归入已有父产品
            return {
                "child_asin": child_asin,
                "action": "merged_to_other",
                "parent_name": existing_parent_name,
                "variant_id": None,
                "message": f"ASIN {child_asin} 已归入父产品 [{existing_parent_name}]（按 ASIN 优先规则）",
            }

    # 2. 无冲突：查找/创建父产品，再创建变体
    parent_product_id = find_or_create_parent_product(
        user_id, parent_name, platform, category
    )

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO product_variants
                   (user_id, product_id, variant_sku, child_asin, platform, status)
                   VALUES (%s, %s, %s, %s, %s, %s)
                   ON CONFLICT (user_id, platform, child_asin)
                   WHERE platform IS NOT NULL AND child_asin IS NOT NULL
                   DO UPDATE SET
                       product_id = EXCLUDED.product_id,
                       variant_sku = COALESCE(NULLIF(EXCLUDED.variant_sku, ''), product_variants.variant_sku)
                   RETURNING id""",
                (
                    user_id,
                    parent_product_id,
                    child_asin,
                    child_asin,
                    platform,
                    "active",
                ),
            )
            variant_id = int(cur.fetchone()[0])
            conn.commit()
            return {
                "child_asin": child_asin,
                "action": "new",
                "parent_name": parent_name,
                "variant_id": variant_id,
                "message": f"ASIN {child_asin} 已归入父产品 [{parent_name}]",
            }
    finally:
        conn.close()


def batch_upsert_variants_for_upload(
    user_id: int,
    platform: str,
    identifiers: list[str],
    parent_name: str,
    category: str | None = None,
) -> list[dict[str, Any]]:
    """批量处理上传中的变体归并，返回每个标识码的处理结果列表。"""
    results: list[dict[str, Any]] = []
    for child_asin in identifiers:
        result = upsert_product_variant_for_upload(
            user_id, platform, child_asin, parent_name, category
        )
        results.append(result)
    return results


def move_variant_to_parent(
    user_id: int, variant_id: int, target_product_id: int
) -> dict[str, Any]:
    """将变体移动到另一个父产品下。

    Args:
        user_id: 当前用户
        variant_id: 要移动的变体 ID
        target_product_id: 目标父产品的 DB PK
    """
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            # 验证变体属于当前用户
            cur.execute(
                "SELECT * FROM product_variants WHERE id = %s AND user_id = %s",
                (variant_id, user_id),
            )
            variant = cur.fetchone()
            if not variant:
                return {"success": False, "message": "变体不存在或无权操作"}

            # 验证目标产品属于当前用户
            cur.execute(
                "SELECT * FROM products WHERE id = %s AND user_id = %s",
                (target_product_id, user_id),
            )
            target = cur.fetchone()
            if not target:
                return {"success": False, "message": "目标父产品不存在或无权操作"}

            old_product_id = int(variant["product_id"])

            # 移动变体
            cur.execute(
                "UPDATE product_variants SET product_id = %s WHERE id = %s",
                (target_product_id, variant_id),
            )
            conn.commit()

            old_name = _get_parent_product_name(user_id, old_product_id)
            target_name = _get_parent_product_name(user_id, target_product_id)

            return {
                "success": True,
                "variant_id": variant_id,
                "child_asin": variant.get("child_asin"),
                "from_parent": old_name,
                "to_parent": target_name,
                "message": f"变体 {variant.get('child_asin')} 已从 [{old_name}] 移动到 [{target_name}]",
            }
    finally:
        conn.close()


# ──────────────────────────────────────────────────────
# Step 11.5: Chrome 插件 Listing 上传
# ──────────────────────────────────────────────────────


def plugin_upload_listing(
    user_id: int,
    parent_asin: str,
    name: str,
    platform: str = "amazon",
    marketplace: str = "us",
    listing: dict[str, Any] | None = None,
    variants: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """处理 Chrome 插件的产品 listing 上传。

    1. 按 parent_asin 查找或创建产品（name 为用户手动填写）
    2. Upsert listing 详情到 product_listings 表
    3. 批量 upsert 变体到 product_variants 表

    Args:
        user_id: 当前用户 ID
        parent_asin: Amazon 父 ASIN
        name: 用户填写的产品名称
        platform: 平台（默认 amazon）
        marketplace: 市场（默认 us）
        listing: listing 详情 dict
        variants: 变体列表 [{asin, color, size, style, material}, ...]

    Returns:
        { product_id, variant_count, listing_updated, message }
    """
    if not parent_asin or not parent_asin.strip():
        raise ValueError("parent_asin is required")
    if not name or not name.strip():
        raise ValueError("name is required")

    parent_asin = parent_asin.strip().upper()
    name = name.strip()
    listing = listing or {}
    variants = variants or []

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            # 1. 查找已有产品（按 parent_asin，即 ASIN 作为唯一标识）
            cur.execute(
                "SELECT id FROM products WHERE user_id = %s AND parent_product_id = %s",
                (user_id, parent_asin),
            )
            row = cur.fetchone()
            if row:
                product_id = int(row[0])
                # 更新产品名称（用户随时可以修改）
                cur.execute(
                    """UPDATE products
                       SET name = %s, platform = COALESCE(platform, %s)
                       WHERE id = %s""",
                    (name, platform, product_id),
                )
                product_created = False
            else:
                # 新建产品
                cur.execute(
                    """INSERT INTO products
                       (user_id, parent_product_id, name, platform, lifecycle_stage, current_version)
                       VALUES (%s, %s, %s, %s, %s, %s)
                       RETURNING id""",
                    (user_id, parent_asin, name, platform, "growth", "V1"),
                )
                product_id = int(cur.fetchone()[0])
                product_created = True

            # 2. Upsert listing 详情到 product_listings
            listing_updated = False
            if listing:
                bullet_points = listing.get("bullet_points") or []
                if isinstance(bullet_points, list):
                    bullet_points_json = psycopg2.extras.Json(bullet_points)
                else:
                    bullet_points_json = psycopg2.extras.Json([])

                best_seller_rank = listing.get("best_seller_rank") or []
                if isinstance(best_seller_rank, list):
                    bsr_json = psycopg2.extras.Json(best_seller_rank)
                else:
                    bsr_json = psycopg2.extras.Json([])

                # 更新 products 表中的快速字段（用于列表页展示）
                cur.execute(
                    """UPDATE products SET
                       brand = COALESCE(%s, brand),
                       image_url = COALESCE(%s, image_url),
                       rating = COALESCE(%s, rating),
                       ratings_total = COALESCE(%s, ratings_total),
                       scraped_title = COALESCE(%s, scraped_title)
                       WHERE id = %s""",
                    (
                        listing.get("brand"),
                        listing.get("main_image_url"),
                        listing.get("rating"),
                        listing.get("ratings_total"),
                        listing.get("title"),
                        product_id,
                    ),
                )

                # Upsert into product_listings
                try:
                    cur.execute(
                        """INSERT INTO product_listings
                           (product_id, parent_asin, marketplace, title, price, price_currency,
                            original_price, rating, ratings_total, brand, bullet_points,
                            main_image_url, description, best_seller_rank, dimensions, weight,
                            seller_name, availability, scraped_at)
                           VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
                           ON CONFLICT (product_id) DO UPDATE SET
                               marketplace = EXCLUDED.marketplace,
                               title = EXCLUDED.title,
                               price = EXCLUDED.price,
                               price_currency = EXCLUDED.price_currency,
                               original_price = EXCLUDED.original_price,
                               rating = EXCLUDED.rating,
                               ratings_total = EXCLUDED.ratings_total,
                               brand = EXCLUDED.brand,
                               bullet_points = EXCLUDED.bullet_points,
                               main_image_url = EXCLUDED.main_image_url,
                               description = EXCLUDED.description,
                               best_seller_rank = EXCLUDED.best_seller_rank,
                               dimensions = EXCLUDED.dimensions,
                               weight = EXCLUDED.weight,
                               seller_name = EXCLUDED.seller_name,
                               availability = EXCLUDED.availability,
                               scraped_at = NOW()""",
                        (
                            product_id,
                            parent_asin,
                            marketplace,
                            listing.get("title"),
                            listing.get("price"),
                            listing.get("price_currency", "USD"),
                            listing.get("original_price"),
                            listing.get("rating"),
                            listing.get("ratings_total"),
                            listing.get("brand"),
                            bullet_points_json,
                            listing.get("main_image_url"),
                            listing.get("description"),
                            bsr_json,
                            listing.get("dimensions"),
                            listing.get("weight"),
                            listing.get("seller_name"),
                            listing.get("availability"),
                        ),
                    )
                    listing_updated = True
                except psycopg2.errors.UndefinedTable:
                    conn.rollback()
                    # product_listings table doesn't exist yet; non-fatal
                    pass

            # 3. 批量 upsert 变体（手动 SELECT → INSERT/UPDATE，不依赖 ON CONFLICT 索引）
            variant_count = 0
            for var in variants:
                child_asin = (var.get("asin") or "").strip().upper()
                if not child_asin or not _is_valid_asin(child_asin, platform):
                    continue

                try:
                    # 查找已有变体：优先匹配 (user_id, platform, child_asin)
                    cur.execute(
                        """SELECT id FROM product_variants
                           WHERE user_id = %s AND platform = %s AND child_asin = %s
                           LIMIT 1""",
                        (user_id, platform, child_asin),
                    )
                    existing = cur.fetchone()
                    if existing:
                        cur.execute(
                            """UPDATE product_variants SET
                               product_id = %s,
                               color = COALESCE(%s, color),
                               size = COALESCE(%s, size),
                               style = COALESCE(%s, style),
                               material = COALESCE(%s, material),
                               status = 'active'
                               WHERE id = %s""",
                            (
                                product_id,
                                var.get("color"),
                                var.get("size"),
                                var.get("style"),
                                var.get("material"),
                                existing[0],
                            ),
                        )
                    else:
                        cur.execute(
                            """INSERT INTO product_variants
                               (user_id, product_id, child_asin, variant_sku, platform,
                                color, size, style, material, status)
                               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                            (
                                user_id,
                                product_id,
                                child_asin,
                                child_asin,
                                platform,
                                var.get("color"),
                                var.get("size"),
                                var.get("style"),
                                var.get("material"),
                                "active",
                            ),
                        )
                    variant_count += 1
                except Exception:
                    conn.rollback()
                    # variant insert/update failed; skip this variant and continue
                    continue

            conn.commit()

            return {
                "product_id": product_id,
                "variant_count": variant_count,
                "listing_updated": listing_updated,
                "message": (
                    "产品已创建并上传成功"
                    if product_created
                    else "产品信息已更新"
                ),
            }
    finally:
        conn.close()


def _is_valid_asin(asin: str, platform: str) -> bool:
    """Check if a string looks like a valid ASIN for the given platform."""
    import re
    if platform.lower() == "amazon":
        return bool(re.match(r"^B[A-Z0-9]{9}$", asin))
    return len(asin) >= 4


def get_parent_variant_analysis(
    user_id: int, product_id: int
) -> dict[str, Any]:
    """获取父变体下所有子 ASIN 的聚合分析数据（仅当前用户）。

    从 sessions/comments 表中聚合当前用户该产品的所有分析结果。
    """
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            # 获取该产品下的所有变体
            cur.execute(
                """SELECT
                       v.child_asin,
                       v.id,
                       COALESCE(vc.review_count, 0) AS review_count
                   FROM product_variants v
                   LEFT JOIN (
                       SELECT source_variant_asin,
                              COUNT(*) AS review_count
                       FROM comments
                       WHERE user_id = %s
                         AND product_id = (
                             SELECT parent_product_id
                             FROM products
                             WHERE id = %s AND user_id = %s
                         )
                         AND source_variant_asin IS NOT NULL
                       GROUP BY source_variant_asin
                   ) vc ON vc.source_variant_asin = v.child_asin
                   WHERE v.user_id = %s
                     AND v.product_id = %s
                     AND v.child_asin IS NOT NULL""",
                (user_id, product_id, user_id, user_id, product_id),
            )
            variants = [dict(r) for r in cur.fetchall()]

            # 聚合该产品所有 session 的分析数据
            cur.execute(
                """SELECT
                    COUNT(*) as total_reviews,
                    COUNT(CASE WHEN sentiment = 'positive' THEN 1 END) as positive_count,
                    COUNT(CASE WHEN sentiment = 'negative' THEN 1 END) as negative_count,
                    COUNT(CASE WHEN sentiment = 'unrecognizable' THEN 1 END) as unrecognizable_count,
                    MAX(date) as latest_date,
                    MIN(date) as earliest_date
                   FROM comments
                   WHERE user_id = %s AND product_id = (
                       SELECT parent_product_id FROM products WHERE id = %s AND user_id = %s
                   )""",
                (user_id, product_id, user_id),
            )
            stats = dict(cur.fetchone() or {})

            # 获取分析中的 ASIN 数量
            cur.execute(
                """SELECT COUNT(DISTINCT uj.id) as in_progress_count
                   FROM upload_jobs uj
                   WHERE uj.user_id = %s
                     AND uj.status IN ('queued', 'processing')
                     AND uj.payload_json->>'platform' = (
                         SELECT platform FROM products WHERE id = %s AND user_id = %s
                     )""",
                (user_id, product_id, user_id),
            )
            in_progress = dict(cur.fetchone() or {})

            return {
                "variants": variants,
                "total_reviews": stats.get("total_reviews", 0) or 0,
                "positive_count": stats.get("positive_count", 0) or 0,
                "negative_count": stats.get("negative_count", 0) or 0,
                "unrecognizable_count": stats.get("unrecognizable_count", 0) or 0,
                "latest_date": str(stats.get("latest_date") or ""),
                "earliest_date": str(stats.get("earliest_date") or ""),
                "in_progress_asin_count": in_progress.get("in_progress_count", 0) or 0,
                "has_data": (stats.get("total_reviews", 0) or 0) > 0,
            }
    finally:
        conn.close()
