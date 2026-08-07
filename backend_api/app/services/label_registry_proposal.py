"""5.9.6-D WP7: Registry proposal artifact generation.

Machine-generated candidates for human review. Four closed action types
per decision n:

  scope_adjust      — change scope_policy or aspect_keys
  alias_merge       — merge synonymous labels
  blocked_rule      — add blocked_contexts entry
  negative_example  — add a negative example

Proposals do NOT auto-modify the registry YAML. They are queued for
human review via the /settings/label-review page (WP8).
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Any

from review_analyzer.database import get_connection

logger = logging.getLogger(__name__)

# Decision n: closed enumeration — do NOT add a 5th type.
PROPOSAL_ACTION_SCOPE_ADJUST = "scope_adjust"
PROPOSAL_ACTION_ALIAS_MERGE = "alias_merge"
PROPOSAL_ACTION_BLOCKED_RULE = "blocked_rule"
PROPOSAL_ACTION_NEGATIVE_EXAMPLE = "negative_example"
VALID_PROPOSAL_ACTIONS = frozenset({
    PROPOSAL_ACTION_SCOPE_ADJUST,
    PROPOSAL_ACTION_ALIAS_MERGE,
    PROPOSAL_ACTION_BLOCKED_RULE,
    PROPOSAL_ACTION_NEGATIVE_EXAMPLE,
})

PROPOSAL_STATUS_PENDING = "pending"
PROPOSAL_STATUS_APPROVED = "approved"
PROPOSAL_STATUS_REJECTED = "rejected"
PROPOSAL_STATUS_APPLIED = "applied"
VALID_PROPOSAL_STATUSES = frozenset({
    PROPOSAL_STATUS_PENDING,
    PROPOSAL_STATUS_APPROVED,
    PROPOSAL_STATUS_REJECTED,
    PROPOSAL_STATUS_APPLIED,
})


@dataclass(frozen=True)
class RegistryProposal:
    """A label registry change proposal for human review.

    proposal_data shape depends on action_type:
      scope_adjust:     {scope_policy, aspect_keys, reason}
      alias_merge:      {source_keys, target_key, reason}
      blocked_rule:     {sub_categories, context_markers, reason}
      negative_example: {type, sub_category, review_text, why_not}
    """

    label_key: str
    action_type: str
    proposal_data: dict[str, Any]
    evidence_summary: str = ""


def _validate_proposal_data(action_type: str, data: dict[str, Any]) -> list[str]:
    """Validate proposal_data shape against action_type. Returns error list."""
    errors: list[str] = []
    if action_type == PROPOSAL_ACTION_SCOPE_ADJUST:
        if "scope_policy" not in data:
            errors.append("scope_adjust: missing scope_policy")
        if "reason" not in data:
            errors.append("scope_adjust: missing reason")
    elif action_type == PROPOSAL_ACTION_ALIAS_MERGE:
        if "target_key" not in data:
            errors.append("alias_merge: missing target_key")
        if not data.get("source_keys"):
            errors.append("alias_merge: missing source_keys")
        else:
            # Repair batch 1a (Bug from audit §5.4): cross-label_type
            # alias_merge would silently merge a highlight into an issue,
            # permanently losing the positive/negative distinction.
            # Hard-reject at the code layer; UI warning is the second layer.
            from backend_api.app.services.review_fragment_label_catalog import (
                get_label_registry_state,
            )

            state = get_label_registry_state()
            label_map = {lb.key: lb for lb in state.labels}

            target_key = str(data.get("target_key", ""))
            target_label = label_map.get(target_key)
            if target_label is None:
                errors.append(
                    f"alias_merge: target_key={target_key!r} not found in registry"
                )
            else:
                target_type = target_label.label_type
                for sk in data["source_keys"]:
                    sk_str = str(sk)
                    src_label = label_map.get(sk_str)
                    if src_label is None:
                        errors.append(
                            f"alias_merge: source_key={sk_str!r} not found in registry"
                        )
                    elif src_label.label_type != target_type:
                        errors.append(
                            f"alias_merge: source_key={sk_str!r} has "
                            f"label_type={src_label.label_type!r} but "
                            f"target_key={target_key!r} has "
                            f"label_type={target_type!r}. Cross-type merge "
                            f"is forbidden — merging a highlight into an "
                            f"issue would permanently lose the "
                            f"positive/negative distinction."
                        )
    elif action_type == PROPOSAL_ACTION_BLOCKED_RULE:
        if not data.get("sub_categories"):
            errors.append("blocked_rule: missing sub_categories")
        if "reason" not in data:
            errors.append("blocked_rule: missing reason")
    elif action_type == PROPOSAL_ACTION_NEGATIVE_EXAMPLE:
        if "type" not in data:
            errors.append("negative_example: missing type")
        if "sub_category" not in data:
            errors.append("negative_example: missing sub_category")
        if "review_text" not in data:
            errors.append("negative_example: missing review_text")
    return errors


def create_proposal(proposal: RegistryProposal) -> int | None:
    """Persist a single proposal to the database.

    Returns the new row id, or None on error.
    """
    if proposal.action_type not in VALID_PROPOSAL_ACTIONS:
        logger.warning(
            "label_registry_proposal: unknown action_type=%r for label=%r",
            proposal.action_type, proposal.label_key,
        )
        return None

    errors = _validate_proposal_data(proposal.action_type, proposal.proposal_data)
    if errors:
        logger.warning(
            "label_registry_proposal: invalid data for label=%r action=%r: %s",
            proposal.label_key, proposal.action_type, errors,
        )
        return None

    try:
        conn = get_connection()
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO label_registry_proposals
                    (label_key, action_type, proposal_data, evidence_summary, proposal_status)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id
                """,
                (
                    proposal.label_key,
                    proposal.action_type,
                    json.dumps(proposal.proposal_data, ensure_ascii=False),
                    proposal.evidence_summary,
                    PROPOSAL_STATUS_PENDING,
                ),
            )
            row = cur.fetchone()
            conn.commit()
            return int(row[0]) if row else None
    except Exception:
        logger.exception(
            "label_registry_proposal: failed to create proposal label=%r action=%r",
            proposal.label_key, proposal.action_type,
        )
        try:
            conn.rollback()
        except Exception:
            pass
        return None


