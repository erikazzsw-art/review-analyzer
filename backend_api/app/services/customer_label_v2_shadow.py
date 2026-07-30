from __future__ import annotations

import copy
import json
import re
from collections import Counter, defaultdict
from collections.abc import Callable
from dataclasses import asdict, dataclass
from typing import Any

from backend_api.app.services import specific_issue as v1_labels
from backend_api.app.services.customer_label_catalog import resolve_customer_label
from backend_api.app.services.customer_label_v2_maturity import (
    CustomerLabelMaturity,
    maturity_gate_decision,
    resolve_customer_label_maturity,
)
from backend_api.app.services.specific_issue import (
    CUSTOMER_LABEL_OCCURRENCE_RULESET_VERSION,
    CUSTOMER_LABEL_OCCURRENCE_SCHEMA_VERSION,
    iter_customer_highlight_occurrences,
    iter_specific_issue_occurrences,
)

CUSTOMER_LABEL_V2_SCHEMA_VERSION = "2.0"
CUSTOMER_LABEL_V2_PROMPT_VERSION = "customer-label-v2.0-shadow"
CUSTOMER_LABEL_V2_VERIFIER_RULESET_VERSION = "customer-label-verifier-v2.0-shadow"
CUSTOMER_LABEL_V2_MOCK_MODEL = "mock-v1-display-replay"
DISPLAY_CONFIDENCE_THRESHOLD = 0.65
CANDIDATE_POOL_PENDING_STATUS = "pending"
CANDIDATE_POOL_REVIEW_ACTIONS = {
    "accept",
    "reject",
    "correct_label",
    "correct_evidence",
    "needs_new_label",
    "ignore",
}

VALID_LABEL_TYPES = {"issue", "highlight"}
VALID_POLARITIES = {"negative", "positive", "mixed", "neutral"}
FOCUS_WADERS_LABELS = {
    ("issue", "water_leaks_through"),
    ("issue", "pocket_not_waterproof"),
    ("highlight", "keeps_water_out"),
    ("highlight", "fits_as_expected"),
    ("highlight", "good_value_for_the_price"),
    ("highlight", "holds_up_well"),
}
GENERIC_PROOF_REQUIRED_LABELS = {
    "water_leaks_through",
    "keeps_water_out",
    "fits_as_expected",
    "good_value_for_the_price",
    "holds_up_well",
}
@dataclass(frozen=True)
class VerificationContext:
    review: dict[str, Any]
    content: str
    category: str
    sub_category: str
    maturity: CustomerLabelMaturity


@dataclass(frozen=True)
class VerificationOutcome:
    occurrence: dict[str, Any] | None
    audit_occurrence: dict[str, Any] | None
    candidate_pool_item: dict[str, Any] | None


@dataclass(frozen=True)
class CandidatePoolItem:
    candidate_id: str
    review_id: Any
    session_id: Any
    product_id: Any
    category: str
    sub_category: str
    label_type: str
    canonical_label_key: str
    raw_label: str
    evidence_candidate: str
    confidence: float
    downgrade_reasons: list[str]
    top_impact_score: float
    review_status: str = CANDIDATE_POOL_PENDING_STATUS

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def _title_from_key(key: str) -> str:
    return " ".join(part.capitalize() for part in key.replace("candidate:", "").split("_") if part)


def _clean_label_type(value: Any) -> str:
    cleaned = str(value or "").strip().lower()
    return cleaned if cleaned in VALID_LABEL_TYPES else ""


def _candidate_confidence(value: Any) -> float:
    try:
        confidence = float(value)
    except (TypeError, ValueError):
        return 0.0
    return min(max(confidence, 0.0), 1.0)


def _v1_confidence(value: float) -> str:
    if value >= 0.8:
        return "high"
    if value >= DISPLAY_CONFIDENCE_THRESHOLD:
        return "medium"
    return "low"


def _confidence_to_float(value: Any) -> float:
    if isinstance(value, (int, float)):
        return _candidate_confidence(value)
    cleaned = str(value or "").strip().lower()
    if cleaned == "high":
        return 0.92
    if cleaned == "medium":
        return 0.74
    if cleaned == "low":
        return 0.48
    return _candidate_confidence(value)


def _normalize_text(value: str) -> str:
    value = value.replace("&", " and ")
    value = re.sub(r"[^a-z0-9]+", " ", value.lower())
    return re.sub(r"\s+", " ", value).strip()


