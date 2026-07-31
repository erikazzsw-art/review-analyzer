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
    build_reviewed_candidate_pool_artifact,
    write_candidate_pool_csv,
    write_candidate_pool_json_artifact,
    write_reviewed_candidate_pool_csv,
    write_reviewed_candidate_pool_json_artifact,
)
from backend_api.app.services.customer_label_v2_frontstage import (
    READ_PATH_V1_CURRENT,
    READ_PATH_V2_SHADOW,
    CustomerLabelV2FrontstageFlag,
    build_customer_label_v2_frontstage_read_model,
    build_frontstage_read_path_artifact,
    frontstage_keys_from_read_model,
)
from backend_api.app.services.customer_label_v2_maturity import maturity_contract_summary
from backend_api.app.services.customer_label_v2_shadow import (
    FOCUS_WADERS_LABELS,
    compare_customer_label_v2_shadow,
    display_keys_from_shadow,
    run_customer_label_v2_shadow,
    v1_display_keys_for_review,
)
from backend_api.app.services.specific_issue import (
    CUSTOMER_LABEL_OCCURRENCE_RULESET_VERSION,
    CUSTOMER_LABEL_OCCURRENCE_SCHEMA_VERSION,
    build_customer_highlight_rows,
    build_specific_issue_rows,
    customer_highlight_tags_for_comment,
    customer_issue_tags_for_comment,
    decorate_comment_customer_labels,
    iter_customer_highlight_occurrences,
    iter_specific_issue_occurrences,
)
from review_analyzer.exporter import _build_comments_data

ROOT = Path(__file__).resolve().parents[1]
FIXTURES_DIR = ROOT / "backend_api" / "tests" / "fixtures"
SESSION120_GOLD = FIXTURES_DIR / "customer_label_waders_session120_human_gold.json"
SESSION121_FIXTURE = FIXTURES_DIR / "customer_label_waders_session121_blind_regression.json"
HUMAN_351_400_GOLD = FIXTURES_DIR / "customer_label_waders_351_400_human_gold.json"
MATURITY_ROLLOUT_FIXTURE = FIXTURES_DIR / "customer_label_v2_maturity_rollout.json"
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
STEP7_SCOPE = "5.9.9 Step 7 v2 frontstage read-path actual consumer integration"
ARTIFACT_DIR = ROOT / "tmp" / "5.9.9-step7-v2-frontstage-read-path-integration"
ARTIFACT_PATH = ARTIFACT_DIR / "waders-shadow-summary.json"
FRONTSTAGE_READ_PATH_ARTIFACT_PATH = ARTIFACT_DIR / "frontstage-read-path-contract.json"
FRONTSTAGE_CONSUMER_INTEGRATION_ARTIFACT_PATH = ARTIFACT_DIR / "frontstage-consumer-integration.json"
CANDIDATE_POOL_ARTIFACT_PATH = ARTIFACT_DIR / "candidate-pool.json"
CANDIDATE_POOL_CSV_PATH = ARTIFACT_DIR / "candidate-pool.csv"
REVIEWED_CANDIDATE_POOL_ARTIFACT_PATH = ARTIFACT_DIR / "candidate-pool-reviewed.json"
REVIEWED_CANDIDATE_POOL_CSV_PATH = ARTIFACT_DIR / "candidate-pool-reviewed.csv"


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


def _human_351_400_reviews() -> list[dict[str, Any]]:
    payload = _load_json(HUMAN_351_400_GOLD)
    reviews: list[dict[str, Any]] = []
    for sample in payload["samples"]:
        review = _review_from_sample(sample)
        review["session_id"] = 351
        review["product_id"] = "TIDEWE-下水服-WD001"
        review["_expected_issue_keys"] = sample["expected_issue_keys"]
        review["_expected_highlight_keys"] = sample["expected_highlight_keys"]
        review["_blocked_issue_keys"] = sample.get("blocked_issue_keys", [])
        review["_blocked_highlight_keys"] = sample.get("blocked_highlight_keys", [])
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


