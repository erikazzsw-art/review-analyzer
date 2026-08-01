from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

from backend_api.app.services.review_signal_frontstage import (
    READ_PATH_REVIEW_SIGNAL_STORED_SHADOW,
    READ_PATH_V1_CURRENT,
    ReviewSignalFrontstageFlag,
    attach_review_signal_frontstage_adapter_for_local_test,
    build_review_signal_frontstage_read_model,
    build_review_signal_phase4_implementation_artifact,
    frontstage_keys_from_review_signal_read_model,
    resolve_review_signal_frontstage_config,
)
from backend_api.app.services.review_signal_shadow import (
    REVIEW_SIGNAL_FP_FN_SCHEMA_VERSION,
    REVIEW_SIGNAL_GOLD_SCHEMA_VERSION,
    REVIEW_SIGNAL_PROJECTION_SCHEMA_VERSION,
    REVIEW_SIGNAL_RULESET_VERSION,
    REVIEW_SIGNAL_SCHEMA_VERSION,
    ROUTE_AUDIT_FILTER,
    ROUTE_CONSUMER_PROFILE,
    ROUTE_CUSTOMER_ISSUE_CANDIDATE,
    ROUTE_CUSTOMER_LABEL_CANDIDATE,
    ROUTE_PURCHASE_MOTIVES,
    ROUTE_UNMET_NEEDS,
    SIGNAL_ACCESSORY_ONLY,
    SIGNAL_AUDIENCE,
    SIGNAL_AUDIT_ONLY,
    SIGNAL_BEHAVIOR,
    SIGNAL_COMPARISON_OR_OTHER_PRODUCT,
    SIGNAL_EXPECTATION,
    SIGNAL_GENERIC_OR_VAGUE,
    SIGNAL_PRODUCT_NEGATIVE,
    SIGNAL_PRODUCT_POSITIVE,
    SIGNAL_PURCHASE_MOTIVATION,
    SIGNAL_SHIPPING_SERVICE,
    SIGNAL_USAGE_LOCATION,
    SIGNAL_USAGE_TIME,
    build_signal_derived_routing_projection,
    compare_baseline_to_signal_shadow,
    normalize_review_signal_gold_fragment,
    review_signal_routing_table,
    review_signal_shadow_safety_flags,
    run_review_signal_shadow,
)
from backend_api.app.services.specific_issue import (
    CUSTOMER_LABEL_OCCURRENCE_RULESET_VERSION,
    CUSTOMER_LABEL_OCCURRENCE_SCHEMA_VERSION,
    build_customer_highlight_rows,
    build_specific_issue_rows,
    customer_highlight_tags_for_comment,
    customer_issue_tags_for_comment,
    iter_customer_highlight_occurrences,
    iter_specific_issue_occurrences,
)
from review_analyzer.exporter import _build_comments_data

ROOT = Path(__file__).resolve().parents[1]
FIXTURE_PATH = ROOT / "backend_api" / "tests" / "fixtures" / "review_signal_step9_1_airpods_minimal.json"
SESSION120_GOLD_PATH = ROOT / "backend_api" / "tests" / "fixtures" / "customer_label_waders_session120_human_gold.json"
SESSION121_BLIND_PATH = ROOT / "backend_api" / "tests" / "fixtures" / "customer_label_waders_session121_blind_regression.json"
WADERS_351_400_GOLD_PATH = ROOT / "backend_api" / "tests" / "fixtures" / "customer_label_waders_351_400_human_gold.json"
SESSION124_RESULTS_PATH = (
    ROOT
    / "tmp"
    / "5.9.9-step9-erika-led-production-truth-check"
    / "session124-readonly"
    / "session-results.json"
)
CANDIDATE_POOL_REVIEWED_PATH = (
    ROOT / "tmp" / "5.9.9-step7-v2-frontstage-read-path-integration" / "candidate-pool-reviewed.json"
)
ARTIFACT_DIR = ROOT / "tmp" / "5.9.9-step9.1-review-signal-layer-minimal"
SUMMARY_PATH = ARTIFACT_DIR / "review-signal-shadow-summary.json"
ROUTING_TABLE_PATH = ARTIFACT_DIR / "review-signal-routing-table.json"
FIXTURE_RESULTS_PATH = ARTIFACT_DIR / "review-signal-fixture-results.json"
GOLD_ASSIMILATION_PATH = ARTIFACT_DIR / "review-signal-gold-assimilation.json"
ROUTING_PROJECTION_PATH = ARTIFACT_DIR / "review-signal-routing-projection.json"
FP_FN_COMPARISON_PATH = ARTIFACT_DIR / "review-signal-shadow-fp-fn-comparison.json"
PHASE4_IMPLEMENTATION_PATH = ARTIFACT_DIR / "review-signal-phase4-implementation.json"


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _routing_for(signal_type: str) -> list[str]:
    return list(review_signal_routing_table()[signal_type]["route_to"])


def _default_polarity_for(signal_type: str) -> str:
    return str(review_signal_routing_table()[signal_type]["default_polarity"])


def _default_scope_for(signal_type: str) -> str:
    return str(review_signal_routing_table()[signal_type]["default_current_product_scope"])


def _fragment(
    review_id: Any,
    evidence_span: str,
    signal_type: str,
    *,
    source: str,
    source_kind: str,
    dataset: str,
    gold_reason: str,
    segment: str,
    label_type: str | None = None,
    canonical_label_key: str | None = None,
    polarity: str | None = None,
    current_product_scope: str | None = None,
    route_to: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "review_id": review_id,
        "evidence_span": evidence_span,
        "expected_signal_type": signal_type,
        "expected_polarity": polarity or _default_polarity_for(signal_type),
        "expected_current_product_scope": current_product_scope or _default_scope_for(signal_type),
        "expected_route_to": route_to or _routing_for(signal_type),
        "expected_label_type": label_type,
        "expected_canonical_label_key": canonical_label_key,
        "source": source,
        "source_kind": source_kind,
        "dataset": dataset,
        "segment": segment,
        "gold_reason": gold_reason,
    }


def _signal_candidate_from_gold(fragment: dict[str, Any]) -> dict[str, Any]:
    return {
        "signal_type": fragment["expected_signal_type"],
        "polarity": fragment["expected_polarity"],
        "evidence_span": fragment["evidence_span"],
        "current_product_scope": fragment["expected_current_product_scope"],
        "confidence": 0.95,
        "reason": fragment["gold_reason"],
    }


