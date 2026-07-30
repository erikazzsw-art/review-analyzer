from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from backend_api.app.services.customer_label_catalog import (
    CustomerLabelCatalogState,
    set_customer_label_catalog_state_for_tests,
)
from backend_api.app.services.customer_label_v2_candidate_pool import (
    build_candidate_pool_artifact,
    write_candidate_pool_csv,
    write_candidate_pool_json_artifact,
)
from backend_api.app.services.customer_label_v2_shadow import (
    FOCUS_WADERS_LABELS,
    compare_customer_label_v2_shadow,
    display_keys_from_shadow,
    run_customer_label_v2_shadow,
    v1_display_keys_for_review,
)

ROOT = Path(__file__).resolve().parents[1]
FIXTURES_DIR = ROOT / "backend_api" / "tests" / "fixtures"
SESSION120_GOLD = FIXTURES_DIR / "customer_label_waders_session120_human_gold.json"
SESSION121_FIXTURE = FIXTURES_DIR / "customer_label_waders_session121_blind_regression.json"
SESSION122_RESULTS = ROOT / "tmp" / "5.9.8-step4-tidewe-waders-prod-20260729" / "session122-readonly" / "session-results.json"
SESSION122_ACCEPTANCE = (
    ROOT / "tmp" / "5.9.8-step4-tidewe-waders-prod-20260729" / "session122-readonly" / "acceptance-summary.json"
)
POSTDEPLOY_AUDIT = (
    ROOT
    / "tmp"
    / "5.9.8-step4-tidewe-waders-prod-20260729"
    / "session122-readonly"
    / "session122-postdeploy-readonly-acceptance-audit.json"
)
ARTIFACT_DIR = ROOT / "tmp" / "5.9.9-step4-candidate-pool-mvp"
ARTIFACT_PATH = ARTIFACT_DIR / "waders-shadow-summary.json"
CANDIDATE_POOL_ARTIFACT_PATH = ARTIFACT_DIR / "candidate-pool.json"
CANDIDATE_POOL_CSV_PATH = ARTIFACT_DIR / "candidate-pool.csv"


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _review_from_sample(sample: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": sample["id"],
        "content": sample["content"],
        "rating": sample.get("rating") or 3,
        "category": "outdoor",
        "sub_category": "waders",
    }


def _expected_from_review(review: dict[str, Any]) -> dict[str, list[str]]:
    return {
        "issue": list(review.get("_expected_issue_keys") or []),
        "highlight": list(review.get("_expected_highlight_keys") or []),
    }


def _blocked_from_review(review: dict[str, Any]) -> dict[str, list[str]]:
    return {
        "issue": list(review.get("_blocked_issue_keys") or []),
        "highlight": list(review.get("_blocked_highlight_keys") or []),
    }


def _session120_reviews() -> list[dict[str, Any]]:
    payload = _load_json(SESSION120_GOLD)
    reviews: list[dict[str, Any]] = []
    for sample in payload["samples"]:
        review = _review_from_sample(sample)
        review["_expected_issue_keys"] = sample["human_issue_keys"]
        review["_expected_highlight_keys"] = sample["human_highlight_keys"]
        review["_blocked_issue_keys"] = sample.get("blocked_issue_keys", [])
        review["_blocked_highlight_keys"] = sample.get("blocked_highlight_keys", [])
        reviews.append(review)
    return reviews


def _session121_reviews() -> list[dict[str, Any]]:
    payload = _load_json(SESSION121_FIXTURE)
    reviews: list[dict[str, Any]] = []
    for sample in payload["samples"]:
        review = _review_from_sample(sample)
        expected = v1_display_keys_for_review(review)
        review["_expected_issue_keys"] = expected["issue"]
        review["_expected_highlight_keys"] = expected["highlight"]
        review["_required_issue_keys"] = sample["required_issue_keys"]
        review["_required_highlight_keys"] = sample["required_highlight_keys"]
        review["_blocked_issue_keys"] = sample["blocked_issue_keys"]
        review["_blocked_highlight_keys"] = sample["blocked_highlight_keys"]
        reviews.append(review)
    return reviews


