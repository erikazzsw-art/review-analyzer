from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from backend_api.app.services.review_signal_shadow import (
    ROUTE_AUDIT_FILTER,
    ROUTE_CONSUMER_PROFILE,
    ROUTE_CUSTOMER_ISSUE_CANDIDATE,
    ROUTE_CUSTOMER_LABEL_CANDIDATE,
    ROUTE_PURCHASE_MOTIVES,
    ROUTE_UNMET_NEEDS,
    SIGNAL_ACCESSORY_ONLY,
    SIGNAL_AUDIENCE,
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
    review_signal_routing_table,
    run_review_signal_shadow,
)

FIXTURES_DIR = Path(__file__).parent / "fixtures"
AIRPODS_FIXTURE = FIXTURES_DIR / "review_signal_step9_1_airpods_minimal.json"


def _load_fixture() -> dict[str, Any]:
    return json.loads(AIRPODS_FIXTURE.read_text(encoding="utf-8"))


def _sample(sample_id: str) -> dict[str, Any]:
    for sample in _load_fixture()["samples"]:
        if sample["id"] == sample_id:
            return sample
    raise AssertionError(f"sample not found: {sample_id}")


def _signal(
    signal_type: str,
    evidence: str,
    *,
    polarity: str = "neutral",
    scope: str = "non_product_context",
    confidence: float = 0.9,
) -> dict[str, Any]:
    return {
        "signal_type": signal_type,
        "polarity": polarity,
        "evidence_span": evidence,
        "current_product_scope": scope,
        "confidence": confidence,
        "reason": f"{signal_type} fixture",
    }


def _result_for_sample(sample_id: str) -> dict[str, Any]:
    sample = _sample(sample_id)
    return run_review_signal_shadow(sample, signal_candidates=sample["review_signals"])


