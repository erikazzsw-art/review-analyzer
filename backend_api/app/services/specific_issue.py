from __future__ import annotations

import copy
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

SPECIFIC_ISSUE_SCHEMA_VERSION = "1.0"
CUSTOMER_LABEL_SCHEMA_VERSION = "1.0"
ISSUE_RULESET_VERSION = "2026-07-24-customer-label-system"
HIGHLIGHT_RULESET_VERSION = "2026-07-24-customer-label-system"
CUSTOMER_LABEL_RULESET_VERSION = f"{ISSUE_RULESET_VERSION}+{HIGHLIGHT_RULESET_VERSION}"

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


_NEGATED_WATER_LEAK_PATTERNS = [
    r"\bno\s+leaks?\b",
    r"\bwithout\s+(any\s+)?leaks?\b",
    r"\bnever\s+(had\s+)?leaks?\b",
    r"\b(did|does|do|has|have|had)(?:n['’]?t| not)\s+leak\b",
    r"\bnot\s+leaking\b",
]


def _is_negated_water_leak_statement(text: str) -> bool:
    return _first_regex(_NEGATED_WATER_LEAK_PATTERNS, text)


def _water_leak_issue_hit(evidence: str, content: str) -> bool:
    basis = evidence.strip() or content[:400]
    if _is_negated_water_leak_statement(basis):
        return False
    text = f"{evidence} {content[:400]}".lower()
    text = re.sub(r"\bno\s+leaks?\b", " ", text)
    text = re.sub(r"\bwithout\s+(any\s+)?leaks?\b", " ", text)
    text = re.sub(r"\bnever\s+(had\s+)?leaks?\b", " ", text)
    text = re.sub(r"\b(did|does|do|has|have|had)(?:n['’]?t| not)\s+leak\b", " ", text)
    text = re.sub(r"\bnot\s+leaking\b", " ", text)
    return _first_regex(
        [
            r"\bnot waterproof\b",
            r"\bleak",
            r"\bwater (gets|got|came|comes|coming|enters|entered) (in|through)",
        ],
        text,
    )