def _session122_reviews() -> list[dict[str, Any]]:
    results = _load_json(SESSION122_RESULTS)
    acceptance = _load_json(SESSION122_ACCEPTANCE)
    acceptance_rows = acceptance["validation"]["rows"]
    reviews: list[dict[str, Any]] = []
    for index, comment in enumerate(results["comments"]):
        row = acceptance_rows[index]
        review = dict(comment)
        review["category"] = "outdoor"
        review["sub_category"] = "waders"
        review["_expected_issue_keys"] = row["issue_keys"]
        review["_expected_highlight_keys"] = row["highlight_keys"]
        review["_blocked_issue_keys"] = []
        review["_blocked_highlight_keys"] = []
        reviews.append(review)
    return reviews


def _required_boundary_summary(reviews: list[dict[str, Any]]) -> dict[str, Any]:
    violations: list[dict[str, Any]] = []
    for review in reviews:
        actual = display_keys_from_shadow(run_customer_label_v2_shadow(review))
        for label_type in ("issue", "highlight"):
            required = set(review.get(f"_required_{label_type}_keys") or [])
            blocked = set(review.get(f"_blocked_{label_type}_keys") or [])
            missing = sorted(required - set(actual[label_type]))
            leaked = sorted(blocked & set(actual[label_type]))
            if missing or leaked:
                violations.append(
                    {
                        "review_id": review["id"],
                        "label_type": label_type,
                        "missing_required": missing,
                        "blocked_displayed": leaked,
                    }
                )
    return {
        "checked_reviews": len(reviews),
        "violations": violations,
        "status": "PASS" if not violations else "REVIEW_NEEDED",
    }


def _candidate(
    *,
    label_type: str,
    canonical: str,
    evidence: str,
    aspect_key: str,
    raw_label: str | None = None,
    confidence: float = 0.9,
) -> dict[str, Any]:
    display = raw_label or " ".join(part.capitalize() for part in canonical.replace("candidate:", "").split("_"))
    return {
        "label_type": label_type,
        "canonical_label_key": canonical,
        "raw_label": display,
        "display_label_en": display,
        "display_label_zh": display,
        "aspect_key": aspect_key,
        "polarity": "negative" if label_type == "issue" else "positive",
        "evidence_candidate": evidence,
        "confidence": confidence,
        "reason": "shadow edge-case fixture",
    }


