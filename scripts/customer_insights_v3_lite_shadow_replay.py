from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend_api.app.services.customer_insights_v3_lite import (
    build_catalog_backlog_draft,
    project_customer_insights_artifact,
    write_catalog_backlog_csv,
    write_customer_insights_json_artifact,
)
from backend_api.app.services.customer_label_catalog import (
    CustomerLabelCatalogState,
    set_customer_label_catalog_state_for_tests,
)
from backend_api.app.services.customer_label_v2_shadow import (
    FOCUS_WADERS_LABELS,
    compare_customer_label_v2_shadow,
    run_customer_label_v2_shadow,
)
from scripts.customer_label_v2_waders_shadow_replay import (
    HUMAN_351_400_GOLD,
    MATURITY_ROLLOUT_FIXTURE,
    SESSION120_GOLD,
    SESSION121_FIXTURE,
    SESSION122_ACCEPTANCE,
    SESSION122_RESULTS,
    _add_precision_recall,
    _aggregate_focus_metrics,
    _blocked_from_review,
    _expected_from_review,
    _human_351_400_reviews,
    _session120_reviews,
    _session121_reviews,
    _session122_reviews,
)

SCOPE = "5.9.9 v3-lite customer_insights shadow/read-model projection"
ARTIFACT_DIR = ROOT / "tmp" / "5.9.9-v3-lite-customer-insights-shadow"
CUSTOMER_INSIGHTS_ARTIFACT_PATH = ARTIFACT_DIR / "customer-insights-shadow.json"
CATALOG_BACKLOG_JSON_PATH = ARTIFACT_DIR / "catalog-backlog-draft.json"
CATALOG_BACKLOG_CSV_PATH = ARTIFACT_DIR / "catalog-backlog-draft.csv"
SUMMARY_PATH = ARTIFACT_DIR / "v3-lite-shadow-summary.json"
REVIEWED_CANDIDATE_POOL_PATH = (
    ROOT / "tmp" / "5.9.9-step7-v2-frontstage-read-path-integration" / "candidate-pool-reviewed.json"
)


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _dataset_reviews() -> dict[str, list[dict[str, Any]]]:
    return {
        "session120_human_gold": _session120_reviews(),
        "session121_blind_boundary_fixture_vs_v1_display": _session121_reviews(),
        "session122_postdeploy_acceptance_summary": _session122_reviews(),
        "waders_351_400_human_gold": _human_351_400_reviews(),
    }


def _shadow_results_by_dataset(datasets: dict[str, list[dict[str, Any]]]) -> dict[str, list[dict[str, Any]]]:
    shadow_results: dict[str, list[dict[str, Any]]] = {}
    for dataset, reviews in datasets.items():
        shadow_results[dataset] = []
        for review in reviews:
            result = run_customer_label_v2_shadow(review)
            result["_dataset"] = dataset
            shadow_results[dataset].append(result)
    return shadow_results


def _flat_shadow_results(shadow_results: dict[str, list[dict[str, Any]]]) -> list[dict[str, Any]]:
    return [result for results in shadow_results.values() for result in results]


def _replay_datasets(datasets: dict[str, list[dict[str, Any]]]) -> list[dict[str, Any]]:
    return [
        _add_precision_recall(
            compare_customer_label_v2_shadow(
                reviews,
                _expected_from_review,
                dataset_name=dataset_name,
                blocked_keys=_blocked_from_review,
            )
        )
        for dataset_name, reviews in datasets.items()
    ]


def _p0_violations(replay_datasets: list[dict[str, Any]]) -> list[dict[str, Any]]:
    focus_metrics = _aggregate_focus_metrics(replay_datasets)
    violations = [
        violation
        for dataset in replay_datasets
        for violation in dataset.get("blocked_violations") or []
    ]
    for label_type, canonical in FOCUS_WADERS_LABELS:
        key = f"{label_type}:{canonical}"
        metrics = focus_metrics.get(key, {})
        if int(metrics.get("fp") or 0) or int(metrics.get("fn") or 0):
            violations.append({"label": key, "metrics": metrics})
    return violations


def _probe_candidate(
    *,
    canonical: str,
    evidence: str,
    raw_label: str,
    aspect_key: str,
    label_type: str = "issue",
    confidence: float = 0.9,
) -> dict[str, Any]:
    return {
        "label_type": label_type,
        "canonical_label_key": canonical,
        "raw_label": raw_label,
        "display_label_en": raw_label,
        "display_label_zh": raw_label,
        "aspect_key": aspect_key,
        "polarity": "negative" if label_type == "issue" else "positive",
        "evidence_candidate": evidence,
        "confidence": confidence,
        "reason": "v3-lite frontstage exclusion probe",
    }


def _audit_candidate_probe_shadow_results() -> list[dict[str, Any]]:
    review = {
        "id": "v3-lite-exclusion-probe",
        "session_id": "v3-lite-exclusion-session",
        "product_id": "TIDEWE-v3-lite",
        "content": "They do not keep you dry. The boot seam leaked on the first trip.",
        "rating": 1,
        "category": "outdoor",
        "sub_category": "waders",
    }
    return [
        run_customer_label_v2_shadow(
            review,
            label_candidates=[
                _probe_candidate(
                    canonical="water_leaks_through",
                    evidence="do not keep you dry",
                    raw_label="Water leaks through",
                    aspect_key="waterproof",
                ),
                _probe_candidate(
                    canonical="water_leaks_through",
                    evidence="missing evidence",
                    raw_label="Water leaks through",
                    aspect_key="waterproof",
                ),
                _probe_candidate(
                    canonical="candidate:boot_seam_leak",
                    evidence="boot seam leaked",
                    raw_label="Boot seam leak",
                    aspect_key="seam_integrity",
                ),
            ],
        )
    ]


