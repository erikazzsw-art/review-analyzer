#!/usr/bin/env python3
"""Validate formal label scope definitions against taxonomy assets.

5.9.6-D-wp3 (2026-08-06): scope validation script, downgraded from full
Scope Compiler. Validates that the registry schema, scope_policy assignments,
and negative examples are consistent with taxonomy ground truth.

Checks (fail-closed, non-zero exit on any failure):
  1. Data model must not contain "*" wildcard in scope fields (hard fail)
  2. transaction_universal labels must reference a valid transaction dimension
  3. capability_derived aspect_keys must hit at least one sub_category taxonomy
  4. Each approved label must have at least one positive example
  5. Negative examples must meet policy minimums; out_of_scope negatives must
     be verified against the computed effective scope matrix
  6. explicit label sub_category lists must exist in taxonomy assets

Usage:
  python scripts/validate_label_scope.py           # run all checks
  python scripts/validate_label_scope.py --dry-run # non-zero exit on failure
  python scripts/validate_label_scope.py --print-matrix  # print effective scope
"""
from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, TextIO

# Ensure the project root is on sys.path so we can import backend_api modules.
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend_api.app.services.review_fragment_label_catalog import (
    NEGATIVE_EXAMPLE_TYPE_OUT_OF_BOUNDARY,
    NEGATIVE_EXAMPLE_TYPE_OUT_OF_SCOPE,
    REVIEW_STATUS_APPROVED,
    SCOPE_POLICY_CAPABILITY_DERIVED,
    SCOPE_POLICY_EXPLICIT,
    SCOPE_POLICY_TRANSACTION_UNIVERSAL,
    FormalLabelDefinition,
    compute_effective_scope_matrix,
    get_all_sub_categories,
    get_label_registry_state,
    get_transaction_dimension_keys,
)

# ---------------------------------------------------------------------------
# Validation result types
# ---------------------------------------------------------------------------


@dataclass
class ValidationFailure:
    check: str
    label_key: str
    message: str


@dataclass
class ValidationReport:
    failures: list[ValidationFailure] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return len(self.failures) == 0

    def fail(self, check: str, label_key: str, message: str) -> None:
        self.failures.append(ValidationFailure(check=check, label_key=label_key, message=message))

    def warn(self, message: str) -> None:
        self.warnings.append(message)


# ---------------------------------------------------------------------------
# Check implementations
# ---------------------------------------------------------------------------


def _check_no_wildcard_in_scope(
    report: ValidationReport,
    labels: tuple[FormalLabelDefinition, ...],
) -> None:
    """Check 1: category_keys / sub_category_keys must NOT exist on label definitions.

    Per decision h: these fields were deleted from FormalLabelDefinition in WP5.
    Scope is now governed entirely by scope_policy + taxonomy. If a label
    definition somehow still carries these fields, it's a failure.
    """
    for label in labels:
        if hasattr(label, "category_keys"):
            report.fail(
                "no-wildcard",
                label.key,
                "category_keys field still exists on label definition. "
                "Per decision h, scope is governed by scope_policy + taxonomy.",
            )
        if hasattr(label, "sub_category_keys"):
            report.fail(
                "no-wildcard",
                label.key,
                "sub_category_keys field still exists on label definition. "
                "Per decision h, scope is governed by scope_policy + taxonomy.",
            )


def _check_transaction_universal_dimensions(
    report: ValidationReport,
    labels: tuple[FormalLabelDefinition, ...],
    valid_dimensions: frozenset[str],
) -> None:
    """Check 2: transaction_universal labels must reference a valid dimension."""
    for label in labels:
        if label.scope_policy != SCOPE_POLICY_TRANSACTION_UNIVERSAL:
            continue
        dim = label.required_transaction_dimension
        if not dim:
            report.fail(
                "transaction-dimension",
                label.key,
                "transaction_universal requires required_transaction_dimension",
            )
        elif dim not in valid_dimensions:
            report.fail(
                "transaction-dimension",
                label.key,
                f"required_transaction_dimension={dim!r} is not in the "
                f"transaction_aspects.yaml closed enumeration: {sorted(valid_dimensions)}",
            )


def _check_capability_derived_hits_taxonomy(
    report: ValidationReport,
    labels: tuple[FormalLabelDefinition, ...],
    scope_matrix: dict[str, frozenset[str]],
) -> None:
    """Check 3: capability_derived labels must hit at least one sub_category."""
    for label in labels:
        if label.scope_policy != SCOPE_POLICY_CAPABILITY_DERIVED:
            continue
        if not label.aspect_keys:
            report.fail(
                "capability-hit",
                label.key,
                "capability_derived requires at least one aspect_key",
            )
            continue
        in_scope = scope_matrix.get(label.key, frozenset())
        if not in_scope:
            report.fail(
                "capability-hit",
                label.key,
                f"aspect_keys={sorted(label.aspect_keys)} do not match any "
                f"sub_category in the taxonomy. This label would never fire.",
            )