def _edge_case_runs() -> tuple[dict[str, Any], list[dict[str, Any]]]:
    cases = {
        "invalid_json": run_customer_label_v2_shadow(
            {"id": "edge-invalid-json", "content": "No leaks.", "category": "outdoor", "sub_category": "waders"},
            llm_output="{not json",
        ),
        "evidence_missing": run_customer_label_v2_shadow(
            {"id": "edge-evidence-missing", "content": "They do not keep you dry.", "category": "outdoor", "sub_category": "waders"},
            label_candidates=[
                _candidate(
                    label_type="issue",
                    canonical="water_leaks_through",
                    evidence="",
                    aspect_key="waterproof",
                )
            ],
        ),
        "evidence_not_found": run_customer_label_v2_shadow(
            {"id": "edge-evidence-not-found", "content": "They do not keep you dry.", "category": "outdoor", "sub_category": "waders"},
            label_candidates=[
                _candidate(
                    label_type="issue",
                    canonical="water_leaks_through",
                    evidence="leaked through the seams",
                    aspect_key="waterproof",
                )
            ],
        ),
        "confidence_low": run_customer_label_v2_shadow(
            {"id": "edge-confidence-low", "content": "They do not keep you dry.", "category": "outdoor", "sub_category": "waders"},
            label_candidates=[
                _candidate(
                    label_type="issue",
                    canonical="water_leaks_through",
                    evidence="do not keep you dry",
                    aspect_key="waterproof",
                    confidence=0.4,
                )
            ],
        ),
        "schema_invalid": run_customer_label_v2_shadow(
            {"id": "edge-schema-invalid", "content": "They do not keep you dry.", "category": "outdoor", "sub_category": "waders"},
            label_candidates=[
                {
                    "label_type": "issue",
                    "canonical_label_key": "water_leaks_through",
                    "raw_label": "",
                    "aspect_key": "waterproof",
                    "polarity": "negative",
                    "evidence_candidate": "do not keep you dry",
                    "confidence": 0.9,
                    "reason": "shadow edge-case fixture",
                }
            ],
        ),
        "unknown_label": run_customer_label_v2_shadow(
            {"id": "edge-unknown-label", "content": "The boot seam leaked on the first trip.", "category": "outdoor", "sub_category": "waders"},
            label_candidates=[
                _candidate(
                    label_type="issue",
                    canonical="candidate:boot_seam_leak",
                    evidence="boot seam leaked",
                    aspect_key="seam_integrity",
                )
            ],
        ),
        "maturity_blocked": run_customer_label_v2_shadow(
            {"id": "edge-maturity-blocked", "content": "They do not keep you dry.", "category": "outdoor", "sub_category": "waders"},
            maturity_level="L0_unknown",
            label_candidates=[
                _candidate(
                    label_type="issue",
                    canonical="water_leaks_through",
                    evidence="do not keep you dry",
                    aspect_key="waterproof",
                )
            ],
        ),
        "aspect_blocked": run_customer_label_v2_shadow(
            {"id": "edge-aspect-blocked", "content": "They do not keep you dry.", "category": "outdoor", "sub_category": "waders"},
            label_candidates=[
                _candidate(
                    label_type="issue",
                    canonical="water_leaks_through",
                    evidence="do not keep you dry",
                    aspect_key="value_for_money",
                )
            ],
        ),
        "old_product_leak": run_customer_label_v2_shadow(
            {
                "id": "edge-old-product",
                "content": (
                    "Bought as a gift for my boyfriend who has had numerous pairs of waders in the past that have "
                    "leaked. These were affordable and have not caused him any issues."
                ),
                "category": "outdoor",
                "sub_category": "waders",
            },
            label_candidates=[
                _candidate(
                    label_type="issue",
                    canonical="water_leaks_through",
                    evidence="leaked",
                    aspect_key="waterproof",
                )
            ],
        ),
        "accessory_phone_case_leak": run_customer_label_v2_shadow(
            {
                "id": "edge-phone-case",
                "content": (
                    "The waders are fine. However, the waterproof phone case is not at all what it shows as. "
                    "It is not waterproof; water leaks in very easily."
                ),
                "category": "outdoor",
                "sub_category": "waders",
            },
            label_candidates=[
                _candidate(
                    label_type="issue",
                    canonical="water_leaks_through",
                    evidence="It is not waterproof",
                    aspect_key="waterproof",
                ),
                _candidate(
                    label_type="issue",
                    canonical="pocket_not_waterproof",
                    evidence="the waterproof phone case is not at all what it shows as",
                    aspect_key="accessory_storage",
                ),
            ],
        ),
        "positive_no_leaks_issue_candidate": run_customer_label_v2_shadow(
            {
                "id": "edge-positive-no-leaks",
                "content": "I wore these in cold water for hours. No leaks and they kept me dry.",
                "category": "outdoor",
                "sub_category": "waders",
            },
            label_candidates=[
                _candidate(
                    label_type="issue",
                    canonical="water_leaks_through",
                    evidence="No leaks",
                    aspect_key="waterproof",
                ),
                _candidate(
                    label_type="highlight",
                    canonical="keeps_water_out",
                    evidence="No leaks",
                    aspect_key="waterproof",
                ),
            ],
        ),
        "negative_do_not_keep_dry_highlight_candidate": run_customer_label_v2_shadow(
            {
                "id": "edge-negative-do-not-keep-dry",
                "content": "They do not keep you dry.",
                "category": "outdoor",
                "sub_category": "waders",
            },
            label_candidates=[
                _candidate(
                    label_type="issue",
                    canonical="water_leaks_through",
                    evidence="do not keep you dry",
                    aspect_key="waterproof",
                ),
                _candidate(
                    label_type="highlight",
                    canonical="keeps_water_out",
                    evidence="keep you dry",
                    aspect_key="waterproof",
                ),
            ],
        ),
        "generic_four_pack": run_customer_label_v2_shadow(
            {"id": "edge-generic-four-pack", "content": "Great product.", "category": "outdoor", "sub_category": "waders"},
            label_candidates=[
                _candidate(label_type="highlight", canonical="fits_as_expected", evidence="Great product", aspect_key="size_fit"),
                _candidate(
                    label_type="highlight",
                    canonical="good_value_for_the_price",
                    evidence="Great product",
                    aspect_key="value_for_money",
                ),
                _candidate(label_type="highlight", canonical="holds_up_well", evidence="Great product", aspect_key="durability"),
                _candidate(label_type="highlight", canonical="keeps_water_out", evidence="Great product", aspect_key="waterproof"),
            ],
        ),
        "cluster_propagated_audit_only": run_customer_label_v2_shadow(
            {"id": "edge-cluster-propagated", "content": "They do not keep you dry.", "category": "outdoor", "sub_category": "waders"},
            label_candidates=[
                {
                    **_candidate(
                        label_type="issue",
                        canonical="water_leaks_through",
                        evidence="do not keep you dry",
                        aspect_key="waterproof",
                    ),
                    "cluster_propagated": True,
                }
            ],
        ),
        "valid_display_occurrence": run_customer_label_v2_shadow(
            {"id": "edge-valid-display", "content": "They do not keep you dry.", "category": "outdoor", "sub_category": "waders"},
            label_candidates=[
                _candidate(
                    label_type="issue",
                    canonical="water_leaks_through",
                    evidence="do not keep you dry",
                    aspect_key="waterproof",
                )
            ],
        ),
    }
    reason_counts: Counter[str] = Counter()
    display_violations: list[dict[str, Any]] = []
    candidate_pool_case_names: list[str] = []
    candidate_pool_raw_count = 0
    for name, result in cases.items():
        for audit in result["audit_occurrences"]:
            for reason in audit.get("downgrade_reasons") or []:
                reason_counts[str(reason)] += 1
        if result.get("candidate_pool_items"):
            candidate_pool_case_names.append(name)
            candidate_pool_raw_count += len(result["candidate_pool_items"])
        if name in {
            "invalid_json",
            "evidence_missing",
            "evidence_not_found",
            "confidence_low",
            "schema_invalid",
            "unknown_label",
            "maturity_blocked",
            "aspect_blocked",
            "old_product_leak",
            "generic_four_pack",
            "cluster_propagated_audit_only",
        }:
            if result["display_occurrences"]:
                display_violations.append({"case": name, "display_occurrences": result["display_occurrences"]})
        if name == "valid_display_occurrence" and not result["display_occurrences"]:
            display_violations.append({"case": name, "display_occurrences": []})
    return {
        "case_count": len(cases),
        "downgrade_reasons": dict(sorted(reason_counts.items())),
        "display_violations": display_violations,
        "candidate_pool_case_names": sorted(candidate_pool_case_names),
        "candidate_pool_raw_count": candidate_pool_raw_count,
        "status": "PASS" if not display_violations else "REVIEW_NEEDED",
    }, list(cases.values())