def _sample_index(payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {str(sample["id"]): sample for sample in payload.get("samples", [])}


def _session124_comment_index(payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {str(comment["id"]): comment for comment in payload.get("comments", [])}


def _local_occurrences(comment: dict[str, Any]) -> list[dict[str, Any]]:
    occurrences: list[dict[str, Any]] = []
    for occurrence in (comment.get("aspects_json") or {}).get("customer_label_occurrences") or []:
        if not occurrence.get("display_allowed"):
            continue
        if not occurrence.get("evidence_verified"):
            continue
        if occurrence.get("cluster_propagated"):
            continue
        label_type = str(occurrence.get("type") or "")
        if label_type == "highlight":
            label_type = "label"
        occurrences.append(
            {
                "label_type": label_type,
                "canonical_label_key": occurrence.get("canonical_label_key"),
                "display_label_en": occurrence.get("display_label_en"),
                "evidence_span": occurrence.get("evidence_span"),
                "evidence_verified": occurrence.get("evidence_verified"),
                "source_detail": occurrence.get("source_detail"),
            }
        )
    return occurrences


def _keys_from_occurrences(occurrences: list[dict[str, Any]], label_type: str) -> list[str]:
    keys: list[str] = []
    for occurrence in occurrences:
        if occurrence.get("label_type") != label_type:
            continue
        key = str(occurrence.get("canonical_label_key") or "").strip()
        if key and key not in keys:
            keys.append(key)
    return sorted(keys)


def _make_review_spec(
    *,
    review_id: Any,
    content: str,
    rating: int | float | None,
    dataset: str,
    source: str,
    source_kind: str,
    source_artifact: Path | str,
    fragments: list[dict[str, Any]],
    baseline_issue_keys: list[str] | None = None,
    baseline_label_keys: list[str] | None = None,
    existing_occurrences: list[dict[str, Any]] | None = None,
    reviewable_cases: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    return {
        "id": review_id,
        "content": content,
        "rating": rating,
        "dataset": dataset,
        "source": source,
        "source_kind": source_kind,
        "source_artifact": str(Path(source_artifact).relative_to(ROOT)) if isinstance(source_artifact, Path) else source_artifact,
        "fragments": fragments,
        "baseline_issue_keys": baseline_issue_keys or [],
        "baseline_label_keys": baseline_label_keys or [],
        "existing_occurrences": existing_occurrences or [],
        "reviewable_cases": reviewable_cases or [],
    }


def _segment_for_airpods(sample: dict[str, Any], signal: dict[str, Any]) -> str:
    signal_type = signal["signal_type"]
    if sample["id"] == "airpods-erika-long-review" and signal_type in {
        SIGNAL_PRODUCT_POSITIVE,
        SIGNAL_PRODUCT_NEGATIVE,
    }:
        return "five_star_mixed_review"
    if sample["id"] == "airpods-mixed-positive-and-negative":
        return "mixed_review"
    if signal_type == SIGNAL_COMPARISON_OR_OTHER_PRODUCT:
        return "old_or_other_product"
    if signal_type == SIGNAL_ACCESSORY_ONLY:
        return "accessory"
    if signal_type == SIGNAL_SHIPPING_SERVICE:
        return "shipping_service"
    if signal_type == SIGNAL_GENERIC_OR_VAGUE:
        return "generic_vague"
    if signal_type in {
        SIGNAL_AUDIENCE,
        SIGNAL_USAGE_LOCATION,
        SIGNAL_USAGE_TIME,
        SIGNAL_BEHAVIOR,
        SIGNAL_PURCHASE_MOTIVATION,
        SIGNAL_EXPECTATION,
    }:
        return "audience_context_motivation_expectation"
    return "overall_customer_issue_label"


def _build_airpods_gold_specs(fixture: dict[str, Any]) -> list[dict[str, Any]]:
    specs: list[dict[str, Any]] = []
    for sample in fixture["samples"]:
        is_screenshot = sample["id"] == "airpods-erika-long-review"
        source_kind = "screenshot_derived_gold" if is_screenshot else "local_shadow_probe"
        source = "erika_airpods_screenshot_long_review" if is_screenshot else "step9_1_airpods_minimal_probe"
        dataset = "airpods_screenshot_gold" if is_screenshot else "airpods_shadow_probe"
        fragments = [
            _fragment(
                sample["id"],
                signal["evidence_span"],
                signal["signal_type"],
                source=source,
                source_kind=source_kind,
                dataset=dataset,
                gold_reason=signal["reason"],
                segment=_segment_for_airpods(sample, signal),
                polarity=signal.get("polarity"),
                current_product_scope=signal.get("current_product_scope"),
            )
            for signal in sample["review_signals"]
        ]
        specs.append(
            _make_review_spec(
                review_id=sample["id"],
                content=sample["content"],
                rating=sample.get("rating"),
                dataset=dataset,
                source=source,
                source_kind=source_kind,
                source_artifact=FIXTURE_PATH,
                fragments=fragments,
            )
        )
    return specs


def _build_session120_gold_specs(payload: dict[str, Any]) -> list[dict[str, Any]]:
    samples = _sample_index(payload)
    dataset = "session120_human_gold"
    source = "customer_label_waders_session120_human_gold"
    source_kind = "human_gold_fixture"

    def f(
        review_id: str,
        evidence: str,
        signal_type: str,
        reason: str,
        segment: str,
        *,
        label_type: str | None = None,
        key: str | None = None,
        scope: str | None = None,
        polarity: str | None = None,
    ) -> dict[str, Any]:
        return _fragment(
            review_id,
            evidence,
            signal_type,
            source=source,
            source_kind=source_kind,
            dataset=dataset,
            gold_reason=reason,
            segment=segment,
            label_type=label_type,
            canonical_label_key=key,
            current_product_scope=scope,
            polarity=polarity,
        )

    fragments_by_id = {
        "session120-row-2": [
            f("session120-row-2", "got a hole somewhere on the boot", SIGNAL_PRODUCT_NEGATIVE, "Current wader durability failure.", "mixed_review", label_type="issue", key="breaks_easily"),
            f("session120-row-2", "not that expensive to buy", SIGNAL_PRODUCT_POSITIVE, "Specific value-for-money praise in the same mixed review.", "mixed_review", label_type="label", key="good_value_for_the_price"),
            f("session120-row-2", "getting started in wading", SIGNAL_PURCHASE_MOTIVATION, "Buyer explains beginner-use purchase context.", "audience_context_motivation_expectation"),
        ],
        "session120-row-3": [
            f("session120-row-3", "my feet slid easily into the flexible bots", SIGNAL_PRODUCT_POSITIVE, "Fit praise grounded in current product wear experience.", "overall_customer_issue_label", label_type="label", key="fits_as_expected"),
            f("session120-row-3", "not yet tested in water", SIGNAL_AUDIT_ONLY, "Not-used-yet waterproof caveat must stay out of issue/label.", "generic_vague", scope="audit_only"),
        ],
        "session120-row-8": [
            f("session120-row-8", "son", SIGNAL_AUDIENCE, "Family/audience signal, not a product label.", "audience_context_motivation_expectation"),
            f("session120-row-8", "avid ocean fisherman", SIGNAL_BEHAVIOR, "Use-case context belongs in profile/context.", "audience_context_motivation_expectation"),
            f("session120-row-8", "Fit great", SIGNAL_PRODUCT_POSITIVE, "Current product fit praise.", "overall_customer_issue_label", label_type="label", key="fits_as_expected"),
            f("session120-row-8", "appear well made", SIGNAL_PRODUCT_POSITIVE, "Current product appearance/build praise mapped to looks-good in human gold.", "overall_customer_issue_label", label_type="label", key="looks_good"),
        ],
        "session120-row-19": [
            f("session120-row-19", "amateur fishing person", SIGNAL_AUDIENCE, "User-skill context must not become issue/label.", "audience_context_motivation_expectation"),
            f("session120-row-19", "fishing in a river for the first time", SIGNAL_BEHAVIOR, "Use behavior/context signal.", "audience_context_motivation_expectation"),
            f("session120-row-19", "a little bit bigger", SIGNAL_PRODUCT_NEGATIVE, "Current product fit complaint.", "mixed_review", label_type="issue", key="size_fit_problem"),
            f("session120-row-19", "product smelled", SIGNAL_PRODUCT_NEGATIVE, "Current product odor complaint.", "mixed_review", label_type="issue", key="strong_chemical_smell"),
        ],
        "session120-row-22": [
            f("session120-row-22", "not leaking", SIGNAL_PRODUCT_POSITIVE, "Current product waterproof praise inside a mixed review.", "mixed_review", label_type="label", key="keeps_water_out"),
            f("session120-row-22", "boots are not like the others I had", SIGNAL_COMPARISON_OR_OTHER_PRODUCT, "Other-product comparison should route to audit/filter.", "old_or_other_product", scope="other_product"),
            f("session120-row-22", "crushes your foot", SIGNAL_PRODUCT_NEGATIVE, "Current product boot/sole complaint.", "mixed_review", label_type="issue", key="soft_soles"),
        ],
        "session120-row-30": [
            f("session120-row-30", "These are great", SIGNAL_PRODUCT_POSITIVE, "Positive fragment remains a label candidate despite size warning.", "mixed_review", label_type="label", key="overall_satisfied"),
            f("session120-row-30", "size up when you order", SIGNAL_PRODUCT_NEGATIVE, "Current product fit guidance/complaint.", "mixed_review", label_type="issue", key="size_fit_problem"),
        ],
        "session120-row-37": [
            f("session120-row-37", "fit was huge", SIGNAL_PRODUCT_NEGATIVE, "Current product fit complaint.", "old_or_other_product", label_type="issue", key="size_fit_problem"),
            f("session120-row-37", "Simms waders and boots", SIGNAL_COMPARISON_OR_OTHER_PRODUCT, "Other brand purchase should not become current-product issue/label.", "old_or_other_product", scope="other_product"),
        ],
        "session120-row-48": [
            f("session120-row-48", "different brands of waders", SIGNAL_COMPARISON_OR_OTHER_PRODUCT, "Other-brand context belongs in audit/filter.", "old_or_other_product", scope="other_product"),
            f("session120-row-48", "family", SIGNAL_AUDIENCE, "Audience context.", "audience_context_motivation_expectation"),
            f("session120-row-48", "child", SIGNAL_AUDIENCE, "Audience context.", "audience_context_motivation_expectation"),
            f("session120-row-48", "dogs an outdoor bath", SIGNAL_BEHAVIOR, "Use behavior/context.", "audience_context_motivation_expectation"),
            f("session120-row-48", "chemical odor", SIGNAL_PRODUCT_NEGATIVE, "Current product odor complaint.", "overall_customer_issue_label", label_type="issue", key="strong_chemical_smell"),
            f("session120-row-48", "clothing was seemingly damp", SIGNAL_PRODUCT_NEGATIVE, "Current product breathability/wet-inside complaint.", "overall_customer_issue_label", label_type="issue", key="not_breathable"),
        ],
        "session120-row-49": [
            f("session120-row-49", "son", SIGNAL_AUDIENCE, "Audience context.", "audience_context_motivation_expectation"),
            f("session120-row-49", "campground", SIGNAL_USAGE_LOCATION, "Usage/work context.", "audience_context_motivation_expectation"),
            f("session120-row-49", "too early to say", SIGNAL_AUDIT_ONLY, "Not enough use evidence; audit only.", "generic_vague", scope="audit_only"),
            f("session120-row-49", "looks good", SIGNAL_PRODUCT_POSITIVE, "Current product appearance praise.", "overall_customer_issue_label", label_type="label", key="looks_good"),
        ],
    }
    specs: list[dict[str, Any]] = []
    for review_id, fragments in fragments_by_id.items():
        sample = samples[review_id]
        specs.append(
            _make_review_spec(
                review_id=review_id,
                content=sample["content"],
                rating=sample.get("rating") or 3,
                dataset=dataset,
                source=source,
                source_kind=source_kind,
                source_artifact=SESSION120_GOLD_PATH,
                fragments=fragments,
                baseline_issue_keys=list(sample["local_current_output"]["issue_keys"]),
                baseline_label_keys=list(sample["local_current_output"]["highlight_keys"]),
            )
        )
    return specs


def _build_session121_gold_specs(payload: dict[str, Any]) -> list[dict[str, Any]]:
    samples = _sample_index(payload)
    dataset = "session121_blind_regression"
    source = "customer_label_waders_session121_blind_regression"
    source_kind = "blind_regression_fixture"

    def f(
        review_id: str,
        evidence: str,
        signal_type: str,
        reason: str,
        segment: str,
        *,
        label_type: str | None = None,
        key: str | None = None,
        scope: str | None = None,
    ) -> dict[str, Any]:
        return _fragment(
            review_id,
            evidence,
            signal_type,
            source=source,
            source_kind=source_kind,
            dataset=dataset,
            gold_reason=reason,
            segment=segment,
            label_type=label_type,
            canonical_label_key=key,
            current_product_scope=scope,
        )

    fragments_by_id = {
        "session121-did-not-keep-dry": [
            f("session121-did-not-keep-dry", "sizing is not great", SIGNAL_PRODUCT_NEGATIVE, "Current product sizing complaint.", "mixed_review", label_type="issue", key="size_fit_problem"),
            f("session121-did-not-keep-dry", "did not keep him dry", SIGNAL_PRODUCT_NEGATIVE, "Current product waterproof failure.", "mixed_review", label_type="issue", key="water_leaks_through"),
            f("session121-did-not-keep-dry", "him", SIGNAL_AUDIENCE, "Audience/context signal.", "audience_context_motivation_expectation"),
        ],
        "session121-all-waders-leak-eventually": [
            f("session121-all-waders-leak-eventually", "ALL WADERS LEAK EVENTUALLY", SIGNAL_GENERIC_OR_VAGUE, "Category-level generalization must not become current-product leak issue.", "generic_vague", scope="unclear"),
            f("session121-all-waders-leak-eventually", "1 pair finally leaked", SIGNAL_COMPARISON_OR_OTHER_PRODUCT, "Old owned product leak, not the current review item.", "old_or_other_product", scope="other_product"),
        ],
        "session121-pocket-not-waterproof": [
            f("session121-pocket-not-waterproof", "more expensive brands", SIGNAL_COMPARISON_OR_OTHER_PRODUCT, "Other-brand context.", "old_or_other_product", scope="other_product"),
            f("session121-pocket-not-waterproof", "eventually leak", SIGNAL_GENERIC_OR_VAGUE, "Generic wader lifecycle claim should not become Water Leaks Through.", "generic_vague", scope="unclear"),
            f("session121-pocket-not-waterproof", "pocket", SIGNAL_PRODUCT_NEGATIVE, "Specific current-product pocket waterproof complaint.", "overall_customer_issue_label", label_type="issue", key="pocket_not_waterproof"),
        ],
        "session121-fit-daughter-wonderfully": [
            f("session121-fit-daughter-wonderfully", "Fit my daughter wonderfully", SIGNAL_PRODUCT_POSITIVE, "Current product fit praise.", "overall_customer_issue_label", label_type="label", key="fits_as_expected"),
            f("session121-fit-daughter-wonderfully", "daughter", SIGNAL_AUDIENCE, "Audience context.", "audience_context_motivation_expectation"),
        ],
        "session122-other-neoprene-waders-leak": [
            f("session122-other-neoprene-waders-leak", "other neoprene waders", SIGNAL_COMPARISON_OR_OTHER_PRODUCT, "Other product comparison.", "old_or_other_product", scope="other_product"),
            f("session122-other-neoprene-waders-leak", "continue to leak", SIGNAL_COMPARISON_OR_OTHER_PRODUCT, "Leak claim applies to other neoprene waders.", "old_or_other_product", scope="other_product"),
            f("session122-other-neoprene-waders-leak", "These waders are lightweight", SIGNAL_PRODUCT_POSITIVE, "Current product lightweight praise; no canonical comparison key in this local fixture.", "overall_customer_issue_label", label_type="label"),
            f("session122-other-neoprene-waders-leak", "keep you dry", SIGNAL_PRODUCT_POSITIVE, "Current product waterproof praise.", "overall_customer_issue_label", label_type="label", key="keeps_water_out"),
        ],
    }
    specs: list[dict[str, Any]] = []
    for review_id, fragments in fragments_by_id.items():
        sample = samples[review_id]
        specs.append(
            _make_review_spec(
                review_id=review_id,
                content=sample["content"],
                rating=sample.get("rating") or 3,
                dataset=dataset,
                source=source,
                source_kind=source_kind,
                source_artifact=SESSION121_BLIND_PATH,
                fragments=fragments,
                baseline_issue_keys=list(sample["required_issue_keys"]),
                baseline_label_keys=list(sample["required_highlight_keys"]),
            )
        )
    return specs


def _build_waders_351_400_gold_specs(payload: dict[str, Any]) -> list[dict[str, Any]]:
    samples = _sample_index(payload)
    dataset = "waders_351_400_human_gold"
    source = "customer_label_waders_351_400_human_gold"
    source_kind = "human_gold_fixture"

    def f(
        review_id: str,
        evidence: str,
        signal_type: str,
        reason: str,
        segment: str,
        *,
        label_type: str | None = None,
        key: str | None = None,
        scope: str | None = None,
    ) -> dict[str, Any]:
        return _fragment(
            review_id,
            evidence,
            signal_type,
            source=source,
            source_kind=source_kind,
            dataset=dataset,
            gold_reason=reason,
            segment=segment,
            label_type=label_type,
            canonical_label_key=key,
            current_product_scope=scope,
        )

    fragments_by_id = {
        "waders-351-400-row-351": [
            f("waders-351-400-row-351", "Great product", SIGNAL_PRODUCT_POSITIVE, "Current product generic but human-mapped satisfaction praise.", "generic_vague", label_type="label", key="overall_satisfied"),
            f("waders-351-400-row-351", "keeps ou dry", SIGNAL_PRODUCT_POSITIVE, "Current product waterproof praise.", "overall_customer_issue_label", label_type="label", key="keeps_water_out"),
        ],
        "waders-351-400-row-365": [
            f("waders-351-400-row-365", "Keep me dryish for the most part", SIGNAL_PRODUCT_POSITIVE, "Positive current-product waterproof/breathability-adjacent candidate remains unresolved.", "mixed_review", label_type="label", key="candidate:breathes_well_evidence_unclear"),
            f("waders-351-400-row-365", "for the price", SIGNAL_PRODUCT_POSITIVE, "Current product value praise.", "mixed_review", label_type="label", key="good_value_for_the_price"),
            f("waders-351-400-row-365", "appropriately sized", SIGNAL_PRODUCT_POSITIVE, "Current product fit praise.", "mixed_review", label_type="label", key="fits_as_expected"),
            f("waders-351-400-row-365", "not super durable", SIGNAL_PRODUCT_NEGATIVE, "Current product durability complaint.", "mixed_review", label_type="issue", key="breaks_easily"),
            f("waders-351-400-row-365", "rubbed my shins raw", SIGNAL_PRODUCT_NEGATIVE, "Current product comfort complaint.", "mixed_review", label_type="issue", key="uncomfortable_fit"),
            f("waders-351-400-row-365", "toe box collapses in water", SIGNAL_PRODUCT_NEGATIVE, "Current product comfort/boot structure complaint.", "mixed_review", label_type="issue", key="uncomfortable_fit"),
        ],
        "waders-351-400-row-368": [
            f("waders-351-400-row-368", "Excellent customer service", SIGNAL_SHIPPING_SERVICE, "Service/support praise should not enter Customer Label.", "shipping_service", scope="shipping_service"),
        ],
        "waders-351-400-row-372": [
            f("waders-351-400-row-372", "good choice for light duty", SIGNAL_EXPECTATION, "Use-condition expectation/opportunity, not a mature display issue key.", "audience_context_motivation_expectation", label_type="issue", key="candidate:not_for_hardcore_conditions"),
            f("waders-351-400-row-372", "not be good for hardcore conditions", SIGNAL_PRODUCT_NEGATIVE, "Current product limitation candidate remains unresolved.", "mixed_review", label_type="issue", key="candidate:not_for_hardcore_conditions"),
            f("waders-351-400-row-372", "They fit find", SIGNAL_PRODUCT_POSITIVE, "Current product fit praise.", "mixed_review", label_type="label", key="fits_as_expected"),
            f("waders-351-400-row-372", "comfortable", SIGNAL_PRODUCT_POSITIVE, "Current product comfort praise.", "mixed_review", label_type="label", key="comfortable_to_wear"),
        ],
        "waders-351-400-row-374": [
            f("waders-351-400-row-374", "Cabelas", SIGNAL_COMPARISON_OR_OTHER_PRODUCT, "Other retailer/product comparison.", "old_or_other_product", scope="other_product"),
            f("waders-351-400-row-374", "comfortable enough", SIGNAL_PRODUCT_POSITIVE, "Current product comfort praise in mixed review.", "mixed_review", label_type="label", key="comfortable_to_wear"),
            f("waders-351-400-row-374", "Size chart was accurate", SIGNAL_PRODUCT_POSITIVE, "Current product fit/size-chart praise.", "mixed_review", label_type="label", key="fits_as_expected"),
            f("waders-351-400-row-374", "comes with extras", SIGNAL_ACCESSORY_ONLY, "Accessory-only note is audit/filter for this routing layer.", "accessory", scope="accessory_only"),
            f("waders-351-400-row-374", "boots are thin sole", SIGNAL_PRODUCT_NEGATIVE, "Current product boot-sole candidate remains unresolved.", "mixed_review", label_type="issue", key="candidate:thin_boot_sole"),
            f("waders-351-400-row-374", "my feet got sore", SIGNAL_PRODUCT_NEGATIVE, "Current product comfort complaint.", "mixed_review", label_type="issue", key="uncomfortable_fit"),
            f("waders-351-400-row-374", "will definitely fail some day", SIGNAL_GENERIC_OR_VAGUE, "Future/generic concern without actual failure should stay audit/filter.", "generic_vague", scope="unclear"),
        ],
        "waders-351-400-row-396": [
            f("waders-351-400-row-396", "wife", SIGNAL_AUDIENCE, "Audience context.", "audience_context_motivation_expectation"),
            f("waders-351-400-row-396", "daughter", SIGNAL_AUDIENCE, "Audience context.", "audience_context_motivation_expectation"),
            f("waders-351-400-row-396", "needed a cheap pair", SIGNAL_PURCHASE_MOTIVATION, "Purchase motivation/value context.", "audience_context_motivation_expectation"),
            f("waders-351-400-row-396", "quality and fit", SIGNAL_PRODUCT_POSITIVE, "Current product quality and fit praise.", "mixed_review", label_type="label", key="good_material_quality"),
            f("waders-351-400-row-396", "backup pair", SIGNAL_EXPECTATION, "Use-frequency expectation/candidate should not be forced into existing key.", "audience_context_motivation_expectation", label_type="issue", key="candidate:not_for_frequent_use"),
            f("waders-351-400-row-396", "doesn't need them often", SIGNAL_EXPECTATION, "Use-frequency expectation/candidate should not be forced into existing key.", "audience_context_motivation_expectation", label_type="issue", key="candidate:not_for_frequent_use"),
        ],
        "waders-351-400-row-400": [
            f("waders-351-400-row-400", "fishing in the river", SIGNAL_BEHAVIOR, "Usage behavior/context.", "audience_context_motivation_expectation"),
            f("waders-351-400-row-400", "Not insulated", SIGNAL_PRODUCT_NEGATIVE, "Current product warmth complaint in 5-star mixed review.", "five_star_mixed_review", label_type="issue", key="insufficient_warmth"),
            f("waders-351-400-row-400", "has not leaked", SIGNAL_PRODUCT_POSITIVE, "Current product waterproof praise in 5-star mixed review.", "five_star_mixed_review", label_type="label", key="keeps_water_out"),
        ],
    }
    specs: list[dict[str, Any]] = []
    for review_id, fragments in fragments_by_id.items():
        sample = samples[review_id]
        specs.append(
            _make_review_spec(
                review_id=review_id,
                content=sample["content"],
                rating=sample.get("rating") or 3,
                dataset=dataset,
                source=source,
                source_kind=source_kind,
                source_artifact=WADERS_351_400_GOLD_PATH,
                fragments=fragments,
                baseline_issue_keys=list(sample["expected_issue_keys"]),
                baseline_label_keys=list(sample["expected_highlight_keys"]),
            )
        )
    return specs


def _build_session124_gold_specs(payload: dict[str, Any]) -> list[dict[str, Any]]:
    comments = _session124_comment_index(payload)
    dataset = "session124_readonly_local_copy"
    source = "session124_readonly_observation_local_copy"
    source_kind = "production_readonly_local_copy"

    def f(
        review_id: str,
        evidence: str,
        signal_type: str,
        reason: str,
        segment: str,
        *,
        label_type: str | None = None,
        key: str | None = None,
        scope: str | None = None,
    ) -> dict[str, Any]:
        return _fragment(
            review_id,
            evidence,
            signal_type,
            source=source,
            source_kind=source_kind,
            dataset=dataset,
            gold_reason=reason,
            segment=segment,
            label_type=label_type,
            canonical_label_key=key,
            current_product_scope=scope,
        )

    fragments_by_id = {
        "27033": [
            f("27033", "kid", SIGNAL_AUDIENCE, "Audience context must not become product issue/label.", "audience_context_motivation_expectation"),
            f("27033", "hold up well", SIGNAL_PRODUCT_POSITIVE, "Positive durability evidence; current baseline had a Breaks Easily FP occurrence on related wording.", "five_star_mixed_review", label_type="label", key="holds_up_well"),
            f("27033", "tear easily", SIGNAL_PRODUCT_POSITIVE, "Negated durability phrase supports no-break praise, not Breaks Easily issue.", "five_star_mixed_review", label_type="label", key="holds_up_well"),
            f("27033", "No leaks", SIGNAL_PRODUCT_POSITIVE, "Current product waterproof praise.", "five_star_mixed_review", label_type="label", key="keeps_water_out"),
            f("27033", "once water gets in", SIGNAL_AUDIT_ONLY, "Over-top water caveat is not current product leak failure.", "generic_vague", scope="audit_only"),
            f("27033", "Great budget option", SIGNAL_PRODUCT_POSITIVE, "Current product value praise.", "five_star_mixed_review", label_type="label", key="good_value_for_the_price"),
        ],
        "27039": [
            f("27039", "size up", SIGNAL_EXPECTATION, "Sizing advice is reviewable and should not be decided by rating alone.", "audience_context_motivation_expectation"),
            f("27039", "no leaks", SIGNAL_PRODUCT_POSITIVE, "Current product waterproof praise.", "accessory", label_type="label", key="keeps_water_out"),
            f("27039", "great price", SIGNAL_PRODUCT_POSITIVE, "Current product value praise.", "accessory", label_type="label", key="good_value_for_the_price"),
            f("27039", "hanger it comes with works great", SIGNAL_ACCESSORY_ONLY, "Accessory-only positive evidence must not become Missing Wader Hanger issue.", "accessory", scope="accessory_only"),
        ],
        "27040": [
            f("27040", "provide good traction", SIGNAL_PRODUCT_POSITIVE, "Positive traction evidence must not become Poor Traction issue.", "mixed_review", label_type="label", key="good_traction"),
            f("27040", "keeping the water out", SIGNAL_PRODUCT_POSITIVE, "Current product waterproof praise.", "mixed_review", label_type="label", key="keeps_water_out"),
            f("27040", "for the price", SIGNAL_PRODUCT_POSITIVE, "Current product value praise.", "mixed_review", label_type="label", key="good_value_for_the_price"),
        ],
        "27044": [
            f("27044", "gift for a family member", SIGNAL_AUDIENCE, "Gift/audience context.", "audience_context_motivation_expectation"),
            f("27044", "did not receive the hanger", SIGNAL_ACCESSORY_ONLY, "Accessory-only missing item is routed to audit/filter in this shadow layer.", "accessory", scope="accessory_only"),
            f("27044", "asked for assistance", SIGNAL_SHIPPING_SERVICE, "Support/service context.", "shipping_service", scope="shipping_service"),
            f("27044", "good quality", SIGNAL_PRODUCT_POSITIVE, "Current product material quality praise.", "accessory", label_type="label", key="good_material_quality"),
            f("27044", "gift for my son-in-law", SIGNAL_AUDIENCE, "Audience context.", "audience_context_motivation_expectation"),
        ],
        "27045": [
            f("27045", "came with a hanger. Well it did not", SIGNAL_ACCESSORY_ONLY, "Accessory-only missing item should be audit/filter for this routing layer.", "accessory", scope="accessory_only"),
            f("27045", "Very disappointing", SIGNAL_GENERIC_OR_VAGUE, "Generic sentiment without product attribute should not route to issue/label.", "generic_vague", scope="unclear"),
        ],
        "27052": [
            f("27052", "arrived on time", SIGNAL_SHIPPING_SERVICE, "Shipping/service signal should stay out of issue/label.", "shipping_service", scope="shipping_service"),
            f("27052", "leaked from the knees", SIGNAL_PRODUCT_NEGATIVE, "Current product waterproof failure.", "mixed_review", label_type="issue", key="water_leaks_through"),
        ],
        "27054": [
            f("27054", "threads came loose", SIGNAL_PRODUCT_NEGATIVE, "Current product durability issue inside 5-star mixed review.", "five_star_mixed_review", label_type="issue", key="breaks_easily"),
            f("27054", "size up", SIGNAL_PRODUCT_NEGATIVE, "Current product fit issue inside 5-star mixed review.", "five_star_mixed_review", label_type="issue", key="runs_too_small"),
            f("27054", "sweat", SIGNAL_PRODUCT_NEGATIVE, "Current product breathability issue inside 5-star mixed review.", "five_star_mixed_review", label_type="issue", key="not_breathable"),
            f("27054", "stayed dry", SIGNAL_PRODUCT_POSITIVE, "Current product waterproof praise in same 5-star mixed review.", "five_star_mixed_review", label_type="label", key="keeps_water_out"),
            f("27054", "no water seeping in", SIGNAL_PRODUCT_POSITIVE, "Negated leak evidence must not become Water Leaks Through issue.", "five_star_mixed_review", label_type="label", key="keeps_water_out"),
            f("27054", "For the price", SIGNAL_PRODUCT_POSITIVE, "Current product value praise.", "five_star_mixed_review", label_type="label", key="good_value_for_the_price"),
            f("27054", "good quality", SIGNAL_PRODUCT_POSITIVE, "Current product material quality praise.", "five_star_mixed_review", label_type="label", key="good_material_quality"),
        ],
        "27071": [
            f("27071", "have not used them fishing", SIGNAL_AUDIT_ONLY, "Not-used-yet caveat must not become product issue/label.", "generic_vague", scope="audit_only"),
            f("27071", "boots prove adequate grip/slip", SIGNAL_EXPECTATION, "Conditional future traction check should route to unmet/expectation, not Poor Traction issue.", "audience_context_motivation_expectation"),
            f("27071", "light weight", SIGNAL_PRODUCT_POSITIVE, "Current product lightweight praise.", "mixed_review", label_type="label", key="lightweight_waders"),
            f("27071", "for the price", SIGNAL_PRODUCT_POSITIVE, "Current product value praise.", "mixed_review", label_type="label", key="good_value_for_the_price"),
        ],
        "27072": [
            f("27072", "kids", SIGNAL_AUDIENCE, "Audience context.", "audience_context_motivation_expectation"),
            f("27072", "Great for the money", SIGNAL_PRODUCT_POSITIVE, "Current product value praise in 5-star mixed review.", "five_star_mixed_review", label_type="label", key="good_value_for_the_price"),
            f("27072", "one did get a hole", SIGNAL_PRODUCT_NEGATIVE, "Current product material failure remains issue candidate despite 5-star rating.", "five_star_mixed_review", label_type="issue", key="feels_thin_and_flimsy"),
            f("27072", "They are thin", SIGNAL_PRODUCT_NEGATIVE, "Current product thin/flimsy complaint in 5-star mixed review.", "five_star_mixed_review", label_type="issue", key="feels_thin_and_flimsy"),
            f("27072", "if you go easy on them they last", SIGNAL_PRODUCT_POSITIVE, "Current product durability praise in same mixed review.", "five_star_mixed_review", label_type="label", key="holds_up_well"),
        ],
        "27079": [
            f("27079", "good quality", SIGNAL_PRODUCT_POSITIVE, "Current product quality praise.", "mixed_review", label_type="label", key="good_material_quality"),
            f("27079", "kept the water out nicely", SIGNAL_PRODUCT_POSITIVE, "Current product waterproof praise.", "mixed_review", label_type="label", key="keeps_water_out"),
            f("27079", "little breast pocket", SIGNAL_PRODUCT_POSITIVE, "Pocket feature mention is positive storage evidence, not waterproof complaint.", "mixed_review", label_type="label", key="useful_storage_space"),
            f("27079", "run smaller", SIGNAL_PRODUCT_NEGATIVE, "Current product size issue.", "mixed_review", label_type="issue", key="runs_too_small"),
            f("27079", "chemical", SIGNAL_PRODUCT_NEGATIVE, "Current product odor/material complaint.", "mixed_review", label_type="issue", key="strong_chemical_smell"),
        ],
    }

    specs: list[dict[str, Any]] = []
    for review_id, fragments in fragments_by_id.items():
        comment = comments[review_id]
        occurrences = _local_occurrences(comment)
        specs.append(
            _make_review_spec(
                review_id=review_id,
                content=comment["content"],
                rating=comment.get("rating"),
                dataset=dataset,
                source=source,
                source_kind=source_kind,
                source_artifact=SESSION124_RESULTS_PATH,
                fragments=fragments,
                baseline_issue_keys=_keys_from_occurrences(occurrences, "issue"),
                baseline_label_keys=_keys_from_occurrences(occurrences, "label"),
                existing_occurrences=occurrences,
            )
        )
    return specs


def _build_candidate_pool_reviewed_specs(payload: dict[str, Any]) -> list[dict[str, Any]]:
    reviewed_items = payload.get("reviewed_candidate_pool_items", [])
    edge_item = next(
        item
        for item in reviewed_items
        if item.get("source_candidate_item", {}).get("review_id") == "edge-unknown-label"
    )
    dataset = "candidate_pool_reviewed"
    source = "step7_candidate_pool_reviewed"
    source_kind = "candidate_pool_reviewed"
    review_id = "edge-unknown-label"
    content = "The boot seam leaked on the first trip."
    output = edge_item["review_output"]
    fragments = [
        _fragment(
            review_id,
            str(output["evidence_candidate"]),
            SIGNAL_PRODUCT_NEGATIVE,
            source=source,
            source_kind=source_kind,
            dataset=dataset,
            gold_reason="Reviewed candidate pool item is a real product-negative fragment but remains candidate-only until canonical catalog mapping is resolved.",
            segment="mixed_review",
            label_type=str(output["label_type"]),
            canonical_label_key=str(output["canonical_label_key"]),
        )
    ]
    reviewable_cases = [
        {
            "review_id": item.get("source_candidate_item", {}).get("review_id"),
            "candidate_id": item.get("candidate_id"),
            "review_status": item.get("review_status"),
            "reason": "candidate_pool_reviewed_sample_without_full_review_content_or_candidate_mapping_only",
        }
        for item in reviewed_items
        if item.get("review_status") == "needs_new_label"
    ]
    return [
        _make_review_spec(
            review_id=review_id,
            content=content,
            rating=1,
            dataset=dataset,
            source=source,
            source_kind=source_kind,
            source_artifact=CANDIDATE_POOL_REVIEWED_PATH,
            fragments=fragments,
            reviewable_cases=reviewable_cases,
        )
    ]


def build_local_gold_review_specs() -> list[dict[str, Any]]:
    fixture = _load_json(FIXTURE_PATH)
    specs: list[dict[str, Any]] = []
    specs.extend(_build_airpods_gold_specs(fixture))
    specs.extend(_build_session120_gold_specs(_load_json(SESSION120_GOLD_PATH)))
    specs.extend(_build_session121_gold_specs(_load_json(SESSION121_BLIND_PATH)))
    specs.extend(_build_waders_351_400_gold_specs(_load_json(WADERS_351_400_GOLD_PATH)))
    specs.extend(_build_session124_gold_specs(_load_json(SESSION124_RESULTS_PATH)))
    specs.extend(_build_candidate_pool_reviewed_specs(_load_json(CANDIDATE_POOL_REVIEWED_PATH)))
    return specs


def _content_by_review_id(specs: list[dict[str, Any]]) -> dict[str, str]:
    return {str(spec["id"]): str(spec["content"]) for spec in specs}


def _normalized_gold_fragments(specs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    content_lookup = _content_by_review_id(specs)
    return [
        normalize_review_signal_gold_fragment(fragment, content_by_review_id=content_lookup)
        for spec in specs
        for fragment in spec["fragments"]
    ]


def _build_gold_assimilation_artifact(specs: list[dict[str, Any]]) -> dict[str, Any]:
    fragments = _normalized_gold_fragments(specs)
    source_kind_counts = Counter(str(fragment.get("source_kind") or "") for fragment in fragments)
    dataset_counts = Counter(str(fragment.get("dataset") or "") for fragment in fragments)
    segment_counts = Counter(str(fragment.get("segment") or "") for fragment in fragments)
    route_counts = Counter(route for fragment in fragments for route in fragment.get("expected_route_to", []))
    schema_errors = [
        {
            "review_id": fragment.get("review_id"),
            "evidence_span": fragment.get("evidence_span"),
            "schema_errors": fragment.get("schema_errors"),
        }
        for fragment in fragments
        if fragment.get("schema_errors")
    ]
    reviewable_cases = [
        {**case, "dataset": spec["dataset"], "source_kind": spec["source_kind"]}
        for spec in specs
        for case in spec.get("reviewable_cases", [])
    ]
    unresolved = [fragment for fragment in fragments if fragment.get("mapping_status") == "extraction_unresolved"]
    return {
        "schema_version": REVIEW_SIGNAL_GOLD_SCHEMA_VERSION,
        "ruleset_version": REVIEW_SIGNAL_RULESET_VERSION,
        "scope": "5.9.9 Step 9.1 Phase 2 local fragment-level gold assimilation",
        "status": "PASS" if not schema_errors else "REVIEW_NEEDED",
        "source_distinction": {
            "screenshot_derived_gold": "Erika screenshot-derived AirPods long-review fragments.",
            "human_gold_fixture": "Local human-gold fixtures such as session120 and 351-400.",
            "blind_regression_fixture": "Local blind regression fixture, not production gold.",
            "production_readonly_local_copy": "Session124 readonly local copy/observation, not renamed as production gold.",
            "candidate_pool_reviewed": "Reviewed candidate-pool artifact kept local and candidate-only.",
        },
        "review_count": len(specs),
        "fragment_count": len(fragments),
        "gold_coverage": {
            "source_kind_counts": dict(sorted(source_kind_counts.items())),
            "dataset_counts": dict(sorted(dataset_counts.items())),
            "segment_counts": dict(sorted(segment_counts.items())),
            "route_counts": dict(sorted(route_counts.items())),
            "evidence_verified_count": sum(1 for fragment in fragments if fragment.get("evidence_verified")),
            "evidence_not_found_count": sum(1 for fragment in fragments if not fragment.get("evidence_verified")),
            "mapped_product_fragment_count": sum(1 for fragment in fragments if fragment.get("mapping_status") == "mapped"),
            "unresolved_mapping_count": len(unresolved),
        },
        "reviews": [
            {
                "review_id": spec["id"],
                "dataset": spec["dataset"],
                "source": spec["source"],
                "source_kind": spec["source_kind"],
                "source_artifact": spec["source_artifact"],
                "rating": spec.get("rating"),
                "baseline_customer_issue_keys": spec["baseline_issue_keys"],
                "baseline_customer_label_keys": spec["baseline_label_keys"],
                "fragment_count": len(spec["fragments"]),
            }
            for spec in specs
        ],
        "gold_fragments": fragments,
        "schema_errors": schema_errors,
        "reviewable_cases": reviewable_cases,
        "safety": review_signal_shadow_safety_flags(),
    }


def _review_projection(spec: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    review = {"id": spec["id"], "content": spec["content"], "rating": spec.get("rating")}
    signal_candidates = [_signal_candidate_from_gold(fragment) for fragment in spec["fragments"]]
    shadow_result = run_review_signal_shadow(review, signal_candidates=signal_candidates)
    projection = build_signal_derived_routing_projection(
        review,
        existing_occurrences=spec.get("existing_occurrences", []),
        review_signals=shadow_result["review_signals"],
        gold_fragments=spec["fragments"],
    )
    comparison = compare_baseline_to_signal_shadow(
        dataset=spec["dataset"],
        baseline_issue_keys=spec["baseline_issue_keys"],
        baseline_label_keys=spec["baseline_label_keys"],
        projection=projection,
        gold_fragments=[
            normalize_review_signal_gold_fragment(
                fragment,
                content_by_review_id={str(spec["id"]): str(spec["content"])},
            )
            for fragment in spec["fragments"]
        ],
    )
    return (
        {
            "review_id": spec["id"],
            "dataset": spec["dataset"],
            "source_kind": spec["source_kind"],
            "rating": spec.get("rating"),
            "segments": sorted({str(fragment["segment"]) for fragment in spec["fragments"]}),
            "baseline_customer_issue_keys": spec["baseline_issue_keys"],
            "baseline_customer_label_keys": spec["baseline_label_keys"],
            "review_signals": shadow_result["review_signals"],
            "projection": projection,
            "reviewable_cases": spec.get("reviewable_cases", []),
        },
        comparison,
    )


def _sum_metric(comparisons: list[dict[str, Any]], section: str, label: str, field: str) -> int:
    return sum(int(comparison[section][label].get(field, 0)) for comparison in comparisons)


def _aggregate_key_lists(comparisons: list[dict[str, Any]], section: str, label: str, field: str) -> list[str]:
    keys: list[str] = []
    for comparison in comparisons:
        for key in comparison[section][label].get(field, []):
            if key not in keys:
                keys.append(key)
    return sorted(keys)


def _aggregate_comparisons(name: str, comparisons: list[dict[str, Any]]) -> dict[str, Any]:
    issue_baseline = {
        "tp": _sum_metric(comparisons, "baseline", "customer_issue", "tp"),
        "fp": _sum_metric(comparisons, "baseline", "customer_issue", "fp"),
        "fn": _sum_metric(comparisons, "baseline", "customer_issue", "fn"),
        "fp_keys": _aggregate_key_lists(comparisons, "baseline", "customer_issue", "fp_keys"),
        "fn_keys": _aggregate_key_lists(comparisons, "baseline", "customer_issue", "fn_keys"),
    }
    label_baseline = {
        "tp": _sum_metric(comparisons, "baseline", "customer_label", "tp"),
        "fp": _sum_metric(comparisons, "baseline", "customer_label", "fp"),
        "fn": _sum_metric(comparisons, "baseline", "customer_label", "fn"),
        "fp_keys": _aggregate_key_lists(comparisons, "baseline", "customer_label", "fp_keys"),
        "fn_keys": _aggregate_key_lists(comparisons, "baseline", "customer_label", "fn_keys"),
    }
    issue_shadow = {
        "tp": _sum_metric(comparisons, "signal_shadow", "customer_issue", "tp"),
        "fp": _sum_metric(comparisons, "signal_shadow", "customer_issue", "fp"),
        "fn": _sum_metric(comparisons, "signal_shadow", "customer_issue", "fn"),
        "fp_keys": _aggregate_key_lists(comparisons, "signal_shadow", "customer_issue", "fp_keys"),
        "fn_keys": _aggregate_key_lists(comparisons, "signal_shadow", "customer_issue", "fn_keys"),
    }
    label_shadow = {
        "tp": _sum_metric(comparisons, "signal_shadow", "customer_label", "tp"),
        "fp": _sum_metric(comparisons, "signal_shadow", "customer_label", "fp"),
        "fn": _sum_metric(comparisons, "signal_shadow", "customer_label", "fn"),
        "fp_keys": _aggregate_key_lists(comparisons, "signal_shadow", "customer_label", "fp_keys"),
        "fn_keys": _aggregate_key_lists(comparisons, "signal_shadow", "customer_label", "fn_keys"),
    }
    split = {
        "routing_fp": {
            "issue": sum(comparison["split_metrics"]["routing_fp"]["issue"] for comparison in comparisons),
            "label": sum(comparison["split_metrics"]["routing_fp"]["label"] for comparison in comparisons),
        },
        "routing_fn": {
            "issue": sum(comparison["split_metrics"]["routing_fn"]["issue"] for comparison in comparisons),
            "label": sum(comparison["split_metrics"]["routing_fn"]["label"] for comparison in comparisons),
        },
        "label_extraction_fp": {
            "issue": sum(comparison["split_metrics"]["label_extraction_fp"]["issue"] for comparison in comparisons),
            "label": sum(comparison["split_metrics"]["label_extraction_fp"]["label"] for comparison in comparisons),
        },
        "label_extraction_fn": {
            "issue": sum(comparison["split_metrics"]["label_extraction_fn"]["issue"] for comparison in comparisons),
            "label": sum(comparison["split_metrics"]["label_extraction_fn"]["label"] for comparison in comparisons),
        },
        "evidence_not_found_count": sum(comparison["split_metrics"]["evidence_not_found_count"] for comparison in comparisons),
        "non_product_leakage_count": sum(comparison["split_metrics"]["non_product_leakage_count"] for comparison in comparisons),
        "unresolved_mapping_count": sum(comparison["split_metrics"]["unresolved_mapping_count"] for comparison in comparisons),
    }
    return {
        "name": name,
        "review_count": len(comparisons),
        "status": "REVIEW_NEEDED" if split["unresolved_mapping_count"] or split["non_product_leakage_count"] else "PASS",
        "baseline": {
            "customer_issue": issue_baseline,
            "customer_label": label_baseline,
        },
        "signal_shadow": {
            "customer_issue": issue_shadow,
            "customer_label": label_shadow,
        },
        "fp_fn_delta": {
            "issue_fp_delta": issue_shadow["fp"] - issue_baseline["fp"],
            "issue_fn_delta": issue_shadow["fn"] - issue_baseline["fn"],
            "label_fp_delta": label_shadow["fp"] - label_baseline["fp"],
            "label_fn_delta": label_shadow["fn"] - label_baseline["fn"],
        },
        "split_metrics": split,
    }


REPORT_SEGMENTS = [
    "five_star_mixed_review",
    "mixed_review",
    "old_or_other_product",
    "accessory",
    "shipping_service",
    "generic_vague",
    "audience_context_motivation_expectation",
]


def _build_routing_projection_and_comparison_artifacts(
    specs: list[dict[str, Any]],
) -> tuple[dict[str, Any], dict[str, Any]]:
    projections: list[dict[str, Any]] = []
    comparisons: list[dict[str, Any]] = []
    for spec in specs:
        projection, comparison = _review_projection(spec)
        projections.append(projection)
        comparisons.append(comparison)

    dataset_summaries: dict[str, dict[str, Any]] = {}
    for dataset in sorted({spec["dataset"] for spec in specs}):
        dataset_summaries[dataset] = _aggregate_comparisons(
            dataset,
            [comparison for comparison in comparisons if comparison["dataset"] == dataset],
        )
    segment_summaries = {
        segment: _aggregate_comparisons(
            segment,
            [
                comparison
                for projection, comparison in zip(projections, comparisons)
                if segment in projection["segments"]
            ],
        )
        for segment in REPORT_SEGMENTS
    }
    overall = _aggregate_comparisons("overall", comparisons)
    reviewable_cases = [
        {**case, "review_id": projection["review_id"], "dataset": projection["dataset"]}
        for projection in projections
        for case in projection.get("reviewable_cases", [])
    ]
    total_leakage = sum(item["projection"]["non_product_leakage_count"] for item in projections)
    total_unresolved = sum(item["projection"]["unresolved_mapping_count"] for item in projections)
    total_evidence_not_found = sum(item["projection"]["evidence_not_found_count"] for item in projections)

    routing_artifact = {
        "schema_version": REVIEW_SIGNAL_PROJECTION_SCHEMA_VERSION,
        "ruleset_version": REVIEW_SIGNAL_RULESET_VERSION,
        "scope": "5.9.9 Step 9.1 Phase 3 signal-derived routing projection",
        "status": "PASS" if total_leakage == 0 else "REVIEW_NEEDED",
        "review_count": len(projections),
        "fragment_count": sum(len(projection["review_signals"]) for projection in projections),
        "dataset_summaries": dataset_summaries,
        "routing_leakage": {
            "non_product_to_issue_label_leakage_count": total_leakage,
            "evidence_not_found_count": total_evidence_not_found,
        },
        "unresolved_mappings": {
            "unresolved_mapping_count": total_unresolved,
            "note": "Unresolved mappings are kept out of TP/FP/FN pass claims.",
        },
        "reviewable_cases": reviewable_cases,
        "review_projections": projections,
        "safety": review_signal_shadow_safety_flags(),
    }
    fp_fn_artifact = {
        "schema_version": REVIEW_SIGNAL_FP_FN_SCHEMA_VERSION,
        "ruleset_version": REVIEW_SIGNAL_RULESET_VERSION,
        "scope": "5.9.9 Step 9.1 Phase 3 baseline vs signal shadow FP/FN comparison",
        "status": "REVIEW_NEEDED" if total_unresolved else overall["status"],
        "decision": {
            "routing_layer_ready_for_controlled_gray_review": total_leakage == 0
            and overall["split_metrics"]["routing_fn"]["issue"] == 0
            and overall["split_metrics"]["routing_fn"]["label"] == 0,
            "full_label_extraction_ready": total_unresolved == 0,
            "production_action_taken": False,
            "review_needed_reason": "Signal routing passed leakage/FN gates, but unresolved extraction/canonical mapping remains."
            if total_unresolved
            else "",
        },
        "overall": overall,
        "dataset_summaries": dataset_summaries,
        "segment_summaries": segment_summaries,
        "review_comparisons": comparisons,
        "routing_leakage": {
            "non_product_to_issue_label_leakage_count": total_leakage,
            "evidence_not_found_count": total_evidence_not_found,
        },
        "unresolved_mappings": {
            "unresolved_mapping_count": total_unresolved,
        },
        "reviewable_cases": reviewable_cases,
        "safety": review_signal_shadow_safety_flags(),
    }
    return routing_artifact, fp_fn_artifact


def _signals_by_review(results: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    return {str(result["review_id"]): list(result["review_signals"]) for result in results}


def _signal_by_evidence(signals: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {str(signal["evidence_span"]): signal for signal in signals}


def _required_fragment_expectations() -> list[dict[str, Any]]:
    return [
        {
            "review_id": "airpods-erika-long-review",
            "evidence_span": "comfortable",
            "expected_signal_type": SIGNAL_PRODUCT_POSITIVE,
            "expected_route_to": ["user_experience.positive", ROUTE_CUSTOMER_LABEL_CANDIDATE],
        },
        {
            "review_id": "airpods-erika-long-review",
            "evidence_span": "fit is secure",
            "expected_signal_type": SIGNAL_PRODUCT_POSITIVE,
            "expected_route_to": ["user_experience.positive", ROUTE_CUSTOMER_LABEL_CANDIDATE],
        },
        {
            "review_id": "airpods-erika-long-review",
            "evidence_span": "battery life is great",
            "expected_signal_type": SIGNAL_PRODUCT_POSITIVE,
            "expected_route_to": ["user_experience.positive", ROUTE_CUSTOMER_LABEL_CANDIDATE],
        },
        {
            "review_id": "airpods-erika-long-review",
            "evidence_span": "charging indicator is unclear",
            "expected_signal_type": SIGNAL_PRODUCT_NEGATIVE,
            "expected_route_to": ["user_experience.negative", ROUTE_CUSTOMER_ISSUE_CANDIDATE],
        },
        {
            "review_id": "airpods-erika-long-review",
            "evidence_span": "noise cancellation is poor",
            "expected_signal_type": SIGNAL_PRODUCT_NEGATIVE,
            "expected_route_to": ["user_experience.negative", ROUTE_CUSTOMER_ISSUE_CANDIDATE],
        },
        {
            "review_id": "airpods-erika-long-review",
            "evidence_span": "fall out when she dances",
            "expected_signal_type": SIGNAL_PRODUCT_NEGATIVE,
            "expected_route_to": ["user_experience.negative", ROUTE_CUSTOMER_ISSUE_CANDIDATE],
        },
        {
            "review_id": "airpods-erika-long-review",
            "evidence_span": "daughter",
            "expected_signal_type": SIGNAL_AUDIENCE,
            "expected_route_to": [ROUTE_CONSUMER_PROFILE],
        },
        {
            "review_id": "airpods-erika-long-review",
            "evidence_span": "son",
            "expected_signal_type": SIGNAL_AUDIENCE,
            "expected_route_to": [ROUTE_CONSUMER_PROFILE],
        },
        {
            "review_id": "airpods-erika-long-review",
            "evidence_span": "kids",
            "expected_signal_type": SIGNAL_AUDIENCE,
            "expected_route_to": [ROUTE_CONSUMER_PROFILE],
        },
        {
            "review_id": "airpods-erika-long-review",
            "evidence_span": "around the house",
            "expected_signal_type": SIGNAL_USAGE_LOCATION,
            "expected_route_to": [ROUTE_CONSUMER_PROFILE],
        },
        {
            "review_id": "airpods-erika-long-review",
            "evidence_span": "homework",
            "expected_signal_type": SIGNAL_BEHAVIOR,
            "expected_route_to": [ROUTE_CONSUMER_PROFILE],
        },
        {
            "review_id": "airpods-erika-long-review",
            "evidence_span": "dance practice",
            "expected_signal_type": SIGNAL_BEHAVIOR,
            "expected_route_to": [ROUTE_CONSUMER_PROFILE],
        },
        {
            "review_id": "airpods-erika-long-review",
            "evidence_span": "I bought them because I wanted noise cancellation for a loud environment",
            "expected_signal_type": SIGNAL_PURCHASE_MOTIVATION,
            "expected_route_to": [ROUTE_PURCHASE_MOTIVES],
        },
        {
            "review_id": "airpods-erika-long-review",
            "evidence_span": "I expected stronger noise cancellation in loud rooms",
            "expected_signal_type": SIGNAL_EXPECTATION,
            "expected_route_to": [ROUTE_UNMET_NEEDS],
        },
        {
            "review_id": "airpods-erika-long-review",
            "evidence_span": "AirPod 3 and 2nd generation Pros",
            "expected_signal_type": SIGNAL_COMPARISON_OR_OTHER_PRODUCT,
            "expected_route_to": [ROUTE_AUDIT_FILTER],
        },
        {
            "review_id": "airpods-erika-long-review",
            "evidence_span": "case cover is cute",
            "expected_signal_type": SIGNAL_ACCESSORY_ONLY,
            "expected_route_to": [ROUTE_AUDIT_FILTER],
        },
        {
            "review_id": "airpods-erika-long-review",
            "evidence_span": "Overall good",
            "expected_signal_type": SIGNAL_GENERIC_OR_VAGUE,
            "expected_route_to": [ROUTE_AUDIT_FILTER],
        },
    ]


def _fragment_checks(results: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    signals_by_review = _signals_by_review(results)
    checks: list[dict[str, Any]] = []
    violations: list[dict[str, Any]] = []
    for expected in _required_fragment_expectations():
        by_evidence = _signal_by_evidence(signals_by_review.get(expected["review_id"], []))
        actual = by_evidence.get(expected["evidence_span"])
        check = {
            **expected,
            "actual_signal_type": actual.get("signal_type") if actual else None,
            "actual_route_to": actual.get("route_to") if actual else None,
            "status": "PASS"
            if actual
            and actual.get("signal_type") == expected["expected_signal_type"]
            and actual.get("route_to") == expected["expected_route_to"]
            else "FAIL",
        }
        checks.append(check)
        if check["status"] != "PASS":
            violations.append(check)
    return checks, violations


def _candidate_signal_types(results: list[dict[str, Any]], route: str) -> list[str]:
    return sorted(
        {
            str(signal.get("signal_type") or "")
            for result in results
            for signal in result["review_signals"]
            if route in signal.get("route_to", [])
        }
    )


def _build_summary(
    fixture: dict[str, Any],
    results: list[dict[str, Any]],
    *,
    gold_assimilation: dict[str, Any] | None = None,
    routing_projection: dict[str, Any] | None = None,
    fp_fn_comparison: dict[str, Any] | None = None,
) -> dict[str, Any]:
    signal_counts: Counter[str] = Counter()
    route_counts: Counter[str] = Counter()
    non_product_candidate_leaks: list[dict[str, Any]] = []
    five_star_product_negative_issue_candidates: list[dict[str, Any]] = []
    mixed_product_positive_label_candidates: list[dict[str, Any]] = []

    for result in results:
        signal_counts.update(result["signal_counts_by_type"])
        route_counts.update(result["route_counts"])
        rating = result.get("rating")
        has_mixed_review_signals = any(
            signal.get("signal_type") == SIGNAL_PRODUCT_NEGATIVE for signal in result["review_signals"]
        ) and any(signal.get("signal_type") == SIGNAL_PRODUCT_POSITIVE for signal in result["review_signals"])
        for signal in result["review_signals"]:
            route_to = signal.get("route_to", [])
            routed_to_issue_or_label = (
                ROUTE_CUSTOMER_ISSUE_CANDIDATE in route_to or ROUTE_CUSTOMER_LABEL_CANDIDATE in route_to
            )
            if signal.get("signal_type") not in {SIGNAL_PRODUCT_NEGATIVE, SIGNAL_PRODUCT_POSITIVE} and routed_to_issue_or_label:
                non_product_candidate_leaks.append(signal)
            if (
                rating == 5
                and signal.get("signal_type") == SIGNAL_PRODUCT_NEGATIVE
                and ROUTE_CUSTOMER_ISSUE_CANDIDATE in route_to
            ):
                five_star_product_negative_issue_candidates.append(signal)
            if (
                has_mixed_review_signals
                and signal.get("signal_type") == SIGNAL_PRODUCT_POSITIVE
                and ROUTE_CUSTOMER_LABEL_CANDIDATE in route_to
            ):
                mixed_product_positive_label_candidates.append(signal)

    fragment_checks, fragment_violations = _fragment_checks(results)
    issue_candidate_signal_types = _candidate_signal_types(results, ROUTE_CUSTOMER_ISSUE_CANDIDATE)
    label_candidate_signal_types = _candidate_signal_types(results, ROUTE_CUSTOMER_LABEL_CANDIDATE)
    candidate_source_violations = []
    if issue_candidate_signal_types != [SIGNAL_PRODUCT_NEGATIVE]:
        candidate_source_violations.append(
            {
                "route": ROUTE_CUSTOMER_ISSUE_CANDIDATE,
                "actual_signal_types": issue_candidate_signal_types,
                "expected_signal_types": [SIGNAL_PRODUCT_NEGATIVE],
            }
        )
    if label_candidate_signal_types != [SIGNAL_PRODUCT_POSITIVE]:
        candidate_source_violations.append(
            {
                "route": ROUTE_CUSTOMER_LABEL_CANDIDATE,
                "actual_signal_types": label_candidate_signal_types,
                "expected_signal_types": [SIGNAL_PRODUCT_POSITIVE],
            }
        )

    violations = non_product_candidate_leaks + fragment_violations + candidate_source_violations
    phase_2_3_status = (fp_fn_comparison or {}).get("status") or "NOT_RUN"
    return {
        "schema_version": REVIEW_SIGNAL_SCHEMA_VERSION,
        "ruleset_version": REVIEW_SIGNAL_RULESET_VERSION,
        "scope": fixture["scope"],
        "status": phase_2_3_status if phase_2_3_status != "NOT_RUN" else "PASS" if not violations else "REVIEW_NEEDED",
        "review_count": len(results),
        "signal_count": sum(signal_counts.values()),
        "signal_counts_by_type": dict(sorted(signal_counts.items())),
        "route_counts": dict(sorted(route_counts.items())),
        "customer_issue_candidate_signal_types": issue_candidate_signal_types,
        "customer_label_candidate_signal_types": label_candidate_signal_types,
        "acceptance_checks": {
            "non_product_to_issue_label_leakage_count": len(non_product_candidate_leaks),
            "customer_issue_candidates_only_from_product_negative": issue_candidate_signal_types
            == [SIGNAL_PRODUCT_NEGATIVE],
            "customer_label_candidates_only_from_product_positive": label_candidate_signal_types
            == [SIGNAL_PRODUCT_POSITIVE],
            "five_star_product_negative_issue_candidate_count": len(five_star_product_negative_issue_candidates),
            "mixed_review_product_positive_label_candidate_count": len(mixed_product_positive_label_candidates),
            "required_fragment_checks": fragment_checks,
        },
        "phase_2_3": {
            "gold_assimilation_status": (gold_assimilation or {}).get("status"),
            "routing_projection_status": (routing_projection or {}).get("status"),
            "fp_fn_comparison_status": (fp_fn_comparison or {}).get("status"),
            "local_gold_review_count": (gold_assimilation or {}).get("review_count"),
            "local_gold_fragment_count": (gold_assimilation or {}).get("fragment_count"),
            "dataset_source_counts": (gold_assimilation or {}).get("gold_coverage", {}).get("dataset_counts", {}),
            "source_kind_counts": (gold_assimilation or {}).get("gold_coverage", {}).get("source_kind_counts", {}),
            "baseline_metrics": (fp_fn_comparison or {}).get("overall", {}).get("baseline", {}),
            "shadow_metrics": (fp_fn_comparison or {}).get("overall", {}).get("signal_shadow", {}),
            "fp_fn_delta": (fp_fn_comparison or {}).get("overall", {}).get("fp_fn_delta", {}),
            "routing_leakage": (fp_fn_comparison or {}).get("routing_leakage", {}),
            "unresolved_mappings": (fp_fn_comparison or {}).get("unresolved_mappings", {}),
            "reviewable_case_count": len((fp_fn_comparison or {}).get("reviewable_cases", [])),
            "decision": (fp_fn_comparison or {}).get("decision", {}),
        },
        "violations": violations,
        "safety": review_signal_shadow_safety_flags(),
    }


def _build_fixture_results(fixture: dict[str, Any], results: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "schema_version": REVIEW_SIGNAL_SCHEMA_VERSION,
        "ruleset_version": REVIEW_SIGNAL_RULESET_VERSION,
        "scope": fixture["scope"],
        "fixture_path": str(FIXTURE_PATH.relative_to(ROOT)),
        "review_results": results,
        "safety": review_signal_shadow_safety_flags(),
    }


def _build_routing_table_artifact(fixture: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": "review-signals-routing-table.1",
        "ruleset_version": REVIEW_SIGNAL_RULESET_VERSION,
        "scope": fixture["scope"],
        "routing_table": review_signal_routing_table(),
        "safety": review_signal_shadow_safety_flags(),
    }


def _phase4_v1_occurrence(
    *,
    label_type: str,
    canonical: str,
    display_en: str,
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
        "display_label_zh": display_en,
        "aspect_key": aspect_key,
        "evidence_span": evidence,
        "evidence_start": -1,
        "evidence_end": -1,
        "confidence": "high",
        "source": "rule",
        "source_detail": "phase4_v1_fixture",
        "evidence_verified": True,
        "cluster_propagated": False,
        "schema_version": CUSTOMER_LABEL_OCCURRENCE_SCHEMA_VERSION,
        "ruleset_version": CUSTOMER_LABEL_OCCURRENCE_RULESET_VERSION,
        "display_allowed": True,
        "source_review_allowed": True,
        "verified_evidence": True,
        "legacy_fallback": False,
        "aspect_allowed": True,
        "context_allowed": True,
    }


def _phase4_review_with_v1() -> dict[str, Any]:
    return {
        "id": "phase4-review-v1",
        "session_id": "phase4-session",
        "product_id": "phase4-product",
        "content": "The zipper broke on day one.",
        "rating": 1,
        "category": "outdoor",
        "sub_category": "waders",
        "aspects_json": {
            "customer_label_occurrence_schema_version": CUSTOMER_LABEL_OCCURRENCE_SCHEMA_VERSION,
            "customer_label_occurrence_ruleset_version": CUSTOMER_LABEL_OCCURRENCE_RULESET_VERSION,
            "sub_category": "waders",
            "customer_label_occurrences": [
                _phase4_v1_occurrence(
                    label_type="issue",
                    canonical="zipper_fails",
                    display_en="Zipper Fails",
                    aspect_key="zipper_quality",
                    evidence="zipper broke",
                    comment_id="phase4-review-v1",
                )
            ],
        },
    }


def _phase4_review_without_v1() -> dict[str, Any]:
    return {
        "id": "phase4-review-guarded",
        "session_id": "phase4-session",
        "product_id": "phase4-product",
        "content": (
            "The seams leaked after one trip. They are comfortable for long walks. "
            "My daughter used them for fishing. I bought them for spring creeks. "
            "I expected more traction on slick rocks. The hanger works great. "
            "Overall good, but the missing phrase is not here."
        ),
        "rating": 4,
        "category": "outdoor",
        "sub_category": "waders",
    }


def _phase4_stored_occurrence(
    *,
    label_type: str,
    canonical: str,
    signal_type: str,
    route_to: list[str],
    evidence: str,
    display_en: str,
    aspect_key: str = "fit",
    **overrides: Any,
) -> dict[str, Any]:
    payload = {
        "label_type": label_type,
        "canonical_label_key": canonical,
        "display_label_en": display_en,
        "display_label_zh": display_en,
        "signal_type": signal_type,
        "route_to": route_to,
        "evidence_span": evidence,
        "evidence_verified": True,
        "display_allowed": True,
        "source_review_allowed": True,
        "aspect_allowed": True,
        "context_allowed": True,
        "maturity_allowed": True,
        "cluster_propagated": False,
        "legacy_fallback": False,
        "mapping_status": "mapped",
        "confidence": 0.93,
        "aspect_key": aspect_key,
    }
    payload.update(overrides)
    return payload


def _phase4_stored_shadow_with_mixed_occurrences() -> dict[str, Any]:
    return {
        "schema_version": "review-signal-stored-shadow.test",
        "frontstage_occurrences": [
            _phase4_stored_occurrence(
                label_type="issue",
                canonical="water_leaks_through",
                signal_type=SIGNAL_PRODUCT_NEGATIVE,
                route_to=["user_experience.negative", ROUTE_CUSTOMER_ISSUE_CANDIDATE],
                evidence="seams leaked",
                display_en="Water Leaks Through",
                aspect_key="waterproof",
            ),
            _phase4_stored_occurrence(
                label_type="highlight",
                canonical="comfortable_to_wear",
                signal_type=SIGNAL_PRODUCT_POSITIVE,
                route_to=["user_experience.positive", ROUTE_CUSTOMER_LABEL_CANDIDATE],
                evidence="comfortable",
                display_en="Comfortable To Wear",
                aspect_key="comfort",
            ),
            _phase4_stored_occurrence(
                label_type="issue",
                canonical="candidate:boot_seam_leak",
                signal_type=SIGNAL_PRODUCT_NEGATIVE,
                route_to=["user_experience.negative", ROUTE_CUSTOMER_ISSUE_CANDIDATE],
                evidence="seams leaked",
                display_en="Boot Seam Leak",
                aspect_key="seam_integrity",
            ),
            _phase4_stored_occurrence(
                label_type="highlight",
                canonical="",
                signal_type=SIGNAL_PRODUCT_POSITIVE,
                route_to=["user_experience.positive", ROUTE_CUSTOMER_LABEL_CANDIDATE],
                evidence="comfortable",
                display_en="Unresolved Comfort Variant",
                mapping_status="extraction_unresolved",
            ),
            _phase4_stored_occurrence(
                label_type="issue",
                canonical="family_use",
                signal_type=SIGNAL_AUDIENCE,
                route_to=[ROUTE_CONSUMER_PROFILE],
                evidence="daughter",
                display_en="Family Use",
            ),
            _phase4_stored_occurrence(
                label_type="highlight",
                canonical="purchase_reason",
                signal_type=SIGNAL_PURCHASE_MOTIVATION,
                route_to=[ROUTE_PURCHASE_MOTIVES],
                evidence="I bought them for spring creeks",
                display_en="Spring Creek Purchase",
            ),
            _phase4_stored_occurrence(
                label_type="issue",
                canonical="traction_expectation",
                signal_type=SIGNAL_EXPECTATION,
                route_to=[ROUTE_UNMET_NEEDS],
                evidence="I expected more traction on slick rocks",
                display_en="Traction Expectation",
            ),
            _phase4_stored_occurrence(
                label_type="issue",
                canonical="missing_wader_hanger",
                signal_type=SIGNAL_ACCESSORY_ONLY,
                route_to=[ROUTE_AUDIT_FILTER],
                evidence="hanger works great",
                display_en="Missing Wader Hanger",
            ),
            _phase4_stored_occurrence(
                label_type="highlight",
                canonical="overall_satisfied",
                signal_type=SIGNAL_AUDIT_ONLY,
                route_to=[ROUTE_AUDIT_FILTER],
                evidence="Overall good",
                display_en="Overall Satisfied",
                audit_only=True,
            ),
            _phase4_stored_occurrence(
                label_type="issue",
                canonical="water_leaks_through",
                signal_type=SIGNAL_PRODUCT_NEGATIVE,
                route_to=["user_experience.negative", ROUTE_CUSTOMER_ISSUE_CANDIDATE],
                evidence="missing seam evidence",
                display_en="Water Leaks Through",
                display_allowed=False,
            ),
        ],
    }


def _phase4_flag(**overrides: Any) -> ReviewSignalFrontstageFlag:
    payload = {"enabled": True, "session_ids": ("phase4-session",)}
    payload.update(overrides)
    return ReviewSignalFrontstageFlag(**payload)


def _phase4_raw_value(headers: list[str], row: list[str], header: str) -> str:
    return str(row[headers.index(header)])


def _phase4_four_path_snapshot(comments: list[dict[str, Any]]) -> dict[str, Any]:
    issue_rows = build_specific_issue_rows(comments, locale="en", limit=20)
    highlight_rows = build_customer_highlight_rows(comments, locale="en", limit=20)
    raw_headers, raw_rows = _build_comments_data(comments, include_specific_issue=True)
    return {
        "top_issue_keys": [str(row.get("canonical_issue_key") or "") for row in issue_rows],
        "top_highlight_keys": [str(row.get("canonical_highlight_key") or "") for row in highlight_rows],
        "detail_issue_tags": [customer_issue_tags_for_comment(comment, locale="en") for comment in comments],
        "detail_highlight_tags": [customer_highlight_tags_for_comment(comment, locale="en") for comment in comments],
        "raw_issue_labels": [_phase4_raw_value(raw_headers, row, "客户痛点") for row in raw_rows],
        "raw_issue_evidence": [_phase4_raw_value(raw_headers, row, "痛点证据") for row in raw_rows],
        "raw_highlight_labels": [_phase4_raw_value(raw_headers, row, "客户亮点") for row in raw_rows],
        "raw_highlight_evidence": [_phase4_raw_value(raw_headers, row, "亮点证据") for row in raw_rows],
        "single_issue_keys": [
            str(occurrence.get("canonical_issue_key") or "")
            for comment in comments
            for occurrence in iter_specific_issue_occurrences(comment, locale="en")
        ],
        "single_highlight_keys": [
            str(occurrence.get("canonical_highlight_key") or "")
            for comment in comments
            for occurrence in iter_customer_highlight_occurrences(comment, locale="en")
        ],
        "single_issue_evidence_verified": [
            bool(occurrence.get("verified_evidence"))
            for comment in comments
            for occurrence in iter_specific_issue_occurrences(comment, locale="en")
        ],
        "single_highlight_evidence_verified": [
            bool(occurrence.get("verified_evidence"))
            for comment in comments
            for occurrence in iter_customer_highlight_occurrences(comment, locale="en")
        ],
    }


def _phase4_path_check(name: str, actual: Any, expected: Any) -> dict[str, Any]:
    return {
        "name": name,
        "status": "PASS" if actual == expected else "FAIL",
        "actual": actual,
        "expected": expected,
    }


def _build_phase4_implementation_artifact() -> dict[str, Any]:
    stored_shadow = _phase4_stored_shadow_with_mixed_occurrences()
    flag_off_review = _phase4_review_with_v1()
    flag_off_model = build_review_signal_frontstage_read_model(
        flag_off_review,
        flag=ReviewSignalFrontstageFlag(),
        stored_shadow=stored_shadow,
    )
    flag_off_snapshot = _phase4_four_path_snapshot(
        [attach_review_signal_frontstage_adapter_for_local_test(flag_off_review, flag_off_model)]
    )

    guarded_review = _phase4_review_without_v1()
    guarded_model = build_review_signal_frontstage_read_model(
        guarded_review,
        flag=_phase4_flag(),
        stored_shadow=stored_shadow,
    )
    guarded_snapshot = _phase4_four_path_snapshot(
        [attach_review_signal_frontstage_adapter_for_local_test(guarded_review, guarded_model)]
    )

    invalid_flag = resolve_review_signal_frontstage_config({"enabled": "maybe"}, source="replay").effective_feature_flag
    fail_closed_cases = [
        (
            "invalid_config",
            invalid_flag,
            stored_shadow,
            "config_invalid",
        ),
        (
            "scope_miss",
            ReviewSignalFrontstageFlag(enabled=True, session_ids=("other-session",)),
            stored_shadow,
            "scope_not_matched",
        ),
        ("stored_shadow_missing", _phase4_flag(), None, "review_signal_stored_shadow_missing"),
        ("rollback", _phase4_flag(rollback_session_ids=("phase4-session",)), stored_shadow, "rollback_session"),
        ("kill_switch", _phase4_flag(kill_switch=True), stored_shadow, "kill_switch_global"),
    ]
    fail_closed_models = [
        build_review_signal_frontstage_read_model(
            {**flag_off_review, "id": case_name},
            flag=flag,
            stored_shadow=case_stored_shadow,
        )
        for case_name, flag, case_stored_shadow, _expected_reason in fail_closed_cases
    ]

    checks = [
        _phase4_path_check("flag_off_read_path", flag_off_model["read_path"], READ_PATH_V1_CURRENT),
        _phase4_path_check("flag_off_top10_v1_issue", flag_off_snapshot["top_issue_keys"], ["zipper_fails"]),
        _phase4_path_check("guarded_read_path", guarded_model["read_path"], READ_PATH_REVIEW_SIGNAL_STORED_SHADOW),
        _phase4_path_check(
            "guarded_selected_keys",
            frontstage_keys_from_review_signal_read_model(guarded_model),
            {"issue": ["water_leaks_through"], "highlight": ["comfortable_to_wear"]},
        ),
        _phase4_path_check("results_top10_issue", guarded_snapshot["top_issue_keys"], ["water_leaks_through"]),
        _phase4_path_check(
            "results_top10_label",
            guarded_snapshot["top_highlight_keys"],
            ["comfortable_to_wear"],
        ),
        _phase4_path_check(
            "single_review_detail_issue_chips",
            guarded_snapshot["detail_issue_tags"],
            [["Water Leaks Through"]],
        ),
        _phase4_path_check(
            "single_review_detail_label_chips",
            guarded_snapshot["detail_highlight_tags"],
            [["Comfortable To Wear"]],
        ),
        _phase4_path_check("raw_review_export_issue", guarded_snapshot["raw_issue_labels"], ["Water Leaks Through"]),
        _phase4_path_check(
            "raw_review_export_label",
            guarded_snapshot["raw_highlight_labels"],
            ["Comfortable To Wear"],
        ),
        _phase4_path_check(
            "single_tag_download_issue_keys",
            guarded_snapshot["single_issue_keys"],
            ["water_leaks_through"],
        ),
        _phase4_path_check(
            "single_tag_download_label_keys",
            guarded_snapshot["single_highlight_keys"],
            ["comfortable_to_wear"],
        ),
        _phase4_path_check(
            "single_tag_download_verified_evidence",
            guarded_snapshot["single_issue_evidence_verified"] + guarded_snapshot["single_highlight_evidence_verified"],
            [True, True],
        ),
        _phase4_path_check(
            "fail_closed_reasons",
            [model["fallback_reason"] for model in fail_closed_models],
            [expected_reason for *_rest, expected_reason in fail_closed_cases],
        ),
    ]
    compatibility = {
        "status": "PASS" if all(check["status"] == "PASS" for check in checks) else "REVIEW_NEEDED",
        "checks": checks,
        "paths": {
            "results_top10": {
                "status": "PASS"
                if guarded_snapshot["top_issue_keys"] == ["water_leaks_through"]
                and guarded_snapshot["top_highlight_keys"] == ["comfortable_to_wear"]
                else "FAIL",
                "snapshot": {
                    "issue_keys": guarded_snapshot["top_issue_keys"],
                    "label_keys": guarded_snapshot["top_highlight_keys"],
                },
            },
            "single_review_detail": {
                "status": "PASS"
                if guarded_snapshot["detail_issue_tags"] == [["Water Leaks Through"]]
                and guarded_snapshot["detail_highlight_tags"] == [["Comfortable To Wear"]]
                else "FAIL",
                "snapshot": {
                    "issue_chips": guarded_snapshot["detail_issue_tags"],
                    "label_chips": guarded_snapshot["detail_highlight_tags"],
                },
            },
            "raw_review_export": {
                "status": "PASS"
                if guarded_snapshot["raw_issue_labels"] == ["Water Leaks Through"]
                and guarded_snapshot["raw_highlight_labels"] == ["Comfortable To Wear"]
                else "FAIL",
                "snapshot": {
                    "issue_labels": guarded_snapshot["raw_issue_labels"],
                    "issue_evidence": guarded_snapshot["raw_issue_evidence"],
                    "label_labels": guarded_snapshot["raw_highlight_labels"],
                    "label_evidence": guarded_snapshot["raw_highlight_evidence"],
                },
            },
            "single_tag_download": {
                "status": "PASS"
                if guarded_snapshot["single_issue_keys"] == ["water_leaks_through"]
                and guarded_snapshot["single_highlight_keys"] == ["comfortable_to_wear"]
                and guarded_snapshot["single_issue_evidence_verified"] == [True]
                and guarded_snapshot["single_highlight_evidence_verified"] == [True]
                else "FAIL",
                "snapshot": {
                    "issue_keys": guarded_snapshot["single_issue_keys"],
                    "label_keys": guarded_snapshot["single_highlight_keys"],
                    "issue_evidence_verified": guarded_snapshot["single_issue_evidence_verified"],
                    "label_evidence_verified": guarded_snapshot["single_highlight_evidence_verified"],
                },
            },
        },
        "local_test_adapter": {
            "used": True,
            "production_connected": False,
            "adapter_field": "customer_label_v2_frontstage_read_model",
        },
    }
    read_models = [flag_off_model, guarded_model, *fail_closed_models]
    return build_review_signal_phase4_implementation_artifact(
        read_models,
        four_path_compatibility=compatibility,
    )


def main() -> None:
    fixture = _load_json(FIXTURE_PATH)
    results = [
        run_review_signal_shadow(sample, signal_candidates=sample["review_signals"])
        for sample in fixture["samples"]
    ]
    gold_specs = build_local_gold_review_specs()
    gold_assimilation = _build_gold_assimilation_artifact(gold_specs)
    routing_projection, fp_fn_comparison = _build_routing_projection_and_comparison_artifacts(gold_specs)
    summary = _build_summary(
        fixture,
        results,
        gold_assimilation=gold_assimilation,
        routing_projection=routing_projection,
        fp_fn_comparison=fp_fn_comparison,
    )
    fixture_results = _build_fixture_results(fixture, results)
    routing_table = _build_routing_table_artifact(fixture)
    phase4_implementation = _build_phase4_implementation_artifact()

    _write_json(SUMMARY_PATH, summary)
    _write_json(ROUTING_TABLE_PATH, routing_table)
    _write_json(FIXTURE_RESULTS_PATH, fixture_results)
    _write_json(GOLD_ASSIMILATION_PATH, gold_assimilation)
    _write_json(ROUTING_PROJECTION_PATH, routing_projection)
    _write_json(FP_FN_COMPARISON_PATH, fp_fn_comparison)
    _write_json(PHASE4_IMPLEMENTATION_PATH, phase4_implementation)
    print(
        json.dumps(
            {
                "status": summary["status"],
                "phase4_implementation_status": phase4_implementation["status"],
                "review_count": summary["review_count"],
                "signal_count": summary["signal_count"],
                "local_gold_review_count": gold_assimilation["review_count"],
                "local_gold_fragment_count": gold_assimilation["fragment_count"],
                "non_product_to_issue_label_leakage_count": fp_fn_comparison["routing_leakage"][
                    "non_product_to_issue_label_leakage_count"
                ],
                "unresolved_mapping_count": fp_fn_comparison["unresolved_mappings"]["unresolved_mapping_count"],
                "artifact_dir": str(ARTIFACT_DIR.relative_to(ROOT)),
                "phase4_artifact": str(PHASE4_IMPLEMENTATION_PATH.relative_to(ROOT)),
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
