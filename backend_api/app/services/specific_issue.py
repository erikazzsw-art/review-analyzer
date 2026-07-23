from __future__ import annotations

import copy
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

SPECIFIC_ISSUE_SCHEMA_VERSION = "1.0"
ISSUE_RULESET_VERSION = "2026-07-23-mvp1"

_LABELS_CACHE: dict[str, dict[str, str]] | None = None


def _load_aspect_labels() -> dict[str, dict[str, str]]:
    global _LABELS_CACHE
    if _LABELS_CACHE is None:
        path = Path(__file__).parent.parent / "i18n" / "aspect_labels.json"
        try:
            _LABELS_CACHE = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            _LABELS_CACHE = {}
    return _LABELS_CACHE


def aspect_label(aspect_key: str, locale: str = "en") -> str:
    labels = _load_aspect_labels().get(aspect_key, {})
    label = labels.get(locale) or labels.get("en") or labels.get("zh")
    return str(label or aspect_key.replace("_", " ").title())


def coerce_aspects_json(value: Any) -> dict[str, Any] | None:
    if isinstance(value, dict):
        return value
    if isinstance(value, str) and value.strip():
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return None
        return parsed if isinstance(parsed, dict) else None
    return None


def _norm_text(value: str) -> str:
    value = value.replace("&", " and ")
    value = re.sub(r"[^a-z0-9]+", " ", value.lower())
    return re.sub(r"\s+", " ", value).strip()


def _slug(value: str) -> str:
    norm = _norm_text(value)
    ascii_slug = re.sub(r"[^a-z0-9]+", "_", norm).strip("_")
    if ascii_slug:
        return ascii_slug
    unicode_slug = re.sub(r"[^\w]+", "_", value.strip().lower(), flags=re.UNICODE).strip("_")
    return unicode_slug or "unspecified_issue"


def _title_case(value: str) -> str:
    words = _norm_text(value).split()
    small = {"a", "an", "and", "as", "at", "by", "for", "in", "of", "on", "or", "the", "to", "with"}
    titled: list[str] = []
    for index, word in enumerate(words[:7]):
        if index > 0 and word in small:
            titled.append(word)
        else:
            titled.append(word.capitalize())
    return " ".join(titled)


_BROAD_LABELS = {
    "accessories and storage",
    "accessory storage",
    "assembly",
    "build quality",
    "comfort",
    "durability",
    "material",
    "materials",
    "other",
    "quality",
    "product quality",
    "user experience",
    "waterproof performance",
}


def _is_broad_issue(issue: str, aspect_key: str, label: str) -> bool:
    norm_issue = _norm_text(issue)
    if not norm_issue:
        return True
    if norm_issue in _BROAD_LABELS:
        return True
    return norm_issue == _norm_text(aspect_key) or norm_issue == _norm_text(label)


def _first_regex(patterns: list[str], text: str) -> bool:
    return any(re.search(pattern, text, re.IGNORECASE) for pattern in patterns)


