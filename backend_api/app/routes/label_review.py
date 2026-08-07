"""5.9.6-D WP8: Label Registry Review API.

Internal page at /settings/label-review (decision o):
  1. Proposal queue list
  2. approve / reject / merge actions
  3. Write back to registry YAML + run validation + generate negative test

Scope: review_fragment_label_registry.yaml ONLY. No DB writes to
customer_label_catalog or legacy tables.
"""
from __future__ import annotations

import logging
import subprocess
import sys
from pathlib import Path
from typing import Any

import yaml
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

from backend_api.app.deps import get_admin_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/settings/label-review", tags=["label-review"])

_REGISTRY_PATH = (
    Path(__file__).resolve().parents[3]
    / "data"
    / "taxonomy"
    / "registry"
    / "review_fragment_label_registry.yaml"
)

_VALIDATE_SCRIPT = (
    Path(__file__).resolve().parents[3]
    / "scripts"
    / "validate_label_scope.py"
)

# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------


class ProposalItem(BaseModel):
    id: int
    label_key: str
    action_type: str
    proposal_data: dict[str, Any] = {}
    evidence_summary: str = ""
    proposal_status: str = "pending"
    reviewer_note: str = ""
    reviewed_by: str = ""
    reviewed_at: str | None = None
    created_at: str = ""


class ProposalListResponse(BaseModel):
    proposals: list[ProposalItem]
    total: int


class ReviewAction(BaseModel):
    proposal_id: int
    action: str  # "approve" | "reject" | "merge"
    reviewer_note: str = ""


class ReviewActionResult(BaseModel):
    success: bool
    message: str
    validation_output: str = ""


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.get("/proposals", response_model=ProposalListResponse)
def list_proposals(
    status_filter: str = Query(default="pending", alias="status"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    current_user: dict = Depends(get_admin_user),
) -> ProposalListResponse:
    """List registry proposals with optional status filter."""
    from backend_api.app.services.label_registry_proposal import query_proposals

    rows = query_proposals(
        proposal_status=status_filter if status_filter != "all" else None,
        limit=limit,
        offset=offset,
    )
    proposals = [_proposal_item(row) for row in rows]
    return ProposalListResponse(proposals=proposals, total=len(proposals))


@router.post("/review", response_model=ReviewActionResult)
def review_proposal(
    body: ReviewAction,
    current_user: dict = Depends(get_admin_user),
) -> ReviewActionResult:
    """Approve, reject, or merge a registry proposal.

    - approve: marks proposal as approved, applies to YAML
    - reject:  marks proposal as rejected
    - merge:   marks as applied, writes back to YAML + generates negative test

    YAML write-back (decision o):
      - Only modifies review_fragment_label_registry.yaml
      - Runs validate_label_scope.py after write
      - Rolls back on validation failure
      - Generates negative example regression test
    """
    from backend_api.app.services.label_registry_proposal import (
        PROPOSAL_STATUS_APPROVED,
        PROPOSAL_STATUS_REJECTED,
        get_proposal_by_id,
        update_proposal_status,
    )

    if body.action not in ("approve", "reject", "merge"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid action: {body.action}. Must be approve, reject, or merge.",
        )

    user_id = str(current_user.get("id", "unknown"))

    # Repair batch 1a (Bug 3): use get_proposal_by_id instead of scanning
    # the most recent proposal. The old limit=1 scan meant only the newest
    # proposal could be approved/rejected/merged — all others returned 404.
    target = get_proposal_by_id(body.proposal_id)

    if target is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Proposal {body.proposal_id} not found.",
        )

    if body.action == "reject":
        ok = update_proposal_status(
            body.proposal_id,
            new_status=PROPOSAL_STATUS_REJECTED,
            reviewer_note=body.reviewer_note,
            reviewed_by=user_id,
        )
        return ReviewActionResult(
            success=ok,
            message="Proposal rejected." if ok else "Failed to update proposal status.",
        )

    if body.action == "approve":
        ok = update_proposal_status(
            body.proposal_id,
            new_status=PROPOSAL_STATUS_APPROVED,
            reviewer_note=body.reviewer_note,
            reviewed_by=user_id,
        )
        return ReviewActionResult(
            success=ok,
            message="Proposal approved." if ok else "Failed to update proposal status.",
        )

    # --- merge: not implemented (decision q, repair batch 1a) ---
    # Registry changes must go through PR workflow, not in-container YAML
    # write-back. The _apply_proposal_to_yaml / _run_validation /
    # _restore_yaml_backup / _generate_negative_test helpers are preserved
    # below but no longer called. They will be reworked when the patch
    # generation architecture lands (batch 2-1).
    if body.action == "merge":
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail=(
                "Merge is not available. Registry changes must go through the "
                "PR workflow: generate a patch from the proposal, submit a PR "
                "against the taxonomy/registry YAML, and run "
                "validate_label_scope.py in CI. See batch 2-1 for the patch "
                "generation tooling."
            ),
        )


# ---------------------------------------------------------------------------
# YAML write-back helpers (decision o → decision q, repair batch 1a)
#
# These functions are preserved but NO LONGER CALLED. Merge was disabled
# in batch 1a (decision q): registry changes must go through PR workflow,
# not in-container YAML write-back. The helpers will be reworked when the
# patch generation architecture lands (batch 2-1).
# ---------------------------------------------------------------------------