def _locate_evidence(content: str, evidence: str) -> dict[str, Any]:
    evidence = str(evidence or "").strip()
    if not content or not evidence:
        return {
            "evidence_span": evidence,
            "evidence_start": -1,
            "evidence_end": -1,
            "evidence_verified": False,
        }
    start = content.find(evidence)
    if start < 0:
        start = content.lower().find(evidence.lower())
    if start < 0:
        return {
            "evidence_span": evidence,
            "evidence_start": -1,
            "evidence_end": -1,
            "evidence_verified": False,
        }
    return {
        "evidence_span": content[start : start + len(evidence)],
        "evidence_start": start,
        "evidence_end": start + len(evidence),
        "evidence_verified": True,
    }


def _append_reason(reasons: list[str], reason: str) -> None:
    if reason not in reasons:
        reasons.append(reason)


def _verification_context(review: dict[str, Any], maturity: CustomerLabelMaturity) -> VerificationContext:
    return VerificationContext(
        review=review,
        content=str(review.get("content") or ""),
        category=str(review.get("category") or "outdoor"),
        sub_category=str(review.get("sub_category") or "waders"),
        maturity=maturity,
    )


def _is_frontstage_occurrence(occurrence: dict[str, Any]) -> bool:
    return bool(
        occurrence.get("display_allowed") is True
        and occurrence.get("source_review_allowed") is True
        and occurrence.get("evidence_verified") is True
        and occurrence.get("evidence_span")
        and occurrence.get("cluster_propagated") is False
        and occurrence.get("legacy_fallback") is False
        and occurrence.get("aspect_allowed") is True
        and occurrence.get("context_allowed") is True
        and occurrence.get("maturity_allowed") is True
    )


def _display_gate_allowed(
    *,
    projected: dict[str, Any],
    downgrade_reasons: list[str],
    maturity_allowed: bool,
    legacy_fallback: bool,
) -> bool:
    return bool(
        not downgrade_reasons
        and projected.get("source_review_allowed")
        and projected.get("evidence_verified")
        and projected.get("aspect_allowed") is not False
        and projected.get("context_allowed") is not False
        and maturity_allowed
        and not projected.get("cluster_propagated")
        and not legacy_fallback
    )


def _collect_downgrade_reasons(audit_occurrences: list[dict[str, Any]]) -> list[str]:
    reasons: list[str] = []
    for occurrence in audit_occurrences:
        for reason in occurrence.get("downgrade_reasons") or []:
            _append_reason(reasons, str(reason))
    return reasons


def _review_for_v1_replay(review: dict[str, Any]) -> dict[str, Any]:
    replay = copy.deepcopy(review)
    replay.setdefault("category", review.get("category") or "outdoor")
    replay.setdefault("sub_category", review.get("sub_category") or "waders")
    if not v1_labels.coerce_aspects_json(replay.get("aspects_json")):
        replay["aspects_json"] = {
            "customer_label_occurrence_schema_version": CUSTOMER_LABEL_OCCURRENCE_SCHEMA_VERSION,
            "customer_label_occurrence_ruleset_version": CUSTOMER_LABEL_OCCURRENCE_RULESET_VERSION,
            "sub_category": replay.get("sub_category") or replay.get("category") or "",
            "customer_label_occurrences": [],
            "aspects": [],
        }
    return replay


def v1_display_keys_for_review(review: dict[str, Any]) -> dict[str, list[str]]:
    replay = _review_for_v1_replay(review)
    keys: dict[str, list[str]] = {"issue": [], "highlight": []}
    for label_type, iterator, canonical_field in (
        ("issue", iter_specific_issue_occurrences, "canonical_issue_key"),
        ("highlight", iter_customer_highlight_occurrences, "canonical_highlight_key"),
    ):
        for occurrence in iterator(replay, locale="en"):
            if not _is_v1_frontstage_occurrence(occurrence):
                continue
            key = str(occurrence.get(canonical_field) or occurrence.get("canonical_label_key") or "").strip()
            if key and key not in keys[label_type]:
                keys[label_type].append(key)
    return keys


def _is_v1_frontstage_occurrence(occurrence: dict[str, Any]) -> bool:
    return bool(
        occurrence.get("display_allowed") is not False
        and occurrence.get("source_review_allowed")
        and occurrence.get("verified_evidence")
        and occurrence.get("evidence_span")
        and not occurrence.get("cluster_propagated")
        and not occurrence.get("legacy_fallback")
        and occurrence.get("aspect_allowed") is not False
        and occurrence.get("context_allowed") is not False
    )