def _issue_from_rules(aspect_key: str, evidence: str, content: str) -> tuple[str, str, str] | None:
    text = f"{evidence} {content[:400]}".lower()

    if aspect_key in {"accessory_storage", "organization", "capacity"}:
        if _first_regex([r"\bpockets?\b.*\b(wet|soak|water|leak)", r"\b(wet|soak|water|leak).*\bpockets?\b"], text):
            return ("Pocket Not Waterproof", "pocket_not_waterproof", "regex_alias_rule")
        if _first_regex([r"\bpockets?\b.*\b(small|tight|tiny|too small|not enough room)"], text):
            return ("Pocket Too Small", "pocket_too_small", "regex_alias_rule")
        if _first_regex([r"\bmissing\b.*\b(hanger|hook)", r"\bno\b.*\b(hanger|hook)"], text):
            return ("Missing Wader Hanger", "missing_wader_hanger", "regex_alias_rule")

    if aspect_key in {"waterproof", "waterproof_performance", "seam_integrity"}:
        if _first_regex([r"\bnot waterproof\b", r"\bleak", r"\bwater (gets|got|came|comes|coming) (in|through)"], text):
            return ("Water Leaks Through", "water_leaks_through", "regex_alias_rule")

    if aspect_key in {"zipper_quality"}:
        if _first_regex([r"\bzipper\b.*\b(broke|break|stuck|jam|fail|cheap)", r"\b(broke|stuck|jammed).*\bzipper\b"], text):
            return ("Zipper Fails", "zipper_fails", "regex_alias_rule")

    if aspect_key in {"assembly", "instructions"}:
        if _first_regex([r"\b(instruction|manual|directions?)\b.*\b(confusing|unclear|bad|poor|wrong|missing)"], text):
            return ("Instructions Unclear", "instructions_unclear", "regex_alias_rule")
        if _first_regex([r"\b(hard|difficult|pain|nightmare)\b.*\b(assemble|assembly|put together|install)"], text):
            return ("Hard To Assemble", "hard_to_assemble", "regex_alias_rule")

    if aspect_key in {"missing_parts", "packaging"}:
        if _first_regex([r"\bmissing\b.*\b(part|screw|bolt|piece|hardware)", r"\bno\b.*\b(screw|bolt|hardware)"], text):
            return ("Missing Parts", "missing_parts", "regex_alias_rule")

    if aspect_key in {"shipping_damage", "packaging"}:
        if _first_regex([r"\b(arrived|came|delivered)\b.*\b(damaged|broken|cracked|bent)", r"\bpackag(e|ing)\b.*\b(damaged|crushed|torn)"], text):
            return ("Arrived Damaged", "arrived_damaged", "regex_alias_rule")

    if aspect_key in {"durability", "build_quality", "stability", "material", "strength"}:
        if _first_regex([r"\b(fell apart|falls apart)\b"], text):
            return ("Falls Apart", "falls_apart", "regex_alias_rule")
        if _first_regex([r"\b(broke|breaks|broken|cracked|snapped)\b"], text):
            return ("Breaks Easily", "breaks_easily", "regex_alias_rule")
        if _first_regex([r"\b(thin|flimsy|cheap)\b"], text):
            return ("Feels Thin and Flimsy", "feels_thin_and_flimsy", "regex_alias_rule")

    if aspect_key in {"size_fit", "boot_fit"}:
        if _first_regex([r"\btoo small\b", r"\bruns small\b", r"\btight\b"], text):
            return ("Runs Too Small", "runs_too_small", "regex_alias_rule")
        if _first_regex([r"\btoo large\b", r"\bruns large\b", r"\bloose\b"], text):
            return ("Runs Too Large", "runs_too_large", "regex_alias_rule")

    if aspect_key in {"comfort", "breathability", "mobility"}:
        if _first_regex([r"\buncomfortable\b", r"\bhurts?\b", r"\bblister"], text):
            return ("Uncomfortable Fit", "uncomfortable_fit", "regex_alias_rule")
        if _first_regex([r"\bhot\b", r"\bsweat", r"\bnot breathable\b"], text):
            return ("Not Breathable", "not_breathable", "regex_alias_rule")

    if aspect_key in {"smell", "scent"}:
        if _first_regex([r"\b(strong|bad|chemical|awful)\b.*\b(smell|odor|scent)", r"\b(smell|odor|scent)\b.*\b(strong|bad|chemical|awful)"], text):
            return ("Strong Chemical Smell", "strong_chemical_smell", "regex_alias_rule")

    if aspect_key in {"value_for_money"}:
        if _first_regex([r"\bnot worth\b", r"\boverpriced\b", r"\btoo expensive\b"], text):
            return ("Not Worth the Price", "not_worth_the_price", "regex_alias_rule")

    if aspect_key in {"customer_service"}:
        if _first_regex([r"\b(customer service|support|seller)\b.*\b(bad|poor|unhelpful|no response|ignored)"], text):
            return ("Poor Customer Service", "poor_customer_service", "regex_alias_rule")

    if aspect_key in {"clumping"}:
        return ("Mascara Clumps", "mascara_clumps", "regex_alias_rule")
    if aspect_key in {"smudge_resistance"} and _first_regex([r"\bsmudge|smear|racoon eyes|runs\b"], text):
        return ("Smudges Easily", "smudges_easily", "regex_alias_rule")
    if aspect_key in {"flaking"}:
        return ("Mascara Flakes", "mascara_flakes", "regex_alias_rule")
    if aspect_key in {"curl_hold"} and _first_regex([r"\bcurl\b.*\b(hold|last|stay|drop)", r"\bdoes not hold\b"], text):
        return ("Curl Does Not Hold", "curl_does_not_hold", "regex_alias_rule")
    if aspect_key in {"lengthening_effect"} and _first_regex([r"\b(no|not enough|little)\b.*\blength", r"\bdoes not lengthen\b"], text):
        return ("Not Enough Length", "not_enough_length", "regex_alias_rule")
    if aspect_key in {"volumizing_effect"} and _first_regex([r"\b(no|not enough|little)\b.*\bvolume", r"\bdoes not volumize\b"], text):
        return ("Not Enough Volume", "not_enough_volume", "regex_alias_rule")
    if aspect_key in {"eye_sensitivity"} and _first_regex([r"\birritat|burn|sting|sensitive"], text):
        return ("Irritates Eyes", "irritates_eyes", "regex_alias_rule")

    if aspect_key in {"noise"} and _first_regex([r"\bsqueak|creak|noisy|noise"], text):
        return ("Makes Squeaking Noise", "makes_squeaking_noise", "regex_alias_rule")
    if aspect_key in {"battery_life"} and _first_regex([r"\bbattery\b.*\b(short|dies|drain|last)", r"\bdoes not hold a charge\b"], text):
        return ("Battery Dies Quickly", "battery_dies_quickly", "regex_alias_rule")
    if aspect_key in {"charging"} and _first_regex([r"\b(charger|charging|charge)\b.*\b(stop|fail|slow|does not work|won't)"], text):
        return ("Charging Fails", "charging_fails", "regex_alias_rule")

    return None