def _step6_v1_occurrence(
    *,
    label_type: str,
    canonical: str,
    display_en: str,
    display_zh: str,
    aspect_key: str,
    evidence: str,
    comment_id: str,
) -> dict[str, Any]:
    return {
        "comment_id": comment_id,
        "type": label_type,
        "raw_label": display_en,
        "canonical_label_key": canonical,
        "display_label_en": display_en,
        "display_label_zh": display_zh,
        "aspect_key": aspect_key,
        "evidence_span": evidence,
        "evidence_start": -1,
        "evidence_end": -1,
        "confidence": "high",
        "source": "rule",
        "source_detail": "step6_v1_fixture",
        "evidence_verified": True,
        "cluster_propagated": False,
        "schema_version": CUSTOMER_LABEL_OCCURRENCE_SCHEMA_VERSION,
        "ruleset_version": CUSTOMER_LABEL_OCCURRENCE_RULESET_VERSION,
        "display_allowed": True,
    }


def _step6_waders_v1_review() -> dict[str, Any]:
    return {
        "id": "step6-readpath-waders",
        "session_id": "step6-readpath-session",
        "product_id": "TIDEWE-step6-readpath",
        "content": "The zipper broke on day one. They do not keep you dry.",
        "rating": 1,
        "category": "outdoor",
        "sub_category": "waders",
        "aspects_json": {
            "customer_label_occurrence_schema_version": CUSTOMER_LABEL_OCCURRENCE_SCHEMA_VERSION,
            "customer_label_occurrence_ruleset_version": CUSTOMER_LABEL_OCCURRENCE_RULESET_VERSION,
            "sub_category": "waders",
            "customer_label_occurrences": [
                _step6_v1_occurrence(
                    label_type="issue",
                    canonical="zipper_fails",
                    display_en="Zipper Fails",
                    display_zh="拉链容易故障",
                    aspect_key="zipper_quality",
                    evidence="zipper broke",
                    comment_id="step6-readpath-waders",
                )
            ],
        },
    }


def _step6_review(
    *,
    review_id: str,
    content: str,
    category: str,
    sub_category: str,
) -> dict[str, Any]:
    return {
        "id": review_id,
        "session_id": "step6-readpath-session",
        "product_id": f"synthetic-{category}",
        "content": content,
        "rating": 2,
        "category": category,
        "sub_category": sub_category,
    }