def _add_precision_recall(dataset: dict[str, Any]) -> dict[str, Any]:
    totals = dataset["tp_fp_fn"]
    tp = totals["issue"]["tp"] + totals["highlight"]["tp"]
    fp = totals["issue"]["fp"] + totals["highlight"]["fp"]
    fn = totals["issue"]["fn"] + totals["highlight"]["fn"]
    dataset["display_candidate_precision"] = round(tp / (tp + fp), 4) if tp + fp else 1.0
    dataset["display_candidate_recall"] = round(tp / (tp + fn), 4) if tp + fn else 1.0
    return dataset


def _aggregate_focus_metrics(datasets: list[dict[str, Any]]) -> dict[str, dict[str, int]]:
    merged: dict[str, Counter[str]] = defaultdict(Counter)
    for dataset in datasets:
        for key, metrics in dataset["focus_label_metrics"].items():
            for metric, value in metrics.items():
                merged[key][metric] += int(value)
    for label_type, canonical in FOCUS_WADERS_LABELS:
        merged.setdefault(f"{label_type}:{canonical}", Counter())
    return {key: dict(value) for key, value in sorted(merged.items())}


def _aggregate_downgrades(datasets: list[dict[str, Any]], edge_cases: dict[str, Any]) -> dict[str, int]:
    merged: Counter[str] = Counter(edge_cases["downgrade_reasons"])
    for dataset in datasets:
        merged.update(dataset["downgrade_reasons"])
    return dict(sorted(merged.items()))