def _frontstage_exclusion_probe(shadow_results: list[dict[str, Any]]) -> dict[str, Any]:
    probe_results = shadow_results + _audit_candidate_probe_shadow_results()
    audit_count = sum(len(result.get("audit_occurrences") or []) for result in probe_results)
    candidate_pool_count = sum(len(result.get("candidate_pool_items") or []) for result in probe_results)
    projected_layers = {
        insight.get("source_layer")
        for result in probe_results
        for projection in [project_customer_insights_artifact([result], scope=SCOPE)]
        for item in projection.get("projections") or []
        for insight in item.get("customer_insights") or []
    }
    violations = []
    if projected_layers - {"display_occurrences"}:
        violations.append({"unexpected_projected_layers": sorted(projected_layers)})
    return {
        "status": "PASS" if not violations else "REVIEW_NEEDED",
        "audit_occurrence_count": audit_count,
        "candidate_pool_item_count": candidate_pool_count,
        "projected_layers": sorted(projected_layers),
        "violations": violations,
    }


def main() -> None:
    set_customer_label_catalog_state_for_tests(CustomerLabelCatalogState())
    try:
        ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
        datasets = _dataset_reviews()
        replay = _replay_datasets(datasets)
        p0_violations = _p0_violations(replay)
        shadow_results_by_dataset = _shadow_results_by_dataset(datasets)
        shadow_results = _flat_shadow_results(shadow_results_by_dataset)
        reviewed_candidate_pool = _load_json(REVIEWED_CANDIDATE_POOL_PATH)
        human_gold_fixture = _load_json(HUMAN_351_400_GOLD)
        source_artifacts = [
            str(SESSION120_GOLD.relative_to(ROOT)),
            str(SESSION121_FIXTURE.relative_to(ROOT)),
            str(HUMAN_351_400_GOLD.relative_to(ROOT)),
            str(MATURITY_ROLLOUT_FIXTURE.relative_to(ROOT)),
            str(SESSION122_RESULTS.relative_to(ROOT)),
            str(SESSION122_ACCEPTANCE.relative_to(ROOT)),
            str(REVIEWED_CANDIDATE_POOL_PATH.relative_to(ROOT)),
        ]

        customer_insights = project_customer_insights_artifact(
            shadow_results,
            scope=SCOPE,
            source_artifacts=source_artifacts,
        )
        customer_insights_path = write_customer_insights_json_artifact(
            CUSTOMER_INSIGHTS_ARTIFACT_PATH,
            customer_insights,
        )
        catalog_backlog = build_catalog_backlog_draft(
            shadow_results=shadow_results,
            reviewed_candidate_pool_artifact=reviewed_candidate_pool,
            human_gold_fixture=human_gold_fixture,
            scope=SCOPE,
            source_artifacts=source_artifacts + [str(customer_insights_path.relative_to(ROOT))],
        )
        catalog_backlog_path = write_customer_insights_json_artifact(CATALOG_BACKLOG_JSON_PATH, catalog_backlog)
        catalog_backlog_csv_path = write_catalog_backlog_csv(
            CATALOG_BACKLOG_CSV_PATH,
            catalog_backlog["catalog_backlog_items"],
        )
        exclusion_probe = _frontstage_exclusion_probe(shadow_results)
        status = (
            "PASS"
            if (
                not p0_violations
                and customer_insights["status"] == "PASS"
                and catalog_backlog["status"] == "PASS"
                and exclusion_probe["status"] == "PASS"
            )
            else "REVIEW_NEEDED"
        )
        summary = {
            "schema_version": "customer-insights-v3-lite-shadow-summary.1",
            "scope": SCOPE,
            "status": status,
            "p0_count": len(p0_violations),
            "p0_violations": p0_violations,
            "datasets": replay,
            "customer_insights_projection": {
                "status": customer_insights["status"],
                "review_count": customer_insights["review_count"],
                "frontstage_display_occurrence_count": customer_insights[
                    "frontstage_display_occurrence_count"
                ],
                "customer_insight_count": customer_insights["customer_insight_count"],
                "frontstage_display_occurrence_coverage": customer_insights[
                    "frontstage_display_occurrence_coverage"
                ],
                "contract_violations": customer_insights["contract_violations"],
                "artifact_json": str(customer_insights_path.relative_to(ROOT)),
            },
            "catalog_backlog_draft": {
                "status": catalog_backlog["status"],
                "item_count": catalog_backlog["item_count"],
                "summary": catalog_backlog["summary"],
                "contract_violations": catalog_backlog["contract_violations"],
                "artifact_json": str(catalog_backlog_path.relative_to(ROOT)),
                "artifact_csv": str(catalog_backlog_csv_path.relative_to(ROOT)),
            },
            "frontstage_exclusion_probe": exclusion_probe,
            "boundaries": {
                "shadow_only": True,
                "production_db_write": False,
                "production_deploy": False,
                "frontstage_wired": False,
                "prompt_confidence_changed": False,
                "category_review_intent_split": False,
                "specific_issue_replaced": False,
                "step9_validation_object_changed": False,
                "catalog_backlog_runtime_source": False,
            },
            "safety": {
                "production_upload": False,
                "production_write_path": False,
                "production_db_write": False,
                "db_write": False,
                "credit_consumed": False,
                "llm_called": False,
                "frontstage_replaced": False,
                "frontstage_mutated": False,
            },
            "source_artifacts": source_artifacts,
        }
        SUMMARY_PATH.write_text(
            json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        print(json.dumps({"status": status, "artifact": str(SUMMARY_PATH.relative_to(ROOT))}, ensure_ascii=False))
    finally:
        set_customer_label_catalog_state_for_tests(None)


if __name__ == "__main__":
    main()