def _issue_from_existing(aspect: dict[str, Any], aspect_key: str, label: str) -> tuple[str, str, str, str, bool] | None:
    specific_issue = str(aspect.get("specific_issue") or "").strip()
    raw_issue = str(aspect.get("specific_issue_raw") or specific_issue or aspect.get("canonical_hint") or "").strip()
    if not raw_issue:
        return None

    issue = _title_case(specific_issue or raw_issue)
    canonical = str(aspect.get("canonical_issue_key") or "").strip() or _slug(issue)
    display_allowed = not _is_broad_issue(issue, aspect_key, label)
    if aspect.get("display_allowed") is False or aspect.get("issue_source") == "broad_fallback":
        display_allowed = False
    return (issue, canonical, "llm_canonical_hint", raw_issue, display_allowed)


def _normalize_aspect_issue(
    aspect: dict[str, Any],
    *,
    sub_category: str,
    content: str,
    locale: str,
) -> dict[str, Any] | None:
    aspect_key = str(aspect.get("key") or aspect.get("aspect_key") or "").strip()
    if not aspect_key:
        return None
    if str(aspect.get("polarity") or "").lower() != "negative":
        return None

    label = str(aspect.get("aspect_label") or aspect.get("label") or aspect_label(aspect_key, locale))
    evidence = str(aspect.get("evidence_span") or aspect.get("evidence") or "").strip()
    existing = _issue_from_existing(aspect, aspect_key, label)

    confidence = str(aspect.get("issue_confidence") or "").lower()
    if confidence not in {"high", "medium", "low"}:
        confidence = "medium"

    if existing:
        issue, canonical, source, raw, display_allowed = existing
    else:
        rule_hit = _issue_from_rules(aspect_key, evidence, content)
        if rule_hit:
            issue, canonical, source = rule_hit
            raw = issue
            confidence = "high" if source.endswith("alias_rule") else confidence
            display_allowed = not _is_broad_issue(issue, aspect_key, label)
        else:
            issue = f"{label} Issue"
            canonical = _slug(issue)
            source = "broad_fallback"
            raw = evidence or label
            confidence = "low"
            display_allowed = False

    return {
        "specific_issue": issue,
        "canonical_issue_key": canonical,
        "issue_confidence": confidence,
        "issue_source": source,
        "specific_issue_raw": raw,
        "display_allowed": bool(display_allowed),
        "aspect_key": aspect_key,
        "dimension": label,
        "sub_category": sub_category,
        "evidence_span": evidence,
    }


