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
CUSTOMER_LABEL_OCCURRENCE_RULESET_VERSION = "2026-07-28-phase7-waterproof-positive-guard"

_OCCURRENCE_SOURCES = {"llm", "rule", "human", "legacy"}

_LABELS_CACHE: dict[str, dict[str, str]] | None = None

_ALLOWED_ASPECT_KEYS_BY_LABEL: dict[str, dict[str, set[str]]] = {
    "highlight": {
        "fits_as_expected": {"size_fit", "boot_fit"},
        "keeps_water_out": {"waterproof", "waterproof_performance"},
        "good_value_for_the_price": {"value_for_money", "price_value"},
        "holds_up_well": {"durability", "build_quality", "seam_integrity", "material"},
        "lightweight_waders": {"weight", "material"},
        "useful_storage_space": {"accessory_storage", "organization", "capacity"},
        "useful_accessories": {"accessory_storage"},
        "good_traction": {"grip"},
        "keeps_warm": {"temperature_rating"},
        "easy_to_clean": {"ease_of_use"},
        "no_strong_odor": {"material", "smell", "scent"},
        "comfortable_to_wear": {"comfort", "mobility", "boot_fit"},
        "breathes_well": {"breathability", "comfort"},
        "feels_well_made": {"build_quality", "material", "durability", "stability"},
        "good_material_quality": {"material", "build_quality"},
        "arrives_on_time_and_intact": {"shipping_damage", "packaging"},
        "fast_shipping": {"shipping_damage", "packaging"},
        "petite_friendly": {"size_fit"},
        "plus_size_friendly": {"size_fit"},
        "women_friendly_fit": {"size_fit"},
        "works_well_for_use_case": {"other"},
        "first_impression_positive": {"other", "material", "build_quality", "aesthetics"},
        "not_used_yet": {"other"},
        "overall_satisfied": {"other"},
        "looks_good": {"aesthetics"},
    },
    "issue": {
        "water_leaks_through": {"waterproof", "waterproof_performance", "seam_integrity"},
        "seam_leaks": {"seam_integrity"},
        "pocket_not_waterproof": {"accessory_storage", "organization", "capacity"},
        "pocket_too_small": {"accessory_storage", "organization", "capacity"},
        "missing_accessories": {"accessory_storage", "shipping_damage", "packaging"},
        "missing_wader_hanger": {"accessory_storage"},
        "accessories_not_as_advertised": {"accessory_storage"},
        "breaks_easily": {"durability", "build_quality", "seam_integrity", "material", "stability"},
        "feels_thin_and_flimsy": {"material", "durability", "build_quality"},
        "strong_chemical_smell": {"material", "smell", "scent"},
        "not_breathable": {"breathability", "comfort", "mobility"},
        "runs_too_small": {"size_fit", "boot_fit"},
        "runs_too_large": {"size_fit", "boot_fit"},
        "inaccurate_size_chart": {"size_fit", "boot_fit"},
        "not_petite_friendly": {"size_fit"},
        "not_plus_size_friendly": {"size_fit"},
        "calf_area_too_tight": {"boot_fit"},
        "pants_too_long": {"size_fit"},
        "boots_too_stiff": {"comfort", "material", "boot_fit"},
        "not_for_long_walks": {"comfort", "boot_fit", "mobility"},
        "poor_traction": {"grip"},
        "soft_soles": {"grip", "durability", "material"},
        "not_worth_the_price": {"value_for_money", "price_value"},
        "poor_value_for_money": {"value_for_money", "price_value"},
        "arrived_damaged": {"shipping_damage", "packaging"},
        "poor_customer_service": {"customer_service"},
        "zipper_fails": {"zipper_quality"},
        "missing_parts": {"assembly", "packaging", "shipping_damage", "accessory_storage"},
        "accessories_not_as_advertised": {"accessory_storage"},
        "gets_hot_quickly": {"temperature_rating", "breathability"},
        "insufficient_warmth": {"temperature_rating"},
        "overall_dissatisfied": {"other"},
        "not_for_heavy_brush": {"durability", "other"},
    },
}


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
    "accessories_not_as_advertised": "配件与描述不符",
    "arrived_damaged": "到货破损",
    "battery_dies_quickly": "电池耗电快",
    "breaks_easily": "容易损坏",
    "boots_too_stiff": "靴子过硬",
    "calf_area_too_tight": "小腿位置偏小",
    "charging_fails": "充电不稳定",
    "curl_does_not_hold": "卷翘保持差",
    "falls_apart": "容易散架",
    "feels_thin_and_flimsy": "材质偏薄不结实",
    "gets_hot_quickly": "升温快",
    "hard_to_assemble": "组装困难",
    "inaccurate_size_chart": "尺码不准",
    "insufficient_warmth": "保暖性差",
    "instructions_unclear": "说明不清楚",
    "irritates_eyes": "刺激眼睛",
    "makes_squeaking_noise": "有异响",
    "mascara_clumps": "睫毛膏容易结块",
    "mascara_flakes": "睫毛膏容易掉渣",
    "missing_accessories": "配件缺失",
    "missing_parts": "缺少配件",
    "missing_wader_hanger": "缺少涉水裤挂架",
    "not_for_heavy_brush": "不适合灌木丛",
    "not_breathable": "不够透气",
    "not_for_long_walks": "不适合长时间步行",
    "not_enough_length": "纤长效果不足",
    "not_enough_volume": "浓密效果不足",
    "not_petite_friendly": "小个子不友好",
    "not_plus_size_friendly": "大码不友好",
    "not_worth_the_price": "不值这个价格",
    "overall_dissatisfied": "整体不满意",
    "pants_too_long": "裤长偏长",
    "pocket_not_waterproof": "口袋不防水",
    "pocket_too_small": "口袋太小",
    "poor_traction": "防滑性不足",
    "poor_customer_service": "客服体验差",
    "runs_too_large": "尺码偏大",
    "runs_too_small": "尺码偏小",
    "smudges_easily": "容易晕染",
    "soft_soles": "鞋底偏软",
    "strong_chemical_smell": "化学气味重",
    "uncomfortable_fit": "穿着不舒服",
    "water_leaks_through": "容易进水",
    "zipper_fails": "拉链容易故障",
}

_CUSTOMER_HIGHLIGHT_ZH_BY_KEY = {
    "arrives_on_time_and_intact": "到货及时完好",
    "comfortable_to_wear": "穿着舒适",
    "easy_to_clean": "容易清洁",
    "feels_well_made": "做工扎实",
    "first_impression_positive": "初步印象良好",
    "fits_as_expected": "尺码合适",
    "good_material_quality": "材质质量好",
    "good_traction": "抓地稳",
    "good_value_for_the_price": "性价比高",
    "holds_up_well": "耐用性高",
    "keeps_warm": "保暖性好",
    "keeps_water_out": "防水可靠",
    "lightweight_waders": "轻便",
    "looks_good": "外观好看",
    "no_strong_odor": "没有明显异味",
    "not_used_yet": "未实际使用",
    "overall_satisfied": "整体满意",
    "petite_friendly": "小个子友好",
    "plus_size_friendly": "大码友好",
    "useful_accessories": "配件实用",
    "useful_storage_space": "收纳空间实用",
    "women_friendly_fit": "女性友好版型",
    "works_well_for_use_case": "场景适用",
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


def _is_label_aspect_allowed(label_type: str, canonical_label_key: str, aspect_key: str) -> bool:
    canonical = str(canonical_label_key or "").strip()
    aspect = str(aspect_key or "").strip()
    if not canonical or not aspect:
        return True
    allowed = _ALLOWED_ASPECT_KEYS_BY_LABEL.get(label_type, {}).get(canonical)
    return True if allowed is None else aspect in allowed


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


def _customer_highlight_zh_label(canonical: str, highlight: str) -> str:
    mapped = _CUSTOMER_HIGHLIGHT_ZH_BY_KEY.get(canonical) or _CUSTOMER_HIGHLIGHT_ZH_BY_KEY.get(_slug(highlight))
    if mapped:
        return mapped
    return highlight


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
    r"\bleak[- ]?proof\b",
    r"\bno\s+leaks?\b",
    r"\bno\s+(?:water\s+)?leakage\b",
    r"\bno\s+water\s+intrusion\b",
    r"\bwithout\s+(any\s+)?leaks?\b",
    r"\bwithout\s+(any\s+)?(?:water\s+)?leakage\b",
    r"\bnever\s+(had\s+)?leaks?\b",
    r"\bnever\s+(had\s+)?(?:a\s+)?(?:water\s+)?leakage\b",
    r"\bhave(?:n['’]?t| not)\s+had\s+(?:any\s+)?(?:issues?\s+with\s+)?leaks?\b",
    r"\bhas(?:n['’]?t| not)\s+had\s+(?:any\s+)?(?:issues?\s+with\s+)?leaks?\b",
    r"\bhad\s+no\s+(?:issues?\s+with\s+)?leaks?\b",
    r"\bno\s+issues?\s+with\s+leaks?\b",
    r"\b(did|does|do|has|have|had)(?:n['’]?t| not)\s+(?:experience|experienced|had|have|see|seen)\s+(?:any\s+)?leak(?:ing|s)?\b",
    r"\b(did|does|do|has|have|had)(?:n['’]?t| not)\s+leak(?:ed|ing|s)?\b",
    r"\b(?:did|does|do)(?:n['’]?t| not)\s+get\s+wet\b",
    r"\b(?:do|does|did)(?:n['’]?t| not)\s+see[^.!?\n]{0,80}\bleak\b",
    r"\bnot\s+a\s+leak\b",
    r"\bnot\s+leaking\b",
]

_POSITIVE_DRY_PATTERNS = [
    r"\b(remained|stayed|kept|keep|keeps)\s+(?:(?:me|you|us|him|her|them|my\s+\w+|your\s+\w+|his\s+\w+|her\s+\w+|their\s+\w+)\s+)?(?:\w+ly\s+)?dry\b",
]

