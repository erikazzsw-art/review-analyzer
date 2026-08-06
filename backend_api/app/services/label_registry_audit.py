"""5.9.6-D WP7: Label registry audit events.

Machine-written records of resolver rejections, shadow diffs, and
human-flagged mislabels. These are the input data for proposal generation
and the review page.

Decision n: audit events are write-only from code, read by the review page.
They do NOT auto-modify the registry YAML.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from review_analyzer.database import get_connection

logger = logging.getLogger(__name__)

AUDIT_EVENT_RESOLVER_REJECT = "resolver_reject"
AUDIT_EVENT_SHADOW_DIFF = "shadow_diff"
AUDIT_EVENT_HUMAN_FLAG = "human_flag"
VALID_AUDIT_EVENT_TYPES = frozenset({
    AUDIT_EVENT_RESOLVER_REJECT,
    AUDIT_EVENT_SHADOW_DIFF,
    AUDIT_EVENT_HUMAN_FLAG,
})


@dataclass(frozen=True)
class AuditEvent:
    """A single audit event for the label registry reflux pipeline."""

    event_type: str  # resolver_reject | shadow_diff | human_flag
    label_key: str
    sub_category: str = ""
    category: str = ""
    reject_reason: str | None = None
    existing_display_label: str = ""
    context: str = ""
    source: str = "system"


def record_audit_event(event: AuditEvent) -> int | None:
    """Persist a single audit event to the database.

    Returns the new row id, or None on error.
    Fail-open: DB errors are logged, not raised. Audit events are
    observational — losing one should not break the request.
    """
    if event.event_type not in VALID_AUDIT_EVENT_TYPES:
        logger.warning(
            "label_registry_audit: unknown event_type=%r for label=%r",
            event.event_type, event.label_key,
        )
        return None

    try:
        conn = get_connection()
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO label_registry_audit_events
                    (event_type, label_key, sub_category, category,
                     reject_reason, existing_display_label, context, source)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
                """,
                (
                    event.event_type,
                    event.label_key,
                    event.sub_category,
                    event.category,
                    event.reject_reason,
                    event.existing_display_label,
                    event.context,
                    event.source,
                ),
            )
            row = cur.fetchone()
            conn.commit()
            return int(row[0]) if row else None
    except Exception:
        logger.exception(
            "label_registry_audit: failed to record event type=%r label=%r",
            event.event_type, event.label_key,
        )
        try:
            conn.rollback()
        except Exception:
            pass
        return None


def record_audit_events_batch(events: list[AuditEvent]) -> int:
    """Persist multiple audit events in one batch.

    Returns the number of successfully inserted rows.
    """
    if not events:
        return 0
    inserted = 0
    for event in events:
        row_id = record_audit_event(event)
        if row_id is not None:
            inserted += 1
    return inserted


def query_audit_events(
    *,
    label_key: str | None = None,
    event_type: str | None = None,
    sub_category: str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[dict[str, Any]]:
    """Read audit events from the database with optional filters."""
    conditions: list[str] = []
    params: list[Any] = []

    if label_key:
        conditions.append("label_key = %s")
        params.append(label_key)
    if event_type:
        conditions.append("event_type = %s")
        params.append(event_type)
    if sub_category:
        conditions.append("sub_category = %s")
        params.append(sub_category)

    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
    query = f"""
        SELECT id, event_type, label_key, sub_category, category,
               reject_reason, existing_display_label, context, source, created_at
        FROM label_registry_audit_events
        {where}
        ORDER BY created_at DESC
        LIMIT %s OFFSET %s
    """
    params.extend([limit, offset])

    try:
        conn = get_connection()
        with conn.cursor() as cur:
            cur.execute(query, params)
            return [dict(row) for row in cur.fetchall()]
    except Exception:
        logger.exception("label_registry_audit: query failed")
        return []