def _step6_frontstage_read_path_artifact() -> dict[str, Any]:
    waders_flag = CustomerLabelV2FrontstageFlag(
        enabled=True,
        sub_categories=("outdoor/waders",),
        shadow_fixture_gate_passed=True,
    )
    waders_v2_candidates = [
        _candidate(
            label_type="issue",
            canonical="water_leaks_through",
            evidence="do not keep you dry",
            aspect_key="waterproof",
        )
    ]
    cases = {
        "flag_off_v1_current": {
            "model": build_customer_label_v2_frontstage_read_model(
                _step6_waders_v1_review(),
                flag=CustomerLabelV2FrontstageFlag(),
                label_candidates=waders_v2_candidates,
            ),
            "expected_path": READ_PATH_V1_CURRENT,
            "expected_keys": "v1_current",
        },
        "flag_on_l3_waders_v2_shadow": {
            "model": build_customer_label_v2_frontstage_read_model(
                _step6_waders_v1_review(),
                flag=waders_flag,
                label_candidates=waders_v2_candidates,
            ),
            "expected_path": READ_PATH_V2_SHADOW,
            "expected_keys": {"issue": ["water_leaks_through"], "highlight": []},
        },
        "flag_on_without_fixture_gate_fallback": {
            "model": build_customer_label_v2_frontstage_read_model(
                _step6_waders_v1_review(),
                flag=CustomerLabelV2FrontstageFlag(
                    enabled=True,
                    sub_categories=("outdoor/waders",),
                    shadow_fixture_gate_passed=False,
                ),
                label_candidates=waders_v2_candidates,
            ),
            "expected_path": READ_PATH_V1_CURRENT,
            "expected_keys": "v1_current",
        },
        "l0_unknown_maturity_blocked": {
            "model": build_customer_label_v2_frontstage_read_model(
                _step6_review(
                    review_id="step6-l0",
                    content="Great product.",
                    category="toys",
                    sub_category="Mystery Toy",
                ),
                flag=CustomerLabelV2FrontstageFlag(
                    enabled=True,
                    categories=("toys",),
                    shadow_fixture_gate_passed=True,
                ),
                label_candidates=[
                    _candidate(
                        label_type="highlight",
                        canonical="overall_satisfied",
                        evidence="Great product",
                        aspect_key="other",
                    )
                ],
            ),
            "expected_path": READ_PATH_V1_CURRENT,
            "expected_keys": {"issue": [], "highlight": []},
        },
        "l1_generic_maturity_blocked": {
            "model": build_customer_label_v2_frontstage_read_model(
                _step6_review(
                    review_id="step6-l1",
                    content="The bib quality is poor.",
                    category="baby",
                    sub_category="Baby Bibs",
                ),
                flag=CustomerLabelV2FrontstageFlag(
                    enabled=True,
                    categories=("baby",),
                    shadow_fixture_gate_passed=True,
                ),
                label_candidates=[
                    _candidate(
                        label_type="issue",
                        canonical="quality_problem",
                        evidence="quality is poor",
                        aspect_key="build_quality",
                    )
                ],
            ),
            "expected_path": READ_PATH_V1_CURRENT,
            "expected_keys": {"issue": [], "highlight": []},
        },
        "l2_category_maturity_blocked": {
            "model": build_customer_label_v2_frontstage_read_model(
                _step6_review(
                    review_id="step6-l2",
                    content="The storage pocket is not waterproof.",
                    category="home",
                    sub_category="床架",
                ),
                flag=CustomerLabelV2FrontstageFlag(
                    enabled=True,
                    categories=("home",),
                    shadow_fixture_gate_passed=True,
                ),
                label_candidates=[
                    _candidate(
                        label_type="issue",
                        canonical="pocket_not_waterproof",
                        evidence="pocket is not waterproof",
                        aspect_key="accessory_storage",
                    )
                ],
            ),
            "expected_path": READ_PATH_V1_CURRENT,
            "expected_keys": {"issue": [], "highlight": []},
        },
        "unknown_label_candidate_pool_only": {
            "model": build_customer_label_v2_frontstage_read_model(
                _step6_review(
                    review_id="step6-unknown",
                    content="The boot seam leaked on the first trip.",
                    category="outdoor",
                    sub_category="waders",
                ),
                flag=waders_flag,
                label_candidates=[
                    _candidate(
                        label_type="issue",
                        canonical="candidate:boot_seam_leak",
                        raw_label="Boot seam leak",
                        evidence="boot seam leaked",
                        aspect_key="seam_integrity",
                    )
                ],
            ),
            "expected_path": READ_PATH_V2_SHADOW,
            "expected_keys": {"issue": [], "highlight": []},
        },
        "rollback_session_returns_v1_current": {
            "model": build_customer_label_v2_frontstage_read_model(
                _step6_waders_v1_review(),
                flag=CustomerLabelV2FrontstageFlag(
                    enabled=True,
                    sub_categories=("outdoor/waders",),
                    shadow_fixture_gate_passed=True,
                    rollback_session_ids=("step6-readpath-session",),
                ),
                label_candidates=waders_v2_candidates,
            ),
            "expected_path": READ_PATH_V1_CURRENT,
            "expected_keys": "v1_current",
        },
    }

    violations: list[dict[str, Any]] = []
    read_models: list[dict[str, Any]] = []
    for name, case in cases.items():
        model = case["model"]
        read_models.append(model)
        actual_keys = frontstage_keys_from_read_model(model)
        expected_keys = model["v1_current"]["keys"] if case["expected_keys"] == "v1_current" else case["expected_keys"]
        if model["read_path"] != case["expected_path"] or actual_keys != expected_keys:
            violations.append(
                {
                    "case": name,
                    "expected_path": case["expected_path"],
                    "actual_path": model["read_path"],
                    "expected_keys": expected_keys,
                    "actual_keys": actual_keys,
                    "fallback_reason": model["fallback_reason"],
                }
            )
        if any(model["frontstage_consumers"][consumer]["input_layer"] != "display_occurrences" for consumer in model["frontstage_consumers"]):
            violations.append({"case": name, "error": "consumer_not_display_occurrences"})
    artifact = build_frontstage_read_path_artifact(read_models, scope=STEP7_SCOPE)
    artifact["case_expectation_violations"] = violations
    artifact["status"] = "PASS" if artifact["status"] == "PASS" and not violations else "REVIEW_NEEDED"
    return artifact


