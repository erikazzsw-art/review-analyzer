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

function normText(value: string): string {
  return value
    .replace(/&/g, " and ")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, " ")
    .replace(/\s+/g, " ")
    .trim();
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
  const decorated = splitTagText(comment.customer_issue_tags);
  if (decorated.length > 0) {
    return uniqueStrings(decorated.filter((label) => isCustomerLabelAllowed(label, locale)));
  }

  const occurrences = customerLabelOccurrences(comment, "issue", locale)
    .map((occurrence) => occurrence.label)
    .filter(Boolean);
  if (occurrences.length > 0) {
    return uniqueStrings(occurrences);
  }

  const payload = parseAspectsPayload(comment);
  const aspects = getAspects(comment);
  const labels = aspects
    .filter((aspect) => {
      const hasSpecificIssuePayload = Boolean(aspect.specific_issue || aspect.specific_issue_zh) &&
        Boolean(aspect.canonical_issue_key);
      return (
        (String(aspect.polarity || "").toLowerCase() === "negative" || hasSpecificIssuePayload) &&
        aspect.display_allowed !== false &&
        hasSpecificIssuePayload
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
  return uniqueStrings(splitTagText(comment.issue_tag).filter((label) => isCustomerLabelAllowed(label, locale)));
}

export function customerHighlightTags(comment: RecordValue, locale: string): string[] {
  const decorated = splitTagText(comment.customer_highlight_tags);
  if (decorated.length > 0) {
    return uniqueStrings(decorated.filter((label) => isCustomerLabelAllowed(label, locale)));
  }

  const occurrences = customerLabelOccurrences(comment, "highlight", locale)
    .map((occurrence) => occurrence.label)
    .filter(Boolean);
  if (occurrences.length > 0) {
    return uniqueStrings(occurrences);
  }

  const payload = parseAspectsPayload(comment);
  const labels = getAspects(comment)
    .filter((aspect) => {
      return (
        String(aspect.polarity || "").toLowerCase() === "positive" &&
        aspect.highlight_display_allowed !== false &&
        Boolean(aspect.customer_highlight || aspect.customer_highlight_zh) &&
        Boolean(aspect.canonical_highlight_key)
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
  return uniqueStrings(splitTagText(comment.highlight_tag).filter((label) => isCustomerLabelAllowed(label, locale)));
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
      const aspectKey = String(occurrence.aspect_key || "").trim();
      const label = localeLabel(occurrence.display_label_en, occurrence.display_label_zh, locale);
      const dimension = localeLabel(occurrence.dimension_en, occurrence.dimension_zh, locale) ||
        (aspectKey ? aspectLabel(aspectKey, locale) : "");
      const evidenceSpan = String(occurrence.evidence_span || "").trim();
      return {
        type,
        label,
        rawLabel: String(occurrence.raw_label || label).trim(),
        canonicalLabelKey: String(occurrence.canonical_label_key || "").trim(),
        aspectKey,
        dimension,
        evidenceSpan,
        evidenceVerified: evidenceVerified(comment, evidenceSpan, clusterPropagated || boolValue(occurrence.cluster_propagated)),
        clusterPropagated: clusterPropagated || boolValue(occurrence.cluster_propagated),
        confidence: String(occurrence.confidence || "").trim(),
        source: String(occurrence.source_detail || occurrence.source || "").trim(),
        subCategory: String(occurrence.sub_category || subCategory).trim(),
        legacyFallback: boolValue(occurrence.legacy_fallback) || String(occurrence.source || "") === "legacy",
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
      const aspectKey = String(aspect.key || aspect.aspect_key || "").trim();
      const label = type === "issue"
        ? localeLabel(aspect.specific_issue, aspect.specific_issue_zh, locale)
        : localeLabel(aspect.customer_highlight, aspect.customer_highlight_zh, locale);
      const canonicalLabelKey = type === "issue"
        ? String(aspect.canonical_issue_key || "").trim()
        : String(aspect.canonical_highlight_key || "").trim();
      const evidenceSpan = String(aspect.evidence_span || aspect.evidence || "").trim();
      const dimension = aspectKey ? aspectLabel(aspectKey, locale) : String(aspect.dimension || aspect.aspect_label || "").trim();
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
        evidenceVerified: evidenceVerified(comment, evidenceSpan, clusterPropagated || boolValue(aspect.cluster_propagated)),
        clusterPropagated: clusterPropagated || boolValue(aspect.cluster_propagated),
        confidence: String(type === "issue" ? aspect.issue_confidence || "" : aspect.highlight_confidence || "").trim(),
        source: String(type === "issue" ? aspect.issue_source || "" : aspect.highlight_source || "").trim(),
        subCategory,
        legacyFallback: false,
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
  return !occurrence.clusterPropagated;
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
