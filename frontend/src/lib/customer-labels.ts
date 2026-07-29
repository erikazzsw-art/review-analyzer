import { aspectLabel } from "@/lib/aspect-labels";

type RecordValue = Record<string, unknown>;

export type CustomerLabelType = "issue" | "highlight";

export type CustomerLabelOccurrence = {
  type: CustomerLabelType;
  label: string;
  rawLabel: string;
  canonicalLabelKey: string;
  aspectKey: string;
  dimension: string;
  evidenceSpan: string;
  evidenceVerified: boolean;
  clusterPropagated: boolean;
  confidence: string;
  source: string;
  subCategory: string;
  legacyFallback: boolean;
  aspectAllowed: boolean;
  contextAllowed: boolean;
};

export type CustomerLabelEvidence = {
  evidenceSpan: string;
  review: string;
};

const BROAD_LABELS = new Set([
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
]);

const BROAD_LABELS_ZH = new Set([
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
]);

const ALLOWED_ASPECT_KEYS_BY_LABEL: Record<CustomerLabelType, Record<string, Set<string>>> = {
  highlight: {
    fits_as_expected: new Set(["size_fit", "boot_fit"]),
    keeps_water_out: new Set(["waterproof", "waterproof_performance"]),
    good_value_for_the_price: new Set(["value_for_money", "price_value"]),
    holds_up_well: new Set(["durability", "build_quality", "seam_integrity", "material"]),
    lightweight_waders: new Set(["weight", "material"]),
    useful_storage_space: new Set(["accessory_storage", "organization", "capacity"]),
    useful_accessories: new Set(["accessory_storage"]),
    good_traction: new Set(["grip"]),
    keeps_warm: new Set(["temperature_rating"]),
    easy_to_clean: new Set(["ease_of_use"]),
    no_strong_odor: new Set(["material", "smell", "scent"]),
    comfortable_to_wear: new Set(["comfort", "mobility", "boot_fit"]),
    feels_well_made: new Set(["build_quality", "material", "durability", "stability"]),
    good_material_quality: new Set(["material", "build_quality"]),
    arrives_on_time_and_intact: new Set(["shipping_damage", "packaging"]),
    fast_shipping: new Set(["shipping_damage", "packaging"]),
    petite_friendly: new Set(["size_fit"]),
    plus_size_friendly: new Set(["size_fit"]),
    women_friendly_fit: new Set(["size_fit"]),
    works_well_for_use_case: new Set(["other"]),
    first_impression_positive: new Set(["other", "material", "build_quality", "aesthetics"]),
    not_used_yet: new Set(["other"]),
    overall_satisfied: new Set(["other"]),
    looks_good: new Set(["aesthetics"]),
  },
  issue: {
    size_fit_problem: new Set(["size_fit", "boot_fit", "mobility"]),
    water_leaks_through: new Set(["waterproof", "waterproof_performance", "seam_integrity"]),
    pocket_not_waterproof: new Set(["accessory_storage", "organization", "capacity"]),
    pocket_too_small: new Set(["accessory_storage", "organization", "capacity"]),
    missing_accessories: new Set(["accessory_storage", "shipping_damage", "packaging"]),
    missing_wader_hanger: new Set(["accessory_storage"]),
    breaks_easily: new Set(["durability", "build_quality", "seam_integrity", "material", "stability"]),
    feels_thin_and_flimsy: new Set(["material", "durability", "build_quality"]),
    strong_chemical_smell: new Set(["material", "smell", "scent"]),
    not_breathable: new Set(["breathability", "comfort", "mobility"]),
    runs_too_small: new Set(["size_fit", "boot_fit"]),
    runs_too_large: new Set(["size_fit", "boot_fit"]),
    inaccurate_size_chart: new Set(["size_fit", "boot_fit"]),
    not_petite_friendly: new Set(["size_fit"]),
    not_plus_size_friendly: new Set(["size_fit"]),
    calf_area_too_tight: new Set(["boot_fit"]),
    pants_too_long: new Set(["size_fit"]),
    boots_too_stiff: new Set(["comfort", "material", "boot_fit"]),
    not_for_long_walks: new Set(["comfort", "boot_fit", "mobility"]),
    poor_traction: new Set(["grip"]),
    soft_soles: new Set(["grip", "durability", "material"]),
    accessories_not_as_advertised: new Set(["accessory_storage"]),
    gets_hot_quickly: new Set(["temperature_rating", "breathability"]),
    insufficient_warmth: new Set(["temperature_rating"]),
    overall_dissatisfied: new Set(["other"]),
    not_for_heavy_brush: new Set(["durability", "other"]),
    not_worth_the_price: new Set(["value_for_money", "price_value"]),
    quality_control_storage_issue: new Set(["shipping_damage", "packaging", "material", "build_quality"]),
    quality_problem: new Set(["shipping_damage", "packaging", "build_quality", "durability", "material"]),
    zipper_fails: new Set(["zipper_quality"]),
    missing_parts: new Set(["assembly", "packaging", "shipping_damage", "accessory_storage"]),
  },
};