def query_proposals(
    *,
    label_key: str | None = None,
    action_type: str | None = None,
    proposal_status: str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[dict[str, Any]]:
    """Read proposals from the database with optional filters."""
    conditions: list[str] = []
    params: list[Any] = []

    if label_key:
        conditions.append("label_key = %s")
        params.append(label_key)
    if action_type:
        conditions.append("action_type = %s")
        params.append(action_type)
    if proposal_status:
        conditions.append("proposal_status = %s")
        params.append(proposal_status)

    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
    query = f"""
        SELECT id, label_key, action_type, proposal_data,
               evidence_summary, proposal_status, reviewer_note,
               reviewed_by, reviewed_at, created_at
        FROM label_registry_proposals
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
        logger.exception("label_registry_proposal: query failed")
        return []


def get_proposal_by_id(proposal_id: int) -> dict[str, Any] | None:
    """Fetch a single proposal by its primary key.

    Returns the proposal dict or None if not found.
    Repair batch 1a (Bug 3): replaces the limit=1 scan that could only find
    the most recent proposal.
    """
    try:
        conn = get_connection()
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, label_key, action_type, proposal_data,
                       evidence_summary, proposal_status, reviewer_note,
                       reviewed_by, reviewed_at, created_at
                FROM label_registry_proposals
                WHERE id = %s
                """,
                (proposal_id,),
            )
            row = cur.fetchone()
            return dict(row) if row else None
    except Exception:
        logger.exception(
            "label_registry_proposal: failed to fetch proposal id=%d",
            proposal_id,
        )
        return None