def _decorate_with_stored_v2_shadow(
    review: dict[str, Any],
    *,
    candidates: list[dict[str, Any]],
    flag: CustomerLabelV2FrontstageFlag,
) -> dict[str, Any]:
    return decorate_comment_customer_labels(
        {
            **review,
            "customer_label_v2_shadow_result": run_customer_label_v2_shadow(
                review,
                label_candidates=candidates,
            ),
        },
        locale="en",
        v2_frontstage_flag=flag,
    )


def _consumer_snapshot(comments: list[dict[str, Any]]) -> dict[str, Any]:
    issue_rows = build_specific_issue_rows(comments, locale="en", limit=20)
    highlight_rows = build_customer_highlight_rows(comments, locale="en", limit=20)
    _, raw_rows = _build_comments_data(comments, include_specific_issue=True)
    return {
        "results_top10": {
            "issue_keys": [str(row.get("canonical_issue_key") or "") for row in issue_rows],
            "highlight_keys": [str(row.get("canonical_highlight_key") or "") for row in highlight_rows],
        },
        "single_review_detail": {
            "issue_tags": [customer_issue_tags_for_comment(comment, locale="en") for comment in comments],
            "highlight_tags": [customer_highlight_tags_for_comment(comment, locale="en") for comment in comments],
        },
        "raw_review_export": {
            "issue_labels": [str(row[11]) for row in raw_rows],
            "issue_evidence": [str(row[12]) for row in raw_rows],
            "highlight_labels": [str(row[13]) for row in raw_rows],
            "highlight_evidence": [str(row[14]) for row in raw_rows],
        },
        "single_tag_download": {
            "issue_keys": [
                str(occurrence.get("canonical_issue_key") or "")
                for comment in comments
                for occurrence in iter_specific_issue_occurrences(comment, locale="en")
            ],
            "highlight_keys": [
                str(occurrence.get("canonical_highlight_key") or "")
                for comment in comments
                for occurrence in iter_customer_highlight_occurrences(comment, locale="en")
            ],
        },
    }


