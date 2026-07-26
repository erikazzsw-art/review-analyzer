from __future__ import annotations

import copy
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from backend_api.app.services.customer_label_catalog import resolve_customer_label

SPECIFIC_ISSUE_SCHEMA_VERSION = "1.0"
CUSTOMER_LABEL_SCHEMA_VERSION = "1.0"
CUSTOMER_LABEL_OCCURRENCE_SCHEMA_VERSION = "1.0"
ISSUE_RULESET_VERSION = "2026-07-24-customer-label-system"
HIGHLIGHT_RULESET_VERSION = "2026-07-24-customer-label-system"
CUSTOMER_LABEL_RULESET_VERSION = f"{ISSUE_RULESET_VERSION}+{HIGHLIGHT_RULESET_VERSION}"
CUSTOMER_LABEL_OCCURRENCE_RULESET_VERSION = "2026-07-24-customer-label-occurrence-v1"

_OCCURRENCE_SOURCES = {"llm", "rule", "human", "legacy"}

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


def _display_aspect_label(aspect: dict[str, Any], aspect_key: str, locale: str) -> str:
    mapped = _load_aspect_labels().get(aspect_key, {})
    if mapped:
        return aspect_label(aspect_key, locale)
    candidate = str(aspect.get("aspect_label") or aspect.get("label") or "").strip()
    if candidate and not (locale.startswith("en") and _has_cjk(candidate)):
        return candidate
    return aspect_label(aspect_key, locale)


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
    "aesthetics",
    "assembly",
    "build quality",
    "capacity",
    "comfort",
    "durability",
    "ease of use",
    "grip",
    "material",
    "materials",
    "mobility",
    "organization",
    "other",
    "packaging",
    "quality",
    "product quality",
    "stability",
    "user experience",
    "waterproof performance",
    "waterproofing",
}

_BROAD_LABELS_ZH = {
    "其他",
    "做工",
    "包装",
    "外观设计",
    "容量/空间",
    "材质用料",
    "产品质量",
    "用户体验",
    "组装难度",
    "耐用性",
    "舒适度",
    "防水性",
    "稳固性",
    "易用性",
    "抓地力",
    "活动灵活性",
    "收纳分区",
}

_SPECIFIC_ISSUE_ZH_BY_KEY = {
    "arrived_damaged": "到货破损",
    "battery_dies_quickly": "电池耗电快",
    "breaks_easily": "容易损坏",
    "charging_fails": "充电不稳定",
    "curl_does_not_hold": "卷翘保持差",
    "falls_apart": "容易散架",
    "feels_thin_and_flimsy": "材质偏薄不结实",
    "hard_to_assemble": "组装困难",
    "instructions_unclear": "说明不清楚",
    "irritates_eyes": "刺激眼睛",
    "makes_squeaking_noise": "有异响",
    "mascara_clumps": "睫毛膏容易结块",
    "mascara_flakes": "睫毛膏容易掉渣",
    "missing_parts": "缺少配件",
    "missing_wader_hanger": "缺少涉水裤挂架",
    "not_breathable": "不够透气",
    "not_enough_length": "纤长效果不足",
    "not_enough_volume": "浓密效果不足",
    "not_worth_the_price": "不值这个价格",
    "pocket_not_waterproof": "口袋不防水",
    "pocket_too_small": "口袋太小",
    "poor_customer_service": "客服体验差",
    "runs_too_large": "尺码偏大",
    "runs_too_small": "尺码偏小",
    "smudges_easily": "容易晕染",
    "strong_chemical_smell": "化学气味重",
    "uncomfortable_fit": "穿着不舒服",
    "water_leaks_through": "容易进水",
    "zipper_fails": "拉链容易故障",
}


def _is_broad_issue(issue: str, aspect_key: str, label: str) -> bool:
    norm_issue = _norm_text(issue)
    if not norm_issue:
        return issue.strip() in _BROAD_LABELS_ZH
    if norm_issue in _BROAD_LABELS:
        return True
    return norm_issue == _norm_text(aspect_key) or norm_issue == _norm_text(label) or issue.strip() == label.strip()


def _has_cjk(value: str) -> bool:
    return bool(re.search(r"[\u3400-\u9fff]", value))


def _is_customer_label_allowed(
    label: str,
    *,
    locale: str,
    aspect_key: str = "",
    aspect_label: str = "",
) -> bool:
    cleaned = label.strip()
    if not cleaned:
        return False
    if locale.startswith("en") and _has_cjk(cleaned):
        return False
    if cleaned in _BROAD_LABELS_ZH:
        return False
    return not _is_broad_issue(cleaned, aspect_key, aspect_label)


def _customer_title(value: str) -> str:
    cleaned = value.strip()
    if not cleaned:
        return ""
    if _has_cjk(cleaned):
        return cleaned
    return _title_case(cleaned) or cleaned


def _specific_issue_zh_label(canonical: str, issue: str) -> str:
    mapped = _SPECIFIC_ISSUE_ZH_BY_KEY.get(canonical) or _SPECIFIC_ISSUE_ZH_BY_KEY.get(_slug(issue))
    if mapped:
        return mapped
    return issue


def _first_regex(patterns: list[str], text: str) -> bool:
    return any(re.search(pattern, text, re.IGNORECASE) for pattern in patterns)


_NOT_BREATHABLE_ISSUE_PATTERNS = [
    r"\bnot breathable\b",
    r"\bdoes(?:n['’]?t| not)\s+breathe\b",
    r"\btoo hot\b",
    r"\buncomfortably hot\b",
    r"\bnot good for hot weather\b",
    r"\bhot and sweaty\b",
    r"\bmakes?\s+(?:me|you|us)?\s*sweat\b",
    r"\bmade\s+(?:me|you|us)?\s*sweat\b",
    r"\bsweat\b",
    r"\bsweaty\b",
    r"\bsweating\b",
]


def _not_breathable_issue_hit(text: str) -> bool:
    return _first_regex(_NOT_BREATHABLE_ISSUE_PATTERNS, text)


def _is_apparel_comfort_sub_category(sub_category: str) -> bool:
    cleaned = str(sub_category or "").strip()
    normalized = _norm_text(cleaned)
    return cleaned == "上衣" or normalized in {
        "apparel",
        "top",
        "tops",
        "shirt",
        "shirts",
        "blouse",
        "blouses",
        "t shirt",
        "t shirts",
        "tee",
        "tees",
        "men s crew t shirts",
    }


def _should_suppress_apparel_breathability_cluster_issue(
    *,
    canonical: str,
    aspect_key: str,
    sub_category: str,
    source_detail: str,
    cluster_propagated: bool,
    evidence_verified: bool,
) -> bool:
    return (
        canonical == "not_breathable"
        and aspect_key in {"comfort", "breathability", "mobility"}
        and _is_apparel_comfort_sub_category(sub_category)
        and cluster_propagated
        and not evidence_verified
        and source_detail.lower() == "sentiment_recovery_rule"
    )


_NEGATED_WATER_LEAK_PATTERNS = [
    r"\bno\s+leaks?\b",
    r"\bno\s+water\s+intrusion\b",
    r"\bwithout\s+(any\s+)?leaks?\b",
    r"\bnever\s+(had\s+)?leaks?\b",
    r"\b(did|does|do|has|have|had)(?:n['’]?t| not)\s+(?:experience|experienced|had|have|see|seen)\s+(?:any\s+)?leak(?:ing|s)?\b",
    r"\b(did|does|do|has|have|had)(?:n['’]?t| not)\s+leak(?:ed|ing|s)?\b",
    r"\b(?:do|does|did)(?:n['’]?t| not)\s+see[^.!?\n]{0,80}\bleak\b",
    r"\bnot\s+a\s+leak\b",
    r"\bnot\s+leaking\b",
]

_POSITIVE_DRY_PATTERNS = [
    r"\b(remained|stayed|kept|keep|keeps)\s+(?:me\s+|my\s+\w+\s+)?dry\b",
]

_WATER_LEAK_HIT_PATTERNS = [
    r"\bnot waterproof\b",
    r"\bnot\s+100%\s+waterproof\b",
    r"\bleak",
    r"\bmoisture\s+coming\s+through\b",
    r"\bwater (gets|got|came|comes|coming|enters|entered) (in|through)",
]

_NON_CURRENT_PRODUCT_LEAK_PATTERNS = [
    r"\bafter\s+(?:my|our|the|his|her)\s+[^.!?]{0,80}\b(?:old|previous|last|magellan|brand|ones?)\b[^.!?]{0,80}\bleak",
    r"\b(?:old|previous|last|other)\s+(?:pair|one|ones|waders?)\b[^.!?]{0,80}\bleak",
    r"\b(?:ones?|waders?)\s+(?:he|she|they|i|we)\s+had\b[^.!?]{0,80}\bleak",
    r"\b(?:pair|one|ones|waders?)\s+from\s+another\s+(?:company|brand)\b[^.!?\n]{0,100}\bleak",
    r"\b(?:heard|reviews?\s+saying)[^.!?\n]{0,100}\bleak",
    r"\bleaks?\s+on\s+some\s+pairs\b",
    r"\bunlike\s+(?:my|our|the|his|her)\s+(?:old|previous|last)\s+(?:pair|one|ones|waders?)\b",
]