def _candidate_from_v1_occurrence(occurrence: dict[str, Any]) -> dict[str, Any]:
    label_type = str(occurrence.get("type") or "")
    canonical = str(occurrence.get("canonical_label_key") or "").strip()
    display_en = str(occurrence.get("display_label_en") or _title_from_key(canonical)).strip()
    display_zh = str(occurrence.get("display_label_zh") or display_en).strip()
    confidence = _confidence_to_float(occurrence.get("confidence"))
    polarity = "negative" if label_type == "issue" else "positive"
    return {
        "label_type": label_type,
        "canonical_label_key": canonical,
        "raw_label": str(occurrence.get("raw_label") or display_en).strip(),
        "display_label_en": display_en,
        "display_label_zh": display_zh,
        "aspect_key": str(occurrence.get("aspect_key") or "unknown").strip() or "unknown",
        "polarity": polarity,
        "evidence_candidate": str(occurrence.get("evidence_span") or "").strip(),
        "evidence_start": None,
        "evidence_end": None,
        "confidence": confidence,
        "reason": "Mock v2 shadow candidate replayed from v1 verified display occurrence.",
    }


def build_mock_llm_payload_from_v1_display(review: dict[str, Any]) -> dict[str, Any]:
    replay = _review_for_v1_replay(review)
    candidates: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str, str]] = set()
    for iterator in (iter_specific_issue_occurrences, iter_customer_highlight_occurrences):
        for occurrence in iterator(replay, locale="en"):
            if not _is_v1_frontstage_occurrence(occurrence):
                continue
            candidate = _candidate_from_v1_occurrence(occurrence)
            key = (
                candidate["label_type"],
                candidate["canonical_label_key"],
                candidate["aspect_key"],
                candidate["evidence_candidate"].lower(),
            )
            if key in seen:
                continue
            seen.add(key)
            candidates.append(candidate)
    return {
        "customer_label_schema_version": CUSTOMER_LABEL_V2_SCHEMA_VERSION,
        "prompt_version": CUSTOMER_LABEL_V2_PROMPT_VERSION,
        "model": CUSTOMER_LABEL_V2_MOCK_MODEL,
        "source": "mock_v1_display_replay",
        "sub_category": str(replay.get("sub_category") or replay.get("category") or ""),
        "category": str(replay.get("category") or "outdoor"),
        "language": "en",
        "label_candidates": candidates,
    }


def _parse_llm_payload(llm_output: str | dict[str, Any] | list[dict[str, Any]]) -> tuple[dict[str, Any] | None, str | None]:
    if isinstance(llm_output, str):
        try:
            parsed = json.loads(llm_output)
        except json.JSONDecodeError:
            return None, "invalid_json"
    else:
        parsed = copy.deepcopy(llm_output)
    if isinstance(parsed, list):
        parsed = {"label_candidates": parsed}
    if not isinstance(parsed, dict):
        return None, "schema_invalid"
    if not isinstance(parsed.get("label_candidates"), list):
        return None, "schema_invalid"
    return parsed, None


def _audit_occurrence(
    *,
    review_id: Any,
    candidate: dict[str, Any] | None,
    downgrade_reasons: list[str],
    evidence: dict[str, Any] | None = None,
    label_type: str = "",
) -> dict[str, Any]:
    candidate = candidate or {}
    canonical = str(candidate.get("canonical_label_key") or "").strip()
    resolved_type = _clean_label_type(candidate.get("label_type")) or label_type or "audit"
    evidence = evidence or {
        "evidence_span": str(candidate.get("evidence_candidate") or "").strip(),
        "evidence_start": -1,
        "evidence_end": -1,
        "evidence_verified": False,
    }
    return {
        "review_id": review_id,
        "label_type": resolved_type,
        "canonical_label_key": canonical,
        "raw_label": str(candidate.get("raw_label") or "").strip(),
        "display_label_en": str(candidate.get("display_label_en") or _title_from_key(canonical)).strip(),
        "display_label_zh": str(candidate.get("display_label_zh") or "").strip(),
        "aspect_key": str(candidate.get("aspect_key") or "unknown").strip() or "unknown",
        "polarity": str(candidate.get("polarity") or "").strip().lower(),
        "evidence_span": evidence["evidence_span"],
        "evidence_start": evidence["evidence_start"],
        "evidence_end": evidence["evidence_end"],
        "confidence": _candidate_confidence(candidate.get("confidence")),
        "source": "llm",
        "source_review_allowed": False,
        "evidence_verified": bool(evidence["evidence_verified"]),
        "aspect_allowed": "aspect_blocked" not in downgrade_reasons,
        "context_allowed": "context_blocked" not in downgrade_reasons,
        "maturity_allowed": "maturity_blocked" not in downgrade_reasons,
        "display_allowed": False,
        "cluster_propagated": False,
        "legacy_fallback": False,
        "downgrade_reasons": downgrade_reasons,
        "verifier_reasons": [],
    }