def _step7_frontstage_consumer_integration_artifact() -> dict[str, Any]:
    waders_flag = CustomerLabelV2FrontstageFlag(
        enabled=True,
        sub_categories=("outdoor/waders",),
        shadow_fixture_gate_passed=True,
        allow_runtime_shadow=False,
    )
    waders_candidates = [
        _candidate(
            label_type="issue",
            canonical="water_leaks_through",
            evidence="do not keep you dry",
            aspect_key="waterproof",
        )
    ]
    baseline = decorate_comment_customer_labels(
        _step6_waders_v1_review(),
        locale="en",
        v2_frontstage_flag=CustomerLabelV2FrontstageFlag(),
    )
    flag_off = _decorate_with_stored_v2_shadow(
        _step6_waders_v1_review(),
        candidates=waders_candidates,
        flag=CustomerLabelV2FrontstageFlag(),
    )
    flag_on = _decorate_with_stored_v2_shadow(
        _step6_waders_v1_review(),
        candidates=waders_candidates,
        flag=waders_flag,
    )
    l1_blocked = _decorate_with_stored_v2_shadow(
        _step6_review(
            review_id="step7-consumer-l1",
            content="The bib quality is poor.",
            category="baby",
            sub_category="Baby Bibs",
        ),
        candidates=[
            _candidate(
                label_type="issue",
                canonical="quality_problem",
                evidence="quality is poor",
                aspect_key="build_quality",
            )
        ],
        flag=CustomerLabelV2FrontstageFlag(
            enabled=True,
            categories=("baby",),
            shadow_fixture_gate_passed=True,
            allow_runtime_shadow=False,
        ),
    )
    unknown = _decorate_with_stored_v2_shadow(
        _step6_review(
            review_id="step7-consumer-unknown",
            content="The boot seam leaked on the first trip.",
            category="outdoor",
            sub_category="waders",
        ),
        candidates=[
            _candidate(
                label_type="issue",
                canonical="candidate:boot_seam_leak",
                raw_label="Boot seam leak",
                evidence="boot seam leaked",
                aspect_key="seam_integrity",
            )
        ],
        flag=waders_flag,
    )
    rollback = _decorate_with_stored_v2_shadow(
        _step6_waders_v1_review(),
        candidates=waders_candidates,
        flag=CustomerLabelV2FrontstageFlag(
            enabled=True,
            sub_categories=("outdoor/waders",),
            shadow_fixture_gate_passed=True,
            rollback_session_ids=("step6-readpath-session",),
            allow_runtime_shadow=False,
        ),
    )

    cases = {
        "flag_off_v1_current": {
            "snapshot": _consumer_snapshot([flag_off]),
            "expected_snapshot": _consumer_snapshot([baseline]),
            "read_path": READ_PATH_V1_CURRENT,
        },
        "flag_on_l3_waders_v2_shadow": {
            "snapshot": _consumer_snapshot([flag_on]),
            "expected_issue_keys": ["water_leaks_through"],
            "read_path": READ_PATH_V2_SHADOW,
        },
        "l1_maturity_blocked_v1_empty": {
            "snapshot": _consumer_snapshot([l1_blocked]),
            "expected_issue_keys": [],
            "read_path": READ_PATH_V1_CURRENT,
        },
        "unknown_label_v2_empty": {
            "snapshot": _consumer_snapshot([unknown]),
            "expected_issue_keys": [],
            "read_path": READ_PATH_V2_SHADOW,
        },
        "rollback_v1_current": {
            "snapshot": _consumer_snapshot([rollback]),
            "expected_snapshot": _consumer_snapshot([baseline]),
            "read_path": READ_PATH_V1_CURRENT,
        },
    }

    violations: list[dict[str, Any]] = []
    for name, case in cases.items():
        snapshot = case["snapshot"]
        expected_snapshot = case.get("expected_snapshot")
        if expected_snapshot is not None and snapshot != expected_snapshot:
            violations.append({"case": name, "error": "v1_current_snapshot_mismatch"})
        expected_issue_keys = case.get("expected_issue_keys")
        if expected_issue_keys is not None:
            for consumer, payload in snapshot.items():
                issue_keys = payload.get("issue_keys") if isinstance(payload, dict) else None
                if issue_keys is not None and issue_keys != expected_issue_keys:
                    violations.append(
                        {
                            "case": name,
                            "consumer": consumer,
                            "error": "issue_key_mismatch",
                            "expected": expected_issue_keys,
                            "actual": issue_keys,
                        }
                    )
        if name == "flag_on_l3_waders_v2_shadow":
            if "zipper_fails" in snapshot["single_tag_download"]["issue_keys"]:
                violations.append({"case": name, "error": "v1_key_leaked_into_v2_single_tag_download"})
        if name == "unknown_label_v2_empty":
            if snapshot["single_tag_download"]["issue_keys"]:
                violations.append({"case": name, "error": "unknown_label_entered_single_tag_download"})

    return {
        "schema_version": "customer-label-v2-frontstage-consumer-integration.1",
        "scope": STEP7_SCOPE,
        "status": "PASS" if not violations else "REVIEW_NEEDED",
        "case_count": len(cases),
        "violations": violations,
        "cases": cases,
        "safety": {
            "production_upload": False,
            "production_write_path": False,
            "production_db_write": False,
            "db_write": False,
            "credit_consumed": False,
            "llm_called": False,
            "frontstage_replaced": False,
        },
    }


def _human_351_400_candidate_shadow_results() -> list[dict[str, Any]]:
    payload = _load_json(HUMAN_351_400_GOLD)
    results: list[dict[str, Any]] = []
    for sample in payload["samples"]:
        review = _review_from_sample(sample)
        review["session_id"] = 351
        review["product_id"] = "TIDEWE-下水服-WD001"
        for item in sample.get("needs_new_label") or []:
            evidence_spans = item.get("evidence_spans") or []
            if not evidence_spans:
                continue
            results.append(
                run_customer_label_v2_shadow(
                    review,
                    label_candidates=[
                        _candidate(
                            label_type=str(item["label_type"]),
                            canonical=str(item["canonical_label_key"]),
                            raw_label=str(item["raw_label_zh"]),
                            evidence=str(evidence_spans[0]["evidence_span"]),
                            aspect_key="other",
                            confidence=0.88,
                        )
                    ],
                )
            )
    return results


def _audit_reasons(result: dict[str, Any]) -> set[str]:
    return {
        str(reason)
        for occurrence in result.get("audit_occurrences") or []
        for reason in occurrence.get("downgrade_reasons") or []
    }