_ACCESSORY_LEAK_CONTEXT_PATTERNS = [
    r"\b(?:pockets?|storage pocket|phone case|case|bag)\b[^.!?\n]{0,80}\bleak",
    r"\bleak(?:ing|ed|s)?\b[^.!?\n]{0,80}\b(?:pockets?|storage pocket|phone case|case|bag)\b",
    r"\b(?:pockets?|storage pocket|hand warmer pocket|phone case|case|bag)\b[^.!?\n]{0,80}\b(?:water gets in|wet|soak)",
    r"\b(?:water gets in|wet|soak)[^.!?\n]{0,80}\b(?:pockets?|storage pocket|hand warmer pocket|phone case|case|bag)\b",
]

_CURRENT_PRODUCT_LEAK_CONTEXT_PATTERNS = [
    r"\b(?:waders?|boot|boots|feet|foot|material|seam|neoprene)\b",
    r"\bnot\s+(?:100%\s+)?waterproof\b",
]

_WATER_LEAK_EVIDENCE_PATTERNS = [
    r"\bnot\s+(?:100%\s+)?waterproof(?:\s+material)?\b",
    r"\bwater\s+leaking\s+(?:in|through)\b",
    r"\bwater\s+(?:gets|got|came|comes|coming|enters|entered)\s+(?:in|through)\b",
    r"\bmoisture\s+coming\s+through\b",
    r"\b(?:both\s+feet\s+are\s+)?leaking\s+around\s+where\s+the\s+boot\s+connects\s+to\s+the\s+wader\b",
    r"\bleak(?:ing|ed|s)?\s+(?:at|around|through|near|from)\s+(?:the\s+)?(?:seams?|boots?|waders?|material|knees?|padding)\b",
    r"\bleaks?\s+(?:around|through|at|near|from)\b[^,.!?\n]{0,80}",
    r"\b(?:are|is|was|were|started|began)\s+leaking\b[^.!?\n]{0,80}",
    r"\bleaked\s+through\b",
    r"\bleak(?:ing|ed|s)?\b",
]


def _is_negated_water_leak_statement(text: str) -> bool:
    return _first_regex(_NEGATED_WATER_LEAK_PATTERNS, text)


def _is_positive_dry_statement(text: str) -> bool:
    return _first_regex(_POSITIVE_DRY_PATTERNS, text) and not _first_regex(
        _WATER_LEAK_HIT_PATTERNS,
        text,
    )


def _water_leak_issue_hit(evidence: str, content: str) -> bool:
    basis = evidence.strip() or content[:400]
    if _is_negated_water_leak_statement(basis) or _is_positive_dry_statement(basis):
        return False
    text = f"{evidence} {content[:400]}".lower()
    text = re.sub(r"\bno\s+leaks?\b", " ", text)
    text = re.sub(r"\bno\s+water\s+intrusion\b", " ", text)
    text = re.sub(r"\bwithout\s+(any\s+)?leaks?\b", " ", text)
    text = re.sub(r"\bnever\s+(had\s+)?leaks?\b", " ", text)
    text = re.sub(r"\b(did|does|do|has|have|had)(?:n['’]?t| not)\s+(?:experience|experienced|had|have|see|seen)\s+(?:any\s+)?leak(?:ing|s)?\b", " ", text)
    text = re.sub(r"\b(did|does|do|has|have|had)(?:n['’]?t| not)\s+leak(?:ed|ing|s)?\b", " ", text)
    text = re.sub(r"\b(?:do|does|did)(?:n['’]?t| not)\s+see[^.!?\n]{0,80}\bleak\b", " ", text)
    text = re.sub(r"\bnot\s+a\s+leak\b", " ", text)
    text = re.sub(r"\bnot\s+leaking\b", " ", text)
    return _first_regex(_WATER_LEAK_HIT_PATTERNS, text)


def _is_non_current_product_leak_context(text: str) -> bool:
    return _first_regex(_NON_CURRENT_PRODUCT_LEAK_PATTERNS, text)


def _is_accessory_only_leak_context(text: str) -> bool:
    return _first_regex(_ACCESSORY_LEAK_CONTEXT_PATTERNS, text) and not _first_regex(
        _CURRENT_PRODUCT_LEAK_CONTEXT_PATTERNS,
        text,
    )


def _sentence_spans(text: str) -> list[tuple[int, str]]:
    spans: list[tuple[int, str]] = []
    for match in re.finditer(r"[^.!?\n]+(?:[.!?]+|$)", text):
        sentence = match.group(0)
        stripped = sentence.strip()
        if not stripped:
            continue
        offset = len(sentence) - len(sentence.lstrip())
        spans.append((match.start() + offset, stripped))
    return spans or [(0, text.strip())] if text.strip() else []


def _first_water_leak_evidence_span(sentence: str) -> str:
    for pattern in _WATER_LEAK_EVIDENCE_PATTERNS:
        match = re.search(pattern, sentence, re.IGNORECASE)
        if match:
            return sentence[match.start() : match.end()].strip()
    return ""


def _current_product_water_leak_evidence(content: str) -> str:
    for _start, sentence in _sentence_spans(content):
        if _is_negated_water_leak_statement(sentence) or _is_positive_dry_statement(sentence):
            continue
        if _is_non_current_product_leak_context(sentence) or _is_accessory_only_leak_context(sentence):
            continue
        evidence = _first_water_leak_evidence_span(sentence)
        if not evidence:
            continue
        if not _water_leak_issue_hit(evidence, sentence):
            continue
        return evidence
    return ""


def _evidence_verified(content: str, evidence: str, *, cluster_propagated: bool = False) -> bool:
    return bool(evidence and evidence in content and not cluster_propagated)


def _locate_evidence_span(content: str, evidence: str) -> dict[str, Any]:
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

    end = start + len(evidence)
    return {
        "evidence_span": content[start:end],
        "evidence_start": start,
        "evidence_end": end,
        "evidence_verified": True,
    }


def _occurrence_source(source_detail: str) -> str:
    source_detail = str(source_detail or "").strip().lower()
    if source_detail in _OCCURRENCE_SOURCES:
        return source_detail
    if source_detail.startswith("legacy_"):
        return "legacy"
    if source_detail.startswith("human_"):
        return "human"
    if source_detail in {"llm_canonical_hint", "llm"}:
        return "llm"
    return "rule"


def _clean_occurrence_source(source: str, source_detail: str = "") -> str:
    cleaned = str(source or "").strip().lower()
    if cleaned in _OCCURRENCE_SOURCES:
        return cleaned
    return _occurrence_source(source_detail)


def _clean_confidence(confidence: Any, default: str = "medium") -> str:
    cleaned = str(confidence or "").strip().lower()
    return cleaned if cleaned in {"high", "medium", "low"} else default


def _display_label_for_locale(en_label: str, zh_label: str, locale: str) -> str:
    if locale.startswith("zh") and zh_label:
        return zh_label
    return en_label or zh_label


def _aspect_dimension_labels(aspect: dict[str, Any], aspect_key: str) -> tuple[str, str]:
    if not aspect_key:
        return ("", "")
    return (
        _display_aspect_label(aspect, aspect_key, "en"),
        _display_aspect_label(aspect, aspect_key, "zh"),
    )


def _build_customer_label_occurrence(
    *,
    label_type: str,
    comment_id: Any,
    content: str,
    aspect: dict[str, Any],
    aspect_key: str,
    raw_label: str,
    canonical_label_key: str,
    display_label_en: str,
    display_label_zh: str,
    evidence_span: str,
    confidence: str,
    source_detail: str,
    sub_category: str,
    cluster_propagated: bool,
    display_allowed: bool = True,
    catalog_source: str = "",
    catalog_ruleset_version: str = "",
) -> dict[str, Any]:
    evidence = _locate_evidence_span(content, evidence_span)
    dimension_en, dimension_zh = _aspect_dimension_labels(aspect, aspect_key)
    source = _occurrence_source(source_detail)
    return {
        "comment_id": comment_id,
        "type": label_type,
        "raw_label": str(raw_label or "").strip(),
        "canonical_label_key": str(canonical_label_key or "").strip(),
        "display_label_en": str(display_label_en or "").strip(),
        "display_label_zh": str(display_label_zh or "").strip(),
        "aspect_key": aspect_key,
        "dimension_en": dimension_en,
        "dimension_zh": dimension_zh,
        "sub_category": sub_category,
        "evidence_span": evidence["evidence_span"],
        "evidence_start": evidence["evidence_start"],
        "evidence_end": evidence["evidence_end"],
        "confidence": _clean_confidence(confidence),
        "source": source,
        "source_detail": source_detail,
        "evidence_verified": evidence["evidence_verified"],
        "cluster_propagated": bool(cluster_propagated),
        "schema_version": CUSTOMER_LABEL_OCCURRENCE_SCHEMA_VERSION,
        "ruleset_version": CUSTOMER_LABEL_OCCURRENCE_RULESET_VERSION,
        "display_allowed": bool(display_allowed),
        "customer_label_catalog_source": catalog_source,
        "customer_label_catalog_ruleset_version": catalog_ruleset_version,
    }