def _candidate_pool_item(
    *,
    review: dict[str, Any],
    candidate: dict[str, Any],
    downgrade_reasons: list[str],
    index: int,
) -> dict[str, Any]:
    canonical = str(candidate.get("canonical_label_key") or "").strip()
    confidence = _candidate_confidence(candidate.get("confidence"))
    return CandidatePoolItem(
        candidate_id=f"shadow:{review.get('id', 'row')}:{index}:{canonical or 'unknown'}",
        review_id=review.get("id"),
        session_id=review.get("session_id"),
        product_id=review.get("product_id"),
        category=str(review.get("category") or "outdoor"),
        sub_category=str(review.get("sub_category") or "waders"),
        label_type=_clean_label_type(candidate.get("label_type")) or "issue",
        canonical_label_key=canonical,
        raw_label=str(candidate.get("raw_label") or "").strip(),
        evidence_candidate=str(candidate.get("evidence_candidate") or "").strip(),
        confidence=confidence,
        downgrade_reasons=list(downgrade_reasons),
        top_impact_score=round(confidence, 3),
    ).as_dict()


def _schema_reasons(candidate: dict[str, Any]) -> list[str]:
    reasons: list[str] = []
    label_type = _clean_label_type(candidate.get("label_type"))
    if not label_type:
        _append_reason(reasons, "schema_invalid")
    if not str(candidate.get("canonical_label_key") or "").strip():
        _append_reason(reasons, "schema_invalid")
    if not str(candidate.get("raw_label") or "").strip():
        _append_reason(reasons, "schema_invalid")
    if not str(candidate.get("aspect_key") or "").strip():
        _append_reason(reasons, "schema_invalid")
    if str(candidate.get("polarity") or "").strip().lower() not in VALID_POLARITIES:
        _append_reason(reasons, "schema_invalid")
    confidence = candidate.get("confidence")
    if not isinstance(confidence, (int, float)) or not (0.0 <= float(confidence) <= 1.0):
        _append_reason(reasons, "schema_invalid")
    if not str(candidate.get("reason") or "").strip():
        _append_reason(reasons, "schema_invalid")
    return reasons


def _candidate_risk_flags(value: Any) -> list[str]:
    if isinstance(value, (list, tuple, set)):
        return [str(flag).strip() for flag in value if str(flag).strip()]
    cleaned = str(value or "").strip()
    return [cleaned] if cleaned else []


def _proof_terms_for_label(canonical: str) -> tuple[str, ...]:
    return {
        "water_leaks_through": ("leak", "wet", "water", "soak", "dry", "waterproof"),
        "keeps_water_out": (
            "dry",
            "no leak",
            "not leak",
            "not leaking",
            "leaking",
            "leak proof",
            "leakproof",
            "waterproof",
            "water out",
            "wet",
        ),
        "fits_as_expected": ("fit", "size", "sizing", "measurement", "true to size", "shoe"),
        "good_value_for_the_price": (
            "price",
            "money",
            "value",
            "worth",
            "cheap",
            "affordable",
            "bargain",
            "expensive",
            "cost",
            "deal",
        ),
        "holds_up_well": (
            "durable",
            "sturdy",
            "heavy duty",
            "last",
            "season",
            "hold",
            "held",
            "strong",
            "tough",
            "secure",
        ),
    }.get(canonical, ())


def _evidence_too_generic(canonical: str, evidence: str, content: str = "") -> bool:
    if canonical not in GENERIC_PROOF_REQUIRED_LABELS:
        return False
    normalized = _normalize_text(evidence)
    if not normalized:
        return True
    context = _normalize_text(v1_labels._evidence_context_window(content, evidence, radius=120)) if content else normalized
    proof_terms = _proof_terms_for_label(canonical)
    if any(term in normalized or term in context for term in proof_terms):
        return False
    return len(normalized.split()) <= 5 or normalized in {
        "good",
        "great",
        "great product",
        "excellent",
        "excellent product",
        "awesome",
        "perfect",
        "nice",
        "very nice",
        "worked out",
        "as described",
    }


def _is_unknown_candidate(canonical: str) -> bool:
    return canonical.startswith("candidate:")


def _source_block_reason(label_type: str, canonical: str, content: str, evidence: str) -> str:
    if label_type != "issue" or canonical != "water_leaks_through":
        return "context_blocked"
    context = v1_labels._evidence_context_sentence(content, evidence)
    window = v1_labels._evidence_context_window(content, evidence)
    if (
        v1_labels._is_non_current_product_leak_context(context)
        or v1_labels._is_non_current_product_leak_context(evidence)
        or v1_labels._is_non_current_product_leak_context(window)
        or v1_labels._is_accessory_only_leak_context(context)
        or v1_labels._is_accessory_only_leak_context(evidence)
        or v1_labels._is_accessory_leak_window(window)
    ):
        return "source_review_blocked"
    return "context_blocked"