def _maturity_rollout_shadow_results() -> tuple[dict[str, Any], list[dict[str, Any]]]:
    payload = _load_json(MATURITY_ROLLOUT_FIXTURE)
    results: list[dict[str, Any]] = []
    violations: list[dict[str, Any]] = []
    category_summary: dict[str, Counter[str]] = defaultdict(Counter)
    downgrade_reasons: Counter[str] = Counter()
    maturity_levels: dict[str, str] = {}

    for group in payload["categories"]:
        category = str(group["category"])
        sub_category = str(group["sub_category"])
        expected_level = str(group["expected_maturity_level"])
        maturity_levels[category] = expected_level
        for case in group["cases"]:
            review = {
                "id": str(case["id"]),
                "session_id": "step5-maturity-rollout",
                "product_id": f"synthetic-{category}",
                "content": str(case["content"]),
                "rating": int(case.get("rating") or 3),
                "category": category,
                "sub_category": sub_category,
            }
            result = run_customer_label_v2_shadow(review, label_candidates=[case["candidate"]])
            results.append(result)
            actual_display = display_keys_from_shadow(result)
            reasons = _audit_reasons(result)
            downgrade_reasons.update(reasons)
            expected_pool_reasons = list(case["expected_candidate_pool_reasons"])
            category_summary[category]["case_count"] += 1
            category_summary[category]["display_count"] += len(result["display_occurrences"])
            category_summary[category]["audit_count"] += len(result["audit_occurrences"])
            category_summary[category]["candidate_pool_count"] += len(result["candidate_pool_items"])

            case_errors: list[str] = []
            if result["maturity_level"] != expected_level:
                case_errors.append("maturity_level_mismatch")
            if actual_display != case["expected_display"]:
                case_errors.append("display_split_mismatch")
            if not set(case["expected_audit_reasons"]) <= reasons:
                case_errors.append("audit_reasons_mismatch")
            if expected_pool_reasons:
                if not result["candidate_pool_items"]:
                    case_errors.append("candidate_pool_missing")
                elif result["candidate_pool_items"][0]["downgrade_reasons"] != expected_pool_reasons:
                    case_errors.append("candidate_pool_reasons_mismatch")
            elif result["candidate_pool_items"]:
                case_errors.append("candidate_pool_unexpected")
            if case_errors:
                violations.append(
                    {
                        "case_id": case["id"],
                        "category": category,
                        "sub_category": sub_category,
                        "errors": case_errors,
                        "actual_maturity_level": result["maturity_level"],
                        "expected_maturity_level": expected_level,
                        "actual_display": actual_display,
                        "expected_display": case["expected_display"],
                        "actual_audit_reasons": sorted(reasons),
                        "expected_audit_reasons": case["expected_audit_reasons"],
                    }
                )

    return {
        "schema_version": str(payload["schema_version"]),
        "fixture_path": str(MATURITY_ROLLOUT_FIXTURE.relative_to(ROOT)),
        "category_count": len(payload["categories"]),
        "case_count": len(results),
        "maturity_levels": dict(sorted(maturity_levels.items())),
        "downgrade_reasons": dict(sorted(downgrade_reasons.items())),
        "category_summary": {
            category: {
                "case_count": int(summary["case_count"]),
                "display_count": int(summary["display_count"]),
                "audit_count": int(summary["audit_count"]),
                "candidate_pool_count": int(summary["candidate_pool_count"]),
            }
            for category, summary in sorted(category_summary.items())
        },
        "violations": violations,
        "status": "PASS" if not violations else "REVIEW_NEEDED",
    }, results


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
    return {
        key: {
            "tp": int(value.get("tp", 0)),
            "fp": int(value.get("fp", 0)),
            "fn": int(value.get("fn", 0)),
        }
        for key, value in sorted(merged.items())
    }


def _aggregate_downgrades(datasets: list[dict[str, Any]], edge_cases: dict[str, Any]) -> dict[str, int]:
    merged: Counter[str] = Counter(edge_cases["downgrade_reasons"])
    for dataset in datasets:
        merged.update(dataset["downgrade_reasons"])
    return dict(sorted(merged.items()))