_WATER_LEAK_HIT_PATTERNS = [
    r"\bnot waterproof\b",
    r"\bnot\s+100%\s+waterproof\b",
    r"\bleak",
    r"\bseep(?:ing|ed|s)?\b",
    r"\bmoisture\s+coming\s+through\b",
    r"\bmoisture\s+inside\b",
    r"\bdamp\b",
    r"\bwater (gets|got|came|comes|coming|enters|entered) (in|through)",
]

_NON_CURRENT_PRODUCT_LEAK_PATTERNS = [
    r"\bafter\s+(?:my|our|the|his|her)\s+[^.!?]{0,80}\b(?:old|previous|last|magellan|brand|ones?)\b[^.!?]{0,80}\bleak",
    r"\b(?:old|previous|last|other)\s+(?:pair|one|ones|waders?)\b[^.!?]{0,80}\bleak",
    r"\b(?:numerous|many|several)\s+pairs?\s+of\s+waders?\s+in\s+the\s+past\b[^.!?\n]{0,120}\bleak",
    r"\bwaders?\s+in\s+the\s+past\b[^.!?\n]{0,120}\bleak",
    r"\b(?:old|previous|last)\s+waders?\b[^.!?\n]{0,120}\bleak",
    r"\b(?:ones?|waders?)\s+(?:he|she|they|i|we)\s+had\b[^.!?]{0,80}\bleak",
    r"\b(?:pair|one|ones|waders?)\s+from\s+another\s+(?:company|brand)\b[^.!?\n]{0,100}\bleak",
    r"\b(?:heard|reviews?\s+saying)[^.!?\n]{0,100}\bleak",
    r"\b(?:reviews?|complaints)\b[^.!?\n]{0,120}\b(?:leaks?|leaking|leaked)\b",
    r"\bleaks?\s+on\s+some\s+pairs\b",
    r"\bunlike\s+(?:my|our|the|his|her)\s+(?:old|previous|last)\s+(?:pair|one|ones|waders?)\b",
]

_ACCESSORY_LEAK_CONTEXT_PATTERNS = [
    r"\b(?:outer\s+)?(?:pockets?|storage pocket|hand warmer pocket|phone case|phone sleeve|phone protector|case|bag)\b[^.!?\n]{0,140}\b(?:not waterproof|leak|water gets in|water leaks in|wet|soak|submerged)",
    r"\b(?:not waterproof|leak(?:ing|ed|s)?|water gets in|water leaks in|wet|soak|submerged)[^.!?\n]{0,140}\b(?:outer\s+)?(?:pockets?|storage pocket|hand warmer pocket|phone case|phone sleeve|phone protector|case|bag)\b",
]

_CURRENT_PRODUCT_LEAK_CONTEXT_PATTERNS = [
    r"\b(?:waders?|boot|boots|feet|foot|material|seam|neoprene)\b",
    r"\bnot\s+(?:100%\s+)?waterproof\b",
]