def enrich_aspects_json(
    aspects_json: Any,
    *,
    sub_category: str = "",
    content: str = "",
    locale: str = "en",
) -> dict[str, Any] | None:
    aj = coerce_aspects_json(aspects_json)
    if not aj:
        return None
    enriched = copy.deepcopy(aj)
    aspects = enriched.get("aspects")
    if not isinstance(aspects, list):
        aspects = []
        enriched["aspects"] = aspects
    normalized_sub_category = sub_category or str(enriched.get("sub_category") or "")
    for aspect in aspects:
        if not isinstance(aspect, dict):
            continue
        issue = _normalize_aspect_issue(
            aspect,
            sub_category=normalized_sub_category,
            content=content,
            locale=locale,
        )
        if not issue:
            continue
        aspect.update(
            {
                "specific_issue": issue["specific_issue"],
                "canonical_issue_key": issue["canonical_issue_key"],
                "issue_confidence": issue["issue_confidence"],
                "issue_source": issue["issue_source"],
                "specific_issue_raw": issue["specific_issue_raw"],
                "display_allowed": issue["display_allowed"],
                "aspect_label": issue["dimension"],
            }
        )
    enriched["specific_issue_schema_version"] = SPECIFIC_ISSUE_SCHEMA_VERSION
    enriched["issue_ruleset_version"] = ISSUE_RULESET_VERSION
    if normalized_sub_category:
        enriched["sub_category"] = normalized_sub_category
    return enriched


def _legacy_issue_occurrences(comment: dict[str, Any], locale: str) -> list[dict[str, Any]]:
    occurrences: list[dict[str, Any]] = []
    content = str(comment.get("content") or "").strip()
    for raw_tag in str(comment.get("issue_tag") or "").split(","):
        issue = raw_tag.strip()
        if not issue:
            continue
        occurrences.append(
            {
                "comment_id": comment.get("id"),
                "content": content,
                "specific_issue": issue,
                "canonical_issue_key": _slug(issue),
                "issue_confidence": "low",
                "issue_source": "legacy_issue_tag",
                "specific_issue_raw": issue,
                "display_allowed": True,
                "aspect_key": "",
                "dimension": "",
                "sub_category": str(comment.get("sub_category") or comment.get("category") or ""),
                "evidence_span": "",
                "verified_evidence": False,
                "legacy_fallback": True,
            }
        )
    return occurrences


def iter_specific_issue_occurrences(comment: dict[str, Any], locale: str = "en") -> list[dict[str, Any]]:
    content = str(comment.get("content") or "").strip()
    aj = coerce_aspects_json(comment.get("aspects_json"))
    schema_version = ""
    has_specific_issue_payload = False
    occurrences: list[dict[str, Any]] = []
    if aj:
        schema_version = str(aj.get("specific_issue_schema_version") or "")
        sub_category = str(aj.get("sub_category") or comment.get("sub_category") or "")
        for aspect in aj.get("aspects") or []:
            if not isinstance(aspect, dict):
                continue
            has_specific_issue_payload = has_specific_issue_payload or any(
                key in aspect
                for key in ("specific_issue", "canonical_issue_key", "display_allowed", "issue_source")
            )
            issue = _normalize_aspect_issue(
                aspect,
                sub_category=sub_category,
                content=content,
                locale=locale,
            )
            if not issue or not issue["display_allowed"]:
                continue
            evidence = issue["evidence_span"]
            occurrences.append(
                {
                    "comment_id": comment.get("id"),
                    "content": content,
                    "specific_issue": issue["specific_issue"],
                    "canonical_issue_key": issue["canonical_issue_key"],
                    "issue_confidence": issue["issue_confidence"],
                    "issue_source": issue["issue_source"],
                    "specific_issue_raw": issue["specific_issue_raw"],
                    "display_allowed": True,
                    "aspect_key": issue["aspect_key"],
                    "dimension": issue["dimension"],
                    "sub_category": issue["sub_category"],
                    "evidence_span": evidence,
                    "verified_evidence": bool(
                        evidence
                        and evidence in content
                        and not bool(aj.get("cluster_propagated"))
                    ),
                    "legacy_fallback": False,
                }
            )
    if occurrences or schema_version == SPECIFIC_ISSUE_SCHEMA_VERSION or has_specific_issue_payload:
        return occurrences
    return _legacy_issue_occurrences(comment, locale)