def update_proposal_status(
    proposal_id: int,
    *,
    new_status: str,
    reviewer_note: str = "",
    reviewed_by: str = "",
) -> bool:
    """Update a proposal's status (approve / reject / applied).

    Returns True on success.
    """
    if new_status not in VALID_PROPOSAL_STATUSES:
        logger.warning(
            "label_registry_proposal: unknown status=%r for proposal=%d",
            new_status, proposal_id,
        )
        return False

    try:
        conn = get_connection()
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE label_registry_proposals
                SET proposal_status = %s,
                    reviewer_note = %s,
                    reviewed_by = %s,
                    reviewed_at = NOW()
                WHERE id = %s
                """,
                (new_status, reviewer_note, reviewed_by, proposal_id),
            )
            conn.commit()
            return cur.rowcount > 0
    except Exception:
        logger.exception(
            "label_registry_proposal: failed to update proposal=%d to status=%r",
            proposal_id, new_status,
        )
        try:
            conn.rollback()
        except Exception:
            pass
        return False


# ---------------------------------------------------------------------------
# Proposal generation helpers (decision n: machine-generated candidates)
# ---------------------------------------------------------------------------


def generate_scope_adjust_proposal(
    label_key: str,
    *,
    current_scope_policy: str,
    suggested_scope_policy: str,
    suggested_aspect_keys: list[str] | None = None,
    reason: str = "",
    evidence_summary: str = "",
) -> RegistryProposal | None:
    """Generate a scope_adjust proposal for human review."""
    data: dict[str, Any] = {
        "current_scope_policy": current_scope_policy,
        "suggested_scope_policy": suggested_scope_policy,
        "reason": reason,
    }
    if suggested_aspect_keys is not None:
        data["suggested_aspect_keys"] = suggested_aspect_keys
    return RegistryProposal(
        label_key=label_key,
        action_type=PROPOSAL_ACTION_SCOPE_ADJUST,
        proposal_data=data,
        evidence_summary=evidence_summary,
    )


def generate_alias_merge_proposal(
    label_key: str,
    *,
    target_key: str,
    source_keys: list[str],
    reason: str = "",
    evidence_summary: str = "",
) -> RegistryProposal | None:
    """Generate an alias_merge proposal for human review."""
    if not source_keys:
        return None
    return RegistryProposal(
        label_key=label_key,
        action_type=PROPOSAL_ACTION_ALIAS_MERGE,
        proposal_data={
            "target_key": target_key,
            "source_keys": source_keys,
            "reason": reason,
        },
        evidence_summary=evidence_summary,
    )


def generate_blocked_rule_proposal(
    label_key: str,
    *,
    sub_categories: list[str],
    context_markers: list[str] | None = None,
    reason: str = "",
    evidence_summary: str = "",
) -> RegistryProposal | None:
    """Generate a blocked_rule proposal for human review."""
    if not sub_categories:
        return None
    data: dict[str, Any] = {
        "sub_categories": sub_categories,
        "reason": reason,
    }
    if context_markers:
        data["context_markers"] = context_markers
    return RegistryProposal(
        label_key=label_key,
        action_type=PROPOSAL_ACTION_BLOCKED_RULE,
        proposal_data=data,
        evidence_summary=evidence_summary,
    )


def generate_negative_example_proposal(
    label_key: str,
    *,
    example_type: str,
    sub_category: str,
    review_text: str,
    why_not: str = "",
    evidence_summary: str = "",
) -> RegistryProposal | None:
    """Generate a negative_example proposal for human review."""
    if not sub_category or not review_text:
        return None
    return RegistryProposal(
        label_key=label_key,
        action_type=PROPOSAL_ACTION_NEGATIVE_EXAMPLE,
        proposal_data={
            "type": example_type,
            "sub_category": sub_category,
            "review_text": review_text,
            "why_not": why_not,
        },
        evidence_summary=evidence_summary,
    )