def _candidate_context_blocked(label_type: str, canonical: str, content: str, evidence: str) -> str | None:
    if label_type == "highlight" and canonical == "keeps_water_out":
        context = v1_labels._evidence_context_sentence(content, evidence)
        if v1_labels._is_positive_waterproof_evidence_for_issue(context):
            return None
        if v1_labels._is_negative_phrase(context) or re.search(
            r"\b(?:do|does|did|are|is|was|were|would)(?:n['’]?t| not)\s+[^.!?\n]{0,80}\bdry\b",
            context,
            re.IGNORECASE,
        ):
            return "context_blocked"
    return None


def _raw_occurrence_from_candidate(
    *,
    review: dict[str, Any],
    candidate: dict[str, Any],
    evidence: dict[str, Any],
) -> dict[str, Any]:
    label_type = _clean_label_type(candidate.get("label_type"))
    canonical = str(candidate.get("canonical_label_key") or "").strip()
    display_en = str(candidate.get("display_label_en") or candidate.get("raw_label") or _title_from_key(canonical)).strip()
    display_zh = str(candidate.get("display_label_zh") or display_en).strip()
    aspect_key = str(candidate.get("aspect_key") or "unknown").strip() or "unknown"
    confidence = _candidate_confidence(candidate.get("confidence"))
    sub_category = str(review.get("sub_category") or "waders")
    catalog = resolve_customer_label(
        label_type=label_type,
        canonical_label_key=canonical,
        display_en=display_en,
        display_zh=display_zh,
        raw_label=str(candidate.get("raw_label") or display_en),
        aspect_key=aspect_key,
        category_key=str(review.get("category") or "outdoor"),
        sub_category_key=sub_category,
        confidence=_v1_confidence(confidence),
        display_allowed=True,
    )
    legacy_fallback = bool(candidate.get("legacy_fallback"))
    cluster_propagated = bool(candidate.get("cluster_propagated"))
    return {
        "comment_id": review.get("id"),
        "type": label_type,
        "raw_label": str(candidate.get("raw_label") or display_en).strip(),
        "canonical_label_key": catalog.canonical_label_key,
        "display_label_en": catalog.display_en or display_en,
        "display_label_zh": catalog.display_zh or display_zh,
        "aspect_key": aspect_key,
        "dimension_en": v1_labels.aspect_label(aspect_key, "en"),
        "dimension_zh": v1_labels.aspect_label(aspect_key, "zh"),
        "sub_category": sub_category,
        "evidence_span": evidence["evidence_span"],
        "evidence_start": evidence["evidence_start"],
        "evidence_end": evidence["evidence_end"],
        "confidence": _v1_confidence(confidence),
        "source": "legacy" if legacy_fallback else str(candidate.get("source") or "llm"),
        "source_detail": "legacy_fallback" if legacy_fallback else "customer_label_v2_shadow",
        "evidence_verified": bool(evidence["evidence_verified"]),
        "cluster_propagated": cluster_propagated,
        "schema_version": CUSTOMER_LABEL_OCCURRENCE_SCHEMA_VERSION,
        "ruleset_version": CUSTOMER_LABEL_OCCURRENCE_RULESET_VERSION,
        "display_allowed": catalog.display_allowed,
        "customer_label_catalog_source": catalog.source,
        "customer_label_catalog_ruleset_version": catalog.ruleset_version,
    }


def _v2_occurrence_from_projected(
    *,
    projected: dict[str, Any],
    candidate: dict[str, Any],
    downgrade_reasons: list[str],
    maturity_allowed: bool,
) -> dict[str, Any]:
    legacy_fallback = bool(projected.get("legacy_fallback") or candidate.get("legacy_fallback"))
    display_allowed = _display_gate_allowed(
        projected=projected,
        downgrade_reasons=downgrade_reasons,
        maturity_allowed=maturity_allowed,
        legacy_fallback=legacy_fallback,
    )
    confidence = _candidate_confidence(candidate.get("confidence"))
    return {
        "review_id": projected.get("comment_id"),
        "label_type": str(projected.get("type") or ""),
        "canonical_label_key": str(projected.get("canonical_label_key") or ""),
        "display_label_en": str(projected.get("display_label_en") or ""),
        "display_label_zh": str(projected.get("display_label_zh") or ""),
        "aspect_key": str(projected.get("aspect_key") or ""),
        "polarity": str(candidate.get("polarity") or ""),
        "evidence_span": str(projected.get("evidence_span") or ""),
        "evidence_start": int(projected.get("evidence_start") or 0),
        "evidence_end": int(projected.get("evidence_end") or 0),
        "confidence": confidence,
        "source": "llm",
        "source_review_allowed": bool(projected.get("source_review_allowed")),
        "evidence_verified": bool(projected.get("evidence_verified")),
        "aspect_allowed": bool(projected.get("aspect_allowed") is not False),
        "context_allowed": bool(projected.get("context_allowed") is not False),
        "maturity_allowed": maturity_allowed,
        "display_allowed": display_allowed,
        "cluster_propagated": bool(projected.get("cluster_propagated")),
        "legacy_fallback": legacy_fallback,
        "downgrade_reasons": downgrade_reasons,
        "verifier_reasons": [
            "evidence_exact_match" if projected.get("evidence_verified") else "evidence_not_verified",
            "subcategory_l3_allowed" if maturity_allowed else "maturity_not_allowed",
        ],
    }