def main() -> None:
    set_customer_label_catalog_state_for_tests(CustomerLabelCatalogState())
    try:
        session120 = _add_precision_recall(
            compare_customer_label_v2_shadow(
                _session120_reviews(),
                _expected_from_review,
                dataset_name="session120_human_gold",
                blocked_keys=_blocked_from_review,
            )
        )
        session121_reviews = _session121_reviews()
        session121 = _add_precision_recall(
            compare_customer_label_v2_shadow(
                session121_reviews,
                _expected_from_review,
                dataset_name="session121_blind_boundary_fixture_vs_v1_display",
                blocked_keys=_blocked_from_review,
            )
        )
        session122 = _add_precision_recall(
            compare_customer_label_v2_shadow(
                _session122_reviews(),
                _expected_from_review,
                dataset_name="session122_postdeploy_acceptance_summary",
                blocked_keys=_blocked_from_review,
            )
        )
        edge_cases, edge_case_shadow_results = _edge_case_runs()
        datasets = [session120, session121, session122]
        focus_metrics = _aggregate_focus_metrics(datasets)
        p0_violations = [
            violation
            for dataset in datasets
            for violation in dataset["blocked_violations"]
        ]
        for key, metrics in focus_metrics.items():
            if int(metrics.get("fp") or 0) or int(metrics.get("fn") or 0):
                p0_violations.append({"label": key, "metrics": metrics})
        postdeploy = _load_json(POSTDEPLOY_AUDIT) if POSTDEPLOY_AUDIT.exists() else {}
        candidate_pool_artifact = build_candidate_pool_artifact(
            edge_case_shadow_results,
            scope="5.9.9 Step 4 candidate pool MVP local waders shadow replay",
            source_artifacts=[
                str(SESSION120_GOLD.relative_to(ROOT)),
                str(SESSION121_FIXTURE.relative_to(ROOT)),
                str(SESSION122_RESULTS.relative_to(ROOT)),
                str(SESSION122_ACCEPTANCE.relative_to(ROOT)),
            ],
        )
        candidate_pool_json_path = write_candidate_pool_json_artifact(
            CANDIDATE_POOL_ARTIFACT_PATH,
            candidate_pool_artifact,
        )
        candidate_pool_csv_path = write_candidate_pool_csv(
            CANDIDATE_POOL_CSV_PATH,
            candidate_pool_artifact["candidate_pool_items"],
        )
        artifact = {
            "status": "PASS" if not p0_violations and edge_cases["status"] == "PASS" else "REVIEW_NEEDED",
            "scope": "5.9.9 Step 4 candidate pool MVP local shadow replay",
            "llm_called": False,
            "production_upload": False,
            "production_write_path": False,
            "production_db_write": False,
            "credit_consumed": False,
            "frontstage_replaced": False,
            "datasets": datasets,
            "session121_required_blocked_gate": _required_boundary_summary(session121_reviews),
            "edge_cases": edge_cases,
            "candidate_pool_mvp": {
                "schema_version": candidate_pool_artifact["schema_version"],
                "raw_item_count": candidate_pool_artifact["raw_item_count"],
                "item_count": candidate_pool_artifact["item_count"],
                "dedupe_fields": candidate_pool_artifact["dedupe_fields"],
                "sort_priority": candidate_pool_artifact["sort_priority"],
                "review_action_contract": candidate_pool_artifact["review_action_contract"],
                "artifact_json": str(candidate_pool_json_path.relative_to(ROOT)),
                "artifact_csv": str(candidate_pool_csv_path.relative_to(ROOT)),
            },
            "aggregate_focus_label_metrics": focus_metrics,
            "aggregate_downgrade_reasons": _aggregate_downgrades(datasets, edge_cases),
            "p0_count": len(p0_violations),
            "p0_violations": p0_violations,
            "session122_postdeploy_reference": {
                "status": postdeploy.get("status"),
                "frontstage_counts": postdeploy.get("frontstage_counts"),
                "single_detail_counts": postdeploy.get("single_detail_counts"),
                "target_single_tag_downloads": postdeploy.get("target_single_tag_downloads"),
                "p0": postdeploy.get("p0"),
            },
            "artifact_files_read": [
                str(SESSION120_GOLD.relative_to(ROOT)),
                str(SESSION121_FIXTURE.relative_to(ROOT)),
                str(SESSION122_RESULTS.relative_to(ROOT)),
                str(SESSION122_ACCEPTANCE.relative_to(ROOT)),
                str(POSTDEPLOY_AUDIT.relative_to(ROOT)),
            ],
            "artifact_files_written": [
                str(ARTIFACT_PATH.relative_to(ROOT)),
                str(candidate_pool_json_path.relative_to(ROOT)),
                str(candidate_pool_csv_path.relative_to(ROOT)),
            ],
        }
        ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
        ARTIFACT_PATH.write_text(json.dumps(artifact, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"status": artifact["status"], "p0_count": artifact["p0_count"], "path": str(ARTIFACT_PATH)}, ensure_ascii=False))
    finally:
        set_customer_label_catalog_state_for_tests(None)


if __name__ == "__main__":
    main()