def _signals_by_evidence(result: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {signal["evidence_span"]: signal for signal in result["review_signals"]}


def test_review_signal_routing_table_contract() -> None:
    table = review_signal_routing_table()

    assert set(table) >= {
        SIGNAL_PRODUCT_POSITIVE,
        SIGNAL_PRODUCT_NEGATIVE,
        SIGNAL_AUDIENCE,
        SIGNAL_USAGE_LOCATION,
        SIGNAL_USAGE_TIME,
        SIGNAL_BEHAVIOR,
        SIGNAL_EXPECTATION,
        SIGNAL_PURCHASE_MOTIVATION,
        SIGNAL_COMPARISON_OR_OTHER_PRODUCT,
        SIGNAL_ACCESSORY_ONLY,
        SIGNAL_SHIPPING_SERVICE,
        SIGNAL_GENERIC_OR_VAGUE,
    }
    assert table[SIGNAL_PRODUCT_POSITIVE]["route_to"] == [
        "user_experience.positive",
        ROUTE_CUSTOMER_LABEL_CANDIDATE,
    ]
    assert table[SIGNAL_PRODUCT_NEGATIVE]["route_to"] == [
        "user_experience.negative",
        ROUTE_CUSTOMER_ISSUE_CANDIDATE,
    ]
    assert table[SIGNAL_AUDIENCE]["route_to"] == [ROUTE_CONSUMER_PROFILE]
    assert table[SIGNAL_USAGE_LOCATION]["route_to"] == [ROUTE_CONSUMER_PROFILE]
    assert table[SIGNAL_USAGE_TIME]["route_to"] == [ROUTE_CONSUMER_PROFILE]
    assert table[SIGNAL_BEHAVIOR]["route_to"] == [ROUTE_CONSUMER_PROFILE]
    assert table[SIGNAL_PURCHASE_MOTIVATION]["route_to"] == [ROUTE_PURCHASE_MOTIVES]
    assert table[SIGNAL_EXPECTATION]["route_to"] == [ROUTE_UNMET_NEEDS]
    assert table[SIGNAL_COMPARISON_OR_OTHER_PRODUCT]["route_to"] == [ROUTE_AUDIT_FILTER]
    assert table[SIGNAL_ACCESSORY_ONLY]["route_to"] == [ROUTE_AUDIT_FILTER]
    assert table[SIGNAL_SHIPPING_SERVICE]["route_to"] == [ROUTE_AUDIT_FILTER]
    assert table[SIGNAL_GENERIC_OR_VAGUE]["route_to"] == [ROUTE_AUDIT_FILTER]


def test_non_product_signals_do_not_route_to_customer_issue_or_label() -> None:
    content = (
        "My daughter uses them around the house after school. I bought them for online classes. "
        "Shipping was fast. The case cover is cute. Nice product."
    )
    result = run_review_signal_shadow(
        content=content,
        review_id="non-product-routing",
        signal_candidates=[
            _signal(SIGNAL_AUDIENCE, "daughter"),
            _signal(SIGNAL_USAGE_LOCATION, "around the house"),
            _signal(SIGNAL_USAGE_TIME, "after school"),
            _signal(SIGNAL_BEHAVIOR, "uses them"),
            _signal(SIGNAL_PURCHASE_MOTIVATION, "I bought them for online classes", scope="current_product_context"),
            _signal(SIGNAL_EXPECTATION, "online classes", scope="current_product_context"),
            _signal(SIGNAL_SHIPPING_SERVICE, "Shipping was fast", scope="shipping_service"),
            _signal(SIGNAL_ACCESSORY_ONLY, "case cover is cute", scope="accessory_only"),
            _signal(SIGNAL_GENERIC_OR_VAGUE, "Nice product", scope="unclear"),
        ],
    )

    projection = result["routing_projection"]
    assert projection["customer_issue_candidates"] == []
    assert projection["customer_label_candidates"] == []
    assert projection["leakage_violations"] == []


def test_product_negative_in_five_star_review_routes_to_issue_candidate() -> None:
    result = _result_for_sample("airpods-erika-long-review")

    issue_spans = {
        signal["evidence_span"]
        for signal in result["routing_projection"]["customer_issue_candidates"]
    }
    assert result["rating"] == 5
    assert {
        "noise cancellation is poor",
        "charging indicator is unclear",
        "fall out when she dances",
    } <= issue_spans
    assert all(
        signal["signal_type"] == SIGNAL_PRODUCT_NEGATIVE
        for signal in result["routing_projection"]["customer_issue_candidates"]
    )


def test_product_positive_in_mixed_review_routes_to_label_candidate() -> None:
    result = _result_for_sample("airpods-mixed-positive-and-negative")

    label_spans = {
        signal["evidence_span"]
        for signal in result["routing_projection"]["customer_label_candidates"]
    }
    assert {"sound is crisp", "pairing is easy"} <= label_spans
    assert all(
        signal["signal_type"] == SIGNAL_PRODUCT_POSITIVE
        for signal in result["routing_projection"]["customer_label_candidates"]
    )


def test_context_signals_route_to_existing_non_label_modules() -> None:
    result = _result_for_sample("airpods-context-routing")
    projection = result["routing_projection"]

    consumer_spans = {signal["evidence_span"] for signal in projection["consumer_profile_signals"]}
    motive_spans = {signal["evidence_span"] for signal in projection["purchase_motive_signals"]}

    assert {"daughter", "after school at night", "doing homework"} <= consumer_spans
    assert motive_spans == {"I bought them for online classes"}
    assert projection["customer_issue_candidates"] == []
    assert projection["customer_label_candidates"] == []


def test_expectation_routes_to_unmet_needs() -> None:
    result = _result_for_sample("airpods-erika-long-review")

    unmet_spans = {signal["evidence_span"] for signal in result["routing_projection"]["unmet_need_signals"]}
    assert "I expected stronger noise cancellation in loud rooms" in unmet_spans
    assert all(
        ROUTE_CUSTOMER_ISSUE_CANDIDATE not in signal["route_to"]
        and ROUTE_CUSTOMER_LABEL_CANDIDATE not in signal["route_to"]
        for signal in result["routing_projection"]["unmet_need_signals"]
    )


def test_old_product_accessory_shipping_and_generic_default_to_audit_filter() -> None:
    result = _result_for_sample("airpods-audit-filter-review")
    audit_by_type = {
        signal["signal_type"]: signal
        for signal in result["routing_projection"]["audit_filter_signals"]
    }

    assert {
        SIGNAL_COMPARISON_OR_OTHER_PRODUCT,
        SIGNAL_ACCESSORY_ONLY,
        SIGNAL_SHIPPING_SERVICE,
        SIGNAL_GENERIC_OR_VAGUE,
    } <= set(audit_by_type)
    assert result["routing_projection"]["customer_issue_candidates"] == []
    assert result["routing_projection"]["customer_label_candidates"] == []


def test_airpods_long_review_core_fragments_are_split_before_issue_label_routing() -> None:
    result = _result_for_sample("airpods-erika-long-review")
    by_evidence = _signals_by_evidence(result)

    for span in ("comfortable", "fit is secure", "battery life is great"):
        signal = by_evidence[span]
        assert signal["signal_type"] == SIGNAL_PRODUCT_POSITIVE
        assert signal["route_to"] == ["user_experience.positive", ROUTE_CUSTOMER_LABEL_CANDIDATE]

    for span in ("charging indicator is unclear", "noise cancellation is poor", "fall out when she dances"):
        signal = by_evidence[span]
        assert signal["signal_type"] == SIGNAL_PRODUCT_NEGATIVE
        assert signal["route_to"] == ["user_experience.negative", ROUTE_CUSTOMER_ISSUE_CANDIDATE]

    for span in ("daughter", "son", "kids"):
        signal = by_evidence[span]
        assert signal["signal_type"] == SIGNAL_AUDIENCE
        assert signal["route_to"] == [ROUTE_CONSUMER_PROFILE]

    for span in ("around the house", "homework", "dance practice"):
        signal = by_evidence[span]
        assert signal["signal_type"] in {SIGNAL_USAGE_LOCATION, SIGNAL_BEHAVIOR}
        assert signal["route_to"] == [ROUTE_CONSUMER_PROFILE]

    assert by_evidence["I bought them because I wanted noise cancellation for a loud environment"]["route_to"] == [
        ROUTE_PURCHASE_MOTIVES
    ]
    assert by_evidence["I expected stronger noise cancellation in loud rooms"]["route_to"] == [ROUTE_UNMET_NEEDS]

    for span in ("AirPod 3 and 2nd generation Pros", "case cover is cute", "Overall good"):
        assert by_evidence[span]["route_to"] == [ROUTE_AUDIT_FILTER]

    assert result["routing_projection"]["leakage_violations"] == []