def _verify_candidate(
    *,
    context: VerificationContext,
    candidate: dict[str, Any],
    index: int,
) -> VerificationOutcome:
    reasons = _schema_reasons(candidate)
    label_type = _clean_label_type(candidate.get("label_type"))
    canonical = str(candidate.get("canonical_label_key") or "").strip()
    evidence_text = str(candidate.get("evidence_candidate") or "").strip()
    if candidate.get("cluster_propagated"):
        _append_reason(reasons, "cluster_propagated")
    if candidate.get("legacy_fallback"):
        _append_reason(reasons, "legacy_fallback")
    if not evidence_text:
        _append_reason(reasons, "evidence_missing")
    if canonical and _is_unknown_candidate(canonical):
        _append_reason(reasons, "unknown_label")
    confidence = _candidate_confidence(candidate.get("confidence"))
    maturity_decision = maturity_gate_decision(
        label_type=label_type,
        canonical_label_key=canonical,
        maturity=context.maturity,
        subcategory_specificity=str(candidate.get("subcategory_specificity") or ""),
        risk_flags=_candidate_risk_flags(candidate.get("risk_flags")),
    )
    confidence_threshold = DISPLAY_CONFIDENCE_THRESHOLD
    if maturity_decision.allowed:
        confidence_threshold = max(confidence_threshold, maturity_decision.minimum_confidence)
    if confidence < confidence_threshold:
        _append_reason(reasons, "confidence_low")
    content = context.content
    if label_type and canonical and _evidence_too_generic(canonical, evidence_text, content):
        _append_reason(reasons, "evidence_too_generic")
    maturity_allowed = bool(maturity_decision.allowed and "unknown_label" not in reasons)
    if canonical and not maturity_allowed and "unknown_label" not in reasons:
        _append_reason(reasons, "maturity_blocked")

    evidence = _locate_evidence(content, evidence_text)
    if evidence_text and not evidence["evidence_verified"]:
        _append_reason(reasons, "evidence_not_found")

    if label_type and canonical and evidence["evidence_verified"]:
        aspect_key = str(candidate.get("aspect_key") or "").strip()
        if not v1_labels._is_label_aspect_allowed(label_type, canonical, aspect_key):
            _append_reason(reasons, "aspect_blocked")
        context_reason = _candidate_context_blocked(label_type, canonical, content, evidence_text)
        if context_reason:
            _append_reason(reasons, context_reason)

    projected = None
    if (
        label_type
        and canonical
        and evidence["evidence_verified"]
        and "unknown_label" not in reasons
        and "schema_invalid" not in reasons
    ):
        raw_occurrence = _raw_occurrence_from_candidate(
            review=context.review,
            candidate=candidate,
            evidence=evidence,
        )
        projected = v1_labels._project_customer_label_occurrence(
            raw_occurrence,
            comment=context.review,
            label_type=label_type,
            locale="en",
        )
        if projected is None:
            if not ({"aspect_blocked", "evidence_too_generic", "maturity_blocked"} & set(reasons)):
                _append_reason(reasons, _source_block_reason(label_type, canonical, content, evidence_text))
        else:
            if projected.get("aspect_allowed") is False:
                _append_reason(reasons, "aspect_blocked")
            if projected.get("context_allowed") is False:
                _append_reason(reasons, _source_block_reason(label_type, canonical, content, evidence_text))
            if not projected.get("source_review_allowed") and not reasons:
                _append_reason(reasons, "source_review_blocked")

    if projected:
        occurrence = _v2_occurrence_from_projected(
            projected=projected,
            candidate=candidate,
            downgrade_reasons=reasons,
            maturity_allowed=maturity_allowed,
        )
        audit = occurrence if reasons or not _is_frontstage_occurrence(occurrence) else None
    else:
        occurrence = None
        audit = _audit_occurrence(
            review_id=context.review.get("id"),
            candidate=candidate,
            downgrade_reasons=reasons or ["schema_invalid"],
            evidence=evidence,
            label_type=label_type,
        )

    pool_item = None
    if "unknown_label" in reasons or "maturity_blocked" in reasons:
        pool_item = _candidate_pool_item(
            review=context.review,
            candidate=candidate,
            downgrade_reasons=reasons,
            index=index,
        )
    return VerificationOutcome(
        occurrence=occurrence,
        audit_occurrence=audit,
        candidate_pool_item=pool_item,
    )