def _apply_proposal_to_yaml(
    label_key: str,
    action_type: str,
    proposal_data: dict[str, Any],
) -> None:
    """Apply an approved proposal to review_fragment_label_registry.yaml.

    Only modifies this single file. Creates a .bak backup before writing.
    """
    from backend_api.app.services.label_registry_proposal import (
        PROPOSAL_ACTION_ALIAS_MERGE,
        PROPOSAL_ACTION_BLOCKED_RULE,
        PROPOSAL_ACTION_NEGATIVE_EXAMPLE,
        PROPOSAL_ACTION_SCOPE_ADJUST,
    )

    # Backup
    backup_path = _REGISTRY_PATH.with_suffix(".yaml.bak")
    backup_path.write_text(_REGISTRY_PATH.read_text(encoding="utf-8"), encoding="utf-8")

    raw = yaml.safe_load(_REGISTRY_PATH.read_text(encoding="utf-8")) or {}
    labels = raw.get("labels") or []

    target_label = None
    for label in labels:
        if label.get("key") == label_key:
            target_label = label
            break

    if target_label is None:
        raise ValueError(f"Label {label_key!r} not found in registry YAML.")

    if action_type == PROPOSAL_ACTION_SCOPE_ADJUST:
        if "scope_policy" in proposal_data:
            target_label["scope_policy"] = proposal_data["scope_policy"]
        if "aspect_keys" in proposal_data:
            target_label["aspect_keys"] = proposal_data["aspect_keys"]
        if "reason" in proposal_data:
            target_label["scope_reason"] = proposal_data["reason"]

    elif action_type == PROPOSAL_ACTION_ALIAS_MERGE:
        existing_aliases = list(target_label.get("aliases") or [])
        for source_key in proposal_data.get("source_keys", []):
            if source_key not in existing_aliases:
                existing_aliases.append(source_key)
        target_label["aliases"] = existing_aliases

    elif action_type == PROPOSAL_ACTION_BLOCKED_RULE:
        existing_blocked = list(target_label.get("blocked_contexts") or [])
        for sc in proposal_data.get("sub_categories", []):
            if sc not in existing_blocked:
                existing_blocked.append(sc)
        target_label["blocked_contexts"] = existing_blocked

    elif action_type == PROPOSAL_ACTION_NEGATIVE_EXAMPLE:
        existing_negatives = list(target_label.get("negative_examples") or [])
        new_neg = {
            "type": proposal_data.get("type", "out_of_scope"),
            "sub_category": proposal_data.get("sub_category", ""),
            "review_text": proposal_data.get("review_text", ""),
        }
        if proposal_data.get("why_not"):
            new_neg["why_not"] = proposal_data.get("why_not", "")
        existing_negatives.append(new_neg)
        target_label["negative_examples"] = existing_negatives

    # Write back
    _REGISTRY_PATH.write_text(
        yaml.dump(raw, default_flow_style=False, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )


def _run_validation() -> tuple[bool, str]:
    """Run validate_label_scope.py --dry-run. Returns (passed, output)."""
    try:
        result = subprocess.run(
            [sys.executable, str(_VALIDATE_SCRIPT), "--dry-run"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        output = result.stdout + "\n" + result.stderr
        return result.returncode == 0, output
    except Exception as exc:
        return False, str(exc)


def _restore_yaml_backup() -> None:
    """Restore the .bak file if validation failed."""
    backup_path = _REGISTRY_PATH.with_suffix(".yaml.bak")
    if backup_path.exists():
        _REGISTRY_PATH.write_text(backup_path.read_text(encoding="utf-8"), encoding="utf-8")


def _generate_negative_test(
    label_key: str,
    action_type: str,
    proposal_data: dict[str, Any],
) -> str:
    """Generate a negative example regression test case.

    Returns a human-readable description of what was generated.
    """
    from backend_api.app.services.label_registry_proposal import (
        PROPOSAL_ACTION_NEGATIVE_EXAMPLE,
    )

    test_file = (
        Path(__file__).resolve().parents[3]
        / "backend_api"
        / "tests"
        / "test_review_fragment_label_catalog.py"
    )

    if action_type == PROPOSAL_ACTION_NEGATIVE_EXAMPLE:
        sub_cat = proposal_data.get("sub_category", "unknown")
        test_name = f"test_negative_{label_key}_{sub_cat}".replace("-", "_")
        # Check if test already exists
        existing = test_file.read_text(encoding="utf-8") if test_file.exists() else ""
        if test_name in existing:
            return f"test already exists: {test_name}"

        snippet = f'''

def {test_name}() -> None:
    """Auto-generated negative example regression test (WP8 merge)."""
    from backend_api.app.services.review_fragment_label_catalog import (
        ResolutionRejectReason,
        resolve_formal_label,
    )
    result = resolve_formal_label(
        "{label_key}",
        category_key="",
        sub_category_key="{sub_cat}",
    )
    assert not result.is_resolved
    assert result.reject_reason in {{
        ResolutionRejectReason.OUT_OF_SCOPE.value,
        ResolutionRejectReason.BLOCKED_CONTEXT.value,
    }}, f"Expected out_of_scope or blocked_context, got {{result.reject_reason}}"
'''
        with open(test_file, "a", encoding="utf-8") as f:
            f.write(snippet)
        return f"generated {test_name}"

    return f"no test generated for action_type={action_type}"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _proposal_item(row: dict[str, Any]) -> ProposalItem:
    created = row.get("created_at")
    reviewed = row.get("reviewed_at")
    return ProposalItem(
        id=row.get("id", 0),
        label_key=row.get("label_key", ""),
        action_type=row.get("action_type", ""),
        proposal_data=row.get("proposal_data") or {},
        evidence_summary=row.get("evidence_summary", ""),
        proposal_status=row.get("proposal_status", "pending"),
        reviewer_note=row.get("reviewer_note", ""),
        reviewed_by=row.get("reviewed_by", ""),
        reviewed_at=reviewed.isoformat() if hasattr(reviewed, "isoformat") else str(reviewed or ""),
        created_at=created.isoformat() if hasattr(created, "isoformat") else str(created or ""),
    )