def _issue_occurrence_from_normalized(
    *,
    comment_id: Any,
    content: str,
    aspect: dict[str, Any],
    issue: dict[str, Any],
    cluster_propagated: bool,
) -> dict[str, Any]:
    return _build_customer_label_occurrence(
        label_type="issue",
        comment_id=comment_id,
        content=content,
        aspect=aspect,
        aspect_key=str(issue.get("aspect_key") or ""),
        raw_label=str(issue.get("specific_issue_raw") or ""),
        canonical_label_key=str(issue.get("canonical_issue_key") or ""),
        display_label_en=str(issue.get("specific_issue") or ""),
        display_label_zh=str(issue.get("specific_issue_zh") or ""),
        evidence_span=str(issue.get("evidence_span") or ""),
        confidence=str(issue.get("issue_confidence") or "medium"),
        source_detail=str(issue.get("issue_source") or ""),
        sub_category=str(issue.get("sub_category") or ""),
        cluster_propagated=cluster_propagated,
        display_allowed=bool(issue.get("display_allowed")),
        catalog_source=str(issue.get("customer_label_catalog_source") or ""),
        catalog_ruleset_version=str(issue.get("customer_label_catalog_ruleset_version") or ""),
    )


def _water_leak_occurrence_from_content(
    *,
    comment_id: Any,
    content: str,
    sub_category: str,
    locale: str,
) -> dict[str, Any] | None:
    evidence = _current_product_water_leak_evidence(content)
    if not evidence:
        return None

    issue = "Water Leaks Through"
    issue_zh = _specific_issue_zh_label("water_leaks_through", issue)
    catalog = resolve_customer_label(
        label_type="issue",
        canonical_label_key="water_leaks_through",
        display_en=issue,
        display_zh=issue_zh,
        raw_label=issue,
        aspect_key="waterproof",
        sub_category_key=sub_category,
        confidence="high",
        display_allowed=True,
    )
    display_en = catalog.display_en or issue
    display_zh = catalog.display_zh or issue_zh
    return _build_customer_label_occurrence(
        label_type="issue",
        comment_id=comment_id,
        content=content,
        aspect={"key": "waterproof"},
        aspect_key="waterproof",
        raw_label=issue,
        canonical_label_key=catalog.canonical_label_key,
        display_label_en=display_en,
        display_label_zh=display_zh,
        evidence_span=evidence,
        confidence=catalog.confidence if catalog.confidence in {"high", "medium", "low"} else "high",
        source_detail="current_product_leak_text_rule",
        sub_category=sub_category,
        cluster_propagated=False,
        display_allowed=catalog.display_allowed,
        catalog_source=catalog.source,
        catalog_ruleset_version=catalog.ruleset_version,
    )