def run_customer_label_v2_shadow(
    review: dict[str, Any] | None = None,
    *,
    content: str | None = None,
    rating: int | float | None = None,
    category: str = "outdoor",
    sub_category: str = "waders",
    review_id: Any = None,
    llm_output: str | dict[str, Any] | list[dict[str, Any]] | None = None,
    label_candidates: list[dict[str, Any]] | None = None,
    maturity_level: str | None = None,
) -> dict[str, Any]:
    source_review = copy.deepcopy(review or {})
    if content is not None:
        source_review["content"] = content
    if rating is not None:
        source_review["rating"] = rating
    if review_id is not None:
        source_review["id"] = review_id
    source_review.setdefault("category", category)
    source_review.setdefault("sub_category", sub_category)
    resolved_maturity = resolve_customer_label_maturity(
        category=str(source_review.get("category") or category),
        sub_category=str(source_review.get("sub_category") or sub_category),
        explicit_level=maturity_level,
    )
    verification_context = _verification_context(source_review, resolved_maturity)

    if label_candidates is not None:
        payload = {
            "customer_label_schema_version": CUSTOMER_LABEL_V2_SCHEMA_VERSION,
            "prompt_version": CUSTOMER_LABEL_V2_PROMPT_VERSION,
            "model": "mock-fixture",
            "source": "fixture",
            "sub_category": source_review.get("sub_category"),
            "category": source_review.get("category"),
            "language": "en",
            "label_candidates": copy.deepcopy(label_candidates),
        }
        parse_error = None
    elif llm_output is not None:
        payload, parse_error = _parse_llm_payload(llm_output)
    else:
        payload = build_mock_llm_payload_from_v1_display(source_review)
        parse_error = None

    audit_occurrences: list[dict[str, Any]] = []
    verified_occurrences: list[dict[str, Any]] = []
    display_occurrences: list[dict[str, Any]] = []
    candidate_pool_items: list[dict[str, Any]] = []

    if parse_error:
        audit_occurrences.append(
            _audit_occurrence(
                review_id=source_review.get("id"),
                candidate=None,
                downgrade_reasons=[parse_error],
                label_type="audit",
            )
        )
        candidates: list[dict[str, Any]] = []
    else:
        candidates = list((payload or {}).get("label_candidates") or [])
        for index, candidate in enumerate(candidates):
            if not isinstance(candidate, dict):
                audit_occurrences.append(
                    _audit_occurrence(
                        review_id=source_review.get("id"),
                        candidate={},
                        downgrade_reasons=["schema_invalid"],
                    )
                )
                continue
            outcome = _verify_candidate(
                context=verification_context,
                candidate=candidate,
                index=index,
            )
            if outcome.occurrence:
                verified_occurrences.append(outcome.occurrence)
                if _is_frontstage_occurrence(outcome.occurrence):
                    display_occurrences.append(outcome.occurrence)
            if outcome.audit_occurrence:
                audit_occurrences.append(outcome.audit_occurrence)
            if outcome.candidate_pool_item:
                candidate_pool_items.append(outcome.candidate_pool_item)

    downgrade_reasons = _collect_downgrade_reasons(audit_occurrences)
    return {
        "review_id": source_review.get("id"),
        "schema_version": CUSTOMER_LABEL_V2_SCHEMA_VERSION,
        "ruleset_version": CUSTOMER_LABEL_V2_VERIFIER_RULESET_VERSION,
        "prompt_version": str((payload or {}).get("prompt_version") or CUSTOMER_LABEL_V2_PROMPT_VERSION),
        "model": str((payload or {}).get("model") or CUSTOMER_LABEL_V2_MOCK_MODEL),
        "source": str((payload or {}).get("source") or "shadow"),
        "category": str(source_review.get("category") or category),
        "sub_category": str(source_review.get("sub_category") or sub_category),
        "maturity_level": resolved_maturity.level,
        "maturity": resolved_maturity.as_dict(),
        "label_candidates": candidates,
        "verified_occurrences": verified_occurrences,
        "display_occurrences": display_occurrences,
        "audit_occurrences": audit_occurrences,
        "candidate_pool_items": candidate_pool_items,
        "downgrade_reasons": downgrade_reasons,
        "shadow_safety": {
            "production_upload": False,
            "production_write_path": False,
            "production_db_write": False,
            "credit_consumed": False,
            "llm_called": False,
            "frontstage_replaced": False,
        },
    }