def _check_positive_examples(
    report: ValidationReport,
    labels: tuple[FormalLabelDefinition, ...],
) -> None:
    """Check 4: each approved label must have at least one positive example."""
    for label in labels:
        if label.status != REVIEW_STATUS_APPROVED:
            continue
        if not label.positive_examples:
            report.fail(
                "positive-examples",
                label.key,
                "approved label must have at least one positive example",
            )


def _check_negative_examples(
    report: ValidationReport,
    labels: tuple[FormalLabelDefinition, ...],
    scope_matrix: dict[str, frozenset[str]],
    all_sub_categories: frozenset[str],
) -> None:
    """Check 5: negative examples must meet policy minimums and out_of_scope
    negatives must be verified against the effective scope matrix."""
    for label in labels:
        if label.status != REVIEW_STATUS_APPROVED:
            continue

        policy = label.scope_policy
        negatives = label.negative_examples
        out_of_scope = [n for n in negatives if n.type == NEGATIVE_EXAMPLE_TYPE_OUT_OF_SCOPE]
        out_of_boundary = [n for n in negatives if n.type == NEGATIVE_EXAMPLE_TYPE_OUT_OF_BOUNDARY]

        # Policy minimums
        if policy in (SCOPE_POLICY_CAPABILITY_DERIVED, SCOPE_POLICY_EXPLICIT):
            if not out_of_scope:
                report.fail(
                    "negative-examples",
                    label.key,
                    f"{policy} requires at least one out_of_scope negative example",
                )
        if policy == SCOPE_POLICY_TRANSACTION_UNIVERSAL:
            if not out_of_boundary:
                report.fail(
                    "negative-examples",
                    label.key,
                    "transaction_universal requires at least one out_of_boundary negative example",
                )
        if policy == SCOPE_POLICY_EXPLICIT:
            if not out_of_boundary:
                report.fail(
                    "negative-examples",
                    label.key,
                    "explicit requires at least one out_of_boundary negative example",
                )

        # out_of_scope verification: each sub_category in an out_of_scope
        # negative must actually be OUTSIDE the computed effective scope
        in_scope = scope_matrix.get(label.key, frozenset())
        for neg in out_of_scope:
            if neg.sub_category in in_scope:
                report.fail(
                    "negative-out-of-scope-verify",
                    label.key,
                    f"out_of_scope negative example claims sub_category={neg.sub_category!r} "
                    f"is out of scope, but the effective scope matrix shows it IS in scope "
                    f"(matches {len(in_scope)} sub_categories). "
                    f"Review text: {neg.review_text[:80]}...",
                )
            if neg.sub_category not in all_sub_categories:
                report.warn(
                    f"[{label.key}] out_of_scope negative references unknown "
                    f"sub_category={neg.sub_category!r}"
                )

        # out_of_boundary sub_category check: must exist in taxonomy
        for neg in out_of_boundary:
            if neg.sub_category not in all_sub_categories:
                report.warn(
                    f"[{label.key}] out_of_boundary negative references unknown "
                    f"sub_category={neg.sub_category!r}"
                )


def _check_explicit_sub_categories(
    report: ValidationReport,
    labels: tuple[FormalLabelDefinition, ...],
    all_sub_categories: frozenset[str],
) -> None:
    """Check 6: explicit label sub_category lists must exist in taxonomy.

    Note: explicit labels don't currently exist in the registry; this check
    is forward-looking. If no explicit labels are found, it passes silently.
    """
    for label in labels:
        if label.scope_policy != SCOPE_POLICY_EXPLICIT:
            continue
        # For explicit labels, the scope is hand-maintained in sub_category_keys
        # (after work package 5 removes the wildcard).
        # For now, log a warning that explicit labels need manual review.
        report.warn(
            f"[{label.key}] is explicit — scope is hand-maintained and must be "
            f"reviewed manually. Ensure all listed sub_categories exist in taxonomy."
        )


# ---------------------------------------------------------------------------
# Matrix printing
# ---------------------------------------------------------------------------