def build_specific_issue_rows(
    comments: list[dict[str, Any]],
    *,
    locale: str = "en",
    limit: int = 10,
) -> list[dict[str, Any]]:
    pool_size = len(comments)
    groups: dict[tuple[str, str, str], dict[str, Any]] = {}
    comment_counts: dict[tuple[str, str, str], set[Any]] = defaultdict(set)
    confidence_counter: dict[tuple[str, str, str], Counter[str]] = defaultdict(Counter)

    for fallback_index, comment in enumerate(comments):
        comment_id = comment.get("id")
        if comment_id is None:
            comment_id = f"row-{fallback_index}"
        seen_in_comment: set[tuple[str, str, str]] = set()
        for occurrence in iter_specific_issue_occurrences(comment, locale=locale):
            key = (
                str(occurrence.get("sub_category") or ""),
                str(occurrence.get("aspect_key") or ""),
                str(occurrence.get("canonical_issue_key") or ""),
            )
            if not key[2] or key in seen_in_comment:
                continue
            seen_in_comment.add(key)
            if key not in groups:
                groups[key] = {
                    "tag": occurrence["specific_issue"],
                    "specific_issue": occurrence["specific_issue"],
                    "canonical_issue_key": occurrence["canonical_issue_key"],
                    "aspect_key": occurrence.get("aspect_key") or "",
                    "dimension": occurrence.get("dimension") or "",
                    "sub_category": occurrence.get("sub_category") or "",
                    "issue_source": occurrence.get("issue_source") or "",
                    "display_allowed": True,
                    "specific_issue_schema_version": SPECIFIC_ISSUE_SCHEMA_VERSION,
                    "issue_ruleset_version": ISSUE_RULESET_VERSION,
                    "representative_comments": [],
                    "evidence_spans": [],
                    "reason": "",
                }
            comment_counts[key].add(comment_id)
            confidence_counter[key][str(occurrence.get("issue_confidence") or "low")] += 1
            content = str(occurrence.get("content") or "").strip()
            evidence = str(occurrence.get("evidence_span") or "").strip()
            if occurrence.get("verified_evidence") and content:
                if content not in groups[key]["representative_comments"]:
                    groups[key]["representative_comments"].append(content[:240])
                if evidence and evidence not in groups[key]["evidence_spans"]:
                    groups[key]["evidence_spans"].append(evidence)

    rows: list[dict[str, Any]] = []
    for key, row in groups.items():
        count = len(comment_counts[key])
        pct = round(count / pool_size * 100, 1) if pool_size else 0.0
        conf = confidence_counter[key].most_common(1)[0][0] if confidence_counter[key] else "low"
        examples = row["representative_comments"][:5]
        evidence_spans = row["evidence_spans"][:5]
        rows.append(
            {
                **row,
                "count": count,
                "pct": pct,
                "mention_share": pct,
                "issue_confidence": conf,
                "representative_comments": examples,
                "evidence_spans": evidence_spans,
                "reason": examples[0] if examples else "No representative comment found.",
            }
        )

    return sorted(rows, key=lambda r: (-int(r["count"]), str(r["specific_issue"]).lower()))[:limit]