def display_keys_from_shadow(result: dict[str, Any]) -> dict[str, list[str]]:
    keys: dict[str, list[str]] = {"issue": [], "highlight": []}
    for occurrence in result.get("display_occurrences") or []:
        label_type = str(occurrence.get("label_type") or "")
        canonical = str(occurrence.get("canonical_label_key") or "").strip()
        if label_type in keys and canonical and canonical not in keys[label_type]:
            keys[label_type].append(canonical)
    return keys


def _compare_sets(actual: set[str], expected: set[str], counter: Counter[str], label_type: str) -> None:
    counter[f"{label_type}_tp"] += len(actual & expected)
    counter[f"{label_type}_fp"] += len(actual - expected)
    counter[f"{label_type}_fn"] += len(expected - actual)
    counter[f"{label_type}_exact_set"] += int(actual == expected)


def compare_customer_label_v2_shadow(
    reviews: list[dict[str, Any]],
    expected_keys: Callable[[dict[str, Any]], dict[str, list[str]]],
    *,
    dataset_name: str,
    blocked_keys: Callable[[dict[str, Any]], dict[str, list[str]]] | None = None,
) -> dict[str, Any]:
    summary: Counter[str] = Counter()
    downgrade_reasons: Counter[str] = Counter()
    focus_metrics: dict[str, Counter[str]] = defaultdict(Counter)
    blocked_violations: list[dict[str, Any]] = []
    row_results: list[dict[str, Any]] = []

    for review in reviews:
        result = run_customer_label_v2_shadow(review)
        actual = display_keys_from_shadow(result)
        expected = expected_keys(review)
        blocked = blocked_keys(review) if blocked_keys else {"issue": [], "highlight": []}

        summary["review_count"] += 1
        summary["candidate_count"] += len(result["label_candidates"])
        summary["display_count"] += len(result["display_occurrences"])
        summary["verified_count"] += len(result["verified_occurrences"])
        evidence_candidates = [item for item in result["label_candidates"] if item.get("evidence_candidate")]
        summary["evidence_candidate_count"] += len(evidence_candidates)
        summary["evidence_located_count"] += sum(1 for item in result["verified_occurrences"] if item.get("evidence_verified"))
        for audit in result["audit_occurrences"]:
            for reason in audit.get("downgrade_reasons") or []:
                downgrade_reasons[str(reason)] += 1

        for label_type in ("issue", "highlight"):
            actual_set = set(actual[label_type])
            expected_set = set(expected[label_type])
            _compare_sets(actual_set, expected_set, summary, label_type)
            for canonical in actual_set | expected_set:
                key = f"{label_type}:{canonical}"
                focus = focus_metrics[key]
                focus["tp"] += int(canonical in actual_set and canonical in expected_set)
                focus["fp"] += int(canonical in actual_set and canonical not in expected_set)
                focus["fn"] += int(canonical not in actual_set and canonical in expected_set)
            blocked_overlap = actual_set & set(blocked.get(label_type) or [])
            for canonical in sorted(blocked_overlap):
                blocked_violations.append(
                    {
                        "review_id": review.get("id"),
                        "label_type": label_type,
                        "canonical_label_key": canonical,
                    }
                )

        row_results.append(
            {
                "review_id": review.get("id"),
                "issue_keys": actual["issue"],
                "highlight_keys": actual["highlight"],
                "expected_issue_keys": expected["issue"],
                "expected_highlight_keys": expected["highlight"],
                "audit_reasons": sorted(
                    {
                        str(reason)
                        for audit in result["audit_occurrences"]
                        for reason in audit.get("downgrade_reasons") or []
                    }
                ),
            }
        )

    evidence_rate = (
        round(summary["evidence_located_count"] / summary["evidence_candidate_count"], 4)
        if summary["evidence_candidate_count"]
        else 1.0
    )
    return {
        "dataset": dataset_name,
        "review_count": summary["review_count"],
        "candidate_count": summary["candidate_count"],
        "verified_count": summary["verified_count"],
        "display_count": summary["display_count"],
        "evidence_locate_rate": evidence_rate,
        "tp_fp_fn": {
            "issue": {
                "tp": summary["issue_tp"],
                "fp": summary["issue_fp"],
                "fn": summary["issue_fn"],
                "exact_set": summary["issue_exact_set"],
            },
            "highlight": {
                "tp": summary["highlight_tp"],
                "fp": summary["highlight_fp"],
                "fn": summary["highlight_fn"],
                "exact_set": summary["highlight_exact_set"],
            },
        },
        "focus_label_metrics": {
            key: dict(value)
            for key, value in sorted(focus_metrics.items())
            if tuple(key.split(":", 1)) in FOCUS_WADERS_LABELS
        },
        "downgrade_reasons": dict(sorted(downgrade_reasons.items())),
        "blocked_violations": blocked_violations,
        "rows": row_results,
    }