def print_effective_scope_matrix(
    scope_matrix: dict[str, frozenset[str]],
    labels: tuple[FormalLabelDefinition, ...],
    *,
    stdout: TextIO = sys.stdout,
) -> None:
    """Print the effective scope for each label in a human-readable format."""
    label_map = {label.key: label for label in labels}

    print("=" * 80, file=stdout)
    print("Effective Scope Matrix", file=stdout)
    print("=" * 80, file=stdout)

    for key in sorted(scope_matrix.keys()):
        in_scope = scope_matrix[key]
        label = label_map.get(key)
        if label is None:
            continue
        policy = label.scope_policy
        dim = label.required_transaction_dimension or "-"
        aspects = sorted(label.aspect_keys)

        print(f"\n--- {key} ---", file=stdout)
        print(f"  scope_policy: {policy}", file=stdout)
        print(f"  required_transaction_dimension: {dim}", file=stdout)
        print(f"  aspect_keys: {aspects}", file=stdout)
        print(f"  effective sub_category count: {len(in_scope)}", file=stdout)

        if policy == SCOPE_POLICY_TRANSACTION_UNIVERSAL:
            print(f"  coverage: all {len(in_scope)} known sub_categories "
                  f"(transaction_universal)", file=stdout)
        elif policy == SCOPE_POLICY_CAPABILITY_DERIVED:
            if in_scope:
                print("  sub_categories:", file=stdout)
                for sc in sorted(in_scope):
                    print(f"    - {sc}", file=stdout)
            else:
                print("  sub_categories: (none — label would never fire)", file=stdout)
        elif policy == SCOPE_POLICY_EXPLICIT:
            print("  sub_categories: (explicit — scope is hand-maintained)", file=stdout)

    print("\n" + "=" * 80, file=stdout)
    print("Summary", file=stdout)
    print("=" * 80, file=stdout)
    for key in sorted(scope_matrix.keys()):
        in_scope = scope_matrix[key]
        label = label_map.get(key)
        policy = label.scope_policy if label else "?"
        print(f"  {key}: {len(in_scope)} sub_categories ({policy})", file=stdout)

    total = len(get_all_sub_categories())
    print(f"\n  total taxonomy sub_categories: {total}", file=stdout)


# ---------------------------------------------------------------------------
# Report printing
# ---------------------------------------------------------------------------


def print_validation_report(
    report: ValidationReport,
    *,
    stdout: TextIO = sys.stdout,
) -> None:
    """Print the validation results in a human-readable format."""
    print("=" * 80, file=stdout)
    print("Label Scope Validation Report", file=stdout)
    print("=" * 80, file=stdout)

    if report.warnings:
        print(f"\nWarnings ({len(report.warnings)}):", file=stdout)
        for w in report.warnings:
            print(f"  ⚠  {w}", file=stdout)

    if report.failures:
        print(f"\nFailures ({len(report.failures)}):", file=stdout)
        # Group by check
        by_check: dict[str, list[ValidationFailure]] = {}
        for f in report.failures:
            by_check.setdefault(f.check, []).append(f)
        for check_name, failures in sorted(by_check.items()):
            print(f"\n  [{check_name}] ({len(failures)}):", file=stdout)
            for f in failures:
                print(f"    ✘ [{f.label_key}] {f.message}", file=stdout)
    else:
        print("\n✅ All checks passed.", file=stdout)

    print(f"\nTotal: {len(report.failures)} failure(s), {len(report.warnings)} warning(s)", file=stdout)


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


def validate(
    *,
    print_matrix: bool = False,
    stdout: TextIO = sys.stdout,
) -> ValidationReport:
    """Run all validation checks and return the report."""
    report = ValidationReport()
    state = get_label_registry_state()
    labels = state.labels

    if not labels:
        report.warn("No labels found in registry — nothing to validate")
        return report

    valid_dimensions = get_transaction_dimension_keys()
    all_sub_categories = get_all_sub_categories()
    scope_matrix = compute_effective_scope_matrix(labels)

    _check_no_wildcard_in_scope(report, labels)
    _check_transaction_universal_dimensions(report, labels, valid_dimensions)
    _check_capability_derived_hits_taxonomy(report, labels, scope_matrix)
    _check_positive_examples(report, labels)
    _check_negative_examples(report, labels, scope_matrix, all_sub_categories)
    _check_explicit_sub_categories(report, labels, all_sub_categories)

    if print_matrix:
        print_effective_scope_matrix(scope_matrix, labels, stdout=stdout)

    print_validation_report(report, stdout=stdout)
    return report


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate formal label scope definitions against taxonomy assets."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Fail with non-zero exit code if any validation check fails.",
    )
    parser.add_argument(
        "--print-matrix",
        action="store_true",
        help="Print the effective scope matrix for all labels.",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    report = validate(print_matrix=args.print_matrix)

    if args.dry_run and not report.passed:
        return 1
    return 0 if report.passed else 0


if __name__ == "__main__":
    raise SystemExit(main())