_WATER_LEAK_EVIDENCE_PATTERNS = [
    r"\bnot\s+(?:100%\s+)?waterproof(?:\s+material)?\b",
    r"\bsmall\s+leaks?\b[^,.!?\n]{0,80}",
    r"\bwater\s+leaking\s+(?:in|through)\b",
    r"\bwater\s+(?:gets|got|came|comes|coming|enters|entered)\s+(?:in|through)\b",
    r"\bwater\s+will\s+seep\s+through\b[^,.!?\n]{0,80}",
    r"\bslowly\s+seep\s+in\s+water\b",
    r"\bloads?\s+of\s+water\s+seep(?:ing|ed|s)?\s+in\b",
    r"\bseep(?:ing|ed|s)?\s+(?:in|into|through)\b[^,.!?\n]{0,80}",
    r"\bmoisture\s+coming\s+through\b",
    r"\bmoisture\s+inside\s+both\s+legs\s+and\s+boots\b",
    r"\bsocks\s+are\s+damp\b",
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


def _is_positive_waterproof_evidence_for_issue(evidence: str) -> bool:
    basis = str(evidence or "").strip()
    if not basis:
        return False
    return _is_negated_water_leak_statement(basis) or _is_positive_dry_statement(basis)


def _is_suppressed_water_leak_issue_occurrence(occurrence: dict[str, Any]) -> bool:
    if str(occurrence.get("type") or "").strip().lower() != "issue":
        return False
    canonical = str(
        occurrence.get("canonical_issue_key") or occurrence.get("canonical_label_key") or ""
    ).strip()
    if canonical != "water_leaks_through":
        return False
    return _is_positive_waterproof_evidence_for_issue(str(occurrence.get("evidence_span") or ""))


def _water_leak_issue_hit(evidence: str, content: str) -> bool:
    basis = evidence.strip() or content[:400]
    if _is_negated_water_leak_statement(basis) or _is_positive_dry_statement(basis):
        return False
    text = f"{evidence} {content[:400]}".lower()
    text = re.sub(r"\bno\s+leaks?\b", " ", text)
    text = re.sub(r"\bno\s+(?:water\s+)?leakage\b", " ", text)
    text = re.sub(r"\bno\s+water\s+intrusion\b", " ", text)
    text = re.sub(r"\bwithout\s+(any\s+)?leaks?\b", " ", text)
    text = re.sub(r"\bwithout\s+(any\s+)?(?:water\s+)?leakage\b", " ", text)
    text = re.sub(r"\bnever\s+(had\s+)?leaks?\b", " ", text)
    text = re.sub(r"\bnever\s+(had\s+)?(?:a\s+)?(?:water\s+)?leakage\b", " ", text)
    text = re.sub(
        r"\b(did|does|do|has|have|had)(?:n['’]?t| not)\s+(?:experience|experienced|had|have|see|seen)\s+(?:any\s+)?leak(?:ing|s)?\b",
        " ",
        text,
    )
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


def _clause_spans(text: str) -> list[tuple[int, str]]:
    clauses: list[tuple[int, str]] = []
    for sentence_start, sentence in _sentence_spans(text):
        cursor = 0
        for match in re.finditer(r"\b(?:but|however|though|although|yet|that being said)\b|[;:]", sentence, re.I):
            part = sentence[cursor : match.start()].strip(" ,;:")
            if part:
                offset = sentence[cursor : match.start()].find(part)
                clauses.append((sentence_start + cursor + max(offset, 0), part))
            cursor = match.end()
        tail = sentence[cursor:].strip(" ,;:")
        if tail:
            offset = sentence[cursor:].find(tail)
            clauses.append((sentence_start + cursor + max(offset, 0), tail))
    return clauses or _sentence_spans(text)


def _first_water_leak_evidence_span(sentence: str) -> str:
    for pattern in _WATER_LEAK_EVIDENCE_PATTERNS:
        match = re.search(pattern, sentence, re.IGNORECASE)
        if match:
            return sentence[match.start() : match.end()].strip()
    return ""


def _current_product_water_leak_evidence(content: str) -> str:
    for _start, sentence in _clause_spans(content):
        if _is_negated_water_leak_statement(sentence) or _is_positive_dry_statement(sentence):
            continue
        if _is_non_current_product_leak_context(sentence) or _is_accessory_only_leak_context(sentence):
            continue
        evidence = _first_water_leak_evidence_span(sentence)
        if not evidence:
            continue
        if _is_blocked_water_leak_issue_context(content, evidence):
            continue
        if not _water_leak_issue_hit(evidence, sentence):
            continue
        return evidence
    return ""


def _evidence_context_sentence(content: str, evidence: str) -> str:
    evidence = str(evidence or "").strip()
    if not evidence:
        return content[:400]
    evidence_lower = evidence.lower()
    for _start, clause in _clause_spans(content):
        if evidence_lower in clause.lower():
            return clause
    for _start, sentence in _sentence_spans(content):
        if evidence_lower in sentence.lower():
            return sentence
    return f"{evidence} {content[:400]}".strip()


def _evidence_context_window(content: str, evidence: str, radius: int = 220) -> str:
    evidence = str(evidence or "").strip()
    if not evidence:
        return content[:400]
    start = content.lower().find(evidence.lower())
    if start < 0:
        return f"{evidence} {content[:400]}".strip()
    return content[max(0, start - radius) : min(len(content), start + len(evidence) + radius)].strip()


def _is_accessory_leak_window(text: str) -> bool:
    return _first_regex(
        [
            r"\b(?:outer\s+)?(?:pockets?|storage pocket|hand warmer pocket|phone case|phone sleeve|phone protector|case|bag)\b[\s\S]{0,220}\b(?:not waterproof|leak|water gets in|water leaks in|wet|soak|submerged)",
            r"\b(?:not waterproof|leak(?:ing|ed|s)?|water gets in|water leaks in|wet|soak|submerged)[\s\S]{0,220}\b(?:outer\s+)?(?:pockets?|storage pocket|hand warmer pocket|phone case|phone sleeve|phone protector|case|bag)\b",
        ],
        text,
    )


def _is_blocked_water_leak_issue_context(content: str, evidence: str) -> bool:
    context = _evidence_context_sentence(content, evidence)
    window = _evidence_context_window(content, evidence)
    evidence_text = str(evidence or "").strip()
    accessory_context = (
        _first_regex(_ACCESSORY_LEAK_CONTEXT_PATTERNS, context)
        or _first_regex(_ACCESSORY_LEAK_CONTEXT_PATTERNS, evidence_text)
        or _is_accessory_leak_window(window)
    )
    return (
        _is_positive_waterproof_evidence_for_issue(context)
        or _is_positive_waterproof_evidence_for_issue(evidence_text)
        or _is_non_current_product_leak_context(context)
        or _is_non_current_product_leak_context(evidence_text)
        or _is_non_current_product_leak_context(window)
        or accessory_context
        or _is_accessory_only_leak_context(context)
        or _is_accessory_only_leak_context(evidence_text)
    )


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


_VALUE_POSITIVE_EVIDENCE_PATTERNS = [
    r"\bvalue\s+for\s+(?:the\s+)?money\b",
    r"\bgood\s+value\b",
    r"\bgreat\s+value\b",
    r"\bbest\s+value\b",
    r"\bexcellent\s+value\b",
    r"\bworth\s+(?:every\s+)?(?:the\s+)?(?:penny|money|price)\b",
    r"\bmoney['’]?s\s+worth\b",
    r"\bfor\s+the\s+(?:money|price)\b",
    r"\bprice\s+(?:is|was|seems|feels)?\s*(?:right|fair|good|great|reasonable|cheap|affordable)\b",
    r"\b(?:cheap|affordable|reasonable|fair|great|good)\s+price\b",
    r"\bbargain\b",
    r"\bsteal\b",
]

_VALUE_NEGATIVE_EVIDENCE_PATTERNS = [
    r"\bnot\s+(?:a\s+)?(?:good\s+)?value\s+for\s+(?:the\s+)?money\b",
    r"\b(?:poor|bad|low)\s+value\b",
    r"\bnot\s+worth\s+(?:it|the\s+money|the\s+price)\b",
    r"\btoo\s+expensive\b",
    r"\boverpriced\b",
    r"\bprice\s+(?:is|was|seems|feels)?\s*(?:high|steep|expensive)\b",
    r"\bprice\s+is\s+too\s+high\b",
    r"\b(?:high|steep|expensive)\s+price\b",
    r"\bpricey\b",
    r"\bfor\s+what\s+you\s+get\b",
]


def _evidence_from_label_text(content: str, label: str, canonical: str, *, label_type: str) -> str:
    if not content:
        return ""
    if canonical == "value_for_money" or _norm_text(label) == "value for money":
        patterns = _VALUE_NEGATIVE_EVIDENCE_PATTERNS if label_type == "issue" else _VALUE_POSITIVE_EVIDENCE_PATTERNS
        for pattern in patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                return content[match.start() : match.end()].strip()
    candidates = [label, canonical.replace("_", " ")]
    for candidate in candidates:
        cleaned = str(candidate or "").strip()
        if not cleaned:
            continue
        located = _locate_evidence_span(content, cleaned)
        if located["evidence_verified"]:
            return str(located["evidence_span"])
    return ""


def _legacy_evidence_from_aspects(
    comment: dict[str, Any],
    *,
    canonical: str,
    label: str,
    label_type: str,
) -> tuple[str, str, str]:
    aj = coerce_aspects_json(comment.get("aspects_json"))
    if not aj or bool(aj.get("cluster_propagated")):
        return ("", "", "")
    aspects = [aspect for aspect in (aj.get("aspects") or []) if isinstance(aspect, dict)]
    expected_polarity = "negative" if label_type == "issue" else "positive"
    fallback: tuple[str, str, str] | None = None
    content = str(comment.get("content") or "").strip()
    for aspect in aspects:
        if bool(aspect.get("cluster_propagated")):
            continue
        polarity = str(aspect.get("polarity") or "").strip().lower()
        if polarity and polarity != expected_polarity:
            continue
        stored = str(aspect.get("evidence_span") or aspect.get("evidence") or "").strip()
        located = _locate_evidence_span(content, stored)
        if not located["evidence_verified"]:
            continue
        aspect_key = str(aspect.get("key") or aspect.get("aspect_key") or "").strip()
        matched_canonical = str(
            (aspect.get("canonical_issue_key") if label_type == "issue" else aspect.get("canonical_highlight_key"))
            or ""
        ).strip()
        if matched_canonical == canonical:
            return (str(located["evidence_span"]), aspect_key, "legacy_aspect_canonical_evidence")
        if aspect_key == canonical:
            return (str(located["evidence_span"]), aspect_key, "legacy_aspect_key_evidence")
        if _norm_text(aspect_key) == _norm_text(canonical.replace("_", " ")):
            return (str(located["evidence_span"]), aspect_key, "legacy_aspect_key_evidence")
        if fallback is None and _norm_text(label) in {_norm_text(aspect_key), _norm_text(str(aspect.get("aspect_label") or ""))}:
            fallback = (str(located["evidence_span"]), aspect_key, "legacy_aspect_label_evidence")
    return fallback or ("", "", "")


def _legacy_evidence_for_label(
    comment: dict[str, Any],
    *,
    canonical: str,
    label: str,
    label_type: str,
) -> tuple[str, str, str]:
    content = str(comment.get("content") or "").strip()
    evidence, aspect_key, source = _legacy_evidence_from_aspects(
        comment,
        canonical=canonical,
        label=label,
        label_type=label_type,
    )
    if evidence:
        return (evidence, aspect_key, source)
    evidence = _evidence_from_label_text(content, label, canonical, label_type=label_type)
    if evidence:
        return (evidence, "", "legacy_review_text_evidence")
    return ("", "", "")


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


def _is_waders_context(sub_category: str, content: str) -> bool:
    normalized = _norm_text(sub_category)
    return normalized in {"waders", "wader", "chest waders", "bootfoot waders"}


def _regex_span(patterns: list[str], text: str) -> str:
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return text[match.start() : match.end()].strip()
    return ""


def _first_content_span(
    content: str,
    patterns: list[str],
    *,
    blocked_patterns: list[str] | None = None,
    clause_level: bool = True,
) -> str:
    spans = _clause_spans(content) if clause_level else _sentence_spans(content)
    for _start, span in spans:
        if blocked_patterns and _first_regex(blocked_patterns, span):
            continue
        evidence = _regex_span(patterns, span)
        if evidence:
            return evidence
    if blocked_patterns and _first_regex(blocked_patterns, content):
        return ""
    return _regex_span(patterns, content)


def _not_used_context(content: str) -> bool:
    return _first_regex(
        [
            r"\bhave\s+not\s+used\b",
            r"\bhaven['’]?t\s+(?:gotten\s+to\s+)?use(?:d)?\b",
            r"\bnot\s+used\s+(?:them|it|these)\b",
            r"\bnot\s+tested\b",
            r"\blook\s+forward\s+to\s+trying\b",
            r"\bwill\s+(?:use|test|try)\b",
            r"\btomorrow\s+I\s+will\s+give\b",
        ],
        content,
    )


def _negative_outcome_context(content: str) -> bool:
    return _first_regex(
        [
            r"\breturn(?:ed|ing)?\s+them\s+all\b",
            r"\bhad\s+to\s+switch\s+to\s+a\s+different\s+brand\b",
            r"\bdon['’]?t\s+buy\s+these\b",
            r"\bwould\s+not\s+recommend\b",
            r"\bthese\s+are\s+horrible\b",
            r"\btrash\b",
            r"\breducing\s+the\s+rating\b",
            r"\bnot\s+what\s+I\s+had\s+in\s+mind\b",
            r"\bvery\s+disappointed\b",
        ],
        content,
    )


def _content_rule_occurrence(
    *,
    label_type: str,
    comment_id: Any,
    content: str,
    sub_category: str,
    canonical_label_key: str,
    display_en: str,
    display_zh: str,
    aspect_key: str,
    evidence_span: str,
    source_detail: str,
    confidence: str = "high",
) -> dict[str, Any] | None:
    if not evidence_span:
        return None
    catalog = resolve_customer_label(
        label_type=label_type,
        canonical_label_key=canonical_label_key,
        display_en=display_en,
        display_zh=display_zh,
        raw_label=display_en,
        aspect_key=aspect_key,
        sub_category_key=sub_category,
        confidence=confidence,
        display_allowed=True,
    )
    return _build_customer_label_occurrence(
        label_type=label_type,
        comment_id=comment_id,
        content=content,
        aspect={"key": aspect_key},
        aspect_key=aspect_key,
        raw_label=display_en,
        canonical_label_key=catalog.canonical_label_key,
        display_label_en=catalog.display_en or display_en,
        display_label_zh=catalog.display_zh or display_zh,
        evidence_span=evidence_span,
        confidence=catalog.confidence if catalog.confidence in {"high", "medium", "low"} else confidence,
        source_detail=source_detail,
        sub_category=sub_category,
        cluster_propagated=False,
        display_allowed=catalog.display_allowed,
        catalog_source=catalog.source,
        catalog_ruleset_version=catalog.ruleset_version,
    )


def _waders_issue_rule_occurrences(
    *,
    comment_id: Any,
    content: str,
    sub_category: str,
) -> list[dict[str, Any]]:
    if not _is_waders_context(sub_category, content):
        return []
    items: list[dict[str, Any]] = []

    def add(key: str, en: str, aspect: str, evidence: str, source_detail: str = "waders_content_rule") -> None:
        item = _content_rule_occurrence(
            label_type="issue",
            comment_id=comment_id,
            content=content,
            sub_category=sub_category,
            canonical_label_key=key,
            display_en=en,
            display_zh=_specific_issue_zh_label(key, en),
            aspect_key=aspect,
            evidence_span=evidence,
            source_detail=source_detail,
        )
        if item:
            items.append(item)

    add("water_leaks_through", "Water Leaks Through", "waterproof", _current_product_water_leak_evidence(content))
    add(
        "pocket_not_waterproof",
        "Pocket Not Waterproof",
        "accessory_storage",
        _regex_span(
            [
                r"\b(?:outer\s+)?(?:pockets?|storage pocket|hand warmer pocket|phone case|phone sleeve|phone protector|case|bag)\b[\s\S]{0,220}\b(?:not waterproof|leak|water gets in|water leaks in|wet|soak|submerged)",
                r"\b(?:not waterproof|leak(?:ing|ed|s)?|water gets in|water leaks in|wet|soak|submerged)[\s\S]{0,220}\b(?:outer\s+)?(?:pockets?|storage pocket|hand warmer pocket|phone case|phone sleeve|phone protector|case|bag)\b",
            ],
            content,
        ),
    )
    add(
        "breaks_easily",
        "Breaks Easily",
        "durability",
        _first_content_span(
            content,
            [
                r"\bno\s+durability\b",
                r"\b(?:rip|ripped|tear|tears|tore|torn)\b[^.!?\n]{0,80}",
                r"\bstitching\s+broke\b[^.!?\n]{0,80}",
                r"\bbroke\b[^.!?\n]{0,80}",
                r"\bdestroyed\b",
            ],
            blocked_patterns=[r"\bdidn['’]?t\s+(?:get\s+wet\s+or\s+)?tear\b", r"\bzipper\b"],
        ),
    )
    add(
        "strong_chemical_smell",
        "Strong Chemical Smell",
        "material",
        _first_content_span(
            content,
            [
                r"\bstrong\s+chemical[^.!?\n]{0,60}\bsmell\b",
                r"\bchemical[^.!?\n]{0,60}\bsmell\b",
                r"\bplastic\s+smell\b",
                r"\bout\s+gasing\s+of\s+the\s+PVC\s+material\b",
            ],
        ),
    )
    add(
        "inaccurate_size_chart",
        "Inaccurate Size Chart",
        "size_fit",
        _first_content_span(
            content,
            [
                r"\bsize\s+chart\b[^.!?\n]{0,100}\b(?:off|wrong|inaccurate|lists)\b",
                r"\bsizing\s+(?:was\s+)?(?:off|very\s+off)\b",
                r"\bsize\s+description\b[^.!?\n]{0,120}\bdidn['’]?t\s+come\s+close\b",
                r"\bhard\s+to\s+figure\s+out\s+what\s+size\b",
                r"\boverall\s+fit\b[^.!?\n]{0,100}\bsmaller\s+than\s+described\b",
                r"\bruns\s+very\s+small\b",
            ],
        ),
    )
    add(
        "runs_too_small",
        "Runs Too Small",
        "size_fit",
        _first_content_span(
            content,
            [
                r"\b(?:runs?|run)\s+(?:very\s+)?small\b",
                r"\btoo\s+small\b",
                r"\bsize\s+up\b",
                r"\btight\s+around\b[^.!?\n]{0,80}",
                r"\bboots?\s+are\s+snug\b",
                r"\bcouldn['’]?t\s+even\s+get\s+my\s+foot\s+in\b",
            ],
        ),
    )
    add(
        "not_petite_friendly",
        "Not Petite Friendly",
        "size_fit",
        _first_content_span(
            content,
            [
                r"\btoo\s+big\s+for\s+me\s+at\s+5['’]\s*6\b",
                r"\bhard\s+to\s+find\s+small\s+waders?\s+for\s+women\b",
                r"\bshort\s+(?:person|woman|women)\b[^.!?\n]{0,80}\b(?:too\s+big|long|loose)\b",
                r"\bbeing\s+engulfed\s+in\s+them\b",
            ],
        ),
    )
    add(
        "pants_too_long",
        "Pants Too Long",
        "size_fit",
        _first_content_span(content, [r"\bpants\s+are\s+long\b", r"\blegs\s+are\s+too\s+long\b"]),
    )
    add(
        "not_plus_size_friendly",
        "Not Plus Size Friendly",
        "size_fit",
        _first_content_span(content, [r"\bnot\s+going\s+past\s+my\s+hips\b", r"\bnot\s+for\s+(?:big|large)\b"]),
    )
    add(
        "not_breathable",
        "Not Breathable",
        "breathability",
        _first_content_span(
            content,
            [r"\bdon['’]?t\s+breathe\b", r"\bnot\s+breathable\b", r"\b(?:sweat|sweaty|sweating)\b[^.!?\n]{0,80}"],
        ),
    )
    add(
        "gets_hot_quickly",
        "Gets Hot Quickly",
        "temperature_rating",
        _first_content_span(content, [r"\bwarms?\s+up\s+quick\b", r"\btoo\s+hot\b"]),
    )
    add(
        "not_for_long_walks",
        "Not for Long Walks",
        "comfort",
        _first_content_span(
            content,
            [r"\bnot\s+walking\s+far\b", r"\bfeet\s+were\s+in\s+pain\b", r"\bboots?\s+hurt\s+after\s+awhile\b"],
        ),
    )
    add(
        "poor_traction",
        "Poor Traction",
        "grip",
        _first_content_span(content, [r"\bslick\s+or\s+slipper\s+rocks\b", r"\bslippery\s+rocks\b", r"\bsoles\s+slipped\b[^.!?\n]{0,80}"]),
    )
    add(
        "boots_too_stiff",
        "Boots Too Stiff",
        "boot_fit",
        _first_content_span(content, [r"\bboots?\b[^.!?\n]{0,60}\bvery\s+stiff\b", r"\brigidity\s+of\s+the\s+boots\b[^.!?\n]{0,80}"]),
    )
    add("soft_soles", "Soft Soles", "grip", _first_content_span(content, [r"\bsoles\s+are\s+a\s+bit\s+soft\b"]))
    add(
        "missing_wader_hanger",
        "Missing Wader Hanger",
        "accessory_storage",
        _first_content_span(
            content,
            [
                r"\b(?:hanger|hook)\b[^.!?\n]{0,80}\b(?:missing|did\s+not\s+come|didn['’]?t\s+come)\b",
                r"\bdid\s+not\s+come\s+with\s+(?:wader\s+)?hanger\b",
            ],
            blocked_patterns=[r"\bphone\s+protector\s+and\s+hanger\s+(?:was|were)\s+missing\b"],
        ),
    )
    add(
        "missing_accessories",
        "Missing Accessories",
        "accessory_storage",
        _first_content_span(content, [r"\bphone\s+protector\s+and\s+hanger\s+(?:was|were)\s+missing\b", r"\bother\s+piece\b[^.!?\n]{0,80}\bdid\s+not\s+even\s+come\b"]),
    )
    add(
        "accessories_not_as_advertised",
        "Accessories Not as Advertised",
        "accessory_storage",
        _first_content_span(content, [r"\bphone\s+case\b[^.!?\n]{0,120}\bnot\s+the\s+same\s+as\s+what\s+is\s+advertised\b"]),
    )
    add(
        "overall_dissatisfied",
        "Overall Dissatisfied",
        "other",
        _first_content_span(content, [r"\btrash\b", r"\byou\s+get\s+what\s+you\s+pay\s+for\b", r"\bdon['’]?t\s+buy\s+these\b"]),
        source_detail="waders_low_priority_context_rule",
    )
    add(
        "not_for_heavy_brush",
        "Not for Heavy Brush",
        "other",
        _first_content_span(content, [r"\baren['’]?t\s+for\s+bush\s+wacking\b", r"\bnot\s+for\s+bush\s+wacking\b"]),
        source_detail="waders_low_priority_context_rule",
    )
    return items


def _waders_highlight_rule_occurrences(
    *,
    comment_id: Any,
    content: str,
    sub_category: str,
) -> list[dict[str, Any]]:
    if not _is_waders_context(sub_category, content):
        return []
    not_used = _not_used_context(content)
    negative_outcome = _negative_outcome_context(content)
    items: list[dict[str, Any]] = []

    def add(key: str, en: str, aspect: str, evidence: str, source_detail: str = "waders_content_rule") -> None:
        item = _content_rule_occurrence(
            label_type="highlight",
            comment_id=comment_id,
            content=content,
            sub_category=sub_category,
            canonical_label_key=key,
            display_en=en,
            display_zh=_customer_highlight_zh_label(key, en),
            aspect_key=aspect,
            evidence_span=evidence,
            source_detail=source_detail,
        )
        if item:
            items.append(item)

    if not negative_outcome:
        add(
            "fits_as_expected",
            "Fits as Expected",
            "size_fit",
            _first_content_span(
                content,
                [
                    r"\bfit(?:s|ted)?\s+(?:great|well|perfect|right|true)\b",
                    r"\bfit\s+is\s+great\b",
                    r"\bperfect\s+fit\b",
                    r"\btrue\s+to\s+size\b",
                    r"\bboots?\s+fit\s+(?:perfect|well|good|like\s+a\s+glove)\b",
                    r"\bmeasurements?\s+(?:are\s+)?very\s+accurate\b",
                    r"\bfoot\s+measurements?/fit\b[^.!?\n]{0,80}\btrue\s+to\s+size\b",
                ],
                blocked_patterns=[
                    r"\b(?:not|didn['’]?t|doesn['’]?t)\s+fit\b",
                    r"\bfit\s+is\s+tight\b",
                    r"\bshort\s+(?:guy|person|woman|women)\b",
                    r"\bI['’]?m\s+petite\b",
                ],
            ),
        )
    if not not_used and not negative_outcome:
        add(
            "keeps_water_out",
            "Keeps Water Out",
            "waterproof",
            _first_content_span(
                content,
                [
                    r"\bleak[- ]?proof\b",
                    r"\bno\s+leaks?\b",
                    r"\bno\s+(?:water\s+)?leakage\b",
                    r"\bhaven['’]?t\s+had\s+any\s+issues?\s+with\s+leaks?\s+yet\b",
                    r"\b(?:stayed|kept|keep|keeps|remain(?:ed)?)\s+(?:(?:me|you|us|him|her|them|my\s+\w+|your\s+\w+|his\s+\w+|her\s+\w+|their\s+\w+)\s+)?(?:\w+ly\s+)?dry\b",
                    r"\bdidn['’]?t\s+get\s+wet\b",
                    r"\bare\s+waterproof\b",
                    r"\bwaterproofing\b[^.!?\n]{0,80}\bsolid\b",
                ],
                blocked_patterns=[
                    r"\bphone\s+case\b",
                    r"\bphone\s+sleeve\b",
                    r"\bnot\s+(?:100%\s+)?waterproof\b",
                    r"\b90%\s+waterproof\b",
                    r"\bleak(?:ed|ing|s)?\b[^.!?\n]{0,80}\b(?:crazy|through|in|around|from)\b",
                ],
            ),
        )
        add(
            "holds_up_well",
            "Holds Up Well",
            "durability",
            _first_content_span(
                content,
                [
                    r"\b(?:held|holds?|hold)\s+up\b[^.!?\n]{0,80}",
                    r"\bstill\s+going\s+strong\b",
                    r"\bpretty\s+durable\b",
                    r"\bdurable\b",
                    r"\btough\b",
                    r"\bdouble\s+stitch\b[^.!?\n]{0,80}",
                ],
                blocked_patterns=[r"\bdidn['’]?t\s+hold\s+up\b", r"\bnot\s+durable\b", r"\bno\s+durability\b"],
            ),
        )
        add("keeps_warm", "Keeps Warm", "temperature_rating", _first_content_span(content, [r"\bkeeps?\s+me\s+warm\b", r"\bthey['’]?re\s+warm\b"]))
    add(
        "good_value_for_the_price",
        "Good Value for the Price",
        "value_for_money",
        _first_content_span(
            content,
            [
                r"\bgood\s+value\b",
                r"\bgreat\s+value\b",
                r"\bfor\s+the\s+price\b",
                r"\bprice\s+point\b",
                r"\baffordable\b",
                r"\breasonable\s+cost\b",
                r"\bcost\s+way\s+less\b",
                r"\bcheap\s+price\b",
                r"\binexpensive\b",
                r"\bdidn['’]?t\s+have\s+to\s+spend\s+a\s+lot\s+of\s+money\b",
            ],
            blocked_patterns=[
                r"\bnot\s+worth\b",
                r"\btoo\s+expensive\b",
                r"\breducing\s+the\s+rating\b",
                r"\bnot\s+what\s+I\s+had\s+in\s+mind\b",
            ],
        ),
    )
    add(
        "lightweight_waders",
        "Lightweight Waders",
        "weight",
        _first_content_span(content, [r"\blight\s*weight\b", r"\blightweight\b", r"\bnot\s+heavy\b"]),
    )
    add(
        "good_material_quality",
        "Good Material Quality",
        "material",
        _first_content_span(
            content,
            [
                r"\bgood\s+quality\b",
                r"\bgreat\s+quality\b",
                r"\bmaterial\s+quality\s+is\s+up\s+there\b",
                r"\bmaterials?\s+(?:look|looks)\s+pretty\s+good\b",
                r"\bthick\s+and\s+durable\b",
                r"\bquality\s+product\b",
                r"\bwell\s+made\b",
            ],
            blocked_patterns=[r"\bdoes\s+not\s+appear\s+sturdy\b", r"\bthin\s+plastic\b"],
        ),
    )
    add("no_strong_odor", "No Strong Odor", "material", _first_content_span(content, [r"\bdid\s+not\s+notice\s+anything\s+extreme\b", r"\bdon['’]?t\s+have\s+any\s+smell\b", r"\bno\s+smell\b"]))
    if not negative_outcome:
        add("petite_friendly", "Petite Friendly", "size_fit", _first_content_span(content, [r"\bshort\s+person\s+and\s+these\s+still\s+fit\s+me\s+well\b", r"\bI['’]?m\s+petite\b[^.!?\n]{0,100}\bfit\s+pretty\s+well\b"]))
        add("plus_size_friendly", "Plus Size Friendly", "size_fit", _first_content_span(content, [r"\brather\s+heavy\b[^.!?\n]{0,100}\bsizing\s+still\s+worked\s+out\s+well\b", r"\bbig\s+belly\b[^.!?\n]{0,100}\bfit\b"]))
        add("women_friendly_fit", "Women Friendly Fit", "size_fit", _first_content_span(content, [r"\bfit\s+my\s+feet\s+and\s+my\s+female\s+figure\b"]))
        add(
            "useful_storage_space",
            "Useful Storage Space",
            "accessory_storage",
            _first_content_span(content, [r"\bplenty\s+of\s+pockets?\s+and\s+storage\b", r"\bgreat\s+pocket\b", r"\bnice\s+pocket\s+storage\b"]),
        )
        add(
            "useful_accessories",
            "Useful Accessories",
            "accessory_storage",
            _first_content_span(content, [r"\brepair\s+kit\s+and\s+a\s+waterproof\s+phone\s+sleeve\b", r"\bphone\s+case,\s*hanger,\s*and\s*repair\s+kit\b", r"\bconvenient\s+hook\b", r"\bboot\s+hanger\s+included\b"]),
        )
    add("easy_to_clean", "Easy to Clean", "ease_of_use", _first_content_span(content, [r"\bclean\s+super\s+easy\b", r"\beasy\s+to\s+clean\b"]))
    if not_used and not negative_outcome:
        add("not_used_yet", "Not Used Yet", "other", _first_content_span(content, [r"\bhave\s+not\s+used[^.!?\n]{0,80}", r"\bhaven['’]?t\s+gotten\s+to\s+use[^.!?\n]{0,80}", r"\bnot\s+tested\s+waterproof[^.!?\n]{0,80}", r"\blook\s+forward\s+to\s+trying\b"]), source_detail="waders_context_rule")
        add("first_impression_positive", "First Impression Positive", "other", _first_content_span(content, [r"\bseem\s+to\s+be\s+good\s+quality\b", r"\blook\s+good\s+out\s+of\s+the\s+box\b", r"\bseem\s+to\s+be\s+decent\b", r"\bso\s+far\s+so\s+good\b", r"\bmaterials?\s+however\s+look\s+pretty\s+good\b"]), source_detail="waders_context_rule")
    add(
        "works_well_for_use_case",
        "Works Well for Use Case",
        "other",
        _first_content_span(
            content,
            [
                r"\bfly\s+fishing\s+in\s+Montana\b",
                r"\bSurf\s+Fishing\b",
                r"\bbrush,\s*mud,\s*and\s*creeks\b",
                r"\bAlaska\b",
                r"\bwork(?:ed)?\s+on\s+my\s+dock\s+piers\b",
                r"\bpreformed\s+flawless\b",
                r"\bworked\s+great\b",
                r"\bgot\s+the\s+job\s+done\b",
                r"\bversatility\s+for\s+fishing\s+or\s+other\s+projects\b",
            ],
            blocked_patterns=[
                r"\bhave\s+not\s+used\b",
                r"\blook\s+forward\s+to\s+trying\b",
                r"\btomorrow\s+I\s+will\s+give\b",
                r"\breducing\s+the\s+rating\b",
                r"\bnot\s+what\s+I\s+had\s+in\s+mind\b",
                r"\bslowly\s+seep\b",
                r"\bwater\s+was\s+pouring\s+in\b",
                r"\bsudden\s+tear\b",
            ],
        ),
    )
    if not negative_outcome:
        add("overall_satisfied", "Overall Satisfied", "other", _first_content_span(content, [r"\bhighly\s+recommend\b", r"\bexcellent\s+purchase\b", r"\bmy\s+husband\s+loves\s+it\b", r"\bI\s+am\s+happy\b", r"\bspot\s+on\b"]))
    if not not_used and not negative_outcome:
        add("looks_good", "Looks Good", "aesthetics", _first_content_span(content, [r"\blooked\s+so\s+nice\b", r"\blooks?\s+good\b"]))
    return items


def _has_frontstage_key(
    comment: dict[str, Any],
    occurrences: list[dict[str, Any]],
    *,
    label_type: str,
    canonical_label_key: str,
    locale: str,
) -> bool:
    for occurrence in occurrences:
        item = _project_customer_label_occurrence(
            occurrence,
            comment=comment,
            label_type=label_type,
            locale=locale,
        )
        if not item:
            continue
        if str(item.get("canonical_label_key") or "") != canonical_label_key:
            continue
        if item.get("source_review_allowed"):
            return True
    return False


def _append_waders_content_rule_occurrences(
    comment: dict[str, Any],
    occurrences: list[dict[str, Any]],
    *,
    label_type: str,
    locale: str,
    aspects_json: dict[str, Any] | None = None,
    project: bool = False,
) -> list[dict[str, Any]]:
    content = str(comment.get("content") or "").strip()
    sub_category = str(
        (aspects_json or {}).get("sub_category") or comment.get("sub_category") or comment.get("category") or ""
    )
    if label_type == "issue":
        candidates = _waders_issue_rule_occurrences(
            comment_id=comment.get("id"),
            content=content,
            sub_category=sub_category,
        )
    else:
        candidates = _waders_highlight_rule_occurrences(
            comment_id=comment.get("id"),
            content=content,
            sub_category=sub_category,
        )
    result = list(occurrences)
    for candidate in candidates:
        canonical = str(candidate.get("canonical_label_key") or "")
        if not canonical:
            continue
        if _has_frontstage_key(comment, result, label_type=label_type, canonical_label_key=canonical, locale=locale):
            continue
        if project:
            projected = _project_customer_label_occurrence(
                candidate,
                comment=comment,
                label_type=label_type,
                locale=locale,
            )
            if projected:
                result.append(projected)
        else:
            result.append(candidate)
    return result


def _append_content_rule_issue_occurrences(
    comment: dict[str, Any],
    occurrences: list[dict[str, Any]],
    *,
    locale: str,
    aspects_json: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    occurrences = [item for item in occurrences if not _is_suppressed_water_leak_issue_occurrence(item)]
    if any(
        str(item.get("canonical_issue_key") or item.get("canonical_label_key") or "") == "water_leaks_through"
        for item in occurrences
    ):
        return _append_waders_content_rule_occurrences(
            comment,
            occurrences,
            label_type="issue",
            locale=locale,
            aspects_json=aspects_json,
            project=True,
        )

    content = str(comment.get("content") or "").strip()
    sub_category = str(
        (aspects_json or {}).get("sub_category") or comment.get("sub_category") or comment.get("category") or ""
    )
    occurrence = _water_leak_occurrence_from_content(
        comment_id=comment.get("id"),
        content=content,
        sub_category=sub_category,
        locale=locale,
    )
    if not occurrence:
        return _append_waders_content_rule_occurrences(
            comment,
            occurrences,
            label_type="issue",
            locale=locale,
            aspects_json=aspects_json,
            project=True,
        )
    projected = _project_customer_label_occurrence(
        occurrence,
        comment=comment,
        label_type="issue",
        locale=locale,
    )
    if projected:
        occurrences.append(projected)
    return _append_waders_content_rule_occurrences(
        comment,
        occurrences,
        label_type="issue",
        locale=locale,
        aspects_json=aspects_json,
        project=True,
    )


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

    stored_evidence = str(occurrence.get("evidence_span") or "").strip()
    if label_type == "issue" and _is_suppressed_water_leak_issue_occurrence(
        {"type": label_type, "canonical_label_key": canonical, "evidence_span": stored_evidence}
    ):
        return None
    context_allowed = True
    if label_type == "issue" and canonical == "water_leaks_through":
        context_allowed = not _is_blocked_water_leak_issue_context(content, stored_evidence)

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
        occurrence.get("sub_category") or comment.get("sub_category") or comment.get("category") or ""
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
    aspect_allowed = _is_label_aspect_allowed(label_type, canonical, aspect_key)
    source_review_allowed = bool(
        content
        and stored_evidence
        and representative_verified
        and aspect_allowed
        and context_allowed
        and source != "legacy"
    )
    common = {
        "comment_id": comment.get("id") if comment.get("id") is not None else occurrence.get("comment_id"),
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
        "schema_version": str(occurrence.get("schema_version") or CUSTOMER_LABEL_OCCURRENCE_SCHEMA_VERSION),
        "ruleset_version": str(occurrence.get("ruleset_version") or CUSTOMER_LABEL_OCCURRENCE_RULESET_VERSION),
        "display_allowed": True,
        "aspect_allowed": aspect_allowed,
        "context_allowed": context_allowed,
        "source_review_allowed": source_review_allowed,
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
        if _first_regex(
            [
                r"\b(?:pockets?|phone case|phone sleeve|phone protector|case)\b.*\b(wet|soak|water|leak|not waterproof|submerged)",
                r"\b(wet|soak|water|leak|not waterproof|submerged).*\b(?:pockets?|phone case|phone sleeve|phone protector|case)\b",
            ],
            text,
        ):
            return ("Pocket Not Waterproof", "pocket_not_waterproof", "regex_alias_rule")
        if _first_regex([r"\bpockets?\b.*\b(small|tight|tiny|too small|not enough room)"], text):
            return ("Pocket Too Small", "pocket_too_small", "regex_alias_rule")
        if _first_regex([r"\bnot\s+the\s+same\s+as\s+what\s+is\s+advertised\b"], text):
            return ("Accessories Not as Advertised", "accessories_not_as_advertised", "regex_alias_rule")
        if _first_regex(
            [
                r"\bmissing\b.*\b(phone protector|phone case)\b",
                r"\b(phone protector|phone case)\b.*\bmissing\b",
                r"\bphone\s+protector\s+and\s+hanger\s+(?:was|were)\s+missing\b",
            ],
            text,
        ):
            return ("Missing Accessories", "missing_accessories", "regex_alias_rule")
        if _first_regex([r"\bmissing\b.*\b(hanger|hook)", r"\bno\b.*\b(hanger|hook)"], text):
            return ("Missing Wader Hanger", "missing_wader_hanger", "regex_alias_rule")

    if aspect_key in {"waterproof", "waterproof_performance", "seam_integrity"}:
        if _water_leak_issue_hit(evidence, content):
            return ("Water Leaks Through", "water_leaks_through", "regex_alias_rule")

    if aspect_key in {"zipper_quality"}:
        if _first_regex(
            [r"\bzipper\b.*\b(broke|break|stuck|jam|fail|cheap)", r"\b(broke|stuck|jammed).*\bzipper\b"], text
        ):
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
        if _first_regex(
            [
                r"\b(arrived|came|delivered)\b.*\b(damaged|broken|cracked|bent)",
                r"\bpackag(e|ing)\b.*\b(damaged|crushed|torn)",
            ],
            text,
        ):
            return ("Arrived Damaged", "arrived_damaged", "regex_alias_rule")

    if aspect_key in {"durability", "build_quality", "stability", "material", "strength"}:
        if _first_regex([r"\b(fell apart|falls apart)\b"], text):
            return ("Falls Apart", "falls_apart", "regex_alias_rule")
        if _first_regex([r"\b(broke|breaks|broken|cracked|snapped|ripped|rip|tear|tore|torn|no durability|destroyed)\b"], text):
            return ("Breaks Easily", "breaks_easily", "regex_alias_rule")
        if aspect_key in {"material", "build_quality"} and _first_regex(
            [
                r"\b(strong|bad|chemical|plastic|awful)\b.*\b(smell|odor|scent)\b",
                r"\b(smell|odor|scent)\b.*\b(strong|bad|chemical|plastic|awful)\b",
                r"\bout\s+gasing\b",
            ],
            text,
        ):
            return ("Strong Chemical Smell", "strong_chemical_smell", "regex_alias_rule")
        if _first_regex(
            [
                r"\b(thin|flimsy)\b",
                r"\bnot\s+sturdy\b",
                r"\bdoes\s+not\s+appear\s+sturdy\b",
                r"\bcheap\s+(?:material|plastic|quality)\b",
            ],
            text,
        ):
            return ("Feels Thin and Flimsy", "feels_thin_and_flimsy", "regex_alias_rule")

    if aspect_key in {"size_fit", "boot_fit"}:
        if aspect_key == "size_fit" and _first_regex([r"\bpants\s+are\s+long\b", r"\blegs\s+are\s+too\s+long\b"], text):
            return ("Pants Too Long", "pants_too_long", "regex_alias_rule")
        if aspect_key == "size_fit" and _first_regex(
            [
                r"\bshort\s+(?:person|woman|women)\b.*\b(?:too big|long|loose)\b",
                r"\btoo\s+big\s+for\s+me\s+at\s+5",
                r"\bhard\s+to\s+find\s+small\s+waders?\s+for\s+women\b",
                r"\bbeing\s+engulfed\s+in\s+them\b",
            ],
            text,
        ):
            return ("Not Petite Friendly", "not_petite_friendly", "regex_alias_rule")
        if aspect_key == "size_fit" and _first_regex([r"\bnot\s+going\s+past\s+my\s+hips\b"], text):
            return ("Not Plus Size Friendly", "not_plus_size_friendly", "regex_alias_rule")
        if _first_regex(
            [
                r"\bsize\s+chart\b.*\b(off|wrong|inaccurate|lists)\b",
                r"\bsizing\s+(?:was\s+)?(?:off|very\s+off)\b",
                r"\bsize\s+description\b.*\bdidn['’]?t\s+come\s+close\b",
                r"\bhard\s+to\s+figure\s+out\s+what\s+size\b",
            ],
            text,
        ):
            return ("Inaccurate Size Chart", "inaccurate_size_chart", "regex_alias_rule")
        if _first_regex([r"\btoo small\b", r"\bruns (?:very\s+)?small\b", r"\btight\b", r"\bboots?\s+are\s+snug\b"], text):
            return ("Runs Too Small", "runs_too_small", "regex_alias_rule")
        if _first_regex([r"\btoo large\b", r"\bruns large\b", r"\bloose\b"], text):
            return ("Runs Too Large", "runs_too_large", "regex_alias_rule")

    if aspect_key in {"comfort", "breathability", "mobility"}:
        if _first_regex([r"\bnot\s+walking\s+far\b", r"\bfeet\s+were\s+in\s+pain\b", r"\bboots?\s+hurt\s+after\s+awhile\b"], text):
            return ("Not for Long Walks", "not_for_long_walks", "regex_alias_rule")
        if _first_regex([r"\bboots?\b.*\bvery\s+stiff\b", r"\brigidity\s+of\s+the\s+boots\b"], text):
            return ("Boots Too Stiff", "boots_too_stiff", "regex_alias_rule")
        if _first_regex([r"\buncomfortable\b", r"\bhurts?\b", r"\bblister"], text):
            return ("Uncomfortable Fit", "uncomfortable_fit", "regex_alias_rule")
        if _not_breathable_issue_hit(text):
            return ("Not Breathable", "not_breathable", "regex_alias_rule")

    if aspect_key in {"temperature_rating"}:
        if _first_regex([r"\bwarms?\s+up\s+quick\b", r"\btoo\s+hot\b"], text):
            return ("Gets Hot Quickly", "gets_hot_quickly", "regex_alias_rule")
        if _first_regex([r"\bcold\s+and\s+wet\b", r"\bnot\s+warm\b"], text):
            return ("Insufficient Warmth", "insufficient_warmth", "regex_alias_rule")

    if aspect_key in {"grip"}:
        if _first_regex([r"\bslick\s+or\s+slipper\s+rocks\b", r"\bslippery\s+rocks\b", r"\bsoles?\s+slipped\b"], text):
            return ("Poor Traction", "poor_traction", "regex_alias_rule")
        if _first_regex([r"\bsoles\s+are\s+a\s+bit\s+soft\b"], text):
            return ("Soft Soles", "soft_soles", "regex_alias_rule")

    if aspect_key in {"smell", "scent"}:
        if _first_regex(
            [
                r"\b(strong|bad|chemical|awful)\b.*\b(smell|odor|scent)",
                r"\b(smell|odor|scent)\b.*\b(strong|bad|chemical|awful)",
            ],
            text,
        ):
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
    if aspect_key in {"lengthening_effect"} and _first_regex(
        [r"\b(no|not enough|little)\b.*\blength", r"\bdoes not lengthen\b"], text
    ):
        return ("Not Enough Length", "not_enough_length", "regex_alias_rule")
    if aspect_key in {"volumizing_effect"} and _first_regex(
        [r"\b(no|not enough|little)\b.*\bvolume", r"\bdoes not volumize\b"], text
    ):
        return ("Not Enough Volume", "not_enough_volume", "regex_alias_rule")
    if aspect_key in {"eye_sensitivity"} and _first_regex([r"\birritat|burn|sting|sensitive"], text):
        return ("Irritates Eyes", "irritates_eyes", "regex_alias_rule")

    if aspect_key in {"noise"} and _first_regex([r"\bsqueak|creak|noisy|noise"], text):
        return ("Makes Squeaking Noise", "makes_squeaking_noise", "regex_alias_rule")
    if aspect_key in {"battery_life"} and _first_regex(
        [r"\bbattery\b.*\b(short|dies|drain|last)", r"\bdoes not hold a charge\b"], text
    ):
        return ("Battery Dies Quickly", "battery_dies_quickly", "regex_alias_rule")
    if aspect_key in {"charging"} and _first_regex(
        [r"\b(charger|charging|charge)\b.*\b(stop|fail|slow|does not work|won't)"], text
    ):
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
    display_allowed = _is_customer_label_allowed(
        display_label, locale=locale, aspect_key=aspect_key, aspect_label=label
    )
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
    if existing and existing[2] == "water_leaks_through" and _is_positive_waterproof_evidence_for_issue(evidence):
        return None

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
            display_allowed = _is_customer_label_allowed(
                display_label, locale=locale, aspect_key=aspect_key, aspect_label=label
            )
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
    text = re.sub(r"\bleak[- ]?proof\b", " ", text)
    text = re.sub(r"\b(no|without)\s+leaks?\b", " ", text)
    text = re.sub(r"\b(no|without)\s+(?:water\s+)?leakage\b", " ", text)
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
        if _first_regex(
            [
                r"\b(waterproof|kept|keep|keeps|stayed|stay)\b.*\b(dry|water out)\b",
                r"\bnever get wet\b",
                r"\bdidn['’]?t\s+get\s+wet\b",
                r"\bno leaks?\b",
                r"\bno\s+(?:water\s+)?leakage\b",
                r"\bno\s+issues?\s+with\s+leaks?\b",
                r"\bleak[- ]?proof\b",
            ],
            text,
        ):
            return _highlight_label("Keeps Water Out", "防水可靠", "keeps_water_out", "regex_alias_rule")

    if aspect_key in {"boot_fit", "size_fit"}:
        if _first_regex(
            [
                r"\bfit(s|ted)?\b.*\b(perfect|great|well|right|true)\b",
                r"\bperfect\s+fit\b",
                r"\btrue to size\b",
                r"\bboots? fit",
                r"\bmeasurements?\s+(?:are\s+)?very\s+accurate\b",
            ],
            text,
        ):
            return _highlight_label("Fits as Expected", "尺码合适", "fits_as_expected", "regex_alias_rule")
        if _first_regex([r"\bshort\s+person\b.*\bfit\s+me\s+well\b", r"\bpetite\b.*\bfit\s+pretty\s+well\b"], text):
            return _highlight_label("Petite Friendly", "小个子友好", "petite_friendly", "regex_alias_rule")

    if aspect_key in {"comfort", "breathability", "mobility"}:
        if _first_regex([r"\bcomfortable\b", r"\beasy\b.*\b(move|walk|bend)", r"\bflexible\b"], text):
            return _highlight_label("Comfortable To Wear", "穿着舒适", "comfortable_to_wear", "regex_alias_rule")
        if _first_regex([r"\bbreathable\b", r"\bnot hot\b"], text):
            return _highlight_label("Breathes Well", "透气性好", "breathes_well", "regex_alias_rule")

    if aspect_key in {"build_quality", "durability", "material", "strength", "stability"}:
        if _first_regex([r"\b(held|holds?) up\b", r"\bstill going strong\b", r"\bdurable\b", r"\btough\b"], text):
            return _highlight_label("Holds Up Well", "耐用可靠", "holds_up_well", "regex_alias_rule")
        if _first_regex(
            [
                r"\b(good|great|nice|excellent)\b.*\bquality\b",
                r"\bmaterial\s+quality\s+is\s+up\s+there\b",
                r"\bmaterials?\s+(?:look|looks)\s+pretty\s+good\b",
                r"\bquality product\b",
                r"\bwell made\b",
                r"\bsturdy\b",
                r"\bsolid\b",
            ],
            text,
        ):
            return _highlight_label("Feels Well Made", "做工扎实", "feels_well_made", "regex_alias_rule")

    if aspect_key in {"value_for_money"}:
        if _first_regex(
            [
                r"\bgood value\b",
                r"\bgreat value\b",
                r"\bfor the price\b",
                r"\bprice point\b",
                r"\bworth\b",
                r"\baffordable\b",
                r"\bcost way less\b",
                r"\breasonable cost\b",
                r"\bdidn['’]?t\s+have\s+to\s+spend\s+a\s+lot\s+of\s+money\b",
            ],
            text,
        ):
            return _highlight_label(
                "Good Value for the Price", "性价比高", "good_value_for_the_price", "regex_alias_rule"
            )

    if aspect_key in {"ease_of_use"}:
        if _first_regex([r"\bclean\s+super\s+easy\b", r"\beasy\s+to\s+clean\b"], text):
            return _highlight_label("Easy to Clean", "容易清洁", "easy_to_clean", "regex_alias_rule")
        if _first_regex([r"\beasy to use\b", r"\beasy\b.*\b(clean|put on|fit|adjust)", r"\bconvenient\b"], text):
            return _highlight_label("Easy To Use", "使用方便", "easy_to_use", "regex_alias_rule")

    if aspect_key in {"accessory_storage", "organization", "capacity"}:
        if _first_regex(
            [r"\b(plenty|enough|great|good)\b.*\b(pockets?|storage|room|space)\b", r"\bconvenient storage\b"], text
        ):
            return _highlight_label("Useful Storage Space", "收纳空间实用", "useful_storage_space", "regex_alias_rule")
        if _first_regex(
            [
                r"\brepair kit\b",
                r"\bphone case,\s*hanger,\s*and\s*repair kit\b",
                r"\bconvenient hook\b",
                r"\bboot hanger included\b",
            ],
            text,
        ):
            return _highlight_label("Useful Accessories", "配件实用", "useful_accessories", "regex_alias_rule")

    if aspect_key in {"grip"}:
        if _first_regex(
            [
                r"\b(good|great|solid)\b.*\b(grip|traction)\b",
                r"\bnon[- ]?slip\b",
                r"\bsoles?\b.*\b(thick|grip|traction)\b",
            ],
            text,
        ):
            return _highlight_label("Good Traction", "抓地稳", "good_traction", "regex_alias_rule")

    if aspect_key in {"shipping_damage", "packaging"}:
        if _first_regex(
            [
                r"\bfast\b.*\b(delivery|shipping)\b",
                r"\barrived\b.*\b(on time|scheduled|intact|safe)\b",
                r"\bcame on time\b",
            ],
            text,
        ):
            return _highlight_label(
                "Arrives On Time and Intact", "到货及时完好", "arrives_on_time_and_intact", "regex_alias_rule"
            )

    if aspect_key in {"aesthetics", "color_accuracy"}:
        if _first_regex([r"\b(look|looks|looked)\b.*\b(great|good|nice|beautiful)\b", r"\bnice looking\b"], text):
            return _highlight_label("Looks Good", "外观好看", "looks_good", "regex_alias_rule")

    if aspect_key in {"smell", "scent"}:
        if _first_regex([r"\b(no|not much|without)\b.*\b(smell|odor|scent)\b"], text):
            return _highlight_label("No Strong Odor", "没有明显异味", "no_strong_odor", "regex_alias_rule")

    if aspect_key in {"weight"}:
        if _first_regex([r"\blight\s*weight\b", r"\blightweight\b", r"\bnot\s+heavy\b"], text):
            return _highlight_label("Lightweight Waders", "轻便", "lightweight_waders", "regex_alias_rule")

    if aspect_key in {"temperature_rating"}:
        if _first_regex([r"\bkeeps?\s+me\s+warm\b", r"\bthey['’]?re\s+warm\b"], text):
            return _highlight_label("Keeps Warm", "保暖性好", "keeps_warm", "regex_alias_rule")

    if aspect_key in {"battery_life"}:
        if _first_regex([r"\bbattery\b.*\b(long|lasts?|holds?)\b", r"\blong battery\b"], text):
            return _highlight_label("Long Battery Life", "续航时间长", "long_battery_life", "regex_alias_rule")

    if aspect_key in {"charging"}:
        if _first_regex([r"\bcharg(es|ed|ing)?\b.*\b(fast|quick|well|easy)\b"], text):
            return _highlight_label("Charges Reliably", "充电稳定", "charges_reliably", "regex_alias_rule")

    if aspect_key in {"clumping", "separation_definition"}:
        if _first_regex([r"\b(no|without)\b.*\bclump", r"\bseparat(es|ed|ion)\b"], text):
            return _highlight_label(
                "Separates Without Clumps", "不易结块根根分明", "separates_without_clumps", "regex_alias_rule"
            )

    if aspect_key in {"smudge_resistance"}:
        if _first_regex([r"\b(no|without|not)\b.*\b(smudge|smear|run)", r"\bsmudge[- ]?proof\b"], text):
            return _highlight_label("Does Not Smudge", "不易晕染", "does_not_smudge", "regex_alias_rule")

    if aspect_key in {"lengthening_effect"}:
        if _first_regex([r"\blength(en|ens|ening)?\b", r"\blong lashes\b"], text):
            return _highlight_label(
                "Adds Noticeable Length", "纤长效果明显", "adds_noticeable_length", "regex_alias_rule"
            )

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
        _is_customer_label_allowed(
            display_label,
            locale=locale,
            aspect_key=aspect_key,
            aspect_label=label_zh if locale.startswith("zh") else label_en,
        ),
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
        if _is_suppressed_water_leak_issue_occurrence(item):
            return
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
                    "customer_label_catalog_ruleset_version": issue["customer_label_catalog_ruleset_version"],
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
                    "customer_label_catalog_ruleset_version": highlight["customer_label_catalog_ruleset_version"],
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
    if not any(str(item.get("canonical_label_key") or "") == "water_leaks_through" for item in occurrences):
        water_leak_occurrence = _water_leak_occurrence_from_content(
            comment_id=comment_id,
            content=content_text,
            sub_category=normalized_sub_category,
            locale=locale,
        )
        if water_leak_occurrence:
            _append_occurrence(water_leak_occurrence)
    content_rule_comment = {
        "id": comment_id,
        "content": content_text,
        "sub_category": normalized_sub_category,
        "category": normalized_sub_category,
    }
    for item in _append_waders_content_rule_occurrences(
        content_rule_comment,
        occurrences,
        label_type="issue",
        locale=locale,
        aspects_json=enriched,
        project=False,
    )[len(occurrences):]:
        _append_occurrence(item)
    for item in _append_waders_content_rule_occurrences(
        content_rule_comment,
        occurrences,
        label_type="highlight",
        locale=locale,
        aspects_json=enriched,
        project=False,
    )[len(occurrences):]:
        _append_occurrence(item)
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
    enriched["customer_label_occurrences"] = occurrences
    enriched["issue_ruleset_version"] = ISSUE_RULESET_VERSION
    enriched["highlight_ruleset_version"] = HIGHLIGHT_RULESET_VERSION
    if normalized_sub_category:
        enriched["sub_category"] = normalized_sub_category
    return enriched


def _legacy_issue_occurrences(comment: dict[str, Any], locale: str) -> list[dict[str, Any]]:
    occurrences: list[dict[str, Any]] = []
    content = str(comment.get("content") or "").strip()
    aj = coerce_aspects_json(comment.get("aspects_json"))
    cluster_propagated = bool(aj.get("cluster_propagated")) if aj else False
    for raw_tag in str(comment.get("issue_tag") or "").split(","):
        issue = raw_tag.strip()
        if not issue:
            continue
        if not _is_customer_label_allowed(issue, locale=locale):
            continue
        canonical = _slug(issue)
        evidence_span, aspect_key, evidence_source = _legacy_evidence_for_label(
            comment,
            canonical=canonical,
            label=issue,
            label_type="issue",
        )
        if canonical == "water_leaks_through" and _is_positive_waterproof_evidence_for_issue(evidence_span):
            continue
        evidence = _locate_evidence_span(content, evidence_span)
        evidence_verified = bool(evidence["evidence_verified"] and not cluster_propagated)
        dimension_en, dimension_zh = _aspect_dimension_labels({}, aspect_key)
        source_detail = evidence_source or "legacy_issue_tag"
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
                "source_detail": source_detail,
                "issue_source": source_detail,
                "specific_issue_raw": issue,
                "display_allowed": True,
                "aspect_key": aspect_key,
                "dimension": _display_label_for_locale(dimension_en, dimension_zh, locale),
                "dimension_en": dimension_en,
                "dimension_zh": dimension_zh,
                "sub_category": str(comment.get("sub_category") or comment.get("category") or ""),
                "evidence_span": evidence["evidence_span"],
                "evidence_start": evidence["evidence_start"],
                "evidence_end": evidence["evidence_end"],
                "evidence_verified": bool(evidence["evidence_verified"]),
                "verified_evidence": evidence_verified,
                "cluster_propagated": cluster_propagated,
                "schema_version": "",
                "ruleset_version": "",
                "aspect_allowed": _is_label_aspect_allowed("issue", canonical, aspect_key),
                "source_review_allowed": False,
                "legacy_fallback": True,
            }
        )
    return occurrences


def _append_unique_snippet(target: list[str], content: str, limit: int = 240) -> None:
    snippet = content.strip()[:limit]
    if snippet and snippet not in target:
        target.append(snippet)


def _is_frontstage_countable_occurrence(occurrence: dict[str, Any]) -> bool:
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
            any(key in aspect for key in ("specific_issue", "canonical_issue_key", "display_allowed", "issue_source"))
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
    total_occurrence_counter: Counter[tuple[str, str]] = Counter()
    propagated_occurrence_counter: Counter[tuple[str, str]] = Counter()
    unverified_occurrence_counter: Counter[tuple[str, str]] = Counter()
    confidence_counter: dict[tuple[str, str], Counter[str]] = defaultdict(Counter)
    label_counter: dict[tuple[str, str], Counter[str]] = defaultdict(Counter)

    for fallback_index, comment in enumerate(comments):
        comment_id = comment.get("id")
        if comment_id is None:
            comment_id = f"row-{fallback_index}"
        counted_in_comment: set[tuple[str, str]] = set()
        for occurrence in iterator(comment, locale=locale):
            canonical = str(occurrence.get(canonical_field) or occurrence.get("canonical_label_key") or "").strip()
            if not canonical:
                continue
            key = (str(occurrence.get("sub_category") or ""), canonical)
            total_occurrence_counter[key] += 1
            if occurrence.get("cluster_propagated"):
                propagated_occurrence_counter[key] += 1
            if not occurrence.get("legacy_fallback") and not occurrence.get("source_review_allowed"):
                unverified_occurrence_counter[key] += 1
            if not _is_frontstage_countable_occurrence(occurrence):
                continue
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
                    "has_cluster_propagated_occurrences": False,
                    "reason": "",
                }
            if not occurrence.get("legacy_fallback"):
                groups[key]["legacy_fallback"] = False
                groups[key][is_specific_field] = True
                groups[key][schema_field] = schema_version
                groups[key]["customer_label_occurrence_schema_version"] = CUSTOMER_LABEL_OCCURRENCE_SCHEMA_VERSION
            aspect_key = str(occurrence.get("aspect_key") or "")
            if aspect_key and aspect_key not in groups[key]["aspect_keys"]:
                groups[key]["aspect_keys"].append(aspect_key)
            dimension = str(occurrence.get("dimension") or "")
            if dimension and dimension not in groups[key]["dimensions"]:
                groups[key]["dimensions"].append(dimension)
            source = str(occurrence.get(source_field) or "")
            if source and source not in groups[key][sources_field]:
                groups[key][sources_field].append(source)
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
                "total_occurrence_count": total_occurrence_counter[key],
                "propagated_occurrence_count": propagated_occurrence_counter[key],
                "unverified_occurrence_count": unverified_occurrence_counter[key],
                "source_review_occurrence_count": raw_occurrence_counter[key],
                "count": mention_count,
                "pct": mention_share,
                confidence_field: conf,
                "representative_comments": examples,
                "evidence_spans": evidence_spans,
                "evidence_verified": bool(evidence_spans),
                "cluster_propagated": False,
                "has_cluster_propagated_occurrences": (propagated_occurrence_counter[key] > 0),
                "reason": examples[0] if examples else "",
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
    aj = coerce_aspects_json(comment.get("aspects_json"))
    cluster_propagated = bool(aj.get("cluster_propagated")) if aj else False
    for raw_tag in str(comment.get("highlight_tag") or "").split(","):
        highlight = raw_tag.strip()
        if not highlight:
            continue
        if not _is_customer_label_allowed(highlight, locale=locale):
            continue
        canonical = _slug(highlight)
        evidence_span, aspect_key, evidence_source = _legacy_evidence_for_label(
            comment,
            canonical=canonical,
            label=highlight,
            label_type="highlight",
        )
        evidence = _locate_evidence_span(content, evidence_span)
        evidence_verified = bool(evidence["evidence_verified"] and not cluster_propagated)
        dimension_en, dimension_zh = _aspect_dimension_labels({}, aspect_key)
        source_detail = evidence_source or "legacy_highlight_tag"
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
                "source_detail": source_detail,
                "highlight_source": source_detail,
                "customer_highlight_raw": highlight,
                "highlight_display_allowed": True,
                "aspect_key": aspect_key,
                "dimension": _display_label_for_locale(dimension_en, dimension_zh, locale),
                "dimension_en": dimension_en,
                "dimension_zh": dimension_zh,
                "sub_category": str(comment.get("sub_category") or comment.get("category") or ""),
                "evidence_span": evidence["evidence_span"],
                "evidence_start": evidence["evidence_start"],
                "evidence_end": evidence["evidence_end"],
                "evidence_verified": bool(evidence["evidence_verified"]),
                "verified_evidence": evidence_verified,
                "cluster_propagated": cluster_propagated,
                "schema_version": "",
                "ruleset_version": "",
                "aspect_allowed": _is_label_aspect_allowed("highlight", canonical, aspect_key),
                "source_review_allowed": False,
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
            projected = _project_customer_label_occurrences(
                comment,
                label_type="highlight",
                locale=locale,
                aspects_json=aj,
            )
            return _append_waders_content_rule_occurrences(
                comment,
                projected,
                label_type="highlight",
                locale=locale,
                aspects_json=aj,
                project=True,
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
        return _append_waders_content_rule_occurrences(
            comment,
            occurrences,
            label_type="highlight",
            locale=locale,
            aspects_json=aj,
            project=True,
        )
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
        if not _is_frontstage_countable_occurrence(occurrence):
            continue
        label = str(occurrence.get("specific_issue") or "").strip()
        if label and label not in seen:
            seen.add(label)
            labels.append(label)
    return labels


def customer_highlight_tags_for_comment(comment: dict[str, Any], locale: str = "en") -> list[str]:
    seen: set[str] = set()
    labels: list[str] = []
    for occurrence in iter_customer_highlight_occurrences(comment, locale=locale):
        if not _is_frontstage_countable_occurrence(occurrence):
            continue
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
            or str(aj.get("customer_label_occurrence_schema_version") or "") == CUSTOMER_LABEL_OCCURRENCE_SCHEMA_VERSION
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