def _evidence_verified(content: str, evidence: str, *, cluster_propagated: bool = False) -> bool:
    return bool(evidence and evidence in content and not cluster_propagated)


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

    return {
        "specific_issue": issue,
        "specific_issue_zh": issue_zh,
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

    return {
        "customer_highlight": highlight_en,
        "customer_highlight_zh": highlight_zh,
        "canonical_highlight_key": canonical,
        "highlight_confidence": confidence,
        "highlight_source": source,
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
        if issue:
            aspect.update(
                {
                    "specific_issue": issue["specific_issue"],
                    "specific_issue_zh": issue["specific_issue_zh"],
                    "canonical_issue_key": issue["canonical_issue_key"],
                    "issue_confidence": issue["issue_confidence"],
                    "issue_source": issue["issue_source"],
                    "specific_issue_raw": issue["specific_issue_raw"],
                    "display_allowed": issue["display_allowed"],
                    "aspect_label": issue["dimension"],
                }
            )
        highlight = _normalize_aspect_highlight(
            aspect,
            sub_category=normalized_sub_category,
            content=content,
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
                    "customer_highlight_raw": highlight["customer_highlight_raw"],
                    "highlight_display_allowed": highlight["highlight_display_allowed"],
                    "aspect_label": highlight["dimension"],
                }
            )
    enriched["specific_issue_schema_version"] = SPECIFIC_ISSUE_SCHEMA_VERSION
    enriched["customer_label_schema_version"] = CUSTOMER_LABEL_SCHEMA_VERSION
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
        occurrences.append(
            {
                "comment_id": comment.get("id"),
                "content": content,
                "specific_issue": issue,
                "specific_issue_en": issue,
                "specific_issue_zh": issue,
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


def _append_unique_snippet(target: list[str], content: str, limit: int = 240) -> None:
    snippet = content.strip()[:limit]
    if snippet and snippet not in target:
        target.append(snippet)


def iter_specific_issue_occurrences(comment: dict[str, Any], locale: str = "en") -> list[dict[str, Any]]:
    content = str(comment.get("content") or "").strip()
    aj = coerce_aspects_json(comment.get("aspects_json"))
    schema_version = ""
    has_specific_issue_payload = False
    occurrences: list[dict[str, Any]] = []
    if aj:
        schema_version = str(aj.get("specific_issue_schema_version") or "")
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
            )
            if not issue or not issue["display_allowed"]:
                continue
            display_label = issue["specific_issue_zh"] if locale.startswith("zh") else issue["specific_issue"]
            evidence = issue["evidence_span"]
            verified_evidence = _evidence_verified(
                content,
                evidence,
                cluster_propagated=bool(aj.get("cluster_propagated")),
            )
            occurrences.append(
                {
                    "comment_id": comment.get("id"),
                    "content": content,
                    "specific_issue": display_label,
                    "specific_issue_en": issue["specific_issue"],
                    "specific_issue_zh": issue["specific_issue_zh"],
                    "canonical_issue_key": issue["canonical_issue_key"],
                    "issue_confidence": issue["issue_confidence"],
                    "issue_source": issue["issue_source"],
                    "specific_issue_raw": issue["specific_issue_raw"],
                    "display_allowed": True,
                    "aspect_key": issue["aspect_key"],
                    "dimension": issue["dimension"],
                    "sub_category": issue["sub_category"],
                    "evidence_span": evidence,
                    "verified_evidence": verified_evidence,
                    "source_review_allowed": bool(
                        content
                        and not bool(aj.get("cluster_propagated"))
                        and (verified_evidence or issue["issue_source"] != "broad_fallback")
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
    groups: dict[tuple[str, str], dict[str, Any]] = {}
    comment_counts: dict[tuple[str, str], set[Any]] = defaultdict(set)
    confidence_counter: dict[tuple[str, str], Counter[str]] = defaultdict(Counter)
    issue_label_counter: dict[tuple[str, str], Counter[str]] = defaultdict(Counter)

    for fallback_index, comment in enumerate(comments):
        comment_id = comment.get("id")
        if comment_id is None:
            comment_id = f"row-{fallback_index}"
        counted_in_comment: set[tuple[str, str]] = set()
        seen_occurrences_in_comment: set[tuple[str, str, str]] = set()
        for occurrence in iter_specific_issue_occurrences(comment, locale=locale):
            occurrence_key = (
                str(occurrence.get("sub_category") or ""),
                str(occurrence.get("aspect_key") or ""),
                str(occurrence.get("canonical_issue_key") or ""),
            )
            if not occurrence_key[2] or occurrence_key in seen_occurrences_in_comment:
                continue
            seen_occurrences_in_comment.add(occurrence_key)
            key = (occurrence_key[0], occurrence_key[2])
            if key not in groups:
                is_legacy = bool(occurrence.get("legacy_fallback"))
                groups[key] = {
                    "tag": occurrence["specific_issue"],
                    "specific_issue": occurrence["specific_issue"],
                    "canonical_issue_key": occurrence["canonical_issue_key"],
                    "aspect_key": occurrence.get("aspect_key") or "",
                    "aspect_keys": [],
                    "dimension": "",
                    "dimensions": [],
                    "sub_category": occurrence.get("sub_category") or "",
                    "issue_source": occurrence.get("issue_source") or "",
                    "issue_sources": [],
                    "legacy_fallback": is_legacy,
                    "is_specific_issue": not is_legacy,
                    "display_allowed": True,
                    "specific_issue_schema_version": "" if is_legacy else SPECIFIC_ISSUE_SCHEMA_VERSION,
                    "issue_ruleset_version": ISSUE_RULESET_VERSION,
                    "representative_comments": [],
                    "evidence_spans": [],
                    "reason": "",
                }
            if not occurrence.get("legacy_fallback"):
                groups[key]["legacy_fallback"] = False
                groups[key]["is_specific_issue"] = True
                groups[key]["specific_issue_schema_version"] = SPECIFIC_ISSUE_SCHEMA_VERSION
            aspect_key = str(occurrence.get("aspect_key") or "")
            if aspect_key and aspect_key not in groups[key]["aspect_keys"]:
                groups[key]["aspect_keys"].append(aspect_key)
            dimension = str(occurrence.get("dimension") or "")
            if dimension and dimension not in groups[key]["dimensions"]:
                groups[key]["dimensions"].append(dimension)
            issue_source = str(occurrence.get("issue_source") or "")
            if issue_source and issue_source not in groups[key]["issue_sources"]:
                groups[key]["issue_sources"].append(issue_source)
            issue_label_counter[key][str(occurrence.get("specific_issue") or groups[key]["specific_issue"])] += 1
            if key not in counted_in_comment:
                comment_counts[key].add(comment_id)
                counted_in_comment.add(key)
            confidence_counter[key][str(occurrence.get("issue_confidence") or "low")] += 1
            content = str(occurrence.get("content") or "").strip()
            evidence = str(occurrence.get("evidence_span") or "").strip()
            if occurrence.get("verified_evidence") and content:
                _append_unique_snippet(groups[key]["representative_comments"], content)
                if evidence and evidence not in groups[key]["evidence_spans"]:
                    groups[key]["evidence_spans"].append(evidence)
            elif occurrence.get("legacy_fallback") and content:
                _append_unique_snippet(groups[key]["representative_comments"], content)

    rows: list[dict[str, Any]] = []
    for key, row in groups.items():
        count = len(comment_counts[key])
        pct = round(count / pool_size * 100, 1) if pool_size else 0.0
        conf = confidence_counter[key].most_common(1)[0][0] if confidence_counter[key] else "low"
        issue = issue_label_counter[key].most_common(1)[0][0] if issue_label_counter[key] else row["specific_issue"]
        aspect_keys = row["aspect_keys"]
        dimensions = row["dimensions"]
        examples = row["representative_comments"][:5]
        evidence_spans = row["evidence_spans"][:5]
        rows.append(
            {
                **row,
                "tag": issue,
                "specific_issue": issue,
                "aspect_key": aspect_keys[0] if aspect_keys else row.get("aspect_key", ""),
                "aspect_keys": aspect_keys,
                "dimension": ", ".join(dimensions),
                "dimensions": dimensions,
                "issue_source": row["issue_sources"][0] if row["issue_sources"] else row.get("issue_source", ""),
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


def _legacy_highlight_occurrences(comment: dict[str, Any], locale: str) -> list[dict[str, Any]]:
    occurrences: list[dict[str, Any]] = []
    content = str(comment.get("content") or "").strip()
    for raw_tag in str(comment.get("highlight_tag") or "").split(","):
        highlight = raw_tag.strip()
        if not highlight:
            continue
        if not _is_customer_label_allowed(highlight, locale=locale):
            continue
        occurrences.append(
            {
                "comment_id": comment.get("id"),
                "content": content,
                "customer_highlight": highlight,
                "canonical_highlight_key": _slug(highlight),
                "highlight_confidence": "low",
                "highlight_source": "legacy_highlight_tag",
                "customer_highlight_raw": highlight,
                "highlight_display_allowed": True,
                "aspect_key": "",
                "dimension": "",
                "sub_category": str(comment.get("sub_category") or comment.get("category") or ""),
                "evidence_span": "",
                "verified_evidence": False,
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
    has_highlight_payload = False
    occurrences: list[dict[str, Any]] = []
    if aj:
        customer_schema_version = str(aj.get("customer_label_schema_version") or "")
        specific_schema_version = str(aj.get("specific_issue_schema_version") or "")
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
            display_label = (
                highlight["customer_highlight_zh"]
                if locale.startswith("zh")
                else highlight["customer_highlight"]
            )
            evidence = highlight["evidence_span"]
            verified_evidence = _evidence_verified(
                content,
                evidence,
                cluster_propagated=bool(aj.get("cluster_propagated")),
            )
            occurrences.append(
                {
                    "comment_id": comment.get("id"),
                    "content": content,
                    "customer_highlight": display_label,
                    "customer_highlight_en": highlight["customer_highlight"],
                    "customer_highlight_zh": highlight["customer_highlight_zh"],
                    "canonical_highlight_key": highlight["canonical_highlight_key"],
                    "highlight_confidence": highlight["highlight_confidence"],
                    "highlight_source": highlight["highlight_source"],
                    "customer_highlight_raw": highlight["customer_highlight_raw"],
                    "highlight_display_allowed": True,
                    "aspect_key": highlight["aspect_key"],
                    "dimension": highlight["dimension"],
                    "dimension_en": highlight["dimension_en"],
                    "dimension_zh": highlight["dimension_zh"],
                    "sub_category": highlight["sub_category"],
                    "evidence_span": evidence,
                    "verified_evidence": verified_evidence,
                    "source_review_allowed": bool(
                        content
                        and not bool(aj.get("cluster_propagated"))
                        and (verified_evidence or highlight["highlight_source"] != "broad_fallback")
                    ),
                    "legacy_fallback": False,
                }
            )
    if occurrences or customer_schema_version == CUSTOMER_LABEL_SCHEMA_VERSION or has_highlight_payload:
        return occurrences
    return _legacy_highlight_occurrences(comment, locale)


def build_customer_highlight_rows(
    comments: list[dict[str, Any]],
    *,
    locale: str = "en",
    limit: int = 10,
) -> list[dict[str, Any]]:
    pool_size = len(comments)
    groups: dict[tuple[str, str], dict[str, Any]] = {}
    comment_counts: dict[tuple[str, str], set[Any]] = defaultdict(set)
    confidence_counter: dict[tuple[str, str], Counter[str]] = defaultdict(Counter)
    label_counter: dict[tuple[str, str], Counter[str]] = defaultdict(Counter)

    for fallback_index, comment in enumerate(comments):
        comment_id = comment.get("id")
        if comment_id is None:
            comment_id = f"row-{fallback_index}"
        counted_in_comment: set[tuple[str, str]] = set()
        seen_occurrences_in_comment: set[tuple[str, str, str]] = set()
        for occurrence in iter_customer_highlight_occurrences(comment, locale=locale):
            occurrence_key = (
                str(occurrence.get("sub_category") or ""),
                str(occurrence.get("aspect_key") or ""),
                str(occurrence.get("canonical_highlight_key") or ""),
            )
            if not occurrence_key[2] or occurrence_key in seen_occurrences_in_comment:
                continue
            seen_occurrences_in_comment.add(occurrence_key)
            key = (occurrence_key[0], occurrence_key[2])
            if key not in groups:
                is_legacy = bool(occurrence.get("legacy_fallback"))
                groups[key] = {
                    "tag": occurrence["customer_highlight"],
                    "customer_highlight": occurrence["customer_highlight"],
                    "canonical_highlight_key": occurrence["canonical_highlight_key"],
                    "aspect_key": occurrence.get("aspect_key") or "",
                    "aspect_keys": [],
                    "dimension": "",
                    "dimensions": [],
                    "sub_category": occurrence.get("sub_category") or "",
                    "highlight_source": occurrence.get("highlight_source") or "",
                    "highlight_sources": [],
                    "legacy_fallback": is_legacy,
                    "is_customer_highlight": not is_legacy,
                    "display_allowed": True,
                    "customer_label_schema_version": "" if is_legacy else CUSTOMER_LABEL_SCHEMA_VERSION,
                    "highlight_ruleset_version": HIGHLIGHT_RULESET_VERSION,
                    "representative_comments": [],
                    "evidence_spans": [],
                    "reason": "",
                }
            if not occurrence.get("legacy_fallback"):
                groups[key]["legacy_fallback"] = False
                groups[key]["is_customer_highlight"] = True
                groups[key]["customer_label_schema_version"] = CUSTOMER_LABEL_SCHEMA_VERSION
            aspect_key = str(occurrence.get("aspect_key") or "")
            if aspect_key and aspect_key not in groups[key]["aspect_keys"]:
                groups[key]["aspect_keys"].append(aspect_key)
            dimension = str(occurrence.get("dimension") or "")
            if dimension and dimension not in groups[key]["dimensions"]:
                groups[key]["dimensions"].append(dimension)
            source = str(occurrence.get("highlight_source") or "")
            if source and source not in groups[key]["highlight_sources"]:
                groups[key]["highlight_sources"].append(source)
            label_counter[key][str(occurrence.get("customer_highlight") or groups[key]["customer_highlight"])] += 1
            if key not in counted_in_comment:
                comment_counts[key].add(comment_id)
                counted_in_comment.add(key)
            confidence_counter[key][str(occurrence.get("highlight_confidence") or "low")] += 1
            content = str(occurrence.get("content") or "").strip()
            evidence = str(occurrence.get("evidence_span") or "").strip()
            if occurrence.get("verified_evidence") and content:
                _append_unique_snippet(groups[key]["representative_comments"], content)
                if evidence and evidence not in groups[key]["evidence_spans"]:
                    groups[key]["evidence_spans"].append(evidence)

    rows: list[dict[str, Any]] = []
    for key, row in groups.items():
        count = len(comment_counts[key])
        if count <= 0:
            continue
        pct = round(count / pool_size * 100, 1) if pool_size else 0.0
        conf = confidence_counter[key].most_common(1)[0][0] if confidence_counter[key] else "low"
        label = label_counter[key].most_common(1)[0][0] if label_counter[key] else row["customer_highlight"]
        aspect_keys = row["aspect_keys"]
        dimensions = row["dimensions"]
        examples = row["representative_comments"][:5]
        evidence_spans = row["evidence_spans"][:5]
        rows.append(
            {
                **row,
                "tag": label,
                "customer_highlight": label,
                "aspect_key": aspect_keys[0] if aspect_keys else row.get("aspect_key", ""),
                "aspect_keys": aspect_keys,
                "dimension": ", ".join(dimensions),
                "dimensions": dimensions,
                "highlight_source": row["highlight_sources"][0] if row["highlight_sources"] else row.get("highlight_source", ""),
                "count": count,
                "pct": pct,
                "mention_share": pct,
                "highlight_confidence": conf,
                "representative_comments": examples,
                "evidence_spans": evidence_spans,
                "reason": examples[0] if examples else "No representative comment found.",
            }
        )

    return sorted(rows, key=lambda r: (-int(r["count"]), str(r["customer_highlight"]).lower()))[:limit]


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
            )
            if enriched:
                decorated["aspects_json"] = enriched
    decorated["customer_issue_tags"] = ", ".join(customer_issue_tags_for_comment(decorated, locale=locale))
    decorated["customer_highlight_tags"] = ", ".join(customer_highlight_tags_for_comment(decorated, locale=locale))
    decorated["customer_label_schema_version"] = CUSTOMER_LABEL_SCHEMA_VERSION
    return decorated