def _append_content_rule_issue_occurrences(
    comment: dict[str, Any],
    occurrences: list[dict[str, Any]],
    *,
    locale: str,
    aspects_json: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    if any(
        str(item.get("canonical_issue_key") or item.get("canonical_label_key") or "")
        == "water_leaks_through"
        for item in occurrences
    ):
        return occurrences

    content = str(comment.get("content") or "").strip()
    sub_category = str(
        (aspects_json or {}).get("sub_category")
        or comment.get("sub_category")
        or comment.get("category")
        or ""
    )
    occurrence = _water_leak_occurrence_from_content(
        comment_id=comment.get("id"),
        content=content,
        sub_category=sub_category,
        locale=locale,
    )
    if not occurrence:
        return occurrences
    projected = _project_customer_label_occurrence(
        occurrence,
        comment=comment,
        label_type="issue",
        locale=locale,
    )
    if projected:
        occurrences.append(projected)
    return occurrences


def _highlight_occurrence_from_normalized(
    *,
    comment_id: Any,
    content: str,
    aspect: dict[str, Any],
    highlight: dict[str, Any],
    cluster_propagated: bool,
) -> dict[str, Any]:
    return _build_customer_label_occurrence(
        label_type="highlight",
        comment_id=comment_id,
        content=content,
        aspect=aspect,
        aspect_key=str(highlight.get("aspect_key") or ""),
        raw_label=str(highlight.get("customer_highlight_raw") or ""),
        canonical_label_key=str(highlight.get("canonical_highlight_key") or ""),
        display_label_en=str(highlight.get("customer_highlight") or ""),
        display_label_zh=str(highlight.get("customer_highlight_zh") or ""),
        evidence_span=str(highlight.get("evidence_span") or ""),
        confidence=str(highlight.get("highlight_confidence") or "medium"),
        source_detail=str(highlight.get("highlight_source") or ""),
        sub_category=str(highlight.get("sub_category") or ""),
        cluster_propagated=cluster_propagated,
        display_allowed=bool(highlight.get("highlight_display_allowed")),
        catalog_source=str(highlight.get("customer_label_catalog_source") or ""),
        catalog_ruleset_version=str(highlight.get("customer_label_catalog_ruleset_version") or ""),
    )


def _project_customer_label_occurrence(
    occurrence: dict[str, Any],
    *,
    comment: dict[str, Any],
    label_type: str,
    locale: str,
    inherited_cluster_propagated: bool = False,
) -> dict[str, Any] | None:
    if str(occurrence.get("type") or "").strip().lower() != label_type:
        return None
    if occurrence.get("display_allowed") is False:
        return None

    content = str(comment.get("content") or "").strip()
    canonical = str(occurrence.get("canonical_label_key") or "").strip()
    if not canonical:
        return None

    display_en = str(occurrence.get("display_label_en") or "").strip()
    display_zh = str(occurrence.get("display_label_zh") or "").strip()
    display_label = _display_label_for_locale(display_en, display_zh, locale)
    aspect_key = str(occurrence.get("aspect_key") or "").strip()
    dimension_en = str(occurrence.get("dimension_en") or "").strip()
    dimension_zh = str(occurrence.get("dimension_zh") or "").strip()
    if aspect_key and (not dimension_en or not dimension_zh):
        fallback_en, fallback_zh = _aspect_dimension_labels({}, aspect_key)
        dimension_en = dimension_en or fallback_en
        dimension_zh = dimension_zh or fallback_zh
    dimension = _display_label_for_locale(dimension_en, dimension_zh, locale)
    if not display_label or not _is_customer_label_allowed(
        display_label,
        locale=locale,
        aspect_key=aspect_key,
        aspect_label=dimension,
    ):
        return None

    stored_evidence = str(occurrence.get("evidence_span") or "").strip()
    evidence = _locate_evidence_span(content, stored_evidence)
    if not content:
        evidence = {
            "evidence_span": stored_evidence,
            "evidence_start": int(occurrence.get("evidence_start") or -1),
            "evidence_end": int(occurrence.get("evidence_end") or -1),
            "evidence_verified": bool(occurrence.get("evidence_verified")),
        }
    if "cluster_propagated" in occurrence:
        cluster_propagated = bool(occurrence.get("cluster_propagated"))
    else:
        cluster_propagated = bool(inherited_cluster_propagated)
    evidence_verified = bool(evidence["evidence_verified"])
    representative_verified = evidence_verified and not cluster_propagated
    confidence = _clean_confidence(occurrence.get("confidence"), default="low")
    source_detail = str(occurrence.get("source_detail") or "").strip()
    source = _clean_occurrence_source(str(occurrence.get("source") or ""), source_detail)
    occurrence_sub_category = str(
        occurrence.get("sub_category")
        or comment.get("sub_category")
        or comment.get("category")
        or ""
    )
    if label_type == "issue" and _should_suppress_apparel_breathability_cluster_issue(
        canonical=canonical,
        aspect_key=aspect_key,
        sub_category=occurrence_sub_category,
        source_detail=source_detail,
        cluster_propagated=cluster_propagated,
        evidence_verified=evidence_verified,
    ):
        return None
    common = {
        "comment_id": comment.get("id")
        if comment.get("id") is not None
        else occurrence.get("comment_id"),
        "content": content,
        "type": label_type,
        "raw_label": str(occurrence.get("raw_label") or "").strip(),
        "canonical_label_key": canonical,
        "display_label_en": display_en,
        "display_label_zh": display_zh,
        "aspect_key": aspect_key,
        "dimension": dimension,
        "dimension_en": dimension_en,
        "dimension_zh": dimension_zh,
        "sub_category": occurrence_sub_category,
        "evidence_span": evidence["evidence_span"],
        "evidence_start": evidence["evidence_start"],
        "evidence_end": evidence["evidence_end"],
        "confidence": confidence,
        "source": source,
        "source_detail": source_detail,
        "evidence_verified": evidence_verified,
        "verified_evidence": representative_verified,
        "cluster_propagated": cluster_propagated,
        "schema_version": str(
            occurrence.get("schema_version") or CUSTOMER_LABEL_OCCURRENCE_SCHEMA_VERSION
        ),
        "ruleset_version": str(
            occurrence.get("ruleset_version") or CUSTOMER_LABEL_OCCURRENCE_RULESET_VERSION
        ),
        "display_allowed": True,
        "source_review_allowed": bool(content and representative_verified),
        "legacy_fallback": False,
    }
    if label_type == "issue":
        issue_source = source_detail or source
        return {
            **common,
            "specific_issue": display_label,
            "specific_issue_en": display_en,
            "specific_issue_zh": display_zh or display_en,
            "canonical_issue_key": canonical,
            "issue_confidence": confidence,
            "issue_source": issue_source,
            "customer_label_catalog_source": occurrence.get("customer_label_catalog_source", ""),
            "customer_label_catalog_ruleset_version": occurrence.get(
                "customer_label_catalog_ruleset_version",
                "",
            ),
            "specific_issue_raw": common["raw_label"],
        }
    highlight_source = source_detail or source
    return {
        **common,
        "customer_highlight": display_label,
        "customer_highlight_en": display_en,
        "customer_highlight_zh": display_zh or display_en,
        "canonical_highlight_key": canonical,
        "highlight_confidence": confidence,
        "highlight_source": highlight_source,
        "customer_label_catalog_source": occurrence.get("customer_label_catalog_source", ""),
        "customer_label_catalog_ruleset_version": occurrence.get(
            "customer_label_catalog_ruleset_version",
            "",
        ),
        "customer_highlight_raw": common["raw_label"],
        "highlight_display_allowed": True,
    }


def _project_customer_label_occurrences(
    comment: dict[str, Any],
    *,
    label_type: str,
    locale: str,
    aspects_json: dict[str, Any],
) -> list[dict[str, Any]]:
    raw_occurrences = aspects_json.get("customer_label_occurrences")
    if not isinstance(raw_occurrences, list):
        return []
    projected: list[dict[str, Any]] = []
    for occurrence in raw_occurrences:
        if not isinstance(occurrence, dict):
            continue
        item = _project_customer_label_occurrence(
            occurrence,
            comment=comment,
            label_type=label_type,
            locale=locale,
            inherited_cluster_propagated=bool(aspects_json.get("cluster_propagated")),
        )
        if item:
            projected.append(item)
    return projected


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
        if _water_leak_issue_hit(evidence, content):
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
        if _not_breathable_issue_hit(text):
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


def _issue_from_existing(
    aspect: dict[str, Any],
    aspect_key: str,
    label: str,
    locale: str,
) -> tuple[str, str, str, str, str, bool] | None:
    specific_issue = str(aspect.get("specific_issue") or "").strip()
    specific_issue_zh = str(aspect.get("specific_issue_zh") or "").strip()
    raw_issue = str(aspect.get("specific_issue_raw") or specific_issue or aspect.get("canonical_hint") or "").strip()
    if not raw_issue:
        return None

    issue = _customer_title(specific_issue or raw_issue)
    canonical = str(aspect.get("canonical_issue_key") or "").strip() or _slug(issue)
    issue_zh = specific_issue_zh or _specific_issue_zh_label(canonical, issue)
    display_label = issue_zh if locale.startswith("zh") else issue
    display_allowed = _is_customer_label_allowed(display_label, locale=locale, aspect_key=aspect_key, aspect_label=label)
    if aspect.get("display_allowed") is False or aspect.get("issue_source") == "broad_fallback":
        display_allowed = False
    return (issue, issue_zh, canonical, "llm_canonical_hint", raw_issue, display_allowed)


def _normalize_aspect_issue(
    aspect: dict[str, Any],
    *,
    sub_category: str,
    content: str,
    locale: str,
    cluster_propagated: bool = False,
) -> dict[str, Any] | None:
    aspect_key = str(aspect.get("key") or aspect.get("aspect_key") or "").strip()
    if not aspect_key:
        return None

    label = _display_aspect_label(aspect, aspect_key, locale)
    evidence = str(aspect.get("evidence_span") or aspect.get("evidence") or "").strip()
    polarity = str(aspect.get("polarity") or "").lower()
    recovered_rule_hit = None
    if polarity != "negative":
        recovered_rule_hit = _issue_from_rules(aspect_key, evidence, content)
        if recovered_rule_hit and _should_suppress_apparel_breathability_cluster_issue(
            canonical=recovered_rule_hit[1],
            aspect_key=aspect_key,
            sub_category=sub_category,
            source_detail="sentiment_recovery_rule",
            cluster_propagated=cluster_propagated,
            evidence_verified=_locate_evidence_span(content, evidence)["evidence_verified"],
        ):
            recovered_rule_hit = _issue_from_rules(aspect_key, evidence, "")
        if not recovered_rule_hit:
            return None
    existing = None if recovered_rule_hit else _issue_from_existing(aspect, aspect_key, label, locale)

    confidence = str(aspect.get("issue_confidence") or "").lower()
    if confidence not in {"high", "medium", "low"}:
        confidence = "medium"

    if existing:
        issue, issue_zh, canonical, source, raw, display_allowed = existing
    else:
        rule_hit = recovered_rule_hit or _issue_from_rules(aspect_key, evidence, content)
        if rule_hit:
            issue, canonical, source = rule_hit
            issue_zh = _specific_issue_zh_label(canonical, issue)
            raw = issue
            confidence = "high" if source.endswith("alias_rule") else confidence
            if recovered_rule_hit:
                source = "sentiment_recovery_rule"
            display_label = issue_zh if locale.startswith("zh") else issue
            display_allowed = _is_customer_label_allowed(display_label, locale=locale, aspect_key=aspect_key, aspect_label=label)
        else:
            issue = f"{label} Issue"
            issue_zh = f"{label}问题" if locale.startswith("zh") else issue
            canonical = _slug(issue)
            source = "broad_fallback"
            raw = evidence or label
            confidence = "low"
            display_allowed = False

    forced_hidden = (
        source == "broad_fallback"
        or aspect.get("display_allowed") is False
        or aspect.get("issue_source") == "broad_fallback"
    )
    catalog = resolve_customer_label(
        label_type="issue",
        canonical_label_key=canonical,
        display_en=issue,
        display_zh=issue_zh,
        raw_label=raw,
        aspect_key=aspect_key,
        sub_category_key=sub_category,
        confidence=confidence,
        display_allowed=not forced_hidden,
    )
    issue = catalog.display_en or issue
    issue_zh = catalog.display_zh or issue_zh
    canonical = catalog.canonical_label_key
    confidence = catalog.confidence if catalog.confidence in {"high", "medium", "low"} else confidence
    display_allowed = False if forced_hidden else catalog.display_allowed

    return {
        "specific_issue": issue,
        "specific_issue_zh": issue_zh,
        "canonical_issue_key": canonical,
        "issue_confidence": confidence,
        "issue_source": source,
        "customer_label_catalog_source": catalog.source,
        "customer_label_catalog_ruleset_version": catalog.ruleset_version,
        "specific_issue_raw": raw,
        "display_allowed": bool(display_allowed),
        "aspect_key": aspect_key,
        "dimension": label,
        "sub_category": sub_category,
        "evidence_span": evidence,
    }


def _highlight_label(en: str, zh: str, canonical: str, source: str) -> tuple[str, str, str, str]:
    return (en, zh, canonical, source)


def _is_negative_phrase(text: str) -> bool:
    text = re.sub(r"\b(no|without)\s+leaks?\b", " ", text)
    text = re.sub(r"\bnever\s+get\s+wet\b", " ", text)
    return _first_regex(
        [
            r"\bnot waterproof\b",
            r"\bleak",
            r"\bwater (gets|got|came|comes|coming|enters|entered) (in|through)",
            r"\b(broke|broken|breaks|fell apart|falls apart)\b",
            r"\btoo (small|large|tight|loose|expensive)\b",
            r"\bruns (small|large)\b",
            r"\breturn(ed|ing)?\b",
            r"\brefund\b",
            r"\bcheap\b.*\b(material|plastic|quality)\b",
        ],
        text,
    )


def _highlight_from_rules(aspect_key: str, evidence: str, content: str) -> tuple[str, str, str, str] | None:
    text = f"{evidence} {content[:400]}".lower()
    if _is_negative_phrase(text):
        return None

    if aspect_key in {"waterproof", "waterproof_performance", "seam_integrity"}:
        if _first_regex([r"\b(waterproof|kept|keep|keeps|stayed|stay)\b.*\b(dry|water out)\b", r"\bnever get wet\b", r"\bno leaks?\b"], text):
            return _highlight_label("Keeps Water Out", "防水可靠", "keeps_water_out", "regex_alias_rule")

    if aspect_key in {"boot_fit", "size_fit"}:
        if _first_regex([r"\bfit(s|ted)?\b.*\b(perfect|great|well|right|true)\b", r"\btrue to size\b", r"\bboots? fit"], text):
            return _highlight_label("Fits as Expected", "尺码合适", "fits_as_expected", "regex_alias_rule")

    if aspect_key in {"comfort", "breathability", "mobility"}:
        if _first_regex([r"\bcomfortable\b", r"\beasy\b.*\b(move|walk|bend)", r"\bflexible\b"], text):
            return _highlight_label("Comfortable To Wear", "穿着舒适", "comfortable_to_wear", "regex_alias_rule")
        if _first_regex([r"\bbreathable\b", r"\bnot hot\b"], text):
            return _highlight_label("Breathes Well", "透气性好", "breathes_well", "regex_alias_rule")

    if aspect_key in {"build_quality", "durability", "material", "strength", "stability"}:
        if _first_regex([r"\b(held|holds?) up\b", r"\bstill going strong\b", r"\bdurable\b", r"\btough\b"], text):
            return _highlight_label("Holds Up Well", "耐用可靠", "holds_up_well", "regex_alias_rule")
        if _first_regex([r"\b(good|great|nice|excellent)\b.*\bquality\b", r"\bquality product\b", r"\bwell made\b", r"\bsturdy\b", r"\bsolid\b"], text):
            return _highlight_label("Feels Well Made", "做工扎实", "feels_well_made", "regex_alias_rule")

    if aspect_key in {"value_for_money"}:
        if _first_regex([r"\bgood value\b", r"\bgreat value\b", r"\bfor the price\b", r"\bworth\b", r"\baffordable\b", r"\bcost way less\b"], text):
            return _highlight_label("Good Value for the Price", "性价比高", "good_value_for_the_price", "regex_alias_rule")

    if aspect_key in {"ease_of_use"}:
        if _first_regex([r"\beasy to use\b", r"\beasy\b.*\b(clean|put on|fit|adjust)", r"\bconvenient\b"], text):
            return _highlight_label("Easy To Use", "使用方便", "easy_to_use", "regex_alias_rule")

    if aspect_key in {"accessory_storage", "organization", "capacity"}:
        if _first_regex([r"\b(plenty|enough|great|good)\b.*\b(pockets?|storage|room|space)\b", r"\bconvenient storage\b"], text):
            return _highlight_label("Useful Storage Space", "收纳空间实用", "useful_storage_space", "regex_alias_rule")

    if aspect_key in {"grip"}:
        if _first_regex([r"\b(good|great|solid)\b.*\b(grip|traction)\b", r"\bnon[- ]?slip\b", r"\bsoles?\b.*\b(thick|grip|traction)\b"], text):
            return _highlight_label("Good Traction", "抓地稳", "good_traction", "regex_alias_rule")

    if aspect_key in {"shipping_damage", "packaging"}:
        if _first_regex([r"\bfast\b.*\b(delivery|shipping)\b", r"\barrived\b.*\b(on time|scheduled|intact|safe)\b", r"\bcame on time\b"], text):
            return _highlight_label("Arrives On Time and Intact", "到货及时完好", "arrives_on_time_and_intact", "regex_alias_rule")

    if aspect_key in {"aesthetics", "color_accuracy"}:
        if _first_regex([r"\b(look|looks|looked)\b.*\b(great|good|nice|beautiful)\b", r"\bnice looking\b"], text):
            return _highlight_label("Looks Good", "外观好看", "looks_good", "regex_alias_rule")

    if aspect_key in {"smell", "scent"}:
        if _first_regex([r"\b(no|not much|without)\b.*\b(smell|odor|scent)\b"], text):
            return _highlight_label("No Strong Odor", "没有明显异味", "no_strong_odor", "regex_alias_rule")

    if aspect_key in {"battery_life"}:
        if _first_regex([r"\bbattery\b.*\b(long|lasts?|holds?)\b", r"\blong battery\b"], text):
            return _highlight_label("Long Battery Life", "续航时间长", "long_battery_life", "regex_alias_rule")

    if aspect_key in {"charging"}:
        if _first_regex([r"\bcharg(es|ed|ing)?\b.*\b(fast|quick|well|easy)\b"], text):
            return _highlight_label("Charges Reliably", "充电稳定", "charges_reliably", "regex_alias_rule")

    if aspect_key in {"clumping", "separation_definition"}:
        if _first_regex([r"\b(no|without)\b.*\bclump", r"\bseparat(es|ed|ion)\b"], text):
            return _highlight_label("Separates Without Clumps", "不易结块根根分明", "separates_without_clumps", "regex_alias_rule")

    if aspect_key in {"smudge_resistance"}:
        if _first_regex([r"\b(no|without|not)\b.*\b(smudge|smear|run)", r"\bsmudge[- ]?proof\b"], text):
            return _highlight_label("Does Not Smudge", "不易晕染", "does_not_smudge", "regex_alias_rule")

    if aspect_key in {"lengthening_effect"}:
        if _first_regex([r"\blength(en|ens|ening)?\b", r"\blong lashes\b"], text):
            return _highlight_label("Adds Noticeable Length", "纤长效果明显", "adds_noticeable_length", "regex_alias_rule")

    if aspect_key in {"volumizing_effect"}:
        if _first_regex([r"\bvolume\b", r"\bvolumiz"], text):
            return _highlight_label("Adds Visible Volume", "浓密效果明显", "adds_visible_volume", "regex_alias_rule")

    if aspect_key in {"curl_hold"}:
        if _first_regex([r"\bcurl\b.*\b(hold|last|stay)", r"\bholds? curl\b"], text):
            return _highlight_label("Holds Curl Well", "卷翘保持好", "holds_curl_well", "regex_alias_rule")

    return None


def _highlight_from_existing(
    aspect: dict[str, Any],
    aspect_key: str,
    label_en: str,
    label_zh: str,
    locale: str,
) -> tuple[str, str, str, str, str, bool] | None:
    highlight = str(aspect.get("customer_highlight") or aspect.get("specific_highlight") or "").strip()
    highlight_zh = str(aspect.get("customer_highlight_zh") or "").strip()
    raw = str(aspect.get("customer_highlight_raw") or highlight or aspect.get("highlight_hint") or "").strip()
    if not raw:
        return None

    highlight_en = _customer_title(highlight or raw)
    if not highlight_zh:
        highlight_zh = highlight_en
    canonical = str(aspect.get("canonical_highlight_key") or "").strip() or _slug(highlight_en)
    display_label = highlight_zh if locale.startswith("zh") else highlight_en
    display_allowed = _is_customer_label_allowed(
        display_label,
        locale=locale,
        aspect_key=aspect_key,
        aspect_label=label_zh if locale.startswith("zh") else label_en,
    )
    if aspect.get("highlight_display_allowed") is False or aspect.get("highlight_source") == "broad_fallback":
        display_allowed = False
    return (highlight_en, highlight_zh, canonical, "llm_canonical_hint", raw, display_allowed)


def _generic_positive_highlight(
    aspect_key: str,
    label_en: str,
    label_zh: str,
    evidence: str,
    content: str,
    locale: str,
) -> tuple[str, str, str, str, str, bool]:
    text = f"{evidence} {content[:240]}".lower()
    if _is_negative_phrase(text):
        return ("", "", "", "broad_fallback", evidence or label_en, False)
    if not evidence:
        return ("", "", "", "broad_fallback", label_en, False)
    if not _is_customer_label_allowed(label_en, locale="en", aspect_key=aspect_key, aspect_label=label_en):
        return ("", "", "", "broad_fallback", evidence or label_en, False)
    highlight_en = f"{label_en} Works Well"
    highlight_zh = f"{label_zh}表现好"
    display_label = highlight_zh if locale.startswith("zh") else highlight_en
    return (
        highlight_en,
        highlight_zh,
        _slug(highlight_en),
        "generic_positive_fallback",
        evidence,
        _is_customer_label_allowed(display_label, locale=locale, aspect_key=aspect_key, aspect_label=label_zh if locale.startswith("zh") else label_en),
    )


def _normalize_aspect_highlight(
    aspect: dict[str, Any],
    *,
    sub_category: str,
    content: str,
    locale: str,
) -> dict[str, Any] | None:
    aspect_key = str(aspect.get("key") or aspect.get("aspect_key") or "").strip()
    if not aspect_key:
        return None
    if str(aspect.get("polarity") or "").lower() != "positive":
        return None

    label_en = _display_aspect_label(aspect, aspect_key, "en")
    label_zh = _display_aspect_label(aspect, aspect_key, "zh")
    evidence = str(aspect.get("evidence_span") or aspect.get("evidence") or "").strip()
    existing = _highlight_from_existing(aspect, aspect_key, label_en, label_zh, locale)

    confidence = str(aspect.get("highlight_confidence") or "").lower()
    if confidence not in {"high", "medium", "low"}:
        confidence = "medium"

    if existing:
        highlight_en, highlight_zh, canonical, source, raw, display_allowed = existing
    else:
        rule_hit = _highlight_from_rules(aspect_key, evidence, content)
        if rule_hit:
            highlight_en, highlight_zh, canonical, source = rule_hit
            raw = evidence or highlight_en
            confidence = "high" if source.endswith("alias_rule") else confidence
            display_label = highlight_zh if locale.startswith("zh") else highlight_en
            display_allowed = _is_customer_label_allowed(
                display_label,
                locale=locale,
                aspect_key=aspect_key,
                aspect_label=label_zh if locale.startswith("zh") else label_en,
            )
        else:
            highlight_en, highlight_zh, canonical, source, raw, display_allowed = _generic_positive_highlight(
                aspect_key,
                label_en,
                label_zh,
                evidence,
                content,
                locale,
            )
            if not highlight_en:
                highlight_en = f"{label_en} Highlight"
                highlight_zh = f"{label_zh}亮点"
                canonical = _slug(highlight_en)
                confidence = "low"
                display_allowed = False

    forced_hidden = (
        source == "broad_fallback"
        or aspect.get("highlight_display_allowed") is False
        or aspect.get("highlight_source") == "broad_fallback"
    )
    catalog = resolve_customer_label(
        label_type="highlight",
        canonical_label_key=canonical,
        display_en=highlight_en,
        display_zh=highlight_zh,
        raw_label=raw,
        aspect_key=aspect_key,
        sub_category_key=sub_category,
        confidence=confidence,
        display_allowed=not forced_hidden,
    )
    highlight_en = catalog.display_en or highlight_en
    highlight_zh = catalog.display_zh or highlight_zh
    canonical = catalog.canonical_label_key
    confidence = catalog.confidence if catalog.confidence in {"high", "medium", "low"} else confidence
    display_allowed = False if forced_hidden else catalog.display_allowed

    return {
        "customer_highlight": highlight_en,
        "customer_highlight_zh": highlight_zh,
        "canonical_highlight_key": canonical,
        "highlight_confidence": confidence,
        "highlight_source": source,
        "customer_label_catalog_source": catalog.source,
        "customer_label_catalog_ruleset_version": catalog.ruleset_version,
        "customer_highlight_raw": raw,
        "highlight_display_allowed": bool(display_allowed),
        "aspect_key": aspect_key,
        "dimension": label_zh if locale.startswith("zh") else label_en,
        "dimension_en": label_en,
        "dimension_zh": label_zh,
        "sub_category": sub_category,
        "evidence_span": evidence,
    }


def enrich_aspects_json(
    aspects_json: Any,
    *,
    sub_category: str = "",
    content: str = "",
    locale: str = "en",
    comment_id: Any = None,
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
    content_text = str(content or "")
    existing_occurrences = enriched.get("customer_label_occurrences")
    occurrences: list[dict[str, Any]] = []
    occurrence_keys: set[tuple[str, str, str, str, str]] = set()

    def _remember_occurrence(item: dict[str, Any]) -> None:
        occurrence_keys.add(
            (
                str(item.get("type") or ""),
                str(item.get("canonical_label_key") or ""),
                str(item.get("aspect_key") or ""),
                str(item.get("raw_label") or ""),
                str(item.get("source_detail") or ""),
            )
        )

    def _append_occurrence(item: dict[str, Any]) -> None:
        _remember_occurrence(item)
        occurrences.append(item)
    for aspect in aspects:
        if not isinstance(aspect, dict):
            continue
        cluster_propagated = bool(enriched.get("cluster_propagated") or aspect.get("cluster_propagated"))
        issue = _normalize_aspect_issue(
            aspect,
            sub_category=normalized_sub_category,
            content=content_text,
            locale=locale,
            cluster_propagated=cluster_propagated,
        )
        if issue:
            aspect.update(
                {
                    "specific_issue": issue["specific_issue"],
                    "specific_issue_zh": issue["specific_issue_zh"],
                    "canonical_issue_key": issue["canonical_issue_key"],
                    "issue_confidence": issue["issue_confidence"],
                    "issue_source": issue["issue_source"],
                    "customer_label_catalog_source": issue["customer_label_catalog_source"],
                    "customer_label_catalog_ruleset_version": issue[
                        "customer_label_catalog_ruleset_version"
                    ],
                    "specific_issue_raw": issue["specific_issue_raw"],
                    "display_allowed": issue["display_allowed"],
                    "aspect_label": issue["dimension"],
                }
            )
            if issue["display_allowed"]:
                _append_occurrence(
                    _issue_occurrence_from_normalized(
                        comment_id=comment_id,
                        content=content_text,
                        aspect=aspect,
                        issue=issue,
                        cluster_propagated=cluster_propagated,
                    )
                )
        highlight = _normalize_aspect_highlight(
            aspect,
            sub_category=normalized_sub_category,
            content=content_text,
            locale=locale,
        )
        if highlight:
            aspect.update(
                {
                    "customer_highlight": highlight["customer_highlight"],
                    "customer_highlight_zh": highlight["customer_highlight_zh"],
                    "canonical_highlight_key": highlight["canonical_highlight_key"],
                    "highlight_confidence": highlight["highlight_confidence"],
                    "highlight_source": highlight["highlight_source"],
                    "customer_label_catalog_source": highlight["customer_label_catalog_source"],
                    "customer_label_catalog_ruleset_version": highlight[
                        "customer_label_catalog_ruleset_version"
                    ],
                    "customer_highlight_raw": highlight["customer_highlight_raw"],
                    "highlight_display_allowed": highlight["highlight_display_allowed"],
                    "aspect_label": highlight["dimension"],
                }
            )
            if highlight["highlight_display_allowed"]:
                _append_occurrence(
                    _highlight_occurrence_from_normalized(
                        comment_id=comment_id,
                        content=content_text,
                        aspect=aspect,
                        highlight=highlight,
                        cluster_propagated=cluster_propagated,
                    )
                )
    if not any(
        str(item.get("canonical_label_key") or "") == "water_leaks_through"
        for item in occurrences
    ):
        water_leak_occurrence = _water_leak_occurrence_from_content(
            comment_id=comment_id,
            content=content_text,
            sub_category=normalized_sub_category,
            locale=locale,
        )
        if water_leak_occurrence:
            _append_occurrence(water_leak_occurrence)
    if isinstance(existing_occurrences, list):
        for item in existing_occurrences:
            if not isinstance(item, dict):
                continue
            key = (
                str(item.get("type") or ""),
                str(item.get("canonical_label_key") or ""),
                str(item.get("aspect_key") or ""),
                str(item.get("raw_label") or ""),
                str(item.get("source_detail") or ""),
            )
            if key not in occurrence_keys:
                _append_occurrence(copy.deepcopy(item))
    enriched["specific_issue_schema_version"] = SPECIFIC_ISSUE_SCHEMA_VERSION
    enriched["customer_label_schema_version"] = CUSTOMER_LABEL_SCHEMA_VERSION
    enriched["customer_label_occurrence_schema_version"] = CUSTOMER_LABEL_OCCURRENCE_SCHEMA_VERSION
    enriched["customer_label_occurrence_ruleset_version"] = CUSTOMER_LABEL_OCCURRENCE_RULESET_VERSION
    if occurrences or aspects or not isinstance(existing_occurrences, list):
        enriched["customer_label_occurrences"] = occurrences
    else:
        enriched["customer_label_occurrences"] = existing_occurrences
    enriched["issue_ruleset_version"] = ISSUE_RULESET_VERSION
    enriched["highlight_ruleset_version"] = HIGHLIGHT_RULESET_VERSION
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
        if not _is_customer_label_allowed(issue, locale=locale):
            continue
        canonical = _slug(issue)
        occurrences.append(
            {
                "comment_id": comment.get("id"),
                "content": content,
                "type": "issue",
                "raw_label": issue,
                "canonical_label_key": canonical,
                "display_label_en": issue,
                "display_label_zh": issue,
                "specific_issue": issue,
                "specific_issue_en": issue,
                "specific_issue_zh": issue,
                "canonical_issue_key": canonical,
                "confidence": "low",
                "issue_confidence": "low",
                "source": "legacy",
                "source_detail": "legacy_issue_tag",
                "issue_source": "legacy_issue_tag",
                "specific_issue_raw": issue,
                "display_allowed": True,
                "aspect_key": "",
                "dimension": "",
                "dimension_en": "",
                "dimension_zh": "",
                "sub_category": str(comment.get("sub_category") or comment.get("category") or ""),
                "evidence_span": "",
                "evidence_start": -1,
                "evidence_end": -1,
                "evidence_verified": False,
                "verified_evidence": False,
                "cluster_propagated": False,
                "schema_version": "",
                "ruleset_version": "",
                "legacy_fallback": True,
            }
        )
    return occurrences


def _append_unique_snippet(target: list[str], content: str, limit: int = 240) -> None:
    snippet = content.strip()[:limit]
    if snippet and snippet not in target:
        target.append(snippet)


def iter_specific_issue_occurrences(comment: dict[str, Any], locale: str = "en") -> list[dict[str, Any]]:
    content = str(comment.get("content") or "").strip()
    aj = coerce_aspects_json(comment.get("aspects_json"))
    schema_version = ""
    occurrence_schema_version = ""
    has_specific_issue_payload = False
    occurrences: list[dict[str, Any]] = []
    if aj:
        schema_version = str(aj.get("specific_issue_schema_version") or "")
        occurrence_schema_version = str(aj.get("customer_label_occurrence_schema_version") or "")
        if occurrence_schema_version == CUSTOMER_LABEL_OCCURRENCE_SCHEMA_VERSION:
            projected = _project_customer_label_occurrences(
                comment,
                label_type="issue",
                locale=locale,
                aspects_json=aj,
            )
            return _append_content_rule_issue_occurrences(
                comment,
                projected,
                locale=locale,
                aspects_json=aj,
            )
        sub_category = str(aj.get("sub_category") or comment.get("sub_category") or "")
        aspects = [aspect for aspect in aj.get("aspects") or [] if isinstance(aspect, dict)]
        has_specific_issue_payload = any(
            any(
                key in aspect
                for key in ("specific_issue", "canonical_issue_key", "display_allowed", "issue_source")
            )
            for aspect in aspects
        )
        if schema_version != SPECIFIC_ISSUE_SCHEMA_VERSION and not has_specific_issue_payload:
            return _legacy_issue_occurrences(comment, locale)
        for aspect in aspects:
            if not isinstance(aspect, dict):
                continue
            issue = _normalize_aspect_issue(
                aspect,
                sub_category=sub_category,
                content=content,
                locale=locale,
                cluster_propagated=bool(aj.get("cluster_propagated") or aspect.get("cluster_propagated")),
            )
            if not issue or not issue["display_allowed"]:
                continue
            unified = _issue_occurrence_from_normalized(
                comment_id=comment.get("id"),
                cluster_propagated=bool(aj.get("cluster_propagated") or aspect.get("cluster_propagated")),
                content=content,
                aspect=aspect,
                issue=issue,
            )
            projected = _project_customer_label_occurrence(
                unified,
                comment=comment,
                label_type="issue",
                locale=locale,
                inherited_cluster_propagated=bool(aj.get("cluster_propagated")),
            )
            if projected:
                occurrences.append(projected)
    if occurrences or schema_version == SPECIFIC_ISSUE_SCHEMA_VERSION or has_specific_issue_payload:
        occurrences = _append_content_rule_issue_occurrences(
            comment,
            occurrences,
            locale=locale,
            aspects_json=aj,
        )
        return occurrences
    return _legacy_issue_occurrences(comment, locale)


def _build_customer_label_rows(
    comments: list[dict[str, Any]],
    *,
    label_type: str,
    locale: str = "en",
    limit: int = 10,
) -> list[dict[str, Any]]:
    if label_type == "issue":
        iterator = iter_specific_issue_occurrences
        label_field = "specific_issue"
        canonical_field = "canonical_issue_key"
        confidence_field = "issue_confidence"
        source_field = "issue_source"
        sources_field = "issue_sources"
        schema_field = "specific_issue_schema_version"
        schema_version = SPECIFIC_ISSUE_SCHEMA_VERSION
        ruleset_field = "issue_ruleset_version"
        ruleset_version = ISSUE_RULESET_VERSION
        is_specific_field = "is_specific_issue"
    elif label_type == "highlight":
        iterator = iter_customer_highlight_occurrences
        label_field = "customer_highlight"
        canonical_field = "canonical_highlight_key"
        confidence_field = "highlight_confidence"
        source_field = "highlight_source"
        sources_field = "highlight_sources"
        schema_field = "customer_label_schema_version"
        schema_version = CUSTOMER_LABEL_SCHEMA_VERSION
        ruleset_field = "highlight_ruleset_version"
        ruleset_version = HIGHLIGHT_RULESET_VERSION
        is_specific_field = "is_customer_highlight"
    else:
        raise ValueError(f"Unsupported customer label type: {label_type}")

    pool_size = len(comments)
    groups: dict[tuple[str, str], dict[str, Any]] = {}
    comment_counts: dict[tuple[str, str], set[Any]] = defaultdict(set)
    raw_occurrence_counter: Counter[tuple[str, str]] = Counter()
    confidence_counter: dict[tuple[str, str], Counter[str]] = defaultdict(Counter)
    label_counter: dict[tuple[str, str], Counter[str]] = defaultdict(Counter)

    for fallback_index, comment in enumerate(comments):
        comment_id = comment.get("id")
        if comment_id is None:
            comment_id = f"row-{fallback_index}"
        counted_in_comment: set[tuple[str, str]] = set()
        for occurrence in iterator(comment, locale=locale):
            canonical = str(
                occurrence.get(canonical_field)
                or occurrence.get("canonical_label_key")
                or ""
            ).strip()
            if not canonical:
                continue
            key = (str(occurrence.get("sub_category") or ""), canonical)
            raw_occurrence_counter[key] += 1
            if key not in groups:
                is_legacy = bool(occurrence.get("legacy_fallback"))
                groups[key] = {
                    "tag": occurrence[label_field],
                    label_field: occurrence[label_field],
                    canonical_field: canonical,
                    "canonical_label_key": canonical,
                    "label_type": label_type,
                    "aspect_key": occurrence.get("aspect_key") or "",
                    "aspect_keys": [],
                    "dimension": "",
                    "dimensions": [],
                    "sub_category": occurrence.get("sub_category") or "",
                    source_field: occurrence.get(source_field) or "",
                    sources_field: [],
                    "legacy_fallback": is_legacy,
                    is_specific_field: not is_legacy,
                    "display_allowed": True,
                    schema_field: "" if is_legacy else schema_version,
                    "customer_label_occurrence_schema_version": (
                        "" if is_legacy else CUSTOMER_LABEL_OCCURRENCE_SCHEMA_VERSION
                    ),
                    ruleset_field: ruleset_version,
                    "representative_comments": [],
                    "evidence_spans": [],
                    "cluster_propagated": False,
                    "reason": "",
                }
            if not occurrence.get("legacy_fallback"):
                groups[key]["legacy_fallback"] = False
                groups[key][is_specific_field] = True
                groups[key][schema_field] = schema_version
                groups[key][
                    "customer_label_occurrence_schema_version"
                ] = CUSTOMER_LABEL_OCCURRENCE_SCHEMA_VERSION
            aspect_key = str(occurrence.get("aspect_key") or "")
            if aspect_key and aspect_key not in groups[key]["aspect_keys"]:
                groups[key]["aspect_keys"].append(aspect_key)
            dimension = str(occurrence.get("dimension") or "")
            if dimension and dimension not in groups[key]["dimensions"]:
                groups[key]["dimensions"].append(dimension)
            source = str(occurrence.get(source_field) or "")
            if source and source not in groups[key][sources_field]:
                groups[key][sources_field].append(source)
            if occurrence.get("cluster_propagated"):
                groups[key]["cluster_propagated"] = True
            label_counter[key][str(occurrence.get(label_field) or groups[key][label_field])] += 1
            if key not in counted_in_comment:
                comment_counts[key].add(comment_id)
                counted_in_comment.add(key)
            confidence_counter[key][str(occurrence.get(confidence_field) or "low")] += 1
            content = str(occurrence.get("content") or "").strip()
            evidence = str(occurrence.get("evidence_span") or "").strip()
            if occurrence.get("verified_evidence") and content:
                _append_unique_snippet(groups[key]["representative_comments"], content)
                if evidence and evidence not in groups[key]["evidence_spans"]:
                    groups[key]["evidence_spans"].append(evidence)

    total_mentions = sum(len(comment_ids) for comment_ids in comment_counts.values())
    rows: list[dict[str, Any]] = []
    for key, row in groups.items():
        mention_count = len(comment_counts[key])
        if mention_count <= 0:
            continue
        mention_share = round(mention_count / total_mentions * 100, 1) if total_mentions else 0.0
        impact_review_share = round(mention_count / pool_size * 100, 1) if pool_size else 0.0
        conf = confidence_counter[key].most_common(1)[0][0] if confidence_counter[key] else "low"
        label = label_counter[key].most_common(1)[0][0] if label_counter[key] else row[label_field]
        aspect_keys = row["aspect_keys"]
        dimensions = row["dimensions"]
        examples = row["representative_comments"][:5]
        evidence_spans = row["evidence_spans"][:5]
        rows.append(
            {
                **row,
                "tag": label,
                label_field: label,
                "aspect_key": aspect_keys[0] if aspect_keys else row.get("aspect_key", ""),
                "aspect_keys": aspect_keys,
                "dimension": ", ".join(dimensions),
                "dimensions": dimensions,
                source_field: row[sources_field][0] if row[sources_field] else row.get(source_field, ""),
                "mention_count": mention_count,
                "mention_share": mention_share,
                "review_count": mention_count,
                "impact_review_share": impact_review_share,
                "raw_occurrence_count": raw_occurrence_counter[key],
                "count": mention_count,
                "pct": mention_share,
                confidence_field: conf,
                "representative_comments": examples,
                "evidence_spans": evidence_spans,
                "evidence_verified": bool(evidence_spans),
                "cluster_propagated": bool(row.get("cluster_propagated")),
                "reason": examples[0] if examples else "No representative comment found.",
            }
        )

    return sorted(rows, key=lambda r: (-int(r["mention_count"]), str(r[label_field]).lower()))[:limit]


def build_specific_issue_rows(
    comments: list[dict[str, Any]],
    *,
    locale: str = "en",
    limit: int = 10,
) -> list[dict[str, Any]]:
    return _build_customer_label_rows(
        comments,
        label_type="issue",
        locale=locale,
        limit=limit,
    )


def _legacy_highlight_occurrences(comment: dict[str, Any], locale: str) -> list[dict[str, Any]]:
    occurrences: list[dict[str, Any]] = []
    content = str(comment.get("content") or "").strip()
    for raw_tag in str(comment.get("highlight_tag") or "").split(","):
        highlight = raw_tag.strip()
        if not highlight:
            continue
        if not _is_customer_label_allowed(highlight, locale=locale):
            continue
        canonical = _slug(highlight)
        occurrences.append(
            {
                "comment_id": comment.get("id"),
                "content": content,
                "type": "highlight",
                "raw_label": highlight,
                "canonical_label_key": canonical,
                "display_label_en": highlight,
                "display_label_zh": highlight,
                "customer_highlight": highlight,
                "customer_highlight_en": highlight,
                "customer_highlight_zh": highlight,
                "canonical_highlight_key": canonical,
                "confidence": "low",
                "highlight_confidence": "low",
                "source": "legacy",
                "source_detail": "legacy_highlight_tag",
                "highlight_source": "legacy_highlight_tag",
                "customer_highlight_raw": highlight,
                "highlight_display_allowed": True,
                "aspect_key": "",
                "dimension": "",
                "dimension_en": "",
                "dimension_zh": "",
                "sub_category": str(comment.get("sub_category") or comment.get("category") or ""),
                "evidence_span": "",
                "evidence_start": -1,
                "evidence_end": -1,
                "evidence_verified": False,
                "verified_evidence": False,
                "cluster_propagated": False,
                "schema_version": "",
                "ruleset_version": "",
                "source_review_allowed": bool(content),
                "legacy_fallback": True,
            }
        )
    return occurrences


def iter_customer_highlight_occurrences(comment: dict[str, Any], locale: str = "en") -> list[dict[str, Any]]:
    content = str(comment.get("content") or "").strip()
    aj = coerce_aspects_json(comment.get("aspects_json"))
    customer_schema_version = ""
    specific_schema_version = ""
    occurrence_schema_version = ""
    has_highlight_payload = False
    occurrences: list[dict[str, Any]] = []
    if aj:
        customer_schema_version = str(aj.get("customer_label_schema_version") or "")
        specific_schema_version = str(aj.get("specific_issue_schema_version") or "")
        occurrence_schema_version = str(aj.get("customer_label_occurrence_schema_version") or "")
        if occurrence_schema_version == CUSTOMER_LABEL_OCCURRENCE_SCHEMA_VERSION:
            return _project_customer_label_occurrences(
                comment,
                label_type="highlight",
                locale=locale,
                aspects_json=aj,
            )
        sub_category = str(aj.get("sub_category") or comment.get("sub_category") or "")
        aspects = [aspect for aspect in aj.get("aspects") or [] if isinstance(aspect, dict)]
        has_highlight_payload = any(
            any(
                key in aspect
                for key in (
                    "customer_highlight",
                    "canonical_highlight_key",
                    "highlight_display_allowed",
                    "highlight_source",
                )
            )
            for aspect in aspects
        )
        can_derive_from_aspects = (
            customer_schema_version == CUSTOMER_LABEL_SCHEMA_VERSION
            or specific_schema_version == SPECIFIC_ISSUE_SCHEMA_VERSION
            or has_highlight_payload
        )
        if not can_derive_from_aspects:
            return _legacy_highlight_occurrences(comment, locale)
        for aspect in aspects:
            highlight = _normalize_aspect_highlight(
                aspect,
                sub_category=sub_category,
                content=content,
                locale=locale,
            )
            if not highlight or not highlight["highlight_display_allowed"]:
                continue
            unified = _highlight_occurrence_from_normalized(
                comment_id=comment.get("id"),
                cluster_propagated=bool(aj.get("cluster_propagated") or aspect.get("cluster_propagated")),
                content=content,
                aspect=aspect,
                highlight=highlight,
            )
            projected = _project_customer_label_occurrence(
                unified,
                comment=comment,
                label_type="highlight",
                locale=locale,
                inherited_cluster_propagated=bool(aj.get("cluster_propagated")),
            )
            if projected:
                occurrences.append(projected)
    if occurrences or customer_schema_version == CUSTOMER_LABEL_SCHEMA_VERSION or has_highlight_payload:
        return occurrences
    return _legacy_highlight_occurrences(comment, locale)


def build_customer_highlight_rows(
    comments: list[dict[str, Any]],
    *,
    locale: str = "en",
    limit: int = 10,
) -> list[dict[str, Any]]:
    return _build_customer_label_rows(
        comments,
        label_type="highlight",
        locale=locale,
        limit=limit,
    )


def customer_issue_tags_for_comment(comment: dict[str, Any], locale: str = "en") -> list[str]:
    seen: set[str] = set()
    labels: list[str] = []
    for occurrence in iter_specific_issue_occurrences(comment, locale=locale):
        label = str(occurrence.get("specific_issue") or "").strip()
        if label and label not in seen:
            seen.add(label)
            labels.append(label)
    return labels


def customer_highlight_tags_for_comment(comment: dict[str, Any], locale: str = "en") -> list[str]:
    seen: set[str] = set()
    labels: list[str] = []
    for occurrence in iter_customer_highlight_occurrences(comment, locale=locale):
        label = str(occurrence.get("customer_highlight") or "").strip()
        if label and label not in seen:
            seen.add(label)
            labels.append(label)
    return labels


def customer_highlight_tags_from_aspects(
    aspects: list[dict[str, Any]],
    *,
    content: str = "",
    sub_category: str = "",
    locale: str = "en",
    limit: int = 3,
) -> str:
    comment = {
        "content": content,
        "aspects_json": {
            "customer_label_schema_version": CUSTOMER_LABEL_SCHEMA_VERSION,
            "sub_category": sub_category,
            "aspects": aspects,
        },
    }
    return ",".join(customer_highlight_tags_for_comment(comment, locale=locale)[:limit])


def decorate_comment_customer_labels(comment: dict[str, Any], locale: str = "en") -> dict[str, Any]:
    decorated = dict(comment)
    aj = coerce_aspects_json(decorated.get("aspects_json"))
    if aj:
        has_new_payload = (
            str(aj.get("specific_issue_schema_version") or "") == SPECIFIC_ISSUE_SCHEMA_VERSION
            or str(aj.get("customer_label_schema_version") or "") == CUSTOMER_LABEL_SCHEMA_VERSION
            or str(aj.get("customer_label_occurrence_schema_version") or "")
            == CUSTOMER_LABEL_OCCURRENCE_SCHEMA_VERSION
            or any(
                isinstance(aspect, dict)
                and any(
                    key in aspect
                    for key in (
                        "specific_issue",
                        "canonical_issue_key",
                        "customer_highlight",
                        "canonical_highlight_key",
                    )
                )
                for aspect in (aj.get("aspects") or [])
            )
        )
        if has_new_payload:
            enriched = enrich_aspects_json(
                aj,
                sub_category=str(aj.get("sub_category") or decorated.get("sub_category") or ""),
                content=str(decorated.get("content") or ""),
                locale=locale,
                comment_id=decorated.get("id"),
            )
            if enriched:
                decorated["aspects_json"] = enriched
    decorated["customer_issue_tags"] = ", ".join(customer_issue_tags_for_comment(decorated, locale=locale))
    decorated["customer_highlight_tags"] = ", ".join(customer_highlight_tags_for_comment(decorated, locale=locale))
    decorated["customer_label_schema_version"] = CUSTOMER_LABEL_SCHEMA_VERSION
    return decorated
