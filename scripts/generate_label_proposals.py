#!/usr/bin/env python3
"""Generate label registry proposals from audit events.

5.9.6-D repair batch 1b (Bug 5b): reads label_registry_audit_events, aggregates
by (label_key, sub_category, reject_reason), and prints candidate proposals for
human review. Only persists to label_registry_proposals when --write is passed.

Deliberately NOT automatic: automatic generation would need a threshold for
"frequent enough", and notes/scope-governance-dod.md §1 has already rejected
thresholds ("阈值会让 scope 随 taxonomy 增长悄悄漂移，是比 ["*"] 更隐蔽的同类故障").
The initial review budget is 2 hours/week — auto-populating the candidate pool
would overflow it immediately.

Usage:
  python3 scripts/generate_label_proposals.py          # dry run, print candidates
  python3 scripts/generate_label_proposals.py --write  # persist to DB
  python3 scripts/generate_label_proposals.py --min-occurrences 5  # filter
  python3 scripts/generate_label_proposals.py --label-key water_leaks_through
"""
from __future__ import annotations

import argparse
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend_api.app.services.label_registry_audit import (
    AUDIT_EVENT_RESOLVER_REJECT,
    AUDIT_EVENT_SHADOW_DIFF,
    query_audit_events,
)
from backend_api.app.services.label_registry_proposal import (
    PROPOSAL_ACTION_SCOPE_ADJUST,
    RegistryProposal,
    create_proposal,
)
from review_analyzer.database import get_connection


def fetch_events(
    *,
    label_key: str | None = None,
    event_types: tuple[str, ...] = (AUDIT_EVENT_RESOLVER_REJECT, AUDIT_EVENT_SHADOW_DIFF),
    limit: int = 10000,
) -> list[dict]:
    """Fetch audit events with optional filters."""
    all_events: list[dict] = []
    for event_type in event_types:
        offset = 0
        while True:
            batch = query_audit_events(
                label_key=label_key,
                event_type=event_type,
                limit=1000,
                offset=offset,
            )
            if not batch:
                break
            all_events.extend(batch)
            if len(batch) < 1000:
                break
            offset += 1000
    return all_events


def aggregate(
    events: list[dict],
    *,
    min_occurrences: int = 1,
) -> list[dict]:
    """Aggregate events by (label_key, sub_category, reject_reason).

    Returns a list of aggregation dicts sorted by occurrence count descending.
    """
    buckets: dict[tuple[str, str, str], list[dict]] = defaultdict(list)
    for e in events:
        key = (
            str(e.get("label_key", "")),
            str(e.get("sub_category", "")),
            str(e.get("reject_reason", "")),
        )
        buckets[key].append(e)

    result: list[dict] = []
    for (label_key, sub_category, reject_reason), items in buckets.items():
        if len(items) < min_occurrences:
            continue
        result.append({
            "label_key": label_key,
            "sub_category": sub_category,
            "reject_reason": reject_reason,
            "occurrences": len(items),
            "sample_event_ids": [e.get("id") for e in items[:5]],
            "categories": sorted({str(e.get("category", "")) for e in items if e.get("category")}),
        })
    result.sort(key=lambda x: x["occurrences"], reverse=True)
    return result


def print_candidates(aggregated: list[dict]) -> None:
    """Print aggregated candidate proposals for human review."""
    if not aggregated:
        print("No candidates found.")
        return

    print(f"\n{'=' * 80}")
    print(f"Candidate Proposals ({len(aggregated)} groups)")
    print(f"{'=' * 80}")

    for i, agg in enumerate(aggregated, 1):
        print(f"\n--- Candidate {i} ---")
        print(f"  label_key:      {agg['label_key']}")
        print(f"  sub_category:   {agg['sub_category']}")
        print(f"  reject_reason:  {agg['reject_reason']}")
        print(f"  occurrences:    {agg['occurrences']}")
        print(f"  categories:     {', '.join(agg['categories'][:10])}")
        suggested_action = _suggest_action(agg["reject_reason"])
        print(f"  suggested_action: {suggested_action}")

    print(f"\n{'=' * 80}")
    print(
        "Run with --write to persist these as scope_adjust proposals "
        "in label_registry_proposals."
    )
    print(f"{'=' * 80}\n")


def _suggest_action(reject_reason: str) -> str:
    """Suggest a proposal action type based on the reject reason."""
    if reject_reason in ("scope_unavailable",):
        return PROPOSAL_ACTION_SCOPE_ADJUST
    if reject_reason in ("out_of_scope",):
        return PROPOSAL_ACTION_SCOPE_ADJUST
    if reject_reason in ("blocked_context",):
        return "blocked_rule"
    return PROPOSAL_ACTION_SCOPE_ADJUST


def persist_candidates(
    aggregated: list[dict],
    *,
    dry_run: bool = True,
) -> int:
    """Persist aggregated candidates as scope_adjust proposals.

    Returns the number of proposals created.
    """
    created = 0
    for agg in aggregated:
        proposal = RegistryProposal(
            label_key=agg["label_key"],
            action_type=_suggest_action(agg["reject_reason"]),
            proposal_data={
                "scope_policy": "capability_derived",
                "reason": (
                    f"Auto-generated from audit: {agg['occurrences']} occurrences "
                    f"of reject_reason={agg['reject_reason']} on "
                    f"sub_category={agg['sub_category']}. "
                    f"Human review required before applying."
                ),
            },
            evidence_summary=(
                f"{agg['occurrences']} occurrences across "
                f"{len(agg['categories'])} categories. "
                f"Sample event IDs: {agg['sample_event_ids'][:3]}"
            ),
        )
        if dry_run:
            print(
                f"  [DRY RUN] Would create proposal: "
                f"label={proposal.label_key} action={proposal.action_type}"
            )
            created += 1
        else:
            row_id = create_proposal(proposal)
            if row_id is not None:
                created += 1
                print(f"  Created proposal id={row_id}: {proposal.label_key}")
            else:
                print(f"  FAILED to create proposal: {proposal.label_key}")
    return created


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate label registry proposals from audit events."
    )
    parser.add_argument(
        "--write",
        action="store_true",
        help="Persist proposals to label_registry_proposals (default: dry run).",
    )
    parser.add_argument(
        "--min-occurrences",
        type=int,
        default=1,
        help="Minimum occurrences to generate a proposal (default: 1).",
    )
    parser.add_argument(
        "--label-key",
        type=str,
        default=None,
        help="Filter audit events to a single label key.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)

    print("Fetching audit events...")
    events = fetch_events(label_key=args.label_key)
    print(f"  Fetched {len(events)} events")

    aggregated = aggregate(events, min_occurrences=args.min_occurrences)
    print_candidates(aggregated)

    if args.write:
        print(f"Persisting {len(aggregated)} candidates...")
        created = persist_candidates(aggregated, dry_run=False)
        print(f"Created {created} proposals.")
    else:
        created = persist_candidates(aggregated, dry_run=True)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