function normText(value: string): string {
  return value
    .replace(/&/g, " and ")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

function isLabelAspectAllowed(type: CustomerLabelType, canonicalLabelKey: string, aspectKey: string): boolean {
  if (!canonicalLabelKey || !aspectKey) return true;
  const allowed = ALLOWED_ASPECT_KEYS_BY_LABEL[type]?.[canonicalLabelKey];
  return allowed ? allowed.has(aspectKey) : true;
}

function isWadersContext(subCategory: string): boolean {
  const normalized = normText(subCategory);
  return ["waders", "wader", "chest waders", "bootfoot waders"].includes(normalized);
}

function firstRegex(patterns: RegExp[], text: string): boolean {
  return patterns.some((pattern) => pattern.test(text));
}

function sentenceForEvidence(content: string, evidence: string): string {
  if (!evidence) return content.slice(0, 400);
  const escaped = evidence.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  const sentencePattern = new RegExp(`[^.!?;:\\n]*(?:\\bbut\\b|\\bhowever\\b|\\byet\\b|^)?[^.!?;:\\n]*${escaped}[^.!?;:\\n]*(?:[;:.!?]+|$)`, "i");
  const match = content.match(sentencePattern);
  return (match?.[0] || `${evidence} ${content.slice(0, 400)}`).trim();
}

function windowForEvidence(content: string, evidence: string): string {
  if (!evidence) return content.slice(0, 400);
  const start = content.toLowerCase().indexOf(evidence.toLowerCase());
  if (start < 0) return `${evidence} ${content.slice(0, 400)}`.trim();
  return content.slice(Math.max(0, start - 220), Math.min(content.length, start + evidence.length + 220));
}

function isBlockedWaterLeakIssueContext(content: string, evidence: string): boolean {
  const text = sentenceForEvidence(content, evidence).toLowerCase();
  const windowText = windowForEvidence(content, evidence).toLowerCase();
  const evidenceText = evidence.toLowerCase();
  const basis = `${evidenceText}\n${text}`;
  const negated = firstRegex([
    /\bleak[- ]?proof\b/,
    /\bno\s+leaks?\b/,
    /\bno\s+(?:water\s+)?leakage\b/,
    /\bwithout\s+(?:any\s+)?leaks?\b/,
    /\bnever\s+(?:had\s+)?leaks?\b/,
    /\bhave(?:n['’]?t| not)\s+had\s+(?:any\s+)?(?:issues?\s+with\s+)?leaks?\b/,
    /\bno\s+issues?\s+with\s+leaks?\b/,
    /\bnot\s+leaking\b/,
  ], basis);
  const positiveDry = firstRegex([
    /\b(?:remained|stayed|kept|keep|keeps)\s+(?:(?:me|you|us|him|her|them|my\s+\w+|your\s+\w+|his\s+\w+|her\s+\w+|their\s+\w+)\s+)?(?:\w+ly\s+)?dry\b/,
  ], basis) && !firstRegex([/\bnot waterproof\b/, /\bleak/, /\bwater (?:gets|got|came|comes|coming|enters|entered) (?:in|through)/], basis);
  const oldProduct = firstRegex([
    /\b(?:old|previous|last|other)\s+(?:pair|one|ones|waders?)\b[^.!?\n]{0,80}\bleak/,
    /\b(?:numerous|many|several)\s+pairs?\s+of\s+waders?\s+in\s+the\s+past\b[^.!?\n]{0,120}\bleak/,
    /\bwaders?\s+in\s+the\s+past\b[^.!?\n]{0,120}\bleak/,
    /\b(?:ones?|waders?)\s+(?:he|she|they|i|we)\s+had\b[^.!?\n]{0,80}\bleak/,
    /\b(?:pair|one|ones|waders?)\s+from\s+another\s+(?:company|brand)\b[^.!?\n]{0,100}\bleak/,
    /\b(?:reviews?|complaints)\b[^.!?\n]{0,120}\b(?:leaks?|leaking|leaked)\b/,
  ], `${basis}\n${windowText}`);
  const accessoryLeak = firstRegex([
    /\b(?:pockets?|storage pocket|hand warmer pocket|phone case|phone sleeve|phone protector|case|bag)\b[\s\S]{0,220}\b(?:not waterproof|leak|water gets in|water leaks in|wet|soak|submerged)/,
    /\b(?:not waterproof|leak(?:ing|ed|s)?|water gets in|water leaks in|wet|soak|submerged)[\s\S]{0,220}\b(?:pockets?|storage pocket|hand warmer pocket|phone case|phone sleeve|phone protector|case|bag)\b/,
  ], `${basis}\n${windowText}`);
  const evidenceAccessoryLeak = firstRegex([
    /\b(?:pockets?|storage pocket|hand warmer pocket|phone case|case|bag)\b[^.!?\n]{0,80}\b(?:leak|water gets in|wet|soak)/,
    /\b(?:leak(?:ing|ed|s)?|water gets in|wet|soak)[^.!?\n]{0,80}\b(?:pockets?|storage pocket|hand warmer pocket|phone case|case|bag)\b/,
  ], evidenceText);
  return negated || positiveDry || oldProduct || evidenceAccessoryLeak || accessoryLeak;
}

function isWadersLabelContextAllowed(
  type: CustomerLabelType,
  canonicalLabelKey: string,
  content: string,
  evidence: string,
  subCategory: string,
): boolean {
  if (!isWadersContext(subCategory)) return true;

  if (type === "highlight" && canonicalLabelKey === "not_used_yet") {
    return false;
  }
  if (type === "highlight" && canonicalLabelKey === "good_material_quality") {
    const context = sentenceForEvidence(content, evidence).toLowerCase();
    return !firstRegex([/\bwell\s+made\b/], evidence.toLowerCase()) &&
      !firstRegex([/\bpriced\s+fairly\b/], context);
  }
  if (type === "highlight" && canonicalLabelKey === "good_value_for_the_price") {
    const context = windowForEvidence(content, evidence).toLowerCase();
    return !firstRegex([/\bproduct\s+smelled\b/, /\bnasty\s+plastic\b/], context);
  }
  if (type === "highlight" && canonicalLabelKey === "holds_up_well") {
    const context = sentenceForEvidence(content, evidence).toLowerCase();
    return !firstRegex([/\bdoes\s+not\s+appear\s+sturdy\b/, /\bnot\s+sturdy\b/], context);
  }
  if (type === "highlight" && canonicalLabelKey === "works_well_for_use_case") {
    const context = sentenceForEvidence(content, evidence).toLowerCase();
    return firstRegex([
      /\bgreat\s+for\s+wade\s+fishing\b/,
      /\bgreat\s+for\s+(?:light\s+)?fly\s+fishing\b/,
      /\bworked\s+well\b[^.!?\n]{0,120}\b(?:fishing|wading|river|creek|dock|brush|marsh)\b/,
      /\bworked\s+great\b[^.!?\n]{0,120}\b(?:fishing|wading|river|creek|dock|brush)\b/,
      /\bpreformed\s+flawless\b/,
      /\bgot\s+the\s+job\s+done\b/,
      /\bversatility\s+for\s+fishing\s+or\s+other\s+projects\b/,
    ], context);
  }
  if (type === "highlight" && canonicalLabelKey === "lightweight_waders") {
    const context = sentenceForEvidence(content, evidence).toLowerCase();
    return firstRegex([
      /\blightweight\b[^.!?\n]{0,80}\b(?:sturdy|still\s+going\s+strong|durable|tough)\b/,
      /\bnice\s+and\s+light\b/,
      /\blight[-\s]+weight\b/,
    ], context);
  }
  return true;
}

function hasCjk(value: string): boolean {
  return /[\u3400-\u9fff]/.test(value);
}

export function splitTagText(value: unknown): string[] {
  return String(value || "")
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

export function uniqueStrings(values: string[]): string[] {
  return Array.from(new Set(values.filter(Boolean)));
}

function finiteNumber(value: unknown): number | null {
  if (typeof value === "number" && Number.isFinite(value)) return value;
  if (typeof value === "string" && value.trim()) {
    const parsed = Number(value.replace("%", ""));
    return Number.isFinite(parsed) ? parsed : null;
  }
  return null;
}

function boolValue(value: unknown): boolean {
  return value === true || value === "true" || value === 1 || value === "1";
}

function localeLabel(enValue: unknown, zhValue: unknown, locale: string): string {
  const en = String(enValue || "").trim();
  const zh = String(zhValue || "").trim();
  return locale.startsWith("zh") ? zh || en : en || zh;
}

function reviewBody(comment: RecordValue): string {
  return String(comment.content || comment.body || comment.comment || "").trim();
}

function evidenceVerified(comment: RecordValue, evidence: string, clusterPropagated: boolean): boolean {
  const content = reviewBody(comment);
  return Boolean(evidence && content.includes(evidence) && !clusterPropagated);
}

export function parseAspectsPayload(comment: RecordValue): RecordValue | null {
  const raw = comment.aspects_json;
  if (raw && typeof raw === "object" && !Array.isArray(raw)) {
    return raw as RecordValue;
  }
  if (typeof raw === "string" && raw.trim()) {
    try {
      const parsed = JSON.parse(raw) as unknown;
      return parsed && typeof parsed === "object" && !Array.isArray(parsed)
        ? (parsed as RecordValue)
        : null;
    } catch {
      return null;
    }
  }
  return null;
}

export function getAspects(comment: RecordValue): RecordValue[] {
  const aspects = parseAspectsPayload(comment)?.aspects;
  return Array.isArray(aspects)
    ? aspects.filter((item): item is RecordValue => Boolean(item) && typeof item === "object")
    : [];
}

function payloadOccurrences(payload: RecordValue | null): RecordValue[] {
  const occurrences = payload?.customer_label_occurrences;
  return Array.isArray(occurrences)
    ? occurrences.filter((item): item is RecordValue => Boolean(item) && typeof item === "object")
    : [];
}

export function isCustomerLabelAllowed(
  label: string,
  locale: string,
  aspectKey = "",
  aspectDisplayLabel = "",
): boolean {
  const cleaned = label.trim();
  if (!cleaned) return false;
  if (locale.startsWith("en") && hasCjk(cleaned)) return false;
  if (BROAD_LABELS_ZH.has(cleaned)) return false;
  const normalized = normText(cleaned);
  if (!normalized && !BROAD_LABELS_ZH.has(cleaned)) return true;
  if (BROAD_LABELS.has(normalized)) return false;
  if (aspectKey && normalized === normText(aspectKey)) return false;
  if (aspectDisplayLabel && (normalized === normText(aspectDisplayLabel) || cleaned === aspectDisplayLabel.trim())) {
    return false;
  }
  return true;
}

function hasCustomerPayload(payload: RecordValue | null, aspectKeys: string[]): boolean {
  if (!payload) return false;
  if (payload.customer_label_schema_version === "1.0" || payload.specific_issue_schema_version === "1.0") {
    return true;
  }
  return getPayloadAspects(payload).some((aspect) => aspectKeys.some((key) => key in aspect));
}

function getPayloadAspects(payload: RecordValue): RecordValue[] {
  const aspects = payload.aspects;
  return Array.isArray(aspects)
    ? aspects.filter((item): item is RecordValue => Boolean(item) && typeof item === "object")
    : [];
}

export function customerIssueTags(comment: RecordValue, locale: string): string[] {
  const allOccurrences = customerLabelOccurrences(comment, "issue", locale);
  const occurrences = allOccurrences
    .filter((occurrence) => isVerifiedSourceReviewOccurrence(occurrence))
    .map((occurrence) => occurrence.label)
    .filter(Boolean);
  if (occurrences.length > 0 || allOccurrences.length > 0) {
    return uniqueStrings(occurrences);
  }

  const payload = parseAspectsPayload(comment);
  const aspects = getAspects(comment);
  const labels = aspects
    .filter((aspect) => {
      const hasSpecificIssuePayload = Boolean(aspect.specific_issue || aspect.specific_issue_zh) &&
        Boolean(aspect.canonical_issue_key);
      const evidenceSpan = String(aspect.evidence_span || aspect.evidence || "").trim();
      const aspectKey = String(aspect.key || aspect.aspect_key || "").trim();
      const canonicalKey = String(aspect.canonical_issue_key || "").trim();
      const aspectClusterPropagated =
        "cluster_propagated" in aspect ? boolValue(aspect.cluster_propagated) : boolValue(payload?.cluster_propagated);
      return (
        (String(aspect.polarity || "").toLowerCase() === "negative" || hasSpecificIssuePayload) &&
        aspect.display_allowed !== false &&
        hasSpecificIssuePayload &&
        isLabelAspectAllowed("issue", canonicalKey, aspectKey) &&
        !(canonicalKey === "water_leaks_through" && isBlockedWaterLeakIssueContext(reviewBody(comment), evidenceSpan)) &&
        evidenceVerified(comment, evidenceSpan, aspectClusterPropagated)
      );
    })
    .map((aspect) => {
      const aspectKey = String(aspect.key || aspect.aspect_key || "").trim();
      const label = String(
        locale.startsWith("zh")
          ? aspect.specific_issue_zh || aspect.specific_issue
          : aspect.specific_issue || aspect.specific_issue_zh,
      ).trim();
      return isCustomerLabelAllowed(label, locale, aspectKey, aspectLabel(aspectKey, locale)) ? label : "";
    })
    .filter(Boolean);

  if (labels.length > 0 || hasCustomerPayload(payload, ["specific_issue", "canonical_issue_key", "display_allowed"])) {
    return uniqueStrings(labels);
  }
  return [];
}

export function customerHighlightTags(comment: RecordValue, locale: string): string[] {
  const allOccurrences = customerLabelOccurrences(comment, "highlight", locale);
  const occurrences = allOccurrences
    .filter((occurrence) => isVerifiedSourceReviewOccurrence(occurrence))
    .map((occurrence) => occurrence.label)
    .filter(Boolean);
  if (occurrences.length > 0 || allOccurrences.length > 0) {
    return uniqueStrings(occurrences);
  }

  const payload = parseAspectsPayload(comment);
  const labels = getAspects(comment)
    .filter((aspect) => {
      const evidenceSpan = String(aspect.evidence_span || aspect.evidence || "").trim();
      const aspectKey = String(aspect.key || aspect.aspect_key || "").trim();
      const canonicalKey = String(aspect.canonical_highlight_key || "").trim();
      const aspectClusterPropagated =
        "cluster_propagated" in aspect ? boolValue(aspect.cluster_propagated) : boolValue(payload?.cluster_propagated);
      return (
        String(aspect.polarity || "").toLowerCase() === "positive" &&
        aspect.highlight_display_allowed !== false &&
        Boolean(aspect.customer_highlight || aspect.customer_highlight_zh) &&
        Boolean(aspect.canonical_highlight_key) &&
        isLabelAspectAllowed("highlight", canonicalKey, aspectKey) &&
        evidenceVerified(comment, evidenceSpan, aspectClusterPropagated)
      );
    })
    .map((aspect) => {
      const aspectKey = String(aspect.key || aspect.aspect_key || "").trim();
      const label = String(
        locale.startsWith("zh")
          ? aspect.customer_highlight_zh || aspect.customer_highlight
          : aspect.customer_highlight || aspect.customer_highlight_zh,
      ).trim();
      return isCustomerLabelAllowed(label, locale, aspectKey, aspectLabel(aspectKey, locale)) ? label : "";
    })
    .filter(Boolean);

  if (
    labels.length > 0 ||
    hasCustomerPayload(payload, ["customer_highlight", "canonical_highlight_key", "highlight_display_allowed"])
  ) {
    return uniqueStrings(labels);
  }
  return [];
}

export function customerTagText(
  comment: RecordValue,
  type: "issue" | "highlight",
  locale: string,
): string {
  const labels = type === "issue" ? customerIssueTags(comment, locale) : customerHighlightTags(comment, locale);
  return labels.join(", ");
}

export function customerLabelOccurrences(
  comment: RecordValue,
  type: CustomerLabelType,
  locale: string,
): CustomerLabelOccurrence[] {
  const payload = parseAspectsPayload(comment);
  const clusterPropagated = boolValue(payload?.cluster_propagated);
  const subCategory = String(payload?.sub_category || comment.sub_category || comment.category || "").trim();
  const projected = payloadOccurrences(payload)
    .filter((occurrence) => String(occurrence.type || "").toLowerCase() === type)
    .map((occurrence) => {
      const occurrenceClusterPropagated =
        "cluster_propagated" in occurrence ? boolValue(occurrence.cluster_propagated) : clusterPropagated;
      const aspectKey = String(occurrence.aspect_key || "").trim();
      let label = localeLabel(occurrence.display_label_en, occurrence.display_label_zh, locale);
      const dimension = localeLabel(occurrence.dimension_en, occurrence.dimension_zh, locale) ||
        (aspectKey ? aspectLabel(aspectKey, locale) : "");
      const evidenceSpan = String(occurrence.evidence_span || "").trim();
      let canonicalLabelKey = String(occurrence.canonical_label_key || "").trim();
      const content = reviewBody(comment);
      const occurrenceSubCategory = String(occurrence.sub_category || subCategory).trim();
      if (type === "highlight" && canonicalLabelKey === "feels_well_made" && isWadersContext(occurrenceSubCategory)) {
        canonicalLabelKey = "good_material_quality";
        label = locale.startsWith("zh") ? "材质质量好" : "Good Material Quality";
      }
      const aspectAllowed = boolValue(occurrence.aspect_allowed ?? true) &&
        isLabelAspectAllowed(type, canonicalLabelKey, aspectKey);
      const contextAllowed = boolValue(occurrence.context_allowed ?? true) &&
        !(type === "issue" && canonicalLabelKey === "water_leaks_through" &&
          isBlockedWaterLeakIssueContext(content, evidenceSpan)) &&
        isWadersLabelContextAllowed(type, canonicalLabelKey, content, evidenceSpan, occurrenceSubCategory);
      return {
        type,
        label,
        rawLabel: String(occurrence.raw_label || label).trim(),
        canonicalLabelKey,
        aspectKey,
        dimension,
        evidenceSpan,
        evidenceVerified: evidenceVerified(comment, evidenceSpan, occurrenceClusterPropagated),
        clusterPropagated: occurrenceClusterPropagated,
        confidence: String(occurrence.confidence || "").trim(),
        source: String(occurrence.source_detail || occurrence.source || "").trim(),
        subCategory: occurrenceSubCategory,
        legacyFallback: boolValue(occurrence.legacy_fallback) || String(occurrence.source || "") === "legacy",
        aspectAllowed,
        contextAllowed,
      };
    })
    .filter((occurrence) => {
      if (!occurrence.label || !occurrence.canonicalLabelKey) return false;
      return isCustomerLabelAllowed(occurrence.label, locale, occurrence.aspectKey, occurrence.dimension);
    });
  if (projected.length > 0) return projected;

  const aspects = getAspects(comment);
  const fromAspects = aspects
    .filter((aspect) => {
      if (type === "issue") {
        const hasIssue = Boolean(aspect.specific_issue || aspect.specific_issue_zh) &&
          Boolean(aspect.canonical_issue_key);
        return (
          hasIssue &&
          aspect.display_allowed !== false &&
          (String(aspect.polarity || "").toLowerCase() === "negative" || hasIssue)
        );
      }
      return (
        Boolean(aspect.customer_highlight || aspect.customer_highlight_zh) &&
        Boolean(aspect.canonical_highlight_key) &&
        aspect.highlight_display_allowed !== false &&
        String(aspect.polarity || "").toLowerCase() === "positive"
      );
    })
    .map((aspect) => {
      const aspectClusterPropagated =
        "cluster_propagated" in aspect ? boolValue(aspect.cluster_propagated) : clusterPropagated;
      const aspectKey = String(aspect.key || aspect.aspect_key || "").trim();
      let label = type === "issue"
        ? localeLabel(aspect.specific_issue, aspect.specific_issue_zh, locale)
        : localeLabel(aspect.customer_highlight, aspect.customer_highlight_zh, locale);
      let canonicalLabelKey = type === "issue"
        ? String(aspect.canonical_issue_key || "").trim()
        : String(aspect.canonical_highlight_key || "").trim();
      if (type === "highlight" && canonicalLabelKey === "feels_well_made" && isWadersContext(subCategory)) {
        canonicalLabelKey = "good_material_quality";
        label = locale.startsWith("zh") ? "材质质量好" : "Good Material Quality";
      }
      const evidenceSpan = String(aspect.evidence_span || aspect.evidence || "").trim();
      const dimension = aspectKey ? aspectLabel(aspectKey, locale) : String(aspect.dimension || aspect.aspect_label || "").trim();
      const aspectAllowed = isLabelAspectAllowed(type, canonicalLabelKey, aspectKey);
      const content = reviewBody(comment);
      const contextAllowed = !(type === "issue" && canonicalLabelKey === "water_leaks_through" &&
        isBlockedWaterLeakIssueContext(content, evidenceSpan)) &&
        isWadersLabelContextAllowed(type, canonicalLabelKey, content, evidenceSpan, subCategory);
      return {
        type,
        label,
        rawLabel: String(
          type === "issue"
            ? aspect.specific_issue_raw || aspect.specific_issue || label
            : aspect.customer_highlight_raw || aspect.customer_highlight || label,
        ).trim(),
        canonicalLabelKey,
        aspectKey,
        dimension,
        evidenceSpan,
        evidenceVerified: evidenceVerified(comment, evidenceSpan, aspectClusterPropagated),
        clusterPropagated: aspectClusterPropagated,
        confidence: String(type === "issue" ? aspect.issue_confidence || "" : aspect.highlight_confidence || "").trim(),
        source: String(type === "issue" ? aspect.issue_source || "" : aspect.highlight_source || "").trim(),
        subCategory,
        legacyFallback: false,
        aspectAllowed,
        contextAllowed,
      };
    })
    .filter((occurrence) => {
      if (!occurrence.label || !occurrence.canonicalLabelKey) return false;
      return isCustomerLabelAllowed(occurrence.label, locale, occurrence.aspectKey, occurrence.dimension);
    });
  if (fromAspects.length > 0 || hasCustomerPayload(payload, type === "issue"
    ? ["specific_issue", "canonical_issue_key", "display_allowed"]
    : ["customer_highlight", "canonical_highlight_key", "highlight_display_allowed"])) {
    return fromAspects;
  }

  const tagField = type === "issue" ? comment.issue_tag : comment.highlight_tag;
  return splitTagText(tagField)
    .filter((label) => isCustomerLabelAllowed(label, locale))
    .map((label) => ({
      type,
      label,
      rawLabel: label,
      canonicalLabelKey: label
        .trim()
        .toLowerCase()
        .replace(/[^a-z0-9]+/g, "_")
        .replace(/^_+|_+$/g, "") || label.trim(),
      aspectKey: "",
      dimension: "",
      evidenceSpan: "",
      evidenceVerified: false,
      clusterPropagated: false,
      confidence: "low",
      source: type === "issue" ? "legacy_issue_tag" : "legacy_highlight_tag",
      subCategory: String(comment.sub_category || comment.category || "").trim(),
      legacyFallback: true,
      aspectAllowed: true,
      contextAllowed: true,
    }));
}

export function rowMentionCount(row: RecordValue): number {
  return finiteNumber(row.mention_count ?? row.count) ?? 0;
}

export function rowReviewCount(row: RecordValue): number {
  return finiteNumber(row.review_count ?? row.count) ?? 0;
}

export function rowMentionShare(row: RecordValue): number {
  return finiteNumber(row.mention_share ?? row.pct ?? row.percentage ?? row.percent) ?? 0;
}

export function rowImpactReviewShare(row: RecordValue, totalReviews?: number): number {
  const explicit = finiteNumber(row.impact_review_share);
  if (explicit !== null) return explicit;
  const reviewCount = rowReviewCount(row);
  if (typeof totalReviews === "number" && totalReviews > 0 && row.review_count !== undefined) {
    return Math.round((reviewCount / totalReviews) * 1000) / 10;
  }
  return finiteNumber(row.pct ?? row.percentage ?? row.percent) ?? 0;
}

export function rowUsesLegacyStats(row: RecordValue): boolean {
  return Boolean(row.legacy_fallback) ||
    (row.mention_share === undefined &&
      row.impact_review_share === undefined &&
      row.mention_count === undefined &&
      row.review_count === undefined);
}

function evidenceStrings(value: unknown): string[] {
  if (Array.isArray(value)) {
    return value
      .map((item) => String(item || "").trim())
      .filter((item) => item && item !== "No representative comment found.");
  }
  const single = String(value || "").trim();
  return single && single !== "No representative comment found." ? [single] : [];
}

export function isFrontstageCustomerLabelOccurrence(occurrence: CustomerLabelOccurrence): boolean {
  return !occurrence.clusterPropagated &&
    !occurrence.legacyFallback &&
    occurrence.aspectAllowed &&
    occurrence.contextAllowed &&
    occurrence.evidenceVerified &&
    Boolean(occurrence.evidenceSpan);
}

export function isVerifiedSourceReviewOccurrence(occurrence: CustomerLabelOccurrence): boolean {
  return isFrontstageCustomerLabelOccurrence(occurrence) && occurrence.evidenceVerified && Boolean(occurrence.evidenceSpan);
}

export function rowRepresentativeEvidence(row: RecordValue): CustomerLabelEvidence[] {
  if (boolValue(row.cluster_propagated) || !boolValue(row.evidence_verified)) {
    return [];
  }
  const result: CustomerLabelEvidence[] = [];
  const seen = new Set<string>();
  const comments = evidenceStrings(row.representative_comments);
  for (const [index, evidenceSpan] of evidenceStrings(row.evidence_spans).entries()) {
    if (seen.has(evidenceSpan)) continue;
    seen.add(evidenceSpan);
    result.push({ evidenceSpan, review: comments[index] || "" });
  }

  const representative = row.representative_evidence;
  const values = Array.isArray(representative) ? representative : representative ? [representative] : [];
  for (const item of values) {
    let evidenceSpan = "";
    let review = "";
    if (item && typeof item === "object") {
      const record = item as RecordValue;
      evidenceSpan = String(record.evidence_span || record.evidenceSpan || record.span || record.text || "").trim();
      review = String(record.review || record.content || record.full_review || record.comment || "").trim();
    } else {
      evidenceSpan = String(item || "").trim();
    }
    if (!evidenceSpan || seen.has(evidenceSpan) || evidenceSpan === "No representative comment found.") continue;
    seen.add(evidenceSpan);
    result.push({ evidenceSpan, review });
  }
  return result;
}