def _mock_review_actions_for_candidate_pool(candidate_pool_artifact: dict[str, Any]) -> list[dict[str, Any]]:
    actions: list[dict[str, Any]] = []
    for item in candidate_pool_artifact.get("candidate_pool_items") or []:
        candidate_id = str(item.get("candidate_id") or "")
        reasons = set(item.get("downgrade_reasons") or [])
        if "unknown_label" in reasons:
            actions.append(
                {
                    "candidate_id": candidate_id,
                    "action": "needs_new_label",
                    "raw_label": str(item.get("raw_label") or ""),
                    "reviewer": "step5-local-review-fixture",
                    "note": "Keep as local catalog backlog candidate; no DB write.",
                }
            )
        elif "maturity_blocked" in reasons:
            actions.append(
                {
                    "candidate_id": candidate_id,
                    "action": "accept",
                    "reviewer": "step5-local-review-fixture",
                    "note": "Accepted in reviewed artifact only; frontstage remains unchanged.",
                }
            )
        else:
            actions.append(
                {
                    "candidate_id": candidate_id,
                    "action": "ignore",
                    "reviewer": "step5-local-review-fixture",
                    "note": "Unhandled local candidate pool fixture reason.",
                }
            )
    return actions


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
        human_351_400 = _add_precision_recall(
            compare_customer_label_v2_shadow(
                _human_351_400_reviews(),
                _expected_from_review,
                dataset_name="waders_351_400_human_gold",
                blocked_keys=_blocked_from_review,
            )
        )
        edge_cases, edge_case_shadow_results = _edge_case_runs()
        human_351_400_candidate_shadow_results = _human_351_400_candidate_shadow_results()
        maturity_rollout, maturity_rollout_shadow_results = _maturity_rollout_shadow_results()
        frontstage_read_path_artifact = _step6_frontstage_read_path_artifact()
        frontstage_consumer_integration_artifact = _step7_frontstage_consumer_integration_artifact()
        ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
        FRONTSTAGE_READ_PATH_ARTIFACT_PATH.write_text(
            json.dumps(frontstage_read_path_artifact, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        FRONTSTAGE_CONSUMER_INTEGRATION_ARTIFACT_PATH.write_text(
            json.dumps(frontstage_consumer_integration_artifact, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        datasets = [session120, session121, session122, human_351_400]
        focus_metrics = _aggregate_focus_metrics(datasets)
        p0_violations = [
            violation
            for dataset in datasets
            for violation in dataset["blocked_violations"]
        ]
        for label_type, canonical in FOCUS_WADERS_LABELS:
            key = f"{label_type}:{canonical}"
            metrics = focus_metrics.get(key, {})
            if int(metrics.get("fp") or 0) or int(metrics.get("fn") or 0):
                p0_violations.append({"label": key, "metrics": metrics})
        postdeploy = _load_json(POSTDEPLOY_AUDIT) if POSTDEPLOY_AUDIT.exists() else {}
        human_gold_payload = _load_json(HUMAN_351_400_GOLD)
        candidate_pool_artifact = build_candidate_pool_artifact(
            edge_case_shadow_results + human_351_400_candidate_shadow_results + maturity_rollout_shadow_results,
            scope=STEP7_SCOPE,
            source_artifacts=[
                str(SESSION120_GOLD.relative_to(ROOT)),
                str(SESSION121_FIXTURE.relative_to(ROOT)),
                str(HUMAN_351_400_GOLD.relative_to(ROOT)),
                str(MATURITY_ROLLOUT_FIXTURE.relative_to(ROOT)),
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
        review_actions = _mock_review_actions_for_candidate_pool(candidate_pool_artifact)
        reviewed_candidate_pool_artifact = build_reviewed_candidate_pool_artifact(
            candidate_pool_artifact,
            review_actions,
            scope=STEP7_SCOPE,
            source_artifacts=[str(candidate_pool_json_path.relative_to(ROOT))],
        )
        reviewed_candidate_pool_json_path = write_reviewed_candidate_pool_json_artifact(
            REVIEWED_CANDIDATE_POOL_ARTIFACT_PATH,
            reviewed_candidate_pool_artifact,
        )
        reviewed_candidate_pool_csv_path = write_reviewed_candidate_pool_csv(
            REVIEWED_CANDIDATE_POOL_CSV_PATH,
            reviewed_candidate_pool_artifact,
        )
        artifact = {
            "status": (
                "PASS"
                if (
                    not p0_violations
                    and edge_cases["status"] == "PASS"
                    and maturity_rollout["status"] == "PASS"
                    and frontstage_read_path_artifact["status"] == "PASS"
                    and frontstage_consumer_integration_artifact["status"] == "PASS"
                    and reviewed_candidate_pool_artifact["status"] == "PASS"
                )
                else "REVIEW_NEEDED"
            ),
            "scope": STEP7_SCOPE,
            "llm_called": False,
            "production_upload": False,
            "production_write_path": False,
            "production_db_write": False,
            "credit_consumed": False,
            "frontstage_replaced": False,
            "datasets": datasets,
            "waders_351_400_human_gold_fixture": {
                "path": str(HUMAN_351_400_GOLD.relative_to(ROOT)),
                "review_count": human_gold_payload["review_count"],
                "needs_new_label_count": human_gold_payload["expected_summary"]["needs_new_label_count"],
                "fixture_validation_error_count": human_gold_payload["expected_summary"][
                    "fixture_validation_error_count"
                ],
                "current_shadow_after_step4_6": human_gold_payload["expected_summary"]["current_shadow_after_step4_6"],
            },
            "session121_required_blocked_gate": _required_boundary_summary(session121_reviews),
            "edge_cases": edge_cases,
            "maturity_contract": maturity_contract_summary(),
            "category_maturity_rollout": maturity_rollout,
            "frontstage_read_path_contract": {
                "schema_version": frontstage_read_path_artifact["schema_version"],
                "status": frontstage_read_path_artifact["status"],
                "case_count": frontstage_read_path_artifact["case_count"],
                "selected_read_paths": frontstage_read_path_artifact["selected_read_paths"],
                "violations": frontstage_read_path_artifact["violations"],
                "case_expectation_violations": frontstage_read_path_artifact["case_expectation_violations"],
                "artifact_json": str(FRONTSTAGE_READ_PATH_ARTIFACT_PATH.relative_to(ROOT)),
            },
            "frontstage_consumer_integration": {
                "schema_version": frontstage_consumer_integration_artifact["schema_version"],
                "status": frontstage_consumer_integration_artifact["status"],
                "case_count": frontstage_consumer_integration_artifact["case_count"],
                "violations": frontstage_consumer_integration_artifact["violations"],
                "artifact_json": str(FRONTSTAGE_CONSUMER_INTEGRATION_ARTIFACT_PATH.relative_to(ROOT)),
            },
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
            "candidate_pool_review_entry_mvp": {
                "schema_version": reviewed_candidate_pool_artifact["schema_version"],
                "source_schema_version": reviewed_candidate_pool_artifact["source_schema_version"],
                "reviewed_item_count": reviewed_candidate_pool_artifact["reviewed_item_count"],
                "review_action_summary": reviewed_candidate_pool_artifact["review_action_summary"],
                "artifact_json": str(reviewed_candidate_pool_json_path.relative_to(ROOT)),
                "artifact_csv": str(reviewed_candidate_pool_csv_path.relative_to(ROOT)),
                "safety": reviewed_candidate_pool_artifact["safety"],
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
                str(HUMAN_351_400_GOLD.relative_to(ROOT)),
                str(MATURITY_ROLLOUT_FIXTURE.relative_to(ROOT)),
                str(SESSION122_RESULTS.relative_to(ROOT)),
                str(SESSION122_ACCEPTANCE.relative_to(ROOT)),
                str(POSTDEPLOY_AUDIT.relative_to(ROOT)),
            ],
            "artifact_files_written": [
                str(ARTIFACT_PATH.relative_to(ROOT)),
                str(FRONTSTAGE_READ_PATH_ARTIFACT_PATH.relative_to(ROOT)),
                str(FRONTSTAGE_CONSUMER_INTEGRATION_ARTIFACT_PATH.relative_to(ROOT)),
                str(candidate_pool_json_path.relative_to(ROOT)),
                str(candidate_pool_csv_path.relative_to(ROOT)),
                str(reviewed_candidate_pool_json_path.relative_to(ROOT)),
                str(reviewed_candidate_pool_csv_path.relative_to(ROOT)),
            ],
        }
        ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
        ARTIFACT_PATH.write_text(json.dumps(artifact, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"status": artifact["status"], "p0_count": artifact["p0_count"], "path": str(ARTIFACT_PATH)}, ensure_ascii=False))
    finally:
        set_customer_label_catalog_state_for_tests(None)


if __name__ == "__main__":
    main()
